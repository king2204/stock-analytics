# Data

| Path | What | Committed? |
|---|---|---|
| `portfolio_transactions.csv` | Your trades — the only hand-maintained input. Record each trade exactly as your broker shows it on the day (unadjusted shares and price). The warehouse restates older trades for later stock splits automatically. | yes |
| `sample_portfolio.csv` | Legacy holdings file used by the old dashboards (prices corrected to real split-adjusted values). | yes |
| `lake/` | Raw Parquet snapshots written by every ingestion run (`raw/prices/symbol=.../ingest_date=.../<run_id>.parquet`). | no (generated) |
| `warehouse/stocks.duckdb` | DuckDB warehouse (`raw`, `staging`, `marts`, `meta` schemas). | no (generated) |

Two trades are deliberately from **before** a stock split so the split handling is exercised:

* `T0001` — 1 AMZN share at $3,022 in March 2022 → 20 shares at $151.10 after the 20:1 split.
* `T0004` — 5 NVDA shares at $397.70 in June 2023 → 50 shares at $39.77 after the 10:1 split.

The dbt test `assert_transaction_price_near_market` fails if a trade price is more than
30% away from that day's market close, which catches typos and pre/post-split mix-ups
(the old sample had GOOGL at $2,800 in June 2023 when the stock traded near $124).
