"""SQLAlchemy ORM models for database tables"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, JSON, ForeignKey, Index, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
import enum

from src.database.connection import Base


class TradeDirection(str, enum.Enum):
    """Trade direction enum"""
    LONG = "LONG"
    SHORT = "SHORT"


class TradeStatus(str, enum.Enum):
    """Trade status enum"""
    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class MarketData(Base):
    """OHLCV and tick data"""
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('idx_symbol_timeframe_timestamp', 'symbol', 'timeframe', 'timestamp'),
    )


class OrderBook(Base):
    """Order book snapshots"""
    __tablename__ = "order_book"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    bids = Column(JSON, nullable=False)  # [[price, quantity], ...]
    asks = Column(JSON, nullable=False)  # [[price, quantity], ...]
    bid_ask_spread = Column(Float)
    imbalance_ratio = Column(Float)  # bid_volume / ask_volume
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Trade(Base):
    """Executed trades"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    direction = Column(SQLEnum(TradeDirection), nullable=False)
    status = Column(SQLEnum(TradeStatus), nullable=False, default=TradeStatus.PENDING)
    
    # Entry
    entry_timestamp = Column(DateTime, nullable=False)
    entry_price = Column(Float, nullable=False)
    position_size = Column(Float, nullable=False)
    leverage = Column(Integer, default=1)
    
    # Exit
    exit_timestamp = Column(DateTime)
    exit_price = Column(Float)
    
    # Risk Management
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    trailing_stop = Column(Float)
    
    # Performance
    pnl = Column(Float)
    pnl_percent = Column(Float)
    fees = Column(Float, default=0.0)
    
    # Metadata
    signal_id = Column(Integer, ForeignKey("signals.id"))
    exchange_order_id = Column(String(100))
    notes = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    signal = relationship("Signal", back_populates="trades")


class Position(Base):
    """Open positions"""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True, unique=True)
    direction = Column(SQLEnum(TradeDirection), nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    position_size = Column(Float, nullable=False)
    leverage = Column(Integer, default=1)
    unrealized_pnl = Column(Float, default=0.0)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    trailing_stop = Column(Float)
    opened_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Signal(Base):
    """Generated trading signals"""
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    direction = Column(SQLEnum(TradeDirection), nullable=False)
    
    # Signal Components
    trend_score = Column(Float, nullable=False)
    momentum_score = Column(Float, nullable=False)
    volume_score = Column(Float, nullable=False)
    orderbook_score = Column(Float, nullable=False)
    volatility_score = Column(Float, nullable=False)
    sentiment_score = Column(Float, nullable=False)
    onchain_score = Column(Float, nullable=False)
    
    # Overall
    confidence_score = Column(Float, nullable=False)
    risk_reward_ratio = Column(Float, nullable=False)
    
    # Entry/Exit Levels
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    
    # Execution
    executed = Column(Boolean, default=False)
    execution_timestamp = Column(DateTime)
    
    # Metadata
    signal_type = Column(String(50))  # breakout, pullback, reversal, news
    market_regime = Column(String(20))  # trending, ranging, volatile
    notes = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    trades = relationship("Trade", back_populates="signal")


class Performance(Base):
    """Daily performance metrics"""
    __tablename__ = "performance"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, unique=True, index=True)
    
    # Trading Metrics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    
    # P&L
    gross_profit = Column(Float, default=0.0)
    gross_loss = Column(Float, default=0.0)
    net_pnl = Column(Float, default=0.0)
    fees_paid = Column(Float, default=0.0)
    
    # Risk Metrics
    max_drawdown = Column(Float, default=0.0)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    profit_factor = Column(Float)
    expectancy = Column(Float)
    
    # Capital
    starting_capital = Column(Float, nullable=False)
    ending_capital = Column(Float, nullable=False)
    peak_capital = Column(Float, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SentimentData(Base):
    """Sentiment scores from various sources"""
    __tablename__ = "sentiment_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    source = Column(String(50), nullable=False)  # twitter, reddit, news, telegram
    
    # Sentiment
    sentiment_score = Column(Float, nullable=False)  # -1 to 1
    sentiment_label = Column(String(20))  # bullish, bearish, neutral
    confidence = Column(Float)
    
    # Metadata
    text_sample = Column(Text)
    author = Column(String(100))
    engagement_score = Column(Float)  # likes, retweets, upvotes
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
    )


class OnChainData(Base):
    """On-chain metrics and whale activity"""
    __tablename__ = "onchain_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Whale Activity
    whale_transactions = Column(Integer, default=0)
    whale_volume = Column(Float, default=0.0)
    
    # Exchange Flows
    exchange_inflow = Column(Float, default=0.0)
    exchange_outflow = Column(Float, default=0.0)
    net_flow = Column(Float, default=0.0)
    
    # Network Activity
    active_addresses = Column(Integer)
    transaction_count = Column(Integer)
    
    # Metadata
    data_source = Column(String(50))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SystemState(Base):
    """System state and configuration"""
    __tablename__ = "system_state"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), nullable=False, unique=True, index=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
