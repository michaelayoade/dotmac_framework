#!/usr/bin/env python3
"""
Comprehensive Import Validation System for DotMac Framework
Validates that all critical components can be imported successfully.
"""

import sys
import os
import importlib
import traceback
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import asyncio
import subprocess

# Add project roots to path
framework_root = Path(__file__).parent.parent
sys.path.insert(0, str(framework_root))
sys.path.insert(0, str(framework_root / "isp-framework" / "src"))
sys.path.insert(0, str(framework_root / "management-platform" / "app"))

class ImportValidator:
    """Validates imports for all framework components."""
    
    def __init__(self):
        self.results = {}
        self.failed_imports = []
        self.success_count = 0
        self.total_count = 0
        
    def test_import(self, module_name: str, description: str = "") -> bool:
        """Test if a module can be imported successfully."""
        self.total_count += 1
        try:
            importlib.import_module(module_name)
            self.results[module_name] = {"status": "success", "description": description}
            self.success_count += 1
            print(f"✅ {module_name}: {description}")
            return True
        except Exception as e:
            self.results[module_name] = {
                "status": "failed", 
                "description": description,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            self.failed_imports.append((module_name, description, str(e)))
            print(f"❌ {module_name}: {description} - {str(e)[:100]}...")
            return False
    
    async def test_async_import(self, module_name: str, async_component: str, description: str = "") -> bool:
        """Test async components that require runtime initialization."""
        self.total_count += 1
        try:
            module = importlib.import_module(module_name)
            component = getattr(module, async_component)
            
            # For async components, just verify they can be accessed
            if callable(component):
                self.results[f"{module_name}.{async_component}"] = {
                    "status": "success", 
                    "description": description
                }
                self.success_count += 1
                print(f"✅ {module_name}.{async_component}: {description}")
                return True
            else:
                raise AttributeError(f"{async_component} is not callable")
                
        except Exception as e:
            self.results[f"{module_name}.{async_component}"] = {
                "status": "failed",
                "description": description,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            self.failed_imports.append((f"{module_name}.{async_component}", description, str(e)))
            print(f"❌ {module_name}.{async_component}: {description} - {str(e)[:100]}...")
            return False

    def validate_isp_framework(self):
        """Validate ISP Framework imports."""
        print("\n🏢 ISP FRAMEWORK VALIDATION")
        print("=" * 50)
        
        # Core modules
        self.test_import("dotmac_isp.app", "Main FastAPI application")
        self.test_import("dotmac_isp.core.settings", "Configuration system")
        self.test_import("dotmac_isp.core.database", "Database connections")
        self.test_import("dotmac_isp.api.routers", "API routing system")
        
        # Module imports
        modules = [
            ("dotmac_isp.modules.identity.router", "Identity management API"),
            ("dotmac_isp.modules.billing.router", "Billing system API"),
            ("dotmac_isp.modules.services.router", "Service management API"),
            ("dotmac_isp.modules.analytics.service", "Analytics engine"),
            ("dotmac_isp.modules.network_integration.service", "Network integration"),
            ("dotmac_isp.modules.omnichannel.enhanced_service", "Communication system"),
        ]
        
        for module, desc in modules:
            self.test_import(module, desc)
        
        # SDKs
        sdk_modules = [
            ("dotmac_isp.sdks.platform.audit_sdk", "Audit logging SDK"),
            ("dotmac_isp.sdks.platform.cache_sdk", "Caching SDK"),
            ("dotmac_isp.sdks.platform.secrets_sdk", "Secrets management SDK"),
            ("dotmac_isp.sdks.networking.voltha_integration", "VOLTHA integration SDK"),
        ]
        
        for module, desc in sdk_modules:
            self.test_import(module, desc)

    def validate_management_platform(self):
        """Validate Management Platform imports."""
        print("\n🎛️ MANAGEMENT PLATFORM VALIDATION")
        print("=" * 50)
        
        # Core modules
        self.test_import("app.run_server", "Application factory")
        self.test_import("config", "Configuration system")
        
        # API modules
        api_modules = [
            ("app.api.v1.admin", "Admin management API"),
            ("app.api.v1.tenant", "Tenant management API"),
            ("app.api.v1.billing", "Billing management API"),
            ("app.api.v1.deployment", "Deployment management API"),
            ("app.api.v1.monitoring", "Monitoring API"),
        ]
        
        for module, desc in api_modules:
            self.test_import(module, desc)
        
        # Services
        service_modules = [
            ("app.services.tenant_service", "Tenant orchestration service"),
            ("app.services.billing_service", "Billing service"),
            ("app.services.deployment_service", "Deployment service"),
            ("app.services.monitoring_service", "Monitoring service"),
        ]
        
        for module, desc in service_modules:
            self.test_import(module, desc)

    def validate_shared_components(self):
        """Validate shared components."""
        print("\n🔗 SHARED COMPONENTS VALIDATION")
        print("=" * 50)
        
        # Test shared utilities that both platforms use
        try:
            # These might not exist yet, but we validate the structure
            shared_modules = [
                ("shared.communication.plugin_system", "Communication plugin system"),
                ("shared.deployments.scripts", "Deployment scripts"),
            ]
            
            for module, desc in shared_modules:
                self.test_import(module, desc)
        except:
            print("⚠️ Shared components not yet implemented")

    def validate_environment_setup(self):
        """Validate environment and dependencies."""
        print("\n🌍 ENVIRONMENT VALIDATION")
        print("=" * 50)
        
        # Check Python version
        python_version = sys.version_info
        if python_version >= (3, 11):
            print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}: Compatible")
        else:
            print(f"❌ Python {python_version.major}.{python_version.minor}.{python_version.micro}: Requires >= 3.11")
        
        # Check critical dependencies
        critical_deps = [
            ("fastapi", "FastAPI framework"),
            ("sqlalchemy", "Database ORM"),
            ("redis", "Caching system"),
            ("celery", "Task queue"),
            ("pytest", "Testing framework"),
        ]
        
        for dep, desc in critical_deps:
            self.test_import(dep, desc)

    def check_docker_compatibility(self):
        """Check Docker-related imports and configurations."""
        print("\n🐳 DOCKER COMPATIBILITY")
        print("=" * 50)
        
        # Check if docker-related imports work
        docker_deps = [
            ("docker", "Docker API client"),
            ("kubernetes", "Kubernetes client"),
        ]
        
        for dep, desc in docker_deps:
            self.test_import(dep, desc)
        
        # Validate Dockerfile entry points can be imported
        try:
            # ISP Framework entry point
            importlib.import_module("dotmac_isp.app")
            print("✅ ISP Framework Docker entry point: Valid")
        except Exception as e:
            print(f"❌ ISP Framework Docker entry point: {e}")
        
        try:
            # Management Platform entry point
            from app.run_server import create_app
            create_app()
            print("✅ Management Platform Docker entry point: Valid")
        except Exception as e:
            print(f"❌ Management Platform Docker entry point: {e}")

    async def run_validation(self):
        """Run complete validation suite."""
        print("🚀 DotMac Framework Import Validation")
        print("=" * 60)
        
        # Set environment variables for testing
        os.environ.setdefault('DATABASE_URL', 'sqlite:///test.db')
        os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
        os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-validation-only')
        os.environ.setdefault('JWT_SECRET_KEY', 'test-jwt-secret-key-for-validation-only-at-least-32-chars')
        os.environ.setdefault('ENVIRONMENT', 'development')
        
        # Run all validations
        self.validate_environment_setup()
        self.validate_isp_framework()
        self.validate_management_platform()
        self.validate_shared_components()
        self.check_docker_compatibility()
        
        # Print summary
        self.print_summary()
        
        return len(self.failed_imports) == 0

    def print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        success_rate = (self.success_count / self.total_count * 100) if self.total_count > 0 else 0
        
        print(f"✅ Successful imports: {self.success_count}")
        print(f"❌ Failed imports: {len(self.failed_imports)}")
        print(f"📈 Success rate: {success_rate:.1f}%")
        
        if self.failed_imports:
            print("\n❌ FAILED IMPORTS:")
            for module, desc, error in self.failed_imports:
                print(f"   • {module}: {desc}")
                print(f"     Error: {error}")
        
        print("\n" + "=" * 60)
        
        if success_rate >= 90:
            print("🎉 VALIDATION PASSED: Framework is import-ready!")
            return True
        elif success_rate >= 75:
            print("⚠️ VALIDATION WARNING: Some components need attention")
            return False
        else:
            print("💥 VALIDATION FAILED: Critical import issues detected")
            return False

async def main():
    """Main validation entry point."""
    validator = ImportValidator()
    success = await validator.run_validation()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())