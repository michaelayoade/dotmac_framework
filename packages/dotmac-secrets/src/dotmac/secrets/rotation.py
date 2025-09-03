"""
Secret rotation helpers and scheduling
Provides utilities for secret rotation management and scheduling
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Union
from dataclasses import dataclass, field
from enum import Enum

from .interfaces import KeyRotationPolicy, SecretsProvider, WritableSecretsProvider
from .types import SecretKind, SecretMetadata

logger = logging.getLogger(__name__)


class RotationStatus(str, Enum):
    """Rotation status for secrets"""
    
    ACTIVE = "active"
    WARNING = "warning"  # Approaching rotation time
    OVERDUE = "overdue"
    ROTATING = "rotating"
    FAILED = "failed"


@dataclass
class RotationRule:
    """Rule for secret rotation"""
    
    secret_path: str
    kind: SecretKind
    max_age_days: int
    warning_threshold_days: int = 7
    enabled: bool = True
    callback: Optional[Callable[[str, SecretKind], bool]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RotationResult:
    """Result of rotation operation"""
    
    secret_path: str
    kind: SecretKind
    status: RotationStatus
    old_version: Optional[str] = None
    new_version: Optional[str] = None
    error: Optional[str] = None
    rotated_at: Optional[datetime] = None


class DefaultRotationPolicy:
    """
    Default implementation of KeyRotationPolicy
    Provides standard rotation logic based on age and configuration
    """
    
    def __init__(
        self,
        default_max_age_days: int = 90,
        warning_threshold_days: int = 7,
        rotation_rules: Optional[Dict[SecretKind, int]] = None
    ) -> None:
        """
        Initialize rotation policy
        
        Args:
            default_max_age_days: Default maximum age before rotation needed
            warning_threshold_days: Days before rotation to start warning
            rotation_rules: Kind-specific max age overrides
        """
        self.default_max_age_days = default_max_age_days
        self.warning_threshold_days = warning_threshold_days
        self.rotation_rules = rotation_rules or {
            SecretKind.JWT_KEYPAIR: 30,  # JWT keys rotate more frequently
            SecretKind.SERVICE_SIGNING_SECRET: 60,
            SecretKind.WEBHOOK_SECRET: 90,
            SecretKind.ENCRYPTION_KEY: 180,  # Encryption keys less frequently
            SecretKind.DATABASE_CREDENTIALS: 90,
        }
    
    def should_rotate(self, metadata: SecretMetadata) -> bool:
        """
        Determine if a secret should be rotated based on age
        
        Args:
            metadata: Secret metadata including creation/update dates
            
        Returns:
            True if secret should be rotated
        """
        if not metadata.created_at and not metadata.updated_at:
            # No timestamp information, assume it needs rotation
            logger.warning(f"No timestamp info for secret {metadata.path}, assuming rotation needed")
            return True
        
        # Use updated_at if available, otherwise created_at
        timestamp_str = metadata.updated_at or metadata.created_at
        if not timestamp_str:
            return True
        
        try:
            # Parse timestamp (assuming ISO format)
            if timestamp_str.endswith('Z'):
                timestamp = datetime.fromisoformat(timestamp_str[:-1] + '+00:00')
            else:
                timestamp = datetime.fromisoformat(timestamp_str)
            
            # Ensure timezone awareness
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            age_days = (now - timestamp).days
            
            # Get max age for this secret kind
            max_age = self.rotation_rules.get(metadata.kind, self.default_max_age_days)
            
            return age_days >= max_age
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse timestamp for {metadata.path}: {e}")
            return True
    
    def get_rotation_schedule(self, metadata: SecretMetadata) -> Optional[str]:
        """
        Get next rotation time as ISO string
        
        Args:
            metadata: Secret metadata
            
        Returns:
            ISO datetime string for next rotation, or None if no rotation needed
        """
        if not metadata.created_at and not metadata.updated_at:
            # No timestamp, rotate immediately
            return datetime.now(timezone.utc).isoformat()
        
        timestamp_str = metadata.updated_at or metadata.created_at
        if not timestamp_str:
            return datetime.now(timezone.utc).isoformat()
        
        try:
            if timestamp_str.endswith('Z'):
                timestamp = datetime.fromisoformat(timestamp_str[:-1] + '+00:00')
            else:
                timestamp = datetime.fromisoformat(timestamp_str)
            
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            
            max_age = self.rotation_rules.get(metadata.kind, self.default_max_age_days)
            next_rotation = timestamp + timedelta(days=max_age)
            
            return next_rotation.isoformat()
            
        except (ValueError, TypeError):
            return datetime.now(timezone.utc).isoformat()
    
    def get_warning_threshold(self) -> int:
        """Get warning threshold in days before rotation needed"""
        return self.warning_threshold_days
    
    def get_status(self, metadata: SecretMetadata) -> RotationStatus:
        """
        Get rotation status for a secret
        
        Args:
            metadata: Secret metadata
            
        Returns:
            Current rotation status
        """
        if self.should_rotate(metadata):
            return RotationStatus.OVERDUE
        
        # Check if we're in warning period
        timestamp_str = metadata.updated_at or metadata.created_at
        if timestamp_str:
            try:
                if timestamp_str.endswith('Z'):
                    timestamp = datetime.fromisoformat(timestamp_str[:-1] + '+00:00')
                else:
                    timestamp = datetime.fromisoformat(timestamp_str)
                
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                
                now = datetime.now(timezone.utc)
                age_days = (now - timestamp).days
                
                max_age = self.rotation_rules.get(metadata.kind, self.default_max_age_days)
                warning_threshold = max_age - self.warning_threshold_days
                
                if age_days >= warning_threshold:
                    return RotationStatus.WARNING
                    
            except (ValueError, TypeError):
                return RotationStatus.WARNING
        
        return RotationStatus.ACTIVE


class RotationScheduler:
    """
    Scheduler for managing secret rotations
    Provides rotation tracking and execution coordination
    """
    
    def __init__(
        self,
        policy: Optional[KeyRotationPolicy] = None,
        provider: Optional[WritableSecretsProvider] = None
    ) -> None:
        """
        Initialize rotation scheduler
        
        Args:
            policy: Rotation policy implementation
            provider: Optional provider for automatic rotation
        """
        self.policy = policy or DefaultRotationPolicy()
        self.provider = provider
        self.rotation_rules: Dict[str, RotationRule] = {}
        self.rotation_history: List[RotationResult] = []
        self._rotation_callbacks: Dict[str, List[Callable]] = {}
        
        # Background task for scheduled rotations
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False
    
    def add_rotation_rule(self, rule: RotationRule) -> None:
        """
        Add rotation rule for a secret
        
        Args:
            rule: Rotation rule configuration
        """
        self.rotation_rules[rule.secret_path] = rule
        logger.info(f"Added rotation rule for {rule.secret_path}: {rule.max_age_days} days")
    
    def remove_rotation_rule(self, secret_path: str) -> bool:
        """
        Remove rotation rule for a secret
        
        Args:
            secret_path: Secret path to remove rule for
            
        Returns:
            True if rule was removed
        """
        if secret_path in self.rotation_rules:
            del self.rotation_rules[secret_path]
            logger.info(f"Removed rotation rule for {secret_path}")
            return True
        return False
    
    def add_rotation_callback(
        self,
        secret_path: str,
        callback: Callable[[RotationResult], None]
    ) -> None:
        """
        Add callback to be called when secret is rotated
        
        Args:
            secret_path: Secret path to monitor
            callback: Callback function to call on rotation
        """
        if secret_path not in self._rotation_callbacks:
            self._rotation_callbacks[secret_path] = []
        self._rotation_callbacks[secret_path].append(callback)
    
    def get_rotation_status(
        self,
        secrets: List[SecretMetadata]
    ) -> Dict[str, RotationStatus]:
        """
        Get rotation status for multiple secrets
        
        Args:
            secrets: List of secret metadata to check
            
        Returns:
            Dictionary mapping secret paths to rotation status
        """
        status_map = {}
        
        for metadata in secrets:
            # Check if there's a specific rule for this secret
            rule = self.rotation_rules.get(metadata.path)
            
            if rule and not rule.enabled:
                status_map[metadata.path] = RotationStatus.ACTIVE
                continue
            
            if isinstance(self.policy, DefaultRotationPolicy):
                status = self.policy.get_status(metadata)
            else:
                # Use generic policy interface
                if self.policy.should_rotate(metadata):
                    status = RotationStatus.OVERDUE
                else:
                    # Simple check for warning period
                    status = RotationStatus.ACTIVE
            
            status_map[metadata.path] = status
        
        return status_map
    
    def get_secrets_needing_rotation(
        self,
        secrets: List[SecretMetadata]
    ) -> List[SecretMetadata]:
        """
        Get list of secrets that need rotation
        
        Args:
            secrets: List of secret metadata to check
            
        Returns:
            List of secrets needing rotation
        """
        needing_rotation = []
        
        for metadata in secrets:
            rule = self.rotation_rules.get(metadata.path)
            
            # Skip disabled rules
            if rule and not rule.enabled:
                continue
            
            if self.policy.should_rotate(metadata):
                needing_rotation.append(metadata)
        
        return needing_rotation
    
    async def rotate_secret(
        self,
        secret_path: str,
        kind: SecretKind,
        new_secret_data: Optional[Dict[str, Any]] = None
    ) -> RotationResult:
        """
        Perform rotation for a single secret
        
        Args:
            secret_path: Path of secret to rotate
            kind: Kind of secret being rotated
            new_secret_data: Optional new secret data, or None to auto-generate
            
        Returns:
            Rotation result
        """
        result = RotationResult(
            secret_path=secret_path,
            kind=kind,
            status=RotationStatus.ROTATING
        )
        
        try:
            # Check if we have a rule-specific callback
            rule = self.rotation_rules.get(secret_path)
            if rule and rule.callback:
                success = rule.callback(secret_path, kind)
                if success:
                    result.status = RotationStatus.ACTIVE
                    result.rotated_at = datetime.now(timezone.utc)
                else:
                    result.status = RotationStatus.FAILED
                    result.error = "Rule callback failed"
            
            # If we have a writable provider and secret data, store the new secret
            elif self.provider and new_secret_data:
                success = await self.provider.put_secret(secret_path, new_secret_data)
                if success:
                    result.status = RotationStatus.ACTIVE
                    result.rotated_at = datetime.now(timezone.utc)
                else:
                    result.status = RotationStatus.FAILED
                    result.error = "Failed to store new secret"
            
            else:
                result.status = RotationStatus.FAILED
                result.error = "No rotation mechanism available"
            
            # Call any registered callbacks
            callbacks = self._rotation_callbacks.get(secret_path, [])
            for callback in callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.warning(f"Rotation callback failed for {secret_path}: {e}")
            
            # Add to history
            self.rotation_history.append(result)
            
            # Limit history size
            if len(self.rotation_history) > 1000:
                self.rotation_history = self.rotation_history[-500:]
            
            logger.info(f"Rotation result for {secret_path}: {result.status}")
            
        except Exception as e:
            result.status = RotationStatus.FAILED
            result.error = str(e)
            logger.error(f"Rotation failed for {secret_path}: {e}")
        
        return result
    
    async def start_scheduler(self, check_interval_hours: int = 24) -> None:
        """
        Start background rotation scheduler
        
        Args:
            check_interval_hours: Hours between rotation checks
        """
        if self._running:
            logger.warning("Rotation scheduler already running")
            return
        
        self._running = True
        self._scheduler_task = asyncio.create_task(
            self._scheduler_loop(check_interval_hours)
        )
        logger.info(f"Started rotation scheduler with {check_interval_hours}h interval")
    
    async def stop_scheduler(self) -> None:
        """Stop background rotation scheduler"""
        self._running = False
        
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped rotation scheduler")
    
    async def _scheduler_loop(self, check_interval_hours: int) -> None:
        """Background scheduler loop"""
        check_interval_seconds = check_interval_hours * 3600
        
        while self._running:
            try:
                await asyncio.sleep(check_interval_seconds)
                
                if not self._running:
                    break
                
                logger.info("Running scheduled rotation check")
                
                # Check each rule for rotation needs
                for path, rule in self.rotation_rules.items():
                    if not rule.enabled:
                        continue
                    
                    # This is a simplified check - in a real implementation,
                    # you'd need to fetch current secret metadata
                    logger.debug(f"Checking rotation for {path}")
                    
                    # For now, just log that we would check
                    # In a full implementation, you'd:
                    # 1. Fetch secret metadata
                    # 2. Check if rotation needed
                    # 3. Perform rotation if needed
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in rotation scheduler: {e}")
                # Continue running even if there was an error
    
    def get_rotation_history(
        self,
        secret_path: Optional[str] = None,
        limit: int = 100
    ) -> List[RotationResult]:
        """
        Get rotation history
        
        Args:
            secret_path: Optional path filter
            limit: Maximum number of results
            
        Returns:
            List of rotation results
        """
        history = self.rotation_history
        
        if secret_path:
            history = [r for r in history if r.secret_path == secret_path]
        
        return sorted(history, key=lambda x: x.rotated_at or datetime.min, reverse=True)[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rotation scheduler statistics"""
        total_rules = len(self.rotation_rules)
        enabled_rules = sum(1 for rule in self.rotation_rules.values() if rule.enabled)
        
        status_counts = {}
        for result in self.rotation_history[-100:]:  # Last 100 rotations
            status = result.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "scheduler_running": self._running,
            "rotation_history_size": len(self.rotation_history),
            "recent_status_counts": status_counts,
        }


