"""Plotly chart builders with one consistent, colour-blind-checked palette.

Rules applied throughout: each ticker keeps the same colour everywhere
(colour follows the entity, never its rank), one y-axis per chart, thin marks,
diverging scales use a grey midpoint, and status colours are reserved for
pass/fail states.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
PORTFOLIO = CATEGORICAL[0]
BENCHMARK = CATEGORICAL[1]
DIVERGING = [[0.0, "#b3261e"], [0.25, "#e98a86"], [0.5, "#f0efec"], [0.75, "#6da7ec"], [1.0, "#184f95"]]
SEQUENTIAL = [[0.0, "#cde2fb"], [0.5, "#3987e5"], [1.0, "#0d366b"]]
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}


def ticker_colors(symbols: list[str]) -> dict[str, str]:
    """Stable symbol -> colour map (alphabetical, so filters never repaint)."""
    return {s: CATEGORICAL[i % len(CATEGORICAL)] for i, s in enumerate(sorted(symbols))}


def _layout(fig: go.Figure, title: str = "", height: int = 380, y_format: str | None = None,
            legend: bool = True) -> go.Figure:
    fig.update_layout(
        title={"text": title, "font": {"size": 15, "color": INK}, "x": 0, "xanchor": "left"},
        height=height,
        margin={"l": 8, "r": 8, "t": 48 if title else 16, "b": 8},
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font={"family": "system-ui, -apple-system, Segoe UI, sans-serif", "color": INK_2, "size": 12},
        hovermode="x unified",
        hoverlabel={"bgcolor": "white", "font_color": INK},
        showlegend=legend,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.0, "xanchor": "right", "x": 1,
                "font": {"color": INK_2}},
    )
    fig.update_xaxes(showgrid=False, linecolor=AXIS, tickfont={"color": MUTED}, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, gridwidth=1, linecolor=AXIS, tickfont={"color": MUTED},
                     zerolinecolor=AXIS, tickformat=y_format)
    return fig


def value_vs_contributions(pf: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=pf.index, y=pf["net_contributions"], name="Money put in",
                             line={"color": MUTED, "width": 2, "shape": "hv", "dash": "dot"},
                             hovertemplate="$%{y:,.0f}"))
    fig.add_trace(go.Scatter(x=pf.index, y=pf["total_value"], name="Portfolio value",
                             line={"color": PORTFOLIO, "width": 2}, fill="tonexty",
                             fillcolor="rgba(42,120,214,0.10)", hovertemplate="$%{y:,.0f}"))
    return _layout(fig, "Portfolio value vs money put in", y_format="$,.0f")


def cumulative_vs_benchmark(pf: pd.DataFrame, benchmark_name: str) -> go.Figure:
    fig = go.Figure()
    port = pf["twr_index"] / pf["twr_index"].iloc[0] - 1
    bench = pf["benchmark_index"] / pf["benchmark_index"].iloc[0] - 1
    fig.add_trace(go.Scatter(x=pf.index, y=port, name="Portfolio (time-weighted)",
                             line={"color": PORTFOLIO, "width": 2}, hovertemplate="%{y:.1%}"))
    fig.add_trace(go.Scatter(x=pf.index, y=bench, name=f"{benchmark_name} (total return)",
                             line={"color": BENCHMARK, "width": 2}, hovertemplate="%{y:.1%}"))
    for series, color in ((port, PORTFOLIO), (bench, BENCHMARK)):
        fig.add_annotation(x=series.index[-1], y=series.iloc[-1], text=f"{series.iloc[-1]:+.0%}",
                           showarrow=False, xanchor="left", xshift=6, font={"color": INK, "size": 12})
        fig.add_trace(go.Scatter(x=[series.index[-1]], y=[series.iloc[-1]], mode="markers",
                                 marker={"color": color, "size": 8, "line": {"color": SURFACE, "width": 2}},
                                 showlegend=False, hoverinfo="skip"))
    return _layout(fig, "Cumulative return: portfolio vs benchmark", y_format=".0%")


def drawdown_chart(pf: pd.DataFrame, bench_dd: pd.Series | None = None) -> go.Figure:
    fig = go.Figure()
    if bench_dd is not None:
        fig.add_trace(go.Scatter(x=bench_dd.index, y=bench_dd, name="Benchmark",
                                 line={"color": BENCHMARK, "width": 1.5}, hovertemplate="%{y:.1%}"))
    fig.add_trace(go.Scatter(x=pf.index, y=pf["drawdown"], name="Portfolio", fill="tozeroy",
                             line={"color": PORTFOLIO, "width": 2}, fillcolor="rgba(42,120,214,0.12)",
                             hovertemplate="%{y:.1%}"))
    worst = pf["drawdown"].idxmin()
    fig.add_annotation(x=worst, y=pf["drawdown"].min(), text=f"Worst {pf['drawdown'].min():.1%}",
                       showarrow=True, arrowcolor=MUTED, ay=30, font={"color": INK})
    return _layout(fig, "Drawdown from previous peak", y_format=".0%")


def allocation_bars(holdings: pd.DataFrame, by: str, colors: dict[str, str] | None = None) -> go.Figure:
    df = holdings.groupby(by, as_index=False)["market_value"].sum()
    df["weight"] = df["market_value"] / df["market_value"].sum()
    df = df.sort_values("weight")
    bar_colors = [colors.get(v, PORTFOLIO) for v in df[by]] if colors else PORTFOLIO
    fig = go.Figure(go.Bar(
        x=df["weight"], y=df[by], orientation="h", marker={"color": bar_colors, "line": {"color": SURFACE, "width": 2}},
        text=[f"{w:.0%}" for w in df["weight"]], textposition="outside", textfont={"color": INK_2},
        customdata=df["market_value"], hovertemplate="%{y}: %{x:.1%} ($%{customdata:,.0f})<extra></extra>",
    ))
    fig.update_xaxes(range=[0, df["weight"].max() * 1.2])
    title = "Allocation by " + ("ticker" if by == "symbol" else by)
    return _layout(fig, title, height=300, legend=False).update_layout(hovermode="closest")


def pnl_bars(holdings: pd.DataFrame, colors: dict[str, str]) -> go.Figure:
    df = holdings.sort_values("unrealized_return")
    fig = go.Figure(go.Bar(
        x=df["unrealized_return"], y=df["symbol"], orientation="h",
        marker={"color": [colors[s] for s in df["symbol"]], "line": {"color": SURFACE, "width": 2}},
        text=[f"{r:+.0%}" for r in df["unrealized_return"]], textposition="outside", textfont={"color": INK_2},
        customdata=df["unrealized_pnl"],
        hovertemplate="%{y}: %{x:+.1%} ($%{customdata:+,.0f})<extra></extra>",
    ))
    lo, hi = min(0, df["unrealized_return"].min()), max(0, df["unrealized_return"].max())
    fig.update_xaxes(range=[lo * 1.25, hi * 1.25], tickformat=".0%")
    return _layout(fig, "Unrealised return on cost", height=300, legend=False).update_layout(hovermode="closest")


def monthly_heatmap(monthly: pd.DataFrame, column: str = "portfolio_return", title: str = "") -> go.Figure:
    df = monthly.copy()
    df["year"] = df["month"].dt.year
    df["m"] = df["month"].dt.strftime("%b")
    order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    grid = df.pivot(index="year", columns="m", values=column).reindex(columns=order)
    limit = float(np.nanmax(np.abs(grid.to_numpy()))) or 0.1
    fig = go.Figure(go.Heatmap(
        z=grid.to_numpy(), x=order, y=[str(y) for y in grid.index], colorscale=DIVERGING,
        zmid=0, zmin=-limit, zmax=limit, xgap=2, ygap=2,
        text=[[("" if pd.isna(v) else f"{v:+.1%}") for v in row] for row in grid.to_numpy()],
        texttemplate="%{text}", textfont={"size": 11, "color": INK},
        hovertemplate="%{x} %{y}: %{z:+.2%}<extra></extra>",
        colorbar={"tickformat": ".0%", "outlinewidth": 0, "thickness": 10},
    ))
    fig.update_yaxes(autorange="reversed", gridcolor=SURFACE)
    return _layout(fig, title, height=90 + 38 * len(grid), legend=False).update_layout(hovermode="closest")


def correlation_heatmap(corr: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Heatmap(
        z=corr.to_numpy(), x=corr.columns, y=corr.index, colorscale=DIVERGING, zmin=-1, zmax=1, zmid=0,
        xgap=2, ygap=2, texttemplate="%{z:.2f}", textfont={"size": 11, "color": INK},
        hovertemplate="%{y} vs %{x}: %{z:.2f}<extra></extra>", colorbar={"outlinewidth": 0, "thickness": 10},
    ))
    fig.update_yaxes(autorange="reversed", gridcolor=SURFACE)
    return _layout(fig, "Correlation of daily returns (1 = move together)", height=420,
                   legend=False).update_layout(hovermode="closest")


def rolling_line(series: dict[str, pd.Series], title: str, y_format: str = ".0%",
                 colors: list[str] | None = None, ref_line: float | None = None) -> go.Figure:
    fig = go.Figure()
    colors = colors or CATEGORICAL
    for (name, s), color in zip(series.items(), colors):
        fig.add_trace(go.Scatter(x=s.index, y=s, name=name, line={"color": color, "width": 2},
                                 hovertemplate="%{y:" + y_format + "}"))
    if ref_line is not None:
        fig.add_hline(y=ref_line, line={"color": AXIS, "width": 1, "dash": "dot"})
    return _layout(fig, title, y_format=y_format, legend=len(series) > 1)


def return_histogram(returns: pd.Series, var: float, cvar: float) -> go.Figure:
    fig = go.Figure(go.Histogram(x=returns.dropna(), nbinsx=80, marker={"color": PORTFOLIO,
                                 "line": {"color": SURFACE, "width": 1}},
                                 hovertemplate="%{x:.1%}: %{y} days<extra></extra>"))
    # VaR label to the right of its line, CVaR (further left) to the left of its line
    for value, label, anchor, shift in ((var, "VaR 95%", "left", 4), (cvar, "CVaR 95%", "right", -4)):
        fig.add_vline(x=value, line={"color": STATUS["critical"], "width": 1.5, "dash": "dash"})
        fig.add_annotation(x=value, y=1, yref="paper", text=f"{label} {value:.1%}", showarrow=False,
                           xanchor=anchor, xshift=shift, font={"color": INK, "size": 11},
                           bgcolor=SURFACE)
    fig.update_xaxes(tickformat=".0%")
    return _layout(fig, "Distribution of daily portfolio returns", legend=False).update_layout(hovermode="closest")


def strategy_growth(results: dict, labels: dict[str, str]) -> go.Figure:
    fig = go.Figure()
    first = next(iter(results.values())).daily
    fig.add_trace(go.Scatter(x=first.index, y=results["dca"].daily["invested"], name="DCA money put in",
                             line={"color": MUTED, "width": 1.5, "dash": "dot", "shape": "hv"},
                             hovertemplate="$%{y:,.0f}"))
    for (key, res), color in zip(results.items(), CATEGORICAL):
        fig.add_trace(go.Scatter(x=res.daily.index, y=res.daily["value"], name=labels[key],
                                 line={"color": color, "width": 2}, hovertemplate="$%{y:,.0f}"))
    return _layout(fig, "Growth of each strategy (same total money invested)", y_format="$,.0f", height=420)


def monte_carlo_fan(mc: pd.DataFrame) -> go.Figure:
    x = mc["years"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=mc["p95"], line={"width": 0}, showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=mc["p5"], fill="tonexty", fillcolor="rgba(42,120,214,0.12)",
                             line={"width": 0}, name="5th-95th percentile", hovertemplate="p5 $%{y:,.0f}"))
    fig.add_trace(go.Scatter(x=x, y=mc["p75"], line={"width": 0}, showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=mc["p25"], fill="tonexty", fillcolor="rgba(42,120,214,0.28)",
                             line={"width": 0}, name="25th-75th percentile", hovertemplate="p25 $%{y:,.0f}"))
    fig.add_trace(go.Scatter(x=x, y=mc["p50"], name="Median", line={"color": PORTFOLIO, "width": 2},
                             hovertemplate="median $%{y:,.0f}"))
    fig.add_trace(go.Scatter(x=x, y=mc["contributed"], name="Money put in",
                             line={"color": MUTED, "width": 1.5, "dash": "dot"}, hovertemplate="$%{y:,.0f}"))
    fig.update_xaxes(title={"text": "Years from today", "font": {"color": MUTED}})
    return _layout(fig, "Monte Carlo projection (block bootstrap of history)", y_format="$,.0f", height=420)


def frontier_scatter(frontier: pd.DataFrame, picks: dict[str, tuple[float, float]],
                     assets: pd.DataFrame | None = None) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=frontier["volatility"], y=frontier["return"], mode="markers", name="Random portfolios",
        marker={"color": frontier["sharpe"], "colorscale": SEQUENTIAL, "size": 5, "opacity": 0.7,
                "colorbar": {"title": "Sharpe", "outlinewidth": 0, "thickness": 10}},
        hovertemplate="vol %{x:.1%}, return %{y:.1%}<extra></extra>",
    ))
    if assets is not None:
        fig.add_trace(go.Scatter(x=assets["volatility"], y=assets["return"], mode="markers+text",
                                 text=assets.index, textposition="top center", name="Single stocks",
                                 marker={"color": MUTED, "size": 8, "symbol": "diamond"},
                                 textfont={"color": INK_2}, hovertemplate="%{text}<extra></extra>"))
    for (name, (vol, ret)), color in zip(picks.items(), (CATEGORICAL[1], CATEGORICAL[2])):
        fig.add_trace(go.Scatter(x=[vol], y=[ret], mode="markers", name=name,
                                 marker={"color": color, "size": 14, "symbol": "star",
                                         "line": {"color": SURFACE, "width": 2}},
                                 hovertemplate=name + ": vol %{x:.1%}, return %{y:.1%}<extra></extra>"))
    fig.update_xaxes(tickformat=".0%", title={"text": "Annual volatility", "font": {"color": MUTED}})
    return _layout(fig, "Efficient frontier (long-only, trailing history)", y_format=".0%",
                   height=460).update_layout(hovermode="closest")
