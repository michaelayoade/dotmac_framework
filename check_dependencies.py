#!/usr/bin/env python3
"""
Check for missing dependencies in the DotMac platform.
"""

import importlib
import sys

def check_packages():
    """Check if all required packages are available."""
    
    required_packages = [
        'opentelemetry',
        'opentelemetry.instrumentation.fastapi',
        'opentelemetry.instrumentation.sqlalchemy', 
        'opentelemetry.instrumentation.redis',
        'opentelemetry.instrumentation.httpx',
        'opentelemetry.instrumentation.urllib3',
        'fastapi',
        'sqlalchemy',
        'redis',
        'celery',
        'pydantic'
    ]
    
    missing = []
    available = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            available.append(package)
        except ImportError:
            missing.append(package)
    
    print("📦 Dependency Check Results")
    print("=" * 40)
    
    if available:
        print(f"✅ Available ({len(available)}):")
        for pkg in available:
            print(f"  - {pkg}")
    
    if missing:
        print(f"\n❌ Missing ({len(missing)}):")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\n🔧 To install missing packages:")
        print("pip install opentelemetry-instrumentation[fastapi,sqlalchemy,redis,httpx,urllib3]")
    else:
        print("\n🎉 All required packages are available!")
    
    return len(missing) == 0

if __name__ == "__main__":
    success = check_packages()
    sys.exit(0 if success else 1)
