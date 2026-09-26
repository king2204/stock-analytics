-- A >50% one-day move with no split recorded usually means the provider sent
-- an unadjusted price (e.g. a 20:1 split showing up as a -95% "crash").
select symbol, price_date, prev_close, close, price_return
from {{ ref('int_daily_returns') }}
where abs(price_return) > 0.5
  and split_ratio = 0
