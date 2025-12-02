"""
Utility functions for API calls with retry logic and error handling.

Provides decorators and helpers for robust API interactions:
- Exponential backoff retry
- Circuit breaker pattern
- Request throttling
- Error categorization
"""
import time
import asyncio
from typing import Callable, Any, Optional, Dict, List
from functools import wraps
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base exception for API-related errors."""
    pass


class TransientAPIError(APIError):
    """Transient error that should be retried."""
    pass


class PermanentAPIError(APIError):
    """Permanent error that should not be retried."""
    pass


class RateLimitError(TransientAPIError):
    """Rate limit exceeded."""
    pass


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for API calls.

    Prevents repeated calls to a failing service by "opening" the circuit
    after a threshold of failures is reached. Automatically attempts to
    "close" the circuit after a cooldown period.
    """

    def __init__(self,
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: type = Exception):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Function to call
            *args, **kwargs: Function arguments

        Returns:
            Function result

        Raises:
            APIError: If circuit is open
        """
        if self.state == "open":
            # Check if we should attempt recovery
            if self.last_failure_time and \
               datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = "half-open"
                logger.info(f"Circuit breaker entering half-open state for {func.__name__}")
            else:
                raise PermanentAPIError(f"Circuit breaker open for {func.__name__}")

        try:
            result = func(*args, **kwargs)

            # Success - reset or close circuit
            if self.state == "half-open":
                logger.info(f"Circuit breaker closing for {func.__name__}")
                self.state = "closed"
                self.failure_count = 0

            return result

        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(f"Circuit breaker opening for {func.__name__} after {self.failure_count} failures")

            raise


class RateLimiter:
    """
    Token bucket rate limiter for API calls.

    Ensures API calls don't exceed specified rate limits.
    """

    def __init__(self, calls_per_second: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            calls_per_second: Maximum calls per second
        """
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time: Optional[float] = None

    def wait_if_needed(self):
        """Wait if necessary to respect rate limit."""
        if self.last_call_time is not None:
            elapsed = time.time() - self.last_call_time
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                time.sleep(sleep_time)

        self.last_call_time = time.time()


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    exceptions: tuple = (TransientAPIError, ConnectionError, TimeoutError)
):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each failure
        max_delay: Maximum delay between retries
        exceptions: Tuple of exceptions to catch and retry

    Example:
        @retry_with_backoff(max_attempts=3, base_delay=1.0)
        def fetch_data(url):
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )

                except PermanentAPIError as e:
                    # Don't retry permanent errors
                    logger.error(f"Permanent error in {func.__name__}: {e}")
                    raise

            # All retries exhausted
            raise last_exception

        return wrapper
    return decorator


async def retry_with_backoff_async(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    exceptions: tuple = (TransientAPIError, ConnectionError, TimeoutError)
):
    """
    Async version of retry_with_backoff decorator.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each failure
        max_delay: Maximum delay between retries
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = base_delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )

                except PermanentAPIError as e:
                    # Don't retry permanent errors
                    logger.error(f"Permanent error in {func.__name__}: {e}")
                    raise

            # All retries exhausted
            raise last_exception

        return wrapper
    return decorator


class ResultAggregator:
    """
    Aggregates results from multiple API sources with error tracking.

    Allows partial success - collects successful results even if some
    sources fail.
    """

    def __init__(self):
        """Initialize result aggregator."""
        self.results: Dict[str, List[Any]] = {}
        self.errors: Dict[str, List[Dict[str, Any]]] = {}
        self.timings: Dict[str, float] = {}

    def add_result(self, source: str, data: List[Any]):
        """
        Add successful results from a source.

        Args:
            source: Name of the data source
            data: List of results
        """
        if source not in self.results:
            self.results[source] = []
        self.results[source].extend(data)

    def add_error(self, source: str, error: Exception, context: Dict[str, Any] = None):
        """
        Add error from a source.

        Args:
            source: Name of the data source
            error: Exception that occurred
            context: Additional context about the error
        """
        if source not in self.errors:
            self.errors[source] = []

        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat(),
            "context": context or {}
        }
        self.errors[source].append(error_info)

    def add_timing(self, source: str, duration: float):
        """
        Add timing information for a source.

        Args:
            source: Name of the data source
            duration: Time taken in seconds
        """
        self.timings[source] = duration

    def get_all_results(self) -> List[Any]:
        """
        Get all results from all sources combined.

        Returns:
            Combined list of all results
        """
        all_results = []
        for source_results in self.results.values():
            all_results.extend(source_results)
        return all_results

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of results and errors.

        Returns:
            Dictionary with summary statistics
        """
        total_results = sum(len(r) for r in self.results.values())
        total_errors = sum(len(e) for e in self.errors.values())
        successful_sources = len(self.results)
        failed_sources = len(self.errors)

        return {
            "total_results": total_results,
            "total_errors": total_errors,
            "successful_sources": successful_sources,
            "failed_sources": failed_sources,
            "sources": list(self.results.keys()),
            "failed_source_names": list(self.errors.keys()),
            "timings": self.timings,
            "average_time": sum(self.timings.values()) / len(self.timings) if self.timings else 0
        }

    def has_results(self) -> bool:
        """Check if any results were collected."""
        return bool(self.results)

    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return bool(self.errors)


def safe_api_call(func: Callable,
                  *args,
                  default=None,
                  error_message: str = None,
                  **kwargs) -> Any:
    """
    Safely call an API function with error handling.

    Args:
        func: Function to call
        *args: Positional arguments for function
        default: Default value to return on error
        error_message: Custom error message to log
        **kwargs: Keyword arguments for function

    Returns:
        Function result or default value on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        msg = error_message or f"Error calling {func.__name__}"
        logger.error(f"{msg}: {e}")
        return default


# Global circuit breakers for different services
circuit_breakers = {
    "oecd": CircuitBreaker(failure_threshold=5, recovery_timeout=300),
    "world_bank": CircuitBreaker(failure_threshold=5, recovery_timeout=300),
    "arxiv": CircuitBreaker(failure_threshold=5, recovery_timeout=180),
    "pubmed": CircuitBreaker(failure_threshold=5, recovery_timeout=180),
    "semantic_scholar": CircuitBreaker(failure_threshold=5, recovery_timeout=180),
}


# Global rate limiters for different services
rate_limiters = {
    "oecd": RateLimiter(calls_per_second=1.0),
    "world_bank": RateLimiter(calls_per_second=2.0),
    "arxiv": RateLimiter(calls_per_second=1.0),
    "pubmed": RateLimiter(calls_per_second=3.0),
    "semantic_scholar": RateLimiter(calls_per_second=1.0),
}
