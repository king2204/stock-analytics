"""Fetch real-time and historical stock data from Yahoo Finance."""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


class StockDataFetcher:
    """Fetch stock market data using Yahoo Finance."""
    
    @staticmethod
    def get_current_price(symbol: str) -> float:
        """
        Get current stock price.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Current price as float
        """
        ticker = yf.Ticker(symbol)
        data = ticker.history(period='1d')
        if len(data) > 0:
            return data['Close'].iloc[-1]
        return None
    
    @staticmethod
    def get_price_history(symbol: str, days: int = 90) -> pd.DataFrame:
        """
        Get historical price data.
        
        Args:
            symbol: Stock ticker symbol
            days: Number of days of history to fetch
            
        Returns:
            DataFrame with Date, Close, High, Low, Volume
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        data = yf.download(symbol, start=start_date.strftime('%Y-%m-%d'), 
                          end=end_date.strftime('%Y-%m-%d'), progress=False)
        data['Symbol'] = symbol
        return data
    
    @staticmethod
    def get_multiple_prices(symbols: list) -> pd.DataFrame:
        """
        Get current prices for multiple stocks.
        
        Args:
            symbols: List of stock ticker symbols
            
        Returns:
            DataFrame with Symbol and Price columns
        """
        prices = []
        for symbol in symbols:
            price = StockDataFetcher.get_current_price(symbol)
            if price is not None:
                prices.append({'Symbol': symbol, 'Price': price})
        
        return pd.DataFrame(prices)
    
    @staticmethod
    def get_stock_info(symbol: str) -> dict:
        """
        Get basic stock information.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with stock info
        """
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            'symbol': symbol,
            'name': info.get('longName', 'N/A'),
            'sector': info.get('sector', 'N/A'),
            'market_cap': info.get('marketCap', 'N/A'),
            'pe_ratio': info.get('trailingPE', 'N/A')
        }
