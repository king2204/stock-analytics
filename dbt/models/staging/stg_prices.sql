-- One clean row per symbol and trading day. `close` is split-adjusted by the
-- provider; provider_adj_close is kept only for reference because providers
-- restate it backwards on every new dividend (see int_daily_returns).
select
    upper(symbol)                as symbol,
    date                         as price_date,
    cast(open as double)         as open,
    cast(high as double)         as high,
    cast(low as double)          as low,
    cast(close as double)        as close,
    cast(adj_close as double)    as provider_adj_close,
    cast(volume as bigint)       as volume,
    source,
    ingested_at
from {{ source('raw', 'prices') }}
where close is not null