# Utility functions for common rotation operations
def schedule_rotation(
    kind: SecretKind,
    name: str,
    cadence_days: int,
    scheduler: RotationScheduler
) -> None:
    """
    Helper to schedule rotation for a secret
    
    Args:
        kind: Type of secret
        name: Secret name/path
        cadence_days: Rotation frequency in days
        scheduler: Rotation scheduler instance
    """
    rule = RotationRule(
        secret_path=name,
        kind=kind,
        max_age_days=cadence_days,
        enabled=True
    )
    scheduler.add_rotation_rule(rule)


async def rotate_jwt_keypair(
    app: str,
    scheduler: RotationScheduler,
    kid: Optional[str] = None
) -> RotationResult:
    """
    Rotate JWT keypair (stub for future implementation)
    
    Args:
        app: Application name
        scheduler: Rotation scheduler
        kid: Optional key ID
        
    Returns:
        Rotation result
    """
    from .types import SecretPaths
    
    path = SecretPaths.jwt_keypair(app, kid)
    
    # This is a stub - actual implementation would:
    # 1. Generate new keypair
    # 2. Update secret in provider
    # 3. Handle key rollover coordination
    
    logger.info(f"JWT keypair rotation requested for {path} (not implemented)")
    
    return await scheduler.rotate_secret(path, SecretKind.JWT_KEYPAIR)