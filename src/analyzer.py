"""การวิเคราะห์พอร์ตโฟลิโอและคำนวณประสิทธิผล"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.data_fetcher import StockDataFetcher
from src.portfolio import Portfolio
from scipy import stats


class PortfolioAnalyzer:
    """วิเคราะห์ประสิทธิภาพและตัวชี้วัดของพอร์ตโฟลิโอ"""

    def __init__(self, portfolio: Portfolio):
        """
        เริ่มต้นการวิเคราะห์

        Args:
            portfolio: วัตถุ Portfolio ที่จะวิเคราะห์
        """
        self.portfolio = portfolio
        self.current_prices = None

    def fetch_current_prices(self):
        """ดึงราคาปัจจุบันของการถือครองทั้งหมด"""
        symbols = self.portfolio.get_symbols()
        if symbols:
            price_data = StockDataFetcher.get_multiple_prices(symbols)
            self.current_prices = price_data.set_index('Symbol')['Price'].to_dict()
        return self.current_prices

    def calculate_current_value(self) -> pd.DataFrame:
        """
        คำนวณมูลค่าปัจจุบันของการถือครองแต่ละครั้ง

        Returns:
            DataFrame ที่มีการถือครองและมูลค่าปัจจุบัน
        """
        if self.current_prices is None:
            self.fetch_current_prices()

        holdings = self.portfolio.holdings.copy()
        holdings['current_price'] = holdings['symbol'].map(self.current_prices)
        holdings['current_value'] = holdings['shares'] * holdings['current_price']
        holdings['gain_loss_dollars'] = holdings['current_value'] - (holdings['shares'] * holdings['purchase_price'])
        holdings['gain_loss_percent'] = (holdings['gain_loss_dollars'] / (holdings['shares'] * holdings['purchase_price'])) * 100

        # รับประกันว่าคอลัมน์ตัวเลขมี dtype ที่ถูกต้อง
        holdings['current_price'] = pd.to_numeric(holdings['current_price'], errors='coerce')
        holdings['current_value'] = pd.to_numeric(holdings['current_value'], errors='coerce')
        holdings['gain_loss_dollars'] = pd.to_numeric(holdings['gain_loss_dollars'], errors='coerce')
        holdings['gain_loss_percent'] = pd.to_numeric(holdings['gain_loss_percent'], errors='coerce')

        return holdings

    def calculate_portfolio_summary(self) -> dict:
        """
        คำนวณตัวชี้วัดสรุปของพอร์ตโฟลิโอขั้นประถมศึกษา

        Returns:
            พจนานุกรมที่มีตัวชี้วัดพอร์ตโฟลิโอ
        """
        holdings = self.calculate_current_value()

        total_invested = (holdings['shares'] * holdings['purchase_price']).sum()
        total_current = holdings['current_value'].sum()
        total_gain_loss = total_current - total_invested
        total_gain_loss_percent = (total_gain_loss / total_invested) * 100 if total_invested > 0 else 0

        return {
            'portfolio_name': self.portfolio.name,
            'total_invested': round(total_invested, 2),
            'total_current_value': round(total_current, 2),
            'total_gain_loss_dollars': round(total_gain_loss, 2),
            'total_gain_loss_percent': round(total_gain_loss_percent, 2),
            'number_of_holdings': len(holdings),
            'as_of_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def calculate_asset_allocation(self) -> pd.DataFrame:
        """
        คำนวณเปอร์เซ็นต์การจัดสรรสินทรัพย์

        Returns:
            DataFrame ที่มีเปอร์เซ็นต์การจัดสรร
        """
        holdings = self.calculate_current_value()
        total_value = holdings['current_value'].sum()

        allocation = holdings[['symbol', 'current_value']].copy()
        allocation['allocation_percent'] = (allocation['current_value'] / total_value * 100).round(2)
        allocation = allocation.sort_values('allocation_percent', ascending=False)

        return allocation

    def get_best_performers(self, top_n: int = 5) -> pd.DataFrame:
        """
        ดึงการถือครองที่มีประสิทธิภาพดีที่สุด

        Args:
            top_n: Number of top performers to return
            
        Returns:
            DataFrame sorted by gain/loss percent
        """
        holdings = self.calculate_current_value()
        return holdings.nlargest(top_n, 'gain_loss_percent')[['symbol', 'gain_loss_percent', 'gain_loss_dollars']]
    
    def get_worst_performers(self, bottom_n: int = 5) -> pd.DataFrame:
        """
        Get worst performing holdings.

        Args:
            bottom_n: Number of worst performers to return

        Returns:
            DataFrame sorted by gain/loss percent
        """
        holdings = self.calculate_current_value()
        return holdings.nsmallest(bottom_n, 'gain_loss_percent')[['symbol', 'gain_loss_percent', 'gain_loss_dollars']]

    def get_price_history(self, symbols: list = None, days: int = 180) -> pd.DataFrame:
        """
        Get historical price data for all holdings or specified symbols.

        Args:
            symbols: List of symbols (None = all holdings)
            days: Number of days of history

        Returns:
            DataFrame with price history
        """
        if symbols is None:
            symbols = self.portfolio.get_symbols()

        price_data = []
        for symbol in symbols:
            hist = StockDataFetcher.get_price_history(symbol, days=days)
            hist['Symbol'] = symbol
            price_data.append(hist[['Close', 'Symbol']].reset_index())

        return pd.concat(price_data, ignore_index=True) if price_data else pd.DataFrame()

    def calculate_volatility(self, symbol: str, days: int = 180) -> float:
        """Calculate annualized volatility for a stock."""
        hist = StockDataFetcher.get_price_history(symbol, days=days)
        returns = hist['Close'].pct_change().dropna()
        return returns.std() * np.sqrt(252)

    def calculate_correlation_matrix(self, symbols: list = None, days: int = 180) -> pd.DataFrame:
        """Calculate correlation matrix between stocks."""
        if symbols is None:
            symbols = self.portfolio.get_symbols()

        price_data = []
        for symbol in symbols:
            hist = StockDataFetcher.get_price_history(symbol, days=days)
            if len(hist) > 1:  # Need at least 2 data points
                df_temp = hist[['Close']].copy()
                df_temp.columns = [symbol]
                df_temp = df_temp.reset_index(drop=True)
                price_data.append(df_temp)

        if len(price_data) == 0:
            return pd.DataFrame()

        # Concatenate all series by index position
        df = pd.concat(price_data, axis=1)
        
        # Handle rows with NaN values (when series lengths differ)
        df = df.dropna()
        
        if len(df) < 2:
            return pd.DataFrame()
        
        return df.corr()

    def calculate_risk_metrics(self, symbols: list = None, days: int = 180) -> pd.DataFrame:
        """Calculate comprehensive risk metrics."""
        if symbols is None:
            symbols = self.portfolio.get_symbols()

        metrics = []
        for symbol in symbols:
            try:
                hist = StockDataFetcher.get_price_history(symbol, days=days)
                if len(hist) < 2:
                    continue

                returns = hist['Close'].pct_change().dropna()
                if len(returns) == 0:
                    continue

                std_dev = float(returns.std())
                volatility = std_dev * np.sqrt(252) if std_dev > 0 else 0
                sharpe = (float(returns.mean()) / std_dev * np.sqrt(252)) if std_dev > 0 else 0
                max_dd = float((hist['Close'].cummax() - hist['Close']).max() / hist['Close'].cummax().max())

                metrics.append({
                    'symbol': symbol,
                    'volatility': volatility,
                    'sharpe_ratio': sharpe,
                    'max_drawdown': max_dd,
                    'avg_return': float(returns.mean()) * 252
                })
            except Exception as e:
                continue

        return pd.DataFrame(metrics) if metrics else pd.DataFrame()
