#!/usr/bin/env python3
"""
Pytest fixtures for LLMSender tests.
"""
import pytest
from typing import Dict, Any


@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Provide a mock configuration for testing."""
    return {
        'tasks': [],
        'timezone': 'UTC',
        'log_level': 'DEBUG'
    }


@pytest.fixture
def mock_task_config() -> Dict[str, Any]:
    """Provide a mock task configuration for testing."""
    return {
        'name': 'Test Task',
        'content': {
            'plugin': 'test_content'
        },
        'llm': {
            'plugin': 'test_llm'
        },
        'notifiers': [
            {'plugin': 'test_notifier'}
        ]
    }


@pytest.fixture
def mock_pack_task_config() -> Dict[str, Any]:
    """Provide a mock pack-based task configuration for testing."""
    return {
        'name': 'Test Pack Task',
        'pack': 'core/test_pack',
        'content': {
            'type': 'default'
        },
        'llm': {
            'plugin': 'test_llm'
        },
        'actions': [
            {'type': 'core/core_actions.filter', 'min_length': 10}
        ],
        'notifiers': [
            {'type': 'test_notifier'}
        ]
    }


@pytest.fixture
def sample_llm_output() -> str:
    """Provide sample LLM output for testing."""
    return "This is a test summary of the content. It contains multiple sentences. The content is interesting."


@pytest.fixture
def sample_context() -> Dict[str, Any]:
    """Provide sample context for action testing."""
    return {
        'task_name': 'test_task',
        'content': 'Original test content',
        'prompt': 'Test prompt',
        'trigger_data': {}
    }


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances before each test."""
    yield
    # Reset after test
    try:
        from core.pack_loader import reset_pack_loader
        reset_pack_loader()
    except ImportError:
        # Optional in some test configurations; skip reset if not available.
        pass
    
    try:
        from core.action_system import reset_action_pipeline
        reset_action_pipeline()
    except ImportError:
        # Optional in some test configurations; skip reset if not available.
        pass
    
    try:
        from core.trigger_system import reset_trigger_manager
        reset_trigger_manager()
    except ImportError:
        # Optional in some test configurations; skip reset if not available.
        pass
    
    try:
        from core.task_executor import reset_task_executor
        reset_task_executor()
    except ImportError:
        # Optional in some test configurations; skip reset if not available.
        pass


# Helper functions for creating mock objects

def create_mock_content_provider(fetch_return: str = "Test content", prompt_return: str = "Test prompt"):
    """Create a mock content provider."""
    from test.mocks.mock_plugins import MockContentProvider
    return MockContentProvider({
        '_fetch_return': fetch_return,
        '_prompt_return': prompt_return
    })


def create_mock_llm_sender(summarize_return: str = "Test summary"):
    """Create a mock LLM sender."""
    from test.mocks.mock_plugins import MockLLMSender
    return MockLLMSender({
        '_summarize_return': summarize_return
    })


def create_mock_notifier(send_return: bool = True):
    """Create a mock notifier."""
    from test.mocks.mock_plugins import MockNotifier
    return MockNotifier({
        '_send_return': send_return
    })


def create_mock_action(
    output: str = "Processed output",
    should_continue: bool = True
):
    """Create a mock action."""
    from test.mocks.mock_plugins import MockAction
    return MockAction({
        '_output': output,
        '_should_continue': should_continue
    })
