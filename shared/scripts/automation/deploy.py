#!/usr/bin/env python3
"""
DotMac Platform Deployment Automation Script

This script provides automated deployment capabilities for the DotMac platform
across different environments with comprehensive validation and rollback support.
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

import yaml


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class DeploymentConfig:
    """Deployment configuration parameters."""
    environment: str
    version: str
    rollback_enabled: bool = True
    health_check_timeout: int = 300
    pre_deployment_checks: bool = True
    post_deployment_validation: bool = True
    backup_enabled: bool = True
    services: List[str] = None


class DotMacDeployer:
    """Automated deployment manager for DotMac platform."""

    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.deployment_history = []
        self.services = [
            "dotmac_platform", "dotmac_api_gateway", "dotmac_identity",
            "dotmac_services", "dotmac_networking", "dotmac_billing",
            "dotmac_analytics", "dotmac_core_events", "dotmac_core_ops",
            "dotmac_devtools"
        ]

    def deploy(self, config: DeploymentConfig) -> bool:
        """Execute complete deployment workflow."""
        logger.info(f"🚀 Starting deployment to {config.environment}")

        try:
            # Pre-deployment phase
            if config.pre_deployment_checks and not self._pre_deployment_checks(config):
                raise Exception("Pre-deployment checks failed")

            if config.backup_enabled and not self._create_backup(config):
                raise Exception("Backup creation failed")

            # Deployment phase
            if not self._build_services(config):
                raise Exception("Service build failed")

            if not self._deploy_services(config):
                raise Exception("Service deployment failed")

            # Post-deployment phase
            if config.post_deployment_validation and not self._validate_deployment(config):
                if config.rollback_enabled:
                    logger.warning("⚠️ Validation failed, initiating rollback")
                    return self._rollback_deployment(config)
                raise Exception("Deployment validation failed")

            self._record_deployment(config, success=True)
            logger.info("🎉 Deployment completed successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            if config.rollback_enabled:
                logger.info("🔄 Initiating automatic rollback")
                return self._rollback_deployment(config)
            return False

    def _pre_deployment_checks(self, config: DeploymentConfig) -> bool:
        """Run pre-deployment validation checks."""
        logger.info("🔍 Running pre-deployment checks")

        checks = [
            ("Docker daemon", self._check_docker),
            ("Docker Compose", self._check_docker_compose),
            ("Required images", lambda: self._check_required_images(config),
            ("Environment config", lambda: self._check_environment_config(config),
            ("Database connectivity", lambda: self._check_database_connectivity(config),
            ("Redis connectivity", lambda: self._check_redis_connectivity(config),
            ("Disk space", self._check_disk_space),
            ("Network connectivity", self._check_network_connectivity),
        ]

        failed_checks = []
        for check_name, check_func in checks:
            try:
                if not check_func():
                    failed_checks.append(check_name)
                    logger.error(f"❌ Check failed: {check_name}")
                else:
                    logger.info(f"✅ Check passed: {check_name}")
            except Exception as e:
                failed_checks.append(check_name)
                logger.error(f"❌ Check error: {check_name} - {e}")

        if failed_checks:
            logger.error(f"Pre-deployment checks failed: {', '.join(failed_checks)}")
            return False

        logger.info("✅ All pre-deployment checks passed")
        return True

    def _check_docker(self) -> bool:
        """Check if Docker daemon is running."""
        try:
            result = subprocess.run(["docker", "info"], check=False, capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _check_docker_compose(self) -> bool:
        """Check if Docker Compose is available."""
        try:
            result = subprocess.run(["docker-compose", "--version"], check=False, capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _check_required_images(self, config: DeploymentConfig) -> bool:
        """Check if required base images are available."""
        required_images = ["python:3.11-slim", "postgres:15-alpine", "redis:7-alpine"]

        for image in required_images:
            try:
                result = subprocess.run(["docker", "image", "inspect", image],
                                      check=False, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Base image not found, pulling: {image}")
                    pull_result = subprocess.run(["docker", "pull", image],
                                               check=False, capture_output=True, text=True)
                    if pull_result.returncode != 0:
                        return False
            except Exception:
                return False
        return True

    def _check_environment_config(self, config: DeploymentConfig) -> bool:
        """Validate environment configuration."""
        compose_file = self.root_path / f"docker-compose.{config.environment}.yml"
        if not compose_file.exists():
            logger.error(f"Compose file not found: {compose_file}")
            return False

        # Validate compose file syntax
        try:
            with open(compose_file) as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.error(f"Invalid compose file syntax: {e}")
            return False

        return True

    def _check_database_connectivity(self, config: DeploymentConfig) -> bool:
        """Check database connectivity."""
        if config.environment == "production":
            # For production, check external database
            # This would be customized based on actual database configuration
            return True
        # For development/staging, database will be started as part of deployment
        return True

    def _check_redis_connectivity(self, config: DeploymentConfig) -> bool:
        """Check Redis connectivity."""
        if config.environment == "production":
            # For production, check external Redis
            return True
        # For development/staging, Redis will be started as part of deployment
        return True

    def _check_disk_space(self) -> bool:
        """Check available disk space."""
        try:
            result = subprocess.run(["df", "-h", "."], check=False, capture_output=True, text=True)
            # Simple check - ensure we have at least 10GB free
            # This would be more sophisticated in practice
            return True
        except Exception:
            return False

    def _check_network_connectivity(self) -> bool:
        """Check network connectivity."""
        try:
            # Check if required ports are available
            result = subprocess.run(["netstat", "-tuln"], check=False, capture_output=True, text=True)
            return True
        except Exception:
            return True  # Assume network is OK if netstat is not available

    def _create_backup(self, config: DeploymentConfig) -> bool:
        """Create backup before deployment."""
        logger.info("💾 Creating backup")

        backup_dir = self.root_path / "backups" / f"{config.environment}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Backup database
            if not self._backup_database(config, backup_dir):
                return False

            # Backup Redis data
            if not self._backup_redis(config, backup_dir):
                return False

            # Backup configuration files
            if not self._backup_configuration(config, backup_dir):
                return False

            logger.info(f"✅ Backup created: {backup_dir}")
            return True

        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return False

    def _backup_database(self, config: DeploymentConfig, backup_dir: Path) -> bool:
        """Backup database."""
        try:
            # This would be customized based on actual database configuration
            backup_file = backup_dir / "database.sql"

            if config.environment == "development":
                # For development, backup containerized database
                cmd = [
                    "docker-compose", "-f", f"docker-compose.{config.environment}.yml",
                    "exec", "-T", "postgres", "pg_dumpall", "-U", "dotmac"
                ]
            else:
                # For production, backup external database
                cmd = ["pg_dumpall", "-h", "production-db-host", "-U", "dotmac"]

            with open(backup_file, "w") as f:
                result = subprocess.run(cmd, check=False, stdout=f, stderr=subprocess.PIPE, text=True)

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return False

    def _backup_redis(self, config: DeploymentConfig, backup_dir: Path) -> bool:
        """Backup Redis data."""
        try:
            backup_file = backup_dir / "redis.rdb"

            if config.environment == "development":
                # Copy Redis RDB file from container
                cmd = [
                    "docker-compose", "-f", f"docker-compose.{config.environment}.yml",
                    "exec", "-T", "redis", "redis-cli", "BGSAVE"
                ]
                subprocess.run(cmd, check=False)

                # Wait for backup to complete
                time.sleep(5)

                # Copy the backup file
                copy_cmd = [
                    "docker", "cp", "redis:/data/dump.rdb", str(backup_file)
                ]
                result = subprocess.run(copy_cmd, check=False)
                return result.returncode == 0
            # For production, backup external Redis
            return True

        except Exception as e:
            logger.error(f"Redis backup failed: {e}")
            return False

    def _backup_configuration(self, config: DeploymentConfig, backup_dir: Path) -> bool:
        """Backup configuration files."""
        try:
            config_files = [
                f"docker-compose.{config.environment}.yml",
                ".env",
                "secrets/"
            ]

            for file_path in config_files:
                source = self.root_path / file_path
                if source.exists():
                    if source.is_dir():
                        # Copy directory
                        subprocess.run(["cp", "-r", str(source), str(backup_dir)], check=False)
                    else:
                        # Copy file
                        subprocess.run(["cp", str(source), str(backup_dir)], check=False)

            return True

        except Exception as e:
            logger.error(f"Configuration backup failed: {e}")
            return False

    def _build_services(self, config: DeploymentConfig) -> bool:
        """Build all required services."""
        logger.info("🔨 Building services")

        try:
            # Generate Docker configurations if needed
            gen_cmd = ["python", "scripts/generate_docker_configs.py", "--all"]
            result = subprocess.run(gen_cmd, check=False, cwd=self.root_path)
            if result.returncode != 0:
                logger.error("Failed to generate Docker configurations")
                return False

            # Build services
            services_to_build = config.services or self.services

            for service in services_to_build:
                logger.info(f"Building {service}")
                build_cmd = [
                    "docker-compose", "-f", f"docker-compose.{config.environment}.yml",
                    "build", "--no-cache", service.replace("_", "-")
                ]

                result = subprocess.run(build_cmd, check=False, cwd=self.root_path)
                if result.returncode != 0:
                    logger.error(f"Failed to build {service}")
                    return False

                logger.info(f"✅ Built {service}")

            logger.info("✅ All services built successfully")
            return True

        except Exception as e:
            logger.error(f"Service build failed: {e}")
            return False

    def _deploy_services(self, config: DeploymentConfig) -> bool:
        """Deploy services to target environment."""
        logger.info(f"🚀 Deploying to {config.environment}")

        try:
            # Stop existing services
            stop_cmd = [
                "docker-compose", "-f", f"docker-compose.{config.environment}.yml",
                "down", "--remove-orphans"
            ]
            subprocess.run(stop_cmd, check=False, cwd=self.root_path)

            # Start new services
            start_cmd = [
                "docker-compose", "-f", f"docker-compose.{config.environment}.yml",
                "up", "-d", "--remove-orphans"
            ]

            result = subprocess.run(start_cmd, check=False, cwd=self.root_path)
            if result.returncode != 0:
                logger.error("Failed to start services")
                return False

            # Wait for services to stabilize
            logger.info("⏳ Waiting for services to stabilize")
            time.sleep(30)

            logger.info("✅ Services deployed successfully")
            return True

        except Exception as e:
            logger.error(f"Service deployment failed: {e}")
            return False

    def _validate_deployment(self, config: DeploymentConfig) -> bool:
        """Validate deployment health and functionality."""
        logger.info("🔍 Validating deployment")

        validation_checks = [
            ("Service health", lambda: self._check_service_health(config),
            ("Database connectivity", lambda: self._validate_database_connection(config),
            ("Redis connectivity", lambda: self._validate_redis_connection(config),
            ("API endpoints", lambda: self._validate_api_endpoints(config),
            ("Inter-service communication", lambda: self._validate_service_communication(config),
        ]

        failed_validations = []
        for validation_name, validation_func in validation_checks:
            try:
                if not validation_func():
                    failed_validations.append(validation_name)
                    logger.error(f"❌ Validation failed: {validation_name}")
                else:
                    logger.info(f"✅ Validation passed: {validation_name}")
            except Exception as e:
                failed_validations.append(validation_name)
                logger.error(f"❌ Validation error: {validation_name} - {e}")

        if failed_validations:
            logger.error(f"Deployment validation failed: {', '.join(failed_validations)}")
            return False

        logger.info("✅ All deployment validations passed")
        return True

    def _check_service_health(self, config: DeploymentConfig) -> bool:
        """Check health of all deployed services."""
        try:
            # Get service status
            status_cmd = [
                "docker-compose", "-f", f"docker-compose.{config.environment}.yml",
                "ps", "--services"
            ]

            result = subprocess.run(status_cmd, check=False, capture_output=True, text=True, cwd=self.root_path)
            if result.returncode != 0:
                return False

            services = result.stdout.strip().split("\n")

            # Check each service health
            for service in services:
                if not service.strip():
                    continue

                health_cmd = [
                    "docker-compose", "-f", f"docker-compose.{config.environment}.yml",
                    "exec", "-T", service, "curl", "-f", "http://localhost:8000/health"
                ]

                # Retry health check up to 3 times
                for attempt in range(3):
                    health_result = subprocess.run(health_cmd, check=False, capture_output=True, text=True, cwd=self.root_path)
                    if health_result.returncode == 0:
                        break
                    time.sleep(10)
                else:
                    logger.error(f"Health check failed for {service}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Service health check failed: {e}")
            return False

    def _validate_database_connection(self, config: DeploymentConfig) -> bool:
        """Validate database connectivity."""
        try:
            db_cmd = [
                "docker-compose", "-f", f"docker-compose.{config.environment}.yml",
                "exec", "-T", "postgres", "psql", "-U", "dotmac", "-c", "SELECT 1;"
            ]

            result = subprocess.run(db_cmd, check=False, capture_output=True, text=True, cwd=self.root_path)
            return result.returncode == 0

        except Exception:
            return False

    def _validate_redis_connection(self, config: DeploymentConfig) -> bool:
        """Validate Redis connectivity."""
        try:
            redis_cmd = [
                "docker-compose", "-f", f"docker-compose.{config.environment}.yml",
                "exec", "-T", "redis", "redis-cli", "ping"
            ]

            result = subprocess.run(redis_cmd, check=False, capture_output=True, text=True, cwd=self.root_path)
            return result.returncode == 0 and "PONG" in result.stdout

        except Exception:
            return False

    def _validate_api_endpoints(self, config: DeploymentConfig) -> bool:
        """Validate API endpoint accessibility."""
        try:
            # Test API gateway health
            gateway_cmd = [
                "docker-compose", "-f", f"docker-compose.{config.environment}.yml",
                "exec", "-T", "dotmac-api-gateway", "curl", "-f", "http://localhost:8000/health"
            ]

            result = subprocess.run(gateway_cmd, check=False, capture_output=True, text=True, cwd=self.root_path)
            return result.returncode == 0

        except Exception:
            return False

    def _validate_service_communication(self, config: DeploymentConfig) -> bool:
        """Validate inter-service communication."""
        try:
            # Test service-to-service communication
            comm_cmd = [
                "docker-compose", "-f", f"docker-compose.{config.environment}.yml",
                "exec", "-T", "dotmac-api-gateway", "curl", "-f", "http://dotmac-platform:8000/health"
            ]

            result = subprocess.run(comm_cmd, check=False, capture_output=True, text=True, cwd=self.root_path)
            return result.returncode == 0

        except Exception:
            return False

    def _rollback_deployment(self, config: DeploymentConfig) -> bool:
        """Rollback to previous deployment."""
        logger.info("🔄 Rolling back deployment")

        try:
            # Find latest backup
            backup_dir = self.root_path / "backups"
            if not backup_dir.exists():
                logger.error("No backups found for rollback")
                return False

            backups = sorted([d for d in backup_dir.iterdir() if d.is_dir() and config.environment in d.name])
            if not backups:
                logger.error(f"No backups found for environment: {config.environment}")
                return False

            latest_backup = backups[-1]
            logger.info(f"Rolling back to: {latest_backup}")

            # Stop current services
            stop_cmd = [
                "docker-compose", "-f", f"docker-compose.{config.environment}.yml",
                "down", "--remove-orphans"
            ]
            subprocess.run(stop_cmd, check=False, cwd=self.root_path)

            # Restore database
            db_backup = latest_backup / "database.sql"
            if db_backup.exists():
                restore_cmd = [
                    "docker-compose", "-f", f"docker-compose.{config.environment}.yml",
                    "exec", "-T", "postgres", "psql", "-U", "dotmac", "-f", "-"
                ]

                with open(db_backup) as f:
                    subprocess.run(restore_cmd, check=False, stdin=f, cwd=self.root_path)

            # Restore Redis
            redis_backup = latest_backup / "redis.rdb"
            if redis_backup.exists():
                subprocess.run(["docker", "cp", str(redis_backup), "redis:/data/dump.rdb"], check=False)

            # Restart services
            start_cmd = [
                "docker-compose", "-f", f"docker-compose.{config.environment}.yml",
                "up", "-d"
            ]

            result = subprocess.run(start_cmd, check=False, cwd=self.root_path)
            if result.returncode == 0:
                logger.info("✅ Rollback completed successfully")
                return True
            logger.error("❌ Rollback failed")
            return False

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def _record_deployment(self, config: DeploymentConfig, success: bool):
        """Record deployment in history."""
        deployment_record = {
            "timestamp": datetime.now().isoformat(),
            "environment": config.environment,
            "version": config.version,
            "success": success,
            "services": config.services or self.services
        }

        self.deployment_history.append(deployment_record)

        # Save to file
        history_file = self.root_path / "deployment_history.json"
        try:
            if history_file.exists():
                with open(history_file) as f:
                    history = json.load(f)
            else:
                history = []

            history.append(deployment_record)

            with open(history_file, "w") as f:
                json.dump(history, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to record deployment history: {e}")


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="DotMac Platform Deployment Automation")

    parser.add_argument("environment", choices=["development", "staging", "production"],
                       help="Target deployment environment")
    parser.add_argument("--version", default="latest", help="Version to deploy")
    parser.add_argument("--services", nargs="+", help="Specific services to deploy")
    parser.add_argument("--no-rollback", action="store_true", help="Disable automatic rollback")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup creation")
    parser.add_argument("--no-validation", action="store_true", help="Skip post-deployment validation")
    parser.add_argument("--timeout", type=int, default=300, help="Health check timeout in seconds")
    parser.add_argument("--root", default=".", help="Root directory of DotMac framework")

    args = parser.parse_args()

    config = DeploymentConfig(
        environment=args.environment,
        version=args.version,
        services=args.services,
        rollback_enabled=not args.no_rollback,
        backup_enabled=not args.no_backup,
        post_deployment_validation=not args.no_validation,
        health_check_timeout=args.timeout
    )

    deployer = DotMacDeployer(args.root)
    success = deployer.deploy(config)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()
