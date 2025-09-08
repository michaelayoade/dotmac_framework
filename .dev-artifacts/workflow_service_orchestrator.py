"""
Phase 3: Service Layer Orchestrator for Workflow Integration

This demonstrates how service layers should be updated to:
1. Inject saga coordinators and idempotency managers into use cases
2. Handle workflow-aware business operations
3. Provide proper dependency injection patterns
"""

import os
import logging
from typing import Optional, Any
from dataclasses import dataclass

from dotmac_shared.business_logic.sagas import SagaCoordinator
from dotmac_shared.business_logic.idempotency import IdempotencyManager
from src.dotmac_management.use_cases.tenant.provision_tenant import (
    ProvisionTenantUseCase,
    ProvisionTenantInput
)
from src.dotmac_management.use_cases.billing.process_billing import (
    ProcessBillingUseCase,
    ProcessBillingInput
)
from src.dotmac_management.use_cases.base import UseCaseContext

logger = logging.getLogger(__name__)


@dataclass
class WorkflowConfiguration:
    """Configuration for workflow orchestration"""
    workflows_enabled: bool
    saga_coordinator: Optional[SagaCoordinator] = None
    idempotency_manager: Optional[IdempotencyManager] = None


class WorkflowAwareService:
    """
    Base class for services that integrate with workflow orchestration.
    
    Provides dependency injection patterns for saga coordinators
    and idempotency managers into business use cases.
    """
    
    def __init__(self, workflow_config: WorkflowConfiguration):
        self.workflow_config = workflow_config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def _inject_workflow_dependencies(self, use_case) -> None:
        """Inject workflow dependencies into use cases (Phase 3 pattern)"""
        if self.workflow_config.workflows_enabled:
            # Inject saga coordinator if available
            if hasattr(use_case, 'inject_saga_coordinator') and self.workflow_config.saga_coordinator:
                use_case.inject_saga_coordinator(self.workflow_config.saga_coordinator)
                self.logger.debug(f"Injected SagaCoordinator into {use_case.__class__.__name__}")
            
            # Inject idempotency manager if available
            if hasattr(use_case, 'inject_idempotency_manager') and self.workflow_config.idempotency_manager:
                use_case.inject_idempotency_manager(self.workflow_config.idempotency_manager)
                self.logger.debug(f"Injected IdempotencyManager into {use_case.__class__.__name__}")


class TenantProvisioningService(WorkflowAwareService):
    """
    Enhanced tenant provisioning service with workflow orchestration support.
    
    Demonstrates Phase 3 integration patterns:
    - Dependency injection of workflow coordinators
    - Use case orchestration with saga support
    - Proper error handling and monitoring
    """
    
    async def provision_tenant(
        self, 
        tenant_data: dict[str, Any], 
        context: Optional[UseCaseContext] = None
    ) -> dict[str, Any]:
        """
        Provision a new tenant with workflow orchestration support.
        
        This method demonstrates the Phase 3 service layer pattern:
        1. Create the appropriate use case
        2. Inject workflow dependencies
        3. Execute with proper error handling
        4. Return structured results
        """
        
        try:
            # Convert input data to use case format
            provision_input = ProvisionTenantInput(
                tenant_id=tenant_data["tenant_id"],
                company_name=tenant_data["company_name"],
                admin_email=tenant_data["admin_email"],
                admin_name=tenant_data.get("admin_name", ""),
                subdomain=tenant_data["subdomain"],
                plan=tenant_data.get("plan", "starter"),
                region=tenant_data.get("region", "us-east-1"),
                billing_info=tenant_data.get("billing_info", {}),
                notification_preferences=tenant_data.get("notification_preferences", {}),
                custom_configuration=tenant_data.get("custom_configuration", {}),
            )
            
            # Create and configure use case
            use_case = ProvisionTenantUseCase()
            
            # Phase 3: Inject workflow dependencies
            self._inject_workflow_dependencies(use_case)
            
            self.logger.info(
                f"Starting tenant provisioning with workflow orchestration",
                extra={
                    "tenant_id": tenant_data["tenant_id"],
                    "workflows_enabled": self.workflow_config.workflows_enabled,
                    "has_saga_coordinator": self.workflow_config.saga_coordinator is not None,
                    "has_idempotency_manager": self.workflow_config.idempotency_manager is not None,
                }
            )
            
            # Execute the use case
            result = await use_case.execute(provision_input, context)
            
            if result.success:
                self.logger.info(
                    f"Tenant provisioning initiated successfully",
                    extra={
                        "tenant_id": tenant_data["tenant_id"],
                        "orchestration_method": result.metadata.get("orchestration_method", "direct"),
                        "saga_id": result.metadata.get("saga_id"),
                    }
                )
                
                return {
                    "success": True,
                    "tenant_id": result.data.tenant_id,
                    "status": result.data.status.value,
                    "domain": result.data.domain,
                    "admin_portal_url": result.data.admin_portal_url,
                    "provisioning_summary": result.data.provisioning_summary,
                    "orchestration_metadata": result.metadata,
                }
            else:
                return {
                    "success": False,
                    "error": result.error,
                    "error_code": result.error_code,
                }
                
        except Exception as e:
            self.logger.error(f"Tenant provisioning service failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "SERVICE_EXECUTION_ERROR",
            }


