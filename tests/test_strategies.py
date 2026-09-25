import numpy as np
import pandas as pd
import pytest

from src import strategies


def make_prices(days=260, growth=0.001, seed=0):
    idx = pd.bdate_range("2023-01-02", periods=days)
    rng = np.random.default_rng(seed)
    a = 100 * np.cumprod(1 + growth + rng.normal(0, 0.01, days))
    b = 50 * np.cumprod(1 + growth / 2 + rng.normal(0, 0.005, days))
    return pd.DataFrame({"A": a, "B": b}, index=idx)


def test_all_strategies_invest_the_same_total():
    prices = make_prices()
    table, results = strategies.compare_strategies(prices, {"A": 0.5, "B": 0.5}, 1000)
    assert table["total_invested"].nunique() == 1
    assert table["total_invested"].iloc[0] == 1000 * 12  # Jan..Dec 2023
    assert results["dca"].daily["invested"].iloc[-1] == 12_000


def test_lump_sum_beats_dca_in_steadily_rising_market():
    idx = pd.bdate_range("2023-01-02", periods=260)
    prices = pd.DataFrame({"A": 100 * 1.001 ** np.arange(260)}, index=idx)
    table, _ = strategies.compare_strategies(prices, {"A": 1.0}, 1000)
    lump = table.loc[strategies.STRATEGIES["lump_sum"], "final_value"]
    dca = table.loc[strategies.STRATEGIES["dca"], "final_value"]
    assert lump > dca
    # constant growth -> every strategy's TWR equals the asset's return
    assert table["twr_annual"].to_numpy() == pytest.approx(1.001 ** 252 - 1, rel=1e-6)


def test_rebalancing_is_a_noop_for_one_asset_and_matters_for_two():
    prices = make_prices(growth=0.003)
    one = prices[["A"]]
    dca = strategies.backtest(one, {"A": 1}, 1000, "dca").daily["value"]
    reb = strategies.backtest(one, {"A": 1}, 1000, "dca_rebalanced").daily["value"]
    assert np.allclose(dca, reb)
    two_dca = strategies.backtest(prices, {"A": 0.5, "B": 0.5}, 1000, "dca").daily["value"]
    two_reb = strategies.backtest(prices, {"A": 0.5, "B": 0.5}, 1000, "dca_rebalanced").daily["value"]
    assert not np.allclose(two_dca, two_reb)


def test_unknown_strategy_rejected():
    with pytest.raises(ValueError):
        strategies.backtest(make_prices(), {"A": 1}, 100, "yolo")


def test_monte_carlo_percentiles_are_ordered_and_contributions_counted():
    r = pd.Series(np.random.default_rng(5).normal(0.0004, 0.01, 800))
    mc = strategies.monte_carlo(r, 10_000, years=2, monthly_contribution=100, n_sims=300)
    assert len(mc) == 504
    assert (mc["p5"] <= mc["p25"]).all() and (mc["p25"] <= mc["p50"]).all()
    assert (mc["p50"] <= mc["p75"]).all() and (mc["p75"] <= mc["p95"]).all()
    assert mc["contributed"].iloc[-1] == 10_000 + 100 * 24


def test_efficient_frontier_weights_valid():
    rets = make_prices().pct_change().dropna()
    frontier, best = strategies.efficient_frontier(rets, n_portfolios=500)
    assert len(frontier) == 500
    for w in best.values():
        assert sum(w.values()) == pytest.approx(1.0)
        assert min(w.values()) >= 0
    # recomputing the max-Sharpe pick from its weights reproduces the cloud's best point
    w = pd.Series(best["max_sharpe"])[rets.columns]
    port = rets @ w
    ret = np.expm1(np.log1p(port).mean() * 252)
    vol = port.std() * np.sqrt(252)
    assert ret / vol == pytest.approx(frontier["sharpe"].max())
