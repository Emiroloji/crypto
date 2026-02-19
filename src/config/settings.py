"""Centralized configuration management using Pydantic Settings"""

from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Environment
    environment: str = Field(default="development", description="Environment: development, staging, production")
    log_level: str = Field(default="INFO", description="Logging level")
    enable_paper_trading: bool = Field(default=True, description="Enable paper trading mode")
    api_key: str = Field(default="", description="API Key for securing endpoints (leave empty to disable)")
    
    # Exchange API Keys
    binance_api_key: str = Field(default="", description="Binance API key")
    binance_api_secret: str = Field(default="", description="Binance API secret")
    binance_testnet: bool = Field(default=False, description="Use Binance testnet")
    bybit_api_key: str = Field(default="", description="Bybit API key")
    bybit_api_secret: str = Field(default="", description="Bybit API secret")
    
    # Database
    database_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/crypto_trading",
        description="PostgreSQL connection URL"
    )
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    
    # Trading Configuration
    trading_pairs: str = Field(default="BTC/USDT,ETH/USDT", description="Comma-separated trading pairs")
    timeframes: str = Field(default="1m,5m,15m", description="Comma-separated timeframes")
    max_leverage: int = Field(default=5, ge=1, le=20, description="Maximum leverage")
    max_position_size_pct: float = Field(default=2.0, ge=0.1, le=10.0, description="Max position size as % of capital")
    max_daily_loss_pct: float = Field(default=5.0, ge=1.0, le=20.0, description="Max daily loss % (kill-switch)")
    max_concurrent_trades: int = Field(default=3, ge=1, le=10, description="Maximum concurrent trades")
    
    # Risk Management
    risk_per_trade_pct: float = Field(default=1.5, ge=0.5, le=5.0, description="Risk per trade as % of capital")
    stop_loss_pct: float = Field(default=2.0, ge=0.5, le=10.0, description="Default stop loss percentage")
    min_risk_reward_ratio: float = Field(default=2.5, ge=1.0, le=10.0, description="Minimum risk/reward ratio")
    confidence_threshold: float = Field(default=75.0, ge=50.0, le=100.0, description="Minimum confidence score for trade")
    
    # Trading Constants
    maker_fee_rate: float = Field(default=0.0002, description="Maker fee rate (0.02%)")
    taker_fee_rate: float = Field(default=0.0004, description="Taker fee rate (0.04%)")
    initial_capital: float = Field(default=10000.0, description="Initial capital for backtesting/paper trading")
    
    # Social Media APIs
    twitter_api_key: str = Field(default="", description="Twitter API key")
    twitter_api_secret: str = Field(default="", description="Twitter API secret")
    twitter_access_token: str = Field(default="", description="Twitter access token")
    twitter_access_secret: str = Field(default="", description="Twitter access secret")
    
    reddit_client_id: str = Field(default="", description="Reddit client ID")
    reddit_client_secret: str = Field(default="", description="Reddit client secret")
    reddit_user_agent: str = Field(default="crypto_trading_bot", description="Reddit user agent")
    
    telegram_bot_token: str = Field(default="", description="Telegram bot token")
    telegram_chat_id: str = Field(default="", description="Telegram chat ID for alerts")
    
    # CORS
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins (set to ['*'] only for development)"
    )
    
    @field_validator("trading_pairs")
    def parse_trading_pairs(cls, v) -> List[str]:
        """Parse comma-separated trading pairs (handles both str and list)"""
        if isinstance(v, list):
            return v
        return [pair.strip() for pair in v.split(",") if pair.strip()]
    
    @field_validator("timeframes")
    def parse_timeframes(cls, v) -> List[str]:
        """Parse comma-separated timeframes (handles both str and list)"""
        if isinstance(v, list):
            return v
        return [tf.strip() for tf in v.split(",") if tf.strip()]

    @field_validator("allowed_origins")
    def parse_allowed_origins(cls, v) -> List[str]:
        """Parse comma-separated CORS origins from env var (handles both str and list)"""
        if isinstance(v, list):
            return v
        return [origin.strip() for origin in v.split(",") if origin.strip()]
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() == "production"
    
    def is_paper_trading(self) -> bool:
        """Check if paper trading is enabled"""
        return self.enable_paper_trading or not self.is_production()


# Global settings instance
settings = Settings()
