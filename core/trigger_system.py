#!/usr/bin/env python3
"""
Trigger management system for event-driven task execution.
"""
import logging
import threading
from typing import Dict, Any, Callable, Optional, List

from .interfaces import Trigger

logger = logging.getLogger(__name__)


class TriggerManager:
    """
    Manager for trigger plugins that handle event-driven task execution.
    
    Triggers can be:
    - Pack-based triggers (e.g., Twitter webhooks, file watchers)
    - Schedule-based triggers (handled by APScheduler in main.py)
    """
    
    def __init__(self):
        self._triggers: Dict[str, Trigger] = {}
        self._callbacks: Dict[str, Callable] = {}
        self._running = False
        self._lock = threading.Lock()
    
    def register_trigger(
        self,
        trigger_id: str,
        trigger_config: Dict[str, Any],
        callback: Callable[[Dict[str, Any]], None]
    ) -> bool:
        """
        Register a trigger with its callback.
        
        Args:
            trigger_id: Unique identifier for this trigger
            trigger_config: Configuration for the trigger
            callback: Function to call when trigger fires
            
        Returns:
            True if registration successful
        """
        trigger_type = trigger_config.get('type', '')
        
        if not trigger_type:
            logger.error(f"Trigger type not specified for trigger '{trigger_id}'")
            return False
        
        try:
            trigger = self._load_trigger(trigger_config)
            
            if trigger is None:
                logger.error(f"Failed to load trigger '{trigger_id}' of type '{trigger_type}'")
                return False
            
            with self._lock:
                self._triggers[trigger_id] = trigger
                self._callbacks[trigger_id] = callback
            
            # Set up the trigger with its callback
            trigger.setup(lambda data: self._on_trigger(trigger_id, data))
            
            logger.info(f"Registered trigger '{trigger_id}' of type '{trigger_type}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register trigger '{trigger_id}': {e}")
            return False
    
    def _load_trigger(self, trigger_config: Dict[str, Any]) -> Optional[Trigger]:
        """
        Load a trigger from configuration.
        
        Args:
            trigger_config: Trigger configuration
            
        Returns:
            The loaded trigger or None if loading fails
        """
        trigger_type = trigger_config.get('type', '')
        
        # Try to load from pack if type contains a dot
        if '.' in trigger_type:
            parts = trigger_type.rsplit('.', 1)
            if len(parts) == 2:
                pack_name, factory_name = parts
                try:
                    from .pack_loader import get_pack_loader
                    pack_loader = get_pack_loader()
                    trigger = pack_loader.load_component(
                        pack_name, 'triggers', factory_name, trigger_config
                    )
                    return trigger
                except Exception as e:
                    logger.error(f"Failed to load trigger from pack: {e}")
        
        return None
    
    def _on_trigger(self, trigger_id: str, trigger_data: Dict[str, Any]) -> None:
        """
        Handle a trigger event.
        
        Args:
            trigger_id: ID of the trigger that fired
            trigger_data: Data associated with the trigger event
        """
        callback = self._callbacks.get(trigger_id)
        
        if callback:
            try:
                logger.info(f"Trigger '{trigger_id}' fired, executing callback")
                callback(trigger_data)
            except Exception as e:
                logger.error(f"Callback for trigger '{trigger_id}' failed: {e}")
        else:
            logger.warning(f"No callback registered for trigger '{trigger_id}'")
    
    def unregister_trigger(self, trigger_id: str) -> bool:
        """
        Unregister a trigger.
        
        Args:
            trigger_id: ID of the trigger to unregister
            
        Returns:
            True if unregistration successful
        """
        with self._lock:
            if trigger_id not in self._triggers:
                logger.warning(f"Trigger '{trigger_id}' not found")
                return False
            
            trigger = self._triggers.pop(trigger_id)
            self._callbacks.pop(trigger_id, None)
            
            try:
                trigger.teardown()
            except Exception as e:
                logger.error(f"Error during trigger teardown: {e}")
            
            logger.info(f"Unregistered trigger '{trigger_id}'")
            return True
    
    def check_trigger(self, trigger_id: str) -> bool:
        """
        Manually check if a trigger condition is met.
        
        Args:
            trigger_id: ID of the trigger to check
            
        Returns:
            True if trigger condition is met
        """
        trigger = self._triggers.get(trigger_id)
        
        if trigger is None:
            logger.warning(f"Trigger '{trigger_id}' not found")
            return False
        
        try:
            return trigger.check()
        except Exception as e:
            logger.error(f"Error checking trigger '{trigger_id}': {e}")
            return False
    
    def get_trigger_data(self, trigger_id: str) -> Dict[str, Any]:
        """
        Get the data from a trigger.
        
        Args:
            trigger_id: ID of the trigger
            
        Returns:
            Trigger data dictionary
        """
        trigger = self._triggers.get(trigger_id)
        
        if trigger is None:
            logger.warning(f"Trigger '{trigger_id}' not found")
            return {}
        
        try:
            return trigger.get_trigger_data()
        except Exception as e:
            logger.error(f"Error getting trigger data for '{trigger_id}': {e}")
            return {}
    
    def list_triggers(self) -> List[str]:
        """
        List all registered trigger IDs.
        
        Returns:
            List of trigger IDs
        """
        with self._lock:
            return list(self._triggers.keys())
    
    def shutdown(self) -> None:
        """Shutdown all triggers gracefully."""
        logger.info("Shutting down trigger manager")
        
        with self._lock:
            for trigger_id, trigger in self._triggers.items():
                try:
                    trigger.teardown()
                    logger.debug(f"Trigger '{trigger_id}' torn down")
                except Exception as e:
                    logger.error(f"Error tearing down trigger '{trigger_id}': {e}")
            
            self._triggers.clear()
            self._callbacks.clear()
        
        logger.info("Trigger manager shutdown complete")


# Singleton instance
_trigger_manager: Optional[TriggerManager] = None


def get_trigger_manager() -> TriggerManager:
    """Get the singleton TriggerManager instance."""
    global _trigger_manager
    if _trigger_manager is None:
        _trigger_manager = TriggerManager()
    return _trigger_manager


def reset_trigger_manager() -> None:
    """Reset the singleton TriggerManager instance (for testing)."""
    global _trigger_manager
    if _trigger_manager is not None:
        _trigger_manager.shutdown()
    _trigger_manager = None
