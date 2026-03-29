# Technical Architecture

Comprehensive technical documentation for the Portfolio Performance Dashboard.

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Streamlit Web Interface                   │
│  (streamlit_advanced.py)                                    │
│                                                              │
│  ┌──────────────────────┬───────────────────────────────┐   │
│  │  Dashboard Tab       │  Simulator Tab                │   │
│  │  (Real-time)         │  (What-if Analysis)           │   │
│  │                      │                               │   │
│  │  ├─ Live Metrics     │  ├─ DCA Configuration        │   │
│  │  ├─ 8 Charts         │  ├─ Run Simulation           │   │
│  │  ├─ Risk Analytics   │  ├─ View Results             │   │
│  │  └─ Toggles/Period   │  └─ Compare vs Actual        │   │
│  └──────────────────────┴───────────────────────────────┘   │
│                                                              │
│  Sidebar: Live Status, Controls, Toggles                    │
└─────────────────────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌─────────────────┐  ┌──────────────────┐  ┌──────────────┐
│ PortfolioAnalyzer│  │ DCASimulator     │  │  Portfolio   │
│ (analyzer.py)    │  │ (simulator.py)   │  │ (portfolio.py)
│                  │  │                  │  │              │
│ • fetch_prices() │  │ • simulate_dca() │  │ • holdings   │
│ • calc_risk()    │  │ • backtest()     │  │ • add_holding│
│ • calc_corr()    │  │ • compare()      │  │              │
│ • performance()  │  │                  │  │              │
└────────┬─────────┘  └──────────┬───────┘  └──────────────┘
         │                       │
         └───────────┬───────────┘
                     │
        ┌────────────┴────────────┐
        │   StockDataFetcher      │
        │ (data_fetcher.py)       │
        │                         │
        │ • get_current_prices()  │
        │ • get_price_history()   │
        │ • get_multiple_prices() │
        └────────────┬────────────┘
                     │
        ┌────────────┴────────────┐
        │   Yahoo Finance API     │
        │   (via yfinance)        │
        │                         │
        │ - Real-time prices      │
        │ - Historical data (3y+) │
        │ - No API key required   │
        └────────────────────────┘
```

---

## Module Details

### 1. **portfolio.py** - Data Model

**Purpose**: Represents a stock portfolio with holdings.

**Class: Portfolio**

```python
class Portfolio:
    def __init__(self, name: str)
    def add_holding(symbol, shares, purchase_price, purchase_date)
    def remove_holding(symbol)
    def get_symbols() -> list
    def save_to_csv(filepath)

    # Attributes
    self.holdings: pd.DataFrame  # [(symbol, shares, purchase_price, purchase_date)]
```

**Data Structure**:
```
DataFrame columns:
- symbol (str)           : Stock ticker (AAPL, MSFT, etc.)
- shares (int)           : Number of shares owned
- purchase_price (float) : Price paid per share
- purchase_date (str)    : Date of purchase (YYYY-MM-DD)
```

**Use Case**: Stores static portfolio configuration, immutable except add/remove.

---

### 2. **data_fetcher.py** - Yahoo Finance Integration

**Purpose**: Fetches real-time and historical stock data.

**Class: StockDataFetcher** (static methods)

```python
class StockDataFetcher:
    @staticmethod
    get_current_price(symbol: str) -> float

    @staticmethod
    get_price_history(symbol: str, days: int = 90) -> pd.DataFrame
    # Returns: DataFrame with Date, Close, High, Low, Volume

    @staticmethod
    get_multiple_prices(symbols: list) -> pd.DataFrame
    # Returns: DataFrame with Symbol, Price for each stock
```

**Key Features**:
- Uses **yfinance** library (https://github.com/ranaroussi/yfinance)
- No API key required (public data)
- Caches automatically via yfinance
- Returns Pandas DataFrames directly

**Sample Output**:
```
get_price_history("AAPL", days=7):
           Date   Close    High     Low    Volume
0  2026-03-29   189.45  190.12  188.90  52300000
1  2026-03-26   188.20  189.30  187.50  48100000
...
```

---

### 3. **analyzer.py** - Core Analytics Engine

**Purpose**: Calculates all portfolio metrics and analytics.

**Class: PortfolioAnalyzer**

```python
class PortfolioAnalyzer:
    def __init__(self, portfolio: Portfolio)

    # Fetch data
    def fetch_current_prices() -> dict

    # Calculate metrics
    def calculate_current_value() -> pd.DataFrame
    def calculate_portfolio_summary() -> dict
    def calculate_asset_allocation() -> pd.DataFrame
    def calculate_volatility(symbol: str, days: int) -> float
    def calculate_correlation_matrix(symbols, days) -> pd.DataFrame
    def calculate_risk_metrics(symbols, days) -> pd.DataFrame

    # Performance
    def get_best_performers(top_n: int) -> pd.DataFrame
    def get_worst_performers(bottom_n: int) -> pd.DataFrame
