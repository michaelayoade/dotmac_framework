"""
Configuration Documentation Generator
Auto-generates documentation for environment variables and OpenBao secrets
"""

import json
import os
from dataclasses import dataclass
from typing import Any, Optional

from dotmac_shared.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ConfigVariable:
    """Represents a configuration variable"""

    name: str
    description: str
    required: bool
    default_value: Optional[str]
    environment: str
    category: str
    example: Optional[str]
    validation_rules: Optional[dict[str, Any]]


class ConfigDocumentationGenerator:
    """
    Generates comprehensive documentation for environment variables
    and OpenBao secrets used in the application.
    """

    def __init__(self):
        self.config_vars: list[ConfigVariable] = []
        self._load_config_definitions()

    def _load_config_definitions(self) -> None:
        """Load configuration variable definitions"""

        # Core infrastructure variables
        infrastructure_vars = [
            ConfigVariable(
                name="ENVIRONMENT",
                description="Application environment (development, staging, production)",
                required=True,
                default_value=None,
                environment="all",
                category="infrastructure",
                example="production",
                validation_rules={"allowed_values": ["development", "staging", "production"]},
            ),
            ConfigVariable(
                name="DATABASE_URL",
                description="PostgreSQL database connection URL",
                required=True,
                default_value=None,
                environment="all",
                category="database",
                example="postgresql://user:pass@host:5432/dbname",
                validation_rules={"pattern": "postgresql://.*"},
            ),
            ConfigVariable(
                name="REDIS_URL",
                description="Redis cache connection URL",
                required=True,
                default_value=None,
                environment="all",
                category="cache",
                example="redis://localhost:6379",
                validation_rules={"pattern": "redis://.*"},
            ),
        ]

        # OpenBao/Vault variables
        openbao_vars = [
            ConfigVariable(
                name="OPENBAO_URL",
                description="OpenBao/Vault server URL",
                required=False,
                default_value="https://vault.local",
                environment="production",
                category="secrets",
                example="https://vault.yourdomain.com",
                validation_rules={"pattern": "https://.*"},
            ),
            ConfigVariable(
                name="OPENBAO_TOKEN",
                description="OpenBao/Vault authentication token",
                required=False,
                default_value=None,
                environment="production",
                category="secrets",
                example="hvs.CAES...",
                validation_rules={"min_length": 20},
            ),
            ConfigVariable(
                name="VAULT_TOKEN",
                description="Vault authentication token (legacy support)",
                required=False,
                default_value=None,
                environment="production",
                category="secrets",
                example="hvs.CAES...",
                validation_rules={"min_length": 20},
            ),
        ]

        # Security variables
        security_vars = [
            ConfigVariable(
                name="JWT_SECRET",
                description="JWT token signing secret",
                required=True,
                default_value="dev-jwt-secret-change-in-production",
                environment="all",
                category="security",
                example="your-64-character-secret-key",
                validation_rules={"min_length": 32},
            ),
            ConfigVariable(
                name="ENCRYPTION_KEY",
                description="Data encryption key for sensitive data",
                required=True,
                default_value="dev-encryption-key-change-in-production",
                environment="all",
                category="security",
                example="your-32-character-encryption-key",
                validation_rules={"min_length": 32},
            ),
            ConfigVariable(
                name="WEBHOOK_SECRET",
                description="Secret for validating webhook signatures",
                required=False,
                default_value="dev-webhook-secret",
                environment="production",
                category="security",
                example="your-webhook-secret-key",
                validation_rules={"min_length": 20},
            ),
        ]

        # Application variables
        app_vars = [
            ConfigVariable(
                name="APP_VERSION",
                description="Application version for tracking",
                required=False,
                default_value="1.0.0",
                environment="all",
                category="application",
                example="2.1.0",
                validation_rules={"pattern": r"\d+\.\d+\.\d+"},
            ),
            ConfigVariable(
                name="STRICT_PROD_BASELINE",
                description="Enable strict production validation",
                required=False,
                default_value="false",
                environment="production",
                category="application",
                example="true",
                validation_rules={"allowed_values": ["true", "false"]},
            ),
            ConfigVariable(
                name="ADMIN_EMAIL",
                description="Administrator email for system notifications",
                required=False,
                default_value=None,
                environment="production",
                category="application",
                example="admin@yourdomain.com",
                validation_rules={"pattern": r".+@.+\..+"},
            ),
        ]

        # External service variables
        external_vars = [
            ConfigVariable(
                name="SMTP_HOST",
                description="SMTP server hostname",
                required=False,
                default_value=None,
                environment="production",
                category="external",
                example="smtp.gmail.com",
                validation_rules=None,
            ),
            ConfigVariable(
                name="SMTP_PORT",
                description="SMTP server port",
                required=False,
                default_value="587",
                environment="production",
                category="external",
                example="587",
                validation_rules={"pattern": r"\d+"},
            ),
            ConfigVariable(
                name="CORS_ORIGINS",
                description="Allowed CORS origins for API access",
                required=False,
                default_value=None,
                environment="production",
                category="security",
                example='["https://admin.yourdomain.com", "https://api.yourdomain.com"]',
                validation_rules=None,
            ),
        ]

        # Combine all variable definitions
        self.config_vars = infrastructure_vars + openbao_vars + security_vars + app_vars + external_vars

    def generate_env_documentation(self, output_format: str = "markdown") -> str:
        """
        Generate comprehensive environment variable documentation.

        Args:
            output_format: Output format ("markdown" or "json")

        Returns:
            Generated documentation as string
        """

        if output_format == "markdown":
            return self._generate_markdown_docs()
        elif output_format == "json":
            return self._generate_json_docs()
        else:
            raise ValueError(f"Unsupported format: {output_format}")

    def _generate_markdown_docs(self) -> str:
        """Generate Markdown documentation"""

        docs = [
            "# Environment Variables Configuration\n",
            "## Overview\n",
            "This document describes all environment variables used by the DotMac platform.\n\n",
            "## Variable Categories\n",
        ]

        # Group variables by category
        categories = {}
        for var in self.config_vars:
            if var.category not in categories:
                categories[var.category] = []
            categories[var.category].append(var)

        # Generate section for each category
        for category, vars_list in categories.items():
            docs.append(f"### {category.title()} Variables\n")
            docs.append("| Variable | Description | Required | Default | Environment | Example |")
            docs.append("|----------|-------------|----------|---------|-------------|---------|")

            for var in vars_list:
                required = "✅" if var.required else "❌"
                default = var.default_value or "None"
                example = var.example or "N/A"

                docs.append(
                    "| "
                    f"`{var.name}` | {var.description} | {required} | "
                    f"`{default}` | {var.environment} | `{example}` |"
                )

            docs.append("")

        # Add configuration examples
        docs.append("## Configuration Examples\n")

        # Development example
        docs.append("### Development Environment\n")
        docs.append("```bash")
        for var in self.config_vars:
            if var.environment in ["all", "development"] and var.default_value:
                docs.append(f"export {var.name}={var.default_value}")
        docs.append("```\n")

        # Production example
        docs.append("### Production Environment\n")
        docs.append("```bash")
        for var in self.config_vars:
            if var.environment in ["all", "production"]:
                value = var.example or var.default_value or "YOUR_VALUE_HERE"
                docs.append(f"export {var.name}={value}")
        docs.append("```\n")

        # Add OpenBao configuration section
        docs.append("## OpenBao Integration\n")
        docs.append("For production deployments, secrets should be managed through OpenBao:\n")
        docs.append("```bash")
        docs.append("# Required OpenBao configuration")
        docs.append("export OPENBAO_URL=https://vault.yourdomain.com")
        docs.append("export OPENBAO_TOKEN=your-openbao-token")
        docs.append("")
        docs.append("# Application will automatically retrieve secrets from:")
        docs.append("# - auth/jwt-secret")
        docs.append("# - database/app-password")
        docs.append("# - external/stripe-secret")
        docs.append("```\n")

        return "\n".join(docs)

    def _generate_json_docs(self) -> str:
        """Generate JSON documentation"""

        docs = {
            "metadata": {
                "generated_at": "2025-09-05T08:34:44+02:00",
                "version": "1.0",
                "description": "DotMac Platform Environment Variables Documentation",
            },
            "categories": {},
            "examples": {"development": {}, "production": {}},
        }

        # Group variables by category
        for var in self.config_vars:
            if var.category not in docs["categories"]:
                docs["categories"][var.category] = []

            docs["categories"][var.category].append(
                {
                    "name": var.name,
                    "description": var.description,
                    "required": var.required,
                    "default_value": var.default_value,
                    "environment": var.environment,
                    "example": var.example,
                    "validation_rules": var.validation_rules,
                }
            )

        # Generate examples
        for var in self.config_vars:
            if var.environment in ["all", "development"] and var.default_value:
                docs["examples"]["development"][var.name] = var.default_value

            if var.environment in ["all", "production"]:
                value = var.example or var.default_value or "YOUR_VALUE_HERE"
                docs["examples"]["production"][var.name] = value

        return json.dumps(docs, indent=2)

    def validate_current_config(self) -> dict[str, Any]:
        """
        Validate current environment configuration against defined variables.

        Returns:
            Validation results with missing/invalid variables
        """

        results = {
            "timestamp": "2025-09-05T08:34:44+02:00",
            "total_variables": len(self.config_vars),
            "missing_required": [],
            "invalid_values": [],
            "using_defaults": [],
            "configured_correctly": [],
        }

        for var in self.config_vars:
            current_value = os.getenv(var.name)

            if var.required and not current_value:
                results["missing_required"].append({"variable": var.name, "description": var.description})
            elif current_value and var.validation_rules:
                # Validate value against rules
                if not self._validate_value(current_value, var.validation_rules):
                    results["invalid_values"].append(
                        {"variable": var.name, "current_value": current_value, "rules": var.validation_rules}
                    )
            elif not current_value and var.default_value:
                results["using_defaults"].append({"variable": var.name, "default_value": var.default_value})
            elif current_value:
                results["configured_correctly"].append({"variable": var.name, "value_set": True})

        return results

    def _validate_value(self, value: str, rules: dict[str, Any]) -> bool:
        """Validate a value against validation rules"""

        if "pattern" in rules:
            import re

            if not re.match(rules["pattern"], value):
                return False

        if "min_length" in rules:
            if len(value) < rules["min_length"]:
                return False

        if "allowed_values" in rules:
            if value not in rules["allowed_values"]:
                return False

        return True

    def export_env_template(self, output_path: str) -> None:
        """
        Export environment template file (.env.example)

        Args:
            output_path: Path to save the template file
        """

        template_lines = [
            "# DotMac Platform Environment Configuration",
            "# Copy this file to .env and update values for your environment",
            "",
            "# Generated on: 2025-09-05",
            "",
        ]

        # Group by category
        categories = {}
        for var in self.config_vars:
            if var.category not in categories:
                categories[var.category] = []
            categories[var.category].append(var)

        for category, vars_list in categories.items():
            template_lines.append(f"# {category.upper()} CONFIGURATION")
            template_lines.append("")

            for var in vars_list:
                if var.example:
                    template_lines.append(f"{var.name}={var.example}")
                elif var.default_value:
                    template_lines.append(f"{var.name}={var.default_value}")
                else:
                    template_lines.append(f"{var.name}=YOUR_VALUE_HERE")

                # Add comment with description
                template_lines.append(f"# {var.description}")
                if var.required:
                    template_lines.append("# REQUIRED")
                template_lines.append("")

        # Write to file
        with open(output_path, "w") as f:
            f.write("\n".join(template_lines))

        logger.info(f"Environment template exported to: {output_path}")


# Convenience functions
def generate_env_docs(format_type: str = "markdown") -> str:
    """Generate environment variable documentation"""
    generator = ConfigDocumentationGenerator()
    return generator.generate_env_documentation(format_type)


def validate_current_environment() -> dict[str, Any]:
    """Validate current environment configuration"""
    generator = ConfigDocumentationGenerator()
    return generator.validate_current_config()


def export_env_template(output_path: str = ".env.example") -> None:
    """Export environment template file"""
    generator = ConfigDocumentationGenerator()
    generator.export_env_template(output_path)
