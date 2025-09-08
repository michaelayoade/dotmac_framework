#!/usr/bin/env python3
"""
Layer 2: Clean up malformed TOML syntax introduced by Layer 1
- Remove extra quotes and spaces from TOML values
- Fix duplicated array elements
- Ensure proper TOML formatting
"""

import re
from pathlib import Path
from typing import List, Tuple


class Layer2TOMLCleanup:
    def __init__(self):
        self.packages_dir = Path("/home/dotmac_framework/packages")
        self.fixes_applied = []

    def clean_toml_content(self, content: str) -> str:
        """Clean up malformed TOML syntax"""
        original_content = content
        
        # Fix 1: Complex array patterns with nested quotes
        # packages = "[{include = "dotmac"", from = " "src"}"]
        content = re.sub(r'= "\[{([^}]+)}\]"', r'= [{\1}]', content)
        
        # Fix 2: Simple array patterns with extra quotes  
        # " ["poetry-core""] -> ["poetry-core"]
        content = re.sub(r'= " \[([^\]]+)\]"', r'= [\1]', content)
        
        # Fix 3: Array values with escaped quotes
        # target-version = "["py39"", "py310", "py311", "py312"]
        content = re.sub(r'= "\[([^\]]+)\]"', r'= [\1]', content)
        
        # Fix 4: Remove extra quotes around string values
        # " "value"" -> "value"
        content = re.sub(r'= " "([^"]+)""', r'= "\1"', content)
        
        # Fix 5: Fix malformed arrays with extra quotes
        # ["value""] -> ["value"]
        content = re.sub(r'\["([^"]+)""\]', r'["\1"]', content)
        
        # Fix 6: Clean up spacing issues around equals
        # key = " value" -> key = "value"
        content = re.sub(r'= " ([^"]+)"', r'= "\1"', content)
        
        # Fix 7: Fix nested quotes in object syntax
        # include = "dotmac"", from = " "src" -> include = "dotmac", from = "src"
        content = re.sub(r'include = "([^"]+)"", from = " "([^"]+)"', r'include = "\1", from = "\2"', content)
        
        # Fix 8: Fix version object syntax
        # {version = ">=0.12.0"", optional = "true"} -> {version = ">=0.12.0", optional = true}
        content = re.sub(r'version = "([^"]+)"", optional = "([^"]+)"', r'version = "\1", optional = \2', content)
        
        # Fix 9: Remove double quotes in array elements
        # "["py39"", -> ["py39",
        content = re.sub(r'"(\[[^]]*)"([^]]*)\]"', r'\1\2]', content)
        
        # Fix 5: Remove duplicate array elements in classifiers
        lines = content.split('\n')
        cleaned_lines = []
        in_classifiers = False
        classifier_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            if stripped.startswith('classifiers = ['):
                in_classifiers = True
                classifier_lines = [line]
            elif in_classifiers and stripped == ']':
                classifier_lines.append(line)
                # Deduplicate classifier entries
                unique_classifiers = []
                seen = set()
                
                for cl_line in classifier_lines[1:-1]:  # Skip opening and closing
                    cl_stripped = cl_line.strip(' ",\n')
                    if cl_stripped and cl_stripped not in seen:
                        seen.add(cl_stripped)
                        unique_classifiers.append(cl_line)
                
                # Rebuild classifiers section
                cleaned_lines.append(classifier_lines[0])  # Opening
                cleaned_lines.extend(unique_classifiers)
                cleaned_lines.append(classifier_lines[-1])  # Closing
                in_classifiers = False
                classifier_lines = []
            elif in_classifiers:
                classifier_lines.append(line)
            else:
                cleaned_lines.append(line)
        
        content = '\n'.join(cleaned_lines)
        
        # Fix 6: Ensure proper TOML section headers
        content = re.sub(r'^\s*\[([^\]]+)\]\s*\n\s*\n', r'[\1]\n', content, flags=re.MULTILINE)
        
        # Fix 7: Remove extra blank lines (max 2 consecutive)
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content

    def validate_toml_syntax(self, content: str) -> Tuple[bool, str]:
        """Validate TOML syntax using basic checks"""
        try:
            # Basic validation checks
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if not stripped or stripped.startswith('#'):
                    continue
                
                # Check for malformed quotes
                if '""' in stripped and not stripped.startswith('"""'):
                    return False, f"Line {i}: Double quotes found: {stripped}"
                
                # Check for malformed arrays
                if re.search(r'\[.*".*".*\]', stripped):
                    bracket_count = stripped.count('[') - stripped.count(']')
                    if bracket_count != 0:
                        return False, f"Line {i}: Unmatched brackets: {stripped}"
            
            return True, "TOML syntax appears valid"
            
        except Exception as e:
            return False, f"Validation error: {e}"

    def process_package(self, package_path: Path) -> bool:
        """Process a single package's pyproject.toml"""
        toml_file = package_path / "pyproject.toml"
        
        if not toml_file.exists():
            print(f"❌ No pyproject.toml found in {package_path.name}")
            return False
        
        try:
            # Read current content
            content = toml_file.read_text()
            
            # Clean up TOML syntax
            cleaned_content = self.clean_toml_content(content)
            
            # Validate cleaned content
            is_valid, message = self.validate_toml_syntax(cleaned_content)
            
            if not is_valid:
                print(f"❌ {package_path.name}: Validation failed - {message}")
                return False
            
            # Write cleaned content
            if cleaned_content != content:
                toml_file.write_text(cleaned_content)
                self.fixes_applied.append(f"{package_path.name}: TOML syntax cleaned")
                print(f"✅ {package_path.name}: TOML syntax cleaned and validated")
            else:
                print(f"✅ {package_path.name}: Already clean")
            
            return True
            
        except Exception as e:
            print(f"❌ {package_path.name}: Error processing - {e}")
            return False

    def run(self) -> bool:
        """Run Layer 2 cleanup on all packages"""
        print("🔧 Layer 2: Cleaning up TOML syntax errors")
        print("=" * 50)
        
        if not self.packages_dir.exists():
            print(f"❌ Packages directory not found: {self.packages_dir}")
            return False
        
        packages = [p for p in self.packages_dir.iterdir() if p.is_dir()]
        success_count = 0
        
        for package_path in sorted(packages):
            if self.process_package(package_path):
                success_count += 1
        
        print("\n" + "=" * 50)
        print(f"📊 Layer 2 Results:")
        print(f"   Processed: {len(packages)} packages")
        print(f"   Success: {success_count}")
        print(f"   Failed: {len(packages) - success_count}")
        
        if self.fixes_applied:
            print(f"\n🔧 Fixes Applied:")
            for fix in self.fixes_applied:
                print(f"   • {fix}")
        
        return success_count == len(packages)


if __name__ == "__main__":
    cleanup = Layer2TOMLCleanup()
    success = cleanup.run()
    
    if success:
        print("\n✅ Layer 2 completed successfully!")
        print("Ready for Layer 3: Update Poetry lock files and dependencies")
    else:
        print("\n❌ Layer 2 had issues - review errors above")