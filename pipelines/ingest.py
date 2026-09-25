"""Extract + load: market data and transactions into the DuckDB ``raw`` schema.

Design:
* **Incremental** — for each ticker we read the high-water mark (max loaded
  date) and only request ``watermark - lookback_days .. today``. The small
  overlap lets late provider corrections overwrite stale rows.
* **Idempotent** — loads are upserts on the natural key, so re-running a day
  (or the whole pipeline) never creates duplicates.
* **Immutable landing zone** — every fetched batch is also written as Parquet
  under ``lake/raw/prices/symbol=X/ingest_date=D/<run_id>.parquet`` so the
  warehouse can be rebuilt without calling the API again.
* **Quarantine** — rows that fail basic sanity checks are kept in
  ``raw.prices_quarantine`` with a reason instead of being silently dropped.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import duckdb
import pandas as pd

from pipelines.config import PipelineConfig
from pipelines.sources import PriceSource, get_source

log = logging.getLogger(__name__)

DDL = """
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS meta;

CREATE TABLE IF NOT EXISTS raw.prices (
    symbol      VARCHAR NOT NULL,
    date        DATE    NOT NULL,
    open        DOUBLE,
    high        DOUBLE,
    low         DOUBLE,
    close       DOUBLE,
    adj_close   DOUBLE,
    volume      BIGINT,
    source      VARCHAR,
    run_id      VARCHAR,
    ingested_at TIMESTAMP,
    PRIMARY KEY (symbol, date)
);

