import logging
from typing import Dict, Any, Optional
import requests
from core.interfaces import LLMSender
from core.utils import retry_with_backoff, get_env_var, sanitize_for_log
from core.dependency_checker import DependencyChecker

logger = logging.getLogger(__name__)

# 尝试导入 OpenAI SDK
try:
    import openai
    HAS_OPENAI_SDK = True
except ImportError:
    HAS_OPENAI_SDK = False
    openai = None


class OpenAISender(LLMSender):
    """Send messages to OpenAI API for summarization."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = get_env_var('OPENAI_API_KEY') or config.get('api_key')
        self.model = config.get('model', 'gpt-4o')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 500)
        self.api_base = config.get('api_base', 'https://api.openai.com/v1')
        self.use_sdk = config.get('use_sdk', True) and HAS_OPENAI_SDK
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
            
        # 如果配置要求使用 SDK 但未安装，给出提示
        if config.get('use_sdk', True) and not HAS_OPENAI_SDK:
            logger.warning(
                "OpenAI SDK not installed. Using HTTP requests instead. "
                "For better performance, install with: pip install openai>=1.0.0"
            )
            # 可选：抛出错误强制安装
            # DependencyChecker.check_and_suggest('openai_sender')
    
    @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
    def summarize(self, prompt: str, content: str) -> str:
        """Generate summary using OpenAI API."""
        full_prompt = f"{prompt}\n\nContent to summarize:\n{content}"
        
        if self.use_sdk:
            return self._summarize_with_sdk(full_prompt)
        else:
            return self._summarize_with_requests(full_prompt)
    
    def _summarize_with_sdk(self, full_prompt: str) -> str:
        """Use official OpenAI SDK."""
        try:
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.api_base if self.api_base != 'https://api.openai.com/v1' else None
            )
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that creates concise summaries."},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI SDK error: {str(e)}")
            raise
    
    def _summarize_with_requests(self, full_prompt: str) -> str:
        """Use raw HTTP requests as fallback."""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
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
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            summary = result['choices'][0]['message']['content'].strip()
            
            # Log token usage if available
            if 'usage' in result:
                logger.info(f"OpenAI token usage - "
                          f"Prompt: {result['usage']['prompt_tokens']}, "
                          f"Completion: {result['usage']['completion_tokens']}, "
                          f"Total: {result['usage']['total_tokens']}")
            
            return summary
            
        except requests.RequestException as e:
            logger.error(f"OpenAI API request error: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI sender: {str(e)}")
            raise


def factory(config: Dict[str, Any]) -> OpenAISender:
    """Factory function to create OpenAISender instance."""
    return OpenAISender(config)