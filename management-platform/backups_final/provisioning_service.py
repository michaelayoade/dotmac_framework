"""
Automated tenant provisioning service for the DotMac Management Platform.
Handles complete tenant lifecycle from onboarding to infrastructure deployment.
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from models.tenant import Tenant, TenantStatus
from models.deployment import Deployment, DeploymentStatus
from repositories.tenant import TenantRepository
from repositories.deployment_additional import DeploymentRepository
from services.stripe_service import StripeService
from services.infrastructure_service import InfrastructureService
from services.dns_service import DNSService
from services.notification_service import NotificationService
from schemas.tenant import TenantCreate, TenantProvisioningRequest
from schemas.deployment import DeploymentCreate
from core.config import settings

logger = logging.getLogger(__name__, timezone)


class ProvisioningStage(str, Enum):
    """Tenant provisioning stages."""
    PENDING = "pending"
    VALIDATING = "validating"
    CREATING_BILLING = "creating_billing"
    PROVISIONING_INFRASTRUCTURE = "provisioning_infrastructure"
    CONFIGURING_DNS = "configuring_dns"
    DEPLOYING_SERVICES = "deploying_services"
    CONFIGURING_MONITORING = "configuring_monitoring"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProvisioningError(Exception):
    """Custom exception for provisioning errors."""
    
    def __init__(self, message: str, stage: ProvisioningStage, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.stage = stage
        self.details = details or {}
        super().__init__(message)


class TenantProvisioningService:
    """Comprehensive tenant provisioning and lifecycle management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tenant_repo = TenantRepository(db)
        self.deployment_repo = DeploymentRepository(db)
        self.stripe_service = StripeService(db)
        self.infrastructure_service = InfrastructureService(db)
        self.dns_service = DNSService(db)
        self.notification_service = NotificationService(db)
    
    async def provision_tenant():
        self,
        provisioning_request: TenantProvisioningRequest,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Complete tenant provisioning workflow.
        
        Handles end-to-end provisioning from tenant creation to service deployment.
        """
        provisioning_id = str(UUID.uuid4()
        current_stage = ProvisioningStage.PENDING
        
        try:
            logger.info(f"Starting tenant provisioning {provisioning_id}")
            
            # Stage 1: Validation
            current_stage = ProvisioningStage.VALIDATING
            await self._update_provisioning_status()
                provisioning_id, current_stage, "Validating tenant request"
            )
            
            validation_result = await self._validate_provisioning_request(provisioning_request)
            if not validation_result["valid"]:
                raise ProvisioningError()
                    f"Validation failed: {validation_result['errors']}",
                    current_stage,
                    validation_result
                )
            
            # Stage 2: Create tenant record
            tenant = await self._create_tenant_record(provisioning_request, user_id)
            
            # Stage 3: Set up billing
            current_stage = ProvisioningStage.CREATING_BILLING
            await self._update_provisioning_status()
                provisioning_id, current_stage, "Setting up billing and payment processing"
            )
            
            billing_result = await self._setup_tenant_billing(tenant, provisioning_request)
            
            # Stage 4: Provision infrastructure
            current_stage = ProvisioningStage.PROVISIONING_INFRASTRUCTURE
            await self._update_provisioning_status()
                provisioning_id, current_stage, "Provisioning cloud infrastructure"
            )
            
            infrastructure_result = await self._provision_infrastructure(tenant, provisioning_request)
            
            # Stage 5: Configure DNS
            current_stage = ProvisioningStage.CONFIGURING_DNS
            await self._update_provisioning_status()
                provisioning_id, current_stage, "Configuring DNS and SSL certificates"
            )
            
            dns_result = await self._configure_dns(tenant, provisioning_request)
            
            # Stage 6: Deploy services
            current_stage = ProvisioningStage.DEPLOYING_SERVICES
            await self._update_provisioning_status()
                provisioning_id, current_stage, "Deploying DotMac ISP Framework services"
            )
            
            deployment_result = await self._deploy_tenant_services(tenant, provisioning_request)
            
            # Stage 7: Configure monitoring
            current_stage = ProvisioningStage.CONFIGURING_MONITORING
            await self._update_provisioning_status()
                provisioning_id, current_stage, "Setting up monitoring and alerting"
            )
            
            monitoring_result = await self._configure_monitoring(tenant)
            
            # Stage 8: Finalization
            current_stage = ProvisioningStage.FINALIZING
            await self._update_provisioning_status()
                provisioning_id, current_stage, "Finalizing tenant setup"
            )
            
            await self._finalize_tenant_provisioning(tenant)
            
            # Stage 9: Completion
            current_stage = ProvisioningStage.COMPLETED
            await self._update_provisioning_status()
                provisioning_id, current_stage, "Tenant provisioning completed successfully"
            )
            
            # Send welcome notification
            await self._send_provisioning_complete_notification(tenant, provisioning_request)
            
            logger.info(f"Tenant provisioning {provisioning_id} completed successfully")
            
            return {
                "provisioning_id": provisioning_id,
                "tenant_id": str(tenant.id),
                "status": "completed",
                "tenant_url": f"https://{tenant.slug}.{settings.base_domain}",
                "admin_url": f"https://{tenant.slug}-admin.{settings.base_domain}",
                "results": {
                    "validation": validation_result,
                    "billing": billing_result,
                    "infrastructure": infrastructure_result,
                    "dns": dns_result,
                    "deployment": deployment_result,
                    "monitoring": monitoring_result
                }
            }
            
        except ProvisioningError:
            raise
        except Exception as e:
            logger.error(f"Tenant provisioning {provisioning_id} failed at stage {current_stage}: {e}")
            await self._handle_provisioning_failure(provisioning_id, current_stage, str(e)
            raise ProvisioningError()
                f"Provisioning failed at stage {current_stage}: {str(e)}",
                current_stage,
                {"error": str(e), "provisioning_id": provisioning_id}
            )
    
    async def _validate_provisioning_request():
        self, 
        request: TenantProvisioningRequest
    ) -> Dict[str, Any]:
        """Validate tenant provisioning request."""
        errors = []
        warnings = []
        
        # Check tenant name availability
        existing_tenant = await self.tenant_repo.get_by_slug(request.slug)
        if existing_tenant:
            errors.append(f"Tenant slug '{request.slug}' is already in use")
        
        # Validate domain name format
        if not request.slug.replace("-", "").replace("_", "").isalnum():
            errors.append("Tenant slug must contain only alphanumeric characters, hyphens, and underscores")
        
        # Check email domain
        email_domain = request.primary_contact_email.split("@")[1]
        if email_domain in ["example.com", "test.com", "localhost"]:
            warnings.append(f"Email domain '{email_domain}' appears to be a test domain")
        
        # Validate infrastructure requirements
        if request.infrastructure_config:
            if request.infrastructure_config.expected_users > 10000:
                warnings.append("Large user count detected - consider premium infrastructure")
            
            if request.infrastructure_config.estimated_bandwidth_gb > 1000:
                warnings.append("High bandwidth requirements - ensure adequate infrastructure tier")
        
        # Check billing configuration
        if request.billing_config and request.billing_config.payment_method:
            # Validate payment method with Stripe (in real implementation)
            pass
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "validation_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _create_tenant_record():
        self, 
        request: TenantProvisioningRequest, 
        user_id: str
    ) -> Tenant:
        """Create initial tenant database record."""
        tenant_data = TenantCreate()
            name=request.name,
            slug=request.slug,
            display_name=request.display_name,
            description=request.description,
            primary_contact_email=request.primary_contact_email,
            billing_email=request.billing_email or request.primary_contact_email,
            phone=request.phone,
            website=request.website,
            billing_address=request.billing_address,
            tier=request.tier or "standard",
            status=TenantStatus.PROVISIONING,
            settings={
                "provisioning_request": request.model_dump(),
                "provisioning_started_at": datetime.now(timezone.utc).isoformat(),
                "provisioned_by": user_id
            }
        )
        
        return await self.tenant_repo.create(tenant_data, user_id)
    
    async def _setup_tenant_billing():
        self, 
        tenant: Tenant, 
        request: TenantProvisioningRequest
    ) -> Dict[str, Any]:
        """Set up Stripe billing for tenant."""
        try:
            # Create Stripe customer
            stripe_customer = await self.stripe_service.create_customer()
                tenant_id=tenant.id,
                email=tenant.billing_email,
                name=tenant.name,
                metadata={
                    "tenant_slug": tenant.slug,
                    "tier": tenant.tier
                )
            )
            
            # Update tenant with Stripe customer ID
            await self.tenant_repo.update()
                tenant.id,
                {"stripe_customer_id": stripe_customer["stripe_customer_id"]},
                "provisioning_service"
            )
            
            # Set up subscription if billing config provided
            subscription_result = None
            if request.billing_config and request.billing_config.pricing_plan_id:
                # This would create subscription based on pricing plan
                subscription_result = {
                    "pricing_plan_id": request.billing_config.pricing_plan_id,
                    "trial_days": request.billing_config.trial_days
                }
            
            return {
                "stripe_customer_id": stripe_customer["stripe_customer_id"],
                "subscription": subscription_result,
                "billing_setup_completed": True
            }
            
        except Exception as e:
            logger.error(f"Billing setup failed for tenant {tenant.id}: {e}")
            raise ProvisioningError()
                f"Failed to set up billing: {str(e)}",
                ProvisioningStage.CREATING_BILLING,
                {"tenant_id": str(tenant.id), "error": str(e)}
            )
    
    async def _provision_infrastructure():
        self, 
        tenant: Tenant, 
        request: TenantProvisioningRequest
    ) -> Dict[str, Any]:
        """Provision cloud infrastructure for tenant."""
        try:
            infrastructure_config = request.infrastructure_config or {}
            
            # Determine infrastructure requirements
            infrastructure_spec = {
                "tenant_id": str(tenant.id),
                "tenant_slug": tenant.slug,
                "region": infrastructure_config.get("preferred_region", "us-east-1"),
                "instance_type": self._determine_instance_type()
                    infrastructure_config.get("expected_users", 100),
                    infrastructure_config.get("estimated_bandwidth_gb", 10)
                ),
                "storage_size": max()
                    infrastructure_config.get("estimated_storage_gb", 50), 
                    20  # Minimum 20GB
                ),
                "backup_retention": infrastructure_config.get("backup_retention_days", 30),
                "high_availability": infrastructure_config.get("high_availability", False)
            )
            
            # Provision infrastructure
            infrastructure_result = await self.infrastructure_service.provision_tenant_infrastructure()
                infrastructure_spec
            )
            
            # Store infrastructure details
            await self.tenant_repo.update()
                tenant.id,
                {
                    "infrastructure_config": infrastructure_spec,
                    "infrastructure_status": "provisioned",
                    "infrastructure_details": infrastructure_result
                },
                "provisioning_service"
            )
            
            return infrastructure_result
            
        except Exception as e:
            logger.error(f"Infrastructure provisioning failed for tenant {tenant.id}: {e}")
            raise ProvisioningError()
                f"Failed to provision infrastructure: {str(e)}",
                ProvisioningStage.PROVISIONING_INFRASTRUCTURE,
                {"tenant_id": str(tenant.id), "error": str(e)}
            )
    
    async def _configure_dns():
        self, 
        tenant: Tenant, 
        request: TenantProvisioningRequest
    ) -> Dict[str, Any]:
        """Configure DNS records and SSL certificates."""
        try:
            dns_config = {
                "tenant_slug": tenant.slug,
                "primary_domain": f"{tenant.slug}.{settings.base_domain}",
                "admin_domain": f"{tenant.slug}-admin.{settings.base_domain}",
                "api_domain": f"{tenant.slug}-api.{settings.base_domain}",
                "custom_domain": request.custom_domain
            }
            
            # Configure DNS records
            dns_result = await self.dns_service.configure_tenant_dns(dns_config)
            
            # Request SSL certificates
            ssl_result = await self.dns_service.provision_ssl_certificates([)
                dns_config["primary_domain"],
                dns_config["admin_domain"], 
                dns_config["api_domain"]
            ])
            
            # Update tenant with DNS configuration
            await self.tenant_repo.update()
                tenant.id,
                {
                    "custom_domain": dns_config["primary_domain"],
                    "dns_config": dns_config,
                    "ssl_certificates": ssl_result
                },
                "provisioning_service"
            )
            
            return {
                "dns_records": dns_result,
                "ssl_certificates": ssl_result,
                "primary_url": f"https://{dns_config['primary_domain']}",
                "admin_url": f"https://{dns_config['admin_domain']}"
            }
            
        except Exception as e:
            logger.error(f"DNS configuration failed for tenant {tenant.id}: {e}")
            raise ProvisioningError()
                f"Failed to configure DNS: {str(e)}",
                ProvisioningStage.CONFIGURING_DNS,
                {"tenant_id": str(tenant.id), "error": str(e)}
            )
    
    async def _deploy_tenant_services():
        self, 
        tenant: Tenant, 
        request: TenantProvisioningRequest
    ) -> Dict[str, Any]:
        """Deploy DotMac ISP Framework services for tenant."""
        try:
            # Create deployment record
            deployment_data = DeploymentCreate()
                tenant_id=tenant.id,
                template_id=None,  # Would use appropriate template
                configuration={
                    "tenant_slug": tenant.slug,
                    "services": request.service_config or {},
                    "features": request.features or {},
                    "environment": "production"
                },
                deployment_type="full_stack",
                status=DeploymentStatus.PENDING
            )
            
            deployment = await self.deployment_repo.create(deployment_data, "provisioning_service")
            
            # Deploy core services
            core_services = [
                "dotmac_core_events",
                "dotmac_identity", 
                "dotmac_billing",
                "dotmac_services",
                "dotmac_networking",
                "dotmac_api_gateway",
                "dotmac_platform"
            ]
            
            service_results = {}
            for service in core_services:
                service_result = await self._deploy_individual_service()
                    tenant, service, deployment.configuration
                )
                service_results[service] = service_result
                
                # Wait briefly between deployments
                await asyncio.sleep(2)
            
            # Update deployment status
            await self.deployment_repo.update()
                deployment.id,
                {
                    "status": DeploymentStatus.COMPLETED,
                    "deployed_at": datetime.now(timezone.utc),
                    "deployment_results": service_results
                },
                "provisioning_service"
            )
            
            return {
                "deployment_id": str(deployment.id),
                "services_deployed": core_services,
                "service_results": service_results,
                "deployment_completed_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Service deployment failed for tenant {tenant.id}: {e}")
            raise ProvisioningError()
                f"Failed to deploy services: {str(e)}",
                ProvisioningStage.DEPLOYING_SERVICES,
                {"tenant_id": str(tenant.id), "error": str(e)}
            )
    
    async def _deploy_individual_service():
        self, 
        tenant: Tenant, 
        service_name: str, 
        configuration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deploy individual DotMac service."""
        logger.info(f"Deploying {service_name} for tenant {tenant.slug}")
        
        # Service-specific configuration
        service_config = {
            "tenant_id": str(tenant.id),
            "tenant_slug": tenant.slug,
            "service_name": service_name,
            "database_url": f"postgresql://tenant_{tenant.slug}:password@db/{service_name}",
            "redis_url": f"redis://redis:6379/{tenant.id.int % 16}",  # Use tenant-specific Redis DB
            "environment": "production",
            **configuration
        }
        
        # Simulate service deployment (in real implementation, this would use K8s API)
        await asyncio.sleep(1)  # Simulate deployment time
        
        return {
            "service": service_name,
            "status": "deployed",
            "endpoint": f"https://{tenant.slug}-api.{settings.base_domain}/{service_name}",
            "health_check": f"https://{tenant.slug}-api.{settings.base_domain}/{service_name}/health",
            "deployed_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def _configure_monitoring(self, tenant: Tenant) -> Dict[str, Any]:
        """Configure monitoring and alerting for tenant."""
        try:
            monitoring_config = {
                "tenant_id": str(tenant.id),
                "tenant_slug": tenant.slug,
                "metrics_retention": "30d",
                "log_retention": "7d",
                "alerting_enabled": True,
                "alert_channels": [
                    {
                        "type": "email",
                        "destination": tenant.primary_contact_email
                    }
                ]
            }
            
            # Set up Prometheus targets
            prometheus_config = await self._configure_prometheus_monitoring(tenant, monitoring_config)
            
            # Configure Grafana dashboards
            grafana_config = await self._configure_grafana_dashboards(tenant, monitoring_config)
            
            # Set up alerting rules
            alerting_config = await self._configure_alerting_rules(tenant, monitoring_config)
            
            return {
                "monitoring_configured": True,
                "prometheus": prometheus_config,
                "grafana": grafana_config,
                "alerting": alerting_config
            }
            
        except Exception as e:
            logger.error(f"Monitoring configuration failed for tenant {tenant.id}: {e}")
            raise ProvisioningError()
                f"Failed to configure monitoring: {str(e)}",
                ProvisioningStage.CONFIGURING_MONITORING,
                {"tenant_id": str(tenant.id), "error": str(e)}
            )
    
    async def _finalize_tenant_provisioning(self, tenant: Tenant) -> None:
        """Finalize tenant provisioning."""
        # Update tenant status
        await self.tenant_repo.update()
            tenant.id,
            {
                "status": TenantStatus.ACTIVE,
                "activated_at": datetime.now(timezone.utc),
                "provisioning_completed_at": datetime.now(timezone.utc)
            },
            "provisioning_service"
        )
        
        # Create initial admin user (would be implemented)
        # await self._create_initial_admin_user(tenant)
        
        # Set up default configurations
        await self._apply_default_tenant_settings(tenant)
    
    async def _determine_instance_type(self, expected_users: int, bandwidth_gb: int) -> str:
        """Determine appropriate infrastructure instance type."""
        if expected_users <= 100 and bandwidth_gb <= 50:
            return "small"
        elif expected_users <= 500 and bandwidth_gb <= 200:
            return "medium"
        elif expected_users <= 2000 and bandwidth_gb <= 500:
            return "large"
        else:
            return "xlarge"
    
    async def _update_provisioning_status():
        self, 
        provisioning_id: str, 
        stage: ProvisioningStage, 
        message: str
    ) -> None:
        """Update provisioning status for tracking."""
        logger.info(f"Provisioning {provisioning_id}: {stage.value} - {message}")
        # In real implementation, this would update a provisioning status table
    
    async def _handle_provisioning_failure():
        self, 
        provisioning_id: str, 
        stage: ProvisioningStage, 
        error: str
    ) -> None:
        """Handle provisioning failure and cleanup."""
        logger.error(f"Provisioning {provisioning_id} failed at {stage.value}: {error}")
        
        # Mark provisioning as failed
        await self._update_provisioning_status()
            provisioning_id, ProvisioningStage.FAILED, f"Failed: {error}"
        )
        
        # Trigger cleanup process
        # await self._cleanup_failed_provisioning(provisioning_id)
    
    async def _send_provisioning_complete_notification():
        self, 
        tenant: Tenant, 
        request: TenantProvisioningRequest
    ) -> None:
        """Send provisioning completion notification."""
        await self.notification_service.send_email()
            to_email=tenant.primary_contact_email,
            subject=f"Welcome to DotMac ISP Framework - {tenant.name} is Ready!",
            template="tenant_provisioning_complete",
            context={
                "tenant_name": tenant.name,
                "tenant_url": f"https://{tenant.slug}.{settings.base_domain}",
                "admin_url": f"https://{tenant.slug}-admin.{settings.base_domain}",
                "provisioning_date": datetime.now(timezone.utc).isoformat()
            )
        )
    
    # Helper methods for monitoring configuration
    
    async def _configure_prometheus_monitoring():
        self, 
        tenant: Tenant, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Configure Prometheus monitoring for tenant."""
        # Implementation would configure Prometheus targets
        return {"targets_configured": True, "scrape_interval": "30s"}
    
    async def _configure_grafana_dashboards():
        self, 
        tenant: Tenant, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Configure Grafana dashboards for tenant."""
        # Implementation would create tenant-specific dashboards
        return {"dashboards_created": ["Overview", "Performance", "Billing"]}
    
    async def _configure_alerting_rules():
        self, 
        tenant: Tenant, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Configure alerting rules for tenant."""
        # Implementation would set up alerting rules
        return {"rules_configured": ["HighCPU", "HighMemory", "ServiceDown"]}
    
    async def _apply_default_tenant_settings(self, tenant: Tenant) -> None:
        """Apply default settings to newly provisioned tenant."""
        default_settings = {
            "max_users": 1000,
            "max_storage_gb": 100,
            "backup_enabled": True,
            "monitoring_enabled": True,
            "ssl_enabled": True,
            "cdn_enabled": False
        }
        
        await self.tenant_repo.update()
            tenant.id,
            {"default_settings": default_settings},
            "provisioning_service"
        )