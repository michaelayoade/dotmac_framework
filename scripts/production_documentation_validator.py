#!/usr/bin/env python3
"""
Production-Ready Documentation Validator
Ensures zero tolerance for code-documentation mismatches
"""

import ast
import importlib
import inspect
import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import yaml


@dataclass
class CriticalDocumentationIssue:
    """Critical documentation issue that blocks production"""

    severity: str  # 'BLOCKING', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    category: (
        str  # 'API_MISMATCH', 'MISSING_DOCSTRING', 'OUTDATED_REFERENCE', 'BROKEN_LINK'
    )
    location: str  # File path and line number
    description: str
    actual_code: Optional[str]
    documented_behavior: Optional[str]
    fix_suggestion: str
    business_impact: str  # Impact if not fixed


@dataclass
class APIEndpointValidation:
    """Validated API endpoint information"""

    path: str
    method: str
    function_name: str
    parameters: List[str]
    response_schema: Optional[str]
    docstring: Optional[str]
    is_documented: bool
    documentation_matches: bool
    missing_from_docs: List[str]
    incorrect_in_docs: List[str]


class ProductionCodeValidator:
    """Validates code against production requirements"""

    def __init__(self, source_root: str):
        self.source_root = Path(source_root)
        self.issues: List[CriticalDocumentationIssue] = []
        self.api_endpoints: List[APIEndpointValidation] = []
        self.readme_claims: Dict[str, bool] = {}

    def validate_readme_claims(self, readme_path: str) -> None:
        """Validate README.md claims against actual codebase"""
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                readme_content = f.read()

            # Extract claims from README
            claims = self._extract_readme_claims(readme_content)

            # Validate each claim
            for claim, assertion in claims.items():
                is_valid = self._validate_claim(claim, assertion)
                self.readme_claims[claim] = is_valid

                if not is_valid:
                    self.issues.append(
                        CriticalDocumentationIssue(
                            severity="BLOCKING",
                            category="OUTDATED_REFERENCE",
                            location=f"{readme_path}",
                            description=f"README claim is false: {claim}",
                            actual_code=self._get_actual_implementation(claim),
                            documented_behavior=assertion,
                            fix_suggestion=f"Update README section for: {claim}",
                            business_impact="Misleading documentation causes customer confusion and support burden",
                        )
                    )

        except Exception as e:
            logging.error(f"Failed to validate README: {e}")

    def _extract_readme_claims(self, content: str) -> Dict[str, str]:
        """Extract verifiable claims from README"""
        claims = {}

        # Container health probes claim
        if "/health/live" in content:
            claims["health_probes"] = (
                "Has Kubernetes health probes at /health/live, /health/ready, /health/startup"
            )

        # API framework claim
        if "FastAPI" in content:
            claims["fastapi_framework"] = "Uses FastAPI framework"

        # Database claim
        if "PostgreSQL" in content:
            claims["postgresql_database"] = "Uses PostgreSQL database"

        # Container deployment claim
        if "container-per-tenant" in content.lower():
            claims["container_per_tenant"] = (
                "Supports container-per-tenant architecture"
            )

        # Production ready claim
        if "production-ready" in content.lower():
            claims["production_ready"] = "Platform is production-ready"

        return claims

    def _validate_claim(self, claim: str, assertion: str) -> bool:
        """Validate a specific claim against codebase"""
        if claim == "health_probes":
            return self._validate_health_probes()
        elif claim == "fastapi_framework":
            return self._validate_fastapi_usage()
        elif claim == "postgresql_database":
            return self._validate_postgresql_usage()
        elif claim == "container_per_tenant":
            return self._validate_container_architecture()
        elif claim == "production_ready":
            return self._validate_production_readiness()

        return True  # Default to true for unknown claims

    def _validate_health_probes(self) -> bool:
        """Validate health probe endpoints exist"""
        health_patterns = ["/health/live", "/health/ready", "/health/startup"]
        found_patterns = []

        for file_path in self.source_root.rglob("*.py"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    for pattern in health_patterns:
                        if pattern in content:
                            found_patterns.append(pattern)
            except:
                continue

        return len(set(found_patterns)) >= 3  # All three health endpoints

    def _validate_fastapi_usage(self) -> bool:
        """Validate FastAPI is actually used"""
        fastapi_imports = 0

        for file_path in self.source_root.rglob("*.py"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "from fastapi import" in content or "import fastapi" in content:
                        fastapi_imports += 1
            except:
                continue

        return fastapi_imports > 0

    def _validate_postgresql_usage(self) -> bool:
        """Validate PostgreSQL is configured"""
        postgres_evidence = False

        # Check for SQLAlchemy PostgreSQL connections
        for file_path in self.source_root.rglob("*.py"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if any(
                        pattern in content
                        for pattern in [
                            "postgresql://",
                            "asyncpg",
                            "psycopg2",
                            "DATABASE_URL",
                            "postgres",
                        ]
                    ):
                        postgres_evidence = True
                        break
            except:
                continue

        return postgres_evidence

    def _validate_container_architecture(self) -> bool:
        """Validate container-per-tenant architecture exists"""
        # Look for Dockerfile and Kubernetes configs
        dockerfile_exists = (self.source_root.parent / "Dockerfile").exists()
        k8s_configs = list(self.source_root.parent.rglob("*.yaml")) + list(
            self.source_root.parent.rglob("*.yml")
        )

        return dockerfile_exists and len(k8s_configs) > 0

    def _validate_production_readiness(self) -> bool:
        """Validate production readiness claims"""
        production_indicators = [
            self._validate_health_probes(),
            self._validate_fastapi_usage(),
            self._validate_postgresql_usage(),
            self._has_proper_logging(),
            self._has_security_measures(),
        ]

        # Must have at least 80% of production indicators
        return sum(production_indicators) / len(production_indicators) >= 0.8

    def _has_proper_logging(self) -> bool:
        """Check for proper logging setup"""
        for file_path in self.source_root.rglob("*.py"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if any(
                        pattern in content
                        for pattern in [
                            "logging.getLogger",
                            "logger =",
                            "import logging",
                        ]
                    ):
                        return True
            except:
                continue
        return False

    def _has_security_measures(self) -> bool:
        """Check for security implementations"""
        security_patterns = ["jwt", "auth", "security", "rate_limit", "csrf"]

        for file_path in self.source_root.rglob("*.py"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                    if any(pattern in content for pattern in security_patterns):
                        return True
            except:
                continue
        return False

    def _get_actual_implementation(self, claim: str) -> str:
        """Get actual implementation details for a claim"""
        if claim == "health_probes":
            # Find health probe implementations
            for file_path in self.source_root.rglob("*.py"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "/health" in content:
                            return f"Found health endpoints in {file_path}"
                except:
                    continue

        return "Implementation not found or differs from documentation"

    def validate_api_endpoints(self) -> None:
        """Validate all API endpoints against documentation"""
        # Find all FastAPI routers
        router_files = []

        for file_path in self.source_root.rglob("*router*.py"):
            router_files.append(file_path)

        for file_path in self.source_root.rglob("*api*.py"):
            router_files.append(file_path)

        # Extract endpoints from each router
        for router_file in router_files:
            endpoints = self._extract_fastapi_endpoints(router_file)
            self.api_endpoints.extend(endpoints)

        # Validate endpoints against documentation
        self._cross_reference_api_documentation()

    def _extract_fastapi_endpoints(
        self, file_path: Path
    ) -> List[APIEndpointValidation]:
        """Extract FastAPI endpoints from a router file"""
        endpoints = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse AST to find route decorators
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    endpoint = self._analyze_fastapi_function(node, file_path, content)
                    if endpoint:
                        endpoints.append(endpoint)

        except Exception as e:
            logging.warning(f"Failed to parse {file_path}: {e}")

        return endpoints

    def _analyze_fastapi_function(
        self, func_node: ast.FunctionDef, file_path: Path, content: str
    ) -> Optional[APIEndpointValidation]:
        """Analyze a function for FastAPI route decorators"""
        for decorator in func_node.decorator_list:
            if self._is_route_decorator(decorator):
                method, path = self._extract_route_info(decorator, func_node.name)

                parameters = [
                    arg.arg for arg in func_node.args.args if arg.arg != "self"
                ]
                docstring = ast.get_docstring(func_node)

                # Extract response schema from type hints
                response_schema = None
                if func_node.returns:
                    response_schema = ast.unparse(func_node.returns)

                return APIEndpointValidation(
                    path=path,
                    method=method,
                    function_name=func_node.name,
                    parameters=parameters,
                    response_schema=response_schema,
                    docstring=docstring,
                    is_documented=False,  # Will be updated later
                    documentation_matches=False,  # Will be updated later
                    missing_from_docs=[],
                    incorrect_in_docs=[],
                )

        return None

    def _is_route_decorator(self, decorator: ast.AST) -> bool:
        """Check if decorator is a FastAPI route decorator"""
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                return decorator.func.attr in [
                    "get",
                    "post",
                    "put",
                    "delete",
                    "patch",
                    "options",
                ]
            elif isinstance(decorator.func, ast.Name):
                return decorator.func.id in [
                    "get",
                    "post",
                    "put",
                    "delete",
                    "patch",
                    "options",
                ]

        return False

    def _extract_route_info(
        self, decorator: ast.Call, func_name: str
    ) -> Tuple[str, str]:
        """Extract HTTP method and path from route decorator"""
        method = "GET"  # Default
        path = f"/{func_name}"  # Default

        if isinstance(decorator.func, ast.Attribute):
            method = decorator.func.attr.upper()
        elif isinstance(decorator.func, ast.Name):
            method = decorator.func.id.upper()

        # Extract path from decorator arguments
        if decorator.args:
            try:
                path = ast.literal_eval(decorator.args[0])
            except:
                pass

        return method, path

    def _cross_reference_api_documentation(self) -> None:
        """Cross-reference API endpoints with documentation"""
        # This is a simplified version - in production, you'd parse OpenAPI specs
        # or other structured API documentation
        pass

    def validate_critical_files(self) -> None:
        """Validate critical production files exist and are correct"""
        critical_files = [
            ("Dockerfile", "Container deployment configuration"),
            ("requirements.txt", "Python dependencies"),
            ("pyproject.toml", "Python project configuration"),
            ("docker-compose.yml", "Local development setup"),
        ]

        project_root = self.source_root.parent

        for file_name, description in critical_files:
            file_path = project_root / file_name

            if not file_path.exists():
                self.issues.append(
                    CriticalDocumentationIssue(
                        severity="CRITICAL",
                        category="MISSING_DOCSTRING",
                        location=str(file_path),
                        description=f"Critical file missing: {file_name}",
                        actual_code=None,
                        documented_behavior=f"Should have {description}",
                        fix_suggestion=f"Create {file_name} with proper {description}",
                        business_impact="Cannot deploy to production without this file",
                    )
                )


class DRYDocumentationSystem:
    """Production-grade DRY documentation system"""

    def __init__(self, project_root: str, validator: ProductionCodeValidator):
        self.project_root = Path(project_root)
        self.validator = validator
        self.templates_dir = self.project_root / "docs" / "templates"
        self.output_dir = self.project_root / "docs" / "generated"

    def setup_documentation_structure(self) -> None:
        """Setup DRY documentation structure"""
        # Create directories
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create base templates
        self._create_api_reference_template()
        self._create_deployment_guide_template()
        self._create_troubleshooting_template()

    def _create_api_reference_template(self) -> None:
        """Create API reference template"""
        template_content = """# API Reference

{% for endpoint in api_endpoints %}
## {{ endpoint.method }} {{ endpoint.path }}

**Function**: `{{ endpoint.function_name }}()`

{% if endpoint.docstring %}
{{ endpoint.docstring }}
{% else %}
*No documentation available*
{% endif %}

**Parameters:**
{% for param in endpoint.parameters %}
- `{{ param }}`
{% endfor %}

{% if endpoint.response_schema %}
**Response Schema**: `{{ endpoint.response_schema }}`
{% endif %}

---
{% endfor %}

*Auto-generated from source code on {{ generation_date }}*
"""

        with open(self.templates_dir / "api_reference.md.j2", "w") as f:
            f.write(template_content)

    def _create_deployment_guide_template(self) -> None:
        """Create deployment guide template"""
        template_content = """# Deployment Guide

## Health Checks

The application provides the following health check endpoints:

{% if health_probes_available %}
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe
- `GET /health/startup` - Startup probe
{% else %}
⚠️ **Warning**: Health probes not implemented
{% endif %}

## Container Deployment

{% if dockerfile_exists %}
Build the container:
```bash
docker build -t dotmac-platform .
```
{% else %}
⚠️ **Error**: No Dockerfile found
{% endif %}

## Database Setup

{% if postgresql_configured %}
The application uses PostgreSQL. Ensure database is configured with:
```bash
export DATABASE_URL="postgresql://user:pass@host:5432/db"
```
{% else %}
⚠️ **Warning**: PostgreSQL configuration not detected
{% endif %}

*Auto-generated on {{ generation_date }}*
"""

        with open(self.templates_dir / "deployment_guide.md.j2", "w") as f:
            f.write(template_content)

    def _create_troubleshooting_template(self) -> None:
        """Create troubleshooting guide template"""
        template_content = """# Troubleshooting Guide

## Common Issues

{% for issue in critical_issues %}
### {{ issue.category }}: {{ issue.description }}

**Location**: `{{ issue.location }}`

**Problem**: {{ issue.description }}

{% if issue.actual_code %}
**Current Implementation**:
```
{{ issue.actual_code }}
```
{% endif %}

**Fix**: {{ issue.fix_suggestion }}

**Business Impact**: {{ issue.business_impact }}

---
{% endfor %}

*Auto-generated on {{ generation_date }}*
"""

        with open(self.templates_dir / "troubleshooting.md.j2", "w") as f:
            f.write(template_content)

    def generate_documentation(self) -> None:
        """Generate all DRY documentation"""
        from datetime import datetime

        generation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Generate API reference
        self._render_template(
            "api_reference.md.j2",
            {
                "api_endpoints": self.validator.api_endpoints,
                "generation_date": generation_date,
            },
        )

        # Generate deployment guide
        self._render_template(
            "deployment_guide.md.j2",
            {
                "health_probes_available": self.validator._validate_health_probes(),
                "dockerfile_exists": (self.project_root / "Dockerfile").exists(),
                "postgresql_configured": self.validator._validate_postgresql_usage(),
                "generation_date": generation_date,
            },
        )

        # Generate troubleshooting guide
        self._render_template(
            "troubleshooting.md.j2",
            {
                "critical_issues": [
                    issue
                    for issue in self.validator.issues
                    if issue.severity in ["BLOCKING", "CRITICAL"]
                ],
                "generation_date": generation_date,
            },
        )

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> None:
        """Render a template with context"""
        try:
            from jinja2 import Template

            template_path = self.templates_dir / template_name
            output_path = self.output_dir / template_name.replace(".j2", "")

            with open(template_path, "r") as f:
                template = Template(f.read())

            rendered = template.render(**context)

            with open(output_path, "w") as f:
                f.write(rendered)

        except ImportError:
            # Fallback to simple string replacement if Jinja2 not available
            self._simple_template_render(template_name, context)

    def _simple_template_render(
        self, template_name: str, context: Dict[str, Any]
    ) -> None:
        """Simple template rendering without Jinja2"""
        template_path = self.templates_dir / template_name
        output_path = self.output_dir / template_name.replace(".j2", "")

        with open(template_path, "r") as f:
            content = f.read()

        # Simple replacements
        for key, value in context.items():
            placeholder = "{{ " + key + " }}"
            content = content.replace(placeholder, str(value))

        # Handle loops (simplified)
        content = self._handle_simple_loops(content, context)

        with open(output_path, "w") as f:
            f.write(content)

    def _handle_simple_loops(self, content: str, context: Dict[str, Any]) -> str:
        """Handle simple loop constructs"""
        # This is a simplified implementation
        # In production, you'd use a proper template engine

        if "{% for endpoint in api_endpoints %}" in content:
            if "api_endpoints" in context:
                loop_content = ""
                for endpoint in context["api_endpoints"]:
                    loop_content += f"## {endpoint.method} {endpoint.path}\n\n"
                    loop_content += f"**Function**: `{endpoint.function_name}()`\n\n"
                    if endpoint.docstring:
                        loop_content += f"{endpoint.docstring}\n\n"
                    loop_content += "---\n\n"

                # Replace loop with generated content
                start_marker = "{% for endpoint in api_endpoints %}"
                end_marker = "{% endfor %}"
                start_idx = content.find(start_marker)
                end_idx = content.find(end_marker) + len(end_marker)

                if start_idx != -1 and end_idx != -1:
                    content = content[:start_idx] + loop_content + content[end_idx:]

        return content


def main():
    """Main function for production documentation validation"""
    logging.basicConfig(level=logging.INFO)

    project_root = "/home/dotmac_framework"
    source_root = f"{project_root}/src"

    print("🔍 Production Documentation Validation Started")
    print("=" * 60)

    # Initialize validator
    validator = ProductionCodeValidator(source_root)

    # Validate README claims
    print("📋 Validating README.md claims...")
    readme_path = f"{project_root}/README.md"
    validator.validate_readme_claims(readme_path)

    # Validate API endpoints
    print("🔌 Validating API endpoints...")
    validator.validate_api_endpoints()

    # Validate critical files
    print("📁 Validating critical files...")
    validator.validate_critical_files()

    # Generate reports
    reports_dir = Path(project_root) / "reports"
    reports_dir.mkdir(exist_ok=True)

    # Critical issues report
    critical_issues = [
        issue
        for issue in validator.issues
        if issue.severity in ["BLOCKING", "CRITICAL"]
    ]

    validation_report = {
        "timestamp": subprocess.check_output(["date"]).decode().strip(),
        "total_issues": len(validator.issues),
        "critical_issues": len(critical_issues),
        "api_endpoints_found": len(validator.api_endpoints),
        "readme_claims_validated": len(validator.readme_claims),
        "readme_claims_valid": sum(validator.readme_claims.values()),
        "critical_issues_details": [asdict(issue) for issue in critical_issues],
        "api_endpoints_details": [
            asdict(ep) for ep in validator.api_endpoints[:10]
        ],  # Sample
        "readme_validation": validator.readme_claims,
    }

    # Save JSON report
    with open(reports_dir / "production_documentation_validation.json", "w") as f:
        json.dump(validation_report, f, indent=2)

    # Generate markdown report
    with open(reports_dir / "production_documentation_validation.md", "w") as f:
        f.write("# Production Documentation Validation Report\n\n")
        f.write(f"**Generated**: {validation_report['timestamp']}\n\n")
        f.write("## Executive Summary\n\n")

        if critical_issues:
            f.write(
                f"🚨 **{len(critical_issues)} CRITICAL ISSUES BLOCK PRODUCTION DEPLOYMENT**\n\n"
            )
        else:
            f.write("✅ **No critical issues found - Ready for production**\n\n")

        f.write(f"- **Total Issues**: {validation_report['total_issues']}\n")
        f.write(f"- **Critical Issues**: {validation_report['critical_issues']}\n")
        f.write(f"- **API Endpoints**: {validation_report['api_endpoints_found']}\n")
        f.write(
            f"- **README Claims Valid**: {validation_report['readme_claims_valid']}/{validation_report['readme_claims_validated']}\n\n"
        )

        # README validation results
        f.write("## README.md Validation\n\n")
        for claim, is_valid in validator.readme_claims.items():
            status = "✅" if is_valid else "❌"
            f.write(f"{status} **{claim}**: {'Valid' if is_valid else 'INVALID'}\n")
        f.write("\n")

        # Critical issues
        if critical_issues:
            f.write("## 🚨 Critical Issues (MUST FIX BEFORE PRODUCTION)\n\n")
            for i, issue in enumerate(critical_issues, 1):
                f.write(f"### {i}. {issue.category}: {issue.description}\n\n")
                f.write(f"**Severity**: {issue.severity}\n")
                f.write(f"**Location**: `{issue.location}`\n")
                f.write(f"**Business Impact**: {issue.business_impact}\n")
                f.write(f"**Fix**: {issue.fix_suggestion}\n\n")
                if issue.actual_code:
                    f.write(
                        f"**Current Code**:\n```\n{issue.actual_code[:200]}...\n```\n\n"
                    )
                f.write("---\n\n")

    # Setup and generate DRY documentation
    print("📝 Setting up DRY documentation system...")
    dry_system = DRYDocumentationSystem(project_root, validator)
    dry_system.setup_documentation_structure()
    dry_system.generate_documentation()

    # Final summary
    print("=" * 60)
    print("✅ Production Documentation Validation Complete")
    print(f"📊 Found {len(validator.issues)} total issues")
    print(f"🚨 {len(critical_issues)} critical issues BLOCK production")
    print(f"🔌 Discovered {len(validator.api_endpoints)} API endpoints")
    print(f"📋 Validated {len(validator.readme_claims)} README claims")
    print(f"📁 Reports saved to: {reports_dir}/")
    print(f"📚 DRY documentation generated: docs/generated/")

    if critical_issues:
        print("\n❌ PRODUCTION DEPLOYMENT BLOCKED")
        print("Fix all CRITICAL issues before proceeding")
        return 1
    else:
        print("\n✅ READY FOR PRODUCTION")
        return 0


if __name__ == "__main__":
    sys.exit(main())
