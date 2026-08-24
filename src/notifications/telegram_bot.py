"""
Telegram bot for delivering trading signals to users
"""
import logging
import asyncio
from typing import List, Optional
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

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
        self.enabled = bool(self.token)

        if not self.enabled:
            logger.warning(
                "TELEGRAM_BOT_TOKEN non configurato — notifiche Telegram disabilitate. "
                "Il sistema funzionerà senza notifiche."
            )
            self.bot = None
        else:
            self.bot = Bot(token=self.token)

        # Lista chat ID per le notifiche (in produzione: da database)
        self._subscribed_chats: List[int] = []

    async def initialize(self):
        """Inizializza il bot e verifica il token. No-op se disabilitato."""
        if not self.enabled:
            logger.info("TelegramNotifier disabilitato — skip initialize")
            return
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
        if not self.enabled:
            logger.debug("TelegramNotifier disabilitato — signal non inviato")
            return False

        message = signal.get_message()

        try:
            if chat_id:
                # Send to specific chat
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
                logger.info(f"Signal sent to chat {chat_id}")
                return True
            else:
                # Send to all subscribers
                for subscriber in self._subscribed_chats:
                    await self.bot.send_message(
                        chat_id=subscriber,
                        text=message,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True,
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
        if not self.enabled:
            logger.debug("TelegramNotifier disabilitato — broadcast non inviato")
            return 0

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

    async def send_message(self, message: str, parse_mode: Optional[str] = None) -> bool:
        """
        Invia un messaggio a tutti i subscriber (alias conveniente per broadcast_message).

        Returns:
            True se almeno un messaggio è stato inviato, False se disabilitato o nessun subscriber.
        """
        if not self.enabled:
            logger.debug("TelegramNotifier disabilitato — send_message ignorato")
            return False
        count = await self.broadcast_message(message, parse_mode=parse_mode)
        return count > 0
