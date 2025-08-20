#!/usr/bin/env python3
"""
Generate and publish unified Swagger/OpenAPI documentation for all DotMac services.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List
import yaml

# Service definitions
SERVICES = [
    {
        "name": "API Gateway",
        "port": 8000,
        "path": "dotmac_api_gateway",
        "description": "Central API gateway with routing, rate limiting, and authentication proxy"
    },
    {
        "name": "Identity Service",
        "port": 8001,
        "path": "dotmac_identity",
        "description": "User authentication, customer management, and organization handling"
    },
    {
        "name": "Billing Service",
        "port": 8002,
        "path": "dotmac_billing",
        "description": "Invoicing, payments, subscriptions, and financial management"
    },
    {
        "name": "Services Provisioning",
        "port": 8003,
        "path": "dotmac_services",
        "description": "Service catalog, provisioning, and lifecycle management"
    },
    {
        "name": "Network Management",
        "port": 8004,
        "path": "dotmac_networking",
        "description": "Network device management, SNMP monitoring, and SSH automation"
    },
    {
        "name": "Analytics Service",
        "port": 8005,
        "path": "dotmac_analytics",
        "description": "Business intelligence, reporting, and data analytics"
    },
    {
        "name": "Platform Service",
        "port": 8006,
        "path": "dotmac_platform",
        "description": "Core platform utilities, RBAC, and shared services"
    },
    {
        "name": "Event Bus",
        "port": 8007,
        "path": "dotmac_core_events",
        "description": "Event-driven architecture, pub/sub, and message queuing"
    },
    {
        "name": "Core Ops",
        "port": 8008,
        "path": "dotmac_core_ops",
        "description": "Workflow orchestration, sagas, and job scheduling"
    }
]

def generate_openapi_spec(service: Dict[str, Any]) -> Dict[str, Any]:
    """Generate OpenAPI specification for a service."""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": service["name"],
            "description": service["description"],
            "version": "1.0.0",
            "contact": {
                "name": "DotMac Platform Team",
                "email": "support@dotmac.io"
            },
            "license": {
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT"
            }
        },
        "servers": [
            {
                "url": f"http://localhost:{service['port']}",
                "description": "Local development server"
            },
            {
                "url": f"http://api.dotmac.io:{service['port']}",
                "description": "Production server"
            }
        ],
        "paths": {
            "/health": {
                "get": {
                    "summary": "Health Check",
                    "description": "Check service health status",
                    "tags": ["Health"],
                    "responses": {
                        "200": {
                            "description": "Service is healthy",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string", "example": "healthy"},
                                            "service": {"type": "string", "example": service["path"]},
                                            "version": {"type": "string", "example": "1.0.0"},
                                            "timestamp": {"type": "string", "format": "date-time"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/v1": {
                "get": {
                    "summary": "API Information",
                    "description": "Get API version and capabilities",
                    "tags": ["API"],
                    "responses": {
                        "200": {
                            "description": "API information",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "version": {"type": "string", "example": "1.0.0"},
                                            "service": {"type": "string", "example": service["name"]},
                                            "capabilities": {
                                                "type": "array",
                                                "items": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                },
                "apiKey": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key"
                }
            },
            "schemas": {
                "Error": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string", "description": "Error code"},
                        "message": {"type": "string", "description": "Error message"},
                        "details": {"type": "object", "description": "Additional error details"}
                    },
                    "required": ["error", "message"]
                },
                "PaginatedResponse": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {"type": "object"}
                        },
                        "total": {"type": "integer", "description": "Total number of items"},
                        "page": {"type": "integer", "description": "Current page"},
                        "per_page": {"type": "integer", "description": "Items per page"},
                        "has_next": {"type": "boolean", "description": "Has next page"},
                        "has_prev": {"type": "boolean", "description": "Has previous page"}
                    }
                }
            }
        },
        "security": [
            {"bearerAuth": []},
            {"apiKey": []}
        ],
        "tags": [
            {"name": "Health", "description": "Health check endpoints"},
            {"name": "API", "description": "API information endpoints"}
        ]
    }

def generate_unified_spec() -> Dict[str, Any]:
    """Generate unified OpenAPI specification for all services."""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "DotMac Platform API",
            "description": """
# DotMac ISP Platform - Unified API Documentation

## Overview
The DotMac Platform is a comprehensive microservices-based telecommunications management platform for Internet Service Providers.

## Services

| Service | Port | Description |
|---------|------|-------------|
| API Gateway | 8000 | Central routing and authentication |
| Identity | 8001 | User and customer management |
| Billing | 8002 | Financial services |
| Services | 8003 | Service provisioning |
| Networking | 8004 | Network management |
| Analytics | 8005 | Business intelligence |
| Platform | 8006 | Core utilities |
| Events | 8007 | Event bus |
| Core Ops | 8008 | Workflow orchestration |

## Authentication
All APIs support JWT Bearer tokens and API keys.

