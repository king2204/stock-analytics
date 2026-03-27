"""Advanced Tableau-style Portfolio Dashboard - Real-time with Auto-Refresh."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np
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

# ============= SIDEBAR - LIVE STATUS FIRST =============
st.sidebar.markdown("**⏰ Live Status**")

# Real-time clock with JavaScript
st.sidebar.markdown("""
<div id="live-time" style="font-size: 24px; font-weight: bold; color: #1f77b4; margin: 10px 0;">
  Last Update: <span id="current-time">00:00:00</span>
</div>
<script>
function updateTime() {
  const now = new Date();
  const timeString = now.toLocaleTimeString('en-US', { hour12: false });
  document.getElementById('current-time').textContent = timeString;
}
updateTime();
setInterval(updateTime, 1000);
</script>
""", unsafe_allow_html=True)

st.sidebar.caption("🟢 LIVE UPDATE")

st.sidebar.markdown("---")
st.sidebar.title("⚙️ Dashboard Controls")

time_option = st.sidebar.selectbox(
    "📅 Select Period",
    ["7 Days", "30 Days", "90 Days"],
    index=1
)

# Convert time option to days
period_map = {"7 Days": 7, "30 Days": 30, "90 Days": 90}
selected_days = period_map[time_option]

refresh_interval = st.sidebar.slider("🔄 Refresh (sec)", 10, 300, 30, 10)

if st.sidebar.button("🔄 Refresh", use_container_width=True):
    st.rerun()

st.sidebar.markdown("---")

# Chart toggles
st.sidebar.markdown("---")
st.sidebar.markdown("**📊 Chart Display Options**")

# Main charts
show_allocation = st.sidebar.checkbox("🥧 Asset Allocation", True)
show_performance = st.sidebar.checkbox("📈 Performance (%)", True)
show_current_value = st.sidebar.checkbox("💰 Current Value", True)
show_gain_loss = st.sidebar.checkbox("💵 Gain/Loss ($)", True)

# Analysis charts
show_correlation = st.sidebar.checkbox("🔗 Correlation", True)
show_risk = st.sidebar.checkbox("⚠️ Risk Analysis", True)
show_invested = st.sidebar.checkbox("📊 Invested vs Current", True)
show_concentration = st.sidebar.checkbox("🎯 Concentration", True)


# ============= AUTO REFRESH - REAL-TIME LIKE YAHOO FINANCE =============
st.markdown(f"""
<meta http-equiv="refresh" content="{refresh_interval}">
""", unsafe_allow_html=True)

# ============= CUSTOM STYLING =============
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 0.75rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    h1 { color: #1f2937; margin-bottom: 0.5rem; }
    h2 { color: #1f77b4; margin-top: 1.5rem; margin-bottom: 1rem; }
    </style>
""", unsafe_allow_html=True)

# ============= LOAD DATA =============
@st.cache_data(ttl=0)
def load_data():
    """Load portfolio with historical purchase data."""
    portfolio = Portfolio("My Stock Portfolio")
    portfolio.add_holding("AAPL", 10, 150.00, "2023-01-15")
    portfolio.add_holding("MSFT", 5, 300.00, "2023-03-20")
    portfolio.add_holding("GOOGL", 3, 2800.00, "2023-06-10")
    portfolio.add_holding("AMZN", 2, 3200.00, "2023-08-05")
    return portfolio

def get_analyzer(portfolio):
    """Create analyzer and fetch real-time prices."""
    analyzer = PortfolioAnalyzer(portfolio)
    try:
        prices = analyzer.fetch_current_prices()
        if prices is None or len(prices) == 0:
            st.error("❌ Failed to fetch prices from Yahoo Finance. Check internet connection.")
            return None
        st.success(f"✅ Fetched {len(prices)} stocks from Yahoo Finance")
        return analyzer
    except Exception as e:
        st.error(f"❌ Error: {str(e)[:100]}")
        return None

