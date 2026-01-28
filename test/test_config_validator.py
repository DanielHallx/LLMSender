#!/usr/bin/env python3
"""
Tests for the ConfigValidator system.
"""
import pytest
from typing import Dict, Any

from core.config_validator import ConfigValidator, ValidationResult, validate_config
from core.exceptions import ValidationError


class TestValidationResult:
    """Tests for ValidationResult dataclass."""
    
    def test_default_valid(self):
        """Test ValidationResult starts as valid."""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []
    
    def test_add_error_makes_invalid(self):
        """Test adding error makes result invalid."""
        result = ValidationResult(valid=True)
        result.add_error("test error")
        
        assert result.valid is False
        assert "test error" in result.errors
    
    def test_add_warning_keeps_valid(self):
        """Test adding warning keeps result valid."""
        result = ValidationResult(valid=True)
        result.add_warning("test warning")
        
        assert result.valid is True
        assert "test warning" in result.warnings
    
    def test_merge_results(self):
        """Test merging validation results."""
        result1 = ValidationResult(valid=True)
        result1.add_warning("warning1")
        
        result2 = ValidationResult(valid=False)
        result2.add_error("error1")
        result2.add_warning("warning2")
        
        result1.merge(result2)
        
        assert result1.valid is False
        assert "error1" in result1.errors
        assert "warning1" in result1.warnings
        assert "warning2" in result1.warnings


