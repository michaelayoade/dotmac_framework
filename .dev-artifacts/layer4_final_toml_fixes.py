#!/usr/bin/env python3
"""
Layer 4: Final comprehensive TOML fixes for remaining syntax errors.

This script will handle:
1. All remaining dictionary-style inline table syntax
2. Orphaned configuration lines
3. Missing section headers
4. Malformed arrays and strings
"""

import re
from pathlib import Path
import tomllib

def layer4_final_fixes():
    """Layer 4: Final comprehensive TOML fixes."""
    
    packages_dir = Path("/home/dotmac_framework/packages")
    toml_files = list(packages_dir.glob("*/pyproject.toml"))
    
    print(f"🔍 Found {len(toml_files)} pyproject.toml files")
    
    fixed_files = 0
    
    for toml_file in toml_files:
        print(f"\n📝 Processing {toml_file.relative_to(Path.cwd())}")
        
        try:
            content = toml_file.read_text()
            original_content = content
            
            # Test current syntax
            try:
                tomllib.loads(content)
                print(f"  ✅ Already valid TOML")
                continue
            except tomllib.TOMLDecodeError:
                pass
            
            # Fix 1: All dictionary-style inline table syntax
            # {"path": "...", "develop": True, "optional": True} → {path = "...", develop = true, optional = true}
            content = re.sub(
                r'\{"path":\s*"([^"]+)",\s*"develop":\s*(True|False)(?:,\s*"optional":\s*(True|False))?\}',
                lambda m: f'{{path = "{m.group(1)}", develop = {m.group(2).lower()}{f", optional = {m.group(3).lower()}" if m.group(3) else ""}}}',
                content
            )
            
            # Fix 2: Version-only dictionary syntax
            # {"version": "...", "optional": True} → {version = "...", optional = true}
            content = re.sub(
                r'\{"version":\s*"([^"]+)",\s*"optional":\s*(True|False)\}',
                lambda m: f'{{version = "{m.group(1)}", optional = {m.group(2).lower()}}}',
                content
            )
            
            # Fix 3: Remove orphaned lines that are not part of any section
            lines = content.split('\n')
            fixed_lines = []
            in_section = False
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                
                # Check if this is a section header
                if stripped.startswith('[') and stripped.endswith(']'):
                    in_section = True
                    fixed_lines.append(line)
                    continue
                
                # If we're not in a section and this looks like a config line, skip it
                if not in_section and ('=' in stripped or stripped.startswith('include =') or stripped.startswith('where =')):
                    print(f"  🗑️  Removing orphaned line: {stripped}")
                    continue
                
                # If it's an empty line or comment, always keep it
                if not stripped or stripped.startswith('#'):
                    fixed_lines.append(line)
                    continue
                
                # If we're in a section, keep the line
                if in_section:
                    fixed_lines.append(line)
                    continue
                
                # Otherwise keep it for now
                fixed_lines.append(line)
            
            content = '\n'.join(fixed_lines)
            
            # Fix 4: Fix malformed extend-exclude patterns
            content = re.sub(
                r'extend-exclude = "/\(\(\n.*?\)\)/\"',
                'extend-exclude = "/(build|dist|migrations)/"',
                content,
                flags=re.DOTALL
            )
            
            # Fix 5: Fix merged sections at line endings
            # Look for patterns like: asyncio_mode = "auto"[tool.mypy]
            content = re.sub(r'(\w+.*?)(\[tool\.)', r'\1\n\n\2', content)
            
            # Fix 6: Clean up excessive whitespace
            content = re.sub(r'\n{3,}', '\n\n', content)
            content = re.sub(r'^\s*\n', '', content, flags=re.MULTILINE)
            
            # Test the fixed content
            try:
                tomllib.loads(content)
                print(f"  ✅ Fixed TOML syntax successfully")
            except tomllib.TOMLDecodeError as e:
                print(f"  ⚠️  Still has TOML error: {e}")
                # Keep trying with more aggressive fixes
                continue
            
            if content != original_content:
                toml_file.write_text(content)
                fixed_files += 1
                print(f"  💾 Saved fixes to {toml_file.name}")
            else:
                print(f"  ✨ No changes needed for {toml_file.name}")
                
        except Exception as e:
            print(f"  ❌ Error processing {toml_file.name}: {e}")
    
    print(f"\n📊 Layer 4 Results:")
    print(f"   Files processed: {len(toml_files)}")
    print(f"   Files fixed: {fixed_files}")

if __name__ == "__main__":
    layer4_final_fixes()