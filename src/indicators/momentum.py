"""Momentum indicators: RSI, Stochastic RSI, MACD, CCI"""

import pandas as pd
import numpy as np
from typing import Tuple

from src.config.constants import INDICATOR_PARAMS


def calculate_rsi(df: pd.DataFrame, period: int = None, column: str = 'close') -> pd.Series:
    """
    Calculate Relative Strength Index
    
    Args:
        df: DataFrame with price data
        period: RSI period
        column: Column to calculate RSI on
        
    Returns:
        RSI series
    """
    period = period or INDICATOR_PARAMS['rsi_period']
    
    delta = df[column].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_stochastic_rsi(df: pd.DataFrame, period: int = None) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate Stochastic RSI
    
    Args:
        df: DataFrame with price data
        period: Period for calculation
        
    Returns:
        Tuple of (Stoch RSI, Stoch RSI signal)
    """
    period = period or INDICATOR_PARAMS['stoch_rsi_period']
    
    rsi = calculate_rsi(df, period)
    
    stoch_rsi = (rsi - rsi.rolling(period).min()) / (rsi.rolling(period).max() - rsi.rolling(period).min()) * 100
    stoch_rsi_k = stoch_rsi.rolling(3).mean()  # %K
    stoch_rsi_d = stoch_rsi_k.rolling(3).mean()  # %D
    
    return stoch_rsi_k, stoch_rsi_d


def calculate_macd(
    df: pd.DataFrame,
    fast: int = None,
    slow: int = None,
    signal: int = None
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD (Moving Average Convergence Divergence)
    
    Args:
        df: DataFrame with price data
        fast: Fast EMA period
        slow: Slow EMA period
        signal: Signal line period
        
    Returns:
        Tuple of (MACD line, Signal line, Histogram)
    """
    fast = fast or INDICATOR_PARAMS['macd_fast']
    slow = slow or INDICATOR_PARAMS['macd_slow']
    signal = signal or INDICATOR_PARAMS['macd_signal']
    
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def detect_macd_divergence(df: pd.DataFrame, lookback: int = 20) -> dict:
    """
    Detect MACD divergence
    
    Args:
        df: DataFrame with price data
        lookback: Lookback period for divergence detection
        
    Returns:
        Dictionary with divergence signals
    """
    macd_line, signal_line, histogram = calculate_macd(df)
    
    # Find recent peaks and troughs
    price_peaks = df['close'].rolling(window=5, center=True).apply(
        lambda x: x[2] if x[2] == max(x) else 0
    )
    price_troughs = df['close'].rolling(window=5, center=True).apply(
        lambda x: x[2] if x[2] == min(x) else 0
    )
    
    macd_peaks = histogram.rolling(window=5, center=True).apply(
        lambda x: x[2] if x[2] == max(x) else 0
    )
    macd_troughs = histogram.rolling(window=5, center=True).apply(
        lambda x: x[2] if x[2] == min(x) else 0
    )
    
    # Bullish divergence: price makes lower low, MACD makes higher low
    bullish_divergence = False
    # Bearish divergence: price makes higher high, MACD makes lower high
    bearish_divergence = False
    
    recent_data = df.tail(lookback)
    
    # Simplified divergence detection
    if len(recent_data) > 10:
        price_trend = recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]
        macd_trend = histogram.iloc[-1] - histogram.iloc[-lookback]
        
        if price_trend < 0 and macd_trend > 0:
            bullish_divergence = True
        elif price_trend > 0 and macd_trend < 0:
            bearish_divergence = True
    
    return {
        'bullish_divergence': bullish_divergence,
        'bearish_divergence': bearish_divergence,
        'macd_value': macd_line.iloc[-1],
        'signal_value': signal_line.iloc[-1],
        'histogram_value': histogram.iloc[-1],
    }


def calculate_cci(df: pd.DataFrame, period: int = None) -> pd.Series:
    """
    Calculate Commodity Channel Index
    
    Args:
        df: DataFrame with OHLCV data
        period: CCI period
        
    Returns:
        CCI series
    """
    period = period or INDICATOR_PARAMS['cci_period']
    
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    sma = typical_price.rolling(window=period).mean()
    mean_deviation = typical_price.rolling(window=period).apply(
        lambda x: np.abs(x - x.mean()).mean()
    )
    
    cci = (typical_price - sma) / (0.015 * mean_deviation)
    
    return cci


