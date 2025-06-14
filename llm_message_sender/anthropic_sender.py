import logging
from typing import Dict, Any
from core.interfaces import LLMSender
from core.utils import retry_with_backoff, get_env_var, sanitize_for_log

try:
    import anthropic
except ImportError:
    anthropic = None

logger = logging.getLogger(__name__)


class AnthropicSender(LLMSender):
    """Send messages to Anthropic API for summarization."""
    
    def __init__(self, config: Dict[str, Any]):
        # Only pass clean config to parent
        clean_config = {
            'model': config.get('model'),
            'temperature': config.get('temperature'),
            'max_tokens': config.get('max_tokens'),
            'api_key': config.get('api_key')
        }
        super().__init__(clean_config)
        
        if anthropic is None:
            raise ImportError("anthropic package is not installed. Install it with: pip install anthropic")
        
        self.api_key = get_env_var('ANTHROPIC_API_KEY') or config.get('api_key')
        self.model = config.get('model', 'claude-sonnet-4-20250514')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 500)
        
        if not self.api_key:
            raise ValueError("Anthropic API key is required")
        
        # Create client with minimal configuration
        logger.debug(f"Creating Anthropic client for model: {self.model}")
        
        # Temporarily clear proxy environment variables if they exist
        import os
        proxy_env_backup = {}
        proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 
                     'NO_PROXY', 'no_proxy', 'ALL_PROXY', 'all_proxy']
        
        for var in proxy_vars:
            if var in os.environ:
                proxy_env_backup[var] = os.environ[var]
                del os.environ[var]
        
        try:
            # Create client with only API key
            self.client = anthropic.Anthropic(api_key=self.api_key)
            logger.info("Successfully created Anthropic client")
        except Exception as e:
            logger.error(f"Failed to create Anthropic client: {e}")
            raise
        finally:
            # Restore proxy environment variables
            for var, value in proxy_env_backup.items():
                os.environ[var] = value
    
    @retry_with_backoff(max_retries=3, exceptions=(anthropic.APIError,))
    def summarize(self, prompt: str, content: str) -> str:
        """Generate summary using Anthropic API."""
        try:
            # Combine prompt and content
            full_prompt = f"{prompt}\n\nContent to summarize:\n{content}"
            
            logger.debug(f"Sending request to Anthropic with model: {self.model}")
            logger.debug(f"Prompt preview: {sanitize_for_log(full_prompt)}")
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system="You are a helpful assistant that creates concise summaries.",
                messages=[
                    {
                        "role": "user", 
                        "content": full_prompt
                    }
                ]
            )
            
            summary = response.content[0].text.strip()
            logger.info(f"Successfully generated summary using {self.model}")
            
            return summary
            
        except anthropic.APIError as e:
            logger.error(f"Failed to call Anthropic API: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Anthropic API: {e}")
            raise


def factory(config: Dict[str, Any]) -> LLMSender:
    """Factory function to create Anthropic sender."""
    return AnthropicSender(config)