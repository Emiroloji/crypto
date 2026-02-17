"""Volatility indicators: ATR, Bollinger Bands, Keltner Channels"""

import pandas as pd
import numpy as np
from typing import Tuple

from src.config.constants import INDICATOR_PARAMS


def calculate_atr(df: pd.DataFrame, period: int = None) -> pd.Series:
    """
    Calculate Average True Range
    
    Args:
        df: DataFrame with OHLCV data
        period: ATR period
        
    Returns:
        ATR series
    """
    period = period or INDICATOR_PARAMS['atr_period']
    
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    atr = true_range.rolling(window=period).mean()
    
    return atr


def calculate_bollinger_bands(
    df: pd.DataFrame,
    period: int = None,
    std_dev: float = None
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands
    
    Args:
        df: DataFrame with price data
        period: Period for moving average
        std_dev: Number of standard deviations
        
    Returns:
        Tuple of (upper band, middle band, lower band)
    """
    period = period or INDICATOR_PARAMS['bb_period']
    std_dev = std_dev or INDICATOR_PARAMS['bb_std']
    
    middle_band = df['close'].rolling(window=period).mean()
    std = df['close'].rolling(window=period).std()
    
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)
    
    return upper_band, middle_band, lower_band


def detect_bb_squeeze(df: pd.DataFrame, lookback: int = 20) -> dict:
    """
    Detect Bollinger Bands squeeze
    
    Args:
        df: DataFrame with price data
        lookback: Lookback period
        
    Returns:
        Dictionary with squeeze information
    """
    upper, middle, lower = calculate_bollinger_bands(df)
    
    # Calculate bandwidth
    bandwidth = (upper - lower) / middle
    
    # Squeeze detected when bandwidth is at multi-period low
    current_bandwidth = bandwidth.iloc[-1]
    min_bandwidth = bandwidth.tail(lookback).min()
    avg_bandwidth = bandwidth.tail(lookback).mean()
    
    is_squeeze = current_bandwidth <= min_bandwidth * 1.1  # Within 10% of minimum
    
    return {
        'is_squeeze': is_squeeze,
        'bandwidth': current_bandwidth,
        'bandwidth_percentile': (bandwidth.tail(lookback) < current_bandwidth).sum() / lookback * 100,
    }


def calculate_keltner_channels(
    df: pd.DataFrame,
    period: int = None,
    multiplier: float = None
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Keltner Channels
    
    Args:
        df: DataFrame with OHLCV data
        period: Period for EMA and ATR
        multiplier: ATR multiplier
        
    Returns:
        Tuple of (upper channel, middle channel, lower channel)
    """
    period = period or INDICATOR_PARAMS['keltner_period']
    multiplier = multiplier or INDICATOR_PARAMS['keltner_multiplier']
    
    middle_channel = df['close'].ewm(span=period, adjust=False).mean()
    atr = calculate_atr(df, period)
    
    upper_channel = middle_channel + (atr * multiplier)
    lower_channel = middle_channel - (atr * multiplier)
    
    return upper_channel, middle_channel, lower_channel


def calculate_historical_volatility(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    Calculate historical volatility (annualized)
    
    Args:
        df: DataFrame with price data
        period: Lookback period
        
    Returns:
        Historical volatility series
    """
    log_returns = np.log(df['close'] / df['close'].shift(1))
    volatility = log_returns.rolling(window=period).std() * np.sqrt(365 * 24 * 60)  # Annualized for 1-min data
    
    return volatility


def get_volatility_regime(df: pd.DataFrame, lookback: int = 100) -> str:
    """
    Determine current volatility regime
    
    Args:
        df: DataFrame with price data
        lookback: Lookback period for percentile calculation
        
    Returns:
        Volatility regime: 'low', 'normal', or 'high'
    """
    hv = calculate_historical_volatility(df)
    
    if len(hv) < lookback:
        return 'normal'
    
    current_hv = hv.iloc[-1]
    hv_percentile = (hv.tail(lookback) < current_hv).sum() / lookback * 100
    
    if hv_percentile < 25:
        return 'low'
    elif hv_percentile > 75:
        return 'high'
    else:
        return 'normal'


def get_volatility_signals(df: pd.DataFrame) -> dict:
    """
    Generate volatility signals from all volatility indicators
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        Dictionary with volatility signals and scores
    """
    signals = {}
    
    # ATR
    atr = calculate_atr(df)
    atr_value = atr.iloc[-1]
    signals['atr_value'] = atr_value
    
    # ATR as percentage of price
    current_price = df['close'].iloc[-1]
    signals['atr_percent'] = (atr_value / current_price) * 100
    
    # Bollinger Bands
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(df)
    signals['bb_upper'] = bb_upper.iloc[-1]
    signals['bb_middle'] = bb_middle.iloc[-1]
    signals['bb_lower'] = bb_lower.iloc[-1]
    
    # Price position relative to BB
    bb_position = (current_price - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])
    signals['bb_position'] = bb_position  # 0 = lower band, 1 = upper band
    
    # BB Squeeze
    squeeze_data = detect_bb_squeeze(df)
    signals['bb_squeeze'] = squeeze_data['is_squeeze']
    signals['bb_bandwidth_percentile'] = squeeze_data['bandwidth_percentile']
    
    # Keltner Channels
    kc_upper, kc_middle, kc_lower = calculate_keltner_channels(df)
    signals['kc_upper'] = kc_upper.iloc[-1]
    signals['kc_middle'] = kc_middle.iloc[-1]
    signals['kc_lower'] = kc_lower.iloc[-1]
    
    # Historical Volatility
    hv = calculate_historical_volatility(df)
    signals['historical_volatility'] = hv.iloc[-1]
    
    # Volatility Regime
    regime = get_volatility_regime(df)
    signals['volatility_regime'] = regime
    
    # Volatility score (-100 to 100)
    # High volatility = good for trading, low volatility = poor conditions
    volatility_score = 0
    
    if regime == 'high':
        volatility_score += 40
    elif regime == 'low':
        volatility_score -= 40
    
    # BB squeeze suggests upcoming volatility expansion
    if signals['bb_squeeze']:
        volatility_score += 30
    
    # Price near BB extremes
    if bb_position > 0.9:
        volatility_score += 15  # Near upper band, potential reversal
    elif bb_position < 0.1:
        volatility_score += 15  # Near lower band, potential reversal
    
    # Bandwidth percentile
    if signals['bb_bandwidth_percentile'] < 20:
        volatility_score += 15  # Low bandwidth, expect expansion
    
    signals['volatility_score'] = np.clip(volatility_score, -100, 100)
    
    return signals