```

**Key Calculations**:

**1. Portfolio Summary**
```python
total_invested = sum(shares * purchase_price)
total_current = sum(current_price * shares)
gain_loss_$ = total_current - total_invested
gain_loss_% = (gain_loss_$ / total_invested) * 100
```

**2. Volatility (Annualized)**
```python
returns = price.pct_change()  # Daily percent changes
volatility = returns.std() * sqrt(252)  # 252 = trading days/year
```

**3. Sharpe Ratio**
```python
# Assuming 0% risk-free rate
sharpe = (returns.mean() / returns.std()) * sqrt(252)
# Higher = better risk-adjusted returns
```

**4. Max Drawdown**
```python
cumulative_max = price.cummax()
drawdown = (cumulative_max - price) / cumulative_max
max_drawdown = drawdown.max()
```

**5. Correlation Matrix**
```python
corr = prices[symbols].corr()  # Pearson correlation
# Range: -1 (perfect negative) to +1 (perfect positive)
# 0 = no correlation
```

---

### 4. **simulator.py** - DCA Backtesting Engine (NEW)

**Purpose**: Simulates dollar-cost averaging strategy over historical periods.

**Class: DCASimulator**

```python
class DCASimulator:
    def simulate_dca(
        symbols: list,           # ["AAPL", "MSFT", "GOOGL", "AMZN"]
        start_date: str,         # "2023-01-01"
        end_date: str,           # "2026-03-29"
        monthly_amount: float,   # 500.0 ($500/month)
        allocation: dict,        # {"AAPL": 0.25, "MSFT": 0.25, ...}
        purchase_day: int = 1    # 1st of each month
    ) -> dict
```

**Algorithm**:
1. For each month from start_date to end_date:
   - Get closing price on purchase_day (or nearest trading day)
   - For each stock:
     - Calculate $amount = monthly_amount × allocation%
     - Calculate shares = $amount / price
     - Add shares to cumulative holdings
   - Record portfolio_value using daily prices

2. Return dict with:
   - total_invested
   - final_value
   - gain_loss
   - gain_loss_percent
   - holdings_final
   - monthly_data (array for charting)

**Example Execution**:
```
Input: $500/month for 36 months (3 years)
Output:
- Total Invested: $18,000
- Final Portfolio: $19,247
- Gain/Loss: +$1,247 (+6.9%)
```

---

### 5. **streamlit_advanced.py** - UI Orchestration

**Purpose**: Web interface with real-time dashboard and simulator.

**Structure**:
```
Page Config
├─ Sidebar
│  ├─ Live Status (Bangkok time)
│  ├─ Dashboard Controls
│  │  ├─ Period Selection (7/30/90 days)
│  │  ├─ Refresh Interval (10-300 sec)
│  │  └─ Chart Toggles (8 charts)
│  └─ Manual Refresh Button
│
└─ Tabs
   ├─ Tab 1: Dashboard
   │  ├─ Header + KPI Metrics
   │  ├─ 8 Interactive Charts (Plotly)
   │  ├─ Risk Analytics
   │  ├─ Correlation Heatmap
   │  └─ Holdings Table + Top/Worst
   │
   └─ Tab 2: Simulator
      ├─ Input Controls
      ├─ Simulation Results
      ├─ Growth Chart
      ├─ Holdings Breakdown
      └─ Actual vs Simulated Comparison
```

**Key Functions**:
- `load_data()` - Initialize portfolio with holdings
- `get_analyzer()` - Create analyzer and fetch real-time prices
- Chart rendering functions (Plotly)
- Simulator integration

---

## Data Flow

### Dashboard Tab (Real-Time)

```
User Opens App
     ↓
load_data() → Portfolio with 4 holdings
     ↓
get_analyzer() → PortfolioAnalyzer
     ↓
fetch_current_prices() → Yahoo Finance
     ↓
Render Dashboard:
  ├─ calculate_portfolio_summary() → KPI Metrics
  ├─ calculate_current_value() → Holdings Table
  ├─ calculate_asset_allocation() → Pie Chart
  ├─ calculate_risk_metrics() → Risk Charts
  ├─ calculate_correlation_matrix() → Heatmap
  └─ Performance calculations → Bar Charts
     ↓
Auto-refresh every N seconds (sidebar slider)
```

### Simulator Tab (Historical)

```
User Inputs:
  - Start Date
  - End Date
  - Monthly Amount
  - Allocation
     ↓
Click "Run Simulation"
     ↓
DCASimulator.simulate_dca()
  ├─ Fetch historical prices via StockDataFetcher
  ├─ Loop: For each month from start to end
  │   ├─ Get price on purchase_day
  │   ├─ Calculate shares: amount / price
  │   ├─ Accumulate holdings
  │   └─ Record portfolio_value
  └─ Return monthly progression
     ↓
