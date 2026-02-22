"""
Walk-Forward Optimization Engine
Dynamically finds the best SIGNAL_WEIGHTS based on recent historical data.
"""

import asyncio
import functools
import itertools
from typing import Dict, List, Tuple
import pandas as pd
from datetime import datetime, timezone

from src.utils.logger import main_logger
from src.config.constants import SIGNAL_WEIGHTS as CURRENT_WEIGHTS
from src.data.exchange_client import binance_client
from src.backtest.engine import BacktestEngine
from src.signals.signal_generator import signal_generator

# Define search space with varying distributions (must sum to ~1.0)
WEIGHT_COMBINATIONS = [
    # 1. Default / Trend Heavy
    {
        "trend_confirmation": 0.30,
        "momentum_alignment": 0.15,
        "volume_confirmation": 0.15,
        "order_book_imbalance": 0.10,
        "volatility_regime": 0.10,
        "sentiment_score": 0.10,
        "advanced_indicators": 0.05,
        "mathematical_models": 0.05,
    },
    # 2. Momentum / Scalping Heavy (Good for ranging)
    {
        "trend_confirmation": 0.15,
        "momentum_alignment": 0.30,
        "volume_confirmation": 0.15,
        "order_book_imbalance": 0.15,
        "volatility_regime": 0.10,
        "sentiment_score": 0.05,
        "advanced_indicators": 0.05,
        "mathematical_models": 0.05,
    },
    # 3. Volume / Breakout Heavy
    {
        "trend_confirmation": 0.20,
        "momentum_alignment": 0.10,
        "volume_confirmation": 0.30,
        "order_book_imbalance": 0.15,
        "volatility_regime": 0.10,
        "sentiment_score": 0.05,
        "advanced_indicators": 0.05,
        "mathematical_models": 0.05,
    },
    # 4. Balanced Advanced
    {
        "trend_confirmation": 0.20,
        "momentum_alignment": 0.15,
        "volume_confirmation": 0.15,
        "order_book_imbalance": 0.10,
        "volatility_regime": 0.10,
        "sentiment_score": 0.10,
        "advanced_indicators": 0.10,
        "mathematical_models": 0.10,
    }
]

class WalkForwardOptimizer:
    """Optimizes weights by running backtests over different configurations"""
    
    def __init__(self, target_metric: str = 'net_pnl'):
        self.target_metric = target_metric
        # Map of the current global SIGNAL_WEIGHTS so we can temporarily override them during testing
        from src.config import constants
        self.config_module = constants
        
    def _create_strategy_fn(self, weights: Dict[str, float]):
        """Creates a strategy simulation function with specific weights injected"""
        
        def strategy(df: pd.DataFrame, current_index: int):
            # Temporarily patch weights
            original_weights = self.config_module.SIGNAL_WEIGHTS.copy()
            self.config_module.SIGNAL_WEIGHTS.update(weights)
            
            try:
                current_df = df.iloc[:current_index+1].copy()
                loop = asyncio.get_event_loop()
                signal_data = loop.run_until_complete(
                    signal_generator.generate_signal(
                        symbol=df.iloc[0]['symbol'],
                        df=current_df,
                        sentiment_score=50.0
                    )
                )
                
                if signal_data and 'direction' in signal_data:
                    direction = signal_data['direction'].value if hasattr(signal_data['direction'], 'value') else signal_data['direction']
                    if direction == 'LONG':
                        return {'action': 'BUY'}
                    elif direction == 'SHORT':
                        return {'action': 'SELL'}
                        
                return {'action': 'HOLD'}
            finally:
                # Restore original
                self.config_module.SIGNAL_WEIGHTS.update(original_weights)
                
        return strategy

    async def optimize(self, symbol: str, timeframe: str = '5m', days_lookback: int = 7) -> Dict[str, float]:
        """
        Runs the optimizer on the past N days to find the best weights.
        Returns the best weight dictionary.
        """
        main_logger.info(f"🔍 Starting Walk-Forward Optimization for {symbol} over past {days_lookback} days.")
        
        limit = (24 * 60) // int(timeframe.replace('m', '')) * days_lookback
        df = await binance_client.fetch_ohlcv(symbol, timeframe, limit=min(limit, 1000))
        
        if df.empty:
            main_logger.warning("No data for optimization.")
            return CURRENT_WEIGHTS
            
        best_metric = -float('inf')
        best_weights = CURRENT_WEIGHTS
        
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            for i, weights in enumerate(WEIGHT_COMBINATIONS):
                main_logger.info(f"Testing weight combination #{i+1}")
                engine = BacktestEngine(initial_capital=10000.0)
                strategy_fn = self._create_strategy_fn(weights)
                
                report = await asyncio.to_thread(
                    functools.partial(engine.run, data=df, strategy_fn=strategy_fn, symbol=symbol)
                )
                
                metric_value = report.get('total_pnl', 0.0) # default target
                main_logger.info(f"Result #{i+1} => PnL: ${metric_value:.2f}, Win Rate: {report.get('win_rate', 0):.1f}%")
                
                if metric_value > best_metric:
                    best_metric = metric_value
                    best_weights = weights
                    
        main_logger.info(f"🏆 Optimization complete. Best PnL: ${best_metric:.2f}")
        return best_weights

optimizer = WalkForwardOptimizer()
