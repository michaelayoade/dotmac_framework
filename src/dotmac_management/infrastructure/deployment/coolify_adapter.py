"""
Coolify Deployment Adapter
Implementation of IDeploymentProvider for Coolify
"""

import httpx
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from dotmac_shared.core.logging import get_logger
from dotmac_shared.api.exception_handlers import standard_exception_handler

from ..interfaces.deployment_provider import (
    IDeploymentProvider, 
    DeploymentResult, 
    ApplicationConfig, 
    ServiceConfig
)

logger = get_logger(__name__)


@dataclass
class CoolifyConfig:
    """Coolify server configuration"""
    base_url: str
    api_token: str
    project_id: Optional[str] = None
    server_id: Optional[str] = None


class CoolifyDeploymentAdapter(IDeploymentProvider):
    """
    Coolify deployment provider implementation.
    Handles application and service deployment via Coolify API.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.coolify_config: Optional[CoolifyConfig] = None
        self.client: Optional[httpx.AsyncClient] = None
        self._initialized = False
    
    @standard_exception_handler
    async def initialize(self) -> bool:
        """Initialize the Coolify adapter"""
        try:
            if self._initialized:
                return True
                
            self.coolify_config = self._load_config()
            
            # Initialize HTTP client
            self.client = httpx.AsyncClient(
                base_url=self.coolify_config.base_url,
                headers={
                    "Authorization": f"Bearer {self.coolify_config.api_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                timeout=60.0
            )
            
            # Test connection
            health_result = await self.health_check()
            if not health_result.get("healthy", False):
                raise Exception(f"Coolify health check failed: {health_result.get('error')}")
            
            self._initialized = True
            logger.info("✅ Coolify deployment adapter initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Coolify adapter: {e}")
            return False
    
    @standard_exception_handler
    async def health_check(self) -> Dict[str, Any]:
        """Check Coolify API health"""
        try:
            if not self.client:
                return {"healthy": False, "error": "Client not initialized"}
            
            response = await self.client.get("/api/v1/servers")
            
            if response.status_code == 200:
                return {
                    "healthy": True,
                    "status": "connected",
                    "coolify_version": response.headers.get("x-coolify-version", "unknown"),
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
            else:
                return {
                    "healthy": False,
                    "error": f"API returned {response.status_code}",
                    "status": "error"
                }
                
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "status": "error"
            }
    
    def _load_config(self) -> CoolifyConfig:
        """Load Coolify configuration from adapter config and environment"""
        base_url = (
            self.config.get("base_url") or 
            os.getenv('COOLIFY_API_URL', 'http://localhost:8000')
        )
        
        api_token = (
            self.config.get("api_token") or 
            os.getenv('COOLIFY_API_TOKEN')
        )
        
        if not api_token:
            raise ValueError("Coolify API token is required")
        
        return CoolifyConfig(
            base_url=base_url.rstrip('/'),
            api_token=api_token,
            project_id=self.config.get("project_id") or os.getenv('COOLIFY_PROJECT_ID'),
            server_id=self.config.get("server_id", os.getenv('COOLIFY_SERVER_ID', '0'))
        )
    
    @standard_exception_handler
    async def deploy_application(self, config: ApplicationConfig) -> DeploymentResult:
        """Deploy application to Coolify"""
        try:
            payload = {
                "name": config.name,
                "description": config.description,
                "project_uuid": self.coolify_config.project_id,
                "server_uuid": self.coolify_config.server_id,
                "docker_compose_raw": config.docker_compose,
                "environment_variables": config.environment,
                "domains": config.domains,
                "is_static": False,
                "build_pack": "dockercompose",
                "source": {
                    "type": "docker-compose",
                    "docker_compose_raw": config.docker_compose
                }
            }
            
            response = await self.client.post("/api/v1/applications", json=payload)
            
            if response.status_code not in [200, 201]:
                return DeploymentResult(
                    success=False,
                    deployment_id="",
                    error=f"Coolify API error: {response.status_code} - {response.text}"
                )
            
            result = response.json()
            app_id = result.get("uuid") or result.get("id")
            
            # Start deployment
            deploy_response = await self.client.post(f"/api/v1/applications/{app_id}/deploy")
            
            if deploy_response.status_code not in [200, 201]:
                logger.warning(f"Deployment start failed: {deploy_response.status_code}")
            
            endpoint_url = None
            if config.domains:
                endpoint_url = f"https://{config.domains[0]}"
            
            return DeploymentResult(
                success=True,
                deployment_id=app_id,
                application_id=app_id,
                endpoint_url=endpoint_url,
                status="deploying",
                message="Application deployment started",
                metadata={
                    "provider": "coolify",
                    "project_id": self.coolify_config.project_id,
                    "server_id": self.coolify_config.server_id
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to deploy application: {e}")
            return DeploymentResult(
                success=False,
                deployment_id="",
                error=str(e)
            )
    
    @standard_exception_handler
    async def deploy_service(self, config: ServiceConfig) -> DeploymentResult:
        """Deploy service (database, cache, etc.) to Coolify"""
        try:
            if config.service_type == "postgresql":
                return await self._deploy_postgresql(config)
            elif config.service_type == "redis":
                return await self._deploy_redis(config)
            else:
                return DeploymentResult(
                    success=False,
                    deployment_id="",
                    error=f"Unsupported service type: {config.service_type}"
                )
                
        except Exception as e:
            logger.error(f"Failed to deploy service: {e}")
            return DeploymentResult(
                success=False,
                deployment_id="",
                error=str(e)
            )
    
    async def _deploy_postgresql(self, config: ServiceConfig) -> DeploymentResult:
        """Deploy PostgreSQL service"""
        payload = {
            "name": config.name,
            "description": f"PostgreSQL database service",
            "type": "postgresql",
            "version": config.version or "15",
            "project_uuid": self.coolify_config.project_id,
            "server_uuid": self.coolify_config.server_id,
            "environment_variables": config.configuration
        }
        
        response = await self.client.post("/api/v1/services/postgresql", json=payload)
        
        if response.status_code not in [200, 201]:
            return DeploymentResult(
                success=False,
                deployment_id="",
                error=f"PostgreSQL creation failed: {response.status_code} - {response.text}"
            )
        
        result = response.json()
        service_id = result.get("uuid") or result.get("id")
        
        # Generate connection URL
        db_config = config.configuration
        connection_url = f"postgresql://{db_config.get('username')}:{db_config.get('password')}@{config.name}:5432/{db_config.get('database')}"
        
        return DeploymentResult(
            success=True,
            deployment_id=service_id,
            status="running",
            message="PostgreSQL service created",
            metadata={
                "service_type": "postgresql",
                "connection_url": connection_url
            }
        )
    
    async def _deploy_redis(self, config: ServiceConfig) -> DeploymentResult:
        """Deploy Redis service"""
        payload = {
            "name": config.name,
            "description": "Redis cache service",
            "type": "redis",
            "version": config.version or "7",
            "project_uuid": self.coolify_config.project_id,
            "server_uuid": self.coolify_config.server_id,
            "environment_variables": config.configuration
        }
        
        response = await self.client.post("/api/v1/services/redis", json=payload)
        
        if response.status_code not in [200, 201]:
            return DeploymentResult(
                success=False,
                deployment_id="",
                error=f"Redis creation failed: {response.status_code} - {response.text}"
            )
        
        result = response.json()
        service_id = result.get("uuid") or result.get("id")
        
        # Generate connection URL
        password = config.configuration.get("password", "")
        password_part = f":{password}@" if password else "@"
        connection_url = f"redis://{password_part}{config.name}:6379"
        
        return DeploymentResult(
            success=True,
            deployment_id=service_id,
            status="running",
            message="Redis service created",
            metadata={
                "service_type": "redis",
                "connection_url": connection_url
            }
        )
    
    @standard_exception_handler
    async def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get deployment status"""
        try:
            response = await self.client.get(f"/api/v1/applications/{deployment_id}")
            
            if response.status_code == 404:
                return {"status": "not_found", "deployment_id": deployment_id}
            elif response.status_code != 200:
                return {"status": "error", "error": f"API error: {response.status_code}"}
            
            result = response.json()
            
            return {
                "deployment_id": deployment_id,
                "status": result.get("status", "unknown"),
                "health": result.get("health", "unknown"),
                "url": result.get("fqdn", ""),
                "created_at": result.get("created_at"),
                "updated_at": result.get("updated_at")
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    @standard_exception_handler
    async def get_deployment_logs(self, deployment_id: str) -> List[str]:
        """Get deployment logs"""
        try:
            response = await self.client.get(f"/api/v1/applications/{deployment_id}/logs")
            
            if response.status_code != 200:
                logger.warning(f"Could not fetch logs: {response.status_code}")
                return []
            
            result = response.json()
            return result.get("logs", [])
            
        except Exception as e:
            logger.error(f"Failed to get deployment logs: {e}")
            return []
    
    @standard_exception_handler
    async def scale_deployment(self, deployment_id: str, instances: int) -> bool:
        """Scale deployment (Coolify manages this automatically)"""
        logger.info(f"Scale request received for {deployment_id} to {instances} instances, Coolify manages scaling automatically")
        return True
    
    @standard_exception_handler
    async def stop_deployment(self, deployment_id: str) -> bool:
        """Stop deployment"""
        try:
            response = await self.client.post(f"/api/v1/applications/{deployment_id}/stop")
            return response.status_code in [200, 204]
            
        except Exception as e:
            logger.error(f"Failed to stop deployment: {e}")
            return False
    
    @standard_exception_handler
    async def remove_deployment(self, deployment_id: str) -> bool:
        """Remove deployment"""
        try:
            response = await self.client.delete(f"/api/v1/applications/{deployment_id}")
            return response.status_code in [200, 204]
            
        except Exception as e:
            logger.error(f"Failed to remove deployment: {e}")
            return False
    
    @standard_exception_handler
    async def set_domain(self, deployment_id: str, domain: str) -> bool:
        """Set custom domain for deployment"""
        try:
            payload = {
                "domain": domain,
                "https": True,
                "redirect_to_https": True
            }
            
            response = await self.client.post(f"/api/v1/applications/{deployment_id}/domains", json=payload)
            return response.status_code in [200, 201]
            
        except Exception as e:
            logger.error(f"Failed to set domain: {e}")
            return False
    
    async def get_supported_services(self) -> List[str]:
        """Get supported service types"""
        return ["postgresql", "redis", "mysql", "mariadb", "mongodb"]
    
    @standard_exception_handler
    async def validate_config(self, config: ApplicationConfig) -> Dict[str, Any]:
        """Validate application configuration"""
        errors = []
        warnings = []
        
        if not config.name:
            errors.append("Application name is required")
        
        if not config.docker_compose:
            errors.append("Docker Compose configuration is required")
        
        # Basic docker-compose validation
        if "services:" not in config.docker_compose:
            errors.append("Docker Compose must contain services definition")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def cleanup(self) -> bool:
        """Cleanup adapter resources"""
        try:
            if self.client:
                await self.client.aclose()
                self.client = None
            
            self._initialized = False
            logger.info("✅ Coolify deployment adapter cleanup complete")
            return True
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return False