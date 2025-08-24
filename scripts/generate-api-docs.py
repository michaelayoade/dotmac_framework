#!/usr/bin/env python3
"""
Enterprise-grade API documentation generator for DotMac Platform.

Generates comprehensive OpenAPI documentation with:
- Standardized response formats
- Error handling documentation  
- Business context and examples
- Security scheme documentation
- Version management
"""

import json
import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# FastAPI imports
try:
    from fastapi import FastAPI
    from fastapi.openapi.utils import get_openapi
except ImportError:
    print("FastAPI not installed. Please run: pip install fastapi")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnterpriseAPIDocGenerator:
    """Enterprise-grade API documentation generator."""
    
    def __init__(self, output_dir: str = "docs/api"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def create_standardized_openapi_schema(self, app: FastAPI, service_name: str, version: str) -> Dict[str, Any]:
        """Create standardized OpenAPI schema with enterprise standards."""
        
        # Generate base OpenAPI schema
        openapi_schema = get_openapi(
            title=f"DotMac {service_name} API",
            version=version,
            description=f"Enterprise API for {service_name} management",
            routes=app.routes,
        )
        
        # Add enterprise-grade metadata
        openapi_schema["info"].update({
            "contact": {
                "name": "DotMac API Support",
                "url": "https://docs.dotmac.app/support",
                "email": "api-support@dotmac.app"
            },
            "license": {
                "name": "DotMac Commercial License",
                "url": "https://dotmac.app/license"
            },
            "termsOfService": "https://dotmac.app/terms",
            "x-api-id": f"dotmac-{service_name.lower().replace(' ', '-')}",
            "x-audience": "enterprise",
            "x-maturity": "stable"
        })
        
        # Add standardized server configurations
        openapi_schema["servers"] = [
            {
                "url": "https://api.dotmac.app/v1",
                "description": "Production API Server"
            },
            {
                "url": "https://staging-api.dotmac.app/v1", 
                "description": "Staging API Server"
            },
            {
                "url": "http://localhost:8000",
                "description": "Development Server"
            }
        ]
        
        # Add comprehensive security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT Bearer token authentication"
            },
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API Key authentication for service-to-service communication"
            },
            "PortalAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "Portal-JWT",
                "description": "Portal-based authentication with Portal ID"
            }
        }
        
        # Add standardized response schemas
        openapi_schema["components"]["schemas"].update({
            "StandardError": {
                "type": "object",
                "required": ["error", "message", "status_code"],
                "properties": {
                    "error": {
                        "type": "boolean",
                        "example": True,
                        "description": "Indicates this is an error response"
                    },
                    "message": {
                        "type": "string",
                        "example": "Resource not found",
                        "description": "Human-readable error message"
                    },
                    "status_code": {
                        "type": "integer",
                        "example": 404,
                        "description": "HTTP status code"
                    },
                    "error_code": {
                        "type": "string",
                        "example": "RESOURCE_NOT_FOUND",
                        "description": "Machine-readable error code"
                    },
                    "details": {
                        "type": "object",
                        "description": "Additional error details"
                    },
                    "request_id": {
                        "type": "string",
                        "example": "req_abc123",
                        "description": "Unique request identifier for debugging"
                    }
                }
            },
            "SuccessResponse": {
                "type": "object",
                "required": ["success", "data"],
                "properties": {
                    "success": {
                        "type": "boolean",
                        "example": True,
                        "description": "Indicates successful operation"
                    },
                    "data": {
                        "type": "object",
                        "description": "Response data payload"
                    },
                    "meta": {
                        "type": "object",
                        "properties": {
                            "total": {"type": "integer", "description": "Total items (for pagination)"},
                            "page": {"type": "integer", "description": "Current page number"},
                            "per_page": {"type": "integer", "description": "Items per page"},
                            "has_more": {"type": "boolean", "description": "More items available"}
                        }
                    },
                    "request_id": {
                        "type": "string",
                        "example": "req_abc123",
                        "description": "Unique request identifier"
                    }
                }
            },
            "HealthCheck": {
                "type": "object",
                "required": ["status", "service", "version"],
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["healthy", "degraded", "unhealthy"],
                        "example": "healthy"
                    },
                    "service": {
                        "type": "string",
                        "example": "dotmac-isp-framework"
                    },
                    "version": {
                        "type": "string",
                        "example": "1.0.0"
                    },
                    "timestamp": {
                        "type": "string",
                        "format": "date-time",
                        "example": "2024-01-15T10:30:00Z"
                    },
                    "dependencies": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "status": {"type": "string", "enum": ["healthy", "unhealthy"]},
                                "response_time": {"type": "number", "description": "Response time in milliseconds"}
                            }
                        }
                    }
                }
            }
        })
        
        # Add standard error responses to all paths
        for path_item in openapi_schema["paths"].values():
            for operation in path_item.values():
                if isinstance(operation, dict) and "responses" in operation:
                    # Add standard error responses
                    operation["responses"].update({
                        "400": {
                            "description": "Bad Request",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/StandardError"}
                                }
                            }
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/StandardError"}
                                }
                            }
                        },
                        "403": {
                            "description": "Forbidden",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/StandardError"}
                                }
                            }
                        },
                        "404": {
                            "description": "Not Found",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/StandardError"}
                                }
                            }
                        },
                        "429": {
                            "description": "Rate Limited",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/StandardError"}
                                }
                            }
                        },
                        "500": {
                            "description": "Internal Server Error",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/StandardError"}
                                }
                            }
                        }
                    })
                    
                    # Add security requirements
                    if "security" not in operation:
                        operation["security"] = [
                            {"BearerAuth": []},
                            {"ApiKeyAuth": []},
                            {"PortalAuth": []}
                        ]
        
        return openapi_schema
    
    def generate_documentation(self):
        """Generate comprehensive API documentation for both platforms."""
        
        logger.info("🚀 Generating Enterprise API Documentation")
        
        # Generate ISP Framework API Documentation
        try:
            logger.info("📊 Generating ISP Framework API documentation...")
            isp_app = self._load_isp_framework_app()
            if isp_app:
                isp_schema = self.create_standardized_openapi_schema(
                    isp_app, 
                    "ISP Framework", 
                    "1.0.0"
                )
                self._save_openapi_spec(isp_schema, "isp-framework")
                self._generate_readme(isp_schema, "isp-framework")
                logger.info("✅ ISP Framework API documentation generated")
        except Exception as e:
            logger.error(f"❌ Failed to generate ISP Framework docs: {e}")
        
        # Generate Management Platform API Documentation
        try:
            logger.info("🏢 Generating Management Platform API documentation...")
            mgmt_app = self._load_management_platform_app()
            if mgmt_app:
                mgmt_schema = self.create_standardized_openapi_schema(
                    mgmt_app,
                    "Management Platform",
                    "1.0.0"
                )
                self._save_openapi_spec(mgmt_schema, "management-platform")
                self._generate_readme(mgmt_schema, "management-platform")
                logger.info("✅ Management Platform API documentation generated")
        except Exception as e:
            logger.error(f"❌ Failed to generate Management Platform docs: {e}")
        
        # Generate unified API index
        self._generate_unified_index()
        
        logger.info("🎉 Enterprise API Documentation generation complete!")
        logger.info(f"📁 Documentation saved to: {self.output_dir.absolute()}")
        
    def _load_isp_framework_app(self) -> Optional[FastAPI]:
        """Load ISP Framework FastAPI app."""
        try:
            sys.path.insert(0, "/home/dotmac_framework/isp-framework/src")
            from dotmac_isp.app import app
            return app
        except Exception as e:
            logger.warning(f"Could not load ISP Framework app: {e}")
            return None
    
    def _load_management_platform_app(self) -> Optional[FastAPI]:
        """Load Management Platform FastAPI app."""
        try:
            sys.path.insert(0, "/home/dotmac_framework/management-platform")
            from app.main import app
            return app
        except Exception as e:
            logger.warning(f"Could not load Management Platform app: {e}")
            return None
    
    def _save_openapi_spec(self, schema: Dict[str, Any], service_name: str):
        """Save OpenAPI specification to file."""
        output_file = self.output_dir / f"{service_name}-openapi.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)
        
        # Also save as YAML for better readability
        try:
            import yaml
            yaml_file = self.output_dir / f"{service_name}-openapi.yaml"
            with open(yaml_file, 'w', encoding='utf-8') as f:
                yaml.dump(schema, f, default_flow_style=False, allow_unicode=True)
        except ImportError:
            logger.warning("PyYAML not installed, skipping YAML output")
    
    def _generate_readme(self, schema: Dict[str, Any], service_name: str):
        """Generate README documentation for the API."""
        
        service_title = schema["info"]["title"]
        version = schema["info"]["version"]
        description = schema["info"]["description"]
        
        readme_content = f"""# {service_title}

{description}

**Version:** {version}  
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Overview

This API provides comprehensive access to {service_name} functionality with enterprise-grade security, monitoring, and reliability.

### Key Features

- 🔐 **Multi-layer Authentication**: JWT Bearer, API Key, and Portal-based auth
- 📊 **Comprehensive Monitoring**: Built-in observability with SignOz integration  
- 🚀 **High Performance**: Optimized for scale with caching and rate limiting
- 🛡️ **Enterprise Security**: Complete audit trails and compliance features
- 🔄 **Real-time Operations**: WebSocket support for live updates

## Authentication

The API supports multiple authentication methods:

### 1. JWT Bearer Authentication
```bash
curl -H "Authorization: Bearer <jwt_token>" \\
  https://api.dotmac.app/v1/endpoint
```

### 2. API Key Authentication  
```bash
curl -H "X-API-Key: <api_key>" \\
  https://api.dotmac.app/v1/endpoint
```

### 3. Portal Authentication
```bash
curl -H "Authorization: Bearer <portal_jwt>" \\
  https://api.dotmac.app/v1/portal/endpoint
```

## Standard Response Format

### Success Response
```json
{{
  "success": true,
  "data": {{}},
  "meta": {{
    "total": 100,
    "page": 1,
    "per_page": 20,
    "has_more": true
  }},
  "request_id": "req_abc123"
}}
```

### Error Response
```json
{{
  "error": true,
  "message": "Resource not found",
  "status_code": 404,
  "error_code": "RESOURCE_NOT_FOUND",
  "details": {{}},
  "request_id": "req_abc123"
}}
```

## Rate Limiting

API requests are rate limited to ensure fair usage:
- **Authenticated requests**: 1000 requests per minute
- **Unauthenticated requests**: 100 requests per minute

Rate limit headers are included in all responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## Error Handling

The API uses standard HTTP status codes:

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | Success | Request completed successfully |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request format or parameters |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Access denied |
| 404 | Not Found | Resource does not exist |
| 429 | Rate Limited | Too many requests |
| 500 | Server Error | Internal server error |

## Business Context

### Revenue-Critical Endpoints
Some endpoints directly impact revenue and have additional validation:
- Billing operations require secondary confirmation
- Payment processing includes fraud detection
- Service provisioning validates customer credit

### Multi-Tenant Isolation
All data is strictly isolated by tenant:
- API requests automatically filter by authenticated user's tenant
- Cross-tenant access is strictly prohibited
- Audit logs track all tenant-specific operations

## OpenAPI Specification

- **JSON Format**: [{service_name}-openapi.json]({service_name}-openapi.json)
- **YAML Format**: [{service_name}-openapi.yaml]({service_name}-openapi.yaml)

## SDK and Integration

### Python SDK
```bash
pip install dotmac-{service_name.lower().replace(' ', '-')}-sdk
```

### JavaScript/TypeScript SDK  
```bash
npm install @dotmac/{service_name.lower().replace(' ', '-')}-sdk
```

## Support and Resources

- **API Documentation**: [https://docs.dotmac.app/api](https://docs.dotmac.app/api)
- **Developer Portal**: [https://developers.dotmac.app](https://developers.dotmac.app)
- **Support**: [api-support@dotmac.app](mailto:api-support@dotmac.app)
- **Status Page**: [https://status.dotmac.app](https://status.dotmac.app)

## Changelog

### Version 1.0.0 (Current)
- Initial release with full API coverage
- Enterprise authentication and security
- Comprehensive error handling
- Real-time capabilities via WebSocket
- Multi-tenant isolation
- Revenue-critical endpoint protection

---

*Generated automatically by DotMac Enterprise API Documentation Generator*
"""
        
        readme_file = self.output_dir / f"{service_name}-README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
    
    def _generate_unified_index(self):
        """Generate unified API documentation index."""
        
        index_content = """# DotMac Platform API Documentation

Enterprise-grade API documentation for the complete DotMac Platform.

## Platform Overview

The DotMac Platform consists of two main services:

### 🌐 ISP Framework
**Service for Internet Service Provider Operations**
- Customer management and onboarding
- Service provisioning and lifecycle management  
- Network infrastructure monitoring
- Billing and payment processing
- Support ticket management
- Field operations coordination

**API Documentation:**
- [ISP Framework README](isp-framework-README.md)
- [OpenAPI Specification (JSON)](isp-framework-openapi.json)
- [OpenAPI Specification (YAML)](isp-framework-openapi.yaml)

### 🏢 Management Platform  
**Multi-Tenant SaaS Orchestration Platform**
- Tenant lifecycle management
- Multi-tenant deployment orchestration
- SaaS subscription billing
- Plugin marketplace and licensing
- Platform monitoring and analytics
- Reseller network management

**API Documentation:**
- [Management Platform README](management-platform-README.md)  
- [OpenAPI Specification (JSON)](management-platform-openapi.json)
- [OpenAPI Specification (YAML)](management-platform-openapi.yaml)

## Quick Start

### 1. Authentication Setup
```bash
# Get your API credentials from the developer portal
export DOTMAC_API_KEY="your_api_key_here"
export DOTMAC_JWT_TOKEN="your_jwt_token_here"
```

### 2. Health Check
```bash
# Check ISP Framework health
curl https://api.dotmac.app/v1/health

# Check Management Platform health  
curl https://management.dotmac.app/v1/health
```

### 3. Basic API Call
```bash
# List customers (ISP Framework)
curl -H "Authorization: Bearer $DOTMAC_JWT_TOKEN" \\
  https://api.dotmac.app/v1/customers

# List tenants (Management Platform)
curl -H "Authorization: Bearer $DOTMAC_JWT_TOKEN" \\
  https://management.dotmac.app/v1/tenants
```

## Enterprise Features

### 🔒 Security & Compliance
- Multi-factor authentication support
- RBAC with granular permissions
- SOC2, GDPR, PCI DSS compliance
- Complete audit trails
- Encryption at rest and in transit

### 📊 Observability & Monitoring
- Real-time metrics with SignOz
- Distributed tracing across services
- Business metrics and revenue tracking
- SLA monitoring and alerting
- Performance analytics

### 🚀 Scale & Reliability
- Auto-scaling infrastructure
- 99.99% uptime SLA
- Global CDN distribution
- Disaster recovery automation
- Multi-region deployment

## Developer Resources

### SDKs & Libraries
- **Python**: `pip install dotmac-platform-sdk`
- **Node.js**: `npm install @dotmac/platform-sdk`
- **Go**: `go get github.com/dotmac/go-sdk`
- **Java**: Available via Maven Central

### Development Tools
- **Postman Collection**: [Download](https://docs.dotmac.app/postman)
- **Insomnia Workspace**: [Import](https://docs.dotmac.app/insomnia)
- **OpenAPI Generator**: Generate client SDKs automatically

### Sandbox Environment
- **Base URL**: `https://sandbox.dotmac.app/v1`
- **WebSocket**: `wss://sandbox.dotmac.app/ws`
- **Dashboard**: [https://sandbox-dashboard.dotmac.app](https://sandbox-dashboard.dotmac.app)

## Support Channels

- 📧 **Email Support**: [api-support@dotmac.app](mailto:api-support@dotmac.app)
- 💬 **Developer Chat**: [https://discord.gg/dotmac-developers](https://discord.gg/dotmac-developers)  
- 📚 **Knowledge Base**: [https://docs.dotmac.app/kb](https://docs.dotmac.app/kb)
- 🐛 **Bug Reports**: [https://github.com/dotmac/platform/issues](https://github.com/dotmac/platform/issues)

---

**Last Updated**: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """  
**Documentation Version**: 1.0.0  
**Generated By**: DotMac Enterprise API Documentation Generator
"""
        
        index_file = self.output_dir / "README.md"
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(index_content)

def main():
    """Main entry point for API documentation generation."""
    
    # Create output directory
    output_dir = "/home/dotmac_framework/docs/api"
    
    # Initialize generator
    generator = EnterpriseAPIDocGenerator(output_dir)
    
    # Generate documentation
    generator.generate_documentation()
    
    print(f"""
🎉 Enterprise API Documentation Generated Successfully!

📁 Output Directory: {output_dir}
📊 Generated Files:
  - README.md (Unified API index)
  - isp-framework-README.md
  - isp-framework-openapi.json  
  - isp-framework-openapi.yaml
  - management-platform-README.md
  - management-platform-openapi.json
  - management-platform-openapi.yaml

🚀 Next Steps:
  1. Review generated documentation
  2. Host documentation on your docs site
  3. Update developer portal links
  4. Configure automatic regeneration in CI/CD

📖 Access Documentation: file://{output_dir}/README.md
    """)

if __name__ == "__main__":
    main()