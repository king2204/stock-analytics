-- Daily total return computed from split-adjusted close + cash dividends.
-- We deliberately do NOT use the provider's adj_close: it is restated for
-- all past dates whenever a new dividend is paid, which an incremental loader
-- would only partially pick up. Recomputing here is always consistent.
with prices as (
    select * from {{ ref('stg_prices') }}
),

joined as (
    select
        p.*,
        coalesce(d.dividend_per_share, 0) as dividend_per_share,
        coalesce(s.split_ratio, 0)        as split_ratio,
        lag(p.close) over (partition by p.symbol order by p.price_date) as prev_close
    from prices p
    left join {{ ref('stg_dividends') }} d
        on d.symbol = p.symbol and d.ex_date = p.price_date
    left join {{ ref('stg_splits') }} s
        on s.symbol = p.symbol and s.split_date = p.price_date
)

select
    symbol,
    price_date,
    open,
    high,
    low,
    close,
    volume,
    dividend_per_share,
    split_ratio,
    prev_close,
    case when prev_close > 0 then (close - prev_close) / prev_close end
        as price_return,
    case when prev_close > 0 then (close + dividend_per_share - prev_close) / prev_close end
        as total_return
from joined
