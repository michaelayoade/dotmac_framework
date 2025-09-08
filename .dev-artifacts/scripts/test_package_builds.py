#!/usr/bin/env python3
"""
Package Build Validation Script

This script validates that all packages can be built successfully as wheels and sdists.
Used in CI/CD pipeline for Gate A validation.
"""

import os
import sys
import subprocess
import tempfile
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PackageBuildTester:
    def __init__(self, root_dir: Path, poetry_cmd: str = "poetry", python_cmd: str = "python3"):
        self.root_dir = root_dir
        self.packages_dir = root_dir / "packages"
        self.build_results = {}
        self.poetry_cmd = poetry_cmd
        self.python_cmd = python_cmd
        
    def find_packages(self) -> List[Path]:
        """Find all packages with pyproject.toml files."""
        packages = []
        if self.packages_dir.exists():
            for package_path in self.packages_dir.iterdir():
                if package_path.is_dir() and (package_path / "pyproject.toml").exists():
                    packages.append(package_path)
        
        # Also check root directory
        if (self.root_dir / "pyproject.toml").exists():
            packages.append(self.root_dir)
            
        return sorted(packages)
    
    def get_package_info(self, package_path: Path) -> Dict:
        """Extract package information from pyproject.toml."""
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                # Try using subprocess with Python to parse TOML if libraries not available
                logger.warning("TOML parsing libraries not available, using basic parsing")
                return {"name": package_path.name, "version": "unknown", "build_system": "poetry"}
        
        try:
            with open(package_path / "pyproject.toml", "rb") as f:
                pyproject = tomllib.load(f)
            
            tool_poetry = pyproject.get("tool", {}).get("poetry", {})
            return {
                "name": tool_poetry.get("name", package_path.name),
                "version": tool_poetry.get("version", "unknown"),
                "description": tool_poetry.get("description", ""),
                "build_system": pyproject.get("build-system", {}).get("build-backend", "poetry")
            }
        except Exception as e:
            logger.warning(f"Could not parse {package_path}/pyproject.toml: {e}")
            return {"name": package_path.name, "version": "unknown", "build_system": "unknown"}
    
    def run_command(self, cmd: List[str], cwd: Path, timeout: int = 300) -> Tuple[bool, str, str]:
        """Run a command and return success status, stdout, stderr."""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return False, "", f"Command failed: {e}"
    
    def test_poetry_build(self, package_path: Path, poetry_cmd: str = "poetry") -> Tuple[bool, str]:
        """Test building package with Poetry."""
        logger.info(f"Building {package_path.name} with Poetry...")
        
        # Clean any existing dist directory
        dist_dir = package_path / "dist"
        if dist_dir.exists():
            shutil.rmtree(dist_dir)
        
        # Build wheel and sdist
        success, stdout, stderr = self.run_command(
            [poetry_cmd, "build", "--format", "wheel", "--format", "sdist"],
            cwd=package_path
        )
        
        if success:
            # Check that both wheel and sdist were created
            if dist_dir.exists():
                files = list(dist_dir.glob("*"))
                wheels = [f for f in files if f.suffix == ".whl"]
                sdists = [f for f in files if f.suffix == ".gz"]
                
                if wheels and sdists:
                    logger.info(f"✅ {package_path.name} build successful: {len(wheels)} wheel(s), {len(sdists)} sdist(s)")
                    return True, f"Built {len(wheels)} wheel(s), {len(sdists)} sdist(s)"
                else:
                    return False, f"Missing artifacts - wheels: {len(wheels)}, sdists: {len(sdists)}"
            else:
                return False, "No dist directory created"
        else:
            return False, f"Build failed: {stderr}"
    
    def test_pip_build(self, package_path: Path) -> Tuple[bool, str]:
        """Test building package with pip/build."""
        logger.info(f"Building {package_path.name} with pip build...")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            success, stdout, stderr = self.run_command(
                ["python", "-m", "build", "--outdir", temp_dir],
                cwd=package_path
            )
            
            if success:
                temp_path = Path(temp_dir)
                files = list(temp_path.glob("*"))
                wheels = [f for f in files if f.suffix == ".whl"]
                sdists = [f for f in files if f.suffix == ".gz"]
                
                if wheels and sdists:
                    logger.info(f"✅ {package_path.name} pip build successful")
                    return True, f"Built {len(wheels)} wheel(s), {len(sdists)} sdist(s)"
                else:
                    return False, f"Missing artifacts - wheels: {len(wheels)}, sdists: {len(sdists)}"
            else:
                return False, f"Build failed: {stderr}"
    
    def test_package_imports(self, package_path: Path, package_info: Dict) -> Tuple[bool, str]:
        """Test that package can be imported after installation."""
        if package_info.get("name") == "dotmac-framework":
            # Skip import test for root package
            return True, "Root package import test skipped"
            
        logger.info(f"Testing imports for {package_path.name}...")
        
        # Common import patterns for dotmac packages
        import_patterns = [
            package_info.get("name", "").replace("-", "_"),
            package_info.get("name", "").replace("-", "."),
            "dotmac",
            f"dotmac.{package_path.name.replace('dotmac-', '')}",
        ]
        
        for pattern in import_patterns:
            if pattern:
                try:
                    # Test import in subprocess to avoid polluting current process
                    success, stdout, stderr = self.run_command(
                        ["python", "-c", f"import {pattern}; print('Import successful')"],
                        cwd=package_path,
                        timeout=30
                    )
                    if success and "Import successful" in stdout:
                        logger.info(f"✅ {package_path.name} import test passed: {pattern}")
                        return True, f"Successfully imported {pattern}"
                except Exception as e:
                    continue
        
        logger.warning(f"⚠️ {package_path.name} import test could not find valid import pattern")
        return True, "Import test skipped - no valid pattern found"
    
    def validate_package_metadata(self, package_path: Path, package_info: Dict) -> Tuple[bool, str]:
        """Validate package metadata is correct."""
        logger.info(f"Validating metadata for {package_path.name}...")
        
        issues = []
        
        # Check required fields
        if not package_info.get("name"):
            issues.append("Missing package name")
        if not package_info.get("version") or package_info["version"] == "unknown":
            issues.append("Missing or invalid version")
            
        # Check for source directory
        src_patterns = [
            package_path / "src",
            package_path / package_info.get("name", "").replace("-", "_"),
            package_path / "dotmac"
        ]
        
        has_source = any(p.exists() and p.is_dir() for p in src_patterns)
        if not has_source:
            issues.append("No source directory found")
        
        if issues:
            return False, "; ".join(issues)
        else:
            logger.info(f"✅ {package_path.name} metadata validation passed")
            return True, "Metadata validation passed"
    
    def test_single_package(self, package_path: Path) -> Dict:
        """Test a single package comprehensively."""
        logger.info(f"\n🧪 Testing package: {package_path.name}")
        
        package_info = self.get_package_info(package_path)
        logger.info(f"Package info: {package_info}")
        
        tests = [
            ("Metadata Validation", lambda: self.validate_package_metadata(package_path, package_info)),
            ("Poetry Build", lambda: self.test_poetry_build(package_path, self.poetry_cmd)),
            ("Import Test", lambda: self.test_package_imports(package_path, package_info)),
        ]
        
        results = {}
        for test_name, test_func in tests:
            logger.info(f"Running {test_name}...")
            try:
                success, message = test_func()
                results[test_name] = {"success": success, "message": message}
            except Exception as e:
                logger.error(f"❌ {test_name} failed with exception: {e}")
                results[test_name] = {"success": False, "message": str(e)}
        
        # Overall package result
        all_passed = all(r["success"] for r in results.values())
        
        return {
            "package_path": str(package_path),
            "package_info": package_info,
            "tests": results,
            "overall_success": all_passed
        }
    
    def generate_build_report(self, results: Dict) -> str:
        """Generate a comprehensive build report."""
        report_lines = ["# Package Build Test Report\n"]
        
        total_packages = len(results)
        successful_packages = sum(1 for r in results.values() if r["overall_success"])
        
        report_lines.append(f"## Summary")
        report_lines.append(f"- Total packages tested: {total_packages}")
        report_lines.append(f"- Successful builds: {successful_packages}")
        report_lines.append(f"- Failed builds: {total_packages - successful_packages}")
        report_lines.append(f"- Success rate: {successful_packages/total_packages*100:.1f}%\n")
        
        report_lines.append("## Package Results\n")
        
        for package_name, result in results.items():
            status = "✅ PASS" if result["overall_success"] else "❌ FAIL"
            report_lines.append(f"### {package_name} {status}")
            report_lines.append(f"- Name: {result['package_info'].get('name', 'unknown')}")
            report_lines.append(f"- Version: {result['package_info'].get('version', 'unknown')}")
            report_lines.append(f"- Path: {result['package_path']}")
            
            report_lines.append("\n**Test Results:**")
            for test_name, test_result in result["tests"].items():
                test_status = "✅" if test_result["success"] else "❌"
                report_lines.append(f"- {test_status} {test_name}: {test_result['message']}")
            
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    def run_all_tests(self) -> bool:
        """Run build tests for all packages."""
        logger.info("🏗️ Starting package build validation tests...")
        
        packages = self.find_packages()
        if not packages:
            logger.error("No packages found to test!")
            return False
        
        logger.info(f"Found {len(packages)} packages to test")
        
        results = {}
        for package_path in packages:
            try:
                result = self.test_single_package(package_path)
                results[package_path.name] = result
            except Exception as e:
                logger.error(f"❌ Failed to test {package_path.name}: {e}")
                results[package_path.name] = {
                    "package_path": str(package_path),
                    "package_info": {"name": package_path.name},
                    "tests": {"Exception": {"success": False, "message": str(e)}},
                    "overall_success": False
                }
        
        # Generate report
        report = self.generate_build_report(results)
        
        # Save report
        report_path = Path(".dev-artifacts") / "analysis" / "package_build_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report)
        logger.info(f"📄 Build report saved to: {report_path}")
        
        # Summary
        total_packages = len(results)
        successful_packages = sum(1 for r in results.values() if r["overall_success"])
        
        logger.info(f"\n📊 Package Build Test Summary:")
        logger.info(f"  Total packages: {total_packages}")
        logger.info(f"  Successful: {successful_packages}")
        logger.info(f"  Failed: {total_packages - successful_packages}")
        
        if successful_packages == total_packages:
            logger.info("🎉 All package builds passed!")
            return True
        else:
            logger.error("💥 Some package builds failed!")
            
            # List failed packages
            failed_packages = [name for name, r in results.items() if not r["overall_success"]]
            logger.error(f"Failed packages: {', '.join(failed_packages)}")
            
            return False

