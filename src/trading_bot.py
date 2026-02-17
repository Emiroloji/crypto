"""Main trading bot orchestrator"""

import asyncio
from typing import Dict, List
from datetime import datetime
import pandas as pd

from src.config.settings import settings
from src.data.exchange_client import binance_client
from src.data.market_data import MarketDataManager
from src.signals.signal_generator import signal_generator
from src.signals.scoring_engine import scoring_engine
from src.execution.trade_executor import trade_executor
from src.risk.risk_monitor import risk_monitor
from src.risk.stop_loss import stop_loss_manager
from src.database.connection import get_db
from src.database.models import Position
from src.utils.logger import main_logger
from src.utils.alerts import alert_manager


class TradingBot:
    """Main trading bot orchestrator"""
    
    def __init__(self):
        self.running = False
        self.trading_pairs = settings.get_trading_pairs()
        self.timeframes = settings.get_timeframes()
        self.market_data_manager = MarketDataManager()
    
    async def start(self):
        """Start the trading bot"""
        main_logger.info("🚀 Starting trading bot...")
        
        # Send startup alert
        await alert_manager.send_system_alert(
            f"Trading bot started\n"
            f"Pairs: {', '.join(self.trading_pairs)}\n"
            f"Timeframes: {', '.join(self.timeframes)}\n"
            f"Paper Trading: {settings.is_paper_trading()}",
            is_critical=False
        )
        
        self.running = True
        
        # Start main loop
        await self.run_loop()
    
    async def stop(self):
        """Stop the trading bot"""
        main_logger.info("Stopping trading bot...")
        self.running = False
        
        await alert_manager.send_system_alert(
            "Trading bot stopped",
            is_critical=False
        )
    
    async def run_loop(self):
        """Main trading loop"""
        while self.running:
            try:
                # Update capital
                await trade_executor.update_capital()
                
                # Process each trading pair
                for symbol in self.trading_pairs:
                    await self.process_symbol(symbol)
                
                # Update open positions
                await self.update_positions()
                
                # Wait before next iteration
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                main_logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(60)
    
    async def process_symbol(self, symbol: str):
        """
        Process a single trading symbol
        
        Args:
            symbol: Trading pair to process
        """
        try:
            main_logger.info(f"Processing {symbol}...")
            
            # Fetch latest market data
            df = await binance_client.fetch_ohlcv(
                symbol,
                timeframe='5m',  # Primary timeframe
                limit=200
            )
            
            if df.empty:
                main_logger.warning(f"No data for {symbol}")
                return
            
            # Save to database
            self.market_data_manager.save_ohlcv(df)
            
            # Fetch order book
            order_book = await binance_client.fetch_order_book(symbol, limit=20)
            self.market_data_manager.save_order_book(order_book)
            
            # Generate signal
            signal_data = signal_generator.generate_signal(
                symbol=symbol,
                df=df,
                order_book_data=order_book,
                sentiment_score=0.0,  # TODO: Integrate sentiment
                onchain_score=0.0,    # TODO: Integrate on-chain
            )
            
            if not signal_data:
                return
            
            # Save signal
            signal_id = signal_generator.save_signal(signal_data)
            if signal_id:
                signal_data['signal_id'] = signal_id
            
            # Check if signal is high confidence
            if signal_data['confidence_score'] >= 85:
                await alert_manager.send_signal_alert({
                    'symbol': symbol,
                    'direction': signal_data['direction'].value,
                    'confidence': signal_data['confidence_score'],
                    'risk_reward': signal_data['risk_reward_ratio'],
                    'signal_type': signal_data['signal_type'],
                })
            
            # Execute if valid
            trade_id = await trade_executor.execute_signal(signal_data)
            
            if trade_id:
                main_logger.info(f"Trade executed: ID {trade_id}")
            
        except Exception as e:
            main_logger.error(f"Error processing {symbol}: {e}")
    
    async def update_positions(self):
        """Update all open positions"""
        try:
            with get_db() as db:
                positions = db.query(Position).all()
                
                for position in positions:
                    await self.update_single_position(position)
                    
        except Exception as e:
            main_logger.error(f"Error updating positions: {e}")
    
    async def update_single_position(self, position: Position):
        """
        Update a single position
        
        Args:
            position: Position to update
        """
        try:
            # Fetch current price
            current_price = self.market_data_manager.get_latest_price(position.symbol)
            
            if not current_price:
                return
            
            # Update position price
            position.current_price = current_price
            
            # Calculate unrealized P&L
            if position.direction.value == 'LONG':
                pnl = (current_price - position.entry_price) * position.position_size
            else:
                pnl = (position.entry_price - current_price) * position.position_size
            
            position.unrealized_pnl = pnl
            
            # Check stop loss
            stop_hit = stop_loss_manager.check_stop_hit(
                current_price,
                position.stop_loss,
                position.direction
            )
            
            if stop_hit:
                main_logger.warning(f"Stop loss hit for {position.symbol}")
                await trade_executor.close_position(position.symbol, "stop_loss")
                return
            
            # Check take profit
            if position.direction.value == 'LONG':
                tp_hit = current_price >= position.take_profit
            else:
                tp_hit = current_price <= position.take_profit
            
            if tp_hit:
                main_logger.info(f"Take profit hit for {position.symbol}")
                await trade_executor.close_position(position.symbol, "take_profit")
                return
            
            # Update trailing stop
            # Fetch ATR for trailing calculation
            df = await binance_client.fetch_ohlcv(position.symbol, '5m', limit=50)
            if not df.empty:
                from src.indicators.volatility import calculate_atr
                atr = calculate_atr(df).iloc[-1]
                
                stop_update = stop_loss_manager.update_trailing_stop(
                    current_price=current_price,
                    entry_price=position.entry_price,
                    current_stop=position.stop_loss,
                    direction=position.direction,
                    atr=atr
                )
                
                if stop_update['stop_updated']:
                    position.stop_loss = stop_update['new_stop']
                    main_logger.info(
                        f"Stop updated for {position.symbol}: {stop_update['new_stop']:.2f}"
                    )
            
            # Save updates
            with get_db() as db:
                db.merge(position)
                db.commit()
                
        except Exception as e:
            main_logger.error(f"Error updating position {position.symbol}: {e}")


# Global trading bot instance
trading_bot = TradingBot()
