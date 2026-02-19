"""FastAPI application"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.trading_bot import trading_bot
from src.execution.trade_executor import trade_executor
from src.risk.risk_monitor import risk_monitor
from src.database.connection import get_db, init_db
from src.database.models import Trade, Position, Signal, Performance
from src.config.settings import settings
from src.utils.logger import main_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown"""
    # Startup
    init_db()
    main_logger.info("API server started")
    yield
    # Shutdown
    main_logger.info("API server shutting down")
    if trading_bot.running:
        await trading_bot.stop()

# Create FastAPI app
app = FastAPI(
    title="Crypto Trading System API",
    description="Advanced AI-powered crypto intraday trading system",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware — allow React dev server + production
_allowed_origins = getattr(settings, 'allowed_origins', [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
])
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)


# Pydantic models for API
class SystemStatus(BaseModel):
    running: bool
    paper_trading: bool
    kill_switch_active: bool
    capital: float
    open_positions: int
    trading_pairs: List[str]


class PositionResponse(BaseModel):
    id: int
    symbol: str
    direction: str
    entry_price: float
    current_price: float
    position_size: float
    unrealized_pnl: float
    stop_loss: float
    take_profit: float
    opened_at: Optional[datetime] = None


class TradeResponse(BaseModel):
    id: int
    symbol: str
    direction: str
    status: str
    entry_price: float
    exit_price: Optional[float]
    pnl: Optional[float]
    pnl_percent: Optional[float]
    fees: Optional[float]
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    created_at: datetime


class PerformanceResponse(BaseModel):
    date: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    net_pnl: float
    gross_profit: float
    gross_loss: float
    fees_paid: float
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    profit_factor: Optional[float]
    max_drawdown: float
    starting_capital: float
    ending_capital: float


class PerformanceSummary(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    net_pnl: float
    total_fees: float
    sharpe_ratio: Optional[float]
    profit_factor: Optional[float]
    max_drawdown: float
    best_day_pnl: float
    worst_day_pnl: float
    avg_daily_pnl: float


class ConfigUpdate(BaseModel):
    trading_pairs: Optional[List[str]] = None
    timeframes: Optional[List[str]] = None
    max_leverage: Optional[int] = None
    max_position_size_pct: Optional[float] = None
    max_daily_loss_pct: Optional[float] = None
    max_concurrent_trades: Optional[int] = None
    risk_per_trade_pct: Optional[float] = None
    min_risk_reward_ratio: Optional[float] = None
    confidence_threshold: Optional[float] = None
    stop_loss_pct: Optional[float] = None


# Mount static files for frontend (React build output)
static_path = Path(__file__).parent.parent.parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


# Root endpoint - serve React app
@app.get("/", include_in_schema=False)
async def root():
    """Serve React frontend"""
    index_path = Path(__file__).parent.parent.parent / "static" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Trading System API", "docs": "/docs"}


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "0.1.0"
    }


# System status
@app.get("/status", response_model=SystemStatus)
async def get_status():
    """Get system status"""
    with get_db() as db:
        open_positions = db.query(Position).count()
    
    return SystemStatus(
        running=trading_bot.running,
        paper_trading=settings.is_paper_trading(),
        kill_switch_active=risk_monitor.kill_switch_active,
        capital=trading_bot.capital,
        open_positions=open_positions,
        trading_pairs=settings.trading_pairs
    )


# Start/Stop bot
@app.post("/bot/start")
async def start_bot(background_tasks: BackgroundTasks):
    """Start the trading bot"""
    if trading_bot.running:
        raise HTTPException(status_code=400, detail="Bot zaten çalışıyor")
    
    background_tasks.add_task(trading_bot.start)
    return {"message": "Trading bot başlatıldı"}


@app.post("/bot/stop")
async def stop_bot():
    """Stop the trading bot"""
    if not trading_bot.running:
        raise HTTPException(status_code=400, detail="Bot zaten durdurulmuş")
    
    await trading_bot.stop()
    return {"message": "Trading bot durduruldu"}


# Kill-switch
@app.post("/killswitch/activate")
async def activate_killswitch():
    """Manually activate kill-switch"""
    risk_monitor.activate_kill_switch(-999.0)
    return {"message": "Kill-switch aktif edildi"}


