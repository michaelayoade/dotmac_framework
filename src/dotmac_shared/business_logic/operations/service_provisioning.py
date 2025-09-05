"""
Service Provisioning Operations

Idempotent operations and saga orchestration for service provisioning
including resource allocation, configuration, and activation.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

from ...standard_exception_handler import standard_exception_handler
from ..exceptions import ErrorContext, ProvisioningError
from ..idempotency import IdempotentOperation
from ..sagas import CompensationHandler, SagaContext, SagaDefinition, SagaStep


class ValidateServiceRequestStep(SagaStep):
    """Step to validate service provisioning request"""

    def __init__(self):
        super().__init__(
            name="validate_service_request",
            timeout_seconds=30,
            retry_count=3,
            compensation_required=False,  # Validation doesn't need compensation
        )

    @standard_exception_handler
    async def execute(self, context: SagaContext) -> dict[str, Any]:
        """Validate service request"""
        service_request = context.get_shared_data("service_request")

        # Validate required fields
        required_fields = ["customer_id", "service_type", "plan", "billing_period"]
        for field in required_fields:
            if field not in service_request:
                raise ValueError(f"Missing required field: {field}")

        # Validate service type
        valid_service_types = ["internet", "hosting", "voip", "security"]
        if service_request["service_type"] not in valid_service_types:
            raise ValueError(f"Invalid service type: {service_request['service_type']}")

        # Validate plan
        valid_plans = ["basic", "standard", "premium", "enterprise"]
        if service_request["plan"] not in valid_plans:
            raise ValueError(f"Invalid plan: {service_request['plan']}")

        # Check customer eligibility (placeholder logic)
        customer_id = service_request["customer_id"]

        validation_result = {
            "customer_id": customer_id,
            "service_type": service_request["service_type"],
            "plan": service_request["plan"],
            "validated_at": datetime.utcnow().isoformat(),
            "eligibility_status": "eligible",
            "estimated_setup_time_minutes": 30,
        }

        context.set_shared_data("validation_result", validation_result)

        await asyncio.sleep(0.1)  # Simulate validation

        return validation_result

    @standard_exception_handler
    async def compensate(self, context: SagaContext) -> None:
        """No compensation needed for validation"""
        pass


class AllocateResourcesStep(SagaStep):
    """Step to allocate resources for service"""

    def __init__(self):
        super().__init__(
            name="allocate_resources",
            timeout_seconds=60,
            retry_count=2,
            compensation_required=True,
        )

    @standard_exception_handler
    async def execute(self, context: SagaContext) -> dict[str, Any]:
        """Allocate resources for service"""
        service_request = context.get_shared_data("service_request")
        context.get_shared_data("validation_result")

        service_type = service_request["service_type"]
        plan = service_request["plan"]

        # Determine resource requirements based on service and plan
        resource_specs = self._get_resource_specs(service_type, plan)

        # Simulate resource allocation
        allocated_resources = {
            "service_id": str(uuid4()),
            "service_type": service_type,
            "plan": plan,
            "resources": resource_specs,
            "allocation_id": str(uuid4()),
            "allocated_at": datetime.utcnow().isoformat(),
            "status": "allocated",
            "expires_if_not_configured": (
                datetime.utcnow() + timedelta(hours=2)
            ).isoformat(),
        }

        context.set_shared_data("allocated_resources", allocated_resources)

        await asyncio.sleep(0.2)  # Simulate allocation process

        return allocated_resources

    def _get_resource_specs(self, service_type: str, plan: str) -> dict[str, Any]:
        """Get resource specifications for service type and plan"""

        base_specs = {
            "internet": {
                "basic": {"bandwidth_mbps": 50, "data_limit_gb": 500},
                "standard": {"bandwidth_mbps": 100, "data_limit_gb": 1000},
                "premium": {"bandwidth_mbps": 500, "data_limit_gb": 5000},
                "enterprise": {"bandwidth_mbps": 1000, "data_limit_gb": "unlimited"},
            },
            "hosting": {
                "basic": {"cpu_cores": 1, "ram_gb": 2, "storage_gb": 50},
                "standard": {"cpu_cores": 2, "ram_gb": 4, "storage_gb": 100},
                "premium": {"cpu_cores": 4, "ram_gb": 8, "storage_gb": 200},
                "enterprise": {"cpu_cores": 8, "ram_gb": 16, "storage_gb": 500},
            },
            "voip": {
                "basic": {"concurrent_calls": 5, "features": ["basic_forwarding"]},
                "standard": {
                    "concurrent_calls": 15,
                    "features": ["forwarding", "voicemail"],
                },
                "premium": {
                    "concurrent_calls": 50,
                    "features": ["forwarding", "voicemail", "conference"],
                },
                "enterprise": {"concurrent_calls": 200, "features": ["all"]},
            },
            "security": {
                "basic": {"endpoints": 10, "features": ["antivirus"]},
                "standard": {"endpoints": 50, "features": ["antivirus", "firewall"]},
                "premium": {
                    "endpoints": 200,
                    "features": ["antivirus", "firewall", "threat_detection"],
                },
                "enterprise": {"endpoints": 1000, "features": ["all"]},
            },
        }

        return base_specs.get(service_type, {}).get(plan, {})

    @standard_exception_handler
    async def compensate(self, context: SagaContext) -> None:
        """Release allocated resources"""
        allocated_resources = context.get_shared_data("allocated_resources")

        if allocated_resources:
            # Simulate resource deallocation
            await asyncio.sleep(0.1)

            context.set_shared_data(
                "resources_released",
                {
                    "allocation_id": allocated_resources["allocation_id"],
                    "released_at": datetime.utcnow().isoformat(),
                },
            )


class ConfigureServiceStep(SagaStep):
    """Step to configure the allocated service"""

    def __init__(self):
        super().__init__(
            name="configure_service",
            timeout_seconds=120,
            retry_count=2,
            compensation_required=True,
        )

    @standard_exception_handler
    async def execute(self, context: SagaContext) -> dict[str, Any]:
        """Configure service with allocated resources"""
        service_request = context.get_shared_data("service_request")
        allocated_resources = context.get_shared_data("allocated_resources")

        service_id = allocated_resources["service_id"]
        customer_id = service_request["customer_id"]

        # Generate service configuration
        service_config = {
            "service_id": service_id,
            "customer_id": customer_id,
            "service_type": service_request["service_type"],
            "plan": service_request["plan"],
            "configuration": {
                "auto_generated_config": True,
                "config_version": "1.0.0",
                **allocated_resources["resources"],
            },
            "network_settings": self._generate_network_settings(
                service_request["service_type"]
            ),
            "billing_settings": {
                "billing_period": service_request["billing_period"],
                "next_billing_date": (datetime.utcnow() + timedelta(days=30))
                .date()
                .isoformat(),
                "setup_fee": self._calculate_setup_fee(service_request["plan"]),
                "monthly_fee": self._calculate_monthly_fee(
                    service_request["service_type"], service_request["plan"]
                ),
            },
            "configured_at": datetime.utcnow().isoformat(),
            "status": "configured",
        }

        context.set_shared_data("service_config", service_config)

        await asyncio.sleep(0.3)  # Simulate configuration process

        return service_config

    def _generate_network_settings(self, service_type: str) -> dict[str, Any]:
        """Generate network settings based on service type"""

        if service_type == "internet":
            return {
                "gateway_ip": "192.168.1.1",
                "dns_servers": ["8.8.8.8", "8.8.4.4"],
                "vlan_id": 100 + hash(str(uuid4())) % 900,  # Random VLAN
            }
        elif service_type == "hosting":
            return {
                "server_ip": "10.0.1." + str(2 + hash(str(uuid4())) % 253),
                "domain_settings": {"dns_zone": "example.com", "ttl": 300},
            }
        elif service_type == "voip":
            return {"sip_server": "sip.provider.com", "port": 5060, "codec": "G.711"}
        else:
            return {}

    def _calculate_setup_fee(self, plan: str) -> float:
        """Calculate setup fee based on plan"""
        setup_fees = {
            "basic": 25.00,
            "standard": 50.00,
            "premium": 100.00,
            "enterprise": 250.00,
        }
        return setup_fees.get(plan, 25.00)

    def _calculate_monthly_fee(self, service_type: str, plan: str) -> float:
        """Calculate monthly fee based on service type and plan"""

        pricing_matrix = {
            "internet": {
                "basic": 49.99,
                "standard": 79.99,
                "premium": 129.99,
                "enterprise": 299.99,
            },
            "hosting": {
                "basic": 9.99,
                "standard": 24.99,
                "premium": 49.99,
                "enterprise": 199.99,
            },
            "voip": {
                "basic": 19.99,
                "standard": 39.99,
                "premium": 79.99,
                "enterprise": 199.99,
            },
            "security": {
                "basic": 14.99,
                "standard": 29.99,
                "premium": 59.99,
                "enterprise": 149.99,
            },
        }

        return pricing_matrix.get(service_type, {}).get(plan, 49.99)

    @standard_exception_handler
    async def compensate(self, context: SagaContext) -> None:
        """Remove service configuration"""
        service_config = context.get_shared_data("service_config")

        if service_config:
            # Simulate configuration removal
            await asyncio.sleep(0.1)

            context.set_shared_data(
                "service_unconfigured",
                {
                    "service_id": service_config["service_id"],
                    "unconfigured_at": datetime.utcnow().isoformat(),
                },
            )


class ActivateServiceStep(SagaStep):
    """Step to activate the configured service"""

    def __init__(self):
        super().__init__(
            name="activate_service",
            timeout_seconds=60,
            retry_count=3,
            compensation_required=True,
        )

    @standard_exception_handler
    async def execute(self, context: SagaContext) -> dict[str, Any]:
        """Activate the service"""
        service_config = context.get_shared_data("service_config")

        service_id = service_config["service_id"]

        # Activate service
        activation_result = {
            "service_id": service_id,
            "customer_id": service_config["customer_id"],
            "status": "active",
            "activated_at": datetime.utcnow().isoformat(),
            "service_start_date": datetime.utcnow().date().isoformat(),
            "access_details": {
                "service_url": f"https://portal.provider.com/service/{service_id}",
                "account_number": f"ACC-{service_id[:8].upper()}",
                "support_reference": f"REF-{service_id[:12].upper()}",
            },
            "billing_account_created": True,
            "monitoring_enabled": True,
        }

        context.set_shared_data("activation_result", activation_result)

        await asyncio.sleep(0.2)  # Simulate activation

        return activation_result

    @standard_exception_handler
    async def compensate(self, context: SagaContext) -> None:
        """Deactivate service"""
        activation_result = context.get_shared_data("activation_result")

        if activation_result:
            # Simulate service deactivation
            await asyncio.sleep(0.1)

            context.set_shared_data(
                "service_deactivated",
                {
                    "service_id": activation_result["service_id"],
                    "deactivated_at": datetime.utcnow().isoformat(),
                    "billing_stopped": True,
                },
            )


class NotifyCustomerStep(SagaStep):
    """Step to notify customer of service activation"""

    def __init__(self):
        super().__init__(
            name="notify_customer",
            timeout_seconds=30,
            retry_count=3,
            compensation_required=False,  # Notification doesn't need compensation
        )

    @standard_exception_handler
    async def execute(self, context: SagaContext) -> dict[str, Any]:
        """Send activation notification to customer"""
        service_request = context.get_shared_data("service_request")
        activation_result = context.get_shared_data("activation_result")
        service_config = context.get_shared_data("service_config")

        customer_id = service_request["customer_id"]
        service_id = activation_result["service_id"]

        # Prepare notification content
        notification_data = {
            "customer_id": customer_id,
            "service_id": service_id,
            "notification_type": "service_activation",
            "subject": f"Your {service_request['service_type'].title()} Service is Now Active",
            "message": {
                "service_type": service_request["service_type"],
                "plan": service_request["plan"],
                "activation_date": activation_result["activated_at"],
                "access_details": activation_result["access_details"],
                "billing_info": {
                    "next_billing_date": service_config["billing_settings"][
                        "next_billing_date"
                    ],
                    "monthly_fee": service_config["billing_settings"]["monthly_fee"],
                },
            },
            "channels": ["email", "sms"],
            "sent_at": datetime.utcnow().isoformat(),
            "delivery_status": "sent",
        }

        context.set_shared_data("notification_sent", notification_data)

        await asyncio.sleep(0.1)  # Simulate notification sending

        return {
            "notification_id": str(uuid4()),
            "customer_id": customer_id,
            "channels_sent": ["email", "sms"],
            "sent_at": notification_data["sent_at"],
        }

    @standard_exception_handler
    async def compensate(self, context: SagaContext) -> None:
        """No compensation needed for notifications"""
        pass


class ServiceProvisioningCompensationHandler(CompensationHandler):
    """Custom compensation handler for service provisioning"""

    @standard_exception_handler
    async def compensate(
        self, context: SagaContext, failed_step: str, completed_steps: list[str]
    ) -> None:
        """Execute custom compensation logic"""

        service_request = context.get_shared_data("service_request")

        # Log compensation details
        compensation_log = {
            "customer_id": service_request.get("customer_id"),
            "service_type": service_request.get("service_type"),
            "failed_step": failed_step,
            "completed_steps": completed_steps,
            "compensation_started_at": datetime.utcnow().isoformat(),
        }

        context.set_shared_data("compensation_log", compensation_log)

        # Send failure notification to customer if service was partially provisioned
        if "activate_service" in completed_steps:
            await self._send_failure_notification(context, service_request)

        # Clean up any external system registrations
        await self._cleanup_external_systems(context)

        context.set_shared_data("custom_compensation_completed", True)

    async def _send_failure_notification(
        self, context: SagaContext, service_request: dict[str, Any]
    ) -> None:
        """Send failure notification to customer"""

        failure_notification = {
            "customer_id": service_request.get("customer_id"),
            "notification_type": "service_provisioning_failed",
            "subject": "Service Provisioning Issue",
            "message": "We encountered an issue while setting up your service. Our team has been notified.",
            "sent_at": datetime.utcnow().isoformat(),
        }

        context.set_shared_data("failure_notification", failure_notification)
        await asyncio.sleep(0.1)  # Simulate sending

    async def _cleanup_external_systems(self, context: SagaContext) -> None:
        """Clean up registrations in external systems"""

        # Simulate cleanup in monitoring, billing, etc.
        cleanup_result = {
            "monitoring_cleanup": True,
            "billing_cleanup": True,
            "cleanup_completed_at": datetime.utcnow().isoformat(),
        }

        context.set_shared_data("external_cleanup", cleanup_result)
        await asyncio.sleep(0.1)  # Simulate cleanup


class ServiceProvisioningOperation(IdempotentOperation[dict[str, Any]]):
    """Idempotent service provisioning operation"""

    def __init__(self):
        super().__init__(
            operation_type="service_provisioning",
            max_attempts=2,
            timeout_seconds=600,  # 10 minutes
            ttl_seconds=7200,  # 2 hours
        )

    def validate_operation_data(self, operation_data: dict[str, Any]) -> None:
        """Validate service provisioning request data"""

        required_fields = ["customer_id", "service_type", "plan", "billing_period"]

        for field in required_fields:
            if field not in operation_data:
                raise ValueError(f"Missing required field: {field}")

        # Validate service type
        valid_service_types = ["internet", "hosting", "voip", "security"]
        if operation_data["service_type"] not in valid_service_types:
            raise ValueError(f"Invalid service type: {operation_data['service_type']}")

        # Validate plan
        valid_plans = ["basic", "standard", "premium", "enterprise"]
        if operation_data["plan"] not in valid_plans:
            raise ValueError(f"Invalid plan: {operation_data['plan']}")

        # Validate billing period
        valid_periods = ["monthly", "quarterly", "annual"]
        if operation_data["billing_period"] not in valid_periods:
            raise ValueError(
                f"Invalid billing period: {operation_data['billing_period']}"
            )

    @standard_exception_handler
    async def execute(
        self, operation_data: dict[str, Any], context: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Execute service provisioning via saga orchestration"""

        context = context or {}

        # Create saga context
        saga_context = SagaContext(
            saga_id=str(uuid4()),
            tenant_id=context.get("tenant_id", "system"),
            user_id=context.get("user_id"),
            correlation_id=context.get("correlation_id", str(uuid4())),
        )

        # Store operation data in saga context
        saga_context.set_shared_data("service_request", operation_data)
        saga_context.set_shared_data("operation_context", context)

        try:
            # Execute steps sequentially (simplified saga execution)
            steps = [
                ValidateServiceRequestStep(),
                AllocateResourcesStep(),
                ConfigureServiceStep(),
                ActivateServiceStep(),
                NotifyCustomerStep(),
            ]

            step_results = {}

            for step in steps:
                result = await step.execute(saga_context)
                step_results[step.name] = result

            # Return consolidated result
            activation_result = saga_context.get_shared_data("activation_result")
            service_config = saga_context.get_shared_data("service_config")

            return {
                "service_id": activation_result["service_id"],
                "customer_id": operation_data["customer_id"],
                "status": "provisioned",
                "service_type": operation_data["service_type"],
                "plan": operation_data["plan"],
                "provisioning_completed_at": datetime.utcnow().isoformat(),
                "step_results": step_results,
                "service_details": {
                    "access_details": activation_result["access_details"],
                    "billing_settings": service_config["billing_settings"],
                    "configuration": service_config["configuration"],
                },
                "saga_context": {
                    "saga_id": saga_context.saga_id,
                    "correlation_id": saga_context.correlation_id,
                },
            }

        except Exception as e:
            # Handle compensation
            error_context = ErrorContext(
                operation="service_provisioning",
                resource_type="service",
                resource_id=f"{operation_data['service_type']}-{operation_data['customer_id']}",
                tenant_id=context.get("tenant_id", "system"),
                user_id=context.get("user_id"),
                correlation_id=saga_context.correlation_id,
            )

            raise ProvisioningError(
                message=f"Service provisioning failed: {str(e)}",
                provisioning_type="service",
                target_id=operation_data.get("customer_id", "unknown"),
                step_failed="unknown",
                rollback_required=True,
                context=error_context,
                saga_id=saga_context.saga_id,
                service_type=operation_data.get("service_type"),
            ) from e


class ServiceProvisioningSaga:
    """Saga definition for service provisioning"""

    @staticmethod
    def create_definition() -> SagaDefinition:
        """Create service provisioning saga definition"""

        definition = SagaDefinition(
            name="service_provisioning",
            description="Complete service provisioning from validation to customer notification",
            timeout_seconds=600,  # 10 minutes
            compensation_handler=ServiceProvisioningCompensationHandler(),
        )

        # Add steps in order
        definition.add_steps(
            [
                ValidateServiceRequestStep(),
                AllocateResourcesStep(),
                ConfigureServiceStep(),
                ActivateServiceStep(),
                NotifyCustomerStep(),
            ]
        )

        return definition
