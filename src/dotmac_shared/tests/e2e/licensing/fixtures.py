"""Test fixtures for licensing E2E tests."""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import httpx
from contextlib import asynccontextmanager

from dotmac_shared.core.logging import get_logger
from .factories import (
    TenantFactory, LicenseContractFactory, FeatureFlagFactory,
    TestScenarioFactory, UserFactory
)

logger = get_logger(__name__)


class LicenseTestFixtures:
    """Centralized fixture management for license testing."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.created_resources: List[Dict[str, Any]] = []
        self.http_client: Optional[httpx.AsyncClient] = None
    
    async def setup(self):
        """Initialize test fixtures."""
        self.http_client = httpx.AsyncClient(timeout=30.0)
        logger.info("License test fixtures initialized")
    
    async def cleanup(self):
        """Cleanup all created test resources."""
        if self.http_client:
            # Cleanup in reverse order of creation
            for resource in reversed(self.created_resources):
                try:
                    await self._cleanup_resource(resource)
                except Exception as e:
                    logger.warning(f"Failed to cleanup resource {resource}: {e}")
            
            await self.http_client.aclose()
        
        self.created_resources.clear()
        logger.info("License test fixtures cleaned up")
    
    async def create_tenant_with_license(self, plan: str = "premium") -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Create a tenant with associated license contract."""
        if plan == "basic":
            tenant, license = TestScenarioFactory.basic_tenant_with_license()
        elif plan == "enterprise":
            tenant, license = TestScenarioFactory.enterprise_tenant_with_license()
        else:
            tenant, license = TestScenarioFactory.premium_tenant_with_license()
        
        # Create tenant in management platform
        tenant_data = await self._create_tenant(tenant.__dict__)
        
        # Create license contract
        license_data = await self._create_license_contract(license.__dict__)
        
        # Track for cleanup
        self.created_resources.extend([
            {"type": "license", "id": license_data["contract_id"]},
            {"type": "tenant", "id": tenant_data["tenant_id"]}
        ])
        
        return tenant_data, license_data
    
    async def create_user_for_tenant(self, tenant_id: str, role: str = "user") -> Dict[str, Any]:
        """Create a user for a specific tenant."""
        if role == "admin":
            user = UserFactory.admin_user(tenant_id=tenant_id)
        else:
            user = UserFactory.basic_user(tenant_id=tenant_id)
        
        user_data = await self._create_user(user)
        
        self.created_resources.append({
            "type": "user", 
            "id": user_data["user_id"],
            "tenant_id": tenant_id
        })
        
        return user_data
    
    async def create_feature_flag(self, tenant_id: str, feature_name: str, **kwargs) -> Dict[str, Any]:
        """Create a feature flag for a tenant."""
        flag = FeatureFlagFactory(
            tenant_id=tenant_id,
            feature_name=feature_name,
            **kwargs
        )
        
        flag_data = await self._create_feature_flag(flag.__dict__)
        
        self.created_resources.append({
            "type": "feature_flag",
            "tenant_id": tenant_id,
            "feature_name": feature_name
        })
        
        return flag_data
    
    async def expire_license(self, contract_id: str) -> Dict[str, Any]:
        """Expire a license contract immediately."""
        update_data = {
            "valid_until": (datetime.now() - timedelta(hours=1)).isoformat(),
            "status": "expired"
        }
        
        response = await self.http_client.patch(
            f"{self.base_url}/api/v1/licensing/contracts/{contract_id}",
            json=update_data
        )
        response.raise_for_status()
        return response.json()["data"]
    
    async def suspend_license(self, contract_id: str) -> Dict[str, Any]:
        """Suspend a license contract."""
        update_data = {"status": "suspended"}
        
        response = await self.http_client.patch(
            f"{self.base_url}/api/v1/licensing/contracts/{contract_id}",
            json=update_data
        )
        response.raise_for_status()
        return response.json()["data"]
    
    async def upgrade_license_plan(self, contract_id: str, new_plan: str) -> Dict[str, Any]:
        """Upgrade a license to a new plan."""
        if new_plan == "enterprise":
            license = LicenseContractFactory.enterprise_license()
        else:  # premium
            license = LicenseContractFactory()
        
        update_data = {
            "contract_type": new_plan,
            "max_customers": license.max_customers,
            "max_concurrent_users": license.max_concurrent_users,
            "max_api_calls_per_hour": license.max_api_calls_per_hour,
            "max_network_devices": license.max_network_devices,
            "enabled_features": license.enabled_features,
            "feature_limits": license.feature_limits
        }
        
        response = await self.http_client.patch(
            f"{self.base_url}/api/v1/licensing/contracts/{contract_id}",
            json=update_data
        )
        response.raise_for_status()
        return response.json()["data"]
    
    async def simulate_usage_near_limit(self, tenant_id: str, feature: str, percentage: float = 90.0):
        """Simulate usage near license limits."""
        # Get current license to determine limits
        license = await self._get_license_by_tenant(tenant_id)
        
        if feature == "customers":
            limit = license.get("max_customers", 100)
            target_count = int(limit * percentage / 100)
            
            # Create customers to approach limit
            for i in range(target_count):
                customer_data = {
                    "name": f"Test Customer {i+1}",
                    "email": f"customer{i+1}@test.com",
                    "tenant_id": tenant_id
                }
                await self._create_customer(customer_data)
        
        elif feature == "api_calls":
            # Simulate API call usage through direct usage log creation
            limit = license.get("max_api_calls_per_hour", 1000)
            target_calls = int(limit * percentage / 100)
            
            usage_data = {
                "tenant_id": tenant_id,
                "feature": "api_calls_per_hour",
                "usage_count": target_calls,
                "timestamp": datetime.now().isoformat()
            }
            await self._record_usage(usage_data)
    
    async def wait_for_feature_propagation(self, tenant_id: str, feature_name: str, timeout: int = 30):
        """Wait for feature flag changes to propagate across apps."""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < timeout:
            try:
                # Check feature availability across multiple app endpoints
                apps_to_check = ["admin", "customer", "reseller"]
                
                propagated_count = 0
                for app in apps_to_check:
                    app_url = f"http://localhost:300{apps_to_check.index(app)}"
                    
                    try:
                        response = await self.http_client.get(
                            f"{app_url}/api/v1/features/{feature_name}",
                            headers={"X-Tenant-ID": tenant_id}
                        )
                        
                        if response.status_code == 200:
                            feature_data = response.json()
                            if feature_data.get("enabled"):
                                propagated_count += 1
                    except:
                        pass  # App might not be running or feature not implemented
                
                # If feature is available in at least one app, consider it propagated
                if propagated_count > 0:
                    return True
            
            except Exception as e:
                logger.debug(f"Feature propagation check failed: {e}")
            
            await asyncio.sleep(1)
        
        return False
    
    # Private helper methods
    async def _create_tenant(self, tenant_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create tenant via management API."""
        response = await self.http_client.post(
            f"{self.base_url}/api/v1/tenants",
            json=tenant_data
        )
        response.raise_for_status()
        return response.json()["data"]
    
    async def _create_license_contract(self, license_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create license contract via management API."""
        # Convert datetime objects to ISO strings
        for key, value in license_data.items():
            if isinstance(value, datetime):
                license_data[key] = value.isoformat()
        
        response = await self.http_client.post(
            f"{self.base_url}/api/v1/licensing/contracts",
            json=license_data
        )
        response.raise_for_status()
        return response.json()["data"]
    
    async def _create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create user via management API."""
        response = await self.http_client.post(
            f"{self.base_url}/api/v1/users",
            json=user_data
        )
        response.raise_for_status()
        return response.json()["data"]
    
    async def _create_feature_flag(self, flag_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create feature flag via management API."""
        response = await self.http_client.post(
            f"{self.base_url}/api/v1/feature-flags",
            json=flag_data
        )
        response.raise_for_status()
        return response.json()["data"]
    
    async def _create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create customer via ISP API."""
        isp_url = "http://localhost:3000"  # Admin portal
        
        response = await self.http_client.post(
            f"{isp_url}/api/v1/customers",
            json=customer_data,
            headers={"X-Tenant-ID": customer_data["tenant_id"]}
        )
        response.raise_for_status()
        return response.json()["data"]
    
    async def _record_usage(self, usage_data: Dict[str, Any]):
        """Record usage data."""
        response = await self.http_client.post(
            f"{self.base_url}/api/v1/licensing/usage",
            json=usage_data
        )
        response.raise_for_status()
    
    async def _get_license_by_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """Get license contract by tenant ID."""
        response = await self.http_client.get(
            f"{self.base_url}/api/v1/licensing/contracts/by-tenant/{tenant_id}"
        )
        response.raise_for_status()
        return response.json()["data"]
    
    async def _cleanup_resource(self, resource: Dict[str, Any]):
        """Cleanup a single resource."""
        if resource["type"] == "tenant":
            await self.http_client.delete(
                f"{self.base_url}/api/v1/tenants/{resource['id']}"
            )
        elif resource["type"] == "license":
            await self.http_client.delete(
                f"{self.base_url}/api/v1/licensing/contracts/{resource['id']}"
            )
        elif resource["type"] == "user":
            await self.http_client.delete(
                f"{self.base_url}/api/v1/users/{resource['id']}"
            )
        elif resource["type"] == "feature_flag":
            await self.http_client.delete(
                f"{self.base_url}/api/v1/feature-flags/{resource['tenant_id']}/{resource['feature_name']}"
            )


@asynccontextmanager
async def license_fixtures():
    """Context manager for license test fixtures."""
    fixtures = LicenseTestFixtures()
    await fixtures.setup()
    try:
        yield fixtures
    finally:
        await fixtures.cleanup()