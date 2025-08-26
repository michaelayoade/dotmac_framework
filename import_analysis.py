#!/usr/bin/env python3
"""
Comprehensive Import Issue Analysis for DotMac SaaS Platform
Analyzes all potential import issues after dependency consolidation.
"""

import ast
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple
import subprocess

class ImportIssueAnalyzer:
    def __init__(self, root_path: str = "/home/dotmac_framework"):
        self.root_path = Path(root_path)
        
        # Define our unified requirements as the source of truth
        self.unified_requirements = self._load_unified_requirements()
        
        # Define packages that should be mocked (from our docs strategy)
        self.mocked_packages = {
            'stripe', 'twilio', 'boto3', 'aiobotocore', 'azure', 'google-cloud',
            'pysnmp', 'netmiko', 'napalm', 'paramiko', 'ansible', 'ansible-runner',
            'opentelemetry', 'opentelemetry-api', 'opentelemetry-sdk',
            'opentelemetry-instrumentation', 'opentelemetry-instrumentation-fastapi',
            'opentelemetry-instrumentation-sqlalchemy', 'opentelemetry-instrumentation-redis',
            'opentelemetry-instrumentation-celery', 'opentelemetry-instrumentation-httpx'
        }
        
        # Component-specific imports that are expected
        self.component_specific = {
            'isp-framework': {'voltha', 'freeradius', 'networkx', 'grpc', 'radius'},
            'management-platform': {'kubernetes', 'docker', 'opentofu', 'chargebee'},
            'docs': {'sphinx', 'myst', 'sphinx-rtd-theme'},
            'frontend': {'node', 'npm', 'react', 'next'}
        }

    def _load_unified_requirements(self) -> Set[str]:
        """Load packages from our unified requirements."""
        unified_file = self.root_path / "requirements-unified.txt"
        if not unified_file.exists():
            return set()
        
        packages = set()
        with open(unified_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    if '==' in line:
                        pkg_name = line.split('==')[0].split('[')[0].strip()
                        packages.add(pkg_name)
                    elif '>=' in line:
                        pkg_name = line.split('>=')[0].split('[')[0].strip()
                        packages.add(pkg_name)
        return packages

    def extract_imports_from_file(self, filepath: Path) -> List[str]:
        """Extract all imports from a Python file."""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            tree = ast.parse(content)
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module.split('.')[0])
            
            return imports
        except Exception as e:
            return []

    def analyze_all_imports(self) -> Dict:
        """Analyze imports across all components."""
        print("🔍 Analyzing imports across DotMac SaaS Platform...")
        
        # Component paths
        components = {
            'isp-framework': self.root_path / "isp-framework" / "src",
            'management-platform': self.root_path / "management-platform" / "app",
            'scripts': self.root_path / "scripts",
            'shared': self.root_path / "shared"
        }
        
        all_imports = defaultdict(set)  # package -> components using it
        component_imports = {}          # component -> imports
        import_files = defaultdict(list)  # package -> files using it
        
        for component, comp_path in components.items():
            if not comp_path.exists():
                continue
                
            comp_imports = set()
            for py_file in comp_path.rglob('*.py'):
                file_imports = self.extract_imports_from_file(py_file)
                comp_imports.update(file_imports)
                
                for imp in file_imports:
                    all_imports[imp].add(component)
                    import_files[imp].append(str(py_file.relative_to(self.root_path)))
            
            component_imports[component] = comp_imports
            print(f"  {component}: {len(comp_imports)} unique imports")
        
        return {
            'all_imports': dict(all_imports),
            'component_imports': component_imports,
            'import_files': dict(import_files),
            'total_unique': len(all_imports)
        }

    def identify_import_issues(self, analysis: Dict) -> Dict:
        """Identify potential import issues."""
        print("\n🚨 Identifying Import Issues...")
        
        issues = {
            'missing_from_unified': [],      # In code but not in requirements
            'version_conflicts': [],         # Different versions needed
            'mocked_but_imported': [],       # Should be mocked but directly imported
            'component_specific_conflicts': [],  # Wrong component importing
            'unused_in_requirements': [],    # In requirements but not used
            'circular_dependencies': [],     # Circular import issues
            'dangerous_imports': []          # Security/stability risks
        }
        
        all_imports = analysis['all_imports']
        
        # Check for imports missing from unified requirements
        for package, components in all_imports.items():
            # Skip standard library and local imports
            if self._is_stdlib_or_local(package):
                continue
            
            if package not in self.unified_requirements:
                if package in self.mocked_packages:
                    issues['mocked_but_imported'].append({
                        'package': package,
                        'components': list(components),
                        'severity': 'HIGH',
                        'reason': f'Package {package} should be mocked in docs, not directly imported'
                    })
                elif any(package in comp_specific for comp_specific in self.component_specific.values():
                    # Component-specific import - check if it's in the right component
                    expected_components = []
                    for comp, packages in self.component_specific.items():
                        if package in packages:
                            expected_components.append(comp)
                    
                    wrong_components = set(components) - set(expected_components)
                    if wrong_components:
                        issues['component_specific_conflicts'].append({
                            'package': package,
                            'wrong_components': list(wrong_components),
                            'expected_components': expected_components,
                            'severity': 'MEDIUM'
                        })
                else:
                    issues['missing_from_unified'].append({
                        'package': package,
                        'components': list(components),
                        'severity': 'HIGH',
                        'files': analysis['import_files'].get(package, [])[:5]  # First 5 files
                    })
        
        # Check for dangerous imports
        dangerous_patterns = {
            'eval': 'Code injection risk',
            'exec': 'Code execution risk', 
            'os.system': 'Command injection risk',
            'subprocess': 'Command execution - verify sanitization',
            'pickle': 'Deserialization vulnerability',
            'yaml.load': 'YAML bomb vulnerability - use safe_load',
            'xml': 'XML parsing vulnerabilities possible'
        }
        
        for dangerous, reason in dangerous_patterns.items():
            if dangerous in all_imports:
                issues['dangerous_imports'].append({
                    'package': dangerous,
                    'reason': reason,
                    'components': list(all_imports[dangerous]),
                    'severity': 'CRITICAL',
                    'files': analysis['import_files'].get(dangerous, [])[:3]
                })
        
        return issues

    def _is_stdlib_or_local(self, package: str) -> bool:
        """Check if package is standard library or local."""
        stdlib_packages = {
            'json', 'os', 'sys', 'logging', 'typing', 'pathlib', 'datetime',
            'asyncio', 'uuid', 're', 'hashlib', 'time', 'tempfile', 'email',
            'dataclasses', 'functools', 'collections', 'itertools', 'operator',
            'contextlib', 'concurrent', 'multiprocessing', 'threading', 'queue',
            'socket', 'ssl', 'http', 'urllib', 'base64', 'hmac', 'secrets',
            'math', 'statistics', 'random', 'decimal', 'fractions',
            'csv', 'configparser', 'argparse', 'shlex', 'glob', 'fnmatch',
            'subprocess', 'shutil', 'tarfile', 'zipfile', 'gzip', 'bz2'
        }
        
        local_packages = {
            'dotmac_isp', 'management_platform', 'shared', 'plugins',
            'app', 'core', 'api', 'models', 'services', 'repositories'
        }
        
        return package in stdlib_packages or package in local_packages

    def generate_fixes(self, issues: Dict) -> List[str]:
        """Generate actionable fixes for import issues."""
        fixes = []
        
        # Fix 1: Add missing packages to unified requirements
        if issues['missing_from_unified']:
            fixes.append("🔧 ADD TO UNIFIED REQUIREMENTS:")
            for issue in issues['missing_from_unified']:
                fixes.append(f"   {issue['package']}  # Used in {', '.join(issue['components'])}")
        
        # Fix 2: Update docs mock imports
        if issues['mocked_but_imported']:
            fixes.append("\n🔧 UPDATE DOCS MOCK IMPORTS (these should NOT be in requirements):")
            for issue in issues['mocked_but_imported']:
                fixes.append(f"   # Remove {issue['package']} from requirements, ensure it's in autodoc_mock_imports")
        
        # Fix 3: Component architecture violations
        if issues['component_specific_conflicts']:
            fixes.append("\n🔧 COMPONENT ARCHITECTURE VIOLATIONS:")
            for issue in issues['component_specific_conflicts']:
                fixes.append(f"   {issue['package']}: Move from {issue['wrong_components']} to {issue['expected_components']}")
        
        # Fix 4: Security issues
        if issues['dangerous_imports']:
            fixes.append("\n🔧 SECURITY ISSUES (HIGH PRIORITY):")
            for issue in issues['dangerous_imports']:
                fixes.append(f"   {issue['package']}: {issue['reason']}")
                fixes.append(f"     Files: {', '.join(issue['files'][:2])}")
        
        return fixes

    def run_complete_analysis(self):
        """Run complete import analysis and generate report."""
        print("🚀 DotMac SaaS Platform Import Analysis")
        print("=" * 60)
        
        # Analyze all imports
        analysis = self.analyze_all_imports()
        
        # Identify issues
        issues = self.identify_import_issues(analysis)
        
        # Generate report
        print(f"\n📊 Import Analysis Summary:")
        print(f"   Total unique imports: {analysis['total_unique']}")
        print(f"   Packages in unified requirements: {len(self.unified_requirements)}")
        print(f"   Mocked packages (should not be in requirements): {len(self.mocked_packages)}")
        
        print(f"\n🚨 Issues Found:")
        print(f"   Missing from unified requirements: {len(issues['missing_from_unified'])}")
        print(f"   Should be mocked (not imported): {len(issues['mocked_but_imported'])}")
        print(f"   Component architecture violations: {len(issues['component_specific_conflicts'])}")
        print(f"   Security concerns: {len(issues['dangerous_imports'])}")
        
        # Generate fixes
        fixes = self.generate_fixes(issues)
        
        if fixes:
            print(f"\n🔧 Recommended Fixes:")
            for fix in fixes:
                print(fix)
        else:
            print(f"\n✅ No critical import issues found!")
        
        # Critical issues summary
        critical_count = (
            len(issues['missing_from_unified']) + 
            len(issues['mocked_but_imported']) + 
            len(issues['dangerous_imports'])
        )
        
        print(f"\n🎯 Action Required:")
        if critical_count == 0:
            print("   ✅ All imports look good for dependency consolidation!")
        else:
            print(f"   ⚠️  {critical_count} critical issues need resolution before consolidation")
            print("   📝 Fix these issues, then re-run dependency consolidation")
        
        return analysis, issues

def main():
    analyzer = ImportIssueAnalyzer()
    analysis, issues = analyzer.run_complete_analysis()
    
    # Save detailed report
    import json
    report_file = Path("/home/dotmac_framework/import_analysis_report.json")
    with open(report_file, 'w') as f:
        json.dump({
            'analysis': {
                'all_imports': analysis['all_imports'],
                'total_unique': analysis['total_unique']
            },
            'issues': issues
        }, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {report_file}")

if __name__ == "__main__":
    main()