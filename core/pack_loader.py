#!/usr/bin/env python3
"""
Pack-based component loader with security validation.
Loads components from packs/ directory structure.
"""
import importlib
import logging
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, Type

from .interfaces import ContentProvider, LLMSender, Notifier, Action, Trigger

logger = logging.getLogger(__name__)


class PackLoader:
    """
    Dynamic pack component discovery and loading system.
    Packs are organized as: packs/<category>/<pack_name>/llmsender_pack_<component>/main.py
    """
    
    # Module name pattern for pack components
    MODULE_PATTERN = 'llmsender_pack_{component}'
    
    # Map component types to their interface classes
    COMPONENT_INTERFACES: Dict[str, Type] = {
        'content': ContentProvider,
        'senders': LLMSender,
        'notifiers': Notifier,
        'actions': Action,
        'triggers': Trigger,
    }
    
    # Map component types to their module names
    COMPONENT_MODULES: Dict[str, str] = {
        'content': 'llmsender_pack_content',
        'senders': 'llmsender_pack_sender',
        'notifiers': 'llmsender_pack_notice',
        'actions': 'llmsender_pack_action',
        'triggers': 'llmsender_pack_trigger',
    }
    
    # Base directory for packs (relative to project root)
    PACKS_BASE_DIR = 'packs'
    
    def __init__(self):
        self._loaded_components: Dict[str, Any] = {}
        self._packs_base_path = Path(self.PACKS_BASE_DIR).resolve()
    
    def _validate_module_path(self, module_path: str) -> bool:
        """
        Validate that the module path is safe to load.
        
        Security checks:
        - No path traversal attacks (..)
        - Path is within packs directory
        - Valid component name format
        
        Args:
            module_path: The module path to validate
            
        Returns:
            True if path is valid, raises ValueError otherwise
        """
        # Check for path traversal
        if '..' in module_path:
            raise ValueError(f"Path traversal detected in module path: {module_path}")
        
        # Convert module path to file path
        path_parts = module_path.split('.')
        
        # Check valid component name format (alphanumeric, underscore only)
        for part in path_parts:
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', part):
                raise ValueError(f"Invalid component name format: {part}")
        
        # Ensure path is within packs directory
        if path_parts[0] != 'packs':
            raise ValueError(f"Module path must start with 'packs': {module_path}")
        
        return True
    
    def _build_module_path(self, pack_name: str, component_type: str) -> str:
        """
        Build the full module path for a pack component.
        
        Args:
            pack_name: Name of the pack (e.g., 'core/twitter')
            component_type: Type of component ('content', 'senders', 'notifiers', 'actions', 'triggers')
            
        Returns:
            Full module path (e.g., 'packs.core.twitter.llmsender_pack_content.main')
        """
        if component_type not in self.COMPONENT_MODULES:
            raise ValueError(f"Unknown component type: {component_type}. "
                           f"Valid types: {list(self.COMPONENT_MODULES.keys())}")
        
        module_name = self.COMPONENT_MODULES[component_type]
        
        # Normalize pack name (replace / with .)
        pack_path = pack_name.replace('/', '.').replace('\\', '.')
        
        return f"packs.{pack_path}.{module_name}.main"
    
    def load_component(
        self,
        pack_name: str,
        component_type: str,
        factory_name: str,
        config: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Load a specific component from a pack.
        
        Args:
            pack_name: Name of the pack (e.g., 'core/twitter')
            component_type: Type of component ('content', 'senders', 'notifiers', 'actions', 'triggers')
            factory_name: Name of the factory function to call
            config: Configuration to pass to the component
            
        Returns:
            Instantiated component or None if loading fails
        """
        try:
            module_path = self._build_module_path(pack_name, component_type)
            
            # Validate module path security
            self._validate_module_path(module_path)
            
            # Import the module
            logger.debug(f"Loading module: {module_path}")
            module = importlib.import_module(module_path)
            
            # Get the factory function
            factory_func = getattr(module, factory_name, None)
            
            if factory_func is None:
                # Try to find a class that implements the interface
                interface_class = self.COMPONENT_INTERFACES.get(component_type)
                if interface_class:
                    component_class = self._find_component_class(module, interface_class)
                    if component_class:
                        logger.info(f"Loaded {component_type} component via class: {component_class.__name__}")
                        return component_class(config)
                
                raise ValueError(f"No factory function '{factory_name}' found in {module_path}")
            
            if not callable(factory_func):
                raise ValueError(f"'{factory_name}' in {module_path} is not callable")
            
            # Create and return the component instance
            component = factory_func(config)
            logger.info(f"Loaded {component_type} component '{factory_name}' from pack '{pack_name}'")
            return component
            
        except ImportError as e:
            logger.error(f"Failed to import pack component {pack_name}/{component_type}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load pack component {pack_name}/{component_type}/{factory_name}: {e}")
            raise
    
    def _find_component_class(self, module: Any, interface: Type) -> Optional[Type]:
        """
        Find a class in the module that implements the given interface.
        
        Args:
            module: The module to search
            interface: The interface class to match
            
        Returns:
            The found class or None
        """
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, interface) and 
                attr is not interface):
                return attr
        return None
    
    def discover_packs(self) -> Dict[str, Dict[str, bool]]:
        """
        Discover all available packs and their components.
        
        Returns:
            Dictionary mapping pack names to their available components
        """
        packs = {}
        packs_path = Path(self.PACKS_BASE_DIR)
        
        if not packs_path.exists():
            logger.warning(f"Packs directory does not exist: {packs_path}")
            return packs
        
        # Walk through packs directory
        for category_path in packs_path.iterdir():
            if not category_path.is_dir() or category_path.name.startswith('.'):
                continue
            
            for pack_path in category_path.iterdir():
                if not pack_path.is_dir() or pack_path.name.startswith('.'):
                    continue
                
                pack_name = f"{category_path.name}/{pack_path.name}"
                components = {}
                
                # Check for each component type
                for comp_type, module_name in self.COMPONENT_MODULES.items():
                    comp_path = pack_path / module_name
                    components[comp_type] = comp_path.exists() and (comp_path / 'main.py').exists()
                
                packs[pack_name] = components
                logger.debug(f"Discovered pack '{pack_name}': {components}")
        
        logger.info(f"Discovered {len(packs)} packs")
        return packs


# Singleton instance
_pack_loader: Optional[PackLoader] = None


def get_pack_loader() -> PackLoader:
    """Get the singleton PackLoader instance."""
    global _pack_loader
    if _pack_loader is None:
        _pack_loader = PackLoader()
    return _pack_loader


def reset_pack_loader() -> None:
    """Reset the singleton PackLoader instance (for testing)."""
    global _pack_loader
    _pack_loader = None
