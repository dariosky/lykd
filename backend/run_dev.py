#!/usr/bin/env python3
"""Development server runner for LYKD backend"""

import setproctitle
import uvicorn

setproctitle.setproctitle("Lykd DEV API")
if __name__ == "__main__":  # pragma: no cover
    uvicorn.run(
        "app:create_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
