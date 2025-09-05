#!/usr/bin/env python3
"""
Production Readiness Validation Script for DotMac Framework.

This script validates that all production requirements are met:
- Environment variables properly configured
- Database connectivity and RLS setup
- Redis connectivity
- OpenBao/secrets integration
- Package version pinning
- Monitoring and alerting configuration

Usage:
    python scripts/production_readiness_check.py

Exit codes:
    0 - All checks passed
    1 - Critical failures found
    2 - Warnings found (non-critical)
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import aiohttp
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class ProductionReadinessChecker:
    """Production readiness validation for DotMac Framework."""

    def __init__(self):
        self.critical_failures = []
        self.warnings = []
        self.successes = []

    def add_success(self, check: str, message: str = ""):
        """Add a successful check."""
        self.successes.append((check, message))
        logger.info(f"✅ {check}: {message}")

    def add_warning(self, check: str, message: str):
        """Add a warning."""
        self.warnings.append((check, message))
        logger.warning(f"⚠️  {check}: {message}")

    def add_critical(self, check: str, message: str):
        """Add a critical failure."""
        self.critical_failures.append((check, message))
        logger.error(f"❌ {check}: {message}")

    async def check_environment_variables(self) -> bool:
        """Check all required production environment variables."""
        logger.info("Checking production environment variables...")

        # Required variables for production
        required_vars = [
            ("ENVIRONMENT", "production"),
            ("STRICT_PROD_BASELINE", "true"),
            ("DATABASE_URL", None),
            ("REDIS_URL", None),
            ("OPENBAO_URL", None),
            ("OPENBAO_TOKEN", None),
            ("APPLY_RLS_AFTER_MIGRATION", "true"),
            ("SECRET_KEY", None),
            ("JWT_SECRET", None),
            ("ENCRYPTION_KEY", None),
        ]

        all_good = True

        for var_name, expected_value in required_vars:
            value = os.getenv(var_name)

            if not value:
                self.add_critical("Environment Variables", f"{var_name} is not set")
                all_good = False
            elif expected_value and value != expected_value:
                self.add_critical("Environment Variables", f"{var_name} should be '{expected_value}', got '{value}'")
                all_good = False
            else:
                # Check for security issues
                if var_name == "DATABASE_URL" and value.startswith("sqlite"):
                    self.add_critical("Database Configuration", "SQLite not allowed in production")
                    all_good = False
                elif var_name in ["SECRET_KEY", "JWT_SECRET", "ENCRYPTION_KEY"] and len(value) < 32:
                    self.add_warning("Security Configuration", f"{var_name} should be at least 32 characters")
                else:
                    self.add_success("Environment Variables", f"{var_name} properly configured")

        # Check CORS configuration
        cors_origins = os.getenv("CORS_ORIGINS", "")
        if "localhost" in cors_origins or "127.0.0.1" in cors_origins:
            self.add_warning("CORS Configuration", "Development URLs found in CORS_ORIGINS")

        return all_good

    async def check_database_connectivity(self) -> bool:
        """Check database connectivity and RLS setup."""
        logger.info("Checking database connectivity...")

        database_url = os.getenv("DATABASE_URL") or os.getenv("ASYNC_DATABASE_URL")
        if not database_url:
            self.add_critical("Database", "DATABASE_URL not configured")
            return False

        # Convert to async URL if needed
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        try:
            engine = create_async_engine(database_url, echo=False)

            async with engine.begin() as conn:
                # Test basic connectivity
                result = await conn.execute(text("SELECT 1"))
                self.add_success("Database Connectivity", "Database connection successful")

                # Check for RLS helper functions
                try:
                    await conn.execute(text("SELECT current_tenant_id()"))
                    self.add_success("RLS Setup", "RLS helper functions available")
                except Exception:
                    self.add_warning("RLS Setup", "RLS helper functions not found - may need setup")

                # Check for tenant-aware tables
                result = await conn.execute(
                    text(
                        """
                    SELECT table_name
                    FROM information_schema.columns
                    WHERE column_name = 'tenant_id'
                """
                    )
                )
                tenant_tables = result.fetchall()
                if tenant_tables:
                    self.add_success("Tenant Isolation", f"Found {len(tenant_tables)} tenant-aware tables")
                else:
                    self.add_warning("Tenant Isolation", "No tenant-aware tables found")

            await engine.dispose()
            return True

        except Exception as e:
            self.add_critical("Database Connectivity", f"Failed to connect: {e}")
            return False

    async def check_redis_connectivity(self) -> bool:
        """Check Redis connectivity."""
        logger.info("Checking Redis connectivity...")

        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            self.add_critical("Redis", "REDIS_URL not configured")
            return False

        try:
            # Simple Redis connection check using aioredis if available
            try:
                import redis.asyncio as redis

                redis_client = redis.from_url(redis_url)
                await redis_client.ping()
                await redis_client.close()

                self.add_success("Redis Connectivity", "Redis connection successful")
                return True

            except ImportError:
                self.add_warning("Redis", "redis package not available for testing")
                return True

        except Exception as e:
            self.add_critical("Redis Connectivity", f"Failed to connect: {e}")
            return False

    async def check_secrets_provider(self) -> bool:
        """Check OpenBao/secrets provider connectivity."""
        logger.info("Checking secrets provider...")

        openbao_url = os.getenv("OPENBAO_URL")
        openbao_token = os.getenv("OPENBAO_TOKEN")

        if not openbao_url:
            self.add_critical("Secrets Provider", "OPENBAO_URL not configured")
            return False

        if not openbao_token:
            self.add_critical("Secrets Provider", "OPENBAO_TOKEN not configured")
            return False

        try:
            headers = {"X-Vault-Token": openbao_token}

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{openbao_url}/v1/sys/health", headers=headers) as response:
                    if response.status == 200:
                        self.add_success("Secrets Provider", "OpenBao connection successful")
                        return True
                    else:
                        self.add_warning("Secrets Provider", f"OpenBao returned status {response.status}")
                        return True  # Non-critical for startup

        except Exception as e:
            self.add_warning("Secrets Provider", f"Failed to connect to OpenBao: {e}")
            return True  # Non-critical for startup

    async def check_package_constraints(self) -> bool:
        """Check that package versions are pinned via constraints."""
        logger.info("Checking package version constraints...")

        constraints_file = Path(__file__).parent.parent / "constraints" / "constraints.txt"

        if not constraints_file.exists():
            self.add_warning("Package Constraints", "constraints.txt not found")
            return True

        try:
            with open(constraints_file) as f:
                content = f.read()

            # Check for pinned dotmac packages
            dotmac_packages = [
                "dotmac-application",
                "dotmac-observability",
                "dotmac-tenant",
                "dotmac-auth",
                "dotmac-tasks",
                "dotmac-database",
                "dotmac-events",
                "dotmac-secrets",
                "dotmac-websockets",
                "dotmac-plugins",
            ]

            pinned_count = 0
            for package in dotmac_packages:
                if f"{package}==" in content:
                    pinned_count += 1

            if pinned_count == len(dotmac_packages):
                self.add_success("Package Constraints", f"All {pinned_count} dotmac packages properly pinned")
            else:
                self.add_warning("Package Constraints", f"Only {pinned_count}/{len(dotmac_packages)} packages pinned")

            return True

        except Exception as e:
            self.add_warning("Package Constraints", f"Failed to read constraints: {e}")
            return True

    async def check_monitoring_configuration(self) -> bool:
        """Check monitoring and alerting configuration."""
        logger.info("Checking monitoring configuration...")

        # Check Prometheus configuration
        prometheus_config = Path(__file__).parent.parent / "monitoring" / "prometheus" / "prometheus.yml"
        alerts_config = Path(__file__).parent.parent / "monitoring" / "prometheus" / "alerts.yml"

        if not prometheus_config.exists():
            self.add_critical("Monitoring", "Prometheus configuration not found")
            return False

        if not alerts_config.exists():
            self.add_critical("Monitoring", "Prometheus alerts configuration not found")
            return False

        try:
            with open(prometheus_config) as f:
                prometheus_content = f.read()

            with open(alerts_config) as f:
                alerts_content = f.read()

            # Check for required scrape jobs
            required_jobs = ["management-platform", "postgresql", "redis"]
            missing_jobs = []

            for job in required_jobs:
                if f"job_name: '{job}'" not in prometheus_content and f'job_name: "{job}"' not in prometheus_content:
                    missing_jobs.append(job)

            if missing_jobs:
                self.add_warning("Monitoring", f"Missing scrape jobs: {', '.join(missing_jobs)}")
            else:
                self.add_success("Monitoring", "Required scrape jobs configured")

            # Check for critical alerts
            critical_alerts = ["HighErrorRate", "ServiceDown", "ManagementAPIDown"]
            missing_alerts = []

            for alert in critical_alerts:
                if alert not in alerts_content:
                    missing_alerts.append(alert)

            if missing_alerts:
                self.add_warning("Alerting", f"Missing critical alerts: {', '.join(missing_alerts)}")
            else:
                self.add_success("Alerting", "Critical alerts configured")

            return True

        except Exception as e:
            self.add_warning("Monitoring", f"Failed to read monitoring config: {e}")
            return True

    async def check_application_startup(self) -> bool:
        """Check that applications would pass strict baseline at startup."""
        logger.info("Checking application startup requirements...")

        # Simulate the strict baseline check from main.py
        environment = os.getenv("ENVIRONMENT", "development")
        strict_baseline = os.getenv("STRICT_PROD_BASELINE", "false").lower() == "true"

        if environment != "production":
            self.add_warning("Environment", "ENVIRONMENT not set to 'production'")
            return True

        if not strict_baseline:
            self.add_warning("Baseline", "STRICT_PROD_BASELINE not enabled")
            return True

        # Check the same requirements as the application startup
        required_for_baseline = ["OPENBAO_URL", "DATABASE_URL", "REDIS_URL", "APPLY_RLS_AFTER_MIGRATION"]

        missing = []
        for var in required_for_baseline:
            value = os.getenv(var)
            if not value:
                missing.append(var)
            elif var == "DATABASE_URL" and value.startswith("sqlite"):
                missing.append(f"{var} (non-sqlite)")

        if missing:
            self.add_critical("Strict Baseline", f"Missing required variables: {', '.join(missing)}")
            return False
        else:
            self.add_success("Strict Baseline", "All baseline requirements met")
            return True

    def generate_report(self) -> dict[str, Any]:
        """Generate comprehensive readiness report."""
        return {
            "overall_status": "READY" if not self.critical_failures else "NOT_READY",
            "critical_failures": len(self.critical_failures),
            "warnings": len(self.warnings),
            "successes": len(self.successes),
            "details": {
                "critical": [{"check": check, "message": msg} for check, msg in self.critical_failures],
                "warnings": [{"check": check, "message": msg} for check, msg in self.warnings],
                "successes": [{"check": check, "message": msg} for check, msg in self.successes],
            },
        }

    async def run_all_checks(self) -> bool:
        """Run all production readiness checks."""
        logger.info("Starting production readiness validation...")

        checks = [
            self.check_environment_variables(),
            self.check_database_connectivity(),
            self.check_redis_connectivity(),
            self.check_secrets_provider(),
            self.check_package_constraints(),
            self.check_monitoring_configuration(),
            self.check_application_startup(),
        ]

        results = await asyncio.gather(*checks, return_exceptions=True)

        # Handle any exceptions that occurred during checks
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.add_critical("Check Execution", f"Check {i} failed with exception: {result}")

        return len(self.critical_failures) == 0


async def main():
    """Main entry point for production readiness check."""
    checker = ProductionReadinessChecker()

    try:
        success = await checker.run_all_checks()

        # Generate and display report
        report = checker.generate_report()

        print("\n" + "=" * 60)
        print("PRODUCTION READINESS REPORT")
        print("=" * 60)
        print(f"Overall Status: {report['overall_status']}")
        print(f"Successes: {report['successes']}")
        print(f"Warnings: {report['warnings']}")
        print(f"Critical Failures: {report['critical_failures']}")

        if report["details"]["critical"]:
            print("\nCRITICAL FAILURES (must fix):")
            for item in report["details"]["critical"]:
                print(f"  ❌ {item['check']}: {item['message']}")

        if report["details"]["warnings"]:
            print("\nWARNINGS (recommended to fix):")
            for item in report["details"]["warnings"]:
                print(f"  ⚠️  {item['check']}: {item['message']}")

        print("\n" + "=" * 60)

        # Write report to file
        report_file = Path(__file__).parent.parent / "production-readiness-report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"Full report saved to: {report_file}")

        if success:
            print("✅ Production readiness validation PASSED")
            return 0
        else:
            print("❌ Production readiness validation FAILED")
            return 1

    except Exception as e:
        logger.error(f"Readiness check failed with exception: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