class BillingService(WorkflowAwareService):
    """
    Enhanced billing service with idempotency and workflow orchestration.
    
    Demonstrates Phase 3 patterns for critical operations that require
    exactly-once execution guarantees.
    """
    
    async def process_billing(
        self,
        billing_data: dict[str, Any],
        context: Optional[UseCaseContext] = None
    ) -> dict[str, Any]:
        """
        Process billing operations with idempotency guarantees.
        
        Critical billing operations (payments, invoice generation) use
        idempotency to prevent duplicate processing.
        """
        
        try:
            # Convert to use case input format
            from src.dotmac_management.use_cases.billing.process_billing import BillingOperation
            
            billing_input = ProcessBillingInput(
                tenant_id=billing_data["tenant_id"],
                operation=BillingOperation(billing_data["operation"]),
                billing_period_start=billing_data["billing_period_start"],
                billing_period_end=billing_data["billing_period_end"],
                parameters=billing_data.get("parameters", {}),
            )
            
            # Create and configure use case
            use_case = ProcessBillingUseCase(billing_data)
            
            # Phase 3: Inject workflow dependencies
            self._inject_workflow_dependencies(use_case)
            
            self.logger.info(
                f"Processing billing operation with workflow orchestration",
                extra={
                    "tenant_id": billing_data["tenant_id"],
                    "operation": billing_data["operation"],
                    "workflows_enabled": self.workflow_config.workflows_enabled,
                    "has_idempotency": self.workflow_config.idempotency_manager is not None,
                }
            )
            
            # Execute the use case
            result = await use_case.execute(billing_input, context)
            
            if result.success:
                return {
                    "success": True,
                    "tenant_id": result.data.tenant_id,
                    "operation": result.data.operation.value,
                    "total": float(result.data.total),
                    "invoice_id": result.data.invoice_id,
                    "payment_status": result.data.payment_status,
                    "idempotency_metadata": {
                        "idempotency_key": result.metadata.get("idempotency_key"),
                        "from_cache": result.metadata.get("from_cache", False),
                        "execution_method": result.metadata.get("execution_method"),
                    }
                }
            else:
                return {
                    "success": False,
                    "error": result.error,
                    "error_code": result.error_code,
                }
                
        except Exception as e:
            self.logger.error(f"Billing service failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "BILLING_SERVICE_ERROR",
            }


