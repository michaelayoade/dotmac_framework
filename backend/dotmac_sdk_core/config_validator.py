"""
Early configuration validation for all DotMac services.
Validates environment variables and configuration at startup.
"""

import os
import sys
import logging
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse
import socket

from pydantic import BaseSettings, Field, validator, ValidationError
from pydantic_settings import SettingsConfigDict

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Deployment environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class ValidationLevel(str, Enum):
    """Configuration validation levels."""
    STRICT = "strict"  # Fail on any issue
    NORMAL = "normal"  # Fail on critical issues only
    LENIENT = "lenient"  # Log warnings but don't fail


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    info: Dict[str, Any]


class BaseServiceConfig(BaseSettings):
    """
    Base configuration for all DotMac services.
    Provides early validation of critical settings.
    """
    
    # Service identification
    service_name: str = Field(
        ...,
        description="Service name (required)",
        min_length=1,
        max_length=50
    )
    service_version: str = Field(
        default="1.0.0",
        description="Service version",
        regex=r'^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$'
    )
    
    # Environment
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Deployment environment"
    )
    debug: bool = Field(
        default=False,
        description="Debug mode"
    )
    
    # Network
    host: str = Field(
        default="0.0.0.0",
        description="Host to bind"
    )
    port: int = Field(
        default=8000,
        description="Port to bind",
        ge=1,
        le=65535
    )
    
    # Database
    database_url: str = Field(
        ...,
        description="PostgreSQL connection URL (required)",
        min_length=1
    )
    database_pool_size: int = Field(
        default=20,
        description="Database connection pool size",
        ge=1,
        le=100
    )
    database_max_overflow: int = Field(
        default=10,
        description="Max overflow connections",
        ge=0,
        le=50
    )
    
    # Redis
    redis_url: str = Field(
        ...,
        description="Redis connection URL (required)",
        min_length=1
    )
    redis_max_connections: int = Field(
        default=50,
        description="Redis max connections",
        ge=1,
        le=500
    )
    
    # Security
    secret_key: str = Field(
        ...,
        description="Secret key for JWT/encryption (required)",
        min_length=32
    )
    cors_origins: List[str] = Field(
        default_factory=list,
        description="Allowed CORS origins"
    )
    
    # Observability
    signoz_endpoint: Optional[str] = Field(
        default=None,
        description="SignOz/OTLP endpoint"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level",
        regex=r'^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$'
    )
    
    # Performance
    workers: Optional[int] = Field(
        default=None,
        description="Number of worker processes",
        ge=1,
        le=32
    )
    timeout_keep_alive: int = Field(
        default=5,
        description="Keep-alive timeout in seconds",
        ge=0,
        le=300
    )
    graceful_timeout: int = Field(
        default=30,
        description="Graceful shutdown timeout",
        ge=0,
        le=300
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"  # Allow service-specific extras
    )
    
    @validator("environment")
    def validate_environment(cls, v, values):
        """Validate environment settings."""
        if v == Environment.PRODUCTION:
            # Production must not have debug enabled
            if values.get("debug"):
                raise ValueError("Debug must be disabled in production")
        return v
    
    @validator("database_url")
    def validate_database_url(cls, v):
        """Validate PostgreSQL connection URL."""
        try:
            result = urlparse(v)
            if not result.scheme.startswith("postgresql"):
                raise ValueError("Database URL must be PostgreSQL")
            if not result.hostname:
                raise ValueError("Database hostname missing")
            if not result.path or result.path == "/":
                raise ValueError("Database name missing")
            return v
        except Exception as e:
            raise ValueError(f"Invalid database URL: {e}")
    
    @validator("redis_url")
    def validate_redis_url(cls, v):
        """Validate Redis connection URL."""
        try:
            result = urlparse(v)
            if not result.scheme.startswith("redis"):
                raise ValueError("Redis URL must start with redis://")
            if not result.hostname:
                raise ValueError("Redis hostname missing")
            return v
        except Exception as e:
            raise ValueError(f"Invalid Redis URL: {e}")
    
    @validator("secret_key")
    def validate_secret_key(cls, v, values):
        """Validate secret key security."""
        env = values.get("environment")
        
        # Check for weak keys
        weak_keys = [
            "secret", "change-me", "dev-secret", "test-secret",
            "12345678901234567890123456789012"
        ]
        
        if any(weak in v.lower() for weak in weak_keys):
            if env == Environment.PRODUCTION:
                raise ValueError("Weak secret key detected in production!")
            elif env == Environment.STAGING:
                logger.warning("Weak secret key detected in staging")
        
        # Check entropy (basic check)
        if len(set(v)) < 10:  # Less than 10 unique characters
            if env in [Environment.PRODUCTION, Environment.STAGING]:
                raise ValueError("Secret key has insufficient entropy")
        
        return v
    
    @validator("cors_origins")
    def validate_cors_origins(cls, v, values):
        """Validate CORS configuration."""
        env = values.get("environment")
        
        if env == Environment.PRODUCTION:
            # No wildcards in production
            if "*" in v:
                raise ValueError("Wildcard CORS origin not allowed in production")
            
            # Validate each origin
            for origin in v:
                parsed = urlparse(origin)
                if not parsed.scheme:
                    raise ValueError(f"CORS origin missing scheme: {origin}")
                if parsed.scheme == "http" and "localhost" not in parsed.hostname:
                    logger.warning(f"Insecure HTTP origin in production: {origin}")
        
        return v
    
    def validate_connectivity(self) -> ValidationResult:
        """
        Validate network connectivity to dependencies.
        Returns validation result with connectivity status.
        """
        errors = []
        warnings = []
        info = {}
        
        # Check database connectivity
        try:
            db_url = urlparse(self.database_url)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((db_url.hostname, db_url.port or 5432))
            sock.close()
            
            if result == 0:
                info["database"] = "reachable"
            else:
                errors.append(f"Cannot reach database at {db_url.hostname}:{db_url.port or 5432}")
                info["database"] = "unreachable"
        except Exception as e:
            warnings.append(f"Database connectivity check failed: {e}")
            info["database"] = "unknown"
        
        # Check Redis connectivity
        try:
            redis_url = urlparse(self.redis_url)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((redis_url.hostname, redis_url.port or 6379))
            sock.close()
            
            if result == 0:
                info["redis"] = "reachable"
            else:
                errors.append(f"Cannot reach Redis at {redis_url.hostname}:{redis_url.port or 6379}")
                info["redis"] = "unreachable"
        except Exception as e:
            warnings.append(f"Redis connectivity check failed: {e}")
            info["redis"] = "unknown"
        
        # Check SignOz if configured
        if self.signoz_endpoint:
            try:
                # Parse gRPC endpoint
                if "://" in self.signoz_endpoint:
                    endpoint_url = urlparse(self.signoz_endpoint)
                    host = endpoint_url.hostname
                    port = endpoint_url.port or 4317
                else:
                    parts = self.signoz_endpoint.split(":")
                    host = parts[0]
                    port = int(parts[1]) if len(parts) > 1 else 4317
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result == 0:
                    info["signoz"] = "reachable"
                else:
                    warnings.append(f"Cannot reach SignOz at {host}:{port}")
                    info["signoz"] = "unreachable"
            except Exception as e:
                warnings.append(f"SignOz connectivity check failed: {e}")
                info["signoz"] = "unknown"
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def validate_all(
        self,
        level: ValidationLevel = ValidationLevel.NORMAL,
        check_connectivity: bool = True
    ) -> ValidationResult:
        """
        Perform complete validation of configuration.
        
        Args:
            level: Validation strictness level
            check_connectivity: Whether to check network connectivity
            
        Returns:
            ValidationResult with all findings
        """
        errors = []
        warnings = []
        info = {
            "service": self.service_name,
            "version": self.service_version,
            "environment": self.environment.value,
            "validation_level": level.value
        }
        
        # Basic validation (Pydantic handles this)
        try:
            self.dict()  # Trigger validation
        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(x) for x in error["loc"])
                msg = f"{field}: {error['msg']}"
                if level == ValidationLevel.STRICT:
                    errors.append(msg)
                elif level == ValidationLevel.NORMAL and error["type"] != "value_error":
                    errors.append(msg)
                else:
                    warnings.append(msg)
        
        # Additional validations
        
        # Check for required environment variables in production
        if self.environment == Environment.PRODUCTION:
            required_env_vars = [
                "DATABASE_URL",
                "REDIS_URL",
                "SECRET_KEY"
            ]
            
            for var in required_env_vars:
                if not os.environ.get(var):
                    errors.append(f"Required environment variable not set: {var}")
        
        # Validate workers based on CPU
        if self.workers:
            cpu_count = os.cpu_count() or 2
            recommended_workers = min(cpu_count * 2, 16)
            
            if self.workers > recommended_workers:
                warnings.append(
                    f"Workers ({self.workers}) exceeds recommended "
                    f"({recommended_workers}) for {cpu_count} CPUs"
                )
        
        # Check connectivity if requested
        if check_connectivity:
            conn_result = self.validate_connectivity()
            errors.extend(conn_result.errors)
            warnings.extend(conn_result.warnings)
            info.update(conn_result.info)
        
        # Determine overall validity
        is_valid = True
        if level == ValidationLevel.STRICT:
            is_valid = len(errors) == 0 and len(warnings) == 0
        elif level == ValidationLevel.NORMAL:
            is_valid = len(errors) == 0
        # LENIENT always passes but logs issues
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            info=info
        )


