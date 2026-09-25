# 📊 Stock Portfolio Analytics

**An end-to-end data engineering and analytics project built on a real stock portfolio.**

Daily market data from Yahoo Finance is loaded **incrementally** into a **DuckDB** warehouse,
modeled with **dbt** into a star schema, checked by **50 data-quality tests**, scheduled with
**Dagster** or GitHub Actions, and served by a **Streamlit** dashboard. The dashboard answers:
*Is my portfolio beating the market, how risky is it, and would a different strategy have done better?*

[![CI](https://github.com/king2204/stock-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/king2204/stock-analytics/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![dbt](https://img.shields.io/badge/dbt-duckdb-orange)
![Dagster](https://img.shields.io/badge/orchestration-dagster-purple)
![Streamlit](https://img.shields.io/badge/dashboard-streamlit-red)

![Dashboard overview](docs/screenshots/v2-01-overview.png)

---

## Contents

1. [How it works](#how-it-works)
2. [Run it on your computer](#run-it-on-your-computer)
3. [The dashboard](#the-dashboard)
4. [Data engineering](#data-engineering)
5. [Data analytics](#data-analytics)
6. [Use your own portfolio](#use-your-own-portfolio)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)
9. [Project layout](#project-layout)
10. [Limitations](#limitations)

---

## How it works

```
 Yahoo Finance (or the offline sample market)
        │
        ▼
 pipelines/ingest.py ──────────► data/lake/raw/prices/…/<run_id>.parquet   (raw copy of every download)
   • only fetches new days (watermark + 5-day lookback)
   • retries, quarantines bad rows, logs every run
        │
        ▼
 DuckDB  raw.*  ──► dbt: staging ──► intermediate ──► marts  (+ 50 data tests)
                                                         │
        Dagster schedule / GitHub Actions cron           │
        (weekdays after the US market close)             ▼
                              Streamlit dashboard · SQL business questions · Jupyter report
```

The dashboard **only reads the warehouse**. It never calls Yahoo on page load, so it opens fast
and keeps working when the data provider is down.

---

## Run it on your computer

You need **Python 3.11 or newer** and **git**.

```bash
git clone https://github.com/king2204/stock-analytics.git
cd stock-analytics

python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

python -m pipelines.run              # load real prices and build the warehouse (about 1 minute the first time)
python -m streamlit run app.py       # open http://localhost:8501
```

Keep the terminal open while you use the dashboard. Press **Ctrl + C** to stop it.

**No internet, or Yahoo blocking you?** Use the built-in sample market instead. The prices are
synthetic, and the dashboard says so:

```bash
SOURCE=sample python -m pipelines.run          # Windows PowerShell: $env:SOURCE="sample"; python -m pipelines.run
```

**Using conda?** Run `conda deactivate` before `source .venv/bin/activate`, and always start the
app with `python -m streamlit`, not `streamlit`. Otherwise conda's own Streamlit may start and
fail with `No module named 'duckdb'`.

### Handy commands

| Command | What it does |
|---|---|
| `python -m pipelines.run` | Load new prices and rebuild the warehouse (models + tests) |
| `python -m pipelines.run --full-refresh` | Reload the full history from `start_date` |
| `python -m streamlit run app.py` | Start the dashboard on http://localhost:8501 |
| `python -m analysis.run_queries` | Print the answers to the 10 SQL business questions |
| `dagster dev -m pipelines.dagster_defs` | Dagster UI with the pipeline graph and daily schedule on http://localhost:3000 |
| `cd dbt && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .` | Browse model lineage and column docs |
| `pytest -q` | Run the 53 tests |
| `docker compose up` | Build the warehouse and serve the dashboard in containers |

On Mac and Linux, the `Makefile` has short versions of these commands (`make pipeline`,
`make dashboard`, `make test`, `make demo`, …).

---

## The dashboard

| Tab | What you see |
|---|---|
| **Overview** | Portfolio value vs money put in, total profit, time-weighted return vs S&P 500 (SPY), money-weighted return (XIRR), allocation by stock and sector, a concentration warning, open positions, and the trade ledger restated for stock splits |
| **Performance** | Cumulative return vs SPY; Sharpe, Sortino and Calmar ratios; beta, alpha, tracking error, information ratio, upside/downside capture; monthly return heatmaps |
| **Risk** | Drawdown vs benchmark, rolling volatility and beta, value-at-risk in dollars, per-stock risk table, correlation matrix |
| **Strategy Lab** | Lump sum vs monthly investing vs monthly with quarterly rebalancing (same money), efficient frontier with max-Sharpe and min-volatility picks, Monte Carlo projection of future value |
| **Pipeline & Data Quality** | Last pipeline runs, data-test pass rate, freshness per stock, warehouse row counts, quarantined rows, and a **Run pipeline** button that shows live progress |

| | |
|---|---|
| ![Performance](docs/screenshots/v2-02-performance.png) | ![Risk](docs/screenshots/v2-03-risk.png) |
| ![Strategy Lab](docs/screenshots/v2-04-strategy-lab.png) | ![Pipeline & Data Quality](docs/screenshots/v2-05-pipeline-data-quality.png) |

*The screenshots use the sample market (synthetic prices).*

---

## Data engineering

### Ingestion (`pipelines/ingest.py`)

- **Incremental:** for each stock, only dates after the last loaded day are requested, plus a
  5-day overlap so late corrections from the provider overwrite stale rows.
- **Idempotent:** rows are upserted on `(symbol, date)`, so re-running a day never creates duplicates.
- **Raw landing zone:** every download is also saved as Parquet under `data/lake/`, so the
  warehouse can be rebuilt without calling the API again.
- **Resilient:** each stock is retried with exponential backoff. One failing stock marks the run
  `partial` instead of stopping everything.
- **Quarantine:** rows with an impossible price (close ≤ 0, high below low, close outside
  the high/low range, duplicate date) go to `raw.prices_quarantine` with a reason.
- **Corporate actions:** dividends and splits are stored separately. If the provider withdraws
  one, it is removed on the next load.
- **One source at a time:** switching between sample and real data reloads that stock's full
  history, so fake and real prices are never mixed.
- **One run at a time:** a lock file stops two pipeline runs from writing at once, and a
  "file is locked" error names the program holding it.
- **Run log:** every run is recorded in `meta.ingestion_runs`, and every data-test result in
  `meta.dbt_results`.

### Modeling (`dbt/`, DuckDB)

| Layer | Models |
|---|---|
| **staging** (views) | `stg_prices`, `stg_dividends`, `stg_splits`, `stg_tickers`, `stg_transactions` |
| **intermediate** | `int_daily_returns`: total return from close + dividends. `int_transactions_split_adjusted`: trades restated for later splits. `int_trade_ledger`: average-cost ledger built with a recursive CTE |
| **marts** (tables) | `dim_date`, `dim_ticker`, `fct_daily_prices`, `fct_position_daily`, `fct_portfolio_daily`, `mart_holdings_current`, `mart_monthly_returns`, `mart_ticker_risk` |

Real-world problems the models handle:

- **Stock splits:** trades are entered exactly as the broker showed them, then restated.
  1 AMZN share bought at $3,022 in March 2022 becomes 20 shares at $151.10 after the 20:1 split.
- **Adjusted prices that change backwards:** providers rewrite `adj_close` for every past day
  whenever a dividend is paid. An incremental load would only pick part of that up, so total
  return is recomputed from `close + dividend` instead.
- **Deposits distort returns:** portfolio performance uses a time-weighted return, which removes
  the effect of when money was added. Money-weighted XIRR is shown alongside it.

### Data quality (50 dbt tests + source freshness)

Custom generic tests (`unique_combination_of_columns`, `positive`, `within_range`,
`not_in_future`), relationship and accepted-value tests, plus business-rule tests:

| Test | Catches |
|---|---|
| `assert_transaction_price_near_market` | A trade price more than 30% away from that day's close. This catches typos and pre/post-split mix-ups; the original sample file had GOOGL at $2,800 in June 2023, when the stock traded near $124 |
| `assert_no_unexplained_price_jumps` | A >50% one-day move with no split recorded, which usually means an unadjusted price |
| `assert_portfolio_reconciles_with_positions` | The portfolio total drifting from the sum of its holdings |
| `shares_after >= 0` on the ledger | Selling more shares than you own |
| source freshness | Prices older than 4 days (warning) or 7 days (error) |

If any test fails, the build stops and the dashboard keeps showing the last good data.

### Orchestration

- **Dagster** (`pipelines/dagster_defs.py`): `raw_market_data` → `dbt_warehouse` assets, a
  freshness check, retries with exponential backoff, and a weekday 17:30 New York schedule.
- **GitHub Actions:**
  - `ci.yml` runs lint, `dbt parse` and all tests on every pull request.
  - `daily-pipeline.yml` loads real prices each weekday evening (keeping the warehouse in the
    Actions cache) and publishes the DuckDB file and test results as a downloadable artifact.

---

## Data analytics

- **Dashboard metrics** (`src/metrics.py`): annualized return and volatility, Sharpe, Sortino,
  Calmar, max drawdown, historical and parametric VaR, CVaR, beta, Jensen's alpha, tracking
  error, information ratio, capture ratios, rolling metrics, TWR and XIRR.
- **Strategies** (`src/strategies.py`): backtests that invest the same total money three ways,
  a block-bootstrap Monte Carlo projection, and a long-only efficient frontier.
- **SQL analysis** (`analysis/business_questions.sql`): 10 questions answered straight from the
  warehouse:
  1. Did we beat the market?
  2. Which positions made the profit?
  3. How concentrated are we by sector (HHI)?
  4. Best and worst months
  5. Monthly hit rate vs the benchmark
  6. Drawdown episodes and recovery time
  7. Dividend income by year
  8. Risk-adjusted ranking of stocks
  9. Did each buy beat simply buying SPY that day?
  10. Data coverage per stock
- **Report** (`notebooks/portfolio_analysis.ipynb`): question → method → findings computed from
  the data → recommendations and caveats. Re-run it with
  `jupyter nbconvert --to notebook --execute --inplace notebooks/portfolio_analysis.ipynb`.

---

## Use your own portfolio

1. **Stocks:** list them in `config/pipeline.toml` with their sector. Keep the benchmark (`SPY`) in the list.
2. **Trades:** put them in `data/portfolio_transactions.csv`, exactly as your broker shows them:

   ```csv
   trade_id,trade_date,symbol,side,shares,price,fees
   T0001,2023-01-17,AAPL,BUY,10,135.94,0.00
   T0002,2025-02-03,AAPL,SELL,2,228.01,0.00
   ```

   Don't adjust anything for later splits yourself; the warehouse does it.
3. **Run** `python -m pipelines.run`. If a trade looks wrong (for example a price far from that
   day's market price, or selling shares you don't own), the build stops and names the trade.

Other settings in `config/pipeline.toml`: `start_date`, `benchmark`, `risk_free_rate`,
`lookback_days`, and the default `source` (`yahoo` or `sample`). Any of them can be overridden
with an environment variable of the same name in capitals, for example `SOURCE=sample`.

---

## Testing

```bash
pytest -q        # 53 tests, about 1 minute, no internet needed
ruff check .     # lint
```

| Level | What is tested |
|---|---|
| Unit | Every metric against hand-computed values; backtest, Monte Carlo and frontier invariants; sample-market properties |
| Ingestion | Incremental windows, idempotency, retries and backoff, quarantine, partial failure, corporate-action retraction, source switching, trade-file validation |
| Locking | A second run is refused, stale locks are cleared, lock errors are readable |
| Warehouse | The full pipeline with dbt on sample data: split restatement, average cost, realized P&L, dividends, TWR matching the Python implementation, reconciliation; bad trades fail the build |
| Serving | All 10 SQL questions run, the dashboard renders every tab and handles a failed run, and the Dagster assets materialize |

CI runs the same suite on every pull request.

---

## Troubleshooting

| You see | What it means and what to do |
|---|---|
| `No module named 'pipelines'` or `app.py` not found | You're not in the project folder, or not on the branch with the new code. Run `cd stock-analytics` and `git pull` |
| `No module named 'duckdb'` from a path containing `miniforge`/`conda` | The wrong Streamlit started. Run `conda deactivate`, then `source .venv/bin/activate`, then `python -m streamlit run app.py` |
| `A pipeline run is already in progress` | Another run is still going. Wait for it to finish |
| `The warehouse file is in use by another program (process 1234)` | An old dashboard or pipeline still has the file open. Stop it with **Ctrl + C** in its terminal, or run `kill 1234` |
| `localhost refused to connect` | The dashboard isn't running. Start it with `python -m streamlit run app.py` and keep that terminal open |
| `dbt build failed` | A data test caught a problem. The failing test name tells you what; the Pipeline & Data Quality tab lists it too |
| Yahoo errors or timeouts | Yahoo Finance is unofficial and rate-limited. Try again later, or use `SOURCE=sample` |

---

## Project layout

```
config/pipeline.toml        stocks, benchmark, data source, paths
data/                       your trades (portfolio_transactions.csv); warehouse and lake are generated here
pipelines/                  data sources, incremental ingestion, locking, CLI runner, Dagster definitions
dbt/                        staging / intermediate / marts models, generic and business-rule tests
src/                        metrics, strategies, charts, warehouse query layer
app.py                      Streamlit dashboard
analysis/                   SQL business questions and runner
notebooks/                  analysis report
tests/                      pytest suite (unit + integration)
.github/workflows/          CI and the daily scheduled pipeline
docs/                       screenshots and a sample build log
```

Older files from the first version of the project (`streamlit_advanced.py`, `dashboard*.py`,
`advanced_dashboard.py`, `streamlit_app.py`, `src/analyzer.py` and related modules, and the
AWS deployment docs) are kept for reference only. They aren't used by the new pipeline or
dashboard, and they're excluded from linting.

---

## Limitations

- Cost basis uses the average-cost method, not individual tax lots (FIFO).
- At portfolio level, dividends are counted as cash rather than reinvested. Per-stock metrics
  reinvest them.
- Yahoo Finance is unofficial and can be rate-limited. For production use, add a paid provider
  as another `PriceSource` in `pipelines/sources.py`.
- Backtests, the efficient frontier and the Monte Carlo projection use past data only. They are
  not forecasts or investment advice.
- The Docker setup is included but hasn't been run end to end yet.
