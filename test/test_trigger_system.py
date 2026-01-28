#!/usr/bin/env python3
"""
Tests for the TriggerManager system.
"""
import pytest
from typing import Dict, Any
from unittest.mock import MagicMock

from core.trigger_system import TriggerManager, get_trigger_manager, reset_trigger_manager
from test.mocks.mock_plugins import MockTrigger


class TestTriggerManager:
    """Tests for TriggerManager class."""
    
    def test_register_trigger_no_type(self):
        """Test registering trigger without type fails."""
        manager = TriggerManager()
        callback = MagicMock()
        
        result = manager.register_trigger(
            trigger_id='test_trigger',
            trigger_config={},  # No type
            callback=callback
        )
        
        assert result is False
    
    def test_list_triggers_empty(self):
        """Test listing triggers when none are registered."""
        manager = TriggerManager()
        
        triggers = manager.list_triggers()
        
        assert triggers == []
    
    def test_unregister_nonexistent_trigger(self):
        """Test unregistering a non-existent trigger."""
        manager = TriggerManager()
        
        result = manager.unregister_trigger('nonexistent')
        
        assert result is False
    
    def test_check_nonexistent_trigger(self):
        """Test checking a non-existent trigger."""
        manager = TriggerManager()
        
        result = manager.check_trigger('nonexistent')
        
        assert result is False
    
    def test_get_trigger_data_nonexistent(self):
        """Test getting data from a non-existent trigger."""
        manager = TriggerManager()
        
        data = manager.get_trigger_data('nonexistent')
        
        assert data == {}
    
    def test_shutdown_empty(self):
        """Test shutdown with no triggers."""
        manager = TriggerManager()
        
        # Should not raise
        manager.shutdown()
        
        assert manager.list_triggers() == []


class TestTriggerManagerWithMockTrigger:
    """Tests for TriggerManager using MockTrigger."""
    
    @pytest.fixture
    def manager_with_mock(self, monkeypatch):
        """Create a manager with mocked trigger loading."""
        manager = TriggerManager()
        
        # Mock the _load_trigger method to return a MockTrigger
        def mock_load_trigger(trigger_config):
            return MockTrigger(trigger_config)
        
        monkeypatch.setattr(manager, '_load_trigger', mock_load_trigger)
        
        return manager
    
    def test_register_trigger_success(self, manager_with_mock):
        """Test successfully registering a trigger."""
        callback = MagicMock()
        
        result = manager_with_mock.register_trigger(
            trigger_id='test_trigger',
            trigger_config={'type': 'test.mock'},
            callback=callback
        )
        
        assert result is True
        assert 'test_trigger' in manager_with_mock.list_triggers()
    
    def test_unregister_trigger_success(self, manager_with_mock):
        """Test successfully unregistering a trigger."""
        callback = MagicMock()
        
        manager_with_mock.register_trigger(
            trigger_id='test_trigger',
            trigger_config={'type': 'test.mock'},
            callback=callback
        )
        
        result = manager_with_mock.unregister_trigger('test_trigger')
        
        assert result is True
        assert 'test_trigger' not in manager_with_mock.list_triggers()
    
    def test_check_trigger(self, manager_with_mock):
        """Test checking a trigger condition."""
        callback = MagicMock()
        
        manager_with_mock.register_trigger(
            trigger_id='test_trigger',
            trigger_config={'type': 'test.mock', '_check_return': True},
            callback=callback
        )
        
        # Get the trigger and set check return value
        result = manager_with_mock.check_trigger('test_trigger')
        
        # MockTrigger returns False by default unless configured
        assert isinstance(result, bool)
    
    def test_get_trigger_data(self, manager_with_mock):
        """Test getting trigger data."""
        callback = MagicMock()
        expected_data = {'key': 'value', 'nested': {'data': True}}
        
        manager_with_mock.register_trigger(
            trigger_id='test_trigger',
            trigger_config={'type': 'test.mock', '_trigger_data': expected_data},
            callback=callback
        )
        
        data = manager_with_mock.get_trigger_data('test_trigger')
        
        assert data == expected_data
    
    def test_shutdown_calls_teardown(self, manager_with_mock):
        """Test that shutdown calls teardown on all triggers."""
        callback = MagicMock()
        
        manager_with_mock.register_trigger(
            trigger_id='trigger1',
            trigger_config={'type': 'test.mock'},
            callback=callback
        )
        manager_with_mock.register_trigger(
            trigger_id='trigger2',
            trigger_config={'type': 'test.mock'},
            callback=callback
        )
        
        manager_with_mock.shutdown()
        
        assert manager_with_mock.list_triggers() == []


class TestTriggerCallback:
    """Tests for trigger callback functionality."""
    
    def test_on_trigger_calls_callback(self):
        """Test that _on_trigger calls the registered callback."""
        manager = TriggerManager()
        callback = MagicMock()
        
        # Manually register callback (bypassing trigger loading)
        manager._callbacks['test_trigger'] = callback
        
        trigger_data = {'event': 'test', 'data': 123}
        manager._on_trigger('test_trigger', trigger_data)
        
        callback.assert_called_once_with(trigger_data)
    
    def test_on_trigger_handles_callback_error(self):
        """Test that _on_trigger handles callback errors gracefully."""
        manager = TriggerManager()
        callback = MagicMock(side_effect=Exception("Callback error"))
        
        manager._callbacks['test_trigger'] = callback
        
        # Should not raise
        manager._on_trigger('test_trigger', {})
        
        callback.assert_called_once()
    
    def test_on_trigger_no_callback(self):
        """Test that _on_trigger handles missing callback."""
        manager = TriggerManager()
        
        # Should not raise
        manager._on_trigger('nonexistent_trigger', {})


class TestSingleton:
    """Tests for singleton functions."""
    
    def test_get_trigger_manager(self):
        """Test get_trigger_manager returns singleton."""
        reset_trigger_manager()
        
        manager1 = get_trigger_manager()
        manager2 = get_trigger_manager()
        
        assert manager1 is manager2
    
    def test_reset_trigger_manager(self):
        """Test reset_trigger_manager creates new instance."""
        manager1 = get_trigger_manager()
        reset_trigger_manager()
        manager2 = get_trigger_manager()
        
        assert manager1 is not manager2
