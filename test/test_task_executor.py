#!/usr/bin/env python3
"""
Tests for the TaskExecutor system.
"""
import pytest
from unittest.mock import MagicMock

from core.task_executor import TaskExecutor, TaskResult, get_task_executor, reset_task_executor
from core.exceptions import ConfigurationError, ContentFetchError, LLMError, ActionError, NotificationError


class TestTaskResult:
    """Tests for TaskResult dataclass."""
    
    def test_default_values(self):
        """Test TaskResult default values."""
        result = TaskResult(success=False, task_name='test')
        assert result.success is False
        assert result.task_name == 'test'
        assert result.output is None
        assert result.error is None
        assert result.notifications_sent == 0
        assert result.notifications_failed == 0
        assert result.metadata == {}
        assert result.duration_seconds == 0.0
    
    def test_with_all_fields(self):
        """Test TaskResult with all fields specified."""
        result = TaskResult(
            success=True,
            task_name='complete_task',
            output='Final output',
            error=None,
            notifications_sent=2,
            notifications_failed=1,
            metadata={'key': 'value'},
            duration_seconds=5.5
        )
        assert result.success is True
        assert result.task_name == 'complete_task'
        assert result.output == 'Final output'
        assert result.notifications_sent == 2
        assert result.notifications_failed == 1
        assert result.metadata == {'key': 'value'}
        assert result.duration_seconds == 5.5


class TestTaskExecutorSuccessPath:
    """Tests for successful TaskExecutor execution."""
    
    @pytest.fixture
    def mock_executor(self):
        """Create an executor with mocked dependencies."""
        executor = TaskExecutor()
        
        # Mock validation to always pass
        mock_validator = MagicMock()
        mock_validation_result = MagicMock()
        mock_validation_result.valid = True
        mock_validation_result.errors = []
        mock_validator.validate_task.return_value = mock_validation_result
        executor.validator = mock_validator
        
        return executor
    
    def test_execute_success_minimal_config(self, mock_executor):
        """Test successful execution with minimal configuration."""
        # Mock _fetch_content
        mock_executor._fetch_content = MagicMock(return_value=('Test content', 'Test prompt'))
        
        # Mock _generate_summary
        mock_executor._generate_summary = MagicMock(return_value='Test summary')
        
        # Mock _send_notifications
        mock_executor._send_notifications = MagicMock(return_value=(1, 0))
        
        task_config = {
            'name': 'Test Task',
            'content': {'plugin': 'test'},
            'llm': {'plugin': 'test_llm'},
            'notifiers': [{'plugin': 'test'}]
        }
        
        result = mock_executor.execute(task_config)
        
        assert result.success is True
        assert result.task_name == 'Test Task'
        assert result.output == 'Test summary'
        assert result.error is None
        assert result.notifications_sent == 1
        assert result.notifications_failed == 0
    
    def test_execute_success_with_actions(self, mock_executor):
        """Test successful execution with action pipeline."""
        from core.action_system import ActionResult
        
        # Mock _fetch_content
        mock_executor._fetch_content = MagicMock(return_value=('Test content', 'Test prompt'))
        
        # Mock _generate_summary
        mock_executor._generate_summary = MagicMock(return_value='LLM output')
        
        # Mock action pipeline
        mock_action_result = ActionResult(
            output='Processed output',
            should_continue=True,
            metadata={'action': 'processed'},
            action_history=[{'name': 'test_action'}]
        )
        mock_executor.action_pipeline.execute_pipeline = MagicMock(return_value=mock_action_result)
        mock_executor.action_pipeline.get_llm_tools = MagicMock(return_value=[])
        
        # Mock _send_notifications
        mock_executor._send_notifications = MagicMock(return_value=(1, 0))
        
        task_config = {
            'name': 'Test Task',
            'content': {'plugin': 'test'},
            'llm': {'plugin': 'test_llm'},
            'actions': [{'type': 'test.action'}],
            'notifiers': [{'plugin': 'test'}]
        }
        
        result = mock_executor.execute(task_config)
        
        assert result.success is True
        assert result.output == 'Processed output'
        assert 'action_history' in result.metadata
    
    def test_execute_skips_notification_when_action_stops(self, mock_executor):
        """Test that notifications are skipped when action pipeline stops."""
        from core.action_system import ActionResult
        
        mock_executor._fetch_content = MagicMock(return_value=('Test content', 'Test prompt'))
        mock_executor._generate_summary = MagicMock(return_value='LLM output')
        
        # Action pipeline returns should_continue=False
        mock_action_result = ActionResult(
            output='Filtered output',
            should_continue=False,
            metadata={},
            action_history=[]
        )
        mock_executor.action_pipeline.execute_pipeline = MagicMock(return_value=mock_action_result)
        mock_executor.action_pipeline.get_llm_tools = MagicMock(return_value=[])
        
        mock_executor._send_notifications = MagicMock()
        
        task_config = {
            'name': 'Test Task',
            'content': {'plugin': 'test'},
            'llm': {'plugin': 'test_llm'},
            'actions': [{'type': 'test.action'}],
            'notifiers': [{'plugin': 'test'}]
        }
        
        result = mock_executor.execute(task_config)
        
        assert result.success is True
        # _send_notifications should not be called
        mock_executor._send_notifications.assert_not_called()


