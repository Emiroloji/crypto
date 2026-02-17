"""README for Advanced Crypto Intraday Trading System

## Overview

This is an AI-powered high-frequency cryptocurrency trading system designed for intraday trading (1m-15m timeframes). The system combines technical analysis, mathematical modeling, order flow analysis, sentiment analysis, and adaptive risk management.

## ⚠️ WARNING

**This is a high-risk trading system. You can lose significant capital. Only use with funds you can afford to lose.**

- Professional funds typically target 3-5% daily returns
- Targeting 20%+ daily returns approaches gambling territory
- Maximum drawdown risk is proportional to profit targets
- Always start with paper trading mode

## Features

- **Multi-Exchange Support**: Binance Futures, Bybit
- **Technical Analysis**: 20+ indicators (EMA, RSI, MACD, Bollinger Bands, etc.)
- **Order Flow Analysis**: Order book imbalance, volume delta, CVD
- **Sentiment Analysis**: Twitter, Reddit, Telegram, news aggregation
- **On-Chain Analytics**: Whale tracking, exchange flows
- **Risk Management**: Dynamic position sizing, ATR-based stops, kill-switch
- **AI Learning**: Reinforcement learning, walk-forward optimization
- **Real-Time Monitoring**: Prometheus + Grafana dashboards
- **Alerts**: Telegram notifications for trades and risks

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 16
- Redis 7

### 2. Installation

```bash
# Clone repository
cd /Users/emircanuysal/Desktop/crypto

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

**Required Configuration:**
- Exchange API keys (Binance/Bybit)
- Database URL
- Telegram bot token (for alerts)
- Social media API keys (optional)

### 4. Database Setup

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Initialize database
python -c "from src.database.connection import init_db; init_db()"
```

### 5. Run System

```bash
# Paper trading mode (recommended for testing)
export ENABLE_PAPER_TRADING=true
python -m src.api.main

# Production mode (use with caution)
export ENABLE_PAPER_TRADING=false
export ENVIRONMENT=production
python -m src.api.main
```

### 6. Access Monitoring

- **API**: http://localhost:8000
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## Project Structure

```
crypto/
├── src/
│   ├── api/              # FastAPI endpoints
│   ├── config/           # Configuration & constants
│   ├── data/             # Data collection & exchange clients
│   ├── database/         # ORM models & connection
│   ├── indicators/       # Technical indicators
│   ├── models/           # Mathematical & statistical models
│   ├── nlp/              # Sentiment analysis
│   ├── signals/          # Signal generation & scoring
│   ├── risk/             # Risk management
│   ├── execution/        # Trade execution
│   ├── ml/               # Machine learning
│   ├── analytics/        # Performance metrics
│   └── utils/            # Utilities (logging, cache, alerts)
├── tests/                # Unit & integration tests
├── logs/                 # Log files
├── data/                 # Historical data
├── models/               # Trained ML models
├── docker-compose.yml    # Docker orchestration
├── Dockerfile            # Container definition
└── requirements.txt      # Python dependencies
```

## Configuration

### Risk Parameters (`.env`)

```bash
MAX_LEVERAGE=5                    # Maximum leverage (1-20)
MAX_POSITION_SIZE_PCT=2.0         # Max position size (% of capital)
MAX_DAILY_LOSS_PCT=5.0            # Kill-switch threshold
MAX_CONCURRENT_TRADES=3           # Max simultaneous trades
RISK_PER_TRADE_PCT=1.5            # Risk per trade
MIN_RISK_REWARD_RATIO=2.5         # Minimum R/R ratio
CONFIDENCE_THRESHOLD=75.0         # Min confidence for trade
```

### Trading Pairs

```bash
TRADING_PAIRS=BTC/USDT,ETH/USDT
TIMEFRAMES=1m,5m,15m
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test suite
pytest tests/unit/test_indicators.py -v
```

## Backtesting

```bash
# Backtest strategy
python -m src.ml.backtester \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --pairs BTC/USDT,ETH/USDT \
  --initial-capital 10000
```

## Deployment

### Docker Deployment

```bash
# Build and run all services
docker-compose up -d

# View logs
docker-compose logs -f trading_system

# Stop services
docker-compose down
```

### AWS EC2 Deployment

1. Launch EC2 instance (t3.medium or larger)
2. Install Docker & Docker Compose
3. Clone repository
4. Configure `.env` file
5. Run `docker-compose up -d`
6. Configure security groups (ports 8000, 3000, 9090)

## Monitoring & Alerts

### Telegram Alerts

The system sends alerts for:
- High confidence signals
- Trade executions
- Risk warnings (approaching daily loss limit)
- Kill-switch activation
- System errors

### Grafana Dashboards

Access Grafana at `http://localhost:3000` to view:
- Real-time P&L
- Win rate & profit factor
- Open positions
- Signal strength
- Risk metrics

## Safety Features

1. **Paper Trading Mode**: Test without real capital
2. **Kill-Switch**: Auto-stop at 5% daily loss
3. **Position Limits**: Max 3 concurrent trades
4. **Risk Per Trade**: Limited to 1-2% of capital
5. **Correlation Filter**: Avoid overexposure
6. **ATR-Based Stops**: Dynamic stop losses

## Performance Metrics

The system tracks:
- Win rate
- Profit factor
- Sharpe ratio
- Sortino ratio
- Maximum drawdown
- Expectancy
- Risk-adjusted returns

## Troubleshooting

### Common Issues

**Database connection error:**
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Restart PostgreSQL
docker-compose restart postgres
```

**Exchange API error:**
- Verify API keys in `.env`
- Check IP whitelist on exchange
- Ensure sufficient permissions (futures trading)

**WebSocket disconnection:**
- System auto-reconnects (max 10 attempts)
- Check internet connection
- Verify exchange status

## Development

### Adding New Indicators

1. Create indicator in `src/indicators/`
2. Add to signal scoring in `src/signals/signal_generator.py`
3. Update weights in `src/config/constants.py`
4. Write tests in `tests/unit/`

### Adding New Exchanges

1. Extend `ExchangeClient` in `src/data/exchange_client.py`
2. Add exchange config in `src/config/constants.py`
3. Update `.env.example` with API key variables

## License

This project is for educational purposes only. Use at your own risk.

## Disclaimer

- **Not Financial Advice**: This system is not financial advice
- **No Guarantees**: Past performance does not guarantee future results
- **High Risk**: Cryptocurrency trading is extremely risky
- **Regulatory Compliance**: Ensure compliance with local regulations
- **No Warranty**: Provided "as is" without warranty of any kind

## Support

For issues and questions:
1. Check logs in `logs/` directory
2. Review Grafana dashboards
3. Enable DEBUG logging in `.env`

## Roadmap

- [ ] Support for more exchanges (OKX, Kraken)
- [ ] Advanced ML models (LSTM, Transformer)
- [ ] Multi-timeframe analysis
- [ ] Portfolio optimization
- [ ] Automated parameter tuning
- [ ] Mobile app for monitoring

---

**Remember: Start with paper trading, validate thoroughly, and never risk more than you can afford to lose.**
