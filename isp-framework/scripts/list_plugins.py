#!/usr/bin/env python3
"""
Plugin Listing Script

Lists available and installed plugins with their status and information.
"""

import json
import sys
import subprocess
from pathlib import Path
from importlib.metadata import distributions, PackageNotFoundError

def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent

def check_package_installed(package_name):
    """Check if a package is installed."""
    try:
        # Handle package names with version specifiers
        clean_name = package_name.split(">=")[0].split("==")[0].split("<")[0]
        
        # Check if package is installed
        for dist in distributions():
            if dist.metadata["Name"].lower() == clean_name.lower():
                return dist.version
        return None
    except Exception:
        return None

def get_plugin_definitions():
    """Get plugin definitions from install_plugin.py."""
    # Import the definitions from install_plugin.py
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "install_plugin", 
        Path(__file__).parent / "install_plugin.py"
    )
    install_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(install_module)
    return install_module.PLUGIN_DEFINITIONS

def get_installed_plugins():
    """Get list of installed plugins from metadata."""
    metadata_file = (
        get_project_root() / "src" / "dotmac_isp" / "plugins" / "registry" / "available_plugins.json"
    )
    
    if not metadata_file.exists():
        return {}
    
    try:
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        return metadata.get("plugins", {})
    except Exception as e:
        print(f"Warning: Could not read plugin metadata: {e}")
        return {}

def format_plugin_status(plugin_name, plugin_info, installed_plugins):
    """Format plugin status for display."""
    # Check if plugin is registered as installed
    is_registered = plugin_name in installed_plugins
    
    # Check if dependencies are actually installed
    deps_installed = []
    deps_missing = []
    
    for dep in plugin_info["dependencies"]:
        version = check_package_installed(dep)
        if version:
            deps_installed.append(f"{dep} ({version})")
        else:
            deps_missing.append(dep)
    
    # Determine overall status
    if is_registered and not deps_missing:
        status = "✅ INSTALLED"
        status_color = "green"
    elif deps_missing:
        status = "❌ MISSING DEPS"
        status_color = "red"
    elif is_registered:
        status = "⚠️  PARTIAL"
        status_color = "yellow"
    else:
        status = "⭕ AVAILABLE"
        status_color = "blue"
    
    return {
        "status": status,
        "status_color": status_color,
        "is_registered": is_registered,
        "deps_installed": deps_installed,
        "deps_missing": deps_missing
    }

def print_plugin_table():
    """Print a formatted table of all plugins."""
    plugin_definitions = get_plugin_definitions()
    installed_plugins = get_installed_plugins()
    
    print("\n🔌 DotMac ISP Framework - Available Integration Plugins")
    print("=" * 80)
    
    # Group plugins by category
    categories = {}
    for plugin_name, plugin_info in plugin_definitions.items():
        category = plugin_info["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append((plugin_name, plugin_info))
    
    # Display plugins by category
    for category, plugins in sorted(categories.items()):
        print(f"\n📦 {category.replace('_', ' ').title()}")
        print("-" * 40)
        
        for plugin_name, plugin_info in sorted(plugins):
            status_info = format_plugin_status(plugin_name, plugin_info, installed_plugins)
            
            print(f"  {status_info['status']} {plugin_name}")
            print(f"    Name: {plugin_info['name']}")
            print(f"    Description: {plugin_info['description']}")
            
            if status_info['deps_installed']:
                print(f"    Installed: {', '.join(status_info['deps_installed'][:2])}")
                if len(status_info['deps_installed']) > 2:
                    print(f"               (+{len(status_info['deps_installed']) - 2} more)")
            
            if status_info['deps_missing']:
                print(f"    Missing: {', '.join(status_info['deps_missing'])}")
            
            print()
    
    # Summary
    total_plugins = len(plugin_definitions)
    installed_count = sum(1 for p in plugin_definitions.keys() if p in installed_plugins)
    fully_working = sum(
        1 for plugin_name, plugin_info in plugin_definitions.items()
        if format_plugin_status(plugin_name, plugin_info, installed_plugins)["status"].startswith("✅")
    )
    
    print(f"📊 Summary: {fully_working}/{installed_count}/{total_plugins} (Working/Registered/Total)")
    print(f"   Use 'make install-plugin PLUGIN=<name>' to install plugins")
    print(f"   Use 'make remove-plugin PLUGIN=<name>' to remove plugins")

def print_installed_only():
    """Print only installed plugins."""
    plugin_definitions = get_plugin_definitions()
    installed_plugins = get_installed_plugins()
    
    if not installed_plugins:
        print("No plugins are currently registered as installed.")
        return
    
    print(f"\n🔌 Installed Plugins ({len(installed_plugins)} total)")
    print("=" * 50)
    
    for plugin_name in sorted(installed_plugins.keys()):
        if plugin_name in plugin_definitions:
            plugin_info = plugin_definitions[plugin_name]
            status_info = format_plugin_status(plugin_name, plugin_info, installed_plugins)
            
            print(f"  {status_info['status']} {plugin_name}")
            print(f"    {plugin_info['description']}")
            
            if status_info['deps_missing']:
                print(f"    ⚠️  Missing dependencies: {', '.join(status_info['deps_missing'])}")
            print()

def main():
    """Main entry point."""
    # Check if we're in the right directory
    project_root = get_project_root()
    if not (project_root / "pyproject.toml").exists():
        print("Error: Must be run from the project root directory")
        sys.exit(1)
    
    # Parse command line arguments
    show_all = True
    if len(sys.argv) > 1:
        if sys.argv[1] == "--installed":
            show_all = False
        elif sys.argv[1] == "--help":
            print("Usage: python list_plugins.py [--installed|--help]")
            print("  --installed  Show only installed plugins")
            print("  --help       Show this help message")
            return
    
    try:
        if show_all:
            print_plugin_table()
        else:
            print_installed_only()
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()