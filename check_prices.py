"""Check real-time prices from Yahoo Finance"""
from src.data_fetcher import StockDataFetcher
from datetime import datetime, timezone, timedelta

bangkok_tz = timezone(timedelta(hours=7))
current_time = datetime.now(bangkok_tz).strftime("%Y-%m-%d %H:%M:%S Thailand Time")

print(f"\n{'='*60}")
print(f"📊 Real-time Stock Prices Check")
print(f"✅ Checked at: {current_time}")
print(f"{'='*60}\n")

symbols = ["AAPL", "MSFT", "GOOGL", "AMZN"]

for symbol in symbols:
    price = StockDataFetcher.get_current_price(symbol)
    if price:
        print(f"💱 {symbol:6} → ${price:.2f}")
    else:
        print(f"❌ {symbol:6} → Failed to fetch")

print(f"\n{'='*60}")
print("👉 นำค่าเหล่านี้ไปเปรียบเทียบกับ Yahoo Finance เว็บแล้ว\n")
