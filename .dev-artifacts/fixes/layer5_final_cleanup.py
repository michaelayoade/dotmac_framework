#!/usr/bin/env python3
"""
Layer 5: Final cleanup for the 4 packages that still have issues
"""

from pathlib import Path


class Layer5FinalCleanup:
    def __init__(self):
        self.packages_dir = Path("/home/dotmac_framework/packages")

    def fix_workflows(self):
        """Fix dotmac-workflows"""
        file_path = self.packages_dir / "dotmac-workflows" / "pyproject.toml"
        content = file_path.read_text()
        content = content.replace('python_functions = ["test_*""]', 'python_functions = ["test_*"]')
        file_path.write_text(content)
        print("✅ Fixed dotmac-workflows")

    def fix_platform_services(self):
        """Fix dotmac-platform-services"""
        file_path = self.packages_dir / "dotmac-platform-services" / "pyproject.toml"
        content = file_path.read_text()
        # Fix the nested quotes in addopts
        content = content.replace('--cov = "src/dotmac"', '--cov=src/dotmac')
        content = content.replace('--cov-report = "term-missing:skip-covered"', '--cov-report=term-missing:skip-covered')
        content = content.replace('--cov-report = "html"', '--cov-report=html')
        content = content.replace('--cov-report = "xml"', '--cov-report=xml')
        content = content.replace('--cov-fail-under = "60"', '--cov-fail-under=60')
        content = content.replace('""', '"')  # Remove any remaining double quotes
        file_path.write_text(content)
        print("✅ Fixed dotmac-platform-services")

    def fix_security(self):
        """Fix dotmac-security"""
        file_path = self.packages_dir / "dotmac-security" / "pyproject.toml"
        content = file_path.read_text()
        # Fix the nested quotes in exclude_lines
        content = content.replace('if __name__ = "= .__main__.:"', 'if __name__ == .__main__.:')
        content = content.replace('""', '"')  # Remove remaining double quotes
        file_path.write_text(content)
        print("✅ Fixed dotmac-security")

    def fix_shared_core(self):
        """Fix dotmac-shared-core"""
        file_path = self.packages_dir / "dotmac-shared-core" / "pyproject.toml"
        content = file_path.read_text()
        # Fix the malformed line
        content = content.replace('indent-style = " "space"line-ending = "auto""', 'indent-style = "space"\nline-ending = "auto"')
        file_path.write_text(content)
        print("✅ Fixed dotmac-shared-core")

    def run(self):
        """Run all fixes"""
        print("🔧 Layer 5: Final cleanup of remaining 4 packages")
        print("=" * 50)
        
        self.fix_workflows()
        self.fix_platform_services()
        self.fix_security()
        self.fix_shared_core()
        
        print("\n✅ Layer 5 completed!")


if __name__ == "__main__":
    cleanup = Layer5FinalCleanup()
    cleanup.run()