#!/usr/bin/env python3
"""
CLI Script to run Emiroloji Backtest Engine
Usage: python run_backtest.py --symbol BTC/USDT --days 7 --timeframe 5m
"""

import sys
import argparse
import asyncio
import functools
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.data.exchange_client import binance_client
from src.backtest.engine import BacktestEngine
from src.signals.signal_generator import signal_generator

def run_strategy(df, current_index):
    """Bridge function for the backtest engine"""
    current_df = df.iloc[:current_index+1].copy()
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    signal_data = loop.run_until_complete(
        signal_generator.generate_signal(
            symbol=df.iloc[0]['symbol'],
            df=current_df,
            sentiment_score=50.0 
        )
    )
    
    # 🌟 İŞTE HAYAT KURTARAN DÜZELTME BURADA 🌟
    if signal_data and 'direction' in signal_data:
        confidence = signal_data.get('confidence_score', 0.0)
        
        # Sadece güven skoru 85 ve üzeriyse işleme gir!
        if confidence >= 85.0:
            direction = signal_data['direction'].value if hasattr(signal_data['direction'], 'value') else signal_data['direction']
            if direction == 'LONG':
                return {'action': 'BUY'}
            elif direction == 'SHORT':
                return {'action': 'SELL'}
            
    return {'action': 'HOLD'}
    
async def main():
    parser = argparse.ArgumentParser(description="Emiroloji Backtest CLI")
    parser.add_argument("--symbol", type=str, default="BTC/USDT", help="Trading pair symbol (e.g., BTC/USDT)")
    parser.add_argument("--days", type=int, default=7, help="Number of days to backtest")
    parser.add_argument("--timeframe", type=str, default="5m", help="Timeframe (e.g., 1m, 5m, 1h)")
    parser.add_argument("--capital", type=float, default=10000.0, help="Initial capital in USDT")
    
    args = parser.parse_args()
    
    print(f"[*] Starting backtest for {args.symbol}")
    print(f"[*] Timeframe: {args.timeframe}, Days: {args.days}, Initial Capital: ${args.capital}")
    print("[*] Fetching historical data from Binance...")
    
    # Calculate limits based on timeframe
    # For 5m: 1 day = 24 * 60 / 5 = 288 candles
    tf_minutes = 5 # Default assuming 5m
    if args.timeframe.endswith('m'):
        tf_minutes = int(args.timeframe[:-1])
    elif args.timeframe.endswith('h'):
        tf_minutes = int(args.timeframe[:-1]) * 60
    elif args.timeframe.endswith('d'):
        tf_minutes = int(args.timeframe[:-1]) * 1440
        
    candles_per_day = (24 * 60) // tf_minutes
    total_limit = candles_per_day * args.days
    
    # CCXT has limits around 1000-1500 per request, for long backtests pagination is needed.
    # For this simple script we fetch up to what binance allows (usually limit=1000 or 1500)
    # If the requested limit is larger, we would need to fetch iteratively using since parameter.
    # Implementing simple fetch for demonstration:
    
    try:
        # Just use the existing fetch_ohlcv. Note: If days is large, you should enhance fetch_ohlcv to support pagination.
        df = await binance_client.fetch_ohlcv(symbol=args.symbol, timeframe=args.timeframe, limit=min(total_limit, 1500))
        
        if df.empty:
            print("[-] Error: No data fetched from exchange.")
            return

        print(f"[+] Fetched {len(df)} candles.")
        print("[*] Running Backtest Engine... (This may take a while depending on signal generation complexity)")
        
        engine = BacktestEngine(initial_capital=args.capital)
        report = await asyncio.to_thread(
            functools.partial(engine.run, data=df, strategy_fn=run_strategy, symbol=args.symbol)
        )
        
        print("\n" + "="*40)
        print("📊 BACKTEST RESULTS")
        print("="*40)
        for key, value in report.items():
            if isinstance(value, float):
                print(f"{key.replace('_', ' ').title()}: {value:.2f}")
            else:
                print(f"{key.replace('_', ' ').title()}: {value}")
        print("="*40)

    except Exception as e:
        print(f"[-] An error occurred during backtest: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
