"""
API Documentation SDK - OpenAPI generation, developer portal, interactive docs.
"""

from datetime import datetime
from ..core.datetime_utils import (
    utc_now_iso,
    utc_now,
    expires_in_days,
    expires_in_hours,
    time_ago_minutes,
    time_ago_hours,
    is_expired_iso,
)
from typing import Any, Dict
from uuid import uuid4


class APIDocumentationService:
    """In-memory service for API documentation operations."""

    def __init__(self):
        self._openapi_specs: Dict[str, Dict[str, Any]] = {}
        self._developer_portals: Dict[str, Dict[str, Any]] = {}
        self._api_explorers: Dict[str, Dict[str, Any]] = {}

    async def generate_openapi_spec(self, **kwargs) -> Dict[str, Any]:
        """Generate OpenAPI specification."""
        spec_id = kwargs.get("spec_id") or str(uuid4())
        gateway_id = kwargs["gateway_id"]

        # Basic OpenAPI 3.0 structure
        openapi_spec = {
            "openapi": "3.0.3",
            "info": {
                "title": kwargs.get("title", "DotMac API"),
                "description": kwargs.get("description", "ISP Operations API"),
                "version": kwargs.get("version", "1.0.0"),
                "contact": {
                    "name": kwargs.get("contact_name", "API Support"),
                    "email": kwargs.get("contact_email", "api-support@dotmac.com"),
                    "url": kwargs.get("contact_url", "https://docs.dotmac.com"),
                },
                "license": {
                    "name": "MIT",
                    "url": "https://opensource.org/licenses/MIT",
                },
            },
            "servers": kwargs.get(
                "servers",
                [
                    {
                        "url": "https://api.dotmac.com",
                        "description": "Production server",
                    },
                    {
                        "url": "https://staging-api.dotmac.com",
                        "description": "Staging server",
                    },
                ],
            ),
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key",
                    },
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                    },
                },
            },
            "security": [{"ApiKeyAuth": []}, {"BearerAuth": []}],
        }

        # Add paths from routes (would be populated from actual gateway routes)
        if kwargs.get("include_examples", True):
            openapi_spec["paths"] = self._generate_example_paths()

        # Add schemas if requested
        if kwargs.get("include_schemas", True):
            openapi_spec["components"]["schemas"] = self._generate_example_schemas()

        spec_data = {
            "spec_id": spec_id,
            "gateway_id": gateway_id,
            "openapi_spec": openapi_spec,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        }

        self._openapi_specs[spec_id] = spec_data
        return spec_data

    async def create_developer_portal(self, **kwargs) -> Dict[str, Any]:
        """Create developer portal."""
        portal_id = kwargs.get("portal_id") or str(uuid4())

        portal = {
            "portal_id": portal_id,
            "name": kwargs["name"],
            "gateway_id": kwargs["gateway_id"],
            "openapi_spec_id": kwargs["openapi_spec_id"],
            "theme": kwargs.get("theme", "default"),
            "custom_css": kwargs.get("custom_css"),
            "custom_logo": kwargs.get("custom_logo"),
            "footer_text": kwargs.get("footer_text", "Powered by DotMac API Gateway"),
            "enable_try_it_out": kwargs.get("enable_try_it_out", True),
            "enable_code_samples": kwargs.get("enable_code_samples", True),
            "supported_languages": kwargs.get(
                "supported_languages",
                ["curl", "javascript", "python", "php", "java", "go"],
            ),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        }

        self._developer_portals[portal_id] = portal
        return portal

    async def create_api_explorer(self, **kwargs) -> Dict[str, Any]:
        """Create interactive API explorer."""
        explorer_id = kwargs.get("explorer_id") or str(uuid4())

        explorer = {
            "explorer_id": explorer_id,
            "portal_id": kwargs["portal_id"],
            "enable_try_it_out": kwargs.get("enable_try_it_out", True),
            "default_auth_header": kwargs.get("default_auth_header", "X-API-Key"),
            "enable_request_persistence": kwargs.get(
                "enable_request_persistence", True
            ),
            "enable_response_caching": kwargs.get("enable_response_caching", False),
            "max_request_timeout": kwargs.get("max_request_timeout", 30),
            "allowed_domains": kwargs.get("allowed_domains", []),
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        }

        self._api_explorers[explorer_id] = explorer
        return explorer

    def _generate_example_paths(self) -> Dict[str, Any]:
        """Generate example API paths."""
        return {
            "/v1/customers": {
                "get": {
                    "summary": "List customers",
                    "description": "Retrieve a list of customers",
                    "tags": ["Customers"],
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "description": "Maximum number of results",
                            "schema": {"type": "integer", "default": 20},
                        },
                        {
                            "name": "offset",
                            "in": "query",
                            "description": "Number of results to skip",
                            "schema": {"type": "integer", "default": 0},
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "customers": {
                                                "type": "array",
                                                "items": {
                                                    "$ref": "#/components/schemas/Customer"
                                                },
                                            },
                                            "total": {"type": "integer"},
                                            "limit": {"type": "integer"},
                                            "offset": {"type": "integer"},
                                        },
                                    }
                                }
                            },
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            },
                        },
                    },
                    "security": [{"ApiKeyAuth": []}],
                },
                "post": {
                    "summary": "Create customer",
                    "description": "Create a new customer",
                    "tags": ["Customers"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/CustomerInput"}
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Customer created",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Customer"}
                                }
                            },
                        },
                        "400": {
                            "description": "Bad request",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            },
                        },
                    },
                    "security": [{"ApiKeyAuth": []}],
                },
            },
            "/v1/customers/{customerId}": {
                "get": {
                    "summary": "Get customer",
                    "description": "Retrieve a specific customer by ID",
                    "tags": ["Customers"],
                    "parameters": [
                        {
                            "name": "customerId",
                            "in": "path",
                            "required": True,
                            "description": "Customer ID",
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Customer"}
                                }
                            },
                        },
                        "404": {
                            "description": "Customer not found",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            },
                        },
                    },
                    "security": [{"ApiKeyAuth": []}],
                }
            },
        }

    def _generate_example_schemas(self) -> Dict[str, Any]:
        """Generate example schemas."""
        return {
            "Customer": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "example": "cust_123"},
                    "display_name": {"type": "string", "example": "Acme Corp"},
                    "customer_type": {
                        "type": "string",
                        "enum": ["residential", "business"],
                        "example": "business",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["active", "suspended", "terminated"],
                        "example": "active",
                    },
                    "created_at": {
                        "type": "string",
                        "format": "date-time",
                        "example": "2024-01-01T00:00:00Z",
                    },
                    "updated_at": {
                        "type": "string",
                        "format": "date-time",
                        "example": "2024-01-01T00:00:00Z",
                    },
                },
                "required": ["customer_id", "display_name", "customer_type"],
            },
            "CustomerInput": {
                "type": "object",
                "properties": {
                    "display_name": {"type": "string", "example": "Acme Corp"},
                    "customer_type": {
                        "type": "string",
                        "enum": ["residential", "business"],
                        "example": "business",
                    },
                    "contact_email": {
                        "type": "string",
                        "format": "email",
                        "example": "contact@acme.com",
                    },
                    "contact_phone": {"type": "string", "example": "+1-555-0123"},
                },
                "required": ["display_name", "customer_type"],
            },
            "Error": {
                "type": "object",
                "properties": {
                    "error": {"type": "string", "example": "VALIDATION_ERROR"},
                    "message": {
                        "type": "string",
                        "example": "Request validation failed",
                    },
                    "details": {
                        "type": "object",
                        "example": {"field": "email", "issue": "Invalid format"},
                    },
                },
                "required": ["error", "message"],
            },
        }


class APIDocumentationSDK:
    """SDK for API documentation and developer portal."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = APIDocumentationService()

    async def generate_openapi_spec(
        self,
        gateway_id: str,
        title: str = "DotMac API",
        version: str = "1.0.0",
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate OpenAPI specification."""
        return await self._service.generate_openapi_spec(
            gateway_id=gateway_id, title=title, version=version, **kwargs
        )

    async def create_developer_portal(
        self, name: str, gateway_id: str, openapi_spec_id: str, **kwargs
    ) -> Dict[str, Any]:
        """Create developer portal."""
        return await self._service.create_developer_portal(
            name=name, gateway_id=gateway_id, openapi_spec_id=openapi_spec_id, **kwargs
        )

    async def create_api_explorer(self, portal_id: str, **kwargs) -> Dict[str, Any]:
        """Create interactive API explorer."""
        return await self._service.create_api_explorer(portal_id=portal_id, **kwargs)
