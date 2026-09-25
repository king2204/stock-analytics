from datetime import date

import numpy as np
import pandas as pd
import pytest

from src import metrics


def test_constant_daily_return_annualises_exactly():
    r = pd.Series([0.001] * 252)
    assert metrics.annualized_return(r) == pytest.approx(1.001 ** 252 - 1)
    assert metrics.annualized_volatility(r) == pytest.approx(0.0, abs=1e-12)
    assert metrics.max_drawdown(r) == 0


def test_max_drawdown_known_path():
    # 100 -> 120 -> 60 -> 90 : worst drawdown is 60/120 - 1 = -50%
    r = pd.Series([0.2, -0.5, 0.5])
    assert metrics.max_drawdown(r) == pytest.approx(-0.5)
    assert metrics.drawdown_series(r).iloc[-1] == pytest.approx(90 / 120 - 1)


def test_beta_of_scaled_series():
    rng = np.random.default_rng(0)
    b = pd.Series(rng.normal(0, 0.01, 500))
    assert metrics.beta(b, b) == pytest.approx(1.0)
    assert metrics.beta(2 * b, b) == pytest.approx(2.0)
    assert metrics.tracking_error(b, b) == pytest.approx(0.0)


def test_alpha_is_zero_when_portfolio_is_levered_benchmark_at_zero_rf():
    rng = np.random.default_rng(1)
    b = pd.Series(rng.normal(0.0005, 0.01, 1000))
    assert abs(metrics.jensens_alpha(b, b)) < 1e-12


def test_value_at_risk_and_cvar():
    r = pd.Series(np.linspace(-0.10, 0.09, 20))  # 20 evenly spaced returns
    var = metrics.value_at_risk(r, 0.95)
    assert var == pytest.approx(np.quantile(r, 0.05))
    assert metrics.conditional_value_at_risk(r, 0.95) <= var
    assert metrics.value_at_risk(r, 0.95, "parametric") < 0


def test_xirr_simple_cases():
    assert metrics.xirr([date(2023, 1, 1), date(2024, 1, 1)], [-100, 110]) == pytest.approx(0.10, abs=1e-3)
    # two deposits, doubled money over ~1.5y on average
    irr = metrics.xirr([date(2022, 1, 1), date(2023, 1, 1), date(2024, 1, 1)], [-100, -100, 300])
    npv = -100 * 1.0 - 100 / (1 + irr) ** 1 + 300 / (1 + irr) ** (730 / 365)
    assert abs(npv) < 1e-6
    with pytest.raises(ValueError):
        metrics.xirr([date(2023, 1, 1)], [-100])


def test_twr_ignores_deposits():
    # Value doubles on day 1, then a 1,000 deposit arrives with no market move.
    values = pd.Series([1000.0, 2000.0, 3000.0])
    flows = pd.Series([1000.0, 0.0, 1000.0])
    assert metrics.time_weighted_return(values, flows) == pytest.approx(1.0)


def test_sortino_higher_than_sharpe_when_only_upside_volatility():
    r = pd.Series([0.02, 0.0, 0.03, 0.0, 0.01, -0.001] * 50)
    assert metrics.sortino_ratio(r) > metrics.sharpe_ratio(r)


def test_performance_summary_keys():
    rng = np.random.default_rng(3)
    p, b = pd.Series(rng.normal(0, 0.01, 300)), pd.Series(rng.normal(0, 0.01, 300))
    s = metrics.performance_summary(p, b, 0.02)
    assert {"sharpe_ratio", "beta", "alpha", "upside_capture", "cvar_95"} <= set(s)
