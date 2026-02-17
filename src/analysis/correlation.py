"""Correlation analysis for crypto assets"""

import pandas as pd
import numpy as np
from typing import Dict, List


def calculate_btc_correlation(df: pd.DataFrame, btc_df: pd.DataFrame, period: int = 30) -> float:
    """
    Calculate correlation between asset and BTC
    
    Args:
        df: Asset DataFrame with OHLCV data
        btc_df: BTC DataFrame with OHLCV data
        period: Correlation period
        
    Returns:
        Correlation coefficient (-1 to 1)
    """
    if len(df) < period or len(btc_df) < period:
        return 0.0
    
    # Get returns
    asset_returns = df['close'].pct_change().tail(period)
    btc_returns = btc_df['close'].pct_change().tail(period)
    
    # Calculate correlation
    correlation = asset_returns.corr(btc_returns)
    
    return float(correlation) if not np.isnan(correlation) else 0.0


def calculate_correlation_score(correlation: float, direction: str) -> float:
    """
    Score based on BTC correlation
    
    Args:
        correlation: Correlation coefficient
        direction: Trade direction ('LONG' or 'SHORT')
        
    Returns:
        Score 0-100
    """
    # High correlation means asset follows BTC
    # Low/negative correlation means divergence
    
    abs_corr = abs(correlation)
    
    if direction.upper() == 'LONG':
        # For LONG: prefer positive correlation (follows BTC uptrend)
        if correlation > 0.7:
            score = 100.0  # Strong positive correlation
        elif correlation > 0.3:
            score = 50.0 + (correlation - 0.3) * 125  # 50-100
        elif correlation > -0.3:
            score = 50.0  # Neutral
        else:
            score = 0.0  # Negative correlation - risky for LONG
    else:  # SHORT
        # For SHORT: prefer negative correlation or low correlation
        if correlation < -0.7:
            score = 100.0  # Strong negative correlation
        elif correlation < -0.3:
            score = 50.0 + abs(correlation + 0.3) * 125  # 50-100
        elif correlation < 0.3:
            score = 50.0  # Neutral/low correlation
        else:
            score = 0.0  # Positive correlation - risky for SHORT
    
    return float(max(0.0, min(100.0, score)))


def detect_divergence(df: pd.DataFrame, btc_df: pd.DataFrame, lookback: int = 20) -> Dict[str, bool]:
    """
    Detect price divergence between asset and BTC
    
    Args:
        df: Asset DataFrame
        btc_df: BTC DataFrame
        lookback: Period to check
        
    Returns:
        Dictionary with divergence flags
    """
    if len(df) < lookback or len(btc_df) < lookback:
        return {
            'bullish_divergence': False,
            'bearish_divergence': False,
        }
    
    recent_asset = df.tail(lookback)
    recent_btc = btc_df.tail(lookback)
    
    # Price trends
    asset_trend = recent_asset['close'].iloc[-1] - recent_asset['close'].iloc[0]
    btc_trend = recent_btc['close'].iloc[-1] - recent_btc['close'].iloc[0]
    
    # Bullish divergence: BTC down, Asset up
    bullish_div = btc_trend < 0 and asset_trend > 0
    
    # Bearish divergence: BTC up, Asset down
    bearish_div = btc_trend > 0 and asset_trend < 0
    
    return {
        'bullish_divergence': bullish_div,
        'bearish_divergence': bearish_div,
    }
