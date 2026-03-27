"""Real-time Tableau-style Dashboard with Auto-Refresh."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import time
from src.portfolio import Portfolio
from src.analyzer import PortfolioAnalyzer

# ============= PAGE CONFIG =============
st.set_page_config(
    page_title="Portfolio Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============= CUSTOM CSS =============
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    h1 { color: #1f77b4; margin-bottom: 0.5rem; }
    h2 { color: #1f77b4; margin-top: 1.5rem; }
    .live-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #22AB94;
        animation: pulse 2s infinite;
        margin-right: 5px;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    </style>
""", unsafe_allow_html=True)

# ============= SIDEBAR CONTROLS =============
with st.sidebar:
    st.title("⚙️ Dashboard Controls")
    st.divider()

    # Refresh settings
    st.subheader("🔄 Auto-Refresh")
    auto_refresh = st.toggle("Enable Auto-Refresh", value=True)
    refresh_interval = st.slider("Refresh Interval (seconds)", 10, 300, 30, step=10)

    if st.button("🔄 Refresh Now", use_container_width=True):
        st.rerun()

    st.divider()

    # Display settings
    st.subheader("📊 Display Settings")
    show_allocation = st.checkbox("Show Asset Allocation", value=True)
    show_performance = st.checkbox("Show Performance Charts", value=True)
    show_table = st.checkbox("Show Holdings Table", value=True)
    show_top_worst = st.checkbox("Show Top/Worst Performers", value=True)

    st.divider()
    st.caption("Dashboard v1.0 | Real-time Portfolio Tracker")

# ============= CREATE PORTFOLIO =============
@st.cache_data(ttl=30)
def load_portfolio():
    portfolio = Portfolio("My Stock Portfolio")
    portfolio.add_holding("AAPL", 10, 150.00, "2023-01-15")
    portfolio.add_holding("MSFT", 5, 300.00, "2023-03-20")
    portfolio.add_holding("GOOGL", 3, 2800.00, "2023-06-10")
    portfolio.add_holding("AMZN", 2, 3200.00, "2023-08-05")
    return portfolio

portfolio = load_portfolio()
analyzer = PortfolioAnalyzer(portfolio)
summary = analyzer.calculate_portfolio_summary()
holdings = analyzer.calculate_current_value()

# ============= HEADER =============
col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    st.title("📊 Portfolio Performance Dashboard")
    if auto_refresh:
        st.markdown("<span class='live-indicator'></span>**Live Data** - Auto-updating every " + str(refresh_interval) + " seconds 🔄", unsafe_allow_html=True)
    else:
        st.markdown("*Real-time data from Yahoo Finance*")

with col2:
    status = "🟢 LIVE" if auto_refresh else "⏸ PAUSED"
    st.metric("Status", status)

with col3:
    st.metric("Last Update", summary['as_of_date'].split()[1])

st.divider()

# ============= KEY METRICS =============
st.subheader("📈 Summary Metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Invested",
        f"${summary['total_invested']:,.0f}",
        delta="Base"
    )

with col2:
    delta_value = summary['total_current_value'] - summary['total_invested']
    st.metric(
        "Current Value",
        f"${summary['total_current_value']:,.0f}",
        delta=f"${delta_value:,.0f}",
        delta_color="inverse" if delta_value < 0 else "normal"
    )

with col3:
    st.metric(
        "Gain/Loss",
        f"${summary['total_gain_loss_dollars']:,.0f}",
        delta=f"{summary['total_gain_loss_percent']:.2f}%",
        delta_color="inverse" if summary['total_gain_loss_percent'] < 0 else "normal"
    )

