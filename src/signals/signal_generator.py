"""Multi-component signal generator"""

from typing import Dict, Optional
import pandas as pd
from datetime import datetime

from src.indicators.trend import get_trend_signals
from src.indicators.momentum import get_momentum_signals
from src.indicators.volatility import get_volatility_signals
from src.indicators.volume import get_volume_signals
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
            
            # Calculate weighted confidence score
            confidence_score = (
                (trend_score / 100) * self.weights['trend_confirmation'] +
                (momentum_score / 100) * self.weights['momentum_alignment'] +
                (volume_score / 100) * self.weights['volume_confirmation'] +
                (orderbook_score / 100) * self.weights['order_book_imbalance'] +
                (volatility_score / 100) * self.weights['volatility_regime'] +
                (sentiment_score / 100) * self.weights['sentiment_score'] +
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
                'trend_score': trend_score,
                'momentum_score': momentum_score,
                'volume_score': volume_score,
                'orderbook_score': orderbook_score,
                'volatility_score': volatility_score,
                'sentiment_score': sentiment_score,
                'onchain_score': onchain_score,
                'confidence_score': abs(confidence_score),
                'risk_reward_ratio': risk_reward_ratio,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'signal_type': signal_type,
                'market_regime': volatility_regime,
                'atr': atr,
            }
            
            signal_logger.info(
                f"Generated signal for {symbol}: {direction} "
                f"Confidence: {abs(confidence_score):.1f}% R/R: {risk_reward_ratio:.2f}"
            )
            
            return signal_data
            
        except Exception as e:
            signal_logger.error(f"Error generating signal for {symbol}: {e}")
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
