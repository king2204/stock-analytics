"""Integration tests: the dbt models produce correct numbers on the sample data."""

import pytest

from pipelines.run import run_pipeline
from src import metrics
from src.warehouse import Warehouse
from tests.conftest import sample_config


def scalar(con, sql):
    return con.execute(sql).fetchone()[0]


def test_trades_before_splits_are_restated(con):
    rows = dict(con.execute("""
        select trade_id, shares from intermediate.int_transactions_split_adjusted
        where trade_id in ('T0001', 'T0004')""").fetchall())
    assert rows["T0001"] == pytest.approx(20)   # 1 AMZN share x 20:1 split
    assert rows["T0004"] == pytest.approx(50)   # 5 NVDA shares x 10:1 split
    price = scalar(con, "select price from intermediate.int_transactions_split_adjusted where trade_id='T0001'")
    assert price == pytest.approx(151.10)


def test_average_cost_and_realised_pnl(con):
    aapl = con.execute("""select shares_after, avg_cost_after from intermediate.int_trade_ledger
                          where symbol='AAPL' order by seq desc limit 1""").fetchone()
    assert aapl[0] == 15
    assert aapl[1] == pytest.approx((10 * 135.94 + 5 * 169.30) / 15)
    msft_realised = scalar(con, "select realized_pnl from intermediate.int_trade_ledger where trade_id='T0010'")
    assert msft_realised == pytest.approx(2 * (410.92 - 272.23))


def test_holdings_match_ledger(con):
    shares = dict(con.execute("select symbol, shares from marts.mart_holdings_current").fetchall())
    assert shares["MSFT"] == pytest.approx(3)
    assert shares["AMZN"] == pytest.approx(40)
    assert scalar(con, "select round(sum(weight), 6) from marts.mart_holdings_current") == 1.0


def test_dividends_only_paid_on_shares_held_before_ex_date(con):
    # NVDA pays 0.01/quarter; 50 shares held -> 0.50 per ex-date, nothing before the buy
    first_div = con.execute("""select date, dividend_income from marts.fct_position_daily
                               where symbol='NVDA' and dividend_income > 0 order by date limit 1""").fetchone()
    assert first_div[1] == pytest.approx(0.50)
    assert str(first_div[0]) > "2023-06-01"


def test_portfolio_twr_matches_python_implementation(built_config):
    pf = Warehouse(built_config.warehouse_path).portfolio_daily()
    py_twr = metrics.time_weighted_return(pf["total_value"], pf["net_cash_flow"])
    assert pf["twr_index"].iloc[-1] - 1 == pytest.approx(py_twr, rel=1e-9)


def test_net_contributions_equal_ledger_cash(con):
    ledger = scalar(con, "select sum(net_cash_flow) from intermediate.int_transactions_split_adjusted")
    mart = scalar(con, "select net_contributions from marts.fct_portfolio_daily order by date desc limit 1")
    assert mart == pytest.approx(ledger)


def test_monthly_returns_chain_to_total_twr(con):
    monthly = scalar(con, "select exp(sum(ln(1 + portfolio_return))) from marts.mart_monthly_returns")
    total = scalar(con, "select twr_index from marts.fct_portfolio_daily order by date desc limit 1")
    assert monthly == pytest.approx(total, rel=1e-9)


def test_all_dbt_tests_passed_and_were_recorded_in_warehouse(built_config):
    results = Warehouse(built_config.warehouse_path).dbt_results()
    tests = results[results["resource_type"] == "test"]
    assert len(tests) >= 50
    assert set(results["status"]) <= {"pass", "success"}


def test_bad_trade_price_is_caught_by_dbt(tmp_path):
    """The old sample file had GOOGL at $2,800 in June 2023 (pre-split price
    entered for a post-split date). The data test must fail the build."""
    bad = tmp_path / "tx.csv"
    bad.write_text("trade_id,trade_date,symbol,side,shares,price,fees\n"
                   "T1,2023-06-12,GOOGL,BUY,3,2800.00,0\n")
    cfg = sample_config(tmp_path, transactions_path=str(bad))
    with pytest.raises(RuntimeError, match="dbt build failed"):
        run_pipeline(cfg)
    results = Warehouse(cfg.warehouse_path).dbt_results()
    failed = set(results.loc[results["status"] == "fail", "name"])
    assert "assert_transaction_price_near_market" in failed


def test_selling_more_than_held_is_caught_by_dbt(tmp_path):
    bad = tmp_path / "tx.csv"
    bad.write_text("trade_id,trade_date,symbol,side,shares,price,fees\n"
                   "T1,2024-02-01,JPM,BUY,5,172.50,0\n"
                   "T2,2024-05-01,JPM,SELL,8,172.50,0\n")
    cfg = sample_config(tmp_path, transactions_path=str(bad))
    with pytest.raises(RuntimeError):
        run_pipeline(cfg)
    results = Warehouse(cfg.warehouse_path).dbt_results()
    failed = results.loc[results["status"] == "fail", "name"].tolist()
    assert any("int_trade_ledger_shares_after" in f for f in failed)
