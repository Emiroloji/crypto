import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from src.signals.signal_generator import SignalGenerator
from src.database.models import TradeDirection

@pytest.fixture
def mock_df():
    # Create sample DataFrame with enough data for indicators
    dates = pd.date_range(start="2024-01-01", periods=100, freq="1h")
    df = pd.DataFrame({
        'timestamp': dates,
        'open': np.linspace(100, 200, 100),
        'high': np.linspace(101, 201, 100),
        'low': np.linspace(99, 199, 100),
        'close': np.linspace(100, 200, 100),
        'volume': np.random.rand(100) * 1000
    })
    return df

@pytest.fixture
def signal_gen():
    return SignalGenerator()

@patch('src.signals.signal_generator.get_trend_signals')
@patch('src.signals.signal_generator.get_momentum_signals')
@patch('src.signals.signal_generator.get_volume_signals')
@patch('src.signals.signal_generator.get_volatility_signals')
@patch('src.signals.signal_generator.sentiment_client')
@patch('src.signals.signal_generator.news_client')
def test_generate_signal_long(
    mock_news, mock_sentiment, mock_volatility, mock_volume, mock_momentum, mock_trend,
    signal_gen, mock_df
):
    # Setup mocks for a bullish signal
    mock_trend.return_value = {'trend_score': 80}
    mock_momentum.return_value = {'momentum_score': 70}
    mock_volume.return_value = {'volume_score': 60, 'orderbook_imbalance_signal': 0.5, 'high_volume': True}
    mock_volatility.return_value = {'volatility_score': 50, 'volatility_regime': 'normal', 'atr_value': 2.0}
    
    mock_sentiment.get_fear_greed_index.return_value = {'value': 40} # Fear (Bullish for Long)
    mock_sentiment.calculate_sentiment_score.return_value = 80.0
    mock_news.calculate_news_sentiment_score.return_value = 70.0
    
    # Run
    signal = signal_gen.generate_signal("BTC/USDT", mock_df)
    
    assert signal is not None
    assert signal['direction'] == TradeDirection.LONG
    assert signal['confidence_score'] > 0
    assert signal['entry_price'] == 200.0 # Last close
    assert signal['stop_loss'] == 200.0 - (2.0 * 2.0) # price - 2*ATR

@patch('src.signals.signal_generator.get_db')
def test_save_signal(mock_get_db, signal_gen):
    mock_session = MagicMock()
    mock_get_db.return_value.__enter__.return_value = mock_session
    
    signal_data = {
        'symbol': 'BTC/USDT',
        'timestamp': pd.Timestamp.now(),
        'direction': TradeDirection.LONG,
        'trend_score': 80.0,
        'momentum_score': 70.0,
        'volume_score': 60.0,
        'orderbook_score': 50.0,
        'volatility_score': 50.0,
        'sentiment_score': 80.0,
        'onchain_score': 0.0,
        'confidence_score': 75.0,
        'risk_reward_ratio': 2.5,
        'entry_price': 50000.0,
        'stop_loss': 49000.0,
        'take_profit': 52500.0,
        'signal_type': 'breakout',
        'market_regime': 'normal',
        'atr': 100.0
    }
    
    # Mock ID generation
    mock_session.add.side_effect = lambda x: setattr(x, 'id', 1)
    
    signal_id = signal_gen.save_signal(signal_data)
    
    assert signal_id == 1
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
