"""Strategy backtests, Monte Carlo projection and efficient frontier.

Inputs are *wide* price frames: index = trading date, one column per ticker,
values = total-return index (dividends reinvested), as produced by
``marts.fct_daily_prices.total_return_index``. Everything is vectorised over
dates, so a 5-year backtest takes milliseconds.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src import metrics

STRATEGIES = {
    "lump_sum": "Lump sum (all money on day 1)",
    "dca": "Monthly DCA, never rebalanced",
    "dca_rebalanced": "Monthly DCA + quarterly rebalance",
}


@dataclass
class BacktestResult:
    strategy: str
    daily: pd.DataFrame        # date -> value, invested
    summary: dict[str, float]


def _normalise(weights: dict[str, float], columns) -> pd.Series:
    w = pd.Series(weights, dtype="float64").reindex(columns).fillna(0.0)
    if w.sum() <= 0:
        raise ValueError("weights must sum to a positive number")
    return w / w.sum()


def _first_trading_day_each_month(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(index, index=index)
    return pd.DatetimeIndex(s.groupby(index.to_period("M")).min().to_numpy())


def backtest(prices: pd.DataFrame, weights: dict[str, float], monthly_amount: float,
             strategy: str = "dca", rebalance: str = "QS") -> BacktestResult:
    """Simulate a strategy over the full span of ``prices``.

    For a fair comparison every strategy invests the same total: lump sum puts
    ``monthly_amount * n_months`` in on the first day, DCA spreads it out.
    """
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy {strategy!r}")
    prices = prices.sort_index().dropna(how="any")
    prices.index = pd.DatetimeIndex(prices.index)
    if len(prices) < 2:
        raise ValueError("need at least two days of prices")
    w = _normalise(weights, prices.columns)
    prices = prices.loc[:, w > 0]
    w = w[w > 0]

    buy_days = _first_trading_day_each_month(prices.index)
    total = monthly_amount * len(buy_days)
    contributions = pd.Series(0.0, index=prices.index)
    if strategy == "lump_sum":
        contributions.iloc[0] = total
    else:
        contributions.loc[buy_days] = monthly_amount

    rebalance_days = set()
    if strategy == "dca_rebalanced":
        s = pd.Series(prices.index, index=prices.index)
        rebalance_days = set(s.groupby(prices.index.to_period(rebalance[0])).min())

    px = prices.to_numpy()
    shares = np.zeros(px.shape[1])
    values = np.empty(len(prices))
    for i, day in enumerate(prices.index):
        cash = contributions.iloc[i]
        if cash:
            shares += cash * w.to_numpy() / px[i]
        if day in rebalance_days and i > 0:
            value = shares @ px[i]
            shares = value * w.to_numpy() / px[i]
        values[i] = shares @ px[i]

    daily = pd.DataFrame({"value": values, "invested": contributions.cumsum(), "flow": contributions},
                         index=prices.index)
    daily["daily_return"] = ((daily["value"] - daily["flow"]) / daily["value"].shift(1) - 1).where(
        daily["value"].shift(1) > 0)

    flows = contributions[contributions > 0]
    irr_dates = list(flows.index) + [prices.index[-1]]
    irr_amounts = list(-flows.to_numpy()) + [values[-1]]
    summary = {
        "total_invested": float(total),
        "final_value": float(values[-1]),
        "profit": float(values[-1] - total),
        "twr_annual": metrics.annualized_return(daily["daily_return"]),
        "xirr": metrics.xirr(irr_dates, irr_amounts),
        "max_drawdown": metrics.max_drawdown(daily["daily_return"]),
        "volatility": metrics.annualized_volatility(daily["daily_return"]),
    }
    return BacktestResult(strategy=strategy, daily=daily, summary=summary)


def compare_strategies(prices: pd.DataFrame, weights: dict[str, float],
                       monthly_amount: float) -> tuple[pd.DataFrame, dict[str, BacktestResult]]:
    results = {s: backtest(prices, weights, monthly_amount, s) for s in STRATEGIES}
    table = pd.DataFrame({STRATEGIES[s]: r.summary for s, r in results.items()}).T
    return table, results


def monte_carlo(daily_returns: pd.Series, start_value: float, years: int = 5,
                monthly_contribution: float = 0.0, n_sims: int = 2000, block: int = 20,
                seed: int = 7) -> pd.DataFrame:
    """Project portfolio value by resampling historical daily returns in
    blocks (keeps volatility clustering that a normal model would miss).
    Returns percentile paths (p5..p95) per future trading day."""
    r = daily_returns.dropna().to_numpy()
    if len(r) < block * 2:
        raise ValueError("not enough history for a block bootstrap")
    rng = np.random.default_rng(seed)
    horizon = years * metrics.TRADING_DAYS
    n_blocks = int(np.ceil(horizon / block))
    starts = rng.integers(0, len(r) - block, size=(n_sims, n_blocks))
    sims = r[starts[..., None] + np.arange(block)].reshape(n_sims, -1)[:, :horizon]

    values = np.empty((n_sims, horizon))
    v = np.full(n_sims, float(start_value))
    for t in range(horizon):
        v = v * (1 + sims[:, t])
        if monthly_contribution and t % 21 == 20:
            v = v + monthly_contribution
        values[:, t] = v

    pct = np.percentile(values, [5, 25, 50, 75, 95], axis=0)
    out = pd.DataFrame(pct.T, columns=["p5", "p25", "p50", "p75", "p95"])
    out.index.name = "trading_day"
    out["years"] = (out.index + 1) / metrics.TRADING_DAYS
    out["contributed"] = start_value + monthly_contribution * ((out.index + 1) // 21)
    return out


def efficient_frontier(daily_returns: pd.DataFrame, n_portfolios: int = 4000,
                       risk_free_rate: float = 0.0, seed: int = 11) -> tuple[pd.DataFrame, dict]:
    """Random long-only portfolios plus the max-Sharpe and min-volatility picks."""
    r = daily_returns.dropna()
    rng = np.random.default_rng(seed)
    w = rng.dirichlet(np.ones(r.shape[1]), n_portfolios)
    # Daily-rebalanced portfolio returns for every candidate at once, then the
    # same geometric annualisation used everywhere else in src.metrics.
    port = r.to_numpy() @ w.T
    ret = np.expm1(np.log1p(port).mean(axis=0) * metrics.TRADING_DAYS)
    vol = port.std(axis=0, ddof=1) * np.sqrt(metrics.TRADING_DAYS)
    sharpe = (ret - risk_free_rate) / vol
    frontier = pd.DataFrame({"return": ret, "volatility": vol, "sharpe": sharpe})
    weights = pd.DataFrame(w, columns=r.columns)
    best = {
        "max_sharpe": weights.iloc[int(np.argmax(sharpe))].to_dict(),
        "min_volatility": weights.iloc[int(np.argmin(vol))].to_dict(),
    }
    return frontier, best
