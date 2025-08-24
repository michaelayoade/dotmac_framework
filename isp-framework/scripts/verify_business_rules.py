#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)

"""
Business Rules Verification - Ensure AI hasn't modified critical business logic.

This script verifies that core business rules and revenue-critical logic
remain intact and haven't been inadvertently modified by AI-generated code.
"""

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
import re


class BusinessRuleVerifier:
    """
    Verifies that critical business rules remain unchanged.
    """
    
    def __init__(self):
        # Critical business rules that should never change
        self.critical_business_rules = {
            # Billing rules
            'billing_calculation': {
                'files': ['*billing*', '*invoice*'],
                'rules': [
                    'Bills must never be negative',
                    'Tax calculation must use proper rates', 
                    'Discounts cannot exceed 100%',
                    'Pro-ration must be calculated correctly'
                ],
                'forbidden_changes': [
                    r'amount\s*\*=\s*-1',  # Negative amount multiplication
                    r'total\s*=\s*0',      # Setting total to zero
                    r'tax_rate\s*=\s*0',   # Eliminating tax
                    r'discount\s*=\s*1\.0|discount\s*=\s*100', # 100% discount
                ]
            },
            
            # Customer management rules
            'customer_lifecycle': {
                'files': ['*customer*', '*identity*'],
                'rules': [
                    'Customer numbers must be unique',
                    'Customer status transitions must be valid',
                    'Customer data must be preserved'
                ],
                'forbidden_changes': [
                    r'customer_number\s*=\s*None',
                    r'unique\s*=\s*False',
                    r'status\s*=\s*["\']deleted["\']',
                ]
            },
            
            # Payment processing rules  
            'payment_processing': {
                'files': ['*payment*', '*billing*'],
                'rules': [
                    'Payments must be validated before processing',
                    'Payment amounts must match invoice amounts',
                    'Refunds must be properly authorized'
                ],
                'forbidden_changes': [
                    r'skip_validation\s*=\s*True',
                    r'authorize\s*=\s*False',
                    r'amount\s*=\s*0',
                ]
            },
            
            # Service provisioning rules
            'service_provisioning': {
                'files': ['*service*', '*provision*'],
                'rules': [
                    'Services must be linked to paying customers',
                    'Service limits must be enforced',
                    'Service activation requires valid payment method'
                ],
                'forbidden_changes': [
                    r'bypass_payment_check\s*=\s*True',
                    r'unlimited\s*=\s*True',
                    r'skip_provisioning\s*=\s*True',
                ]
            }
        }
        
        # Revenue-critical functions that need extra scrutiny
        self.revenue_critical_functions = {
            'calculate_bill',
            'process_payment',
            'apply_discount',
            'calculate_tax',
            'generate_invoice',
            'refund_payment',
            'suspend_service',
            'activate_service'
        }
    
    def verify_file(self, file_path: Path) -> Dict[str, Any]:
        """Verify business rules in a specific file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return {'error': f"Failed to read {file_path}: {e}"}
        
        results = {
            'file': str(file_path),
            'violations': [],
            'warnings': [],
            'revenue_critical_functions': [],
            'business_rule_category': self._categorize_file(file_path)
        }
        
        # Check for forbidden patterns
        category = results['business_rule_category']
        if category and category in self.critical_business_rules:
            rule_set = self.critical_business_rules[category]
            for pattern in rule_set['forbidden_changes']:
                matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
                if matches:
                    results['violations'].append({
                        'rule': f"{category}_rule",
                        'pattern': pattern,
                        'matches': matches,
                        'severity': 'critical',
                        'description': f"Forbidden pattern detected in {category}"
                    })
        
        # Check for revenue-critical function modifications
        self._check_revenue_critical_functions(content, results)
        
        # Check for suspicious mathematical operations
        self._check_mathematical_operations(content, results)
        
        # Check for dangerous conditional bypasses
        self._check_conditional_bypasses(content, results)
        
        return results
    
    def _categorize_file(self, file_path: Path) -> str:
        """Categorize file based on business domain."""
        path_str = str(file_path).lower()
        
        for category, rule_set in self.critical_business_rules.items():
            for file_pattern in rule_set['files']:
                pattern = file_pattern.replace('*', '.*')
                if re.search(pattern, path_str):
                    return category
        
        return None
    
    def _check_revenue_critical_functions(self, content: str, results: Dict[str, Any]):
        """Check for modifications to revenue-critical functions."""
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name in self.revenue_critical_functions:
                        results['revenue_critical_functions'].append({
                            'name': node.name,
                            'line': node.lineno,
                            'complexity': self._calculate_complexity(node)
                        })
                        
                        # Check for suspicious modifications in critical functions
                        func_source = ast.get_source_segment(content, node)
                        if func_source:
                            self._analyze_critical_function(func_source, node.name, results)
                            
        except SyntaxError:
            results['warnings'].append({
                'type': 'syntax_error',
                'description': 'File contains syntax errors'
            })
    
    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Decision points that increase complexity
            if isinstance(child, (ast.If, ast.While, ast.For, ast.Try)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.BoolOp, ast.Compare)):
                # Boolean operations add complexity
                if isinstance(child, ast.BoolOp):
                    complexity += len(child.values) - 1
        
        return complexity
    
    def _analyze_critical_function(self, func_source: str, func_name: str, results: Dict[str, Any]):
        """Analyze a revenue-critical function for suspicious changes."""
        suspicious_patterns = [
            (r'return\s+0', 'Returns zero value'),
            (r'amount\s*\*=?\s*-', 'Negative amount calculation'),
            (r'if\s+False:', 'Dead code branch'),
            (r'pass\s*#.*skip', 'Intentional skip comment'),
            (r'TODO.*bypass', 'Security bypass implementation'),
            (r'\.99\s*\*', 'Suspicious percentage calculation'),
        ]
        
        for pattern, description in suspicious_patterns:
            if re.search(pattern, func_source, re.IGNORECASE):
                results['violations'].append({
                    'rule': 'critical_function_modification',
                    'function': func_name,
                    'pattern': pattern,
                    'severity': 'high',
                    'description': f"{description} in {func_name}"
                })
    
    def _check_mathematical_operations(self, content: str, results: Dict[str, Any]):
        """Check for suspicious mathematical operations in business logic."""
        suspicious_math = [
            (r'amount\s*\*\s*0', 'Multiplying amount by zero'),
            (r'price\s*\*\s*0', 'Multiplying price by zero'), 
            (r'total\s*=\s*total\s*-\s*total', 'Zeroing total'),
            (r'rate\s*=\s*-', 'Negative rate assignment'),
            (r'/\s*0', 'Division by zero'),
            (r'\*\s*-1\s*$', 'Multiplication by -1'),
        ]
        
        for pattern, description in suspicious_math:
            matches = re.findall(pattern, content, re.MULTILINE)
            if matches:
                results['violations'].append({
                    'rule': 'suspicious_mathematics',
                    'pattern': pattern,
                    'matches': matches,
                    'severity': 'high',
                    'description': description
                })
    
    def _check_conditional_bypasses(self, content: str, results: Dict[str, Any]):
        """Check for conditional logic that might bypass business rules."""
        bypass_patterns = [
            (r'if\s+True:', 'Always true condition'),
            (r'if\s+False:', 'Always false condition'),
            (r'if\s+not\s+validate:', 'Validation bypass'),
            (r'if\s+skip_', 'Skip condition'),
            (r'if\s+bypass_', 'Bypass condition'),
            (r'if\s+debug\s*:', 'Debug condition in production code'),
        ]
        
        for pattern, description in bypass_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                results['warnings'].append({
                    'rule': 'conditional_bypass',
                    'pattern': pattern,
                    'matches': matches,
                    'severity': 'medium',
                    'description': description
                })
    
    def verify_directory(self, directory: Path) -> List[Dict[str, Any]]:
        """Verify business rules across directory."""
        results = []
        
        # Focus on business-critical files
        business_files = []
        for py_file in directory.rglob("*.py"):
            if self._is_business_critical_file(py_file):
                business_files.append(py_file)
        
        for file_path in business_files:
            file_results = self.verify_file(file_path)
            if file_results.get('violations') or file_results.get('warnings'):
                results.append(file_results)
        
        return results
    
    def _is_business_critical_file(self, file_path: Path) -> bool:
        """Check if file contains business-critical logic."""
        path_str = str(file_path).lower()
        critical_keywords = [
            'billing', 'payment', 'invoice', 'customer', 'service',
            'price', 'rate', 'tax', 'discount', 'refund', 'charge'
        ]
        
        return any(keyword in path_str for keyword in critical_keywords)
    
    def generate_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate business rules verification report."""
        total_violations = sum(len(r.get('violations', [])) for r in results)
        total_warnings = sum(len(r.get('warnings', [])) for r in results)
        critical_violations = sum(
            len([v for v in r.get('violations', []) if v.get('severity') == 'critical'])
            for r in results
        )
        
        report = {
            'summary': {
                'files_checked': len(results),
                'total_violations': total_violations,
                'critical_violations': critical_violations,
                'total_warnings': total_warnings,
                'status': 'FAIL' if critical_violations > 0 else 'PASS'
            },
            'critical_files': [
                r for r in results 
                if any(v.get('severity') == 'critical' for v in r.get('violations', []))
            ],
            'all_results': results
        }
        
        return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Verify business rules integrity')
    parser.add_argument('--directory', '-d', default='src', help='Directory to verify')
    parser.add_argument('--strict', action='store_true', help='Fail on any violations')
    parser.add_argument('--output', '-o', help='Output JSON report file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    verifier = BusinessRuleVerifier()
    directory = Path(args.directory)
    
    if not directory.exists():
logger.error(f"Error: Directory {directory} does not exist", file=sys.stderr)
        sys.exit(1)
    
logger.info(f"Verifying business rules in {directory}...")
    results = verifier.verify_directory(directory)
    
    report = verifier.generate_report(results)
    
    # Print summary
    summary = report['summary']
logger.info(f"\n📋 Business Rules Verification Summary:")
logger.info(f"   Files checked: {summary['files_checked']}")
logger.info(f"   Total violations: {summary['total_violations']}")
logger.info(f"   Critical violations: {summary['critical_violations']}")
logger.warning(f"   Warnings: {summary['total_warnings']}")
logger.info(f"   Status: {summary['status']}")
    
    if report['critical_files']:
logger.info(f"\n🚨 CRITICAL VIOLATIONS DETECTED:")
        for file_info in report['critical_files']:
logger.info(f"   📄 {file_info['file']}")
            for violation in file_info['violations']:
                if violation.get('severity') == 'critical':
logger.info(f"      ❌ {violation['description']}")
logger.info(f"         Pattern: {violation['pattern']}")
    
    if args.verbose and results:
logger.info(f"\n🔍 Detailed Results:")
        for result in results:
logger.info(f"\n📄 {result['file']}")
logger.info(f"   Category: {result['business_rule_category']}")
            
            if result.get('violations'):
logger.info(f"   Violations:")
                for violation in result['violations']:
logger.info(f"     ❌ {violation['description']} (severity: {violation['severity']})")
            
            if result.get('warnings'):
logger.warning(f"   Warnings:")
                for warning in result['warnings']:
logger.warning(f"     ⚠️  {warning['description']}")
            
            if result.get('revenue_critical_functions'):
logger.info(f"   Revenue-Critical Functions:")
                for func in result['revenue_critical_functions']:
logger.info(f"     💰 {func['name']} (line {func['line']}, complexity: {func['complexity']})")
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
logger.info(f"\n📝 Report saved to: {args.output}")
    
    # Exit with appropriate code
    if args.strict and summary['total_violations'] > 0:
logger.error(f"\n❌ Strict mode: Exiting with error due to violations")
        sys.exit(1)
    elif summary['critical_violations'] > 0:
logger.info(f"\n❌ Critical violations detected - business rules may be compromised")
        sys.exit(1)
    
logger.info(f"\n✅ Business rules verification completed successfully")


if __name__ == '__main__':
    main()