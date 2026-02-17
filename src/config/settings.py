"""Centralized configuration management using Pydantic Settings"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator


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
    
    # Exchange API Keys
    binance_api_key: str = Field(default="", description="Binance API key")
    binance_api_secret: str = Field(default="", description="Binance API secret")
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
    min_risk_reward_ratio: float = Field(default=2.5, ge=1.0, le=10.0, description="Minimum risk/reward ratio")
    confidence_threshold: float = Field(default=75.0, ge=50.0, le=100.0, description="Minimum confidence score for trade")
    
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
    
    @validator("trading_pairs")
    def parse_trading_pairs(cls, v: str) -> List[str]:
        """Parse comma-separated trading pairs"""
        return [pair.strip() for pair in v.split(",") if pair.strip()]
    
    @validator("timeframes")
    def parse_timeframes(cls, v: str) -> List[str]:
        """Parse comma-separated timeframes"""
        return [tf.strip() for tf in v.split(",") if tf.strip()]
    
    def get_trading_pairs(self) -> List[str]:
        """Get list of trading pairs"""
        if isinstance(self.trading_pairs, str):
            return [pair.strip() for pair in self.trading_pairs.split(",") if pair.strip()]
        return self.trading_pairs
    
    def get_timeframes(self) -> List[str]:
        """Get list of timeframes"""
        if isinstance(self.timeframes, str):
            return [tf.strip() for tf in self.timeframes.split(",") if tf.strip()]
        return self.timeframes
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() == "production"
    
    def is_paper_trading(self) -> bool:
        """Check if paper trading is enabled"""
        return self.enable_paper_trading or not self.is_production()


# Global settings instance
settings = Settings()
