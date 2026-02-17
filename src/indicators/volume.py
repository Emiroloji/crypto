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
