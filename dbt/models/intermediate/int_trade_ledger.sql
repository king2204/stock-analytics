-- Running position per symbol using the average-cost method, computed
-- trade by trade with a recursive CTE (buys move the average cost, sells
-- realise P&L against it and leave it unchanged).
with recursive ordered as (
    select
        *,
        row_number() over (partition by symbol order by trade_date, trade_id) as seq
    from {{ ref('int_transactions_split_adjusted') }}
),

ledger as (
    select
        symbol, seq, trade_id, trade_date, side, shares, price, fees, net_cash_flow,
        case when side = 'BUY' then shares else -shares end                    as shares_after,
        case when side = 'BUY' then (shares * price + fees) / shares else 0 end as avg_cost_after,
        case when side = 'SELL' then -(shares * price) - fees else 0 end       as realized_pnl
    from ordered
    where seq = 1

    union all

    select
        o.symbol, o.seq, o.trade_id, o.trade_date, o.side, o.shares, o.price, o.fees, o.net_cash_flow,
        l.shares_after + case when o.side = 'BUY' then o.shares else -o.shares end,
        case
            when o.side = 'BUY'
                then (l.shares_after * l.avg_cost_after + o.shares * o.price + o.fees)
                     / nullif(l.shares_after + o.shares, 0)
            else l.avg_cost_after
        end,
        case when o.side = 'SELL' then o.shares * (o.price - l.avg_cost_after) - o.fees else 0 end
    from ordered o
    join ledger l on o.symbol = l.symbol and o.seq = l.seq + 1
)

select
    symbol,
    seq,
    trade_id,
    trade_date,
    side,
    shares,
    price,
    fees,
    net_cash_flow,
    shares_after,
    avg_cost_after,
    realized_pnl,
    sum(realized_pnl)  over (partition by symbol order by seq) as realized_pnl_cumulative,
    sum(net_cash_flow) over (partition by symbol order by seq) as net_invested_cumulative
from ledger