class TestTaskExecutorConfigurationError:
    """Tests for configuration error handling."""
    
    @pytest.fixture
    def executor(self):
        """Create a fresh executor."""
        return TaskExecutor()
    
    def test_configuration_error_invalid_task(self, executor):
        """Test handling of invalid task configuration."""
        # Create mock that returns invalid validation
        mock_validation_result = MagicMock()
        mock_validation_result.valid = False
        mock_validation_result.errors = ['Missing required field']
        executor.validator.validate_task = MagicMock(return_value=mock_validation_result)
        
        task_config = {
            'name': 'Bad Task'
            # Missing content and llm
        }
        
        result = executor.execute(task_config)
        
        assert result.success is False
        assert 'Configuration error' in result.error
    
    def test_configuration_error_missing_llm_plugin(self, executor):
        """Test handling of missing LLM plugin."""
        mock_validation_result = MagicMock()
        mock_validation_result.valid = True
        mock_validation_result.errors = []
        executor.validator.validate_task = MagicMock(return_value=mock_validation_result)
        executor._fetch_content = MagicMock(return_value=('Test content', 'Test prompt'))
        
        task_config = {
            'name': 'Test Task',
            'content': {'plugin': 'test'},
            'llm': {}  # Missing plugin key
        }
        
        result = executor.execute(task_config)
        
        assert result.success is False
        assert 'Configuration error' in result.error


class TestTaskExecutorContentFetchError:
    """Tests for content fetch error handling."""
    
    @pytest.fixture
    def executor(self):
        """Create an executor with validation mocked."""
        executor = TaskExecutor()
        mock_validation_result = MagicMock()
        mock_validation_result.valid = True
        mock_validation_result.errors = []
        executor.validator.validate_task = MagicMock(return_value=mock_validation_result)
        return executor
    
    def test_content_fetch_error(self, executor):
        """Test handling of content fetch errors."""
        executor._fetch_content = MagicMock(side_effect=ContentFetchError("Failed to fetch"))
        
        task_config = {
            'name': 'Test Task',
            'content': {'plugin': 'test'},
            'llm': {'plugin': 'test_llm'}
        }
        
        result = executor.execute(task_config)
        
        assert result.success is False
        assert 'Content fetch error' in result.error


class TestTaskExecutorLLMError:
    """Tests for LLM error handling."""
    
    @pytest.fixture
    def executor(self):
        """Create an executor with validation and content mocked."""
        executor = TaskExecutor()
        mock_validation_result = MagicMock()
        mock_validation_result.valid = True
        mock_validation_result.errors = []
        executor.validator.validate_task = MagicMock(return_value=mock_validation_result)
        executor._fetch_content = MagicMock(return_value=('Test content', 'Test prompt'))
        return executor
    
    def test_llm_error(self, executor):
        """Test handling of LLM errors."""
        executor._generate_summary = MagicMock(side_effect=LLMError("LLM service unavailable"))
        
        task_config = {
            'name': 'Test Task',
            'content': {'plugin': 'test'},
            'llm': {'plugin': 'test_llm'}
        }
        
        result = executor.execute(task_config)
        
        assert result.success is False
        assert 'LLM error' in result.error


class TestTaskExecutorActionError:
    """Tests for action error handling."""
    
    @pytest.fixture
    def executor(self):
        """Create an executor with validation, content, and LLM mocked."""
        executor = TaskExecutor()
        mock_validation_result = MagicMock()
        mock_validation_result.valid = True
        mock_validation_result.errors = []
        executor.validator.validate_task = MagicMock(return_value=mock_validation_result)
        executor._fetch_content = MagicMock(return_value=('Test content', 'Test prompt'))
        executor._generate_summary = MagicMock(return_value='LLM output')
        executor.action_pipeline.get_llm_tools = MagicMock(return_value=[])
        return executor
    
    def test_action_error(self, executor):
        """Test handling of action pipeline errors."""
        executor.action_pipeline.execute_pipeline = MagicMock(side_effect=Exception("Action failed"))
        
        task_config = {
            'name': 'Test Task',
            'content': {'plugin': 'test'},
            'llm': {'plugin': 'test_llm'},
            'actions': [{'type': 'test.action'}]
        }
        
        result = executor.execute(task_config)
        
        assert result.success is False
        assert 'Action error' in result.error


