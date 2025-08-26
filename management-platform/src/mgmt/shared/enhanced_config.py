"""
Enhanced Configuration Management for DotMac Management Platform.
Provides enterprise-grade configuration with security features matching ISP Framework.
"""

import os
import logging
from functools import lru_cache
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Import security components from ISP Framework (creating unified architecture)
from .security.secrets_manager import get_secrets_manager, SecretType, init_secrets_manager
from .security.config_encryption import get_config_encryption, init_config_encryption
from .security.config_audit import get_config_audit, ChangeType, ChangeSource, init_config_audit
from .security.config_backup import get_config_backup, BackupType, init_config_backup
from .security.config_hotreload import get_config_hotreload, init_config_hotreload
from .security.secure_config_validator import get_secure_validator, ComplianceFramework, init_secure_validator

logger = logging.getLogger(__name__)


class ManagementPlatformSettings(BaseSettings):
    """
    Enhanced Management Platform settings with enterprise security features.
    Provides unified configuration management across DotMac ecosystem.
    """
    
    model_config = SettingsConfigDict(
        env_file=[".env", ".env.local"],
        env_file_encoding="utf-8", 
        case_sensitive=False,
        extra="ignore"
    )
    
    # Core application settings
    app_name: str = "DotMac Management Platform"
    app_version: str = "1.0.0"
    service_name: str = Field(
        default="mgmt-platform",
        description="Service name for distributed tracing and logging"
    )
    
    # Environment configuration with strict validation
    environment: str = Field(
        default="development",
        pattern="^(development|staging|production)$",
        description="Deployment environment - must be development, staging, or production"
    )
    
    # Security-first debug configuration
    debug: bool = Field(
        default=False,
        description="Debug mode - automatically disabled in production"
    )
    
    # Server configuration
    host: str = Field(
        default="127.0.0.1",  # More secure default
        description="Host to bind - use 127.0.0.1 for local, 0.0.0.0 for external"
    )
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Port to bind"
    )
    workers: int = Field(
        default=1,
        ge=1,
        le=32,
        description="Number of worker processes"
    )
    
    # API configuration with environment awareness
    api_v1_prefix: str = "/api/v1"
    docs_url: Optional[str] = Field(
        default="/docs",
        description="API docs URL - disabled in production for security"
    )
    redoc_url: Optional[str] = Field(
        default="/redoc",
        description="ReDoc URL - disabled in production for security"
    )
    openapi_url: Optional[str] = Field(
        default="/openapi.json",
        description="OpenAPI spec URL - disabled in production for security"
    )
    
    # Database configuration with security validation
    database_url: str = Field(
        default="postgresql://mgmt_user:mgmt_password@localhost:5432/mgmt_platform",
        description="Primary database URL - must use SSL in production"
    )
    database_pool_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Database connection pool size"
    )
    database_max_overflow: int = Field(
        default=30,
        ge=0,
        le=50,
        description="Max overflow connections"
    )
    
    # Redis configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    redis_max_connections: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Redis max connections"
    )
    
    # Enhanced security configuration
    secret_key: str = Field(
        default="",  # Will be loaded from secrets manager
        min_length=32,
        description="Application secret key - loaded from secure storage"
    )
    jwt_secret_key: str = Field(
        default="",  # Will be loaded from secrets manager
        min_length=32,
        description="JWT secret key - loaded from secure storage"
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15  # Reduced for security
    jwt_refresh_token_expire_days: int = 7
    
    # CORS configuration with strict defaults
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:3001,http://localhost:3002",
        description="Allowed CORS origins (comma-separated)"
    )
    
    # Trusted hosts configuration
    allowed_hosts: str = Field(
        default="localhost,127.0.0.1",
        description="Allowed host headers (comma-separated)"
    )
    
    # Multi-tenant isolation
    enable_row_level_security: bool = Field(
        default=True,
        description="Enable PostgreSQL RLS for tenant isolation"
    )
    tenant_schema_isolation: bool = Field(
        default=True,
        description="Use schema-based tenant isolation"
    )
    
    # External service configuration
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_test_mode: bool = True
    
    sendgrid_api_key: Optional[str] = None
    sendgrid_from_email: str = "noreply@dotmac.app"
    
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    
    # Cloud provider credentials (handled via OpenBao)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None
    gcp_service_account_json: Optional[str] = None
    
    # SSL/TLS configuration
    ssl_enabled: bool = Field(
        default=False,
        description="Enable HTTPS with SSL certificates"
    )
    ssl_email: Optional[str] = None
    ssl_domains: str = ""
    ssl_cert_dir: str = "/etc/ssl/dotmac-mgmt"
    
    # OpenBao secrets management
    openbao_url: str = "http://localhost:8200"
    openbao_token: Optional[str] = None
    openbao_role_id: Optional[str] = None
    openbao_secret_id: Optional[str] = None
    enable_secrets_management: bool = True
    
    # SignOz observability
    signoz_endpoint: str = "localhost:4317"
    signoz_access_token: Optional[str] = None
    enable_observability: bool = True
    
    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "json"
    log_audit_enabled: bool = True
    
    # Rate limiting configuration
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60  # Conservative for management platform
    rate_limit_burst_multiplier: int = 2
    
    # Security enhancement features
    enable_config_encryption: bool = Field(
        default=True,
        description="Enable configuration encryption for sensitive data"
    )
    enable_config_audit: bool = Field(
        default=True,
        description="Enable configuration audit logging"
    )
    enable_config_backup: bool = Field(
        default=True,
        description="Enable automated configuration backups"
    )
    enable_hot_reload: bool = Field(
        default=True,
        description="Enable configuration hot-reloading"
    )
    
    # Compliance configuration for SaaS platform
    compliance_frameworks: str = Field(
        default="soc2,iso27001,gdpr,pci_dss",  # More comprehensive for SaaS
        description="Comma-separated list of compliance frameworks to enforce"
    )
    
    # Tenant management specific settings
    max_tenants_per_instance: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Maximum tenants supported per management platform instance"
    )
    default_tenant_tier: str = Field(
        default="small",
        description="Default resource tier for new tenants"
    )
    tenant_deployment_timeout: int = Field(
        default=1800,  # 30 minutes
        ge=300,
        le=3600,
        description="Timeout for tenant deployment operations (seconds)"
    )
    
    # Kubernetes orchestration settings
    kubernetes_config_path: Optional[str] = Field(
        default=None,
        description="Path to Kubernetes config file"
    )
    kubernetes_namespace_prefix: str = Field(
        default="dotmac-tenant",
        description="Prefix for tenant namespaces"
    )
    enable_kubernetes_rbac: bool = Field(
        default=True,
        description="Enable Kubernetes RBAC for tenant isolation"
    )
    
    # Plugin licensing settings
    plugin_catalog_url: str = Field(
        default="https://catalog.dotmac.app",
        description="URL for plugin catalog service"
    )
    enable_usage_tracking: bool = Field(
        default=True,
        description="Enable plugin usage tracking for billing"
    )
    usage_reporting_interval: int = Field(
        default=3600,  # 1 hour
        ge=300,
        le=86400,
        description="Usage reporting interval in seconds"
    )
    
    # SaaS monitoring settings
    health_check_interval: int = Field(
        default=300,  # 5 minutes
        ge=60,
        le=3600,
        description="Health check interval for tenant monitoring"
    )
    sla_calculation_window: int = Field(
        default=86400,  # 24 hours
        ge=3600,
        le=604800,  # 1 week
        description="SLA calculation window in seconds"
    )
    alert_escalation_timeout: int = Field(
        default=900,  # 15 minutes
        ge=60,
        le=3600,
        description="Alert escalation timeout in seconds"
    )
    
    # Internal state (not loaded from environment)
    _secrets_loaded: bool = False
    _security_validated: bool = False
    _config_managers_initialized: bool = False
    
    def __init__(self, **kwargs):
        """Initialize enhanced settings with security features."""
        super().__init__(**kwargs)
        
        # Initialize security managers
        self._initialize_security_managers()
        
        # Load secrets from secure storage
        self._load_secrets_from_secure_storage()
        
        # Validate security configuration
        self._validate_security_configuration()
        
        # Create initial backup
        self._create_initial_backup()
        
        # Log configuration load
        self._log_configuration_load()
    
    def _initialize_security_managers(self):
        """Initialize security management components."""
        try:
            if self.enable_secrets_management:
                # Initialize secrets manager
                init_secrets_manager(
                    backend="openbao" if self.openbao_token else "local",
                    openbao_url=self.openbao_url,
                    openbao_token=self.openbao_token
                )
            
            if self.enable_config_encryption:
                # Initialize config encryption
                init_config_encryption(
                    master_key=os.getenv("CONFIG_MASTER_KEY"),
                    key_rotation_enabled=True
                )
            
            if self.enable_config_audit:
                # Initialize config audit
                init_config_audit(
                    require_approval=self.environment == "production",
                    encryption_enabled=self.enable_config_encryption
                )
            
            if self.enable_config_backup:
                # Initialize config backup
                init_config_backup(
                    backup_storage_path="/var/backups/dotmac/mgmt-platform",
                    encryption_key=os.getenv("BACKUP_ENCRYPTION_KEY")
                )
            
            if self.enable_hot_reload:
                # Initialize hot reload (will be configured by application)
                pass
            
            # Initialize secure validator
            init_secure_validator()
            
            self._config_managers_initialized = True
            logger.info("Security managers initialized successfully for Management Platform")
            
        except Exception as e:
            logger.error(f"Failed to initialize security managers: {e}")
            if self.environment == "production":
                raise  # Fail fast in production
    
    def _load_secrets_from_secure_storage(self):
        """Load sensitive configuration from secure storage."""
        if not self.enable_secrets_management:
            return
        
        try:
            secrets_manager = get_secrets_manager()
            
            # Load JWT secret key
            if not self.jwt_secret_key:
                jwt_secret = secrets_manager.get_secret("mgmt_jwt_secret_key")
                if jwt_secret:
                    self.jwt_secret_key = jwt_secret.value
                elif self.environment == "production":
                    raise ValueError("Management Platform JWT secret key not found in secure storage")
            
            # Load application secret key
            if not self.secret_key:
                app_secret = secrets_manager.get_secret("mgmt_app_secret_key")
                if app_secret:
                    self.secret_key = app_secret.value
                elif self.environment == "production":
                    raise ValueError("Management Platform application secret key not found in secure storage")
            
            # Load external service credentials
            external_services = [
                ("stripe_secret_key", "mgmt_stripe_secret_key"),
                ("stripe_webhook_secret", "mgmt_stripe_webhook_secret"),
                ("sendgrid_api_key", "mgmt_sendgrid_api_key"),
                ("twilio_auth_token", "mgmt_twilio_auth_token"),
                ("aws_secret_access_key", "mgmt_aws_secret_key"),
                ("azure_client_secret", "mgmt_azure_client_secret"),
                ("gcp_service_account_json", "mgmt_gcp_service_account")
            ]
            
            for attr_name, secret_id in external_services:
                if not getattr(self, attr_name):
                    secret = secrets_manager.get_secret(secret_id)
                    if secret:
                        setattr(self, attr_name, secret.value)
            
            self._secrets_loaded = True
            logger.info("Secrets loaded from secure storage for Management Platform")
            
        except Exception as e:
            logger.error(f"Failed to load secrets from secure storage: {e}")
            if self.environment == "production":
                raise
    
    def _validate_security_configuration(self):
        """Validate configuration using secure validator."""
        try:
            validator = get_secure_validator()
            
            # Get compliance frameworks
            frameworks = []
            if self.compliance_frameworks:
                framework_names = [f.strip() for f in self.compliance_frameworks.split(",")]
                frameworks = [ComplianceFramework(name) for name in framework_names if name]
            
            # Validate configuration
            config_dict = self.model_dump()
            result = validator.validate_configuration(
                config=config_dict,
                environment=self.environment,
                service="management-platform",
                compliance_frameworks=frameworks
            )
            
            # Handle validation results
            if not result.is_valid:
                error_msg = f"Management Platform configuration validation failed with {len(result.critical_issues)} critical and {len(result.error_issues)} error issues"
                logger.error(error_msg)
                
                # Log critical issues
                for issue in result.critical_issues:
                    logger.critical(f"CRITICAL: {issue.field_path} - {issue.message}")
                
                # Log error issues
                for issue in result.error_issues:
                    logger.error(f"ERROR: {issue.field_path} - {issue.message}")
                
                if self.environment == "production":
                    raise ValueError(error_msg)
            
            # Log warnings
            for issue in result.warning_issues:
                logger.warning(f"WARNING: {issue.field_path} - {issue.message}")
            
            self._security_validated = True
            logger.info(f"Management Platform security validation passed (score: {result.security_score:.1f}/100)")
            
        except Exception as e:
            logger.error(f"Security validation failed: {e}")
            if self.environment == "production":
                raise
    
    def _create_initial_backup(self):
        """Create initial configuration backup."""
        if not self.enable_config_backup:
            return
        
        try:
            backup_manager = get_config_backup()
            config_dict = self.model_dump()
            
            backup_id = backup_manager.create_backup(
                config_data=config_dict,
                backup_type=BackupType.SNAPSHOT,
                environments=[self.environment],
                services=["management-platform"],
                tags=["initial", "startup", "mgmt-platform"],
                created_by="system"
            )
            
            logger.info(f"Initial Management Platform configuration backup created: {backup_id}")
            
        except Exception as e:
            logger.warning(f"Failed to create initial backup: {e}")
    
    def _log_configuration_load(self):
        """Log configuration load event."""
        if not self.enable_config_audit:
            return
        
        try:
            audit = get_config_audit()
            
            audit.log_configuration_change(
                field_path="__mgmt_platform_startup__",
                old_value=None,
                new_value="configuration_loaded",
                change_type=ChangeType.ACCESS,
                source=ChangeSource.SYSTEM,
                environment=self.environment,
                service="management-platform",
                change_reason="Management Platform startup configuration load"
            )
            
        except Exception as e:
            logger.warning(f"Failed to log configuration load: {e}")
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]
    
    @property
    def allowed_hosts_list(self) -> list[str]:
        """Get allowed hosts as a list."""
        return [host.strip() for host in self.allowed_hosts.split(',') if host.strip()]
    
    @property
    def compliance_frameworks_list(self) -> list[str]:
        """Get compliance frameworks as a list."""
        return [fw.strip() for fw in self.compliance_frameworks.split(',') if fw.strip()]
    
    @model_validator(mode='after')
    def validate_management_platform_security(self):
        """Validate management platform specific security settings."""
        # Production security validation
        if self.environment == "production":
            errors = []
            
            # Debug mode must be False
            if self.debug:
                errors.append("DEBUG mode MUST be False in production")
            
            # API documentation must be disabled
            if self.docs_url or self.redoc_url or self.openapi_url:
                logger.warning("API documentation endpoints enabled in production - auto-disabling")
                # Auto-disable in production
                self.docs_url = None
                self.redoc_url = None
                self.openapi_url = None
            
            # CORS origins must not be localhost
            if any(host in self.cors_origins.lower() for host in ["localhost", "127.0.0.1"]):
                errors.append("CORS origins must not include localhost in production")
            
            # Allowed hosts must not be localhost only
            if self.allowed_hosts == "localhost,127.0.0.1":
                errors.append("Allowed hosts must be configured for production domains")
            
            # SSL should be enabled
            if not self.ssl_enabled:
                logger.warning("SSL is not enabled in production")
            
            # External services validation
            if not self.stripe_secret_key:
                errors.append("Stripe secret key is required for SaaS billing in production")
            
            if not self.sendgrid_api_key:
                errors.append("SendGrid API key is required for notifications in production")
            
            # OpenBao validation
            if "localhost" in self.openbao_url:
                errors.append("OpenBao URL should not use localhost in production")
            
            # Multi-tenant security
            if not self.enable_row_level_security:
                errors.append("Row Level Security must be enabled for multi-tenant production")
            
            if not self.tenant_schema_isolation:
                errors.append("Tenant schema isolation must be enabled in production")
            
            if errors:
                error_msg = "CRITICAL MANAGEMENT PLATFORM PRODUCTION SECURITY ISSUES:\n" + "\n".join(f"- {error}" for error in errors)
                logger.critical(error_msg)
                raise ValueError(error_msg)
        
        # Staging environment warnings
        elif self.environment == "staging":
            if self.debug:
                logger.warning("Debug mode enabled in staging environment")
        
        return self
    
    @field_validator('jwt_secret_key', 'secret_key')
    @classmethod
    def validate_secret_keys(cls, v: str, info) -> str:
        """Validate secret key strength."""
        field_name = info.field_name
        
        if not v:
            # Will be loaded from secrets manager, so this is acceptable
            return v
        
        if len(v) < 32:
            raise ValueError(f"{field_name} must be at least 32 characters long")
        
        # Check for weak secrets
        weak_patterns = ["secret", "change", "test", "demo", "default", "password", "mgmt"]
        if any(pattern in v.lower() for pattern in weak_patterns):
            logger.warning(f"Potentially weak {field_name} detected")
        
        return v
    
    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment setting."""
        valid_environments = ["development", "staging", "production"]
        if v not in valid_environments:
            raise ValueError(f"Environment must be one of: {', '.join(valid_environments)}")
        return v
    
    @field_validator('database_url')
    @classmethod
    def validate_database_url(cls, v: str, info) -> str:
        """Validate database URL security."""
        # Check for SSL in production
        if info.data.get('environment') == 'production':
            if 'sslmode=require' not in v and 'sslmode=verify' not in v:
                logger.warning("Database URL should use SSL in production")
        return v
    
    def update_setting(
        self,
        field_path: str,
        new_value: Any,
        user_id: Optional[str] = None,
        change_reason: Optional[str] = None
    ) -> bool:
        """
        Securely update a configuration setting with audit trail.
        
        Args:
            field_path: Path to the setting
            new_value: New value for the setting
            user_id: User making the change
            change_reason: Reason for the change
            
        Returns:
            True if update was successful
        """
        if not self.enable_config_audit:
            # Direct update without audit
            setattr(self, field_path, new_value)
            return True
        
        try:
            # Get current value
            old_value = getattr(self, field_path, None)
            
            # Log the change
            audit = get_config_audit()
            event_id = audit.log_configuration_change(
                field_path=field_path,
                old_value=old_value,
                new_value=new_value,
                change_type=ChangeType.UPDATE,
                source=ChangeSource.API if user_id else ChangeSource.SYSTEM,
                environment=self.environment,
                user_id=user_id,
                service="management-platform",
                change_reason=change_reason
            )
            
            # Apply the change (if not requiring approval)
            if not audit.require_approval or self.environment != "production":
                setattr(self, field_path, new_value)
                logger.info(f"Management Platform configuration updated: {field_path} (event: {event_id})")
                return True
            else:
                logger.info(f"Management Platform configuration change pending approval: {field_path} (event: {event_id})")
                return False
            
        except Exception as e:
            logger.error(f"Failed to update Management Platform configuration {field_path}: {e}")
            return False
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get security status of configuration."""
        return {
            "secrets_loaded": self._secrets_loaded,
            "security_validated": self._security_validated,
            "managers_initialized": self._config_managers_initialized,
            "environment": self.environment,
            "ssl_enabled": self.ssl_enabled,
            "debug_mode": self.debug,
            "secrets_management_enabled": self.enable_secrets_management,
            "config_encryption_enabled": self.enable_config_encryption,
            "config_audit_enabled": self.enable_config_audit,
            "config_backup_enabled": self.enable_config_backup,
            "hot_reload_enabled": self.enable_hot_reload,
            "compliance_frameworks": self.compliance_frameworks_list,
            "multi_tenant_security": {
                "row_level_security": self.enable_row_level_security,
                "schema_isolation": self.tenant_schema_isolation,
                "max_tenants": self.max_tenants_per_instance
            },
            "saas_features": {
                "kubernetes_orchestration": bool(self.kubernetes_config_path),
                "plugin_licensing": self.enable_usage_tracking,
                "health_monitoring": True,
                "sla_tracking": True
            }
        }
    
    def get_tenant_security_config(self, tenant_id: str) -> Dict[str, Any]:
        """
        Generate security configuration for tenant deployment.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Security configuration for tenant
        """
        return {
            "tenant_id": tenant_id,
            "secrets_management": {
                "openbao_url": self.openbao_url,
                "tenant_namespace": f"tenant-{tenant_id}",
                "rotation_enabled": True
            },
            "compliance_frameworks": self.compliance_frameworks_list,
            "security_features": {
                "config_encryption": self.enable_config_encryption,
                "audit_logging": self.enable_config_audit,
                "backup_enabled": self.enable_config_backup,
                "hot_reload": self.enable_hot_reload
            },
            "isolation": {
                "database_schema": f"tenant_{tenant_id}",
                "kubernetes_namespace": f"{self.kubernetes_namespace_prefix}-{tenant_id}",
                "rbac_enabled": self.enable_kubernetes_rbac
            }
        }


@lru_cache()
def get_enhanced_settings() -> ManagementPlatformSettings:
    """Get cached enhanced management platform settings."""
    return ManagementPlatformSettings()


# Backwards compatibility
def get_settings() -> ManagementPlatformSettings:
    """Get enhanced settings (backwards compatible)."""
    return get_enhanced_settings()


# Export for easy import
Settings = ManagementPlatformSettings