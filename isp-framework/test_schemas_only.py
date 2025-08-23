#!/usr/bin/env python3
"""Standalone test runner for shared schemas module."""

import sys
import os
import subprocess

# Set up paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set environment variables for SQLite testing
os.environ['DATABASE_URL'] = 'sqlite:///./test.db'
os.environ['ASYNC_DATABASE_URL'] = 'sqlite+aiosqlite:///./test.db'
os.environ['TESTING'] = 'true'
os.environ['PYTHONPATH'] = os.path.join(os.path.dirname(__file__), 'src')

if __name__ == "__main__":
    # Run the specific test with coverage
    cmd = [
        'python3', '-m', 'pytest', 
        'tests/unit/shared/test_schemas.py',
        '-v',
        '--cov=dotmac_isp.shared.schemas',
        '--cov-report=term-missing',
        '--tb=short'
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=os.path.dirname(__file__))
    sys.exit(result.returncode)