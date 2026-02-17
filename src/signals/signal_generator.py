"""Multi-component signal generator"""

from typing import Dict, Optional
import pandas as pd
from datetime import datetime

from src.indicators.trend import get_trend_signals
from src.indicators.momentum import get_momentum_signals
from src.indicators.volatility import get_volatility_signals
from src.indicators.volume import get_volume_signals
from src.indicators.advanced import (
    calculate_fibonacci_levels, calculate_fibonacci_score,
    calculate_adx, calculate_adx_score,
    calculate_stochastic_rsi, calculate_stochastic_rsi_score,
    calculate_ichimoku_cloud, calculate_ichimoku_score
)
from src.indicators.volume_indicators import (
    calculate_obv, calculate_obv_score,
    calculate_vwap, calculate_vwap_score
)
from src.analysis.statistical import (
    calculate_linear_regression, calculate_regression_score,
    detect_support_resistance, calculate_sr_score
)
from src.analysis.correlation import (
    calculate_correlation_score, detect_divergence
)
from src.analysis.volatility import (
    forecast_volatility_simple, calculate_volatility_score
)
from src.data.sentiment_client import sentiment_client
from src.data.news_client import news_client
from src.config.constants import SIGNAL_WEIGHTS
from src.utils.logger import signal_logger
from src.database.models import Signal, TradeDirection
from src.database.connection import get_db


