import logging
from typing import Dict, Any, Optional
import requests
import json
from core.interfaces import LLMSender
from core.utils import retry_with_backoff, get_env_var, sanitize_for_log

logger = logging.getLogger(__name__)


class GeminiSender(LLMSender):
    """Send messages to Google Gemini API for summarization."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Apply preset configurations based on variant
        preset_config = self._get_preset_config(config)
        final_config = {**preset_config, **config}
        
        self.api_key = get_env_var('GEMINI_API_KEY') or final_config.get('api_key')
        self.model = final_config.get('model', 'gemini-2.5-pro')
        self.temperature = final_config.get('temperature', 0.7)
        self.max_output_tokens = final_config.get('max_output_tokens', 500)
        self.top_p = final_config.get('top_p', 0.95)
        self.top_k = final_config.get('top_k', 40)
        self.api_base = final_config.get('api_base', 'https://generativelanguage.googleapis.com/v1beta')
        
        if not self.api_key:
            raise ValueError("Gemini API key is required")
        
        # Available models mapping
        self.model_mapping = {
            'gemini-2.5-pro': 'gemini-2.5-pro',
        }
        
        # Validate and map model name
        if self.model in self.model_mapping:
            self.model = self.model_mapping[self.model]
        else:
            logger.warning(f"Unknown Gemini model '{self.model}', using default 'gemini-2.5-pro'")
            self.model = 'gemini-2.5-pro'
    
    def _get_preset_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get preset configuration based on variant or model."""
        variant = config.get('variant', 'standard')
        model = config.get('model', '')
        
        # Define presets
        presets = {
            'pro': {
                'model': 'gemini-1.5-pro',
                'max_output_tokens': 1000,
                'temperature': 0.7,
            },
            'flash': {
                'model': 'gemini-2.5-pro',
                'max_output_tokens': 500,
                'temperature': 0.5,
            }
        }
        
        # Apply preset based on variant
        if variant in presets:
            return presets[variant]
        
        # Apply preset based on model
        if model in ['gemini-1.5-pro', 'gemini-pro']:
            return presets['pro']
        elif model in ['gemini-2.5-pro']:
            return presets['flash']
        
        return {}
    
    @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
    def summarize(self, prompt: str, content: str) -> str:
        """Generate summary using Google Gemini API."""
        try:
            # Combine prompt and content
            full_prompt = f"{prompt}\n\nContent to summarize:\n{content}"
            
            # Prepare request data
            data = {
                "contents": [
                    {
                        "parts": [
                            {"text": full_prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": self.temperature,
                    "topK": self.top_k,
                    "topP": self.top_p,
                    "maxOutputTokens": self.max_output_tokens,
                }
            }
            
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
            }
            
            # Construct URL
            url = f"{self.api_base}/models/{self.model}:generateContent"
            params = {'key': self.api_key}
            
            logger.debug(f"Sending request to Gemini API with model: {self.model}")
            logger.debug(f"Prompt preview: {sanitize_for_log(full_prompt)}")
            
            response = requests.post(
                url,
                headers=headers,
                params=params,
                json=data,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Parse response
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                
                # Check for content filtering
                if 'finishReason' in candidate and candidate['finishReason'] == 'SAFETY':
                    logger.warning("Content was filtered by Gemini safety filters")
                    return "Content filtered by safety filters. Please try with different content."
                
                # Extract text content
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    if parts and 'text' in parts[0]:
                        summary = parts[0]['text'].strip()
                        logger.info(f"Successfully generated summary using {self.model}")
                        return summary
            
            # Handle error responses
            if 'error' in result:
                error_msg = result['error'].get('message', 'Unknown error')
                logger.error(f"Gemini API error: {error_msg}")
                raise ValueError(f"Gemini API error: {error_msg}")
            
            # Fallback if no valid content found
            logger.error("No valid content found in Gemini response")
            raise ValueError("No valid content in Gemini response")
            
        except requests.RequestException as e:
            logger.error(f"Failed to call Gemini API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Response: {error_detail}")
                except:
                    logger.error(f"Response: {e.response.text}")
            raise
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Unexpected response format from Gemini: {e}")
            raise


def factory(config: Dict[str, Any]) -> LLMSender:
    """Factory function to create Gemini sender with dynamic configuration."""
    return GeminiSender(config)