#!/usr/bin/env python3
"""
OpenAPI Documentation Generator for DotMac Platform.
Aggregates OpenAPI specifications from all services and generates unified documentation.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import httpx
import yaml
from datetime import datetime


# Service registry with ports
SERVICES = {
    "dotmac_identity": {
        "port": 8001,
        "name": "Identity Service",
        "description": "User authentication and customer management"
    },
    "dotmac_billing": {
        "port": 8002,
        "name": "Billing Service",
        "description": "Billing, invoicing, and payment processing"
    },
    "dotmac_services": {
        "port": 8003,
        "name": "Services Platform",
        "description": "Service provisioning and lifecycle management"
    },
    "dotmac_networking": {
        "port": 8004,
        "name": "Networking Service",
        "description": "Network infrastructure and device management"
    },
    "dotmac_analytics": {
        "port": 8005,
        "name": "Analytics Service",
        "description": "Business intelligence and reporting"
    },
    "dotmac_platform": {
        "port": 8006,
        "name": "Platform Service",
        "description": "Core platform SDKs and utilities"
    },
    "dotmac_api_gateway": {
        "port": 8000,
        "name": "API Gateway",
        "description": "API routing and aggregation"
    },
}


class OpenAPIDocGenerator:
    """Generate unified OpenAPI documentation from multiple services."""
    
    def __init__(self, output_dir: str = "docs/api"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.specs = {}
        self.unified_spec = None
    
    async def fetch_openapi_spec(self, service: str, port: int) -> Dict[str, Any]:
        """Fetch OpenAPI specification from a service."""
        url = f"http://localhost:{port}/openapi.json"
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    print(f"✅ Fetched OpenAPI spec from {service}")
                    return response.json()
                else:
                    print(f"⚠️  Failed to fetch spec from {service}: HTTP {response.status_code}")
                    return None
            except Exception as e:
                print(f"❌ Error fetching spec from {service}: {e}")
                return None
    
    async def collect_all_specs(self):
        """Collect OpenAPI specifications from all services."""
        tasks = []
        for service, config in SERVICES.items():
            tasks.append(self.fetch_openapi_spec(service, config["port"]))
        
        results = await asyncio.gather(*tasks)
        
        for service, spec in zip(SERVICES.keys(), results):
            if spec:
                self.specs[service] = spec
    
    def merge_specifications(self):
        """Merge all service specifications into a unified spec."""
        self.unified_spec = {
            "openapi": "3.0.3",
            "info": {
                "title": "DotMac Platform API",
                "description": self._generate_unified_description(),
                "version": "1.0.0",
                "contact": {
                    "name": "DotMac Platform Team",
                    "email": "api-support@dotmac.com",
                    "url": "https://docs.dotmac.com"
                },
                "license": {
                    "name": "MIT",
                    "url": "https://opensource.org/licenses/MIT"
                }
            },
            "servers": [
                {
                    "url": "https://api.dotmac.com",
                    "description": "Production API Gateway"
                },
                {
                    "url": "https://staging-api.dotmac.com",
                    "description": "Staging API Gateway"
                },
                {
                    "url": "http://localhost:8000",
                    "description": "Local Development"
                }
            ],
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {
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
            },
            "security": [
                {"BearerAuth": []},
                {"ApiKeyAuth": []}
            ],
            "tags": []
        }
        
        # Merge paths and schemas from each service
        for service, spec in self.specs.items():
            service_prefix = f"/{service.replace('dotmac_', '')}"
            
            # Add service tag
            self.unified_spec["tags"].append({
                "name": SERVICES[service]["name"],
                "description": SERVICES[service]["description"],
                "x-service": service
            })
            
            # Merge paths with service prefix
            if "paths" in spec:
                for path, path_spec in spec["paths"].items():
                    # Prefix the path with service name
                    prefixed_path = service_prefix + path if path != "/" else service_prefix
                    self.unified_spec["paths"][prefixed_path] = path_spec
                    
                    # Update tags in operations
                    for method in ["get", "post", "put", "patch", "delete"]:
                        if method in path_spec:
                            if "tags" not in path_spec[method]:
                                path_spec[method]["tags"] = []
                            # Add service tag
                            path_spec[method]["tags"].insert(0, SERVICES[service]["name"])
            
            # Merge component schemas
            if "components" in spec and "schemas" in spec["components"]:
                for schema_name, schema_spec in spec["components"]["schemas"].items():
                    # Prefix schema name with service to avoid conflicts
                    prefixed_name = f"{service}_{schema_name}"
                    self.unified_spec["components"]["schemas"][prefixed_name] = schema_spec
    
    def _generate_unified_description(self) -> str:
        """Generate comprehensive API description."""
        return """
