#!/usr/bin/env python3
"""
Action pipeline system for processing LLM output through a chain of actions.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from .interfaces import Action

logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    """Result from an action pipeline execution."""
    output: str
    should_continue: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    action_history: List[Dict[str, Any]] = field(default_factory=list)


class ActionPipeline:
    """
    Pipeline for executing a chain of actions on LLM output.
    
    Actions are executed in sequence, with each action receiving:
    - The output from the previous action (or original LLM output for first action)
    - The full context including trigger data, content, etc.
    """
    
    def __init__(self):
        self._actions: Dict[str, Action] = {}
    
    def register_action(self, name: str, action: Action) -> None:
        """
        Register an action for use in pipelines.
        
        Args:
            name: Unique name for this action
            action: The action instance
        """
        self._actions[name] = action
        logger.debug(f"Registered action: {name}")
    
    def get_action(self, name: str) -> Optional[Action]:
        """
        Get a registered action by name.
        
        Args:
            name: The action name
            
        Returns:
            The action instance or None if not found
        """
        return self._actions.get(name)
    
    def execute_pipeline(
        self,
        llm_output: str,
        actions_config: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> ActionResult:
        """
        Execute a pipeline of actions on the LLM output.
        
        Args:
            llm_output: The output from the LLM to process
            actions_config: List of action configurations
            context: Context data including trigger_data, content, etc.
            
        Returns:
            ActionResult with final output and metadata
        """
        result = ActionResult(output=llm_output)
        current_output = llm_output
        
        for i, action_config in enumerate(actions_config):
            action_type = action_config.get('type', '')
            action_name = action_config.get('name', f'action_{i}')
            
            logger.info(f"Executing action {i+1}/{len(actions_config)}: {action_name} ({action_type})")
            
            try:
                # Load the action
                action = self._load_action(action_config, context)
                
                if action is None:
                    logger.warning(f"Action '{action_name}' not found, skipping")
                    continue
                
                # Execute the action
                action_result = action.process(current_output, context)
                
                # Record history
                result.action_history.append({
                    'name': action_name,
                    'type': action_type,
                    'should_continue': action_result.get('should_continue', True),
                    'metadata': action_result.get('metadata', {})
                })
                
                # Update output
                current_output = action_result.get('output', current_output)
                result.output = current_output
                result.metadata.update(action_result.get('metadata', {}))
                
                # Check if we should continue
                if not action_result.get('should_continue', True):
                    logger.info(f"Action '{action_name}' stopped pipeline")
                    result.should_continue = False
                    break
                    
            except Exception as e:
                logger.error(f"Action '{action_name}' failed: {e}")
                result.action_history.append({
                    'name': action_name,
                    'type': action_type,
                    'error': str(e)
                })
                # Continue to next action by default
                continue
        
        logger.info(f"Pipeline completed: {len(result.action_history)} actions executed")
        return result
    
    def _load_action(self, action_config: Dict[str, Any], context: Dict[str, Any]) -> Optional[Action]:
        """
        Load an action from configuration.
        
        Args:
            action_config: Configuration for the action
            context: Context data
            
        Returns:
            The loaded action or None if not found
        """
        action_type = action_config.get('type', '')
        
        # Check if action is already registered
        if action_type in self._actions:
            return self._actions[action_type]
        
        # Try to load from pack
        if '.' in action_type:
            # Pack-based action: pack_name.action_name
            parts = action_type.rsplit('.', 1)
            if len(parts) == 2:
                pack_name, factory_name = parts
                try:
                    from .pack_loader import get_pack_loader
                    pack_loader = get_pack_loader()
                    action = pack_loader.load_component(
                        pack_name, 'actions', factory_name, action_config
                    )
                    if action:
                        # Cache for future use
                        self._actions[action_type] = action
                        return action
                except Exception as e:
                    logger.error(f"Failed to load action from pack: {e}")
        
        return None
    
    def get_llm_tools(self, actions_config: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get tool specifications from all actions for LLM function calling.
        
        Args:
            actions_config: List of action configurations
            
        Returns:
            List of OpenAI-compatible tool specifications
        """
        tools = []
        
        for action_config in actions_config:
            try:
                action = self._load_action(action_config, {})
                if action:
                    tool_spec = action.get_tool_spec()
                    if tool_spec:
                        tools.append(tool_spec)
            except Exception as e:
                logger.warning(f"Failed to get tool spec for action: {e}")
        
        return tools
    
    def clear_actions(self) -> None:
        """Clear all registered actions."""
        self._actions.clear()


# Singleton instance
_action_pipeline: Optional[ActionPipeline] = None


def get_action_pipeline() -> ActionPipeline:
    """Get the singleton ActionPipeline instance."""
    global _action_pipeline
    if _action_pipeline is None:
        _action_pipeline = ActionPipeline()
    return _action_pipeline


def reset_action_pipeline() -> None:
    """Reset the singleton ActionPipeline instance (for testing)."""
    global _action_pipeline
    _action_pipeline = None
