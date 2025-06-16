import importlib
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class DependencyChecker:
    """Check and provide installation instructions for optional dependencies."""
    
    OPTIONAL_DEPENDENCIES = {
        'anthropic': {
            'package': 'anthropic',
            'install': 'pip install anthropic>=0.54.0',
            'plugins': ['anthropic_sender']
        },
        'openai': {
            'package': 'openai',
            'install': 'pip install openai>=1.0.0',
            'plugins': ['openai_sender']
        },
        'google.generativeai': {
            'package': 'google-generativeai',
            'install': 'pip install google-generativeai>=0.3.0',
            'plugins': ['gemini_sender']
        },
        'telegram': {
            'package': 'python-telegram-bot',
            'install': 'pip install python-telegram-bot>=20.0',
            'plugins': ['telegram']
        }
    }
    
    @classmethod
    def check_dependency(cls, module_name: str) -> bool:
        """Check if a module is installed."""
        try:
            importlib.import_module(module_name)
            return True
        except ImportError:
            return False
    
    @classmethod
    def get_missing_dependencies(cls, plugin_name: str) -> Optional[Dict]:
        """Get missing dependencies for a plugin."""
        for dep_name, dep_info in cls.OPTIONAL_DEPENDENCIES.items():
            if plugin_name in dep_info.get('plugins', []):
                if not cls.check_dependency(dep_name):
                    return dep_info
        return None
    
    @classmethod
    def check_and_suggest(cls, plugin_name: str) -> None:
        """Check dependencies and raise error with installation instructions."""
        missing = cls.get_missing_dependencies(plugin_name)
        if missing:
            raise ImportError(
                f"Plugin '{plugin_name}' requires '{missing['package']}'. "
                f"Install it with: {missing['install']}"
            )