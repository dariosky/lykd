import asyncio
import datetime
import json
import logging
import os
import re
from functools import wraps
from pathlib import Path
from typing import Callable, Any

logger = logging.getLogger("lykd.cache")


def _escape_part(part: Any) -> str:
    """Escape a value to a filesystem-safe path segment."""
    s = str(part)
    # Replace path separators and control chars
    s = s.replace(os.sep, "_")
    if os.altsep:
        s = s.replace(os.altsep, "_")
    # Collapse whitespace to underscores
    s = re.sub(r"\s+", "_", s)
    # Remove characters not safe on common filesystems
    s = re.sub(r"[^A-Za-z0-9._\-=]", "_", s)
    # Avoid empty names
    s = s or "_"
    # Limit segment length to avoid extremely long filenames
    return s[:128]


def _json_default(o: Any):
    # Fallback conversions for non-JSON-serializable objects
    if isinstance(o, datetime.date):
        return o.strftime("%Y-%m-%d")
    if isinstance(o, datetime.datetime):
        return (
            o.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            if o.tzinfo
            else o.strftime("%Y-%m-%dT%H:%M:%S")
        )
    elif isinstance(o, datetime.time):
        return o.isoformat()
    elif isinstance(o, set):
        return list(o)
    elif isinstance(o, bytes):
        try:
            return o.decode("utf-8")
        except Exception:
            return list(o)
    elif hasattr(o, "dict") and callable(getattr(o, "dict")):
        return o.dict()
    elif hasattr(o, "__dict__"):
        return {k: v for k, v in o.__dict__.items() if not k.startswith("__")}
    return str(o)


def _read_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        logger.debug(f"Failed reading cache file {path}: {e}")
        return None


def _write_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, default=_json_default)
    os.replace(tmp, path)


def disk_cache(cache_dir: str = "./cache", namespace: str = "", enable: bool = True):
    def decorator(func: Callable) -> Callable:
        # If caching is disabled, return the original function
        if not enable:
            return func

        is_async = asyncio.iscoroutinefunction(func)

        def _build_key_parts(*args, **kwargs) -> list[str]:
            """Create ordered key parts from args and kwargs, skipping 'self'."""
            parts: list[str] = []
            if namespace:
                parts.append(str(namespace))

            # Positional args: skip instance (self) for methods
            for i, arg in enumerate(args):
                if i == 0 and hasattr(arg, "__dict__") and hasattr(arg, func.__name__):
                    continue
                parts.append(str(arg))

            # Keyword args in stable order
            for key in sorted(kwargs.keys()):
                parts.append(f"{key}={kwargs[key]}")

            return parts

        def _path_for(*args, **kwargs) -> Path:
            key_parts = [_escape_part(p) for p in _build_key_parts(*args, **kwargs)]
            base = Path(cache_dir) / _escape_part(func.__name__)
            if not key_parts:
                # No parameters: single file under function dir
                return base / "no_args.json"
            # First key part becomes a directory; remaining parts become the filename
            first, rest = key_parts[0], key_parts[1:]
            filename = ("__".join(rest) if rest else "data") + ".json"
            return base / first / filename

        async def _async_get_or_set(*args, **kwargs):
            path = _path_for(*args, **kwargs)
            cached = await asyncio.to_thread(_read_json, path)
            if cached is not None:
                return cached

            result = await func(*args, **kwargs)
            try:
                await asyncio.to_thread(_write_json, path, result)
            except Exception as e:
                logger.error(f"Failed writing cache file {path}: {e}")
            return result

        def _sync_get_or_set(*args, **kwargs):
            path = _path_for(*args, **kwargs)
            cached = _read_json(path)
            if cached is not None:
                return cached

            result = func(*args, **kwargs)
            try:
                _write_json(path, result)
            except Exception as e:
                logger.error(f"Failed writing cache file {path}: {e}")
            return result

        if is_async:

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await _async_get_or_set(*args, **kwargs)

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return _sync_get_or_set(*args, **kwargs)

            return sync_wrapper

    return decorator