# DotMac Platform - Unified API Documentation

## Overview
The DotMac Platform provides a comprehensive suite of APIs for Internet Service Provider operations.
This unified documentation covers all microservices and their endpoints.

## Services

### 🔐 Identity Service
- User authentication and authorization
- Customer account management
- Organization and contact management
- User profiles and preferences

### 💰 Billing Service
- Invoice generation and management
- Payment processing
- Subscription billing
- Tax calculation
- Credit management

### 📦 Services Platform
- Service catalog management
- Service provisioning
- Lifecycle management
- Service bundles and packages

### 🌐 Networking Service
- Network device management
- SNMP monitoring
- SSH automation
- Network topology

### 📊 Analytics Service
- Business intelligence
- Reporting and dashboards
- Data visualization
- Performance metrics

### 🛠️ Platform Service
- Core platform utilities
- Feature flags
- Audit logging
- File storage

### 🚪 API Gateway
- Request routing
- Rate limiting
- API aggregation
- Service discovery

## Authentication

All API endpoints require authentication using either:
- **Bearer Token**: JWT token in Authorization header
- **API Key**: X-API-Key header

## Rate Limiting

API requests are rate limited to:
- 1000 requests per minute for authenticated users
- 100 requests per minute for unauthenticated users

## Error Handling

All errors follow a consistent format:
```json
{
    "error": "ERROR_CODE",
    "message": "Human readable message",
    "details": {},
    "request_id": "req_123"
}
```

## Pagination

List endpoints support pagination with:
- `page`: Page number (1-based)
- `limit`: Items per page (max 100)
- `sort_by`: Field to sort by
- `sort_order`: asc or desc

## Webhooks

Many operations support webhook notifications.
Configure webhooks in your account settings.

## Support

- Documentation: https://docs.dotmac.com
- API Status: https://status.dotmac.com
- Support: api-support@dotmac.com
"""
    
    def generate_html_documentation(self):
        """Generate HTML documentation using ReDoc."""
        html_template = """<!DOCTYPE html>
<html>
<head>
    <title>DotMac Platform API Documentation</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body {
            margin: 0;
            padding: 0;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-family: 'Montserrat', sans-serif;
        }
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>DotMac Platform API</h1>
        <p>Comprehensive API documentation for ISP operations</p>
    </div>
    <redoc spec-url="openapi.json"></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js"></script>
