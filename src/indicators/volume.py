"""Volume and order flow indicators"""

import pandas as pd
import numpy as np
from typing import Optional

from src.config.constants import INDICATOR_PARAMS, ORDER_BOOK_PARAMS


def calculate_volume_delta(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Volume Delta (buy volume - sell volume approximation)
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        Volume delta series
    """
    # Approximate buy/sell volume based on price movement
    # If close > open: buying pressure, else selling pressure
    buy_volume = df['volume'].where(df['close'] > df['open'], 0)
    sell_volume = df['volume'].where(df['close'] <= df['open'], 0)
    
    volume_delta = buy_volume - sell_volume
    
    return volume_delta


def calculate_cvd(df: pd.DataFrame, lookback: int = None) -> pd.Series:
    """
    Calculate Cumulative Volume Delta
    
    Args:
        df: DataFrame with OHLCV data
        lookback: Lookback period for cumulative sum
        
    Returns:
        CVD series
    """
    lookback = lookback or INDICATOR_PARAMS['cvd_lookback']
    
    volume_delta = calculate_volume_delta(df)
    cvd = volume_delta.rolling(window=lookback).sum()
    
    return cvd


def analyze_order_book_imbalance(order_book_data: dict) -> dict:
    """
    Analyze order book imbalance
    
    Args:
        order_book_data: Order book data with bids and asks
        
    Returns:
        Dictionary with imbalance metrics
    """
    if not order_book_data:
        return {
            'imbalance_ratio': 1.0,
            'imbalance_signal': 0,
            'bid_volume': 0,
            'ask_volume': 0,
        }
    
    bids = order_book_data.get('bids', [])
    asks = order_book_data.get('asks', [])
    
    # Calculate total volume at each side
    bid_volume = sum([bid[1] for bid in bids[:ORDER_BOOK_PARAMS['depth_levels']]])
    ask_volume = sum([ask[1] for ask in asks[:ORDER_BOOK_PARAMS['depth_levels']]])
    
    # Imbalance ratio
    imbalance_ratio = bid_volume / ask_volume if ask_volume > 0 else 1.0
    
    # Signal: 1 (bullish), -1 (bearish), 0 (neutral)
    threshold = ORDER_BOOK_PARAMS['imbalance_threshold']
    if imbalance_ratio > threshold:
        imbalance_signal = 1  # More bids = bullish
    elif imbalance_ratio < (1 / threshold):
        imbalance_signal = -1  # More asks = bearish
    else:
        imbalance_signal = 0
    
    return {
        'imbalance_ratio': imbalance_ratio,
        'imbalance_signal': imbalance_signal,
        'bid_volume': bid_volume,
        'ask_volume': ask_volume,
    }


def detect_large_orders(order_book_data: dict) -> dict:
    """
    Detect large orders in order book
    
    Args:
        order_book_data: Order book data
        
    Returns:
        Dictionary with large order information
    """
    if not order_book_data:
        return {
            'large_bids': [],
            'large_asks': [],
            'has_large_orders': False,
        }
    
    bids = order_book_data.get('bids', [])
    asks = order_book_data.get('asks', [])
    threshold = ORDER_BOOK_PARAMS['large_order_threshold']
    
    # Find large orders (price * quantity > threshold)
    large_bids = [
        {'price': bid[0], 'quantity': bid[1], 'value': bid[0] * bid[1]}
        for bid in bids
        if bid[0] * bid[1] > threshold
    ]
    
    large_asks = [
        {'price': ask[0], 'quantity': ask[1], 'value': ask[0] * ask[1]}
        for ask in asks
        if ask[0] * ask[1] > threshold
    ]
    
    return {
        'large_bids': large_bids,
        'large_asks': large_asks,
        'has_large_orders': len(large_bids) > 0 or len(large_asks) > 0,
    }


def analyze_spread_anomaly(order_book_data: dict, avg_spread: float) -> dict:
    """
    Detect spread anomalies
    
    Args:
        order_book_data: Order book data
        avg_spread: Average spread for comparison
        
    Returns:
        Dictionary with spread anomaly information
    """
    if not order_book_data or not avg_spread:
        return {
            'current_spread': 0,
            'is_anomaly': False,
            'spread_ratio': 1.0,
        }
    
    current_spread = order_book_data.get('bid_ask_spread', 0)
    spread_ratio = current_spread / avg_spread if avg_spread > 0 else 1.0
    
    # Anomaly if spread is significantly wider than average
    is_anomaly = spread_ratio > ORDER_BOOK_PARAMS['spread_anomaly_multiplier']
    
    return {
        'current_spread': current_spread,
        'is_anomaly': is_anomaly,
        'spread_ratio': spread_ratio,
    }


def get_volume_signals(df: pd.DataFrame, order_book_data: Optional[dict] = None) -> dict:
    """
    Generate volume and order flow signals
    
    Args:
        df: DataFrame with OHLCV data
        order_book_data: Optional order book data
        
    Returns:
        Dictionary with volume signals and scores
    """
    signals = {}
    
    # Volume analysis
    current_volume = df['volume'].iloc[-1]
    avg_volume = df['volume'].rolling(window=INDICATOR_PARAMS['volume_ma_period']).mean().iloc[-1]
    
    signals['current_volume'] = current_volume
    signals['avg_volume'] = avg_volume
    signals['volume_ratio'] = current_volume / avg_volume if avg_volume > 0 else 1.0
    signals['high_volume'] = signals['volume_ratio'] > 1.5
    
    # Volume Delta
    volume_delta = calculate_volume_delta(df)
    signals['volume_delta'] = volume_delta.iloc[-1]
    signals['volume_delta_positive'] = volume_delta.iloc[-1] > 0
    
    # Cumulative Volume Delta
    cvd = calculate_cvd(df)
    signals['cvd'] = cvd.iloc[-1]
    signals['cvd_trend'] = 1 if cvd.iloc[-1] > cvd.iloc[-5] else -1  # Compare with 5 periods ago
    
    # Order book analysis (if available)
    if order_book_data:
        imbalance = analyze_order_book_imbalance(order_book_data)
        signals['orderbook_imbalance_ratio'] = imbalance['imbalance_ratio']
        signals['orderbook_imbalance_signal'] = imbalance['imbalance_signal']
        signals['bid_volume'] = imbalance['bid_volume']
        signals['ask_volume'] = imbalance['ask_volume']
        
        large_orders = detect_large_orders(order_book_data)
        signals['has_large_orders'] = large_orders['has_large_orders']
        signals['large_bids_count'] = len(large_orders['large_bids'])
        signals['large_asks_count'] = len(large_orders['large_asks'])
    else:
        signals['orderbook_imbalance_ratio'] = 1.0
        signals['orderbook_imbalance_signal'] = 0
        signals['has_large_orders'] = False
    
    # Volume score (-100 to 100)
    volume_score = 0
    
    # High volume confirmation (30 points)
    if signals['high_volume']:
        volume_score += 30
    
    # Volume delta (25 points)
    if signals['volume_delta_positive']:
        volume_score += 25
    else:
        volume_score -= 25
    
    # CVD trend (25 points)
    volume_score += signals['cvd_trend'] * 25
    
    # Order book imbalance (20 points)
    volume_score += signals['orderbook_imbalance_signal'] * 20
    
    signals['volume_score'] = np.clip(volume_score, -100, 100)
    
    return signals


# ─── OBV and VWAP ────────────────────────────────────────────────────────────

def calculate_obv(df: pd.DataFrame) -> pd.Series:
    """
    Calculate On-Balance Volume (OBV)

    Args:
        df: DataFrame with OHLCV data

    Returns:
        OBV Series
    """
    if len(df) < 2:
        return pd.Series([0] * len(df), index=df.index)

    # Vectorized OBV: direction = sign of close change, multiply by volume, cumsum
    direction = np.sign(df['close'].diff()).fillna(0)
    obv = (direction * df['volume']).cumsum()
    # First bar: seed with its own volume (no previous close to compare)
    obv.iloc[0] = df['volume'].iloc[0]

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

    recent_obv = obv.tail(20)
    x = np.arange(len(recent_obv))

    if len(x) > 1:
        slope = np.polyfit(x, recent_obv.values, 1)[0]
        avg_obv = abs(recent_obv.mean())
        normalized_slope = (slope / avg_obv) * 100 if avg_obv > 0 else 0
    else:
        normalized_slope = 0

    if direction.upper() == 'LONG':
        score = min(100.0, 50 + normalized_slope * 10) if normalized_slope > 0 else max(0.0, 50 + normalized_slope * 10)
    else:
        score = min(100.0, 50 - normalized_slope * 10) if normalized_slope < 0 else max(0.0, 50 - normalized_slope * 10)

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

    typical_price = (df['high'] + df['low'] + df['close']) / 3
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

    deviation = (current_price - vwap_value) / vwap_value * 100

    if direction.upper() == 'LONG':
        if deviation < -2:
            score = 100.0
        elif deviation < 0:
            score = 100.0 - abs(deviation) * 25
        elif deviation < 2:
            score = 50.0 - deviation * 25
        else:
            score = 0.0
    else:
        if deviation > 2:
            score = 100.0
        elif deviation > 0:
            score = 100.0 - deviation * 25
        elif deviation > -2:
            score = 50.0 + abs(deviation) * 25
        else:
            score = 0.0

    return float(max(0.0, min(100.0, score)))
