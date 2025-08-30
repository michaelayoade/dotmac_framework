"""
DotMac Framework Python SDK

Official Python SDK for the DotMac Platform API.
"""

from typing import Any, Dict, Optional

import httpx

__version__ = "1.0.0"
__author__ = "DotMac Team"
__email__ = "support@dotmac.com"

# Main client exports
from .client import DotMacClient
from .exceptions import DotMacAPIError, DotMacAuthError, DotMacConfigError

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "DotMacClient",
    "DotMacAPIError",
    "DotMacAuthError",
    "DotMacConfigError",
]


# Legacy compatibility - keep the old class for backwards compatibility
class _LegacyDotMacClient:
    """Main client for DotMac Platform API."""

    def __init__(
        self,
        base_url: str = "https://api.dotmac.com",
        api_key: Optional[str] = None,
        access_token: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize DotMac API client.

        Args:
            base_url: API base URL
            api_key: API key for authentication
            access_token: JWT access token for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # Set up authentication headers
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["X-API-Key"] = api_key
        elif access_token:
            self.headers["Authorization"] = f"Bearer {access_token}"

        # Initialize service clients
        self.customers = CustomerService(self)
        self.invoices = InvoiceService(self)
        self.services = ServiceManagement(self)
        self.tickets = TicketService(self)
        self.network = NetworkService(self)

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        **kwargs,
    ) -> httpx.Response:
        """Make HTTP request to API."""
        url = f"{self.base_url}{path}"

        with httpx.Client(timeout=self.timeout) as client:
            response = client.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=json_data,
                **kwargs,
            )
            response.raise_for_status()
            return response


class CustomerService:
    """Customer management operations."""

    def __init__(self, client: DotMacClient):
        self.client = client

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new customer.

        Args:
            data: Customer data including display_name, customer_type, etc.

        Returns:
            Created customer object
        """
        response = self.client.request("POST", "/api/v1/customers", json_data=data)
        return response.json()

    def get(self, customer_id: str) -> Dict[str, Any]:
        """
        Get customer by ID.

        Args:
            customer_id: Customer unique identifier

        Returns:
            Customer object
        """
        response = self.client.request("GET", f"/api/v1/customers/{customer_id}")
        return response.json()

    def list(
        self,
        page: int = 1,
        limit: int = 20,
        state: Optional[str] = None,
        customer_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List customers with pagination.

        Args:
            page: Page number (1-based)
            limit: Items per page
            state: Filter by customer state
            customer_type: Filter by customer type

        Returns:
            Paginated list of customers
        """
        params = {"page": page, "limit": limit}
        if state:
            params["state"] = state
        if customer_type:
            params["customer_type"] = customer_type

        response = self.client.request("GET", "/api/v1/customers", params=params)
        return response.json()

    def update(self, customer_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update customer information.

        Args:
            customer_id: Customer unique identifier
            data: Fields to update

        Returns:
            Updated customer object
        """
        response = self.client.request(
            "PATCH", f"/api/v1/customers/{customer_id}", json_data=data
        )
        return response.json()

    def activate(
        self, customer_id: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Activate customer account.

        Args:
            customer_id: Customer unique identifier
            reason: Activation reason

        Returns:
            Updated customer object
        """
        data = {"reason": reason} if reason else {}
        response = self.client.request(
            "POST", f"/api/v1/customers/{customer_id}/activate", json_data=data
        )
        return response.json()

    def suspend(self, customer_id: str, reason: str) -> Dict[str, Any]:
        """
        Suspend customer account.

        Args:
            customer_id: Customer unique identifier
            reason: Suspension reason

        Returns:
            Updated customer object
        """
        response = self.client.request(
            "POST",
            f"/api/v1/customers/{customer_id}/suspend",
            json_data={"reason": reason},
        )
        return response.json()

    def delete(self, customer_id: str, force: bool = False) -> None:
        """
        Delete customer account.

        Args:
            customer_id: Customer unique identifier
            force: Force delete even with active services
        """
        params = {"force": force} if force else {}
        self.client.request("DELETE", f"/api/v1/customers/{customer_id}", params=params)


class InvoiceService:
    """Invoice and billing operations."""

    def __init__(self, client: DotMacClient):
        self.client = client

    def list(
        self, customer_id: Optional[str] = None, status: Optional[str] = None
    ) -> Dict[str, Any]:
        """List invoices with optional filtering."""
        params = {}
        if customer_id:
            params["customer_id"] = customer_id
        if status:
            params["status"] = status

        response = self.client.request("GET", "/api/v1/invoices", params=params)
        return response.json()

    def get(self, invoice_id: str) -> Dict[str, Any]:
        """Get invoice by ID."""
        response = self.client.request("GET", f"/api/v1/invoices/{invoice_id}")
        return response.json()

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new invoice."""
        response = self.client.request("POST", "/api/v1/invoices", json_data=data)
        return response.json()


class ServiceManagement:
    """Service provisioning and management."""

    def __init__(self, client: DotMacClient):
        self.client = client

    def list(self, customer_id: Optional[str] = None) -> Dict[str, Any]:
        """List services."""
        params = {"customer_id": customer_id} if customer_id else {}
        response = self.client.request("GET", "/api/v1/services", params=params)
        return response.json()

    def provision(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Provision new service."""
        response = self.client.request(
            "POST", "/api/v1/services/provision", json_data=data
        )
        return response.json()

    def activate(self, service_id: str) -> Dict[str, Any]:
        """Activate service."""
        response = self.client.request(
            "POST", f"/api/v1/services/{service_id}/activate"
        )
        return response.json()

    def suspend(self, service_id: str, reason: str) -> Dict[str, Any]:
        """Suspend service."""
        response = self.client.request(
            "POST",
            f"/api/v1/services/{service_id}/suspend",
            json_data={"reason": reason},
        )
        return response.json()


# TicketService removed - use dotmac_shared.ticketing package instead


class NetworkService:
    """Network management operations."""

    def __init__(self, client: DotMacClient):
        self.client = client

    def get_status(self) -> Dict[str, Any]:
        """Get network status."""
        response = self.client.request("GET", "/api/v1/network/status")
        return response.json()

    def list_devices(self) -> Dict[str, Any]:
        """List network devices."""
        response = self.client.request("GET", "/api/v1/network/devices")
        return response.json()

    def get_device(self, device_id: str) -> Dict[str, Any]:
        """Get device details."""
        response = self.client.request("GET", f"/api/v1/network/devices/{device_id}")
        return response.json()


# Exception classes
class DotMacAPIError(Exception):
    """Base exception for DotMac API errors."""

    pass


class AuthenticationError(DotMacAPIError):
    """Authentication failed."""

    pass


class RateLimitError(DotMacAPIError):
    """Rate limit exceeded."""

    pass


class ValidationError(DotMacAPIError):
    """Request validation failed."""

    pass
