#!/usr/bin/env python3
"""
Layer 1: Fundamental TOML Structure Fix

This script fixes basic TOML syntax errors using a systematic approach:
1. Fix duplicated sections
2. Fix malformed arrays
3. Fix malformed key-value pairs
4. Ensure proper section ordering
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TOMLStructureFixer:
    def __init__(self):
        self.fixes_applied = {}
    
    def fix_duplicated_sections(self, content: str) -> str:
        """Fix duplicated section headers and merge content."""
        lines = content.split('\n')
        sections = {}
        current_section = None
        result_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Check for section header
            if line.startswith('[') and line.endswith(']') and '=' not in line:
                section_name = line
                if section_name in sections:
                    # Skip duplicate section header, content will be merged later
                    logger.debug(f"Skipping duplicate section: {section_name}")
                    i += 1
                    continue
                else:
                    sections[section_name] = True
                    current_section = section_name
            
            result_lines.append(lines[i])
            i += 1
        
        return '\n'.join(result_lines)
    
    def fix_malformed_arrays(self, content: str) -> str:
        """Fix malformed arrays, especially classifiers."""
        lines = content.split('\n')
        result_lines = []
        in_array = False
        array_name = None
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Check for start of array
            if '= [' in stripped and not stripped.endswith(']'):
                in_array = True
                array_name = stripped.split('=')[0].strip()
                result_lines.append(line)
                i += 1
                continue
            
            # Check for orphaned array items (lines starting with quotes)
            if not in_array and stripped.startswith('"') and stripped.endswith('",') and '=' not in stripped:
                # This looks like an orphaned array item - skip it
                logger.debug(f"Removing orphaned array item: {stripped}")
                i += 1
                continue
            
            # Check for end of array
            if in_array and (stripped == ']' or stripped.endswith(']')):
                in_array = False
                array_name = None
            
            result_lines.append(line)
            i += 1
        
        return '\n'.join(result_lines)
    
    def fix_malformed_key_values(self, content: str) -> str:
        """Fix malformed key-value pairs."""
        # Fix unquoted strings that should be quoted
        content = re.sub(r'(\w+)\s*=\s*([^"\[\{][^,\n\]]*?)(\s*[,\n\]])', r'\1 = "\2"\3', content)
        
        # Fix JSON-style objects in TOML
        # Convert {"key": "value", "key2": "value2"} to {key = "value", key2 = "value2"}
        def fix_json_object(match):
            obj_content = match.group(1)
            # Convert "key": "value" to key = "value"
            obj_content = re.sub(r'"([^"]+)"\s*:\s*"([^"]+)"', r'\1 = "\2"', obj_content)
            # Convert "key": true/false to key = true/false
            obj_content = re.sub(r'"([^"]+)"\s*:\s*(true|false)', r'\1 = \2', obj_content)
            return '{' + obj_content + '}'
        
        content = re.sub(r'\{([^}]+)\}', fix_json_object, content)
        
        return content
    
    def ensure_proper_sections(self, content: str) -> str:
        """Ensure proper TOML section ordering and structure."""
        lines = content.split('\n')
        sections = {
            'build-system': [],
            'tool.poetry': [],
            'tool.poetry.dependencies': [],
            'tool.poetry.group.dev.dependencies': [],
            'other': []
        }
        
        current_section = 'other'
        
        for line in lines:
            stripped = line.strip()
            
            if stripped.startswith('[build-system]'):
                current_section = 'build-system'
            elif stripped.startswith('[tool.poetry]') and not stripped.startswith('[tool.poetry.'):
                current_section = 'tool.poetry'
            elif stripped.startswith('[tool.poetry.dependencies]'):
                current_section = 'tool.poetry.dependencies'
            elif stripped.startswith('[tool.poetry.group.dev.dependencies]'):
                current_section = 'tool.poetry.group.dev.dependencies'
            elif stripped.startswith('[') and ']' in stripped:
                current_section = 'other'
            
            sections[current_section].append(line)
        
        # Reconstruct in proper order
        result = []
        
        # Add build-system first
        if sections['build-system']:
            result.extend(sections['build-system'])
            result.append('')
        
        # Add tool.poetry
        if sections['tool.poetry']:
            result.extend(sections['tool.poetry'])
            result.append('')
        
        # Add dependencies
        if sections['tool.poetry.dependencies']:
            result.extend(sections['tool.poetry.dependencies'])
            result.append('')
        
        # Add dev dependencies
        if sections['tool.poetry.group.dev.dependencies']:
            result.extend(sections['tool.poetry.group.dev.dependencies'])
            result.append('')
        
        # Add other sections
        if sections['other']:
            result.extend(sections['other'])
        
        return '\n'.join(result)
    
    def clean_empty_lines(self, content: str) -> str:
        """Clean up excessive empty lines."""
        # Replace multiple consecutive empty lines with single empty line
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        return content.strip() + '\n'
    
    def fix_file(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Fix a single TOML file."""
        logger.info(f"Layer 1 fixing: {file_path.name}")
        
        try:
            original_content = file_path.read_text(encoding='utf-8')
            content = original_content
            fixes = []
            
            # Apply fixes in order
            new_content = self.fix_duplicated_sections(content)
            if new_content != content:
                fixes.append("Fixed duplicated sections")
                content = new_content
            
            new_content = self.fix_malformed_arrays(content)
            if new_content != content:
                fixes.append("Fixed malformed arrays")
                content = new_content
            
            new_content = self.fix_malformed_key_values(content)
            if new_content != content:
                fixes.append("Fixed malformed key-value pairs")
                content = new_content
            
            new_content = self.ensure_proper_sections(content)
            if new_content != content:
                fixes.append("Reorganized sections")
                content = new_content
            
            content = self.clean_empty_lines(content)
            
            # Only write if changes were made
            if content != original_content:
                file_path.write_text(content, encoding='utf-8')
                logger.info(f"✅ Fixed {file_path.name}: {', '.join(fixes)}")
                return True, fixes
            else:
                logger.info(f"ℹ️ No changes needed for {file_path.name}")
                return True, []
            
        except Exception as e:
            logger.error(f"❌ Failed to fix {file_path}: {e}")
            return False, [f"Error: {e}"]
    
    def fix_all_files(self) -> Dict[str, Dict]:
        """Fix all pyproject.toml files in the project."""
        root_dir = Path.cwd()
        results = {}
        
        # Find all pyproject.toml files
        toml_files = []
        
        # Root file
        root_toml = root_dir / "pyproject.toml"
        if root_toml.exists():
            toml_files.append(("root", root_toml))
        
        # Package files
        packages_dir = root_dir / "packages"
        if packages_dir.exists():
            for package_dir in packages_dir.iterdir():
                if package_dir.is_dir():
                    toml_file = package_dir / "pyproject.toml"
                    if toml_file.exists():
                        toml_files.append((package_dir.name, toml_file))
        
        logger.info(f"🔧 Layer 1: Fixing {len(toml_files)} TOML files...")
        
        # Fix each file
        for name, toml_file in toml_files:
            success, fixes = self.fix_file(toml_file)
            results[name] = {
                "success": success,
                "fixes": fixes,
                "path": str(toml_file)
            }
        
        return results

def main():
    """Main entry point."""
    fixer = TOMLStructureFixer()
    results = fixer.fix_all_files()
    
    # Summary
    total = len(results)
    successful = sum(1 for r in results.values() if r["success"])
    failed = total - successful
    
    logger.info(f"\n📊 Layer 1 Fix Summary:")
    logger.info(f"  - Files processed: {total}")
    logger.info(f"  - Successfully fixed: {successful}")
    logger.info(f"  - Failed: {failed}")
    
    if failed == 0:
        logger.info("🎉 Layer 1 completed successfully!")
        return True
    else:
        logger.error("💥 Layer 1 had some failures")
        # Show failures
        for name, result in results.items():
            if not result["success"]:
                logger.error(f"  ❌ {name}: {result['fixes']}")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)