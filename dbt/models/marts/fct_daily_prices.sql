select
    symbol,
    price_date,
    open,
    high,
    low,
    close,
    volume,
    dividend_per_share,
    split_ratio,
    price_return,
    total_return,
    ln(1 + total_return) as log_return,
    -- growth of $1 invested at the first loaded date, dividends reinvested
    exp(sum(ln(1 + coalesce(total_return, 0)))
        over (partition by symbol order by price_date)) as total_return_index
from {{ ref('int_daily_returns') }}
