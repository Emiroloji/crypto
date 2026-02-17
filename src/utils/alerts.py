"""Alert system for critical events via Telegram"""

import asyncio
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError

from src.config.settings import settings
from src.utils.logger import main_logger


class AlertManager:
    """Manage alerts via Telegram"""
    
    def __init__(self):
        self.bot: Optional[Bot] = None
        self.chat_id = settings.telegram_chat_id
        
        if settings.telegram_bot_token:
            try:
                self.bot = Bot(token=settings.telegram_bot_token)
            except Exception as e:
                main_logger.error(f"Failed to initialize Telegram bot: {e}")
    
    async def send_alert(self, message: str, priority: str = "INFO") -> bool:
        """
        Send alert message
        
        Args:
            message: Alert message
            priority: Priority level (INFO, WARNING, CRITICAL)
            
        Returns:
            Success status
        """
        if not self.bot or not self.chat_id:
            main_logger.warning("Telegram bot not configured, skipping alert")
            return False
        
        # Format message with priority
        emoji_map = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "CRITICAL": "🚨",
        }
        emoji = emoji_map.get(priority, "📢")
        formatted_message = f"{emoji} *{priority}*\n\n{message}"
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=formatted_message,
                parse_mode="Markdown"
            )
            main_logger.info(f"Alert sent: {priority} - {message[:50]}...")
            return True
        except TelegramError as e:
            main_logger.error(f"Failed to send Telegram alert: {e}")
            return False
    
    def send_alert_sync(self, message: str, priority: str = "INFO") -> bool:
        """
        Synchronous wrapper for send_alert
        
        Args:
            message: Alert message
            priority: Priority level
            
        Returns:
            Success status
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new task if loop is already running
                asyncio.create_task(self.send_alert(message, priority))
                return True
            else:
                return loop.run_until_complete(self.send_alert(message, priority))
        except Exception as e:
            main_logger.error(f"Failed to send alert: {e}")
            return False
    
    async def send_trade_alert(self, trade_data: dict) -> bool:
        """
        Send trade execution alert
        
        Args:
            trade_data: Trade information
            
        Returns:
            Success status
        """
        message = (
            f"🔔 *Trade Executed*\n\n"
            f"Symbol: {trade_data.get('symbol')}\n"
            f"Direction: {trade_data.get('direction')}\n"
            f"Entry: ${trade_data.get('entry_price'):.2f}\n"
            f"Size: {trade_data.get('position_size'):.4f}\n"
            f"Stop Loss: ${trade_data.get('stop_loss'):.2f}\n"
            f"Take Profit: ${trade_data.get('take_profit'):.2f}\n"
            f"Confidence: {trade_data.get('confidence', 0):.1f}%"
        )
        return await self.send_alert(message, "INFO")
    
    async def send_signal_alert(self, signal_data: dict) -> bool:
        """
        Send high-confidence signal alert
        
        Args:
            signal_data: Signal information
            
        Returns:
            Success status
        """
        message = (
            f"📊 *High Confidence Signal*\n\n"
            f"Symbol: {signal_data.get('symbol')}\n"
            f"Direction: {signal_data.get('direction')}\n"
            f"Confidence: {signal_data.get('confidence'):.1f}%\n"
            f"R/R: 1:{signal_data.get('risk_reward', 0):.2f}\n"
            f"Type: {signal_data.get('signal_type', 'N/A')}"
        )
        return await self.send_alert(message, "INFO")
    
    async def send_risk_alert(self, alert_type: str, details: dict) -> bool:
        """
        Send risk management alert
        
        Args:
            alert_type: Type of risk alert
            details: Alert details
            
        Returns:
            Success status
        """
        priority = "CRITICAL" if "kill" in alert_type.lower() else "WARNING"
        
        message = (
            f"⚠️ *Risk Alert: {alert_type}*\n\n"
            f"Details: {details.get('message', 'N/A')}\n"
            f"Current Loss: {details.get('current_loss_pct', 0):.2f}%\n"
            f"Action: {details.get('action', 'Monitor')}"
        )
        return await self.send_alert(message, priority)
    
    async def send_system_alert(self, message: str, is_critical: bool = False) -> bool:
        """
        Send system status alert
        
        Args:
            message: System message
            is_critical: Whether this is a critical alert
            
        Returns:
            Success status
        """
        priority = "CRITICAL" if is_critical else "WARNING"
        return await self.send_alert(f"🔧 System: {message}", priority)


# Global alert manager instance
alert_manager = AlertManager()