</body>
</html>"""
        
        html_path = self.output_dir / "index.html"
        html_path.write_text(html_template)
        print(f"📄 Generated HTML documentation: {html_path}")
    
    def generate_postman_collection(self):
        """Generate Postman collection from OpenAPI spec."""
        if not self.unified_spec:
            return
        
        collection = {
            "info": {
                "name": "DotMac Platform API",
                "description": self.unified_spec["info"]["description"],
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": [],
            "auth": {
                "type": "bearer",
                "bearer": [
                    {
                        "key": "token",
                        "value": "{{access_token}}",
                        "type": "string"
                    }
                ]
            },
            "variable": [
                {
                    "key": "base_url",
                    "value": "http://localhost:8000"
                },
                {
                    "key": "access_token",
                    "value": ""
                }
            ]
        }
        
        # Convert OpenAPI paths to Postman requests
        for path, path_spec in self.unified_spec["paths"].items():
            folder = {
                "name": path.split("/")[1] if path != "/" else "root",
                "item": []
            }
            
            for method, operation in path_spec.items():
                if method in ["get", "post", "put", "patch", "delete"]:
                    request = {
                        "name": operation.get("summary", f"{method.upper()} {path}"),
                        "request": {
                            "method": method.upper(),
                            "header": [],
                            "url": {
                                "raw": "{{base_url}}" + path,
                                "host": ["{{base_url}}"],
                                "path": path.split("/")[1:]
                            },
                            "description": operation.get("description", "")
                        }
                    }
                    
                    # Add request body example if available
                    if "requestBody" in operation:
                        request["request"]["body"] = {
                            "mode": "raw",
                            "raw": "{}",
                            "options": {
                                "raw": {
                                    "language": "json"
                                }
                            }
                        }
                    
                    folder["item"].append(request)
            
            if folder["item"]:
                collection["item"].append(folder)
        
        postman_path = self.output_dir / "postman_collection.json"
        postman_path.write_text(json.dumps(collection, indent=2))
        print(f"📮 Generated Postman collection: {postman_path}")
    
    def save_specifications(self):
        """Save all specifications to files."""
        # Save unified OpenAPI spec
        if self.unified_spec:
            # JSON format
            json_path = self.output_dir / "openapi.json"
            json_path.write_text(json.dumps(self.unified_spec, indent=2))
            print(f"📝 Saved unified OpenAPI spec: {json_path}")
            
            # YAML format
            yaml_path = self.output_dir / "openapi.yaml"
            yaml_path.write_text(yaml.dump(self.unified_spec, sort_keys=False))
            print(f"📝 Saved unified OpenAPI spec: {yaml_path}")
        
        # Save individual service specs
        services_dir = self.output_dir / "services"
        services_dir.mkdir(exist_ok=True)
        
        for service, spec in self.specs.items():
            service_path = services_dir / f"{service}.json"
            service_path.write_text(json.dumps(spec, indent=2))
            print(f"📝 Saved {service} spec: {service_path}")
    
    def generate_markdown_summary(self):
        """Generate a markdown summary of all endpoints."""
        lines = ["# DotMac Platform API Endpoints\n"]
        lines.append(f"Generated: {datetime.now().isoformat()}\n\n")
        
        if self.unified_spec and "paths" in self.unified_spec:
            # Group endpoints by service
            by_service = {}
            for path, path_spec in self.unified_spec["paths"].items():
                service = path.split("/")[1] if path != "/" else "root"
                if service not in by_service:
                    by_service[service] = []
                
                for method in ["get", "post", "put", "patch", "delete"]:
                    if method in path_spec:
                        operation = path_spec[method]
                        by_service[service].append({
                            "method": method.upper(),
                            "path": path,
                            "summary": operation.get("summary", ""),
                            "operation_id": operation.get("operationId", "")
                        })
            
            # Write service sections
            for service, endpoints in sorted(by_service.items()):
                lines.append(f"## {service.replace('_', ' ').title()}\n\n")
                lines.append("| Method | Path | Description | Operation ID |\n")
                lines.append("|--------|------|-------------|-------------|\n")
                
                for endpoint in sorted(endpoints, key=lambda x: (x["path"], x["method"])):
                    lines.append(f"| {endpoint['method']} | `{endpoint['path']}` | {endpoint['summary']} | {endpoint['operation_id']} |\n")
                
                lines.append("\n")
        
        # Statistics
        lines.append("## Statistics\n\n")
        lines.append(f"- Total Services: {len(self.specs)}\n")
        if self.unified_spec:
            lines.append(f"- Total Endpoints: {len(self.unified_spec.get('paths', {}))}\n")
            lines.append(f"- Total Schemas: {len(self.unified_spec.get('components', {}).get('schemas', {}))}\n")
        
        summary_path = self.output_dir / "API_SUMMARY.md"
        summary_path.write_text("".join(lines))
        print(f"📊 Generated API summary: {summary_path}")
    
    async def generate_all(self):
        """Generate all documentation formats."""
        print("🚀 Starting OpenAPI documentation generation...\n")
        
        # Collect specs from services
        print("📡 Fetching OpenAPI specifications from services...")
        await self.collect_all_specs()
        
        if not self.specs:
            print("❌ No OpenAPI specifications found. Make sure services are running.")
            return
        
        print(f"\n✅ Collected specs from {len(self.specs)} services")
        
        # Merge specifications
        print("\n🔧 Merging specifications...")
        self.merge_specifications()
        
        # Save all formats
        print("\n💾 Generating documentation files...")
        self.save_specifications()
        self.generate_html_documentation()
        self.generate_postman_collection()
        self.generate_markdown_summary()
        
        print(f"\n✨ Documentation generated successfully in {self.output_dir}")
        print("\nTo view the documentation:")
        print(f"  1. Open {self.output_dir}/index.html in a browser")
        print(f"  2. Import {self.output_dir}/postman_collection.json into Postman")
        print(f"  3. View {self.output_dir}/API_SUMMARY.md for a quick reference")


async def main():
    """Main entry point."""
    generator = OpenAPIDocGenerator()
    await generator.generate_all()


if __name__ == "__main__":
    # Check if running with --serve flag to start a simple HTTP server
    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        import http.server
        import socketserver
        
        os.chdir("docs/api")
        PORT = 8080
        Handler = http.server.SimpleHTTPRequestHandler
        
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"📡 Serving documentation at http://localhost:{PORT}")
            httpd.serve_forever()
    else:
        asyncio.run(main())