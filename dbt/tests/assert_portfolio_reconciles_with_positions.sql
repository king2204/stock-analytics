-- The portfolio mart must equal the sum of its positions on the latest date.
with latest_portfolio as (
    select market_value from {{ ref('fct_portfolio_daily') }}
    order by date desc limit 1
),
latest_holdings as (
    select sum(market_value) as market_value from {{ ref('mart_holdings_current') }}
)
select p.market_value as portfolio_value, h.market_value as holdings_value
from latest_portfolio p, latest_holdings h
where abs(p.market_value - h.market_value) > 0.01
