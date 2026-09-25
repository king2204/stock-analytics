# Architecture

## Layers

```
┌──────────────┐   ┌──────────────────────┐   ┌─────────────────────────────┐   ┌──────────────────┐
│ Sources      │   │ Extract / Load        │   │ Transform (dbt on DuckDB)   │   │ Serve            │
│ YahooSource  │──►│ pipelines/ingest.py   │──►│ staging → intermediate →    │──►│ app.py (Streamlit)│
│ SampleSource │   │  watermark+lookback   │   │ marts  (+50 data tests)     │   │ analysis/*.sql   │
└──────────────┘   │  retries, quarantine  │   └─────────────────────────────┘   │ notebooks/       │
                   │  lake/*.parquet       │                                     └──────────────────┘
                   │  meta.ingestion_runs  │
                   └──────────────────────┘
        Orchestration: pipelines/run.py (CLI) · pipelines/dagster_defs.py · .github/workflows/daily-pipeline.yml
```

## Warehouse schemas (`data/warehouse/stocks.duckdb`)

| Schema | Written by | Contents |
|---|---|---|
| `raw` | ingest.py | `prices` (PK symbol+date), `corporate_actions`, `tickers`, `transactions`, `prices_quarantine` |
| `meta` | ingest.py | `ingestion_runs`: one row per run, with status, row counts and failed tickers |
| `staging` | dbt views | typed, renamed, one source table each |
| `intermediate` | dbt views | returns, split-adjusted trades, average-cost ledger (recursive CTE) |
| `marts` | dbt tables | star schema + analytics marts, the only layer the dashboard reads |

### Star schema

```
          dim_date ─────────┐
                             ▼
dim_ticker ──► fct_daily_prices        (symbol × trading day)
          └──► fct_position_daily      (held symbol × trading day)
                   └──► fct_portfolio_daily (trading day)
                            ├──► mart_monthly_returns
                            └──► mart_holdings_current (latest snapshot)
fct_daily_prices ──► mart_ticker_risk (trailing 252 days)
```

## Key design decisions

1. **Incremental + idempotent loads.** Watermark = `max(date)` per symbol. Each run re-requests the last
   `lookback_days` (5) and upserts, so provider corrections land and duplicates cannot happen.
2. **Raw Parquet landing zone.** Every API response is kept as an immutable file per run. That supports
   replay and backfill, and helps with debugging ("what did the API return on the 14th?").
3. **Quarantine, don't drop.** Invalid rows are stored with a reason and surfaced on the dashboard.
4. **Recompute total return instead of trusting `adj_close`.** Providers restate `adj_close` for all past
   dates whenever a dividend is paid. Total return = `(close_t + dividend_t) / close_{t-1} − 1`.
5. **Trades stored as traded; splits applied in the model.** This matches how brokers report trades, and
   the price-sanity test catches pre/post-split mistakes.
6. **Time-weighted return for skill, XIRR for the investor.** TWR chains
   `(V_t − CF_t) / V_{t−1}`, so deposits don't look like gains. XIRR answers "what did *my* money earn?".
7. **Serving never calls the API.** The dashboard reads only marts, so it is fast and still works when Yahoo is down.
8. **Offline sample source.** A seeded synthetic market that passes through realistic anchor prices and
   contains real split and dividend events. It makes CI deterministic and the demo network-free.

## Portfolio accounting conventions
- **Average-cost basis:** buys update the average cost, sells realise P&L against it.
- **Dividends:** paid on shares held at the previous close before the ex-date, and held as cash at
  portfolio level.
- **Sale proceeds** leave the portfolio as a negative cash flow.

## Testing strategy

| Level | Where | What |
|---|---|---|
| Unit | `tests/test_metrics.py`, `test_strategies.py`, `test_sources.py` | Metric formulas against hand-computed values, backtest invariants |
| Component | `tests/test_ingest.py` | Incremental windows, idempotency, retries/backoff, quarantine, partial failure, input validation |
| Data | `dbt build` | Schema tests, relationships, business-rule singular tests, freshness |
| Integration | `tests/test_dbt_models.py`, `test_serving.py` | Full pipeline on sample data, numbers reconcile, bad inputs fail the build, every SQL question runs, dashboard renders, Dagster assets materialize |
