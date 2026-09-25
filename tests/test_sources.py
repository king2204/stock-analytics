from datetime import date

import pandas as pd

from pipelines.sources import COLUMNS, SampleSource


def test_sample_source_schema_and_sanity():
    df = SampleSource().fetch("AAPL", date(2023, 1, 1), date(2023, 12, 31))
    assert list(df.columns) == COLUMNS
    assert len(df) > 240  # ~250 trading days
    assert (df["close"] > 0).all()
    assert (df["high"] >= df["low"]).all()
    assert df["date"].is_monotonic_increasing
    assert pd.Timestamp(df["date"].iloc[0]).dayofweek < 5


def test_sample_source_is_deterministic_and_window_stable():
    src = SampleSource()
    short = src.fetch("MSFT", date(2023, 1, 1), date(2023, 6, 30))
    longer = src.fetch("MSFT", date(2023, 1, 1), date(2024, 6, 30))
    merged = short.merge(longer, on="date", suffixes=("_a", "_b"))
    assert len(merged) == len(short)
    assert (merged["close_a"] == merged["close_b"]).all()


def test_sample_source_passes_through_anchor_prices():
    # T0005 in the sample ledger: GOOGL bought at 123.64 on 2023-06-12
    df = SampleSource().fetch("GOOGL", date(2023, 6, 12), date(2023, 6, 12))
    assert abs(df["close"].iloc[0] - 123.64) < 0.01


def test_sample_source_emits_real_split_events():
    df = SampleSource().fetch("NVDA", date(2024, 6, 1), date(2024, 6, 30))
    splits = df[df["split_ratio"] > 0]
    assert splits["date"].tolist() == [date(2024, 6, 10)]
    assert splits["split_ratio"].iloc[0] == 10.0


def test_adj_close_is_restated_by_later_dividends():
    """Mirrors Yahoo: a dividend paid later lowers adj_close for earlier dates."""
    src = SampleSource()
    early = src.fetch("JPM", date(2023, 1, 3), date(2023, 1, 3))
    later = src.fetch("JPM", date(2023, 1, 3), date(2024, 1, 3)).head(1)
    assert early["close"].iloc[0] == later["close"].iloc[0]
    assert later["adj_close"].iloc[0] < early["adj_close"].iloc[0]
