#!/usr/bin/env python3
"""
Main entry point for the DotMac Core Operations application.
"""

import sys
from pathlib import Path

import uvicorn
import structlog

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

from dotmac_core_ops.runtime import create_ops_app_from_env, OpsConfig

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


def main():
    """Main entry point."""
    try:
        # Load configuration from environment
        config = OpsConfig.from_env()

        logger.info(
            "Starting DotMac Core Operations",
            app_name=config.app_name,
            version=config.app_version,
            host=config.host,
            port=config.port,
            debug=config.debug
        )

        # Create FastAPI app
        app = create_ops_app_from_env()

        # Run the application
        uvicorn.run(
            app,
            host=config.host,
            port=config.port,
            workers=config.workers,
            log_level="info" if not config.debug else "debug",
            access_log=True,
            reload=config.debug,
        )

    except Exception as e:
        logger.error("Failed to start application", error=str(e), exc_info=e)
        sys.exit(1)


if __name__ == "__main__":
    main()
