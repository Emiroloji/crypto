import pytest
import pandas as pd
from src.backtest.engine import BacktestEngine

def simple_strategy(df, index):
    """Simple SMA crossover strategy for testing"""
    if index < 20:
        return {'action': 'HOLD'}
        
    current_price = df.iloc[index]['close']
    prev_price = df.iloc[index-1]['close']
    
    # Simple logic: Buy if price goes up, Sell if price goes down (Trend Following)
    if current_price > prev_price:
        return {'action': 'BUY', 'amount_usd': 1000}
    elif current_price < prev_price:
        return {'action': 'SELL'}
        
    return {'action': 'HOLD'}

def test_backtest_run(backtest_engine, mock_ohlcv_data):
    """Test running the backtest engine"""
    result = backtest_engine.run(mock_ohlcv_data, simple_strategy, symbol="BTC/USDT")
    
    assert isinstance(result, dict)
    assert "initial_capital" in result
    assert "final_capital" in result
    assert "total_trades" in result
    
    # We expect some trades with the simple strategy on random-ish data
    # (The mock data is strictly increasing so it should buy and hold mostly)
    
    # Actually mock data is strictly increasing loops?
    # conftest: 'close': [102.0 + i for i in range(100)] -> Strictly increasing
    # So Strategy: current > prev -> BUY.
    # It should BUY at index 50 and then HOLD/BUY more if logic allows.
    # My logic: 
    # if current > prev: BUY.
    # Engine logic: 
    # if signal['action'] == 'BUY':
    #   if position is None: Open LONG
    #   elif position.side == 'SHORT': Flip
    #   else (LONG): Do nothing (Pyramiding not implemented in simple engine)
    
    # So it should Buy once and hold till end.
    
    assert result['total_trades'] >= 1
    assert backtest_engine.trades[0].side == 'LONG'
