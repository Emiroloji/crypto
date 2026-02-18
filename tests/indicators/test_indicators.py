import pytest
import pandas as pd
import numpy as np
from src.indicators.trend import calculate_ema, calculate_vwap, calculate_supertrend
from src.indicators.momentum import calculate_rsi

@pytest.fixture
def mock_df():
    # Create sample DataFrame
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
def mock_series():
    return pd.Series(np.linspace(10, 20, 20))

def test_calculate_ema(mock_df):
    ema = calculate_ema(mock_df, period=5)
    assert len(ema) == 100
    assert not np.isnan(ema.iloc[-1])

def test_calculate_vwap(mock_df):
    vwap = calculate_vwap(mock_df)
    assert len(vwap) == 100
    assert vwap.iloc[-1] > 0

def test_calculate_rsi(mock_df):
    rsi = calculate_rsi(mock_df, period=14)
    assert len(rsi) == 100
    # On linear up trend, RSI should be high
    assert rsi.iloc[-1] > 90

def test_calculate_supertrend(mock_df):
    supertrend, direction = calculate_supertrend(mock_df, period=10, multiplier=3.0)
    assert len(supertrend) == 100
    assert len(direction) == 100
    # First few are nan/init, check last
    assert not np.isnan(direction.iloc[-1])
