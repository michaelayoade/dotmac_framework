"""
Comprehensive tests for DotMac Services SDKs.

Tests service lifecycle management, catalog management, tariff management,
and provisioning bindings functionality.
"""

from datetime import datetime, timedelta
from dotmac_services.core.datetime_utils import utc_now, utc_now_iso
from unittest.mock import patch
from uuid import uuid4

import pytest

# Import core exceptions
from dotmac_services.core.exceptions import (
    InvalidStateTransitionError,
)
from dotmac_services.sdks.provisioning_bindings import ProvisioningBindingsSDK
from dotmac_services.sdks.service_catalog import ServiceCatalogSDK

# Import services SDKs
from dotmac_services.sdks.service_management import (
    ServiceManagementSDK,
    ServiceState,
)
from dotmac_services.sdks.tariff import TariffSDK


class TestServiceManagementSDK:
    """Test service lifecycle management functionality."""

    @pytest.fixture
    def service_sdk(self):
        """Create service management SDK instance."""
        return ServiceManagementSDK(tenant_id="test-tenant-123")

    @pytest.mark.asyncio
    async def test_create_service_instance(self, service_sdk):
        """Test service instance creation."""
        customer_id = str(uuid4())
        service_plan_id = str(uuid4())

        result = await service_sdk.create_service_instance(
            customer_id=customer_id,
            service_plan_id=service_plan_id,
            service_name="Test Internet Service",
            configuration={
                "bandwidth": "100Mbps",
                "data_limit": "unlimited"
            }
        )

        assert result["customer_id"] == customer_id
        assert result["service_plan_id"] == service_plan_id
        assert result["service_name"] == "Test Internet Service"
        assert result["state"] == ServiceState.REQUESTED.value
        assert result["configuration"]["bandwidth"] == "100Mbps"
        assert "instance_id" in result
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_service_lifecycle_transitions(self, service_sdk):
        """Test complete service lifecycle state transitions."""
        # Create service instance
        instance = await service_sdk.create_service_instance(
            customer_id=str(uuid4()),
            service_plan_id=str(uuid4()),
            service_name="Lifecycle Test Service"
        )
        instance_id = instance["instance_id"]

        # Start provisioning
        provisioning_result = await service_sdk.start_provisioning(
            instance_id=instance_id,
            provisioning_steps=["validate", "allocate", "configure", "activate"],
            triggered_by="admin"
        )

        assert provisioning_result["state_transition"]["from"] == ServiceState.REQUESTED.value
        assert provisioning_result["state_transition"]["to"] == ServiceState.PROVISIONING.value

        # Update provisioning progress
        progress_result = await service_sdk.update_provisioning_progress(
            instance_id=instance_id,
            progress_percentage=50,
            current_step="configure",
            completed_steps=["validate", "allocate"]
        )

        assert progress_result["provisioning_progress"]["percentage"] == 50
        assert progress_result["provisioning_progress"]["current_step"] == "configure"

        # Complete provisioning (should auto-activate)
        await service_sdk.update_provisioning_progress(
            instance_id=instance_id,
            progress_percentage=100,
            current_step="completed"
        )

        # Verify service is now active
        service_details = await service_sdk.get_service_instance(instance_id)
        assert service_details["state"] == ServiceState.ACTIVE.value

        # Suspend service
        suspend_result = await service_sdk.suspend_service(
            instance_id=instance_id,
            suspension_reason="Billing issue",
            suspension_type="billing",
            triggered_by="billing_system"
        )

        assert suspend_result["state_transition"]["to"] == ServiceState.SUSPENDED.value
        assert suspend_result["suspension_details"]["reason"] == "Billing issue"

        # Resume service
        resume_result = await service_sdk.resume_service(
            instance_id=instance_id,
            triggered_by="customer_payment"
        )

        assert resume_result["state_transition"]["to"] == ServiceState.ACTIVE.value

        # Terminate service
        terminate_result = await service_sdk.terminate_service(
            instance_id=instance_id,
            termination_reason="Customer request",
            termination_type="normal",
            data_retention_until=(utc_now() + timedelta(days=30)).isoformat()
        )

        assert terminate_result["state_transition"]["to"] == ServiceState.TERMINATED.value
        assert terminate_result["termination_details"]["reason"] == "Customer request"

    @pytest.mark.asyncio
    async def test_invalid_state_transitions(self, service_sdk):
        """Test invalid state transition handling."""
        # Create service instance
        instance = await service_sdk.create_service_instance(
            customer_id=str(uuid4()),
            service_plan_id=str(uuid4())
        )
        instance_id = instance["instance_id"]

        # Try to suspend a service that's not active (should fail)
        with pytest.raises(InvalidStateTransitionError):
            await service_sdk.suspend_service(
                instance_id=instance_id,
                suspension_reason="Test invalid transition"
            )

    @pytest.mark.asyncio
    async def test_service_retry_mechanism(self, service_sdk):
        """Test failed service retry mechanism."""
        # Create and start provisioning
        instance = await service_sdk.create_service_instance(
            customer_id=str(uuid4()),
            service_plan_id=str(uuid4()),
            max_retries=2
        )
        instance_id = instance["instance_id"]

        await service_sdk.start_provisioning(instance_id)

        # Simulate failure by manually transitioning to failed state
        await service_sdk._service.transition_service_state(
            instance_id=instance_id,
            target_state=ServiceState.FAILED.value,
            reason="Provisioning failed"
        )

        # Retry failed service
        retry_result = await service_sdk.retry_failed_service(instance_id)

        assert retry_result["retry_attempt"] == 1
        assert retry_result["max_retries"] == 2
        assert retry_result["new_state"] == ServiceState.PROVISIONING.value

    @pytest.mark.asyncio
    async def test_service_state_history(self, service_sdk):
        """Test service state transition history."""
        instance = await service_sdk.create_service_instance(
            customer_id=str(uuid4()),
            service_plan_id=str(uuid4())
        )
        instance_id = instance["instance_id"]

        # Go through several state transitions
        await service_sdk.start_provisioning(instance_id)
        await service_sdk.activate_service(instance_id)

        # Get state history
        history = await service_sdk.get_state_history(instance_id)

        assert len(history) >= 3  # requested -> provisioning -> active
        assert history[0]["to_state"] == ServiceState.REQUESTED.value
        assert history[-1]["to_state"] == ServiceState.ACTIVE.value

        # Verify all transitions have required fields
        for transition in history:
            assert "transition_id" in transition
            assert "to_state" in transition
            assert "timestamp" in transition

    @pytest.mark.asyncio
    async def test_list_services_by_state(self, service_sdk):
        """Test listing services by state."""
        customer_id = str(uuid4())

        # Create multiple services
        service1 = await service_sdk.create_service_instance(
            customer_id=customer_id,
            service_plan_id=str(uuid4()),
            service_name="Service 1"
        )

        service2 = await service_sdk.create_service_instance(
            customer_id=customer_id,
            service_plan_id=str(uuid4()),
            service_name="Service 2"
        )

        # Start provisioning one service
        await service_sdk.start_provisioning(service1["instance_id"])

        # List services by state
        requested_services = await service_sdk.list_services_by_state(
            state=ServiceState.REQUESTED.value,
            customer_id=customer_id
        )

        provisioning_services = await service_sdk.list_services_by_state(
            state=ServiceState.PROVISIONING.value,
            customer_id=customer_id
        )

        assert len(requested_services) == 1
        assert requested_services[0]["service_name"] == "Service 2"

        assert len(provisioning_services) == 1
        assert provisioning_services[0]["service_name"] == "Service 1"


