"""Dollar-Cost Averaging (DCA) Investment Simulator"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.data_fetcher import StockDataFetcher


class DCASimulator:
    """Simulate consistent investment strategy using historical data"""

    def __init__(self):
        """Initialize DCA simulator"""
        pass

    def simulate_dca(
        self,
        symbols: list,
        start_date: str,
        end_date: str,
        monthly_amount: float,
        allocation: dict = None,
        purchase_day: int = 1
    ) -> dict:
        """
        Simulate a consistent investment strategy

        Parameters:
            symbols: List of stock symbols e.g. ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
            start_date: Start date in format 'YYYY-MM-DD'
            end_date: End date in format 'YYYY-MM-DD'
            monthly_amount: Amount to invest per month in dollars
            allocation: Dictionary mapping symbols to allocation percentages e.g. {'AAPL': 0.25, ...}
                       If None, uses equal allocation for all stocks
            purchase_day: Day of month for purchases (default: 1)

        Returns:
            Dictionary with simulation results
        """
        try:
            # If no allocation specified, use equal split for all stocks
            if allocation is None:
                allocation = {symbol: 1.0 / len(symbols) for symbol in symbols}

            # Normalize allocation to sum to 100%
            total_allocation = sum(allocation.values())
            allocation = {k: v / total_allocation for k, v in allocation.items()}

            # Convert dates to pandas Timestamp
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)

            # Fetch price history for all stocks (~10 years max)
            price_data_dict = {}
            for symbol in symbols:
                try:
                    hist = StockDataFetcher.get_price_history(symbol, days=3650)  # ~10 years
                    hist = hist.reset_index()

                    # Convert MultiIndex columns to simple strings
                    if isinstance(hist.columns, pd.MultiIndex):
                        hist.columns = [col[0] if col[1] in [symbol, ''] else f"{col[0]}_{col[1]}" for col in hist.columns]

                    # Verify Date column exists
                    if 'Date' not in hist.columns:
                       hist['Date'] = pd.to_datetime(hist.get('date', hist.get('Datetime', hist.index)))
                    else:
                        hist['Date'] = pd.to_datetime(hist['Date'])

                    hist = hist.sort_values('Date')
                    price_data_dict[symbol] = hist
                except Exception as e:
                    return self._error_response(f"Failed to fetch data for {symbol}: {str(e)[:100]}")

            # Initialize holdings and tracking data
            holdings = {symbol: 0.0 for symbol in symbols}
            monthly_data = []
            total_invested = 0.0

            # Create list of months for purchases
            current = start
            while current <= end:
                # Try to select purchase date (purchase_day of current month)
                try:
                    purchase_date = current.replace(day=purchase_day)
                except ValueError:
                    # Handle months with fewer days (e.g., Feb 30)
                    purchase_date = current

                # If purchase date is in future, skip
                if purchase_date > end:
                    break

                # Find nearest trading day
                trading_date = self._find_nearest_trading_day(purchase_date, price_data_dict)

                if trading_date is None:
                    # Move to next month safely
                    current = self._next_month(current)
                    continue

                # Purchase stocks for each symbol on this day
                for symbol in symbols:
                    price = self._get_price_at_date(trading_date, symbol, price_data_dict)
                    if price is not None and price > 0:
                        allocation_amount = monthly_amount * allocation[symbol]
                        shares_purchased = allocation_amount / price
                        holdings[symbol] += shares_purchased

                total_invested += monthly_amount

                # Calculate portfolio value on this day
                portfolio_value = self._calculate_portfolio_value(trading_date, holdings, price_data_dict)

                monthly_data.append({
                    'date': trading_date.strftime('%Y-%m-%d'),
                    'date_obj': trading_date,
                    'total_invested': round(total_invested, 2),
                    'portfolio_value': round(portfolio_value, 2),
                    'gain_loss': round(portfolio_value - total_invested, 2),
                    'holdings': {k: v for k, v in holdings.items()}
                })

                # Move to next month
                current = self._next_month(current)

            if not monthly_data:
                return self._error_response("No trading data found for selected period")

            # Get final portfolio value
            final_portfolio_value = self._calculate_portfolio_value(end, holdings, price_data_dict)
            gain_loss = final_portfolio_value - total_invested
            gain_loss_percent = (gain_loss / total_invested * 100) if total_invested > 0 else 0

            # Transform holdings to include final prices and values
            holdings_final = {}
            for symbol in symbols:
                shares = holdings[symbol]
                final_price = self._get_latest_price(symbol, price_data_dict)
                current_value = shares * final_price if final_price else 0
                holdings_final[symbol] = {
                    'shares': round(shares, 4),
                    'final_price': round(final_price, 2) if final_price else 0,
                    'current_value': round(current_value, 2)
                }

            return {
                'success': True,
                'total_invested': round(total_invested, 2),
                'final_value': round(final_portfolio_value, 2),
                'gain_loss': round(gain_loss, 2),
                'gain_loss_percent': round(gain_loss_percent, 2),
                'holdings_final': holdings_final,
                'monthly_data': monthly_data,
                'start_date': start_date,
                'end_date': end_date,
                'months_simulated': len(monthly_data)
            }

        except Exception as e:
            return self._error_response(f"Simulation error: {str(e)[:200]}")

    def _get_close_column_name(self, hist: pd.DataFrame, symbol: str):
        """Get Close price column name"""
        if 'Close' in hist.columns:
            return 'Close'
        # Fallback: look for column containing Close in name
        for col in hist.columns:
            if 'Close' in str(col).lower():
                return col
        return None

    def _next_month(self, date: pd.Timestamp) -> pd.Timestamp:
        """Move to next month safely, handling month-end dates"""
        if date.month == 12:
            return pd.Timestamp(year=date.year + 1, month=1, day=min(date.day, 31))
        else:
            # Get last day of next month
            if date.month + 1 in [4, 6, 9, 11]:
                last_day = 30
            elif date.month + 1 == 2:
                is_leap = (date.year % 4 == 0 and date.year % 100 != 0) or (date.year % 400 == 0)
                last_day = 29 if is_leap else 28
            else:
                last_day = 31

            return pd.Timestamp(year=date.year, month=date.month + 1, day=min(date.day, last_day))

    def _find_nearest_trading_day(self, target_date: pd.Timestamp, price_data_dict: dict, days_range: int = 5) -> pd.Timestamp:
        """Find the nearest trading day to the target date"""
        # Check if target date itself has data
        for symbol in price_data_dict.keys():
            hist = price_data_dict[symbol]
            if 'Date' in hist.columns:
                matching = hist[hist['Date'].dt.date == target_date.date()]
                if len(matching) > 0:
                    return target_date

        # Search within date range
        for offset in range(1, days_range + 1):
            for direction in [-1, 1]:
                check_date = target_date + timedelta(days=offset * direction)
                for symbol in price_data_dict.keys():
                    hist = price_data_dict[symbol]
                    if 'Date' in hist.columns:
                        matching = hist[hist['Date'].dt.date == check_date.date()]
                        if len(matching) > 0:
                            return check_date

        return None

    def _get_price_at_date(self, date: pd.Timestamp, symbol: str, price_data_dict: dict):
        """Get stock price at specified or nearby date"""
        hist = price_data_dict.get(symbol)
        if hist is None or len(hist) == 0 or 'Date' not in hist.columns:
            return None

        close_col = self._get_close_column_name(hist, symbol)
        if close_col is None:
            return None

        # Direct date match
        try:
            matching = hist[hist['Date'].dt.date == date.date()]
            if len(matching) > 0:
                price = matching.iloc[0][close_col]
                return float(price.item()) if hasattr(price, 'item') else float(price)
        except Exception:
            pass

        # Find nearest date within 5 days
        try:
            hist_copy = hist.copy()
            hist_copy['DateDiff'] = abs((hist_copy['Date'] - date).dt.days)
            nearest = hist_copy.nsmallest(1, 'DateDiff')

            if len(nearest) > 0:
                date_diff = nearest.iloc[0]['DateDiff']
                if date_diff <= 5:
                    price = nearest.iloc[0][close_col]
                    return float(price.item()) if hasattr(price, 'item') else float(price)
        except Exception:
            pass

        return None

    def _get_latest_price(self, symbol: str, price_data_dict: dict):
        """Get the latest price for a stock"""
        hist = price_data_dict.get(symbol)
        if hist is None or len(hist) == 0:
            return None

        close_col = self._get_close_column_name(hist, symbol)
        if close_col is None:
            return None

        try:
            price = hist.iloc[-1][close_col]
            return float(price.item()) if hasattr(price, 'item') else float(price)
        except (ValueError, TypeError, KeyError):
            return None

    def _calculate_portfolio_value(self, as_of_date: pd.Timestamp, holdings: dict, price_data_dict: dict) -> float:
        """Calculate total portfolio value based on current holdings"""
        total_value = 0.0
        for symbol, shares in holdings.items():
            price = self._get_price_at_date(as_of_date, symbol, price_data_dict)
            if price and price > 0:
                total_value += shares * price
        return total_value

    def _error_response(self, error_msg: str) -> dict:
        """Return error response dictionary"""
        return {
            'success': False,
            'error': error_msg,
            'total_invested': 0,
            'final_value': 0,
            'gain_loss': 0,
            'gain_loss_percent': 0,
            'holdings_final': {},
            'monthly_data': [],
            'months_simulated': 0
        }