class WorkflowOrchestrationFactory:
    """
    Factory for creating workflow-aware services with proper dependency injection.
    
    This demonstrates how to bootstrap services with workflow orchestration
    in the Phase 3 integration pattern.
    """
    
    @classmethod
    def create_from_app_state(cls, app_state) -> WorkflowConfiguration:
        """Create workflow configuration from FastAPI app state (Phase 2 integration)"""
        workflows_enabled = os.getenv("BUSINESS_LOGIC_WORKFLOWS_ENABLED", "false").lower() == "true"
        
        saga_coordinator = None
        idempotency_manager = None
        
        if workflows_enabled and hasattr(app_state, 'saga_coordinator'):
            saga_coordinator = app_state.saga_coordinator
            
        if workflows_enabled and hasattr(app_state, 'idempotency_manager'):
            idempotency_manager = app_state.idempotency_manager
            
        return WorkflowConfiguration(
            workflows_enabled=workflows_enabled,
            saga_coordinator=saga_coordinator,
            idempotency_manager=idempotency_manager,
        )
    
    @classmethod
    def create_tenant_provisioning_service(cls, workflow_config: WorkflowConfiguration) -> TenantProvisioningService:
        """Create a workflow-aware tenant provisioning service"""
        return TenantProvisioningService(workflow_config)
    
    @classmethod
    def create_billing_service(cls, workflow_config: WorkflowConfiguration) -> BillingService:
        """Create a workflow-aware billing service"""
        return BillingService(workflow_config)


# Example usage in FastAPI route handlers
def demonstrate_service_layer_integration():
    """
    Example showing how FastAPI routes should integrate with workflow-aware services.
    
    This pattern should be used in actual route handlers in main.py or router files.
    """
    
    async def tenant_provisioning_endpoint(tenant_data: dict, app_state):
        """Example tenant provisioning endpoint with Phase 3 integration"""
        
        # Create workflow configuration from app state (Phase 2 components)
        workflow_config = WorkflowOrchestrationFactory.create_from_app_state(app_state)
        
        # Create workflow-aware service
        provisioning_service = WorkflowOrchestrationFactory.create_tenant_provisioning_service(workflow_config)
        
        # Create execution context
        context = UseCaseContext(
            tenant_id=tenant_data.get("tenant_id"),
            user_id=tenant_data.get("user_id"),
            correlation_id=f"api-{tenant_data['tenant_id']}-provision"
        )
        
        # Execute with workflow orchestration
        result = await provisioning_service.provision_tenant(tenant_data, context)
        
        return result
    
    async def billing_processing_endpoint(billing_data: dict, app_state):
        """Example billing endpoint with Phase 3 idempotency integration"""
        
        # Create workflow configuration
        workflow_config = WorkflowOrchestrationFactory.create_from_app_state(app_state)
        
        # Create workflow-aware service  
        billing_service = WorkflowOrchestrationFactory.create_billing_service(workflow_config)
        
        # Create execution context
        context = UseCaseContext(
            tenant_id=billing_data["tenant_id"],
            user_id=billing_data.get("user_id"),
            correlation_id=f"api-{billing_data['tenant_id']}-billing-{billing_data['operation']}"
        )
        
        # Execute with idempotency
        result = await billing_service.process_billing(billing_data, context)
        
        return result

    return tenant_provisioning_endpoint, billing_processing_endpoint


if __name__ == "__main__":
    # Demonstration of the Phase 3 integration pattern
    print("Phase 3: Workflow orchestration service layer integration")
    print("This file demonstrates how to:")
    print("1. Inject saga coordinators and idempotency managers into use cases")
    print("2. Create workflow-aware services that orchestrate business operations")
    print("3. Provide proper dependency injection patterns for Phase 3")
    print("")
    print("Key patterns:")
    print("- WorkflowConfiguration for dependency management")
    print("- WorkflowAwareService base class for injection")
    print("- Service-specific implementations (TenantProvisioningService, BillingService)")
    print("- Factory pattern for creating configured services")
    print("- Integration examples for FastAPI route handlers")