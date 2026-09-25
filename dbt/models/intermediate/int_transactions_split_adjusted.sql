-- Restate each trade in today's share units. A trade of 1 AMZN share at
-- $3,022 before the 20:1 split in June 2022 becomes 20 shares at $151.10,
-- which is what makes it comparable with split-adjusted prices.
with tx as (
    select * from {{ ref('stg_transactions') }}
),

factors as (
    select
        tx.trade_id,
        -- product of all split ratios after the trade date (exp(sum(ln)) = product)
        round(coalesce(exp(sum(ln(s.split_ratio))), 1.0), 8) as split_factor
    from tx
    left join {{ ref('stg_splits') }} s
        on s.symbol = tx.symbol and s.split_date > tx.trade_date
    group by tx.trade_id
)

select
    tx.trade_id,
    tx.trade_date,
    tx.symbol,
    tx.side,
    tx.shares                          as shares_as_traded,
    tx.price                           as price_as_traded,
    f.split_factor,
    tx.shares * f.split_factor         as shares,
    tx.price / f.split_factor          as price,
    tx.fees,
    tx.shares * tx.price               as gross_amount,
    -- cash put into (+) or taken out of (-) the portfolio
    case when tx.side = 'BUY' then tx.shares * tx.price + tx.fees
         else -(tx.shares * tx.price - tx.fees) end as net_cash_flow
from tx
join factors f using (trade_id)
