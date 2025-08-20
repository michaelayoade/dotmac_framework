"""
Schema Registry Client SDK for high-level schema operations.

Provides a high-level async client for:
- Schema registration and retrieval
- Schema validation
- Compatibility checking
- Version management
"""

from typing import Any, Dict, List, Optional

from .http_client import HTTPClient


class SchemasClient:
    """High-level client for schema registry operations."""

    def __init__(
        self,
        base_url: str,
        tenant_id: str,
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize the schemas client.

        Args:
            base_url: Base URL of the API server
            tenant_id: Tenant identifier
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.tenant_id = tenant_id
        self.http_client = HTTPClient(
            base_url=f"{self.base_url}/api/v1/schemas",
            headers={
                "X-Tenant-ID": tenant_id,
                **({"Authorization": f"Bearer {api_key}"} if api_key else {})
            },
            timeout=timeout
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self.http_client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.http_client.__aexit__(exc_type, exc_val, exc_tb)

    async def register_schema(
        self,
        event_type: str,
        version: str,
        schema: Dict[str, Any],
        compatibility_level: str = "BACKWARD"
    ) -> Dict[str, Any]:
        """
        Register a new schema version.

        Args:
            event_type: Event type identifier
            version: Schema version
            schema: JSON schema definition
            compatibility_level: Compatibility level (BACKWARD, FORWARD, FULL, NONE)

        Returns:
            Registration result with schema ID and metadata
        """
        data = {
            "version": version,
            "schema": schema,
            "compatibility_level": compatibility_level
        }

        response = await self.http_client.post(f"/{event_type}", json=data)
        return response

    async def get_schema(
        self,
        event_type: str,
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a schema by event type and version.

        Args:
            event_type: Event type identifier
            version: Schema version (latest if not specified)

        Returns:
            Schema definition and metadata
        """
        url = f"/{event_type}"
        if version:
            url += f"/{version}"

        response = await self.http_client.get(url)
        return response

    async def list_schemas(self, event_type: str) -> List[Dict[str, Any]]:
        """
        List all schema versions for an event type.

        Args:
            event_type: Event type identifier

        Returns:
            List of schema versions with metadata
        """
        response = await self.http_client.get(f"/{event_type}/versions")
        return response.get("versions", [])

    async def validate_data(
        self,
        event_type: str,
        data: Dict[str, Any],
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate data against a schema.

        Args:
            event_type: Event type identifier
            data: Data to validate
            version: Schema version (latest if not specified)

        Returns:
            Validation result with success status and errors
        """
        payload = {
            "data": data
        }
        if version:
            payload["version"] = version

        response = await self.http_client.post(
            f"/{event_type}/validate",
            json=payload
        )
        return response

    async def check_compatibility(
        self,
        event_type: str,
        schema: Dict[str, Any],
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check schema compatibility.

        Args:
            event_type: Event type identifier
            schema: Schema to check compatibility for
            version: Version to check against (latest if not specified)

        Returns:
            Compatibility check result
        """
        payload = {
            "schema": schema
        }
        if version:
            payload["version"] = version

        response = await self.http_client.post(
            f"/{event_type}/compatibility",
            json=payload
        )
        return response

    async def delete_schema(
        self,
        event_type: str,
        version: Optional[str] = None
    ) -> None:
        """
        Delete a schema version.

        Args:
            event_type: Event type identifier
            version: Schema version (all versions if not specified)
        """
        url = f"/{event_type}"
        if version:
            url += f"/{version}"

        await self.http_client.delete(url)

    async def list_event_types(self) -> List[str]:
        """
        List all event types with registered schemas.

        Returns:
            List of event type identifiers
        """
        response = await self.http_client.get("/")
        return response.get("event_types", [])


# Convenience functions
async def register_schema(
    base_url: str,
    tenant_id: str,
    event_type: str,
    version: str,
    schema: Dict[str, Any],
    compatibility_level: str = "BACKWARD",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to register a schema.

    Args:
        base_url: Base URL of the API server
        tenant_id: Tenant identifier
        event_type: Event type identifier
        version: Schema version
        schema: JSON schema definition
        compatibility_level: Compatibility level
        api_key: Optional API key for authentication

    Returns:
        Registration result
    """
    async with SchemasClient(base_url, tenant_id, api_key) as client:
        return await client.register_schema(
            event_type, version, schema, compatibility_level
        )


async def validate_data(
    base_url: str,
    tenant_id: str,
    event_type: str,
    data: Dict[str, Any],
    version: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to validate data against a schema.

    Args:
        base_url: Base URL of the API server
        tenant_id: Tenant identifier
        event_type: Event type identifier
        data: Data to validate
        version: Schema version
        api_key: Optional API key for authentication

    Returns:
        Validation result
    """
    async with SchemasClient(base_url, tenant_id, api_key) as client:
        return await client.validate_data(event_type, data, version)


async def get_schema(
    base_url: str,
    tenant_id: str,
    event_type: str,
    version: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to get a schema.

    Args:
        base_url: Base URL of the API server
        tenant_id: Tenant identifier
        event_type: Event type identifier
        version: Schema version
        api_key: Optional API key for authentication

    Returns:
        Schema definition and metadata
    """
    async with SchemasClient(base_url, tenant_id, api_key) as client:
        return await client.get_schema(event_type, version)
