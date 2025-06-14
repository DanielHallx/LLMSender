import importlib
import os
from typing import Dict, Any, Type, Optional
import logging
from pathlib import Path
from .interfaces import ContentProvider, LLMSender, Notifier

logger = logging.getLogger(__name__)


class PluginLoader:
    """Dynamic plugin discovery and loading system."""
    
    PLUGIN_DIRS = {
        'content': 'send_to_ai_content',
        'llm': 'llm_message_sender',
        'notifier': 'message_notice'
    }
    
    PLUGIN_INTERFACES = {
        'content': ContentProvider,
        'llm': LLMSender,
        'notifier': Notifier
    }
    
    @classmethod
    def discover_plugins(cls, plugin_type: str) -> Dict[str, str]:
        """Discover all available plugins of a given type."""
        if plugin_type not in cls.PLUGIN_DIRS:
            raise ValueError(f"Unknown plugin type: {plugin_type}")
        
        plugin_dir = cls.PLUGIN_DIRS[plugin_type]
        plugins = {}
        
        if not os.path.exists(plugin_dir):
            logger.warning(f"Plugin directory {plugin_dir} does not exist")
            return plugins
        
        for filename in os.listdir(plugin_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                plugin_name = filename[:-3]  # Remove .py extension
                plugins[plugin_name] = f"{plugin_dir}.{plugin_name}"
        
        logger.info(f"Discovered {len(plugins)} {plugin_type} plugins: {list(plugins.keys())}")
        return plugins
    
    @classmethod
    def load_plugin(cls, plugin_type: str, plugin_name: str, config: Dict[str, Any]) -> Any:
        """Load and instantiate a specific plugin."""
        if plugin_type not in cls.PLUGIN_DIRS:
            raise ValueError(f"Unknown plugin type: {plugin_type}")
        
        module_path = f"{cls.PLUGIN_DIRS[plugin_type]}.{plugin_name}"
        
        try:
            module = importlib.import_module(module_path)
            
            # Look for a factory function or class with matching interface
            factory_func = getattr(module, 'factory', None)
            if factory_func and callable(factory_func):
                plugin_instance = factory_func(config)
            else:
                # Try to find a class that implements the interface
                interface_class = cls.PLUGIN_INTERFACES[plugin_type]
                plugin_class = cls._find_plugin_class(module, interface_class)
                
                if not plugin_class:
                    raise ValueError(f"No valid plugin class found in {module_path}")
                
                plugin_instance = plugin_class(config)
            
            logger.info(f"Successfully loaded {plugin_type} plugin: {plugin_name}")
            return plugin_instance
            
        except ImportError as e:
            logger.error(f"Failed to import plugin {module_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to instantiate plugin {plugin_name}: {e}")
            raise
    
    @classmethod
    def _find_plugin_class(cls, module: Any, interface: Type) -> Optional[Type]:
        """Find a class in the module that implements the given interface."""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, interface) and 
                attr is not interface):
                return attr
        return None