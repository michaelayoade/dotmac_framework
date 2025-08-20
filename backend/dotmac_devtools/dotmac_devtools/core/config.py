"""
Core configuration management for DotMac Developer Tools.
"""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, validator


class TemplateConfig(BaseModel):
    """Template configuration settings."""

    custom_path: Path = Field(default_factory=lambda: Path.home() / ".dotmac" / "templates")
    default_language: str = Field("python", description="Default programming language")
    cache_enabled: bool = Field(True, description="Enable template caching")
    auto_update: bool = Field(True, description="Auto-update templates")


class SecurityConfig(BaseModel):
    """Security configuration for zero-trust model."""

    enforce_mtls: bool = Field(True, description="Enforce mutual TLS")
    cert_authority: str = Field("vault", description="Certificate authority provider")
    policy_enforcement: str = Field("strict", description="Policy enforcement mode")
    default_cert_validity: int = Field(90, description="Default certificate validity in days")
    service_mesh_provider: str = Field("istio", description="Service mesh provider")


class PortalConfig(BaseModel):
    """Developer portal configuration."""

    default_domain: str = Field("developer.local", description="Default portal domain")
    auth_provider: str = Field("auth0", description="Authentication provider")
    analytics_provider: str = Field("mixpanel", description="Analytics provider")
    support_integration: str = Field("zendesk", description="Support system integration")
    approval_workflow: str = Field("automatic", description="Partner approval workflow")


class DefaultsConfig(BaseModel):
    """Default settings for generated projects."""

    author: str = Field("DotMac Team", description="Default author name")
    license: str = Field("MIT", description="Default license")
    python_version: str = Field("3.11", description="Default Python version")
    docker_registry: str = Field("docker.io", description="Default Docker registry")
    git_provider: str = Field("github", description="Default Git provider")


class SDKConfig(BaseModel):
    """SDK generation configuration."""

    supported_languages: list[str] = Field(
        default=["python", "typescript", "go", "java", "csharp"],
        description="Supported programming languages"
    )
    default_output_dir: str = Field("./sdk", description="Default SDK output directory")
    include_examples: bool = Field(True, description="Include example code in SDKs")
    include_tests: bool = Field(True, description="Include test files in SDKs")
    async_by_default: bool = Field(True, description="Generate async SDKs by default")


class GeneratorConfig(BaseModel):
    """Code generation configuration."""

    auto_format: bool = Field(True, description="Auto-format generated code")
    run_tests: bool = Field(True, description="Run tests after generation")
    git_init: bool = Field(True, description="Initialize Git repository")
    create_venv: bool = Field(True, description="Create virtual environment")
    install_deps: bool = Field(True, description="Install dependencies")


class DevToolsConfig(BaseModel):
    """Main configuration for DotMac Developer Tools."""

    # Core settings
    workspace_path: Path = Field(default_factory=lambda: Path.cwd())
    log_level: str = Field("INFO", description="Logging level")
    debug: bool = Field(False, description="Enable debug mode")

    # Component configurations
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    templates: TemplateConfig = Field(default_factory=TemplateConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    portal: PortalConfig = Field(default_factory=PortalConfig)
    sdk: SDKConfig = Field(default_factory=SDKConfig)
    generator: GeneratorConfig = Field(default_factory=GeneratorConfig)

    # Environment-specific settings
    environment: str = Field("development", description="Current environment")
    tenant_id: str | None = Field(None, description="Tenant identifier")

    @validator('workspace_path', pre=True)
    def validate_workspace_path(cls, v):
        """Validate and expand workspace path."""
        if isinstance(v, str):
            return Path(v).expanduser().resolve()
        return v

    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    class Config:
        env_prefix = "DOTMAC_"
        case_sensitive = False


def load_config(config_path: str | Path | None = None) -> DevToolsConfig:
    """Load configuration from file or environment."""

    # Default config paths to check
    default_paths = [
        Path.cwd() / "dotmac.yaml",
        Path.cwd() / "dotmac.yml",
        Path.home() / ".dotmac" / "config.yaml",
        Path.home() / ".dotmac" / "config.yml",
    ]

    config_data = {}

    # Try to load from specified path or default paths
    config_file = None
    if config_path:
        config_file = Path(config_path)
    else:
        for path in default_paths:
            if path.exists():
                config_file = path
                break

    if config_file and config_file.exists():
        try:
            with open(config_file) as f:
                config_data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Failed to load config from {config_file}: {e}")

    # Create configuration with environment variable overrides
    return DevToolsConfig(**config_data)


def save_config(config: DevToolsConfig, config_path: str | Path | None = None):
    """Save configuration to file."""

    if config_path is None:
        config_dir = Path.home() / ".dotmac"
        config_dir.mkdir(exist_ok=True)
        config_path = config_dir / "config.yaml"
    else:
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict and save
    config_dict = config.dict(exclude_none=True)

    with open(config_path, 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)


def get_template_path(template_name: str, config: DevToolsConfig | None = None) -> Path:
    """Get the path to a specific template."""

    if config is None:
        config = load_config()

    # Check custom templates first
    custom_template_path = config.templates.custom_path / template_name
    if custom_template_path.exists():
        return custom_template_path

    # Check built-in templates
    builtin_template_path = Path(__file__).parent.parent / "templates" / template_name
    if builtin_template_path.exists():
        return builtin_template_path

    raise FileNotFoundError(f"Template '{template_name}' not found")


def validate_environment() -> dict[str, Any]:
    """Validate the development environment."""

    validation_results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "info": {}
    }

    # Check Python version
    import sys
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    if sys.version_info < (3, 10):
        validation_results["errors"].append(
            f"Python 3.10+ required, found {python_version}"
        )
        validation_results["valid"] = False
    else:
        validation_results["info"]["python_version"] = python_version

    # Check required tools
    required_tools = ["git", "docker"]
    for tool in required_tools:
        import subprocess
        try:
            result = subprocess.run([tool, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                validation_results["info"][f"{tool}_version"] = result.stdout.split('\n')[0]
            else:
                validation_results["warnings"].append(f"{tool} not found or not working")
        except FileNotFoundError:
            validation_results["warnings"].append(f"{tool} not found in PATH")

    # Check workspace
    cwd = Path.cwd()
    if not cwd.is_dir():
        validation_results["errors"].append("Current directory is not accessible")
        validation_results["valid"] = False

    if not os.access(cwd, os.W_OK):
        validation_results["errors"].append("Current directory is not writable")
        validation_results["valid"] = False

    return validation_results


# Create default config instance
default_config = DevToolsConfig()
