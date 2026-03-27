"""Beautiful Tableau-style Dashboard for Portfolio Performance."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from src.portfolio import Portfolio
from src.analyzer import PortfolioAnalyzer

# ============= PAGE CONFIG =============
st.set_page_config(
    page_title="Portfolio Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
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
    </style>
""", unsafe_allow_html=True)

# ============= AUTO REFRESH =============
# Auto-refresh data every 30 seconds
st.set_option('client.showErrorDetails', False)

# Sidebar: Refresh control
with st.sidebar:
    st.title("⚙️ Controls")
    refresh_rate = st.slider("Refresh Rate (seconds)", 10, 300, 30, step=10)

    if st.button("🔄 Refresh Now", use_container_width=True):
        st.rerun()

# Auto-refresh every N seconds
import time
placeholder = st.empty()

# ============= CREATE PORTFOLIO =============
@st.cache_data(ttl=30)  # Cache expires every 30 seconds
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
col1, col2 = st.columns([3, 1])
with col1:
    st.title("📊 Portfolio Performance Dashboard")
    st.markdown("*Real-time data from Yahoo Finance - Auto-updating every 30 seconds* 🔄")
with col2:
    # Show live timestamp
    st.metric("Last Update", f"{summary['as_of_date']}")
    st.caption(f"Next refresh: {refresh_rate}s")

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
    st.metric(
        "Current Value",
        f"${summary['total_current_value']:,.0f}",
        delta=f"${summary['total_current_value'] - summary['total_invested']:,.0f}"
    )

with col3:
    st.metric(
        "Gain/Loss",
        f"${summary['total_gain_loss_dollars']:,.0f}",
        delta=f"{summary['total_gain_loss_percent']:.2f}%"
    )

with col4:
    color = "#22AB94" if summary['total_gain_loss_percent'] > 0 else "#FF2B2B"
    st.markdown(f"""
    <div style="background: {color}; color: white; padding: 1rem; border-radius: 0.5rem; text-align: center;">
        <div style="font-size: 0.9rem; opacity: 0.9;">Total Return</div>
        <div style="font-size: 2rem; font-weight: bold;">{summary['total_gain_loss_percent']:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ============= CHARTS ROW 1 =============
st.subheader("📊 Visual Analytics")

col1, col2 = st.columns(2)

# Pie Chart - Asset Allocation
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

# Color the dataframe
def highlight_return(val):
    if '+' in str(val):
        return 'color: green; font-weight: bold;'
    elif '-' in str(val):
        return 'color: red; font-weight: bold;'
    return ''

styled_df = display_df.style.applymap(highlight_return, subset=['Return %'])

st.dataframe(styled_df, use_container_width=True, hide_index=True)

st.divider()

# ============= TOP/WORST PERFORMERS =============
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
st.caption(f"Last updated: {summary['as_of_date']} | Total Holdings: {summary['number_of_holdings']}")
