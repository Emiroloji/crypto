"""Trade execution orchestrator"""

from typing import Dict, Optional
from datetime import datetime, timezone

from src.config.settings import settings

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
        self.capital = settings.initial_capital
        self.peak_capital = settings.initial_capital
    
    async def update_capital(self):
        """Update current capital from exchange"""
        try:
            balance = await self.exchange.get_balance()
            self.capital = balance.get('USDT', settings.initial_capital)
            
            # Update peak capital
            if self.capital > self.peak_capital:
                self.peak_capital = self.capital
                
            execution_logger.info(f"Capital updated: ${self.capital:.2f}")
            
        except Exception as e:
            execution_logger.error(f"Error updating capital: {e}")
    
    async def execute_signal(self, signal_data: Dict, db=None) -> Optional[int]:
        """
        Execute trade from signal
        
        Args:
            signal_data: Signal information
            db: Optional database session
            
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
            trade_id = await self._place_order(signal_data, position_info, signal_quality, db)
            
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
        signal_quality: Dict,
        db=None
    ) -> Optional[int]:
        """
        Place order on exchange
        
        Args:
            signal_data: Signal information
            position_info: Position sizing information
            signal_quality: Signal quality metrics
            db: Optional database session
            
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
            
            # Save trade and position in a single transaction
            trade_id = self._save_trade_and_position(signal_data, position_info, order, db)
            
            return trade_id
            
        except Exception as e:
            execution_logger.error(f"Error placing order: {e}")
            return None
    
    def _save_trade_and_position(
        self,
        signal_data: Dict,
        position_info: Dict,
        order: Dict,
        db=None
    ) -> Optional[int]:
        """Save trade and position in a single atomic DB transaction"""
        
        def _save(session):
            signal_id = signal_data.get('signal_id')
            entry_price = order.get('price', signal_data['entry_price'])
            now = datetime.now(timezone.utc)

            trade = Trade(
                symbol=signal_data['symbol'],
                direction=signal_data['direction'],
                status=TradeStatus.OPEN,
                entry_timestamp=now,
                entry_price=entry_price,
                position_size=position_info['position_size'],
                leverage=int(position_info['leverage']),
                stop_loss=signal_data['stop_loss'],
                take_profit=signal_data['take_profit'],
                signal_id=signal_id,
                exchange_order_id=order.get('id'),
            )
            session.add(trade)

            position = Position(
                symbol=signal_data['symbol'],
                direction=signal_data['direction'],
                entry_price=entry_price,
                current_price=entry_price,
                position_size=position_info['position_size'],
                leverage=int(position_info['leverage']),
                unrealized_pnl=0.0,
                stop_loss=signal_data['stop_loss'],
                take_profit=signal_data['take_profit'],
                opened_at=now,
            )
            session.add(position)
            session.commit()
            session.refresh(trade)
            
            execution_logger.info(
                f"Trade {trade.id} and position saved for {signal_data['symbol']}"
            )
            return trade.id

        try:
            if db:
                return _save(db)
            else:
                with get_db() as new_db:
                    return _save(new_db)

        except Exception as e:
            execution_logger.error(f"Error saving trade and position: {e}")
            return None
    
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
                fee_rate = settings.taker_fee_rate
                entry_fee = position.entry_price * position.position_size * fee_rate
                exit_fee = exit_price * position.position_size * fee_rate
                total_fees = entry_fee + exit_fee

                # Calculate P&L (net of both entry and exit fees)
                if position.direction == TradeDirection.LONG:
                    gross_pnl = (exit_price - position.entry_price) * position.position_size
                else:
                    gross_pnl = (position.entry_price - exit_price) * position.position_size

                pnl = gross_pnl - total_fees
                pnl_percent = (pnl / (position.entry_price * position.position_size)) * 100
                
                # Update trade record
                trade = db.query(Trade).filter(
                    Trade.symbol == symbol,
                    Trade.status == TradeStatus.OPEN
                ).first()
                
                if trade:
                    trade.status = TradeStatus.CLOSED
                    trade.exit_timestamp = datetime.now(timezone.utc)
                    trade.exit_price = exit_price
                    trade.pnl = pnl
                    trade.pnl_percent = pnl_percent
                    trade.fees = total_fees
                    trade.notes = f"Closed: {reason}"
                
                # Delete position
                db.delete(position)
                db.commit()
                
                execution_logger.info(
                    f"Position closed: {symbol} P&L: ${pnl:.2f} ({pnl_percent:.2f}%) Fee: ${exit_fee:.2f}"
                )
                
                return True
                
        except Exception as e:
            execution_logger.error(f"Error closing position: {e}")
            return False

    async def close_partial_position(
        self,
        symbol: str,
        fraction: float = 0.5,
        reason: str = "partial_take_profit"
    ) -> bool:
        """
        Close a fraction of an open position
        
        Args:
            symbol: Trading symbol
            fraction: Fraction of position to close (e.g., 0.5 for 50%)
            reason: Reason for closing
            
        Returns:
            Success status
        """
        if not (0 < fraction < 1):
            execution_logger.error(f"Invalid fraction {fraction} for partial close on {symbol}")
            return False
            
        try:
            with get_db() as db:
                # Get position
                position = db.query(Position).filter(
                    Position.symbol == symbol
                ).first()
                
                if not position:
                    execution_logger.warning(f"No position found for {symbol} to partially close")
                    return False
                
                # Determine order side (opposite of position)
                side = 'sell' if position.direction == TradeDirection.LONG else 'buy'
                
                amount_to_close = position.position_size * fraction
                
                # Place closing order
                order = await self.exchange.place_order(
                    symbol=symbol,
                    side=side,
                    order_type='market',
                    amount=amount_to_close
                )
                
                exit_price = order.get('price', position.current_price)
                fee_rate = settings.taker_fee_rate
                
                # Calculate fees for the closed portion
                entry_fee = position.entry_price * amount_to_close * fee_rate
                exit_fee = exit_price * amount_to_close * fee_rate
                total_fees = entry_fee + exit_fee

                # Calculate P&L for the closed portion
                if position.direction == TradeDirection.LONG:
                    gross_pnl = (exit_price - position.entry_price) * amount_to_close
                else:
                    gross_pnl = (position.entry_price - exit_price) * amount_to_close

                pnl = gross_pnl - total_fees
                pnl_percent = (pnl / (position.entry_price * amount_to_close)) * 100
                
                # Create a new trade record for the partial close
                trade_record = db.query(Trade).filter(
                    Trade.symbol == symbol,
                    Trade.status == TradeStatus.OPEN
                ).first()
                
                # We do not close the original Trade entry if we want to track it entirely or 
                # we just log a separate CLOSED Trade record representing this partial exit.
                # Here we create a new Trade just to record the partial PnL.
                if trade_record:
                    partial_trade = Trade(
                        symbol=symbol,
                        direction=position.direction,
                        status=TradeStatus.CLOSED,
                        entry_timestamp=trade_record.entry_timestamp,
                        entry_price=position.entry_price,
                        position_size=amount_to_close,
                        leverage=position.leverage,
                        exit_timestamp=datetime.now(timezone.utc),
                        exit_price=exit_price,
                        pnl=pnl,
                        pnl_percent=pnl_percent,
                        fees=total_fees,
                        notes=f"Partial Close ({fraction*100}%): {reason}"
                    )
                    db.add(partial_trade)
                
                # Reduce position size
                position.position_size -= amount_to_close
                if trade_record:
                    trade_record.position_size -= amount_to_close
                db.commit()
                
                execution_logger.info(
                    f"Partial Position closed (50%): {symbol} P&L: ${pnl:.2f} ({pnl_percent:.2f}%) Fee: ${exit_fee:.2f}"
                )
                
                return True
                
        except Exception as e:
            execution_logger.error(f"Error partially closing position: {e}")
            return False


# Global trade executor instance
trade_executor = TradeExecutor()
