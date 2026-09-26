-- Every configured ticker should have loaded price history.
select symbol from {{ ref('dim_ticker') }} where trading_days_loaded = 0