@app.post("/killswitch/deactivate")
async def deactivate_killswitch():
    """Manually deactivate kill-switch"""
    risk_monitor.deactivate_kill_switch()
    return {"message": "Kill-switch devre dışı bırakıldı"}


# Positions
@app.get("/positions", response_model=List[PositionResponse])
async def get_positions():
    """Get all open positions"""
    with get_db() as db:
        positions = db.query(Position).all()
        
        return [
            PositionResponse(
                id=p.id,
                symbol=p.symbol,
                direction=p.direction.value,
                entry_price=p.entry_price,
                current_price=p.current_price,
                position_size=p.position_size,
                unrealized_pnl=p.unrealized_pnl,
                stop_loss=p.stop_loss,
                take_profit=p.take_profit,
                opened_at=p.opened_at,
            )
            for p in positions
        ]


@app.post("/positions/{symbol}/close")
async def close_position(symbol: str):
    """Close a specific position"""
    success = await trade_executor.close_position(symbol, "manual")
    
    if success:
        return {"message": f"Pozisyon {symbol} kapatıldı"}
    else:
        raise HTTPException(status_code=404, detail="Pozisyon bulunamadı")


# Trades
@app.get("/trades", response_model=List[TradeResponse])
async def get_trades(limit: int = 50):
    """Get recent trades"""
    with get_db() as db:
        trades = db.query(Trade).order_by(
            Trade.entry_timestamp.desc()
        ).limit(limit).all()
        
        return [
            TradeResponse(
                id=t.id,
                symbol=t.symbol,
                direction=t.direction.value,
                status=t.status.value,
                entry_price=t.entry_price,
                exit_price=t.exit_price,
                pnl=t.pnl,
                pnl_percent=t.pnl_percent,
                fees=t.fees,
                stop_loss=t.stop_loss,
                take_profit=t.take_profit,
                created_at=t.entry_timestamp
            )
            for t in trades
        ]


# Signals
@app.get("/signals")
async def get_signals(limit: int = 50):
    """Get recent signals"""
    with get_db() as db:
        signals = db.query(Signal).order_by(
            Signal.timestamp.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": s.id,
                "symbol": s.symbol,
                "timestamp": s.timestamp.isoformat(),
                "direction": s.direction.value if s.direction else None,
                "confidence_score": s.confidence_score,
                "risk_reward_ratio": s.risk_reward_ratio,
                "signal_type": s.signal_type,
                "market_regime": s.market_regime,
                "entry_price": s.entry_price,
                "stop_loss": s.stop_loss,
                "take_profit": s.take_profit,
                "executed": s.executed,
                "trend_score": s.trend_score,
                "momentum_score": s.momentum_score,
                "volume_score": s.volume_score,
                "orderbook_score": s.orderbook_score,
                "volatility_score": s.volatility_score,
                "sentiment_score": s.sentiment_score,
                "onchain_score": s.onchain_score,
            }
            for s in signals
        ]


# Performance - daily list
@app.get("/performance", response_model=List[PerformanceResponse])
async def get_performance(days: int = 30):
    """Get daily performance metrics"""
    with get_db() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        performance = db.query(Performance).filter(
            Performance.date >= cutoff
        ).order_by(Performance.date.desc()).all()
        
        return [
            PerformanceResponse(
                date=p.date,
                total_trades=p.total_trades,
                winning_trades=p.winning_trades,
                losing_trades=p.losing_trades,
                win_rate=p.win_rate,
                net_pnl=p.net_pnl,
                gross_profit=p.gross_profit,
                gross_loss=p.gross_loss,
                fees_paid=p.fees_paid,
                sharpe_ratio=p.sharpe_ratio,
                sortino_ratio=p.sortino_ratio,
                profit_factor=p.profit_factor,
                max_drawdown=p.max_drawdown,
                starting_capital=p.starting_capital,
                ending_capital=p.ending_capital,
            )
            for p in performance
        ]


