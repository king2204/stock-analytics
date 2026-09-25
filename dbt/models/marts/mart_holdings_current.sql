-- Latest snapshot of open positions — what the dashboard's holdings table shows.
with latest as (
    select * from {{ ref('fct_position_daily') }}
    where date = (select max(date) from {{ ref('fct_position_daily') }})
),

totals as (
    select sum(market_value) as portfolio_value from latest where shares > 1e-9
)

select
    l.date                                        as as_of_date,
    l.symbol,
    t.company_name,
    t.sector,
    l.shares,
    l.avg_cost,
    l.cost_basis,
    l.close                                       as last_price,
    l.market_value,
    l.unrealized_pnl,
    l.unrealized_pnl / nullif(l.cost_basis, 0)    as unrealized_return,
    l.realized_pnl_cumulative                     as realized_pnl,
    l.dividends_cumulative                        as dividends_received,
    l.market_value / nullif(totals.portfolio_value, 0) as weight
from latest l
cross join totals
join {{ ref('dim_ticker') }} t using (symbol)
where l.shares > 1e-9
