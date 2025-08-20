"""
DotMac API Gateway - Command line entry point.
"""

import argparse
import sys
from pathlib import Path

from .runtime import run_gateway


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="DotMac API Gateway")

    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )

    args = parser.parse_args()

    # Validate config file if provided
    if args.config and not Path(args.config).exists():
        print(f"Error: Configuration file not found: {args.config}")
        sys.exit(1)

    try:
        run_gateway(
            config_path=args.config,
            host=args.host,
            port=args.port,
            workers=args.workers,
            reload=args.reload,
        )
    except KeyboardInterrupt:
        print("\nShutting down API Gateway...")
    except Exception as e:
        print(f"Error starting API Gateway: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
