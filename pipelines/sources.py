"""Market data sources.

Every source returns the same daily frame so the rest of the pipeline does not
care where the data came from:

    date, open, high, low, close, adj_close, volume, dividend, split_ratio

Prices follow Yahoo conventions: ``close`` is split-adjusted, ``adj_close`` is
split- and dividend-adjusted, ``dividend`` is cash per (split-adjusted) share on
the ex-date and ``split_ratio`` is new/old shares on the split date (0 = none).
"""

from __future__ import annotations

import zlib
from datetime import date, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd

COLUMNS = ["date", "open", "high", "low", "close", "adj_close", "volume", "dividend", "split_ratio"]


class PriceSource:
    name = "base"

    def fetch(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        """Return daily bars for ``symbol`` with start <= date <= end."""
        raise NotImplementedError


class YahooSource(PriceSource):
    """Real market data via yfinance (needs internet access)."""

    name = "yahoo"

    def fetch(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        import yfinance as yf

        hist = yf.Ticker(symbol).history(
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),  # yfinance end is exclusive
            auto_adjust=False,
            actions=True,
        )
        if hist.empty:
            return pd.DataFrame(columns=COLUMNS)

        df = hist.reset_index().rename(
            columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adj_close",
                "Volume": "volume",
                "Dividends": "dividend",
                "Stock Splits": "split_ratio",
            }
        )
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.date
        for col in ("dividend", "split_ratio"):
            if col not in df:
                df[col] = 0.0
        return df[COLUMNS]


# ---------------------------------------------------------------------------
# Synthetic source
# ---------------------------------------------------------------------------

# Approximate split-adjusted closes on a few dates per ticker. The generator
# draws a random path that passes exactly through these points, so the fake
# market has a realistic shape (2022 drawdown, 2023-24 rally, April 2025 dip)
# while every value in between is synthetic. Do not use it for real decisions.
_ANCHORS: dict[str, list[tuple[str, float]]] = {
    "AAPL": [("2021-01-04", 129), ("2022-01-03", 182), ("2022-12-30", 130), ("2023-01-17", 135.94),
             ("2024-01-02", 185), ("2024-05-01", 169.30), ("2025-01-02", 243), ("2025-04-08", 172),
             ("2025-09-02", 230), ("2026-06-30", 250)],
    "MSFT": [("2021-01-04", 217), ("2022-01-03", 334), ("2022-11-03", 214), ("2023-03-20", 272.23),
             ("2024-01-02", 370), ("2024-07-05", 467), ("2025-02-03", 410.92), ("2025-04-08", 355),
             ("2025-07-31", 530), ("2026-06-30", 520)],
    "GOOGL": [("2021-01-04", 86), ("2022-01-03", 145), ("2022-11-03", 83), ("2023-06-12", 123.64),
              ("2024-01-02", 138), ("2024-07-10", 191), ("2025-01-02", 190), ("2025-04-08", 145),
              ("2025-09-02", 212), ("2026-06-30", 240)],
    "AMZN": [("2021-01-04", 159), ("2021-07-08", 186), ("2022-03-01", 151.10), ("2022-12-28", 81),
             ("2023-08-07", 140.64), ("2024-01-02", 149), ("2025-02-04", 238), ("2025-04-08", 170),
             ("2025-09-02", 225), ("2026-06-30", 235)],
    "TSLA": [("2021-01-04", 243), ("2021-11-04", 409), ("2022-12-27", 109), ("2023-07-18", 293),
             ("2023-09-01", 245.01), ("2024-04-22", 142), ("2024-12-17", 479), ("2025-04-08", 221),
             ("2025-09-02", 333), ("2026-06-30", 400)],
    "NVDA": [("2021-01-04", 13), ("2021-11-29", 33), ("2022-10-13", 11), ("2023-06-01", 39.77),
             ("2024-01-02", 48), ("2024-06-18", 135), ("2025-01-06", 149), ("2025-04-04", 94),
             ("2025-09-02", 172), ("2026-06-30", 190)],
    "JPM": [("2021-01-04", 125), ("2022-01-03", 165), ("2022-10-12", 102), ("2024-02-01", 172.50),
            ("2025-01-02", 240), ("2025-04-08", 215), ("2025-09-02", 300), ("2026-06-30", 310)],
    "SPY": [("2021-01-04", 369), ("2022-01-03", 477), ("2022-10-12", 357), ("2023-07-31", 457),
            ("2024-01-02", 472), ("2025-02-19", 612), ("2025-04-08", 496), ("2025-09-02", 645),
            ("2026-06-30", 680)],
}

# (ex-date, new shares per old share) — the real split history in the window.
_SPLITS: dict[str, list[tuple[str, float]]] = {
    "AMZN": [("2022-06-06", 20.0)],
    "GOOGL": [("2022-07-18", 20.0)],
    "TSLA": [("2022-08-25", 3.0)],
    "NVDA": [("2021-07-20", 4.0), ("2024-06-10", 10.0)],
}

# (first ex-date, quarterly amount at start, yearly growth)
_DIVIDENDS: dict[str, tuple[str, float, float]] = {
    "AAPL": ("2021-02-05", 0.205, 0.04),
    "MSFT": ("2021-02-17", 0.56, 0.10),
    "JPM": ("2021-01-05", 0.90, 0.10),
    "SPY": ("2021-03-19", 1.26, 0.06),
    "GOOGL": ("2024-06-10", 0.20, 0.05),
    "NVDA": ("2021-03-09", 0.01, 0.0),
}