class TestTaskExecutorNotificationError:
    """Tests for notification error handling."""
    
    @pytest.fixture
    def executor(self):
        """Create an executor with most dependencies mocked."""
        executor = TaskExecutor()
        mock_validation_result = MagicMock()
        mock_validation_result.valid = True
        mock_validation_result.errors = []
        executor.validator.validate_task = MagicMock(return_value=mock_validation_result)
        executor._fetch_content = MagicMock(return_value=('Test content', 'Test prompt'))
        executor._generate_summary = MagicMock(return_value='LLM output')
        return executor
    
    def test_notification_error(self, executor):
        """Test handling of notification errors."""
        executor._send_notifications = MagicMock(side_effect=NotificationError("Notification service unavailable"))
        
        task_config = {
            'name': 'Test Task',
            'content': {'plugin': 'test'},
            'llm': {'plugin': 'test_llm'},
            'notifiers': [{'plugin': 'test'}]
        }
        
        result = executor.execute(task_config)
        
        assert result.success is False
        assert 'Notification error' in result.error


class TestTaskExecutorUnexpectedError:
    """Tests for unexpected error handling."""
    
    @pytest.fixture
    def executor(self):
        """Create an executor with validation mocked."""
        executor = TaskExecutor()
        mock_validation_result = MagicMock()
        mock_validation_result.valid = True
        mock_validation_result.errors = []
        executor.validator.validate_task = MagicMock(return_value=mock_validation_result)
        return executor
    
    def test_unexpected_error(self, executor):
        """Test handling of unexpected errors."""
        executor._fetch_content = MagicMock(side_effect=RuntimeError("Unexpected error"))
        
        task_config = {
            'name': 'Test Task',
            'content': {'plugin': 'test'},
            'llm': {'plugin': 'test_llm'}
        }
        
        result = executor.execute(task_config)
        
        assert result.success is False
        assert 'Unexpected error' in result.error


class TestTaskExecutorHelperMethods:
    """Tests for TaskExecutor helper methods."""
    
    @pytest.fixture
    def executor(self):
        """Create a fresh executor."""
        return TaskExecutor()
    
    def test_is_pack_task_with_pack(self, executor):
        """Test _is_pack_task returns True when pack is present."""
        assert executor._is_pack_task({'pack': 'core/twitter'}) is True
    
    def test_is_pack_task_with_actions(self, executor):
        """Test _is_pack_task returns True when actions are present."""
        assert executor._is_pack_task({'actions': [{'type': 'test'}]}) is True
    
    def test_is_pack_task_with_trigger(self, executor):
        """Test _is_pack_task returns True when trigger is present."""
        assert executor._is_pack_task({'trigger': {'type': 'test'}}) is True
    
    def test_is_pack_task_legacy(self, executor):
        """Test _is_pack_task returns False for legacy config."""
        assert executor._is_pack_task({'content': {'plugin': 'test'}}) is False
    
    def test_build_context(self, executor):
        """Test _build_context creates proper context."""
        task_config = {'name': 'Test Task'}
        trigger_data = {'event': 'test'}
        
        context = executor._build_context(task_config, trigger_data)
        
        assert context['task_name'] == 'Test Task'
        assert context['trigger_data'] == trigger_data
        assert 'timestamp' in context
    
    def test_build_context_no_trigger_data(self, executor):
        """Test _build_context handles missing trigger data."""
        task_config = {'name': 'Test Task'}
        
        context = executor._build_context(task_config, None)
        
        assert context['trigger_data'] == {}


class TestSingleton:
    """Tests for singleton functions."""
    
    def test_get_task_executor(self):
        """Test get_task_executor returns singleton."""
        reset_task_executor()
        
        executor1 = get_task_executor()
        executor2 = get_task_executor()
        
        assert executor1 is executor2
    
    def test_reset_task_executor(self):
        """Test reset_task_executor creates new instance."""
        executor1 = get_task_executor()
        reset_task_executor()
        executor2 = get_task_executor()
        
        assert executor1 is not executor2
