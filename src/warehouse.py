"""Read-only query helpers used by the dashboard, notebook and tests.

The serving layer only ever reads ``marts`` / ``meta`` tables — it never
calls a market data API — so dashboard load time does not depend on Yahoo.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from pipelines.locking import friendly_lock_error


class Warehouse:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"No warehouse at {self.path}. Run `python -m pipelines.run` first.")

    def query(self, sql: str, params: list | None = None) -> pd.DataFrame:
        try:
            con = duckdb.connect(str(self.path), read_only=True)
        except duckdb.IOException as exc:
            raise friendly_lock_error(exc) from exc
        with con:
            return con.execute(sql, params or []).df()

    def has_marts(self) -> bool:
        n = self.query("select count(*) as n from information_schema.tables "
                       "where table_schema = 'marts' and table_name = 'fct_portfolio_daily'")
        return bool(n["n"].iloc[0])

    def holdings(self) -> pd.DataFrame:
        return self.query("select * from marts.mart_holdings_current order by market_value desc")

    def portfolio_daily(self) -> pd.DataFrame:
        df = self.query("select * from marts.fct_portfolio_daily order by date")
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")

    def position_daily(self) -> pd.DataFrame:
        df = self.query("select * from marts.fct_position_daily order by date, symbol")
        df["date"] = pd.to_datetime(df["date"])
        return df

    def monthly_returns(self) -> pd.DataFrame:
        df = self.query("select * from marts.mart_monthly_returns order by month")
        df["month"] = pd.to_datetime(df["month"])
        return df

    def ticker_risk(self) -> pd.DataFrame:
        return self.query("""
            select r.*, t.company_name, t.sector, t.is_benchmark
            from marts.mart_ticker_risk r join marts.dim_ticker t using (symbol)
            order by t.is_benchmark, r.symbol
        """)

    def tickers(self) -> pd.DataFrame:
        return self.query("select * from marts.dim_ticker order by is_benchmark, symbol")

    def price_matrix(self, column: str = "total_return_index", start=None, end=None) -> pd.DataFrame:
        """Wide frame: date x symbol."""
        if column not in ("close", "total_return_index", "total_return"):
            raise ValueError(column)
        df = self.query(f"""
            select price_date, symbol, {column} as v from marts.fct_daily_prices
            where (? is null or price_date >= ?) and (? is null or price_date <= ?)
        """, [start, start, end, end])
        wide = df.pivot(index="price_date", columns="symbol", values="v").sort_index()
        wide.index = pd.to_datetime(wide.index)
        return wide

    def transactions(self) -> pd.DataFrame:
        return self.query("select * from intermediate.int_transactions_split_adjusted order by trade_date")

    # ---- pipeline observability -------------------------------------------------

    def ingestion_runs(self, limit: int = 20) -> pd.DataFrame:
        return self.query("select * from meta.ingestion_runs order by started_at desc limit ?", [limit])

    def table_stats(self) -> pd.DataFrame:
        tables = self.query("""
            select schema_name, table_name from duckdb_tables()
            where schema_name in ('raw', 'marts', 'meta') order by schema_name, table_name
        """)
        if tables.empty:
            return pd.DataFrame(columns=["schema", "table", "rows"])
        union = " union all ".join(
            f"select '{s}' as schema, '{t}' as \"table\", count(*) as rows from {s}.{t}"
            for s, t in tables.itertuples(index=False))
        return self.query(union)

    def quarantine(self) -> pd.DataFrame:
        return self.query("select * from raw.prices_quarantine order by ingested_at desc limit 200")

    def freshness(self) -> pd.DataFrame:
        return self.query("""
            select symbol, cast(max(date) as date) as last_price_date, current_date - max(date) as days_behind,
                   max(ingested_at) as last_ingested_at, count(*) as rows
            from raw.prices group by symbol order by symbol
        """)


    def dbt_results(self) -> pd.DataFrame:
        """Node results of the most recent dbt build recorded in meta.dbt_results."""
        exists = self.query("select count(*) as n from duckdb_tables() "
                            "where schema_name = 'meta' and table_name = 'dbt_results'")["n"].iloc[0]
        if not exists:
            return pd.DataFrame(columns=["name", "resource_type", "status", "failures", "execution_time"])
        return self.query("""
            select name, resource_type, status, failures, round(execution_time, 3) as execution_time,
                   message, run_id, generated_at
            from meta.dbt_results
            where generated_at = (select max(generated_at) from meta.dbt_results)
            order by resource_type, name
        """)
