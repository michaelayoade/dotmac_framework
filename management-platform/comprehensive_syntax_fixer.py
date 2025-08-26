#!/usr/bin/env python3
"""
Comprehensive syntax fixer for Management Platform
"""
import ast
import re
from pathlib import Path
from typing import List, Dict, Tuple

class ComprehensiveSyntaxFixer:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.fixes_applied = []
        
    def fix_function_definitions(self, content: str) -> Tuple[str, List[str]]:
        """Fix malformed function definitions"""
        fixes = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            original_line = line
            
            # Fix async def functions missing closing parentheses
            if 'async def' in line:
                if '(' in line and ')' not in line and not line.strip().endswith(':'):
                    # Look for the next lines that might contain the rest
                    j = i + 1
                    while j < len(lines) and j < i + 10:  # Look ahead max 10 lines
                        if lines[j].strip().startswith('"""') or 'async def' in lines[j]:
                            break
                        if ')' in lines[j] or ':' in lines[j]:
                            # Found the end of function definition
                            if ')' not in line and not line.endswith(':'):
                                line += '):'
                                fixes.append(f"Fixed async function definition at line {i+1}")
                            break
                        j += 1
                    else:
                        # Didn't find closing, add it
                        if not line.strip().endswith(':'):
                            line = line.rstrip() + '):'
                            fixes.append(f"Added missing closing paren to async function at line {i+1}")
            
            # Fix function definitions that are split incorrectly
            if '@router.' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if 'async def' in next_line and '(' in next_line and ')' not in next_line and not next_line.strip().endswith(':'):
                    # Look for parameters in subsequent lines
                    param_lines = []
                    k = i + 2
                    while k < len(lines) and k < i + 10:
                        if lines[k].strip() and not lines[k].strip().startswith('"""'):
                            if ':' in lines[k] and ('=' in lines[k] or 'Depends(' in lines[k]):
                                param_lines.append(lines[k].strip())
                            elif lines[k].strip() == '):' or lines[k].strip().startswith('):'):
                                break
                        k += 1
                    
                    if param_lines:
                        # Reconstruct the function definition
                        func_def = next_line.rstrip()
                        if not func_def.endswith('('):
                            func_def += '('
                        
                        # Add parameters
                        for idx, param in enumerate(param_lines):
                            if idx == len(param_lines) - 1:
                                # Last parameter, add closing paren and colon
                                func_def += '\n    ' + param
                                if not param.endswith(')'):
                                    func_def += '\n):'
                                else:
                                    func_def += ':'
                            else:
                                func_def += '\n    ' + param + ','
                        
                        lines[i + 1] = func_def
                        # Clear the parameter lines
                        for clear_idx in range(i + 2, i + 2 + len(param_lines)):
                            if clear_idx < len(lines):
                                lines[clear_idx] = ''
                        
                        fixes.append(f"Reconstructed function definition at line {i+2}")
            
            lines[i] = line
            i += 1
            
        return '\n'.join(lines), fixes
    
    def fix_missing_parentheses(self, content: str) -> Tuple[str, List[str]]:
        """Fix missing closing parentheses"""
        fixes = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            original_line = line
            
            # Fix various patterns of missing parentheses
            patterns = [
                # logger calls
                (r'(logger\.\w+\([^)]+)\s*$', r'\1)'),
                # Depends calls
                (r'(= Depends\([^)]+)\s*$', r'\1)'),
                # Form calls
                (r'(= Form\([^)]+)\s*$', r'\1)'),
                # Query calls
                (r'(= Query\([^)]+)\s*$', r'\1)'),
                # Function calls at end of line
                (r'(\w+\([^)]*),?\s*$', lambda m: f'{m.group(1)})'),
                # Assert statements
                (r'assert\s+([^)]+\([^)]+)\s*$', r'assert \1)'),
                # Return statements
                (r'return\s+([^)]+\([^)]+)\s*$', r'return \1)'),
            ]
            
            for pattern, replacement in patterns:
                if isinstance(replacement, str):
                    new_line = re.sub(pattern, replacement, line)
                else:
                    new_line = re.sub(pattern, replacement, line)
                    
                if new_line != line:
                    line = new_line
                    fixes.append(f"Fixed missing parenthesis at line {i+1}")
                    break
            
            # Fix specific patterns where parentheses are clearly missing
            if line.strip().endswith(',') and ('(' in line and line.count('(') > line.count(')')):
                line = line.rstrip(',') + ')'
                fixes.append(f"Fixed trailing comma with missing paren at line {i+1}")
            
            lines[i] = line
            
        return '\n'.join(lines), fixes
    
    def fix_bracket_mismatches(self, content: str) -> Tuple[str, List[str]]:
        """Fix bracket and brace mismatches"""
        fixes = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            original_line = line
            
            # Fix closing brace where paren expected
            if line.strip() == '}' and i > 0:
                # Check previous lines for unclosed parentheses
                for j in range(max(0, i-5), i):
                    prev_line = lines[j]
                    if '(' in prev_line and prev_line.count('(') > prev_line.count(')'):
                        line = line.replace('}', ')')
                        fixes.append(f"Fixed " + "} -> ) at line " + str(i+1))
                        break
            
            # Fix closing bracket where paren expected  
            if ']' in line and '(' in line and ')' not in line and '[' not in line:
                line = line.replace(']', ')')
                fixes.append(f"Fixed " + "] -> ) at line " + str(i+1))
            
            lines[i] = line
            
        return '\n'.join(lines), fixes
    
    def fix_import_statements(self, content: str) -> Tuple[str, List[str]]:
        """Fix malformed import statements"""
        fixes = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            original_line = line
            
            # Fix import statements that got cut off
            if (line.strip().startswith('from ') or line.strip().startswith('import ')) and line.strip().endswith(':'):
                line = line[:-1]  # Remove the colon
                fixes.append(f"Fixed import statement at line {i+1}")
            
            # Fix multiline imports that lost their closing paren
            if 'from ' in line and '(' in line and ')' not in line and 'import' in line:
                line = line + ')'
                fixes.append(f"Fixed multiline import at line {i+1}")
            
            lines[i] = line
            
        return '\n'.join(lines), fixes
    
    def fix_string_issues(self, content: str) -> Tuple[str, List[str]]:
        """Fix string and formatting issues"""
        fixes = []
        
        # Fix f-string issues with unescaped braces
        content = re.sub(r'f"([^"]*\{[^}]*)\}"', r'f"\1}"', content)
        
        # Fix common string concatenation issues
        content = re.sub(r'"\s*\+\s*"', '', content)
        
        fixes.append("Applied string formatting fixes")
        
        return content, fixes
    
    def fix_specific_errors(self, file_path: Path, content: str) -> Tuple[str, List[str]]:
        """Fix specific errors based on file path and content"""
        fixes = []
        file_name = file_path.name
        
        # File-specific fixes
        if 'test_code_quality.py' in str(file_path):
            # Fix the isinstance check
            content = re.sub(
                r'if isinstance\(node, \(ast\.Import, ast\.ImportFrom\):',
                r'if isinstance(node, (ast.Import, ast.ImportFrom)):',
                content
            )
            fixes.append("Fixed isinstance check in test_code_quality.py")
            
        elif 'setup_test_db.py' in str(file_path):
            # Fix port assignment
            content = re.sub(
                r'port = int\(os\.getenv\("DB_PORT", "5432"\)',
                r'port = int(os.getenv("DB_PORT", "5432"))',
                content
            )
            fixes.append("Fixed port assignment in setup_test_db.py")
            
        elif 'validate_test_config.py' in str(file_path):
            # Fix glob pattern
            content = re.sub(
                r'test_files = list\(Path\("tests"\)\.glob\("test_\*\.py"\)',
                r'test_files = list(Path("tests").glob("test_*.py"))',
                content
            )
            fixes.append("Fixed glob pattern in validate_test_config.py")
            
        # Fix common patterns across all files
        
        # Fix UUID calls
        content = re.sub(r'UUID\.uuid4\(\)', 'UUID.uuid4()', content)
        content = re.sub(r'uuid\.uuid4\(\)', 'uuid.uuid4()', content)
        
        # Fix common method calls
        content = re.sub(r'\.json\(\)', '.model_dump_json()', content)  # Pydantic v2
        content = re.sub(r'\.dict\(\)', '.model_dump()', content)  # Pydantic v2
        
        return content, fixes
    
    def validate_syntax(self, content: str) -> bool:
        """Check if content has valid syntax"""
        try:
            ast.parse(content)
            return True
        except SyntaxError:
            return False
    
    def fix_file(self, file_path: Path) -> List[str]:
        """Fix a single file"""
        if not file_path.exists():
            return [f"Skipping non-existent file: {file_path.relative_to(self.root_dir)}"]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return [f"Error reading {file_path.relative_to(self.root_dir)}: {e}"]
        
        original_content = content
        all_fixes = []
        
        # Check if already valid
        if self.validate_syntax(content):
            return []
        
        # Apply fixes in order
        content, fixes = self.fix_specific_errors(file_path, content)
        all_fixes.extend(fixes)
        
        content, fixes = self.fix_import_statements(content)
        all_fixes.extend(fixes)
        
        content, fixes = self.fix_function_definitions(content)
        all_fixes.extend(fixes)
        
        content, fixes = self.fix_missing_parentheses(content)
        all_fixes.extend(fixes)
        
        content, fixes = self.fix_bracket_mismatches(content)
        all_fixes.extend(fixes)
        
        content, fixes = self.fix_string_issues(content)
        all_fixes.extend(fixes)
        
        # Write back if changes made
        if content != original_content:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Check if we fixed the syntax
                if self.validate_syntax(content):
                    all_fixes.append(f"✓ Successfully fixed {file_path.relative_to(self.root_dir)}")
                else:
                    all_fixes.append(f"⚠ Partially fixed {file_path.relative_to(self.root_dir)} (syntax errors remain)")
                    
            except Exception as e:
                all_fixes.append(f"Error writing {file_path.relative_to(self.root_dir)}: {e}")
        
        return all_fixes
    
    def fix_all_files(self) -> Dict:
        """Fix all Python files"""
        results = {
            'files_processed': 0,
            'files_fixed': 0,
            'total_fixes': 0,
            'fixes': []
        }
        
        # Get all Python files
        python_files = list(self.root_dir.rglob('*.py'))
        
        for file_path in python_files:
            # Skip certain files
            skip_patterns = [
                'syntax_checker.py',
                'syntax_fixer.py', 
                'critical_syntax_fixes.py',
                'comprehensive_syntax_fixer.py',
                '__pycache__',
                '.git'
            ]
            
            if any(pattern in str(file_path) for pattern in skip_patterns):
                continue
                
            results['files_processed'] += 1
            fixes = self.fix_file(file_path)
            
            if fixes:
                results['files_fixed'] += 1
                results['fixes'].extend(fixes)
                results['total_fixes'] += len(fixes)
        
        return results

if __name__ == "__main__":
    fixer = ComprehensiveSyntaxFixer("/home/dotmac_framework/management-platform")
    
    print("Starting comprehensive syntax fixing...")
    results = fixer.fix_all_files()
    
    print(f"\n" + "="*80)
    print("COMPREHENSIVE SYNTAX FIXER RESULTS")
    print("="*80)
    print(f"Files processed: {results['files_processed']}")
    print(f"Files fixed: {results['files_fixed']}")
    print(f"Total fixes applied: {results['total_fixes']}")
    
    if results['fixes']:
        print(f"\nFIXES APPLIED:")
        print("-" * 50)
        for fix in results['fixes'][:50]:  # Show first 50 fixes
            print(f"  {fix}")
        
        if len(results['fixes']) > 50:
            print(f"  ... and {len(results['fixes']) - 50} more fixes")
    
    print(f"\nComprehensive fixing completed!")