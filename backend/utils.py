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


def humanize_milliseconds(elapsed):
    """Write a millisecond amount in a human-readable way.
    >>> humanize_milliseconds(0)
    '0 ms.'
    >>> humanize_milliseconds(11)
    '11 ms.'
    >>> humanize_milliseconds(65*1000)
    '1\\'5"'
    >>> humanize_milliseconds(30*1000)
    '30"'
    >>> humanize_milliseconds(30*1000+10)
    '30.0"'
    >>> humanize_milliseconds((115*60 + 10)*1000)
    "1h55'"
    """
    elapsed = int(elapsed)
    if elapsed <= 5000:  # up to 5" we show milliseconds
        return f"{elapsed:,} ms."
    elapsed /= 1000.0
    if elapsed >= 60 * 90:
        # more than 1.5h sho hours
        hours = int(elapsed / 3600)
        minutes = int((elapsed % 3600) / 60)
        return f"{hours}h{minutes}'"
    if elapsed >= 60:  # keep the minute
        minutes = int(elapsed / 60)
        seconds = int(elapsed - minutes * 60)
        return f"{minutes}'{seconds}\""
    else:
        # just the seconds
        if elapsed == int(elapsed):  # get rid of decimals
            return f'{int(elapsed)}"'
        return f'{elapsed:.1f}"'
