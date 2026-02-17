"""Dynamic position sizing with Kelly Criterion"""

from typing import Dict, Optional
import numpy as np

from src.config.settings import settings
from src.utils.logger import risk_logger
from src.database.connection import get_db
from src.database.models import Performance


class PositionSizer:
    """Calculate optimal position sizes"""
    
    def __init__(self):
        self.max_position_pct = settings.max_position_size_pct
        self.risk_per_trade_pct = settings.risk_per_trade_pct
        self.max_leverage = settings.max_leverage
    
    def calculate_position_size(
        self,
        capital: float,
        entry_price: float,
        stop_loss: float,
        signal_quality: Optional[Dict] = None,
        use_kelly: bool = True
    ) -> Dict:
        """
        Calculate position size
        
        Args:
            capital: Available capital
            entry_price: Entry price
            stop_loss: Stop loss price
            signal_quality: Optional signal quality metrics
            use_kelly: Whether to use Kelly Criterion
            
        Returns:
            Dictionary with position sizing information
        """
        # Calculate risk per trade in dollars
        risk_amount = capital * (self.risk_per_trade_pct / 100)
        
        # Calculate risk per unit
        risk_per_unit = abs(entry_price - stop_loss)
        
        # Basic position size
        position_size = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
        
        # Apply Kelly Criterion adjustment if enabled
        if use_kelly and signal_quality:
            kelly_fraction = self._calculate_kelly_fraction()
            if kelly_fraction > 0:
                # Use fractional Kelly (more conservative)
                kelly_multiplier = min(kelly_fraction * 0.5, 1.0)  # Half Kelly
                position_size *= kelly_multiplier
                risk_logger.info(f"Kelly adjustment: {kelly_multiplier:.2f}x")
        
        # Apply signal quality adjustment
        if signal_quality:
            quality_multiplier = self._get_quality_multiplier(signal_quality)
            position_size *= quality_multiplier
            risk_logger.info(f"Quality adjustment: {quality_multiplier:.2f}x")
        
        # Calculate position value
        position_value = position_size * entry_price
        
        # Check against max position size
        max_position_value = capital * (self.max_position_pct / 100)
        if position_value > max_position_value:
            position_size = max_position_value / entry_price
            position_value = max_position_value
            risk_logger.warning(f"Position capped at {self.max_position_pct}% of capital")
        
        # Calculate required leverage
        required_leverage = position_value / capital
        
        # Check leverage limits
        if required_leverage > self.max_leverage:
            position_size = (capital * self.max_leverage) / entry_price
            position_value = position_size * entry_price
            required_leverage = self.max_leverage
            risk_logger.warning(f"Leverage capped at {self.max_leverage}x")
        
        # Calculate actual risk
        actual_risk = position_size * risk_per_unit
        actual_risk_pct = (actual_risk / capital) * 100
        
        return {
            'position_size': position_size,
            'position_value': position_value,
            'leverage': required_leverage,
            'risk_amount': actual_risk,
            'risk_percent': actual_risk_pct,
            'risk_per_unit': risk_per_unit,
        }
    
    def _calculate_kelly_fraction(self) -> float:
        """
        Calculate Kelly Criterion fraction based on historical performance
        
        Returns:
            Kelly fraction (0 to 1)
        """
        try:
            with get_db() as db:
                # Get recent performance data
                recent_perf = db.query(Performance).order_by(
                    Performance.date.desc()
                ).limit(30).all()
                
                if not recent_perf or len(recent_perf) < 10:
                    return 0.25  # Default conservative value
                
                # Calculate win rate and average win/loss
                total_trades = sum(p.total_trades for p in recent_perf)
                winning_trades = sum(p.winning_trades for p in recent_perf)
                
                if total_trades == 0:
                    return 0.25
                
                win_rate = winning_trades / total_trades
                
                # Calculate average win and loss
                total_profit = sum(p.gross_profit for p in recent_perf)
                total_loss = abs(sum(p.gross_loss for p in recent_perf))
                
                if winning_trades == 0 or (total_trades - winning_trades) == 0:
                    return 0.25
                
                avg_win = total_profit / winning_trades
                avg_loss = total_loss / (total_trades - winning_trades)
                
                if avg_loss == 0:
                    return 0.25
                
                # Kelly formula: f = (p * b - q) / b
                # where p = win rate, q = loss rate, b = avg_win / avg_loss
                b = avg_win / avg_loss
                kelly = (win_rate * b - (1 - win_rate)) / b
                
                # Cap Kelly between 0 and 1
                kelly = max(0, min(kelly, 1.0))
                
                risk_logger.info(
                    f"Kelly Criterion: {kelly:.2f} "
                    f"(WR: {win_rate:.2%}, W/L: {b:.2f})"
                )
                
                return kelly
                
        except Exception as e:
            risk_logger.error(f"Error calculating Kelly fraction: {e}")
            return 0.25  # Default conservative value
    
    def _get_quality_multiplier(self, signal_quality: Dict) -> float:
        """
        Get position size multiplier based on signal quality
        
        Args:
            signal_quality: Signal quality metrics
            
        Returns:
            Multiplier (0.5 to 1.5)
        """
        grade = signal_quality.get('grade', 'C')
        
        multipliers = {
            'A': 1.3,  # Increase position by 30%
            'B': 1.1,  # Increase position by 10%
            'C': 1.0,  # Standard position
            'D': 0.7,  # Reduce position by 30%
        }
        
        return multipliers.get(grade, 1.0)


# Global position sizer instance
position_sizer = PositionSizer()
