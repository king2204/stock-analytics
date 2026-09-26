-- Trailing one-year (252 trading days) risk/return profile for every ticker.
{% set rf = var('risk_free_rate') %}
with recent as (
    select *
    from {{ ref('fct_daily_prices') }}
    qualify row_number() over (partition by symbol order by price_date desc) <= 253
),

bench as (
    select price_date, total_return as bench_return
    from recent where symbol = '{{ var("benchmark") }}'
),

joined as (
    select
        r.symbol, r.price_date, r.total_return, r.total_return_index, b.bench_return,
        r.total_return_index
            / max(r.total_return_index) over (partition by r.symbol order by r.price_date) - 1 as drawdown
    from recent r
    left join bench b using (price_date)
)

select
    symbol,
    count(total_return)                                             as observations,
    exp(avg(ln(1 + total_return)) * 252) - 1                         as annual_return,
    stddev_samp(total_return) * sqrt(252)                            as annual_volatility,
    (exp(avg(ln(1 + total_return)) * 252) - 1 - {{ rf }})
        / nullif(stddev_samp(total_return) * sqrt(252), 0)           as sharpe_ratio,
    (exp(avg(ln(1 + total_return)) * 252) - 1 - {{ rf }})
        / nullif(sqrt(avg(power(least(total_return - {{ rf }} / 252, 0), 2))) * sqrt(252), 0)
                                                                     as sortino_ratio,
    min(drawdown)                                                    as max_drawdown,
    covar_samp(total_return, bench_return) / nullif(var_samp(bench_return), 0) as beta,
    corr(total_return, bench_return)                                 as correlation_to_benchmark,
    quantile_cont(total_return, 0.05)                                as var_95_daily
from joined
group by symbol
