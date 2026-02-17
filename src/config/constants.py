"""System constants and indicator parameters"""

from typing import Dict, Any

# Indicator Parameters
INDICATOR_PARAMS: Dict[str, Any] = {
    # Trend Indicators
    "ema_periods": [9, 21, 50, 200],
    "supertrend_period": 10,
    "supertrend_multiplier": 3.0,
    "adx_period": 14,
    "adx_threshold": 25,
    
    # Momentum Indicators
    "rsi_period": 14,
    "rsi_overbought": 70,
    "rsi_oversold": 30,
    "stoch_rsi_period": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "cci_period": 20,
    
    # Volatility Indicators
    "atr_period": 14,
    "bb_period": 20,
    "bb_std": 2.0,
    "keltner_period": 20,
    "keltner_multiplier": 2.0,
    
    # Volume Indicators
    "volume_ma_period": 20,
    "cvd_lookback": 100,
}

# Signal Weights (must sum to 100%)
SIGNAL_WEIGHTS: Dict[str, float] = {
    "trend_confirmation": 0.20,      # 20%
    "momentum_alignment": 0.15,      # 15%
    "volume_confirmation": 0.20,     # 20%
    "order_book_imbalance": 0.15,    # 15%
    "volatility_regime": 0.10,       # 10%
    "sentiment_score": 0.10,         # 10%
    "onchain_data": 0.10,            # 10%
}

# Risk Management Constants
RISK_CONSTANTS: Dict[str, Any] = {
    "atr_stop_multiplier": 2.0,      # Stop loss = ATR * multiplier
    "trailing_stop_multiplier": 1.5,  # Trailing stop = ATR * multiplier
    "breakeven_trigger": 1.0,        # Move to breakeven at 1:1 R/R
    "partial_take_profit": 0.5,      # Take 50% profit at 1:1.5 R/R
    "max_position_hold_hours": 24,   # Max hours to hold position
}

# Market Regime Thresholds
REGIME_THRESHOLDS: Dict[str, Any] = {
    "trending_adx_min": 25,
    "ranging_adx_max": 20,
    "high_volatility_percentile": 75,
    "low_volatility_percentile": 25,
    "chop_threshold": 38.2,          # Choppiness Index threshold
}

# Order Book Analysis
ORDER_BOOK_PARAMS: Dict[str, Any] = {
    "depth_levels": 20,              # Number of order book levels to analyze
    "imbalance_threshold": 1.5,      # Bid/ask imbalance ratio threshold
    "large_order_threshold": 10000,  # USD value for large order detection
    "spread_anomaly_multiplier": 2.0, # Spread > avg_spread * multiplier
}

# Sentiment Analysis
SENTIMENT_PARAMS: Dict[str, Any] = {
    "twitter_lookback_hours": 4,
    "reddit_lookback_hours": 6,
    "news_lookback_hours": 2,
    "sentiment_decay_hours": 1,      # Half-life for sentiment score decay
    "min_sentiment_sources": 3,      # Minimum sources for valid sentiment
}

# On-Chain Analysis
ONCHAIN_PARAMS: Dict[str, Any] = {
    "whale_threshold_btc": 10,       # BTC amount for whale classification
    "whale_threshold_eth": 100,      # ETH amount for whale classification
    "exchange_flow_threshold": 1000000, # USD value for significant flow
}

# Timeframe Mappings
TIMEFRAME_MINUTES: Dict[str, int] = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
}

# Exchange Configuration
EXCHANGE_CONFIG: Dict[str, Any] = {
    "binance": {
        "testnet": "https://testnet.binancefuture.com",
        "mainnet": "https://fapi.binance.com",
        "rate_limit": 1200,  # requests per minute
    },
    "bybit": {
        "testnet": "https://api-testnet.bybit.com",
        "mainnet": "https://api.bybit.com",
        "rate_limit": 600,   # requests per minute
    },
}

# WebSocket Configuration
WEBSOCKET_CONFIG: Dict[str, Any] = {
    "reconnect_delay": 5,            # seconds
    "max_reconnect_attempts": 10,
    "ping_interval": 20,             # seconds
    "ping_timeout": 10,              # seconds
}

# Database Configuration
DATABASE_CONFIG: Dict[str, Any] = {
    "pool_size": 10,
    "max_overflow": 20,
    "pool_timeout": 30,
    "pool_recycle": 3600,
}

# Cache Configuration
CACHE_CONFIG: Dict[str, Any] = {
    "market_data_ttl": 60,           # seconds
    "indicator_ttl": 300,            # seconds
    "sentiment_ttl": 600,            # seconds
    "onchain_ttl": 1800,             # seconds
}

# Machine Learning Configuration
ML_CONFIG: Dict[str, Any] = {
    "training_lookback_days": 90,
    "validation_split": 0.2,
    "walk_forward_window": 30,       # days
    "min_training_samples": 1000,
    "feature_importance_threshold": 0.01,
}

# Alert Thresholds
ALERT_THRESHOLDS: Dict[str, Any] = {
    "high_confidence_signal": 85.0,
    "daily_loss_warning": 3.0,       # % of capital
    "daily_loss_critical": 4.5,      # % of capital
    "consecutive_losses": 5,
    "drawdown_warning": 10.0,        # % from peak
    "drawdown_critical": 15.0,       # % from peak
}
