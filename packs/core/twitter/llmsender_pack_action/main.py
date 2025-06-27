#!/usr/bin/env python3
import logging
from typing import Dict, Any, Optional
import re

from core.interfaces import Action

logger = logging.getLogger(__name__)


class FilterTweetsAction(Action):
    """Filter tweets based on various criteria."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.min_likes = config.get('min_likes', 0)
        self.keywords = config.get('keywords', [])
        self.exclude_keywords = config.get('exclude_keywords', [])
        self.min_length = config.get('min_length', 0)
    
    def process(self, llm_output: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Filter content based on configured criteria."""
        content = context.get('content', '')
        
        # Extract tweets from content for filtering
        filtered_content = self._filter_content(content)
        
        # If no content passes filter, don't notify
        if not filtered_content.strip():
            return {
                'output': "No tweets matched the filter criteria",
                'should_continue': False,
                'metadata': {'filtered': True, 'reason': 'no_matches'}
            }
        
        # Re-process with LLM if content was significantly filtered
        if len(filtered_content) < len(content) * 0.5:
            return {
                'output': llm_output,  # Keep original for now, could re-process
                'should_continue': True,
                'metadata': {'filtered': True, 'content_reduced': True}
            }
        
        return {
            'output': llm_output,
            'should_continue': True,
            'metadata': {'filtered': False}
        }
    
    def _filter_content(self, content: str) -> str:
        """Filter content based on criteria."""
        lines = content.split('\n')
        filtered_lines = []
        
        for line in lines:
            # Skip empty lines and headers
            if not line.strip() or line.startswith('Recent tweets') or line.startswith('Twitter Timeline'):
                filtered_lines.append(line)
                continue
            
            # Extract tweet info
            tweet_match = re.search(r'Likes: (\d+)', line)
            if tweet_match:
                likes = int(tweet_match.group(1))
                if likes < self.min_likes:
                    continue
            
            # Check length
            if len(line.strip()) < self.min_length:
                continue
            
            # Check keywords
            if self.keywords:
                if not any(keyword.lower() in line.lower() for keyword in self.keywords):
                    continue
            
            # Check exclude keywords
            if self.exclude_keywords:
                if any(keyword.lower() in line.lower() for keyword in self.exclude_keywords):
                    continue
            
            filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def get_tool_spec(self) -> Optional[Dict[str, Any]]:
        """This action can be used as an LLM tool."""
        return {
            'type': 'function',
            'function': {
                'name': 'filter_tweets',
                'description': 'Filter tweets based on engagement metrics and keywords',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'min_likes': {
                            'type': 'integer',
                            'description': 'Minimum number of likes required'
                        },
                        'keywords': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': 'Keywords that must be present'
                        },
                        'exclude_keywords': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': 'Keywords to exclude'
                        }
                    }
                }
            }
        }


class TranslateTweetAction(Action):
    """Translate tweet content to another language."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.target_language = config.get('target_language', 'en')
        self.translate_service = config.get('service', 'simple')  # Could extend with real translation
    
    def process(self, llm_output: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Translate the LLM output."""
        if self.target_language == 'en':
            # No translation needed
            return {
                'output': llm_output,
                'should_continue': True,
                'metadata': {'translated': False}
            }
        
        # For demo purposes, just add a note about translation
        # In a real implementation, you'd use a translation service
        translated_output = f"[Translated to {self.target_language}]\n{llm_output}"
        
        return {
            'output': translated_output,
            'should_continue': True,
            'metadata': {'translated': True, 'target_language': self.target_language}
        }
    
    def get_tool_spec(self) -> Optional[Dict[str, Any]]:
        """This action is not exposed as an LLM tool."""
        return None


class SentimentAnalysisAction(Action):
    """Analyze sentiment and decide whether to notify."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.notify_on_negative = config.get('notify_on_negative', True)
        self.notify_on_positive = config.get('notify_on_positive', True)
        self.sentiment_threshold = config.get('sentiment_threshold', 0.0)
    
    def process(self, llm_output: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sentiment and decide notification."""
        # Simple sentiment analysis (in practice, use a proper sentiment analysis library)
        positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'love', 'like', 'happy', 'excited']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'angry', 'sad', 'disappointed', 'frustrated', 'worried', 'problem']
        
        text_lower = llm_output.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        sentiment_score = positive_count - negative_count
        sentiment = 'positive' if sentiment_score > 0 else 'negative' if sentiment_score < 0 else 'neutral'
        
        should_notify = True
        if sentiment == 'positive' and not self.notify_on_positive:
            should_notify = False
        elif sentiment == 'negative' and not self.notify_on_negative:
            should_notify = False
        
        return {
            'output': llm_output,
            'should_continue': should_notify,
            'metadata': {
                'sentiment': sentiment,
                'sentiment_score': sentiment_score,
                'positive_count': positive_count,
                'negative_count': negative_count
            }
        }
    
    def get_tool_spec(self) -> Optional[Dict[str, Any]]:
        """This action can be used as an LLM tool."""
        return {
            'type': 'function',
            'function': {
                'name': 'analyze_sentiment',
                'description': 'Analyze sentiment of content and determine notification worthiness',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'text': {
                            'type': 'string',
                            'description': 'Text to analyze'
                        }
                    },
                    'required': ['text']
                }
            }
        }


# Factory functions
def filter_tweets(config: Dict[str, Any]) -> FilterTweetsAction:
    """Factory for tweet filter action."""
    return FilterTweetsAction(config)


def translate_tweet(config: Dict[str, Any]) -> TranslateTweetAction:
    """Factory for tweet translation action."""
    return TranslateTweetAction(config)


def analyze_sentiment(config: Dict[str, Any]) -> SentimentAnalysisAction:
    """Factory for sentiment analysis action."""
    return SentimentAnalysisAction(config)