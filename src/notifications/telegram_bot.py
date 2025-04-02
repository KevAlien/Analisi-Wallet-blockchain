"""
Telegram bot for delivering trading signals to users
"""
import logging
import asyncio
from typing import Dict, List, Any, Optional
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import Application

from src.config.settings import TELEGRAM_BOT_TOKEN
from src.signals.signal_generator import Signal

# Configure logger
logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Notifier for sending signals via Telegram"""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the Telegram notifier
        
        Args:
            token: Telegram Bot API token (defaults to TELEGRAM_BOT_TOKEN from settings)
        """
        self.token = token or TELEGRAM_BOT_TOKEN
        
        if not self.token:
            logger.error("No Telegram bot token provided")
            raise ValueError("Telegram bot token is required")
            
        self.bot = Bot(token=self.token)
        
        # List of chat IDs to send notifications to
        # In a real implementation, this would be stored in the database
        self._subscribed_chats: List[int] = []
    
    async def initialize(self):
        """Initialize the bot and verify token"""
        try:
            bot_info = await self.bot.get_me()
            logger.info(f"Connected to Telegram as {bot_info.username}")
        except TelegramError as e:
            logger.error(f"Failed to initialize Telegram bot: {str(e)}")
            raise ConnectionError(f"Telegram bot initialization failed: {str(e)}")
    
    def add_subscriber(self, chat_id: int):
        """
        Add a subscriber to receive notifications
        
        Args:
            chat_id: Telegram chat ID to send messages to
        """
        if chat_id not in self._subscribed_chats:
            self._subscribed_chats.append(chat_id)
            logger.info(f"Added subscriber {chat_id}")
    
    def remove_subscriber(self, chat_id: int):
        """
        Remove a subscriber from receiving notifications
        
        Args:
            chat_id: Telegram chat ID to remove
        """
        if chat_id in self._subscribed_chats:
            self._subscribed_chats.remove(chat_id)
            logger.info(f"Removed subscriber {chat_id}")
    
    async def send_signal(self, signal: Signal, chat_id: Optional[int] = None):
        """
        Send a signal to a specific chat or all subscribers
        
        Args:
            signal: Signal to send
            chat_id: Optional chat ID (if None, sends to all subscribers)
        
        Returns:
            Success status
        """
        message = signal.get_message()
        
        try:
            if chat_id:
                # Send to specific chat
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info(f"Signal sent to chat {chat_id}")
                return True
            else:
                # Send to all subscribers
                for subscriber in self._subscribed_chats:
                    await self.bot.send_message(
                        chat_id=subscriber,
                        text=message,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    # Add a small delay to avoid rate limits
                    await asyncio.sleep(0.1)
                
                logger.info(f"Signal sent to {len(self._subscribed_chats)} subscribers")
                return True
                
        except TelegramError as e:
            logger.error(f"Failed to send signal: {str(e)}")
            return False
    
    async def broadcast_message(self, message: str, parse_mode: Optional[str] = None):
        """
        Broadcast a text message to all subscribers
        
        Args:
            message: Message text to send
            parse_mode: Optional parse mode (Markdown, HTML)
            
        Returns:
            Count of successful deliveries
        """
        successful = 0
        
        for chat_id in self._subscribed_chats:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=parse_mode
                )
                successful += 1
                
                # Add a small delay to avoid rate limits
                await asyncio.sleep(0.1)
                
            except TelegramError as e:
                logger.warning(f"Failed to send message to {chat_id}: {str(e)}")
        
        logger.info(f"Broadcast message sent to {successful}/{len(self._subscribed_chats)} subscribers")
        return successful
