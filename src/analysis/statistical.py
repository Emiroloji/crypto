"""Statistical and mathematical models for trading"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from sklearn.linear_model import LinearRegression


def calculate_linear_regression(df: pd.DataFrame, period: int = 50) -> Dict[str, float]:
    """
    Calculate linear regression trend
    
    Args:
        df: DataFrame with OHLCV data
        period: Regression period
        
    Returns:
        Dictionary with regression metrics
    """
    if len(df) < period:
        return {
            'slope': 0.0,
            'intercept': 0.0,
            'r_squared': 0.0,
            'predicted_price': 0.0,
            'upper_channel': 0.0,
            'lower_channel': 0.0,
        }
    
    recent = df.tail(period)
    close_prices = recent['close'].values
    
    # Prepare data for regression
    X = np.arange(len(close_prices)).reshape(-1, 1)
    y = close_prices
    
    # Fit linear regression
    model = LinearRegression()
    model.fit(X, y)
    
    # Get predictions
    predictions = model.predict(X)
    
    # Calculate R-squared
    ss_res = np.sum((y - predictions) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    # Calculate standard deviation for channel
    residuals = y - predictions
    std_dev = np.std(residuals)
    
    # Predict next price
    next_x = np.array([[len(close_prices)]])
    predicted_price = model.predict(next_x)[0]
    
    return {
        'slope': float(model.coef_[0]),
        'intercept': float(model.intercept_),
        'r_squared': float(r_squared),
        'predicted_price': float(predicted_price),
        'upper_channel': float(predicted_price + 2 * std_dev),
        'lower_channel': float(predicted_price - 2 * std_dev),
    }


def calculate_regression_score(current_price: float, regression: Dict[str, float], direction: str) -> float:
    """
    Score based on linear regression trend
    
    Args:
        current_price: Current market price
        regression: Regression metrics from calculate_linear_regression
        direction: Trade direction ('LONG' or 'SHORT')
        
    Returns:
        Score 0-100
    """
    slope = regression['slope']
    r_squared = regression['r_squared']
    predicted = regression['predicted_price']
    
    # Trend strength based on R-squared (how well price follows trend)
    trend_quality = r_squared * 100  # 0-100
    
    # Direction alignment
    if direction.upper() == 'LONG':
        # Prefer positive slope (uptrend)
        if slope > 0:
            slope_score = min(100.0, abs(slope) * 1000)  # Normalize slope
        else:
            slope_score = 0.0
            
        # Prefer price below predicted (potential bounce)
        price_position = (predicted - current_price) / current_price * 100
        if price_position > 0:  # Below predicted
            position_score = min(100.0, price_position * 50)
        else:
            position_score = 50.0
            
    else:  # SHORT
        # Prefer negative slope (downtrend)
        if slope < 0:
            slope_score = min(100.0, abs(slope) * 1000)
        else:
            slope_score = 0.0
            
        # Prefer price above predicted (potential rejection)
        price_position = (current_price - predicted) / current_price * 100
        if price_position > 0:  # Above predicted
            position_score = min(100.0, price_position * 50)
        else:
            position_score = 50.0
    
    # Combined score
    final_score = (trend_quality * 0.3 + slope_score * 0.4 + position_score * 0.3)
    
    return float(max(0.0, min(100.0, final_score)))


def detect_support_resistance(df: pd.DataFrame, lookback: int = 100, num_levels: int = 5) -> Dict[str, List[float]]:
    """
    Detect support and resistance levels using clustering
    
    Args:
        df: DataFrame with OHLCV data
        lookback: Period to analyze
        num_levels: Number of S/R levels to detect
        
    Returns:
        Dictionary with support and resistance levels
    """
    if len(df) < lookback:
        return {
            'support_levels': [],
            'resistance_levels': [],
        }
    
    recent = df.tail(lookback)
    
    # Find local highs and lows
    highs = []
    lows = []
    
    for i in range(2, len(recent) - 2):
        # Local high
        if (recent['high'].iloc[i] > recent['high'].iloc[i-1] and 
            recent['high'].iloc[i] > recent['high'].iloc[i-2] and
            recent['high'].iloc[i] > recent['high'].iloc[i+1] and 
            recent['high'].iloc[i] > recent['high'].iloc[i+2]):
            highs.append(recent['high'].iloc[i])
        
        # Local low
        if (recent['low'].iloc[i] < recent['low'].iloc[i-1] and 
            recent['low'].iloc[i] < recent['low'].iloc[i-2] and
            recent['low'].iloc[i] < recent['low'].iloc[i+1] and 
            recent['low'].iloc[i] < recent['low'].iloc[i+2]):
            lows.append(recent['low'].iloc[i])
    
    # Cluster levels (simple approach: group nearby levels)
    def cluster_levels(levels, tolerance=0.02):
        if not levels:
            return []
        
        levels = sorted(levels)
        clusters = []
        current_cluster = [levels[0]]
        
        for level in levels[1:]:
            if abs(level - current_cluster[-1]) / current_cluster[-1] < tolerance:
                current_cluster.append(level)
            else:
                clusters.append(np.mean(current_cluster))
                current_cluster = [level]
        
        clusters.append(np.mean(current_cluster))
        return sorted(clusters)
    
    resistance_levels = cluster_levels(highs)[:num_levels]
    support_levels = cluster_levels(lows)[:num_levels]
    
    return {
        'support_levels': [float(x) for x in support_levels],
        'resistance_levels': [float(x) for x in resistance_levels],
    }


def calculate_sr_score(current_price: float, sr_levels: Dict[str, List[float]], direction: str) -> float:
    """
    Score based on proximity to support/resistance levels
    
    Args:
        current_price: Current market price
        sr_levels: S/R levels from detect_support_resistance
        direction: Trade direction ('LONG' or 'SHORT')
        
    Returns:
        Score 0-100
    """
    support_levels = sr_levels['support_levels']
    resistance_levels = sr_levels['resistance_levels']
    
    if not support_levels and not resistance_levels:
        return 50.0
    
    if direction.upper() == 'LONG':
        # For LONG: prefer price near support
        if support_levels:
            distances = [abs(current_price - level) / current_price for level in support_levels]
            min_distance = min(distances)
            
            # Within 1% of support = 100, Within 3% = 50, Beyond = 0
            if min_distance < 0.01:
                score = 100.0
            elif min_distance < 0.03:
                score = 100.0 - (min_distance - 0.01) * 2500
            else:
                score = 0.0
        else:
            score = 50.0
            
    else:  # SHORT
        # For SHORT: prefer price near resistance
        if resistance_levels:
            distances = [abs(current_price - level) / current_price for level in resistance_levels]
            min_distance = min(distances)
            
            # Within 1% of resistance = 100, Within 3% = 50, Beyond = 0
            if min_distance < 0.01:
                score = 100.0
            elif min_distance < 0.03:
                score = 100.0 - (min_distance - 0.01) * 2500
            else:
                score = 0.0
        else:
            score = 50.0
    
    return float(max(0.0, min(100.0, score)))
