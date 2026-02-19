import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("Checking module integrity...")

try:
    print("Importing settings...")
    from src.config.settings import settings
    print("✅ Settings imported")

    print("Importing database models...")
    from src.database.models import Base
    print("✅ Models imported")

    print("Importing MarketDataManager...")
    from src.data.market_data import market_data_manager
    print("✅ MarketDataManager imported")

    print("Importing SignalGenerator...")
    from src.signals.signal_generator import signal_generator
    print("✅ SignalGenerator imported")

    print("Importing TradeExecutor...")
    from src.execution.trade_executor import trade_executor
    print("✅ TradeExecutor imported")

    print("Importing TradingBot...")
    from src.trading_bot import trading_bot
    print("✅ TradingBot imported")

    print("Importing API...")
    from src.api.main import app
    print("✅ API imported")

    print("\n🎉 All core modules imported successfully!")

except Exception as e:
    print(f"\n❌ Integrity check failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
