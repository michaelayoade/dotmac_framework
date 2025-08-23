"""
API documentation and developer tools service.
Provides comprehensive API documentation, SDK generation, and developer resources.
"""

import json
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..core.exceptions import ValidationError, DatabaseError
from ..core.logging import get_logger
from ..models.user import User
from ..schemas.api_docs import (
    APIEndpoint,
    SDKLanguage,
    CodeSample,
    APIDocumentation,
    DeveloperGuide,
    ChangelogEntry
)

logger = get_logger(__name__)


class APIDocumentationService:
    """Service for generating and managing API documentation."""
    
    def __init__(self, db: AsyncSession, app: FastAPI):
        self.db = db
        self.app = app
        self.base_url = "https://api.dotmac.io"
        
    async def generate_openapi_spec(
        self,
        include_examples: bool = True,
        include_schemas: bool = True,
        version: str = "v1"
    ) -> Dict[str, Any]:
        """
        Generate comprehensive OpenAPI specification.
        
        Args:
            include_examples: Include request/response examples
            include_schemas: Include detailed schemas
            version: API version
            
        Returns:
            Dict containing OpenAPI specification
        """
        try:
            logger.info("Generating OpenAPI specification")
            
            # Get base OpenAPI spec from FastAPI
            openapi_spec = get_openapi(
                title="DotMac Management Platform API",
                version=version,
                description=self._get_api_description(),
                routes=self.app.routes,
                servers=[
                    {"url": f"{self.base_url}/{version}", "description": "Production server"},
                    {"url": f"https://staging-api.dotmac.io/{version}", "description": "Staging server"},
                    {"url": f"http://localhost:8000/{version}", "description": "Development server"}
                ]
            )
            
            # Enhance with additional metadata
            openapi_spec["info"].update({
                "contact": {
                    "name": "DotMac API Support",
                    "url": "https://docs.dotmac.io/support",
                    "email": "api-support@dotmac.io"
                },
                "license": {
                    "name": "MIT",
                    "url": "https://opensource.org/licenses/MIT"
                },
                "termsOfService": "https://dotmac.io/terms"
            })
            
            # Add security schemes
            openapi_spec["components"]["securitySchemes"] = {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                },
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key"
                }
            }
            
            # Add global security
            openapi_spec["security"] = [
                {"BearerAuth": []},
                {"ApiKeyAuth": []}
            ]
            
            # Add tags with descriptions
            openapi_spec["tags"] = self._get_api_tags()
            
            # Enhance paths with examples
            if include_examples:
                await self._add_endpoint_examples(openapi_spec)
            
            # Add custom extensions
            openapi_spec["x-logo"] = {
                "url": "https://dotmac.io/logo.png",
                "altText": "DotMac Logo"
            }
            
            openapi_spec["x-tagGroups"] = [
                {
                    "name": "Core Resources",
                    "tags": ["tenants", "users", "authentication"]
                },
                {
                    "name": "Platform Services",
                    "tags": ["billing", "infrastructure", "notifications"]
                },
                {
                    "name": "Management",
                    "tags": ["admin", "analytics", "webhooks"]
                }
            ]
            
            return openapi_spec
            
        except Exception as e:
            logger.error(f"Failed to generate OpenAPI spec: {e}")
            raise DatabaseError(f"Failed to generate OpenAPI spec: {e}")
    
    async def generate_postman_collection(
        self,
        version: str = "v1",
        include_auth: bool = True
    ) -> Dict[str, Any]:
        """
        Generate Postman collection for API testing.
        
        Args:
            version: API version
            include_auth: Include authentication examples
            
        Returns:
            Dict containing Postman collection
        """
        try:
            logger.info("Generating Postman collection")
            
            openapi_spec = await self.generate_openapi_spec(version=version)
            
            collection = {
                "info": {
                    "name": "DotMac Management Platform API",
                    "description": "Complete API collection for DotMac Management Platform",
                    "version": version,
                    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
                },
                "auth": {
                    "type": "bearer",
                    "bearer": [
                        {
                            "key": "token",
                            "value": "{{access_token}}",
                            "type": "string"
                        }
                    ]
                } if include_auth else None,
                "variable": [
                    {
                        "key": "base_url",
                        "value": f"{self.base_url}/{version}",
                        "type": "string"
                    },
                    {
                        "key": "access_token",
                        "value": "your_jwt_token_here",
                        "type": "string"
                    }
                ],
                "item": []
            }
            
            # Convert OpenAPI paths to Postman requests
            for path, methods in openapi_spec.get("paths", {}).items():
                for method, operation in methods.items():
                    if method in ["get", "post", "put", "delete", "patch"]:
                        request_item = self._create_postman_request(
                            path, method, operation, openapi_spec
                        )
                        collection["item"].append(request_item)
            
            return collection
            
        except Exception as e:
            logger.error(f"Failed to generate Postman collection: {e}")
            raise DatabaseError(f"Failed to generate Postman collection: {e}")
    
    async def generate_sdk_documentation(
        self,
        language: SDKLanguage,
        version: str = "v1"
    ) -> Dict[str, Any]:
        """
        Generate SDK documentation for specified language.
        
        Args:
            language: Target programming language
            version: API version
            
        Returns:
            Dict containing SDK documentation
        """
        try:
            logger.info(f"Generating SDK documentation for {language}")
            
            openapi_spec = await self.generate_openapi_spec(version=version)
            
            sdk_docs = {
                "language": language.value,
                "version": version,
                "installation": self._get_installation_instructions(language),
                "quickstart": self._get_quickstart_guide(language),
                "authentication": self._get_authentication_examples(language),
                "code_samples": await self._generate_code_samples(openapi_spec, language),
                "error_handling": self._get_error_handling_examples(language),
                "best_practices": self._get_best_practices(language),
                "changelog": await self._get_sdk_changelog(language),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return sdk_docs
            
        except Exception as e:
            logger.error(f"Failed to generate SDK documentation: {e}")
            raise DatabaseError(f"Failed to generate SDK documentation: {e}")
    
    async def create_interactive_docs(
        self,
        version: str = "v1",
        theme: str = "default"
    ) -> Dict[str, Any]:
        """
        Create interactive API documentation.
        
        Args:
            version: API version
            theme: Documentation theme
            
        Returns:
            Dict containing interactive documentation configuration
        """
        try:
            logger.info("Creating interactive documentation")
            
            openapi_spec = await self.generate_openapi_spec(version=version)
            
            interactive_docs = {
                "title": "DotMac Management Platform API Documentation",
                "version": version,
                "theme": theme,
                "spec_url": f"/api/{version}/openapi.json",
                "redoc_config": {
                    "theme": {
                        "colors": {
                            "primary": {"main": "#1976d2"},
                            "success": {"main": "#4caf50"},
                            "warning": {"main": "#ff9800"},
                            "error": {"main": "#f44336"}
                        },
                        "typography": {
                            "fontSize": "14px",
                            "fontFamily": "'Roboto', sans-serif"
                        }
                    },
                    "hideDownloadButton": False,
                    "hideHostname": False,
                    "expandResponses": "200,201",
                    "requiredPropsFirst": True,
                    "sortPropsAlphabetically": True,
                    "showExtensions": True
                },
                "swagger_config": {
                    "deepLinking": True,
                    "displayOperationId": False,
                    "defaultModelsExpandDepth": 1,
                    "defaultModelExpandDepth": 1,
                    "defaultModelRendering": "example",
                    "displayRequestDuration": True,
                    "docExpansion": "list",
                    "filter": True,
                    "operationsSorter": "alpha",
                    "showExtensions": True,
                    "tagsSorter": "alpha",
                    "tryItOutEnabled": True
                },
                "custom_css": self._get_custom_css(theme),
                "custom_js": self._get_custom_js(),
                "examples": await self._get_interactive_examples(openapi_spec)
            }
            
            return interactive_docs
            
        except Exception as e:
            logger.error(f"Failed to create interactive docs: {e}")
            raise DatabaseError(f"Failed to create interactive docs: {e}")
    
    async def generate_developer_guide(
        self,
        sections: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive developer guide.
        
        Args:
            sections: Optional list of sections to include
            
        Returns:
            Dict containing developer guide
        """
        try:
            logger.info("Generating developer guide")
            
            default_sections = [
                "getting_started", "authentication", "rate_limiting",
                "pagination", "webhooks", "error_handling", "best_practices",
                "examples", "troubleshooting", "changelog"
            ]
            
            if not sections:
                sections = default_sections
            
            guide = {
                "title": "DotMac Management Platform Developer Guide",
                "version": "1.0.0",
                "last_updated": datetime.utcnow().isoformat(),
                "sections": {}
            }
            
            for section in sections:
                guide["sections"][section] = await self._generate_guide_section(section)
            
            return guide
            
        except Exception as e:
            logger.error(f"Failed to generate developer guide: {e}")
            raise DatabaseError(f"Failed to generate developer guide: {e}")
    
    async def create_changelog_entry(
        self,
        version: str,
        changes: List[Dict[str, Any]],
        release_date: Optional[datetime] = None,
        created_by: str
    ) -> Dict[str, Any]:
        """
        Create a new changelog entry.
        
        Args:
            version: Release version
            changes: List of changes
            release_date: Optional release date
            created_by: User creating the entry
            
        Returns:
            Dict containing changelog entry
        """
        try:
            logger.info(f"Creating changelog entry for version {version}")
            
            if not release_date:
                release_date = datetime.utcnow()
            
            changelog_entry = {
                "id": str(uuid4()),
                "version": version,
                "release_date": release_date.isoformat(),
                "changes": changes,
                "created_by": created_by,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # In a real implementation, this would be saved to database
            # For now, we'll return the structured entry
            
            return changelog_entry
            
        except Exception as e:
            logger.error(f"Failed to create changelog entry: {e}")
            raise DatabaseError(f"Failed to create changelog entry: {e}")
    
    async def get_api_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get API usage metrics for documentation insights.
        
        Args:
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            Dict containing API metrics
        """
        try:
            logger.info("Getting API metrics")
            
            # In a real implementation, this would query API logs
            # For now, return sample metrics
            
            metrics = {
                "period": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                },
                "total_requests": 1000000,
                "unique_developers": 150,
                "most_used_endpoints": [
                    {"endpoint": "/api/v1/tenants", "requests": 50000},
                    {"endpoint": "/api/v1/users", "requests": 35000},
                    {"endpoint": "/api/v1/billing/invoices", "requests": 25000}
                ],
                "error_rates": {
                    "4xx": 2.5,
                    "5xx": 0.3
                },
                "response_times": {
                    "p50": 120,
                    "p95": 500,
                    "p99": 1200
                },
                "sdk_downloads": {
                    "python": 500,
                    "javascript": 350,
                    "go": 200,
                    "php": 150
                },
                "documentation_views": 5000,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get API metrics: {e}")
            raise DatabaseError(f"Failed to get API metrics: {e}")
    
    # Private helper methods
    
    def _get_api_description(self) -> str:
        """Get comprehensive API description."""
        return """
        The DotMac Management Platform API provides comprehensive access to manage tenants, 
        users, billing, infrastructure, and analytics. This RESTful API supports JSON 
        request/response format and uses JWT tokens for authentication.
        
        ## Features
        - Multi-tenant architecture support
        - Comprehensive billing and subscription management
        - Infrastructure provisioning and management
        - Real-time notifications and webhooks
        - Analytics and reporting
        - Role-based access control (RBAC)
        
        ## Rate Limiting
        API requests are rate limited to ensure fair usage:
        - 1000 requests per hour for authenticated users
        - 100 requests per hour for unauthenticated requests
        
        ## Support
        For API support, visit our documentation at https://docs.dotmac.io
        or contact us at api-support@dotmac.io
        """
    
    def _get_api_tags(self) -> List[Dict[str, str]]:
        """Get API tags with descriptions."""
        return [
            {
                "name": "authentication",
                "description": "Authentication and authorization endpoints"
            },
            {
                "name": "tenants",
                "description": "Tenant management operations"
            },
            {
                "name": "users",
                "description": "User management and RBAC operations"
            },
            {
                "name": "billing",
                "description": "Billing, invoicing, and payment operations"
            },
            {
                "name": "infrastructure",
                "description": "Infrastructure provisioning and management"
            },
            {
                "name": "notifications",
                "description": "Notification and messaging operations"
            },
            {
                "name": "analytics",
                "description": "Analytics and reporting endpoints"
            },
            {
                "name": "admin",
                "description": "Administrative operations"
            },
            {
                "name": "webhooks",
                "description": "Webhook management and endpoints"
            },
            {
                "name": "portal",
                "description": "Tenant self-service portal endpoints"
            }
        ]
    
    async def _add_endpoint_examples(self, openapi_spec: Dict[str, Any]) -> None:
        """Add examples to OpenAPI endpoints."""
        # This would add comprehensive examples to each endpoint
        # For brevity, we'll just add a structure
        for path, methods in openapi_spec.get("paths", {}).items():
            for method, operation in methods.items():
                if "requestBody" in operation:
                    # Add request examples
                    pass
                if "responses" in operation:
                    # Add response examples
                    pass
    
    def _create_postman_request(
        self,
        path: str,
        method: str,
        operation: Dict[str, Any],
        openapi_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create Postman request from OpenAPI operation."""
        return {
            "name": operation.get("summary", f"{method.upper()} {path}"),
            "request": {
                "method": method.upper(),
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "url": {
                    "raw": "{{base_url}}" + path,
                    "host": ["{{base_url}}"],
                    "path": path.strip("/").split("/")
                },
                "description": operation.get("description", "")
            },
            "response": []
        }
    
    def _get_installation_instructions(self, language: SDKLanguage) -> Dict[str, str]:
        """Get installation instructions for SDK language."""
        instructions = {
            SDKLanguage.PYTHON: {
                "pip": "pip install dotmac-sdk",
                "conda": "conda install -c dotmac dotmac-sdk",
                "requirements": "dotmac-sdk>=1.0.0"
            },
            SDKLanguage.JAVASCRIPT: {
                "npm": "npm install @dotmac/sdk",
                "yarn": "yarn add @dotmac/sdk",
                "package.json": '"@dotmac/sdk": "^1.0.0"'
            },
            SDKLanguage.GO: {
                "go_get": "go get github.com/dotmac/go-sdk",
                "go_mod": "require github.com/dotmac/go-sdk v1.0.0"
            },
            SDKLanguage.PHP: {
                "composer": "composer require dotmac/sdk",
                "composer.json": '"dotmac/sdk": "^1.0"'
            }
        }
        
        return instructions.get(language, {})
    
    def _get_quickstart_guide(self, language: SDKLanguage) -> Dict[str, str]:
        """Get quickstart guide for SDK language."""
        quickstart = {
            SDKLanguage.PYTHON: {
                "import": "from dotmac_sdk import DotMacClient",
                "init": "client = DotMacClient(api_key='your_api_key')",
                "example": "tenants = client.tenants.list()"
            },
            SDKLanguage.JAVASCRIPT: {
                "import": "import { DotMacClient } from '@dotmac/sdk';",
                "init": "const client = new DotMacClient({ apiKey: 'your_api_key' });",
                "example": "const tenants = await client.tenants.list();"
            },
            SDKLanguage.GO: {
                "import": 'import "github.com/dotmac/go-sdk"',
                "init": 'client := dotmac.NewClient("your_api_key")',
                "example": "tenants, err := client.Tenants.List()"
            },
            SDKLanguage.PHP: {
                "import": "use DotMac\\SDK\\DotMacClient;",
                "init": "$client = new DotMacClient('your_api_key');",
                "example": "$tenants = $client->tenants->list();"
            }
        }
        
        return quickstart.get(language, {})
    
    def _get_authentication_examples(self, language: SDKLanguage) -> Dict[str, str]:
        """Get authentication examples for SDK language."""
        # Return language-specific auth examples
        return {
            "jwt_token": "Example of JWT token authentication",
            "api_key": "Example of API key authentication",
            "oauth": "Example of OAuth flow"
        }
    
    async def _generate_code_samples(
        self,
        openapi_spec: Dict[str, Any],
        language: SDKLanguage
    ) -> List[Dict[str, Any]]:
        """Generate code samples for SDK language."""
        samples = []
        
        # Generate samples for common operations
        common_operations = [
            "create_tenant", "list_users", "create_invoice", 
            "provision_infrastructure", "send_notification"
        ]
        
        for operation in common_operations:
            sample = {
                "operation": operation,
                "description": f"Example of {operation.replace('_', ' ')}",
                "code": self._generate_code_sample(operation, language)
            }
            samples.append(sample)
        
        return samples
    
    def _generate_code_sample(self, operation: str, language: SDKLanguage) -> str:
        """Generate specific code sample."""
        # This would generate actual code samples
        # For now, return placeholder
        return f"// {operation} example for {language.value}\n// Code sample here"
    
    def _get_error_handling_examples(self, language: SDKLanguage) -> Dict[str, str]:
        """Get error handling examples for SDK language."""
        return {
            "try_catch": f"Error handling example for {language.value}",
            "status_codes": "HTTP status code handling",
            "custom_errors": "Custom error types"
        }
    
    def _get_best_practices(self, language: SDKLanguage) -> List[str]:
        """Get best practices for SDK language."""
        return [
            "Always handle errors appropriately",
            "Use environment variables for API keys",
            "Implement proper retry logic",
            "Cache responses when appropriate",
            "Follow rate limiting guidelines"
        ]
    
    async def _get_sdk_changelog(self, language: SDKLanguage) -> List[Dict[str, Any]]:
        """Get SDK changelog for language."""
        return [
            {
                "version": "1.0.0",
                "date": "2024-01-01",
                "changes": ["Initial release", "Core API support"]
            }
        ]
    
    def _get_custom_css(self, theme: str) -> str:
        """Get custom CSS for documentation theme."""
        return """
        .redoc-wrap {
            font-family: 'Roboto', sans-serif;
        }
        
        .api-info-wrap h1 {
            color: #1976d2;
        }
        """
    
    def _get_custom_js(self) -> str:
        """Get custom JavaScript for documentation."""
        return """
        // Custom documentation enhancements
        document.addEventListener('DOMContentLoaded', function() {
            // Add copy buttons to code examples
            // Add interactive features
        });
        """
    
    async def _get_interactive_examples(self, openapi_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Get interactive examples for documentation."""
        return {
            "sample_requests": {},
            "sample_responses": {},
            "curl_examples": {}
        }
    
    async def _generate_guide_section(self, section: str) -> Dict[str, Any]:
        """Generate specific guide section."""
        sections = {
            "getting_started": {
                "title": "Getting Started",
                "content": "How to get started with the DotMac API",
                "subsections": ["registration", "api_keys", "first_request"]
            },
            "authentication": {
                "title": "Authentication",
                "content": "Authentication methods and security",
                "subsections": ["jwt_tokens", "api_keys", "oauth"]
            },
            "rate_limiting": {
                "title": "Rate Limiting",
                "content": "API rate limits and best practices",
                "subsections": ["limits", "headers", "handling"]
            }
            # Add more sections as needed
        }
        
        return sections.get(section, {"title": section, "content": "Section content", "subsections": []})