_DAILY_VOL = {"AAPL": 0.016, "MSFT": 0.015, "GOOGL": 0.018, "AMZN": 0.020, "TSLA": 0.033,
              "NVDA": 0.028, "JPM": 0.014, "SPY": 0.009}
_MARKET_BETA = {"AAPL": 1.1, "MSFT": 1.0, "GOOGL": 1.1, "AMZN": 1.2, "TSLA": 1.8,
                "NVDA": 1.7, "JPM": 0.9, "SPY": 1.0}

_CALENDAR_START = "2020-01-01"
_CALENDAR_END = "2030-12-31"
_MARKET_SEED = 20240601


@lru_cache(maxsize=1)
def _calendar() -> pd.DatetimeIndex:
    from pandas.tseries.holiday import USFederalHolidayCalendar
    from pandas.tseries.offsets import CustomBusinessDay

    return pd.date_range(_CALENDAR_START, _CALENDAR_END,
                         freq=CustomBusinessDay(calendar=USFederalHolidayCalendar()))


@lru_cache(maxsize=1)
def _market_shocks() -> np.ndarray:
    """Shared daily market factor so synthetic tickers are correlated."""
    return np.random.default_rng(_MARKET_SEED).normal(0.0, 0.009, len(_calendar()))


@lru_cache(maxsize=32)
def _full_history(symbol: str) -> pd.DataFrame:
    """Generate the whole 2020-2030 path once so any requested window is a
    stable slice of it (re-running with a later end date never rewrites the
    past — which is what lets the incremental loader be tested)."""
    cal = _calendar()
    n = len(cal)
    rng = np.random.default_rng(zlib.crc32(symbol.encode()))
    vol = _DAILY_VOL.get(symbol, 0.02)
    beta = _MARKET_BETA.get(symbol, 1.0)
    idio_vol = np.sqrt(max(vol**2 - (beta * 0.009) ** 2, 1e-6))
    shocks = beta * _market_shocks() + rng.normal(0.0, idio_vol, n)
    walk = np.concatenate([[0.0], np.cumsum(shocks[1:])])

    anchors = _ANCHORS.get(symbol) or [(_CALENDAR_START, 100.0)]
    anchor_idx = [int(cal.searchsorted(pd.Timestamp(d))) for d, _ in anchors]
    anchor_log = [np.log(p) for _, p in anchors]

    log_price = walk.copy()
    # Before the first anchor: walk backwards from it.
    first = anchor_idx[0]
    log_price[: first + 1] = anchor_log[0] + walk[: first + 1] - walk[first]
    # Between anchors: Brownian bridge pinned at both ends.
    for (i0, p0), (i1, p1) in zip(zip(anchor_idx, anchor_log), zip(anchor_idx[1:], anchor_log[1:])):
        seg = walk[i0 : i1 + 1] - walk[i0]
        t = np.linspace(0.0, 1.0, i1 - i0 + 1)
        log_price[i0 : i1 + 1] = p0 + (p1 - p0) * t + seg - t * seg[-1]
    # After the last anchor: free random walk.
    last = anchor_idx[-1]
    log_price[last:] = anchor_log[-1] + walk[last:] - walk[last]

    close = np.exp(log_price)
    open_ = np.concatenate([[close[0]], close[:-1]]) * np.exp(rng.normal(0, vol * 0.3, n))
    spread = np.abs(rng.normal(0, vol * 0.5, n))
    high = np.maximum(open_, close) * (1 + spread)
    low = np.minimum(open_, close) * (1 - spread)
    base_volume = {"SPY": 7e7, "TSLA": 1e8, "NVDA": 3e8}.get(symbol, 4e7)
    volume = (base_volume * np.exp(rng.normal(0, 0.35, n))).astype("int64")

    df = pd.DataFrame({"date": cal, "open": open_, "high": high, "low": low,
                       "close": close, "volume": volume, "dividend": 0.0, "split_ratio": 0.0})

    for d, ratio in _SPLITS.get(symbol, []):
        df.loc[cal.searchsorted(pd.Timestamp(d)), "split_ratio"] = ratio

    if symbol in _DIVIDENDS:
        first_ex, amount, growth = _DIVIDENDS[symbol]
        for k, ex in enumerate(pd.date_range(first_ex, _CALENDAR_END, freq="91D")):
            idx = cal.searchsorted(ex)
            if idx < n:
                df.loc[idx, "dividend"] = round(amount * (1 + growth) ** (k // 4), 4)

    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].round(4)
    df["date"] = df["date"].dt.date
    return df


class SampleSource(PriceSource):
    """Deterministic synthetic market data — no network needed."""

    name = "sample"

    def fetch(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        as_of = min(end, date.today())
        full = _full_history(symbol.upper())
        full = full[full["date"] <= as_of].reset_index(drop=True)

        # Dividend-adjusted close, Yahoo style: every dividend paid up to today
        # scales all earlier prices down. That means adj_close for old dates
        # changes whenever a new dividend is paid, just like the real feed.
        close = full["close"].to_numpy()
        factor = np.ones(len(full))
        for idx in np.flatnonzero(full["dividend"].to_numpy() > 0):
            if idx > 0:
                factor[:idx] *= 1 - full.at[idx, "dividend"] / close[idx - 1]
        full["adj_close"] = (close * factor).round(4)

        window = full[full["date"] >= start].reset_index(drop=True)
        return window[COLUMNS]


def get_source(name: str) -> PriceSource:
    sources = {"yahoo": YahooSource, "sample": SampleSource}
    if name not in sources:
        raise ValueError(f"Unknown source {name!r}")
    return sources[name]()
