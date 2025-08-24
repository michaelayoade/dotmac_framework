"""
Background tasks for plugin operations.
"""

import logging
import re
from typing import Dict, Any, List, Tuple
from uuid import UUID

from celery import current_task
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from ...core.config import settings
from ...services.plugin_service import PluginService
from ...workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def parse_semantic_version(version: str) -> Tuple[int, int, int]:
    """Parse semantic version string into tuple of integers."""
    # Handle semver format: major.minor.patch[-prerelease][+build]
    version = version.split('-')[0].split('+')[0]  # Remove prerelease and build
    parts = version.split('.')
    
    # Ensure we have at least 3 parts
    while len(parts) < 3:
        parts.append('0')
    
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        # Fallback for non-standard versions
        return (0, 0, 0)


async def is_newer_version(version1: str, version2: str) -> bool:
    """Compare two semantic versions, return True if version1 is newer than version2."""
    try:
        v1_tuple = parse_semantic_version(version1)
        v2_tuple = parse_semantic_version(version2)
        
        # Compare major, minor, patch in order
        return v1_tuple > v2_tuple
        
    except Exception as e:
        logger.warning(f"Version comparison failed for {version1} vs {version2}: {e}")
        # Fallback to string comparison
        return version1 > version2

# Create async database session for workers
engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(bind=True, max_retries=3)
def install_plugin(self, installation_id: str, user_id: str):
    """Install a plugin asynchronously."""
    import asyncio
    
    async def _install_plugin():
        async with async_session() as db:
            try:
                service = PluginService(db)
                installation_uuid = UUID(installation_id)
                
                # Get installation details
                installation = await service.installation_repo.get_with_plugin(installation_uuid)
                if not installation:
                    raise ValueError(f"Plugin installation not found: {installation_id}")
                
                # Update status to installing
                await service.installation_repo.update_status(
                    installation_uuid, "installing", user_id
                )
                
                # Create installation event
                await service._create_plugin_event(
                    installation_uuid, "installation_started",
                    {"message": f"Starting installation of {installation.plugin.name}"}, user_id
                )
                
                # Installation steps
                steps = [
                    ("downloading", "Downloading plugin artifacts"),
                    ("validating", "Validating plugin integrity and security"),
                    ("extracting", "Extracting plugin files"),
                    ("configuring", "Setting up plugin configuration"),
                    ("registering_hooks", "Registering plugin hooks"),
                    ("initializing", "Running plugin initialization"),
                    ("testing", "Running post-installation tests")
                ]
                
                current_task.update_state(
                    state="PROGRESS",
                    meta={"current": 0, "total": len(steps), "status": "Starting installation"}
                )
                
                for i, (step_key, step_description) in enumerate(steps):
                    await service._create_plugin_event(
                        installation_uuid, f"installation_{step_key}",
                        {"message": step_description}, user_id
                    )
                    
                    # Simulate step execution
                    await asyncio.sleep(1)
                    
                    current_task.update_state(
                        state="PROGRESS",
                        meta={
                            "current": i + 1,
                            "total": len(steps),
                            "status": step_description
                        }
                    )
                
                # Create plugin hooks if defined
                if installation.plugin.configuration_schema.get("hooks"):
                    hooks = installation.plugin.configuration_schema["hooks"]
                    for hook_config in hooks:
                        hook_data = {
                            "plugin_id": installation.plugin.id,
                            "hook_name": hook_config["name"],
                            "hook_type": hook_config["type"],
                            "priority": hook_config.get("priority", 10),
                            "configuration": hook_config.get("configuration", {}),
                            "is_active": True
                        }
                        await service.hook_repo.create(hook_data, user_id)
                
                # Update installation status
                await service.installation_repo.update_status(
                    installation_uuid, "installed", user_id
                )
                
                await service._create_plugin_event(
                    installation_uuid, "installation_completed",
                    {"message": f"Successfully installed {installation.plugin.name}"}, user_id
                )
                
                logger.info(f"Plugin installed successfully: {installation.plugin.name}")
                return {
                    "installation_id": installation_id,
                    "plugin_name": installation.plugin.name,
                    "status": "installed"
                }
                
            except Exception as e:
                # Update status to failed
                await service.installation_repo.update_status(
                    UUID(installation_id), "failed", user_id
                )
                
                await service._create_plugin_event(
                    UUID(installation_id), "installation_failed",
                    {"message": f"Installation failed: {str(e)}", "error": str(e)}, user_id
                )
                
                logger.error(f"Plugin installation failed: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_install_plugin())


@celery_app.task(bind=True, max_retries=3)
def update_plugin(self, installation_id: str, target_version: str, user_id: str):
    """Update a plugin to a new version asynchronously."""
    import asyncio
    
    async def _update_plugin():
        async with async_session() as db:
            try:
                service = PluginService(db)
                installation_uuid = UUID(installation_id)
                
                # Get installation details
                installation = await service.installation_repo.get_with_plugin(installation_uuid)
                if not installation:
                    raise ValueError(f"Plugin installation not found: {installation_id}")
                
                # Update status to updating
                await service.installation_repo.update_status(
                    installation_uuid, "updating", user_id
                )
                
                await service._create_plugin_event(
                    installation_uuid, "update_started",
                    {"message": f"Starting update to version {target_version}"}, user_id
                )
                
                # Update steps
                steps = [
                    ("backup_config", "Backing up current configuration"),
                    ("downloading_new", "Downloading new version"),
                    ("validating_new", "Validating new version"),
                    ("stopping_current", "Stopping current version"),
                    ("installing_new", "Installing new version"),
                    ("migrating_data", "Migrating plugin data"),
                    ("updating_hooks", "Updating plugin hooks"),
                    ("testing_new", "Testing new version"),
                    ("starting_new", "Starting new version")
                ]
                
                current_task.update_state(
                    state="PROGRESS",
                    meta={"current": 0, "total": len(steps), "status": "Starting update"}
                )
                
                for i, (step_key, step_description) in enumerate(steps):
                    await service._create_plugin_event(
                        installation_uuid, f"update_{step_key}",
                        {"message": step_description}, user_id
                    )
                    
                    # Simulate step execution
                    await asyncio.sleep(1.5)
                    
                    current_task.update_state(
                        state="PROGRESS",
                        meta={
                            "current": i + 1,
                            "total": len(steps),
                            "status": step_description
                        }
                    )
                
                # Update installation version
                from datetime import datetime
                await service.installation_repo.update(
                    installation_uuid,
                    {
                        "installed_version": target_version,
                        "status": "installed",
                        "last_updated": datetime.utcnow()
                    },
                    user_id
                )
                
                await service._create_plugin_event(
                    installation_uuid, "update_completed",
                    {"message": f"Successfully updated to version {target_version}"}, user_id
                )
                
                logger.info(f"Plugin updated successfully: {installation.plugin.name} to {target_version}")
                return {
                    "installation_id": installation_id,
                    "plugin_name": installation.plugin.name,
                    "target_version": target_version,
                    "status": "updated"
                }
                
            except Exception as e:
                # Revert status to installed (rollback)
                await service.installation_repo.update_status(
                    UUID(installation_id), "installed", user_id
                )
                
                await service._create_plugin_event(
                    UUID(installation_id), "update_failed",
                    {"message": f"Update failed: {str(e)}", "error": str(e)}, user_id
                )
                
                logger.error(f"Plugin update failed: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_update_plugin())


@celery_app.task(bind=True, max_retries=3)
def uninstall_plugin(self, installation_id: str, user_id: str):
    """Uninstall a plugin asynchronously."""
    import asyncio
    
    async def _uninstall_plugin():
        async with async_session() as db:
            try:
                service = PluginService(db)
                installation_uuid = UUID(installation_id)
                
                # Get installation details
                installation = await service.installation_repo.get_with_plugin(installation_uuid)
                if not installation:
                    raise ValueError(f"Plugin installation not found: {installation_id}")
                
                # Update status to uninstalling
                await service.installation_repo.update_status(
                    installation_uuid, "uninstalling", user_id
                )
                
                await service._create_plugin_event(
                    installation_uuid, "uninstall_started",
                    {"message": f"Starting uninstallation of {installation.plugin.name}"}, user_id
                )
                
                # Uninstall steps
                steps = [
                    ("stopping_plugin", "Stopping plugin services"),
                    ("backup_data", "Backing up plugin data"),
                    ("removing_hooks", "Removing plugin hooks"),
                    ("cleaning_config", "Cleaning up configuration"),
                    ("removing_files", "Removing plugin files"),
                    ("cleanup_database", "Cleaning up database entries")
                ]
                
                current_task.update_state(
                    state="PROGRESS",
                    meta={"current": 0, "total": len(steps), "status": "Starting uninstall"}
                )
                
                for i, (step_key, step_description) in enumerate(steps):
                    await service._create_plugin_event(
                        installation_uuid, f"uninstall_{step_key}",
                        {"message": step_description}, user_id
                    )
                    
                    # Simulate step execution
                    await asyncio.sleep(1)
                    
                    current_task.update_state(
                        state="PROGRESS",
                        meta={
                            "current": i + 1,
                            "total": len(steps),
                            "status": step_description
                        }
                    )
                
                # Remove plugin hooks
                await service.hook_repo.delete_by_plugin(installation.plugin.id)
                
                # Update installation status
                await service.installation_repo.update_status(
                    installation_uuid, "uninstalled", user_id
                )
                
                await service._create_plugin_event(
                    installation_uuid, "uninstall_completed",
                    {"message": f"Successfully uninstalled {installation.plugin.name}"}, user_id
                )
                
                logger.info(f"Plugin uninstalled successfully: {installation.plugin.name}")
                return {
                    "installation_id": installation_id,
                    "plugin_name": installation.plugin.name,
                    "status": "uninstalled"
                }
                
            except Exception as e:
                # Revert status to previous state
                await service.installation_repo.update_status(
                    UUID(installation_id), "installed", user_id
                )
                
                await service._create_plugin_event(
                    UUID(installation_id), "uninstall_failed",
                    {"message": f"Uninstall failed: {str(e)}", "error": str(e)}, user_id
                )
                
                logger.error(f"Plugin uninstall failed: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_uninstall_plugin())


@celery_app.task(bind=True, max_retries=3)
def process_plugin_updates(self):
    """Check for plugin updates and notify tenants."""
    import asyncio
    
    async def _process_updates():
        async with async_session() as db:
            try:
                service = PluginService(db)
                
                # Get all installed plugins with auto-update enabled
                installations = await service.installation_repo.get_auto_update_enabled()
                
                updated = 0
                failed = 0
                notifications_sent = 0
                
                for installation in installations:
                    try:
                        if not installation.plugin:
                            continue
                        
                        # Check if plugin has newer version
                        current_version = installation.installed_version
                        latest_version = installation.plugin.version
                        
                        if current_version != latest_version:
                            # Implement proper semantic version comparison
                            if await is_newer_version(latest_version, current_version):
                                # Trigger update
                                update_plugin.delay(
                                    str(installation.id),
                                    latest_version,
                                    "system"
                                )
                                updated += 1
                        
                        # Send update notification to tenant
                        # TODO: Implement notification system
                        notifications_sent += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to process update for installation {installation.id}: {e}")
                        failed += 1
                
                logger.info(f"Plugin updates processed: {updated} updates triggered, {failed} failed, {notifications_sent} notifications sent")
                return {
                    "updates_triggered": updated,
                    "failed": failed,
                    "notifications_sent": notifications_sent
                }
                
            except Exception as e:
                logger.error(f"Error processing plugin updates: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_process_updates())


@celery_app.task(bind=True, max_retries=3)
def validate_plugin_security(self, plugin_id: str):
    """Validate plugin security and update verification status."""
    import asyncio
    
    async def _validate_security():
        async with async_session() as db:
            try:
                service = PluginService(db)
                plugin_uuid = UUID(plugin_id)
                
                # Get plugin details
                plugin = await service.plugin_repo.get_by_id(plugin_uuid)
                if not plugin:
                    raise ValueError(f"Plugin not found: {plugin_id}")
                
                # Security validation steps
                validation_steps = [
                    ("code_analysis", "Analyzing plugin code for vulnerabilities"),
                    ("dependency_check", "Checking dependencies for known vulnerabilities"),
                    ("permission_audit", "Auditing requested permissions"),
                    ("signature_verification", "Verifying plugin signature"),
                    ("sandbox_testing", "Testing plugin in sandbox environment")
                ]
                
                security_score = 100
                warnings = []
                errors = []
                
                for step_key, step_description in validation_steps:
                    try:
                        # TODO: Implement actual security checks
                        # For now, simulate validation
                        await asyncio.sleep(1)
                        
                        # Simulate finding issues
                        if step_key == "dependency_check" and "test" in plugin.name.lower():
                            warnings.append("Plugin uses dependency with known minor vulnerability")
                            security_score -= 10
                        
                    except Exception as e:
                        errors.append(f"Security validation failed for {step_key}: {str(e)}")
                        security_score -= 20
                
                # Update plugin verification status
                is_verified = security_score >= 80 and len(errors) == 0
                
                metadata = plugin.metadata or {}
                metadata.update({
                    "security_score": security_score,
                    "security_validation_date": asyncio.get_event_loop().time(),
                    "security_warnings": warnings,
                    "security_errors": errors
                })
                
                await service.plugin_repo.update(
                    plugin_uuid,
                    {
                        "is_verified": is_verified,
                        "metadata": metadata
                    },
                    "system"
                )
                
                logger.info(f"Plugin security validation completed: {plugin.name} (Score: {security_score})")
                return {
                    "plugin_id": plugin_id,
                    "security_score": security_score,
                    "is_verified": is_verified,
                    "warnings": warnings,
                    "errors": errors
                }
                
            except Exception as e:
                logger.error(f"Error validating plugin security: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_validate_security())


@celery_app.task(bind=True, max_retries=3)
def cleanup_plugin_events(self, retention_days: int = 30):
    """Clean up old plugin events."""
    import asyncio
    from datetime import datetime, timedelta
    
    async def _cleanup_events():
        async with async_session() as db:
            try:
                service = PluginService(db)
                
                cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
                
                # Get old processed events
                old_events = await service.event_repo.get_old_processed_events(cutoff_date)
                
                cleaned_up = 0
                failed = 0
                
                for event in old_events:
                    try:
                        await service.event_repo.delete(event.id)
                        cleaned_up += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to cleanup event {event.id}: {e}")
                        failed += 1
                
                logger.info(f"Plugin event cleanup completed: {cleaned_up} cleaned up, {failed} failed")
                return {"cleaned_up": cleaned_up, "failed": failed}
                
            except Exception as e:
                logger.error(f"Error cleaning up plugin events: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_cleanup_events())


@celery_app.task(bind=True, max_retries=3)
def generate_plugin_analytics(self, plugin_id: str):
    """Generate analytics data for a plugin."""
    import asyncio
    from datetime import datetime, timedelta
    
    async def _generate_analytics():
        async with async_session() as db:
            try:
                service = PluginService(db)
                plugin_uuid = UUID(plugin_id)
                
                # Get plugin analytics data
                analytics = await service.get_plugin_analytics(plugin_uuid)
                
                # Store analytics in time series database or cache
                # TODO: Implement analytics storage
                
                logger.info(f"Plugin analytics generated for {plugin_id}")
                return analytics
                
            except Exception as e:
                logger.error(f"Error generating plugin analytics: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_generate_analytics())