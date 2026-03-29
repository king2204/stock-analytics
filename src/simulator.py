"""Dollar-Cost Averaging (DCA) investment simulator."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.data_fetcher import StockDataFetcher


class DCASimulator:
    """Simulate dollar-cost averaging strategy over historical data."""

    def __init__(self):
        """Initialize DCA simulator."""
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
        Simulate DCA investment strategy.

        Args:
            symbols: List of stock symbols (e.g., ['AAPL', 'MSFT', 'GOOGL', 'AMZN'])
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            monthly_amount: Monthly investment amount in dollars
            allocation: Dict mapping symbols to allocation % (e.g., {'AAPL': 0.25, ...})
                       If None, uses equal weight allocation
            purchase_day: Day of month to make purchases (default 1st)

        Returns:
            Dictionary containing:
                - total_invested: Total amount invested over period
                - final_value: Final portfolio value at end date
                - gain_loss: Dollar gain/loss
                - gain_loss_percent: Percentage gain/loss
                - holdings_final: Final shares held per stock
                - monthly_data: List of dicts with monthly progression
        """
        try:
            # Set default equal allocation if not provided
            if allocation is None:
                allocation = {symbol: 1.0 / len(symbols) for symbol in symbols}

            # Normalize allocation to sum to 1.0
            total_allocation = sum(allocation.values())
            allocation = {k: v / total_allocation for k, v in allocation.items()}

            # Parse dates
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)

            # Get price history for all symbols
            price_data_dict = {}
            for symbol in symbols:
                try:
                    hist = StockDataFetcher.get_price_history(symbol, days=3650)  # ~10 years
                    hist = hist.reset_index()
                    hist['Date'] = pd.to_datetime(hist['Date'])
                    hist = hist.sort_values('Date')
                    price_data_dict[symbol] = hist
                except Exception as e:
                    print(f"Error fetching {symbol}: {e}")
                    return self._error_response(f"Failed to fetch data for {symbol}")

            # Initialize holdings and tracking
            holdings = {symbol: 0 for symbol in symbols}
            monthly_data = []
            total_invested = 0

            # Generate list of purchase months
            current = start
            while current <= end:
                # Try to get purchase date (purchase_day of current month)
                try:
                    purchase_date = current.replace(day=purchase_day)
                except ValueError:
                    # Handle months with fewer days (e.g., Feb 30)
                    last_day = pd.Timestamp(current.year, current.month + 1, 1) - timedelta(days=1)
                    purchase_date = last_day.replace(day=last_day.day)

                # If purchase_date is in future, skip
                if purchase_date > end:
                    break

                # Find nearest trading day
                trading_date = self._find_nearest_trading_day(purchase_date, price_data_dict)

                if trading_date is None:
                    # Move to next month
                    if current.month == 12:
                        current = current.replace(year=current.year + 1, month=1)
                    else:
                        current = current.replace(month=current.month + 1)
                    continue

                # Buy shares for each symbol on this date
                for symbol in symbols:
                    price = self._get_price_at_date(trading_date, symbol, price_data_dict)
                    if price is not None and price > 0:
                        allocation_amount = monthly_amount * allocation[symbol]
                        shares_purchased = allocation_amount / price
                        holdings[symbol] += shares_purchased

                total_invested += monthly_amount

                # Calculate portfolio value at this date using current prices
                portfolio_value = self._calculate_portfolio_value(trading_date, holdings, price_data_dict)

                monthly_data.append({
                    'date': trading_date.strftime('%Y-%m-%d'),
                    'date_obj': trading_date,
                    'total_invested': round(total_invested, 2),
                    'portfolio_value': round(portfolio_value, 2),
                    'gain_loss': round(portfolio_value - total_invested, 2),
                    'holdings': holdings.copy()
                })

                # Move to next month
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)

            if not monthly_data:
                return self._error_response("No trading data found for selected period")

            # Get final portfolio value using latest available prices
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
            return self._error_response(f"Simulation error: {str(e)}")

    def _find_nearest_trading_day(self, target_date, price_data_dict, days_range=5):
        """Find nearest trading day to target date."""
        # Check if target_date itself has data
        for symbol in price_data_dict.keys():
            hist = price_data_dict[symbol]
            matching = hist[hist['Date'].dt.date == target_date.date()]
            if not matching.empty:
                return target_date

        # Search within days_range
        for offset in range(1, days_range + 1):
            for direction in [-1, 1]:
                check_date = target_date + timedelta(days=offset * direction)
                for symbol in price_data_dict.keys():
                    hist = price_data_dict[symbol]
                    matching = hist[hist['Date'].dt.date == check_date.date()]
                    if not matching.empty:
                        return check_date

        return None

    def _get_price_at_date(self, date, symbol, price_data_dict):
        """Get price for symbol at or nearest to given date."""
        hist = price_data_dict.get(symbol)
        if hist is None:
            return None

        matching = hist[hist['Date'].dt.date == date.date()]
        if not matching.empty:
            return float(matching.iloc[0]['Close'])

        # Find nearest date
        hist['DateDiff'] = abs((hist['Date'] - date).dt.days)
        nearest = hist.nsmallest(1, 'DateDiff')
        if not nearest.empty and nearest.iloc[0]['DateDiff'] <= 5:
            return float(nearest.iloc[0]['Close'])

        return None

    def _get_latest_price(self, symbol, price_data_dict):
        """Get most recent price for symbol."""
        hist = price_data_dict.get(symbol)
        if hist is None or hist.empty:
            return None
        return float(hist.iloc[-1]['Close'])

    def _calculate_portfolio_value(self, as_of_date, holdings, price_data_dict):
        """Calculate total portfolio value given holdings and prices as of a date."""
        total_value = 0
        for symbol, shares in holdings.items():
            price = self._get_price_at_date(as_of_date, symbol, price_data_dict)
            if price:
                total_value += shares * price
        return total_value

    def _error_response(self, error_msg):
        """Return error response dict."""
        return {
            'success': False,
            'error': error_msg,
            'total_invested': 0,
            'final_value': 0,
            'gain_loss': 0,
            'gain_loss_percent': 0,
            'holdings_final': {},
            'monthly_data': []
        }
