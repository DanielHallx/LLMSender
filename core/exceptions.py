#!/usr/bin/env python3
"""
Custom exceptions for LLMSender.

Categorized exceptions for better error handling and debugging.
"""


class LLMSenderError(Exception):
    """Base exception for all LLMSender errors."""
    pass


class ConfigurationError(LLMSenderError):
    """
    Raised when there's a configuration error.
    
    Examples:
    - Missing required fields
    - Invalid configuration values
    - Incompatible configuration combinations
    """
    pass


class ContentFetchError(LLMSenderError):
    """
    Raised when content fetching fails.
    
    Examples:
    - Network errors
    - API rate limiting
    - Invalid content source
    """
    pass


class LLMError(LLMSenderError):
    """
    Raised when LLM service fails.
    
    Examples:
    - API errors
    - Rate limiting
    - Invalid model configuration
    """
    pass


class NotificationError(LLMSenderError):
    """
    Raised when notification sending fails.
    
    Examples:
    - Failed to connect to notification service
    - Invalid credentials
    - Rate limiting
    """
    pass


class ActionError(LLMSenderError):
    """
    Raised when action execution fails.
    
    Examples:
    - Action processing error
    - Invalid action configuration
    - Pipeline execution failure
    """
    pass


class TriggerError(LLMSenderError):
    """
    Raised when trigger operations fail.
    
    Examples:
    - Trigger setup failure
    - Invalid trigger configuration
    - Trigger callback error
    """
    pass


class PackLoadError(LLMSenderError):
    """
    Raised when pack loading fails.
    
    Examples:
    - Module not found
    - Invalid pack structure
    - Security validation failure
    """
    pass


class TaskTimeoutError(LLMSenderError):
    """
    Raised when a task or operation times out.
    
    Examples:
    - Content fetch timeout
    - LLM response timeout
    - Action execution timeout
    """
    pass


class SecurityError(LLMSenderError):
    """
    Raised when a security violation is detected.
    
    Examples:
    - Path traversal attempt
    - Invalid module path
    - Unauthorized access
    """
    pass


class ValidationError(LLMSenderError):
    """
    Raised when validation fails.
    
    Examples:
    - Invalid task configuration
    - Missing required fields
    - Type mismatch
    """
    pass
