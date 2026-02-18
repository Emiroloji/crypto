"""Performance metrics calculation"""

from typing import Dict, List
from datetime import datetime, timedelta, timezone
import numpy as np
from sqlalchemy import and_, func

from src.database.connection import get_db
from src.database.models import Trade, Performance, TradeStatus
from src.utils.logger import main_logger


class PerformanceMetrics:
    """Calculate trading performance metrics"""
    
    @staticmethod
    def calculate_daily_metrics(date: datetime, starting_capital: float) -> Dict:
        """
        Calculate performance metrics for a specific day
        
        Args:
            date: Date to calculate metrics for
            starting_capital: Starting capital for the day
            
        Returns:
            Dictionary with performance metrics
        """
        try:
            with get_db() as db:
                # Get all closed trades for the day
                trades = db.query(Trade).filter(
                    and_(
                        func.date(Trade.entry_timestamp) == date.date(),
                        Trade.status == TradeStatus.CLOSED
                    )
                ).all()
                
                if not trades:
                    return None
                
                # Calculate basic metrics
                total_trades = len(trades)
                winning_trades = sum(1 for t in trades if t.pnl and t.pnl > 0)
                losing_trades = sum(1 for t in trades if t.pnl and t.pnl < 0)
                
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                
                # Calculate P&L
                gross_profit = sum(t.pnl for t in trades if t.pnl and t.pnl > 0)
                gross_loss = sum(t.pnl for t in trades if t.pnl and t.pnl < 0)
                net_pnl = gross_profit + gross_loss
                fees_paid = sum(t.fees for t in trades if t.fees)
                
                # Calculate profit factor
                profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else 0
                
                # Calculate expectancy
                avg_win = gross_profit / winning_trades if winning_trades > 0 else 0
                avg_loss = abs(gross_loss / losing_trades) if losing_trades > 0 else 0
                expectancy = (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * avg_loss)
                
                # Calculate ending capital
                ending_capital = starting_capital + net_pnl
                
                # Calculate returns
                returns = [t.pnl / starting_capital for t in trades if t.pnl]
                
                # Calculate Sharpe ratio (annualized)
                if len(returns) > 1:
                    returns_array = np.array(returns)
                    sharpe_ratio = (
                        np.mean(returns_array) / np.std(returns_array) * np.sqrt(365)
                        if np.std(returns_array) > 0 else 0
                    )
                else:
                    sharpe_ratio = 0
                
                # Calculate Sortino ratio (downside deviation)
                downside_returns = [r for r in returns if r < 0]
                if len(downside_returns) > 1:
                    downside_std = np.std(downside_returns)
                    sortino_ratio = (
                        np.mean(returns) / downside_std * np.sqrt(365)
                        if downside_std > 0 else 0
                    )
                else:
                    sortino_ratio = 0
                
                # Calculate max drawdown
                cumulative_returns = np.cumsum(returns)
                running_max = np.maximum.accumulate(cumulative_returns)
                drawdown = (cumulative_returns - running_max) / starting_capital * 100
                max_drawdown = abs(np.min(drawdown)) if len(drawdown) > 0 else 0
                
                # Find peak capital
                peak_capital = max(starting_capital + np.max(cumulative_returns) * starting_capital, starting_capital)
                
                return {
                    'date': date,
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades,
                    'win_rate': win_rate,
                    'gross_profit': gross_profit,
                    'gross_loss': gross_loss,
                    'net_pnl': net_pnl,
                    'fees_paid': fees_paid,
                    'profit_factor': profit_factor,
                    'expectancy': expectancy,
                    'sharpe_ratio': sharpe_ratio,
                    'sortino_ratio': sortino_ratio,
                    'max_drawdown': max_drawdown,
                    'starting_capital': starting_capital,
                    'ending_capital': ending_capital,
                    'peak_capital': peak_capital,
                }
                
        except Exception as e:
            main_logger.error(f"Error calculating daily metrics: {e}")
            return None
    
    @staticmethod
    def save_daily_performance(metrics: Dict) -> bool:
        """
        Save daily performance to database
        
        Args:
            metrics: Performance metrics dictionary
            
        Returns:
            Success status
        """
        if not metrics:
            return False
        
        try:
            with get_db() as db:
                # Check if record exists
                existing = db.query(Performance).filter(
                    func.date(Performance.date) == metrics['date'].date()
                ).first()
                
                if existing:
                    # Update existing
                    for key, value in metrics.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                else:
                    # Create new
                    performance = Performance(**metrics)
                    db.add(performance)
                
                db.commit()
                main_logger.info(f"Saved performance for {metrics['date'].date()}")
                return True
                
        except Exception as e:
            main_logger.error(f"Error saving performance: {e}")
            return False
    
    @staticmethod
    def get_overall_stats(days: int = 30) -> Dict:
        """
        Get overall statistics for a period
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with overall statistics
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            
            with get_db() as db:
                # Get all closed trades in period
                trades = db.query(Trade).filter(
                    and_(
                        Trade.entry_timestamp >= cutoff,
                        Trade.status == TradeStatus.CLOSED
                    )
                ).all()
                
                if not trades:
                    return {}
                
                # Calculate overall metrics
                total_trades = len(trades)
                winning_trades = sum(1 for t in trades if t.pnl and t.pnl > 0)
                
                total_pnl = sum(t.pnl for t in trades if t.pnl)
                
                # Best and worst trades
                best_trade = max(trades, key=lambda t: t.pnl if t.pnl else 0)
                worst_trade = min(trades, key=lambda t: t.pnl if t.pnl else 0)
                
                # Average hold time
                hold_times = [
                    (t.exit_timestamp - t.entry_timestamp).total_seconds() / 3600
                    for t in trades if t.exit_timestamp
                ]
                avg_hold_time = np.mean(hold_times) if hold_times else 0
                
                # Get performance records
                performance = db.query(Performance).filter(
                    Performance.date >= cutoff
                ).all()
                
                avg_sharpe = np.mean([p.sharpe_ratio for p in performance if p.sharpe_ratio])
                avg_sortino = np.mean([p.sortino_ratio for p in performance if p.sortino_ratio])
                max_dd = max([p.max_drawdown for p in performance], default=0)
                
                return {
                    'period_days': days,
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
                    'total_pnl': total_pnl,
                    'best_trade_pnl': best_trade.pnl if best_trade else 0,
                    'worst_trade_pnl': worst_trade.pnl if worst_trade else 0,
                    'avg_hold_time_hours': avg_hold_time,
                    'avg_sharpe_ratio': avg_sharpe,
                    'avg_sortino_ratio': avg_sortino,
                    'max_drawdown': max_dd,
                }
                
        except Exception as e:
            main_logger.error(f"Error calculating overall stats: {e}")
            return {}


# Global performance metrics instance
performance_metrics = PerformanceMetrics()
