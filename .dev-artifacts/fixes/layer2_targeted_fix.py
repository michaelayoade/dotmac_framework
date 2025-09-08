#!/usr/bin/env python3
"""
Layer 2: Targeted fix for Layer 1 malformed TOML syntax
Direct fix for specific patterns introduced by Layer 1
"""

import re
from pathlib import Path


class Layer2TargetedFix:
    def __init__(self):
        self.packages_dir = Path("/home/dotmac_framework/packages")
        self.fixes_applied = []

    def fix_toml_file(self, file_path: Path) -> bool:
        """Apply targeted fixes to a TOML file"""
        try:
            content = file_path.read_text()
            original_content = content
            
            # Fix 1: Pattern = " "value""  -> = "value"
            content = re.sub(r'= " "([^"]+)""', r'= "\1"', content)
            
            # Fix 2: Pattern = " ["array", "items""]  -> = ["array", "items"]
            content = re.sub(r'= " \[([^\]]+)\]"', r'= [\1]', content)
            
            # Fix 3: Pattern target-version = " ["py39"", "py310"] -> target-version = ["py39", "py310"]
            content = re.sub(r'target-version = " \[([^\]]+)\]"', r'target-version = [\1]', content)
            
            # Fix 4: Pattern select = " ["E"", "W""] -> select = ["E", "W"]
            content = re.sub(r'select = " \[([^\]]+)\]"', r'select = [\1]', content)
            
            # Fix 5: Pattern python_files = " ["test_*.py""] -> python_files = ["test_*.py"]
            content = re.sub(r'python_files = " \[([^\]]+)\]"', r'python_files = [\1]', content)
            
            # Fix 6: Pattern include = " ["/src""] -> include = ["/src"]
            content = re.sub(r'include = " \[([^\]]+)\]"', r'include = [\1]', content)
            
            # Fix 7: Pattern packages = " [{include = "dotmac"", from = " "src"}"] -> packages = [{include = "dotmac", from = "src"}]
            content = re.sub(r'packages = " \[{([^}]+)}\]"', r'packages = [{\1}]', content)
            
            # Fix 8: Inside package objects, fix nested quotes
            # include = "dotmac"", from = " "src" -> include = "dotmac", from = "src"
            content = re.sub(r'include = "([^"]+)"", from = " "([^"]+)"', r'include = "\1", from = "\2"', content)
            
            # Fix 9: Dependency objects {version = ">=0.12.0"", optional = "true"}
            content = re.sub(r'{version = "([^"]+)"", optional = "([^"]+)"}', r'{version = "\1", optional = \2}', content)
            content = re.sub(r'{version = "([^"]+)"", python = "([^"]+)"}', r'{version = "\1", python = "\2"}', content)
            
            # Fix 10: Path dependencies {path = "../dotmac-core"", develop = "true"}
            content = re.sub(r'{path = "([^"]+)"", develop = "([^"]+)"}', r'{path = "\1", develop = \2}', content)
            
            # Fix 11: Clean up double quotes in array elements ""value"" -> "value"
            content = re.sub(r'""([^"]+)""', r'"\1"', content)
            
            # Fix 12: Remove extra spaces and ensure proper formatting
            content = re.sub(r'requires = " \[([^\]]+)\]"', r'requires = [\1]', content)
            content = re.sub(r'build-backend = " "([^"]+)""', r'build-backend = "\1"', content)
            
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

    def run(self) -> bool:
        """Run targeted fixes on all packages"""
        print("🔧 Layer 2: Targeted TOML syntax fixes")
        print("=" * 50)
        
        packages = [p for p in self.packages_dir.iterdir() if p.is_dir()]
        success_count = 0
        
        for package_path in sorted(packages):
            toml_file = package_path / "pyproject.toml"
            if toml_file.exists():
                if self.fix_toml_file(toml_file):
                    success_count += 1
        
        print(f"\n📊 Results: {success_count}/{len(packages)} packages processed")
        if self.fixes_applied:
            print(f"🔧 Fixed: {', '.join(self.fixes_applied)}")
        
        return success_count == len(packages)


if __name__ == "__main__":
    fix = Layer2TargetedFix()
    success = fix.run()
    
    if success:
        print("\n✅ Layer 2 completed successfully!")
    else:
        print("\n❌ Some packages had issues")