class TestServiceCatalogSDK:
    """Test service catalog management functionality."""

    @pytest.fixture
    def catalog_sdk(self):
        """Create service catalog SDK instance."""
        return ServiceCatalogSDK(tenant_id="test-tenant-123")

    @pytest.mark.asyncio
    async def test_create_service_definition(self, catalog_sdk):
        """Test service definition creation."""
        definition = await catalog_sdk.create_service_definition(
            name="High-Speed Internet",
            service_type="data",
            description="Fiber optic internet service",
            technical_specs={
                "technology": "fiber",
                "max_bandwidth": "1Gbps",
                "latency": "<5ms"
            }
        )

        assert definition["name"] == "High-Speed Internet"
        assert definition["service_type"] == "data"
        assert definition["technical_specs"]["technology"] == "fiber"
        assert definition["status"] == "draft"
        assert "definition_id" in definition

    @pytest.mark.asyncio
    async def test_create_service_plan(self, catalog_sdk):
        """Test service plan creation."""
        # First create a service definition
        definition = await catalog_sdk.create_service_definition(
            name="Internet Service",
            service_type="data"
        )

        plan = await catalog_sdk.create_service_plan(
            definition_id=definition["definition_id"],
            name="Premium Plan",
            base_price=79.99,
            billing_cycle="monthly",
            currency="USD",
            features={
                "bandwidth": "500Mbps",
                "data_limit": "unlimited",
                "static_ip": True
            },
            setup_fee=25.00
        )

        assert plan["name"] == "Premium Plan"
        assert plan["base_price"] == 79.99
        assert plan["billing_cycle"] == "monthly"
        assert plan["features"]["bandwidth"] == "500Mbps"
        assert plan["setup_fee"] == 25.00

    @pytest.mark.asyncio
    async def test_create_service_bundle(self, catalog_sdk):
        """Test service bundle creation."""
        # Create service definitions and plans
        definition1 = await catalog_sdk.create_service_definition(
            name="Internet Service",
            service_type="data"
        )
        plan1 = await catalog_sdk.create_service_plan(
            definition_id=definition1["definition_id"],
            name="Internet Plan",
            base_price=59.99
        )

        definition2 = await catalog_sdk.create_service_definition(
            name="Voice Service",
            service_type="voice"
        )
        plan2 = await catalog_sdk.create_service_plan(
            definition_id=definition2["definition_id"],
            name="Voice Plan",
            base_price=29.99
        )

        bundle = await catalog_sdk.create_bundle(
            name="Internet + Voice Bundle",
            included_services=[plan1["plan_id"], plan2["plan_id"]],
            discount_value=15.0,
            discount_type="percentage",
            description="Save 15% on Internet and Voice"
        )

        assert bundle["name"] == "Internet + Voice Bundle"
        assert plan1["plan_id"] in bundle["included_services"]
        assert plan2["plan_id"] in bundle["included_services"]
        assert bundle["discount_value"] == 15.0
        assert bundle["discount_type"] == "percentage"

    @pytest.mark.asyncio
    async def test_create_addon(self, catalog_sdk):
        """Test service add-on creation."""
        # Create service definition and plan
        definition = await catalog_sdk.create_service_definition(
            name="Internet Service",
            service_type="data"
        )
        plan = await catalog_sdk.create_service_plan(
            definition_id=definition["definition_id"],
            name="Basic Plan",
            base_price=39.99
        )

        addon = await catalog_sdk.create_addon(
            name="Speed Boost",
            addon_type="feature",
            price=15.00,
            compatible_plans=[plan["plan_id"]],
            features={
                "additional_bandwidth": "200Mbps",
                "priority_traffic": True
            }
        )

        assert addon["name"] == "Speed Boost"
        assert addon["addon_type"] == "feature"
        assert addon["price"] == 15.00
        assert plan["plan_id"] in addon["compatible_plans"]
        assert addon["features"]["additional_bandwidth"] == "200Mbps"

    @pytest.mark.asyncio
    async def test_bundle_pricing_calculation(self, catalog_sdk):
        """Test bundle pricing calculation."""
        # Create services and bundle
        def1 = await catalog_sdk.create_service_definition(name="Internet", service_type="data")
        plan1 = await catalog_sdk.create_service_plan(
            definition_id=def1["definition_id"], name="Internet Plan", base_price=60.00
        )

        def2 = await catalog_sdk.create_service_definition(name="TV", service_type="video")
        plan2 = await catalog_sdk.create_service_plan(
            definition_id=def2["definition_id"], name="TV Plan", base_price=40.00
        )

        bundle = await catalog_sdk.create_bundle(
            name="Internet + TV Bundle",
            included_services=[plan1["plan_id"], plan2["plan_id"]],
            discount_value=20.0,
            discount_type="percentage"
        )

        pricing = await catalog_sdk.calculate_bundle_pricing(
            bundle_id=bundle["bundle_id"],
            selected_services=[plan1["plan_id"], plan2["plan_id"]]
        )

        assert pricing["pricing"]["individual_total"] == 100.00
        assert pricing["pricing"]["discount_amount"] == 20.00
        assert pricing["pricing"]["final_price"] == 80.00
        assert pricing["pricing"]["discount_percentage"] == 20.0

    @pytest.mark.asyncio
    async def test_get_service_catalog(self, catalog_sdk):
        """Test service catalog retrieval."""
        # Create some service definitions and plans
        definition = await catalog_sdk.create_service_definition(
            name="Internet Service",
            service_type="data",
            status="published"
        )

        plan = await catalog_sdk.create_service_plan(
            definition_id=definition["definition_id"],
            name="Standard Plan",
            base_price=49.99,
            status="active"
        )

        catalog = await catalog_sdk.get_service_catalog(
            service_type="data",
            status="published"
        )

        assert catalog["total_services"] >= 1
        assert len(catalog["catalog_items"]) >= 1

        catalog_item = catalog["catalog_items"][0]
        assert catalog_item["definition"]["service_type"] == "data"
        assert len(catalog_item["plans"]) >= 1
        assert catalog_item["plans"][0]["base_price"] == 49.99

    @pytest.mark.asyncio
    async def test_get_compatible_addons(self, catalog_sdk):
        """Test getting compatible add-ons for a service plan."""
        # Create service and add-on
        definition = await catalog_sdk.create_service_definition(
            name="Internet Service",
            service_type="data"
        )
        plan = await catalog_sdk.create_service_plan(
            definition_id=definition["definition_id"],
            name="Basic Plan",
            base_price=39.99
        )

        addon = await catalog_sdk.create_addon(
            name="Static IP",
            addon_type="feature",
            price=5.00,
            compatible_plans=[plan["plan_id"]]
        )

        compatible_addons = await catalog_sdk.get_compatible_addons(plan["plan_id"])

        assert len(compatible_addons) == 1
        assert compatible_addons[0]["name"] == "Static IP"
        assert compatible_addons[0]["price"] == 5.00

    @pytest.mark.asyncio
    async def test_validate_service_combination(self, catalog_sdk):
        """Test service combination validation."""
        # Create services and add-ons
        definition = await catalog_sdk.create_service_definition(
            name="Internet Service",
            service_type="data"
        )
        plan = await catalog_sdk.create_service_plan(
            definition_id=definition["definition_id"],
            name="Basic Plan",
            base_price=39.99
        )

        addon = await catalog_sdk.create_addon(
            name="Speed Boost",
            addon_type="feature",
            price=10.00,
            compatible_plans=[plan["plan_id"]]
        )

        # Test valid combination
        validation = await catalog_sdk.validate_service_combination(
            service_plans=[plan["plan_id"]],
            addons=[addon["addon_id"]]
        )

        assert validation["valid"] is True
        assert len(validation["errors"]) == 0

        # Test invalid combination
        invalid_validation = await catalog_sdk.validate_service_combination(
            service_plans=["nonexistent-plan"],
            addons=[addon["addon_id"]]
        )

        assert invalid_validation["valid"] is False
        assert len(invalid_validation["errors"]) > 0


