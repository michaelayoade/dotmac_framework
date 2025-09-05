#!/usr/bin/env python3
"""Development server with hot reload."""

import subprocess
from pathlib import Path


def main():
    """Start development server."""
    framework_root = Path(__file__).parent.parent.parent

    cmd = [
        "poetry",
        "run",
        "uvicorn",
        "src.dotmac_isp.main:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--log-level",
        "info",
    ]

    print("🚀 Starting DotMac Framework development server...")
    print("   http://localhost:8000")
    print("   http://localhost:8000/docs (API docs)")

    try:
        subprocess.run(cmd, cwd=framework_root)
    except KeyboardInterrupt:
        print("\n✅ Development server stopped")


if __name__ == "__main__":
    main()
