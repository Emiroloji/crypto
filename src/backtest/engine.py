"""
Simple Backtesting Engine for Crypto Trading Strategies
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass
from src.utils.logger import execution_logger as logger

@dataclass
class Trade:
    symbol: str
    entry_price: float
    exit_price: Optional[float]
    amount: float
    side: str  # 'LONG' or 'SHORT'
    entry_time: datetime
    exit_time: Optional[datetime]
    pnl: float = 0.0
    pnl_percent: float = 0.0
    status: str = 'OPEN'  # OPEN, CLOSED

class BacktestEngine:
    def __init__(self, initial_capital: float = 10000.0, fee_rate: float = 0.001):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.fee_rate = fee_rate
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict] = []
        
    def run(self, 
            data: pd.DataFrame, 
            strategy_fn: Callable[[pd.DataFrame, int], Dict],
            symbol: str = "BTC/USDT"):
        """
        Run backtest on provided data using a strategy function.
        
        Args:
            data: DataFrame with OHLCV data
            strategy_fn: Function that takes (df, current_index) and returns signal dict
                         {'action': 'BUY'/'SELL'/'HOLD', 'amount': float}
            symbol: Trading pair symbol
        """
        logger.info(f"Starting backtest for {symbol} with ${self.initial_capital}")
        
        self.current_capital = self.initial_capital
        self.trades = []
        self.equity_curve = []
        
        position = None  # None or Trade object
        
        # Ensure data is sorted
        df = data.sort_values('timestamp').reset_index(drop=True)
        
        for i in range(50, len(df)):
            # Update equity curve
            current_value = self.current_capital
            if position:
                current_price = df.iloc[i]['close']
                if position.side == 'LONG':
                    unrealized_pnl = (current_price - position.entry_price) * position.amount
                else:
                    unrealized_pnl = (position.entry_price - current_price) * position.amount
                current_value += unrealized_pnl
                
            self.equity_curve.append({
                'timestamp': df.iloc[i]['timestamp'],
                'equity': current_value
            })
            
            # Get signal from strategy
            # Pass slice of data up to current point to avoid lookahead bias
            # In a real engine, we'd be more careful about passing only past data
            signal = strategy_fn(df, i)
            
            current_price = df.iloc[i]['close']
            current_time = df.iloc[i]['timestamp']
            
            if signal['action'] == 'BUY':
                if position is None:
                    # Open LONG
                    amount_to_invest = min(self.current_capital, signal.get('amount_usd', self.current_capital * 0.95))
                    fee = amount_to_invest * self.fee_rate
                    net_investment = amount_to_invest - fee
                    amount = net_investment / current_price
                    
                    self.current_capital -= amount_to_invest
                    
                    position = Trade(
                        symbol=symbol,
                        entry_price=current_price,
                        exit_price=None,
                        amount=amount,
                        side='LONG',
                        entry_time=current_time,
                        exit_time=None
                    )
                elif position.side == 'SHORT':
                    # Close SHORT and Open LONG (Flip)
                    self._close_position(position, current_price, current_time)
                    position = None
                    # Re-evaluate logic for opening long could go here
            
            elif signal['action'] == 'SELL':
                if position and position.side == 'LONG':
                    # Close LONG
                    self._close_position(position, current_price, current_time)
                    position = None
                    
                elif position is None:
                    # Open SHORT (if supported)
                    pass 

        # Close any open position at the end
        if position:
            self._close_position(position, df.iloc[-1]['close'], df.iloc[-1]['timestamp'])
            
        return self._generate_report()

    def _close_position(self, trade: Trade, price: float, time: datetime):
        """Close an active trade"""
        trade.exit_price = price
        trade.exit_time = time
        trade.status = 'CLOSED'
        
        gross_value = trade.amount * price
        fee = gross_value * self.fee_rate
        net_value = gross_value - fee
        
        if trade.side == 'LONG':
            # Profit = (Exit - Entry) * Amount
            pnl = (price - trade.entry_price) * trade.amount
            initial_value = trade.amount * trade.entry_price
            
            # Net Value = Exit Value - Fee
            # We add Net Value back to capital
            self.current_capital += net_value
            
            # Pnl = Net Value - Cost
            realized_pnl = net_value - initial_value
            
        elif trade.side == 'SHORT':
            # Profit = (Entry - Exit) * Amount
            pnl = (trade.entry_price - price) * trade.amount
            initial_value = trade.amount * trade.entry_price
            
            # For SHORT:
            # We received Entry Value (Entry Price * Amount) when opening [Theoretically, simplified]
            # But in this simple engine we deducted "Cost" (collateral) at start.
            # To Close: We "Buy Back" at Exit Price.
            # Cost to Close = Exit Price * Amount + Fee
            # PnL = Initial Collateral + (Entry - Exit)*Amount - Fees
            
            # Simplified Capital Logic:
            # Capital was reduced by 'amount_to_invest' at open.
            # Return Capital = amount_to_invest + PnL
            
            # Logic:
            # Entry: Sold 'amount' @ entry_price. Value = amount * entry_price.
            # Exit: Bought 'amount' @ price. Cost = amount * price.
            # GW PnL = (Entry - Exit) * Amount
            
            gross_pnl = (trade.entry_price - price) * trade.amount
            
            # We paid fee on entry (deducted from capital).
            # We pay fee on exit:
            exit_fee = (price * trade.amount) * self.fee_rate
            
            realized_pnl = gross_pnl - exit_fee
            
            # Add back the original "investment" plus PnL
            # Assuming 1x leverage, investment ~= entry_value
            investment = trade.amount * trade.entry_price
            
            # Note: Entry fee was already deducted from capital in 'run' loop.
            # So capital += investment + realized_pnl
            self.current_capital += (investment + realized_pnl)
            
            initial_value = investment

        trade.pnl = realized_pnl
        trade.pnl_percent = (realized_pnl / initial_value) * 100 if initial_value > 0 else 0.0
        self.trades.append(trade)

    def _generate_report(self) -> Dict:
        """Generate performance report"""
        total_trades = len(self.trades)
        if total_trades == 0:
            return {"error": "No trades executed"}
            
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]
        
        win_rate = (len(winning_trades) / total_trades) * 100
        total_pnl = self.current_capital - self.initial_capital
        roi = (total_pnl / self.initial_capital) * 100
        
        return {
            "initial_capital": self.initial_capital,
            "final_capital": self.current_capital,
            "total_trades": total_trades,
            "win_rate": win_rate,
            "roi_percent": roi,
            "total_pnl": total_pnl,
            "max_drawdown": self._calculate_max_drawdown()
        }
        
    def _calculate_max_drawdown(self) -> float:
        if not self.equity_curve:
            return 0.0
            
        peak = self.equity_curve[0]['equity']
        max_dd = 0.0
        
        for point in self.equity_curve:
            equity = point['equity']
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100
            if dd > max_dd:
                max_dd = dd
                
        return max_dd
