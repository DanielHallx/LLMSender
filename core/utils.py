import logging
import functools
import time
import re
import signal
import threading
from typing import Any, Callable, Optional, Dict
from contextlib import contextmanager
import os
import sys

from .exceptions import TaskTimeoutError


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'  # Reset color
    
    def __init__(self, use_colors: bool = True):
        # Format: "时间 - Level - 函数 - 内容"
        super().__init__(
            fmt='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        self.use_colors = use_colors
    
    def format(self, record):
        if self.use_colors and record.levelname in self.COLORS:
            # Add color to the level name
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        
        return super().format(record)


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """Configure logging for the application with colored console output."""
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Create console handler with colored formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter(use_colors=sys.stdout.isatty()))
    root_logger.addHandler(console_handler)
    
    # Create file handler with plain formatter (no colors)
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(ColoredFormatter(use_colors=False))
        root_logger.addHandler(file_handler)
    
    # Set logging level
    root_logger.setLevel(getattr(logging, log_level.upper()))


def retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
) -> Callable:
    """Decorator for exponential backoff retry logic."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            logger = logging.getLogger(func.__module__ if hasattr(func, '__module__') else __name__)
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        sleep_time = backoff_factor ** attempt
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                            f"Retrying in {sleep_time}s..."
                        )
                        
                        if on_retry:
                            on_retry(attempt + 1, e)
                        
                        time.sleep(sleep_time)
                    else:
                        logger.error(
                            f"All {max_retries} attempts failed for {func.__name__}: {e}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


def get_env_var(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """Get environment variable with optional requirement check."""
    value = os.environ.get(key, default)
    
    if required and value is None:
        raise ValueError(f"Required environment variable '{key}' is not set")
    
    return value


class TaskTimer:
    """Context manager for timing task execution."""
    
    def __init__(self, task_name: str):
        self.task_name = task_name
        self.start_time = None
        self.end_time = None
        self.logger = logging.getLogger(__name__)
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"Starting task: {self.task_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        if exc_type:
            self.logger.error(
                f"Task '{self.task_name}' failed after {duration:.2f}s: {exc_val}"
            )
        else:
            self.logger.info(
                f"Task '{self.task_name}' completed in {duration:.2f}s"
            )
    
    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.time()
        return end - self.start_time


# =============================================================================
# Timeout Utilities
# =============================================================================

@contextmanager
def timeout(seconds: int, operation_name: str = "operation"):
    """
    Context manager for operation timeout control.
    
    Args:
        seconds: Timeout in seconds
        operation_name: Name of the operation (for error messages)
        
    Raises:
        TaskTimeoutError: If operation exceeds timeout
        
    Note:
        On Windows or in non-main threads, timeout is not enforced and a warning is logged.
        This is a limitation of signal-based timeouts.
        
    Example:
        >>> with timeout(30, "API call"):
        ...     response = api.call()
    """
    def _timeout_handler(signum, frame):
        raise TaskTimeoutError(f"{operation_name} timed out after {seconds} seconds")
    
    # Only use signal-based timeout on Unix-like systems and in main thread
    use_signal = (
        hasattr(signal, 'SIGALRM') and 
        threading.current_thread() is threading.main_thread()
    )
    
    if use_signal:
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        # Fallback for non-Unix or non-main thread - just yield without timeout
        # Real timeout would require threading which adds complexity
        logger = logging.getLogger(__name__)
        logger.warning(
            f"Timeout not enforced for '{operation_name}': "
            "signal-based timeout only works on Unix in main thread"
        )
        yield


def with_timeout(seconds: int, operation_name: str = "operation"):
    """
    Decorator for adding timeout to a function.
    
    Args:
        seconds: Timeout in seconds
        operation_name: Name of the operation (for error messages)
        
    Returns:
        Decorated function
        
    Example:
        >>> @with_timeout(30, "API call")
        ... def call_api():
        ...     return api.call()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            with timeout(seconds, operation_name or func.__name__):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# Log Sanitization Utilities
