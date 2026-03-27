"""Streamlit Dashboard for Portfolio Performance."""

import streamlit as st
import pandas as pd
from datetime import datetime
from src.portfolio import Portfolio
from src.analyzer import PortfolioAnalyzer
from src.reporter import PortfolioReporter

# Page config
st.set_page_config(page_title="Portfolio Dashboard", page_icon="📊", layout="wide")

# Title
st.title("📊 Stock Portfolio Performance Dashboard")
st.markdown("*Real-time data from Yahoo Finance*")

# Create portfolio
portfolio = Portfolio("My Stock Portfolio")
portfolio.add_holding("AAPL", 10, 150.00, "2023-01-15")
portfolio.add_holding("MSFT", 5, 300.00, "2023-03-20")
portfolio.add_holding("GOOGL", 3, 2800.00, "2023-06-10")
portfolio.add_holding("AMZN", 2, 3200.00, "2023-08-05")

# Analyze
analyzer = PortfolioAnalyzer(portfolio)
summary = analyzer.calculate_portfolio_summary()

# Display Summary Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Invested", f"${summary['total_invested']:,.2f}")

with col2:
    st.metric("Current Value", f"${summary['total_current_value']:,.2f}")

with col3:
    st.metric("Gain/Loss", f"${summary['total_gain_loss_dollars']:,.2f}")

with col4:
    color = "🟢" if summary['total_gain_loss_percent'] > 0 else "🔴"
    st.metric("Return", f"{color} {summary['total_gain_loss_percent']:.2f}%")

st.divider()

# Holdings Table
st.subheader("Holdings Details")
holdings = analyzer.calculate_current_value()
display_df = holdings[['symbol', 'shares', 'purchase_price', 'current_price', 'current_value', 'gain_loss_dollars', 'gain_loss_percent']].copy()
display_df.columns = ['Stock', 'Shares', 'Buy Price', 'Current Price', 'Value', 'Gain/Loss $', 'Gain/Loss %']

# Format for display
st.dataframe(
    display_df.style.format({
        'Shares': '{:.0f}',
        'Buy Price': '${:.2f}',
        'Current Price': '${:.2f}',
        'Value': '${:,.2f}',
        'Gain/Loss $': '${:,.2f}',
        'Gain/Loss %': '{:.2f}%'
    }).background_gradient(subset=['Gain/Loss %'], cmap='RdYlGn', vmin=-100, vmax=100),
    use_container_width=True
)

st.divider()

# Charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("Asset Allocation")
    allocation = analyzer.calculate_asset_allocation()
    st.bar_chart(allocation.set_index('symbol')['allocation_percent'])

with col2:
    st.subheader("Gain/Loss Performance")
    perf_df = holdings[['symbol', 'gain_loss_percent']].set_index('symbol')
    st.bar_chart(perf_df)

st.divider()

# Last Updated
st.caption(f"Last updated: {summary['as_of_date']}")
