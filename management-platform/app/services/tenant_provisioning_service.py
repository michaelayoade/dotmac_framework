"""
Tenant Provisioning Service for Container-per-Tenant Architecture

This service handles the complete lifecycle of tenant provisioning:
1. Database schema isolation per tenant
2. Redis namespace allocation
3. Container deployment with tenant-specific configuration
4. Health validation and monitoring setup
"""

import asyncio
import hashlib
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import asyncpg
from sqlalchemy import text
from redis.asyncio import Redis

from app.core.database import get_database
from app.core.cache import get_redis
from app.models.tenant import TenantModel
from app.schemas.tenant import TenantCreate, TenantResponse

logger = logging.getLogger(__name__)


@dataclass
class TenantResources:
    """Resources allocated to a tenant."""
    tenant_id: str
    database_schema: str
    database_url: str
    redis_db: int
    redis_namespace: str
    vault_path: str
    container_config: Dict[str, Any]


class TenantProvisioningError(Exception):
    """Raised when tenant provisioning fails."""
    pass


class TenantProvisioningService:
    """Service for provisioning tenant resources and containers."""
    
    def __init__(self):
        self.redis_db_allocator = {}  # Track allocated Redis DBs
        
    async def provision_tenant(self, tenant_data: TenantCreate) -> TenantResponse:
        """
        Provision a complete tenant with isolated resources.
        
        Args:
            tenant_data: Tenant configuration data
            
        Returns:
            TenantResponse with provisioning details
            
        Raises:
            TenantProvisioningError: If provisioning fails
        """
        tenant_id = tenant_data.subdomain or self._generate_tenant_id(tenant_data.name)
        
        logger.info(f"Starting tenant provisioning for: {tenant_id}")
        
        try:
            # 1. Provision database resources
            db_resources = await self._provision_database_resources(tenant_id)
            
            # 2. Provision Redis resources
            redis_resources = await self._provision_redis_resources(tenant_id)
            
            # 3. Provision Vault resources
            vault_resources = await self._provision_vault_resources(tenant_id)
            
            # 4. Generate container configuration
            container_config = self._generate_container_config(
                tenant_id, db_resources, redis_resources, vault_resources
            )
            
            # 5. Deploy tenant container
            container_info = await self._deploy_tenant_container(tenant_id, container_config)
            
            # 6. Validate tenant health
            await self._validate_tenant_health(tenant_id)
            
            # 7. Create tenant record in management database
            tenant = await self._create_tenant_record(tenant_data, tenant_id, {
                "database_schema": db_resources["schema"],
                "redis_db": redis_resources["db"],
                "container_id": container_info["id"],
                "endpoints": container_info["endpoints"]
            })
            
            logger.info(f"Tenant provisioning completed for: {tenant_id}")
            return tenant
            
        except Exception as e:
            logger.error(f"Tenant provisioning failed for {tenant_id}: {str(e)}")
            # Cleanup any partially created resources
            await self._cleanup_tenant_resources(tenant_id)
            raise TenantProvisioningError(f"Failed to provision tenant {tenant_id}: {str(e)}")
    
    async def _provision_database_resources(self, tenant_id: str) -> Dict[str, Any]:
        """Create isolated database schema for tenant."""
        schema_name = f"tenant_{tenant_id}"
        
        logger.info(f"Creating database schema: {schema_name}")
        
        try:
            # Connect to main database as admin
            async with get_database() as db:
                # Create schema
                await db.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
                
                # Create tenant-specific user (optional, for stronger isolation)
                tenant_user = f"user_{tenant_id}"
                tenant_password = self._generate_secure_password()
                
                await db.execute(text(f"""
                    CREATE USER {tenant_user} WITH PASSWORD '{tenant_password}'
                """))
                
                # Grant permissions to schema
                await db.execute(text(f"""
                    GRANT USAGE, CREATE ON SCHEMA {schema_name} TO {tenant_user}
                """))
                
                await db.commit()
                
            # Generate tenant-specific database URL
            database_url = f"postgresql+asyncpg://{tenant_user}:{tenant_password}@postgres-shared:5432/dotmac_isp?options=-csearch_path={schema_name}"
            
            return {
                "schema": schema_name,
                "user": tenant_user,
                "password": tenant_password,
                "url": database_url
            }
            
        except Exception as e:
            logger.error(f"Failed to create database resources for {tenant_id}: {str(e)}")
            raise
    
    async def _provision_redis_resources(self, tenant_id: str) -> Dict[str, Any]:
        """Allocate Redis database and namespace for tenant."""
        # Use hash to consistently allocate Redis DB (0-15)
        redis_db = hash(tenant_id) % 16
        redis_namespace = f"tenant:{tenant_id}:"
        
        logger.info(f"Allocating Redis DB {redis_db} with namespace {redis_namespace}")
        
        try:
            # Test Redis connection
            redis = await get_redis()
            await redis.select(redis_db)
            
            # Set a marker key to indicate this DB is allocated
            await redis.set(f"{redis_namespace}:allocated", datetime.utcnow().isoformat())
            
            return {
                "db": redis_db,
                "namespace": redis_namespace,
                "url": f"redis://:{{REDIS_PASSWORD}}@redis-shared:6379/{redis_db}"
            }
            
        except Exception as e:
            logger.error(f"Failed to allocate Redis resources for {tenant_id}: {str(e)}")
            raise
    
    async def _provision_vault_resources(self, tenant_id: str) -> Dict[str, Any]:
        """Create Vault path for tenant secrets."""
        vault_path = f"secret/tenants/{tenant_id}"
        
        logger.info(f"Creating Vault path: {vault_path}")
        
        # TODO: Implement actual Vault integration
        # For now, return the path structure
        return {
            "path": vault_path,
            "policies": [f"tenant-{tenant_id}-policy"]
        }
    
    def _generate_container_config(
        self, 
        tenant_id: str, 
        db_resources: Dict[str, Any],
        redis_resources: Dict[str, Any],
        vault_resources: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate Docker container configuration for tenant."""
        
        container_config = {
            "name": f"dotmac-tenant-{tenant_id}",
            "image": "dotmac-isp:latest",
            "environment": {
                # Tenant identification
                "TENANT_ID": tenant_id,
                "TENANT_SUBDOMAIN": tenant_id,
                
                # Database configuration (isolated schema)
                "DATABASE_URL": db_resources["url"],
                "DATABASE_SCHEMA": db_resources["schema"],
                
                # Redis configuration (isolated namespace)
                "REDIS_URL": redis_resources["url"],
                "REDIS_NAMESPACE": redis_resources["namespace"],
                
                # Vault configuration
                "VAULT_PATH": vault_resources["path"],
                
                # Application configuration
                "ENVIRONMENT": "production",
                "LOG_LEVEL": "INFO",
                "DEBUG": "false",
                
                # Import path fix
                "PYTHONPATH": "/app/src:/app/shared",
                
                # SignOz (with tenant tagging)
                "SIGNOZ_ENDPOINT": "signoz-collector:4317",
                "OTEL_RESOURCE_ATTRIBUTES": f"service.name=dotmac-tenant-{tenant_id},tenant.id={tenant_id}",
            },
            "ports": {
                "8000/tcp": None  # Dynamic port allocation
            },
            "volumes": {
                "/app/shared": {"bind": "/home/dotmac_framework/shared", "mode": "ro"}
            },
            "networks": ["dotmac-network"],
            "labels": {
                "com.dotmac.tenant.id": tenant_id,
                "com.dotmac.service": "isp-framework",
                "com.dotmac.provisioned": datetime.utcnow().isoformat()
            },
            "healthcheck": {
                "test": ["CMD", "curl", "-f", "http://localhost:8000/health"],
                "interval": "30s",
                "timeout": "10s",
                "retries": 5,
                "start_period": "60s"
            },
            "restart_policy": {"Name": "unless-stopped"},
            "resources": {
                "limits": {
                    "memory": "512M",
                    "cpus": "0.5"
                },
                "reservations": {
                    "memory": "256M", 
                    "cpus": "0.25"
                }
            }
        }
        
        return container_config
    
    async def _deploy_tenant_container(self, tenant_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy tenant container using Docker API."""
        
        # TODO: Implement actual Docker container deployment
        # This would use the Docker SDK to:
        # 1. Pull/build the tenant image
        # 2. Create the container with the config
        # 3. Start the container
        # 4. Wait for healthy status
        
        logger.info(f"Deploying container for tenant: {tenant_id}")
        
        # Mock container info for now
        return {
            "id": f"container_{tenant_id}_{hash(tenant_id) % 10000}",
            "endpoints": {
                "api": f"http://tenant-{tenant_id}:8000",
                "health": f"http://tenant-{tenant_id}:8000/health"
            },
            "status": "running"
        }
    
    async def _validate_tenant_health(self, tenant_id: str) -> bool:
        """Validate tenant container is healthy and APIs are responding."""
        
        logger.info(f"Validating tenant health: {tenant_id}")
        
        # TODO: Implement actual health checks
        # 1. Check container status
        # 2. Test API endpoints
        # 3. Verify database connectivity
        # 4. Check Redis connectivity
        
        await asyncio.sleep(2)  # Mock validation delay
        return True
    
    async def _create_tenant_record(
        self, 
        tenant_data: TenantCreate, 
        tenant_id: str, 
        provisioning_info: Dict[str, Any]
    ) -> TenantResponse:
        """Create tenant record in management database."""
        
        # TODO: Implement actual tenant model creation
        # This would save the tenant info to the management database
        
        return TenantResponse(
            id=tenant_id,
            name=tenant_data.name,
            subdomain=tenant_id,
            status="active",
            created_at=datetime.utcnow(),
            endpoints=provisioning_info.get("endpoints", {}),
            resources={
                "database_schema": provisioning_info["database_schema"],
                "redis_db": provisioning_info["redis_db"],
                "container_id": provisioning_info["container_id"]
            }
        )
    
    async def _cleanup_tenant_resources(self, tenant_id: str) -> None:
        """Clean up any partially created tenant resources."""
        
        logger.warning(f"Cleaning up tenant resources for: {tenant_id}")
        
        try:
            # Clean up database resources
            schema_name = f"tenant_{tenant_id}"
            async with get_database() as db:
                await db.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
                await db.execute(text(f"DROP USER IF EXISTS user_{tenant_id}"))
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to cleanup database for {tenant_id}: {str(e)}")
        
        try:
            # Clean up Redis resources
            redis = await get_redis()
            redis_db = hash(tenant_id) % 16
            await redis.select(redis_db)
            await redis.flushdb()  # Clear the allocated Redis DB
        except Exception as e:
            logger.error(f"Failed to cleanup Redis for {tenant_id}: {str(e)}")
        
        # TODO: Clean up containers, Vault resources, etc.
    
    def _generate_tenant_id(self, tenant_name: str) -> str:
        """Generate a unique tenant ID from tenant name."""
        # Create a URL-safe tenant ID
        safe_name = "".join(c.lower() for c in tenant_name if c.isalnum() or c in '-_')
        hash_suffix = hashlib.md5(tenant_name.encode()).hexdigest()[:8]
        return f"{safe_name}-{hash_suffix}"
    
    def _generate_secure_password(self) -> str:
        """Generate a secure password for tenant database user."""
        import secrets
        import string
        
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(16))


# Singleton instance
tenant_provisioning_service = TenantProvisioningService()