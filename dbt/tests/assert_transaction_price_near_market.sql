-- Every trade must happen on a day with market data, at a price within
-- `trade_price_tolerance` of that day's close (after split adjustment).
-- Catches typos and pre-/post-split mix-ups, e.g. GOOGL entered at $2,800
-- in June 2023 when the (post-split) stock traded around $124.
select
    t.trade_id,
    t.symbol,
    t.trade_date,
    t.price_as_traded,
    t.price       as split_adjusted_price,
    p.close       as market_close,
    case when p.close is null then 'no market data on trade date'
         else 'price ' || round(100 * (t.price / p.close - 1), 1) || '% away from close' end as problem
from {{ ref('int_transactions_split_adjusted') }} t
left join {{ ref('stg_prices') }} p
    on p.symbol = t.symbol and p.price_date = t.trade_date
where p.close is null
   or abs(t.price / p.close - 1) > {{ var('trade_price_tolerance') }}
