with bounds as (
    select min(price_date) as start_date, max(price_date) as end_date
    from {{ ref('stg_prices') }}
),

spine as (
    select cast(range as date) as date_day
    from bounds, range(bounds.start_date, bounds.end_date + interval 1 day, interval 1 day)
),

trading_days as (
    select price_date from {{ ref('stg_prices') }} where symbol = '{{ var("benchmark") }}'
)

select
    s.date_day,
    extract(year from s.date_day)     as year,
    extract(quarter from s.date_day)  as quarter,
    extract(month from s.date_day)    as month,
    monthname(s.date_day)             as month_name,
    date_trunc('month', s.date_day)   as month_start,
    extract(isodow from s.date_day)   as iso_day_of_week,
    dayname(s.date_day)               as day_name,
    t.price_date is not null          as is_trading_day,
    t.price_date is not null
        and s.date_day = max(t.price_date) over (partition by date_trunc('month', s.date_day))
                                      as is_month_end_trading_day
from spine s
left join trading_days t on t.price_date = s.date_day
