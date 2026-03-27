"""Advanced Tableau-style Portfolio Dashboard - Real-time with interactive filters."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np
from src.portfolio import Portfolio
from src.analyzer import PortfolioAnalyzer

# ============= PAGE CONFIG =============
st.set_page_config(
    page_title="Advanced Portfolio Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============= CUSTOM THEME & COLORS =============
PRIMARY_COLOR = "#1f77b4"
SUCCESS_COLOR = "#2ca02c"
DANGER_COLOR = "#d62728"
WARNING_COLOR = "#ff7f0e"
BG_COLOR = "#f8f9fa"

st.markdown("""
    <style>
    * { margin: 0; padding: 0; }
    .main { background-color: #f0f2f6; }

    /* KPI Cards */
    .kpi-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 0.75rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
    .kpi-card h3 { font-size: 0.95rem; opacity: 0.9; margin-bottom: 0.5rem; }
    .kpi-card .value { font-size: 2rem; font-weight: bold; }
    .kpi-card .delta { font-size: 0.85rem; margin-top: 0.25rem; }

    /* Section Headers */
    h1 { color: #1f2937; margin-bottom: 0.25rem; font-size: 2.5rem; }
    h2 { color: #1f77b4; margin-top: 2rem; margin-bottom: 1rem; font-size: 1.5rem; }
    h3 { color: #374151; font-size: 1.1rem; }

    /* Dividers */
    hr { border: none; border-top: 2px solid #e5e7eb; margin: 1.5rem 0; }

    /* Tables */
    .dataframe { font-size: 0.9rem; }
    </style>
""", unsafe_allow_html=True)

# ============= SIDEBAR CONTROLS =============
st.sidebar.title("⚙️ Dashboard Controls")
st.sidebar.markdown("---")

# Time Period Selection
time_option = st.sidebar.selectbox(
    "📅 Select Time Period",
    ["7 Days", "30 Days", "90 Days", "180 Days", "1 Year"],
    index=2
)

time_mapping = {
    "7 Days": 7,
    "30 Days": 30,
    "90 Days": 90,
    "180 Days": 180,
    "1 Year": 365
}
days_back = time_mapping[time_option]

# Auto-refresh
refresh_rate = st.sidebar.slider(
    "🔄 Refresh Rate (seconds)",
    10, 300, 60, step=10
)

if st.sidebar.button("🔄 Refresh Now", use_container_width=True):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Display Options")
show_correlation = st.sidebar.checkbox("Show Correlation Matrix", value=True)
show_risk_analysis = st.sidebar.checkbox("Show Risk Analytics", value=True)
show_price_comparison = st.sidebar.checkbox("Show Price Comparison", value=True)

# ============= LOAD DATA =============
@st.cache_data(ttl=60)
def load_portfolio():
    portfolio = Portfolio("My Stock Portfolio")
    portfolio.add_holding("AAPL", 10, 150.00, "2023-01-15")
    portfolio.add_holding("MSFT", 5, 300.00, "2023-03-20")
    portfolio.add_holding("GOOGL", 3, 2800.00, "2023-06-10")
    portfolio.add_holding("AMZN", 2, 3200.00, "2023-08-05")
    return portfolio

@st.cache_data(ttl=60)
def get_analysis_data(days):
    portfolio = load_portfolio()
    analyzer = PortfolioAnalyzer(portfolio)
    return analyzer, portfolio

analyzer, portfolio = get_analysis_data(days_back)
summary = analyzer.calculate_portfolio_summary()
holdings = analyzer.calculate_current_value()
allocation = analyzer.calculate_asset_allocation()

# ============= HEADER SECTION =============
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    st.title("📊 Advanced Portfolio Dashboard")
    st.markdown("*Real-time market data with advanced analytics*")

with col2:
    st.metric(
        "Portfolio Value",
        f"${summary['total_current_value']:,.0f}",
        f"${summary['total_gain_loss_dollars']:,.0f}"
    )

with col3:
    st.metric(
        "Return %",
        f"{summary['total_gain_loss_percent']:.2f}%",
        f"{time_option}"
    )

st.markdown("---")

# ============= KPI SECTION =============
st.subheader("📈 Key Performance Indicators")

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

with kpi_col1:
    gained = summary['total_gain_loss_percent'] > 0
    color = "🟢" if gained else "🔴"
    st.metric(
        "Total Return",
        f"{color} {summary['total_gain_loss_percent']:.2f}%",
        "Up" if gained else "Down"
    )

with kpi_col2:
    st.metric(
        "Total Invested",
        f"${summary['total_invested']:,.0f}",
        f"{summary['number_of_holdings']} stocks"
    )

with kpi_col3:
    best = analyzer.get_best_performers(1)
    if len(best) > 0:
        st.metric(
            "Best Stock",
            best.iloc[0]['symbol'],
            f"🟢 +{best.iloc[0]['gain_loss_percent']:.2f}%"
        )

with kpi_col4:
    worst = analyzer.get_worst_performers(1)
    if len(worst) > 0:
        st.metric(
            "Worst Stock",
            worst.iloc[0]['symbol'],
            f"🔴 {worst.iloc[0]['gain_loss_percent']:.2f}%"
        )

st.markdown("---")

# ============= MAIN ANALYTICS SECTION =============
st.subheader("📊 Visual Analytics")

# ROW 1: Asset Allocation & Performance
col1, col2 = st.columns(2)

with col1:
    fig_pie = go.Figure(data=[go.Pie(
        labels=allocation['symbol'],
        values=allocation['current_value'],
        marker=dict(colors=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']),
        textposition='inside',
        textinfo='label+percent',
        hovertemplate='<b>%{label}</b><br>Value: $%{value:,.0f}<br>%{percent}<extra></extra>'
    )])

    fig_pie.update_layout(
        title="Asset Allocation (Current Value)",
        height=450,
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(size=12)
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    colors = ['#2ca02c' if x > 0 else '#d62728' for x in holdings['gain_loss_percent']]

    fig_bar = go.Figure(data=[go.Bar(
        x=holdings['symbol'],
        y=holdings['gain_loss_percent'],
        marker=dict(color=colors, line=dict(color='white', width=2)),
        text=[f"{x:.1f}%" for x in holdings['gain_loss_percent']],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Return: %{y:.2f}%<br><extra></extra>'
    )])

    fig_bar.update_layout(
        title="Performance by Stock (%)",
        xaxis_title="Stock",
        yaxis_title="Return %",
        height=450,
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        hovermode='x unified',
        font=dict(size=11)
    )
    fig_bar.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.3)
    st.plotly_chart(fig_bar, use_container_width=True)

# ROW 2: Current Values & Gains
col1, col2 = st.columns(2)

with col1:
    fig_value = go.Figure(data=[go.Bar(
        x=holdings['symbol'],
        y=holdings['current_value'],
        marker=dict(color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']),
        text=[f"${x:,.0f}" for x in holdings['current_value']],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Current Value: $%{y:,.0f}<extra></extra>'
    )])

    fig_value.update_layout(
        title="Current Value by Stock",
        xaxis_title="Stock",
        yaxis_title="Value ($)",
        height=450,
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(size=11)
    )
    st.plotly_chart(fig_value, use_container_width=True)

with col2:
    colors = ['#2ca02c' if x > 0 else '#d62728' for x in holdings['gain_loss_dollars']]

    fig_dollar = go.Figure(data=[go.Bar(
        x=holdings['symbol'],
        y=holdings['gain_loss_dollars'],
        marker=dict(color=colors, line=dict(color='white', width=2)),
        text=[f"${x:,.0f}" for x in holdings['gain_loss_dollars']],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Gain/Loss: $%{y:,.0f}<extra></extra>'
    )])

    fig_dollar.update_layout(
        title="Gain/Loss Amount by Stock ($)",
        xaxis_title="Stock",
        yaxis_title="Gain/Loss ($)",
        height=450,
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        hovermode='x unified',
        font=dict(size=11)
    )
    fig_dollar.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.3)
    st.plotly_chart(fig_dollar, use_container_width=True)

st.markdown("---")

# ============= TIME SERIES ANALYSIS =============
if show_price_comparison:
    st.subheader("📈 Price Trend Analysis")

    try:
        price_history = analyzer.get_price_history(days=days_back)

        if not price_history.empty:
            fig_line = go.Figure()

            for symbol in holdings['symbol']:
                symbol_data = price_history[price_history['Symbol'] == symbol].sort_values('Date')
                if not symbol_data.empty:
                    fig_line.add_trace(go.Scatter(
                        x=symbol_data['Date'],
                        y=symbol_data['Close'],
                        mode='lines',
                        name=symbol,
                        hovertemplate='<b>%{fullData.name}</b><br>Date: %{x|%Y-%m-%d}<br>Price: $%{y:.2f}<extra></extra>'
                    ))

            fig_line.update_layout(
                title=f"Stock Price Trends - Last {time_option}",
                xaxis_title="Date",
                yaxis_title="Price ($)",
                height=500,
                hovermode='x unified',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(size=11)
            )
            st.plotly_chart(fig_line, use_container_width=True)
    except Exception as e:
        st.warning(f"⚠️ Could not load price history: {str(e)}")

st.markdown("---")

# ============= RISK ANALYTICS =============
if show_risk_analysis:
    st.subheader("⚠️ Risk Analytics")

    try:
        risk_metrics = analyzer.calculate_risk_metrics(days=days_back)

        col1, col2 = st.columns(2)

        with col1:
            # Volatility Chart
            fig_vol = go.Figure(data=[go.Bar(
                x=risk_metrics['symbol'],
                y=risk_metrics['volatility'],
                marker=dict(color='#ff7f0e'),
                text=[f"{x:.1%}" for x in risk_metrics['volatility']],
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>Volatility: %{y:.2%}<extra></extra>'
            )])

            fig_vol.update_layout(
                title="Annualized Volatility",
                xaxis_title="Stock",
                yaxis_title="Volatility",
                height=400,
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(size=11)
            )
            st.plotly_chart(fig_vol, use_container_width=True)

        with col2:
            # Sharpe Ratio Chart
            fig_sharpe = go.Figure(data=[go.Bar(
                x=risk_metrics['symbol'],
                y=risk_metrics['sharpe_ratio'],
                marker=dict(color=['#2ca02c' if x > 0 else '#d62728' for x in risk_metrics['sharpe_ratio']]),
                text=[f"{x:.2f}" for x in risk_metrics['sharpe_ratio']],
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>Sharpe Ratio: %{y:.2f}<extra></extra>'
            )])

            fig_sharpe.update_layout(
                title="Sharpe Ratio (Risk-Adjusted Return)",
                xaxis_title="Stock",
                yaxis_title="Sharpe Ratio",
                height=400,
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(size=11)
            )
            st.plotly_chart(fig_sharpe, use_container_width=True)

        # Risk Metrics Table
        st.markdown("### Risk Metrics Summary")
        risk_display = risk_metrics.copy()
        risk_display['volatility'] = risk_display['volatility'].apply(lambda x: f"{x:.2%}")
        risk_display['sharpe_ratio'] = risk_display['sharpe_ratio'].apply(lambda x: f"{x:.2f}")
        risk_display['max_drawdown'] = risk_display['max_drawdown'].apply(lambda x: f"{x:.2%}")
        risk_display['avg_return'] = risk_display['avg_return'].apply(lambda x: f"{x:.2%}")

        st.dataframe(
            risk_display.rename(columns={
                'symbol': 'Stock',
                'volatility': 'Volatility',
                'sharpe_ratio': 'Sharpe',
                'max_drawdown': 'Max Drawdown',
                'avg_return': 'Avg Return'
            }),
            use_container_width=True,
            hide_index=True
        )
    except Exception as e:
        st.warning(f"⚠️ Could not calculate risk metrics: {str(e)}")

st.markdown("---")

# ============= CORRELATION ANALYSIS =============
if show_correlation:
    st.subheader("🔗 Correlation Matrix")

    try:
        corr_matrix = analyzer.calculate_correlation_matrix(days=days_back)

        fig_corr = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.index,
            colorscale='RdBu',
            zmid=0,
            text=np.round(corr_matrix.values, 2),
            texttemplate='%{text:.2f}',
            textfont={"size": 12},
            hovertemplate='%{y} vs %{x}: %{z:.2f}<extra></extra>'
        ))

        fig_corr.update_layout(
            title="Stock Correlation Matrix",
            height=400,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(size=11)
        )
        st.plotly_chart(fig_corr, use_container_width=True)
    except Exception as e:
        st.warning(f"⚠️ Could not load correlation data: {str(e)}")

st.markdown("---")

# ============= HOLDINGS TABLE =============
st.subheader("📋 Holdings Details")

table_df = holdings[['symbol', 'shares', 'purchase_price', 'current_price', 'current_value', 'gain_loss_dollars', 'gain_loss_percent']].copy()
table_df.columns = ['Stock', 'Shares', 'Buy Price', 'Current Price', 'Value', 'Gain/Loss $', 'Return %']

# Format display
display_df = table_df.copy()
display_df['Buy Price'] = display_df['Buy Price'].apply(lambda x: f"${x:,.2f}")
display_df['Current Price'] = display_df['Current Price'].apply(lambda x: f"${x:,.2f}")
display_df['Value'] = display_df['Value'].apply(lambda x: f"${x:,.2f}")
display_df['Gain/Loss $'] = display_df['Gain/Loss $'].apply(lambda x: f"${x:,.2f}")
display_df['Return %'] = display_df['Return %'].apply(lambda x: f"{x:.2f}%")

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)

st.markdown("---")

# ============= TOP & WORST PERFORMERS =============
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏆 Top Performers")
    top = analyzer.get_best_performers(len(holdings))
    for idx, row in top.iterrows():
        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.write(f"**{row['symbol']}**")
        with col_b:
            st.write(f"🟢 +{row['gain_loss_percent']:.2f}%")

with col2:
    st.subheader("📉 Worst Performers")
    worst = analyzer.get_worst_performers(len(holdings))
    for idx, row in worst.iterrows():
        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.write(f"**{row['symbol']}**")
        with col_b:
            st.write(f"🔴 {row['gain_loss_percent']:.2f}%")

st.markdown("---")

# ============= FOOTER =============
st.markdown(f"""
<div style='text-align: center; color: #6b7280; font-size: 0.9rem; margin-top: 2rem;'>
    <p>Last updated: {summary['as_of_date']} | Auto-refresh every {refresh_rate}s</p>
    <p>📊 Advanced Portfolio Dashboard v1.0</p>
</div>
""", unsafe_allow_html=True)
