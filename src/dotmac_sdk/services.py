"""
DotMac SDK Service Classes

Individual service clients for different API endpoints.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from .client import DotMacClient


class CustomerService:
    """Customer management operations."""

    def __init__(self, client: "DotMacClient"):
        """__init__ service method."""
        self.client = client

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new customer."""
        response = self.client.request("POST", "/api/v1/customers", json_data=data)
        return response.json()

    def get(self, customer_id: str) -> Dict[str, Any]:
        """Get customer by ID."""
        response = self.client.request("GET", f"/api/v1/customers/{customer_id}")
        return response.json()

    def list(
        self,
        page: int = 1,
        limit: int = 20,
        state: Optional[str] = None,
        customer_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List customers with pagination."""
        params = {"page": page, "limit": limit}
        if state:
            params["state"] = state
        if customer_type:
            params["customer_type"] = customer_type

        response = self.client.request("GET", "/api/v1/customers", params=params)
        return response.json()


class InvoiceService:
    """Invoice and billing operations."""

    def __init__(self, client: "DotMacClient"):
        """__init__ service method."""
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


class ServiceManagement:
    """Service provisioning and management."""

    def __init__(self, client: "DotMacClient"):
        """__init__ service method."""
        self.client = client

    def list(self, customer_id: Optional[str] = None) -> Dict[str, Any]:
        """List services."""
        params = {"customer_id": customer_id} if customer_id else {}
        response = self.client.request("GET", "/api/v1/services", params=params)
        return response.json()


# TicketService removed - use dotmac_shared.ticketing package instead


class NetworkService:
    """Network management operations."""

    def __init__(self, client: "DotMacClient"):
        """__init__ service method."""
        self.client = client

    def get_status(self) -> Dict[str, Any]:
        """Get network status."""
        response = self.client.request("GET", "/api/v1/network/status")
        return response.json()

    def list_devices(self) -> Dict[str, Any]:
        """List network devices."""
        response = self.client.request("GET", "/api/v1/network/devices")
        return response.json()
