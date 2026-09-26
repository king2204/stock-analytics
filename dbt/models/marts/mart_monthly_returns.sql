select
    date_trunc('month', date)                                   as month,
    exp(sum(ln(1 + coalesce(daily_return, 0)))) - 1             as portfolio_return,
    exp(sum(ln(1 + coalesce(benchmark_return, 0)))) - 1         as benchmark_return,
    (exp(sum(ln(1 + coalesce(daily_return, 0)))) - 1)
      - (exp(sum(ln(1 + coalesce(benchmark_return, 0)))) - 1)   as excess_return,
    sum(net_cash_flow)                                          as net_cash_flow,
    arg_max(total_value, date)                                  as month_end_value
from {{ ref('fct_portfolio_daily') }}
group by 1