class SignalGenerator:
    """Generate trading signals from multiple components"""
    
    def __init__(self):
        self.weights = SIGNAL_WEIGHTS
    
    def generate_signal(
        self,
        symbol: str,
        df: pd.DataFrame,
        order_book_data: Optional[Dict] = None,
        sentiment_score: float = 0.0,
        onchain_score: float = 0.0
    ) -> Dict:
        """
        Generate comprehensive trading signal
        
        Args:
            symbol: Trading pair
            df: DataFrame with OHLCV data
            order_book_data: Optional order book data
            sentiment_score: Sentiment score (-100 to 100)
            onchain_score: On-chain score (-100 to 100)
            
        Returns:
            Dictionary with signal information
        """
        try:
            # Get volatility regime first (needed for momentum)
            volatility_signals = get_volatility_signals(df)
            volatility_regime = volatility_signals['volatility_regime']
            
            # Get all component signals
            trend_signals = get_trend_signals(df)
            momentum_signals = get_momentum_signals(df, volatility_regime)
            volume_signals = get_volume_signals(df, order_book_data)
            
            # Extract component scores
            trend_score = trend_signals['trend_score']
            momentum_score = momentum_signals['momentum_score']
            volume_score = volume_signals['volume_score']
            orderbook_score = volume_signals['orderbook_imbalance_signal'] * 100
            volatility_score = volatility_signals['volatility_score']
            
            # Calculate advanced indicators
            current_price = df['close'].iloc[-1]
            
            # Fibonacci levels
            fib_levels = calculate_fibonacci_levels(df, lookback=50)
            fib_score = calculate_fibonacci_score(current_price, fib_levels)
            
            # ADX (need direction first for scoring)
            adx, di_plus, di_minus = calculate_adx(df, period=14)
            adx_value = adx.iloc[-1] if len(adx) > 0 else 0
            di_plus_value = di_plus.iloc[-1] if len(di_plus) > 0 else 0
            di_minus_value = di_minus.iloc[-1] if len(di_minus) > 0 else 0
            
            # Stochastic RSI
            stoch_k, stoch_d = calculate_stochastic_rsi(df, rsi_period=14, stoch_period=14)
            stoch_k_value = stoch_k.iloc[-1] if len(stoch_k) > 0 else 50
            stoch_d_value = stoch_d.iloc[-1] if len(stoch_d) > 0 else 50
            
            # OBV
            obv = calculate_obv(df)
            
            # VWAP
            vwap = calculate_vwap(df)
            vwap_value = vwap.iloc[-1] if len(vwap) > 0 else current_price
            
            # Ichimoku Cloud
            ichimoku = calculate_ichimoku_cloud(df)
            
            # Linear Regression
            regression = calculate_linear_regression(df, period=50)
            
            # Support/Resistance
            sr_levels = detect_support_resistance(df, lookback=100, num_levels=5)
            
            # Volatility Forecasting
            vol_forecast = forecast_volatility_simple(df, period=20, forecast_days=5)
            
            # Fear & Greed Index (sentiment)
            fear_greed_data = sentiment_client.get_fear_greed_index()
            fear_greed_value = fear_greed_data['value'] if fear_greed_data else None
            
            # Determine preliminary direction for advanced scoring
            prelim_confidence = (
                (trend_score / 100) * self.weights['trend_confirmation'] +
                (momentum_score / 100) * self.weights['momentum_alignment'] +
                (volume_score / 100) * self.weights['volume_confirmation']
            ) * 100
            
            prelim_direction = 'LONG' if prelim_confidence > 0 else 'SHORT'
            
            # Calculate advanced indicator scores
            adx_score = calculate_adx_score(adx_value, di_plus_value, di_minus_value, prelim_direction)
            stoch_rsi_score = calculate_stochastic_rsi_score(stoch_k_value, stoch_d_value, prelim_direction)
            obv_score = calculate_obv_score(df, obv, prelim_direction)
            vwap_score = calculate_vwap_score(current_price, vwap_value, prelim_direction)
            ichimoku_score = calculate_ichimoku_score(current_price, ichimoku, prelim_direction)
            
            # Calculate mathematical model scores
            regression_score = calculate_regression_score(current_price, regression, prelim_direction)
            sr_score = calculate_sr_score(current_price, sr_levels, prelim_direction)
            
            # Calculate correlation score (using demo correlation for now)
            # In production, would fetch BTC data and calculate real correlation
            demo_correlation = 0.5  # Neutral correlation for demo
            correlation_score = calculate_correlation_score(demo_correlation, prelim_direction)
            
            # Calculate volatility score
            volatility_forecast_score = calculate_volatility_score(vol_forecast, prelim_direction)
            
            # Calculate sentiment score from Fear & Greed
            sentiment_fg_score = sentiment_client.calculate_sentiment_score(fear_greed_value, prelim_direction)
            
            # Calculate news sentiment score
            news_sentiment_score = news_client.calculate_news_sentiment_score(symbol.split('/')[0], prelim_direction)
            
            # Combined advanced indicators score (average of all 6)
            advanced_score = (fib_score + adx_score + stoch_rsi_score + obv_score + vwap_score + ichimoku_score) / 6
            
            # Combined mathematical models score (average of 4)
            math_score = (regression_score + sr_score + correlation_score + volatility_forecast_score) / 4
            
            # Combined sentiment score (Fear & Greed 60% + News 40%)
            combined_sentiment = (sentiment_fg_score * 0.6 + news_sentiment_score * 0.4)
            
            # Calculate weighted confidence score with ALL components
            confidence_score = (
                (trend_score / 100) * 0.25 +           # 25% - Trend confirmation
                (momentum_score / 100) * 0.20 +        # 20% - Momentum alignment
                (volume_score / 100) * 0.15 +          # 15% - Volume confirmation
                (orderbook_score / 100) * 0.10 +       # 10% - Order book imbalance
                (volatility_score / 100) * 0.10 +      # 10% - Volatility regime
                (advanced_score / 100) * 0.10 +        # 10% - Advanced indicators (6)
                (math_score / 100) * 0.08 +            # 8% - Mathematical models (4)
                (combined_sentiment / 100) * 0.07 +    # 7% - Sentiment (F&G + News)
                (sentiment_score / 100) * 0.00 +       # 0% - Legacy sentiment (unused)
                (onchain_score / 100) * self.weights['onchain_data']
            ) * 100
            
            # Determine direction
            if confidence_score > 0:
                direction = TradeDirection.LONG
            elif confidence_score < 0:
                direction = TradeDirection.SHORT
            else:
                direction = None
            
            # Calculate entry/exit levels
            current_price = df['close'].iloc[-1]
            atr = volatility_signals['atr_value']
            
            # Entry price (current price for market orders)
            entry_price = current_price
            
            # Stop loss and take profit based on ATR
            if direction == TradeDirection.LONG:
                stop_loss = current_price - (atr * 2.0)
                take_profit = current_price + (atr * 5.0)  # 1:2.5 R/R
            elif direction == TradeDirection.SHORT:
                stop_loss = current_price + (atr * 2.0)
                take_profit = current_price - (atr * 5.0)
            else:
                stop_loss = current_price
                take_profit = current_price
            
            # Calculate risk/reward ratio
            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)
            risk_reward_ratio = reward / risk if risk > 0 else 0
            
            # Determine signal type
            signal_type = self._determine_signal_type(
                trend_signals,
                momentum_signals,
                volume_signals,
                volatility_signals
            )
            
            signal_data = {
                'symbol': symbol,
                'timestamp': datetime.utcnow(),
                'direction': direction,
                'trend_score': float(trend_score),
                'momentum_score': float(momentum_score),
                'volume_score': float(volume_score),
                'orderbook_score': float(orderbook_score),
                'volatility_score': float(volatility_score),
                'sentiment_score': float(sentiment_score),
                'onchain_score': float(onchain_score),
                'confidence_score': float(abs(confidence_score)),
                'risk_reward_ratio': float(risk_reward_ratio),
                'entry_price': float(entry_price),
                'stop_loss': float(stop_loss),
                'take_profit': float(take_profit),
                'signal_type': signal_type,
                'market_regime': volatility_regime,
                'atr': float(atr),
            }
            
            signal_logger.info(
                f"Generated signal for {symbol}: {direction} "
                f"Confidence: {abs(confidence_score):.1f}% R/R: {risk_reward_ratio:.2f}"
            )
            
            return signal_data
            
        except Exception as e:
            import traceback
            signal_logger.error(f"Error generating signal for {symbol}: {e}")
            signal_logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def _determine_signal_type(
        self,
        trend_signals: Dict,
        momentum_signals: Dict,
        volume_signals: Dict,
        volatility_signals: Dict
    ) -> str:
        """
        Determine the type of signal
        
        Returns:
            Signal type: breakout, pullback, reversal, or continuation
        """
        # Breakout: high volume + BB squeeze + trend alignment
        if (volume_signals['high_volume'] and 
            volatility_signals.get('bb_squeeze', False) and
            abs(trend_signals['trend_score']) > 50):
            return 'breakout'
        
        # Pullback: trend strong but momentum oversold/overbought
        if (abs(trend_signals['trend_score']) > 60 and
            (momentum_signals.get('rsi_oversold', False) or 
             momentum_signals.get('rsi_overbought', False))):
            return 'pullback'
        
        # Reversal: divergence detected
        if (momentum_signals.get('bullish_divergence', False) or
            momentum_signals.get('bearish_divergence', False)):
            return 'reversal'
        
        # Continuation: trend and momentum aligned
        if (trend_signals['trend_score'] * momentum_signals['momentum_score'] > 0 and
            abs(trend_signals['trend_score']) > 40):
            return 'continuation'
        
        return 'other'
    
    def save_signal(self, signal_data: Dict) -> Optional[int]:
        """
        Save signal to database
        
        Args:
            signal_data: Signal information
            
        Returns:
            Signal ID or None
        """
        if not signal_data or not signal_data.get('direction'):
            return None
        
        try:
            with get_db() as db:
                signal = Signal(
                    symbol=signal_data['symbol'],
                    timestamp=signal_data['timestamp'],
                    direction=signal_data['direction'],
                    trend_score=signal_data['trend_score'],
                    momentum_score=signal_data['momentum_score'],
                    volume_score=signal_data['volume_score'],
                    orderbook_score=signal_data['orderbook_score'],
                    volatility_score=signal_data['volatility_score'],
                    sentiment_score=signal_data['sentiment_score'],
                    onchain_score=signal_data['onchain_score'],
                    confidence_score=signal_data['confidence_score'],
                    risk_reward_ratio=signal_data['risk_reward_ratio'],
                    entry_price=signal_data['entry_price'],
                    stop_loss=signal_data['stop_loss'],
                    take_profit=signal_data['take_profit'],
                    signal_type=signal_data['signal_type'],
                    market_regime=signal_data['market_regime'],
                )
                db.add(signal)
                db.commit()
                db.refresh(signal)
                
                signal_logger.info(f"Saved signal ID {signal.id} for {signal_data['symbol']}")
                return signal.id
                
        except Exception as e:
            signal_logger.error(f"Error saving signal: {e}")
            return None


# Global signal generator instance
signal_generator = SignalGenerator()
