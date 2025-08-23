#!/usr/bin/env python3
"""Check current plugins module coverage and identify missing tests."""

import sys
import os
import subprocess

# Set up paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set environment variables for testing
os.environ['DATABASE_URL'] = 'sqlite:///./test.db'
os.environ['ASYNC_DATABASE_URL'] = 'sqlite+aiosqlite:///./test.db'
os.environ['TESTING'] = 'true'
os.environ['PYTHONPATH'] = os.path.join(os.path.dirname(__file__), 'src')

def check_plugins_coverage():
    """Check coverage for plugins module."""
    print("🔍 Checking Plugins Module Coverage")
    print("=" * 50)
    
    # First, let's see what plugin files exist
    plugins_dir = os.path.join(os.path.dirname(__file__), 'src', 'dotmac_isp', 'plugins')
    
    print("📁 Plugin files found:")
    for root, dirs, files in os.walk(plugins_dir):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                rel_path = os.path.relpath(os.path.join(root, file), plugins_dir)
                print(f"  📄 {rel_path}")
    
    print()
    
    # Check existing tests
    tests_dir = os.path.join(os.path.dirname(__file__), 'tests', 'unit', 'plugins')
    print("🧪 Existing test files:")
    
    if os.path.exists(tests_dir):
        for root, dirs, files in os.walk(tests_dir):
            for file in files:
                if file.endswith('.py') and file != '__init__.py':
                    rel_path = os.path.relpath(os.path.join(root, file), tests_dir)
                    print(f"  ✅ {rel_path}")
    else:
        print("  ❌ No test files found")
    
    # Try to import plugins and see what we can test
    print()
    print("🧪 Testing plugin imports:")
    
    try:
        # Test core plugins
        from dotmac_isp.plugins.core import base, registry, loader, manager, models, exceptions, config_service
        print("  ✅ Plugin core modules imported successfully")
        
        # Test network automation
        from dotmac_isp.plugins.network_automation import freeradius_plugin
        print("  ✅ Network automation plugins imported successfully")
        
    except Exception as e:
        print(f"  ❌ Import error: {e}")
    
    return True

if __name__ == "__main__":
    check_plugins_coverage()