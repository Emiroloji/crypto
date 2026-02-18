"""Advanced technical indicators: Fibonacci, ADX, Ichimoku"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, List


def calculate_fibonacci_levels(df: pd.DataFrame, lookback: int = 50) -> Dict[str, float]:
    """
    Calculate Fibonacci retracement levels
    
    Args:
        df: DataFrame with OHLCV data
        lookback: Period to find swing high/low
        
    Returns:
        Dictionary with Fibonacci levels and swing points
    """
    if len(df) < lookback:
        return {
            'swing_high': 0,
            'swing_low': 0,
            'fib_0': 0,
            'fib_236': 0,
            'fib_382': 0,
            'fib_500': 0,
            'fib_618': 0,
            'fib_786': 0,
            'fib_1000': 0,
        }
    
    recent = df.tail(lookback)
    swing_high = recent['high'].max()
    swing_low = recent['low'].min()
    
    diff = swing_high - swing_low
    
    # Fibonacci retracement levels
    levels = {
        'swing_high': float(swing_high),
        'swing_low': float(swing_low),
        'fib_0': float(swing_high),  # 0% (swing high)
        'fib_236': float(swing_high - 0.236 * diff),  # 23.6%
        'fib_382': float(swing_high - 0.382 * diff),  # 38.2%
        'fib_500': float(swing_high - 0.500 * diff),  # 50%
        'fib_618': float(swing_high - 0.618 * diff),  # 61.8% (Golden ratio)
        'fib_786': float(swing_high - 0.786 * diff),  # 78.6%
        'fib_1000': float(swing_low),  # 100% (swing low)
    }
    
    return levels


def calculate_fibonacci_score(current_price: float, fib_levels: Dict[str, float]) -> float:
    """
    Score based on Fibonacci level proximity
    
    Args:
        current_price: Current market price
        fib_levels: Fibonacci levels from calculate_fibonacci_levels
        
    Returns:
        Score 0-100 (higher = better alignment with key levels)
    """
    if fib_levels['swing_high'] == 0:
        return 50.0
    
    # Check proximity to key Fibonacci levels
    key_levels = [
        fib_levels['fib_382'],  # Strong support/resistance
        fib_levels['fib_500'],  # Psychological level
        fib_levels['fib_618'],  # Golden ratio - strongest
    ]
    
    # Find closest level
    min_distance = float('inf')
    for level in key_levels:
        distance = abs(current_price - level) / current_price
        min_distance = min(min_distance, distance)
    
    # Score: closer to key level = higher score
    # Within 1% = 100, Within 5% = 50, Beyond 5% = 0
    if min_distance < 0.01:  # Within 1%
        score = 100.0
    elif min_distance < 0.05:  # Within 5%
        score = 100.0 - (min_distance - 0.01) * 1250  # Linear decay
    else:
        score = 0.0
    
    return max(0.0, min(100.0, score))


def calculate_adx(df: pd.DataFrame, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate ADX (Average Directional Index) and DI+/DI-
    
    Args:
        df: DataFrame with OHLCV data
        period: ADX period (default 14)
        
    Returns:
        Tuple of (ADX, DI+, DI-) Series
    """
    if len(df) < period + 1:
        return pd.Series([0] * len(df)), pd.Series([0] * len(df)), pd.Series([0] * len(df))
    
    # Calculate True Range
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Calculate Directional Movement
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    
    plus_dm = pd.Series(0.0, index=df.index)
    minus_dm = pd.Series(0.0, index=df.index)
    
    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move
    
    # Smooth with Wilder's smoothing (exponential moving average)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)
    
    # Calculate DX and ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    
    return adx, plus_di, minus_di


