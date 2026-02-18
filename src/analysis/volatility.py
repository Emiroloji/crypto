"""Volatility forecasting and analysis"""

import pandas as pd
import numpy as np
from typing import Dict


def calculate_historical_volatility(df: pd.DataFrame, period: int = 20) -> float:
    """
    Calculate historical volatility (standard deviation of returns)
    
    Args:
        df: DataFrame with OHLCV data
        period: Calculation period
        
    Returns:
        Annualized volatility percentage
    """
    if len(df) < period:
        return 0.0
    
    # Calculate returns
    returns = df['close'].pct_change().tail(period)
    
    # Standard deviation of returns
    volatility = returns.std()
    
    # Annualize (assuming 365 trading days for crypto)
    annualized_vol = volatility * np.sqrt(365) * 100
    
    return float(annualized_vol) if not np.isnan(annualized_vol) else 0.0


def forecast_volatility_simple(df: pd.DataFrame, period: int = 20, forecast_days: int = 5) -> Dict[str, float]:
    """
    Simple volatility forecast using EWMA
    
    Args:
        df: DataFrame with OHLCV data
        period: Historical period
        forecast_days: Days to forecast
        
    Returns:
        Dictionary with volatility metrics
    """
    if len(df) < period:
        return {
            'current_volatility': 0.0,
            'forecasted_volatility': 0.0,
            'volatility_trend': 0.0,
        }
    
    # Calculate returns
    returns = df['close'].pct_change()
    
    # Current volatility (EWMA)
    ewma_vol = returns.ewm(span=period).std().iloc[-1] * np.sqrt(365) * 100
    
    # Vectorized rolling volatility forecast (replaces manual loop)
    window_sizes = range(5, min(20, len(df)))
    if window_sizes:
        recent_vols = [
            returns.tail(w).std() * np.sqrt(365) * 100
            for w in window_sizes
        ]
        weights = np.exp(np.linspace(-1, 0, len(recent_vols)))
        weights /= weights.sum()
        forecasted_vol = float(np.average(recent_vols, weights=weights))
        vol_trend = (
            (recent_vols[-1] - recent_vols[0]) / recent_vols[0] * 100
            if recent_vols[0] > 0 else 0.0
        )
    else:
        forecasted_vol = float(ewma_vol)
        vol_trend = 0.0
    
    return {
        'current_volatility': float(ewma_vol) if not np.isnan(ewma_vol) else 0.0,
        'forecasted_volatility': float(forecasted_vol) if not np.isnan(forecasted_vol) else 0.0,
        'volatility_trend': float(vol_trend) if not np.isnan(vol_trend) else 0.0,
    }


def calculate_volatility_score(volatility_metrics: Dict[str, float], direction: str) -> float:
    """
    Score based on volatility forecast
    
    Args:
        volatility_metrics: Metrics from forecast_volatility_simple
        direction: Trade direction ('LONG' or 'SHORT')
        
    Returns:
        Score 0-100
    """
    current_vol = volatility_metrics['current_volatility']
    forecasted_vol = volatility_metrics['forecasted_volatility']
    vol_trend = volatility_metrics['volatility_trend']
    
    # Volatility interpretation:
    # Low volatility (< 30%): Consolidation, potential breakout
    # Medium volatility (30-70%): Normal trading
    # High volatility (> 70%): Risky, potential reversal
    
    # Base score from volatility level
    if current_vol < 30:
        base_score = 70.0  # Low vol - good for entries
    elif current_vol < 70:
        base_score = 100.0  # Medium vol - ideal
    else:
        base_score = 30.0  # High vol - risky
    
    # Adjust for volatility trend
    if direction.upper() == 'LONG':
        # For LONG: prefer stable or decreasing volatility
        if vol_trend < -10:
            trend_bonus = 20.0  # Volatility decreasing
        elif vol_trend < 10:
            trend_bonus = 10.0  # Stable
        else:
            trend_bonus = -20.0  # Volatility increasing - risky
    else:  # SHORT
        # For SHORT: can handle increasing volatility
        if vol_trend > 10:
            trend_bonus = 10.0  # Volatility increasing
        elif vol_trend > -10:
            trend_bonus = 5.0  # Stable
        else:
            trend_bonus = -10.0  # Volatility decreasing
    
    final_score = base_score + trend_bonus
    
    return float(max(0.0, min(100.0, final_score)))
