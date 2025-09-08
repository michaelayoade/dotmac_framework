"""
Integration examples showing how to use the DotMac Billing Package
in different platform scenarios.
"""

from datetime import date
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters import create_basic_billing_service, create_stripe_billing_service
from ..adapters.isp_platform_adapter import ISPBillingAdapter
from ..adapters.management_platform_adapter import ManagementPlatformBillingAdapter
from ..schemas.billing_schemas import (
    CustomerCreate,
)


async def example_basic_isp_billing(db: AsyncSession):
    """Example: Basic ISP billing workflow."""

    # Create billing service
    billing_service = create_basic_billing_service(db, tenant_id=uuid4())
    adapter = ISPBillingAdapter(billing_service)

    # 1. Create ISP customer
    customer_data = {
        "email": "john.doe@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "phone": "+1-555-0123",
        "address": "123 Main St",
        "city": "Springfield",
        "state": "IL",
        "zip_code": "62701",
        "customer_number": "ISP001",
        "service_address": "123 Main St, Springfield, IL 62701",
    }

    customer_result = await adapter.create_isp_customer(
        customer_data, billing_service.default_tenant_id
    )

    # 2. Create internet service plan
    service_data = {
        "speed_mbps": 100,
        "monthly_price": 59.99,
        "installation_fee": 99.00,
        "has_usage_cap": True,
        "data_cap_gb": 1000,
        "overage_price_per_gb": 0.05,
        "technology": "fiber",
    }

    plan_result = await adapter.create_internet_service_plan(
        service_data, billing_service.default_tenant_id
    )

    # 3. Create customer subscription
    installation_data = {
        "service_start_date": date.today(),
        "installation_address": "123 Main St, Springfield, IL",
        "technician_id": "TECH001",
        "equipment_serial": "ONT123456789",
    }

    subscription_result = await adapter.create_customer_subscription(
        customer_id=customer_result["id"],
        service_plan_id=plan_result["id"],
        installation_data=installation_data,
        tenant_id=billing_service.default_tenant_id,
    )

    # 4. Record bandwidth usage
    usage_data = {
        "data_used_gb": 850.5,
        "usage_date": date.today(),
        "session_id": "session_123",
        "user_mac": "00:11:22:33:44:55",
        "source": "radius_accounting",
    }

    await adapter.record_bandwidth_usage(
        subscription_id=subscription_result["id"],
        usage_data=usage_data,
        tenant_id=billing_service.default_tenant_id,
    )

    # 5. Generate invoice for billing period
    billing_period_data = {
        "period_start": date(2024, 1, 1),
        "period_end": date(2024, 1, 31),
        "service_charges": 59.99,
        "overage_charges": 0.0,  # Under cap
        "total_amount": 59.99,
        "total_usage_gb": 850.5,
        "included_gb": 1000,
        "overage_gb": 0,
    }

    invoice_result = await adapter.generate_service_invoice(
        subscription_id=subscription_result["id"],
        billing_period_data=billing_period_data,
        tenant_id=billing_service.default_tenant_id,
    )

    return {
        "customer": customer_result,
        "plan": plan_result,
        "subscription": subscription_result,
        "invoice": invoice_result,
    }


async def example_saas_platform_billing(db: AsyncSession):
    """Example: SaaS platform billing workflow."""

    # Create billing service with Stripe integration
    billing_service = create_stripe_billing_service(
        db=db, stripe_secret_key="sk_test_example_key", tenant_id=uuid4()
    )
    adapter = ManagementPlatformBillingAdapter(billing_service)

    # 1. Create tenant billing customer
    tenant_data = {
        "tenant_code": "TENANT001",
        "company_name": "Acme ISP Corp",
        "admin_email": "admin@acmeisp.com",
        "phone": "+1-555-0199",
        "address": "456 Business Ave",
        "city": "Chicago",
        "state": "IL",
        "postal_code": "60601",
        "tenant_type": "isp",
        "region": "us-central",
        "user_count": 25,
    }

    customer_result = await adapter.create_tenant_customer(
        tenant_data, billing_service.default_tenant_id
    )

    # 2. Create SaaS billing plan
    plan_data = {
        "plan_code": "ENTERPRISE",
        "name": "Enterprise Plan",
        "description": "Full-featured plan for large ISPs",
        "base_price": 499.99,
        "billing_cycle": "monthly",
        "has_user_tiers": True,
        "included_users": 50,
        "price_per_additional_user": 9.99,
        "setup_fee": 1000.00,
        "trial_days": 14,
        "features": {
            "max_customers": 10000,
            "api_rate_limit": 10000,
            "support_level": "priority",
        },
    }

    plan_result = await adapter.create_saas_plan(
        plan_data, billing_service.default_tenant_id
    )

    # 3. Subscribe tenant to plan
    subscription_data = {
        "start_date": date.today(),
        "quantity": 1,
        "deployment_tier": "enterprise",
        "auto_scaling": True,
    }

    subscription_result = await adapter.subscribe_tenant_to_plan(
        customer_id=customer_result["id"],
        plan_id=plan_result["id"],
        subscription_data=subscription_data,
        master_tenant_id=billing_service.default_tenant_id,
    )

    # 4. Record API usage
    api_usage_data = {
        "api_calls": 5250,
        "usage_date": date.today(),
        "tenant_id": tenant_data["id"],
        "endpoint": "/api/v1/customers",
        "response_time_avg": 150,
        "api_type": "rest",
    }

    await adapter.record_api_usage(
        subscription_id=subscription_result["id"],
        usage_data=api_usage_data,
        master_tenant_id=billing_service.default_tenant_id,
    )

    # 5. Get billing analytics
    analytics_result = await adapter.get_tenant_billing_analytics(
        customer_id=customer_result["id"],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        master_tenant_id=billing_service.default_tenant_id,
    )

    return {
        "customer": customer_result,
        "plan": plan_result,
        "subscription": subscription_result,
        "analytics": analytics_result,
    }