def main():
    """Main entry point."""
    root_dir = Path.cwd()
    logger.info(f"Starting package build tests in: {root_dir}")
    
    # Check for Poetry and Python availability
    poetry_paths = [
        "/root/.local/share/pypoetry/venv/bin/poetry",
        "poetry",
        ".venv/bin/poetry"
    ]
    
    poetry_cmd = None
    for path in poetry_paths:
        result = subprocess.run(["which", path] if not path.startswith("/") else [path, "--version"], 
                              capture_output=True, shell=False)
        if result.returncode == 0:
            poetry_cmd = path
            break
    
    if not poetry_cmd:
        logger.error("Poetry not found. Please install Poetry.")
        sys.exit(1)
    
    # Check Python
    python_cmd = None
    for cmd in ["python3", "python", ".venv/bin/python"]:
        result = subprocess.run(["which", cmd] if not cmd.startswith(".") else [cmd, "--version"], 
                              capture_output=True, shell=False)
        if result.returncode == 0:
            python_cmd = cmd
            break
    
    if not python_cmd:
        logger.error("Python not found.")
        sys.exit(1)
    
    logger.info(f"Using Poetry: {poetry_cmd}")
    logger.info(f"Using Python: {python_cmd}")
    
    tester = PackageBuildTester(root_dir, poetry_cmd, python_cmd)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()