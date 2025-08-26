#!/usr/bin/env python3
"""
DotMac Development Workflow Automation

This script provides automated development workflow management including
code quality checks, testing, and development environment management.
"""

import argparse
import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class WorkflowConfig:
    """Development workflow configuration."""
    check_formatting: bool = True
    check_linting: bool = True
    check_types: bool = True
    check_security: bool = True
    run_tests: bool = True
    test_coverage: bool = True
    auto_fix: bool = False
    services: List[str] = None


class DevelopmentWorkflow:
    """Automated development workflow manager."""

    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.services = [
            "dotmac_platform", "dotmac_api_gateway", "dotmac_identity",
            "dotmac_services", "dotmac_networking", "dotmac_billing",
            "dotmac_analytics", "dotmac_core_events", "dotmac_core_ops",
            "dotmac_devtools"
        ]

    def run_workflow(self, config: WorkflowConfig) -> bool:
        """Execute complete development workflow."""
        logger.info("🚀 Starting development workflow")

        workflow_steps = [
            ("Code formatting", lambda: self._check_formatting(config) if config.check_formatting else True),
            ("Code linting", lambda: self._check_linting(config) if config.check_linting else True),
            ("Type checking", lambda: self._check_types(config) if config.check_types else True),
            ("Security scanning", lambda: self._check_security(config) if config.check_security else True),
            ("Unit tests", lambda: self._run_tests(config) if config.run_tests else True),
            ("Test coverage", lambda: self._check_coverage(config) if config.test_coverage else True),
        ]

        failed_steps = []
        for step_name, step_func in workflow_steps:
            logger.info(f"📋 Running: {step_name}")
            try:
                if not step_func():
                    failed_steps.append(step_name)
                    logger.error(f"❌ Failed: {step_name}")
                else:
                    logger.info(f"✅ Passed: {step_name}")
            except Exception as e:
                failed_steps.append(step_name)
                logger.error(f"❌ Error in {step_name}: {e}")

        if failed_steps:
            logger.error(f"Workflow failed on: {', '.join(failed_steps)}")
            return False

        logger.info("🎉 Development workflow completed successfully")
        return True

    def _check_formatting(self, config: WorkflowConfig) -> bool:
        """Check code formatting with Black."""
        logger.info("🎨 Checking code formatting")

        try:
            services_to_check = config.services or self.services

            for service in services_to_check:
                service_path = self.root_path / service
                if not service_path.exists():
                    continue

                # Check formatting
                check_cmd = ["black", "--check", "--line-length", "88", str(service_path)]
                result = subprocess.run(check_cmd, check=False, capture_output=True, text=True)

                if result.returncode != 0:
                    if config.auto_fix:
                        logger.info(f"Auto-fixing formatting for {service}")
                        fix_cmd = ["black", "--line-length", "88", str(service_path)]
                        fix_result = subprocess.run(fix_cmd, check=False, capture_output=True, text=True)
                        if fix_result.returncode != 0:
                            logger.error(f"Failed to auto-fix formatting for {service}")
                            return False
                    else:
                        logger.error(f"Formatting issues found in {service}")
                        logger.error(result.stdout)
                        return False

                logger.info(f"✅ Formatting OK: {service}")

            return True

        except Exception as e:
            logger.error(f"Formatting check failed: {e}")
            return False

    def _check_linting(self, config: WorkflowConfig) -> bool:
        """Check code quality with Ruff."""
        logger.info("🔍 Running code linting")

        try:
            services_to_check = config.services or self.services

            for service in services_to_check:
                service_path = self.root_path / service
                if not service_path.exists():
                    continue

                # Run ruff check
                check_cmd = ["ruff", "check", str(service_path)]
                result = subprocess.run(check_cmd, check=False, capture_output=True, text=True)

                if result.returncode != 0:
                    if config.auto_fix:
                        logger.info(f"Auto-fixing linting issues for {service}")
                        fix_cmd = ["ruff", "check", "--fix", str(service_path)]
                        fix_result = subprocess.run(fix_cmd, check=False, capture_output=True, text=True)
                        if fix_result.returncode != 0:
                            logger.error(f"Failed to auto-fix linting issues for {service}")
                            logger.error(fix_result.stdout)
                            return False
                    else:
                        logger.error(f"Linting issues found in {service}")
                        logger.error(result.stdout)
                        return False

                logger.info(f"✅ Linting OK: {service}")

            return True

        except Exception as e:
            logger.error(f"Linting check failed: {e}")
            return False

    def _check_types(self, config: WorkflowConfig) -> bool:
        """Check type annotations with mypy."""
        logger.info("🔤 Checking type annotations")

        try:
            services_to_check = config.services or self.services

            for service in services_to_check:
                service_path = self.root_path / service
                if not service_path.exists():
                    continue

                # Run mypy
                check_cmd = ["mypy", str(service_path), "--ignore-missing-imports"]
                result = subprocess.run(check_cmd, check=False, capture_output=True, text=True)

                if result.returncode != 0:
                    logger.error(f"Type checking issues found in {service}")
                    logger.error(result.stdout)
                    return False

                logger.info(f"✅ Type checking OK: {service}")

            return True

        except Exception as e:
            logger.error(f"Type checking failed: {e}")
            return False

    def _check_security(self, config: WorkflowConfig) -> bool:
        """Run security scanning with Bandit."""
        logger.info("🔒 Running security scan")

        try:
            services_to_check = config.services or self.services

            for service in services_to_check:
                service_path = self.root_path / service
                if not service_path.exists():
                    continue

                # Run bandit
                check_cmd = ["bandit", "-r", str(service_path), "-f", "json"]
                result = subprocess.run(check_cmd, check=False, capture_output=True, text=True)

                if result.returncode != 0:
                    try:
                        scan_results = json.loads(result.stdout)
                        if scan_results.get("results"):
                            logger.error(f"Security issues found in {service}")
                            for issue in scan_results["results"]:
                                logger.error(f"  {issue['test_id']}: {issue['issue_text']}")
                            return False
                    except json.JSONDecodeError:
                        logger.error(f"Security scan failed for {service}")
                        return False

                logger.info(f"✅ Security scan OK: {service}")

            return True

        except Exception as e:
            logger.error(f"Security scan failed: {e}")
            return False

    def _run_tests(self, config: WorkflowConfig) -> bool:
        """Run unit tests with pytest."""
        logger.info("🧪 Running unit tests")

        try:
            services_to_test = config.services or self.services

            for service in services_to_test:
                service_path = self.root_path / service
                test_path = service_path / "tests"

                if not test_path.exists():
                    logger.warning(f"No tests found for {service}")
                    continue

                # Run pytest
                test_cmd = ["python", "-m", "pytest", str(test_path), "-v"]
                result = subprocess.run(test_cmd, check=False, capture_output=True, text=True, cwd=service_path)

                if result.returncode != 0:
                    logger.error(f"Tests failed for {service}")
                    logger.error(result.stdout)
                    return False

                logger.info(f"✅ Tests passed: {service}")

            return True

        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            return False

    def _check_coverage(self, config: WorkflowConfig) -> bool:
        """Check test coverage."""
        logger.info("📊 Checking test coverage")

        try:
            services_to_check = config.services or self.services

            for service in services_to_check:
                service_path = self.root_path / service
                test_path = service_path / "tests"

                if not test_path.exists():
                    continue

                # Run coverage
                coverage_cmd = [
                    "python", "-m", "pytest", str(test_path),
                    "--cov=" + str(service_path),
                    "--cov-report=term-missing",
                    "--cov-fail-under=80"
                ]

                result = subprocess.run(coverage_cmd, check=False, capture_output=True, text=True, cwd=service_path)

                if result.returncode != 0:
                    logger.error(f"Coverage below threshold for {service}")
                    logger.error(result.stdout)
                    return False

                logger.info(f"✅ Coverage OK: {service}")

            return True

        except Exception as e:
            logger.error(f"Coverage check failed: {e}")
            return False

    def setup_development_environment(self) -> bool:
        """Set up development environment."""
        logger.info("🛠️ Setting up development environment")

        try:
            # Install development dependencies
            if not self._install_dev_dependencies():
                return False

            # Set up pre-commit hooks
            if not self._setup_pre_commit_hooks():
                return False

            # Create development database
            if not self._setup_development_database():
                return False

            # Start development services
            if not self._start_development_services():
                return False

            logger.info("✅ Development environment setup complete")
            return True

        except Exception as e:
            logger.error(f"Development environment setup failed: {e}")
            return False

    def _install_dev_dependencies(self) -> bool:
        """Install development dependencies."""
        logger.info("📦 Installing development dependencies")

        try:
            # Install Python dependencies
            for service in self.services:
                service_path = self.root_path / service
                requirements_dev = service_path / "requirements-dev.txt"

                if requirements_dev.exists():
                    install_cmd = ["pip", "install", "-r", str(requirements_dev)]
                    result = subprocess.run(install_cmd, check=False, cwd=service_path)
                    if result.returncode != 0:
                        logger.error(f"Failed to install dev dependencies for {service}")
                        return False

            # Install global tools
            global_tools = [
                "black", "ruff", "mypy", "bandit", "pytest", "pytest-cov", "pre-commit"
            ]

            for tool in global_tools:
                install_cmd = ["pip", "install", tool]
                result = subprocess.run(install_cmd, check=False)
                if result.returncode != 0:
                    logger.warning(f"Failed to install {tool}")

            return True

        except Exception as e:
            logger.error(f"Failed to install dev dependencies: {e}")
            return False

    def _setup_pre_commit_hooks(self) -> bool:
        """Set up pre-commit hooks."""
        logger.info("🎣 Setting up pre-commit hooks")

        try:
            # Create pre-commit config
            pre_commit_config = self.root_path / ".pre-commit-config.yaml"

            if not pre_commit_config.exists():
                config_content = """
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        args: [--line-length=88]

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.0.270
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        args: [--ignore-missing-imports]

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: [-r, ., -f, json]
"""
                with open(pre_commit_config, "w") as f:
                    f.write(config_content.strip()

            # Install pre-commit hooks
            install_cmd = ["pre-commit", "install"]
            result = subprocess.run(install_cmd, check=False, cwd=self.root_path)

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to setup pre-commit hooks: {e}")
            return False

    def _setup_development_database(self) -> bool:
        """Set up development database."""
        logger.info("🗃️ Setting up development database")

        try:
            # Start development database
            db_cmd = [
                "docker-compose", "-f", "docker-compose.development.yml",
                "up", "-d", "postgres"
            ]

            result = subprocess.run(db_cmd, check=False, cwd=self.root_path)
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to setup development database: {e}")
            return False

    def _start_development_services(self) -> bool:
        """Start development services."""
        logger.info("🏃 Starting development services")

        try:
            # Start all development services
            start_cmd = [
                "docker-compose", "-f", "docker-compose.development.yml",
                "up", "-d"
            ]

            result = subprocess.run(start_cmd, check=False, cwd=self.root_path)
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to start development services: {e}")
            return False

    def generate_project_report(self) -> Dict:
        """Generate project health report."""
        logger.info("📋 Generating project report")

        report = {
            "timestamp": str(datetime.now(),
            "services": {},
            "overall_health": "healthy"
        }

        try:
            for service in self.services:
                service_path = self.root_path / service
                if not service_path.exists():
                    continue

                service_report = {
                    "exists": True,
                    "has_tests": (service_path / "tests").exists(),
                    "has_requirements": (service_path / "requirements.txt").exists(),
                    "has_dockerfile": (service_path / "Dockerfile").exists(),
                    "line_count": self._count_lines(service_path),
                    "test_count": self._count_tests(service_path)
                }

                report["services"][service] = service_report

            return report

        except Exception as e:
            logger.error(f"Failed to generate project report: {e}")
            return report

    def _count_lines(self, path: Path) -> int:
        """Count lines of code in a service."""
        try:
            result = subprocess.run(["find", str(path), "-name", "*.py", "-exec", "wc", "-l", "{}", "+"],
                                  check=False, capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if lines and "total" in lines[-1]:
                    return int(lines[-1].split()[0])
            return 0
        except Exception:
            return 0

    def _count_tests(self, path: Path) -> int:
        """Count number of tests in a service."""
        try:
            test_path = path / "tests"
            if not test_path.exists():
                return 0

            result = subprocess.run(["find", str(test_path), "-name", "test_*.py"],
                                  check=False, capture_output=True, text=True)
            if result.returncode == 0:
                return len([f for f in result.stdout.strip().split("\n") if f])
            return 0
        except Exception:
            return 0


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="DotMac Development Workflow Automation")

    parser.add_argument("command", choices=["workflow", "setup", "report"],
                       help="Command to execute")
    parser.add_argument("--services", nargs="+", help="Specific services to process")
    parser.add_argument("--auto-fix", action="store_true", help="Automatically fix issues where possible")
    parser.add_argument("--skip-formatting", action="store_true", help="Skip formatting check")
    parser.add_argument("--skip-linting", action="store_true", help="Skip linting check")
    parser.add_argument("--skip-types", action="store_true", help="Skip type checking")
    parser.add_argument("--skip-security", action="store_true", help="Skip security scan")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests")
    parser.add_argument("--skip-coverage", action="store_true", help="Skip coverage check")
    parser.add_argument("--root", default=".", help="Root directory of DotMac framework")

    args = parser.parse_args()

    workflow = DevelopmentWorkflow(args.root)

    if args.command == "workflow":
        config = WorkflowConfig(
            services=args.services,
            auto_fix=args.auto_fix,
            check_formatting=not args.skip_formatting,
            check_linting=not args.skip_linting,
            check_types=not args.skip_types,
            check_security=not args.skip_security,
            run_tests=not args.skip_tests,
            test_coverage=not args.skip_coverage
        )

        success = workflow.run_workflow(config)
        return 0 if success else 1

    if args.command == "setup":
        success = workflow.setup_development_environment()
        return 0 if success else 1

    if args.command == "report":
        report = workflow.generate_project_report()
        print(json.dumps(report, indent=2)
        return 0

    return 1


if __name__ == "__main__":
    from datetime import datetime
    sys.exit(main()
