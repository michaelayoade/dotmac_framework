"""
Entity-Specific Factories for DotMac Framework

Pre-built factories for common DotMac entities including:
- Tenant/ISP management entities
- Customer and user entities
- Billing and service entities
- Network and device entities
- Support and ticketing entities

Each factory includes realistic default data and relationship support.
"""

import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from .factories import BaseFactory, FactoryMetadata, TenantIsolatedFactory
from .generators import DataGenerator, DataType


# Import base models - these would be the actual model classes
# For now using dict representations
class MockEntity(dict):
    """Mock entity for testing - replace with actual models."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "id" not in self:
            self["id"] = str(uuid4())

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            # Hide underlying KeyError to present a clean attribute error
            raise AttributeError(name) from None

    def __setattr__(self, name, value):
        self[name] = value


class TenantFactory(BaseFactory):
    """Factory for tenant/ISP entities."""

    def _create_metadata(self) -> FactoryMetadata:
        return FactoryMetadata(
            name="tenant_factory",
            entity_type=MockEntity,
            provides={"tenant"},
            cleanup_order=10,  # Clean up tenants last
        )

    def _create_instance(self, **kwargs) -> MockEntity:
        """Create tenant instance with ISP-appropriate defaults."""
        generator = DataGenerator()

        defaults = {
            "id": str(uuid4()),
            "name": kwargs.get("name") or generator.generate(DataType.COMPANY),
            "subdomain": kwargs.get("subdomain") or f"isp{secrets.token_hex(4)}",
            "domain": kwargs.get("domain")
            or f"{kwargs.get('subdomain', 'test')}.example.com",
            "status": "active",
            "plan": kwargs.get("plan", "professional"),
            "region": kwargs.get("region", "us-east-1"),
            "admin_name": generator.generate(DataType.NAME),
            "admin_email": generator.generate(DataType.EMAIL),
            "company_address": generator.generate(DataType.ADDRESS),
            "phone": generator.generate(DataType.PHONE),
            "settings": {
                "timezone": "UTC",
                "currency": "USD",
                "language": "en",
                "features": ["billing", "customers", "support"],
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Merge with provided kwargs
        defaults.update(kwargs)
        return MockEntity(**defaults)

    def _persist_instance(self, instance: MockEntity) -> MockEntity:
        """Persist tenant instance."""
        # In real implementation, this would save to database
        return instance

    def _cleanup_instance(self, instance: MockEntity) -> None:
        """Clean up tenant instance."""
        # In real implementation, this would delete from database
        pass


class UserFactory(TenantIsolatedFactory):
    """Factory for user entities with tenant isolation."""

    def _create_metadata(self) -> FactoryMetadata:
        return FactoryMetadata(
            name="user_factory",
            entity_type=MockEntity,
            dependencies={"tenant"},
            provides={"user"},
            tenant_isolated=True,
            cleanup_order=50,
        )

    def _create_instance(self, **kwargs) -> MockEntity:
        """Create user instance."""
        generator = DataGenerator()
        sequence = generator.next_sequence("user")

        defaults = {
            "id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "username": kwargs.get("username") or f"user{sequence:04d}",
            "email": kwargs.get("email") or f"user{sequence}@example.com",
            "full_name": generator.generate(DataType.NAME),
            "phone": generator.generate(DataType.PHONE),
            "role": kwargs.get("role", "customer"),
            "status": kwargs.get("status", "active"),
            "is_active": True,
            "is_verified": kwargs.get("is_verified", True),
            "password_hash": "hashed_password_placeholder",
            "last_login": None,
            "preferences": {"notifications": True, "language": "en", "timezone": "UTC"},
            **self._create_tenant_context(),
        }

        defaults.update(kwargs)
        return MockEntity(**defaults)

    def _persist_instance(self, instance: MockEntity) -> MockEntity:
        """Persist user instance."""
        return instance

    def _cleanup_instance(self, instance: MockEntity) -> None:
        """Clean up user instance."""
        pass


class CustomerFactory(TenantIsolatedFactory):
    """Factory for customer entities."""

    def _create_metadata(self) -> FactoryMetadata:
        return FactoryMetadata(
            name="customer_factory",
            entity_type=MockEntity,
            dependencies={"tenant"},
            provides={"customer"},
            tenant_isolated=True,
            cleanup_order=60,
        )

    def _create_instance(self, **kwargs) -> MockEntity:
        """Create customer instance."""
        generator = DataGenerator()
        sequence = generator.next_sequence("customer")

        customer_type = kwargs.get("type", "residential")

        defaults = {
            "id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "customer_number": f"CUST-{sequence:06d}",
            "type": customer_type,
            "status": kwargs.get("status", "active"),
            "name": generator.generate(DataType.NAME),
            "email": generator.generate(DataType.EMAIL),
            "phone": generator.generate(DataType.PHONE),
            "address": generator.generate(DataType.ADDRESS),
            "billing_address": kwargs.get(
                "billing_address"
            ),  # Will default to same as address
            "company_name": generator.generate(DataType.COMPANY)
            if customer_type == "business"
            else None,
            "tax_id": f"TAX{secrets.token_hex(6).upper()}"
            if customer_type == "business"
            else None,
            "credit_limit": Decimal("1000.00")
            if customer_type == "business"
            else Decimal("500.00"),
            "payment_terms": kwargs.get("payment_terms", 30),
            "notes": "",
            **self._create_tenant_context(),
        }

        # Set billing address to main address if not provided
        if not defaults["billing_address"]:
            defaults["billing_address"] = defaults["address"]

        defaults.update(kwargs)
        return MockEntity(**defaults)

    def _persist_instance(self, instance: MockEntity) -> MockEntity:
        return instance

    def _cleanup_instance(self, instance: MockEntity) -> None:
        pass


class ServiceFactory(TenantIsolatedFactory):
    """Factory for service entities."""

    def _create_metadata(self) -> FactoryMetadata:
        return FactoryMetadata(
            name="service_factory",
            entity_type=MockEntity,
            dependencies={"customer"},
            provides={"service"},
            tenant_isolated=True,
            cleanup_order=70,
        )

    def _create_instance(self, **kwargs) -> MockEntity:
        """Create service instance."""
        generator = DataGenerator()
        sequence = generator.next_sequence("service")

        service_type = kwargs.get("service_type", "internet")

        defaults = {
            "id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "customer_id": kwargs.get("customer_id"),
            "service_number": f"SRV-{sequence:06d}",
            "service_type": service_type,
            "status": kwargs.get("status", "active"),
            "plan_name": self._get_plan_for_type(service_type),
            "monthly_rate": self._get_rate_for_type(service_type),
            "setup_fee": Decimal("99.00"),
            "activation_date": datetime.utcnow().date(),
            "billing_cycle": kwargs.get("billing_cycle", "monthly"),
            "contract_term": kwargs.get("contract_term", 12),
            "auto_renew": kwargs.get("auto_renew", True),
            "technical_details": self._get_technical_details(service_type),
            **self._create_tenant_context(),
        }

        defaults.update(kwargs)
        return MockEntity(**defaults)

    def _persist_instance(self, instance: MockEntity) -> MockEntity:
        return instance

    def _cleanup_instance(self, instance: MockEntity) -> None:
        pass

    def _get_plan_for_type(self, service_type: str) -> str:
        """Get realistic plan name for service type."""
        plans = {
            "internet": "High Speed Internet 100/10",
            "phone": "Unlimited Voice",
            "tv": "Digital TV Premium",
            "hosting": "Web Hosting Pro",
        }
        return plans.get(service_type, "Basic Service")

    def _get_rate_for_type(self, service_type: str) -> Decimal:
        """Get realistic monthly rate for service type."""
        rates = {
            "internet": Decimal("79.99"),
            "phone": Decimal("29.99"),
            "tv": Decimal("89.99"),
            "hosting": Decimal("19.99"),
        }
        return rates.get(service_type, Decimal("49.99"))

    def _get_technical_details(self, service_type: str) -> dict[str, Any]:
        """Get technical details for service type."""
        if service_type == "internet":
            return {
                "download_speed": "100 Mbps",
                "upload_speed": "10 Mbps",
                "technology": "fiber",
                "static_ip": False,
                "bandwidth_limit": None,
            }
        elif service_type == "phone":
            return {
                "number": f"+1{secrets.randbelow(900) + 100}{secrets.randbelow(900) + 100:04d}",
                "features": ["voicemail", "caller_id", "call_waiting"],
                "international": False,
            }
        return {}


class BillingFactory(TenantIsolatedFactory):
    """Factory for billing-related entities."""

    def _create_metadata(self) -> FactoryMetadata:
        return FactoryMetadata(
            name="billing_factory",
            entity_type=MockEntity,
            dependencies={"customer"},
            provides={"invoice", "payment", "billing_account"},
            tenant_isolated=True,
            cleanup_order=80,
        )

    def _create_instance(self, **kwargs) -> MockEntity:
        """Create billing entity (invoice by default)."""
        entity_type = kwargs.get("entity_type", "invoice")

        if entity_type == "invoice":
            return self._create_invoice(**kwargs)
        elif entity_type == "payment":
            return self._create_payment(**kwargs)
        elif entity_type == "billing_account":
            return self._create_billing_account(**kwargs)
        else:
            raise ValueError(f"Unknown billing entity type: {entity_type}")

    def _create_invoice(self, **kwargs) -> MockEntity:
        """Create invoice entity."""
        generator = DataGenerator()
        sequence = generator.next_sequence("invoice")

        issue_date = kwargs.get("issue_date", datetime.utcnow().date())
        due_date = kwargs.get("due_date", issue_date + timedelta(days=30))

        defaults = {
            "id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "customer_id": kwargs.get("customer_id"),
            "invoice_number": f"INV-{sequence:06d}",
            "status": kwargs.get("status", "pending"),
            "issue_date": issue_date,
            "due_date": due_date,
            "subtotal": kwargs.get("subtotal", Decimal("79.99")),
            "tax_amount": kwargs.get("tax_amount", Decimal("6.40")),
            "total_amount": kwargs.get("total_amount", Decimal("86.39")),
            "currency": "USD",
            "payment_terms": 30,
            "line_items": kwargs.get(
                "line_items",
                [
                    {
                        "description": "Internet Service - Monthly",
                        "quantity": 1,
                        "unit_price": Decimal("79.99"),
                        "total": Decimal("79.99"),
                    }
                ],
            ),
            **self._create_tenant_context(),
        }

        # Calculate totals if not provided
        if "total_amount" not in kwargs:
            defaults["total_amount"] = defaults["subtotal"] + defaults["tax_amount"]

        defaults.update(kwargs)
        return MockEntity(**defaults)

    def _create_payment(self, **kwargs) -> MockEntity:
        """Create payment entity."""
        sequence = self._get_sequence("payment")

        defaults = {
            "id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "customer_id": kwargs.get("customer_id"),
            "invoice_id": kwargs.get("invoice_id"),
            "payment_number": f"PAY-{sequence:06d}",
            "amount": kwargs.get("amount", Decimal("86.39")),
            "currency": "USD",
            "payment_method": kwargs.get("payment_method", "credit_card"),
            "status": kwargs.get("status", "completed"),
            "processed_date": datetime.utcnow(),
            "transaction_id": f"txn_{secrets.token_hex(8)}",
            **self._create_tenant_context(),
        }

        defaults.update(kwargs)
        return MockEntity(**defaults)

    def _create_billing_account(self, **kwargs) -> MockEntity:
        """Create billing account entity."""
        defaults = {
            "id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "customer_id": kwargs.get("customer_id"),
            "account_number": f"BA-{secrets.token_hex(8).upper()}",
            "status": kwargs.get("status", "active"),
            "balance": kwargs.get("balance", Decimal("0.00")),
            "credit_limit": kwargs.get("credit_limit", Decimal("500.00")),
            "payment_method": kwargs.get("payment_method", "auto_pay"),
            "billing_cycle": kwargs.get("billing_cycle", "monthly"),
            "auto_pay_enabled": kwargs.get("auto_pay_enabled", True),
            **self._create_tenant_context(),
        }

        defaults.update(kwargs)
        return MockEntity(**defaults)

    def _persist_instance(self, instance: MockEntity) -> MockEntity:
        return instance

    def _cleanup_instance(self, instance: MockEntity) -> None:
        pass

    def _get_sequence(self, name: str) -> int:
        """Get next sequence number."""
        generator = DataGenerator()
        return generator.next_sequence(name)


class DeviceFactory(TenantIsolatedFactory):
    """Factory for network device entities."""

    def _create_metadata(self) -> FactoryMetadata:
        return FactoryMetadata(
            name="device_factory",
            entity_type=MockEntity,
            dependencies={"customer"},
            provides={"device"},
            tenant_isolated=True,
            cleanup_order=75,
        )

    def _create_instance(self, **kwargs) -> MockEntity:
        """Create device instance."""
        generator = DataGenerator()
        generator.next_sequence("device")

        device_type = kwargs.get("device_type", "router")

        defaults = {
            "id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "customer_id": kwargs.get("customer_id"),
            "serial_number": f"SN{secrets.token_hex(6).upper()}",
            "mac_address": generator.generate(DataType.MAC_ADDRESS, vendor="cisco"),
            "device_type": device_type,
            "model": self._get_model_for_type(device_type),
            "manufacturer": self._get_manufacturer_for_type(device_type),
            "status": kwargs.get("status", "active"),
            "ip_address": generator.generate(DataType.IP_ADDRESS, type="private"),
            "firmware_version": kwargs.get("firmware_version", "1.2.3"),
            "location": kwargs.get("location", "Customer Premises"),
            "installation_date": datetime.utcnow().date(),
            "warranty_expires": datetime.utcnow().date() + timedelta(days=365),
            "configuration": self._get_default_config(device_type),
            **self._create_tenant_context(),
        }

        defaults.update(kwargs)
        return MockEntity(**defaults)

    def _persist_instance(self, instance: MockEntity) -> MockEntity:
        return instance

    def _cleanup_instance(self, instance: MockEntity) -> None:
        pass

    def _get_model_for_type(self, device_type: str) -> str:
        """Get realistic model for device type."""
        models = {
            "router": "ISR-4331",
            "switch": "SG300-28",
            "modem": "DPC3008",
            "access_point": "WAP571",
        }
        return models.get(device_type, "GENERIC-001")

    def _get_manufacturer_for_type(self, device_type: str) -> str:
        """Get manufacturer for device type."""
        manufacturers = {
            "router": "Cisco",
            "switch": "Cisco",
            "modem": "Arris",
            "access_point": "Cisco",
        }
        return manufacturers.get(device_type, "Generic")

    def _get_default_config(self, device_type: str) -> dict[str, Any]:
        """Get default configuration for device type."""
        if device_type == "router":
            return {
                "dhcp_enabled": True,
                "nat_enabled": True,
                "firewall_enabled": True,
                "wireless_enabled": False,
            }
        elif device_type == "access_point":
            return {
                "ssid": f"WiFi-{secrets.token_hex(4)}",
                "security": "WPA2",
                "channel": 6,
                "power": "100%",
            }
        return {}


class TicketFactory(TenantIsolatedFactory):
    """Factory for support ticket entities."""

    def _create_metadata(self) -> FactoryMetadata:
        return FactoryMetadata(
            name="ticket_factory",
            entity_type=MockEntity,
            dependencies={"customer"},
            provides={"ticket"},
            tenant_isolated=True,
            cleanup_order=85,
        )

    def _create_instance(self, **kwargs) -> MockEntity:
        """Create support ticket instance."""
        generator = DataGenerator()
        sequence = generator.next_sequence("ticket")

        priorities = ["low", "medium", "high", "urgent"]
        categories = ["technical", "billing", "service", "general"]

        defaults = {
            "id": str(uuid4()),
            "tenant_id": self.tenant_id,
            "customer_id": kwargs.get("customer_id"),
            "ticket_number": f"TKT-{sequence:06d}",
            "subject": kwargs.get("subject", f"Support request #{sequence}"),
            "description": kwargs.get(
                "description", "Customer needs assistance with service"
            ),
            "category": kwargs.get("category", secrets.choice(categories)),
            "priority": kwargs.get("priority", secrets.choice(priorities)),
            "status": kwargs.get("status", "open"),
            "assigned_to": kwargs.get("assigned_to"),
            "created_by": kwargs.get("created_by"),
            "resolution": kwargs.get("resolution"),
            "estimated_resolution": kwargs.get("estimated_resolution"),
            "tags": kwargs.get("tags", []),
            **self._create_tenant_context(),
        }

        defaults.update(kwargs)
        return MockEntity(**defaults)

    def _persist_instance(self, instance: MockEntity) -> MockEntity:
        return instance

    def _cleanup_instance(self, instance: MockEntity) -> None:
        pass
