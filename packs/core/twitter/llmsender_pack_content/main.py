#!/usr/bin/env python3
import logging
from typing import Dict, Any
import tweepy

from core.interfaces import ContentProvider

logger = logging.getLogger(__name__)


class FetchTweetsContent(ContentProvider):
    """Fetch tweets from a user's timeline."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.username = config.get('username')
        self.count = config.get('count', 10)
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
    
    def get_prompt(self) -> str:
        """Return the prompt for summarizing tweets."""
        return f"""Please analyze and summarize the following tweets from @{self.username}:

Key points to include:
1. Main topics or themes discussed
2. Important announcements or news
3. Overall sentiment and tone
4. Notable interactions or engagement

Please provide a concise summary in a conversational tone suitable for a notification."""
    
    def fetch(self) -> str:
        """Fetch tweets from the user's timeline."""
        if not self.api or not self.username:
            raise ValueError("Twitter API not configured or username missing")
        
        try:
            tweets = self.api.user_timeline(
                screen_name=self.username,
                count=self.count,
                tweet_mode='extended',
                exclude_replies=True,
                include_rts=False
            )
            
            if not tweets:
                return f"No recent tweets found for @{self.username}"
            
            content_lines = [f"Recent tweets from @{self.username}:\n"]
            
            for i, tweet in enumerate(tweets, 1):
                timestamp = tweet.created_at.strftime('%Y-%m-%d %H:%M')
                content_lines.append(
                    f"{i}. [{timestamp}] {tweet.full_text}\n"
                    f"   Likes: {tweet.favorite_count} | Retweets: {tweet.retweet_count}\n"
                )
            
            return "\n".join(content_lines)
            
        except Exception as e:
            logger.error(f"Error fetching tweets: {e}")
            raise


class FetchTimelineContent(ContentProvider):
    """Fetch home timeline tweets."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.count = config.get('count', 20)
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
    
    def get_prompt(self) -> str:
        """Return the prompt for summarizing timeline."""
        return """Please summarize the following Twitter timeline content:

Key points to include:
1. Major news or trending topics
2. Important updates from followed accounts
3. Interesting discussions or threads
4. Overall sentiment and themes

Provide a concise digest suitable for a daily briefing."""
    
    def fetch(self) -> str:
        """Fetch home timeline tweets."""
        if not self.api:
            raise ValueError("Twitter API not configured")
        
        try:
            tweets = self.api.home_timeline(
                count=self.count,
                tweet_mode='extended'
            )
            
            if not tweets:
                return "No tweets found in timeline"
            
            content_lines = ["Twitter Timeline Digest:\n"]
            
            for i, tweet in enumerate(tweets, 1):
                timestamp = tweet.created_at.strftime('%H:%M')
                username = tweet.user.screen_name
                content_lines.append(
                    f"{i}. @{username} [{timestamp}]: {tweet.full_text[:100]}{'...' if len(tweet.full_text) > 100 else ''}\n"
                )
            
            return "\n".join(content_lines)
            
        except Exception as e:
            logger.error(f"Error fetching timeline: {e}")
            raise


# Factory functions
def fetch_tweets(config: Dict[str, Any]) -> FetchTweetsContent:
    """Factory for user tweets content provider."""
    return FetchTweetsContent(config)


def fetch_timeline(config: Dict[str, Any]) -> FetchTimelineContent:
    """Factory for timeline content provider."""
    return FetchTimelineContent(config)