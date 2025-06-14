import requests
import logging
from typing import Dict, Any, List
from datetime import datetime
from core.interfaces import ContentProvider
from core.utils import retry_with_backoff, get_env_var

logger = logging.getLogger(__name__)


class NewsProvider(ContentProvider):
    """Fetch news headlines from NewsAPI."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = get_env_var('NEWS_API_KEY') or config.get('api_key')
        self.country = config.get('country', 'us')
        self.category = config.get('category', 'general')
        self.language = config.get('language', 'en')
        self.page_size = config.get('page_size', 10)
        
        if not self.api_key:
            raise ValueError("NewsAPI key is required")
    
    def get_prompt(self) -> str:
        """Return the prompt for AI to summarize news."""
        return (
            f"Please provide a brief summary of today's top {self.category} news headlines. "
            f"Highlight the most important stories and any significant trends. "
            f"Keep it concise and suitable for a daily news briefing."
        )
    
    @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
    def fetch(self) -> str:
        """Fetch top news headlines."""
        try:
            url = "https://newsapi.org/v2/top-headlines"
            params = {
                'apiKey': self.api_key,
                'country': self.country,
                'category': self.category,
                'pageSize': self.page_size
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 'ok':
                raise ValueError(f"NewsAPI error: {data.get('message', 'Unknown error')}")
            
            # Format the news data
            result = self._format_news_data(data)
            logger.info(f"Successfully fetched {len(data.get('articles', []))} news articles")
            return result
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch news data: {e}")
            raise
    
    def _format_news_data(self, data: Dict) -> str:
        """Format news data into readable text."""
        articles = data.get('articles', [])
        
        if not articles:
            return "No news articles found for the specified criteria."
        
        result = f"Top {self.category.title()} News Headlines ({self.country.upper()}):\n"
        result += f"Retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for i, article in enumerate(articles, 1):
            title = article.get('title', 'No title')
            source = article.get('source', {}).get('name', 'Unknown source')
            description = article.get('description', '')
            published = article.get('publishedAt', '')
            
            # Format published time
            if published:
                try:
                    pub_time = datetime.fromisoformat(published.replace('Z', '+00:00'))
                    time_str = pub_time.strftime('%H:%M')
                except:
                    time_str = 'Unknown time'
            else:
                time_str = 'Unknown time'
            
            result += f"{i}. {title}\n"
            result += f"   Source: {source} | Time: {time_str}\n"
            
            if description and description != title:
                # Truncate long descriptions
                if len(description) > 150:
                    description = description[:147] + "..."
                result += f"   {description}\n"
            
            result += "\n"
        
        return result


def factory(config: Dict[str, Any]) -> NewsProvider:
    """Factory function to create NewsProvider instance."""
    return NewsProvider(config)