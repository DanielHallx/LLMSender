#!/usr/bin/env python3
"""
Tests for the PackLoader system.
"""
import pytest

from core.pack_loader import PackLoader, get_pack_loader, reset_pack_loader


class TestPackLoader:
    """Tests for PackLoader class."""
    
    def test_component_interfaces_mapping(self):
        """Test that COMPONENT_INTERFACES contains all expected types."""
        loader = PackLoader()
        
        expected_types = ['content', 'senders', 'notifiers', 'actions', 'triggers']
        for comp_type in expected_types:
            assert comp_type in loader.COMPONENT_INTERFACES
    
    def test_component_modules_mapping(self):
        """Test that COMPONENT_MODULES contains all expected types."""
        loader = PackLoader()
        
        expected_mappings = {
            'content': 'llmsender_pack_content',
            'senders': 'llmsender_pack_sender',
            'notifiers': 'llmsender_pack_notice',
            'actions': 'llmsender_pack_action',
            'triggers': 'llmsender_pack_trigger',
        }
        
        for comp_type, module_name in expected_mappings.items():
            assert loader.COMPONENT_MODULES[comp_type] == module_name
    
    def test_validate_module_path_valid(self):
        """Test validation passes for valid paths."""
        loader = PackLoader()
        
        # Valid paths
        assert loader._validate_module_path('packs.core.twitter.llmsender_pack_content.main') is True
        assert loader._validate_module_path('packs.core.core_actions.llmsender_pack_action.main') is True
    
    def test_validate_module_path_traversal_attack(self):
        """Test validation fails for path traversal attempts."""
        loader = PackLoader()
        
        with pytest.raises(ValueError, match="Path traversal detected"):
            loader._validate_module_path('packs..core.twitter.main')
        
        with pytest.raises(ValueError, match="Path traversal detected"):
            loader._validate_module_path('packs.core.twitter..main')
    
    def test_validate_module_path_invalid_start(self):
        """Test validation fails for paths not starting with 'packs'."""
        loader = PackLoader()
        
        with pytest.raises(ValueError, match="must start with 'packs'"):
            loader._validate_module_path('core.twitter.main')
        
        with pytest.raises(ValueError, match="must start with 'packs'"):
            loader._validate_module_path('etc.passwd')
    
    def test_validate_module_path_invalid_component_name(self):
        """Test validation fails for invalid component names."""
        loader = PackLoader()
        
        with pytest.raises(ValueError, match="Invalid component name format"):
            loader._validate_module_path('packs.core.twitter-pack.main')
        
        with pytest.raises(ValueError, match="Invalid component name format"):
            loader._validate_module_path('packs.core.123invalid.main')
    
    def test_build_module_path(self):
        """Test building module paths from pack name and component type."""
        loader = PackLoader()
        
        # Test content component
        path = loader._build_module_path('core/twitter', 'content')
        assert path == 'packs.core.twitter.llmsender_pack_content.main'
        
        # Test actions component
        path = loader._build_module_path('core/core_actions', 'actions')
        assert path == 'packs.core.core_actions.llmsender_pack_action.main'
        
        # Test senders component (LLMSender support)
        path = loader._build_module_path('core/test', 'senders')
        assert path == 'packs.core.test.llmsender_pack_sender.main'
    
    def test_build_module_path_invalid_component_type(self):
        """Test building module path fails for invalid component type."""
        loader = PackLoader()
        
        with pytest.raises(ValueError, match="Unknown component type"):
            loader._build_module_path('core/twitter', 'invalid_type')
    
    def test_discover_packs(self):
        """Test discovering available packs."""
        loader = PackLoader()
        
        packs = loader.discover_packs()
        
        # Should find at least the core packs
        assert 'core/twitter' in packs or 'core/core_actions' in packs
        
        # Check structure of discovered packs
        for pack_name, components in packs.items():
            assert isinstance(components, dict)
            assert 'content' in components
            assert 'actions' in components
    
    def test_load_component_success(self):
        """Test loading an existing component."""
        loader = PackLoader()
        
        # Load an action from the core_actions pack
        try:
            action = loader.load_component(
                pack_name='core/core_actions',
                component_type='actions',
                factory_name='filter',
                config={'min_length': 10}
            )
            assert action is not None
        except ImportError:
            pytest.skip("Core actions pack not available")
    
    def test_load_component_not_found(self):
        """Test loading a non-existent component raises error."""
        loader = PackLoader()
        
        with pytest.raises(Exception):
            loader.load_component(
                pack_name='nonexistent/pack',
                component_type='content',
                factory_name='test',
                config={}
            )
    
    def test_load_component_security_check(self):
        """Test that load_component validates module path."""
        loader = PackLoader()
        
        # Attempt to load with path traversal should fail
        with pytest.raises(ValueError):
            loader.load_component(
                pack_name='../etc',
                component_type='content',
                factory_name='passwd',
                config={}
            )


class TestSingleton:
    """Tests for singleton functions."""
    
    def test_get_pack_loader(self):
        """Test get_pack_loader returns singleton."""
        reset_pack_loader()
        
        loader1 = get_pack_loader()
        loader2 = get_pack_loader()
        
        assert loader1 is loader2
    
    def test_reset_pack_loader(self):
        """Test reset_pack_loader creates new instance."""
        loader1 = get_pack_loader()
        reset_pack_loader()
        loader2 = get_pack_loader()
        
        assert loader1 is not loader2


class TestSecurityHardening:
    """Tests for security features in PackLoader."""
    
    def test_blocks_system_paths(self):
        """Test that system paths are blocked."""
        loader = PackLoader()
        
        dangerous_paths = [
            '/etc/passwd',
            'C:\\Windows\\System32',
            '../../../etc/passwd',
            'packs/../etc/passwd',
        ]
        
        for path in dangerous_paths:
            with pytest.raises(ValueError):
                loader._validate_module_path(path)
    
    def test_valid_pack_name_characters(self):
        """Test that only valid characters are allowed in pack names."""
        loader = PackLoader()
        
        # Valid names should work
        valid_path = loader._build_module_path('core/twitter', 'content')
        assert 'packs.core.twitter' in valid_path
        
        # Invalid characters should be rejected through validation
        with pytest.raises(ValueError):
            loader._validate_module_path('packs.core.twit$er.main')
