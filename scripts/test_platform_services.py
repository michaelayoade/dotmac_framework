#!/usr/bin/env python3
"""
Platform Services Test Runner
Focused testing for SigNoz dashboard functionality and platform services.
"""

import os
import subprocess
import sys


def main():
    """Run platform services tests with proper environment setup."""
    print("🔍 Testing Platform Services (SigNoz Dashboard)")
    print("=" * 50)

    # Set up environment
    env = os.environ.copy()
    env["PYTHONPATH"] = "./packages/dotmac-platform-services/src"

    try:
        result = subprocess.run(
            [
                "python3",
                "-m",
                "pytest",
                "./packages/dotmac-platform-services/tests/test_observability.py",
                "-v",
                "--tb=short",
                "--no-cov",
            ],
            env=env,
            timeout=300,  # 5 minutes
        )

        if result.returncode == 0:
            print("\n✅ Platform Services tests PASSED")
            print("🎯 SigNoz dashboard functionality validated")
        else:
            print(f"\n❌ Platform Services tests FAILED (exit code {result.returncode})")

        return result.returncode

    except subprocess.TimeoutExpired:
        print("\n⏰ Platform Services tests TIMED OUT")
        return 1
    except Exception as e:
        print(f"\n💥 Platform Services tests ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
