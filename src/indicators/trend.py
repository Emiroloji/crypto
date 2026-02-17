"""Trend indicators: EMA, VWAP, Supertrend, Ichimoku, ADX"""

import pandas as pd
import numpy as np
from typing import Tuple

from src.config.constants import INDICATOR_PARAMS


def calculate_ema(df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
    """
    Calculate Exponential Moving Average
    
    Args:
        df: DataFrame with price data
        period: EMA period
        column: Column to calculate EMA on
        
    Returns:
        EMA series
    """
    return df[column].ewm(span=period, adjust=False).mean()


def calculate_multiple_emas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate multiple EMAs
    
    Args:
        df: DataFrame with price data
        
    Returns:
        DataFrame with EMA columns
    """
    result = df.copy()
    for period in INDICATOR_PARAMS['ema_periods']:
        result[f'ema_{period}'] = calculate_ema(df, period)
    return result


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Volume Weighted Average Price
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        VWAP series
    """
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    return (typical_price * df['volume']).cumsum() / df['volume'].cumsum()


def calculate_supertrend(
    df: pd.DataFrame,
    period: int = None,
    multiplier: float = None
) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate Supertrend indicator
    
    Args:
        df: DataFrame with OHLCV data
        period: ATR period
        multiplier: ATR multiplier
        
    Returns:
        Tuple of (supertrend, direction)
    """
    period = period or INDICATOR_PARAMS['supertrend_period']
    multiplier = multiplier or INDICATOR_PARAMS['supertrend_multiplier']
    
    # Calculate ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    atr = true_range.rolling(period).mean()
    
    # Calculate basic bands
    hl_avg = (df['high'] + df['low']) / 2
    upper_band = hl_avg + (multiplier * atr)
    lower_band = hl_avg - (multiplier * atr)
    
    # Initialize
    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    
    for i in range(period, len(df)):
        if i == period:
            supertrend.iloc[i] = lower_band.iloc[i]
            direction.iloc[i] = 1
        else:
            # Uptrend
            if direction.iloc[i-1] == 1:
                if df['close'].iloc[i] <= supertrend.iloc[i-1]:
                    supertrend.iloc[i] = upper_band.iloc[i]
                    direction.iloc[i] = -1
                else:
                    supertrend.iloc[i] = max(lower_band.iloc[i], supertrend.iloc[i-1])
                    direction.iloc[i] = 1
            # Downtrend
            else:
                if df['close'].iloc[i] >= supertrend.iloc[i-1]:
                    supertrend.iloc[i] = lower_band.iloc[i]
                    direction.iloc[i] = 1
                else:
                    supertrend.iloc[i] = min(upper_band.iloc[i], supertrend.iloc[i-1])
                    direction.iloc[i] = -1
    
    return supertrend, direction


def calculate_ichimoku(df: pd.DataFrame) -> dict:
    """
    Calculate Ichimoku Cloud components
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        Dictionary with Ichimoku components
    """
    # Tenkan-sen (Conversion Line): (9-period high + 9-period low)/2
    period9_high = df['high'].rolling(window=9).max()
    period9_low = df['low'].rolling(window=9).min()
    tenkan_sen = (period9_high + period9_low) / 2
    
    # Kijun-sen (Base Line): (26-period high + 26-period low)/2
    period26_high = df['high'].rolling(window=26).max()
    period26_low = df['low'].rolling(window=26).min()
    kijun_sen = (period26_high + period26_low) / 2
    
    # Senkou Span A (Leading Span A): (Conversion Line + Base Line)/2
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)
    
    # Senkou Span B (Leading Span B): (52-period high + 52-period low)/2
    period52_high = df['high'].rolling(window=52).max()
    period52_low = df['low'].rolling(window=52).min()
    senkou_span_b = ((period52_high + period52_low) / 2).shift(26)
    
    # Chikou Span (Lagging Span): Current closing price shifted back 26 periods
    chikou_span = df['close'].shift(-26)
    
    return {
        'tenkan_sen': tenkan_sen,
        'kijun_sen': kijun_sen,
        'senkou_span_a': senkou_span_a,
        'senkou_span_b': senkou_span_b,
        'chikou_span': chikou_span,
    }


def calculate_adx(df: pd.DataFrame, period: int = None) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Average Directional Index (ADX)
    
    Args:
        df: DataFrame with OHLCV data
        period: ADX period
        
    Returns:
        Tuple of (ADX, +DI, -DI)
    """
    period = period or INDICATOR_PARAMS['adx_period']
    
    # Calculate True Range
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    
    # Calculate Directional Movement
    up_move = df['high'] - df['high'].shift()
    down_move = df['low'].shift() - df['low']
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    
    # Smooth the values
    atr = true_range.rolling(window=period).mean()
    plus_di = 100 * (pd.Series(plus_dm).rolling(window=period).mean() / atr)
    minus_di = 100 * (pd.Series(minus_dm).rolling(window=period).mean() / atr)
    
    # Calculate ADX
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return adx, plus_di, minus_di


def get_trend_signals(df: pd.DataFrame) -> dict:
    """
    Generate trend signals from all trend indicators
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        Dictionary with trend signals and scores
    """
    signals = {}
    
    # EMA trend
    df_ema = calculate_multiple_emas(df)
    current_price = df['close'].iloc[-1]
    ema_9 = df_ema['ema_9'].iloc[-1]
    ema_21 = df_ema['ema_21'].iloc[-1]
    ema_50 = df_ema['ema_50'].iloc[-1]
    
    ema_bullish = (current_price > ema_9 > ema_21 > ema_50)
    ema_bearish = (current_price < ema_9 < ema_21 < ema_50)
    signals['ema_trend'] = 1 if ema_bullish else (-1 if ema_bearish else 0)
    
    # VWAP
    vwap = calculate_vwap(df).iloc[-1]
    signals['vwap_position'] = 1 if current_price > vwap else -1
    
    # Supertrend
    supertrend, st_direction = calculate_supertrend(df)
    signals['supertrend_direction'] = int(st_direction.iloc[-1])
    
    # ADX
    adx, plus_di, minus_di = calculate_adx(df)
    adx_value = adx.iloc[-1]
    signals['adx_strength'] = adx_value
    signals['adx_trending'] = adx_value > INDICATOR_PARAMS['adx_threshold']
    signals['di_direction'] = 1 if plus_di.iloc[-1] > minus_di.iloc[-1] else -1
    
    # Ichimoku
    ichimoku = calculate_ichimoku(df)
    tenkan = ichimoku['tenkan_sen'].iloc[-1]
    kijun = ichimoku['kijun_sen'].iloc[-1]
    senkou_a = ichimoku['senkou_span_a'].iloc[-1]
    senkou_b = ichimoku['senkou_span_b'].iloc[-1]
    
    # Price above cloud = bullish, below = bearish
    cloud_top = max(senkou_a, senkou_b) if not pd.isna(senkou_a) and not pd.isna(senkou_b) else None
    cloud_bottom = min(senkou_a, senkou_b) if not pd.isna(senkou_a) and not pd.isna(senkou_b) else None
    
    if cloud_top and cloud_bottom:
        if current_price > cloud_top:
            signals['ichimoku_position'] = 1
        elif current_price < cloud_bottom:
            signals['ichimoku_position'] = -1
        else:
            signals['ichimoku_position'] = 0
    else:
        signals['ichimoku_position'] = 0
    
    # Overall trend score (-100 to 100)
    trend_score = 0
    trend_score += signals['ema_trend'] * 30
    trend_score += signals['vwap_position'] * 20
    trend_score += signals['supertrend_direction'] * 25
    trend_score += signals['di_direction'] * 15
    trend_score += signals['ichimoku_position'] * 10
    
    signals['trend_score'] = trend_score
    
    return signals
