-- One row per held symbol per trading day: shares, cost basis, market value,
-- dividends received and P&L. Grain: (symbol, date).
with calendar as (
    select price_date as date
    from {{ ref('stg_prices') }}
    where symbol = '{{ var("benchmark") }}'
),

first_trade as (
    select symbol, min(trade_date) as first_trade_date
    from {{ ref('int_trade_ledger') }}
    group by symbol
),

-- position at the end of each trade date (several trades a day -> last one)
ledger_eod as (
    select *
    from {{ ref('int_trade_ledger') }}
    qualify row_number() over (partition by symbol, trade_date order by seq desc) = 1
),

daily_flows as (
    select symbol, trade_date, sum(net_cash_flow) as net_cash_flow
    from {{ ref('int_transactions_split_adjusted') }}
    group by symbol, trade_date
),

grid as (
    select c.date, f.symbol
    from calendar c
    join first_trade f on c.date >= f.first_trade_date
),

positioned as (
    select
        g.date,
        g.symbol,
        l.shares_after            as shares,
        l.avg_cost_after          as avg_cost,
        l.realized_pnl_cumulative as realized_pnl_cumulative,
        coalesce(df.net_cash_flow, 0) as net_cash_flow
    from grid g
    asof left join ledger_eod l
        on l.symbol = g.symbol and g.date >= l.trade_date
    left join daily_flows df
        on df.symbol = g.symbol and df.trade_date = g.date
),

priced as (
    select
        p.*,
        -- carry the last close forward if a ticker has a gap
        last_value(r.close ignore nulls) over (
            partition by p.symbol order by p.date rows between unbounded preceding and current row
        ) as close,
        coalesce(r.dividend_per_share, 0) as dividend_per_share,
        -- dividends go to shares held going into the ex-date
        lag(p.shares, 1, 0) over (partition by p.symbol order by p.date) as shares_prev_day
    from positioned p
    left join {{ ref('int_daily_returns') }} r
        on r.symbol = p.symbol and r.price_date = p.date
)

select
    date,
    symbol,
    shares,
    avg_cost,
    shares * avg_cost                              as cost_basis,
    close,
    shares * close                                 as market_value,
    shares * (close - avg_cost)                    as unrealized_pnl,
    realized_pnl_cumulative,
    net_cash_flow,
    shares_prev_day * dividend_per_share           as dividend_income,
    sum(shares_prev_day * dividend_per_share)
        over (partition by symbol order by date)   as dividends_cumulative
from priced
