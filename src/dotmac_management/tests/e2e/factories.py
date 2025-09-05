"""
Test Data Factories for E2E Tests

Provides factory classes for generating consistent test data across
tenant provisioning, container lifecycle, and isolation tests.

Uses factory-boy pattern for reproducible test data generation.
"""

import importlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

# Optional test dependency: factory_boy
_factory = importlib.import_module("factory")
Factory = _factory.Factory
Faker = _factory.Faker
LazyAttribute = _factory.LazyAttribute
SubFactory = _factory.SubFactory
Sequence = _factory.Sequence
try:
    SQLAlchemyModelFactory = importlib.import_module(
        "factory.alchemy"
    ).SQLAlchemyModelFactory
except Exception:  # Optional

    class SQLAlchemyModelFactory:  # type: ignore
        pass


from dotmac_management.models.tenant import TenantStatus


class TenantFactory(Factory, timezone):
    """Factory for creating test tenant data."""

    class Meta:
        model = dict

    tenant_id = LazyAttribute(lambda obj: f"tenant_{secrets.token_hex(6)}")
    subdomain = LazyAttribute(lambda obj: f"test{secrets.token_hex(4)}")
    company_name = Faker("company")
    admin_name = Faker("name")
    admin_email = Faker("email")
    plan = Faker("random_element", elements=["starter", "professional", "enterprise"])
    region = Faker("random_element", elements=["us-east-1", "us-west-2", "eu-west-1"])
    status = TenantStatus.PENDING
    created_at = Faker("date_time_this_month")
    settings = {}

    @classmethod
    def create_provisioning_workflow_tenant(cls, **kwargs):
        """Create tenant data optimized for provisioning workflow tests."""
        defaults = {
            "company_name": "E2E Test ISP Company",
            "admin_name": "Test Admin User",
            "admin_email": "admin@e2e-test.com",
            "plan": "professional",
            "region": "us-east-1",
            "status": TenantStatus.PENDING,
            "settings": {"enable_test_mode": True, "skip_email_verification": True},
        }
        defaults.update(kwargs)
        return cls(**defaults)

    @classmethod
    def create_isolation_test_tenants(cls, count: int = 2) -> list[dict[str, Any]]:
        """Create multiple tenants for isolation testing."""
        tenants = []
        for i in range(count):
            tenant_data = cls.create_provisioning_workflow_tenant(
                company_name=f"Isolation Test ISP {chr(65 + i)}",  # A, B, C...
                admin_email=f"admin_{chr(97 + i)}@isolation-test.com",  # a, b, c...
                subdomain=f"iso{chr(97 + i)}",
                tenant_id=f"tenant_isolation_{chr(97 + i)}",
            )
            tenants.append(tenant_data)
        return tenants

    @classmethod
    def create_lifecycle_test_tenant(cls, **kwargs):
        """Create tenant for container lifecycle testing."""
        defaults = {
            "company_name": "Lifecycle Test ISP",
            "admin_name": "Lifecycle Admin",
            "admin_email": "lifecycle@test.com",
            "plan": "professional",
            "region": "us-east-1",
            "status": TenantStatus.READY,  # Start as ready for lifecycle tests
            "settings": {
                "enable_container_monitoring": True,
                "enable_scaling": True,
                "test_mode": True,
            },
        }
        defaults.update(kwargs)
        return cls(**defaults)


class ProvisioningEventFactory(Factory):
    """Factory for tenant provisioning events."""

    class Meta:
        model = dict

    tenant_id = LazyAttribute(lambda obj: f"tenant_{secrets.token_hex(6)}")
    event_type = Faker(
        "random_element",
        elements=[
            "status_change.pending",
            "status_change.provisioning",
            "status_change.migrating",
            "status_change.seeding",
            "status_change.testing",
            "status_change.ready",
            "status_change.active",
        ],
    )
    status = "in_progress"
    message = Faker("sentence", nb_words=6)
    step_number = Faker("random_int", min=1, max=10)
    correlation_id = LazyAttribute(lambda obj: f"provision-{secrets.token_hex(8)}")
    operator = "system"
    created_at = Faker("date_time_this_hour")

    @classmethod
    def create_provisioning_sequence(
        cls, tenant_id: str, correlation_id: str
    ) -> list[dict[str, Any]]:
        """Create a complete provisioning event sequence."""
        events = []

        provisioning_steps = [
            ("status_change.pending", "Tenant creation initiated", 1),
            ("status_change.validating", "Validating tenant configuration", 2),
            ("database_created", "Database and Redis created", 3),
            ("secrets_generated", "Tenant secrets generated", 4),
            ("status_change.provisioning", "Deploying container stack", 5),
            ("container_deployed", "Container stack deployed", 6),
            ("status_change.migrating", "Running database migrations", 7),
            ("migrations_completed", "Database migrations completed", 8),
            ("status_change.seeding", "Seeding initial data", 9),
            ("data_seeded", "Initial data seeded", 10),
            ("admin_created", "Admin account created", 11),
            ("license_provisioned", "License provisioned", 12),
            ("status_change.testing", "Running health checks", 13),
            ("health_check_passed", "Health checks passed", 14),
            ("status_change.ready", "Provisioning completed successfully", 15),
            ("status_change.active", "Tenant is now active", 16),
        ]

        for event_type, message, step_number in provisioning_steps:
            event = cls(
                tenant_id=tenant_id,
                event_type=event_type,
                message=message,
                step_number=step_number,
                correlation_id=correlation_id,
                status="success" if step_number <= 16 else "in_progress",
            )
            events.append(event)

        return events


