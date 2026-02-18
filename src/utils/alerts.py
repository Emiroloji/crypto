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
        import concurrent.futures
        try:
            loop = asyncio.get_running_loop()
            # Loop is already running (e.g. inside an async context) — schedule as a task
            future = asyncio.run_coroutine_threadsafe(
                self.send_alert(message, priority), loop
            )
            future.result(timeout=5)
            return True
        except RuntimeError:
            # No running loop — safe to use asyncio.run()
            return asyncio.run(self.send_alert(message, priority))
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
        Send high-confidence signal alert with detailed analysis
        
        Args:
            signal_data: Signal information
            
        Returns:
            Success status
        """
        # Extract data with defaults
        symbol = signal_data.get('symbol', 'N/A')
        direction = str(signal_data.get('direction', 'N/A')).replace('TradeDirection.', '')
        confidence = signal_data.get('confidence_score', signal_data.get('confidence', 0))
        rr_ratio = signal_data.get('risk_reward_ratio', signal_data.get('risk_reward', 0))
        signal_type = signal_data.get('signal_type', 'N/A')
        
        # Price levels
        entry = signal_data.get('entry_price', 0)
        stop_loss = signal_data.get('stop_loss', 0)
        take_profit = signal_data.get('take_profit', 0)
        
        # Technical scores
        trend_score = signal_data.get('trend_score', 0)
        momentum_score = signal_data.get('momentum_score', 0)
        volume_score = signal_data.get('volume_score', 0)
        
        # Calculate risk/reward percentages
        if entry > 0:
            risk_pct = abs((stop_loss - entry) / entry * 100)
            reward_pct = abs((take_profit - entry) / entry * 100)
        else:
            risk_pct = reward_pct = 0
        
        # Direction emoji
        dir_emoji = "🟢" if "LONG" in direction else "🔴"
        
        # Confidence stars
        stars = "⭐" * min(5, int(confidence / 20))
        
        message = (
            f"🚨 *YÜKSEK GÜVENİLİRLİK SİNYALİ*\n"
            f"{'━' * 30}\n\n"
            
            f"📊 *GENEL BİLGİ*\n"
            f"Symbol: *{symbol}*\n"
            f"Yön: *{direction}* {dir_emoji}\n"
            f"Confidence: *{confidence:.1f}%* {stars}\n"
            f"Risk/Reward: *1:{rr_ratio:.2f}*\n"
            f"Sinyal Tipi: _{signal_type}_\n\n"
            
            f"💰 *FİYAT SEVİYELERİ*\n"
            f"Entry: `${entry:.2f}`\n"
            f"Stop Loss: `${stop_loss:.2f}` (-{risk_pct:.1f}%)\n"
            f"Take Profit: `${take_profit:.2f}` (+{reward_pct:.1f}%)\n\n"
            
            f"📈 *TEKNİK ANALİZ*\n"
            f"Trend: {trend_score:.0f}/100 {'✅' if trend_score > 70 else '⚠️'}\n"
            f"Momentum: {momentum_score:.0f}/100 {'✅' if momentum_score > 70 else '⚠️'}\n"
            f"Volume: {volume_score:.0f}/100 {'✅' if volume_score > 70 else '⚠️'}\n\n"
            
            f"🎯 *ÖNERİ*\n"
            f"• Pozisyon: 1-2% sermaye\n"
            f"• Giriş: Limit order önerilir\n"
            f"• Risk: {risk_pct:.1f}% | Hedef: {reward_pct:.1f}%\n\n"
            
            f"⚠️ *DİKKAT*\n"
            f"• Stop loss'u mutlaka kullan\n"
            f"• Pozisyon büyüklüğüne dikkat et\n"
            f"• Haber akışını takip et\n\n"
            
            f"{'━' * 30}\n"
            f"⏰ Manuel işlem önerilir"
        )
        
        return await self.send_alert(message, "WARNING")
    
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
