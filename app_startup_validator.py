#!/usr/bin/env python3
"""
Comprehensive App Startup Validator for DotMac SaaS Platform
Tests all potential blockers that could prevent the applications from running.
"""

import ast
import os
import sys
import importlib.util
from pathlib import Path
from typing import List, Dict, Tuple
import subprocess
import traceback

class AppStartupValidator:
    def __init__(self, root_path: str = "/home/dotmac_framework"):
        self.root_path = Path(root_path)
        self.issues = []
        self.components = {
            'isp-framework': {
                'path': self.root_path / 'isp-framework' / 'src',
                'app_module': 'dotmac_isp.app',
                'main_file': 'dotmac_isp/app.py'
            },
            'management-platform': {
                'path': self.root_path / 'management-platform' / 'app',
                'app_module': 'main',
                'main_file': 'main.py'
            }
        }

    def check_syntax_errors(self) -> List[Dict]:
        """Check for syntax errors that block import."""
        print("🔍 Checking for syntax errors...")
        syntax_errors = []
        
        for component, info in self.components.items():
            if not info['path'].exists():
                continue
                
            print(f"  📁 Scanning {component}...")
            for py_file in info['path'].rglob('*.py'):
                try:
                    with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Try to parse the AST
                    ast.parse(content, filename=str(py_file)
                    
                except SyntaxError as e:
                    syntax_errors.append({
                        'component': component,
                        'file': str(py_file.relative_to(self.root_path)),
                        'line': e.lineno,
                        'error': str(e),
                        'severity': 'CRITICAL'
                    })
                except Exception as e:
                    # Other parsing issues
                    syntax_errors.append({
                        'component': component,
                        'file': str(py_file.relative_to(self.root_path)),
                        'line': 'unknown',
                        'error': f'Parse error: {str(e)}',
                        'severity': 'HIGH'
                    })
        
        return syntax_errors

    def test_app_imports(self) -> List[Dict]:
        """Test if main applications can be imported."""
        print("🔍 Testing application imports...")
        import_errors = []
        
        for component, info in self.components.items():
            print(f"  📦 Testing {component} import...")
            
            # Add the component path to sys.path temporarily
            original_path = sys.path.copy()
            sys.path.insert(0, str(info['path'])
            
            try:
                # Try to import the main app module
                if component == 'isp-framework':
                    import dotmac_isp.app
                    print(f"    ✅ {component}: Main app imports successfully")
                elif component == 'management-platform':
                    # Test individual components that are imported by main.py
                    test_imports = [
                        'config',
                        'database',
                        'core.logging',
                        'core.middleware',
                        'core.exceptions'
                    ]
                    
                    for test_import in test_imports:
                        try:
                            importlib.import_module(test_import)
                        except ImportError as e:
                            import_errors.append({
                                'component': component,
                                'module': test_import,
                                'error': str(e),
                                'severity': 'HIGH'
                            })
                    
                    if not import_errors:
                        print(f"    ✅ {component}: Core modules import successfully")
                    
            except ImportError as e:
                import_errors.append({
                    'component': component,
                    'module': info['app_module'],
                    'error': str(e),
                    'severity': 'CRITICAL',
                    'traceback': traceback.format_exc()
                })
                print(f"    ❌ {component}: Import failed - {str(e)}")
                
            except Exception as e:
                import_errors.append({
                    'component': component,
                    'module': info['app_module'],
                    'error': f'Unexpected error: {str(e)}',
                    'severity': 'CRITICAL',
                    'traceback': traceback.format_exc()
                })
                print(f"    ❌ {component}: Unexpected error - {str(e)}")
                
            finally:
                # Restore original sys.path
                sys.path = original_path
        
        return import_errors

    def check_missing_dependencies(self) -> List[Dict]:
        """Check for missing dependencies that would block startup."""
        print("🔍 Checking for missing dependencies...")
        missing_deps = []
        
        # Check if core dependencies from our unified requirements are available
        core_deps = [
            'fastapi', 'uvicorn', 'pydantic', 'sqlalchemy', 'asyncpg',
            'httpx', 'structlog', 'redis', 'celery', 'passlib'
        ]
        
        for dep in core_deps:
            try:
                importlib.import_module(dep)
                print(f"    ✅ {dep}: Available")
            except ImportError:
                missing_deps.append({
                    'dependency': dep,
                    'severity': 'HIGH',
                    'impact': 'Application startup will fail'
                })
                print(f"    ❌ {dep}: Missing")
        
        return missing_deps

    def check_environment_variables(self) -> List[Dict]:
        """Check for required environment variables."""
        print("🔍 Checking environment variables...")
        env_issues = []
        
        # Common environment variables that might be required
        common_env_vars = [
            'DATABASE_URL',
            'REDIS_URL', 
            'SECRET_KEY',
            'ENVIRONMENT'
        ]
        
        for var in common_env_vars:
            value = os.getenv(var)
            if not value:
                env_issues.append({
                    'variable': var,
                    'severity': 'MEDIUM',
                    'impact': f'Application may fail to start or use defaults for {var}'
                })
                print(f"    ⚠️ {var}: Not set (may use defaults)")
            else:
                print(f"    ✅ {var}: Set")
        
        return env_issues

    def check_database_requirements(self) -> List[Dict]:
        """Check if database connection requirements are met."""
        print("🔍 Checking database requirements...")
        db_issues = []
        
        try:
            import asyncpg
            import sqlalchemy
            print("    ✅ Database drivers available")
            
            # Check if we can create a basic SQLAlchemy engine (without connecting)
            from sqlalchemy import create_engine
            
            # Test with a dummy URL to check if drivers are working
            test_url = "postgresql://test:test@localhost:5432/test"
            engine = create_engine(test_url, strategy='mock', executor=lambda sql, *_: None)
            print("    ✅ SQLAlchemy engine creation works")
            
        except ImportError as e:
            db_issues.append({
                'component': 'database',
                'error': f'Database driver missing: {str(e)}',
                'severity': 'HIGH'
            })
        except Exception as e:
            db_issues.append({
                'component': 'database',
                'error': f'Database configuration issue: {str(e)}',
                'severity': 'MEDIUM'
            })
        
        return db_issues

    def run_comprehensive_validation(self) -> Dict:
        """Run all validation checks."""
        print("🚀 DotMac SaaS Platform - Comprehensive App Startup Validation")
        print("=" * 70)
        
        results = {
            'syntax_errors': self.check_syntax_errors(),
            'import_errors': self.test_app_imports(), 
            'missing_dependencies': self.check_missing_dependencies(),
            'environment_issues': self.check_environment_variables(),
            'database_issues': self.check_database_requirements()
        }
        
        # Summary
        total_critical = (
            len([e for e in results['syntax_errors'] if e['severity'] == 'CRITICAL']) +
            len([e for e in results['import_errors'] if e['severity'] == 'CRITICAL'])
        )
        
        total_high = (
            len([e for e in results['syntax_errors'] if e['severity'] == 'HIGH']) +
            len([e for e in results['import_errors'] if e['severity'] == 'HIGH']) +
            len(results['missing_dependencies']) +
            len(results['database_issues'])
        )
        
        total_medium = (
            len(results['environment_issues']) +
            len([e for e in results['database_issues'] if e['severity'] == 'MEDIUM'])
        )
        
        print(f"\n📊 Validation Results:")
        print(f"  🔴 Critical issues: {total_critical}")
        print(f"  🟠 High priority issues: {total_high}")
        print(f"  🟡 Medium priority issues: {total_medium}")
        
        if total_critical > 0:
            print(f"\n🚨 CRITICAL: Applications will NOT start due to {total_critical} critical issues")
            print("📝 Fix critical issues before attempting to run applications")
        elif total_high > 0:
            print(f"\n⚠️ HIGH PRIORITY: Applications may not start due to {total_high} high priority issues")
            print("📝 Recommended to fix high priority issues before deployment")
        else:
            print(f"\n✅ Applications should start successfully!")
            if total_medium > 0:
                print(f"📝 {total_medium} medium priority issues may affect functionality")
        
        return results

def main():
    validator = AppStartupValidator()
    results = validator.run_comprehensive_validation()
    
    # Show detailed issues if any
    if any(results.values():
        print(f"\n📋 Detailed Issues:")
        
        for category, issues in results.items():
            if issues:
                print(f"\n{category.replace('_', ' ').title()}:")
                for issue in issues[:5]:  # Show first 5 of each type
                    severity = issue.get('severity', 'UNKNOWN')
                    if 'file' in issue:
                        print(f"  {severity}: {issue['file']}:{issue.get('line', '?')} - {issue['error']}")
                    elif 'module' in issue:
                        print(f"  {severity}: {issue['module']} - {issue['error']}")
                    elif 'dependency' in issue:
                        print(f"  {severity}: Missing {issue['dependency']}")
                    elif 'variable' in issue:
                        print(f"  {severity}: Environment variable {issue['variable']} not set")
                    else:
                        print(f"  {severity}: {issue}")

if __name__ == "__main__":
    main()