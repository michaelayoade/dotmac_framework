#!/usr/bin/env python3

import subprocess
from pathlib import Path

def validate_poetry_packages():
    """Final validation of Poetry package configurations."""
    
    packages_dir = Path("packages")
    valid_count = 0
    invalid_count = 0
    
    print("🔍 Final Poetry Package Validation")
    print("=" * 50)
    
    for pyproject_file in packages_dir.rglob("pyproject.toml"):
        try:
            # Check if the file can be parsed by Poetry
            result = subprocess.run(
                ["poetry", "check", "--directory", str(pyproject_file.parent)],
                capture_output=True,
                text=True,
                cwd=pyproject_file.parent
            )
            
            if result.returncode == 0:
                print(f"✅ {pyproject_file.relative_to(packages_dir)}")
                valid_count += 1
            else:
                print(f"❌ {pyproject_file.relative_to(packages_dir)}")
                print(f"   Error: {result.stderr.strip()}")
                invalid_count += 1
                
        except Exception as e:
            print(f"❌ {pyproject_file.relative_to(packages_dir)} - {e}")
            invalid_count += 1
    
    print("\n📊 Final Validation Results:")
    print(f"   ✅ Successfully converted to Poetry: {valid_count} packages")
    print(f"   ❌ Issues remaining: {invalid_count} packages")
    
    if invalid_count == 0:
        print("\n🎉 ALL PACKAGES SUCCESSFULLY CONVERTED TO POETRY! 🎉")
        return True
    else:
        return False

if __name__ == "__main__":
    success = validate_poetry_packages()
    exit(0 if success else 1)