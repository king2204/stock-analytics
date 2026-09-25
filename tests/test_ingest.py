from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from pipelines.ingest import plan_window, read_transactions, run_ingestion, split_valid_rows
from pipelines.sources import PriceSource, SampleSource
from tests.conftest import sample_config


def count(cfg, sql):
    with duckdb.connect(str(cfg.warehouse_path), read_only=True) as con:
        return con.execute(sql).fetchone()[0]


def test_incremental_load_only_fetches_new_days_and_is_idempotent(tmp_path):
    cfg = sample_config(tmp_path)
    first = run_ingestion(cfg, symbols=["AAPL"], today=date(2025, 6, 30))
    assert first.status == "success"
    rows_after_first = count(cfg, "select count(*) from raw.prices")

    calls = []

    class Spy(SampleSource):
        def fetch(self, symbol, start, end):
            calls.append((start, end))
            return super().fetch(symbol, start, end)

    second = run_ingestion(cfg, symbols=["AAPL"], today=date(2025, 7, 31), source=Spy())
    # watermark 2025-06-30 minus 5 lookback days
    assert calls == [(date(2025, 6, 25), date(2025, 7, 31))]
    assert second.rows_loaded < 30
    rows_after_second = count(cfg, "select count(*) from raw.prices")
    assert rows_after_second > rows_after_first

    # Re-running the same day changes nothing: upsert, no duplicates.
    run_ingestion(cfg, symbols=["AAPL"], today=date(2025, 7, 31))
    assert count(cfg, "select count(*) from raw.prices") == rows_after_second
    assert count(cfg, "select count(*) - count(distinct (symbol, date)) from raw.prices") == 0
    assert count(cfg, "select count(*) from meta.ingestion_runs where status = 'success'") == 3


def test_every_run_lands_an_immutable_parquet_file(tmp_path):
    cfg = sample_config(tmp_path)
    result = run_ingestion(cfg, symbols=["SPY"], today=date(2024, 1, 31))
    files = list(Path(cfg.lake_path).rglob("*.parquet"))
    assert len(files) == 1
    assert "symbol=SPY" in str(files[0]) and result.run_id in files[0].name
    assert len(pd.read_parquet(files[0])) == result.rows_loaded


def test_plan_window_full_refresh_and_first_load(tmp_path):
    cfg = sample_config(tmp_path)
    today = date(2025, 1, 10)
    assert plan_window("AAPL", {}, cfg, today, False) == (cfg.start_date, today)
    wm = {"AAPL": date(2025, 1, 8)}
    assert plan_window("AAPL", wm, cfg, today, False) == (date(2025, 1, 3), today)
    assert plan_window("AAPL", wm, cfg, today, True) == (cfg.start_date, today)


def test_bad_rows_are_quarantined_not_loaded(tmp_path):
    class Dirty(SampleSource):
        def fetch(self, symbol, start, end):
            df = super().fetch(symbol, start, end)
            df.loc[0, "close"] = -1.0          # impossible price
            df.loc[1, "high"] = df.loc[1, "low"] - 1  # high below low
            return df

    cfg = sample_config(tmp_path)
    result = run_ingestion(cfg, symbols=["MSFT"], today=date(2024, 3, 1), source=Dirty())
    assert result.rows_quarantined == 2
    assert count(cfg, "select count(*) from raw.prices where close <= 0") == 0
    reasons = count(cfg, "select string_agg(reason, '|' order by date) from raw.prices_quarantine")
    assert "close missing or <= 0" in reasons and "high < low" in reasons


def test_one_failing_ticker_gives_partial_status(tmp_path, monkeypatch):
    monkeypatch.setattr("pipelines.ingest.time.sleep", lambda s: None)

    class Flaky(SampleSource):
        def fetch(self, symbol, start, end):
            if symbol == "TSLA":
                raise ConnectionError("rate limited")
            return super().fetch(symbol, start, end)

    cfg = sample_config(tmp_path)
    result = run_ingestion(cfg, symbols=["AAPL", "TSLA"], today=date(2024, 3, 1), source=Flaky())
    assert result.status == "partial"
    assert set(result.tickers_failed) == {"TSLA"}
    assert count(cfg, "select tickers_failed from meta.ingestion_runs") == "TSLA"


def test_fetch_is_retried_with_backoff(tmp_path, monkeypatch):
    sleeps = []
    monkeypatch.setattr("pipelines.ingest.time.sleep", sleeps.append)

    class FailsTwice(PriceSource):
        name = "flaky"
        attempts = 0

        def fetch(self, symbol, start, end):
            FailsTwice.attempts += 1
            if FailsTwice.attempts < 3:
                raise TimeoutError("timeout")
            return SampleSource().fetch(symbol, start, end)

    cfg = sample_config(tmp_path)
    result = run_ingestion(cfg, symbols=["JPM"], today=date(2024, 3, 1), source=FailsTwice())
    assert result.status == "success"
    assert sleeps == [2.0, 4.0]


@pytest.mark.parametrize("bad_row, message", [
    ("T9,2024-01-02,AAPL,HOLD,1,100,0", "side must be BUY or SELL"),
    ("T9,2024-01-02,XXXX,BUY,1,100,0", "symbols not in config"),
    ("T9,2024-01-02,AAPL,BUY,-1,100,0", "shares and price must be > 0"),
    ("T0001,2024-01-02,AAPL,BUY,1,100,0", "duplicate trade_id"),
])
def test_invalid_transactions_fail_loudly(tmp_path, bad_row, message):
    path = tmp_path / "tx.csv"
    path.write_text("trade_id,trade_date,symbol,side,shares,price,fees\n"
                    "T0001,2024-01-02,AAPL,BUY,1,180,0\n" + bad_row + "\n")
    with pytest.raises(ValueError, match=message):
        read_transactions(path, {"AAPL", "SPY"})


def test_split_valid_rows_flags_duplicates():
    d = date(2024, 1, 2)
    df = pd.DataFrame({"symbol": ["A", "A"], "date": [d, d], "open": [1, 1], "high": [2, 2],
                       "low": [0.5, 0.5], "close": [1.5, 1.6], "volume": [10, 10]})
    valid, bad = split_valid_rows(df)
    assert len(valid) == 1 and valid["close"].iloc[0] == 1.6  # last one wins
    assert bad["reason"].iloc[0] == "duplicate date"


def test_future_today_is_capped_by_sample_source(tmp_path):
    cfg = sample_config(tmp_path)
    run_ingestion(cfg, symbols=["AAPL"], today=date.today() + timedelta(days=30))
    assert count(cfg, "select max(date) from raw.prices") <= date.today()
