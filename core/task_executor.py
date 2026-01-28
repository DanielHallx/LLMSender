#!/usr/bin/env python3
"""
Unified task execution engine for LLMSender.

Provides a single execution flow for both legacy and pack-based tasks,
reducing code duplication and improving maintainability.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

from .plugin_loader import PluginLoader
from .pack_loader import get_pack_loader
from .action_system import get_action_pipeline
from .config_validator import ConfigValidator
from .utils import TaskTimer, sanitize_config_for_log
from .exceptions import (
    ConfigurationError,
    ContentFetchError,
    LLMError,
    NotificationError,
    ActionError,
)

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Result of task execution."""
    success: bool
    task_name: str
    output: Optional[str] = None
    error: Optional[str] = None
    notifications_sent: int = 0
    notifications_failed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0


class TaskExecutor:
    """
    Unified task execution engine.
    
    Execution flow:
    1. Validate configuration
    2. Load content (auto-detect pack vs legacy)
    3. Get data (with timeout + retry)
    4. Load LLM (with tool specs)
    5. Generate summary
    6. Execute Action pipeline (optional)
    7. Send notifications
    8. Categorized error handling
    """
    
    def __init__(self):
        self.pack_loader = get_pack_loader()
        self.action_pipeline = get_action_pipeline()
        self.validator = ConfigValidator()
    
    def execute(
        self,
        task_config: Dict[str, Any],
        trigger_data: Optional[Dict[str, Any]] = None
    ) -> TaskResult:
        """
        Execute a task using the unified execution flow.
        
        Args:
            task_config: Task configuration dictionary
            trigger_data: Optional trigger data (for event-driven tasks)
            
        Returns:
            TaskResult with execution details
        """
        task_name = task_config.get('name', 'Unnamed Task')
        result = TaskResult(success=False, task_name=task_name)
        
        with TaskTimer(task_name) as timer:
            try:
                # Step 1: Validate configuration
                validation = self.validator.validate_task(task_config)
                if not validation.valid:
                    raise ConfigurationError(
                        f"Invalid task configuration: {'; '.join(validation.errors)}"
                    )
                
                # Build execution context
                context = self._build_context(task_config, trigger_data)
                
                # Determine if this is a pack-based task
                is_pack_task = self._is_pack_task(task_config)
                
                # Step 2: Load and fetch content
                content, prompt = self._fetch_content(task_config, context, is_pack_task)
                context['content'] = content
                context['prompt'] = prompt
                
                # Step 3: Prepare LLM configuration
                llm_config = task_config.get('llm', {}).copy()
                llm_plugin_name = llm_config.pop('plugin', None)
                
                if not llm_plugin_name:
                    raise ConfigurationError("LLM plugin not specified")
                
                # Step 4: Load actions and prepare LLM tools (for pack tasks)
                actions_config = task_config.get('actions', [])
                if actions_config:
                    llm_tools = self.action_pipeline.get_llm_tools(actions_config)
                    if llm_tools:
                        llm_config['tools'] = llm_tools
                        logger.info(f"Loaded {len(llm_tools)} LLM tools from actions")
                
                # Step 5: Generate LLM response
                llm_output = self._generate_summary(llm_plugin_name, llm_config, prompt, content)
                context['llm_output'] = llm_output
                
                # Step 6: Process through action pipeline (if configured)
                final_output = llm_output
                should_notify = True
                
                if actions_config:
                    logger.info(f"Processing through {len(actions_config)} actions")
                    try:
                        action_result = self.action_pipeline.execute_pipeline(
                            llm_output, actions_config, context
                        )
                        final_output = action_result.output
                        should_notify = action_result.should_continue
                        context['action_metadata'] = action_result.metadata
                        result.metadata['action_history'] = action_result.action_history
                    except Exception as e:
                        raise ActionError(f"Action pipeline failed: {e}") from e
                
                # Step 7: Send notifications
                if should_notify:
                    sent, failed = self._send_notifications(
                        task_config, final_output, context, is_pack_task
                    )
                    result.notifications_sent = sent
                    result.notifications_failed = failed
                else:
                    logger.info("Notification skipped by action pipeline")
                
                # Success
                result.success = True
                result.output = final_output
                logger.info(f"Task '{task_name}' completed successfully")
                
            except ConfigurationError as e:
                result.error = f"Configuration error: {e}"
                logger.error(result.error)
                self._handle_error_notifications(task_config, result.error)
                
            except ContentFetchError as e:
                result.error = f"Content fetch error: {e}"
                logger.error(result.error)
                self._handle_error_notifications(task_config, result.error)
                
            except LLMError as e:
                result.error = f"LLM error: {e}"
                logger.error(result.error)
                self._handle_error_notifications(task_config, result.error)
                
            except ActionError as e:
                result.error = f"Action error: {e}"
                logger.error(result.error)
                self._handle_error_notifications(task_config, result.error)
                
            except NotificationError as e:
                result.error = f"Notification error: {e}"
                logger.error(result.error)
                
            except Exception as e:
                result.error = f"Unexpected error: {e}"
                logger.error(f"Task '{task_name}' failed: {e}")
                self._handle_error_notifications(task_config, result.error)
            
            result.duration_seconds = timer.elapsed
        
        return result
    
    def _build_context(
        self,
        task_config: Dict[str, Any],
        trigger_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build execution context."""
        from datetime import timezone
        return {
            'task_name': task_config.get('name', 'Unnamed Task'),
            'task_config': sanitize_config_for_log(task_config),
            'trigger_data': trigger_data or {},
            'timestamp': datetime.now(timezone.utc)
        }
    
    def _is_pack_task(self, task_config: Dict[str, Any]) -> bool:
        """Determine if this is a pack-based task."""
        return 'pack' in task_config or 'actions' in task_config or 'trigger' in task_config
    
    def _fetch_content(
        self,
        task_config: Dict[str, Any],
        context: Dict[str, Any],
        is_pack_task: bool
    ) -> tuple:
        """
        Load content provider and fetch content.
        
        Returns:
            Tuple of (content, prompt)
        """
        content_config = task_config.get('content', {})
        
        try:
            if is_pack_task and 'pack' in task_config:
                # Pack-based content loading
                pack_name = task_config['pack']
                content_type = content_config.get('type', 'default')
                content_provider = self.pack_loader.load_component(
                    pack_name, 'content', content_type, content_config
                )
            else:
                # Legacy content loading
                content_config_copy = content_config.copy()
                content_plugin_name = content_config_copy.pop('plugin', None)
                if not content_plugin_name:
                    raise ConfigurationError("Content plugin not specified")
                content_provider = PluginLoader.load_plugin(
                    'content', content_plugin_name, content_config_copy
                )
            
            if not content_provider:
                raise ContentFetchError("Failed to load content provider")
            
            # Fetch content
            logger.info(f"Fetching content for task: {context['task_name']}")
            content = content_provider.fetch()
            prompt = content_provider.get_prompt()
            
            return content, prompt
            
        except Exception as e:
            raise ContentFetchError(f"Failed to fetch content: {e}") from e
    
    def _generate_summary(
        self,
        llm_plugin_name: str,
        llm_config: Dict[str, Any],
        prompt: str,
        content: str
    ) -> str:
        """Generate summary using LLM."""
        try:
            llm_sender = PluginLoader.load_plugin('llm', llm_plugin_name, llm_config)
            if not llm_sender:
                raise LLMError(f"Failed to load LLM plugin: {llm_plugin_name}")
            
            logger.info(f"Using {llm_plugin_name} to generate summary")
            return llm_sender.summarize(prompt, content)
            
        except Exception as e:
            raise LLMError(f"LLM generation failed: {e}") from e
    
    def _send_notifications(
        self,
        task_config: Dict[str, Any],
        message: str,
        context: Dict[str, Any],
        is_pack_task: bool
    ) -> tuple:
        """
        Send notifications.
        
        Returns:
            Tuple of (sent_count, failed_count)
        """
        notifiers = task_config.get('notifiers', [])
        title = task_config.get('title', context['task_name'])
        sent = 0
        failed = 0
        
        for notifier_config in notifiers:
            notifier_config_copy = notifier_config.copy()
            
            try:
                # Support both pack and legacy notifiers
                if is_pack_task and 'pack' in task_config and 'type' in notifier_config:
                    pack_name = task_config['pack']
                    notifier_type = notifier_config_copy.pop('type')
                    notifier = self.pack_loader.load_component(
                        pack_name, 'notifiers', notifier_type, notifier_config_copy
                    )
                else:
                    # Legacy notifier loading
                    notifier_plugin_name = notifier_config_copy.pop('plugin', None)
                    if not notifier_plugin_name:
                        logger.warning("Notifier plugin not specified, skipping")
                        failed += 1
                        continue
                    notifier = PluginLoader.load_plugin(
                        'notifier', notifier_plugin_name, notifier_config_copy
                    )
                
                if notifier:
                    logger.info(f"Sending notification via {notifier.__class__.__name__}")
                    success = notifier.send(message, title)
                    if success:
                        logger.info("Notification sent successfully")
                        sent += 1
                    else:
                        logger.error("Failed to send notification")
                        failed += 1
                else:
                    failed += 1
                    
            except Exception as e:
                logger.error(f"Notifier error: {e}")
                failed += 1
        
        return sent, failed
    
    def _handle_error_notifications(
        self,
        task_config: Dict[str, Any],
        error_message: str
    ) -> None:
        """Send error notifications if configured."""
        task_name = task_config.get('name', 'Unnamed Task')
        error_notifiers = task_config.get('error_notifiers', [])
        
        for notifier_config in error_notifiers:
            try:
                notifier_config_copy = notifier_config.copy()
                notifier_plugin_name = notifier_config_copy.pop('plugin', None)
                if notifier_plugin_name:
                    notifier = PluginLoader.load_plugin(
                        'notifier', notifier_plugin_name, notifier_config_copy
                    )
                    notifier.send(
                        f"Task failed: {error_message}",
                        f"Error: {task_name}"
                    )
            except Exception as notify_error:
                logger.error(f"Failed to send error notification: {notify_error}")


# Singleton instance
_task_executor: Optional[TaskExecutor] = None


def get_task_executor() -> TaskExecutor:
    """Get the singleton TaskExecutor instance."""
    global _task_executor
    if _task_executor is None:
        _task_executor = TaskExecutor()
    return _task_executor


def reset_task_executor() -> None:
    """Reset the singleton TaskExecutor instance (for testing)."""
    global _task_executor
    _task_executor = None