CREATE TABLE IF NOT EXISTS raw.prices_quarantine (
    symbol      VARCHAR,
    date        DATE,
    open        DOUBLE,
    high        DOUBLE,
    low         DOUBLE,
    close       DOUBLE,
    adj_close   DOUBLE,
    volume      BIGINT,
    reason      VARCHAR,
    source      VARCHAR,
    run_id      VARCHAR,
    ingested_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw.corporate_actions (
    symbol      VARCHAR NOT NULL,
    date        DATE    NOT NULL,
    action_type VARCHAR NOT NULL,   -- 'dividend' | 'split'
    value       DOUBLE  NOT NULL,   -- cash per share | new shares per old share
    source      VARCHAR,
    run_id      VARCHAR,
    ingested_at TIMESTAMP,
    PRIMARY KEY (symbol, date, action_type)
);

CREATE TABLE IF NOT EXISTS raw.tickers (
    symbol       VARCHAR PRIMARY KEY,
    name         VARCHAR,
    sector       VARCHAR,
    is_benchmark BOOLEAN,
    updated_at   TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw.transactions (
    trade_id    VARCHAR,
    trade_date  DATE,
    symbol      VARCHAR,
    side        VARCHAR,
    shares      DOUBLE,
    price       DOUBLE,
    fees        DOUBLE,
    source_file VARCHAR,
    ingested_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS meta.ingestion_runs (
    run_id            VARCHAR PRIMARY KEY,
    source            VARCHAR,
    started_at        TIMESTAMP,
    finished_at       TIMESTAMP,
    status            VARCHAR,      -- running | success | partial | failed
    tickers_requested INTEGER,
    tickers_failed    VARCHAR,
    rows_loaded       INTEGER,
    rows_quarantined  INTEGER,
    error             VARCHAR
);
"""

PRICE_COLUMNS = ["symbol", "date", "open", "high", "low", "close", "adj_close", "volume"]
TRANSACTION_COLUMNS = ["trade_id", "trade_date", "symbol", "side", "shares", "price", "fees"]


@dataclass
class IngestResult:
    run_id: str
    status: str
    rows_loaded: int = 0
    rows_quarantined: int = 0
    tickers_failed: dict[str, str] = field(default_factory=dict)


def connect(path: Path) -> duckdb.DuckDBPyConnection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute(DDL)
    return con


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def get_watermarks(con: duckdb.DuckDBPyConnection) -> dict[str, date]:
    rows = con.execute("SELECT symbol, max(date) FROM raw.prices GROUP BY symbol").fetchall()
    return {symbol: d for symbol, d in rows}


def reset_if_source_changed(con: duckdb.DuckDBPyConnection, symbol: str, source_name: str) -> bool:
    """Never mix sources in one price history: a sample-data history topped up
    with a few days of real quotes would be one long fake series with a jump.
    When the stored source differs, drop the symbol so it is reloaded in full."""
    stored = {row[0] for row in con.execute(
        "SELECT DISTINCT source FROM raw.prices WHERE symbol = ?", [symbol]).fetchall()}
    if not stored or stored == {source_name}:
        return False
    con.execute("DELETE FROM raw.prices WHERE symbol = ?", [symbol])
    con.execute("DELETE FROM raw.corporate_actions WHERE symbol = ?", [symbol])
    return True


def plan_window(symbol: str, watermarks: dict[str, date], cfg: PipelineConfig,
                today: date, full_refresh: bool) -> tuple[date, date]:
    """Date range to request for one ticker."""
    if full_refresh or symbol not in watermarks:
        return cfg.start_date, today
    start = max(cfg.start_date, watermarks[symbol] - timedelta(days=cfg.lookback_days))
    return start, today


def split_valid_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pre-load sanity checks. Returns (valid, quarantined-with-reason)."""
    reasons = pd.Series("", index=df.index)
    checks = {
        "close missing or <= 0": df["close"].isna() | (df["close"] <= 0),
        "high < low": df["high"] < df["low"],
        "close outside high/low": (df["close"] > df["high"] * 1.0001) | (df["close"] < df["low"] * 0.9999),
        "negative volume": df["volume"] < 0,
        "duplicate date": df.duplicated(["symbol", "date"], keep="last"),
    }
    for reason, mask in checks.items():
        reasons[mask.fillna(False)] += reason + "; "
    bad = reasons != ""
    quarantined = df[bad].copy()
    quarantined["reason"] = reasons[bad].str.rstrip("; ")
    return df[~bad].copy(), quarantined


def fetch_with_retry(source: PriceSource, symbol: str, start: date, end: date,
                     attempts: int = 3, backoff_seconds: float = 2.0) -> pd.DataFrame:
    for attempt in range(1, attempts + 1):
        try:
            return source.fetch(symbol, start, end)
        except Exception as exc:  # network errors, rate limits, parsing errors
            if attempt == attempts:
                raise
            wait = backoff_seconds * 2 ** (attempt - 1)
            log.warning("fetch %s failed (%s), retry %d/%d in %.0fs", symbol, exc, attempt, attempts - 1, wait)
            time.sleep(wait)
    raise AssertionError("unreachable")


def write_to_lake(df: pd.DataFrame, lake_path: Path, symbol: str, run_id: str, ingest_date: date) -> Path:
    out_dir = lake_path / "raw" / "prices" / f"symbol={symbol}" / f"ingest_date={ingest_date.isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{run_id}.parquet"
    df.to_parquet(out, index=False)
    return out


def load_prices(con: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> None:
    con.register("incoming_prices", df)
    con.execute("""
        INSERT OR REPLACE INTO raw.prices
        SELECT symbol, date, open, high, low, close, adj_close, volume, source, run_id, ingested_at
        FROM incoming_prices
    """)
    con.unregister("incoming_prices")


def load_actions(con: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> None:
    dividends = df.loc[df["dividend"] > 0, ["symbol", "date", "dividend"]].rename(columns={"dividend": "value"})
    dividends["action_type"] = "dividend"
    splits = df.loc[df["split_ratio"] > 0, ["symbol", "date", "split_ratio"]].rename(columns={"split_ratio": "value"})
    splits["action_type"] = "split"
    actions = pd.concat([dividends, splits], ignore_index=True)
    # The fetched window is the source of truth for its dates: drop any action
    # previously stored there so a provider retraction doesn't leave a phantom
    # dividend/split behind.
    for symbol, dates in df.groupby("symbol")["date"]:
        con.execute("DELETE FROM raw.corporate_actions WHERE symbol = ? AND date BETWEEN ? AND ?",
                    [symbol, dates.min(), dates.max()])
    if actions.empty:
        return
    actions["source"] = df["source"].iloc[0]
    actions["run_id"] = df["run_id"].iloc[0]
    actions["ingested_at"] = df["ingested_at"].iloc[0]
    con.register("incoming_actions", actions)
    con.execute("""
        INSERT OR REPLACE INTO raw.corporate_actions
        SELECT symbol, date, action_type, value, source, run_id, ingested_at FROM incoming_actions
    """)
    con.unregister("incoming_actions")


def load_tickers(con: duckdb.DuckDBPyConnection, cfg: PipelineConfig) -> None:
    df = pd.DataFrame([{"symbol": t.symbol, "name": t.name, "sector": t.sector,
                        "is_benchmark": t.is_benchmark, "updated_at": _now()} for t in cfg.tickers])
    con.register("incoming_tickers", df)
    con.execute("INSERT OR REPLACE INTO raw.tickers SELECT * FROM incoming_tickers")
    con.unregister("incoming_tickers")


def read_transactions(path: Path, known_symbols: set[str]) -> pd.DataFrame:
    """Read and validate the trade ledger. Bad input fails loudly — these are
    the user's own records, so guessing a fix would be worse than stopping."""
    df = pd.read_csv(path, dtype={"trade_id": str, "symbol": str, "side": str})
    missing = set(TRANSACTION_COLUMNS) - set(df.columns) - {"fees"}
    if missing:
        raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
    if "fees" not in df:
        df["fees"] = 0.0
    df["fees"] = df["fees"].fillna(0.0)
    df["symbol"] = df["symbol"].str.strip().str.upper()
    df["side"] = df["side"].str.strip().str.upper()
    df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y-%m-%d").dt.date

    problems = []
    if df["trade_id"].duplicated().any():
        problems.append(f"duplicate trade_id: {df.loc[df['trade_id'].duplicated(), 'trade_id'].tolist()}")
    if not df["side"].isin(["BUY", "SELL"]).all():
        problems.append(f"side must be BUY or SELL: {df.loc[~df['side'].isin(['BUY', 'SELL']), 'trade_id'].tolist()}")
    bad_amounts = df["shares"].isna() | df["price"].isna() | (df["shares"] <= 0) | (df["price"] <= 0)
    if bad_amounts.any():
        problems.append(f"shares and price must be present and > 0: {df.loc[bad_amounts, 'trade_id'].tolist()}")
    unknown = set(df["symbol"]) - known_symbols
    if unknown:
        problems.append(f"symbols not in config/pipeline.toml: {sorted(unknown)}")
    if problems:
        raise ValueError(f"{path.name}: " + "; ".join(problems))
    return df[TRANSACTION_COLUMNS]


def load_transactions(con: duckdb.DuckDBPyConnection, cfg: PipelineConfig) -> int:
    df = read_transactions(cfg.transactions_path, set(cfg.symbols))
    df["source_file"] = cfg.transactions_path.name
    df["ingested_at"] = _now()
    con.register("incoming_transactions", df)
    # Small user-owned file: full replace each run is simplest and exact.
    con.execute("BEGIN")
    con.execute("DELETE FROM raw.transactions")
    con.execute("INSERT INTO raw.transactions SELECT * FROM incoming_transactions")
    con.execute("COMMIT")
    con.unregister("incoming_transactions")
    return len(df)


def run_ingestion(cfg: PipelineConfig, symbols: list[str] | None = None, full_refresh: bool = False,
                  today: date | None = None, source: PriceSource | None = None) -> IngestResult:
    today = today or date.today()
    source = source or get_source(cfg.source)
    symbols = [s.upper() for s in (symbols or cfg.symbols)]
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
    result = IngestResult(run_id=run_id, status="running")

    con = connect(cfg.warehouse_path)
    try:
        con.execute("INSERT INTO meta.ingestion_runs (run_id, source, started_at, status, tickers_requested) "
                    "VALUES (?, ?, ?, 'running', ?)", [run_id, source.name, _now(), len(symbols)])
        load_tickers(con, cfg)
        n_trades = load_transactions(con, cfg)
        log.info("loaded %d transactions", n_trades)

        watermarks = get_watermarks(con)
        for symbol in symbols:
            if reset_if_source_changed(con, symbol, source.name):
                log.warning("%s: stored data came from another source; reloading full history from %s",
                            symbol, source.name)
                watermarks.pop(symbol, None)
            start, end = plan_window(symbol, watermarks, cfg, today, full_refresh)
            try:
                df = fetch_with_retry(source, symbol, start, end)
            except Exception as exc:
                log.error("giving up on %s: %s", symbol, exc)
                result.tickers_failed[symbol] = str(exc)[:200]
                continue
            if df.empty:
                log.info("%s: no new rows for %s..%s", symbol, start, end)
                continue

            df = df.copy()
            df.insert(0, "symbol", symbol)
            df["source"] = source.name
            df["run_id"] = run_id
            df["ingested_at"] = _now()
            write_to_lake(df, cfg.lake_path, symbol, run_id, today)

            valid, bad = split_valid_rows(df)
            if not bad.empty:
                con.register("bad_rows", bad)
                con.execute("INSERT INTO raw.prices_quarantine SELECT symbol, date, open, high, low, close, "
                            "adj_close, volume, reason, source, run_id, ingested_at FROM bad_rows")
                con.unregister("bad_rows")
                result.rows_quarantined += len(bad)
                log.warning("%s: quarantined %d rows", symbol, len(bad))

            load_prices(con, valid)
            load_actions(con, valid)
            result.rows_loaded += len(valid)
            log.info("%s: loaded %d rows (%s..%s)", symbol, len(valid), start, end)

        if len(result.tickers_failed) == len(symbols):
            result.status = "failed"
        elif result.tickers_failed:
            result.status = "partial"
        else:
            result.status = "success"
    except Exception as exc:
        result.status = "failed"
        con.execute("UPDATE meta.ingestion_runs SET status='failed', finished_at=?, error=? WHERE run_id=?",
                    [_now(), str(exc)[:500], run_id])
        con.close()
        raise

    con.execute(
        "UPDATE meta.ingestion_runs SET status=?, finished_at=?, rows_loaded=?, rows_quarantined=?, "
        "tickers_failed=? WHERE run_id=?",
        [result.status, _now(), result.rows_loaded, result.rows_quarantined,
         ",".join(sorted(result.tickers_failed)) or None, run_id],
    )
    con.close()
    return result
