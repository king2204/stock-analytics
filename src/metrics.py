"""Performance and risk metrics on daily return series.

All functions take plain pandas objects so they work the same on warehouse
data, notebook data and test fixtures. Returns are simple daily returns
(0.01 == +1%) and annualisation assumes 252 trading days.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
from scipy import optimize, stats

TRADING_DAYS = 252


def _clean(returns: pd.Series) -> pd.Series:
    return pd.Series(returns, dtype="float64").dropna()


def annualized_return(returns: pd.Series) -> float:
    r = _clean(returns)
    if r.empty:
        return float("nan")
    return float(np.exp(np.log1p(r).mean() * TRADING_DAYS) - 1)


def annualized_volatility(returns: pd.Series) -> float:
    r = _clean(returns)
    return float(r.std(ddof=1) * np.sqrt(TRADING_DAYS)) if len(r) > 1 else float("nan")


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    vol = annualized_volatility(returns)
    if not vol or np.isnan(vol):
        return float("nan")
    return (annualized_return(returns) - risk_free_rate) / vol


def downside_deviation(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    r = _clean(returns) - risk_free_rate / TRADING_DAYS
    return float(np.sqrt((np.minimum(r, 0) ** 2).mean()) * np.sqrt(TRADING_DAYS))


def sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    dd = downside_deviation(returns, risk_free_rate)
    return (annualized_return(returns) - risk_free_rate) / dd if dd else float("nan")


def wealth_index(returns: pd.Series) -> pd.Series:
    return (1 + _clean(returns)).cumprod()


def drawdown_series(returns: pd.Series) -> pd.Series:
    wealth = wealth_index(returns)
    return wealth / wealth.cummax() - 1


def max_drawdown(returns: pd.Series) -> float:
    dd = drawdown_series(returns)
    return float(dd.min()) if not dd.empty else float("nan")


def calmar_ratio(returns: pd.Series) -> float:
    mdd = max_drawdown(returns)
    return annualized_return(returns) / abs(mdd) if mdd else float("nan")


def value_at_risk(returns: pd.Series, level: float = 0.95, method: str = "historical") -> float:
    """One-day VaR as a (negative) return: 5% of days are expected to be worse."""
    r = _clean(returns)
    if method == "historical":
        return float(np.quantile(r, 1 - level))
    if method == "parametric":
        return float(r.mean() + stats.norm.ppf(1 - level) * r.std(ddof=1))
    raise ValueError("method must be 'historical' or 'parametric'")


def conditional_value_at_risk(returns: pd.Series, level: float = 0.95) -> float:
    """Expected shortfall: the average return on the days beyond the VaR."""
    r = _clean(returns)
    var = value_at_risk(r, level)
    return float(r[r <= var].mean())


def _aligned(returns: pd.Series, benchmark: pd.Series) -> pd.DataFrame:
    return pd.concat([returns.rename("p"), benchmark.rename("b")], axis=1).dropna()


def beta(returns: pd.Series, benchmark: pd.Series) -> float:
    df = _aligned(returns, benchmark)
    return float(df["p"].cov(df["b"]) / df["b"].var()) if len(df) > 2 else float("nan")


def jensens_alpha(returns: pd.Series, benchmark: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Annualised return above what beta exposure to the benchmark explains (CAPM)."""
    df = _aligned(returns, benchmark)
    b = beta(df["p"], df["b"])
    return (annualized_return(df["p"]) - risk_free_rate) - b * (annualized_return(df["b"]) - risk_free_rate)


def tracking_error(returns: pd.Series, benchmark: pd.Series) -> float:
    df = _aligned(returns, benchmark)
    return float((df["p"] - df["b"]).std(ddof=1) * np.sqrt(TRADING_DAYS))


def information_ratio(returns: pd.Series, benchmark: pd.Series) -> float:
    df = _aligned(returns, benchmark)
    te = tracking_error(df["p"], df["b"])
    return (annualized_return(df["p"]) - annualized_return(df["b"])) / te if te else float("nan")


def capture_ratios(returns: pd.Series, benchmark: pd.Series) -> tuple[float, float]:
    """(upside capture, downside capture): >1 up and <1 down is the ideal."""
    df = _aligned(returns, benchmark)
    up, down = df[df["b"] > 0], df[df["b"] < 0]
    upside = annualized_return(up["p"]) / annualized_return(up["b"]) if len(up) else float("nan")
    downside = annualized_return(down["p"]) / annualized_return(down["b"]) if len(down) else float("nan")
    return upside, downside


def rolling_volatility(returns: pd.Series, window: int = 60) -> pd.Series:
    return _clean(returns).rolling(window).std() * np.sqrt(TRADING_DAYS)


def rolling_beta(returns: pd.Series, benchmark: pd.Series, window: int = 60) -> pd.Series:
    df = _aligned(returns, benchmark)
    return df["p"].rolling(window).cov(df["b"]) / df["b"].rolling(window).var()


def rolling_correlation(returns: pd.Series, benchmark: pd.Series, window: int = 60) -> pd.Series:
    df = _aligned(returns, benchmark)
    return df["p"].rolling(window).corr(df["b"])


def time_weighted_return(values: pd.Series, flows: pd.Series) -> float:
    """Chain-linked TWR. ``values`` are end-of-day values *including* the day's
    flow; ``flows`` are money added (+) or withdrawn (-) that day."""
    v = pd.Series(values, dtype="float64")
    f = pd.Series(flows, dtype="float64").reindex(v.index).fillna(0.0)
    prev = v.shift(1)
    r = ((v - f) / prev - 1).where(prev > 0)
    return float((1 + r.dropna()).prod() - 1)


def xirr(dates: list[date] | pd.Series, amounts: list[float] | pd.Series) -> float:
    """Money-weighted annual return. Convention: deposits negative, final value /
    withdrawals positive (investor's point of view)."""
    d = pd.to_datetime(pd.Series(list(dates))).to_numpy()
    a = np.asarray(list(amounts), dtype="float64")
    if not (np.any(a > 0) and np.any(a < 0)):
        raise ValueError("xirr needs at least one positive and one negative cash flow")
    years = (d - d.min()).astype("timedelta64[D]").astype("float64") / 365.0

    def npv(rate: float) -> float:
        return float(np.sum(a / (1 + rate) ** years))

    return float(optimize.brentq(npv, -0.9999, 100.0))


def performance_summary(returns: pd.Series, benchmark: pd.Series | None = None,
                        risk_free_rate: float = 0.0) -> dict[str, float]:
    summary = {
        "annual_return": annualized_return(returns),
        "annual_volatility": annualized_volatility(returns),
        "sharpe_ratio": sharpe_ratio(returns, risk_free_rate),
        "sortino_ratio": sortino_ratio(returns, risk_free_rate),
        "max_drawdown": max_drawdown(returns),
        "calmar_ratio": calmar_ratio(returns),
        "var_95": value_at_risk(returns, 0.95),
        "cvar_95": conditional_value_at_risk(returns, 0.95),
    }
    if benchmark is not None:
        up, down = capture_ratios(returns, benchmark)
        summary.update({
            "beta": beta(returns, benchmark),
            "alpha": jensens_alpha(returns, benchmark, risk_free_rate),
            "tracking_error": tracking_error(returns, benchmark),
            "information_ratio": information_ratio(returns, benchmark),
            "upside_capture": up,
            "downside_capture": down,
        })
    return summary
