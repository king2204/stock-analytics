select
    upper(symbol)  as symbol,
    date           as ex_date,
    value          as dividend_per_share
from {{ source('raw', 'corporate_actions') }}
where action_type = 'dividend'
