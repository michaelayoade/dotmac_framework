#!/usr/bin/env python3
"""
Development Artifacts Validation and Cleanup Script

This script validates that all development work is complete and cleans up 
temporary artifacts following the project's development guidelines.
"""

import os
import sys
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DevelopmentArtifactsManager:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.dev_artifacts_dir = root_dir / ".dev-artifacts"
        self.production_dirs = [
            "src", "packages", "tests", "frontend", 
            ".github", "scripts", "docker", "docs"
        ]
        
    def scan_for_dev_artifacts_outside_folder(self) -> List[Path]:
        """Scan for development artifacts outside the .dev-artifacts folder."""
        logger.info("🔍 Scanning for development artifacts in production directories...")
        
        artifacts = []
        
        # Patterns that indicate development artifacts
        dev_patterns = [
            "**/temp_*.py",
            "**/debug_*.py", 
            "**/test_temp_*.py",
            "**/fix_*.py",
            "**/validate_*.py",
            "**/*_temp.*",
            "**/*_debug.*",
            "**/*_fix.*",
            "**/scratch_*",
            "**/draft_*",
        ]
        
        for prod_dir in self.production_dirs:
            prod_path = self.root_dir / prod_dir
            if prod_path.exists():
                for pattern in dev_patterns:
                    artifacts.extend(prod_path.glob(pattern))
        
        # Also check root directory
        for pattern in dev_patterns:
            artifacts.extend(self.root_dir.glob(pattern))
        
        # Filter out known legitimate files
        legitimate_patterns = [
            "test_*.py",  # Legitimate test files
            "**/tests/**",  # Files in test directories
        ]
        
        filtered_artifacts = []
        for artifact in artifacts:
            is_legitimate = False
            for legit_pattern in legitimate_patterns:
                if artifact.match(legit_pattern) or "/tests/" in str(artifact):
                    is_legitimate = True
                    break
            
            if not is_legitimate:
                filtered_artifacts.append(artifact)
        
        return filtered_artifacts
    
    def validate_no_dev_dependencies_in_production(self) -> List[str]:
        """Check for development-only imports in production code."""
        logger.info("📦 Validating no development dependencies in production code...")
        
        issues = []
        
        # Development-only imports to check for
        dev_imports = [
            "from .dev_artifacts",
            "import dev_artifacts", 
            "from dev_artifacts",
            "from ..dev_artifacts",
            "from .temp_",
            "from .debug_",
            "from .fix_",
        ]
        
        # Scan production Python files
        for prod_dir in ["src", "packages"]:
            prod_path = self.root_dir / prod_dir
            if prod_path.exists():
                for py_file in prod_path.rglob("*.py"):
                    try:
                        content = py_file.read_text(encoding='utf-8')
                        for dev_import in dev_imports:
                            if dev_import in content:
                                issues.append(f"{py_file}: contains '{dev_import}'")
                    except Exception as e:
                        logger.warning(f"Could not read {py_file}: {e}")
        
        return issues
    
    def validate_artifacts_folder_structure(self) -> Dict[str, List[str]]:
        """Validate .dev-artifacts folder has proper structure."""
        logger.info("📁 Validating .dev-artifacts folder structure...")
        
        if not self.dev_artifacts_dir.exists():
            return {"errors": ["No .dev-artifacts folder found"]}
        
        expected_dirs = ["scripts", "fixes", "validation", "analysis", "temp"]
        results = {"created": [], "existing": [], "files": []}
        
        for expected_dir in expected_dirs:
            dir_path = self.dev_artifacts_dir / expected_dir
            if dir_path.exists():
                results["existing"].append(expected_dir)
            else:
                dir_path.mkdir(parents=True, exist_ok=True)
                results["created"].append(expected_dir)
        
        # List all files in dev artifacts
        for file_path in self.dev_artifacts_dir.rglob("*"):
            if file_path.is_file():
                results["files"].append(str(file_path.relative_to(self.dev_artifacts_dir)))
        
        return results
    
    def validate_implementation_completeness(self) -> Dict[str, any]:
        """Validate that implementation appears complete."""
        logger.info("✅ Validating implementation completeness...")
        
        results = {
            "scripts_created": [],
            "ci_pipeline_enhanced": False,
            "test_coverage": {},
            "production_ready": True,
            "recommendations": []
        }
        
        # Check for created testing scripts
        expected_scripts = [
            "test_database_migrations.py",
            "test_container_smoke.py", 
            "test_package_builds.py",
            "test_cross_service_integration.py",
            "test_signoz_observability.py"
        ]
        
        scripts_dir = self.dev_artifacts_dir / "scripts"
        for script in expected_scripts:
            script_path = scripts_dir / script
            if script_path.exists():
                results["scripts_created"].append(script)
        
        # Check for enhanced CI pipeline
        enhanced_ci_path = self.dev_artifacts_dir / "enhanced-ci-pipeline.yml"
        if enhanced_ci_path.exists():
            results["ci_pipeline_enhanced"] = True
        
        # Analyze test coverage by examining existing tests
        tests_dir = self.root_dir / "tests"
        if tests_dir.exists():
            unit_tests = len(list(tests_dir.rglob("test_*.py")))
            results["test_coverage"]["unit_tests"] = unit_tests
            results["test_coverage"]["has_integration"] = (tests_dir / "integration").exists()
            results["test_coverage"]["has_e2e"] = (tests_dir / "e2e").exists()
        
        # Generate recommendations
        if len(results["scripts_created"]) < len(expected_scripts):
            missing = set(expected_scripts) - set(results["scripts_created"])
            results["recommendations"].append(f"Missing testing scripts: {', '.join(missing)}")
        
        if not results["ci_pipeline_enhanced"]:
            results["recommendations"].append("Enhanced CI pipeline not found")
        
        return results
    
    def generate_cleanup_report(self) -> str:
        """Generate a report of what will be cleaned up."""
        logger.info("📋 Generating cleanup report...")
        
        if not self.dev_artifacts_dir.exists():
            return "No .dev-artifacts directory found - nothing to clean up."
        
        # Count files by type
        file_counts = {}
        total_size = 0
        
        for file_path in self.dev_artifacts_dir.rglob("*"):
            if file_path.is_file():
                suffix = file_path.suffix or "no_extension"
                file_counts[suffix] = file_counts.get(suffix, 0) + 1
                
                try:
                    total_size += file_path.stat().st_size
                except:
                    pass
        
        # Format report
        report_lines = [
            "# Development Artifacts Cleanup Report",
            f"## Directory: {self.dev_artifacts_dir}",
            f"## Total size: {total_size / 1024:.1f} KB",
            "",
            "## Files by type:"
        ]
        
        for suffix, count in sorted(file_counts.items()):
            report_lines.append(f"- {suffix}: {count} file(s)")
        
        # List all files
        report_lines.extend([
            "",
            "## All files to be removed:"
        ])
        
        for file_path in sorted(self.dev_artifacts_dir.rglob("*")):
            if file_path.is_file():
                rel_path = file_path.relative_to(self.dev_artifacts_dir)
                report_lines.append(f"- {rel_path}")
        
        return "\n".join(report_lines)
    
    def cleanup_dev_artifacts(self, dry_run: bool = False) -> bool:
        """Clean up development artifacts."""
        if dry_run:
            logger.info("🧪 DRY RUN: Showing what would be cleaned up...")
        else:
            logger.info("🧹 Cleaning up development artifacts...")
        
        if not self.dev_artifacts_dir.exists():
            logger.info("No .dev-artifacts directory found - nothing to clean up.")
            return True
        
        try:
            if dry_run:
                report = self.generate_cleanup_report()
                print("\n" + report)
                logger.info(f"Would remove directory: {self.dev_artifacts_dir}")
            else:
                # Actually remove the directory
                shutil.rmtree(self.dev_artifacts_dir)
                logger.info(f"✅ Successfully removed {self.dev_artifacts_dir}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            return False
    
    def run_comprehensive_validation(self) -> bool:
        """Run all validation checks."""
        logger.info("🔍 Starting comprehensive development artifacts validation...")
        
        all_checks_passed = True
        
        # Check 1: Scan for artifacts outside dev folder
        misplaced_artifacts = self.scan_for_dev_artifacts_outside_folder()
        if misplaced_artifacts:
            logger.warning(f"⚠️ Found {len(misplaced_artifacts)} misplaced development artifacts:")
            for artifact in misplaced_artifacts[:5]:  # Show first 5
                logger.warning(f"  - {artifact}")
            if len(misplaced_artifacts) > 5:
                logger.warning(f"  ... and {len(misplaced_artifacts) - 5} more")
            all_checks_passed = False
        else:
            logger.info("✅ No misplaced development artifacts found")
        
        # Check 2: Validate no dev dependencies in production
        dev_dependency_issues = self.validate_no_dev_dependencies_in_production()
        if dev_dependency_issues:
            logger.warning(f"⚠️ Found {len(dev_dependency_issues)} development dependency issues:")
            for issue in dev_dependency_issues[:3]:  # Show first 3
                logger.warning(f"  - {issue}")
            all_checks_passed = False
        else:
            logger.info("✅ No development dependencies in production code")
        
        # Check 3: Validate artifacts folder structure
        structure_results = self.validate_artifacts_folder_structure()
        if "errors" in structure_results:
            logger.warning(f"⚠️ Artifacts folder issues: {structure_results['errors']}")
            all_checks_passed = False
        else:
            if structure_results["created"]:
                logger.info(f"📁 Created missing directories: {structure_results['created']}")
            logger.info(f"✅ Artifacts folder structure valid ({len(structure_results['files'])} files)")
        
        # Check 4: Validate implementation completeness
        implementation_results = self.validate_implementation_completeness()
        logger.info("📊 Implementation Status:")
        logger.info(f"  - Testing scripts: {len(implementation_results['scripts_created'])}/5")
        logger.info(f"  - Enhanced CI: {'✅' if implementation_results['ci_pipeline_enhanced'] else '❌'}")
        logger.info(f"  - Unit tests: {implementation_results['test_coverage'].get('unit_tests', 0)}")
        
        if implementation_results["recommendations"]:
            logger.info("💡 Recommendations:")
            for rec in implementation_results["recommendations"]:
                logger.info(f"  - {rec}")
        
        # Summary
        logger.info(f"\n📋 Validation Summary:")
        logger.info(f"  - Misplaced artifacts: {len(misplaced_artifacts)}")
        logger.info(f"  - Dev dependency issues: {len(dev_dependency_issues)}")
        logger.info(f"  - Implementation completeness: {'Good' if not implementation_results['recommendations'] else 'Needs attention'}")
        
        return all_checks_passed

def main():
    """Main entry point."""
    root_dir = Path.cwd()
    manager = DevelopmentArtifactsManager(root_dir)
    
    # Parse command line arguments
    dry_run = "--dry-run" in sys.argv
    cleanup = "--cleanup" in sys.argv
    validate_only = "--validate-only" in sys.argv
    
    if not any([dry_run, cleanup, validate_only]):
        # Default behavior: validate and show cleanup report
        logger.info("🚀 Running development artifacts validation...")
        logger.info("Use --cleanup to actually remove artifacts, --dry-run to see what would be removed")
        
        validation_passed = manager.run_comprehensive_validation()
        
        # Show cleanup report
        if manager.dev_artifacts_dir.exists():
            report = manager.generate_cleanup_report()
            print(f"\n{report}")
        
        if validation_passed:
            logger.info("✅ All validation checks passed - ready for cleanup")
            sys.exit(0)
        else:
            logger.warning("⚠️ Some validation issues found - review before cleanup")
            sys.exit(1)
            
    elif validate_only:
        logger.info("🔍 Running validation checks only...")
        validation_passed = manager.run_comprehensive_validation()
        sys.exit(0 if validation_passed else 1)
        
    elif dry_run:
        logger.info("🧪 Running dry-run cleanup...")
        manager.run_comprehensive_validation()
        success = manager.cleanup_dev_artifacts(dry_run=True)
        sys.exit(0 if success else 1)
        
    elif cleanup:
        logger.info("🧹 Running actual cleanup...")
        validation_passed = manager.run_comprehensive_validation()
        
        if validation_passed:
            success = manager.cleanup_dev_artifacts(dry_run=False)
            if success:
                logger.info("🎉 Development artifacts successfully cleaned up!")
                logger.info("Production code is now ready for deployment")
            sys.exit(0 if success else 1)
        else:
            logger.error("❌ Validation failed - cleanup aborted")
            logger.error("Fix validation issues before running cleanup")
            sys.exit(1)

if __name__ == "__main__":
    main()