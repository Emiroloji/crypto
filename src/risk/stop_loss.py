"""Stop loss management with ATR-based dynamic stops"""

from typing import Dict
import pandas as pd

from src.config.constants import RISK_CONSTANTS
from src.utils.logger import risk_logger
from src.database.models import TradeDirection


class StopLossManager:
    """Manage stop losses and trailing stops"""
    
    def __init__(self):
        self.atr_multiplier = RISK_CONSTANTS['atr_stop_multiplier']
        self.trailing_multiplier = RISK_CONSTANTS['trailing_stop_multiplier']
        self.breakeven_trigger = RISK_CONSTANTS['breakeven_trigger']
    
    def calculate_initial_stop(
        self,
        entry_price: float,
        direction: TradeDirection,
        atr: float
    ) -> float:
        """
        Calculate initial stop loss
        
        Args:
            entry_price: Entry price
            direction: Trade direction
            atr: Average True Range
            
        Returns:
            Stop loss price
        """
        if direction == TradeDirection.LONG:
            stop_loss = entry_price - (atr * self.atr_multiplier)
        else:  # SHORT
            stop_loss = entry_price + (atr * self.atr_multiplier)
        
        risk_logger.info(
            f"Initial stop: {stop_loss:.2f} "
            f"(Entry: {entry_price:.2f}, ATR: {atr:.2f})"
        )
        
        return stop_loss
    
    def update_trailing_stop(
        self,
        current_price: float,
        entry_price: float,
        current_stop: float,
        direction: TradeDirection,
        atr: float
    ) -> Dict:
        """
        Update trailing stop loss
        
        Args:
            current_price: Current market price
            entry_price: Entry price
            current_stop: Current stop loss
            direction: Trade direction
            atr: Average True Range
            
        Returns:
            Dictionary with updated stop information
        """
        new_stop = current_stop
        moved_to_breakeven = False
        
        if direction == TradeDirection.LONG:
            # Calculate profit
            profit = current_price - entry_price
            
            # Move to breakeven if profit >= entry risk
            if profit >= (entry_price - current_stop) * self.breakeven_trigger:
                if current_stop < entry_price:
                    new_stop = entry_price
                    moved_to_breakeven = True
                    risk_logger.info("Stop moved to breakeven")
            
            # Trail stop if in profit
            if current_price > entry_price:
                trailing_stop = current_price - (atr * self.trailing_multiplier)
                if trailing_stop > current_stop:
                    new_stop = trailing_stop
                    risk_logger.info(f"Trailing stop updated: {new_stop:.2f}")
        
        else:  # SHORT
            # Calculate profit
            profit = entry_price - current_price
            
            # Move to breakeven
            if profit >= (current_stop - entry_price) * self.breakeven_trigger:
                if current_stop > entry_price:
                    new_stop = entry_price
                    moved_to_breakeven = True
                    risk_logger.info("Stop moved to breakeven")
            
            # Trail stop if in profit
            if current_price < entry_price:
                trailing_stop = current_price + (atr * self.trailing_multiplier)
                if trailing_stop < current_stop:
                    new_stop = trailing_stop
                    risk_logger.info(f"Trailing stop updated: {new_stop:.2f}")
        
        return {
            'new_stop': new_stop,
            'stop_updated': new_stop != current_stop,
            'moved_to_breakeven': moved_to_breakeven,
        }
    
    def check_stop_hit(
        self,
        current_price: float,
        stop_loss: float,
        direction: TradeDirection
    ) -> bool:
        """
        Check if stop loss is hit
        
        Args:
            current_price: Current market price
            stop_loss: Stop loss price
            direction: Trade direction
            
        Returns:
            True if stop is hit
        """
        if direction == TradeDirection.LONG:
            return current_price <= stop_loss
        else:  # SHORT
            return current_price >= stop_loss


# Global stop loss manager instance
stop_loss_manager = StopLossManager()
