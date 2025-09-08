#!/usr/bin/env python3
"""
Layer 4: Final aggressive TOML fix - handle all remaining malformed patterns
Fix everything to ensure valid TOML syntax
"""

import re
from pathlib import Path


class Layer4FinalTOMLFix:
    def __init__(self):
        self.packages_dir = Path("/home/dotmac_framework/packages")
        self.fixes_applied = []

    def fix_toml_file(self, file_path: Path) -> bool:
        """Apply aggressive final fixes to a TOML file"""
        try:
            content = file_path.read_text()
            original_content = content
            
            # Fix 1: All remaining " [" patterns -> [
            content = re.sub(r'= " \[', r'= [', content)
            
            # Fix 2: All remaining ]" patterns -> ]
            content = re.sub(r'\]"', r']', content)
            
            # Fix 3: All remaining " "value"" patterns -> "value"
            content = re.sub(r'= " "([^"]+)""', r'= "\1"', content)
            
            # Fix 4: Fix build-system requires specifically
            content = re.sub(r'requires = " \["poetry-core""\]', r'requires = ["poetry-core"]', content)
            
            # Fix 5: Fix all array-like patterns with malformed quotes
            # authors = " ["value""] -> authors = ["value"]
            content = re.sub(r'(authors|testpaths|python_files|python_classes|python_functions|markers|addopts|filterwarnings|source|exclude_lines|known-first-party) = " \[([^\]]+)\]"?', 
                           r'\1 = [\2]', content)
            
            # Fix 6: Fix packages array specifically
            # packages = " [{include = "dotmac", from = "src"}"] -> packages = [{include = "dotmac", from = "src"}]
            content = re.sub(r'packages = " \[({[^}]+})\]"?', r'packages = [\1]', content)
            
            # Fix 7: Fix select arrays specifically for ruff
            # select = " ["E"", "W", "F"] -> select = ["E", "W", "F"]
            content = re.sub(r'(select|ignore) = " \[([^\]]+)\]"?', r'\1 = [\2]', content)
            
            # Fix 8: Fix target-version arrays
            # target-version = " ["py39"", "py310"] -> target-version = ["py39", "py310"]
            content = re.sub(r'target-version = " \[([^\]]+)\]"?', r'target-version = [\1]', content)
            
            # Fix 9: Remove all double quotes within array elements
            # "value"" -> "value"
            content = re.sub(r'""([^"]*)"', r'"\1"', content)
            
            # Fix 10: Fix boolean values that got quoted
            content = re.sub(r'develop = "true"', r'develop = true', content)
            content = re.sub(r'optional = "true"', r'optional = true', content)
            content = re.sub(r'strict = "true"', r'strict = true', content)
            content = re.sub(r'branch = "true"', r'branch = true', content)
            
            # Fix 11: Clean up any remaining malformed dependency objects
            # Fix complex version/path/develop objects
            content = re.sub(r'= " \{([^}]+)\}"', r'= {\1}', content)
            
            # Fix 12: Handle malformed multi-line strings and arrays
            lines = content.split('\n')
            cleaned_lines = []
            
            for line in lines:
                # Skip empty lines that might be artifacts
                if line.strip() == '""':
                    continue
                    
                # Fix lines that start with quote artifacts
                if line.strip().startswith('""') and len(line.strip()) > 2:
                    line = line.replace('""', '"', 1)
                
                cleaned_lines.append(line)
            
            content = '\n'.join(cleaned_lines)
            
            # Fix 13: Final cleanup of any remaining quote artifacts
            content = re.sub(r'^(\s*)""([^"]+)""(\s*)$', r'\1"\2"\3', content, flags=re.MULTILINE)
            
            if content != original_content:
                file_path.write_text(content)
                self.fixes_applied.append(file_path.parent.name)
                print(f"✅ Fixed {file_path.parent.name}")
                return True
            else:
                print(f"✅ {file_path.parent.name} already clean")
                return True
                
        except Exception as e:
            print(f"❌ Error fixing {file_path.parent.name}: {e}")
            return False

    def validate_toml_basic(self, file_path: Path) -> bool:
        """Basic TOML validation"""
        try:
            content = file_path.read_text()
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if not stripped or stripped.startswith('#'):
                    continue
                
                # Check for obvious malformed patterns
                if ' " [' in stripped:
                    print(f"❌ {file_path.parent.name}:{i}: Malformed array: {stripped}")
                    return False
                
                if '""' in stripped and not stripped.startswith('"""'):
                    print(f"❌ {file_path.parent.name}:{i}: Double quotes: {stripped}")
                    return False
                
                if ']"' in stripped:
                    print(f"❌ {file_path.parent.name}:{i}: Malformed array end: {stripped}")
                    return False
            
            print(f"✅ {file_path.parent.name}: Basic validation passed")
            return True
            
        except Exception as e:
            print(f"❌ {file_path.parent.name}: Validation error: {e}")
            return False

    def run(self) -> bool:
        """Run Layer 4 fixes and validation on all packages"""
        print("🔧 Layer 4: Final aggressive TOML fixes")
        print("=" * 50)
        
        packages = [p for p in self.packages_dir.iterdir() if p.is_dir()]
        fix_success = 0
        validation_success = 0
        
        # First pass: Apply fixes
        for package_path in sorted(packages):
            toml_file = package_path / "pyproject.toml"
            if toml_file.exists():
                if self.fix_toml_file(toml_file):
                    fix_success += 1
        
        print("\n🔍 Validating fixed files...")
        print("-" * 30)
        
        # Second pass: Validate
        for package_path in sorted(packages):
            toml_file = package_path / "pyproject.toml"
            if toml_file.exists():
                if self.validate_toml_basic(toml_file):
                    validation_success += 1
        
        print(f"\n📊 Results:")
        print(f"   Fixed: {fix_success}/{len(packages)} packages")
        print(f"   Validated: {validation_success}/{len(packages)} packages")
        
        if self.fixes_applied:
            print(f"🔧 Fixed: {', '.join(self.fixes_applied)}")
        
        return validation_success == len(packages)


if __name__ == "__main__":
    fix = Layer4FinalTOMLFix()
    success = fix.run()
    
    if success:
        print("\n✅ Layer 4 completed successfully!")
        print("Ready for Poetry build testing")
    else:
        print("\n❌ Some packages still have issues")