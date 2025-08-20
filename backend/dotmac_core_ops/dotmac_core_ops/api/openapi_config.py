"""
Shared OpenAPI documentation configuration and utilities.
Provides standardized documentation helpers for all DotMac services.
"""

from typing import Dict, List, Any
from fastapi import FastAPI
from pydantic import BaseModel, Field


def create_openapi_tags() -> List[Dict[str, str]]:
    """Create standardized OpenAPI tags for services."""
    return [
        {
            "name": "Health",
            "description": "Service health and status endpoints",
        },
        {
            "name": "Authentication",
            "description": "Authentication and authorization operations",
        },
        {
            "name": "Management",
            "description": "Resource management operations",
        },
    ]


def configure_openapi(
    app: FastAPI,
    title: str,
    description: str,
    version: str = "1.0.0",
    tags: List[Dict[str, str]] = None,
    include_admin_endpoints: bool = False
) -> None:
    """
    Configure OpenAPI documentation for a FastAPI application.
    
    Args:
        app: FastAPI application instance
        title: API title
        description: API description
        version: API version
        tags: Custom tags for the API
        include_admin_endpoints: Whether to include admin endpoints
    """
    app.title = title
    app.description = description
    app.version = version
    
    if tags:
        app.openapi_tags = tags
    
    # Add servers configuration
    if app.openapi_schema:
        app.openapi_schema = None  # Reset to regenerate
    
    # Configure license
    app.license_info = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }
    
    # Configure contact
    app.contact = {
        "name": "DotMac Platform Team",
        "email": "api-support@dotmac.com",
        "url": "https://docs.dotmac.com",
    }


def get_standard_responses() -> Dict[int, Dict[str, Any]]:
    """Get standardized API response definitions."""
    return {
        200: {
            "description": "Successful operation",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"},
                            "data": {"type": "object"},
                        }
                    }
                }
            }
        },
        400: {
            "description": "Bad request - Invalid input data",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                }
            }
        },
        401: {
            "description": "Unauthorized - Authentication required",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                }
            }
        },
        403: {
            "description": "Forbidden - Insufficient permissions",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                }
            }
        },
        404: {
            "description": "Not found - Resource does not exist",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                }
            }
        },
        409: {
            "description": "Conflict - Resource already exists",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                }
            }
        },
        422: {
            "description": "Validation error - Invalid field values",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ValidationErrorResponse"}
                }
            }
        },
        429: {
            "description": "Too many requests - Rate limit exceeded",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                }
            }
        },
    }


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str = Field(
        ...,
        description="Error code for programmatic handling",
        example="VALIDATION_ERROR"
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
        example="The provided input data is invalid"
    )
    details: Dict[str, Any] = Field(
        default=None,
        description="Additional error details",
        example={"field": "email", "issue": "Invalid email format"}
    )
    request_id: str = Field(
        default=None,
        description="Unique request identifier for debugging",
        example="req_1234567890"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "error": "VALIDATION_ERROR",
                "message": "The provided input data is invalid",
                "details": {
                    "field": "email",
                    "issue": "Invalid email format"
                },
                "request_id": "req_1234567890"
            }
        }


class ValidationErrorResponse(BaseModel):
    """Validation error response model."""
    
    error: str = Field(
        default="VALIDATION_ERROR",
        description="Error code",
        example="VALIDATION_ERROR"
    )
    message: str = Field(
        ...,
        description="Error message",
        example="Request validation failed"
    )
    validation_errors: List[Dict[str, Any]] = Field(
        ...,
        description="List of validation errors",
        example=[
            {
                "loc": ["body", "email"],
                "msg": "invalid email format",
                "type": "value_error.email"
            }
        ]
    )
    
    class Config:
        schema_extra = {
            "example": {
                "error": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "validation_errors": [
                    {
                        "loc": ["body", "email"],
                        "msg": "invalid email format",
                        "type": "value_error.email"
                    }
                ]
            }
        }


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(
        ...,
        description="Service health status",
        example="healthy"
    )
    service: str = Field(
        ...,
        description="Service name",
        example="dotmac_identity"
    )
    version: str = Field(
        ...,
        description="Service version",
        example="1.0.0"
    )
    timestamp: str = Field(
        ...,
        description="Current timestamp in ISO format",
        example="2024-01-15T10:30:00Z"
    )
    dependencies: Dict[str, str] = Field(
        default=None,
        description="Status of service dependencies",
        example={
            "database": "healthy",
            "redis": "healthy",
            "message_bus": "healthy"
        }
    )
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "service": "dotmac_identity",
                "version": "1.0.0",
                "timestamp": "2024-01-15T10:30:00Z",
                "dependencies": {
                    "database": "healthy",
                    "redis": "healthy",
                    "message_bus": "healthy"
                }
            }
        }


class PaginationParams(BaseModel):
    """Standard pagination parameters."""
    
    page: int = Field(
        default=1,
        ge=1,
        description="Page number (1-based)",
        example=1
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page",
        example=20
    )
    sort_by: str = Field(
        default="created_at",
        description="Field to sort by",
        example="created_at"
    )
    sort_order: str = Field(
        default="desc",
        regex="^(asc|desc)$",
        description="Sort order (asc or desc)",
        example="desc"
    )


class PaginatedResponse(BaseModel):
    """Standard paginated response model."""
    
    items: List[Any] = Field(
        ...,
        description="List of items for current page"
    )
    total: int = Field(
        ...,
        description="Total number of items",
        example=100
    )
    page: int = Field(
        ...,
        description="Current page number",
        example=1
    )
    limit: int = Field(
        ...,
        description="Items per page",
        example=20
    )
    pages: int = Field(
        ...,
        description="Total number of pages",
        example=5
    )
    has_next: bool = Field(
        ...,
        description="Whether there is a next page",
        example=True
    )
    has_prev: bool = Field(
        ...,
        description="Whether there is a previous page",
        example=False
    )


def add_openapi_examples(app: FastAPI) -> None:
    """Add OpenAPI examples to the application schema."""
    
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
            
        openapi_schema = app.openapi()
        
        # Add security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT authentication token"
            },
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API key authentication"
            }
        }
        
        # Add global security requirement
        openapi_schema["security"] = [
            {"BearerAuth": []},
            {"ApiKeyAuth": []}
        ]
        
        # Add external documentation
        openapi_schema["externalDocs"] = {
            "description": "DotMac Platform Documentation",
            "url": "https://docs.dotmac.com"
        }
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi