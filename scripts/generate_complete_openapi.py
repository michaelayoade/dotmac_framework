#!/usr/bin/env python3
"""
Generate complete OpenAPI documentation from all DotMac microservices.
This script collects actual endpoints from each service and creates unified documentation.
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List
import yaml

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

def get_service_openapi(service_name: str, port: int) -> Dict[str, Any]:
    """Get OpenAPI spec from a running service."""
    try:
        # Try to fetch from running service
        import requests
        response = requests.get(f"http://localhost:{port}/openapi.json", timeout=2)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    
    # If service isn't running, try to import and generate
    try:
        if service_name == "dotmac_platform":
            from dotmac_platform.app import app
        elif service_name == "dotmac_core_events":
            from dotmac_core_events.runtime.app_factory import create_app
            app = create_app()
        elif service_name == "dotmac_core_ops":
            from dotmac_core_ops.main import app
        elif service_name == "dotmac_networking":
            from dotmac_networking.main import app
        elif service_name == "dotmac_analytics":
            from dotmac_analytics.main import app
        elif service_name == "dotmac_api_gateway":
            from dotmac_api_gateway.main import app
        elif service_name == "dotmac_billing":
            from dotmac_billing.main import app
        elif service_name == "dotmac_identity":
            from dotmac_identity.main import app
        elif service_name == "dotmac_services":
            from dotmac_services.main import app
        else:
            return None
            
        # Get OpenAPI schema
        if hasattr(app, 'openapi'):
            return app.openapi()
        return None
    except Exception as e:
        print(f"Error loading {service_name}: {e}")
        return None

def merge_openapi_specs(specs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge multiple OpenAPI specs into one unified spec."""
    merged = {
        "openapi": "3.0.0",
        "info": {
            "title": "DotMac ISP Platform - Complete API",
            "description": "Unified API documentation for all DotMac microservices",
            "version": "2.0.0",
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
                "description": "Local development (unified API)"
            },
            {
                "url": "https://api.dotmac.io",
                "description": "Production API"
            }
        ],
        "paths": {},
        "components": {
            "schemas": {},
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
            }
        },
        "tags": []
    }
    
    # Merge each spec
    for spec in specs:
        if not spec:
            continue
            
        # Add service tag
        service_name = spec.get("info", {}).get("title", "Unknown Service")
        service_tag = {
            "name": service_name,
            "description": spec.get("info", {}).get("description", "")
        }
        if service_tag not in merged["tags"]:
            merged["tags"].append(service_tag)
        
        # Merge paths
        for path, methods in spec.get("paths", {}).items():
            # Prefix path with service name if not already
            if not path.startswith("/api/"):
                service_prefix = "/" + service_name.lower().replace(" ", "_").replace("dotmac_", "")
                prefixed_path = service_prefix + path
            else:
                prefixed_path = path
                
            if prefixed_path not in merged["paths"]:
                merged["paths"][prefixed_path] = {}
                
            for method, details in methods.items():
                # Add service tag to operation
                if "tags" not in details:
                    details["tags"] = []
                if service_name not in details["tags"]:
                    details["tags"].append(service_name)
                    
                merged["paths"][prefixed_path][method] = details
        
        # Merge schemas
        for schema_name, schema in spec.get("components", {}).get("schemas", {}).items():
            # Prefix schema name to avoid conflicts
            prefixed_name = f"{service_name.replace(' ', '')}_{schema_name}"
            merged["components"]["schemas"][prefixed_name] = schema
    
    return merged

def main():
    """Generate complete OpenAPI documentation."""
    print("🚀 Generating Complete OpenAPI Documentation")
    print("=" * 50)
    
    services = [
        ("dotmac_platform", 8006),
        ("dotmac_core_events", 8007),
        ("dotmac_core_ops", 8008),
        ("dotmac_networking", 8004),
        ("dotmac_analytics", 8005),
        ("dotmac_api_gateway", 8000),
        ("dotmac_billing", 8002),
        ("dotmac_identity", 8001),
        ("dotmac_services", 8003),
    ]
    
    specs = []
    endpoint_count = 0
    
    for service_name, port in services:
        print(f"📊 Processing {service_name}...")
        spec = get_service_openapi(service_name, port)
        
        if spec:
            path_count = len(spec.get("paths", {}))
            endpoint_count += path_count
            print(f"  ✅ Found {path_count} paths")
            specs.append(spec)
        else:
            print(f"  ⚠️  Could not load OpenAPI spec")
    
    # Merge all specs
    print("\n🔀 Merging OpenAPI specifications...")
    merged_spec = merge_openapi_specs(specs)
    
    # Save merged spec
    output_dir = Path(__file__).parent.parent / "docs" / "api"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save as JSON
    json_path = output_dir / "complete_openapi.json"
    with open(json_path, "w") as f:
        json.dump(merged_spec, f, indent=2)
    print(f"✅ Saved JSON: {json_path}")
    
    # Save as YAML
    yaml_path = output_dir / "complete_openapi.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(merged_spec, f, default_flow_style=False)
    print(f"✅ Saved YAML: {yaml_path}")
    
    # Generate summary
    print("\n" + "=" * 50)
    print("✨ Documentation Generation Complete!")
    print(f"📊 Total services processed: {len(services)}")
    print(f"📍 Total endpoints documented: {endpoint_count}")
    print(f"📁 Output directory: {output_dir}")
    
    # Create HTML viewer
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>DotMac Platform - Complete API Documentation</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css">
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {
            const ui = SwaggerUIBundle({
                url: './complete_openapi.json',
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
    </script>
</body>
</html>"""
    
    html_path = output_dir / "index.html"
    with open(html_path, "w") as f:
        f.write(html_content)
    print(f"✅ Created HTML viewer: {html_path}")
    
    print("\n📚 View documentation:")
    print(f"   Open: file://{html_path}")
    print(f"   Or serve: python -m http.server 8080 -d {output_dir}")

if __name__ == "__main__":
    main()