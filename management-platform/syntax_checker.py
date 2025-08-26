#!/usr/bin/env python3
"""
Comprehensive syntax error checker for Management Platform
"""
import ast
import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import traceback
import re

class SyntaxErrorDetector:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.errors = []
        self.pydantic_issues = []
        
    def check_file(self, file_path: Path) -> Dict:
        """Check a single Python file for syntax errors and Pydantic issues"""
        results = {
            'file': str(file_path.relative_to(self.root_dir)),
            'syntax_errors': [],
            'pydantic_issues': [],
            'missing_parentheses': [],
            'other_issues': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for syntax errors
            try:
                ast.parse(content)
            except SyntaxError as e:
                results['syntax_errors'].append({
                    'line': e.lineno,
                    'column': e.offset,
                    'message': e.msg,
                    'text': e.text.strip() if e.text else None
                })
            except Exception as e:
                results['other_issues'].append(f"Parse error: {str(e)}")
                
            # Check for Pydantic v1 patterns
            pydantic_patterns = [
                (r'\.dict\(\)', 'Use .model_dump() instead of .dict()'),
                (r'Config:', 'Use model_config instead of Config class'),
                (r'validator\(', 'Use field_validator instead of validator'),
                (r'root_validator\(', 'Use model_validator instead of root_validator'),
                (r'parse_obj\(', 'Use model_validate instead of parse_obj'),
                (r'schema\(\)', 'Use model_json_schema() instead of schema()'),
            ]
            
            for pattern, suggestion in pydantic_patterns:
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    results['pydantic_issues'].append({
                        'line': line_num,
                        'pattern': pattern,
                        'suggestion': suggestion,
                        'match': match.group()
                    })
            
            # Check for common missing parentheses patterns
            missing_paren_patterns = [
                (r'asyncio\.run\([^)]*$', 'Missing closing parenthesis in asyncio.run'),
                (r'logger\.[^(]*\([^)]*$', 'Missing closing parenthesis in logger call'),
                (r'app\.[^(]*\([^)]*$', 'Missing closing parenthesis in app method'),
                (r'return [^,\n]*,[^,\n]*$', 'Possible missing parentheses in return statement'),
            ]
            
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                for pattern, description in missing_paren_patterns:
                    if re.search(pattern, line.strip()):
                        results['missing_parentheses'].append({
                            'line': i,
                            'description': description,
                            'text': line.strip()
                        })
                        
        except Exception as e:
            results['other_issues'].append(f"File read error: {str(e)}")
            
        return results
    
    def scan_directory(self) -> Dict:
        """Scan all Python files in the directory"""
        all_results = {
            'files_scanned': 0,
            'files_with_errors': 0,
            'total_syntax_errors': 0,
            'total_pydantic_issues': 0,
            'files': []
        }
        
        # Find all Python files
        python_files = list(self.root_dir.rglob('*.py'))
        
        for file_path in python_files:
            # Skip certain directories
            skip_dirs = ['.git', '__pycache__', '.pytest_cache', 'venv', '.venv']
            if any(skip_dir in str(file_path) for skip_dir in skip_dirs):
                continue
                
            results = self.check_file(file_path)
            all_results['files'].append(results)
            all_results['files_scanned'] += 1
            
            if (results['syntax_errors'] or results['pydantic_issues'] or 
                results['missing_parentheses'] or results['other_issues']):
                all_results['files_with_errors'] += 1
                
            all_results['total_syntax_errors'] += len(results['syntax_errors'])
            all_results['total_pydantic_issues'] += len(results['pydantic_issues'])
            
        return all_results
    
    def generate_report(self, results: Dict) -> str:
        """Generate a detailed report"""
        report = []
        report.append("=" * 80)
        report.append("MANAGEMENT PLATFORM SYNTAX ERROR REPORT")
        report.append("=" * 80)
        report.append(f"Files scanned: {results['files_scanned']}")
        report.append(f"Files with issues: {results['files_with_errors']}")
        report.append(f"Total syntax errors: {results['total_syntax_errors']}")
        report.append(f"Total Pydantic issues: {results['total_pydantic_issues']}")
        report.append("")
        
        # Group files by issue type
        files_with_syntax = []
        files_with_pydantic = []
        files_with_parentheses = []
        
        for file_result in results['files']:
            if file_result['syntax_errors']:
                files_with_syntax.append(file_result)
            if file_result['pydantic_issues']:
                files_with_pydantic.append(file_result)
            if file_result['missing_parentheses']:
                files_with_parentheses.append(file_result)
        
        if files_with_syntax:
            report.append("SYNTAX ERRORS:")
            report.append("-" * 40)
            for file_result in files_with_syntax:
                report.append(f"\n{file_result['file']}:")
                for error in file_result['syntax_errors']:
                    report.append(f"  Line {error['line']}: {error['message']}")
                    if error['text']:
                        report.append(f"    Text: {error['text']}")
        
        if files_with_pydantic:
            report.append("\nPYDANTIC V2 COMPATIBILITY ISSUES:")
            report.append("-" * 40)
            for file_result in files_with_pydantic:
                report.append(f"\n{file_result['file']}:")
                for issue in file_result['pydantic_issues']:
                    report.append(f"  Line {issue['line']}: {issue['suggestion']}")
                    report.append(f"    Found: {issue['match']}")
        
        if files_with_parentheses:
            report.append("\nPOSSIBLE MISSING PARENTHESES:")
            report.append("-" * 40)
            for file_result in files_with_parentheses:
                report.append(f"\n{file_result['file']}:")
                for issue in file_result['missing_parentheses']:
                    report.append(f"  Line {issue['line']}: {issue['description']}")
                    report.append(f"    Text: {issue['text']}")
        
        return "\n".join(report)

if __name__ == "__main__":
    detector = SyntaxErrorDetector("/home/dotmac_framework/management-platform")
    results = detector.scan_directory()
    report = detector.generate_report(results)
    print(report)
    
    # Save report to file
    with open("syntax_error_report.txt", "w") as f:
        f.write(report)
    
    print(f"\nReport saved to syntax_error_report.txt")
    print(f"Exit code: {1 if results['files_with_errors'] > 0 else 0}")
    sys.exit(1 if results['files_with_errors'] > 0 else 0)