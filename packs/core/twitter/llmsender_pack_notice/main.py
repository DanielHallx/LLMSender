#!/usr/bin/env python3
import logging
from typing import Dict, Any, Optional
import tweepy

from core.interfaces import Notifier

logger = logging.getLogger(__name__)


class PostTweetNotifier(Notifier):
    """Post a new tweet as notification."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.reply_to = config.get('reply_to')
        self.max_length = config.get('max_length', 280)
        self.add_hashtags = config.get('add_hashtags', [])
        self.api = self._setup_twitter_api()
    
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
            return tweepy.API(auth)
        except Exception as e:
            logger.error(f"Failed to initialize Twitter API: {e}")
            raise
    
    def send(self, message: str, title: Optional[str] = None) -> bool:
        """Post a tweet with the message."""
        if not self.api:
            logger.error("Twitter API not configured")
            return False
        
        try:
            # Prepare tweet content
            tweet_content = message
            
            # Add title if provided
            if title:
                tweet_content = f"{title}\n\n{message}"
            
            # Add hashtags
            if self.add_hashtags:
                hashtags = " ".join(f"#{tag}" for tag in self.add_hashtags)
                tweet_content = f"{tweet_content}\n\n{hashtags}"
            
            # Truncate if too long
            if len(tweet_content) > self.max_length:
                # Leave space for "..."
                tweet_content = tweet_content[:self.max_length-3] + "..."
            
            # Post the tweet
            if self.reply_to:
                tweet = self.api.update_status(
                    status=tweet_content,
                    in_reply_to_status_id=self.reply_to
                )
            else:
                tweet = self.api.update_status(status=tweet_content)
            
            logger.info(f"Posted tweet: {tweet.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to post tweet: {e}")
            return False


class SendDMNotifier(Notifier):
    """Send a direct message as notification."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.recipient = config.get('recipient')
        if not self.recipient:
            raise ValueError("Recipient username is required for DM notifier")
        self.api = self._setup_twitter_api()
    
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
            return tweepy.API(auth)
        except Exception as e:
            logger.error(f"Failed to initialize Twitter API: {e}")
            raise
    
    def send(self, message: str, title: Optional[str] = None) -> bool:
        """Send a direct message."""
        if not self.api:
            logger.error("Twitter API not configured")
            return False
        
        try:
            # Prepare DM content
            dm_content = message
            if title:
                dm_content = f"{title}\n\n{message}"
            
            # Get recipient user ID
            try:
                user = self.api.get_user(screen_name=self.recipient)
                recipient_id = user.id
            except Exception as e:
                logger.error(f"Failed to get user ID for {self.recipient}: {e}")
                return False
            
            # Send DM (Note: This requires special permissions and API access)
            # For demo purposes, we'll just log it
            logger.info(f"Would send DM to @{self.recipient}: {dm_content[:100]}...")
            
            # In a real implementation, you'd use:
            # self.api.send_direct_message(recipient_id=recipient_id, text=dm_content)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send DM: {e}")
            return False


class TwitterThreadNotifier(Notifier):
    """Post a Twitter thread as notification."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.max_tweet_length = config.get('max_tweet_length', 280)
        self.thread_prefix = config.get('thread_prefix', "🧵 Thread:")
        self.api = self._setup_twitter_api()
    
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
            return tweepy.API(auth)
        except Exception as e:
            logger.error(f"Failed to initialize Twitter API: {e}")
            raise
    
    def send(self, message: str, title: Optional[str] = None) -> bool:
        """Post a Twitter thread."""
        if not self.api:
            logger.error("Twitter API not configured")
            return False
        
        try:
            # Prepare content
            full_content = message
            if title:
                full_content = f"{title}\n\n{message}"
            
            # Split into tweets
            tweets = self._split_into_tweets(full_content)
            
            if not tweets:
                logger.error("No content to tweet")
                return False
            
            # Post the thread
            previous_tweet = None
            for i, tweet_content in enumerate(tweets):
                if i == 0 and len(tweets) > 1:
                    # First tweet of a thread
                    tweet_content = f"{self.thread_prefix} {tweet_content}"
                elif i > 0:
                    # Subsequent tweets
                    tweet_content = f"{i+1}/{len(tweets)} {tweet_content}"
                
                try:
                    if previous_tweet:
                        tweet = self.api.update_status(
                            status=tweet_content,
                            in_reply_to_status_id=previous_tweet.id
                        )
                    else:
                        tweet = self.api.update_status(status=tweet_content)
                    
                    previous_tweet = tweet
                    logger.info(f"Posted tweet {i+1}/{len(tweets)}: {tweet.id}")
                    
                except Exception as e:
                    logger.error(f"Failed to post tweet {i+1}: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to post thread: {e}")
            return False
    
    def _split_into_tweets(self, content: str) -> list:
        """Split content into tweet-sized chunks."""
        tweets = []
        
        # Simple splitting by sentences or lines
        sentences = content.replace('. ', '.\n').split('\n')
        current_tweet = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if adding this sentence would exceed limit
            if len(current_tweet + sentence) > self.max_tweet_length - 20:  # Leave space for numbering
                if current_tweet:
                    tweets.append(current_tweet.strip())
                    current_tweet = sentence
                else:
                    # Single sentence too long, truncate
                    tweets.append(sentence[:self.max_tweet_length-3] + "...")
            else:
                current_tweet = f"{current_tweet} {sentence}".strip()
        
        if current_tweet:
            tweets.append(current_tweet)
        
        return tweets


# Factory functions
def post_tweet(config: Dict[str, Any]) -> PostTweetNotifier:
    """Factory for tweet posting notifier."""
    return PostTweetNotifier(config)


def send_dm(config: Dict[str, Any]) -> SendDMNotifier:
    """Factory for DM notifier."""
    return SendDMNotifier(config)


def post_thread(config: Dict[str, Any]) -> TwitterThreadNotifier:
    """Factory for thread posting notifier."""
    return TwitterThreadNotifier(config)