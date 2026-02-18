# Quick Start Guide

## Prerequisites

1. **Python 3.11+**
2. **Docker & Docker Compose**
3. **Exchange API Keys** (Binance or Bybit)
4. **Telegram Bot** (optional, for alerts)

## Installation Steps

### 1. Setup Environment

```bash
cd /Users/emircanuysal/Desktop/crypto

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy template
cp .env.example .env

# Edit .env file
nano .env
```

**Minimum Required Configuration:**
```bash
# Exchange API (choose one)
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/crypto_trading
REDIS_URL=redis://localhost:6379/0

# Trading Configuration
TRADING_PAIRS=BTC/USDT,ETH/USDT
TIMEFRAMES=1m,5m,15m

# Risk Management
MAX_LEVERAGE=5
MAX_DAILY_LOSS_PCT=5.0
RISK_PER_TRADE_PCT=1.5

# IMPORTANT: Enable paper trading for testing
ENABLE_PAPER_TRADING=true
ENVIRONMENT=development
```

### 3. Start Database Services

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Wait for services to be ready (about 10 seconds)
sleep 10

# Initialize database
python -c "from src.database.connection import init_db; init_db()"
```

### 4. Run the Trading System

```bash
# Run in development mode (paper trading)
source venv/bin/activate
python main.py
```

The system will:
- Start the trading bot
- Launch API server on http://localhost:8000
- Begin monitoring configured trading pairs
- Generate signals and execute trades (paper mode)

### 5. Access the System

**API Documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Monitoring:**
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090

**API Endpoints:**
- System Status: `GET /status`
- Open Positions: `GET /positions`
- Recent Trades: `GET /trades`
- Signals: `GET /signals`
- Performance: `GET /performance`

## Testing the System

### 1. Check System Status

```bash
curl http://localhost:8000/status
```

Expected response:
```json
{
  "running": true,
  "paper_trading": true,
  "kill_switch_active": false,
  "capital": 10000.0,
  "open_positions": 0,
  "trading_pairs": ["BTC/USDT", "ETH/USDT"]
}
```

### 2. View Recent Signals

```bash
curl http://localhost:8000/signals
```

### 3. Monitor Positions

```bash
curl http://localhost:8000/positions
```

### 4. Check Performance

```bash
curl http://localhost:8000/performance?days=7
```

### 5. Run Tests

```bash
PYTHONPATH=. ./venv/bin/python -m pytest tests/ -v
```

## Docker Deployment (Full Stack)

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f trading_system

# Stop all services
docker-compose down
```

## Safety Checks

✅ **Paper Trading Enabled**: No real money at risk
✅ **Kill-Switch**: Auto-stops at 5% daily loss
✅ **Position Limits**: Max 3 concurrent trades
✅ **Risk Per Trade**: Limited to 1.5% of capital
✅ **Leverage Cap**: Maximum 5x leverage

## Common Issues

### Database Connection Error
```bash
# Restart PostgreSQL
docker-compose restart postgres

# Check if running
docker-compose ps postgres
```

### Exchange API Error
- Verify API keys in `.env`
- Check IP whitelist on exchange
- Ensure API has futures trading permissions

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## Next Steps

1. **Monitor for 24 hours** in paper trading mode
2. **Review signals** and trade decisions
3. **Check performance metrics**
4. **Adjust parameters** in `.env` if needed
5. **Only after validation**, consider live trading (NOT RECOMMENDED without extensive testing)

## Important Reminders

> [!WARNING]
> This is a high-risk trading system. Always start with paper trading.
> Never risk more than you can afford to lose.
> Professional funds target 3-5% daily returns.
> Targeting 20%+ approaches gambling territory.

## Support

Check logs in `logs/` directory for detailed information:
- `trading.log` - Main system logs
- `data.log` - Data collection logs
- `signals.log` - Signal generation logs
- `execution.log` - Trade execution logs
- `risk.log` - Risk management logs
