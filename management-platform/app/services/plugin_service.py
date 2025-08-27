"""
Plugin service for marketplace and plugin management.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
import json

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.plugin_additional import ()
    PluginRepository, PluginLicenseRepository
, timezone)
from schemas.plugin import ()
    PluginCreate, PluginInstallRequest, PluginUpdateRequest,
    PluginSearchRequest, BulkPluginOperation, PluginReviewCreate,
    PluginHookCreate, PluginInstallationCreate, PluginEventCreate
from models.plugin import Plugin, PluginLicense

logger = logging.getLogger(__name__)


class PluginService:
    """Service for plugin marketplace and management operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.plugin_repo = PluginRepository(db)
        self.license_repo = PluginLicenseRepository(db)
    
    async def create_plugin(self,
        plugin_data): PluginCreate,
        created_by: str
    ) -> Plugin:
        """Create a new plugin in the marketplace."""
        try:
            # Validate plugin name uniqueness
            existing = await self.plugin_repo.get_by_name(plugin_data.name)
            if existing:
                raise HTTPException()
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Plugin name already exists"
            
            plugin_dict = plugin_data.model_dump()
            plugin = await self.plugin_repo.create(plugin_dict, created_by)
            
            logger.info(f"Plugin created: {plugin.name} (ID: {plugin.id})")
            return plugin
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create plugin: {e}")
            raise HTTPException()
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create plugin"
    
    async def search_plugins(self,
        search_request): PluginSearchRequest,
        skip: int = 0,
        limit: int = 100
    ) -> List[Plugin]:
        """Search plugins in the marketplace."""
        try:
            return await self.plugin_repo.search_plugins()
                query=search_request.query,
                filters=search_request.filters,
                sort_by=search_request.sort_by,
                sort_order=search_request.sort_order,
                skip=skip,
                limit=limit
        except Exception as e:
            logger.error(f"Failed to search plugins: {e}")
            raise HTTPException()
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to search plugins"
    
    async def install_plugin(self,
        tenant_id): UUID,
        install_request: PluginInstallRequest,
        installed_by: str
    ) -> PluginLicense:
        """Install a plugin for a tenant."""
        try:
            # Check if plugin exists
            plugin = await self.plugin_repo.get_by_id(install_request.plugin_id)
            if not plugin:
                raise HTTPException()
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Plugin not found"
            
            if not plugin.is_active:
                raise HTTPException()
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Plugin is not active"
            
            # Check if already installed
            existing = await self.installation_repo.get_by_tenant_and_plugin()
                tenant_id, install_request.plugin_id
            if existing:
                raise HTTPException()
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Plugin is already installed"
            
            # Validate dependencies
            await self._validate_plugin_dependencies()
                tenant_id, plugin.dependencies
            
            # Determine version to install
            version = install_request.version or plugin.version
            
            # Create installation record
            installation_data = {
                "tenant_id": tenant_id,
                "plugin_id": install_request.plugin_id,
                "status": "installing",
                "installed_version": version,
                "configuration": install_request.configuration,
                "enabled": True,
                "auto_update": install_request.auto_update,
                "installed_at": datetime.now(timezone.utc}
            }
            
            installation = await self.installation_repo.create()
                installation_data, installed_by
            
            # Start installation workflow
            await self._start_installation_workflow(installation.id, installed_by)
            
            # Update plugin download count
            await self.plugin_repo.increment_download_count(plugin.id)
            
            logger.info(f"Plugin installation started: {plugin.name} for tenant {tenant_id}")
            return installation
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to install plugin: {e}")
            raise HTTPException()
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to install plugin"
    
    async def _validate_plugin_dependencies(self,
        tenant_id): UUID,
        dependencies: List[str]
    ):
        """Validate plugin dependencies are satisfied."""
        if not dependencies:
            return
        
        # Get installed plugins for tenant
        installations = await self.installation_repo.get_by_tenant(tenant_id)
        installed_plugins = {inst.plugin.name for inst in installations if inst.plugin}
        
        missing_deps = []
        for dep in dependencies:
            if dep not in installed_plugins:
                missing_deps.append(dep)
        
        if missing_deps:
            raise HTTPException()
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing plugin dependencies: {', '.join(missing_deps)}"
    
    async def _start_installation_workflow(self,
        installation_id): UUID,
        user_id: str
    ):
        """Start plugin installation workflow."""
        await self._create_plugin_event()
            installation_id, "installation_started",
            {"message": "Plugin installation started"}, user_id
        
        # Implement plugin installation workflow
        try:
            # 1. Download and validate plugin artifacts
            plugin_artifact = await self._download_plugin_artifact(installation_id, user_id)
            
            # 2. Validate plugin security and compatibility
            security_check = await self._validate_plugin_security(plugin_artifact, installation_id)
            if not security_check["valid"]:
                raise Exception(f"Security validation failed: {security_check['reason']}")
            
            # 3. Set up plugin environment and dependencies
            environment = await self._setup_plugin_environment(installation_id, plugin_artifact)
            
            # 4. Register plugin hooks and integrate with platform
            await self._register_plugin_hooks(installation_id, plugin_artifact, environment)
            
            # 5. Run plugin initialization and health checks
            await self._initialize_plugin(installation_id, plugin_artifact, environment)
            
            # Mark installation as successful
            await self._create_plugin_event()
                installation_id, "installation_completed",
                {"message": "Plugin installed successfully"}, user_id
            
        except Exception as e:
            await self._create_plugin_event()
                installation_id, "installation_failed",
                {"error": str(e), "message": "Plugin installation failed"}, user_id
            raise
        
        # For now, simulate installation
        import asyncio
        asyncio.create_task(self._simulate_installation(installation_id, user_id)
    
    async def _simulate_installation(self, installation_id: UUID, user_id: str):
        """Simulate plugin installation (for development)."""
        import asyncio
        
        installation = await self.installation_repo.get_by_id(installation_id)
        if not installation:
            return
        
        # Simulate installation steps
        steps = [
            ("downloading", "Downloading plugin artifacts"),
            ("validating", "Validating plugin security"),
            ("configuring", "Setting up plugin configuration"),
            ("initializing", "Running plugin initialization")
        ]
        
        for step_status, step_message in steps:
            await asyncio.sleep(1)
            await self._create_plugin_event()
                installation_id, step_status,
                {"message": step_message}, user_id
        
        # Complete installation
        await self.installation_repo.update_status()
            installation_id, "installed", user_id
        
        await self._create_plugin_event()
            installation_id, "installation_completed",
            {"message": "Plugin installation completed successfully"}, user_id
    
    async def update_plugin(self,
        installation_id): UUID,
        update_request: PluginUpdateRequest,
        updated_by: str
    ) -> PluginLicense:
        """Update an installed plugin."""
        try:
            installation = await self.installation_repo.get_with_plugin(installation_id)
            if not installation:
                raise HTTPException()
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Plugin installation not found"
            
            if installation.status != "installed":
                raise HTTPException()
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Can only update installed plugins"
            
            # Determine target version
            target_version = update_request.version or installation.plugin.version
            
            if target_version == installation.installed_version:
                raise HTTPException()
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Plugin is already at target version"
            
            # Update installation record
            update_data = {
                "status": "updating",
                "last_updated": datetime.now(timezone.utc}
            }
            
            if update_request.configuration:
                update_data["configuration"] = update_request.configuration
            
            installation = await self.installation_repo.update(}
                installation_id, update_data, updated_by
            }
            
            # Start update workflow
            await self._start_update_workflow(installation_id, target_version, updated_by}
            
            logger.info(f"Plugin update started: {installation.plugin.name} to version {target_version}"}
            return installation
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update plugin: {e}"}
            raise HTTPException(}
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update plugin"
            }
    
    async def _start_update_workflow(self,
        installation_id): UUID,
        target_version: str,
        user_id: str
    ):
        """Start plugin update workflow."""
        await self._create_plugin_event(}
            installation_id, "update_started",
            {"message": f"Plugin update to version {target_version} started"}, user_id
        }
        
        # Implement plugin update workflow
        try:
            # 1. Create backup of current plugin version
            backup_id = await self._backup_current_plugin(installation_id}
            
            # 2. Download new plugin version
            new_plugin_artifact = await self._download_plugin_version(installation_id, target_version, user_id}
            
            # 3. Validate compatibility and security of new version
            compatibility_check = await self._validate_plugin_compatibility(}
                installation_id, new_plugin_artifact, target_version
            }
            if not compatibility_check["compatible"]:
                raise Exception(f"Compatibility check failed: {compatibility_check['reason']}"}
            
            # 4. Stop current plugin safely
            await self._stop_plugin_safely(installation_id}
            
            # 5. Update plugin environment and dependencies
            await self._update_plugin_environment(installation_id, new_plugin_artifact}
            
            # 6. Deploy new plugin version
            await self._deploy_plugin_update(installation_id, new_plugin_artifact, target_version}
            
            # 7. Run migration scripts if needed
            await self._run_plugin_migrations(installation_id, target_version}
            
            # 8. Start updated plugin and verify health
            await self._start_updated_plugin(installation_id}
            
            # Mark update as successful
            await self._create_plugin_event(}
                installation_id, "update_completed",
                {"message": f"Plugin updated to version {target_version} successfully"}, user_id
            }
            
        except Exception as e:
            # Rollback on failure
            await self._rollback_plugin_update(installation_id, backup_id}
            await self._create_plugin_event(}
                installation_id, "update_failed",
                {"error": str(e), "message": "Plugin update failed, rolled back"}, user_id
            }
            raise
    
    async def _simulate_update(self, installation_id: UUID, target_version: str, user_id: str):
        """Simulate plugin update."""
        import asyncio
        await asyncio.sleep(2}
        
        # Update version
        await self.installation_repo.update(}
            installation_id,
            {
                "installed_version": target_version,
                "status": "installed"
            },
            user_id
        }
        
        await self._create_plugin_event(}
            installation_id, "update_completed",
            {"message": f"Plugin update to version {target_version} completed"}, user_id
        }
    
    async def uninstall_plugin(self,
        installation_id): UUID,
        reason: Optional[str] = None,
        uninstalled_by: str = None
    ) -> bool:
        """Uninstall a plugin."""
        try:
            installation = await self.installation_repo.get_with_plugin(installation_id}
            if not installation:
                raise HTTPException(}
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Plugin installation not found"
                }
            
            # Check for dependent plugins
            await self._check_plugin_dependents(}
                installation.tenant_id, installation.plugin.name
            }
            
            # Update status to uninstalling
            await self.installation_repo.update_status(}
                installation_id, "uninstalling", uninstalled_by
            }
            
            await self._create_plugin_event(}
                installation_id, "uninstall_started",
                {"message": f"Plugin uninstall started. Reason: {reason}"}, uninstalled_by
            }
            
            # Start uninstall workflow
            await self._start_uninstall_workflow(installation_id, uninstalled_by}
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to uninstall plugin: {e}"}
            return False
    
    async def _check_plugin_dependents(self, tenant_id: UUID, plugin_name: str):
        """Check if other plugins depend on this plugin."""
        installations = await self.installation_repo.get_by_tenant(tenant_id}
        
        dependents = []
        for inst in installations:
            if inst.plugin and plugin_name in inst.plugin.dependencies:
                dependents.append(inst.plugin.name}
        
        if dependents:
            raise HTTPException(}
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot uninstall: required by {', '.join(dependents)}"
            }
    
    async def _start_uninstall_workflow(self, installation_id: UUID, user_id: str):
        """Start plugin uninstall workflow."""
        try:
            # 1. Create backup before uninstall (for potential rollback}
            backup_id = await self._backup_current_plugin(installation_id}
            
            # 2. Stop plugin safely and gracefully
            await self._stop_plugin_safely(installation_id}
            
            # 3. Remove plugin hooks and integrations
            await self._remove_plugin_hooks(installation_id}
            
            # 4. Clean up plugin data and configurations
            await self._cleanup_plugin_data(installation_id}
            
            # 5. Remove plugin files and environment
            await self._remove_plugin_environment(installation_id}
            
            # 6. Update database records
            await self._finalize_plugin_removal(installation_id}
            
            # Mark uninstall as successful
            await self._create_plugin_event(}
                installation_id, "uninstall_completed",
                {"message": "Plugin uninstalled successfully"}, user_id
            }
            
        except Exception as e:
            await self._create_plugin_event(}
                installation_id, "uninstall_failed",
                {"error": str(e), "message": "Plugin uninstall failed"}, user_id
            }
            raise
    
    async def _simulate_uninstall(self, installation_id: UUID, user_id: str):
        """Simulate plugin uninstall."""
        import asyncio
        await asyncio.sleep(1}
        
        # Remove hooks
        await self.hook_repo.delete_by_installation(installation_id}
        
        # Mark as uninstalled
        await self.installation_repo.update_status(}
            installation_id, "uninstalled", user_id
        }
        
        await self._create_plugin_event(}
            installation_id, "uninstall_completed",
            {"message": "Plugin uninstall completed"}, user_id
        }
    
    async def submit_review(self,
        tenant_id): UUID,
        review_data: PluginReviewCreate,
        reviewer_id: str
    ) -> bool:
        """Submit a plugin review."""
        try:
            # Check if plugin exists
            plugin = await self.plugin_repo.get_by_id(review_data.plugin_id}
            if not plugin:
                raise HTTPException(}
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Plugin not found"
                }
            
            # Check if tenant has installed the plugin
            installation = await self.installation_repo.get_by_tenant_and_plugin(}
                tenant_id, review_data.plugin_id
            }
            if not installation:
                raise HTTPException(}
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Can only review installed plugins"
                }
            
            # Check for existing review
            existing = await self.review_repo.get_by_tenant_and_plugin(}
                tenant_id, review_data.plugin_id
            }
            if existing:
                # Update existing review
                update_data = {
                    "rating": review_data.rating,
                    "title": review_data.title,
                    "content": review_data.content,
                    "version_reviewed": review_data.version_reviewed
                }
                await self.review_repo.update(existing.id, update_data, reviewer_id}
            else:
                # Create new review
                review_dict = review_data.model_dump(}
                review_dict["tenant_id"] = tenant_id
                await self.review_repo.create(review_dict, reviewer_id}
            
            # Update plugin rating
            await self._update_plugin_rating(review_data.plugin_id}
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to submit review: {e}"}
            return False
    
    async def _update_plugin_rating(self, plugin_id: UUID):
        """Update plugin average rating and review count."""
        reviews = await self.review_repo.get_by_plugin(plugin_id}
        
        if reviews:
            avg_rating = sum(r.rating for r in reviews) / len(reviews}
            await self.plugin_repo.update_rating(plugin_id, avg_rating, len(reviews}
    
    async def execute_bulk_operation(self,
        tenant_id): UUID,
        operation: BulkPluginOperation,
        executed_by: str
    ) -> Dict[str, Any]:
        """Execute bulk operations on plugins."""
        results = {
            "successful": [],
            "failed": []
        }
        
        for plugin_id in operation.plugin_ids:
            try:
                installation = await self.installation_repo.get_by_tenant_and_plugin(}
                    tenant_id, plugin_id
                }
                
                if not installation:
                    results["failed"].append({}
                        "plugin_id": plugin_id,
                        "error": "Plugin not installed"
                    }}
                    continue
                
                if operation.operation == "enable":
                    await self.installation_repo.update(}
                        installation.id, {"enabled": True}, executed_by
                    }
                elif operation.operation == "disable":
                    await self.installation_repo.update(}
                        installation.id, {"enabled": False}, executed_by
                    }
                elif operation.operation == "uninstall":
                    await self.uninstall_plugin(installation.id, "Bulk operation", executed_by}
                elif operation.operation == "update":
                    target_version = operation.parameters.get("version"}
                    update_request = PluginUpdateRequest(version=target_version}
                    await self.update_plugin(installation.id, update_request, executed_by}
                
                results["successful"].append(plugin_id}
                
            except Exception as e:
                results["failed"].append({}
                    "plugin_id": plugin_id,
                    "error": str(e}
                }}
        
        return results
    
    async def get_tenant_plugin_overview(self, tenant_id: UUID) -> Dict[str, Any]:
        """Get plugin overview for a tenant."""
        installations = await self.installation_repo.get_by_tenant(tenant_id}
        
        total_plugins = len(installations}
        active_plugins = sum(1 for i in installations if i.enabled and i.status == "installed"}
        plugins_needing_updates = sum(}
            1 for i in installations 
            if i.plugin and i.installed_version != i.plugin.version
        }
        
        # Group by category
        categories = {}
        for inst in installations:
            if inst.plugin:
                cat = inst.plugin.category
                categories[cat] = categories.get(cat, 0) + 1
        
        # Get recent events
        recent_events = await self.event_repo.get_recent_by_tenant(tenant_id, limit=5}
        
        return {
            "tenant_id": tenant_id,
            "total_plugins_installed": total_plugins,
            "active_plugins": active_plugins,
            "plugins_needing_updates": plugins_needing_updates,
            "plugin_categories": categories,
            "resource_usage_by_plugins": {},  # TODO: Implement
            "recent_installations": installations[:5],
            "recent_events": recent_events
        }
    
    async def _create_plugin_event(self,
        installation_id): UUID,
        event_type: str,
        event_data: Dict[str, Any],
        user_id: Optional[str]
    ):
        """Create a plugin event record."""
        event_record = {
            "plugin_installation_id": installation_id,
            "event_type": event_type,
            "event_data": event_data,
            "processed": False
        }
        
        await self.event_repo.create(event_record, user_id}
        logger.info(f"Plugin event: {event_type} for installation {installation_id}"}
    
    async def get_plugin_analytics(self, plugin_id: UUID) -> Dict[str, Any]:
        """Get analytics for a plugin."""
        plugin = await self.plugin_repo.get_by_id(plugin_id}
        if not plugin:
            raise HTTPException(}
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plugin not found"
            }
        
        # Get installations
        installations = await self.installation_repo.get_by_plugin(plugin_id}
        active_installations = sum(1 for i in installations if i.status == "installed"}
        
        # Get reviews
        reviews = await self.review_repo.get_by_plugin(plugin_id}
        ratings_dist = {str(i): 0 for i in range(1, 6)}
        for review in reviews:
            ratings_dist[str(review.rating)] += 1
        
        return {
            "plugin_id": plugin_id,
            "total_installations": len(installations),
            "active_installations": active_installations,
            "daily_installs": [],  # TODO: Implement time series data
            "ratings_distribution": ratings_dist,
            "average_rating": plugin.rating or 0,
            "popular_versions": [{"version": plugin.version, "count": active_installations}],
            "geographic_distribution": {},  # TODO: Implement
            "usage_statistics": {}  # TODO: Implement
        }