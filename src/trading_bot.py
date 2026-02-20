"""Main trading bot orchestrator"""

import asyncio
import pandas as pd
from typing import Dict, List
from datetime import datetime, timezone

from src.config.settings import settings
from src.data.exchange_client import binance_client
from src.data.market_data import MarketDataManager
from src.signals.signal_generator import signal_generator
from src.execution.trade_executor import trade_executor
from src.risk.risk_monitor import risk_monitor
from src.risk.stop_loss import stop_loss_manager
from src.indicators.volatility import calculate_atr
from src.database.connection import get_db
from src.database.models import Position
from src.utils.logger import main_logger
from src.utils.alerts import alert_manager


class TradingBot:
    """Main trading bot orchestrator"""
    
    def __init__(self):
        self.running = False
        self.capital = 0.0
        self.market_data_manager = MarketDataManager()
    
    @property
    def trading_pairs(self) -> List[str]:
        """Read trading pairs fresh from settings each time."""
        return settings.trading_pairs

    @property
    def timeframes(self) -> List[str]:
        """Read timeframes fresh from settings each time."""
        return settings.timeframes
    
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
                self.capital = trade_executor.capital
                
                # Fetch global sentiment ONCE per loop to avoid rate limiting
                try:
                    from src.data.sentiment_client import sentiment_client
                    from src.data.news_client import news_client
                    
                    # Run synchronous requests in a separate thread to prevent blocking the event loop
                    fear_greed_data = await asyncio.to_thread(sentiment_client.get_fear_greed_index)
                    fg_value = fear_greed_data['value'] if fear_greed_data else 50
                    
                    news_items = await asyncio.to_thread(news_client.get_latest_news, "BTC", 20)
                    
                    # Sentiment analysis is CPU-bound but fast, run synchronously or also in thread
                    news_sentiment = news_client.analyze_news_sentiment(news_items)
                    news_score = news_sentiment['sentiment_score'] # -100 to +100
                    
                    # Convert news to 0-100 where 50 is neutral
                    normalized_news = (news_score + 100) / 2
                    
                    # Global bullish sentiment (0-100)
                    global_sentiment_score = (fg_value * 0.6) + (normalized_news * 0.4)
                except Exception as e:
                    main_logger.error(f"Error fetching global sentiment: {e}")
                    global_sentiment_score = 50.0  # Neutral fallback

                with get_db() as db:
                    # Process each trading pair
                    for symbol in self.trading_pairs:
                        await self.process_symbol(symbol, db, sentiment_score=global_sentiment_score)
                    
                    # Update open positions
                    await self.update_positions(db)
                
                # Wait before next iteration
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                main_logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(60)
    
    async def process_symbol(self, symbol: str, db=None, sentiment_score: float = 50.0):
        """
        Process a single trading symbol
        
        Args:
            symbol: Trading pair to process
            db: Optional database session
            sentiment_score: Global sentiment score (0-100)
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
            self.market_data_manager.save_ohlcv(df, db)
            
            # Fetch order book
            order_book = await binance_client.fetch_order_book(symbol, limit=20)
            self.market_data_manager.save_order_book(order_book, db)
            
            # Generate signal
            signal_data = await signal_generator.generate_signal(
                symbol=symbol,
                df=df,
                order_book_data=order_book,
                sentiment_score=sentiment_score,
            )
            
            main_logger.info(f"Signal generated for {symbol}: {signal_data is not None}")
            
            if not signal_data:
                main_logger.info(f"No signal data returned for {symbol}")
                return
            
            main_logger.info(
                f"Signal details - Direction: {signal_data.get('direction')}, "
                f"Confidence: {signal_data.get('confidence_score', 0):.1f}%"
            )
            
            # Save signal
            signal_id = signal_generator.save_signal(signal_data, db)
            main_logger.info(f"Signal save result for {symbol}: ID={signal_id}")
            
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
            trade_id = await trade_executor.execute_signal(signal_data, db)
            
            if trade_id:
                main_logger.info(f"Trade executed: ID {trade_id}")
            
        except Exception as e:
            main_logger.error(f"Error processing {symbol}: {e}")
    
    async def update_positions(self, db=None):
        """Update all open positions"""
        try:
            # Use provided db or new session
            if db:
                positions = db.query(Position).all()
                for position in positions:
                    await self.update_single_position(position, db)
            else:
                with get_db() as new_db:
                    positions = new_db.query(Position).all()
                    for position in positions:
                        await self.update_single_position(position, new_db)
                    
        except Exception as e:
            main_logger.error(f"Error updating positions: {e}")
    
    async def update_single_position(self, position: Position, db=None):
        """
        Update a single position
        
        Args:
            position: Position to update
            db: Optional database session (reuse from caller to avoid nested sessions)
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
            
            # Check partial take profit
            if not getattr(position, 'partial_tp_hit', False):
                # Calculate required current profit to hit partial TP
                atr_distance = abs(position.take_profit - position.entry_price) / 5.0
                partial_tp_distance = atr_distance * 2.0
                
                partial_tp_price = (
                    position.entry_price + partial_tp_distance 
                    if position.direction.value == 'LONG' 
                    else position.entry_price - partial_tp_distance
                )
                
                partial_hit = (
                    current_price >= partial_tp_price if position.direction.value == 'LONG'
                    else current_price <= partial_tp_price
                )
                
                if partial_hit:
                    main_logger.info(f"Partial Take Profit (ATR * 2) hit for {position.symbol}. Selling 50% and moving to Breakeven.")
                    success = await trade_executor.close_partial_position(position.symbol, fraction=0.5)
                    if success:
                        position.partial_tp_hit = True
                        position.stop_loss = position.entry_price  # Move to breakeven
                        main_logger.info(f"Stop loss moved to breakeven ({position.entry_price}) for {position.symbol}")
            
            # Check take profit
            if position.direction.value == 'LONG':
                tp_hit = current_price >= position.take_profit
            else:
                tp_hit = current_price <= position.take_profit
            
            if tp_hit:
                main_logger.info(f"Full Take Profit hit for {position.symbol}")
                await trade_executor.close_position(position.symbol, "take_profit")
                return
            
            # Update trailing stop
            df = await binance_client.fetch_ohlcv(position.symbol, '5m', limit=50)
            if not df.empty:
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
            
            # Save updates — reuse caller's session if provided, else open a new one
            def _save(session):
                session.merge(position)
                session.commit()
            
            if db is not None:
                _save(db)
            else:
                with get_db() as new_db:
                    _save(new_db)
                
        except Exception as e:
            main_logger.error(f"Error updating position {position.symbol}: {e}")


# Global trading bot instance
trading_bot = TradingBot()
