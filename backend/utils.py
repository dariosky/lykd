import functools
import logging
import time
import warnings


def time_it(func):
    """Decorator to measure execution time of async functions"""

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            print(f"\n{func.__name__} completed in {execution_time:.2f} seconds")

    return async_wrapper


def setup_logs():
    # logging.captureWarnings(True)
    warnings.simplefilter("default")
    logging.getLogger("lykd").setLevel(logging.DEBUG)
    logging.basicConfig()
