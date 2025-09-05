#!/usr/bin/env python3
"""
Strategic Ruff Issues Cleanup Script

Systematically addresses the 4 major categories of Ruff issues:
1. Print statements → proper logging (735 instances)
2. Unused imports (141 instances)
3. Broad exception handling (110 instances)
4. Undefined name references (98 instances)

Usage:
    python .dev-artifacts/strategic_ruff_cleanup.py --category=prints --dry-run
    python .dev-artifacts/strategic_ruff_cleanup.py --category=imports --apply
"""

import argparse
import ast
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


class RuffCleanupStrategy:
    """Strategic cleanup of Ruff issues with prioritized approach."""
    
    def __init__(self, project_root: Path, dry_run: bool = True):
        self.project_root = project_root
        self.dry_run = dry_run
        self.logger = self._setup_logging()
        
        # Issue counts from analysis
        self.issue_counts = {
            'prints': 735,
            'unused_imports': 141,
            'broad_exceptions': 110,
            'undefined_names': 98
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for cleanup operations."""
        logger = logging.getLogger('ruff_cleanup')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def get_ruff_issues(self, category: str) -> List[Dict]:
        """Get specific category of Ruff issues."""
        category_codes = {
            'prints': ['T201'],  # print() statements
            'unused_imports': ['F401'],  # unused imports
            'broad_exceptions': ['E722', 'BLE001'],  # broad exceptions
            'undefined_names': ['F821']  # undefined names
        }
        
        if category not in category_codes:
            raise ValueError(f"Unknown category: {category}")
        
        cmd = [
            'ruff', 'check', 
            '--select', ','.join(category_codes[category]),
            '--output-format', 'json',
            str(self.project_root)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.stdout:
                import json
                return json.loads(result.stdout)
            return []
        except Exception as e:
            self.logger.error(f"Failed to get Ruff issues: {e}")
            return []
    
    def cleanup_print_statements(self) -> int:
        """
        Strategic cleanup of print() statements.
        
        Priority:
        1. Error/warning prints → logger.error/warning
        2. Debug prints → logger.debug  
        3. Info prints → logger.info
        4. Remove development/temporary prints
        """
        issues = self.get_ruff_issues('prints')
        cleaned_count = 0
        
        self.logger.info(f"Processing {len(issues)} print statement issues...")
        
        # Group by file for efficient processing
        files_with_prints = {}
        for issue in issues:
            file_path = Path(issue['filename'])
            if file_path not in files_with_prints:
                files_with_prints[file_path] = []
            files_with_prints[file_path].append(issue)
        
        for file_path, file_issues in files_with_prints.items():
            cleaned_count += self._cleanup_prints_in_file(file_path, file_issues)
        
        return cleaned_count
    
    def _cleanup_prints_in_file(self, file_path: Path, issues: List[Dict]) -> int:
        """Cleanup print statements in a single file."""
        if not file_path.exists():
            return 0
        
        try:
            content = file_path.read_text(encoding='utf-8')
            original_lines = content.split('\n')
            modified_lines = original_lines.copy()
            changes_made = 0
            
            # Add logging import if not present
            has_logging_import = 'import logging' in content or 'from logging import' in content
            if not has_logging_import and not self.dry_run:
                # Find the best place to add logging import
                insert_line = self._find_import_insertion_point(original_lines)
                if insert_line is not None:
                    modified_lines.insert(insert_line, 'import logging')
                    # Adjust line numbers for subsequent changes
                    for issue in issues:
                        if issue['location']['row'] > insert_line:
                            issue['location']['row'] += 1
            
            # Process issues in reverse order to maintain line numbers
            issues_sorted = sorted(issues, key=lambda x: x['location']['row'], reverse=True)
            
            for issue in issues_sorted:
                line_num = issue['location']['row'] - 1  # Convert to 0-based
                if 0 <= line_num < len(modified_lines):
                    old_line = modified_lines[line_num]
                    new_line = self._convert_print_to_logging(old_line, file_path)
                    
                    if new_line != old_line:
                        if not self.dry_run:
                            modified_lines[line_num] = new_line
                        changes_made += 1
                        
                        self.logger.info(f"{file_path}:{line_num + 1}")
                        self.logger.info(f"  OLD: {old_line.strip()}")
                        self.logger.info(f"  NEW: {new_line.strip()}")
            
            # Write changes if not dry run
            if not self.dry_run and changes_made > 0:
                file_path.write_text('\n'.join(modified_lines), encoding='utf-8')
                self.logger.info(f"Updated {file_path} with {changes_made} changes")
            
            return changes_made
            
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")
            return 0
    
    def _find_import_insertion_point(self, lines: List[str]) -> int:
        """Find the best line to insert logging import."""
        # Look for existing imports
        import_end = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(('import ', 'from ')) and not stripped.startswith('from __future__'):
                import_end = i + 1
            elif stripped and not stripped.startswith('#') and import_end > 0:
                break
        
        return import_end if import_end > 0 else 0
    
    def _convert_print_to_logging(self, line: str, file_path: Path) -> str:
        """Convert print statement to appropriate logging call."""
        stripped = line.strip()
        indent = line[:len(line) - len(line.lstrip())]
        
        # Skip if already converted or not a simple print
        if 'logger.' in stripped or 'logging.' in stripped:
            return line
        
        # Extract print content
        print_match = re.match(r'print\((.*)\)', stripped)
        if not print_match:
            return line
        
        print_content = print_match.group(1).strip()
        
        # Determine appropriate logging level based on content
        content_lower = print_content.lower()
        
        # Add logger initialization if needed
        logger_name = f'logger = logging.getLogger(__name__)'
        
        if any(word in content_lower for word in ['error', 'failed', 'exception', 'critical']):
            log_level = 'error'
        elif any(word in content_lower for word in ['warning', 'warn', 'deprecated']):
            log_level = 'warning'
        elif any(word in content_lower for word in ['debug', 'trace', 'verbose']):
            log_level = 'debug'
        elif any(word in content_lower for word in ['todo', 'fixme', 'hack', 'temp']):
            # Remove development prints
            return f"{indent}# TODO: Removed debug print: {print_content}"
        else:
            log_level = 'info'
        
        # Handle f-strings and formatting
        if print_content.startswith('f"') or print_content.startswith("f'"):
            # F-string - can use directly
            new_line = f"{indent}logger.{log_level}({print_content})"
        elif '"' in print_content or "'" in print_content:
            # String literal
            new_line = f"{indent}logger.{log_level}({print_content})"
        else:
            # Variable or expression - wrap in f-string
            new_line = f"{indent}logger.{log_level}(f\"{print_content}\")"
        
        return new_line
    
    def cleanup_unused_imports(self) -> int:
        """
        Strategic cleanup of unused imports.
        
        Uses Ruff's --fix capability for automatic removal.
        """
        self.logger.info("Cleaning up unused imports using Ruff --fix...")
        
        cmd = [
            'ruff', 'check',
            '--select', 'F401',  # unused imports
            '--fix' if not self.dry_run else '--diff',
            str(self.project_root)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if self.dry_run:
                # Count potential fixes from diff output
                fixes = len(re.findall(r'^\-.*import', result.stdout, re.MULTILINE))
                self.logger.info(f"Would remove {fixes} unused imports")
                return fixes
            else:
                # Get count of actual fixes
                issues_before = len(self.get_ruff_issues('unused_imports'))
                issues_after = len(self.get_ruff_issues('unused_imports'))
                fixed = issues_before - issues_after
                self.logger.info(f"Removed {fixed} unused imports")
                return fixed
                
        except Exception as e:
            self.logger.error(f"Error cleaning unused imports: {e}")
            return 0
    
    def cleanup_broad_exceptions(self) -> int:
        """
        Strategic cleanup of broad exception handling.
        
        Priority:
        1. except: → except Exception:
        2. Add specific exception types where possible
        3. Improve error handling patterns
        """
        issues = self.get_ruff_issues('broad_exceptions')
        cleaned_count = 0
        
        self.logger.info(f"Processing {len(issues)} broad exception issues...")
        
        # Group by file
        files_with_exceptions = {}
        for issue in issues:
            file_path = Path(issue['filename'])
            if file_path not in files_with_exceptions:
                files_with_exceptions[file_path] = []
            files_with_exceptions[file_path].append(issue)
        
        for file_path, file_issues in files_with_exceptions.items():
            cleaned_count += self._cleanup_exceptions_in_file(file_path, file_issues)
        
        return cleaned_count
    
    def _cleanup_exceptions_in_file(self, file_path: Path, issues: List[Dict]) -> int:
        """Cleanup broad exception handling in a single file."""
        if not file_path.exists():
            return 0
        
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            changes_made = 0
            
            # Process in reverse order to maintain line numbers
            issues_sorted = sorted(issues, key=lambda x: x['location']['row'], reverse=True)
            
            for issue in issues_sorted:
                line_num = issue['location']['row'] - 1
                if 0 <= line_num < len(lines):
                    old_line = lines[line_num]
                    new_line = self._improve_exception_handling(old_line, file_path)
                    
                    if new_line != old_line:
                        if not self.dry_run:
                            lines[line_num] = new_line
                        changes_made += 1
                        
                        self.logger.info(f"{file_path}:{line_num + 1}")
                        self.logger.info(f"  OLD: {old_line.strip()}")
                        self.logger.info(f"  NEW: {new_line.strip()}")
            
            if not self.dry_run and changes_made > 0:
                file_path.write_text('\n'.join(lines), encoding='utf-8')
                self.logger.info(f"Updated {file_path} with {changes_made} changes")
            
            return changes_made
            
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")
            return 0
    
    def _improve_exception_handling(self, line: str, file_path: Path) -> str:
        """Improve exception handling pattern."""
        stripped = line.strip()
        indent = line[:len(line) - len(line.lstrip())]
        
        # Handle bare except:
        if stripped == 'except:':
            return f"{indent}except Exception as e:"
        
        # Handle except Exception: without variable
        if stripped == 'except Exception:':
            return f"{indent}except Exception as e:"
        
        # More specific patterns could be added based on context analysis
        return line
    
    def cleanup_undefined_names(self) -> int:
        """
        Strategic cleanup of undefined name references.
        
        Priority:
        1. Add missing imports
        2. Fix typos in variable names
        3. Add missing variable definitions
        """
        issues = self.get_ruff_issues('undefined_names')
        cleaned_count = 0
        
        self.logger.info(f"Processing {len(issues)} undefined name issues...")
        
        # This requires more sophisticated analysis
        # For now, report issues for manual review
        for issue in issues:
            self.logger.warning(f"Undefined name in {issue['filename']}:{issue['location']['row']}")
            self.logger.warning(f"  Issue: {issue['message']}")
            
            # Common fixes could be automated:
            if 'Dict' in issue['message'] or 'List' in issue['message']:
                cleaned_count += self._fix_typing_imports(Path(issue['filename']))
        
        return cleaned_count
    
    def _fix_typing_imports(self, file_path: Path) -> int:
        """Fix common typing imports (Dict, List, etc.)."""
        if not file_path.exists():
            return 0
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Check if typing imports are missing
            needs_typing_import = False
            if 'Dict[' in content and 'from typing import' not in content:
                needs_typing_import = True
            
            if needs_typing_import and not self.dry_run:
                # Add typing import
                lines = content.split('\n')
                import_line = self._find_import_insertion_point(lines)
                lines.insert(import_line, 'from typing import Dict, List, Optional, Any')
                file_path.write_text('\n'.join(lines), encoding='utf-8')
                self.logger.info(f"Added typing imports to {file_path}")
                return 1
            
        except Exception as e:
            self.logger.error(f"Error fixing typing imports in {file_path}: {e}")
        
        return 0
    
    def run_category_cleanup(self, category: str) -> int:
        """Run cleanup for specific category."""
        self.logger.info(f"Starting {category} cleanup...")
        
        cleanup_methods = {
            'prints': self.cleanup_print_statements,
            'imports': self.cleanup_unused_imports,
            'exceptions': self.cleanup_broad_exceptions,
            'undefined': self.cleanup_undefined_names
        }
        
        if category not in cleanup_methods:
            raise ValueError(f"Unknown category: {category}")
        
        return cleanup_methods[category]()
    
    def run_full_cleanup(self) -> Dict[str, int]:
        """Run full cleanup in strategic order."""
        results = {}
        
        # Order matters: imports first, then prints, then exceptions, finally undefined
        cleanup_order = ['imports', 'prints', 'exceptions', 'undefined']
        
        for category in cleanup_order:
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"PHASE {cleanup_order.index(category) + 1}: {category.upper()} CLEANUP")
            self.logger.info(f"{'='*60}")
            
            results[category] = self.run_category_cleanup(category)
            
            self.logger.info(f"Phase {cleanup_order.index(category) + 1} completed: {results[category]} issues addressed")
        
        return results
    
    def generate_report(self, results: Dict[str, int]) -> str:
        """Generate cleanup report."""
        total_fixed = sum(results.values())
        total_issues = sum(self.issue_counts.values())
        
        report = f"""
RUFF CLEANUP REPORT
{'='*50}

Issues Addressed:
  • Print statements: {results.get('prints', 0)}/{self.issue_counts['prints']}
  • Unused imports: {results.get('imports', 0)}/{self.issue_counts['unused_imports']}
  • Broad exceptions: {results.get('exceptions', 0)}/{self.issue_counts['broad_exceptions']}
  • Undefined names: {results.get('undefined', 0)}/{self.issue_counts['undefined_names']}

Total Progress: {total_fixed}/{total_issues} issues ({total_fixed/total_issues*100:.1f}%)

Recommendations:
  1. Run Ruff again to verify fixes
  2. Test functionality after changes
  3. Commit changes in logical groups
  4. Review remaining manual issues

Next Steps:
  ruff check --statistics  # Verify improvements
  python -m pytest tests/  # Run tests
"""
        
        return report


def main():
    parser = argparse.ArgumentParser(description='Strategic Ruff cleanup')
    parser.add_argument('--category', choices=['prints', 'imports', 'exceptions', 'undefined', 'all'],
                       default='all', help='Category to clean up')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed')
    parser.add_argument('--project-root', type=Path, default=Path('.'),
                       help='Project root directory')
    
    args = parser.parse_args()
    
    cleanup = RuffCleanupStrategy(args.project_root, args.dry_run)
    
    try:
        if args.category == 'all':
            results = cleanup.run_full_cleanup()
            print(cleanup.generate_report(results))
        else:
            fixed = cleanup.run_category_cleanup(args.category)
            print(f"\n{args.category.title()} cleanup: {fixed} issues addressed")
    
    except KeyboardInterrupt:
        print("\nCleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Cleanup failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()