## Rate Limiting
Default: 1000 requests per minute per client.
            """,
            "version": "1.0.0",
            "contact": {
                "name": "DotMac Platform Team",
                "email": "support@dotmac.io",
                "url": "https://dotmac.io"
            },
            "license": {
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT"
            }
        },
        "servers": [
            {
                "url": "http://localhost:8000",
                "description": "API Gateway (Local)"
            },
            {
                "url": "https://api.dotmac.io",
                "description": "API Gateway (Production)"
            }
        ],
        "paths": {},
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "JWT authentication token"
                },
                "apiKey": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "API key for service-to-service communication"
                }
            }
        },
        "security": [
            {"bearerAuth": []},
            {"apiKey": []}
        ]
    }

def save_swagger_specs():
    """Save Swagger specifications to files."""
    # Create docs directory
    docs_dir = Path("docs/swagger")
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate and save individual service specs
    for service in SERVICES:
        spec = generate_openapi_spec(service)
        
        # Save as JSON
        json_path = docs_dir / f"{service['path']}.json"
        with open(json_path, "w") as f:
            json.dump(spec, f, indent=2)
        
        # Save as YAML
        yaml_path = docs_dir / f"{service['path']}.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(spec, f, default_flow_style=False)
        
        print(f"✅ Generated Swagger spec for {service['name']}")
    
    # Generate and save unified spec
    unified_spec = generate_unified_spec()
    
    # Add all service endpoints to unified spec
    for service in SERVICES:
        service_prefix = f"/{service['path'].replace('_', '-')}"
        unified_spec["paths"][f"{service_prefix}/health"] = {
            "get": {
                "summary": f"{service['name']} Health Check",
                "description": f"Check {service['name']} health status",
                "tags": [service['name']],
                "servers": [{"url": f"http://localhost:{service['port']}"}],
                "responses": {
                    "200": {
                        "description": "Service is healthy",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "service": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    
    # Save unified spec
    unified_json_path = docs_dir / "dotmac_platform.json"
    with open(unified_json_path, "w") as f:
        json.dump(unified_spec, f, indent=2)
    
    unified_yaml_path = docs_dir / "dotmac_platform.yaml"
    with open(unified_yaml_path, "w") as f:
        yaml.dump(unified_spec, f, default_flow_style=False)
    
    print(f"✅ Generated unified Swagger spec")
    
    # Create HTML documentation
    create_html_docs(docs_dir)

def create_html_docs(docs_dir: Path):
    """Create HTML documentation using Swagger UI."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>DotMac Platform - API Documentation</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css">
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: sans-serif;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5rem;
        }
        .header p {
            margin: 0.5rem 0;
            opacity: 0.9;
        }
        .service-selector {
            padding: 1rem;
            background: #f5f5f5;
            text-align: center;
        }
        .service-selector select {
            padding: 0.5rem 1rem;
            font-size: 1rem;
            border-radius: 4px;
            border: 1px solid #ddd;
        }
        #swagger-ui {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 DotMac Platform API</h1>
        <p>Comprehensive ISP Management Platform</p>
        <p>Version 1.0.0</p>
    </div>
    
    <div class="service-selector">
        <label for="service">Select Service: </label>
        <select id="service" onchange="loadService(this.value)">
            <option value="dotmac_platform">All Services (Unified)</option>
            <option value="dotmac_api_gateway">API Gateway</option>
            <option value="dotmac_identity">Identity Service</option>
            <option value="dotmac_billing">Billing Service</option>
            <option value="dotmac_services">Services Provisioning</option>
            <option value="dotmac_networking">Network Management</option>
            <option value="dotmac_analytics">Analytics Service</option>
            <option value="dotmac_platform">Platform Service</option>
            <option value="dotmac_core_events">Event Bus</option>
            <option value="dotmac_core_ops">Core Ops</option>
        </select>
    </div>
    
    <div id="swagger-ui"></div>
    
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-standalone-preset.js"></script>
    <script>
        function loadService(service) {
            const ui = SwaggerUIBundle({
                url: `./${service}.json`,
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout"
            });
            window.ui = ui;
        }
        
        // Load unified spec by default
        loadService('dotmac_platform');
    </script>
</body>
</html>"""
    
    html_path = docs_dir / "index.html"
    with open(html_path, "w") as f:
        f.write(html_content)
    
    print(f"✅ Created HTML documentation at docs/swagger/index.html")

def main():
    """Main function."""
    print("🚀 Generating Swagger/OpenAPI Documentation...")
    print("=" * 50)
    
    save_swagger_specs()
    
    print("=" * 50)
    print("✨ Documentation generation complete!")
    print("\nFiles created:")
    print("  📁 docs/swagger/")
    print("  ├── index.html (Interactive documentation)")
    print("  ├── dotmac_platform.json (Unified spec)")
    print("  └── [service].json (Individual service specs)")
    print("\nTo view documentation:")
    print("  1. Open docs/swagger/index.html in a browser")
    print("  2. Or serve with: python -m http.server 8080 -d docs/swagger")

if __name__ == "__main__":
    main()