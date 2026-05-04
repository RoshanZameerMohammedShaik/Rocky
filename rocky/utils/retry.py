"""Retry logic for Rocky.Ai."""

import time
from typing import Callable, TypeVar, Optional
from functools import wraps
from rocky.utils.logging import get_logger

T = TypeVar("T")
logger = get_logger(__name__)


class RetryError(Exception):
    """Raised when all retries are exhausted."""
    def __init__(self, message: str, last_error: Optional[Exception] = None):
        super().__init__(message)
        self.last_error = last_error


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """Decorator for retrying functions."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed: {e}"
                    )
                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff
            
            raise RetryError(
                f"Failed after {max_attempts} attempts",
                last_error=last_exception
            )
        return wrapper
    return decorator


def retry_with_feedback(
    func: Callable[..., T],
    error_handler: Callable[[Exception], str],
    max_attempts: int = 2,
) -> tuple[Optional[T], Optional[str]]:
    """
    Retry a function with error feedback.
    Returns (result, None) on success or (None, error_message) on failure.
    """
    last_error = None
    
    for attempt in range(max_attempts):
        try:
            result = func()
            return result, None
        except Exception as e:
            last_error = e
            feedback = error_handler(e)
            logger.warning(f"Attempt {attempt + 1} failed: {feedback}")
    
    return None, str(last_error) if last_error else "Unknown error"
