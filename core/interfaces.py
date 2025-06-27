from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable


class Trigger(ABC):
    """Base interface for all trigger plugins."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with plugin-specific configuration."""
        self.config = config
        self._callback: Optional[Callable] = None
    
    @abstractmethod
    def setup(self, callback: Callable) -> None:
        """Set up the trigger with a callback function to execute when triggered."""
        pass
    
    @abstractmethod
    def check(self) -> bool:
        """Check if the trigger condition is met."""
        pass
    
    @abstractmethod
    def teardown(self) -> None:
        """Clean up any resources used by the trigger."""
        pass
    
    @abstractmethod
    def get_trigger_data(self) -> Dict[str, Any]:
        """Get any data associated with the trigger event."""
        pass


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


class Action(ABC):
    """Base interface for all action plugins that process LLM output."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with plugin-specific configuration."""
        self.config = config
    
    @abstractmethod
    def process(self, llm_output: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the LLM output and return modified result with metadata.
        
        Args:
            llm_output: The output from the LLM
            context: Additional context including trigger data, content data, etc.
            
        Returns:
            Dict containing:
                - output: The processed output
                - should_continue: Whether to continue to notification
                - metadata: Any additional metadata
        """
        pass
    
    @abstractmethod
    def get_tool_spec(self) -> Optional[Dict[str, Any]]:
        """
        Get the tool specification for LLM function calling.
        
        Returns:
            OpenAI-compatible function specification or None if not a tool.
        """
        pass
    
    def should_notify(self) -> bool:
        """Whether this action's result should trigger notifications."""
        return True