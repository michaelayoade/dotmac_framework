"""
Example usage of enhanced application middleware for DotMac Framework.

Demonstrates:
- Tenant boundary enforcement with gateway header validation
- API versioning with deprecation headers and routing policy
- Background operations with idempotency keys and saga patterns
- Integration with RouterFactory patterns
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Request

from dotmac.security.tenant_isolation import TenantSecurityEnforcer
from dotmac_shared.application.config import (
    DeploymentContext,
    DeploymentMode,
    PlatformConfig,
)
from dotmac_shared.application.middleware import StandardMiddlewareStack
from dotmac_shared.middleware.api_versioning import (
    APIVersionInfo,
    APIVersioningMiddleware,
    VersionStatus,
)
from dotmac_shared.middleware.background_operations import (
    BackgroundOperationsMiddleware,
)

logger = logging.getLogger(__name__)


def create_enhanced_app() -> FastAPI:
    """Create FastAPI app with enhanced middleware stack."""

    # Create FastAPI app
    app = FastAPI(
        title="DotMac Enhanced Application",
        version="1.0.0",
        description="Example application with enhanced middleware",
    )

    # Configure platform settings
    platform_config = PlatformConfig(
        platform_name="example_platform",
        deployment_context=DeploymentContext(
            mode=DeploymentMode.TENANT_CONTAINER, tenant_id="example-tenant-123"
        ),
    )

    # Create enhanced middleware components
    tenant_enforcer = TenantSecurityEnforcer()

    api_versioning = APIVersioningMiddleware(
        default_version="v1",
        supported_versions={
            "v1": APIVersionInfo(version="v1", status=VersionStatus.CURRENT),
            "v2": APIVersionInfo(version="v2", status=VersionStatus.SUPPORTED),
            "v0.9": APIVersionInfo(
                version="v0.9",
                status=VersionStatus.DEPRECATED,
                sunset_date=datetime.now(timezone.utc) + timedelta(days=90),
                replacement_version="v1",
            ),
        },
    )

    background_ops = BackgroundOperationsMiddleware()

    # Create and apply middleware stack
    middleware_stack = StandardMiddlewareStack(
        platform_config=platform_config,
        tenant_security_enforcer=tenant_enforcer,
        api_versioning=api_versioning,
        background_operations=background_ops,
    )

    applied_middleware = middleware_stack.apply_to_app(app)
    logger.info(f"Applied middleware: {applied_middleware}")

    # Register operation handlers for saga workflows
    ops_manager = background_ops.operations_manager
    ops_manager.register_operation_handler("create_customer", create_customer_operation)
    ops_manager.register_operation_handler(
        "provision_service", provision_service_operation
    )
    ops_manager.register_compensation_handler(
        "create_customer", compensate_create_customer
    )
    ops_manager.register_compensation_handler(
        "provision_service", compensate_provision_service
    )

    return app


# Example route handlers with enhanced middleware features
def create_routes(app: FastAPI):
    """Create example routes demonstrating middleware features."""

    @app.get("/api/v1/health")
    async def health_check():
        """Health check endpoint (exempt from tenant enforcement)."""
        return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}

    @app.get("/api/v1/tenant-info")
    async def get_tenant_info(request: Request):
        """Get current tenant information from enforced context."""
        tenant_context = getattr(request.state, "tenant_context", None)
        if not tenant_context:
            raise HTTPException(status_code=400, detail="Tenant context not available")

        return {
            "tenant_id": tenant_context.tenant_id,
            "source": tenant_context.source,
            "validated": tenant_context.validated,
            "gateway_validated": tenant_context.gateway_validated,
        }

    @app.get("/api/v1/version-info")
    async def get_version_info(request: Request):
        """Get API version information."""
        api_version = getattr(request.state, "api_version", "unknown")
        version_info = getattr(request.state, "version_info", None)

        return {
            "api_version": api_version,
            "status": version_info.status if version_info else "unknown",
            "sunset_date": version_info.sunset_date.isoformat()
            if version_info and version_info.sunset_date
            else None,
        }

    @app.post("/api/v1/customers")
    async def create_customer(request: Request, customer_data: dict):
        """Create customer with idempotency support."""
        # Check for idempotency key
        idempotency_key = request.headers.get("Idempotency-Key")
        if idempotency_key:
            ops_manager = getattr(request.state, "operations_manager", None)
            if ops_manager:
                existing = await ops_manager.check_idempotency(idempotency_key)
                if existing and existing.status.value == "completed":
                    return existing.result

        # Process customer creation
        result = {"customer_id": "cust_12345", "status": "created"}

        # Store result for idempotency
        if idempotency_key and ops_manager:
            key_obj = await ops_manager.create_idempotency_key(
                tenant_id=getattr(request.state, "tenant_id", "unknown"),
                user_id="user_123",  # Would come from auth
                operation_type="create_customer",
                key=idempotency_key,
            )
            key_obj.result = result
            key_obj.status = "completed"

        return result

    @app.post("/api/v1/workflows/customer-onboarding")
    async def start_customer_onboarding_saga(request: Request, workflow_data: dict):
        """Start customer onboarding saga workflow."""
        ops_manager = getattr(request.state, "operations_manager", None)
        if not ops_manager:
            raise HTTPException(
                status_code=500, detail="Operations manager not available"
            )

        tenant_id = getattr(request.state, "tenant_id", "unknown")

        # Define saga steps
        saga_steps = [
            {
                "name": "Create Customer Record",
                "operation": "create_customer",
                "parameters": {"customer_data": workflow_data.get("customer", {})},
                "compensation_operation": "create_customer",
                "compensation_parameters": {"customer_id": "to_be_filled"},
            },
            {
                "name": "Provision Service",
                "operation": "provision_service",
                "parameters": {
                    "service_type": workflow_data.get("service_type", "basic")
                },
                "compensation_operation": "provision_service",
                "compensation_parameters": {"service_id": "to_be_filled"},
            },
        ]

        # Create saga workflow
        saga = await ops_manager.create_saga_workflow(
            tenant_id=tenant_id, workflow_type="customer_onboarding", steps=saga_steps
        )

        # Execute asynchronously (in production, use background task queue)
        # For demo purposes, return saga ID
        return {
            "saga_id": saga.saga_id,
            "status": saga.status,
            "steps": len(saga.steps),
            "message": "Workflow started - use GET /api/v1/workflows/{saga_id} to check status",
        }

    @app.get("/api/v1/workflows/{saga_id}")
    async def get_saga_status(saga_id: str, request: Request):
        """Get saga workflow status."""
        ops_manager = getattr(request.state, "operations_manager", None)
        if not ops_manager:
            raise HTTPException(
                status_code=500, detail="Operations manager not available"
            )

        saga = ops_manager.saga_workflows.get(saga_id)
        if not saga:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return {
            "saga_id": saga.saga_id,
            "status": saga.status,
            "current_step": saga.current_step,
            "total_steps": len(saga.steps),
            "steps": [
                {"name": step.name, "status": step.status, "error": step.error}
                for step in saga.steps
            ],
        }


# Example operation handlers for saga workflows
async def create_customer_operation(parameters: dict) -> dict:
    """Example customer creation operation."""
    # Simulate customer creation
    parameters.get("customer_data", {})
    customer_id = f"cust_{datetime.now().timestamp()}"

    logger.info(f"Creating customer: {customer_id}")
    # Here you would call actual customer creation service

    return {"customer_id": customer_id, "status": "created"}


async def provision_service_operation(parameters: dict) -> dict:
    """Example service provisioning operation."""
    service_type = parameters.get("service_type", "basic")
    service_id = f"svc_{datetime.now().timestamp()}"

    logger.info(f"Provisioning service: {service_id} ({service_type})")
    # Here you would call actual service provisioning

    return {"service_id": service_id, "type": service_type, "status": "provisioned"}


async def compensate_create_customer(parameters: dict) -> dict:
    """Compensate customer creation."""
    customer_id = parameters.get("customer_id")
    logger.info(f"Compensating customer creation: {customer_id}")
    # Here you would call customer deletion/cleanup
    return {"status": "compensated"}


async def compensate_provision_service(parameters: dict) -> dict:
    """Compensate service provisioning."""
    service_id = parameters.get("service_id")
    logger.info(f"Compensating service provisioning: {service_id}")
    # Here you would call service deprovisioning
    return {"status": "compensated"}


# Example usage
if __name__ == "__main__":
    # Create enhanced application
    app = create_enhanced_app()
    create_routes(app)

    # Example request headers for testing:
    # X-Tenant-ID: example-tenant-123
    # X-API-Version: v1
    # Idempotency-Key: unique-key-12345

    logger.info("Enhanced application created successfully!")
    logger.info("Example curl commands:")
    logger.info("")
    logger.info("# Health check (no tenant required)")
    logger.info("curl http://localhost:8000/api/v1/health")
    logger.info("")
    logger.info("# Get tenant info (requires X-Tenant-ID header)")
    logger.info(
        "curl -H 'X-Tenant-ID: example-tenant-123' http://localhost:8000/api/v1/tenant-info"
    )
    logger.info("")
    logger.info("# Create customer with idempotency")
    logger.info(
        "curl -X POST -H 'X-Tenant-ID: example-tenant-123' -H 'Idempotency-Key: unique-key-1' \\"
    )
    logger.info("     -H 'Content-Type: application/json' \\")
    logger.info('     -d \'{"name": "John Doe", "email": "john@example.com"}\' \\')
    logger.info("     http://localhost:8000/api/v1/customers")
    logger.info("")
    logger.info("# Start saga workflow")
    logger.info("curl -X POST -H 'X-Tenant-ID: example-tenant-123' \\")
    logger.info("     -H 'Content-Type: application/json' \\")
    logger.info(
        '     -d \'{"customer": {"name": "Jane Doe"}, "service_type": "premium"}\' \\'
    )
    logger.info("     http://localhost:8000/api/v1/workflows/customer-onboarding")
