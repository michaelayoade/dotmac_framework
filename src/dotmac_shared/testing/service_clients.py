"""
Service client manager for integration testing
"""
import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class ServiceClient:
    """Base service client for HTTP API testing"""

    def __init__(self, base_url: str, service_name: str):
        self.base_url = base_url.rstrip("/")
        self.service_name = service_name
        self._client = None

    async def initialize(self):
        """Initialize HTTP client"""
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        logger.info(f"Initialized {self.service_name} client for {self.base_url}")

    async def cleanup(self):
        """Cleanup HTTP client"""
        if self._client:
            await self._client.aclose()
            logger.info(f"Cleaned up {self.service_name} client")

    async def get(self, path: str, **kwargs) -> httpx.Response:
        """Make GET request"""
        return await self._client.get(path, **kwargs)

    async def post(self, path: str, **kwargs) -> httpx.Response:
        """Make POST request"""
        return await self._client.post(path, **kwargs)

    async def put(self, path: str, **kwargs) -> httpx.Response:
        """Make PUT request"""
        return await self._client.put(path, **kwargs)

    async def delete(self, path: str, **kwargs) -> httpx.Response:
        """Make DELETE request"""
        return await self._client.delete(path, **kwargs)


class ISPServiceClient(ServiceClient):
    """Client for ISP service API testing"""

    def __init__(self, base_url: str = "http://localhost:8001"):
        super().__init__(base_url, "isp_service")

    async def create_service_plan(self, plan_data: dict[str, Any], journey_id: str) -> dict[str, Any]:
        """Create a service plan"""
        response = await self.post("/api/service-plans", json=plan_data, headers={"X-Journey-ID": journey_id})
        response.raise_for_status()
        return response.json()

    async def create_subscription(self, subscription_data: dict[str, Any], journey_id: str) -> dict[str, Any]:
        """Create a service subscription"""
        response = await self.post(
            "/api/subscriptions",
            json=subscription_data,
            headers={"X-Journey-ID": journey_id},
        )
        response.raise_for_status()
        return response.json()

    async def provision_service(self, subscription_id: str, journey_id: str) -> dict[str, Any]:
        """Provision a service"""
        response = await self.post(
            f"/api/subscriptions/{subscription_id}/provision",
            headers={"X-Journey-ID": journey_id},
        )
        response.raise_for_status()
        return response.json()

    async def suspend_service(
        self, subscription_id: str, suspension_data: dict[str, Any], journey_id: str
    ) -> dict[str, Any]:
        """Suspend a service"""
        response = await self.post(
            f"/api/subscriptions/{subscription_id}/suspend",
            json=suspension_data,
            headers={"X-Journey-ID": journey_id},
        )
        response.raise_for_status()
        return response.json()

    async def restore_service(
        self, subscription_id: str, restoration_data: dict[str, Any], journey_id: str
    ) -> dict[str, Any]:
        """Restore a suspended service"""
        response = await self.post(
            f"/api/subscriptions/{subscription_id}/restore",
            json=restoration_data,
            headers={"X-Journey-ID": journey_id},
        )
        response.raise_for_status()
        return response.json()

    async def reconfigure_service(
        self, subscription_id: str, config_data: dict[str, Any], journey_id: str
    ) -> dict[str, Any]:
        """Reconfigure a service"""
        response = await self.put(
            f"/api/subscriptions/{subscription_id}/configuration",
            json=config_data,
            headers={"X-Journey-ID": journey_id},
        )
        response.raise_for_status()
        return response.json()


class CustomerServiceClient(ServiceClient):
    """Client for customer service API testing"""

    def __init__(self, base_url: str = "http://localhost:8003"):
        super().__init__(base_url, "customer_service")

    async def register_customer(self, customer_data: dict[str, Any], journey_id: str) -> dict[str, Any]:
        """Register a new customer"""
        response = await self.post(
            "/api/customers/register",
            json=customer_data,
            headers={"X-Journey-ID": journey_id},
        )
        response.raise_for_status()
        return response.json()

    async def request_service_upgrade(self, upgrade_data: dict[str, Any], journey_id: str) -> dict[str, Any]:
        """Request service upgrade"""
        response = await self.post(
            "/api/service-upgrades",
            json=upgrade_data,
            headers={"X-Journey-ID": journey_id},
        )
        response.raise_for_status()
        return response.json()


