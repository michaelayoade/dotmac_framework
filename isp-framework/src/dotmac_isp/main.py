"""Main entry point for the DotMac ISP Framework."""

import uvicorn

from dotmac_isp.app import app


def main():
    """Run the application."""
    uvicorn.run(
        "dotmac_isp.app:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )


if __name__ == "__main__":
    main()
