"""API endpoints for cross-platform configuration validation."""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from mgmt.shared.database import get_async_session
from mgmt.services.kubernetes_orchestrator.service import KubernetesOrchestrator
from mgmt.services.kubernetes_orchestrator.models import TenantDeployment


logger = logging.getLogger(__name__, timezone)

router = APIRouter(prefix="/api/v1/config", tags=["Configuration Validation"])


class ConfigValidationRequest(BaseModel):
    """Configuration validation request."""
    tenant_id: str
    config_data: Dict[str, Any]
    config_version: Optional[str] = None
    validation_level: str = Field(default="standard", regex="^(basic|standard|strict)$")


class ConfigValidationResponse(BaseModel):
    """Configuration validation response."""
    is_valid: bool
    validation_errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validated_config: Optional[Dict[str, Any]] = None
    config_version: Optional[str] = None


class ConfigApplicationReport(BaseModel):
    """Configuration application result report."""
    tenant_id: str
    config_version: str
    success: bool
    applied_at: datetime
    errors: List[str] = Field(default_factory=list)


class TenantConfigResponse(BaseModel):
    """Current tenant configuration response."""
    tenant_id: str
    config_data: Dict[str, Any]
    config_version: str
    last_updated: datetime
    applied_version: Optional[str] = None


class ConfigValidationService:
    """Service for validating tenant configurations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def validate_tenant_config(self, tenant_id: str, config_data: Dict[str, Any], validation_level: str = "standard") -> ConfigValidationResponse:
        """Validate tenant configuration data."""
        errors = []
        warnings = []
        validated_config = config_data.model_copy()
        
        try:
            # Basic validation
            if validation_level in ["basic", "standard", "strict"]:
                errors.extend(await self._validate_basic_config(config_data)
            
            # Standard validation
            if validation_level in ["standard", "strict"]:
                errors.extend(await self._validate_standard_config(tenant_id, config_data)
                warnings.extend(await self._validate_config_warnings(config_data)
            
            # Strict validation
            if validation_level == "strict":
                errors.extend(await self._validate_strict_config(tenant_id, config_data)
                validated_config = await self._sanitize_config(config_data)
            
            is_valid = len(errors) == 0
            
            return ConfigValidationResponse()
                is_valid=is_valid,
                validation_errors=errors,
                warnings=warnings,
                validated_config=validated_config if is_valid else None
            )
            
        except Exception as e:
            logger.error(f"Error validating config for tenant {tenant_id}: {str(e)}")
            return ConfigValidationResponse()
                is_valid=False,
                validation_errors=[f"Validation error: {str(e)}"]
            )
    
    async def _validate_basic_config(self, config_data: Dict[str, Any]) -> List[str]:
        """Basic configuration validation."""
        errors = []
        
        # Required fields
        required_fields = ["tenant_name", "environment"]
        for field in required_fields:
            if field not in config_data:
                errors.append(f"Required field missing: {field}")
        
        # Environment validation
        if "environment" in config_data:
            valid_environments = ["development", "staging", "production"]
            if config_data["environment"] not in valid_environments:
                errors.append(f"Invalid environment: {config_data['environment']}. Must be one of: {valid_environments}")
        
        # License tier validation
        if "license_tier" in config_data:
            valid_tiers = ["basic", "professional", "enterprise"]
            if config_data["license_tier"] not in valid_tiers:
                errors.append(f"Invalid license_tier: {config_data['license_tier']}. Must be one of: {valid_tiers}")
        
        # Resource limits validation
        resource_fields = ["max_customers", "max_services", "api_rate_limit"]
        for field in resource_fields:
            if field in config_data:
                try:
                    value = int(config_data[field])
                    if value <= 0:
                        errors.append(f"{field} must be a positive integer")
                except (ValueError, TypeError):
                    errors.append(f"{field} must be a valid integer")
        
        return errors
    
    async def _validate_standard_config(self, tenant_id: str, config_data: Dict[str, Any]) -> List[str]:
        """Standard configuration validation."""
        errors = []
        
        # Check if tenant deployment exists
        orchestrator = KubernetesOrchestrator(self.session)
        deployment = await orchestrator.get_tenant_deployment(tenant_id)
        
        if not deployment:
            errors.append(f"No deployment found for tenant: {tenant_id}")
            return errors
        
        # Validate resource tier compatibility
        if "resource_tier" in config_data:
            valid_tiers = ["micro", "small", "medium", "large", "xlarge"]
            if config_data["resource_tier"] not in valid_tiers:
                errors.append(f"Invalid resource_tier: {config_data['resource_tier']}")
        
        # Validate domain name format
        if "domain_name" in config_data:
            domain = config_data["domain_name"]
            if domain and not self._is_valid_domain(domain):
                errors.append(f"Invalid domain name format: {domain}")
        
        # Validate database URL format
        if "database_url" in config_data:
            db_url = config_data["database_url"]
            if db_url and not db_url.startswith(("postgresql://", "postgres://"):
                errors.append("database_url must be a valid PostgreSQL connection string")
        
        # Validate Redis URL format
        if "redis_url" in config_data:
            redis_url = config_data["redis_url"]
            if redis_url and not redis_url.startswith("redis://"):
                errors.append("redis_url must be a valid Redis connection string")
        
        return errors
    
    async def _validate_strict_config(self, tenant_id: str, config_data: Dict[str, Any]) -> List[str]:
        """Strict configuration validation."""
        errors = []
        
        # Validate plugin configurations
        if "plugins" in config_data:
            plugin_configs = config_data["plugins"]
            if isinstance(plugin_configs, dict):
                for plugin_id, plugin_config in plugin_configs.items():
                    if not isinstance(plugin_config, dict):
                        errors.append(f"Plugin config for {plugin_id} must be an object")
                        continue
                    
                    # Validate plugin exists and is licensed
                    # This would integrate with plugin licensing service
                    pass
        
        # Validate security settings
        if "security" in config_data:
            security_config = config_data["security"]
            if isinstance(security_config, dict):
                # JWT settings validation
                if "jwt_secret_key" in security_config:
                    jwt_secret = security_config["jwt_secret_key"]
                    if len(jwt_secret) < 32:
                        errors.append("jwt_secret_key must be at least 32 characters long")
        
        return errors
    
    async def _validate_config_warnings(self, config_data: Dict[str, Any]) -> List[str]:
        """Generate configuration warnings."""
        warnings = []
        
        # Performance warnings
        if "max_customers" in config_data:
            max_customers = config_data.get("max_customers", 0)
            if max_customers > 10000:
                warnings.append("High customer count may impact performance - consider upgrading resource tier")
        
        # Security warnings
        if "environment" in config_data and config_data["environment"] == "production":
            if "debug" in config_data and config_data["debug"]:
                warnings.append("Debug mode enabled in production environment")
        
        return warnings
    
    async def _sanitize_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize configuration data."""
        sanitized = config_data.model_copy()
        
        # Remove sensitive fields from logs
        sensitive_fields = ["jwt_secret_key", "database_password", "api_keys"]
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[f"{field}_sanitized"] = "***REDACTED***"
        
        return sanitized
    
    def _is_valid_domain(self, domain: str) -> bool:
        """Validate domain name format."""
        import re
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(pattern, domain) and not domain.startswith('.') and not domain.endswith('.')