with col4:
    color = "#22AB94" if summary['total_gain_loss_percent'] > 0 else "#FF2B2B"
    st.markdown(f"""
    <div style="background: {color}; color: white; padding: 1rem; border-radius: 0.5rem; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        <div style="font-size: 0.9rem; opacity: 0.9;">Total Return</div>
        <div style="font-size: 2rem; font-weight: bold;">{summary['total_gain_loss_percent']:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ============= CHARTS ROW 1 =============
if show_allocation or show_performance:
    st.subheader("📊 Visual Analytics")

    if show_allocation and show_performance:
        col1, col2 = st.columns(2)
    elif show_allocation or show_performance:
        col1, col2 = st.columns([1, 1])

    # Pie Chart - Asset Allocation
    if show_allocation:
        with col1:
            allocation = analyzer.calculate_asset_allocation()

            fig_pie = go.Figure(data=[go.Pie(
                labels=allocation['symbol'],
                values=allocation['current_value'],
                marker=dict(colors=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']),
                hovertemplate='<b>%{label}</b><br>Value: $%{value:,.2f}<br>%{percent}<extra></extra>'
            )])

            fig_pie.update_layout(
                title="Asset Allocation",
                height=400,
                showlegend=True,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )

            st.plotly_chart(fig_pie, use_container_width=True)

    # Bar Chart - Gain/Loss by Stock
    if show_performance:
        with col2:
            colors = ['#22AB94' if x > 0 else '#FF2B2B' for x in holdings['gain_loss_percent']]

            fig_bar = go.Figure(data=[go.Bar(
                x=holdings['symbol'],
                y=holdings['gain_loss_percent'],
                marker=dict(color=colors),
                text=[f"{x:.1f}%" for x in holdings['gain_loss_percent']],
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>Return: %{y:.2f}%<extra></extra>'
            )])

            fig_bar.update_layout(
                title="Performance by Stock (%)",
                xaxis_title="Stock",
                yaxis_title="Gain/Loss %",
                height=400,
                showlegend=False,
                hovermode='x unified',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            fig_bar.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

            st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # ============= CHARTS ROW 2 =============
    col1, col2 = st.columns(2)

    # Current Value by Stock
    with col1:
        fig_value = go.Figure(data=[go.Bar(
            x=holdings['symbol'],
            y=holdings['current_value'],
            marker=dict(color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']),
            text=[f"${x:,.0f}" for x in holdings['current_value']],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Current Value: $%{y:,.2f}<extra></extra>'
        )])

        fig_value.update_layout(
            title="Current Portfolio Value by Stock",
            xaxis_title="Stock",
            yaxis_title="Value ($)",
            height=400,
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )

        st.plotly_chart(fig_value, use_container_width=True)

    # Gain/Loss Dollar Amount
    with col2:
        colors = ['#22AB94' if x > 0 else '#FF2B2B' for x in holdings['gain_loss_dollars']]

        fig_dollar = go.Figure(data=[go.Bar(
            x=holdings['symbol'],
            y=holdings['gain_loss_dollars'],
            marker=dict(color=colors),
            text=[f"${x:,.0f}" for x in holdings['gain_loss_dollars']],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Gain/Loss: $%{y:,.2f}<extra></extra>'
        )])

        fig_dollar.update_layout(
            title="Gain/Loss by Stock ($)",
            xaxis_title="Stock",
            yaxis_title="Gain/Loss ($)",
            height=400,
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        fig_dollar.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

        st.plotly_chart(fig_dollar, use_container_width=True)

    st.divider()

# ============= DETAILED TABLE =============
if show_table:
    st.subheader("📋 Holdings Details")

    # Prepare data for display
    table_df = holdings[['symbol', 'shares', 'purchase_price', 'current_price', 'current_value', 'gain_loss_dollars', 'gain_loss_percent']].copy()
    table_df.columns = ['Stock', 'Shares', 'Buy Price', 'Current Price', 'Value', 'Gain/Loss', 'Return %']

    # Format as currency and percentage
    display_df = table_df.copy()
    display_df['Buy Price'] = display_df['Buy Price'].apply(lambda x: f"${x:,.2f}")
    display_df['Current Price'] = display_df['Current Price'].apply(lambda x: f"${x:,.2f}")
    display_df['Value'] = display_df['Value'].apply(lambda x: f"${x:,.2f}")
    display_df['Gain/Loss'] = display_df['Gain/Loss'].apply(lambda x: f"${x:,.2f}")
    display_df['Return %'] = display_df['Return %'].apply(lambda x: f"{x:.2f}%")

    st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.divider()

# ============= TOP/WORST PERFORMERS =============
if show_top_worst:
    st.subheader("🏆 Performance Comparison")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏆 Top Performers")
        top = analyzer.get_best_performers(5)
        for idx, row in top.iterrows():
            emoji = "🟢" if row['gain_loss_percent'] > 0 else "🔴"
            st.metric(
                f"{emoji} {row['symbol']}",
                f"{row['gain_loss_percent']:.2f}%",
                f"${row['gain_loss_dollars']:,.2f}"
            )

    with col2:
        st.subheader("📉 Worst Performers")
        worst = analyzer.get_worst_performers(5)
        for idx, row in worst.iterrows():
            emoji = "🔴" if row['gain_loss_percent'] < 0 else "🟢"
            st.metric(
                f"{emoji} {row['symbol']}",
                f"{row['gain_loss_percent']:.2f}%",
                f"${row['gain_loss_dollars']:,.2f}"
            )

st.divider()

# ============= FOOTER =============
col1, col2, col3 = st.columns(3)
with col1:
    st.caption(f"📊 Holdings: {summary['number_of_holdings']}")
with col2:
    st.caption(f"🔄 Updated: {summary['as_of_date']}")
with col3:
    next_update = refresh_interval if auto_refresh else "Manual"
    st.caption(f"⏱️ Next Update: {next_update}s" if auto_refresh else "⏱️ Auto-Refresh: OFF")

# ============= AUTO-REFRESH LOOP =============
if auto_refresh:
    import streamlit.components.v1 as components

    # JavaScript to auto-refresh
    refresh_code = f"""
    <script>
        setTimeout(function() {{
            window.location.reload();
        }}, {refresh_interval * 1000});
    </script>
    """

    components.html(refresh_code)
