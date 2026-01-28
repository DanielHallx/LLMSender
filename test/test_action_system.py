#!/usr/bin/env python3
"""
Tests for the ActionPipeline system.
"""
import pytest
from typing import Dict, Any

from core.action_system import ActionPipeline, ActionResult, get_action_pipeline, reset_action_pipeline
from test.mocks.mock_plugins import MockAction


class TestActionResult:
    """Tests for ActionResult dataclass."""
    
    def test_default_values(self):
        """Test ActionResult default values."""
        result = ActionResult(output="test")
        assert result.output == "test"
        assert result.should_continue is True
        assert result.metadata == {}
        assert result.action_history == []
    
    def test_with_all_fields(self):
        """Test ActionResult with all fields specified."""
        result = ActionResult(
            output="test output",
            should_continue=False,
            metadata={'key': 'value'},
            action_history=[{'name': 'action1'}]
        )
        assert result.output == "test output"
        assert result.should_continue is False
        assert result.metadata == {'key': 'value'}
        assert result.action_history == [{'name': 'action1'}]


class TestActionPipeline:
    """Tests for ActionPipeline class."""
    
    def test_register_action(self):
        """Test registering an action."""
        pipeline = ActionPipeline()
        action = MockAction({'_output': 'test'})
        
        pipeline.register_action('test_action', action)
        
        assert pipeline.get_action('test_action') is action
    
    def test_get_nonexistent_action(self):
        """Test getting a non-existent action."""
        pipeline = ActionPipeline()
        
        assert pipeline.get_action('nonexistent') is None
    
    def test_execute_empty_pipeline(self):
        """Test executing an empty pipeline."""
        pipeline = ActionPipeline()
        
        result = pipeline.execute_pipeline(
            llm_output="test output",
            actions_config=[],
            context={}
        )
        
        assert result.output == "test output"
        assert result.should_continue is True
        assert result.action_history == []
    
    def test_execute_pipeline_with_registered_action(self):
        """Test executing pipeline with a registered action."""
        pipeline = ActionPipeline()
        action = MockAction({
            '_output': 'processed output',
            '_should_continue': True
        })
        pipeline.register_action('test_action', action)
        
        result = pipeline.execute_pipeline(
            llm_output="original output",
            actions_config=[{'type': 'test_action', 'name': 'my_action'}],
            context={'task_name': 'test'}
        )
        
        assert result.output == 'processed output'
        assert result.should_continue is True
        assert len(result.action_history) == 1
        assert result.action_history[0]['name'] == 'my_action'
        assert action.process_called is True
    
    def test_execute_pipeline_stops_on_should_continue_false(self):
        """Test that pipeline stops when action returns should_continue=False."""
        pipeline = ActionPipeline()
        
        action1 = MockAction({'_output': 'output1', '_should_continue': False})
        action2 = MockAction({'_output': 'output2', '_should_continue': True})
        
        pipeline.register_action('action1', action1)
        pipeline.register_action('action2', action2)
        
        result = pipeline.execute_pipeline(
            llm_output="original",
            actions_config=[
                {'type': 'action1', 'name': 'first'},
                {'type': 'action2', 'name': 'second'}
            ],
            context={}
        )
        
        assert result.output == 'output1'
        assert result.should_continue is False
        assert len(result.action_history) == 1
        assert action1.process_called is True
        assert action2.process_called is False
    
    def test_execute_pipeline_chains_output(self):
        """Test that pipeline chains output between actions."""
        pipeline = ActionPipeline()
        
        # First action modifies output
        action1 = MockAction({'_output': 'modified1', '_should_continue': True})
        # Second action should receive modified output
        action2 = MockAction({'_output': 'modified2', '_should_continue': True})
        
        pipeline.register_action('action1', action1)
        pipeline.register_action('action2', action2)
        
        result = pipeline.execute_pipeline(
            llm_output="original",
            actions_config=[
                {'type': 'action1', 'name': 'first'},
                {'type': 'action2', 'name': 'second'}
            ],
            context={}
        )
        
        assert result.output == 'modified2'
        assert len(result.action_history) == 2
        # Second action should have received first action's output
        assert action2.last_llm_output == 'modified1'
    
    def test_execute_pipeline_skips_missing_action(self):
        """Test that pipeline skips missing actions."""
        pipeline = ActionPipeline()
        
        result = pipeline.execute_pipeline(
            llm_output="original",
            actions_config=[{'type': 'nonexistent', 'name': 'missing'}],
            context={}
        )
        
        assert result.output == "original"
        assert result.should_continue is True
    
    def test_get_llm_tools_empty(self):
        """Test getting LLM tools from empty config."""
        pipeline = ActionPipeline()
        
        tools = pipeline.get_llm_tools([])
        
        assert tools == []
    
    def test_get_llm_tools_with_tool_spec(self):
        """Test getting LLM tools from action with tool spec."""
        pipeline = ActionPipeline()
        tool_spec = {
            'type': 'function',
            'function': {'name': 'test_func', 'description': 'Test function'}
        }
        action = MockAction({'_tool_spec': tool_spec})
        pipeline.register_action('test_action', action)
        
        tools = pipeline.get_llm_tools([{'type': 'test_action'}])
        
        assert len(tools) == 1
        assert tools[0] == tool_spec
    
    def test_clear_actions(self):
        """Test clearing all actions."""
        pipeline = ActionPipeline()
        action = MockAction({})
        pipeline.register_action('test', action)
        
        pipeline.clear_actions()
        
        assert pipeline.get_action('test') is None


class TestSingleton:
    """Tests for singleton functions."""
    
    def test_get_action_pipeline(self):
        """Test get_action_pipeline returns singleton."""
        reset_action_pipeline()
        
        pipeline1 = get_action_pipeline()
        pipeline2 = get_action_pipeline()
        
        assert pipeline1 is pipeline2
    
    def test_reset_action_pipeline(self):
        """Test reset_action_pipeline creates new instance."""
        pipeline1 = get_action_pipeline()
        reset_action_pipeline()
        pipeline2 = get_action_pipeline()
        
        assert pipeline1 is not pipeline2
