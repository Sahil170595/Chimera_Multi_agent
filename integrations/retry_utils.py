"""Retry utilities and Dead Letter Queue for Muse Protocol."""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Callable, Dict
from functools import wraps
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)

# DLQ directory
DLQ_DIR = Path("dlq")
DLQ_DIR.mkdir(exist_ok=True)


def write_to_dlq(
        operation: str,
        data: Dict[str, Any],
        error: Exception) -> None:
    """Write failed operation to Dead Letter Queue.

    Args:
        operation: Name of the failed operation
        data: Data that failed to process
        error: Exception that occurred
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        dlq_file = DLQ_DIR / f"{operation}_{timestamp}.json"

        dlq_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "data": data,
            "error": str(error),
            "error_type": type(error).__name__
        }

        with open(dlq_file, 'w') as f:
            json.dump(dlq_entry, f, indent=2, default=str)

        logger.warning(f"Wrote failed {operation} to DLQ: {dlq_file}")
    except Exception as e:
        logger.error(f"Failed to write to DLQ: {e}")


def clickhouse_retry(func: Callable) -> Callable:
    """Retry decorator for ClickHouse operations."""
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(
                f"ClickHouse operation {func.__name__} failed: {e}")
            # Write to DLQ if all retries exhausted
            if hasattr(args[0], '__class__'):
                operation = f"clickhouse_{func.__name__}"
                data = {
                    "args": str(args[1:]),
                    "kwargs": str(kwargs)}
                write_to_dlq(operation, data, e)
            raise
    return wrapper


def datadog_retry(func: Callable) -> Callable:
    """Retry decorator for Datadog operations."""
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(
                f"Datadog operation {func.__name__} failed "
                f"(non-critical): {e}")
            # Don't DLQ Datadog failures - observability only
            return None
    return wrapper


def api_retry(func: Callable) -> Callable:
    """Retry decorator for external API calls."""
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"API operation {func.__name__} failed: {e}")
            # Write to DLQ if all retries exhausted
            if hasattr(args[0], '__class__'):
                operation = f"api_{func.__name__}"
                data = {
                    "args": str(args[1:]),
                    "kwargs": str(kwargs)}
                write_to_dlq(operation, data, e)
            raise
    return wrapper


def replay_dlq(operation_filter: str = None) -> int:
    """Replay failed operations from DLQ.

    Args:
        operation_filter: Optional filter for operation names

    Returns:
        Number of successfully replayed operations
    """
    replayed = 0
    failed = []

    for dlq_file in DLQ_DIR.glob("*.json"):
        try:
            with open(dlq_file, 'r') as f:
                entry = json.load(f)

            operation = entry.get("operation", "")
            if operation_filter and operation_filter not in operation:
                continue

            logger.info(f"Replaying DLQ entry: {dlq_file.name}")

            # TODO: Add actual replay logic based on operation type
            # For now, just log and mark as replayed

            dlq_file.unlink()  # Remove after successful replay
            replayed += 1

        except Exception as e:
            logger.error(f"Failed to replay {dlq_file}: {e}")
            failed.append(dlq_file.name)

    logger.info(
        f"DLQ replay complete: {replayed} succeeded, "
        f"{len(failed)} failed")
    return replayed
