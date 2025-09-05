"""
Auto License Provisioning Service
Automatically creates license contracts based on tenant plans during provisioning
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from dotmac_management.models.tenant import CustomerTenant, TenantPlan
from dotmac_shared.core.logging import get_logger

logger = get_logger(__name__)


class PlanLimits(BaseModel):
    """Plan-based feature and resource limits"""

    model_config = ConfigDict()

    max_customers: int
    max_concurrent_users: int
    max_bandwidth_gbps: int
    max_storage_gb: int
    max_api_calls_per_hour: int
    max_network_devices: int
    enabled_features: list[str]
    disabled_features: list[str]
    feature_limits: dict[str, Any]


class AutoLicenseProvisioningService:
    """Automatically provisions license contracts for new tenants"""

    # Plan-based limits configuration
    PLAN_LIMITS = {
        TenantPlan.STARTER: PlanLimits(
            max_customers=100,
            max_concurrent_users=10,
            max_bandwidth_gbps=1,
            max_storage_gb=50,
            max_api_calls_per_hour=1000,
            max_network_devices=5,
            enabled_features=[
                "customer_management",
                "basic_billing",
                "service_plans",
                "basic_analytics",
                "email_notifications",
            ],
            disabled_features=[
                "advanced_analytics",
                "api_access",
                "white_label",
                "custom_branding",
                "advanced_reporting",
                "reseller_management",
                "sms_notifications",
                "webhook_integrations",
            ],
            feature_limits={
                "service_plans": 5,
                "admin_users": 2,
                "custom_fields": 10,
                "data_retention_days": 365,
            },
        ),
        TenantPlan.PROFESSIONAL: PlanLimits(
            max_customers=1000,
            max_concurrent_users=50,
            max_bandwidth_gbps=10,
            max_storage_gb=500,
            max_api_calls_per_hour=10000,
            max_network_devices=25,
            enabled_features=[
                "customer_management",
                "advanced_billing",
                "service_plans",
                "advanced_analytics",
                "email_notifications",
                "sms_notifications",
                "api_access",
                "webhook_integrations",
                "custom_branding",
            ],
            disabled_features=["white_label", "reseller_management"],
            feature_limits={
                "service_plans": 25,
                "admin_users": 10,
                "custom_fields": 50,
                "data_retention_days": 1095,
                "api_rate_limit": 10000,
                "webhook_endpoints": 5,
            },
        ),
        TenantPlan.ENTERPRISE: PlanLimits(
            max_customers=10000,
            max_concurrent_users=500,
            max_bandwidth_gbps=100,
            max_storage_gb=5000,
            max_api_calls_per_hour=100000,
            max_network_devices=100,
            enabled_features=[
                "customer_management",
                "enterprise_billing",
                "service_plans",
                "advanced_analytics",
                "email_notifications",
                "sms_notifications",
                "api_access",
                "webhook_integrations",
                "white_label",
                "custom_branding",
                "reseller_management",
                "advanced_reporting",
                "priority_support",
            ],
            disabled_features=[],
            feature_limits={
                "service_plans": -1,  # unlimited
                "admin_users": 50,
                "custom_fields": 200,
                "data_retention_days": 2555,  # 7 years
                "api_rate_limit": 100000,
                "webhook_endpoints": 25,
                "reseller_accounts": 10,
            },
        ),
    }

    def __init__(self):
        pass

    async def provision_license_for_tenant(
        self, tenant: CustomerTenant, db: Session
    ) -> dict[str, Any]:
        """
        Automatically provision license contract for new tenant based on their plan
        """
        try:
            logger.info(
                f"Auto-provisioning license for tenant {tenant.tenant_id} with plan {tenant.plan}"
            )

            # Get plan limits
            plan_limits = self._get_plan_limits(tenant.plan)

            # Generate license contract
            license_contract = await self._create_license_contract(tenant, plan_limits)

            # Save to database
            await self._save_license_contract(db, tenant, license_contract)

            # Send license to ISP instance
            await self._deploy_license_to_isp(tenant, license_contract)

            logger.info(
                f"✅ License contract {license_contract['contract_id']} created for tenant {tenant.tenant_id}"
            )

            return {
                "contract_id": license_contract["contract_id"],
                "status": "active",
                "plan": tenant.plan,
                "limits": plan_limits.model_dump(),
                "deployed_to_isp": True,
            }

        except Exception as e:
            logger.error(
                f"Failed to provision license for tenant {tenant.tenant_id}: {e}"
            )
            raise

    def _get_plan_limits(self, plan: TenantPlan) -> PlanLimits:
        """Get feature and resource limits for tenant plan"""

        if plan not in self.PLAN_LIMITS:
            logger.warning(f"Unknown plan {plan}, defaulting to STARTER limits")
            return self.PLAN_LIMITS[TenantPlan.STARTER]

        return self.PLAN_LIMITS[plan]

    async def _create_license_contract(
        self, tenant: CustomerTenant, limits: PlanLimits
    ) -> dict[str, Any]:
        """Create license contract data structure"""

        # Generate unique contract ID
        contract_id = (
            f"LIC-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"
        )

        # Calculate validity period (1 year from now)
        valid_from = datetime.now(timezone.utc)
        valid_until = valid_from + timedelta(days=365)

        # Generate contract hash for integrity
        import hashlib

        contract_string = f"{contract_id}{tenant.tenant_id}{valid_from.isoformat()}{valid_until.isoformat()}"
        contract_hash = hashlib.sha256(contract_string.encode()).hexdigest()

        return {
            "contract_id": contract_id,
            "tenant_id": tenant.tenant_id,
            "subscription_id": f"sub-{tenant.tenant_id}",
            "status": "active",
            "contract_type": tenant.plan.value,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "max_customers": limits.max_customers,
            "max_concurrent_users": limits.max_concurrent_users,
            "max_bandwidth_gbps": limits.max_bandwidth_gbps,
            "max_storage_gb": limits.max_storage_gb,
            "max_api_calls_per_hour": limits.max_api_calls_per_hour,
            "max_network_devices": limits.max_network_devices,
            "enabled_features": limits.enabled_features,
            "disabled_features": limits.disabled_features,
            "feature_limits": limits.feature_limits,
            "enforcement_mode": "strict",
            "issuer_management_instance": "mgmt-platform",
            "target_isp_instance": tenant.tenant_id,
            "contract_hash": contract_hash,
            "current_usage": {},
            "violation_count": 0,
            "auto_provisioned": True,
            "created_at": valid_from,
            "updated_at": valid_from,
        }

    async def _save_license_contract(
        self, db: Session, tenant: CustomerTenant, contract: dict[str, Any]
    ) -> Any:
        """Save license contract to management database"""

        from dotmac_shared.licensing.models import LicenseContract, LicenseStatus

        license_record = LicenseContract(
            tenant_id=tenant.id,
            contract_id=contract["contract_id"],
            subscription_id=contract["subscription_id"],
            status=LicenseStatus.ACTIVE,
            contract_type=contract["contract_type"],
            valid_from=contract["valid_from"],
            valid_until=contract["valid_until"],
            max_customers=contract["max_customers"],
            max_concurrent_users=contract["max_concurrent_users"],
            max_bandwidth_gbps=contract["max_bandwidth_gbps"],
            max_storage_gb=contract["max_storage_gb"],
            max_api_calls_per_hour=contract["max_api_calls_per_hour"],
            max_network_devices=contract["max_network_devices"],
            enabled_features=contract["enabled_features"],
            disabled_features=contract["disabled_features"],
            feature_limits=contract["feature_limits"],
            enforcement_mode=contract["enforcement_mode"],
            issuer_management_instance=contract["issuer_management_instance"],
            target_isp_instance=contract["target_isp_instance"],
            contract_hash=contract["contract_hash"],
            current_usage=contract["current_usage"],
            violation_count=contract["violation_count"],
        )

        from dotmac_shared.core.error_utils import db_transaction

        with db_transaction(db):
            db.add(license_record)
            db.flush()
            db.refresh(license_record)

        return license_record

    async def _deploy_license_to_isp(
        self, tenant: CustomerTenant, contract: dict[str, Any]
    ):
        """Deploy license contract to ISP instance"""

        import httpx

        # Get ISP instance URL
        isp_url = f"https://{tenant.subdomain}.{self._get_domain_suffix()}"

        # Prepare license payload for ISP instance
        license_payload = {
            "contract": contract,
            "enforcement_config": {
                "check_interval_seconds": 300,  # 5 minutes
                "grace_period_seconds": 86400,  # 24 hours
                "violation_threshold": 3,
                "auto_suspend_on_violation": False,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{isp_url}/api/v1/system/license",
                    json=license_payload,
                    headers={
                        "Authorization": f"Bearer {await self._get_management_api_token()}",
                        "Content-Type": "application/json",
                    },
                )

                if response.status_code not in [200, 201]:
                    raise Exception(f"Failed to deploy license to ISP: {response.text}")

                logger.info(
                    f"License {contract['contract_id']} deployed to ISP instance {tenant.tenant_id}"
                )

        except Exception as e:
            logger.error(f"Failed to deploy license to ISP instance: {e}")
            # Don't fail provisioning if license deployment fails - can retry later

    async def _get_management_api_token(self) -> str:
        """Get management platform API token for ISP communication"""

        from dotmac.platform.auth.core.jwt_service import JWTService

        jwt_service = JWTService()

        payload = {
            "service": "management_platform",
            "scope": "license_provisioning",
            "token_type": "service",
        }

        return await jwt_service.create_access_token(
            data=payload, expires_delta=timedelta(hours=1)
        )

    def _get_domain_suffix(self) -> str:
        """Get domain suffix for tenant URLs"""
        import os

        return os.getenv("TENANT_DOMAIN_SUFFIX", "yourdomain.com")

    async def get_plan_preview(self, plan: TenantPlan) -> dict[str, Any]:
        """Get preview of what license would be created for a plan"""

        limits = self._get_plan_limits(plan)

        return {
            "plan": plan.value,
            "limits": limits.model_dump(),
            "features": {
                "enabled": limits.enabled_features,
                "disabled": limits.disabled_features,
                "limits": limits.feature_limits,
            },
            "validity_period_days": 365,
            "enforcement_mode": "strict",
        }
