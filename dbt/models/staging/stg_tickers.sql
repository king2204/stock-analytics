select
    upper(symbol)               as symbol,
    name                        as company_name,
    sector,
    coalesce(is_benchmark, false) as is_benchmark
from {{ source('raw', 'tickers') }}
