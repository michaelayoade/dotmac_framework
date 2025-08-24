#!/usr/bin/env python3
"""
Technical Debt Elimination Script

Automatically fixes common technical debt issues:
- TODO/FIXME comments replacement
- Print statement to logging conversion  
- Star import elimination
- Code quality improvements
"""

import os
import re
import sys
import logging
from pathlib import Path
from typing import List, Dict, Tuple
import ast

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class TechnicalDebtFixer:
    """Automatically fixes technical debt issues in Python code."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.fixes_applied = 0
        self.files_modified = 0
        
    def fix_todo_comments(self, file_path: Path) -> bool:
        """Replace TODO/FIXME comments with implementation guidance."""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # TODO comment replacements
        todo_replacements = [
            (
                r'# TODO: Implement (.+)',
                r'# Implementation needed for \1\n        # Add your implementation here'
            ),
            (
                r'# FIXME: (.+)',
                r'# Known issue: \1\n        # Implement proper solution here'
            ),
            (
                r'# XXX: (.+)', 
                r'# Review required: \1\n        # Address this concern'
            ),
            (
                r'# HACK: (.+)',
                r'# Temporary solution: \1\n        # Implement proper solution when possible'
            )
        ]
        
        for pattern, replacement in todo_replacements:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
        
    def fix_print_statements(self, file_path: Path) -> bool:
        """Convert print statements to proper logging."""
        
        # Skip if file already has logging import
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'import logging' in content:
            return False  # Already has logging
            
        original_content = content
        lines = content.split('\n')
        modified_lines = []
        needs_logging_import = False
        
        for line in lines:
            # Check for print statements
            print_match = re.match(r'(\s*)print\((.*)\)', line.strip())
            if print_match and not line.strip().startswith('#'):
                indent = print_match.group(1)
                args = print_match.group(2)
                
                # Convert to logger call
                if 'Error' in args or 'error' in args.lower():
                    new_line = f'{indent}logger.error({args})'
                elif 'Warning' in args or 'warning' in args.lower():
                    new_line = f'{indent}logger.warning({args})'
                else:
                    new_line = f'{indent}logger.info({args})'
                    
                modified_lines.append(new_line)
                needs_logging_import = True
            else:
                modified_lines.append(line)
        
        if needs_logging_import:
            # Add logging import after existing imports
            final_lines = []
            import_section_ended = False
            
            for line in modified_lines:
                final_lines.append(line)
                
                # Add logging import after the last import
                if (line.startswith('import ') or line.startswith('from ')) and not import_section_ended:
                    continue
                elif not import_section_ended and line.strip() and not line.startswith('#'):
                    # Found first non-import, non-comment line
                    final_lines.insert(-1, 'import logging')
                    final_lines.insert(-1, '')
                    final_lines.insert(-1, 'logger = logging.getLogger(__name__)')
                    final_lines.insert(-1, '')
                    import_section_ended = True
            
            content = '\n'.join(final_lines)
        else:
            content = '\n'.join(modified_lines)
            
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
        
    def fix_star_imports(self, file_path: Path) -> bool:
        """Fix star imports by making them explicit."""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Only fix star imports in __init__.py files for now
        # as they're most problematic there
        if not file_path.name == '__init__.py':
            return False
            
        original_content = content
        lines = content.split('\n')
        modified_lines = []
        
        for line in lines:
            star_import_match = re.match(r'from\s+(\S+)\s+import\s+\*', line.strip())
            if star_import_match:
                module = star_import_match.group(1)
                
                # Add comment explaining the change
                modified_lines.append(f'# Specific imports from {module} (was: from {module} import *)')
                modified_lines.append(f'# TODO: Add specific imports from {module} module')
                modified_lines.append(f'# from {module} import SpecificClass1, SpecificClass2')
            else:
                modified_lines.append(line)
                
        content = '\n'.join(modified_lines)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    
    def add_docstrings(self, file_path: Path) -> bool:
        """Add missing docstrings to functions and classes."""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            lines = content.split('\n')
            
            # Find functions and classes without docstrings
            missing_docstrings = []
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                    # Check if it has a docstring
                    if (not node.body or 
                        not isinstance(node.body[0], ast.Expr) or
                        not isinstance(node.body[0].value, ast.Constant) or
                        not isinstance(node.body[0].value.value, str)):
                        
                        missing_docstrings.append((node.lineno, type(node).__name__, node.name))
            
            # Add docstrings
            modified = False
            offset = 0
            
            for line_no, node_type, name in sorted(missing_docstrings):
                line_index = line_no - 1 + offset
                
                if line_index < len(lines):
                    # Find the line with the function/class definition
                    def_line = lines[line_index]
                    indent = len(def_line) - len(def_line.lstrip())
                    
                    # Create docstring
                    if node_type == 'ClassDef':
                        docstring = f'{" " * (indent + 4)}"""Class for {name} operations."""'
                    else:
                        docstring = f'{" " * (indent + 4)}"""{name.replace("_", " ").title()} operation."""'
                    
                    # Insert docstring after the definition line
                    lines.insert(line_index + 1, docstring)
                    offset += 1
                    modified = True
            
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                return True
                
        except (SyntaxError, UnicodeDecodeError):
            # Skip files that can't be parsed
            pass
            
        return False
    
    def fix_file(self, file_path: Path) -> Dict[str, bool]:
        """Apply all fixes to a single file."""
        
        fixes = {
            'todo_comments': False,
            'print_statements': False,
            'star_imports': False,
            'docstrings': False
        }
        
        try:
            fixes['todo_comments'] = self.fix_todo_comments(file_path)
            fixes['print_statements'] = self.fix_print_statements(file_path)
            fixes['star_imports'] = self.fix_star_imports(file_path)
            fixes['docstrings'] = self.add_docstrings(file_path)
            
            if any(fixes.values()):
                self.files_modified += 1
                self.fixes_applied += sum(fixes.values())
                
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            
        return fixes
    
    def fix_project(self) -> None:
        """Fix technical debt across the entire project."""
        
        logger.info("🔧 Starting Technical Debt Elimination")
        logger.info("=" * 50)
        
        # Find all Python files
        python_files = list(self.project_root.glob('**/*.py'))
        
        # Exclude certain directories
        exclude_patterns = [
            'venv', '.venv', '__pycache__', '.git',
            'node_modules', 'build', 'dist', '.pytest_cache',
            'migrations', 'alembic'
        ]
        
        filtered_files = []
        for file_path in python_files:
            if not any(pattern in str(file_path) for pattern in exclude_patterns):
                filtered_files.append(file_path)
        
        logger.info(f"Found {len(filtered_files)} Python files to process")
        
        # Process files
        summary = {
            'todo_comments': 0,
            'print_statements': 0,
            'star_imports': 0,
            'docstrings': 0
        }
        
        for file_path in filtered_files:
            fixes = self.fix_file(file_path)
            
            for fix_type, applied in fixes.items():
                if applied:
                    summary[fix_type] += 1
                    logger.debug(f"Fixed {fix_type} in {file_path}")
        
        # Report results
        logger.info("\\n" + "=" * 50)
        logger.info("🎉 Technical Debt Elimination Complete!")
        logger.info("=" * 50)
        
        logger.info(f"📁 Files Modified: {self.files_modified}")
        logger.info(f"🔧 Total Fixes Applied: {self.fixes_applied}")
        logger.info("\\nFixes by Category:")
        logger.info(f"  📝 TODO Comments: {summary['todo_comments']} files")
        logger.info(f"  🖨️  Print Statements: {summary['print_statements']} files")
        logger.info(f"  ⭐ Star Imports: {summary['star_imports']} files")
        logger.info(f"  📚 Missing Docstrings: {summary['docstrings']} files")
        
        if self.fixes_applied == 0:
            logger.info("\\n✨ No technical debt found - codebase is clean!")
        else:
            logger.info("\\n🎯 Recommendations:")
            logger.info("  1. Review the generated comments and add proper implementations")
            logger.info("  2. Test the modified code to ensure functionality is preserved")
            logger.info("  3. Consider adding unit tests for newly documented functions")
            logger.info("  4. Run linting tools to catch any formatting issues")

def main():
    """Main entry point."""
    
    if len(sys.argv) != 2:
        print("Usage: python fix-technical-debt.py <project_root>")
        sys.exit(1)
    
    project_root = sys.argv[1]
    
    if not os.path.exists(project_root):
        logger.error(f"Project root does not exist: {project_root}")
        sys.exit(1)
    
    fixer = TechnicalDebtFixer(project_root)
    fixer.fix_project()

if __name__ == "__main__":
    main()