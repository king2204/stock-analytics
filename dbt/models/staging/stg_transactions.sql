-- Trades exactly as entered by the user, i.e. in shares/prices of the day.
select
    trade_id,
    trade_date,
    upper(trim(symbol))  as symbol,
    upper(trim(side))    as side,
    shares,
    price,
    coalesce(fees, 0)    as fees
from {{ source('raw', 'transactions') }}
