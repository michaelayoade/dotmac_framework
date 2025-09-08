#!/usr/bin/env python3
"""
DotMac Framework Targeted Gap Analysis
Focuses on specific, actionable improvements for critical areas
"""
import os
import re
import ast
import json
from pathlib import Path
from typing import Dict, List, Any, Set
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class TargetedGapAnalyzer:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.critical_security_files = []
        self.missing_base_classes = []
        self.inconsistent_patterns = []
        self.unprotected_endpoints = []
        self.missing_error_handling = []
        self.performance_bottlenecks = []
        
    def analyze_critical_security_gaps(self):
        """Analyze critical security vulnerabilities with specific examples"""
        logger.info("Analyzing critical security gaps...")
        
        security_issues = {
            'hardcoded_secrets': [],
            'sql_injection_risks': [],
            'unvalidated_endpoints': [],
            'missing_auth_decorators': [],
            'weak_error_handling': []
        }
        
        # Check for hardcoded secrets in specific high-risk files
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', 'hardcoded_password'),
            (r'secret\s*=\s*["\'][^"\']{10,}["\']', 'hardcoded_secret'),
            (r'api_key\s*=\s*["\'][^"\']+["\']', 'hardcoded_api_key'),
            (r'jwt_secret\s*=\s*["\'][^"\']+["\']', 'hardcoded_jwt'),
        ]
        
        # Files to specifically check for security issues
        high_risk_patterns = [
            'auth*', 'security*', '*middleware*', '*router*', 'api/*'
        ]
        
        for pattern in high_risk_patterns:
            for file_path in self.root_path.rglob(f"{pattern}.py"):
                if self._should_analyze_file(file_path):
                    self._analyze_file_security(file_path, secret_patterns, security_issues)
                    
        return security_issues
        
    def _analyze_file_security(self, file_path: Path, patterns: List, results: Dict):
        """Analyze individual file for security issues"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for pattern, issue_type in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    results['hardcoded_secrets'].append({
                        'file': str(file_path),
                        'issue': issue_type,
                        'matches': len(matches),
                        'line_examples': self._find_line_numbers(content, pattern)
                    })
                    
            # Check for SQL injection risks
            if '.execute(' in content and 'f"' in content:
                sql_risks = re.findall(r'\.execute\([^)]*f"[^"]*\{[^}]+\}', content)
                if sql_risks:
                    results['sql_injection_risks'].append({
                        'file': str(file_path),
                        'risk_count': len(sql_risks),
                        'examples': sql_risks[:3]
                    })
                    
            # Check for unvalidated API endpoints
            if '@router.' in content or '@app.' in content:
                endpoint_risks = self._check_endpoint_validation(content, file_path)
                if endpoint_risks:
                    results['unvalidated_endpoints'].extend(endpoint_risks)
                    
        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")
            
    def _check_endpoint_validation(self, content: str, file_path: Path) -> List[Dict]:
        """Check API endpoints for missing validation"""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Find route definitions
            if re.search(r'@router\.(get|post|put|delete|patch)', line):
                # Check next few lines for validation
                validation_found = False
                for j in range(i, min(i + 10, len(lines))):
                    if any(keyword in lines[j] for keyword in [
                        'Depends(', 'validate_', 'check_', '@validate', 'pydantic'
                    ]):
                        validation_found = True
                        break
                        
                if not validation_found and 'request:' in ''.join(lines[i:i+5]):
                    issues.append({
                        'file': str(file_path),
                        'line': i,
                        'endpoint': line.strip(),
                        'issue': 'missing_input_validation'
                    })
                    
        return issues
        
    def _find_line_numbers(self, content: str, pattern: str) -> List[int]:
        """Find line numbers for pattern matches"""
        lines = content.split('\n')
        line_numbers = []
        
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                line_numbers.append(i)
                
        return line_numbers[:5]  # Return first 5 matches
        
    def analyze_architecture_inconsistencies(self):
        """Find specific architecture patterns that need standardization"""
        logger.info("Analyzing architecture inconsistencies...")
        
        inconsistencies = {
            'repository_patterns': [],
            'service_patterns': [],
            'middleware_patterns': [],
            'exception_handling': []
        }
        
        # Check repository patterns
        repo_files = list(self.root_path.rglob("*repository*.py"))
        base_patterns = self._analyze_base_class_usage(repo_files, 'Repository')
        inconsistencies['repository_patterns'] = base_patterns
        
        # Check service patterns  
        service_files = list(self.root_path.rglob("*service*.py"))
        service_patterns = self._analyze_base_class_usage(service_files, 'Service')
        inconsistencies['service_patterns'] = service_patterns
        
        # Check middleware consistency
        middleware_files = list(self.root_path.rglob("*middleware*.py"))
        middleware_patterns = self._analyze_middleware_patterns(middleware_files)
        inconsistencies['middleware_patterns'] = middleware_patterns
        
        return inconsistencies
        
    def _analyze_base_class_usage(self, files: List[Path], class_type: str) -> List[Dict]:
        """Analyze usage of base classes in files"""
        issues = []
        base_class_usage = defaultdict(list)
        
        for file_path in files:
            if not self._should_analyze_file(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for class definitions
                class_matches = re.findall(rf'class\s+(\w*{class_type}\w*)\s*\([^)]*\):', content)
                
                for class_name in class_matches:
                    # Check if using base class
                    if 'Base' in content or 'ABC' in content:
                        base_class_usage['with_base'].append({
                            'file': str(file_path),
                            'class': class_name
                        })
                    else:
                        base_class_usage['without_base'].append({
                            'file': str(file_path), 
                            'class': class_name
                        })
                        
            except Exception as e:
                continue
                
        # If more than 3 classes without base, it's an issue
        if len(base_class_usage['without_base']) > 3:
            issues.append({
                'type': f'inconsistent_{class_type.lower()}_inheritance',
                'description': f"Found {len(base_class_usage['without_base'])} {class_type} classes without base class",
                'examples': base_class_usage['without_base'][:5],
                'recommendation': f"Create a base {class_type} class and standardize inheritance"
            })
            
        return issues
        
    def _analyze_middleware_patterns(self, files: List[Path]) -> List[Dict]:
        """Analyze middleware implementation patterns"""
        patterns = []
        middleware_types = defaultdict(list)
        
        for file_path in files:
            if not self._should_analyze_file(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check middleware patterns
                if 'async def __call__' in content:
                    middleware_types['asgi'].append(str(file_path))
                elif 'def process_request' in content:
                    middleware_types['django_style'].append(str(file_path))
                elif '@middleware' in content:
                    middleware_types['decorator_style'].append(str(file_path))
                else:
                    middleware_types['other'].append(str(file_path))
                    
            except Exception as e:
                continue
                
        # Check for consistency
        if len(middleware_types) > 2:
            patterns.append({
                'type': 'inconsistent_middleware_patterns',
                'description': f"Found {len(middleware_types)} different middleware patterns",
                'patterns': dict(middleware_types),
                'recommendation': "Standardize on ASGI middleware pattern"
            })
            
        return patterns
        
    def analyze_missing_error_handling(self):
        """Find files with inadequate error handling"""
        logger.info("Analyzing error handling gaps...")
        
        issues = []
        critical_files = []
        
        # Focus on API routes and services
        for pattern in ['*router*.py', '*service*.py', '*api*.py']:
            critical_files.extend(self.root_path.rglob(pattern))
            
        for file_path in critical_files:
            if not self._should_analyze_file(file_path):
                continue
                
            error_issues = self._check_error_handling(file_path)
            if error_issues:
                issues.extend(error_issues)
                
        return issues
        
    def _check_error_handling(self, file_path: Path) -> List[Dict]:
        """Check specific file for error handling issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            lines = content.split('\n')
            
            # Check for bare except clauses
            for i, line in enumerate(lines, 1):
                if re.search(r'except\s*:', line):
                    issues.append({
                        'file': str(file_path),
                        'line': i,
                        'issue': 'bare_except_clause',
                        'severity': 'high',
                        'recommendation': 'Use specific exception types'
                    })
                    
            # Check for try blocks without logging
            try_blocks = []
            for i, line in enumerate(lines):
                if line.strip().startswith('try:'):
                    # Look for corresponding except block
                    for j in range(i + 1, min(i + 20, len(lines))):
                        if lines[j].strip().startswith('except'):
                            # Check if logging is present in except block
                            except_block = []
                            for k in range(j, min(j + 10, len(lines))):
                                if lines[k].strip().startswith(('def ', 'class ', 'try:', 'if ', 'for ')):
                                    break
                                except_block.append(lines[k])
                                
                            except_content = '\n'.join(except_block)
                            if not any(keyword in except_content for keyword in [
                                'logger', 'log.', 'logging', 'print('
                            ]):
                                issues.append({
                                    'file': str(file_path),
                                    'line': j + 1,
                                    'issue': 'missing_error_logging',
                                    'severity': 'medium',
                                    'recommendation': 'Add error logging in exception handlers'
                                })
                            break
                            
        except Exception as e:
            logger.warning(f"Failed to check error handling in {file_path}: {e}")
            
        return issues
        
    def analyze_performance_bottlenecks(self):
        """Find specific performance issues"""
        logger.info("Analyzing performance bottlenecks...")
        
        bottlenecks = {
            'n_plus_one_queries': [],
            'missing_async': [],
            'inefficient_loops': [],
            'missing_caching': []
        }
        
        # Focus on service and repository files
        perf_files = []
        for pattern in ['*service*.py', '*repository*.py', '*api*.py']:
            perf_files.extend(self.root_path.rglob(pattern))
            
        for file_path in perf_files:
            if not self._should_analyze_file(file_path):
                continue
                
            perf_issues = self._check_performance_issues(file_path)
            for issue_type, issues in perf_issues.items():
                bottlenecks[issue_type].extend(issues)
                
        return bottlenecks
        
    def _check_performance_issues(self, file_path: Path) -> Dict[str, List]:
        """Check file for performance issues"""
        issues = {
            'n_plus_one_queries': [],
            'missing_async': [],
            'inefficient_loops': [],
            'missing_caching': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            lines = content.split('\n')
            
            # Check for N+1 query patterns
            for i, line in enumerate(lines):
                if 'for ' in line and i + 1 < len(lines):
                    next_line = lines[i + 1] if i + 1 < len(lines) else ''
                    if any(keyword in next_line for keyword in [
                        '.query(', '.get(', '.filter(', 'session.execute'
                    ]):
                        issues['n_plus_one_queries'].append({
                            'file': str(file_path),
                            'line': i + 1,
                            'code': line.strip() + ' -> ' + next_line.strip()
                        })
                        
            # Check for missing async in database operations
            if 'async def' in content:
                for i, line in enumerate(lines):
                    if any(keyword in line for keyword in ['.execute(', '.query(', '.get(']):
                        if 'await ' not in line:
                            issues['missing_async'].append({
                                'file': str(file_path),
                                'line': i + 1,
                                'code': line.strip()
                            })
                            
            # Check for inefficient loops
            for i, line in enumerate(lines):
                if 'for ' in line and '.append(' in ''.join(lines[i:i+5]):
                    if '[' in line or 'list(' in ''.join(lines[max(0, i-3):i]):
                        issues['inefficient_loops'].append({
                            'file': str(file_path),
                            'line': i + 1,
                            'recommendation': 'Consider list comprehension'
                        })
                        
        except Exception as e:
            logger.warning(f"Failed to check performance in {file_path}: {e}")
            
        return issues
        
    def _should_analyze_file(self, file_path: Path) -> bool:
        """Determine if file should be analyzed"""
        exclude_patterns = [
            '/.venv/', '/node_modules/', '/.git/', '/__pycache__/',
            '/migrations/', '/test-reports/', '/htmlcov/', 
            '/.dev-artifacts/', '/frontend/', '/tests/',
            '/venv/', '/.mypy_cache/', '/.ruff_cache/'
        ]
        path_str = str(file_path)
        return not any(pattern in path_str for pattern in exclude_patterns)
        
    def generate_actionable_report(self) -> Dict[str, Any]:
        """Generate report with specific, actionable recommendations"""
        logger.info("Generating actionable recommendations report...")
        
        security_gaps = self.analyze_critical_security_gaps()
        architecture_gaps = self.analyze_architecture_inconsistencies()
        error_gaps = self.analyze_missing_error_handling()
        performance_gaps = self.analyze_performance_bottlenecks()
        
        # Prioritize issues by severity and impact
        critical_actions = []
        high_actions = []
        medium_actions = []
        
        # Security issues are critical
        for issue_type, issues in security_gaps.items():
            if issues:
                critical_actions.append({
                    'category': 'Security',
                    'issue': issue_type,
                    'count': len(issues),
                    'examples': issues[:3],
                    'action': self._get_security_action(issue_type),
                    'priority': 'CRITICAL'
                })
                
        # Architecture inconsistencies are high priority
        for issue_type, issues in architecture_gaps.items():
            if issues:
                high_actions.append({
                    'category': 'Architecture',
                    'issue': issue_type,
                    'count': len(issues),
                    'examples': issues[:3],
                    'action': self._get_architecture_action(issue_type),
                    'priority': 'HIGH'
                })
                
        # Error handling gaps
        if error_gaps:
            high_actions.append({
                'category': 'Error Handling',
                'issue': 'inadequate_error_handling',
                'count': len(error_gaps),
                'examples': error_gaps[:5],
                'action': 'Implement standardized error handling with logging',
                'priority': 'HIGH'
            })
            
        # Performance issues are medium priority
        for issue_type, issues in performance_gaps.items():
            if issues:
                medium_actions.append({
                    'category': 'Performance',
                    'issue': issue_type,
                    'count': len(issues),
                    'examples': issues[:3],
                    'action': self._get_performance_action(issue_type),
                    'priority': 'MEDIUM'
                })
                
        return {
            'summary': {
                'total_critical': len(critical_actions),
                'total_high': len(high_actions),
                'total_medium': len(medium_actions),
                'analysis_date': '2025-09-07'
            },
            'critical_actions': critical_actions,
            'high_priority_actions': high_actions,
            'medium_priority_actions': medium_actions,
            'implementation_roadmap': self._create_implementation_roadmap(
                critical_actions, high_actions, medium_actions
            )
        }
        
    def _get_security_action(self, issue_type: str) -> str:
        """Get specific action for security issue"""
        actions = {
            'hardcoded_secrets': 'Move all secrets to environment variables or vault',
            'sql_injection_risks': 'Use parameterized queries and ORM methods',
            'unvalidated_endpoints': 'Add Pydantic models for all API inputs',
            'missing_auth_decorators': 'Add authentication decorators to all endpoints',
            'weak_error_handling': 'Implement secure error responses without info leakage'
        }
        return actions.get(issue_type, 'Review and fix security issue')
        
    def _get_architecture_action(self, issue_type: str) -> str:
        """Get specific action for architecture issue"""
        actions = {
            'repository_patterns': 'Create BaseRepository class and standardize inheritance',
            'service_patterns': 'Create BaseService class with common methods',
            'middleware_patterns': 'Standardize on ASGI middleware pattern',
            'exception_handling': 'Implement global exception handler with custom exceptions'
        }
        return actions.get(issue_type, 'Review and standardize pattern')
        
    def _get_performance_action(self, issue_type: str) -> str:
        """Get specific action for performance issue"""  
        actions = {
            'n_plus_one_queries': 'Use eager loading with joinedload() or selectinload()',
            'missing_async': 'Add await to database operations in async functions',
            'inefficient_loops': 'Replace loops with list comprehensions or bulk operations',
            'missing_caching': 'Add Redis caching for expensive operations'
        }
        return actions.get(issue_type, 'Optimize performance issue')
        
    def _create_implementation_roadmap(self, critical, high, medium) -> Dict[str, Any]:
        """Create implementation roadmap"""
        return {
            'phase_1_immediate': {
                'description': 'Fix critical security vulnerabilities',
                'duration': '1-2 weeks',
                'actions': [action['issue'] for action in critical],
                'success_metrics': 'Zero hardcoded secrets, all endpoints validated'
            },
            'phase_2_architecture': {
                'description': 'Standardize architecture patterns',
                'duration': '3-4 weeks', 
                'actions': [action['issue'] for action in high],
                'success_metrics': 'Consistent base classes, standardized error handling'
            },
            'phase_3_performance': {
                'description': 'Optimize performance bottlenecks',
                'duration': '2-3 weeks',
                'actions': [action['issue'] for action in medium],
                'success_metrics': 'Reduced query counts, improved response times'
            }
        }

if __name__ == "__main__":
    analyzer = TargetedGapAnalyzer("/home/dotmac_framework")
    report = analyzer.generate_actionable_report()
    
    # Save report
    output_path = "/home/dotmac_framework/.dev-artifacts/analysis/targeted_gap_analysis.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
        
    print(f"Targeted analysis complete! Report saved to {output_path}")
    print(f"Critical issues: {report['summary']['total_critical']}")
    print(f"High priority issues: {report['summary']['total_high']}")
    print(f"Medium priority issues: {report['summary']['total_medium']}")