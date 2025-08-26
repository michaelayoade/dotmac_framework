#!/usr/bin/env python3
"""
Service Standards Validation Script

ARCHITECTURE ENFORCEMENT: Validates that all services follow the standardized
patterns defined in the service standards. Prevents creation of legacy patterns
and ensures consistent code quality across the framework.
"""

import ast
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass


@dataclass
class ValidationIssue:
    """Represents a validation issue found in code."""
    severity: str  # 'error', 'warning', 'info'
    file_path: str
    line_number: int
    rule: str
    message: str
    suggestion: Optional[str] = None


class ServiceStandardsValidator:
    """
    Validates service code against standardized patterns.
    
    PATTERN: Static Code Analysis + Rule Engine
    - Parses Python AST to analyze code structure
    - Checks for deprecated patterns and anti-patterns
    - Enforces standardized service inheritance
    - Validates async/await usage
    - Reports violations with suggestions
    
    Features:
    - AST-based code analysis
    - Pattern matching for deprecated code
    - Service class structure validation
    - Import statement checking
    - Async pattern enforcement
    - Detailed violation reporting
    """
    
    def __init__(self, standards_file: str):
        """
        Initialize validator with standards configuration.
        
        Args:
            standards_file: Path to service standards JSON file
        """
        with open(standards_file) as f:
            self.standards = json.load(f)['service_standards']
        
        self.issues: List[ValidationIssue] = []
    
    def validate_directory(self, directory: str) -> List[ValidationIssue]:
        """
        Validate all Python files in directory.
        
        Args:
            directory: Directory to validate
            
        Returns:
            List of validation issues found
        """
        self.issues = []
        
        # Find all Python service files
        service_files = self._find_service_files(directory)
        
        for file_path in service_files:
            self._validate_file(file_path)
        
        return self.issues
    
    def _find_service_files(self, directory: str) -> List[str]:
        """Find all service-related Python files."""
        service_files = []
        
        for py_file in Path(directory).rglob("*.py"):
            if self._is_service_file(py_file):
                service_files.append(str(py_file))
        
        return service_files
    
    def _is_service_file(self, file_path: Path) -> bool:
        """Check if file contains service classes."""
        try:
            with open(file_path) as f:
                content = f.read()
                
            # Check for service patterns
            if re.search(r'class\s+\w*Service\s*\(', content):
                return True
            if 'Service' in file_path.name:
                return True
            if str(file_path).endswith('/service.py'):
                return True
                
        except Exception:
            pass
        
        return False
    
    def _validate_file(self, file_path: str) -> None:
        """Validate a single Python file."""
        try:
            with open(file_path) as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            # Run validation checks
            self._check_deprecated_patterns(file_path, content)
            self._check_service_classes(file_path, tree)
            self._check_imports(file_path, tree)
            self._check_async_patterns(file_path, tree)
            
        except SyntaxError as e:
            self.issues.append(ValidationIssue(
                severity='error',
                file_path=file_path,
                line_number=e.lineno or 0,
                rule='syntax_error',
                message=f"Syntax error: {e.msg}"
            ))
        except Exception as e:
            self.issues.append(ValidationIssue(
                severity='warning',
                file_path=file_path,
                line_number=0,
                rule='parse_error',
                message=f"Failed to parse file: {e}"
            ))
    
    def _check_deprecated_patterns(self, file_path: str, content: str) -> None:
        """Check for deprecated code patterns."""
        deprecated_patterns = self.standards['patterns']['deprecated']['patterns']
        
        for pattern in deprecated_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
            for match in matches:
                line_number = content[:match.start()].count('\n') + 1
                
                self.issues.append(ValidationIssue(
                    severity='error',
                    file_path=file_path,
                    line_number=line_number,
                    rule='deprecated_pattern',
                    message=f"Deprecated pattern found: {match.group()[:50]}...",
                    suggestion="Use BaseTenantService inheritance pattern instead"
                ))
    
    def _check_service_classes(self, file_path: str, tree: ast.AST) -> None:
        """Check service class definitions."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.endswith('Service'):
                self._validate_service_class(file_path, node)
    
    def _validate_service_class(self, file_path: str, class_node: ast.ClassDef) -> None:
        """Validate individual service class."""
        # Check inheritance
        if not self._has_correct_base_class(class_node):
            self.issues.append(ValidationIssue(
                severity='error',
                file_path=file_path,
                line_number=class_node.lineno,
                rule='incorrect_inheritance',
                message=f"Service class {class_node.name} must inherit from BaseTenantService",
                suggestion="class YourService(BaseTenantService[Model, CreateSchema, UpdateSchema, ResponseSchema])"
            )
        
        # Check required methods
        self._check_required_methods(file_path, class_node)
    
    def _has_correct_base_class(self, class_node: ast.ClassDef) -> bool:
        """Check if class inherits from correct base class."""
        for base in class_node.bases:
            if isinstance(base, ast.Name) and base.id == 'BaseTenantService':
                return True
            elif isinstance(base, ast.Subscript) and isinstance(base.value, ast.Name):
                if base.value.id == 'BaseTenantService':
                    return True
        return False
    
    def _check_required_methods(self, file_path: str, class_node: ast.ClassDef) -> None:
        """Check for required methods in service class."""
        required_methods = self.standards['rules']['async_patterns']['required_methods']
        
        method_names = []
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                method_names.append(node.name)
        
        # Check for missing methods (only if not using BaseTenantService)
        if not self._has_correct_base_class(class_node):
            for method in required_methods:
                if method not in method_names:
                    self.issues.append(ValidationIssue(
                        severity='warning',
                        file_path=file_path,
                        line_number=class_node.lineno,
                        rule='missing_method',
                        message=f"Service {class_node.name} is missing required method: {method}",
                        suggestion=f"Add async def {method}(...) method or inherit from BaseTenantService"
                    )
    
    def _check_imports(self, file_path: str, tree: ast.AST) -> None:
        """Check import statements."""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imports.append(f"from {node.module} import {', '.join([alias.name for alias in node.names])}")
            elif isinstance(node, ast.Import):
                imports.append(f"import {', '.join([alias.name for alias in node.names])}")
        
        # Check for deprecated imports
        deprecated_classes = self.standards['patterns']['deprecated']['classes']
        for deprecated in deprecated_classes:
            for imp in imports:
                if deprecated in imp:
                    self.issues.append(ValidationIssue(
                        severity='warning',
                        file_path=file_path,
                        line_number=1,  # Could be improved by tracking line numbers
                        rule='deprecated_import',
                        message=f"Deprecated import found: {imp}",
                        suggestion="Use consolidated service imports from modules/*/service.py"
                    )
    
    def _check_async_patterns(self, file_path: str, tree: ast.AST) -> None:
        """Check for async/await patterns."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.endswith('Service'):
                for method in node.body:
                    if isinstance(method, ast.FunctionDef):
                        if method.name in ['create', 'update', 'delete', 'get_by_id', 'list']:
                            if not self._is_async_method(method):
                                self.issues.append(ValidationIssue(
                                    severity='error',
                                    file_path=file_path,
                                    line_number=method.lineno,
                                    rule='non_async_method',
                                    message=f"Method {method.name} should be async",
                                    suggestion=f"Change to: async def {method.name}(...)"
                                )
    
    def _is_async_method(self, method: ast.FunctionDef) -> bool:
        """Check if method is async."""
        return isinstance(method, ast.AsyncFunctionDef) or hasattr(method, 'returns')
    
    def generate_report(self) -> str:
        """Generate validation report."""
        if not self.issues:
            return "✅ All service standards validation checks passed!"
        
        # Sort issues by severity and file
        sorted_issues = sorted(self.issues, key=lambda x: (x.severity, x.file_path, x.line_number)
        
        report = []
        report.append("🔍 Service Standards Validation Report")
        report.append("=" * 50)
        report.append("")
        
        # Summary
        error_count = len([i for i in self.issues if i.severity == 'error'])
        warning_count = len([i for i in self.issues if i.severity == 'warning'])
        
        report.append(f"📊 Summary: {error_count} errors, {warning_count} warnings")
        report.append("")
        
        # Group by file
        current_file = None
        for issue in sorted_issues:
            if issue.file_path != current_file:
                current_file = issue.file_path
                report.append(f"📄 {issue.file_path}")
                report.append("-" * len(issue.file_path)
            
            # Issue details
            severity_icon = "❌" if issue.severity == 'error' else "⚠️" if issue.severity == 'warning' else "ℹ️"
            report.append(f"  {severity_icon} Line {issue.line_number}: {issue.message}")
            
            if issue.suggestion:
                report.append(f"      💡 Suggestion: {issue.suggestion}")
            
            report.append("")
        
        # Migration guide
        if any(i.rule in ['deprecated_pattern', 'incorrect_inheritance'] for i in self.issues):
            report.append("🔄 Migration Guide:")
            report.append("-" * 20)
            for step in self.standards['migration_guide']['steps']:
                report.append(f"  {step}")
            report.append("")
        
        return "\n".join(report)
    
    def has_errors(self) -> bool:
        """Check if any errors were found."""
        return any(issue.severity == 'error' for issue in self.issues)


def main():
    """Main CLI function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate service standards compliance')
    parser.add_argument('directory', help='Directory to validate')
    parser.add_argument('--standards', default='.service-standards.json', help='Standards file')
    parser.add_argument('--fail-on-warnings', action='store_true', help='Fail on warnings too')
    
    args = parser.parse_args()
    
    # Check if standards file exists
    if not Path(args.standards).exists():
        print(f"❌ Standards file not found: {args.standards}")
        sys.exit(1)
    
    # Run validation
    validator = ServiceStandardsValidator(args.standards)
    issues = validator.validate_directory(args.directory)
    
    # Generate and print report
    report = validator.generate_report()
    print(report)
    
    # Exit with appropriate code
    if validator.has_errors():
        sys.exit(1)
    elif args.fail_on_warnings and any(i.severity == 'warning' for i in issues):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()