async def example_plugin_marketplace_billing(db: AsyncSession):
    """Example: Plugin marketplace billing workflow."""

    billing_service = create_basic_billing_service(db, tenant_id=uuid4())
    adapter = ManagementPlatformBillingAdapter(billing_service)

    # 1. Create plugin billing plan
    plugin_data = {
        "id": "plugin_advanced_analytics",
        "plugin_code": "ADV_ANALYTICS",
        "name": "Advanced Analytics Plugin",
        "description": "Advanced customer analytics and reporting",
        "version": "2.1.0",
        "vendor_id": "vendor_analytics_pro",
        "category": "analytics",
        "pricing_type": "fixed",
        "price": 29.99,
        "billing_cycle": "monthly",
        "license_type": "subscription",
    }

    plugin_plan_result = await adapter.create_plugin_marketplace_plan(
        plugin_data, billing_service.default_tenant_id
    )

    # 2. Create another usage-based plugin plan
    usage_plugin_data = {
        "id": "plugin_sms_gateway",
        "plugin_code": "SMS_GATEWAY",
        "name": "SMS Gateway Plugin",
        "description": "Send SMS notifications to customers",
        "version": "1.5.2",
        "vendor_id": "vendor_sms_solutions",
        "category": "communications",
        "pricing_type": "usage",
        "price": 0.05,  # Base price per SMS
        "usage_unit": "sms_sent",
        "usage_price": 0.05,
        "billing_cycle": "monthly",
    }

    usage_plugin_plan_result = await adapter.create_plugin_marketplace_plan(
        usage_plugin_data, billing_service.default_tenant_id
    )

    return {
        "plugin_plan": plugin_plan_result,
        "usage_plugin_plan": usage_plugin_plan_result,
    }


async def example_multi_tenant_billing(db: AsyncSession):
    """Example: Multi-tenant billing with isolation."""

    # Create separate billing services for different tenants
    tenant_a_id = uuid4()
    tenant_b_id = uuid4()

    billing_service_a = create_basic_billing_service(db, tenant_id=tenant_a_id)
    billing_service_b = create_basic_billing_service(db, tenant_id=tenant_b_id)

    # Tenant A - Small ISP
    customer_data_a = CustomerCreate(
        customer_code="TENANT_A_CUST001",
        email="customer@tenanta.com",
        name="Tenant A Customer",
        tenant_id=tenant_a_id,
    )
    customer_a = await billing_service_a.customer_repo.create(customer_data_a)

    # Tenant B - Large ISP
    customer_data_b = CustomerCreate(
        customer_code="TENANT_B_CUST001",
        email="customer@tenantb.com",
        name="Tenant B Customer",
        tenant_id=tenant_b_id,
    )
    customer_b = await billing_service_b.customer_repo.create(customer_data_b)

    # Verify tenant isolation
    await billing_service_a.customer_repo.get_multi(tenant_id=tenant_a_id)
    await billing_service_b.customer_repo.get_multi(tenant_id=tenant_b_id)

    # Verify cross-tenant isolation
    await billing_service_a.customer_repo.get(customer_b.id, tenant_a_id)

    return {
        "tenant_a": {"customer": customer_a, "tenant_id": tenant_a_id},
        "tenant_b": {"customer": customer_b, "tenant_id": tenant_b_id},
    }


async def run_all_examples(db: AsyncSession):
    """Run all billing package examples."""

    try:
        # Run examples
        isp_example = await example_basic_isp_billing(db)
        saas_example = await example_saas_platform_billing(db)
        plugin_example = await example_plugin_marketplace_billing(db)
        multi_tenant_example = await example_multi_tenant_billing(db)

        return {
            "isp_billing": isp_example,
            "saas_billing": saas_example,
            "plugin_billing": plugin_example,
            "multi_tenant": multi_tenant_example,
        }

    except Exception:
        raise


if __name__ == "__main__":
    # This would typically be called from your application
    # with a proper database session
    pass
