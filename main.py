"""Main entry point for the trading system"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.api.main import app
from src.trading_bot import trading_bot
from src.utils.logger import main_logger
import uvicorn


async def main():
    """Main entry point"""
    main_logger.info("=" * 60)
    main_logger.info("Advanced Crypto Intraday Trading System")
    main_logger.info("=" * 60)
    
    # Start trading bot in background
    asyncio.create_task(trading_bot.start())
    
    # Start API server
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        main_logger.info("Shutting down...")
    except Exception as e:
        main_logger.error(f"Fatal error: {e}")
        sys.exit(1)