class TestTariffSDK:
    """Test tariff management functionality."""

    @pytest.fixture
    def tariff_sdk(self):
        """Create tariff SDK instance."""
        return TariffSDK(tenant_id="test-tenant-123")

    @pytest.mark.asyncio
    async def test_create_tariff_plan(self, tariff_sdk):
        """Test tariff plan creation."""
        tariff = await tariff_sdk.create_tariff_plan(
            name="Business Internet Tariff",
            service_type="data",
            base_rate=99.99,
            currency="USD",
            billing_cycle="monthly",
            rate_structure={
                "type": "flat",
                "included_usage": "unlimited",
                "overage_rate": 0.0
            },
            taxes_and_fees={
                "regulatory_fee": 2.50,
                "service_tax_rate": 0.08
            }
        )

        assert tariff["name"] == "Business Internet Tariff"
        assert tariff["base_rate"] == 99.99
        assert tariff["rate_structure"]["type"] == "flat"
        assert tariff["taxes_and_fees"]["regulatory_fee"] == 2.50

    @pytest.mark.asyncio
    async def test_usage_based_billing_calculation(self, tariff_sdk):
        """Test usage-based billing calculation."""
        # Create usage-based tariff
        tariff = await tariff_sdk.create_tariff_plan(
            name="Pay-per-GB Plan",
            service_type="data",
            base_rate=19.99,
            rate_structure={
                "type": "usage_based",
                "included_gb": 10,
                "overage_rate_per_gb": 2.00,
                "rate_tiers": [
                    {"min_gb": 0, "max_gb": 50, "rate_per_gb": 2.00},
                    {"min_gb": 51, "max_gb": 100, "rate_per_gb": 1.50},
                    {"min_gb": 101, "max_gb": None, "rate_per_gb": 1.00}
                ]
            }
        )

        # Calculate bill for 75GB usage
        bill = await tariff_sdk.calculate_usage_bill(
            tariff_id=tariff["tariff_id"],
            usage_data={
                "data_usage_gb": 75,
                "billing_period": "2024-01"
            }
        )

        assert bill["base_charge"] == 19.99
        assert bill["usage_charges"] > 0  # Should have overage charges
        assert bill["total_usage_gb"] == 75
        assert "breakdown" in bill

    @pytest.mark.asyncio
    async def test_promotional_pricing(self, tariff_sdk):
        """Test promotional pricing application."""
        # Create tariff with promotional pricing
        tariff = await tariff_sdk.create_tariff_plan(
            name="Promotional Plan",
            service_type="data",
            base_rate=59.99,
            promotional_pricing=[
                {
                    "promotion_id": "new_customer_50",
                    "discount_type": "percentage",
                    "discount_value": 50.0,
                    "duration_months": 6,
                    "conditions": {"customer_type": "new"}
                }
            ]
        )

        # Calculate bill with promotion
        bill = await tariff_sdk.calculate_promotional_bill(
            tariff_id=tariff["tariff_id"],
            customer_profile={
                "customer_type": "new",
                "signup_date": "2024-01-01"
            },
            billing_period="2024-01"
        )

        assert bill["base_rate"] == 59.99
        assert bill["promotional_discount"] == 29.995  # 50% discount
        assert bill["final_amount"] == 29.995
        assert "applied_promotions" in bill


