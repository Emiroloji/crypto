"""Trade execution orchestrator"""

from typing import Dict, Optional
from datetime import datetime

from src.signals.signal_generator import signal_generator
from src.signals.scoring_engine import scoring_engine
from src.risk.position_sizer import position_sizer
from src.risk.risk_monitor import risk_monitor
from src.risk.stop_loss import stop_loss_manager
from src.data.exchange_client import binance_client
from src.database.connection import get_db
from src.database.models import Trade, Position, Signal, TradeStatus, TradeDirection
from src.utils.logger import execution_logger
from src.utils.alerts import alert_manager


class TradeExecutor:
    """Execute trades based on validated signals"""
    
    def __init__(self, exchange_client=None):
        self.exchange = exchange_client or binance_client
        self.capital = 10000.0  # Default, should be updated from account
        self.peak_capital = 10000.0
    
    async def update_capital(self):
        """Update current capital from exchange"""
        try:
            balance = await self.exchange.get_balance()
            self.capital = balance.get('USDT', 10000.0)
            
            # Update peak capital
            if self.capital > self.peak_capital:
                self.peak_capital = self.capital
                
            execution_logger.info(f"Capital updated: ${self.capital:.2f}")
            
        except Exception as e:
            execution_logger.error(f"Error updating capital: {e}")
    
    async def execute_signal(self, signal_data: Dict) -> Optional[int]:
        """
        Execute trade from signal
        
        Args:
            signal_data: Signal information
            
        Returns:
            Trade ID or None
        """
        try:
            symbol = signal_data['symbol']
            
            # Update capital
            await self.update_capital()
            
            # Check if trading is allowed
            allowed, reason = risk_monitor.is_trading_allowed(
                symbol, self.capital, self.peak_capital
            )
            
            if not allowed:
                execution_logger.warning(f"Trading not allowed: {reason}")
                return None
            
            # Validate signal
            is_valid, validation_reason = scoring_engine.validate_signal(signal_data)
            if not is_valid:
                execution_logger.info(f"Signal not valid: {validation_reason}")
                return None
            
            # Calculate signal quality
            signal_quality = scoring_engine.calculate_signal_quality(signal_data)
            
            # Calculate position size
            position_info = position_sizer.calculate_position_size(
                capital=self.capital,
                entry_price=signal_data['entry_price'],
                stop_loss=signal_data['stop_loss'],
                signal_quality=signal_quality,
                use_kelly=True
            )
            
            # Execute order
            trade_id = await self._place_order(signal_data, position_info, signal_quality)
            
            if trade_id:
                # Send alert
                await alert_manager.send_trade_alert({
                    'symbol': symbol,
                    'direction': signal_data['direction'].value,
                    'entry_price': signal_data['entry_price'],
                    'position_size': position_info['position_size'],
                    'stop_loss': signal_data['stop_loss'],
                    'take_profit': signal_data['take_profit'],
                    'confidence': signal_data['confidence_score'],
                })
            
            return trade_id
            
        except Exception as e:
            execution_logger.error(f"Error executing signal: {e}")
            return None
    
    async def _place_order(
        self,
        signal_data: Dict,
        position_info: Dict,
        signal_quality: Dict
    ) -> Optional[int]:
        """
        Place order on exchange
        
        Args:
            signal_data: Signal information
            position_info: Position sizing information
            signal_quality: Signal quality metrics
            
        Returns:
            Trade ID or None
        """
        try:
            symbol = signal_data['symbol']
            direction = signal_data['direction']
            entry_price = signal_data['entry_price']
            position_size = position_info['position_size']
            
            # Determine order side
            side = 'buy' if direction == TradeDirection.LONG else 'sell'
            
            # Place market order
            order = await self.exchange.place_order(
                symbol=symbol,
                side=side,
                order_type='market',
                amount=position_size,
                params={'leverage': int(position_info['leverage'])}
            )
            
            execution_logger.info(
                f"Order placed: {order['id']} - {side.upper()} {position_size} {symbol}"
            )
            
            # Save trade to database
            trade_id = self._save_trade(signal_data, position_info, order)
            
            # Create position record
            self._create_position(signal_data, position_info, order)
            
            return trade_id
            
        except Exception as e:
            execution_logger.error(f"Error placing order: {e}")
            return None
    
    def _save_trade(
        self,
        signal_data: Dict,
        position_info: Dict,
        order: Dict
    ) -> Optional[int]:
        """Save trade to database"""
        try:
            with get_db() as db:
                # Get signal ID if exists
                signal_id = None
                if 'signal_id' in signal_data:
                    signal_id = signal_data['signal_id']
                
                trade = Trade(
                    symbol=signal_data['symbol'],
                    direction=signal_data['direction'],
                    status=TradeStatus.OPEN,
                    entry_timestamp=datetime.utcnow(),
                    entry_price=order.get('price', signal_data['entry_price']),
                    position_size=position_info['position_size'],
                    leverage=int(position_info['leverage']),
                    stop_loss=signal_data['stop_loss'],
                    take_profit=signal_data['take_profit'],
                    signal_id=signal_id,
                    exchange_order_id=order.get('id'),
                )
                
                db.add(trade)
                db.commit()
                db.refresh(trade)
                
                execution_logger.info(f"Trade saved: ID {trade.id}")
                return trade.id
                
        except Exception as e:
            execution_logger.error(f"Error saving trade: {e}")
            return None
    
    def _create_position(
        self,
        signal_data: Dict,
        position_info: Dict,
        order: Dict
    ):
        """Create position record"""
        try:
            with get_db() as db:
                position = Position(
                    symbol=signal_data['symbol'],
                    direction=signal_data['direction'],
                    entry_price=order.get('price', signal_data['entry_price']),
                    current_price=order.get('price', signal_data['entry_price']),
                    position_size=position_info['position_size'],
                    leverage=int(position_info['leverage']),
                    unrealized_pnl=0.0,
                    stop_loss=signal_data['stop_loss'],
                    take_profit=signal_data['take_profit'],
                    opened_at=datetime.utcnow(),
                )
                
                db.add(position)
                db.commit()
                
                execution_logger.info(f"Position created for {signal_data['symbol']}")
                
        except Exception as e:
            execution_logger.error(f"Error creating position: {e}")
    
    async def close_position(
        self,
        symbol: str,
        reason: str = "manual"
    ) -> bool:
        """
        Close open position
        
        Args:
            symbol: Trading symbol
            reason: Reason for closing
            
        Returns:
            Success status
        """
        try:
            with get_db() as db:
                # Get position
                position = db.query(Position).filter(
                    Position.symbol == symbol
                ).first()
                
                if not position:
                    execution_logger.warning(f"No position found for {symbol}")
                    return False
                
                # Determine order side (opposite of position)
                side = 'sell' if position.direction == TradeDirection.LONG else 'buy'
                
                # Place closing order
                order = await self.exchange.place_order(
                    symbol=symbol,
                    side=side,
                    order_type='market',
                    amount=position.position_size
                )
                
                exit_price = order.get('price', position.current_price)
                
                # Calculate P&L
                if position.direction == TradeDirection.LONG:
                    pnl = (exit_price - position.entry_price) * position.position_size
                else:
                    pnl = (position.entry_price - exit_price) * position.position_size
                
                pnl_percent = (pnl / (position.entry_price * position.position_size)) * 100
                
                # Update trade record
                trade = db.query(Trade).filter(
                    Trade.symbol == symbol,
                    Trade.status == TradeStatus.OPEN
                ).first()
                
                if trade:
                    trade.status = TradeStatus.CLOSED
                    trade.exit_timestamp = datetime.utcnow()
                    trade.exit_price = exit_price
                    trade.pnl = pnl
                    trade.pnl_percent = pnl_percent
                    trade.notes = f"Closed: {reason}"
                
                # Delete position
                db.delete(position)
                db.commit()
                
                execution_logger.info(
                    f"Position closed: {symbol} P&L: ${pnl:.2f} ({pnl_percent:.2f}%)"
                )
                
                return True
                
        except Exception as e:
            execution_logger.error(f"Error closing position: {e}")
            return False


# Global trade executor instance
trade_executor = TradeExecutor()
