#!/usr/bin/env python3
"""
Layer 3: Fix remaining array and quote issues in TOML files
Clean up malformed arrays, duplicate sections, and remaining quote problems
"""

import re
from pathlib import Path


class Layer3ArrayCleanup:
    def __init__(self):
        self.packages_dir = Path("/home/dotmac_framework/packages")
        self.fixes_applied = []

    def fix_toml_file(self, file_path: Path) -> bool:
        """Apply Layer 3 fixes to a TOML file"""
        try:
            content = file_path.read_text()
            original_content = content
            
            # Fix 1: Still malformed arrays with quotes = " ["item""] -> = ["item"]
            content = re.sub(r'= " \[([^\]]+)\]"', r'= [\1]', content)
            
            # Fix 2: Fix remaining double quotes in strings ""value"" -> "value"
            content = re.sub(r'""([^"]+)""', r'"\1"', content)
            
            # Fix 3: Fix malformed dependency objects with quotes
            # {path = "../dotmac-core"", develop = "true"} -> {path = "../dotmac-core", develop = true}
            content = re.sub(r'\{([^}]*)"",([^}]*)"([^}]*)\}', r'{\1",\2\3}', content)
            content = re.sub(r'develop = "true"', r'develop = true', content)
            content = re.sub(r'optional = "true"', r'optional = true', content)
            
            # Fix 4: Fix packages array structure
            # packages = " [{include = "dotmac", from = "src"}"] -> packages = [{include = "dotmac", from = "src"}]
            content = re.sub(r'packages = " \[({[^}]+})\]"', r'packages = [\1]', content)
            
            # Fix 5: Fix extras arrays
            # voltha = " ["voltha-protos"", "grpcio", "grpcio-tools"] -> voltha = ["voltha-protos", "grpcio", "grpcio-tools"]
            content = re.sub(r'(\w+) = " \[([^\]]+)\]"', r'\1 = [\2]', content)
            
            # Fix 6: Clean up build-backend and requires
            content = re.sub(r'requires = " \[([^\]]+)\]"', r'requires = [\1]', content)
            content = re.sub(r'build-backend = " "([^"]+)""', r'build-backend = "\1"', content)
            
            # Fix 7: Fix malformed string descriptions with quotes in middle
            # description = " "ISP package - IPAM", device automation" -> description = "ISP package - IPAM, device automation"
            content = re.sub(r'description = " "([^"]*)", ([^"]*)"', r'description = "\1, \2"', content)
            
            # Fix 8: Fix remaining array elements in select, ignore, etc.
            # select = " ["E"", "F"] -> select = ["E", "F"]
            content = re.sub(r'(select|ignore|testpaths|python_files|python_classes|python_functions|markers|addopts|filterwarnings|source|exclude_lines) = " \[([^\]]+)\]"', 
                           r'\1 = [\2]', content)
            
            # Fix 9: Clean up duplicate sections and malformed classifiers
            lines = content.split('\n')
            cleaned_lines = []
            i = 0
            
            while i < len(lines):
                line = lines[i]
                
                # Handle duplicate classifier sections
                if line.strip().startswith('classifiers = '):
                    # Find the end of this classifiers section
                    classifier_lines = [line]
                    i += 1
                    bracket_count = line.count('[') - line.count(']')
                    
                    while i < len(lines) and bracket_count > 0:
                        classifier_lines.append(lines[i])
                        bracket_count += lines[i].count('[') - lines[i].count(']')
                        i += 1
                    
                    # Skip any orphaned classifier items that might follow
                    while i < len(lines) and (lines[i].strip().startswith('"') or lines[i].strip() == ']'):
                        if lines[i].strip() == ']':
                            break
                        i += 1
                    
                    # Add the cleaned classifier section
                    cleaned_lines.extend(classifier_lines)
                else:
                    cleaned_lines.append(line)
                    i += 1
            
            content = '\n'.join(cleaned_lines)
            
            # Fix 10: Ensure proper TOML boolean values (no quotes)
            content = re.sub(r'= "true"', r'= true', content)
            content = re.sub(r'= "false"', r'= false', content)
            
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
        """Run Layer 3 fixes on all packages"""
        print("🔧 Layer 3: Fixing remaining array and quote issues")
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
    fix = Layer3ArrayCleanup()
    success = fix.run()
    
    if success:
        print("\n✅ Layer 3 completed successfully!")
    else:
        print("\n❌ Some packages had issues")