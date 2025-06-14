import logging
from typing import Dict, Any, Optional
import requests
from core.interfaces import LLMSender
from core.utils import retry_with_backoff, get_env_var, sanitize_for_log

logger = logging.getLogger(__name__)


class OpenAISender(LLMSender):
    """Send messages to OpenAI API for summarization."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = get_env_var('OPENAI_API_KEY') or config.get('api_key')
        self.model = config.get('model', 'gpt-4o')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 500)
        self.api_base = config.get('api_base', 'https://api.openai.com/v1')
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
    
    @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
    def summarize(self, prompt: str, content: str) -> str:
        """Generate summary using OpenAI API."""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Combine prompt and content
            full_prompt = f"{prompt}\n\nContent to summarize:\n{content}"
            
            data = {
                'model': self.model,
                'messages': [
                    {'role': 'system', 'content': 'You are a helpful assistant that creates concise summaries.'},
                    {'role': 'user', 'content': full_prompt}
                ],
                'temperature': self.temperature,
                'max_tokens': self.max_tokens
            }
            
            logger.debug(f"Sending request to OpenAI with model: {self.model}")
            logger.debug(f"Prompt preview: {sanitize_for_log(full_prompt)}")
            
            response = requests.post(
                f'{self.api_base}/chat/completions',
                headers=headers,
                json=data,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            summary = result['choices'][0]['message']['content'].strip()
            logger.info(f"Successfully generated summary using {self.model}")
            
            return summary
            
        except requests.RequestException as e:
            logger.error(f"Failed to call OpenAI API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected response format from OpenAI: {e}")
            raise


class AzureOpenAISender(LLMSender):
    """Send messages to Azure OpenAI API for summarization."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = get_env_var('AZURE_OPENAI_API_KEY') or config.get('api_key')
        self.endpoint = get_env_var('AZURE_OPENAI_ENDPOINT') or config.get('endpoint')
        self.deployment_name = config.get('deployment_name')
        self.api_version = config.get('api_version', '2023-05-15')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 500)
        
        if not all([self.api_key, self.endpoint, self.deployment_name]):
            raise ValueError("Azure OpenAI API key, endpoint, and deployment name are required")
    
    @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
    def summarize(self, prompt: str, content: str) -> str:
        """Generate summary using Azure OpenAI API."""
        try:
            headers = {
                'api-key': self.api_key,
                'Content-Type': 'application/json'
            }
            
            full_prompt = f"{prompt}\n\nContent to summarize:\n{content}"
            
            data = {
                'messages': [
                    {'role': 'system', 'content': 'You are a helpful assistant that creates concise summaries.'},
                    {'role': 'user', 'content': full_prompt}
                ],
                'temperature': self.temperature,
                'max_tokens': self.max_tokens
            }
            
            url = (
                f"{self.endpoint}/openai/deployments/{self.deployment_name}"
                f"/chat/completions?api-version={self.api_version}"
            )
            
            logger.debug(f"Sending request to Azure OpenAI deployment: {self.deployment_name}")
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            summary = result['choices'][0]['message']['content'].strip()
            logger.info(f"Successfully generated summary using Azure OpenAI")
            
            return summary
            
        except requests.RequestException as e:
            logger.error(f"Failed to call Azure OpenAI API: {e}")
            raise


def factory(config: Dict[str, Any]) -> LLMSender:
    """Factory function to create appropriate OpenAI sender."""
    provider = config.get('provider', 'openai')
    
    if provider == 'azure':
        return AzureOpenAISender(config)
    else:
        return OpenAISender(config)