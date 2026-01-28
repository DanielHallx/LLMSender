#!/usr/bin/env python3
"""
Rate limiting for LLMSender.

Implements token bucket algorithm for controlling task execution rate.
"""
import logging
import time
import threading
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_second: float = 1.0
    burst_size: int = 5
    enabled: bool = True


class TokenBucket:
    """
    Token bucket rate limiter implementation.
    
    Allows burst traffic up to bucket capacity, then limits
    to the configured rate.
    """
    
    def __init__(
        self,
        rate: float = 1.0,
        capacity: int = 5
    ):
        """
        Initialize token bucket.
        
        Args:
            rate: Tokens per second to add
            capacity: Maximum bucket capacity (burst size)
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self._lock = threading.Lock()
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now
    
    def acquire(self, tokens: int = 1, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire
            blocking: If True, wait for tokens; if False, return immediately
            timeout: Maximum time to wait (None = infinite)
            
        Returns:
            True if tokens acquired, False otherwise
        """
        start_time = time.monotonic()
        
        while True:
            with self._lock:
                self._refill()
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
                
                if not blocking:
                    return False
                
                # Calculate wait time
                wait_time = (tokens - self.tokens) / self.rate
            
            # Check timeout
            if timeout is not None:
                elapsed = time.monotonic() - start_time
                if elapsed + wait_time > timeout:
                    return False
                wait_time = min(wait_time, timeout - elapsed)
            
            # Wait and try again
            time.sleep(min(wait_time, 0.1))  # Check at least every 100ms
    
    def try_acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens without waiting.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens acquired, False otherwise
        """
        return self.acquire(tokens, blocking=False)
    
    def available_tokens(self) -> float:
        """Get current available tokens."""
        with self._lock:
            self._refill()
            return self.tokens


class RateLimiter:
    """
    Rate limiter manager for multiple rate limit buckets.
    
    Supports per-task rate limiting with configurable rates.
    """
    
    def __init__(self, default_config: Optional[RateLimitConfig] = None):
        """
        Initialize rate limiter.
        
        Args:
            default_config: Default rate limit configuration
        """
        self.default_config = default_config or RateLimitConfig()
        self._buckets: Dict[str, TokenBucket] = {}
        self._configs: Dict[str, RateLimitConfig] = {}
        self._lock = threading.Lock()
    
    def configure(self, task_id: str, config: RateLimitConfig) -> None:
        """
        Configure rate limiting for a specific task.
        
        Args:
            task_id: Task identifier
            config: Rate limit configuration
        """
        with self._lock:
            self._configs[task_id] = config
            # Recreate bucket with new config
            if task_id in self._buckets:
                del self._buckets[task_id]
    
    def _get_bucket(self, task_id: str) -> TokenBucket:
        """Get or create bucket for task."""
        with self._lock:
            if task_id not in self._buckets:
                config = self._configs.get(task_id, self.default_config)
                self._buckets[task_id] = TokenBucket(
                    rate=config.requests_per_second,
                    capacity=config.burst_size
                )
            return self._buckets[task_id]
    
    def acquire(
        self,
        task_id: str,
        blocking: bool = True,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Acquire a token for the specified task.
        
        Args:
            task_id: Task identifier
            blocking: If True, wait for token; if False, return immediately
            timeout: Maximum time to wait
            
        Returns:
            True if token acquired, False otherwise
        """
        config = self._configs.get(task_id, self.default_config)
        
        # Skip rate limiting if disabled
        if not config.enabled:
            return True
        
        bucket = self._get_bucket(task_id)
        result = bucket.acquire(blocking=blocking, timeout=timeout)
        
        if not result:
            logger.warning(f"Rate limit exceeded for task: {task_id}")
        
        return result
    
    def try_acquire(self, task_id: str) -> bool:
        """
        Try to acquire a token without waiting.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if token acquired, False otherwise
        """
        return self.acquire(task_id, blocking=False)
    
    def get_available_tokens(self, task_id: str) -> float:
        """
        Get available tokens for a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Number of available tokens
        """
        bucket = self._get_bucket(task_id)
        return bucket.available_tokens()
    
    def reset(self, task_id: Optional[str] = None) -> None:
        """
        Reset rate limiter state.
        
        Args:
            task_id: Specific task to reset, or None to reset all
        """
        with self._lock:
            if task_id:
                if task_id in self._buckets:
                    del self._buckets[task_id]
            else:
                self._buckets.clear()


# Singleton instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the singleton RateLimiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def reset_rate_limiter() -> None:
    """Reset the singleton RateLimiter instance (for testing)."""
    global _rate_limiter
    _rate_limiter = None
