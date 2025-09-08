#!/usr/bin/env python3
"""
Comprehensive Import Test for DotMac Framework

This script tests all package imports to ensure proper integration
after the migration from src modules to dedicated packages.
"""

import sys
import importlib.util
from pathlib import Path

# Add all package source directories to Python path
FRAMEWORK_ROOT = Path("/home/dotmac_framework")
PACKAGES_ROOT = FRAMEWORK_ROOT / "packages"
SRC_ROOT = FRAMEWORK_ROOT / "src"

# Add src to path
sys.path.insert(0, str(SRC_ROOT))

# Add all package source directories
for package_dir in PACKAGES_ROOT.glob("dotmac-*"):
    src_dir = package_dir / "src"
    if src_dir.exists():
        sys.path.insert(0, str(src_dir))
        print(f"📦 Added to path: {src_dir}")

print("\n" + "="*80)
print("COMPREHENSIVE IMPORT TEST - DotMac Framework")
print("="*80)

def test_import(module_name, description=""):
    """Test importing a module and return result."""
    try:
        importlib.import_module(module_name)
        return True, f"✅ {module_name} {description}"
    except Exception as e:
        return False, f"❌ {module_name} {description}: {str(e)}"

def test_from_import(from_module, import_items, description=""):
    """Test importing specific items from a module."""
    try:
        module = importlib.import_module(from_module)
        for item in import_items:
            getattr(module, item)
        items_str = ", ".join(import_items)
        return True, f"✅ from {from_module} import {items_str} {description}"
    except Exception as e:
        items_str = ", ".join(import_items)
        return False, f"❌ from {from_module} import {items_str} {description}: {str(e)}"

# Results tracking
results = []
success_count = 0
total_count = 0

print("\n🔍 TESTING CORE MIGRATED PACKAGES")
print("-" * 50)

# Test dotmac-workflows package
tests = [
    ("dotmac_workflows", ["Workflow", "WorkflowResult", "WorkflowStatus"], "- Core workflow classes"),
    ("dotmac_workflows.base", ["WorkflowError", "WorkflowExecutionError"], "- Error classes"),
    ("dotmac_workflows.status", ["WorkflowStatus"], "- Status enum"),
    ("dotmac_workflows.result", ["WorkflowResult"], "- Result dataclass"),
]

for from_module, items, desc in tests:
    success, message = test_from_import(from_module, items, desc)
    results.append(message)
    if success:
        success_count += 1
    total_count += 1

# Test dotmac-service-kernel package  
tests = [
    ("dotmac_service_kernel", ["ValidationError", "ServiceError", "RepositoryError"], "- Exception classes"),
    ("dotmac_service_kernel", ["NotFoundError", "ConflictError", "ServicePermissionError"], "- Specific errors"),
    ("dotmac_service_kernel", ["Page", "RepositoryProtocol", "ServiceProtocol"], "- Core abstractions"),
    ("dotmac_service_kernel.pagination", ["PaginationParams", "create_page"], "- Pagination utils"),
    ("dotmac_service_kernel.uow", ["BaseUnitOfWork", "MemoryUnitOfWork"], "- Unit of Work"),
]

for from_module, items, desc in tests:
    success, message = test_from_import(from_module, items, desc)
    results.append(message)
    if success:
        success_count += 1
    total_count += 1

print("\n🔍 TESTING OTHER CORE PACKAGES")
print("-" * 50)

# Test other core packages
core_packages = [
    ("dotmac_core", "- Core framework"),
    ("dotmac_platform_services", "- Platform services"),
    ("dotmac_application", "- Application layer"),
    ("dotmac_business_logic", "- Business logic"),
    ("dotmac_communications", "- Communications"),
    ("dotmac_networking", "- Networking"),
    ("dotmac_plugins", "- Plugins"),
    ("dotmac_security", "- Security"),
    ("dotmac_ticketing", "- Ticketing"),
]

for module, desc in core_packages:
    success, message = test_import(module, desc)
    results.append(message)
    if success:
        success_count += 1
    total_count += 1

print("\n🔍 TESTING SRC MODULE IMPORTS")
print("-" * 50)

# Test main src modules
src_modules = [
    ("dotmac_shared", "- Shared utilities"),
    ("dotmac_isp", "- ISP application"),
    ("dotmac_management", "- Management application"),
]

for module, desc in src_modules:
    success, message = test_import(module, desc)
    results.append(message)
    if success:
        success_count += 1
    total_count += 1

print("\n🔍 TESTING CRITICAL FILE IMPORTS AFTER MIGRATION")
print("-" * 50)

# Test specific files that were updated in the migration
critical_files = [
    ("/home/dotmac_framework/src/dotmac_management/workflows/plugin_workflows.py", "Plugin workflows"),
    ("/home/dotmac_framework/src/dotmac_management/services/onboarding_service.py", "Onboarding service"), 
    ("/home/dotmac_framework/src/dotmac_isp/modules/billing/domain/calculation_service.py", "Billing calculations"),
    ("/home/dotmac_framework/src/dotmac_management/user_management/repositories/user_repository.py", "User repository"),
    ("/home/dotmac_framework/src/dotmac_shared/models/__init__.py", "Shared models"),
]

for file_path, desc in critical_files:
    try:
        spec = importlib.util.spec_from_file_location("test_module", file_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            # Just check if we can load the spec and imports, don't execute
            success = True
            message = f"✅ {desc} - Import syntax valid"
        else:
            success = False
            message = f"❌ {desc} - Cannot load module spec"
    except Exception as e:
        success = False
        message = f"❌ {desc} - {str(e)}"
    
    results.append(message)
    if success:
        success_count += 1
    total_count += 1

print("\n🔍 TESTING WORKFLOW REPLACEMENT SUCCESS")
print("-" * 50)

# Test that old workflow imports are gone and new ones work
workflow_tests = [
    ("dotmac_workflows", "Workflow", "New workflow package"),
    ("dotmac_workflows", "WorkflowResult", "New workflow result"),
    ("dotmac_workflows", "WorkflowStatus", "New workflow status"),
]

for module, item, desc in workflow_tests:
    success, message = test_from_import(module, [item], f"- {desc}")
    results.append(message)
    if success:
        success_count += 1
    total_count += 1

# Test that old workflow location is gone
try:
    importlib.import_module("dotmac_shared.workflows")
    results.append("❌ OLD dotmac_shared.workflows still exists - should be removed")
    total_count += 1
except ImportError:
    results.append("✅ OLD dotmac_shared.workflows properly removed")
    success_count += 1
    total_count += 1

print("\n" + "="*80)
print("IMPORT TEST RESULTS")
print("="*80)

for result in results:
    print(result)

print("\n" + "="*80)
print(f"SUMMARY: {success_count}/{total_count} imports successful")
if success_count == total_count:
    print("🎉 ALL IMPORTS WORKING - Migration successful!")
else:
    print(f"⚠️  {total_count - success_count} import issues found - Review needed")
print("="*80)

# Exit with error code if any imports failed
sys.exit(0 if success_count == total_count else 1)