#!/usr/bin/env python3
"""
API Documentation Generator for DotMac Framework
Generates comprehensive API documentation from existing FastAPI applications
"""

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests


class APIDocumentationGenerator:
    def __init__(self, output_dir: str = None):
        self.project_root = Path(__file__).parent.parent  # noqa: B008
        self.output_dir = (
            Path(output_dir) if output_dir else self.project_root / "docs" / "api"
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

    def wait_for_service(self, url: str, timeout: int = 60) -> bool:
        """Wait for service to be ready"""
        self.logger.info(f"Waiting for service at {url}...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code == 200:
                    self.logger.info(f"Service ready at {url}")
                    return True
            except Exception:

                pass
            time.sleep(2)

        self.logger.error(f"Service not ready at {url} after {timeout}s")
        return False

    def fetch_openapi_spec(self, service_url: str, service_name: str) -> dict[str, Any]:
        """Fetch OpenAPI specification from running service"""
        self.logger.info(f"Fetching OpenAPI spec from {service_name}...")

        try:
            response = requests.get(f"{service_url}/openapi.json", timeout=10)
            if response.status_code == 200:
                spec = response.json()
                self.logger.info(
                    f"Successfully fetched OpenAPI spec for {service_name}"
                )
                return spec
            else:
                self.logger.error(
                    f"Failed to fetch OpenAPI spec: {response.status_code}"
                )
                return {}
        except Exception as e:
            self.logger.error(f"Error fetching OpenAPI spec from {service_name}: {e}")
            return {}

    def generate_markdown_docs(self, spec: dict[str, Any], service_name: str) -> str:
        """Generate Markdown documentation from OpenAPI spec"""
        self.logger.info(f"Generating Markdown documentation for {service_name}...")

        if not spec:
            return f"# {service_name} API Documentation\n\nNo OpenAPI specification available.\n"

        # Extract basic info
        info = spec.get("info", {})
        title = info.get("title", service_name)
        version = info.get("version", "1.0.0")
        description = info.get("description", "API documentation")

        # Start building markdown
        markdown = f"""# {title} API Documentation

**Version:** {version}

{description}

## Base URL

- Development: `http://localhost:8000` (for ISP Framework)
- Development: `http://localhost:8001` (for Management Platform)
- Production: Configure according to your deployment

## Authentication

Most endpoints require authentication. Include the JWT token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

## Endpoints

"""

        # Process paths
        paths = spec.get("paths", {})

        # Group paths by tags
        tagged_paths = {}
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    tags = details.get("tags", ["General"])
                    tag = tags[0] if tags else "General"

                    if tag not in tagged_paths:
                        tagged_paths[tag] = []

                    tagged_paths[tag].append(
                        {"path": path, "method": method.upper(), "details": details}
                    )

        # Generate documentation for each tag
        for tag, endpoints in tagged_paths.items():
            markdown += f"\n### {tag}\n\n"

            for endpoint in endpoints:
                path = endpoint["path"]
                method = endpoint["method"]
                details = endpoint["details"]

                summary = details.get("summary", f"{method} {path}")
                description = details.get("description", "")

                markdown += f"#### {method} `{path}`\n\n"
                markdown += f"**Summary:** {summary}\n\n"

                if description:
                    markdown += f"{description}\n\n"

                # Parameters
                parameters = details.get("parameters", [])
                if parameters:
                    markdown += "**Parameters:**\n\n"
                    markdown += "| Name | Type | In | Required | Description |\n"
                    markdown += "|------|------|----|---------|--------------|\n"

                    for param in parameters:
                        name = param.get("name", "")
                        param_type = param.get("schema", {}).get("type", "string")
                        param_in = param.get("in", "query")
                        required = "Yes" if param.get("required", False) else "No"
                        param_desc = param.get("description", "")

                        markdown += f"| {name} | {param_type} | {param_in} | {required} | {param_desc} |\n"

                    markdown += "\n"

                # Request Body
                request_body = details.get("requestBody", {})
                if request_body:
                    markdown += "**Request Body:**\n\n"
                    content = request_body.get("content", {})
                    for content_type, schema_info in content.items():
                        markdown += f"Content-Type: `{content_type}`\n\n"
                        schema = schema_info.get("schema", {})
                        if schema:
                            markdown += "```json\n"
                            markdown += self.format_schema_example(
                                schema, spec.get("components", {})
                            )
                            markdown += "\n```\n\n"

                # Responses
                responses = details.get("responses", {})
                if responses:
                    markdown += "**Responses:**\n\n"

                    for status_code, response_info in responses.items():
                        description = response_info.get("description", "")
                        markdown += f"- **{status_code}**: {description}\n"

                        content = response_info.get("content", {})
                        for content_type, schema_info in content.items():
                            schema = schema_info.get("schema", {})
                            if schema:
                                markdown += f"\n  Content-Type: `{content_type}`\n\n"
                                markdown += "  ```json\n"
                                markdown += "  " + self.format_schema_example(
                                    schema, spec.get("components", {})
                                ).replace("\n", "\n  ")
                                markdown += "\n  ```\n"

                    markdown += "\n"

                markdown += "---\n\n"

        # Add schemas section
        components = spec.get("components", {})
        schemas = components.get("schemas", {})

        if schemas:
            markdown += "\n## Data Models\n\n"

            for schema_name, schema_def in schemas.items():
                markdown += f"### {schema_name}\n\n"

                schema_type = schema_def.get("type", "object")
                description = schema_def.get("description", "")

                if description:
                    markdown += f"{description}\n\n"

                if schema_type == "object":
                    properties = schema_def.get("properties", {})
                    required = schema_def.get("required", [])

                    if properties:
                        markdown += "| Field | Type | Required | Description |\n"
                        markdown += "|-------|------|----------|-------------|\n"

                        for prop_name, prop_def in properties.items():
                            prop_type = prop_def.get("type", "string")
                            is_required = "Yes" if prop_name in required else "No"
                            prop_desc = prop_def.get("description", "")

                            markdown += f"| {prop_name} | {prop_type} | {is_required} | {prop_desc} |\n"

                        markdown += "\n"

                # Example
                example = schema_def.get("example")
                if example:
                    markdown += "**Example:**\n\n```json\n"
                    markdown += json.dumps(example, indent=2)
                    markdown += "\n```\n\n"

                markdown += "---\n\n"

        return markdown

    def format_schema_example(
        self, schema: dict[str, Any], components: dict[str, Any]
    ) -> str:
        """Generate example JSON from schema"""
        try:
            if "$ref" in schema:
                # Handle reference
                ref_path = schema["$ref"].replace("#/components/schemas/", "")
                if ref_path in components.get("schemas", {}):
                    return self.format_schema_example(
                        components["schemas"][ref_path], components
                    )

            schema_type = schema.get("type", "string")

            if schema_type == "object":
                example = {}
                properties = schema.get("properties", {})

                for prop_name, prop_def in properties.items():
                    if prop_def.get("type") == "string":
                        example[prop_name] = prop_def.get("example", "string")
                    elif prop_def.get("type") == "integer":
                        example[prop_name] = prop_def.get("example", 0)
                    elif prop_def.get("type") == "boolean":
                        example[prop_name] = prop_def.get("example", True)
                    elif prop_def.get("type") == "array":
                        items = prop_def.get("items", {})
                        example[prop_name] = [
                            self.format_schema_example(items, components)
                        ]
                    else:
                        example[prop_name] = prop_def.get("example", "value")

                return json.dumps(example, indent=2)

            elif schema_type == "array":
                items = schema.get("items", {})
                return json.dumps(
                    [self.format_schema_example(items, components)], indent=2
                )

            elif schema_type == "string":
                return json.dumps(schema.get("example", "string"))

            elif schema_type == "integer":
                return str(schema.get("example", 0))

            elif schema_type == "boolean":
                return str(schema.get("example", True)).lower()

            else:
                return json.dumps(schema.get("example", "value"))

        except Exception as e:
            self.logger.warning(f"Error formatting schema example: {e}")
            return "{}"

    def generate_postman_collection(
        self, spec: dict[str, Any], service_name: str
    ) -> dict[str, Any]:
        """Generate Postman collection from OpenAPI spec"""
        self.logger.info(f"Generating Postman collection for {service_name}...")

        if not spec:
            return {}

        info = spec.get("info", {})
        collection = {
            "info": {
                "name": f"{service_name} API",
                "description": info.get("description", "API collection"),
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            },
            "variable": [
                {"key": "base_url", "value": "http://localhost:8000", "type": "string"},
                {"key": "auth_token", "value": "your-jwt-token-here", "type": "string"},
            ],
            "item": [],
        }

        paths = spec.get("paths", {})

        # Group by tags
        tagged_requests = {}
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    tags = details.get("tags", ["General"])
                    tag = tags[0] if tags else "General"

                    if tag not in tagged_requests:
                        tagged_requests[tag] = []

                    # Build request
                    request = {
                        "name": details.get("summary", f"{method.upper()} {path}"),
                        "request": {
                            "method": method.upper(),
                            "header": [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{auth_token}}",
                                    "type": "text",
                                }
                            ],
                            "url": {
                                "raw": "{{base_url}}" + path,
                                "host": ["{{base_url}}"],
                                "path": path.strip("/").split("/"),
                            },
                        },
                    }

                    # Add request body for POST/PUT/PATCH
                    if method.upper() in ["POST", "PUT", "PATCH"]:
                        request_body = details.get("requestBody", {})
                        if request_body:
                            content = request_body.get("content", {})
                            if "application/json" in content:
                                schema = content["application/json"].get("schema", {})
                                example_body = self.format_schema_example(
                                    schema, spec.get("components", {})
                                )

                                request["request"]["body"] = {
                                    "mode": "raw",
                                    "raw": example_body,
                                    "options": {"raw": {"language": "json"}},
                                }

                                request["request"]["header"].append(
                                    {
                                        "key": "Content-Type",
                                        "value": "application/json",
                                        "type": "text",
                                    }
                                )

                    tagged_requests[tag].append(request)

        # Convert to Postman collection format
        for tag, requests in tagged_requests.items():
            folder = {"name": tag, "item": requests}
            collection["item"].append(folder)

        return collection

    def start_services_for_docs(self) -> bool:
        """Start services if not running for documentation generation"""
        self.logger.info("Checking service status...")

        production_dir = self.project_root / "deployment" / "production"
        if not production_dir.exists():
            self.logger.error("Production directory not found")
            return False

        os.chdir(production_dir)

        try:
            # Check if services are running
            result = subprocess.run(
                "docker-compose -f docker-compose.prod.yml ps --services --filter status=running",
                shell=True,
                capture_output=True,
                text=True,
            )

            running_services = (
                result.stdout.strip().split("\n") if result.stdout.strip() else []
            )
            required_services = ["isp-framework", "management-platform"]

            missing_services = [
                s for s in required_services if s not in running_services
            ]

            if missing_services:
                self.logger.info(f"Starting missing services: {missing_services}")
                subprocess.run(
                    f"docker-compose -f docker-compose.prod.yml up -d {' '.join(missing_services)}",
                    shell=True,
                    check=True,
                )

                # Wait for services to be ready
                time.sleep(30)

            return True

        except Exception as e:
            self.logger.error(f"Error starting services: {e}")
            return False

    def generate_documentation(self) -> bool:
        """Generate comprehensive API documentation"""
        self.logger.info("🚀 Starting API Documentation Generation")
        self.logger.info("=" * 60)

        # Ensure services are running
        if not self.start_services_for_docs():
            self.logger.error("Failed to start services")
            return False

        # Service configurations
        services = [
            {
                "name": "ISP Framework",
                "url": "http://localhost:8001",
                "filename": "isp-framework-api",
            },
            {
                "name": "Management Platform",
                "url": "http://localhost:8000",
                "filename": "management-platform-api",
            },
        ]

        successful_generations = 0

        for service in services:
            self.logger.info(f"\n📖 Generating documentation for {service['name']}...")

            # Wait for service to be ready
            if not self.wait_for_service(service["url"]):
                self.logger.error(f"Service {service['name']} not ready, skipping")
                continue

            # Fetch OpenAPI spec
            spec = self.fetch_openapi_spec(service["url"], service["name"])

            if not spec:
                self.logger.error(f"No OpenAPI spec available for {service['name']}")
                continue

            # Generate Markdown documentation
            markdown_docs = self.generate_markdown_docs(spec, service["name"])
            markdown_file = self.output_dir / f"{service['filename']}.md"

            with open(markdown_file, "w") as f:
                f.write(markdown_docs)

            self.logger.info(f"✅ Markdown documentation saved: {markdown_file}")

            # Generate Postman collection
            postman_collection = self.generate_postman_collection(spec, service["name"])
            if postman_collection:
                postman_file = self.output_dir / f"{service['filename']}-postman.json"

                with open(postman_file, "w") as f:
                    json.dump(postman_collection, f, indent=2)

                self.logger.info(f"✅ Postman collection saved: {postman_file}")

            # Save raw OpenAPI spec
            spec_file = self.output_dir / f"{service['filename']}-openapi.json"
            with open(spec_file, "w") as f:
                json.dump(spec, f, indent=2)

            self.logger.info(f"✅ OpenAPI spec saved: {spec_file}")

            successful_generations += 1

        # Generate combined API index
        self.generate_api_index()

        # Summary
        self.logger.info("\n" + "=" * 60)
        self.logger.info("📖 API Documentation Generation Summary")
        self.logger.info(
            f"✅ Generated: {successful_generations}/{len(services)} services"
        )

        if successful_generations > 0:
            self.logger.info("\n🎉 API documentation generated successfully!")
            self.logger.info(f"📁 Output directory: {self.output_dir}")
            self.logger.info("\nGenerated files:")
            for file in self.output_dir.glob("*"):
                self.logger.info(f"  📄 {file.name}")

            self.logger.info("\nUsage:")
            self.logger.info("1. View Markdown docs in your preferred viewer")
            self.logger.info("2. Import Postman collections for API testing")
            self.logger.info("3. Use OpenAPI specs with other tools")
            return True
        else:
            self.logger.error("❌ No documentation generated")
            return False

    def generate_api_index(self):
        """Generate API documentation index"""
        index_content = """# DotMac Framework API Documentation

This directory contains comprehensive API documentation for the DotMac Framework services.

## Available APIs

### ISP Framework API
- **Documentation**: [isp-framework-api.md](./isp-framework-api.md)
- **Postman Collection**: [isp-framework-api-postman.json](./isp-framework-api-postman.json)
- **OpenAPI Spec**: [isp-framework-api-openapi.json](./isp-framework-api-openapi.json)
- **Base URL**: `http://localhost:8001` (development)

### Management Platform API
- **Documentation**: [management-platform-api.md](./management-platform-api.md)
- **Postman Collection**: [management-platform-api-postman.json](./management-platform-api-postman.json)
- **OpenAPI Spec**: [management-platform-api-openapi.json](./management-platform-api-openapi.json)
- **Base URL**: `http://localhost:8000` (development)

## Quick Start

1. **View Documentation**: Open the `.md` files in your preferred Markdown viewer
2. **Test APIs**: Import the Postman collections into Postman for interactive testing
3. **Integration**: Use the OpenAPI specifications for code generation or other tooling

## Authentication

Most API endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

## Getting Started

1. Start the services:
   ```bash
   cd deployment/production
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. Get authentication token:
   ```bash
   # Use the appropriate login endpoint
   curl -X POST http://localhost:8000/api/v1/auth/login \\
     -H "Content-Type: application/json" \\
     -d '{"email": "your@email.com", "password": "yourpassword"}'
   ```

3. Test endpoints using the token

## Regenerating Documentation

To regenerate the API documentation:

```bash
python3 scripts/generate_api_docs.py
```

## Support

- Check the individual API documentation files for detailed endpoint information
- Use the Postman collections for interactive testing
- Refer to the OpenAPI specifications for integration details
"""

        index_file = self.output_dir / "README.md"
        with open(index_file, "w") as f:
            f.write(index_content)

        self.logger.info(f"✅ API index generated: {index_file}")


def main():
    import argparse


    parser = argparse.ArgumentParser(
        description="Generate API documentation for DotMac Framework"
    )
    parser.add_argument(
        "--output-dir", help="Output directory for documentation", default=None
    )
    parser.add_argument(
        "--start-services", action="store_true", help="Start services if not running"
    )

    args = parser.parse_args()

    generator = APIDocumentationGenerator(output_dir=args.output_dir)
    success = generator.generate_documentation()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