def get_momentum_signals(df: pd.DataFrame, volatility_regime: str = 'normal') -> dict:
    """
    Generate momentum signals from all momentum indicators
    
    Args:
        df: DataFrame with OHLCV data
        volatility_regime: Current volatility regime (low, normal, high)
        
    Returns:
        Dictionary with momentum signals and scores
    """
    signals = {}
    
    # Adaptive RSI thresholds based on volatility
    if volatility_regime == 'high':
        rsi_overbought = 75
        rsi_oversold = 25
    elif volatility_regime == 'low':
        rsi_overbought = 65
        rsi_oversold = 35
    else:
        rsi_overbought = INDICATOR_PARAMS['rsi_overbought']
        rsi_oversold = INDICATOR_PARAMS['rsi_oversold']
    
    # RSI
    rsi = calculate_rsi(df)
    rsi_value = rsi.iloc[-1]
    signals['rsi_value'] = rsi_value
    signals['rsi_overbought'] = rsi_value > rsi_overbought
    signals['rsi_oversold'] = rsi_value < rsi_oversold
    
    # RSI momentum: 1 (bullish), -1 (bearish), 0 (neutral)
    if rsi_value > 50:
        signals['rsi_momentum'] = 1
    elif rsi_value < 50:
        signals['rsi_momentum'] = -1
    else:
        signals['rsi_momentum'] = 0
    
    # Stochastic RSI
    stoch_k, stoch_d = calculate_stochastic_rsi(df)
    stoch_k_value = stoch_k.iloc[-1]
    stoch_d_value = stoch_d.iloc[-1]
    
    signals['stoch_rsi_k'] = stoch_k_value
    signals['stoch_rsi_d'] = stoch_d_value
    signals['stoch_rsi_bullish'] = stoch_k_value > stoch_d_value and stoch_k_value < 80
    signals['stoch_rsi_bearish'] = stoch_k_value < stoch_d_value and stoch_k_value > 20
    
    # MACD
    macd_data = detect_macd_divergence(df)
    signals['macd_value'] = macd_data['macd_value']
    signals['macd_signal'] = macd_data['signal_value']
    signals['macd_histogram'] = macd_data['histogram_value']
    signals['macd_bullish'] = macd_data['macd_value'] > macd_data['signal_value']
    signals['macd_bearish'] = macd_data['macd_value'] < macd_data['signal_value']
    signals['bullish_divergence'] = macd_data['bullish_divergence']
    signals['bearish_divergence'] = macd_data['bearish_divergence']
    
    # CCI
    cci = calculate_cci(df)
    cci_value = cci.iloc[-1]
    signals['cci_value'] = cci_value
    signals['cci_overbought'] = cci_value > 100
    signals['cci_oversold'] = cci_value < -100
    
    # Overall momentum score (-100 to 100)
    momentum_score = 0
    
    # RSI contribution (30 points)
    if signals['rsi_oversold']:
        momentum_score += 30
    elif signals['rsi_overbought']:
        momentum_score -= 30
    else:
        momentum_score += (rsi_value - 50) * 0.6
    
    # Stochastic RSI contribution (25 points)
    if signals['stoch_rsi_bullish']:
        momentum_score += 25
    elif signals['stoch_rsi_bearish']:
        momentum_score -= 25
    
    # MACD contribution (30 points)
    if signals['macd_bullish']:
        momentum_score += 15
    if signals['bullish_divergence']:
        momentum_score += 15
    if signals['macd_bearish']:
        momentum_score -= 15
    if signals['bearish_divergence']:
        momentum_score -= 15
    
    # CCI contribution (15 points)
    if signals['cci_oversold']:
        momentum_score += 15
    elif signals['cci_overbought']:
        momentum_score -= 15
    
    signals['momentum_score'] = np.clip(momentum_score, -100, 100)
    
    return signals
