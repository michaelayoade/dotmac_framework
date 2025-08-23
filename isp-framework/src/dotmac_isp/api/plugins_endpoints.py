"""
Plugin Management API Endpoints

Provides REST API endpoints for managing third-party integration plugins
through the admin interface.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from dotmac_isp.shared.auth import get_current_admin_user
from dotmac_isp.plugins.core.manager import PluginManager, plugin_manager
from dotmac_isp.plugins.core.base import PluginConfig, PluginStatus, PluginCategory
from dotmac_isp.core.security_checker import security_check


router = APIRouter(prefix="/api/admin/plugins", tags=["Plugin Management"])


class PluginInfo(BaseModel):
    """Plugin information for API responses."""
    id: str
    name: str
    category: str
    description: str
    version: Optional[str] = None
    status: str
    dependencies: List[str]
    config_template: Optional[str] = None
    last_updated: Optional[str] = None
    installed: bool = False


class PluginInstallRequest(BaseModel):
    """Plugin installation request."""
    plugin_id: str = Field(..., description="Plugin ID to install")
    config_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Plugin configuration")
    tenant_id: Optional[UUID] = Field(None, description="Tenant-specific installation")


class PluginInstallResponse(BaseModel):
    """Plugin installation response."""
    plugin_id: str
    status: str
    message: str
    task_id: Optional[str] = None


class PluginConfigRequest(BaseModel):
    """Plugin configuration update request."""
    config_data: Dict[str, Any]
    enabled: bool = True


# Background task tracking
installation_tasks: Dict[str, Dict[str, Any]] = {}


def get_plugin_definitions() -> Dict[str, Dict[str, Any]]:
    """Get available plugin definitions."""
    # Import plugin definitions from the installation script
    scripts_dir = Path(__file__).parent.parent.parent.parent / "scripts"
    sys.path.insert(0, str(scripts_dir))
    
    try:
        import install_plugin
        return install_plugin.PLUGIN_DEFINITIONS
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not load plugin definitions: {e}"
        )
    finally:
        if str(scripts_dir) in sys.path:
            sys.path.remove(str(scripts_dir))


def get_installed_plugins() -> Dict[str, Dict[str, Any]]:
    """Get installed plugin metadata."""
    project_root = Path(__file__).parent.parent.parent.parent
    metadata_file = project_root / "src" / "dotmac_isp" / "plugins" / "registry" / "available_plugins.json"
    
    if not metadata_file.exists():
        return {}
    
    try:
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        return metadata.get("plugins", {})
    except Exception:
        return {}


@router.get("/", response_model=List[PluginInfo])
async def list_plugins(
    category: Optional[str] = None,
    status: Optional[str] = None,
    current_user = Depends(get_current_admin_user)
):
    """List available and installed plugins."""
    try:
        plugin_definitions = get_plugin_definitions()
        installed_plugins = get_installed_plugins()
        
        plugins = []
        for plugin_id, plugin_def in plugin_definitions.items():
            is_installed = plugin_id in installed_plugins
            
            # Get plugin status from plugin manager if installed
            plugin_status = "available"
            if is_installed:
                try:
                    manager_status = plugin_manager.get_plugin_status(plugin_id)
                    plugin_status = manager_status.value if manager_status else "installed"
                except:
                    plugin_status = "installed"
            
            plugin_info = PluginInfo(
                id=plugin_id,
                name=plugin_def["name"],
                category=plugin_def["category"],
                description=plugin_def["description"],
                status=plugin_status,
                dependencies=plugin_def["dependencies"],
                installed=is_installed,
                config_template=f"config/plugins/{plugin_id}.json.example" if is_installed else None
            )
            
            # Apply filters
            if category and plugin_info.category != category:
                continue
            if status and plugin_info.status != status:
                continue
                
            plugins.append(plugin_info)
        
        return plugins
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list plugins: {str(e)}"
        )


@router.get("/categories", response_model=Dict[str, Dict[str, Any]])
async def get_plugin_categories(
    current_user = Depends(get_current_admin_user)
):
    """Get available plugin categories with metadata."""
    return {
        "communication": {
            "name": "Communication",
            "icon": "📞",
            "description": "SMS, email, and messaging integrations"
        },
        "billing": {
            "name": "Billing & Payments",
            "icon": "💳",
            "description": "Payment processors and billing systems"
        },
        "network_automation": {
            "name": "Network Automation",
            "icon": "🔧",
            "description": "Network device management and automation"
        },
        "crm_integration": {
            "name": "CRM Integration",
            "icon": "👥",
            "description": "Customer relationship management systems"
        },
        "monitoring": {
            "name": "Monitoring",
            "icon": "📊",
            "description": "System and network monitoring tools"
        },
        "ticketing": {
            "name": "Support & Ticketing",
            "icon": "🎫",
            "description": "Support ticket and helpdesk systems"
        }
    }


@router.post("/install", response_model=PluginInstallResponse)
async def install_plugin(
    request: PluginInstallRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_admin_user)
):
    """Install a plugin with its dependencies."""
    plugin_definitions = get_plugin_definitions()
    
    if request.plugin_id not in plugin_definitions:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin '{request.plugin_id}' not found"
        )
    
    # Check if already installed
    installed_plugins = get_installed_plugins()
    if request.plugin_id in installed_plugins:
        raise HTTPException(
            status_code=409,
            detail=f"Plugin '{request.plugin_id}' is already installed"
        )
    
    # Security check for plugin installation
    await security_check(
        action="install_plugin",
        resource=f"plugin:{request.plugin_id}",
        user_id=current_user["id"]
    )
    
    # Generate task ID for tracking
    task_id = f"install_{request.plugin_id}_{id(request)}"
    
    # Start background installation
    background_tasks.add_task(
        install_plugin_background,
        task_id,
        request.plugin_id,
        request.config_data,
        request.tenant_id
    )
    
    return PluginInstallResponse(
        plugin_id=request.plugin_id,
        status="installing",
        message="Plugin installation started",
        task_id=task_id
    )


@router.delete("/{plugin_id}", response_model=Dict[str, str])
async def uninstall_plugin(
    plugin_id: str,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_admin_user)
):
    """Uninstall a plugin and its dependencies."""
    installed_plugins = get_installed_plugins()
    
    if plugin_id not in installed_plugins:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin '{plugin_id}' is not installed"
        )
    
    # Security check
    await security_check(
        action="uninstall_plugin",
        resource=f"plugin:{plugin_id}",
        user_id=current_user["id"]
    )
    
    # Stop plugin if active
    try:
        await plugin_manager.stop_plugin(plugin_id)
        await plugin_manager.uninstall_plugin(plugin_id)
    except Exception as e:
        # Continue with dependency removal even if plugin manager fails
        pass
    
    # Start background uninstallation
    task_id = f"uninstall_{plugin_id}_{id(background_tasks)}"
    background_tasks.add_task(
        uninstall_plugin_background,
        task_id,
        plugin_id
    )
    
    return {
        "plugin_id": plugin_id,
        "status": "uninstalling",
        "message": "Plugin uninstallation started",
        "task_id": task_id
    }


@router.get("/{plugin_id}/status", response_model=Dict[str, Any])
async def get_plugin_status(
    plugin_id: str,
    current_user = Depends(get_current_admin_user)
):
    """Get detailed plugin status and health."""
    try:
        # Get basic plugin info
        plugin_definitions = get_plugin_definitions()
        if plugin_id not in plugin_definitions:
            raise HTTPException(status_code=404, detail="Plugin not found")
        
        installed_plugins = get_installed_plugins()
        is_installed = plugin_id in installed_plugins
        
        status_info = {
            "plugin_id": plugin_id,
            "installed": is_installed,
            "status": "available"
        }
        
        if is_installed:
            try:
                # Get status from plugin manager
                manager_status = plugin_manager.get_plugin_status(plugin_id)
                status_info["status"] = manager_status.value if manager_status else "installed"
                
                # Get health check if plugin is active
                if manager_status == PluginStatus.ACTIVE:
                    health = await plugin_manager.get_plugin_health(plugin_id)
                    status_info["health"] = health
                    
                    # Get metrics
                    metrics = await plugin_manager.get_plugin_metrics(plugin_id)
                    status_info["metrics"] = metrics
                    
            except Exception as e:
                status_info["status"] = "error"
                status_info["error"] = str(e)
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get plugin status: {str(e)}"
        )


@router.put("/{plugin_id}/config", response_model=Dict[str, str])
async def update_plugin_config(
    plugin_id: str,
    request: PluginConfigRequest,
    current_user = Depends(get_current_admin_user)
):
    """Update plugin configuration."""
    installed_plugins = get_installed_plugins()
    
    if plugin_id not in installed_plugins:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin '{plugin_id}' is not installed"
        )
    
    try:
        # Create plugin configuration
        config = PluginConfig(
            enabled=request.enabled,
            config_data=request.config_data
        )
        
        # Update via plugin manager
        plugin_manager.configure_plugin(plugin_id, config)
        
        return {
            "plugin_id": plugin_id,
            "status": "configured",
            "message": "Plugin configuration updated successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update plugin configuration: {str(e)}"
        )


@router.post("/{plugin_id}/activate", response_model=Dict[str, str])
async def activate_plugin(
    plugin_id: str,
    current_user = Depends(get_current_admin_user)
):
    """Activate an installed plugin."""
    try:
        await plugin_manager.start_plugin(plugin_id)
        
        return {
            "plugin_id": plugin_id,
            "status": "active",
            "message": "Plugin activated successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to activate plugin: {str(e)}"
        )


@router.post("/{plugin_id}/deactivate", response_model=Dict[str, str])
async def deactivate_plugin(
    plugin_id: str,
    current_user = Depends(get_current_admin_user)
):
    """Deactivate an active plugin."""
    try:
        await plugin_manager.stop_plugin(plugin_id)
        
        return {
            "plugin_id": plugin_id,
            "status": "inactive",
            "message": "Plugin deactivated successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deactivate plugin: {str(e)}"
        )


@router.get("/tasks/{task_id}", response_model=Dict[str, Any])
async def get_installation_task_status(
    task_id: str,
    current_user = Depends(get_current_admin_user)
):
    """Get status of plugin installation/uninstallation task."""
    if task_id not in installation_tasks:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
    
    return installation_tasks[task_id]


# Background task functions

async def install_plugin_background(
    task_id: str,
    plugin_id: str,
    config_data: Dict[str, Any],
    tenant_id: Optional[UUID]
):
    """Background task for plugin installation."""
    installation_tasks[task_id] = {
        "task_id": task_id,
        "plugin_id": plugin_id,
        "status": "installing",
        "progress": 0,
        "message": "Starting installation..."
    }
    
    try:
        # Run installation script
        project_root = Path(__file__).parent.parent.parent.parent
        script_path = project_root / "scripts" / "install_plugin.py"
        
        # Update progress
        installation_tasks[task_id].update({
            "progress": 20,
            "message": "Installing dependencies..."
        })
        
        # Execute installation
        result = subprocess.run([
            sys.executable, str(script_path), plugin_id
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            installation_tasks[task_id].update({
                "progress": 80,
                "message": "Registering with plugin manager..."
            })
            
            # Register with plugin manager if config provided
            if config_data:
                try:
                    config = PluginConfig(
                        enabled=True,
                        config_data=config_data,
                        tenant_id=tenant_id
                    )
                    
                    await plugin_manager.install_plugin(
                        plugin_source=f"dotmac_isp.plugins.{plugin_id}",
                        config=config,
                        tenant_id=tenant_id
                    )
                except Exception as e:
                    # Plugin installed but not registered - partial success
                    pass
            
            installation_tasks[task_id].update({
                "status": "completed",
                "progress": 100,
                "message": "Plugin installed successfully!"
            })
        else:
            installation_tasks[task_id].update({
                "status": "error",
                "progress": 0,
                "message": f"Installation failed: {result.stderr or result.stdout}"
            })
    
    except Exception as e:
        installation_tasks[task_id].update({
            "status": "error",
            "progress": 0,
            "message": f"Installation failed: {str(e)}"
        })


async def uninstall_plugin_background(task_id: str, plugin_id: str):
    """Background task for plugin uninstallation."""
    installation_tasks[task_id] = {
        "task_id": task_id,
        "plugin_id": plugin_id,
        "status": "uninstalling",
        "progress": 0,
        "message": "Starting uninstallation..."
    }
    
    try:
        # Run uninstallation script
        project_root = Path(__file__).parent.parent.parent.parent
        script_path = project_root / "scripts" / "remove_plugin.py"
        
        installation_tasks[task_id].update({
            "progress": 50,
            "message": "Removing dependencies..."
        })
        
        result = subprocess.run([
            sys.executable, str(script_path), plugin_id
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            installation_tasks[task_id].update({
                "status": "completed",
                "progress": 100,
                "message": "Plugin uninstalled successfully!"
            })
        else:
            installation_tasks[task_id].update({
                "status": "error",
                "progress": 0,
                "message": f"Uninstallation failed: {result.stderr or result.stdout}"
            })
    
    except Exception as e:
        installation_tasks[task_id].update({
            "status": "error",
            "progress": 0,
            "message": f"Uninstallation failed: {str(e)}"
        })