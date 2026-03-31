"""โมเดลข้อมูลพอร์ตโฟลิโอและการจัดการ"""

import pandas as pd
from datetime import datetime


class Portfolio:
    """แสดงถึงพอร์ตโฟลิโอหุ้นที่มีการถือครอง"""

    def __init__(self, name: str):
        """
        เริ่มต้นพอร์ตโฟลิโอ

        Args:
            name: ชื่อพอร์ตโฟลิโอ
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
        เพิ่มการถือครองหุ้นในพอร์ตโฟลิโอ

        Args:
            symbol: สัญลักษณ์ ticker ของหุ้น เช่น 'AAPL'
            shares: จำนวนหุ้น
            purchase_price: ราคาต่อหุ้นเมื่อซื้อ
            purchase_date: วันที่ซื้อ (รูปแบบ YYYY-MM-DD)
        """
        new_holding = pd.DataFrame([{
            'symbol': symbol.upper(),
            'shares': shares,
            'purchase_price': purchase_price,
            'purchase_date': purchase_date
        }])
        self.holdings = pd.concat([self.holdings, new_holding], ignore_index=True)

    def remove_holding(self, symbol: str):
        """ลบการถือครองออกจากพอร์ตโฟลิโอ"""
        self.holdings = self.holdings[self.holdings['symbol'] != symbol.upper()]

    def get_symbols(self) -> list:
        """ดึงรายการสัญลักษณ์หุ้นที่มีอยู่ในพอร์ตโฟลิโอ"""
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