def calculate_adx_score(adx_value: float, di_plus: float, di_minus: float, direction: str) -> float:
    """
    Score based on ADX trend strength
    
    Args:
        adx_value: Current ADX value
        di_plus: Current DI+ value
        di_minus: Current DI- value
        direction: Trade direction ('LONG' or 'SHORT')
        
    Returns:
        Score 0-100 (higher = stronger trend in desired direction)
    """
    # ADX interpretation:
    # 0-25: Weak/no trend
    # 25-50: Strong trend
    # 50-75: Very strong trend
    # 75-100: Extremely strong trend
    
    # Base score from ADX strength
    if adx_value < 25:
        trend_strength = adx_value / 25 * 50  # 0-50
    else:
        trend_strength = 50 + (adx_value - 25) / 75 * 50  # 50-100
    
    # Direction confirmation
    if direction.upper() == 'LONG':
        if di_plus > di_minus:
            direction_score = 100.0  # Aligned
        else:
            direction_score = 0.0  # Opposite
    else:  # SHORT
        if di_minus > di_plus:
            direction_score = 100.0  # Aligned
        else:
            direction_score = 0.0  # Opposite
    
    # Combined score: trend strength * direction alignment
    final_score = trend_strength * (direction_score / 100.0)
    
    return float(max(0.0, min(100.0, final_score)))