class TestConfigValidator:
    """Tests for ConfigValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return ConfigValidator()
    
    def test_validate_empty_config(self, validator):
        """Test validating empty configuration."""
        result = validator.validate({})
        
        assert result.valid is True
        assert any("No tasks defined" in w for w in result.warnings)
    
    def test_validate_valid_task(self, validator):
        """Test validating a valid task configuration."""
        config = {
            'tasks': [{
                'name': 'Test Task',
                'content': {'plugin': 'test_content'},
                'llm': {'plugin': 'test_llm'},
                'schedule': {'type': 'once'},
                'notifiers': [{'plugin': 'test_notifier'}]
            }]
        }
        
        result = validator.validate(config)
        
        assert result.valid is True
        assert result.errors == []
    
    def test_validate_missing_content_plugin(self, validator):
        """Test validation fails for missing content plugin."""
        config = {
            'tasks': [{
                'name': 'Test Task',
                'content': {'some_option': True},  # Has content but missing plugin
                'llm': {'plugin': 'test_llm'}
            }]
        }
        
        result = validator.validate(config)
        
        assert result.valid is False
        assert any("content.plugin" in e for e in result.errors)
    
    def test_validate_missing_llm_plugin(self, validator):
        """Test validation fails for missing LLM plugin."""
        config = {
            'tasks': [{
                'name': 'Test Task',
                'content': {'plugin': 'test_content'},
                'llm': {'model': 'test'}  # Has llm but missing plugin
            }]
        }
        
        result = validator.validate(config)
        
        assert result.valid is False
        assert any("llm.plugin" in e for e in result.errors)
    
    def test_validate_missing_content_section(self, validator):
        """Test validation fails for missing content section."""
        config = {
            'tasks': [{
                'name': 'Test Task',
                'llm': {'plugin': 'test_llm'}
            }]
        }
        
        result = validator.validate(config)
        
        assert result.valid is False
        assert any("content" in e for e in result.errors)
    
    def test_validate_missing_llm_section(self, validator):
        """Test validation fails for missing llm section."""
        config = {
            'tasks': [{
                'name': 'Test Task',
                'content': {'plugin': 'test_content'}
            }]
        }
        
        result = validator.validate(config)
        
        assert result.valid is False
        assert any("llm" in e for e in result.errors)
    
    def test_validate_invalid_schedule_type(self, validator):
        """Test validation fails for invalid schedule type."""
        config = {
            'tasks': [{
                'name': 'Test Task',
                'content': {'plugin': 'test_content'},
                'llm': {'plugin': 'test_llm'},
                'schedule': {'type': 'invalid_type'}
            }]
        }
        
        result = validator.validate(config)
        
        assert result.valid is False
        assert any("invalid schedule.type" in e for e in result.errors)
    
    def test_validate_cron_schedule_missing_hour(self, validator):
        """Test warning for cron schedule missing hour."""
        config = {
            'tasks': [{
                'name': 'Test Task',
                'content': {'plugin': 'test_content'},
                'llm': {'plugin': 'test_llm'},
                'schedule': {'type': 'cron'}  # Missing hour
            }]
        }
        
        result = validator.validate(config)
        
        # Should produce a warning, not an error
        assert any("cron schedule missing" in w for w in result.warnings)
    
    def test_validate_interval_schedule_missing_interval(self, validator):
        """Test validation fails for interval schedule without interval values."""
        config = {
            'tasks': [{
                'name': 'Test Task',
                'content': {'plugin': 'test_content'},
                'llm': {'plugin': 'test_llm'},
                'schedule': {'type': 'interval'}  # Missing seconds/minutes/hours
            }]
        }
        
        result = validator.validate(config)
        
        assert result.valid is False
        assert any("interval schedule needs" in e for e in result.errors)
    
    def test_validate_notifier_missing_plugin(self, validator):
        """Test validation fails for notifier without plugin."""
        config = {
            'tasks': [{
                'name': 'Test Task',
                'content': {'plugin': 'test_content'},
                'llm': {'plugin': 'test_llm'},
                'notifiers': [{}]  # Missing plugin
            }]
        }
        
        result = validator.validate(config)
        
        assert result.valid is False
        assert any("plugin" in e and "type" in e for e in result.errors)
    
    def test_validate_pack_task_content(self, validator):
        """Test validation for pack-based task doesn't require content plugin."""
        config = {
            'tasks': [{
                'name': 'Test Pack Task',
                'pack': 'core/twitter',
                'content': {'type': 'default'},  # No plugin needed for pack
                'llm': {'plugin': 'test_llm'}
            }]
        }
        
        result = validator.validate(config)
        
        # Should not have error about missing content.plugin
        assert not any("content.plugin" in e for e in result.errors)
    
    def test_validate_action_missing_type(self, validator):
        """Test validation fails for action without type."""
        config = {
            'tasks': [{
                'name': 'Test Task',
                'content': {'plugin': 'test_content'},
                'llm': {'plugin': 'test_llm'},
                'actions': [{}]  # Missing type
            }]
        }
        
        result = validator.validate(config)
        
        assert result.valid is False
        assert any("missing 'type'" in e for e in result.errors)
    
    def test_validate_invalid_timezone(self, validator):
        """Test validation fails for invalid timezone type."""
        config = {
            'timezone': 123,  # Should be string
            'tasks': []
        }
        
        result = validator.validate(config)
        
        assert result.valid is False
        assert any("timezone" in e and "string" in e for e in result.errors)
    
    def test_validate_invalid_log_level(self, validator):
        """Test validation fails for invalid log level."""
        config = {
            'log_level': 'INVALID',
            'tasks': []
        }
        
        result = validator.validate(config)
        
        assert result.valid is False
        assert any("log_level" in e for e in result.errors)


class TestValidateConfigFunction:
    """Tests for the validate_config convenience function."""
    
    def test_validate_config_returns_result(self):
        """Test validate_config returns ValidationResult."""
        result = validate_config({'tasks': []})
        
        assert isinstance(result, ValidationResult)
    
    def test_validate_config_raises_on_error(self):
        """Test validate_config raises when raise_on_error is True."""
        with pytest.raises(ValidationError):
            validate_config({
                'tasks': [{
                    'name': 'Bad Task',
                    'llm': {'plugin': 'test'}
                    # Missing content
                }]
            }, raise_on_error=True)
    
    def test_validate_config_no_raise_by_default(self):
        """Test validate_config doesn't raise by default."""
        result = validate_config({
            'tasks': [{
                'name': 'Bad Task',
                'llm': {'plugin': 'test'}
                # Missing content
            }]
        })
        
        assert result.valid is False
        assert len(result.errors) > 0
