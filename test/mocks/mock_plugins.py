#!/usr/bin/env python3
"""
Mock plugin implementations for testing.
"""
from typing import Dict, Any, Optional, Callable

from core.interfaces import ContentProvider, LLMSender, Notifier, Action, Trigger


class MockContentProvider(ContentProvider):
    """Mock content provider for testing."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._fetch_return = config.get('_fetch_return', 'Mock content')
        self._prompt_return = config.get('_prompt_return', 'Mock prompt')
        self.fetch_called = False
        self.get_prompt_called = False
    
    def fetch(self) -> str:
        """Fetch mock content."""
        self.fetch_called = True
        return self._fetch_return
    
    def get_prompt(self) -> str:
        """Get mock prompt."""
        self.get_prompt_called = True
        return self._prompt_return


class MockLLMSender(LLMSender):
    """Mock LLM sender for testing."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._summarize_return = config.get('_summarize_return', 'Mock summary')
        self.summarize_called = False
        self.last_prompt = None
        self.last_content = None
    
    def summarize(self, prompt: str, content: str) -> str:
        """Generate mock summary."""
        self.summarize_called = True
        self.last_prompt = prompt
        self.last_content = content
        return self._summarize_return


class MockNotifier(Notifier):
    """Mock notifier for testing."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._send_return = config.get('_send_return', True)
        self.send_called = False
        self.last_message = None
        self.last_title = None
    
    def send(self, message: str, title: Optional[str] = None) -> bool:
        """Send mock notification."""
        self.send_called = True
        self.last_message = message
        self.last_title = title
        return self._send_return


class MockAction(Action):
    """Mock action for testing."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._output = config.get('_output', 'Processed output')
        self._should_continue = config.get('_should_continue', True)
        self._tool_spec = config.get('_tool_spec', None)
        self.process_called = False
        self.last_llm_output = None
        self.last_context = None
    
    def process(self, llm_output: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process mock action."""
        self.process_called = True
        self.last_llm_output = llm_output
        self.last_context = context
        return {
            'output': self._output,
            'should_continue': self._should_continue,
            'metadata': {'mock': True}
        }
    
    def get_tool_spec(self) -> Optional[Dict[str, Any]]:
        """Get mock tool specification."""
        return self._tool_spec


class MockTrigger(Trigger):
    """Mock trigger for testing."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._check_return = config.get('_check_return', False)
        self._trigger_data = config.get('_trigger_data', {})
        self.setup_called = False
        self.check_called = False
        self.teardown_called = False
    
    def setup(self, callback: Callable) -> None:
        """Set up mock trigger."""
        self.setup_called = True
        self._callback = callback
    
    def check(self) -> bool:
        """Check mock trigger condition."""
        self.check_called = True
        return self._check_return
    
    def teardown(self) -> None:
        """Tear down mock trigger."""
        self.teardown_called = True
    
    def get_trigger_data(self) -> Dict[str, Any]:
        """Get mock trigger data."""
        return self._trigger_data
    
    def fire(self) -> None:
        """Manually fire the trigger (for testing)."""
        if self._callback:
            self._callback(self._trigger_data)


# Factory functions for the mock plugins

def mock_content(config: Dict[str, Any]) -> MockContentProvider:
    """Factory for mock content provider."""
    return MockContentProvider(config)


def mock_llm(config: Dict[str, Any]) -> MockLLMSender:
    """Factory for mock LLM sender."""
    return MockLLMSender(config)


def mock_notifier(config: Dict[str, Any]) -> MockNotifier:
    """Factory for mock notifier."""
    return MockNotifier(config)


def mock_action(config: Dict[str, Any]) -> MockAction:
    """Factory for mock action."""
    return MockAction(config)


def mock_trigger(config: Dict[str, Any]) -> MockTrigger:
    """Factory for mock trigger."""
    return MockTrigger(config)