class TestProvisioningBindingsSDK:
    """Test provisioning bindings functionality."""

    @pytest.fixture
    def provisioning_sdk(self):
        """Create provisioning bindings SDK instance."""
        return ProvisioningBindingsSDK(tenant_id="test-tenant-123")

    @pytest.mark.asyncio
    async def test_register_provisioning_adapter(self, provisioning_sdk):
        """Test provisioning adapter registration."""
        adapter_config = {
            "adapter_name": "cisco_router_adapter",
            "adapter_type": "network_device",
            "endpoint_url": "https://api.ciscorouter.local",
            "authentication": {
                "type": "api_key",
                "credentials": {"api_key": "test_key"}
            },
            "capabilities": [
                "interface_configuration",
                "vlan_setup",
                "routing_configuration"
            ]
        }

        result = await provisioning_sdk.register_provisioning_adapter(
            service_type="data",
            **adapter_config
        )

        assert result["adapter_name"] == "cisco_router_adapter"
        assert result["service_type"] == "data"
        assert "interface_configuration" in result["capabilities"]
        assert result["status"] == "registered"

    @pytest.mark.asyncio
    async def test_execute_provisioning_workflow(self, provisioning_sdk):
        """Test provisioning workflow execution."""
        # Register adapter first
        await provisioning_sdk.register_provisioning_adapter(
            service_type="data",
            adapter_name="test_adapter",
            adapter_type="network_device",
            endpoint_url="https://test.local"
        )

        # Execute provisioning workflow
        workflow_result = await provisioning_sdk.execute_provisioning_workflow(
            service_instance_id=str(uuid4()),
            service_type="data",
            provisioning_config={
                "customer_id": str(uuid4()),
                "service_plan": "premium_internet",
                "network_config": {
                    "bandwidth": "1Gbps",
                    "vlan_id": 100,
                    "ip_allocation": "static"
                }
            }
        )

        assert workflow_result["service_instance_id"] is not None
        assert workflow_result["provisioning_status"] == "initiated"
        assert "workflow_id" in workflow_result
        assert "execution_steps" in workflow_result

    @pytest.mark.asyncio
    async def test_rollback_provisioning(self, provisioning_sdk):
        """Test provisioning rollback functionality."""
        # Mock a failed provisioning scenario
        workflow_id = str(uuid4())

        rollback_result = await provisioning_sdk.rollback_provisioning(
            workflow_id=workflow_id,
            rollback_reason="Configuration validation failed",
            rollback_steps=[
                "remove_vlan_configuration",
                "deallocate_ip_address",
                "cleanup_customer_data"
            ]
        )

        assert rollback_result["workflow_id"] == workflow_id
        assert rollback_result["rollback_status"] == "initiated"
        assert "cleanup_customer_data" in rollback_result["rollback_steps"]

    @pytest.mark.asyncio
    async def test_get_provisioning_status(self, provisioning_sdk):
        """Test provisioning status monitoring."""
        workflow_id = str(uuid4())

        # Mock workflow status
        with patch.object(provisioning_sdk._service, "_workflows", {workflow_id: {
            "workflow_id": workflow_id,
            "status": "in_progress",
            "current_step": "network_configuration",
            "completed_steps": ["validate_customer", "allocate_resources"],
            "progress_percentage": 60,
            "started_at": utc_now().isoformat()
        }}):
            status = await provisioning_sdk.get_provisioning_status(workflow_id)

            assert status["workflow_id"] == workflow_id
            assert status["status"] == "in_progress"
            assert status["progress_percentage"] == 60
            assert status["current_step"] == "network_configuration"


