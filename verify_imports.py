import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

try:
    print("Checking imports...")
    from src.data.exchange_client import binance_client, ExchangeClient
    print(f"✅ exchange_client imported: {binance_client}")
    
    from src.data.market_data import market_data_manager, MarketDataManager
    print(f"✅ market_data imported: {market_data_manager}")
    
    from src.data.sentiment_client import sentiment_client
    print(f"✅ sentiment_client imported: {sentiment_client}")
    
    from src.data.news_client import news_client
    print(f"✅ news_client imported: {news_client}")
    
    print("All critical data clients imported successfully.")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