def calculate_stochastic_rsi(df: pd.DataFrame, rsi_period: int = 14, stoch_period: int = 14) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate Stochastic RSI
    
    Args:
        df: DataFrame with OHLCV data
        rsi_period: RSI calculation period
        stoch_period: Stochastic calculation period
        
    Returns:
        Tuple of (Stoch RSI %K, Stoch RSI %D)
    """
    if len(df) < rsi_period + stoch_period:
        return pd.Series([50] * len(df)), pd.Series([50] * len(df))
    
    # Calculate RSI first
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # Calculate Stochastic of RSI
    rsi_min = rsi.rolling(window=stoch_period).min()
    rsi_max = rsi.rolling(window=stoch_period).max()
    rsi_range = rsi_max - rsi_min
    # Avoid division by zero: flat RSI → neutral StochRSI (50)
    stoch_rsi = (100 * (rsi - rsi_min) / rsi_range.replace(0, np.nan)).fillna(50)
    stoch_rsi_d = stoch_rsi.rolling(window=3).mean()  # %D is 3-period SMA of %K
    
    return stoch_rsi.fillna(50), stoch_rsi_d.fillna(50)


def calculate_stochastic_rsi_score(stoch_k: float, stoch_d: float, direction: str) -> float:
    """
    Score based on Stochastic RSI
    
    Args:
        stoch_k: Stochastic RSI %K value
        stoch_d: Stochastic RSI %D value
        direction: Trade direction ('LONG' or 'SHORT')
        
    Returns:
        Score 0-100
    """
    # Stochastic RSI interpretation:
    # > 80: Overbought
    # < 20: Oversold
    # Crossovers indicate momentum shifts
    
    if direction.upper() == 'LONG':
        # For LONG: prefer oversold or rising from oversold
        if stoch_k < 20:
            score = 100.0  # Oversold - good for LONG
        elif stoch_k < 50:
            score = 80.0 - (stoch_k - 20) * 1.33  # 80-40
        elif stoch_k < 80:
            score = 40.0 - (stoch_k - 50) * 1.33  # 40-0
        else:
            score = 0.0  # Overbought - bad for LONG
            
        # Bonus for bullish crossover (K > D)
        if stoch_k > stoch_d:
            score = min(100.0, score * 1.2)
    else:  # SHORT
        # For SHORT: prefer overbought or falling from overbought
        if stoch_k > 80:
            score = 100.0  # Overbought - good for SHORT
        elif stoch_k > 50:
            score = 80.0 - (80 - stoch_k) * 1.33  # 80-40
        elif stoch_k > 20:
            score = 40.0 - (50 - stoch_k) * 1.33  # 40-0
        else:
            score = 0.0  # Oversold - bad for SHORT
            
        # Bonus for bearish crossover (K < D)
        if stoch_k < stoch_d:
            score = min(100.0, score * 1.2)
    
    return float(max(0.0, min(100.0, score)))


def calculate_ichimoku_cloud(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """
    Calculate Ichimoku Cloud components
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        Dictionary with Ichimoku components
    """
    if len(df) < 52:
        empty_series = pd.Series([0] * len(df))
        return {
            'tenkan_sen': empty_series,
            'kijun_sen': empty_series,
            'senkou_span_a': empty_series,
            'senkou_span_b': empty_series,
            'chikou_span': empty_series,
        }
    
    high = df['high']
    low = df['low']
    close = df['close']
    
    # Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
    period9_high = high.rolling(window=9).max()
    period9_low = low.rolling(window=9).min()
    tenkan_sen = (period9_high + period9_low) / 2
    
    # Kijun-sen (Base Line): (26-period high + 26-period low) / 2
    period26_high = high.rolling(window=26).max()
    period26_low = low.rolling(window=26).min()
    kijun_sen = (period26_high + period26_low) / 2
    
    # Senkou Span A (Leading Span A): (Tenkan-sen + Kijun-sen) / 2, shifted 26 periods ahead
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)
    
    # Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2, shifted 26 periods ahead
    period52_high = high.rolling(window=52).max()
    period52_low = low.rolling(window=52).min()
    senkou_span_b = ((period52_high + period52_low) / 2).shift(26)
    
    # Chikou Span (Lagging Span): Close price shifted 26 periods back
    chikou_span = close.shift(-26)
    
    return {
        'tenkan_sen': tenkan_sen.fillna(0),
        'kijun_sen': kijun_sen.fillna(0),
        'senkou_span_a': senkou_span_a.fillna(0),
        'senkou_span_b': senkou_span_b.fillna(0),
        'chikou_span': chikou_span.fillna(0),
    }


def calculate_ichimoku_score(current_price: float, ichimoku: Dict[str, pd.Series], direction: str) -> float:
    """
    Score based on Ichimoku Cloud signals
    
    Args:
        current_price: Current market price
        ichimoku: Ichimoku components from calculate_ichimoku_cloud
        direction: Trade direction ('LONG' or 'SHORT')
        
    Returns:
        Score 0-100
    """
    # Get latest values
    tenkan = ichimoku['tenkan_sen'].iloc[-1] if len(ichimoku['tenkan_sen']) > 0 else 0
    kijun = ichimoku['kijun_sen'].iloc[-1] if len(ichimoku['kijun_sen']) > 0 else 0
    span_a = ichimoku['senkou_span_a'].iloc[-1] if len(ichimoku['senkou_span_a']) > 0 else 0
    span_b = ichimoku['senkou_span_b'].iloc[-1] if len(ichimoku['senkou_span_b']) > 0 else 0
    
    if tenkan == 0 or kijun == 0:
        return 50.0
    
    score = 0.0
    
    # Cloud position (most important)
    cloud_top = max(span_a, span_b)
    cloud_bottom = min(span_a, span_b)
    
    if direction.upper() == 'LONG':
        # Bullish signals
        # 1. Price above cloud (40 points)
        if current_price > cloud_top:
            score += 40.0
        elif current_price > cloud_bottom:
            score += 20.0  # Inside cloud
        
        # 2. Tenkan above Kijun (30 points)
        if tenkan > kijun:
            score += 30.0
        
        # 3. Bullish cloud (Span A > Span B) (30 points)
        if span_a > span_b:
            score += 30.0
            
    else:  # SHORT
        # Bearish signals
        # 1. Price below cloud (40 points)
        if current_price < cloud_bottom:
            score += 40.0
        elif current_price < cloud_top:
            score += 20.0  # Inside cloud
        
        # 2. Tenkan below Kijun (30 points)
        if tenkan < kijun:
            score += 30.0
        
        # 3. Bearish cloud (Span A < Span B) (30 points)
        if span_a < span_b:
            score += 30.0
    
    return float(max(0.0, min(100.0, score)))

