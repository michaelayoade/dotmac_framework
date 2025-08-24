#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)

"""
Plugin Removal Script

This script handles the removal of third-party integration plugins
by uninstalling their dependencies and unregistering them from the plugin system.
"""

import subprocess
import sys
import json
import os
from pathlib import Path

def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent

def get_plugin_definitions():
    """Get plugin definitions from install_plugin.py."""
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
logger.warning(f"Warning: Could not read plugin metadata: {e}")
        return {}

def check_dependency_conflicts(plugin_name, plugin_definitions, installed_plugins):
    """Check if removing this plugin would break other plugins."""
    if plugin_name not in plugin_definitions:
        return []
    
    plugin_deps = set(plugin_definitions[plugin_name]["dependencies"])
    conflicts = []
    
    for other_plugin, other_info in installed_plugins.items():
        if other_plugin == plugin_name:
            continue
        
        if other_plugin in plugin_definitions:
            other_deps = set(plugin_definitions[other_plugin]["dependencies"])
            shared_deps = plugin_deps.intersection(other_deps)
            if shared_deps:
                conflicts.append({
                    "plugin": other_plugin,
                    "shared_dependencies": list(shared_deps)
                })
    
    return conflicts

def uninstall_dependencies(dependencies, conflicts):
    """Uninstall plugin dependencies, considering conflicts."""
    if conflicts:
logger.info("⚠️  Dependency conflicts detected:")
        for conflict in conflicts:
logger.info(f"   - {conflict['plugin']} also uses: {', '.join(conflict['shared_dependencies'])}")
        
        response = input("\nProceed with removal anyway? Dependencies will remain installed. (y/N): ")
        if response.lower() not in ['y', 'yes']:
logger.info("Removal cancelled.")
            return False
        
logger.info("Keeping shared dependencies installed due to conflicts.")
        return True
    
    # No conflicts, safe to uninstall
logger.info(f"Uninstalling dependencies: {', '.join(dependencies)}")
    try:
        # Extract package names without version specifiers
        package_names = []
        for dep in dependencies:
            clean_name = dep.split(">=")[0].split("==")[0].split("<")[0]
            package_names.append(clean_name)
        
        subprocess.check_call([
            sys.executable, "-m", "pip", "uninstall", "-y"
        ] + package_names)
        return True
    except subprocess.CalledProcessError as e:
logger.warning(f"Warning: Could not uninstall some dependencies: {e}")
logger.info("You may need to manually uninstall them.")
        return True  # Don't fail removal for this

def remove_plugin_config(plugin_name):
    """Remove plugin configuration files."""
    config_dir = get_project_root() / "config" / "plugins"
    
    files_removed = []
    for pattern in [f"{plugin_name}.json", f"{plugin_name}.json.example"]:
        config_file = config_dir / pattern
        if config_file.exists():
            try:
                config_file.unlink()
                files_removed.append(str(config_file))
            except Exception as e:
logger.warning(f"Warning: Could not remove {config_file}: {e}")
    
    if files_removed:
logger.info(f"Removed configuration files: {', '.join(files_removed)}")

def unregister_plugin_metadata(plugin_name):
    """Unregister plugin metadata."""
    metadata_file = (
        get_project_root() / "src" / "dotmac_isp" / "plugins" / "registry" / "available_plugins.json"
    )
    
    if not metadata_file.exists():
        return
    
    try:
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        if plugin_name in metadata.get("plugins", {}):
            del metadata["plugins"][plugin_name]
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
logger.info(f"Plugin metadata unregistered from: {metadata_file}")
        
    except Exception as e:
logger.warning(f"Warning: Could not update plugin metadata: {e}")

def remove_plugin(plugin_name):
    """Remove a specific plugin."""
    plugin_definitions = get_plugin_definitions()
    installed_plugins = get_installed_plugins()
    
    if plugin_name not in installed_plugins:
logger.info(f"Plugin '{plugin_name}' is not installed.")
        if plugin_name in plugin_definitions:
logger.info(f"Plugin '{plugin_name}' is available but not installed.")
logger.info("Use 'make list-plugins' to see installed plugins.")
        else:
logger.info(f"Unknown plugin: {plugin_name}")
logger.info(f"Available plugins: {', '.join(plugin_definitions.keys())}")
        return False
    
    plugin_info = plugin_definitions.get(plugin_name, {})
logger.info(f"\nRemoving {plugin_info.get('name', plugin_name)}...")
    
    # Check for dependency conflicts
    conflicts = check_dependency_conflicts(plugin_name, plugin_definitions, installed_plugins)
    
    # Remove dependencies
    dependencies = plugin_info.get("dependencies", [])
    if dependencies:
        if not uninstall_dependencies(dependencies, conflicts):
            return False
    
    # Remove configuration files
    remove_plugin_config(plugin_name)
    
    # Unregister plugin metadata
    unregister_plugin_metadata(plugin_name)
    
logger.info(f"\n✅ {plugin_info.get('name', plugin_name)} removed successfully!")
    
    if conflicts:
logger.info(f"\nNote: Some dependencies were kept due to conflicts with:")
        for conflict in conflicts:
logger.info(f"  - {conflict['plugin']}")
    
logger.info(f"\nNext steps:")
logger.info(f"1. Restart any running services that were using this plugin")
logger.info(f"2. Remove any plugin-specific configuration from your secrets/vault")
logger.info(f"3. Update any code that was directly calling this plugin")
    
    return True

def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        plugin_definitions = get_plugin_definitions()
        installed_plugins = get_installed_plugins()
        
logger.info("Usage: python remove_plugin.py <plugin_name>")
        
        if installed_plugins:
logger.info(f"\nInstalled plugins: {', '.join(installed_plugins.keys())}")
        else:
logger.info("\nNo plugins are currently installed.")
        
logger.info(f"Available plugins: {', '.join(plugin_definitions.keys())}")
        sys.exit(1)
    
    plugin_name = sys.argv[1].lower()
    
    # Check if we're in the right directory
    project_root = get_project_root()
    if not (project_root / "pyproject.toml").exists():
logger.error("Error: Must be run from the project root directory")
        sys.exit(1)
    
    success = remove_plugin(plugin_name)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()