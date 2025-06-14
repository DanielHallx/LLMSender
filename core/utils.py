import logging
import functools
import time
from typing import Any, Callable, Optional
import os
from datetime import datetime
import sys


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


def sanitize_for_log(text: str, max_length: int = 100) -> str:
    """Sanitize sensitive data for logging."""
    if len(text) > max_length:
        return f"{text[:max_length]}... (truncated)"
    return text


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