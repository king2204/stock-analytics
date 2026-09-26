-- Portfolio-level daily series with a time-weighted return (TWR) that strips
-- out the effect of deposits/withdrawals, plus the benchmark on the same days.
-- Convention: dividends are held as cash (not reinvested) and sale proceeds
-- leave the portfolio as a negative cash flow.
with daily as (
    select
        date,
        sum(market_value)             as market_value,
        sum(cost_basis)               as cost_basis,
        sum(unrealized_pnl)           as unrealized_pnl,
        sum(realized_pnl_cumulative)  as realized_pnl_cumulative,
        sum(net_cash_flow)            as net_cash_flow,
        sum(dividend_income)          as dividend_income,
        sum(dividends_cumulative)     as dividends_cumulative,
        count(*) filter (where shares > 0) as positions
    from {{ ref('fct_position_daily') }}
    group by date
),

valued as (
    select
        *,
        market_value + dividends_cumulative                          as total_value,
        sum(net_cash_flow) over (order by date)                      as net_contributions,
        lag(market_value + dividends_cumulative) over (order by date) as prev_total_value
    from daily
),

returns as (
    select
        *,
        case when prev_total_value > 0
             then (total_value - net_cash_flow) / prev_total_value - 1 end as daily_return
    from valued
),

indexed as (
    select
        *,
        exp(sum(ln(1 + coalesce(daily_return, 0))) over (order by date)) as twr_index
    from returns
),

benchmark as (
    select price_date as date, total_return as benchmark_return, total_return_index
    from {{ ref('fct_daily_prices') }}
    where symbol = '{{ var("benchmark") }}'
)

select
    i.date,
    i.positions,
    i.market_value,
    i.cost_basis,
    i.dividends_cumulative,
    i.total_value,
    i.net_cash_flow,
    i.net_contributions,
    i.total_value - i.net_contributions                    as total_pnl,
    i.unrealized_pnl,
    i.realized_pnl_cumulative,
    i.dividend_income,
    i.daily_return,
    i.twr_index,
    i.twr_index / max(i.twr_index) over (order by i.date) - 1 as drawdown,
    case when i.prev_total_value > 0 then b.benchmark_return end as benchmark_return,
    b.total_return_index / first_value(b.total_return_index) over (order by i.date)
                                                           as benchmark_index
from indexed i
left join benchmark b using (date)
