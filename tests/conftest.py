import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime

from src.data.exchange_client import ExchangeClient
from src.backtest.engine import BacktestEngine

@pytest.fixture
def mock_exchange_client():
    with patch('src.data.exchange_client.ExchangeClient._check_demo_mode', return_value=True):
        client = ExchangeClient(exchange_name="binance")
        client.exchange = MagicMock()
        return client

@pytest.fixture
def mock_ohlcv_data():
    """Generate sample OHLCV data for testing"""
    dates = pd.date_range(start="2024-01-01", periods=100, freq="1h")
    data = {
        'timestamp': dates,
        'open': [100.0 + i for i in range(100)],
        'high': [105.0 + i for i in range(100)],
        'low': [95.0 + i for i in range(100)],
        'close': [102.0 + i for i in range(100)],
        'volume': [1000.0 for _ in range(100)]
    }
    return pd.DataFrame(data)

@pytest.fixture
def backtest_engine():
    return BacktestEngine(initial_capital=10000.0)
