import logging
import tweepy
from typing import Dict, Any, Optional
from core.interfaces import Notifier
from core.utils import retry_with_backoff, get_env_var

logger = logging.getLogger(__name__)


class TwitterNotifier(Notifier):
    """Send notifications via Twitter (X) API."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.consumer_key = get_env_var('TWITTER_CONSUMER_KEY') or config.get('consumer_key')
        self.consumer_secret = get_env_var('TWITTER_CONSUMER_SECRET') or config.get('consumer_secret')
        self.access_token = get_env_var('TWITTER_ACCESS_TOKEN') or config.get('access_token')
        self.access_token_secret = get_env_var('TWITTER_ACCESS_TOKEN_SECRET') or config.get('access_token_secret')
        
        if not all([self.consumer_key, self.consumer_secret, self.access_token, self.access_token_secret]):
            raise ValueError("Twitter API credentials (consumer_key, consumer_secret, access_token, access_token_secret) are required")
        
        # Initialize the Twitter client
        self.client = tweepy.Client(
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            access_token=self.access_token,
            access_token_secret=self.access_token_secret,
            wait_on_rate_limit=True
        )
        
        # Optional configuration
        self.max_length = config.get('max_length', 280)
        self.include_title = config.get('include_title', True)
    
    @retry_with_backoff(max_retries=3, exceptions=(tweepy.TweepyException,))
    def send(self, message: str, title: Optional[str] = None) -> bool:
        """Post message to Twitter."""
        try:
            # Format tweet with title if provided
            if title and self.include_title:
                tweet_text = f"{title}\n\n{message}"
            else:
                tweet_text = message
            
            # Truncate if too long
            if len(tweet_text) > self.max_length:
                # Leave room for ellipsis
                tweet_text = tweet_text[:self.max_length - 3] + "..."
            
            # Send tweet
            response = self.client.create_tweet(text=tweet_text)
            
            if response.data:
                tweet_id = response.data.get('id')
                logger.info(f"Successfully posted tweet with ID: {tweet_id}")
                return True
            else:
                logger.error("Failed to post tweet: No data in response")
                return False
                
        except tweepy.TweepyException as e:
            logger.error(f"Failed to send Twitter notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Twitter notification: {e}")
            return False


def factory(config: Dict[str, Any]) -> TwitterNotifier:
    """Factory function to create TwitterNotifier instance."""
    return TwitterNotifier(config)