# =============================================================================

# Patterns for sensitive data - only match when in context
SENSITIVE_PATTERNS = [
    (re.compile(r'(api[_-]?key\s*[=:]\s*)["\']?[\w\-]+["\']?', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(api[_-]?secret\s*[=:]\s*)["\']?[\w\-]+["\']?', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(\btoken\s*[=:]\s*)["\']?[\w\-\.]+["\']?', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(\bpassword\s*[=:]\s*)["\']?[^\s"\']+["\']?', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(\bsecret\s*[=:]\s*)["\']?[\w\-]+["\']?', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(\bauth\s*[=:]\s*)["\']?[\w\-]+["\']?', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(bearer\s+)[\w\-\.]+', re.IGNORECASE), r'\1[REDACTED]'),
    # API key patterns (well-known formats only)
    (re.compile(r'sk-[a-zA-Z0-9]{20,}'), '[REDACTED_API_KEY]'),
    # AWS access key format
    (re.compile(r'AKIA[A-Z0-9]{16}'), '[REDACTED_AWS_KEY]'),
]

# Keys that should be redacted in config dictionaries (exact matches only)
SENSITIVE_KEYS = {
    'api_key', 'api_secret', 'apikey', 'apisecret',
    'token', 'access_token', 'access_token_secret',
    'password', 'passwd', 'secret', 'private_key',
    'consumer_key', 'consumer_secret', 'bearer_token',
    'auth', 'authorization', 'credentials',
}


def sanitize_for_log(text: str, max_length: int = 100) -> str:
    """
    Sanitize sensitive data for logging.
    
    Args:
        text: Text to sanitize
        max_length: Maximum length before truncation
        
    Returns:
        Sanitized text
    """
    # Apply sensitive patterns
    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        if callable(replacement):
            result = pattern.sub(replacement, result)
        else:
            result = pattern.sub(replacement, result)
    
    # Truncate if too long
    if len(result) > max_length:
        return f"{result[:max_length]}... (truncated)"
    return result


def sanitize_config_for_log(config: Dict[str, Any], depth: int = 0, max_depth: int = 10) -> Dict[str, Any]:
    """
    Sanitize configuration dictionary for logging.
    
    Recursively processes dictionaries and lists, redacting sensitive values.
    
    Args:
        config: Configuration dictionary
        depth: Current recursion depth
        max_depth: Maximum recursion depth
        
    Returns:
        Sanitized configuration dictionary
    """
    if depth > max_depth:
        return {"_truncated": "max depth exceeded"}
    
    result = {}
    for key, value in config.items():
        config_key_lower = key.lower()
        
        # Check if key is sensitive (exact match or contains sensitive words as whole words)
        is_sensitive = (
            config_key_lower in SENSITIVE_KEYS or
            any(config_key_lower.endswith(f'_{s}') or config_key_lower.endswith(f'-{s}') or 
                config_key_lower.startswith(f'{s}_') or config_key_lower.startswith(f'{s}-') or
                config_key_lower == s
                for s in ['key', 'secret', 'token', 'password', 'auth', 'credential'])
        )
        
        if is_sensitive:
            result[key] = '[REDACTED]'
        elif isinstance(value, dict):
            result[key] = sanitize_config_for_log(value, depth + 1, max_depth)
        elif isinstance(value, list):
            result[key] = [
                sanitize_config_for_log(item, depth + 1, max_depth) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    
    return result


class SecureLogFilter(logging.Filter):
    """
    Logging filter that sanitizes sensitive data.
    
    Add to a logger to automatically sanitize messages:
        logger.addFilter(SecureLogFilter())
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and sanitize log record."""
        if isinstance(record.msg, str):
            record.msg = sanitize_for_log(record.msg, max_length=10000)
        
        # Sanitize arguments if present
        if record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized_args.append(sanitize_for_log(arg, max_length=10000))
                elif isinstance(arg, dict):
                    sanitized_args.append(sanitize_config_for_log(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        
        return True