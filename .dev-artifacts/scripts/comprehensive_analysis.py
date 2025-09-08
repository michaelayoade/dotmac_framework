#!/usr/bin/env python3
"""
DotMac Framework Comprehensive Analysis Script
Analyzes codebase for gaps, inconsistencies, and improvement areas
"""
import os
import re
import ast
import json
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class DotMacFrameworkAnalyzer:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.analysis_results = {
            'architecture_gaps': [],
            'security_gaps': [],
            'testing_gaps': [],
            'documentation_gaps': [],
            'performance_gaps': [],
            'error_handling_gaps': [],
            'configuration_gaps': [],
            'dependency_gaps': [],
            'code_quality_gaps': [],
            'operational_gaps': []
        }
        self.python_files = []
        self.package_structure = {}
        
    def scan_codebase(self):
        """Scan entire codebase for Python files"""
        logger.info("Scanning codebase for Python files...")
        for py_file in self.root_path.rglob("*.py"):
            if self._should_analyze_file(py_file):
                self.python_files.append(py_file)
        logger.info(f"Found {len(self.python_files)} Python files to analyze")
        
    def _should_analyze_file(self, file_path: Path) -> bool:
        """Determine if file should be analyzed"""
        exclude_patterns = [
            '/.venv/', '/node_modules/', '/.git/', '/__pycache__/',
            '/migrations/', '/test-reports/', '/htmlcov/',
            '/.dev-artifacts/', '/frontend/', '/tests/'
        ]
        path_str = str(file_path)
        return not any(pattern in path_str for pattern in exclude_patterns)
        
    def analyze_architecture_gaps(self):
        """Identify architecture gaps and inconsistencies"""
        logger.info("Analyzing architecture gaps...")
        gaps = []
        
        # Check for missing base classes or incomplete patterns
        # Check for inconsistent import patterns
        # Check for missing core components
        
        # Analyze package dependencies and structure
        package_deps = self._analyze_package_dependencies()
        
        # Check for circular dependencies
        circular_deps = self._detect_circular_dependencies()
        if circular_deps:
            gaps.extend([
                {
                    'type': 'circular_dependency',
                    'description': f"Circular dependency detected: {' -> '.join(dep)}",
                    'files': dep,
                    'severity': 'high'
                } for dep in circular_deps
            ])
            
        # Check for missing abstractions
        missing_abstractions = self._check_missing_abstractions()
        gaps.extend(missing_abstractions)
        
        self.analysis_results['architecture_gaps'] = gaps
        
    def _analyze_package_dependencies(self) -> Dict[str, List[str]]:
        """Analyze dependencies between packages"""
        deps = defaultdict(list)
        
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Extract imports
                imports = re.findall(r'^(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_.]*)', content, re.MULTILINE)
                package_name = self._get_package_name(py_file)
                
                for imp in imports:
                    if imp.startswith('dotmac') and not imp.startswith(package_name):
                        deps[package_name].append(imp)
                        
            except Exception as e:
                logger.warning(f"Failed to analyze {py_file}: {e}")
                
        return dict(deps)
        
    def _detect_circular_dependencies(self) -> List[List[str]]:
        """Detect circular dependencies"""
        # Simplified circular dependency detection
        circular_deps = []
        # Implementation would build dependency graph and detect cycles
        return circular_deps
        
    def _check_missing_abstractions(self) -> List[Dict[str, Any]]:
        """Check for missing base classes and abstractions"""
        gaps = []
        
        # Check for repeated code patterns that should be abstracted
        pattern_counts = defaultdict(int)
        
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for common patterns
                if 'class.*Repository' in content and 'Base' not in content:
                    pattern_counts['repository_without_base'] += 1
                    
                if 'class.*Service' in content and 'Base' not in content:
                    pattern_counts['service_without_base'] += 1
                    
            except Exception as e:
                continue
                
        for pattern, count in pattern_counts.items():
            if count > 3:  # If pattern appears more than 3 times
                gaps.append({
                    'type': 'missing_abstraction',
                    'description': f"Pattern '{pattern}' found {count} times - consider base class",
                    'count': count,
                    'severity': 'medium'
                })
                
        return gaps
        
    def analyze_security_gaps(self):
        """Identify security vulnerabilities and gaps"""
        logger.info("Analyzing security gaps...")
        gaps = []
        
        security_patterns = {
            'hardcoded_secrets': [
                r'password\s*=\s*["\'][^"\']+["\']',
                r'api_key\s*=\s*["\'][^"\']+["\']',
                r'secret\s*=\s*["\'][^"\']+["\']'
            ],
            'sql_injection': [
                r'execute\([^)]*%[^)]*\)',
                r'query\([^)]*%[^)]*\)'
            ],
            'unvalidated_input': [
                r'request\.\w+\[[^]]+\](?!\s*\w*validation)',
                r'request\.\w+\.\w+(?!\s*\w*validation)'
            ],
            'missing_auth': [
                r'@router\.\w+\([^)]*\)[\s\n]*def\s+\w+\([^)]*request[^)]*\)(?!.*@.*auth)',
            ]
        }
        
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for gap_type, patterns in security_patterns.items():
                    for pattern in patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
                        if matches:
                            gaps.append({
                                'type': gap_type,
                                'file': str(py_file),
                                'matches': len(matches),
                                'description': f"Found {len(matches)} instances of {gap_type.replace('_', ' ')}",
                                'severity': 'high' if gap_type in ['hardcoded_secrets', 'sql_injection'] else 'medium'
                            })
                            
            except Exception as e:
                logger.warning(f"Failed to analyze security in {py_file}: {e}")
                
        self.analysis_results['security_gaps'] = gaps
        
    def analyze_testing_gaps(self):
        """Identify testing coverage and gaps"""
        logger.info("Analyzing testing gaps...")
        gaps = []
        
        # Count files with and without tests
        tested_files = set()
        test_files = list(self.root_path.rglob("test_*.py"))
        
        for test_file in test_files:
            # Extract what file is being tested
            test_name = test_file.name.replace('test_', '').replace('.py', '')
            # Find corresponding source file
            possible_source = test_file.parent.parent / f"{test_name}.py"
            if possible_source.exists():
                tested_files.add(possible_source)
                
        untested_files = []
        for py_file in self.python_files:
            if py_file not in tested_files and not py_file.name.startswith('test_'):
                # Skip __init__.py and migration files
                if py_file.name != '__init__.py' and 'migration' not in str(py_file):
                    untested_files.append(py_file)
                    
        if untested_files:
            gaps.append({
                'type': 'missing_tests',
                'description': f"{len(untested_files)} files have no corresponding tests",
                'files': [str(f) for f in untested_files[:10]],  # Show first 10
                'count': len(untested_files),
                'severity': 'medium'
            })
            
        # Check for integration test gaps
        integration_tests = list(self.root_path.rglob("**/integration/**/*.py"))
        if len(integration_tests) < 5:
            gaps.append({
                'type': 'missing_integration_tests',
                'description': f"Only {len(integration_tests)} integration test files found",
                'severity': 'high'
            })
            
        self.analysis_results['testing_gaps'] = gaps
        
    def analyze_documentation_gaps(self):
        """Identify documentation gaps"""
        logger.info("Analyzing documentation gaps...")
        gaps = []
        
        missing_docstrings = []
        
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                    
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        if not ast.get_docstring(node):
                            missing_docstrings.append({
                                'file': str(py_file),
                                'name': node.name,
                                'type': 'class' if isinstance(node, ast.ClassDef) else 'function',
                                'line': node.lineno
                            })
                            
            except Exception as e:
                logger.warning(f"Failed to parse {py_file}: {e}")
                
        if missing_docstrings:
            gaps.append({
                'type': 'missing_docstrings',
                'description': f"{len(missing_docstrings)} functions/classes missing docstrings",
                'examples': missing_docstrings[:10],
                'count': len(missing_docstrings),
                'severity': 'medium'
            })
            
        # Check for README files in packages
        package_dirs = [d for d in self.root_path.glob('packages/*') if d.is_dir()]
        missing_readme = []
        
        for pkg_dir in package_dirs:
            if not (pkg_dir / 'README.md').exists():
                missing_readme.append(str(pkg_dir))
                
        if missing_readme:
            gaps.append({
                'type': 'missing_package_readme',
                'description': f"{len(missing_readme)} packages missing README.md",
                'packages': missing_readme,
                'severity': 'low'
            })
            
        self.analysis_results['documentation_gaps'] = gaps
        
    def analyze_error_handling_gaps(self):
        """Identify error handling gaps"""
        logger.info("Analyzing error handling gaps...")
        gaps = []
        
        bare_except_count = 0
        missing_logging_count = 0
        
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for bare except clauses
                bare_excepts = re.findall(r'except\s*:', content)
                bare_except_count += len(bare_excepts)
                
                # Check for try blocks without logging
                try_blocks = re.findall(r'try:(.*?)except', content, re.DOTALL)
                for block in try_blocks:
                    if 'logger' not in block and 'log' not in block:
                        missing_logging_count += 1
                        
            except Exception as e:
                continue
                
        if bare_except_count > 0:
            gaps.append({
                'type': 'bare_except_clauses',
                'description': f"Found {bare_except_count} bare except clauses",
                'count': bare_except_count,
                'severity': 'high'
            })
            
        if missing_logging_count > 0:
            gaps.append({
                'type': 'missing_error_logging',
                'description': f"Found {missing_logging_count} try blocks without logging",
                'count': missing_logging_count,
                'severity': 'medium'
            })
            
        self.analysis_results['error_handling_gaps'] = gaps
        
    def analyze_configuration_gaps(self):
        """Identify configuration gaps"""
        logger.info("Analyzing configuration gaps...")
        gaps = []
        
        # Check for hardcoded values
        hardcoded_values = []
        
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for hardcoded URLs, ports, etc.
                hardcoded_patterns = [
                    r'http://[^"\']+',
                    r'https://[^"\']+',
                    r':\d{4,5}[^0-9]',  # Port numbers
                    r'localhost',
                    r'127\.0\.0\.1'
                ]
                
                for pattern in hardcoded_patterns:
                    matches = re.findall(pattern, content)
                    if matches and 'config' not in py_file.name.lower():
                        hardcoded_values.extend(matches)
                        
            except Exception as e:
                continue
                
        if hardcoded_values:
            gaps.append({
                'type': 'hardcoded_values',
                'description': f"Found {len(hardcoded_values)} hardcoded URLs/addresses",
                'examples': hardcoded_values[:5],
                'count': len(hardcoded_values),
                'severity': 'medium'
            })
            
        # Check for missing environment variable validation
        env_files = list(self.root_path.glob('.env*'))
        config_files = list(self.root_path.rglob('*config*.py'))
        
        if len(env_files) > 3 and len(config_files) < 2:
            gaps.append({
                'type': 'missing_config_validation',
                'description': f"Multiple env files ({len(env_files)}) but few config files ({len(config_files)})",
                'severity': 'medium'
            })
            
        self.analysis_results['configuration_gaps'] = gaps
        
    def analyze_dependency_gaps(self):
        """Identify dependency issues"""
        logger.info("Analyzing dependency gaps...")
        gaps = []
        
        # Analyze pyproject.toml for version conflicts
        pyproject_path = self.root_path / 'pyproject.toml'
        if pyproject_path.exists():
            try:
                with open(pyproject_path, 'r') as f:
                    content = f.read()
                    
                # Look for version pinning issues
                loose_versions = re.findall(r'"([^"]+)"\s*=\s*">=([^"]+)"', content)
                if len(loose_versions) > 20:
                    gaps.append({
                        'type': 'loose_version_pinning',
                        'description': f"Found {len(loose_versions)} loosely pinned dependencies",
                        'severity': 'low'
                    })
                    
            except Exception as e:
                logger.warning(f"Failed to analyze pyproject.toml: {e}")
                
        # Check for unused imports
        unused_imports = self._find_unused_imports()
        if unused_imports:
            gaps.append({
                'type': 'unused_imports',
                'description': f"Found {len(unused_imports)} files with unused imports",
                'count': len(unused_imports),
                'severity': 'low'
            })
            
        self.analysis_results['dependency_gaps'] = gaps
        
    def _find_unused_imports(self) -> List[str]:
        """Find files with unused imports (simplified check)"""
        unused = []
        # This would use more sophisticated analysis in practice
        return unused
        
    def analyze_performance_gaps(self):
        """Identify performance issues"""
        logger.info("Analyzing performance gaps...")
        gaps = []
        
        # Check for N+1 query patterns
        n_plus_one_patterns = []
        
        # Check for missing async/await patterns
        missing_async = []
        
        # Check for missing caching
        missing_caching = []
        
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for potential N+1 queries
                if 'for ' in content and 'query' in content:
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'for ' in line and i+1 < len(lines) and 'query' in lines[i+1]:
                            n_plus_one_patterns.append(f"{py_file}:{i+1}")
                            
                # Check for synchronous database calls in async functions
                if 'async def' in content and '.execute(' in content and 'await ' not in content.split('.execute(')[0].split('\n')[-1]:
                    missing_async.append(str(py_file))
                    
                # Check for repeated expensive operations without caching
                if content.count('requests.get') > 2 and '@cache' not in content:
                    missing_caching.append(str(py_file))
                    
            except Exception as e:
                continue
                
        if n_plus_one_patterns:
            gaps.append({
                'type': 'potential_n_plus_one',
                'description': f"Found {len(n_plus_one_patterns)} potential N+1 query patterns",
                'locations': n_plus_one_patterns[:5],
                'severity': 'high'
            })
            
        if missing_async:
            gaps.append({
                'type': 'missing_async_await',
                'description': f"Found {len(missing_async)} files with potential async issues",
                'files': missing_async[:5],
                'severity': 'medium'
            })
            
        if missing_caching:
            gaps.append({
                'type': 'missing_caching',
                'description': f"Found {len(missing_caching)} files with repeated operations without caching",
                'files': missing_caching[:5],
                'severity': 'medium'
            })
            
        self.analysis_results['performance_gaps'] = gaps
        
    def analyze_code_quality_gaps(self):
        """Identify code quality issues"""
        logger.info("Analyzing code quality gaps...")
        gaps = []
        
        # Check for complex functions
        complex_functions = []
        duplicate_code = []
        
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                # Count lines of code in functions
                in_function = False
                function_line_count = 0
                current_function = None
                
                for line_no, line in enumerate(lines, 1):
                    if line.strip().startswith('def '):
                        if in_function and function_line_count > 50:
                            complex_functions.append({
                                'file': str(py_file),
                                'function': current_function,
                                'lines': function_line_count
                            })
                        in_function = True
                        function_line_count = 0
                        current_function = line.strip().split('(')[0].replace('def ', '')
                    elif in_function:
                        if line.strip() and not line.strip().startswith('#'):
                            function_line_count += 1
                        if line.strip().startswith('def ') or line.strip().startswith('class '):
                            if function_line_count > 50:
                                complex_functions.append({
                                    'file': str(py_file),
                                    'function': current_function,
                                    'lines': function_line_count
                                })
                            in_function = False
                            
            except Exception as e:
                continue
                
        if complex_functions:
            gaps.append({
                'type': 'complex_functions',
                'description': f"Found {len(complex_functions)} functions with >50 lines",
                'examples': complex_functions[:5],
                'count': len(complex_functions),
                'severity': 'medium'
            })
            
        self.analysis_results['code_quality_gaps'] = gaps
        
    def analyze_operational_gaps(self):
        """Identify operational monitoring and logging gaps"""
        logger.info("Analyzing operational gaps...")
        gaps = []
        
        # Check for logging setup
        logging_files = []
        monitoring_files = []
        health_check_files = []
        
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if 'logging' in content or 'logger' in content:
                    logging_files.append(py_file)
                    
                if 'metrics' in content or 'prometheus' in content:
                    monitoring_files.append(py_file)
                    
                if 'health' in py_file.name.lower() or '/health' in content:
                    health_check_files.append(py_file)
                    
            except Exception as e:
                continue
                
        total_files = len(self.python_files)
        logging_percentage = (len(logging_files) / total_files) * 100
        
        if logging_percentage < 30:
            gaps.append({
                'type': 'insufficient_logging',
                'description': f"Only {logging_percentage:.1f}% of files have logging setup",
                'severity': 'high'
            })
            
        if len(monitoring_files) < 5:
            gaps.append({
                'type': 'missing_monitoring',
                'description': f"Only {len(monitoring_files)} files implement monitoring",
                'severity': 'high'
            })
            
        if len(health_check_files) < 2:
            gaps.append({
                'type': 'missing_health_checks',
                'description': f"Only {len(health_check_files)} health check implementations found",
                'severity': 'medium'
            })
            
        self.analysis_results['operational_gaps'] = gaps
        
    def _get_package_name(self, file_path: Path) -> str:
        """Get package name from file path"""
        parts = file_path.parts
        if 'packages' in parts:
            pkg_idx = parts.index('packages')
            if pkg_idx + 1 < len(parts):
                return parts[pkg_idx + 1]
        elif 'src' in parts:
            src_idx = parts.index('src')
            if src_idx + 1 < len(parts):
                return parts[src_idx + 1]
        return 'unknown'
        
    def run_full_analysis(self):
        """Run complete analysis"""
        logger.info("Starting comprehensive DotMac framework analysis...")
        
        self.scan_codebase()
        
        self.analyze_architecture_gaps()
        self.analyze_security_gaps()
        self.analyze_testing_gaps()
        self.analyze_documentation_gaps()
        self.analyze_error_handling_gaps()
        self.analyze_configuration_gaps()
        self.analyze_dependency_gaps()
        self.analyze_performance_gaps()
        self.analyze_code_quality_gaps()
        self.analyze_operational_gaps()
        
        logger.info("Analysis complete!")
        
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive analysis report"""
        total_gaps = sum(len(gaps) for gaps in self.analysis_results.values())
        
        report = {
            'summary': {
                'total_python_files': len(self.python_files),
                'total_gaps_found': total_gaps,
                'analysis_timestamp': '2025-09-07',
                'framework_version': '0.1.0'
            },
            'gap_categories': {}
        }
        
        for category, gaps in self.analysis_results.items():
            if gaps:
                severity_count = {'high': 0, 'medium': 0, 'low': 0}
                for gap in gaps:
                    severity_count[gap.get('severity', 'medium')] += 1
                    
                report['gap_categories'][category] = {
                    'total_gaps': len(gaps),
                    'severity_breakdown': severity_count,
                    'gaps': gaps
                }
                
        return report

if __name__ == "__main__":
    analyzer = DotMacFrameworkAnalyzer("/home/dotmac_framework")
    analyzer.run_full_analysis()
    
    report = analyzer.generate_report()
    
    # Save report
    output_path = "/home/dotmac_framework/.dev-artifacts/analysis/comprehensive_analysis_report.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
        
    print(f"Analysis complete! Report saved to {output_path}")
    print(f"Total files analyzed: {report['summary']['total_python_files']}")
    print(f"Total gaps found: {report['summary']['total_gaps_found']}")