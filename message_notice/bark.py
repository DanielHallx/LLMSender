import logging
import requests
from typing import Dict, Any, Optional
from urllib.parse import urlencode
from core.interfaces import Notifier
from core.utils import retry_with_backoff, get_env_var

logger = logging.getLogger(__name__)


class BarkNotifier(Notifier):
    """Send notifications via Bark iOS app."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.device_key = get_env_var('BARK_DEVICE_KEY') or config.get('device_key')
        self.server_url = config.get('server_url', 'https://api.day.app')
        self.sound = config.get('sound', 'default')
        self.icon = config.get('icon')
        self.group = config.get('group', 'LLMSender')
        self.level = config.get('level', 'active')  # active, timeSensitive, passive
        
        if not self.device_key:
            raise ValueError("Bark device key is required")
    
    @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
    def send(self, message: str, title: Optional[str] = None) -> bool:
        """Send notification to Bark app."""
        try:
            # Prepare the notification data
            params = {
                'title': title or 'LLMSender Notification',
                'body': message,
                'sound': self.sound,
                'group': self.group,
                'level': self.level
            }
            
            # Add optional parameters
            if self.icon:
                params['icon'] = self.icon
            
            # Construct URL
            url = f"{self.server_url}/{self.device_key}"
            
            # Send notification
            response = requests.post(
                url,
                json=params,
                timeout=10
            )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') == 200:
                logger.info(f"Successfully sent Bark notification")
                return True
            else:
                logger.error(f"Bark API returned error: {result.get('message', 'Unknown error')}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Failed to send Bark notification: {e}")
            return False


class BarkSimpleNotifier(Notifier):
    """Send notifications via Bark using simple GET requests."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.device_key = get_env_var('BARK_DEVICE_KEY') or config.get('device_key')
        self.server_url = config.get('server_url', 'https://api.day.app')
        
        if not self.device_key:
            raise ValueError("Bark device key is required")
    
    @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
    def send(self, message: str, title: Optional[str] = None) -> bool:
        """Send notification to Bark app using simple GET request."""
        try:
            # For simple GET request, construct URL with path parameters
            if title:
                url = f"{self.server_url}/{self.device_key}/{title}/{message}"
            else:
                url = f"{self.server_url}/{self.device_key}/{message}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') == 200:
                logger.info(f"Successfully sent Bark notification (simple mode)")
                return True
            else:
                logger.error(f"Bark API returned error: {result.get('message', 'Unknown error')}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Failed to send Bark notification: {e}")
            return False


def factory(config: Dict[str, Any]) -> Notifier:
    """Factory function to create appropriate Bark notifier."""
    mode = config.get('mode', 'advanced')
    
    if mode == 'simple':
        return BarkSimpleNotifier(config)
    else:
        return BarkNotifier(config)