# Performance - summary aggregate
@app.get("/performance/summary", response_model=PerformanceSummary)
async def get_performance_summary(days: int = 30):
    """Get aggregated performance summary"""
    with get_db() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        rows = db.query(Performance).filter(
            Performance.date >= cutoff
        ).all()

        if not rows:
            return PerformanceSummary(
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0.0, net_pnl=0.0, total_fees=0.0,
                sharpe_ratio=None, profit_factor=None, max_drawdown=0.0,
                best_day_pnl=0.0, worst_day_pnl=0.0, avg_daily_pnl=0.0,
            )

        total_trades = sum(r.total_trades for r in rows)
        winning_trades = sum(r.winning_trades for r in rows)
        losing_trades = sum(r.losing_trades for r in rows)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        net_pnl = sum(r.net_pnl for r in rows)
        total_fees = sum(r.fees_paid for r in rows)
        max_drawdown = max(r.max_drawdown for r in rows)
        pnls = [r.net_pnl for r in rows]
        best_day_pnl = max(pnls) if pnls else 0.0
        worst_day_pnl = min(pnls) if pnls else 0.0
        avg_daily_pnl = (net_pnl / len(rows)) if rows else 0.0

        # Weighted average sharpe from rows that have it
        sharpe_rows = [r for r in rows if r.sharpe_ratio is not None]
        sharpe_ratio = (sum(r.sharpe_ratio for r in sharpe_rows) / len(sharpe_rows)) if sharpe_rows else None

        # Profit factor: gross_profit / abs(gross_loss)
        total_gross_profit = sum(r.gross_profit for r in rows)
        total_gross_loss = sum(r.gross_loss for r in rows)
        profit_factor = (total_gross_profit / abs(total_gross_loss)) if total_gross_loss != 0 else None

        return PerformanceSummary(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            net_pnl=net_pnl,
            total_fees=total_fees,
            sharpe_ratio=sharpe_ratio,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            best_day_pnl=best_day_pnl,
            worst_day_pnl=worst_day_pnl,
            avg_daily_pnl=avg_daily_pnl,
        )


# Configuration - GET
@app.get("/config")
async def get_config():
    """Get current configuration"""
    return {
        "trading_pairs": settings.trading_pairs,
        "timeframes": settings.timeframes,
        "max_leverage": settings.max_leverage,
        "max_position_size_pct": settings.max_position_size_pct,
        "max_daily_loss_pct": settings.max_daily_loss_pct,
        "max_concurrent_trades": settings.max_concurrent_trades,
        "risk_per_trade_pct": settings.risk_per_trade_pct,
        "min_risk_reward_ratio": settings.min_risk_reward_ratio,
        "confidence_threshold": settings.confidence_threshold,
        "stop_loss_pct": settings.stop_loss_pct,
        "paper_trading": settings.is_paper_trading(),
        "environment": settings.environment,
        "log_level": settings.log_level,
    }


# Configuration - POST (update runtime settings)
@app.post("/config")
async def update_config(update: ConfigUpdate):
    """Update runtime configuration (in-memory only; persisted settings require .env restart)"""
    updated = {}
    if update.trading_pairs is not None:
        settings.trading_pairs = update.trading_pairs
        updated["trading_pairs"] = update.trading_pairs
    if update.timeframes is not None:
        settings.timeframes = update.timeframes
        updated["timeframes"] = update.timeframes
    if update.max_leverage is not None:
        settings.max_leverage = update.max_leverage
        updated["max_leverage"] = update.max_leverage
    if update.max_position_size_pct is not None:
        settings.max_position_size_pct = update.max_position_size_pct
        updated["max_position_size_pct"] = update.max_position_size_pct
    if update.max_daily_loss_pct is not None:
        settings.max_daily_loss_pct = update.max_daily_loss_pct
        updated["max_daily_loss_pct"] = update.max_daily_loss_pct
    if update.max_concurrent_trades is not None:
        settings.max_concurrent_trades = update.max_concurrent_trades
        updated["max_concurrent_trades"] = update.max_concurrent_trades
    if update.risk_per_trade_pct is not None:
        settings.risk_per_trade_pct = update.risk_per_trade_pct
        updated["risk_per_trade_pct"] = update.risk_per_trade_pct
    if update.min_risk_reward_ratio is not None:
        settings.min_risk_reward_ratio = update.min_risk_reward_ratio
        updated["min_risk_reward_ratio"] = update.min_risk_reward_ratio
    if update.confidence_threshold is not None:
        settings.confidence_threshold = update.confidence_threshold
        updated["confidence_threshold"] = update.confidence_threshold
    if update.stop_loss_pct is not None:
        settings.stop_loss_pct = update.stop_loss_pct
        updated["stop_loss_pct"] = update.stop_loss_pct

    return {"message": "Ayarlar güncellendi", "updated": updated}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
