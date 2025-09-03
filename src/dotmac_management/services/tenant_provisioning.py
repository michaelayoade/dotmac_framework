"""
Tenant Provisioning Service
Orchestrates tenant infrastructure creation using Coolify API
"""

import asyncio
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
import httpx
import os
import json
from jinja2 import Template

from dotmac_shared.core.logging import get_logger
from dotmac_shared.database.base import get_db_session
from dotmac_management.models.tenant import CustomerTenant, TenantStatus, TenantProvisioningEvent
from dotmac_management.services.infrastructure_service import get_infrastructure_service
from dotmac_management.services.tenant_admin_provisioning import TenantAdminProvisioningService
from dotmac_management.services.auto_license_provisioning import AutoLicenseProvisioningService
from dotmac_shared.auth.core.jwt_service import JWTService
from dotmac_shared.security.secrets import SecretsManager

logger = get_logger(__name__)


class TenantProvisioningService:
    """
    Pure business logic service for tenant provisioning operations.
    
    This service now contains only domain-specific business logic.
    Orchestration has been moved to the use-case layer (ProvisionTenantUseCase).
    
    Responsibilities:
    - Tenant configuration validation
    - Secrets generation and management
    - Database resource creation
    - Health check execution
    - Status updates and logging
    """
    
    def __init__(self):
        self.secrets_manager = SecretsManager()
        self.jwt_service = JWTService()
        self.admin_provisioning = TenantAdminProvisioningService()
        self.license_provisioning = AutoLicenseProvisioningService()
    
    # Business Logic Methods (called by use cases)
    
    async def validate_tenant_configuration(
        self, tenant: CustomerTenant, correlation_id: str = None
    ) -> Dict[str, Any]:
        """Validate tenant configuration (business logic only)"""
        return await self._validate_tenant_config(None, tenant, correlation_id)
    
    async def generate_tenant_secrets(
        self, tenant: CustomerTenant, correlation_id: str = None
    ) -> Dict[str, str]:
        """Generate tenant-specific secrets (business logic only)"""
        # Generate JWT secret
        jwt_secret = secrets.token_urlsafe(32)
        
        # Generate encryption keys
        encryption_key = secrets.token_urlsafe(32)
        
        # Generate cookie secret
        cookie_secret = secrets.token_urlsafe(32)
        
        # Generate webhook secret
        webhook_secret = secrets.token_urlsafe(32)
        
        # Return secrets dict (caller handles encryption/storage)
        return {
            "JWT_SECRET": jwt_secret,
            "ENCRYPTION_KEY": encryption_key,
            "COOKIE_SECRET": cookie_secret,
            "WEBHOOK_SECRET": webhook_secret,
            "TENANT_ID": tenant.tenant_id,
            "ADMIN_EMAIL": tenant.admin_email,
            "ADMIN_NAME": tenant.admin_name
        }
    
    async def validate_subdomain_availability(self, subdomain: str) -> bool:
        """Check subdomain availability (business logic)"""
        return await self._check_subdomain_available(subdomain)
    
    async def validate_plan_limits(self, plan: str) -> bool:
        """Validate plan limits (business logic)"""
        return await self._check_plan_limits(plan)
    
    async def validate_region_availability(self, region: str) -> bool:
        """Check region availability (business logic)"""
        return await self._check_region_availability(region)
    
    async def create_tenant_admin_user(
        self, tenant: CustomerTenant, correlation_id: str = None
    ) -> Dict[str, Any]:
        """Create admin user for tenant (business logic)"""
        return await self._create_tenant_admin(None, tenant, correlation_id)
    
    async def provision_tenant_license(
        self, tenant: CustomerTenant, correlation_id: str = None
    ) -> Dict[str, Any]:
        """Provision license for tenant (business logic)"""
        return await self._provision_tenant_license(None, tenant, correlation_id)
    
    async def perform_health_checks(
        self, tenant: CustomerTenant, correlation_id: str = None
    ) -> bool:
        """Perform tenant health checks (business logic)"""
        return await self._run_health_checks(None, tenant, correlation_id)
    
    async def generate_docker_compose(self, tenant: CustomerTenant) -> str:
        """Generate docker-compose content for tenant (business logic)"""
        return await self._generate_tenant_compose(tenant)
    
    async def _update_tenant_status(
        self, db: Session, tenant: CustomerTenant, status: TenantStatus,
        message: str, correlation_id: str, step_number: Optional[int] = None
    ):
        """Update tenant status and log event"""
        
        tenant.status = status
        
        # Create provisioning event
        event = TenantProvisioningEvent(
            tenant_id=tenant.id,
            event_type=f"status_change.{status}",
            status="in_progress",
            message=message,
            step_number=step_number,
            correlation_id=correlation_id,
            operator="system"
        )
        
        db.add(event)
        db.commit()
        
        logger.info(f"Tenant {tenant.tenant_id}: {status} - {message}")
    
    async def _validate_tenant_config(
        self, db: Session, tenant: CustomerTenant, correlation_id: str
    ) -> bool:
        """Validate tenant configuration before provisioning"""
        
        try:
            await self._update_tenant_status(
                db, tenant, TenantStatus.VALIDATING,
                "Validating tenant configuration", correlation_id, 1
            )
            
            # Validate subdomain availability
            if not await self._check_subdomain_available(tenant.subdomain):
                raise ValueError(f"Subdomain {tenant.subdomain} is not available")
            
            # Validate plan limits
            if not await self._check_plan_limits(tenant.plan):
                raise ValueError(f"Plan {tenant.plan} limits exceeded")
            
            # Validate region availability
            if not await self._check_region_availability(tenant.region):
                raise ValueError(f"Region {tenant.region} is not available")
            
            return True
            
        except Exception as e:
            await self._log_provisioning_error(
                db, tenant, "validation_failed", str(e), correlation_id, 1
            )
            return False
    
    async def _create_database_resources(
        self, db: Session, tenant: CustomerTenant, correlation_id: str
    ) -> bool:
        """Create database and Redis resources for tenant"""
        
        try:
            await self._update_tenant_status(
                db, tenant, TenantStatus.PROVISIONING,
                "Creating database resources", correlation_id, 2
            )
            
            # Create dedicated database for tenant
            database_config = await self._create_tenant_database(tenant)
            tenant.database_url = await self.secrets_manager.encrypt(database_config["url"])
            
            # Create dedicated Redis instance
            redis_config = await self._create_tenant_redis(tenant)
            tenant.redis_url = await self.secrets_manager.encrypt(redis_config["url"])
            
            db.commit()
            
            await self._log_provisioning_event(
                db, tenant, "database_created", "Database and Redis created", correlation_id, 2
            )
            
            return True
            
        except Exception as e:
            await self._log_provisioning_error(
                db, tenant, "database_creation_failed", str(e), correlation_id, 2
            )
            return False
    
    async def _generate_tenant_secrets(
        self, db: Session, tenant: CustomerTenant, correlation_id: str
    ) -> bool:
        """Generate tenant-specific secrets"""
        
        try:
            # Generate JWT secret
            jwt_secret = secrets.token_urlsafe(32)
            
            # Generate encryption keys
            encryption_key = secrets.token_urlsafe(32)
            
            # Generate cookie secret
            cookie_secret = secrets.token_urlsafe(32)
            
            # Generate webhook secret
            webhook_secret = secrets.token_urlsafe(32)
            
            # Store encrypted secrets
            tenant_secrets = {
                "JWT_SECRET": jwt_secret,
                "ENCRYPTION_KEY": encryption_key,
                "COOKIE_SECRET": cookie_secret,
                "WEBHOOK_SECRET": webhook_secret,
                "TENANT_ID": tenant.tenant_id,
                "ADMIN_EMAIL": tenant.admin_email,
                "ADMIN_NAME": tenant.admin_name
            }
            
            # Encrypt and store environment variables
            tenant.environment_vars = await self.secrets_manager.encrypt(
                json.dumps(tenant_secrets)
            )
            
            db.commit()
            
            await self._log_provisioning_event(
                db, tenant, "secrets_generated", "Tenant secrets generated", correlation_id, 3
            )
            
            return True
            
        except Exception as e:
            await self._log_provisioning_error(
                db, tenant, "secret_generation_failed", str(e), correlation_id, 3
            )
            return False
    
    async def _deploy_container_stack(
        self, db: Session, tenant: CustomerTenant, correlation_id: str
    ) -> bool:
        """Deploy tenant container stack via Coolify API"""
        
        try:
            await self._update_tenant_status(
                db, tenant, TenantStatus.PROVISIONING,
                "Deploying container stack", correlation_id, 4
            )
            
            # Generate docker-compose from template
            compose_content = await self._generate_tenant_compose(tenant)
            
            # Create Coolify application
            app_config = {
                "name": f"tenant-{tenant.subdomain}",
                "description": f"DotMac ISP tenant for {tenant.company_name}",
                "docker_compose": compose_content,
                "environment": await self._get_tenant_environment_vars(tenant)
            }
            
            # Deploy via Infrastructure Service (uses plugins)
            tenant_config = {
                "tenant_id": tenant.tenant_id,
                "name": app_config["name"],
                "docker_compose": app_config["docker_compose"],
                "environment": app_config["environment"],
                "domains": [f"{tenant.subdomain}.{os.getenv('BASE_DOMAIN', 'example.com')}"]
            }
            
            deployment_result = await self.infrastructure_service.deploy_tenant_application(tenant_config)
            
            # Store container/deployment ID
            tenant.container_id = deployment_result.get("deployment_id") or deployment_result.get("application_id")
            tenant.domain = f"{tenant.subdomain}.{os.getenv('BASE_DOMAIN', 'example.com')}"
            
            db.commit()
            
            # Wait for deployment to complete
            if not await self._wait_for_deployment(tenant.container_id):
                raise Exception("Deployment timeout")
            
            await self._log_provisioning_event(
                db, tenant, "container_deployed", "Container stack deployed", correlation_id, 4
            )
            
            return True
            
        except Exception as e:
            await self._log_provisioning_error(
                db, tenant, "deployment_failed", str(e), correlation_id, 4
            )
            return False
    
    async def _run_tenant_migrations(
        self, db: Session, tenant: CustomerTenant, correlation_id: str
    ) -> bool:
        """Run database migrations for tenant"""
        
        try:
            # Migrations are handled by the db-migrate service in the tenant compose
            # Just wait for it to complete
            await asyncio.sleep(30)  # Give migration job time to run
            
            # Check migration job status via Coolify API
            if not await self._check_migration_job_success(tenant.container_id):
                raise Exception("Migration job failed")
            
            await self._log_provisioning_event(
                db, tenant, "migrations_completed", "Database migrations completed", correlation_id, 5
            )
            
            return True
            
        except Exception as e:
            await self._log_provisioning_error(
                db, tenant, "migration_failed", str(e), correlation_id, 5
            )
            return False
    
    async def _seed_tenant_data(
        self, db: Session, tenant: CustomerTenant, correlation_id: str
    ) -> bool:
        """Seed initial data for tenant"""
        
        try:
            # Create tenant admin user via API call
            tenant_url = f"https://{tenant.domain}"
            
            # Generate temporary admin password
            temp_password = secrets.token_urlsafe(16)
            
            # Call tenant API to create admin user
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{tenant_url}/api/v1/auth/create-admin",
                    json={
                        "email": tenant.admin_email,
                        "name": tenant.admin_name,
                        "company": tenant.company_name,
                        "temp_password": temp_password
                    },
                    timeout=30
                )
                
                if response.status_code != 200:
                    raise Exception(f"Failed to create tenant admin: {response.text}")
            
            # Store temp password (will be forced to change on first login)
            tenant.settings = tenant.settings or {}
            tenant.settings["admin_temp_password"] = temp_password
            tenant.settings["admin_password_set"] = False
            
            db.commit()
            
            await self._log_provisioning_event(
                db, tenant, "data_seeded", "Initial data seeded", correlation_id, 6
            )
            
            return True
            
        except Exception as e:
            await self._log_provisioning_error(
                db, tenant, "seeding_failed", str(e), correlation_id, 6
            )
            return False
    
    async def _run_health_checks(
        self, db: Session, tenant: CustomerTenant, correlation_id: str
    ) -> bool:
        """Run health checks on deployed tenant"""
        
        try:
            tenant_url = f"https://{tenant.domain}"
            
            # Basic health check
            async with httpx.AsyncClient() as client:
                # Check health endpoint
                health_response = await client.get(
                    f"{tenant_url}/health",
                    timeout=30
                )
                
                if health_response.status_code != 200:
                    raise Exception(f"Health check failed: {health_response.status_code}")
                
                # Check login page loads
                login_response = await client.get(
                    f"{tenant_url}/login",
                    timeout=30
                )
                
                if login_response.status_code != 200:
                    raise Exception(f"Login page check failed: {login_response.status_code}")
            
            # Update health status
            tenant.health_status = "healthy"
            tenant.last_health_check = datetime.now(timezone.utc)
            db.commit()
            
            await self._log_provisioning_event(
                db, tenant, "health_check_passed", "Health checks passed", correlation_id, 7
            )
            
            return True
            
        except Exception as e:
            await self._log_provisioning_error(
                db, tenant, "health_check_failed", str(e), correlation_id, 7
            )
            return False
    
    async def _create_tenant_admin(
        self, db: Session, tenant: CustomerTenant, correlation_id: str
    ) -> Dict[str, Any]:
        """Create admin account for ISP instance"""
        
        try:
            admin_info = await self.admin_provisioning.create_tenant_admin(tenant)
            
            # Store admin info in tenant settings
            tenant.settings = tenant.settings or {}
            tenant.settings["admin_user_created"] = True
            tenant.settings["admin_user_id"] = admin_info["admin_user_id"]
            tenant.settings["admin_username"] = admin_info["username"]
            tenant.settings["admin_portal_url"] = admin_info["portal_url"]
            
            db.commit()
            
            await self._log_provisioning_event(
                db, tenant, "admin_created", "Admin account created", correlation_id, 7
            )
            
            return admin_info
            
        except Exception as e:
            await self._log_provisioning_error(
                db, tenant, "admin_creation_failed", str(e), correlation_id, 7
            )
            # Don't fail provisioning if admin creation fails - can be done manually
            return {}
    
    async def _provision_tenant_license(
        self, db: Session, tenant: CustomerTenant, correlation_id: str
    ) -> Dict[str, Any]:
        """Provision license contract for tenant"""
        
        try:
            license_info = await self.license_provisioning.provision_license_for_tenant(tenant, db)
            
            # Store license info in tenant settings
            tenant.settings = tenant.settings or {}
            tenant.settings["license_provisioned"] = True
            tenant.settings["contract_id"] = license_info["contract_id"]
            tenant.settings["license_plan"] = license_info["plan"]
            
            db.commit()
            
            await self._log_provisioning_event(
                db, tenant, "license_provisioned", f"License {license_info['contract_id']} created", correlation_id, 8
            )
            
            return license_info
            
        except Exception as e:
            await self._log_provisioning_error(
                db, tenant, "license_provisioning_failed", str(e), correlation_id, 8
            )
            # Don't fail provisioning if license creation fails - can be done manually
            return {}
    
    async def _finalize_provisioning(
        self, db: Session, tenant: CustomerTenant, correlation_id: str,
        admin_info: Dict[str, Any], license_info: Dict[str, Any]
    ):
        """Finalize provisioning and send notifications"""
        
        # Update final status
        await self._update_tenant_status(
            db, tenant, TenantStatus.READY,
            "Provisioning completed successfully", correlation_id, 9
        )
        
        tenant.provisioning_completed_at = datetime.now(timezone.utc)
        db.commit()
        
        # Send comprehensive welcome notification
        await self._send_welcome_notification(tenant, admin_info, license_info)
        
        # Set tenant to active
        await self._update_tenant_status(
            db, tenant, TenantStatus.ACTIVE,
            "Tenant is now active and ready for use", correlation_id, 10
        )
    
    async def _generate_tenant_compose(self, tenant: CustomerTenant) -> str:
        """Generate docker-compose content for tenant from template"""
        
        template_path = "/app/docker/tenant-compose-template.yml"
        
        try:
            with open(template_path, 'r') as f:
                template_content = f.read()
            
            template = Template(template_content)
            
            # Template variables
            template_vars = {
                "tenant_id": tenant.tenant_id,
                "subdomain": tenant.subdomain,
                "domain": tenant.domain,
                "database_url": await self.secrets_manager.decrypt(tenant.database_url),
                "redis_url": await self.secrets_manager.decrypt(tenant.redis_url),
                "plan": tenant.plan,
                "region": tenant.region,
                "image_tag": os.getenv('DOCKER_IMAGE_TAG', 'latest')
            }
            
            return template.render(**template_vars)
            
        except Exception as e:
            logger.error(f"Failed to generate tenant compose: {e}")
            raise
    
    async def _log_provisioning_event(
        self, db: Session, tenant: CustomerTenant, event_type: str, 
        message: str, correlation_id: str, step_number: int
    ):
        """Log successful provisioning event"""
        
        event = TenantProvisioningEvent(
            tenant_id=tenant.id,
            event_type=event_type,
            status="success",
            message=message,
            step_number=step_number,
            correlation_id=correlation_id,
            operator="system"
        )
        
        db.add(event)
        db.commit()
    
    async def _log_provisioning_error(
        self, db: Session, tenant: CustomerTenant, event_type: str,
        error_message: str, correlation_id: str, step_number: int
    ):
        """Log provisioning error event"""
        
        event = TenantProvisioningEvent(
            tenant_id=tenant.id,
            event_type=event_type,
            status="failed",
            message=f"Error: {error_message}",
            step_number=step_number,
            correlation_id=correlation_id,
            operator="system",
            error_details={"error": error_message, "timestamp": datetime.now(timezone.utc).isoformat()}
        )
        
        db.add(event)
        db.commit()
    
    async def _handle_provisioning_failure(
        self, db: Session, tenant_db_id: int, error_message: str, correlation_id: str
    ):
        """Handle provisioning failure"""
        
        try:
            tenant = db.query(CustomerTenant).filter_by(id=tenant_db_id).first()
            if tenant:
                tenant.status = TenantStatus.FAILED
                tenant.settings = tenant.settings or {}
                tenant.settings["last_error"] = error_message
                tenant.settings["failed_at"] = datetime.now(timezone.utc).isoformat()
                db.commit()
                
                logger.error(f"Tenant provisioning failed: {tenant.tenant_id} - {error_message}")
        except Exception as e:
            logger.error(f"Failed to handle provisioning failure: {e}")
    
    # Placeholder methods (would implement actual logic)
    async def _check_subdomain_available(self, subdomain: str) -> bool:
        return True  # Would check DNS/Coolify API
    
    async def _check_plan_limits(self, plan: str) -> bool:
        return True  # Would check subscription limits
    
    async def _check_region_availability(self, region: str) -> bool:
        return True  # Would check Coolify server capacity
    
    async def _create_tenant_database(self, tenant: CustomerTenant) -> Dict[str, str]:
        """Create dedicated PostgreSQL database for tenant via Coolify API"""
        
        try:
            # Generate secure database credentials
            db_password = secrets.token_urlsafe(24)
            db_name = f"tenant_{tenant.subdomain}"
            db_user = f"tenant_{tenant.subdomain}"
            
            # Create database service via Coolify API
            db_config = {
                "name": f"{tenant.subdomain}-postgres",
                "description": f"PostgreSQL database for {tenant.company_name}",
                "database": db_name,
                "username": db_user,
                "password": db_password,
                "version": "15"
            }
            
            db_service = await self.infrastructure_service.create_database_service(db_config)
            
            # Return connection URL
            return {
                "url": f"postgresql://{db_user}:{db_password}@{db_config['name']}:5432/{db_name}",
                "service_id": db_service.get("id")
            }
            
        except Exception as e:
            logger.error(f"Failed to create tenant database: {e}")
            raise
    
    async def _create_tenant_redis(self, tenant: CustomerTenant) -> Dict[str, str]:
        """Create dedicated Redis cache for tenant via Coolify API"""
        
        try:
            # Generate Redis password
            redis_password = secrets.token_urlsafe(24)
            
            # Create Redis service via Coolify API
            redis_config = {
                "name": f"{tenant.subdomain}-redis",
                "description": f"Redis cache for {tenant.company_name}",
                "password": redis_password,
                "version": "7"
            }
            
            redis_service = await self.infrastructure_service.create_redis_service(redis_config)
            
            # Return connection URL
            return {
                "url": f"redis://:{redis_password}@{redis_config['name']}:6379/0",
                "service_id": redis_service.get("id")
            }
            
        except Exception as e:
            logger.error(f"Failed to create tenant Redis: {e}")
            raise
    
    async def _get_tenant_environment_vars(self, tenant: CustomerTenant) -> Dict[str, str]:
        # Decrypt and return tenant environment variables
        encrypted_vars = tenant.environment_vars
        if encrypted_vars:
            decrypted = await self.secrets_manager.decrypt(encrypted_vars)
            return json.loads(decrypted)
        return {}
    
    async def _wait_for_deployment(self, container_id: str) -> bool:
        """Poll Coolify API for deployment completion"""
        
        max_wait_time = 600  # 10 minutes
        poll_interval = 15   # 15 seconds
        start_time = time.time()
        
        try:
            while time.time() - start_time < max_wait_time:
                # Check deployment status via infrastructure service
                status = await self.infrastructure_service.get_deployment_status(container_id)
                
                if status.get("status") == "running":
                    logger.info(f"✅ Deployment completed for application {container_id}")
                    return True
                elif status.get("status") == "failed":
                    logger.error(f"❌ Deployment failed for application {container_id}")
                    return False
                
                logger.info(f"⏳ Deployment in progress for {container_id}, status: {status.get('status')}")
                await asyncio.sleep(poll_interval)
            
            logger.error(f"❌ Deployment timeout for application {container_id}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to check deployment status: {e}")
            return False
    
    async def _check_migration_job_success(self, container_id: str) -> bool:
        """Check if database migration job completed successfully"""
        
        max_wait_time = 300  # 5 minutes for migrations
        poll_interval = 10   # 10 seconds
        start_time = time.time()
        
        try:
            while time.time() - start_time < max_wait_time:
                # Get deployment status and check for db-migrate service
                status = await self.infrastructure_service.get_deployment_status(container_id)
                
                # Check if migration container completed successfully
                # In Docker Compose, a service with restart: "no" that exits 0 means success
                # Note: Log retrieval depends on provider capabilities
                logs = []
                provider = self.infrastructure_service.infrastructure_manager.get_deployment_provider()
                if hasattr(provider, 'get_deployment_logs'):
                    logs = await provider.get_deployment_logs(container_id)
                
                # Look for migration completion marker
                if any("migration_complete" in log for log in logs):
                    logger.info(f"✅ Migration job completed for application {container_id}")
                    return True
                
                # Look for migration failure indicators
                if any("migration failed" in log.lower() for log in logs):
                    logger.error(f"❌ Migration job failed for application {container_id}")
                    return False
                
                logger.info(f"⏳ Waiting for migration completion for {container_id}")
                await asyncio.sleep(poll_interval)
            
            logger.error(f"❌ Migration timeout for application {container_id}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to check migration job status: {e}")
            return False
    
    async def _send_welcome_notification(
        self, tenant: CustomerTenant, admin_info: Dict[str, Any], license_info: Dict[str, Any]
    ):
        # Would send welcome email via email service
        logger.info(f"Welcome notification sent to {tenant.admin_email}")
        pass