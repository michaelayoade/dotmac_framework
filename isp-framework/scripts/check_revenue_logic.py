#!/usr/bin/env python3
"""
Revenue Logic Checker - Ensure AI hasn't modified revenue-critical calculations.

This script specifically focuses on protecting revenue-generating logic
from unintended AI modifications that could impact business finances.
"""

import argparse
import ast
import json
import hashlib
import sys
from pathlib import Path
from typing import Dict, List, Any, Set
import re


class RevenueLogicChecker:
    """
    Specialized checker for revenue-critical logic integrity.
    """
    
    def __init__(self):
        # Critical revenue calculations that must be protected
        self.revenue_critical_patterns = {
            'billing_amounts': [
                r'amount\s*=.*\*',         # Amount calculations
                r'total\s*=.*\+',          # Total calculations
                r'subtotal\s*=.*',         # Subtotal calculations
                r'tax\s*=.*\*',            # Tax calculations
                r'discount\s*=.*',         # Discount applications
            ],
            
            'pricing_logic': [
                r'price\s*\*\s*quantity',  # Price * quantity
                r'rate\s*\*\s*usage',      # Rate * usage  
                r'monthly_cost\s*\*',      # Monthly cost calculations
                r'prorated\s*=.*/',        # Proration logic
            ],
            
            'payment_processing': [
                r'charge\s*\(',            # Payment charges
                r'refund\s*\(',            # Refund processing
                r'credit\s*\(',            # Credit applications
                r'payment\s*=.*',          # Payment assignments
            ]
        }
        
        # Mathematical operations that should never appear in revenue code
        self.forbidden_operations = [
            r'amount\s*\*\s*0',           # Zeroing amount
            r'price\s*\*\s*0',            # Zeroing price
            r'total\s*=\s*0',             # Setting total to zero
            r'amount\s*\*=\s*-1',         # Negating amount
            r'discount\s*=\s*1\.0',       # 100% discount
            r'tax_rate\s*=\s*0',          # No tax
            r'/\s*0',                     # Division by zero
        ]
        
        # Revenue-critical functions to monitor
        self.critical_functions = {
            'calculate_monthly_bill',
            'calculate_usage_charge', 
            'apply_discount',
            'calculate_tax',
            'process_payment',
            'generate_invoice_total',
            'calculate_prorated_amount',
            'calculate_refund_amount',
            'apply_credit',
            'charge_customer',
        }
    
    def check_file(self, file_path: Path) -> Dict[str, Any]:
        """Check a file for revenue logic integrity."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return {'error': f"Failed to read {file_path}: {e}"}
        
        results = {
            'file': str(file_path),
            'content_hash': hashlib.sha256(content.encode()).hexdigest()[:16],
            'revenue_functions': [],
            'forbidden_operations': [],
            'suspicious_changes': [],
            'risk_level': 'low'
        }
        
        # Check for forbidden operations
        for pattern in self.forbidden_operations:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                results['forbidden_operations'].append({
                    'pattern': pattern,
                    'matches': matches,
                    'severity': 'critical'
                })
                results['risk_level'] = 'critical'
        
        # Analyze revenue-critical functions
        self._analyze_revenue_functions(content, results)
        
        # Check for suspicious mathematical patterns
        self._check_mathematical_integrity(content, results)
        
        # Determine overall risk level
        if results['forbidden_operations']:
            results['risk_level'] = 'critical'
        elif len(results['suspicious_changes']) > 2:
            results['risk_level'] = 'high'
        elif results['suspicious_changes']:
            results['risk_level'] = 'medium'
        
        return results
    
    def _analyze_revenue_functions(self, content: str, results: Dict[str, Any]):
        """Analyze revenue-critical functions for changes."""
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name in self.critical_functions:
                        func_info = {
                            'name': node.name,
                            'line': node.lineno,
                            'signature_hash': self._hash_function_signature(node),
                            'body_hash': self._hash_function_body(content, node),
                            'return_analysis': self._analyze_return_statements(node)
                        }
                        
                        results['revenue_functions'].append(func_info)
                        
                        # Check for suspicious patterns in the function
                        func_source = ast.get_source_segment(content, node)
                        if func_source:
                            self._check_function_integrity(func_source, node.name, results)
                            
        except SyntaxError:
            results['suspicious_changes'].append({
                'type': 'syntax_error',
                'description': 'File contains syntax errors - possible corruption'
            })
    
    def _hash_function_signature(self, node: ast.FunctionDef) -> str:
        """Create hash of function signature for change detection."""
        signature_parts = [
            node.name,
            str(len(node.args.args)),
            str([arg.arg for arg in node.args.args]),
        ]
        if node.returns:
            signature_parts.append(ast.dump(node.returns))
        
        signature_str = '|'.join(signature_parts)
        return hashlib.md5(signature_str.encode()).hexdigest()[:8]
    
    def _hash_function_body(self, content: str, node: ast.FunctionDef) -> str:
        """Create hash of function body for change detection."""
        func_source = ast.get_source_segment(content, node)
        if func_source:
            # Normalize whitespace for consistent hashing
            normalized = re.sub(r'\s+', ' ', func_source.strip())
            return hashlib.md5(normalized.encode()).hexdigest()[:8]
        return "unknown"
    
    def _analyze_return_statements(self, node: ast.FunctionDef) -> Dict[str, Any]:
        """Analyze return statements for suspicious patterns."""
        returns = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.Return):
                if child.value:
                    return_info = {
                        'line': child.lineno,
                        'type': type(child.value).__name__
                    }
                    
                    # Check for suspicious return values
                    if isinstance(child.value, ast.Constant):
                        if child.value.value == 0:
                            return_info['warning'] = 'Returns zero - potential revenue loss'
                        elif isinstance(child.value.value, (int, float)) and child.value.value < 0:
                            return_info['warning'] = 'Returns negative value - critical issue'
                    
                    returns.append(return_info)
        
        return {'count': len(returns), 'details': returns}
    
    def _check_function_integrity(self, func_source: str, func_name: str, results: Dict[str, Any]):
        """Check specific function for revenue integrity issues."""
        # Patterns that indicate potential revenue manipulation
        dangerous_patterns = [
            (r'return\s+0\s*$', 'Function returns zero'),
            (r'return\s+-', 'Function returns negative value'),
            (r'amount\s*=\s*0', 'Amount set to zero'),
            (r'price\s*=\s*0', 'Price set to zero'),
            (r'if\s+False\s*:', 'Dead code branch'),
            (r'#.*bypass', 'Bypass comment'),
            (r'#.*skip', 'Skip comment'),
            (r'pass\s*#', 'Pass with comment (potential placeholder)'),
        ]
        
        for pattern, description in dangerous_patterns:
            if re.search(pattern, func_source, re.IGNORECASE | re.MULTILINE):
                results['suspicious_changes'].append({
                    'function': func_name,
                    'pattern': pattern,
                    'description': description,
                    'severity': 'high'
                })
    
    def _check_mathematical_integrity(self, content: str, results: Dict[str, Any]):
        """Check mathematical operations for integrity."""
        # Revenue calculation patterns
        for category, patterns in self.revenue_critical_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    # Check if the calculation looks suspicious
                    for match in matches:
                        if self._is_suspicious_calculation(match):
                            results['suspicious_changes'].append({
                                'category': category,
                                'calculation': match,
                                'description': f'Suspicious {category} calculation',
                                'severity': 'medium'
                            })
    
    def _is_suspicious_calculation(self, calculation: str) -> bool:
        """Determine if a calculation looks suspicious."""
        suspicious_indicators = [
            r'\*\s*0',          # Multiply by zero
            r'\*\s*-',          # Multiply by negative
            r'/\s*0',           # Divide by zero
            r'\+\s*0\s*$',      # Add zero at end
            r'-\s*\w+\s*$',     # Subtract variable at end
        ]
        
        return any(re.search(pattern, calculation) for pattern in suspicious_indicators)
    
    def check_directory(self, directory: Path) -> List[Dict[str, Any]]:
        """Check directory for revenue logic integrity."""
        results = []
        
        # Focus on revenue-related files
        revenue_files = self._find_revenue_files(directory)
        
        for file_path in revenue_files:
            file_results = self.check_file(file_path)
            if (file_results.get('forbidden_operations') or 
                file_results.get('suspicious_changes') or 
                file_results.get('revenue_functions')):
                results.append(file_results)
        
        return results
    
    def _find_revenue_files(self, directory: Path) -> List[Path]:
        """Find files containing revenue-critical code."""
        revenue_keywords = [
            'billing', 'payment', 'invoice', 'charge', 'price',
            'cost', 'fee', 'tax', 'discount', 'refund', 'credit'
        ]
        
        revenue_files = []
        for py_file in directory.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            path_str = str(py_file).lower()
            if any(keyword in path_str for keyword in revenue_keywords):
                revenue_files.append(py_file)
        
        return revenue_files
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_patterns = [
            '__pycache__',
            '.pytest_cache',
            'venv',
            'virtualenv',
            '.git',
            'migrations',
            'tests/',
            'test_',
        ]
        
        path_str = str(file_path)
        return any(pattern in path_str for pattern in skip_patterns)
    
    def generate_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate revenue logic integrity report."""
        critical_files = [r for r in results if r.get('risk_level') == 'critical']
        high_risk_files = [r for r in results if r.get('risk_level') == 'high']
        
        report = {
            'summary': {
                'files_checked': len(results),
                'critical_risk_files': len(critical_files),
                'high_risk_files': len(high_risk_files),
                'total_revenue_functions': sum(len(r.get('revenue_functions', [])) for r in results),
                'total_forbidden_operations': sum(len(r.get('forbidden_operations', [])) for r in results),
                'status': 'CRITICAL' if critical_files else 'PASS'
            },
            'critical_issues': critical_files,
            'high_risk_issues': high_risk_files,
            'all_results': results
        }
        
        return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Check revenue logic integrity')
    parser.add_argument('--directory', '-d', default='src', help='Directory to check')
    parser.add_argument('--verify-unchanged', action='store_true', help='Verify no changes to critical functions')
    parser.add_argument('--output', '-o', help='Output JSON report file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    checker = RevenueLogicChecker()
    directory = Path(args.directory)
    
    if not directory.exists():
        print(f"Error: Directory {directory} does not exist", file=sys.stderr)
        sys.exit(1)
    
    print(f"Checking revenue logic integrity in {directory}...")
    results = checker.check_directory(directory)
    
    if not results:
        print("✅ No revenue-critical files found or no issues detected.")
        sys.exit(0)
    
    report = checker.generate_report(results)
    
    # Print summary
    summary = report['summary']
    print(f"\n💰 Revenue Logic Integrity Summary:")
    print(f"   Files checked: {summary['files_checked']}")
    print(f"   Revenue functions: {summary['total_revenue_functions']}")
    print(f"   Critical risk files: {summary['critical_risk_files']}")
    print(f"   High risk files: {summary['high_risk_files']}")
    print(f"   Forbidden operations: {summary['total_forbidden_operations']}")
    print(f"   Status: {summary['status']}")
    
    if report['critical_issues']:
        print(f"\n🚨 CRITICAL REVENUE ISSUES DETECTED:")
        for file_info in report['critical_issues']:
            print(f"   📄 {file_info['file']} (risk: {file_info['risk_level']})")
            
            for op in file_info.get('forbidden_operations', []):
                print(f"      ❌ FORBIDDEN: {op['pattern']}")
                print(f"         Matches: {op['matches']}")
            
            for change in file_info.get('suspicious_changes', []):
                print(f"      ⚠️  {change['description']}")
    
    if args.verbose and results:
        print(f"\n🔍 Detailed Results:")
        for result in results:
            print(f"\n📄 {result['file']} (risk: {result['risk_level']})")
            print(f"   Content hash: {result['content_hash']}")
            
            if result.get('revenue_functions'):
                print(f"   Revenue Functions:")
                for func in result['revenue_functions']:
                    print(f"     💰 {func['name']} (line {func['line']})")
                    print(f"        Signature: {func['signature_hash']}")
                    print(f"        Body: {func['body_hash']}")
                    
                    returns = func['return_analysis']
                    if returns['details']:
                        for ret in returns['details']:
                            if 'warning' in ret:
                                print(f"        ⚠️  {ret['warning']} (line {ret['line']})")
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📝 Report saved to: {args.output}")
    
    # Exit with appropriate status
    if summary['status'] == 'CRITICAL':
        print(f"\n❌ CRITICAL revenue integrity issues detected!")
        print(f"   Revenue-generating logic may have been compromised.")
        print(f"   Manual review required before deployment.")
        sys.exit(1)
    
    print(f"\n✅ Revenue logic integrity check completed successfully")


if __name__ == '__main__':
    main()