#!/usr/bin/env python3
"""Development server runner for LYKD backend"""

import uvicorn

if __name__ == "__main__":  # pragma: no cover
    uvicorn.run(
        "app:create_app",
        factory=True,
        host="127.0.0.1",
        port=3626,
        reload=False,
        workers=2,
        log_level="info",
        proxy_headers=True,
    )
