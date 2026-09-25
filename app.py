"""Portfolio analytics dashboard (serving layer).

Reads only from the DuckDB warehouse built by ``python -m pipelines.run``.
Run with:  streamlit run app.py
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import streamlit as st

from pipelines.config import load_config
from pipelines.run import run_pipeline
from src import charts, metrics, strategies
from src.warehouse import Warehouse

st.set_page_config(page_title="Portfolio Analytics", page_icon="📊", layout="wide")

CFG = load_config()


# --------------------------------------------------------------------------- data


def bootstrap_warehouse() -> str | None:
    """Build the warehouse on first start (e.g. a fresh Streamlit Cloud box).
    Falls back to the synthetic source if Yahoo is unreachable."""
    wh_ok = CFG.warehouse_path.exists() and Warehouse(CFG.warehouse_path).has_marts()
    if wh_ok:
        return None
    with st.spinner(f"First run: building the warehouse from the '{CFG.source}' source…"):
        try:
            if run_pipeline(CFG) in (0, 2):
                return None
        except Exception as exc:  # noqa: BLE001 - surface any failure and fall back
            if CFG.source == "sample":
                raise
            err = str(exc)
        else:
            err = "ingestion failed"
        sample_cfg = load_config(source="sample")
        run_pipeline(sample_cfg)
        return f"Could not load live data ({err[:120]}), so the dashboard is showing synthetic sample data."


@st.cache_data(ttl=600, show_spinner=False)
def load_all(path: str, _version: float) -> dict:
    wh = Warehouse(path)
    return {
        "pf": wh.portfolio_daily(),
        "holdings": wh.holdings(),
        "monthly": wh.monthly_returns(),
        "risk": wh.ticker_risk(),
        "tickers": wh.tickers(),
        "tri": wh.price_matrix("total_return_index"),
        "returns": wh.price_matrix("total_return"),
        "transactions": wh.transactions(),
        "runs": wh.ingestion_runs(),
        "freshness": wh.freshness(),
        "tables": wh.table_stats(),
        "quarantine": wh.quarantine(),
        "dbt": wh.dbt_results(),
    }


fallback_note = bootstrap_warehouse()
version = os.path.getmtime(CFG.warehouse_path)
data = load_all(str(CFG.warehouse_path), version)
pf_all: pd.DataFrame = data["pf"]
holdings: pd.DataFrame = data["holdings"]
bench = CFG.benchmark
colors = charts.ticker_colors(data["tickers"]["symbol"].tolist())
last_source = data["runs"]["source"].iloc[0] if not data["runs"].empty else CFG.source

# --------------------------------------------------------------------------- sidebar

st.sidebar.title("📊 Portfolio Analytics")
if last_source == "sample":
    st.sidebar.warning("**Synthetic sample data.** Prices are generated, not real quotes. "
                       "Set `source = \"yahoo\"` in `config/pipeline.toml` for live data.", icon="⚠️")
else:
    st.sidebar.success(f"Live data source: **{last_source}**", icon="✅")
if fallback_note:
    st.sidebar.info(fallback_note)

as_of = pf_all.index.max().date()
st.sidebar.caption(f"Data as of **{as_of}** · benchmark **{bench}** · risk-free {CFG.risk_free_rate:.1%}")

period = st.sidebar.radio("Analysis window", ["Since inception", "5Y", "3Y", "1Y", "YTD"], index=0)
start = pf_all.index.min()
if period == "YTD":
    start = max(start, pd.Timestamp(as_of.year, 1, 1))
elif period != "Since inception":
    start = max(start, pd.Timestamp(as_of) - pd.DateOffset(years=int(period[0])))
pf = pf_all.loc[start:].copy()
# rebase so every window starts at 0% and 0 drawdown
pf["twr_index"] = pf["twr_index"] / pf["twr_index"].iloc[0]
pf["benchmark_index"] = pf["benchmark_index"] / pf["benchmark_index"].iloc[0]
pf["drawdown"] = pf["twr_index"] / pf["twr_index"].cummax() - 1

if st.sidebar.button("🔄 Reload data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

port_ret = pf["daily_return"].iloc[1:]
bench_ret = pf["benchmark_return"].iloc[1:]

# --------------------------------------------------------------------------- tabs

tab_overview, tab_perf, tab_risk, tab_lab, tab_pipeline = st.tabs(
    ["Overview", "Performance", "Risk", "Strategy Lab", "Pipeline & Data Quality"])

# ---- Overview ---------------------------------------------------------------
with tab_overview:
    latest = pf_all.iloc[-1]
    flows = data["transactions"]
    irr_dates = list(pd.to_datetime(flows["trade_date"])) + [pf_all.index[-1]]
    irr_amounts = list(-flows["net_cash_flow"]) + [latest["total_value"]]
    try:
        money_weighted = metrics.xirr(irr_dates, irr_amounts)
    except ValueError:
        money_weighted = float("nan")
    twr_total = pf_all["twr_index"].iloc[-1] - 1
    bench_total = pf_all["benchmark_index"].iloc[-1] / pf_all["benchmark_index"].iloc[0] - 1

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Portfolio value", f"${latest['total_value']:,.0f}",
              help="Market value of open positions + dividends received (held as cash).")
    c2.metric("Net money put in", f"${latest['net_contributions']:,.0f}",
              help="Buys + fees minus sale proceeds.")
    c3.metric("Total profit", f"${latest['total_pnl']:,.0f}",
              f"{latest['total_pnl'] / latest['net_contributions']:+.1%} on money put in")
    c4.metric("Time-weighted return", f"{twr_total:+.1%}", f"{twr_total - bench_total:+.1%} vs {bench}",
              help="Return of the strategy itself, ignoring when money was added. Use this to compare "
                   "against the benchmark.")
    c5.metric("Money-weighted (XIRR)", f"{money_weighted:.1%} / yr",
              help="Annual return on your actual cash flows — reflects your timing.")

    st.plotly_chart(charts.value_vs_contributions(pf_all), use_container_width=True)

    left, right = st.columns(2)
    left.plotly_chart(charts.allocation_bars(holdings, "symbol", colors), use_container_width=True)
    right.plotly_chart(charts.allocation_bars(holdings, "sector"), use_container_width=True)

    max_weight = holdings["weight"].max()
    if max_weight > 0.25:
        top = holdings.loc[holdings["weight"].idxmax(), "symbol"]
        st.warning(f"⚠️ Concentration: **{top}** is {max_weight:.0%} of the portfolio (above a 25% guideline).")

    st.plotly_chart(charts.pnl_bars(holdings, colors), use_container_width=True)
    st.subheader("Open positions")
    st.dataframe(
        holdings[["symbol", "company_name", "sector", "shares", "avg_cost", "last_price", "market_value",
                  "unrealized_pnl", "unrealized_return", "dividends_received", "realized_pnl", "weight"]],
        hide_index=True, use_container_width=True,
        column_config={
            "symbol": "Ticker", "company_name": "Company", "sector": "Sector",
            "shares": st.column_config.NumberColumn("Shares", format="%.2f"),
            "avg_cost": st.column_config.NumberColumn("Avg cost", format="$%.2f"),
            "last_price": st.column_config.NumberColumn("Last price", format="$%.2f"),
            "market_value": st.column_config.NumberColumn("Value", format="dollar"),
            "unrealized_pnl": st.column_config.NumberColumn("Unrealised P&L", format="dollar"),
            "unrealized_return": st.column_config.NumberColumn("Return", format="percent"),
            "dividends_received": st.column_config.NumberColumn("Dividends", format="dollar"),
            "realized_pnl": st.column_config.NumberColumn("Realised P&L", format="dollar"),
            "weight": st.column_config.ProgressColumn("Weight", format="percent", min_value=0, max_value=1),
        })
    with st.expander("Trade ledger (restated for stock splits)"):
        st.dataframe(flows[["trade_date", "trade_id", "symbol", "side", "shares_as_traded", "price_as_traded",
                            "split_factor", "shares", "price", "net_cash_flow"]],
                     hide_index=True, use_container_width=True)

# ---- Performance --------------------------------------------------------------
with tab_perf:
    st.plotly_chart(charts.cumulative_vs_benchmark(pf, bench), use_container_width=True)

    summary = metrics.performance_summary(port_ret, bench_ret, CFG.risk_free_rate)
    bench_summary = metrics.performance_summary(bench_ret, None, CFG.risk_free_rate)
    rows = [
        ("Annual return", "annual_return", "{:.1%}"), ("Annual volatility", "annual_volatility", "{:.1%}"),
        ("Sharpe ratio", "sharpe_ratio", "{:.2f}"), ("Sortino ratio", "sortino_ratio", "{:.2f}"),
        ("Max drawdown", "max_drawdown", "{:.1%}"), ("Calmar ratio", "calmar_ratio", "{:.2f}"),
    ]
    table = pd.DataFrame(
        [{"Metric": label, "Portfolio": fmt.format(summary[key]), bench: fmt.format(bench_summary[key])}
         for label, key, fmt in rows])
    left, right = st.columns([3, 2])
    left.subheader(f"Risk-adjusted performance · {period}")
    left.dataframe(table, hide_index=True, use_container_width=True)
    right.subheader(f"Relative to {bench}")
    rel = pd.DataFrame([
        {"Metric": "Beta", "Value": f"{summary['beta']:.2f}",
         "Meaning": "1.0 = moves with the market"},
        {"Metric": "Alpha (annual)", "Value": f"{summary['alpha']:+.1%}",
         "Meaning": "return not explained by beta"},
        {"Metric": "Tracking error", "Value": f"{summary['tracking_error']:.1%}",
         "Meaning": "how far it strays from benchmark"},
        {"Metric": "Information ratio", "Value": f"{summary['information_ratio']:.2f}",
         "Meaning": "excess return per unit of tracking error"},
        {"Metric": "Upside capture", "Value": f"{summary['upside_capture']:.0%}",
         "Meaning": "share of up-days gains captured"},
        {"Metric": "Downside capture", "Value": f"{summary['downside_capture']:.0%}",
         "Meaning": "share of down-days losses taken"},
    ])
    right.dataframe(rel, hide_index=True, use_container_width=True)

    monthly = data["monthly"][data["monthly"]["month"] >= start.to_period("M").to_timestamp()]
    st.plotly_chart(charts.monthly_heatmap(monthly, "portfolio_return", "Monthly portfolio return"),
                    use_container_width=True)
    st.plotly_chart(charts.monthly_heatmap(monthly, "excess_return", f"Monthly excess return vs {bench}"),
                    use_container_width=True)

# ---- Risk -------------------------------------------------------------------
with tab_risk:
    bench_dd = pf["benchmark_index"] / pf["benchmark_index"].cummax() - 1
    st.plotly_chart(charts.drawdown_chart(pf, bench_dd), use_container_width=True)

    window = st.select_slider("Rolling window (trading days)", [21, 42, 63, 126, 252], value=63)
    left, right = st.columns(2)
    left.plotly_chart(charts.rolling_line(
        {"Portfolio": metrics.rolling_volatility(port_ret, window),
         bench: metrics.rolling_volatility(bench_ret, window)},
        f"Rolling {window}-day volatility (annualised)", colors=[charts.PORTFOLIO, charts.BENCHMARK]),
        use_container_width=True)
    right.plotly_chart(charts.rolling_line(
        {"Beta": metrics.rolling_beta(port_ret, bench_ret, window)},
        f"Rolling {window}-day beta to {bench}", y_format=".2f", ref_line=1.0), use_container_width=True)

    var95 = metrics.value_at_risk(port_ret, 0.95)
    cvar95 = metrics.conditional_value_at_risk(port_ret, 0.95)
    st.plotly_chart(charts.return_histogram(port_ret, var95, cvar95), use_container_width=True)
    value_now = pf_all["total_value"].iloc[-1]
    st.caption(f"On a typical bad day (1 in 20) the portfolio loses about **{-var95:.1%} "
               f"(\\${-var95 * value_now:,.0f})**; on those bad days the average loss is **{-cvar95:.1%}** "
               f"(\\${-cvar95 * value_now:,.0f}). Historical method, {period.lower()} window.")

    st.subheader("Per-ticker risk (trailing 1 year, from `marts.mart_ticker_risk`)")
    risk = data["risk"]
    st.dataframe(
        risk[["symbol", "sector", "annual_return", "annual_volatility", "sharpe_ratio", "sortino_ratio",
              "max_drawdown", "beta", "correlation_to_benchmark", "var_95_daily"]],
        hide_index=True, use_container_width=True,
        column_config={c: st.column_config.NumberColumn(format="percent") for c in
                       ["annual_return", "annual_volatility", "max_drawdown", "var_95_daily"]}
        | {c: st.column_config.NumberColumn(format="%.2f") for c in
           ["sharpe_ratio", "sortino_ratio", "beta", "correlation_to_benchmark"]})

    corr = data["returns"].loc[start:].dropna().corr()
    st.plotly_chart(charts.correlation_heatmap(corr), use_container_width=True)

# ---- Strategy Lab -------------------------------------------------------------
with tab_lab:
    st.markdown("Backtest how *the same money* would have done with different strategies, using "
                "dividend-reinvested prices from the warehouse.")
    tradeable = [s for s in data["tri"].columns]
    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
    picks = c1.multiselect("Tickers", tradeable, default=[s for s in holdings["symbol"] if s in tradeable])
    monthly_amount = c2.number_input("Monthly amount ($)", 100, 100_000, 1_000, 100)
    years_back = c3.selectbox("Backtest length", [1, 2, 3, 4, 5], index=2, format_func=lambda y: f"{y} years")
    weighting = c4.selectbox("Weights", ["Equal", "Current portfolio", "Max Sharpe"])

    if len(picks) < 1:
        st.info("Pick at least one ticker.")
    else:
        lab_start = pd.Timestamp(as_of) - pd.DateOffset(years=years_back)
        prices = data["tri"].loc[lab_start:, picks].dropna()
        rets = data["returns"].loc[lab_start:, picks].dropna()
        frontier, best = strategies.efficient_frontier(rets, risk_free_rate=CFG.risk_free_rate) \
            if len(picks) > 1 else (None, None)
        if weighting == "Equal" or len(picks) == 1:
            weights = {s: 1 / len(picks) for s in picks}
        elif weighting == "Current portfolio":
            cur = holdings.set_index("symbol")["weight"]
            weights = {s: float(cur.get(s, 0.0)) for s in picks}
            if sum(weights.values()) == 0:
                weights = {s: 1 / len(picks) for s in picks}
        else:
            weights = best["max_sharpe"]

        st.caption("Weights: " + ", ".join(f"{s} {w:.0%}" for s, w in weights.items() if w > 0.005))
        table, results = strategies.compare_strategies(prices, weights, monthly_amount)
        st.plotly_chart(charts.strategy_growth(results, strategies.STRATEGIES), use_container_width=True)
        st.dataframe(table, use_container_width=True, column_config={
            "total_invested": st.column_config.NumberColumn("Invested", format="dollar"),
            "final_value": st.column_config.NumberColumn("Final value", format="dollar"),
            "profit": st.column_config.NumberColumn("Profit", format="dollar"),
            "twr_annual": st.column_config.NumberColumn("TWR / yr", format="percent"),
            "xirr": st.column_config.NumberColumn("XIRR / yr", format="percent"),
            "max_drawdown": st.column_config.NumberColumn("Max drawdown", format="percent"),
            "volatility": st.column_config.NumberColumn("Volatility", format="percent"),
        })
        winner = table["final_value"].idxmax()
        st.caption(f"Over this window **{winner}** ended highest. Lump sum usually wins in rising markets "
                   "because money is invested longer; DCA reduces the risk of investing everything at a peak.")

        if frontier is not None:
            asset_stats = pd.DataFrame({"return": np.expm1(np.log1p(rets).mean() * 252),
                                        "volatility": rets.std() * np.sqrt(252)})
            pick_points = {}
            for name, w in (("Max Sharpe", best["max_sharpe"]), ("Min volatility", best["min_volatility"])):
                wr = rets @ pd.Series(w)
                pick_points[name] = (metrics.annualized_volatility(wr), metrics.annualized_return(wr))
            st.plotly_chart(charts.frontier_scatter(frontier, pick_points, asset_stats), use_container_width=True)
            st.caption("Max-Sharpe weights: " + ", ".join(
                f"{s} {w:.0%}" for s, w in sorted(best["max_sharpe"].items(), key=lambda kv: -kv[1]) if w > 0.01)
                + ". Past optimal weights are not a forecast — treat this as a diversification lens.")

    st.divider()
    st.subheader("Where could the current portfolio be in the future?")
    m1, m2 = st.columns(2)
    horizon = m1.slider("Years ahead", 1, 20, 10)
    contrib = m2.number_input("Monthly contribution ($)", 0, 100_000, 500, 100)
    mc = strategies.monte_carlo(pf_all["daily_return"].iloc[1:], pf_all["total_value"].iloc[-1],
                                years=horizon, monthly_contribution=contrib)
    st.plotly_chart(charts.monte_carlo_fan(mc), use_container_width=True)
    end_row = mc.iloc[-1]
    st.caption(f"After {horizon} years: median **\\${end_row['p50']:,.0f}**, 1-in-20 bad case "
               f"**\\${end_row['p5']:,.0f}**, 1-in-20 good case **\\${end_row['p95']:,.0f}** "
               f"(vs \\${end_row['contributed']:,.0f} put in). Resamples 20-day blocks of past daily returns, "
               "so it assumes the future looks like this portfolio's history.")

# ---- Pipeline & data quality -------------------------------------------------
with tab_pipeline:
    dbt_results = data["dbt"]
    tests = dbt_results[dbt_results["resource_type"] == "test"]
    failed = tests[tests["status"].isin(["fail", "error"])]
    warned = tests[tests["status"] == "warn"]
    runs = data["runs"]
    fresh = data["freshness"]
    stale = fresh[fresh["days_behind"] > 4]

    c1, c2, c3, c4 = st.columns(4)
    last_run = runs.iloc[0] if not runs.empty else None
    status_icon = {"success": "✅", "partial": "🟠", "failed": "❌", "running": "⏳"}
    c1.metric("Last ingestion", f"{status_icon.get(last_run['status'], '')} {last_run['status']}"
              if last_run is not None else "never")
    c2.metric("dbt tests passed", f"{'✅' if failed.empty else '❌'} {len(tests) - len(failed)}/{len(tests)}",
              f"{len(warned)} warnings" if len(warned) else None, delta_color="off")
    c3.metric("Stale tickers (>4 days)", f"{'✅' if stale.empty else '⚠️'} {len(stale)}")
    c4.metric("Quarantined rows", f"{'✅' if data['quarantine'].empty else '⚠️'} {len(data['quarantine'])}")

    if not failed.empty:
        st.error("Failing data tests:\n\n" + "\n".join(f"- `{n}`" for n in failed["name"]))

    st.subheader("Ingestion runs (`meta.ingestion_runs`)")
    st.dataframe(runs, hide_index=True, use_container_width=True)
    left, right = st.columns(2)
    left.subheader("Freshness by ticker")
    left.dataframe(fresh, hide_index=True, use_container_width=True, column_config={
        "last_price_date": st.column_config.DateColumn("last_price_date", format="YYYY-MM-DD")})
    right.subheader("Warehouse tables")
    right.dataframe(data["tables"], hide_index=True, use_container_width=True)
    generated = dbt_results["generated_at"].iloc[0] if not dbt_results.empty else "n/a"
    with st.expander(f"dbt build results ({len(dbt_results)} nodes, generated {generated}) "
                     "· `meta.dbt_results`"):
        st.dataframe(dbt_results, hide_index=True, use_container_width=True)
    if not data["quarantine"].empty:
        with st.expander("Quarantined rows"):
            st.dataframe(data["quarantine"], hide_index=True, use_container_width=True)

    st.subheader("Run the pipeline")
    source_choice = st.radio("Source", ["yahoo", "sample"], horizontal=True,
                             index=0 if CFG.source == "yahoo" else 1)
    if source_choice != last_source:
        st.caption(f"Switching from **{last_source}** to **{source_choice}** reloads the full price history "
                   "for every ticker, so the two sources are never mixed.")
    if st.button("▶️ Run incremental load + dbt build"):
        with st.spinner("Running pipeline…"):
            try:
                code = run_pipeline(load_config(source=source_choice))
                error = None
            except Exception as exc:  # noqa: BLE001 - show the failure instead of crashing the page
                code, error = 1, str(exc)
        st.cache_data.clear()
        if error is None and code == 0:
            st.success("Pipeline finished: data loaded and all dbt tests passed.")
            st.rerun()
        elif error is None:
            st.warning(f"Pipeline finished with exit code {code}: some tickers could not be loaded. "
                       "See the ingestion runs table above.")
        else:
            st.error(f"Pipeline failed: {error}")
            failing = Warehouse(CFG.warehouse_path).dbt_results()
            failing = failing[failing["status"].isin(["fail", "error"])]
            if not failing.empty:
                st.markdown("**Failing data checks** (the dashboard still shows the last good build):")
                st.dataframe(failing[["name", "status", "failures", "message"]], hide_index=True,
                             use_container_width=True)
            if source_choice == "yahoo":
                st.caption("If Yahoo Finance is unreachable or rate-limited, try again later or switch to "
                           "**sample**.")
