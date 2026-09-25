with price_span as (
    select symbol, min(price_date) as first_price_date, max(price_date) as last_price_date,
           count(*) as trading_days_loaded
    from {{ ref('stg_prices') }}
    group by symbol
),

trades as (
    select symbol, min(trade_date) as first_trade_date, count(*) as trade_count
    from {{ ref('stg_transactions') }}
    group by symbol
)

select
    t.symbol,
    t.company_name,
    t.sector,
    t.is_benchmark,
    p.first_price_date,
    p.last_price_date,
    coalesce(p.trading_days_loaded, 0) as trading_days_loaded,
    tr.first_trade_date,
    coalesce(tr.trade_count, 0)       as trade_count
from {{ ref('stg_tickers') }} t
left join price_span p using (symbol)
left join trades tr using (symbol)