def validate_service_config(
    config_class: Type[BaseServiceConfig] = BaseServiceConfig,
    service_name: Optional[str] = None,
    fail_fast: bool = True,
    check_connectivity: bool = True
) -> BaseServiceConfig:
    """
    Validate service configuration at startup.
    
    Args:
        config_class: Configuration class to use
        service_name: Override service name
        fail_fast: Exit on validation failure
        check_connectivity: Check network connectivity
        
    Returns:
        Validated configuration instance
        
    Raises:
        SystemExit: If validation fails and fail_fast=True
    """
    try:
        # Set service name if provided
        if service_name:
            os.environ["SERVICE_NAME"] = service_name
        
        # Load configuration
        config = config_class()
        
        # Determine validation level based on environment
        if config.environment == Environment.PRODUCTION:
            level = ValidationLevel.STRICT
        elif config.environment == Environment.STAGING:
            level = ValidationLevel.NORMAL
        else:
            level = ValidationLevel.LENIENT
        
        # Validate
        result = config.validate_all(
            level=level,
            check_connectivity=check_connectivity
        )
        
        # Log results
        logger.info(f"Configuration validation for {config.service_name}:")
        logger.info(f"  Environment: {config.environment.value}")
        logger.info(f"  Validation level: {level.value}")
        
        for warning in result.warnings:
            logger.warning(f"  ⚠ {warning}")
        
        for error in result.errors:
            logger.error(f"  ✗ {error}")
        
        if result.is_valid:
            logger.info("  ✓ Configuration valid")
            
            # Log connectivity status
            if check_connectivity:
                for service, status in result.info.items():
                    if service in ["database", "redis", "signoz"]:
                        emoji = "✓" if status == "reachable" else "✗"
                        logger.info(f"  {emoji} {service}: {status}")
        else:
            logger.error("  ✗ Configuration invalid")
            
            if fail_fast:
                sys.exit(1)
        
        return config
        
    except ValidationError as e:
        logger.error(f"Configuration validation failed: {e}")
        if fail_fast:
            sys.exit(1)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during validation: {e}")
        if fail_fast:
            sys.exit(1)
        raise


# CLI for testing configuration
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate service configuration")
    parser.add_argument("--service", help="Service name")
    parser.add_argument("--env-file", help="Environment file to load")
    parser.add_argument("--no-connectivity", action="store_true", help="Skip connectivity checks")
    parser.add_argument("--strict", action="store_true", help="Use strict validation")
    
    args = parser.parse_args()
    
    # Load env file if specified
    if args.env_file:
        from dotenv import load_dotenv
        load_dotenv(args.env_file)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Validate
    config = validate_service_config(
        service_name=args.service,
        check_connectivity=not args.no_connectivity
    )
    
    # Print configuration (sanitized)
    print("\nLoaded configuration:")
    for key, value in config.dict().items():
        if "secret" in key.lower() or "password" in key.lower():
            print(f"  {key}: ***REDACTED***")
        else:
            print(f"  {key}: {value}")