portfolio = load_data()
analyzer = get_analyzer(portfolio)

if analyzer is None:
    st.stop()

try:
    summary = analyzer.calculate_portfolio_summary()
    holdings = analyzer.calculate_current_value()
    allocation = analyzer.calculate_asset_allocation()
    is_real_time = True
except Exception as e:
    st.warning(f"⚠️ Error: {str(e)[:100]}")
    is_real_time = False
    summary = {"total_current_value": 0, "total_invested": 0, "total_gain_loss_dollars": 0,
               "total_gain_loss_percent": 0, "number_of_holdings": 0, "as_of_date": "Error"}
    holdings = pd.DataFrame()
    allocation = pd.DataFrame()

# ============= HEADER =============
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    st.title("📊 Portfolio Dashboard")
    st.markdown(f"🔄 **Real-time** - Auto-refresh every {refresh_interval} seconds (like Yahoo Finance)")

with col2:
    st.metric("Portfolio Value", f"${summary['total_current_value']:,.0f}",
              f"${summary['total_gain_loss_dollars']:,.0f}")

with col3:
    st.metric("Portfolio Value Change", f"{summary['total_gain_loss_percent']:.2f}%")

st.divider()

# ============= KPI CARDS =============
st.subheader("📈 Key Metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    color = "🟢" if summary['total_gain_loss_percent'] > 0 else "🔴"
    st.metric("Total Return", f"{color} {summary['total_gain_loss_percent']:.2f}%")

with col2:
    st.metric("Total Invested", f"${summary['total_invested']:,.0f}")

with col3:
    if len(holdings) > 0:
        best = analyzer.get_best_performers(1)
        if len(best) > 0:
            st.metric("🏆 Best", f"{best.iloc[0]['symbol']}", f"+{best.iloc[0]['gain_loss_percent']:.1f}%")

with col4:
    if len(holdings) > 0:
        worst = analyzer.get_worst_performers(1)
        if len(worst) > 0:
            st.metric("📉 Worst", f"{worst.iloc[0]['symbol']}", f"{worst.iloc[0]['gain_loss_percent']:.1f}%")

st.divider()

# ============= MAIN CHARTS =============
if is_real_time and len(holdings) > 0:
    st.subheader("📊 Visual Analytics")

    col1, col2 = st.columns(2)

    # Pie Chart - Asset Allocation
    if show_allocation:
        with col1:
            fig_pie = go.Figure(data=[go.Pie(
                labels=allocation['symbol'],
                values=allocation['current_value'],
                textposition='inside',
                textinfo='label+percent',
                marker=dict(colors=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']),
                hovertemplate='<b>%{label}</b><br>$%{value:,.0f}<extra></extra>'
            )])
            fig_pie.update_layout(
                title="Asset Allocation",
                height=450,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    # Performance Bar - By Stock %
    if show_performance:
        col_perf = col2 if show_allocation else col1
        with col_perf:
            colors = ['#2ca02c' if x > 0 else '#d62728' for x in holdings['gain_loss_percent']]
            fig_bar = go.Figure(data=[go.Bar(
                x=holdings['symbol'],
                y=holdings['gain_loss_percent'],
                marker=dict(color=colors),
                text=[f"{x:.1f}%" for x in holdings['gain_loss_percent']],
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>%{y:.2f}%<extra></extra>'
            )])
            fig_bar.update_layout(
                title="Performance by Stock (%)",
                xaxis_title="Stock",
                yaxis_title="Return %",
                height=450,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            fig_bar.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_bar, use_container_width=True)

    if show_allocation or show_performance:
        st.divider()

    col1, col2 = st.columns(2)

    # Current Value Chart
    if show_current_value:
        with col1:
            fig_val = go.Figure(data=[go.Bar(
                x=holdings['symbol'],
                y=holdings['current_value'],
                marker=dict(color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']),
                text=[f"${x:,.0f}" for x in holdings['current_value']],
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>$%{y:,.0f}<extra></extra>'
            )])
            fig_val.update_layout(
                title="Current Value by Stock",
                xaxis_title="Stock",
                yaxis_title="Value ($)",
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_val, use_container_width=True)

    # Gain/Loss Chart
    if show_gain_loss:
        with col2:
            colors = ['#2ca02c' if x > 0 else '#d62728' for x in holdings['gain_loss_dollars']]
            fig_gl = go.Figure(data=[go.Bar(
                x=holdings['symbol'],
                y=holdings['gain_loss_dollars'],
                marker=dict(color=colors),
                text=[f"${x:,.0f}" for x in holdings['gain_loss_dollars']],
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>$%{y:,.0f}<extra></extra>'
            )])
            fig_gl.update_layout(
                title="Gain/Loss by Stock ($)",
                xaxis_title="Stock",
                yaxis_title="Gain/Loss ($)",
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            fig_gl.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_gl, use_container_width=True)

    if show_current_value or show_gain_loss:
        st.divider()

    # Invested vs Current Value
    if show_invested:
        col1, col2 = st.columns(2)
        with col1:
            invested = holdings['shares'] * holdings['purchase_price']
            fig_comp = go.Figure(data=[
                go.Bar(x=holdings['symbol'], y=invested,
                       name='Invested', marker=dict(color='#1f77b4')),
                go.Bar(x=holdings['symbol'], y=holdings['current_value'],
                       name='Current', marker=dict(color='#ff7f0e'))
            ])
            fig_comp.update_layout(
                title="Invested vs Current Value",
                xaxis_title="Stock",
                yaxis_title="Value ($)",
                barmode='group',
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_comp, use_container_width=True)

        # Concentration chart
        if show_concentration:
            with col2:
                concentration = (holdings['current_value'] / summary['total_current_value'] * 100)
                colors_conc = ['#d62728' if x > 30 else '#ff7f0e' if x > 20 else '#2ca02c'
                              for x in concentration]
                fig_conc = go.Figure(data=[go.Bar(
                    x=holdings['symbol'],
                    y=concentration,
                    marker=dict(color=colors_conc),
                    text=[f"{x:.1f}%" for x in concentration],
                    textposition='outside',
                    hovertemplate='<b>%{x}</b><br>%{y:.1f}% of portfolio<extra></extra>'
                )])
                fig_conc.update_layout(
                    title="Portfolio Concentration",
                    xaxis_title="Stock",
                    yaxis_title="% of Portfolio",
                    height=400,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                fig_conc.add_hline(y=20, line_dash="dash", line_color="orange",
                                  annotation_text="20% threshold", annotation_position="right")
                st.plotly_chart(fig_conc, use_container_width=True)

        if show_concentration:
            st.divider()
else:
    st.error("❌ Unable to fetch real-time data. Please check your internet connection.")

st.divider()

# ============= RISK ANALYTICS =============
if show_risk and is_real_time:
    st.subheader(f"⚠️ Risk Analytics ({time_option})")

    try:
        risk_metrics = analyzer.calculate_risk_metrics(days=selected_days)

        col1, col2 = st.columns(2)

        with col1:
            fig_vol = go.Figure(data=[go.Bar(
                x=risk_metrics['symbol'],
                y=risk_metrics['volatility'],
                marker=dict(color='#ff7f0e'),
                text=[f"{x:.1%}" for x in risk_metrics['volatility']],
                textposition='outside'
            )])
            fig_vol.update_layout(
                title=f"Annualized Volatility ({time_option})",
                height=350,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_vol, use_container_width=True)

        with col2:
            colors_sharpe = ['#2ca02c' if x > 0 else '#d62728' for x in risk_metrics['sharpe_ratio']]
            fig_sharpe = go.Figure(data=[go.Bar(
                x=risk_metrics['symbol'],
                y=risk_metrics['sharpe_ratio'],
                marker=dict(color=colors_sharpe),
                text=[f"{x:.2f}" for x in risk_metrics['sharpe_ratio']],
                textposition='outside'
            )])
            fig_sharpe.update_layout(
                title=f"Sharpe Ratio ({time_option})",
                height=350,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_sharpe, use_container_width=True)

        # Risk Summary Table
        risk_display = risk_metrics.copy()
        risk_display['volatility'] = risk_display['volatility'].apply(lambda x: f"{x:.2%}")
        risk_display['sharpe_ratio'] = risk_display['sharpe_ratio'].apply(lambda x: f"{x:.2f}")
        risk_display['max_drawdown'] = risk_display['max_drawdown'].apply(lambda x: f"{x:.2%}")

        st.dataframe(
            risk_display[['symbol', 'volatility', 'sharpe_ratio', 'max_drawdown']].rename(
                columns={'symbol': 'Stock', 'volatility': 'Volatility',
                        'sharpe_ratio': 'Sharpe', 'max_drawdown': 'Max DD'}
            ),
            use_container_width=True, hide_index=True
        )
    except Exception as e:
        st.warning(f"⚠️ Could not load risk metrics: {str(e)[:50]}")

st.divider()

# ============= CORRELATION =============
if show_correlation and is_real_time:
    st.subheader(f"🔗 Correlation Matrix ({time_option})")

    try:
        corr = analyzer.calculate_correlation_matrix(days=selected_days)

        fig_corr = go.Figure(data=go.Heatmap(
            z=corr.values,
            x=corr.columns,
            y=corr.index,
            colorscale='RdBu',
            zmid=0,
            text=np.round(corr.values, 2),
            texttemplate='%{text:.2f}',
            textfont={"size": 11}
        ))
        fig_corr.update_layout(
            title=f"Stock Correlation ({time_option})",
            height=400,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_corr, use_container_width=True)
    except Exception as e:
        st.warning(f"⚠️ Could not load correlation: {str(e)[:50]}")

st.divider()

# ============= HOLDINGS TABLE =============
if is_real_time and len(holdings) > 0:
    st.subheader("📋 Holdings Details")

    table_df = holdings[['symbol', 'shares', 'purchase_price', 'current_price', 'current_value', 'gain_loss_dollars', 'gain_loss_percent']].copy()
    display_df = table_df.copy()
    display_df.columns = ['Stock', 'Shares', 'Buy Price', 'Current Price', 'Value', 'Gain/Loss', 'Return %']
    display_df['Shares'] = display_df['Shares'].apply(lambda x: f"{x:.0f}")
    display_df['Buy Price'] = display_df['Buy Price'].apply(lambda x: f"${x:.2f}")
    display_df['Current Price'] = display_df['Current Price'].apply(lambda x: f"${x:.2f}")
    display_df['Value'] = display_df['Value'].apply(lambda x: f"${x:,.0f}")
    display_df['Gain/Loss'] = display_df['Gain/Loss'].apply(lambda x: f"${x:,.0f}")
    display_df['Return %'] = display_df['Return %'].apply(lambda x: f"{x:.2f}%")

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.divider()

    # ============= TOP/WORST =============
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏆 Top Performers")
        top = analyzer.get_best_performers(len(holdings))
        for _, row in top.iterrows():
            st.write(f"**{row['symbol']}** → 🟢 +{row['gain_loss_percent']:.2f}%")

    with col2:
        st.subheader("📉 Worst Performers")
        worst = analyzer.get_worst_performers(len(holdings))
        for _, row in worst.iterrows():
            st.write(f"**{row['symbol']}** → 🔴 {row['gain_loss_percent']:.2f}%")

    st.divider()

    # ============= FOOTER =============
    st.caption(f"📊 Last Updated: {summary['as_of_date']} | Auto-refresh: {refresh_interval}s | Holdings: {summary['number_of_holdings']}")
else:
    st.error("❌ No data to display. Fetching real-time data failed.")
