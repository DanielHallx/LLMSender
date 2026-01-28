#!/usr/bin/env python3
"""
Configuration validation for LLMSender.

Validates task configurations at startup to catch errors early.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from .exceptions import ValidationError

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
        self.valid = False
    
    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)
    
    def merge(self, other: 'ValidationResult') -> None:
        """Merge another validation result into this one."""
        if not other.valid:
            self.valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


class ConfigValidator:
    """
    Validates LLMSender configuration.
    
    Checks:
    - Required fields exist
    - Field types are correct
    - References to plugins/packs are valid
    - Schedule/trigger configurations are valid
    """
    
    REQUIRED_TASK_FIELDS = ['name']
    REQUIRED_CONTENT_FIELDS = ['plugin']
    REQUIRED_LLM_FIELDS = ['plugin']
    
    def __init__(self):
        self._available_plugins: Dict[str, List[str]] = {}
        self._available_packs: Dict[str, Dict[str, bool]] = {}
    
    def validate(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate the entire configuration.
        
        Args:
            config: The configuration dictionary
            
        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult(valid=True)
        
        # Validate global settings
        global_result = self._validate_global_settings(config)
        result.merge(global_result)
        
        # Validate tasks
        tasks = config.get('tasks', [])
        if not tasks:
            result.add_warning("No tasks defined in configuration")
        
        for i, task in enumerate(tasks):
            task_result = self.validate_task(task, task_index=i)
            result.merge(task_result)
        
        return result
    
    def _validate_global_settings(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate global configuration settings."""
        result = ValidationResult(valid=True)
        
        # Validate timezone if present
        timezone = config.get('timezone')
        if timezone and not isinstance(timezone, str):
            result.add_error("'timezone' must be a string")
        
        # Validate log_level if present
        log_level = config.get('log_level')
        if log_level:
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if log_level.upper() not in valid_levels:
                result.add_error(f"Invalid log_level '{log_level}'. Must be one of: {valid_levels}")
        
        return result
    
    def validate_task(self, task: Dict[str, Any], task_index: int = 0) -> ValidationResult:
        """
        Validate a single task configuration.
        
        Args:
            task: The task configuration dictionary
            task_index: Index of the task (for error messages)
            
        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult(valid=True)
        task_name = task.get('name', f'task_{task_index}')
        
        # Check required fields
        if 'name' not in task:
            result.add_warning(f"Task at index {task_index} has no 'name' field")
        
        # Determine if this is a pack-based task
        is_pack_task = 'pack' in task or 'actions' in task or 'trigger' in task
        
        # Validate content configuration
        content_result = self._validate_content_config(task, task_name, is_pack_task)
        result.merge(content_result)
        
        # Validate LLM configuration
        llm_result = self._validate_llm_config(task, task_name)
        result.merge(llm_result)
        
        # Validate schedule/trigger
        schedule_result = self._validate_schedule_config(task, task_name)
        result.merge(schedule_result)
        
        # Validate notifiers
        notifiers_result = self._validate_notifiers_config(task, task_name)
        result.merge(notifiers_result)
        
        # Validate actions (for pack tasks)
        if 'actions' in task:
            actions_result = self._validate_actions_config(task, task_name)
            result.merge(actions_result)
        
        return result
    
    def _validate_content_config(
        self, 
        task: Dict[str, Any], 
        task_name: str,
        is_pack_task: bool
    ) -> ValidationResult:
        """Validate content configuration."""
        result = ValidationResult(valid=True)
        
        content = task.get('content')
        
        if content is None:
            result.add_error(f"Task '{task_name}': missing 'content' configuration")
            return result
        
        if is_pack_task and 'pack' in task:
            # Pack-based content - type is optional
            pass
        else:
            # Legacy content - plugin is required
            if 'plugin' not in content:
                result.add_error(f"Task '{task_name}': content.plugin not specified")
        
        return result
    
    def _validate_llm_config(
        self, 
        task: Dict[str, Any], 
        task_name: str
    ) -> ValidationResult:
        """Validate LLM configuration."""
        result = ValidationResult(valid=True)
        
        llm = task.get('llm')
        
        if llm is None:
            result.add_error(f"Task '{task_name}': missing 'llm' configuration")
            return result
        
        if 'plugin' not in llm:
            result.add_error(f"Task '{task_name}': llm.plugin not specified")
        
        return result
    
    def _validate_schedule_config(
        self, 
        task: Dict[str, Any], 
        task_name: str
    ) -> ValidationResult:
        """Validate schedule/trigger configuration."""
        result = ValidationResult(valid=True)
        
        schedule = task.get('schedule', {})
        trigger = task.get('trigger', {})
        
        if not schedule and not trigger:
            result.add_warning(f"Task '{task_name}': no schedule or trigger defined")
            return result
        
        if schedule:
            schedule_type = schedule.get('type')
            if not schedule_type:
                result.add_error(f"Task '{task_name}': schedule.type not specified")
            elif schedule_type not in ['cron', 'interval', 'once']:
                result.add_error(f"Task '{task_name}': invalid schedule.type '{schedule_type}'")
            
            # Validate cron schedule
            if schedule_type == 'cron':
                if 'hour' not in schedule:
                    result.add_warning(f"Task '{task_name}': cron schedule missing 'hour'")
            
            # Validate interval schedule
            if schedule_type == 'interval':
                has_interval = any(k in schedule for k in ['seconds', 'minutes', 'hours'])
                if not has_interval:
                    result.add_error(f"Task '{task_name}': interval schedule needs 'seconds', 'minutes', or 'hours'")
        
        if trigger:
            trigger_type = trigger.get('type')
            if not trigger_type:
                result.add_error(f"Task '{task_name}': trigger.type not specified")
        
        return result
    
    def _validate_notifiers_config(
        self, 
        task: Dict[str, Any], 
        task_name: str
    ) -> ValidationResult:
        """Validate notifiers configuration."""
        result = ValidationResult(valid=True)
        
        notifiers = task.get('notifiers', [])
        
        if not notifiers:
            result.add_warning(f"Task '{task_name}': no notifiers defined")
            return result
        
        for i, notifier in enumerate(notifiers):
            # Check for plugin or type
            has_plugin = 'plugin' in notifier
            has_type = 'type' in notifier
            
            if not has_plugin and not has_type:
                result.add_error(
                    f"Task '{task_name}': notifier {i} missing 'plugin' or 'type'"
                )
        
        return result
    
    def _validate_actions_config(
        self, 
        task: Dict[str, Any], 
        task_name: str
    ) -> ValidationResult:
        """Validate actions configuration."""
        result = ValidationResult(valid=True)
        
        actions = task.get('actions', [])
        
        for i, action in enumerate(actions):
            if 'type' not in action:
                result.add_error(f"Task '{task_name}': action {i} missing 'type'")
        
        return result


def validate_config(config: Dict[str, Any], raise_on_error: bool = False) -> ValidationResult:
    """
    Convenience function to validate configuration.
    
    Args:
        config: The configuration dictionary
        raise_on_error: If True, raise ValidationError on validation failure
        
    Returns:
        ValidationResult
        
    Raises:
        ValidationError: If raise_on_error is True and validation fails
    """
    validator = ConfigValidator()
    result = validator.validate(config)
    
    # Log warnings
    for warning in result.warnings:
        logger.warning(f"Config warning: {warning}")
    
    # Log errors
    for error in result.errors:
        logger.error(f"Config error: {error}")
    
    if raise_on_error and not result.valid:
        raise ValidationError(f"Configuration validation failed: {'; '.join(result.errors)}")
    
    return result
