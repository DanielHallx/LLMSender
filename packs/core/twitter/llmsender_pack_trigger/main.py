#!/usr/bin/env python3
import logging
import time
from typing import Dict, Any, Callable, Optional
from datetime import datetime
import tweepy

from core.interfaces import Trigger

logger = logging.getLogger(__name__)


class NewTweetTrigger(Trigger):
    """Trigger when a specified user posts a new tweet."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.username = config.get('username')
        self.check_interval = config.get('check_interval', 300)
        self.last_tweet_id = None
        self.api = None
        self._setup_twitter_api()
    
    def _setup_twitter_api(self):
        """Initialize Twitter API client."""
        try:
            auth = tweepy.OAuthHandler(
                self.config.get('api_key'),
                self.config.get('api_secret')
            )
            auth.set_access_token(
                self.config.get('access_token'),
                self.config.get('access_token_secret')
            )
            self.api = tweepy.API(auth)
        except Exception as e:
            logger.error(f"Failed to initialize Twitter API: {e}")
            raise
    
    def setup(self, callback: Callable) -> None:
        """Set up the trigger with a callback function."""
        self._callback = callback
        # Get the latest tweet ID to start monitoring from
        try:
            tweets = self.api.user_timeline(
                screen_name=self.username,
                count=1,
                tweet_mode='extended'
            )
            if tweets:
                self.last_tweet_id = tweets[0].id
        except Exception as e:
            logger.error(f"Failed to get initial tweet: {e}")
    
    def check(self) -> bool:
        """Check if there's a new tweet."""
        if not self.api:
            return False
        
        try:
            tweets = self.api.user_timeline(
                screen_name=self.username,
                count=10,
                since_id=self.last_tweet_id,
                tweet_mode='extended'
            )
            
            if tweets:
                # New tweets found
                self.last_tweet_id = tweets[0].id
                self._trigger_data = {
                    'tweets': [self._tweet_to_dict(t) for t in tweets],
                    'username': self.username,
                    'timestamp': datetime.utcnow().isoformat()
                }
                return True
                
        except Exception as e:
            logger.error(f"Error checking for new tweets: {e}")
        
        return False
    
    def teardown(self) -> None:
        """Clean up resources."""
        self.api = None
    
    def get_trigger_data(self) -> Dict[str, Any]:
        """Get data about the new tweets."""
        return getattr(self, '_trigger_data', {})
    
    def _tweet_to_dict(self, tweet) -> Dict[str, Any]:
        """Convert tweet object to dictionary."""
        return {
            'id': tweet.id_str,
            'text': tweet.full_text,
            'created_at': tweet.created_at.isoformat(),
            'user': tweet.user.screen_name,
            'likes': tweet.favorite_count,
            'retweets': tweet.retweet_count,
            'url': f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id_str}"
        }


class UserMentionTrigger(Trigger):
    """Trigger when someone mentions a user."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.username = config.get('username')
        self.last_mention_id = None
        self.api = None
        self._setup_twitter_api()
    
    def _setup_twitter_api(self):
        """Initialize Twitter API client."""
        try:
            auth = tweepy.OAuthHandler(
                self.config.get('api_key'),
                self.config.get('api_secret')
            )
            auth.set_access_token(
                self.config.get('access_token'),
                self.config.get('access_token_secret')
            )
            self.api = tweepy.API(auth)
        except Exception as e:
            logger.error(f"Failed to initialize Twitter API: {e}")
            raise
    
    def setup(self, callback: Callable) -> None:
        """Set up the trigger with a callback function."""
        self._callback = callback
        # Get the latest mention ID
        try:
            mentions = self.api.mentions_timeline(count=1, tweet_mode='extended')
            if mentions:
                self.last_mention_id = mentions[0].id
        except Exception as e:
            logger.error(f"Failed to get initial mentions: {e}")
    
    def check(self) -> bool:
        """Check if there are new mentions."""
        if not self.api:
            return False
        
        try:
            mentions = self.api.mentions_timeline(
                since_id=self.last_mention_id,
                tweet_mode='extended'
            )
            
            if mentions:
                # New mentions found
                self.last_mention_id = mentions[0].id
                self._trigger_data = {
                    'mentions': [self._mention_to_dict(m) for m in mentions],
                    'username': self.username,
                    'timestamp': datetime.utcnow().isoformat()
                }
                return True
                
        except Exception as e:
            logger.error(f"Error checking for mentions: {e}")
        
        return False
    
    def teardown(self) -> None:
        """Clean up resources."""
        self.api = None
    
    def get_trigger_data(self) -> Dict[str, Any]:
        """Get data about the mentions."""
        return getattr(self, '_trigger_data', {})
    
    def _mention_to_dict(self, mention) -> Dict[str, Any]:
        """Convert mention to dictionary."""
        return {
            'id': mention.id_str,
            'text': mention.full_text,
            'created_at': mention.created_at.isoformat(),
            'user': mention.user.screen_name,
            'in_reply_to': mention.in_reply_to_screen_name,
            'url': f"https://twitter.com/{mention.user.screen_name}/status/{mention.id_str}"
        }


# Factory functions for the pack loader
def new_tweet(config: Dict[str, Any]) -> NewTweetTrigger:
    """Factory for new tweet trigger."""
    return NewTweetTrigger(config)


def user_mention(config: Dict[str, Any]) -> UserMentionTrigger:
    """Factory for user mention trigger."""
    return UserMentionTrigger(config)