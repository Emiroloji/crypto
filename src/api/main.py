"""FastAPI application"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from src.trading_bot import trading_bot
from src.risk.risk_monitor import risk_monitor
from src.database.connection import get_db
from src.database.models import Trade, Position, Signal, Performance
from src.config.settings import settings
from src.utils.logger import main_logger

# Create FastAPI app
app = FastAPI(
    title="Crypto Trading System API",
    description="Advanced AI-powered crypto intraday trading system",
    version="0.1.0"
)

# Mount static files for frontend
static_path = Path(__file__).parent.parent.parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
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


class TradeResponse(BaseModel):
    id: int
    symbol: str
    direction: str
    status: str
    entry_price: float
    exit_price: Optional[float]
    pnl: Optional[float]
    pnl_percent: Optional[float]
    created_at: datetime


class PerformanceResponse(BaseModel):
    date: datetime
    total_trades: int
    win_rate: float
    net_pnl: float
    sharpe_ratio: Optional[float]
    max_drawdown: float


# Root endpoint - serve dashboard
@app.get("/", include_in_schema=False)
async def root():
    """Serve the dashboard"""
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
        "timestamp": datetime.utcnow().isoformat(),
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
        capital=trading_bot.capital if hasattr(trading_bot, 'capital') else 0.0,
        open_positions=open_positions,
        trading_pairs=settings.get_trading_pairs()
    )


# Start/Stop bot
@app.post("/bot/start")
async def start_bot(background_tasks: BackgroundTasks):
    """Start the trading bot"""
    if trading_bot.running:
        raise HTTPException(status_code=400, detail="Bot is already running")
    
    background_tasks.add_task(trading_bot.start)
    return {"message": "Trading bot started"}


@app.post("/bot/stop")
async def stop_bot():
    """Stop the trading bot"""
    if not trading_bot.running:
        raise HTTPException(status_code=400, detail="Bot is not running")
    
    await trading_bot.stop()
    return {"message": "Trading bot stopped"}


# Kill-switch
@app.post("/killswitch/activate")
async def activate_killswitch():
    """Manually activate kill-switch"""
    risk_monitor.activate_kill_switch(-999.0)
    return {"message": "Kill-switch activated"}


@app.post("/killswitch/deactivate")
async def deactivate_killswitch():
    """Manually deactivate kill-switch"""
    risk_monitor.deactivate_kill_switch()
    return {"message": "Kill-switch deactivated"}


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
                take_profit=p.take_profit
            )
            for p in positions
        ]


@app.post("/positions/{symbol}/close")
async def close_position(symbol: str):
    """Close a specific position"""
    from src.execution.trade_executor import trade_executor
    
    success = await trade_executor.close_position(symbol, "manual")
    
    if success:
        return {"message": f"Position {symbol} closed"}
    else:
        raise HTTPException(status_code=404, detail="Position not found")


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
                created_at=t.entry_timestamp
            )
            for t in trades
        ]


# Signals
@app.get("/signals")
async def get_signals(limit: int = 20):
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
                "created_at": s.timestamp.isoformat(),
                "direction": s.direction.value if s.direction else None,
                "confidence_score": s.confidence_score,
                "risk_reward_ratio": s.risk_reward_ratio,
                "signal_type": s.signal_type,
                "entry_price": s.entry_price,
                "stop_loss": s.stop_loss,
                "take_profit": s.take_profit,
                "executed": s.executed
            }
            for s in signals
        ]


# Performance
@app.get("/performance", response_model=List[PerformanceResponse])
async def get_performance(days: int = 30):
    """Get performance metrics"""
    with get_db() as db:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        performance = db.query(Performance).filter(
            Performance.date >= cutoff
        ).order_by(Performance.date.desc()).all()
        
        return [
            PerformanceResponse(
                date=p.date,
                total_trades=p.total_trades,
                win_rate=p.win_rate,
                net_pnl=p.net_pnl,
                sharpe_ratio=p.sharpe_ratio,
                max_drawdown=p.max_drawdown
            )
            for p in performance
        ]


# Configuration
@app.get("/config")
async def get_config():
    """Get current configuration"""
    return {
        "trading_pairs": settings.get_trading_pairs(),
        "timeframes": settings.get_timeframes(),
        "max_leverage": settings.max_leverage,
        "max_position_size_pct": settings.max_position_size_pct,
        "max_daily_loss_pct": settings.max_daily_loss_pct,
        "max_concurrent_trades": settings.max_concurrent_trades,
        "risk_per_trade_pct": settings.risk_per_trade_pct,
        "min_risk_reward_ratio": settings.min_risk_reward_ratio,
        "confidence_threshold": settings.confidence_threshold,
        "stop_loss_pct": settings.stop_loss_pct,
        "paper_trading": settings.is_paper_trading(),
    }


@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    main_logger.info("API server started")
    
    # Initialize database
    from src.database.connection import init_db
    init_db()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    main_logger.info("API server shutting down")
    
    if trading_bot.running:
        await trading_bot.stop()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
