"""Main entry point for the DotMac ISP Framework."""

import uvicorn

from dotmac_isp.core.settings import get_settings


def main():
    """Run the application."""
    settings = get_settings()
    uvicorn.run(
        "dotmac_isp.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