# Integration tests
class TestServicesIntegration:
    """Test integration between service SDKs."""

    @pytest.mark.asyncio
    async def test_catalog_to_management_integration(self):
        """Test integration between catalog and management SDKs."""
        catalog_sdk = ServiceCatalogSDK(tenant_id="test-tenant")
        management_sdk = ServiceManagementSDK(tenant_id="test-tenant")

        # Create service definition and plan in catalog
        definition = await catalog_sdk.create_service_definition(
            name="Integrated Test Service",
            service_type="data"
        )

        plan = await catalog_sdk.create_service_plan(
            definition_id=definition["definition_id"],
            name="Standard Plan",
            base_price=49.99
        )

        # Create service instance using the catalog plan
        instance = await management_sdk.create_service_instance(
            customer_id=str(uuid4()),
            service_plan_id=plan["plan_id"],
            service_name="Customer Internet Service"
        )

        assert instance["service_plan_id"] == plan["plan_id"]
        assert instance["state"] == ServiceState.REQUESTED.value

        # Complete the service lifecycle
        await management_sdk.start_provisioning(instance["instance_id"])
        await management_sdk.update_provisioning_progress(
            instance["instance_id"], 100, "completed"
        )

        # Verify service is active
        final_state = await management_sdk.get_service_instance(instance["instance_id"])
        assert final_state["state"] == ServiceState.ACTIVE.value

    @pytest.mark.asyncio
    async def test_bundle_service_provisioning(self):
        """Test provisioning services from a bundle."""
        catalog_sdk = ServiceCatalogSDK(tenant_id="test-tenant")
        management_sdk = ServiceManagementSDK(tenant_id="test-tenant")

        # Create services for bundle
        internet_def = await catalog_sdk.create_service_definition(
            name="Internet", service_type="data"
        )
        internet_plan = await catalog_sdk.create_service_plan(
            definition_id=internet_def["definition_id"],
            name="Internet Plan",
            base_price=60.00
        )

        voice_def = await catalog_sdk.create_service_definition(
            name="Voice", service_type="voice"
        )
        voice_plan = await catalog_sdk.create_service_plan(
            definition_id=voice_def["definition_id"],
            name="Voice Plan",
            base_price=30.00
        )

        # Create bundle
        bundle = await catalog_sdk.create_bundle(
            name="Internet + Voice Bundle",
            included_services=[internet_plan["plan_id"], voice_plan["plan_id"]],
            discount_value=15.0
        )

        customer_id = str(uuid4())

        # Provision each service in the bundle
        internet_instance = await management_sdk.create_service_instance(
            customer_id=customer_id,
            service_plan_id=internet_plan["plan_id"],
            bundle_id=bundle["bundle_id"]
        )

        voice_instance = await management_sdk.create_service_instance(
            customer_id=customer_id,
            service_plan_id=voice_plan["plan_id"],
            bundle_id=bundle["bundle_id"]
        )

        # Verify both services are associated with the bundle
        assert internet_instance["customer_id"] == customer_id
        assert voice_instance["customer_id"] == customer_id

        # List all services for customer
        customer_services = await management_sdk.list_services_by_state(
            state=ServiceState.REQUESTED.value,
            customer_id=customer_id
        )

        assert len(customer_services) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