class ContainerLifecycleDataFactory(Factory):
    """Factory for container lifecycle test data."""

    class Meta:
        model = dict

    container_id = LazyAttribute(lambda obj: f"app_{secrets.token_hex(8)}")
    tenant_id = LazyAttribute(lambda obj: f"tenant_{secrets.token_hex(6)}")
    status = "running"
    health = "healthy"
    cpu_usage = Faker("random_int", min=10, max=80)
    memory_usage = Faker("random_int", min=128, max=2048)
    disk_usage = Faker("random_int", min=1, max=50)

    @classmethod
    def create_scaling_scenario(cls, base_container_id: str) -> list[dict[str, Any]]:
        """Create container data for scaling scenarios."""
        scenarios = []

        # Base container
        scenarios.append(
            cls(
                container_id=base_container_id,
                status="running",
                cpu_usage=85,  # High CPU triggers scaling
                memory_usage=1800,  # High memory
                replicas=1,
            )
        )

        # Scaled up containers
        for i in range(2, 4):  # Scale to 3 total
            scenarios.append(
                cls(
                    container_id=f"{base_container_id}-{i}",
                    status="running",
                    cpu_usage=30,  # Distributed load
                    memory_usage=600,
                    replicas=i,
                )
            )

        return scenarios


class DatabaseIsolationFactory(Factory):
    """Factory for database isolation test data."""

    class Meta:
        model = dict

    @classmethod
    def create_customer_data(cls, tenant_prefix: str) -> dict[str, Any]:
        """Create customer data specific to a tenant."""
        return {
            "id": f"{tenant_prefix}_customer_{secrets.token_hex(4)}",
            "email": f"customer_{tenant_prefix}@test.com",
            "name": f"Customer {tenant_prefix.upper()}",
            "phone": f"+1{secrets.randbelow(9000000000) + 1000000000}",
            "address": f"{secrets.randbelow(999) + 1} {tenant_prefix.title()} St",
            "city": f"{tenant_prefix.title()} City",
            "tenant_id": f"tenant_{tenant_prefix}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True,
        }

    @classmethod
    def create_service_data(
        cls, tenant_prefix: str, customer_id: str
    ) -> dict[str, Any]:
        """Create service data for a customer."""
        return {
            "id": f"{tenant_prefix}_service_{secrets.token_hex(4)}",
            "customer_id": customer_id,
            "service_type": Faker(
                "random_element", elements=["fiber", "dsl", "wireless"]
            ).generate(),
            "plan_name": f"{tenant_prefix.title()} Internet Plan",
            "bandwidth": Faker(
                "random_element", elements=["100/10", "500/50", "1000/1000"]
            ).generate(),
            "monthly_rate": Faker("random_int", min=50, max=200).generate(),
            "status": "active",
            "tenant_id": f"tenant_{tenant_prefix}",
        }

    @classmethod
    def create_billing_data(
        cls, tenant_prefix: str, customer_id: str
    ) -> dict[str, Any]:
        """Create billing data for a customer."""
        return {
            "id": f"{tenant_prefix}_bill_{secrets.token_hex(4)}",
            "customer_id": customer_id,
            "amount": Faker("random_int", min=5000, max=20000).generate()
            / 100,  # $50-$200
            "due_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "status": "unpaid",
            "tenant_id": f"tenant_{tenant_prefix}",
        }


class ApiTestDataFactory(Factory):
    """Factory for API test data."""

    class Meta:
        model = dict

    @classmethod
    def create_management_admin_credentials(cls) -> dict[str, str]:
        """Create management admin test credentials."""
        return {
            "username": "test_management_admin",
            "password": "test_password_123!",
            "email": "management.admin@test.com",
            "role": "management_admin",
        }

    @classmethod
    def create_tenant_admin_credentials(cls, tenant_id: str) -> dict[str, str]:
        """Create tenant admin test credentials."""
        return {
            "username": f"admin_{tenant_id}",
            "password": "tenant_admin_pass_123!",
            "email": f"admin@{tenant_id}.test.com",
            "role": "tenant_admin",
            "tenant_id": tenant_id,
        }

    @classmethod
    def create_test_jwt_payload(
        cls, tenant_id: Optional[str] = None, role: str = "user"
    ) -> dict[str, Any]:
        """Create JWT payload for API testing."""
        payload = {
            "sub": f"test_user_{secrets.token_hex(4)}",
            "email": "test@user.com",
            "role": role,
            "iat": datetime.now(timezone.utc).timestamp(),
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        }

        if tenant_id:
            payload["tenant_id"] = tenant_id

        return payload


class HealthCheckDataFactory(Factory):
    """Factory for health check test data."""

    class Meta:
        model = dict

    @classmethod
    def create_healthy_response(cls) -> dict[str, Any]:
        """Create healthy system response."""
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                "database": {"status": "healthy", "response_time": 0.05},
                "redis": {"status": "healthy", "response_time": 0.01},
                "container": {"status": "running", "uptime": 3600},
            },
        }

    @classmethod
    def create_unhealthy_response(cls, failing_service: str) -> dict[str, Any]:
        """Create unhealthy system response."""
        services = {
            "database": {"status": "healthy", "response_time": 0.05},
            "redis": {"status": "healthy", "response_time": 0.01},
            "container": {"status": "running", "uptime": 3600},
        }

        services[failing_service] = {
            "status": "unhealthy",
            "error": f"{failing_service} connection failed",
            "last_success": (
                datetime.now(timezone.utc) - timedelta(minutes=5)
            ).isoformat(),
        }

        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": services,
        }


# Export all factories
__all__ = [
    "TenantFactory",
    "ProvisioningEventFactory",
    "ContainerLifecycleDataFactory",
    "DatabaseIsolationFactory",
    "ApiTestDataFactory",
    "HealthCheckDataFactory",
]
