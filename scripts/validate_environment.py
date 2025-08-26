#!/usr/bin/env python3
"""
Environment Variable Validation System for DotMac Framework
Ensures all required environment variables are properly configured.
"""

import os
import sys
import re
from typing import Dict, List, Tuple, Optional, Union, Any
from pathlib import Path
import yaml
import json


class EnvironmentValidator:
    """Validates environment variables for all framework components."""
    
    def __init__(self):
        self.results = {}
        self.warnings = []
        self.errors = []
        self.total_checks = 0
        self.passed_checks = 0
        
    def check_required(self, var_name: str, description: str = "", validator=None) -> bool:
        """Check if a required environment variable exists and is valid."""
        self.total_checks += 1
        value = os.getenv(var_name)
        
        if value is None:
            error_msg = f"❌ {var_name}: Required - {description}"
            self.errors.append(error_msg)
            print(error_msg)
            return False
            
        if validator and not validator(value):
            error_msg = f"❌ {var_name}: Invalid value - {description}"
            self.errors.append(error_msg)
            print(error_msg)
            return False
            
        self.passed_checks += 1
        print(f"✅ {var_name}: {description} = {value[:50]}{'...' if len(value) > 50 else ''}")
        return True
    
    def check_optional(self, var_name: str, default: str, description: str = "", validator=None) -> bool:
        """Check an optional environment variable with default."""
        self.total_checks += 1
        value = os.getenv(var_name, default)
        
        if validator and not validator(value):
            warning_msg = f"⚠️ {var_name}: Invalid value, using default - {description}"
            self.warnings.append(warning_msg)
            print(warning_msg)
            os.environ[var_name] = default
            return True
            
        self.passed_checks += 1
        if value == default:
            print(f"✅ {var_name}: Using default - {description}")
        else:
            print(f"✅ {var_name}: {description} = {value[:50]}{'...' if len(value) > 50 else ''}")
        return True
    
    def validate_url(self, url: str) -> bool:
        """Validate URL format."""
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(url_pattern, url))
    
    def validate_database_url(self, url: str) -> bool:
        """Validate database URL format."""
        db_patterns = [
            r'^postgresql\+asyncpg://[^:]+:[^@]+@[^:]+:\d+/\w+$',
            r'^postgresql://[^:]+:[^@]+@[^:]+:\d+/\w+$',
            r'^sqlite:///.*\.db$',
        ]
        return any(re.match(pattern, url) for pattern in db_patterns)
    
    def validate_redis_url(self, url: str) -> bool:
        """Validate Redis URL format."""
        redis_patterns = [
            r'^redis://:[^@]*@[^:]+:\d+/\d+$',
            r'^redis://[^:]+:\d+/\d+$',
        ]
        return any(re.match(pattern, url) for pattern in redis_patterns)
    
    def validate_secret_key(self, key: str) -> bool:
        """Validate secret key strength."""
        return len(key) >= 32 and key != 'change-me'
    
    def validate_environment_name(self, env: str) -> bool:
        """Validate environment name."""
        return env in ['development', 'staging', 'production', 'test']
    
    def validate_log_level(self, level: str) -> bool:
        """Validate log level."""
        return level.upper() in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

    def validate_shared_infrastructure(self):
        """Validate shared infrastructure environment variables."""
        print("\n🏗️ SHARED INFRASTRUCTURE VALIDATION")
        print("=" * 50)
        
        # Database validation
        self.check_required(
            "POSTGRES_PASSWORD", 
            "PostgreSQL password for shared database",
            lambda x: len(x) >= 8
        )
        
        # Redis validation
        self.check_required(
            "REDIS_PASSWORD", 
            "Redis password for shared cache",
            lambda x: len(x) >= 8
        )
        
        # OpenBao/Vault validation
        self.check_required(
            "VAULT_TOKEN", 
            "OpenBao root token for secrets management",
            lambda x: len(x) >= 16
        )
        
        # ClickHouse for observability
        self.check_required(
            "CLICKHOUSE_PASSWORD", 
            "ClickHouse password for SignOz",
            lambda x: len(x) >= 8
        )
        
        # Optional SignOz token
        self.check_optional(
            "SIGNOZ_ACCESS_TOKEN", 
            "", 
            "SignOz access token (optional for development)"
        )

    def validate_isp_framework(self):
        """Validate ISP Framework environment variables."""
        print("\n🏢 ISP FRAMEWORK VALIDATION")
        print("=" * 50)
        
        # Core configuration
        self.check_optional(
            "ENVIRONMENT", 
            "development", 
            "Application environment",
            self.validate_environment_name
        )
        
        # Database configuration
        self.check_optional(
            "DATABASE_URL", 
            "postgresql+asyncpg://dotmac_admin:${POSTGRES_PASSWORD}@postgres-shared:5432/dotmac_isp",
            "ISP Framework database connection",
            self.validate_database_url
        )
        
        # Redis configuration
        self.check_optional(
            "REDIS_URL", 
            "redis://:${REDIS_PASSWORD}@redis-shared:6379/0",
            "ISP Framework Redis cache connection"
        )
        
        # Celery configuration
        self.check_optional(
            "CELERY_BROKER_URL", 
            "redis://:${REDIS_PASSWORD}@redis-shared:6379/1",
            "Celery message broker URL"
        )
        
        self.check_optional(
            "CELERY_RESULT_BACKEND", 
            "redis://:${REDIS_PASSWORD}@redis-shared:6379/2",
            "Celery result backend URL"
        )
        
        # Observability
        self.check_optional(
            "SIGNOZ_ENDPOINT", 
            "signoz-collector:4317",
            "SignOz OpenTelemetry endpoint"
        )
        
        # Logging
        self.check_optional(
            "LOG_LEVEL", 
            "INFO", 
            "Application log level",
            self.validate_log_level
        )

    def validate_management_platform(self):
        """Validate Management Platform environment variables."""
        print("\n🎛️ MANAGEMENT PLATFORM VALIDATION")
        print("=" * 50)
        
        # Core configuration
        self.check_optional(
            "ENVIRONMENT", 
            "development", 
            "Application environment",
            self.validate_environment_name
        )
        
        # Database configuration
        self.check_optional(
            "DATABASE_URL", 
            "postgresql+asyncpg://dotmac_admin:${POSTGRES_PASSWORD}@postgres-shared:5432/mgmt_platform",
            "Management Platform database connection",
            self.validate_database_url
        )
        
        # Redis configuration
        self.check_optional(
            "REDIS_URL", 
            "redis://:${REDIS_PASSWORD}@redis-shared:6379/3",
            "Management Platform Redis cache connection"
        )
        
        # Celery configuration
        self.check_optional(
            "CELERY_BROKER_URL", 
            "redis://:${REDIS_PASSWORD}@redis-shared:6379/4",
            "Celery message broker URL"
        )
        
        self.check_optional(
            "CELERY_RESULT_BACKEND", 
            "redis://:${REDIS_PASSWORD}@redis-shared:6379/5",
            "Celery result backend URL"
        )
        
        # Security secrets
        self.check_required(
            "MGMT_SECRET_KEY", 
            "Management Platform secret key (minimum 32 chars)",
            self.validate_secret_key
        )
        
        self.check_required(
            "MGMT_JWT_SECRET_KEY", 
            "JWT secret key (minimum 32 chars)",
            self.validate_secret_key
        )
        
        # External services
        self.check_optional(
            "STRIPE_SECRET_KEY", 
            "sk_test_placeholder",
            "Stripe payment processing key"
        )
        
        self.check_optional(
            "SENDGRID_API_KEY", 
            "sg_placeholder",
            "SendGrid email API key"
        )
        
        # CORS origins
        self.check_optional(
            "CORS_ORIGINS", 
            '["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"]',
            "CORS allowed origins (JSON array)"
        )
        
        # ISP Framework integration
        self.check_optional(
            "ISP_FRAMEWORK_URL", 
            "http://isp-framework:8000",
            "ISP Framework API URL",
            self.validate_url
        )

    def validate_docker_environment(self):
        """Validate Docker-specific environment variables."""
        print("\n🐳 DOCKER ENVIRONMENT VALIDATION")
        print("=" * 50)
        
        # Check if running in Docker
        in_docker = os.path.exists('/.dockerenv') or os.getenv('DOCKER_ENV') == 'true'
        
        if in_docker:
            print("✅ Running in Docker container")
            
            # Docker-specific checks
            self.check_optional(
                "PYTHONUNBUFFERED", 
                "1", 
                "Python output buffering (should be disabled in Docker)"
            )
            
            self.check_optional(
                "PYTHONDONTWRITEBYTECODE", 
                "1", 
                "Python bytecode writing (should be disabled in Docker)"
            )
            
        else:
            print("ℹ️ Not running in Docker (development mode)")
            
            # Development-specific checks
            self.check_optional(
                "PYTHONPATH", 
                ".", 
                "Python module search path"
            )

    def validate_production_requirements(self):
        """Validate production-specific requirements."""
        environment = os.getenv('ENVIRONMENT', 'development')
        
        if environment == 'production':
            print("\n🏭 PRODUCTION ENVIRONMENT VALIDATION")
            print("=" * 50)
            
            # Production-specific security checks
            production_required = [
                ("SSL_CERT_PATH", "SSL certificate file path"),
                ("SSL_KEY_PATH", "SSL private key file path"),
                ("BACKUP_ENCRYPTION_KEY", "Backup encryption key"),
                ("MONITORING_WEBHOOK_URL", "Production monitoring webhook"),
            ]
            
            for var_name, description in production_required:
                self.check_optional(var_name, "", description)
            
            # Validate no development defaults in production
            dangerous_defaults = [
                ("MGMT_SECRET_KEY", "mgmt-secret-key"),
                ("MGMT_JWT_SECRET_KEY", "mgmt-jwt-secret"),
                ("POSTGRES_PASSWORD", "password"),
                ("REDIS_PASSWORD", "password"),
            ]
            
            for var_name, dangerous_value in dangerous_defaults:
                value = os.getenv(var_name, "")
                if dangerous_value in value.lower():
                    error_msg = f"❌ {var_name}: Using insecure default in production"
                    self.errors.append(error_msg)
                    print(error_msg)

    def generate_env_template(self):
        """Generate a .env template file with all required variables."""
        template_content = """# DotMac Framework Environment Configuration Template
# Copy this to .env and fill in the actual values

# ===== SHARED INFRASTRUCTURE =====
# Required passwords (minimum 8 characters)
POSTGRES_PASSWORD=your-secure-postgres-password-here
REDIS_PASSWORD=your-secure-redis-password-here
CLICKHOUSE_PASSWORD=your-secure-clickhouse-password-here

# OpenBao/Vault token (minimum 16 characters)
VAULT_TOKEN=your-openbao-root-token-here

# ===== MANAGEMENT PLATFORM SECRETS =====
# Required secret keys (minimum 32 characters)
MGMT_SECRET_KEY=your-management-platform-secret-key-minimum-32-chars
MGMT_JWT_SECRET_KEY=your-jwt-secret-key-minimum-32-chars-long

# ===== OPTIONAL EXTERNAL SERVICES =====
# Stripe (for payment processing)
STRIPE_SECRET_KEY=sk_test_your_stripe_key_here

# SendGrid (for email notifications)
SENDGRID_API_KEY=SG.your_sendgrid_key_here

# SignOz (for observability - optional in development)
SIGNOZ_ACCESS_TOKEN=your-signoz-token-here

# ===== OPTIONAL CONFIGURATION =====
# Application environment (development|staging|production)
ENVIRONMENT=development

# Log level (DEBUG|INFO|WARNING|ERROR|CRITICAL)
LOG_LEVEL=INFO

# CORS origins (JSON array format)
CORS_ORIGINS=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"]

# ===== PRODUCTION ONLY =====
# Uncomment and configure for production deployment
# SSL_CERT_PATH=/path/to/ssl/cert.pem
# SSL_KEY_PATH=/path/to/ssl/private.key
# BACKUP_ENCRYPTION_KEY=your-backup-encryption-key-here
# MONITORING_WEBHOOK_URL=https://your-monitoring-system/webhook
"""
        
        template_path = Path(__file__).parent.parent / ".env.template"
        with open(template_path, 'w') as f:
            f.write(template_content)
        
        print(f"✅ Generated environment template: {template_path}")
        print("   Copy to .env and customize the values")

    def check_env_file_exists(self):
        """Check if .env file exists and warn if missing."""
        env_file = Path(__file__).parent.parent / ".env"
        if not env_file.exists():
            warning_msg = "⚠️ .env file not found - using system environment variables only"
            self.warnings.append(warning_msg)
            print(warning_msg)
            return False
        else:
            print("✅ .env file found")
            return True

    def run_validation(self):
        """Run complete environment validation."""
        print("🌍 DotMac Framework Environment Validation")
        print("=" * 60)
        
        # Check for .env file
        self.check_env_file_exists()
        
        # Run all validations
        self.validate_shared_infrastructure()
        self.validate_isp_framework()
        self.validate_management_platform()
        self.validate_docker_environment()
        self.validate_production_requirements()
        
        # Generate template if needed
        if len(self.errors) > 5:  # Many missing variables
            print("\n📝 Generating environment template...")
            self.generate_env_template()
        
        # Print summary
        self.print_summary()
        
        return len(self.errors) == 0

    def print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 60)
        print("📊 ENVIRONMENT VALIDATION SUMMARY")
        print("=" * 60)
        
        success_rate = (self.passed_checks / self.total_checks * 100) if self.total_checks > 0 else 0
        
        print(f"✅ Passed checks: {self.passed_checks}/{self.total_checks}")
        print(f"⚠️ Warnings: {len(self.warnings)}")
        print(f"❌ Errors: {len(self.errors)}")
        print(f"📈 Success rate: {success_rate:.1f}%")
        
        if self.warnings:
            print("\n⚠️ WARNINGS:")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"   • {error}")
        
        print("\n" + "=" * 60)
        
        if len(self.errors) == 0:
            print("🎉 ENVIRONMENT VALIDATION PASSED!")
            print("   All required environment variables are properly configured.")
        elif len(self.errors) <= 5:
            print("⚠️ MINOR ENVIRONMENT ISSUES DETECTED")
            print("   Please fix the errors above before deployment.")
        else:
            print("💥 MAJOR ENVIRONMENT CONFIGURATION ISSUES")
            print("   Critical environment variables are missing or invalid.")
            print("   Use the generated .env.template to configure your environment.")
        
        return len(self.errors) == 0


def main():
    """Main validation entry point."""
    validator = EnvironmentValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()