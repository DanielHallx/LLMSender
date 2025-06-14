import logging
import requests
from typing import Dict, Any, Optional
from core.interfaces import Notifier
from core.utils import retry_with_backoff, get_env_var

logger = logging.getLogger(__name__)


class TelegramNotifier(Notifier):
    """Send notifications via Telegram Bot API."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bot_token = get_env_var('TELEGRAM_BOT_TOKEN') or config.get('bot_token')
        self.chat_id = get_env_var('TELEGRAM_CHAT_ID') or config.get('chat_id')
        self.parse_mode = config.get('parse_mode', 'HTML')
        self.disable_notification = config.get('disable_notification', False)
        
        if not self.bot_token or not self.chat_id:
            raise ValueError("Telegram bot token and chat ID are required")
        
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
    def send(self, message: str, title: Optional[str] = None) -> bool:
        """Send message to Telegram chat."""
        try:
            # Format message with title if provided
            if title:
                formatted_message = f"<b>{self._escape_html(title)}</b>\n\n{self._escape_html(message)}"
            else:
                formatted_message = self._escape_html(message)
            
            data = {
                'chat_id': self.chat_id,
                'text': formatted_message,
                'parse_mode': self.parse_mode,
                'disable_notification': self.disable_notification
            }
            
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json=data,
                timeout=10
            )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get('ok'):
                logger.info(f"Successfully sent Telegram message to chat {self.chat_id}")
                return True
            else:
                logger.error(f"Telegram API returned error: {result.get('description', 'Unknown error')}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if self.parse_mode != 'HTML':
            return text
        
        replacements = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text


def factory(config: Dict[str, Any]) -> TelegramNotifier:
    """Factory function to create TelegramNotifier instance."""
    return TelegramNotifier(config)