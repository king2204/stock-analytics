select
    upper(symbol)  as symbol,
    date           as split_date,
    value          as split_ratio   -- new shares per old share, e.g. 20 for a 20:1 split
from {{ source('raw', 'corporate_actions') }}
where action_type = 'split'
