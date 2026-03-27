# Portfolio Performance Dashboard

A Python-based data analytics project for analyzing stock portfolio performance using real-time market data.

## Features

- Fetch real-time stock prices from Yahoo Finance
- Calculate portfolio performance metrics
- Analyze asset allocation
- Generate performance reports
- Visualize portfolio trends

## Project Structure

```
.
├── src/
│   ├── __init__.py
│   ├── portfolio.py          # Portfolio data model
│   ├── data_fetcher.py       # Yahoo Finance API integration
│   ├── analyzer.py           # Portfolio analysis functions
│   └── reporter.py           # Report generation
├── data/
│   └── sample_portfolio.csv  # Sample data
├── notebooks/
│   └── analysis.ipynb        # Jupyter notebooks for exploration
├── requirements.txt          # Python dependencies
└── README.md
```

## Getting Started

1. **Clone or create the project**
2. **Create virtual environment**: `python -m venv venv`
3. **Activate**: `source venv/bin/activate` (macOS/Linux)
4. **Install dependencies**: `pip install -r requirements.txt`
5. **Run analysis**: `python main.py`

## Data Source

- Yahoo Finance API (via `yfinance` library)
- Stock price data: Historical and real-time
- No API key required for basic usage