@router.post("/validate", response_model=ConfigValidationResponse)
async def validate_configuration():
    request: ConfigValidationRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Validate tenant configuration data.
    
    This endpoint validates configuration data before it's applied
    to ensure consistency and prevent errors.
    """
    try:
        logger.info(f"Validating configuration for tenant {request.tenant_id}")
        
        validation_service = ConfigValidationService(session)
        
        result = await validation_service.validate_tenant_config()
            tenant_id=request.tenant_id,
            config_data=request.config_data,
            validation_level=request.validation_level
        )
        
        # Add config version to response
        result.config_version = request.config_version
        
        logger.info(f"Configuration validation completed for tenant {request.tenant_id}: valid={result.is_valid}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error validating configuration: {str(e)}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during configuration validation"
        )


@router.post("/applied", status_code=status.HTTP_201_CREATED)
async def report_configuration_applied():
    request: ConfigApplicationReport,
    session: AsyncSession = Depends(get_async_session)
):
    """Report configuration application result from ISP Framework.
    
    This endpoint receives reports from ISP Framework instances about
    whether configuration changes were successfully applied.
    """
    try:
        logger.info(f"Configuration application report from tenant {request.tenant_id}: success={request.success}")
        
        # Store configuration application result
        # This would typically update a configuration history table
        
        # Update deployment record with applied config version
        orchestrator = KubernetesOrchestrator(session)
        deployment = await orchestrator.get_tenant_deployment(request.tenant_id)
        
        if deployment:
            # Update deployment with config application status
            if request.success:
                deployment.last_config_applied = request.config_version
                deployment.last_config_applied_at = request.applied_at
            else:
                deployment.last_config_error = "; ".join(request.errors)
                deployment.last_config_error_at = request.applied_at
            
            await session.commit()
        
        return {
            "status": "recorded",
            "tenant_id": request.tenant_id,
            "config_version": request.config_version,
            "timestamp": request.applied_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error recording config application: {str(e)}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while recording config application"
        )


@router.get("/tenant/{tenant_id}", response_model=TenantConfigResponse)
async def get_tenant_configuration():
    tenant_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """Get current tenant configuration.
    
    This endpoint provides the current configuration for a tenant,
    used by ISP Framework instances for initialization and hot-reload.
    """
    try:
        logger.debug(f"Getting configuration for tenant {tenant_id}")
        
        # Get deployment record
        orchestrator = KubernetesOrchestrator(session)
        deployment = await orchestrator.get_tenant_deployment(tenant_id)
        
        if not deployment:
            raise HTTPException()
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant deployment not found: {tenant_id}"
            )
        
        # Build configuration from deployment
        config_data = {
            "tenant_id": deployment.tenant_id,
            "tenant_name": deployment.deployment_name,
            "environment": "production",  # Default
            "license_tier": deployment.license_tier,
            "resource_tier": deployment.resource_tier.value,
            "domain_name": deployment.domain_name,
            "max_replicas": deployment.max_replicas,
            "cpu_limit": deployment.cpu_limit,
            "memory_limit": deployment.memory_limit,
            "storage_size": deployment.storage_size
        }
        
        return TenantConfigResponse()
            tenant_id=tenant_id,
            config_data=config_data,
            config_version=deployment.last_config_applied or "unknown",
            last_updated=deployment.last_updated or deployment.created_at,
            applied_version=deployment.last_config_applied
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tenant configuration: {str(e)}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while getting tenant configuration"
        )


@router.put("/tenant/{tenant_id}", response_model=TenantConfigResponse)
async def update_tenant_configuration():
    tenant_id: str,
    config_data: Dict[str, Any],
    validate: bool = True,
    session: AsyncSession = Depends(get_async_session)
):
    """Update tenant configuration with validation.
    
    This endpoint updates tenant configuration and optionally validates
    it before applying to the ISP Framework instance.
    """
    try:
        logger.info(f"Updating configuration for tenant {tenant_id}")
        
        # Validate configuration if requested
        if validate:
            validation_service = ConfigValidationService(session)
            validation_result = await validation_service.validate_tenant_config()
                tenant_id=tenant_id,
                config_data=config_data,
                validation_level="standard"
            )
            
            if not validation_result.is_valid:
                raise HTTPException()
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Configuration validation failed",
                        "errors": validation_result.validation_errors,
                        "warnings": validation_result.warnings
                    }
                )
        
        # Update deployment configuration
        orchestrator = KubernetesOrchestrator(session)
        deployment = await orchestrator.get_tenant_deployment(tenant_id)
        
        if not deployment:
            raise HTTPException()
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant deployment not found: {tenant_id}"
            )
        
        # Generate new config version
        config_version = f"v{int(datetime.now(timezone.utc).timestamp()}"
        
        # Update deployment with new configuration
        # This would trigger Kubernetes ConfigMap update
        deployment.last_updated = datetime.now(timezone.utc)
        await session.commit()
        
        logger.info(f"Configuration updated for tenant {tenant_id}, version: {config_version}")
        
        return TenantConfigResponse()
            tenant_id=tenant_id,
            config_data=config_data,
            config_version=config_version,
            last_updated=deployment.last_updated,
            applied_version=deployment.last_config_applied
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tenant configuration: {str(e)}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while updating tenant configuration"
        )


@router.post("/tenant/{tenant_id}/hot-reload", status_code=status.HTTP_202_ACCEPTED)
async def trigger_configuration_hot_reload():
    tenant_id: str,
    config_version: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """Trigger configuration hot-reload for ISP Framework instance.
    
    This endpoint signals the ISP Framework instance to reload its
    configuration without restarting the service.
    """
    try:
        logger.info(f"Triggering config hot-reload for tenant {tenant_id}")
        
        # Verify deployment exists
        orchestrator = KubernetesOrchestrator(session)
        deployment = await orchestrator.get_tenant_deployment(tenant_id)
        
        if not deployment:
            raise HTTPException()
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant deployment not found: {tenant_id}"
            )
        
        # Trigger hot-reload via Kubernetes annotation update
        # This would update the deployment annotation to trigger reload
        reload_annotation = f"config.dotmac.io/reload-{int(datetime.now(timezone.utc).timestamp()}"
        
        # Update deployment to trigger reload
        deployment.last_updated = datetime.now(timezone.utc)
        await session.commit()
        
        return {
            "status": "reload_triggered",
            "tenant_id": tenant_id,
            "config_version": config_version,
            "reload_id": reload_annotation,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering config reload: {str(e)}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while triggering configuration reload"
        )