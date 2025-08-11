import asyncio
import hashlib
from functools import wraps
from typing import Callable

import diskcache as dc

import logging

logger = logging.getLogger("lykd.cache")


def disk_cache(
    cache_dir: str = "./cache/default", namespace: str = "", enable: bool = True
):
    """
    Decorator that caches function results to disk for unlimited time.
    Works with both sync and async functions.
    Cache key is based on function name, arguments, and keyword arguments.

    Args:
        cache_dir: Directory where cache files will be stored
        namespace: Optional namespace to separate different caches
        enable: Whether caching is enabled. If False, function is called directly without caching
    """

    def decorator(func: Callable) -> Callable:
        # If caching is disabled, return the original function
        if not enable:
            return func

        cache = dc.Cache(cache_dir)
        is_async = asyncio.iscoroutinefunction(func)

        def _create_cache_key(*args, **kwargs) -> str:
            """Create a cache key based on function name and parameters"""
            # Convert complex objects to string representations for hashing
            args_str = []
            for i, arg in enumerate(args):
                # Skip 'self' parameter for instance methods (first argument)
                if i == 0 and hasattr(arg, "__dict__") and hasattr(arg, func.__name__):
                    continue  # Skip the instance object

                if hasattr(arg, "__dict__"):
                    # For objects, use a string representation
                    arg_str = str(arg)
                    args_str.append(arg_str)
                else:
                    args_str.append(str(arg))

            kwargs_str = []
            for key, value in sorted(kwargs.items()):
                if hasattr(value, "__dict__"):
                    value_str = str(value)
                    kwargs_str.append(f"{key}={value_str}")
                else:
                    kwargs_str.append(f"{key}={str(value)}")

            # Create cache key from function name, namespace, args and kwargs
            key_parts = [namespace, func.__name__] + args_str + kwargs_str
            key_string = ":".join(filter(None, key_parts))

            # Hash the key to avoid filesystem issues with long/special characters
            return hashlib.sha256(key_string.encode()).hexdigest()

        if is_async:

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                cache_key = _create_cache_key(*args, **kwargs)

                # Try to get cached result
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for {func.__name__}: {cache_key[:16]}...")
                    return cached_result

                logger.debug(f"Cache miss for {func.__name__}: {cache_key[:16]}...")

                # Execute function and cache result
                result = await func(*args, **kwargs)
                cache.set(cache_key, result)

                return result

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                cache_key = _create_cache_key(*args, **kwargs)

                # Try to get cached result
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for {func.__name__}: {cache_key[:16]}...")
                    return cached_result

                logger.debug(f"Cache miss for {func.__name__}: {cache_key[:16]}...")

                # Execute function and cache result
                result = func(*args, **kwargs)
                cache.set(cache_key, result)

                return result

            return sync_wrapper

    return decorator
