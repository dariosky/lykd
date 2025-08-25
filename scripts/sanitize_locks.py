import sys
import re
import os
import subprocess  # nosec: B404
from pathlib import Path
from urllib.parse import urlparse

PROJECT_PATH = Path(__file__).parent.parent
LOCK_PATH = PROJECT_PATH / "uv.lock"
PYPROJECT_PATH = PROJECT_PATH / "pyproject.toml"

changed = False

# Get schema+host from UV_DEFAULT_INDEX
uv_default_index = os.environ.get("UV_DEFAULT_INDEX")
custom_host_pattern = None
if uv_default_index:
    parsed = urlparse(uv_default_index)
    # Build schema+host (with port if present)
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    # Remove trailing /simple if present
    path = parsed.path
    if path.endswith("/simple"):
        path = path[: -len("simple")]
    # Only use scheme://host[:port][path] (without credentials, without /simple)
    custom_host_pattern = f"{parsed.scheme}://{host}{port}{path}"

# Sanitize uv.lock
if LOCK_PATH.exists() and custom_host_pattern:
    with LOCK_PATH.open("r", encoding="utf-8") as f:
        content = f.read()
    # Remove all occurrences of the custom index (schema+host, no credentials, no /simple)
    sanitized = re.sub(re.escape(custom_host_pattern), "https://pypi.org/", content)
    if sanitized != content:
        with LOCK_PATH.open("w", encoding="utf-8") as f:
            f.write(sanitized)
        subprocess.run(["git", "add", str(LOCK_PATH)], check=True)  # nosec: B603, B607
        print(f"Sanitized uv.lock by removing {custom_host_pattern} and re-staged.")
        changed = True

# Remove all [[tool.uv.index]] sections from pyproject.toml
if PYPROJECT_PATH.exists():
    with PYPROJECT_PATH.open("r", encoding="utf-8") as f:
        pyproject = f.read()
    # Regex to match [[tool.uv.index]] blocks (including multiline)
    sanitized_pyproject = re.sub(
        r"(?sm)^\[\[tool.uv.index\]\](?:\n.*?)*(?=^\[|\Z)", "", pyproject
    )
    if sanitized_pyproject != pyproject:
        with PYPROJECT_PATH.open("w", encoding="utf-8") as f:
            f.write(sanitized_pyproject)
        subprocess.run(["git", "add", str(PYPROJECT_PATH)], check=True)  # nosec: B603, B607
        print("Removed [[tool.uv.index]] section(s) from pyproject.toml and re-staged.")
        changed = True

if changed:
    sys.exit(1)  # Abort commit so user can review
else:
    sys.exit(0)
