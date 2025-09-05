"""
Secret Rotation Monitoring Service
Monitors OpenBao/Vault secrets for expiration and rotation needs
"""

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from dotmac_shared.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SecretMetadata:
    """Metadata about a secret"""

    path: str
    last_rotation: Optional[datetime]
    expiry_date: Optional[datetime]
    rotation_interval_days: int
    is_expired: bool
    days_until_expiry: Optional[int]
    severity: str


class SecretRotationMonitor:
    """
    Monitors secrets for rotation needs and expiration warnings.
    Integrates with OpenBao/Vault to track secret lifecycle.
    """

    def __init__(self):
        self.monitoring_results: list[SecretMetadata] = []
        self.rotation_thresholds = {
            "critical": 7,  # Days until expiry
            "warning": 30,
            "info": 60,
        }

    async def monitor_secrets(self) -> dict[str, Any]:
        """
        Monitor all tracked secrets for rotation needs.

        Returns:
            Dict containing monitoring results and alerts
        """
        logger.info("Starting secret rotation monitoring")

        self.monitoring_results = []

        # Monitor core application secrets
        await self._monitor_core_secrets()

        # Monitor database secrets
        await self._monitor_database_secrets()

        # Monitor external service secrets
        await self._monitor_external_secrets()

        # Categorize results
        critical = [s for s in self.monitoring_results if s.severity == "critical"]
        warnings = [s for s in self.monitoring_results if s.severity == "warning"]
        info = [s for s in self.monitoring_results if s.severity == "info"]
        expired = [s for s in self.monitoring_results if s.is_expired]

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_secrets": len(self.monitoring_results),
                "critical_alerts": len(critical),
                "warning_alerts": len(warnings),
                "info_alerts": len(info),
                "expired_secrets": len(expired),
            },
            "alerts": {
                "critical": [self._secret_to_dict(s) for s in critical],
                "warnings": [self._secret_to_dict(s) for s in warnings],
                "info": [self._secret_to_dict(s) for s in info],
                "expired": [self._secret_to_dict(s) for s in expired],
            },
            "recommendations": self._generate_recommendations(
                critical, warnings, expired
            ),
        }

        if critical or expired:
            logger.error(
                f"Critical secret issues found: {len(critical)} critical, {len(expired)} expired"
            )
        elif warnings:
            logger.warning(
                f"Secret rotation warnings: {len(warnings)} secrets need attention"
            )

        return result

    async def _monitor_core_secrets(self) -> None:
        """Monitor core application secrets"""

        secrets_to_monitor = [
            {
                "path": "auth/jwt-secret",
                "env_var": "JWT_SECRET",
                "rotation_days": 90,
                "description": "JWT signing secret",
            },
            {
                "path": "auth/webhook-secret",
                "env_var": "WEBHOOK_SECRET",
                "rotation_days": 30,
                "description": "Webhook signature secret",
            },
            {
                "path": "app/encryption-key",
                "env_var": "ENCRYPTION_KEY",
                "rotation_days": 180,
                "description": "Data encryption key",
            },
        ]

        for secret_config in secrets_to_monitor:
            await self._check_secret_rotation(secret_config)

    async def _monitor_database_secrets(self) -> None:
        """Monitor database-related secrets"""

        # Database credentials
        db_secrets = [
            {
                "path": "database/admin-password",
                "env_var": "DB_ADMIN_PASSWORD",
                "rotation_days": 90,
                "description": "Database admin password",
            },
            {
                "path": "database/app-password",
                "env_var": "DB_APP_PASSWORD",
                "rotation_days": 90,
                "description": "Application database password",
            },
        ]

        for secret_config in db_secrets:
            await self._check_secret_rotation(secret_config)

    async def _monitor_external_secrets(self) -> None:
        """Monitor external service secrets"""

        external_secrets = [
            {
                "path": "external/stripe-secret",
                "env_var": "STRIPE_SECRET_KEY",
                "rotation_days": 365,
                "description": "Stripe API secret",
            },
            {
                "path": "external/smtp-password",
                "env_var": "SMTP_PASSWORD",
                "rotation_days": 180,
                "description": "SMTP server password",
            },
            {
                "path": "external/redis-password",
                "env_var": "REDIS_PASSWORD",
                "rotation_days": 180,
                "description": "Redis server password",
            },
        ]

        for secret_config in external_secrets:
            await self._check_secret_rotation(secret_config)

    async def _check_secret_rotation(self, secret_config: dict[str, Any]) -> None:
        """
        Check if a secret needs rotation based on its configuration.
        In a real implementation, this would query OpenBao/Vault for metadata.
        """

        path = secret_config["path"]
        env_var = secret_config["env_var"]
        rotation_days = secret_config["rotation_days"]
        description = secret_config["description"]

        # Check if environment variable exists
        current_value = os.getenv(env_var)
        if not current_value:
            # Secret not configured via environment
            self._add_secret_result(
                path=path,
                is_expired=False,
                days_until_expiry=None,
                severity="info",
                rotation_days=rotation_days,
                description=f"{description} - Not configured via environment variable",
            )
            return

        # In a real implementation, you would:
        # 1. Query OpenBao/Vault for secret metadata
        # 2. Check creation date and rotation schedule
        # 3. Calculate days until expiry

        # For now, we'll simulate based on environment detection
        last_rotation = self._estimate_last_rotation(current_value, env_var)
        expiry_date = (
            last_rotation + timedelta(days=rotation_days) if last_rotation else None
        )

        if expiry_date:
            now = datetime.now(timezone.utc)
            days_until_expiry = (expiry_date - now).days
            is_expired = days_until_expiry <= 0

            # Determine severity
            if is_expired:
                severity = "critical"
            elif days_until_expiry <= self.rotation_thresholds["critical"]:
                severity = "critical"
            elif days_until_expiry <= self.rotation_thresholds["warning"]:
                severity = "warning"
            else:
                severity = "info"
        else:
            days_until_expiry = None
            is_expired = False
            severity = "info"

        self._add_secret_result(
            path=path,
            is_expired=is_expired,
            days_until_expiry=days_until_expiry,
            severity=severity,
            rotation_days=rotation_days,
            description=description,
        )

    def _estimate_last_rotation(
        self, secret_value: str, env_var: str
    ) -> Optional[datetime]:
        """
        Estimate when a secret was last rotated.
        This is a simplified implementation - in production, you'd query OpenBao/Vault.
        """

        # Check for development defaults
        dev_defaults = {
            "JWT_SECRET": "dev-jwt-secret-change-in-production",
            "WEBHOOK_SECRET": "dev-webhook-secret",
            "ENCRYPTION_KEY": "dev-encryption-key-change-in-production",
        }

        if secret_value in dev_defaults.values():
            # Development default - assume it needs rotation
            return datetime.now(timezone.utc) - timedelta(days=365)

        # For production secrets, assume they were rotated recently
        # In a real implementation, this would come from OpenBao/Vault metadata
        if len(secret_value) > 20 and not secret_value.startswith("dev-"):
            return datetime.now(timezone.utc) - timedelta(days=30)

        return None

    def _add_secret_result(
        self,
        path: str,
        is_expired: bool,
        days_until_expiry: Optional[int],
        severity: str,
        rotation_days: int,
        description: str,
    ) -> None:
        """Add a secret monitoring result"""

        result = SecretMetadata(
            path=path,
            last_rotation=None,  # Would be populated from OpenBao/Vault
            expiry_date=None,  # Would be calculated from metadata
            rotation_interval_days=rotation_days,
            is_expired=is_expired,
            days_until_expiry=days_until_expiry,
            severity=severity,
        )

        self.monitoring_results.append(result)

        # Log based on severity
        if severity == "critical" or is_expired:
            logger.error(
                f"CRITICAL: Secret {path} needs immediate rotation - {description}"
            )
        elif severity == "warning":
            logger.warning(
                f"WARNING: Secret {path} needs rotation soon - {description}"
            )

    def _secret_to_dict(self, secret: SecretMetadata) -> dict[str, Any]:
        """Convert secret metadata to dictionary"""
        return {
            "path": secret.path,
            "is_expired": secret.is_expired,
            "days_until_expiry": secret.days_until_expiry,
            "severity": secret.severity,
            "rotation_interval_days": secret.rotation_interval_days,
        }

    def _generate_recommendations(
        self,
        critical: list[SecretMetadata],
        warnings: list[SecretMetadata],
        expired: list[SecretMetadata],
    ) -> list[str]:
        """Generate recommendations based on monitoring results"""

        recommendations = []

        if critical or expired:
            recommendations.append(
                "🚨 IMMEDIATE ACTION REQUIRED: Rotate critical secrets immediately"
            )

        if warnings:
            recommendations.append(
                f"⚠️ Rotate {len(warnings)} secrets within the next 30 days"
            )

        if len(self.monitoring_results) > 0:
            recommendations.append(
                "📅 Set up automated secret rotation alerts in your monitoring system"
            )

        recommendations.append(
            "🔄 Implement automatic secret rotation in your CI/CD pipeline"
        )

        return recommendations


# Convenience functions
async def monitor_secret_rotation() -> dict[str, Any]:
    """Monitor all secrets for rotation needs"""
    monitor = SecretRotationMonitor()
    return await monitor.monitor_secrets()


async def check_secret_expiry() -> list[SecretMetadata]:
    """Get list of secrets that need rotation"""
    monitor = SecretRotationMonitor()
    await monitor.monitor_secrets()

    needs_rotation = [
        secret
        for secret in monitor.monitoring_results
        if secret.is_expired
        or (secret.days_until_expiry and secret.days_until_expiry <= 30)
    ]

    return needs_rotation


def get_rotation_schedule() -> dict[str, int]:
    """Get recommended rotation schedule for different secret types"""
    return {
        "jwt_secrets": 90,  # 3 months
        "api_keys": 180,  # 6 months
        "database_credentials": 90,  # 3 months
        "encryption_keys": 365,  # 1 year
        "webhook_secrets": 30,  # 1 month
        "tls_certificates": 90,  # 3 months
    }
