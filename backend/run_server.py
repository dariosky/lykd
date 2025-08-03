#!/usr/bin/env python3
"""Production server runner for LYKD backend"""

import uvicorn
from app import create_app

if __name__ == "__main__":
    app = create_app()
    uvicorn.run(
        "app:create_app", factory=True, host="0.0.0.0", port=8000, log_level="info"
    )
