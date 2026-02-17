"""Risk monitoring and kill-switch implementation"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import and_, func

from src.config.settings import settings
from src.config.constants import ALERT_THRESHOLDS
from src.utils.logger import risk_logger
from src.utils.alerts import alert_manager
from src.database.connection import get_db
from src.database.models import Trade, Position, Performance, TradeStatus


class RiskMonitor:
    """Monitor risk metrics and enforce limits"""
    
    def __init__(self):
        self.max_daily_loss_pct = settings.max_daily_loss_pct
        self.max_concurrent_trades = settings.max_concurrent_trades
        self.kill_switch_active = False
    
    def check_daily_loss(self, capital: float) -> tuple[bool, float]:
        """
        Check if daily loss limit is reached
        
        Args:
            capital: Current capital
            
        Returns:
            Tuple of (limit_reached, current_loss_pct)
        """
        try:
            today = datetime.utcnow().date()
            
            with get_db() as db:
                # Get today's closed trades
                today_trades = db.query(Trade).filter(
                    and_(
                        func.date(Trade.entry_timestamp) == today,
                        Trade.status == TradeStatus.CLOSED
                    )
                ).all()
                
                # Calculate today's P&L
                total_pnl = sum(t.pnl for t in today_trades if t.pnl)
                loss_pct = (total_pnl / capital) * 100 if capital > 0 else 0
                
                # Check thresholds
                if loss_pct <= -self.max_daily_loss_pct:
                    self.activate_kill_switch(loss_pct)
                    return True, loss_pct
                elif loss_pct <= -ALERT_THRESHOLDS['daily_loss_critical']:
                    self._send_risk_alert('critical', loss_pct)
                elif loss_pct <= -ALERT_THRESHOLDS['daily_loss_warning']:
                    self._send_risk_alert('warning', loss_pct)
                
                return False, loss_pct
                
        except Exception as e:
            risk_logger.error(f"Error checking daily loss: {e}")
            return False, 0.0
    
    def check_concurrent_trades(self) -> tuple[bool, int]:
        """
        Check if concurrent trade limit is reached
        
        Returns:
            Tuple of (limit_reached, current_count)
        """
        try:
            with get_db() as db:
                open_positions = db.query(Position).count()
                
                if open_positions >= self.max_concurrent_trades:
                    risk_logger.warning(
                        f"Concurrent trade limit reached: {open_positions}/{self.max_concurrent_trades}"
                    )
                    return True, open_positions
                
                return False, open_positions
                
        except Exception as e:
            risk_logger.error(f"Error checking concurrent trades: {e}")
            return False, 0
    
    def check_correlation_exposure(self, new_symbol: str) -> tuple[bool, float]:
        """
        Check correlation exposure to avoid overexposure
        
        Args:
            new_symbol: Symbol to check
            
        Returns:
            Tuple of (overexposed, correlation_score)
        """
        try:
            with get_db() as db:
                open_positions = db.query(Position).all()
                
                # Simple correlation check: count BTC-correlated pairs
                btc_correlated = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
                
                if new_symbol in btc_correlated:
                    existing_btc_positions = sum(
                        1 for p in open_positions 
                        if p.symbol in btc_correlated
                    )
                    
                    # Don't allow more than 2 BTC-correlated positions
                    if existing_btc_positions >= 2:
                        risk_logger.warning(
                            f"Correlation limit: {existing_btc_positions} BTC-correlated positions"
                        )
                        return True, 1.0
                
                return False, 0.0
                
        except Exception as e:
            risk_logger.error(f"Error checking correlation: {e}")
            return False, 0.0
    
    def check_drawdown(self, capital: float, peak_capital: float) -> tuple[bool, float]:
        """
        Check current drawdown from peak
        
        Args:
            capital: Current capital
            peak_capital: Peak capital
            
        Returns:
            Tuple of (critical_drawdown, drawdown_pct)
        """
        if peak_capital == 0:
            return False, 0.0
        
        drawdown_pct = ((peak_capital - capital) / peak_capital) * 100
        
        if drawdown_pct >= ALERT_THRESHOLDS['drawdown_critical']:
            risk_logger.critical(f"Critical drawdown: {drawdown_pct:.2f}%")
            self._send_drawdown_alert('critical', drawdown_pct)
            return True, drawdown_pct
        elif drawdown_pct >= ALERT_THRESHOLDS['drawdown_warning']:
            risk_logger.warning(f"Drawdown warning: {drawdown_pct:.2f}%")
            self._send_drawdown_alert('warning', drawdown_pct)
        
        return False, drawdown_pct
    
    def check_consecutive_losses(self) -> tuple[bool, int]:
        """
        Check for consecutive losing trades
        
        Returns:
            Tuple of (threshold_reached, consecutive_count)
        """
        try:
            with get_db() as db:
                recent_trades = db.query(Trade).filter(
                    Trade.status == TradeStatus.CLOSED
                ).order_by(Trade.exit_timestamp.desc()).limit(10).all()
                
                consecutive_losses = 0
                for trade in recent_trades:
                    if trade.pnl and trade.pnl < 0:
                        consecutive_losses += 1
                    else:
                        break
                
                if consecutive_losses >= ALERT_THRESHOLDS['consecutive_losses']:
                    risk_logger.warning(f"Consecutive losses: {consecutive_losses}")
                    self._send_consecutive_loss_alert(consecutive_losses)
                    return True, consecutive_losses
                
                return False, consecutive_losses
                
        except Exception as e:
            risk_logger.error(f"Error checking consecutive losses: {e}")
            return False, 0
    
    def activate_kill_switch(self, loss_pct: float):
        """
        Activate kill-switch to stop all trading
        
        Args:
            loss_pct: Current loss percentage
        """
        self.kill_switch_active = True
        
        risk_logger.critical(
            f"🚨 KILL-SWITCH ACTIVATED 🚨 Daily loss: {loss_pct:.2f}%"
        )
        
        # Send critical alert
        alert_manager.send_alert_sync(
            f"🚨 KILL-SWITCH ACTIVATED\n\n"
            f"Daily loss limit reached: {loss_pct:.2f}%\n"
            f"All trading stopped.\n"
            f"Manual intervention required.",
            priority="CRITICAL"
        )
    
    def deactivate_kill_switch(self):
        """Deactivate kill-switch (manual intervention)"""
        self.kill_switch_active = False
        risk_logger.info("Kill-switch deactivated")
        
        alert_manager.send_alert_sync(
            "Kill-switch deactivated. Trading resumed.",
            priority="INFO"
        )
    
    def is_trading_allowed(self, symbol: str, capital: float, peak_capital: float) -> tuple[bool, str]:
        """
        Check if trading is allowed
        
        Args:
            symbol: Trading symbol
            capital: Current capital
            peak_capital: Peak capital
            
        Returns:
            Tuple of (allowed, reason)
        """
        # Check kill-switch
        if self.kill_switch_active:
            return False, "Kill-switch active"
        
        # Check daily loss
        daily_loss_reached, loss_pct = self.check_daily_loss(capital)
        if daily_loss_reached:
            return False, f"Daily loss limit reached: {loss_pct:.2f}%"
        
        # Check concurrent trades
        concurrent_limit, count = self.check_concurrent_trades()
        if concurrent_limit:
            return False, f"Concurrent trade limit: {count}/{self.max_concurrent_trades}"
        
        # Check correlation
        corr_limit, _ = self.check_correlation_exposure(symbol)
        if corr_limit:
            return False, "Correlation exposure limit"
        
        # Check drawdown
        critical_dd, dd_pct = self.check_drawdown(capital, peak_capital)
        if critical_dd:
            return False, f"Critical drawdown: {dd_pct:.2f}%"
        
        # Check consecutive losses
        consec_limit, count = self.check_consecutive_losses()
        if consec_limit:
            return False, f"Too many consecutive losses: {count}"
        
        return True, "Trading allowed"
    
    def _send_risk_alert(self, level: str, loss_pct: float):
        """Send risk alert"""
        alert_manager.send_alert_sync(
            f"Daily loss {level}: {loss_pct:.2f}%\n"
            f"Limit: {self.max_daily_loss_pct}%",
            priority="WARNING" if level == "warning" else "CRITICAL"
        )
    
    def _send_drawdown_alert(self, level: str, dd_pct: float):
        """Send drawdown alert"""
        alert_manager.send_alert_sync(
            f"Drawdown {level}: {dd_pct:.2f}%",
            priority="WARNING" if level == "warning" else "CRITICAL"
        )
    
    def _send_consecutive_loss_alert(self, count: int):
        """Send consecutive loss alert"""
        alert_manager.send_alert_sync(
            f"Consecutive losses: {count}\n"
            f"Review strategy performance.",
            priority="WARNING"
        )


# Global risk monitor instance
risk_monitor = RiskMonitor()