Render Results:
  ├─ Key Metrics (invested, final value, gain)
  ├─ Growth Chart (line + fill)
  ├─ Holdings Breakdown (table + pie)
  └─ Comparison vs Actual Portfolio
```

---

## Performance Considerations

### Data Caching

```python
@st.cache_data(ttl=0)
def load_data():
    # Always fresh, no caching
    # ttl=0 = cache never expires but is always checked
```

**Strategy**: No caching (ttl=0) ensures always-fresh real-time data.

### API Calls

- **Current Prices**: 1 call per page refresh
- **Price History**: 1 call per stock per risk analysis
- **Rate Limiting**: yfinance handles transparently
- **Typical Page Load**: 2-4 Yahoo Finance calls

### Time Complexity

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| Asset Allocation | O(n) | n = holdings |
| Risk Metrics | O(n·m) | n = holdings, m = days |
| Correlation | O(n²) | n = holdings |
| Simulator | O(m·n) | m = months, n = stocks |

---

## Error Handling & Validation

### Network Errors
```python
try:
    prices = analyzer.fetch_current_prices()
except Exception as e:
    st.error(f"Failed to fetch prices: {e}")
```

### Data Validation
```python
if len(hist) < 2:
    # Need at least 2 data points
    return pd.DataFrame()

if allocation_sum != 1.0:
    # Allocation must sum to 100%
    st.error("Allocation must sum to 100%")
```

### Edge Cases Handled
- Weekend/holiday (no trading) → nearest trading day
- Insufficient historical data → graceful fallback
- NaN values in correlations → skip, handle dropna()
- Zero risk metrics → return 0, don't divide by zero

---

## Period-Based Analysis

Selected period (7/30/90 days) affects:

| Metric | Impact |
|--------|--------|
| Risk Analysis | Recalculates volatility, Sharpe, max-DD |
| Correlation | Recalculates using selected period's data |
| Holdings Table | Uses full data (not affected by period) |

```python
selected_days = period_map[time_option]  # 7, 30, or 90
risk_metrics = analyzer.calculate_risk_metrics(days=selected_days)
```

---

## Scaling & Future Enhancements

### Current Limitations
- 4 hardcoded stocks (AAPL, MSFT, GOOGL, AMZN)
- Single user only (no auth)
- Portfolio stored in code, not database
- No dividend calculation

### Scale to Production
1. **Database**: Store portfolios in PostgreSQL
2. **Authentication**: Add user login
3. **API**: Create REST API for portfolio CRUD
4. **Worker Jobs**: Background job for nightly risk calculations
5. **Caching**: Redis for price cache
6. **Monitoring**: Prometheus metrics, alerts

### Potential Features
- Dividend yield calculation
- Tax-loss harvesting analysis
- Portfolio backtesting vs benchmarks
- ML-based anomaly detection
- Multi-user support with shared portfolios
- Mobile app via React Native
- Real-time alerts/notifications

---

## Code Quality

### Testing Approach
- **Unit Tests**: Test each module independently
- **Integration Tests**: Test Analyzer + DataFetcher
- **Edge Cases**: Weekends, holidays, missing data

### Linting
```bash
black src/              # Format code
flake8 src/             # Check style
mypy src/               # Type checking
```

### Documentation
- Docstrings for public functions
- Type hints on parameters
- Comments for complex logic
- README + ARCHITECTURE + DEPLOYMENT guides

---

## Security Considerations

- **No Secrets in Code**: All publicly available Yahoo Finance data
- **HTTPS in Production**: Streamlit Cloud handles SSL
- **.gitignore**: Never commit .streamlit/secrets.toml
- **No SQL Injection**: yfinance handles safely
- **No XSS**: Streamlit sanitizes all outputs

---

## Debugging Tips

### Enable Verbose Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test Simulator Locally
```python
from src.simulator import DCASimulator

simulator = DCASimulator()
result = simulator.simulate_dca(
    symbols=["AAPL", "MSFT", "GOOGL", "AMZN"],
    start_date="2023-01-01",
    end_date="2026-03-29",
    monthly_amount=500.0,
    allocation={"AAPL": 0.25, "MSFT": 0.25, "GOOGL": 0.25, "AMZN": 0.25}
)
print(result)
```

---

## Deployment Architecture

### Streamlit Cloud
```
GitHub Repo
     ↓
Streamlit Cloud Hooks
     ↓
Clone Repo
     ↓
pip install -r requirements_streamlit.txt
     ↓
streamlit run streamlit_advanced.py
     ↓
Available at: https://share.streamlit.io/...
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for full deployment guide.

---

## References

- [Streamlit Docs](https://docs.streamlit.io/)
- [Plotly Charts](https://plotly.com/python/)
- [yfinance GitHub](https://github.com/ranaroussi/yfinance)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [SciPy Reference](https://docs.scipy.org/)
