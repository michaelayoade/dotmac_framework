#!/usr/bin/env python3
"""
Repository Cleanup Script
Removes temporary development files and artifacts from the DotMac framework repository
"""

import os
import shutil
from pathlib import Path
from typing import List, Set

def get_files_to_remove() -> List[str]:
    """
    Returns list of temporary/development files that should be removed
    """
    return [
        # Temporary analysis and fix scripts
        "analyze_async_patterns.py",
        "async_pattern_analysis.md",
        "check_dependencies.py", 
        "check_router_syntax.py",
        "complete_hvac_removal.py",
        "final_comprehensive_fix.py",
        "fix_base_imports.py",
        "fix_core_syntax.py",
        "fix_datetime_deprecation.py",
        "fix_malformed_inits_bulk.py",
        "fix_mgmt_platform_imports.py",
        "fix_missing_dependencies.py",
        "fix_remaining_syntax.py",
        "fix_router_syntax.py",
        "fix_startup_blockers.py",
        "fix_syntax_errors.py",
        "fix_syntax_patterns.py",
        "fix_tariff_syntax.py",
        "fix_unreachable_code.py",
        "simple_syntax_fixer.py",
        "update_pydantic_v2_comprehensive.py",
        "validate_dependency_fixes.py",
        
        # Test files that are temporary
        "quick_auth_test.py",
        "test_config_audit_fixes.py",
        "test_identity_fixes.py",
        "test_isp_final.py",
        "test_openbao_migration.py",
        "test_startup_improvements.py",
        "test_table_conflicts.py",
        
        # Analysis reports and temporary configs
        "import_analysis.py",
        "security_validation_report.json",
        "resolve_table_conflicts.py",
        "deployment_config.json",
        "pyrightconfig.json",
        
        # Summary files that are now outdated
        "ASYNC_STANDARDIZATION_GUIDE.md",
        "NEXT_STEPS.md", 
        "PRIORITY_1_FIXES_SUMMARY.md",
        "ROUTER_FIXES_SUMMARY.md",
        
        # Temporary deployment files
        "deploy_remote.sh",
        "deploy_to_remote.py",
        "docker-compose.remote.yml",
        
        # Development lock files (keep requirements-dev.txt but remove lock)
        "requirements-dev.lock",
        
        # Branch protection setup files (temporary)
        "setup_branch_protection.html",
        "scripts/setup_branch_protection.py"
    ]

def get_directories_to_remove() -> List[str]:
    """
    Returns list of temporary directories that should be removed
    """
    return [
        "management-platform/backups_final",
        "management-platform/backups_syntax_fixes"
    ]

def should_keep_file(filepath: str) -> bool:
    """
    Determines if a file should be kept in the repository
    """
    keep_patterns = {
        # Core application directories
        ".github/", "api-specifications/", "certs/", "config/", "deployment/",
        "docker/", "docs/", "frontend/", "isp-framework/", "management-platform/",
        "monitoring/", "nginx/", "plugins/", "postgres/", "redis/", "scripts/",
        "sdk/", "security/", "shared/", "signoz/", "templates/", "tests/",
        
        # Essential config files
        ".editorconfig", ".env.example", ".gitignore", ".pre-commit-config.yaml",
        ".quality-gates.yml", "Makefile", "pyproject.toml", "pytest.ini",
        "requirements.txt", "docker-compose.yml", "docker-compose.production.yml",
        "docker-compose.unified.yml", "env-setup.sh",
        
        # Documentation files
        "README.md", "CHANGELOG.md", "CONTRIBUTING.md", "TESTING_GUIDE.md",
        "BUSINESS_MODEL_VISION.md", "ISP_VALUE_PROPOSITION.md", 
        "OPERATIONAL_RUNBOOKS.md", "PARTNER_BUSINESS_OVERVIEW.md",
        "PRODUCTION_READINESS_CHECKLIST.md", "SECURITY_CONFIGURATION.md",
        "TESTING_STRATEGY.md", "DEPENDENCY_CONSOLIDATION_RESULTS.md",
        "DOCUMENTATION_ALIGNMENT.md", "SIMPLIFICATION_STRATEGY.md",
        
        # Essential scripts
        "conftest.py", "test_management_platform.py", "test_security_controls.py",
        "dependency_manager.py", "app_startup_validator.py", "consolidate_deps.py"
    }
    
    # Check if file matches any keep pattern
    for pattern in keep_patterns:
        if filepath.startswith(pattern) or filepath.endswith(pattern):
            return True
    
    return False

def cleanup_repository():
    """
    Main cleanup function
    """
    repo_root = Path("/home/dotmac_framework")
    removed_files = []
    removed_dirs = []
    
    print("🧹 Starting repository cleanup...")
    
    # Remove specific files
    files_to_remove = get_files_to_remove()
    for filename in files_to_remove:
        filepath = repo_root / filename
        if filepath.exists():
            try:
                filepath.unlink()
                removed_files.append(filename)
                print(f"  ✅ Removed: {filename}")
            except Exception as e:
                print(f"  ❌ Failed to remove {filename}: {e}")
    
    # Remove specific directories
    dirs_to_remove = get_directories_to_remove()
    for dirname in dirs_to_remove:
        dirpath = repo_root / dirname
        if dirpath.exists():
            try:
                shutil.rmtree(dirpath)
                removed_dirs.append(dirname)
                print(f"  ✅ Removed directory: {dirname}")
            except Exception as e:
                print(f"  ❌ Failed to remove directory {dirname}: {e}")
    
    # Clean up any remaining .pyc files and __pycache__ directories
    for root, dirs, files in os.walk(repo_root):
        # Remove __pycache__ directories
        if "__pycache__" in dirs:
            pycache_path = Path(root) / "__pycache__"
            try:
                shutil.rmtree(pycache_path)
                print(f"  ✅ Removed: {pycache_path.relative_to(repo_root)}")
            except Exception as e:
                print(f"  ❌ Failed to remove {pycache_path}: {e}")
        
        # Remove .pyc files
        for file in files:
            if file.endswith('.pyc'):
                pyc_path = Path(root) / file
                try:
                    pyc_path.unlink()
                    print(f"  ✅ Removed: {pyc_path.relative_to(repo_root)}")
                except Exception as e:
                    print(f"  ❌ Failed to remove {pyc_path}: {e}")
    
    print(f"\n📊 Cleanup Summary:")
    print(f"  • Removed {len(removed_files)} files")
    print(f"  • Removed {len(removed_dirs)} directories")
    print(f"  • Cleaned up Python cache files")
    
    print(f"\n✨ Repository cleanup completed!")
    print(f"Your repository now contains only essential files for production.")

if __name__ == "__main__":
    cleanup_repository()