class ManagementServiceClient(ServiceClient):
    """Client for management service API testing"""

    def __init__(self, base_url: str = "http://localhost:8002"):
        super().__init__(base_url, "management_service")

    async def approve_upgrade_request(
        self, request_id: str, approval_data: dict[str, Any], journey_id: str
    ) -> dict[str, Any]:
        """Approve an upgrade request"""
        response = await self.put(
            f"/api/upgrade-requests/{request_id}/approve",
            json=approval_data,
            headers={"X-Journey-ID": journey_id},
        )
        response.raise_for_status()
        return response.json()


class BillingServiceClient(ServiceClient):
    """Client for billing service API testing"""

    def __init__(self, base_url: str = "http://localhost:8004"):
        super().__init__(base_url, "billing_service")

    async def create_billing_account(self, account_data: dict[str, Any], journey_id: str) -> dict[str, Any]:
        """Create billing account"""
        response = await self.post(
            "/api/billing-accounts",
            json=account_data,
            headers={"X-Journey-ID": journey_id},
        )
        response.raise_for_status()
        return response.json()

    async def generate_invoice(self, account_id: str, journey_id: str) -> dict[str, Any]:
        """Generate invoice"""
        response = await self.post(
            f"/api/billing-accounts/{account_id}/invoices",
            headers={"X-Journey-ID": journey_id},
        )
        response.raise_for_status()
        return response.json()

    async def process_payment(self, account_id: str, payment_data: dict[str, Any], journey_id: str) -> dict[str, Any]:
        """Process payment"""
        response = await self.post(
            f"/api/billing-accounts/{account_id}/payments",
            json=payment_data,
            headers={"X-Journey-ID": journey_id},
        )
        response.raise_for_status()
        return response.json()

    async def simulate_payment_failure(
        self, account_id: str, failure_data: dict[str, Any], journey_id: str
    ) -> dict[str, Any]:
        """Simulate payment failure for testing"""
        response = await self.post(
            f"/api/billing-accounts/{account_id}/payments/simulate-failure",
            json=failure_data,
            headers={"X-Journey-ID": journey_id},
        )
        response.raise_for_status()
        return response.json()

    async def process_plan_change(
        self, account_id: str, change_data: dict[str, Any], journey_id: str
    ) -> dict[str, Any]:
        """Process billing plan change"""
        response = await self.post(
            f"/api/billing-accounts/{account_id}/plan-changes",
            json=change_data,
            headers={"X-Journey-ID": journey_id},
        )
        response.raise_for_status()
        return response.json()


class NotificationServiceClient(ServiceClient):
    """Client for notification service API testing"""

    def __init__(self, base_url: str = "http://localhost:8080"):
        super().__init__(base_url, "notification_service")

    async def get_notifications_by_journey(self, journey_id: str) -> list[dict[str, Any]]:
        """Get notifications by journey ID"""
        response = await self.get("/api/notifications", params={"journey_id": journey_id})
        response.raise_for_status()
        return response.json()

    async def get_notifications_by_customer(
        self, customer_id: str, notification_type: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Get notifications by customer ID"""
        params = {"customer_id": customer_id}
        if notification_type:
            params["type"] = notification_type

        response = await self.get("/api/notifications", params=params)
        response.raise_for_status()
        return response.json()


class ServiceClientManager:
    """Manages multiple service clients for integration testing"""

    def __init__(self):
        self.clients = {}

    async def initialize_clients(self, service_names: list[str]):
        """Initialize specified service clients"""
        client_classes = {
            "isp_service": ISPServiceClient,
            "customer_service": CustomerServiceClient,
            "management_service": ManagementServiceClient,
            "billing_service": BillingServiceClient,
            "notification_service": NotificationServiceClient,
        }

        for service_name in service_names:
            if service_name in client_classes:
                client = client_classes[service_name]()
                await client.initialize()
                self.clients[service_name] = client
                logger.info(f"Initialized {service_name} client")

        # Create convenience properties
        self.isp_service = self.clients.get("isp_service")
        self.customer_service = self.clients.get("customer_service")
        self.management_service = self.clients.get("management_service")
        self.billing_service = self.clients.get("billing_service")
        self.notification_service = self.clients.get("notification_service")

    async def cleanup(self):
        """Cleanup all service clients"""
        for client in self.clients.values():
            await client.cleanup()
        self.clients.clear()
        logger.info("Cleaned up all service clients")
