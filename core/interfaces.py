from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class ContentProvider(ABC):
    """Base interface for all content provider plugins."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with plugin-specific configuration."""
        self.config = config
    
    @abstractmethod
    def get_prompt(self) -> str:
        """Return the prompt to send to AI for this content type."""
        pass
    
    @abstractmethod
    def fetch(self) -> str:
        """Fetch and return the raw content data."""
        pass


class LLMSender(ABC):
    """Base interface for all LLM/AI provider plugins."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with plugin-specific configuration."""
        self.config = config
    
    @abstractmethod
    def summarize(self, prompt: str, content: str) -> str:
        """Generate summary using the AI service."""
        pass


class Notifier(ABC):
    """Base interface for all notification service plugins."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with plugin-specific configuration."""
        self.config = config
    
    @abstractmethod
    def send(self, message: str, title: Optional[str] = None) -> bool:
        """Send notification and return success status."""
        pass