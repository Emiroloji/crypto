"""Volume-based indicators: OBV, VWAP"""

import pandas as pd
import numpy as np
from typing import Tuple


def calculate_obv(df: pd.DataFrame) -> pd.Series:
    """
    Calculate On-Balance Volume (OBV)
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        OBV Series
    """
    if len(df) < 2:
        return pd.Series([0] * len(df))
    
    obv = pd.Series(0.0, index=df.index)
    obv.iloc[0] = df['volume'].iloc[0]
    
    for i in range(1, len(df)):
        if df['close'].iloc[i] > df['close'].iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] + df['volume'].iloc[i]
        elif df['close'].iloc[i] < df['close'].iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] - df['volume'].iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i-1]
    
    return obv


def calculate_obv_score(df: pd.DataFrame, obv: pd.Series, direction: str) -> float:
    """
    Score based on OBV trend
    
    Args:
        df: DataFrame with OHLCV data
        obv: OBV Series from calculate_obv
        direction: Trade direction ('LONG' or 'SHORT')
        
    Returns:
        Score 0-100
    """
    if len(obv) < 20:
        return 50.0
    
    # Calculate OBV trend (20-period slope)
    recent_obv = obv.tail(20)
    x = np.arange(len(recent_obv))
    
    # Linear regression to find trend
    if len(x) > 1:
        slope = np.polyfit(x, recent_obv.values, 1)[0]
        
        # Normalize slope
        avg_obv = abs(recent_obv.mean())
        if avg_obv > 0:
            normalized_slope = (slope / avg_obv) * 100
        else:
            normalized_slope = 0
    else:
        normalized_slope = 0
    
    # Score based on direction
    if direction.upper() == 'LONG':
        # Positive OBV trend = bullish
        if normalized_slope > 0:
            score = min(100.0, 50 + normalized_slope * 10)
        else:
            score = max(0.0, 50 + normalized_slope * 10)
    else:  # SHORT
        # Negative OBV trend = bearish
        if normalized_slope < 0:
            score = min(100.0, 50 - normalized_slope * 10)
        else:
            score = max(0.0, 50 - normalized_slope * 10)
    
    return float(max(0.0, min(100.0, score)))


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Volume Weighted Average Price (VWAP)
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        VWAP Series
    """
    if len(df) == 0:
        return pd.Series([0] * len(df))
    
    # Typical price
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    
    # VWAP = Cumulative(Typical Price * Volume) / Cumulative(Volume)
    cumulative_tp_volume = (typical_price * df['volume']).cumsum()
    cumulative_volume = df['volume'].cumsum()
    
    vwap = cumulative_tp_volume / cumulative_volume
    
    return vwap.fillna(0)


def calculate_vwap_score(current_price: float, vwap_value: float, direction: str) -> float:
    """
    Score based on price position relative to VWAP
    
    Args:
        current_price: Current market price
        vwap_value: Current VWAP value
        direction: Trade direction ('LONG' or 'SHORT')
        
    Returns:
        Score 0-100
    """
    if vwap_value == 0:
        return 50.0
    
    # Calculate deviation from VWAP
    deviation = (current_price - vwap_value) / vwap_value * 100
    
    if direction.upper() == 'LONG':
        # For LONG: prefer price near or below VWAP (potential bounce)
        if deviation < -2:  # More than 2% below VWAP
            score = 100.0
        elif deviation < 0:  # Below VWAP
            score = 100.0 - abs(deviation) * 25
        elif deviation < 2:  # Slightly above VWAP
            score = 50.0 - deviation * 25
        else:  # Too far above VWAP
            score = 0.0
    else:  # SHORT
        # For SHORT: prefer price near or above VWAP (potential rejection)
        if deviation > 2:  # More than 2% above VWAP
            score = 100.0
        elif deviation > 0:  # Above VWAP
            score = 100.0 - deviation * 25
        elif deviation > -2:  # Slightly below VWAP
            score = 50.0 + abs(deviation) * 25
        else:  # Too far below VWAP
            score = 0.0
    
    return float(max(0.0, min(100.0, score)))
