#!/usr/bin/env python3
"""
Comprehensive syntax error fixer for Management Platform
"""
import ast
import os
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import shutil
import sys

class SyntaxFixer:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.fixes_applied = []
        self.backup_dir = self.root_dir / "backups_syntax_fixes"
        self.backup_dir.mkdir(exist_ok=True)
        
    def backup_file(self, file_path: Path) -> None:
        """Create backup of file before fixing"""
        backup_path = self.backup_dir / file_path.relative_to(self.root_dir)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, backup_path)
        
    def fix_file_syntax(self, file_path: Path) -> List[str]:
        """Fix syntax errors in a single file"""
        fixes = []
        relative_path = str(file_path.relative_to(self.root_dir))
        
        try:
            if not file_path.exists():
                fixes.append(f"Skipping non-existent file: {relative_path}")
                return fixes
                
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
                
            content = original_content
            
            # Test if file already has valid syntax
            try:
                ast.parse(content)
                return fixes  # No fixes needed
            except SyntaxError:
                pass  # Need to fix
                
            self.backup_file(file_path)
            
            # Apply specific fixes based on file patterns
            
            # 1. Fix missing closing parentheses in common patterns
            content, file_fixes = self._fix_missing_parentheses(content, relative_path)
            fixes.extend(file_fixes)
            
            # 2. Fix missing commas
            content, file_fixes = self._fix_missing_commas(content, relative_path)
            fixes.extend(file_fixes)
            
            # 3. Fix malformed function definitions
            content, file_fixes = self._fix_function_definitions(content, relative_path)
            fixes.extend(file_fixes)
            
            # 4. Fix import statement issues
            content, file_fixes = self._fix_import_statements(content, relative_path)
            fixes.extend(file_fixes)
            
            # 5. Fix bracket mismatches
            content, file_fixes = self._fix_bracket_mismatches(content, relative_path)
            fixes.extend(file_fixes)
            
            # 6. File-specific fixes
            if 'test_code_quality.py' in relative_path:
                content, file_fixes = self._fix_test_code_quality(content)
                fixes.extend(file_fixes)
            elif 'security_check.py' in relative_path:
                content, file_fixes = self._fix_security_check(content)
                fixes.extend(file_fixes)
            elif 'validate_test_config.py' in relative_path:
                content, file_fixes = self._fix_validate_test_config(content)
                fixes.extend(file_fixes)
            elif 'setup_test_db.py' in relative_path:
                content, file_fixes = self._fix_setup_test_db(content)
                fixes.extend(file_fixes)
            elif 'cost_monitor.py' in relative_path:
                content, file_fixes = self._fix_cost_monitor(content)
                fixes.extend(file_fixes)
                
            # Write fixed content
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                # Verify fix worked
                try:
                    ast.parse(content)
                    fixes.append(f"Successfully fixed syntax errors in {relative_path}")
                except SyntaxError as e:
                    fixes.append(f"Warning: {relative_path} still has syntax error at line {e.lineno}: {e.msg}")
                    
        except Exception as e:
            fixes.append(f"Error processing {relative_path}: {str(e)}")
            
        return fixes
    
    def _fix_missing_parentheses(self, content: str, file_path: str) -> Tuple[str, List[str]]:
        """Fix missing closing parentheses"""
        fixes = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            original_line = line
            
            # Common patterns with missing parentheses
            patterns = [
                # asyncio.run missing closing paren
                (r'asyncio\.run\(([^)]+)$', lambda m: f'asyncio.run({m.group(1)})'),
                # logger calls missing closing paren
                (r'(logger\.\w+)\(([^)]+)$', lambda m: f'{m.group(1)}({m.group(2)})'),
                # app method calls missing closing paren
                (r'(app\.\w+)\(([^)]+)$', lambda m: f'{m.group(1)}({m.group(2)})'),
                # Function calls at end of line missing paren
                (r'(\w+\([^)]*),\s*$', lambda m: f'{m.group(1)})'),
                # Assert statements missing closing paren
                (r'assert\s+([^)]+\([^)]+)$', lambda m: f'assert {m.group(1)})'),
                # Return statements with function calls missing paren
                (r'return\s+(\w+\([^)]+)$', lambda m: f'return {m.group(1)})'),
            ]
            
            for pattern, replacement in patterns:
                if re.search(pattern, line):
                    line = re.sub(pattern, replacement, line)
                    if line != original_line:
                        fixes.append(f"Fixed missing parenthesis at line {i+1}: {original_line.strip()} -> {line.strip()}")
                        break
                        
            lines[i] = line
            
        return '\n'.join(lines), fixes
    
    def _fix_missing_commas(self, content: str, file_path: str) -> Tuple[str, List[str]]:
        """Fix missing commas in expressions"""
        fixes = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            original_line = line
            
            # Pattern for missing comma in function parameters
            if re.search(r'\w+\s*=\s*\w+\([^,)]*\s*$', line.strip()):
                # Look for common patterns like: port = int(os.getenv("DB_PORT", "5432")
                if '"' in line and line.count('"') % 2 == 0:  # Even number of quotes
                    line = re.sub(r'("[^"]*")\s*$', r'\1)', line)
                    if line != original_line:
                        fixes.append(f"Fixed missing closing parenthesis at line {i+1}: {original_line.strip()} -> {line.strip()}")
                        
            lines[i] = line
            
        return '\n'.join(lines), fixes
    
    def _fix_function_definitions(self, content: str, file_path: str) -> Tuple[str, List[str]]:
        """Fix malformed function definitions"""
        fixes = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            original_line = line
            
            # Fix async def statements that are malformed
            if 'async def' in line and not line.strip().endswith(':'):
                if ')' not in line and '(' in line:
                    # Find the opening paren and add closing paren before colon
                    line = re.sub(r'async def\s+\w+\([^)]*$', lambda m: f'{m.group(0)})', line)
                    if not line.strip().endswith(':'):
                        line += ':'
                    if line != original_line:
                        fixes.append(f"Fixed async def at line {i+1}: {original_line.strip()} -> {line.strip()}")
                        
            lines[i] = line
            
        return '\n'.join(lines), fixes
    
    def _fix_import_statements(self, content: str, file_path: str) -> Tuple[str, List[str]]:
        """Fix import statement issues"""
        fixes = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            original_line = line
            
            # Fix import statements with missing closing parentheses
            if line.strip().startswith('from ') and '(' in line and ')' not in line:
                # This is likely a multi-line import that got malformed
                if line.endswith(':'):
                    line = line[:-1] + ')'
                    fixes.append(f"Fixed import statement at line {i+1}: {original_line.strip()} -> {line.strip()}")
                    
            lines[i] = line
            
        return '\n'.join(lines), fixes
    
    def _fix_bracket_mismatches(self, content: str, file_path: str) -> Tuple[str, List[str]]:
        """Fix bracket/parentheses mismatches"""
        fixes = []
        lines = content.split('\n')
        
        # Track bracket states
        paren_stack = []
        bracket_stack = []
        brace_stack = []
        
        for i, line in enumerate(lines):
            original_line = line
            
            # Count opening and closing brackets
            for j, char in enumerate(line):
                if char == '(':
                    paren_stack.append((i, j))
                elif char == ')':
                    if paren_stack:
                        paren_stack.pop()
                elif char == '[':
                    bracket_stack.append((i, j))
                elif char == ']':
                    if bracket_stack:
                        bracket_stack.pop()
                elif char == '{':
                    brace_stack.append((i, j))
                elif char == '}':
                    if brace_stack:
                        brace_stack.pop()
                        
            # Fix obvious mismatches in single lines
            if '}' in line and '(' in line and ')' not in line:
                # Replace closing brace with closing paren
                line = line.replace('}', ')')
                if line != original_line:
                    fixes.append(f"Fixed bracket mismatch at line {i+1}: " + "} -> )")
                    
            if ']' in line and '(' in line and ')' not in line and '[' not in line:
                # Replace closing bracket with closing paren
                line = line.replace(']', ')')
                if line != original_line:
                    fixes.append(f"Fixed bracket mismatch at line {i+1}: " + "] -> )")
                    
            lines[i] = line
            
        return '\n'.join(lines), fixes
    
    def _fix_test_code_quality(self, content: str) -> Tuple[str, List[str]]:
        """Fix specific issues in test_code_quality.py"""
        fixes = []
        
        # Fix the if statement syntax error
        old_pattern = r'if isinstance\(node, \(ast\.Import, ast\.ImportFrom\):'
        new_pattern = r'if isinstance(node, (ast.Import, ast.ImportFrom)):'
        
        if re.search(old_pattern, content):
            content = re.sub(old_pattern, new_pattern, content)
            fixes.append("Fixed isinstance check syntax")
            
        return content, fixes
    
    def _fix_security_check(self, content: str) -> Tuple[str, List[str]]:
        """Fix specific issues in security_check.py"""
        fixes = []
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            # Look for the except clause that's malformed
            if 'except Exception as e:' in line and i > 0:
                prev_line = lines[i-1].strip()
                if prev_line and not prev_line.endswith(':') and not prev_line.endswith('\\'):
                    # Check if previous line needs completion
                    if '(' in prev_line and prev_line.count('(') > prev_line.count(')'):
                        lines[i-1] = prev_line + ')'
                        fixes.append(f"Fixed missing closing parenthesis before except at line {i}")
                        
        return '\n'.join(lines), fixes
    
    def _fix_validate_test_config(self, content: str) -> Tuple[str, List[str]]:
        """Fix specific issues in validate_test_config.py"""
        fixes = []
        
        # Fix the specific line with missing closing paren
        old_pattern = r'test_files = list\(Path\("tests"\)\.glob\("test_\*\.py"\)'
        new_pattern = r'test_files = list(Path("tests").glob("test_*.py"))'
        
        if re.search(old_pattern.replace('*', r'\*'), content):
            content = re.sub(old_pattern.replace('*', r'\*'), new_pattern, content)
            fixes.append("Fixed test_files assignment")
            
        return content, fixes
    
    def _fix_setup_test_db(self, content: str) -> Tuple[str, List[str]]:
        """Fix specific issues in setup_test_db.py"""
        fixes = []
        
        # Fix missing closing parenthesis in port assignment
        old_pattern = r'port = int\(os\.getenv\("DB_PORT", "5432"\)'
        new_pattern = r'port = int(os.getenv("DB_PORT", "5432"))'
        
        content = re.sub(old_pattern, new_pattern, content)
        fixes.append("Fixed port assignment")
        
        return content, fixes
    
    def _fix_cost_monitor(self, content: str) -> Tuple[str, List[str]]:
        """Fix specific issues in cost_monitor.py"""
        fixes = []
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip() == '}' and i > 0:
                # Look for opening brace or paren in previous lines
                for j in range(i-1, max(0, i-10), -1):
                    prev_line = lines[j].strip()
                    if prev_line.endswith('{') or '(' in prev_line:
                        if '(' in prev_line and prev_line.count('(') > prev_line.count(')'):
                            lines[i] = line.replace('}', ')')
                            fixes.append(f"Fixed closing bracket mismatch at line {i+1}")
                            break
                            
        return '\n'.join(lines), fixes
    
    def fix_pydantic_v2_issues(self, file_path: Path) -> List[str]:
        """Fix Pydantic v2 compatibility issues"""
        fixes = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            original_content = content
            
            # Fix common Pydantic v1 to v2 migration issues
            pydantic_fixes = [
                (r'\.dict\(\)', '.model_dump()', 'Replaced .dict() with .model_dump()'),
                (r'\.json\(\)', '.model_dump_json()', 'Replaced .json() with .model_dump_json()'),
                (r'parse_obj\(', 'model_validate(', 'Replaced parse_obj with model_validate'),
                (r'\.schema\(\)', '.model_json_schema()', 'Replaced .schema() with .model_json_schema()'),
                (r'from pydantic import validator', 'from pydantic import field_validator', 'Updated validator import'),
                (r'@validator\(', '@field_validator(', 'Updated validator decorator'),
                (r'from pydantic import root_validator', 'from pydantic import model_validator', 'Updated root_validator import'),
                (r'@root_validator\(', '@model_validator(mode="before")(', 'Updated root_validator decorator'),
            ]
            
            for pattern, replacement, description in pydantic_fixes:
                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content)
                    fixes.append(f"{description} in {file_path.relative_to(self.root_dir)}")
            
            # Fix Config class to model_config
            config_pattern = r'class Config:\s*\n((?:\s+\w+\s*=\s*[^\n]+\n)*)'
            
            def replace_config(match):
                config_body = match.group(1)
                # Convert Config class attributes to model_config dict
                attributes = []
                for line in config_body.split('\n'):
                    line = line.strip()
                    if '=' in line and line:
                        attributes.append(line)
                
                if attributes:
                    config_dict = 'model_config = {\n'
                    for attr in attributes:
                        if '=' in attr:
                            key, value = attr.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            config_dict += f'    "{key}": {value},\n'
                    config_dict += '}'
                    return config_dict
                return 'model_config = {}'
            
            if re.search(config_pattern, content, re.MULTILINE):
                content = re.sub(config_pattern, replace_config, content, flags=re.MULTILINE)
                fixes.append(f"Converted Config class to model_config in {file_path.relative_to(self.root_dir)}")
            
            if content != original_content:
                self.backup_file(file_path)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
        except Exception as e:
            fixes.append(f"Error fixing Pydantic issues in {file_path.relative_to(self.root_dir)}: {str(e)}")
            
        return fixes
    
    def fix_all_files(self) -> Dict:
        """Fix all Python files in the directory"""
        results = {
            'files_processed': 0,
            'files_fixed': 0,
            'total_fixes': 0,
            'fixes': [],
            'errors': []
        }
        
        # Find all Python files
        python_files = list(self.root_dir.rglob('*.py'))
        
        for file_path in python_files:
            # Skip certain directories
            skip_dirs = ['.git', '__pycache__', '.pytest_cache', 'venv', '.venv', 'backups_syntax_fixes']
            if any(skip_dir in str(file_path) for skip_dir in skip_dirs):
                continue
                
            if file_path.name in ['syntax_checker.py', 'syntax_fixer.py']:
                continue  # Skip our own files
                
            results['files_processed'] += 1
            
            # Fix syntax errors
            syntax_fixes = self.fix_file_syntax(file_path)
            if syntax_fixes:
                results['files_fixed'] += 1
                results['fixes'].extend(syntax_fixes)
                results['total_fixes'] += len(syntax_fixes)
                
            # Fix Pydantic v2 issues
            pydantic_fixes = self.fix_pydantic_v2_issues(file_path)
            if pydantic_fixes:
                results['fixes'].extend(pydantic_fixes)
                results['total_fixes'] += len(pydantic_fixes)
                
        return results

if __name__ == "__main__":
    fixer = SyntaxFixer("/home/dotmac_framework/management-platform")
    
    print("Starting comprehensive syntax and Pydantic fixes...")
    results = fixer.fix_all_files()
    
    print("\n" + "="*80)
    print("SYNTAX FIXER RESULTS")
    print("="*80)
    print(f"Files processed: {results['files_processed']}")
    print(f"Files fixed: {results['files_fixed']}")
    print(f"Total fixes applied: {results['total_fixes']}")
    
    if results['fixes']:
        print("\nFIXES APPLIED:")
        print("-" * 40)
        for fix in results['fixes']:
            print(f"  {fix}")
    
    if results['errors']:
        print("\nERRORS:")
        print("-" * 40)
        for error in results['errors']:
            print(f"  {error}")
    
    print(f"\nBackups saved to: {fixer.backup_dir}")
    print("Fix operation completed.")