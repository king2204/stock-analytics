"""Portfolio data model and management"""

import pandas as pd
from datetime import datetime


class Portfolio:
    """Represents a stock portfolio with holdings"""

    def __init__(self, name: str):
        """
        Initialize portfolio

        Args:
            name: Portfolio name
        """
        self.name = name
        self.holdings = pd.DataFrame(columns=['symbol', 'shares', 'purchase_price', 'purchase_date']).astype({
            'symbol': 'object',
            'shares': 'int64',
            'purchase_price': 'float64',
            'purchase_date': 'object'
        })
        self.created_date = datetime.now()

    def add_holding(self, symbol: str, shares: int, purchase_price: float, purchase_date: str):
        """
        Add a stock holding to portfolio

        Args:
            symbol: Stock ticker symbol e.g., 'AAPL'
            shares: Number of shares
            purchase_price: Price per share when purchased
            purchase_date: Purchase date (format: YYYY-MM-DD)
        """
        new_holding = pd.DataFrame([{
            'symbol': symbol.upper(),
            'shares': shares,
            'purchase_price': purchase_price,
            'purchase_date': purchase_date
        }])
        self.holdings = pd.concat([self.holdings, new_holding], ignore_index=True)

    def remove_holding(self, symbol: str):
        """Remove a holding from portfolio"""
        self.holdings = self.holdings[self.holdings['symbol'] != symbol.upper()]

    def get_symbols(self) -> list:
        """Get list of stock symbols in portfolio"""
        return self.holdings['symbol'].unique().tolist()
    
    def save_to_csv(self, filepath: str):
        """Save portfolio to CSV file."""
        self.holdings.to_csv(filepath, index=False)
    
    @staticmethod
    def load_from_csv(filepath: str, name: str = "Loaded Portfolio") -> 'Portfolio':
        """Load portfolio from CSV file."""
        portfolio = Portfolio(name)
        portfolio.holdings = pd.read_csv(filepath)
        return portfolio
