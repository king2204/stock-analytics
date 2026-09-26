-- Business questions answered directly against the warehouse.
-- Run all of them:   python -m analysis.run_queries
-- Or open the DB:     duckdb data/warehouse/stocks.duckdb   and paste a query.
-- Each query starts with a "-- name:" line so the runner (and the tests) can find it.

-- name: q1_did_we_beat_the_market
-- Q1. Since the first trade, did the portfolio beat the benchmark (time-weighted)?
select
    min(date)                                                    as since,
    max(date)                                                    as as_of,
    last(twr_index order by date) - 1                            as portfolio_return,
    last(benchmark_index order by date) - 1                      as benchmark_return,
    (last(twr_index order by date) - last(benchmark_index order by date)) as excess_return
from marts.fct_portfolio_daily;

-- name: q2_contribution_to_profit
-- Q2. Which positions contributed most to total profit (unrealised + realised + dividends)?
select
    symbol,
    sector,
    unrealized_pnl + realized_pnl + dividends_received                         as total_contribution,
    (unrealized_pnl + realized_pnl + dividends_received)
        / sum(unrealized_pnl + realized_pnl + dividends_received) over ()      as share_of_profit
from marts.mart_holdings_current
order by total_contribution desc;

-- name: q3_sector_concentration
-- Q3. How concentrated is the portfolio by sector? (HHI > 0.25 = highly concentrated)
with s as (
    select sector, sum(weight) as weight
    from marts.mart_holdings_current
    group by sector
)
select
    sector,
    weight,
    sum(weight * weight) over () as herfindahl_index
from s
order by weight desc;

-- name: q4_best_and_worst_months
-- Q4. Best and worst three months, with the benchmark in the same month.
(select 'best' as bucket, month, portfolio_return, benchmark_return
 from marts.mart_monthly_returns order by portfolio_return desc limit 3)
union all
(select 'worst' as bucket, month, portfolio_return, benchmark_return
 from marts.mart_monthly_returns order by portfolio_return asc limit 3)
order by bucket, portfolio_return desc;

-- name: q5_hit_rate_vs_benchmark
-- Q5. In what share of months did the portfolio beat the benchmark, by year?
select
    extract(year from month)                                        as year,
    count(*)                                                        as months,
    count(*) filter (where excess_return > 0)                       as months_beating_benchmark,
    count(*) filter (where excess_return > 0) / count(*)            as hit_rate,
    exp(sum(ln(1 + portfolio_return))) - 1                          as portfolio_year_return,
    exp(sum(ln(1 + benchmark_return))) - 1                          as benchmark_year_return
from marts.mart_monthly_returns
group by 1
order by 1;

-- name: q6_drawdown_episodes
-- Q6. Worst drawdown episodes: peak date, trough, depth and days to recover.
with flagged as (
    select *,
           sum(case when drawdown = 0 then 1 else 0 end) over (order by date) as episode
    from marts.fct_portfolio_daily
),
episodes as (
    select
        episode,
        min(date)                         as peak_date,
        arg_min(date, drawdown)           as trough_date,
        min(drawdown)                     as depth,
        max(date)                         as last_underwater_date,
        count(*) - 1                      as days_underwater
    from flagged
    group by episode
    having min(drawdown) < 0
)
select peak_date, trough_date, depth, days_underwater,
       last_underwater_date < (select max(date) from marts.fct_portfolio_daily) as recovered
from episodes
order by depth
limit 5;

-- name: q7_dividend_income_by_year
-- Q7. Dividend income received per year and per ticker.
select
    extract(year from date) as year,
    symbol,
    sum(dividend_income)    as dividends
from marts.fct_position_daily
where dividend_income > 0
group by 1, 2
order by 1, 3 desc;

-- name: q8_risk_return_ranking
-- Q8. Rank tickers by risk-adjusted return over the last year.
select
    symbol,
    annual_return,
    annual_volatility,
    sharpe_ratio,
    beta,
    rank() over (order by sharpe_ratio desc) as sharpe_rank
from marts.mart_ticker_risk
order by sharpe_rank;

-- name: q9_trade_timing
-- Q9. Did each buy beat simply buying the benchmark on the same day?
-- Both sides are total return (dividends reinvested) from the trade date.
with buys as (
    select trade_id, symbol, trade_date, price
    from intermediate.int_transactions_split_adjusted
    where side = 'BUY'
),
latest as (
    select symbol, arg_max(total_return_index, price_date) as last_tri
    from marts.fct_daily_prices group by symbol
),
bench as (
    select symbol from marts.dim_ticker where is_benchmark limit 1
)
select
    b.trade_id,
    b.symbol,
    b.trade_date,
    -- entry at the trade price rather than the close, then grow with the index
    (l.last_tri / p.total_return_index) * (p.close / b.price) - 1      as trade_return,
    bl.last_tri / bp.total_return_index - 1                            as benchmark_return_same_period,
    (l.last_tri / p.total_return_index) * (p.close / b.price)
        - bl.last_tri / bp.total_return_index                          as excess_vs_benchmark
from buys b
join marts.fct_daily_prices p on p.symbol = b.symbol and p.price_date = b.trade_date
join latest l on l.symbol = b.symbol
cross join bench
join marts.fct_daily_prices bp on bp.symbol = bench.symbol and bp.price_date = b.trade_date
join latest bl on bl.symbol = bench.symbol
order by excess_vs_benchmark desc;

-- name: q10_data_coverage
-- Q10. Data coverage and freshness per ticker (a data-engineering sanity check).
select
    t.symbol,
    t.first_price_date,
    t.last_price_date,
    t.trading_days_loaded,
    d.expected_days,
    t.trading_days_loaded / d.expected_days as coverage
from marts.dim_ticker t
cross join (select count(*) as expected_days from marts.dim_date where is_trading_day) d
order by coverage, t.symbol;
