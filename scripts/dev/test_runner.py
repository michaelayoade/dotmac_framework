#!/usr/bin/env python3
"""Comprehensive test runner."""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    """Run tests with various options."""
    parser = argparse.ArgumentParser(description="DotMac Framework Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--cov", action="store_true", help="Run with coverage")
    parser.add_argument("--fast", action="store_true", help="Run tests in parallel")

    args = parser.parse_args()

    framework_root = Path(__file__).parent.parent.parent

    cmd = ["poetry", "run", "pytest"]

    if args.unit:
        cmd.append("tests/unit")
    elif args.integration:
        cmd.append("tests/integration")
    else:
        cmd.append("tests/")

    cmd.extend(["-v"])

    if args.cov:
        cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term-missing"])

    if args.fast:
        cmd.extend(["-n", "auto"])  # Parallel execution

    print(f"🧪 Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, cwd=framework_root)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted")
        sys.exit(1)


if __name__ == "__main__":
    main()
