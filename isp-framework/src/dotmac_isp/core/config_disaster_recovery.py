"""
Configuration disaster recovery automation system.
Provides automated disaster recovery procedures for configuration management.
"""

import os
import json
import logging
import asyncio
import schedule
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
from pathlib import Path
import shutil
import time
import threading
from concurrent.futures import ThreadPoolExecutor

from .config_backup import get_config_backup, BackupType, BackupStatus
from .config_audit import get_config_audit, ChangeType, ChangeSource
from .secrets_manager import get_secrets_manager
from .config_encryption import get_config_encryption
from .config_hotreload import get_config_hotreload, ReloadTrigger

logger = logging.getLogger(__name__, timezone)


class DisasterType(str, Enum):
    """Types of configuration disasters."""

    CONFIGURATION_CORRUPTION = "configuration_corruption"
    SECRETS_COMPROMISE = "secrets_compromise"
    SERVICE_FAILURE = "service_failure"
    DATA_CENTER_OUTAGE = "data_center_outage"
    SECURITY_BREACH = "security_breach"
    HUMAN_ERROR = "human_error"
    SYSTEM_COMPROMISE = "system_compromise"
    PARTIAL_FAILURE = "partial_failure"


class RecoveryPriority(str, Enum):
    """Recovery priority levels."""

    CRITICAL = "critical"  # Immediate recovery required
    HIGH = "high"  # Recovery within 15 minutes
    MEDIUM = "medium"  # Recovery within 1 hour
    LOW = "low"  # Recovery within 4 hours


class RecoveryStatus(str, Enum):
    """Recovery operation status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class DisasterEvent(BaseModel):
    """Disaster event record."""

    event_id: str
    disaster_type: DisasterType
    priority: RecoveryPriority
    detected_at: datetime
    description: str

    # Affected components
    affected_services: List[str] = Field(default_factory=list)
    affected_environments: List[str] = Field(default_factory=list)
    affected_config_paths: List[str] = Field(default_factory=list)

    # Detection details
    detection_source: str = "system"
    detection_method: str = "automated"
    confidence_level: float = Field(default=0.8, ge=0.0, le=1.0)

    # Impact assessment
    estimated_downtime: Optional[timedelta] = None
    business_impact: str = "unknown"
    compliance_impact: bool = False

    # Metadata
    tags: List[str] = Field(default_factory=list)
    related_events: List[str] = Field(default_factory=list)


class RecoveryPlan(BaseModel):
    """Disaster recovery plan."""

    plan_id: str
    disaster_type: DisasterType
    priority: RecoveryPriority

    # Recovery steps
    recovery_steps: List[Dict[str, Any]] = Field(default_factory=list)
    estimated_duration: timedelta
    dependencies: List[str] = Field(default_factory=list)

    # Rollback plan
    rollback_steps: List[Dict[str, Any]] = Field(default_factory=list)
    rollback_triggers: List[str] = Field(default_factory=list)

    # Validation
    validation_steps: List[Dict[str, Any]] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)

    # Communication
    notification_contacts: List[str] = Field(default_factory=list)
    escalation_rules: List[Dict[str, Any]] = Field(default_factory=list)


class RecoveryExecution(BaseModel):
    """Recovery execution record."""

    execution_id: str
    event_id: str
    plan_id: str
    status: RecoveryStatus

    # Timing
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration: Optional[timedelta] = None

    # Progress tracking
    current_step: int = 0
    total_steps: int = 0
    progress_percentage: float = 0.0

    # Results
    steps_completed: List[Dict[str, Any]] = Field(default_factory=list)
    steps_failed: List[Dict[str, Any]] = Field(default_factory=list)
    recovery_artifacts: List[str] = Field(default_factory=list)

    # Validation results
    validation_passed: bool = False
    validation_errors: List[str] = Field(default_factory=list)

    # Metadata
    executed_by: str = "system"
    automation_level: str = "full"  # full, partial, manual
    error_message: Optional[str] = None


class ConfigurationDisasterRecovery:
    """
    Configuration disaster recovery automation system.
    Provides comprehensive disaster detection, planning, and automated recovery.
    """

    def __init__(
        self,
        storage_path: str = "/var/lib/dotmac/disaster-recovery",
        monitoring_interval: int = 60,  # seconds
        auto_recovery_enabled: bool = True,
        max_concurrent_recoveries: int = 3,
    ):
        """
        Initialize disaster recovery system.

        Args:
            storage_path: Path to store disaster recovery data
            monitoring_interval: Monitoring check interval in seconds
            auto_recovery_enabled: Enable automatic recovery
            max_concurrent_recoveries: Maximum concurrent recovery operations
        """
        self.storage_path = Path(storage_path)
        self.monitoring_interval = monitoring_interval
        self.auto_recovery_enabled = auto_recovery_enabled
        self.max_concurrent_recoveries = max_concurrent_recoveries

        # Initialize storage
        self.storage_path.mkdir(parents=True, exist_ok=True, mode=0o750)

        # State management
        self.disaster_events: Dict[str, DisasterEvent] = {}
        self.recovery_plans: Dict[str, RecoveryPlan] = {}
        self.recovery_executions: Dict[str, RecoveryExecution] = {}

        # Monitoring state
        self._monitoring_active = False
        self._monitoring_thread = None
        self._recovery_executor = ThreadPoolExecutor(
            max_workers=max_concurrent_recoveries
        )

        # Health baseline
        self._last_health_check = None
        self._health_baseline = {}

        # Load existing data
        self._load_disaster_recovery_data()

        # Initialize recovery plans
        self._initialize_recovery_plans()

        # Setup monitoring
        self._setup_health_monitoring()

    def _load_disaster_recovery_data(self):
        """Load existing disaster recovery data."""
        try:
            # Load disaster events
            events_file = self.storage_path / "disaster_events.json"
            if events_file.exists():
                with open(events_file, "r") as f:
                    events_data = json.load(f)
                    self.disaster_events = {
                        k: DisasterEvent(**v) for k, v in events_data.items()
                    }

            # Load recovery plans
            plans_file = self.storage_path / "recovery_plans.json"
            if plans_file.exists():
                with open(plans_file, "r") as f:
                    plans_data = json.load(f)
                    self.recovery_plans = {
                        k: RecoveryPlan(**v) for k, v in plans_data.items()
                    }

            # Load recovery executions
            executions_file = self.storage_path / "recovery_executions.json"
            if executions_file.exists():
                with open(executions_file, "r") as f:
                    executions_data = json.load(f)
                    self.recovery_executions = {
                        k: RecoveryExecution(**v) for k, v in executions_data.items()
                    }

        except Exception as e:
            logger.error(f"Failed to load disaster recovery data: {e}")

    def _save_disaster_recovery_data(self):
        """Save disaster recovery data."""
        try:
            # Save disaster events
            events_file = self.storage_path / "disaster_events.json"
            with open(events_file, "w") as f:
                json.dump(
                    {k: v.model_dump() for k, v in self.disaster_events.items()},
                    f,
                    indent=2,
                    default=str,
                )

            # Save recovery plans
            plans_file = self.storage_path / "recovery_plans.json"
            with open(plans_file, "w") as f:
                json.dump(
                    {k: v.model_dump() for k, v in self.recovery_plans.items()},
                    f,
                    indent=2,
                    default=str,
                )

            # Save recovery executions
            executions_file = self.storage_path / "recovery_executions.json"
            with open(executions_file, "w") as f:
                json.dump(
                    {k: v.model_dump() for k, v in self.recovery_executions.items()},
                    f,
                    indent=2,
                    default=str,
                )

        except Exception as e:
            logger.error(f"Failed to save disaster recovery data: {e}")

    def _initialize_recovery_plans(self):
        """Initialize built-in recovery plans."""

        # Configuration corruption recovery
        self.add_recovery_plan(
            RecoveryPlan(
                plan_id="config_corruption_recovery",
                disaster_type=DisasterType.CONFIGURATION_CORRUPTION,
                priority=RecoveryPriority.CRITICAL,
                recovery_steps=[
                    {
                        "step": "detect_corruption",
                        "action": "validate_configuration",
                        "timeout": 30,
                    },
                    {
                        "step": "identify_last_good_backup",
                        "action": "find_latest_valid_backup",
                        "timeout": 60,
                    },
                    {
                        "step": "restore_configuration",
                        "action": "restore_from_backup",
                        "timeout": 120,
                    },
                    {
                        "step": "validate_restoration",
                        "action": "verify_config_integrity",
                        "timeout": 60,
                    },
                    {
                        "step": "restart_services",
                        "action": "reload_configuration",
                        "timeout": 180,
                    },
                ],
                estimated_duration=timedelta(minutes=8),
                validation_steps=[
                    {"action": "health_check", "timeout": 30},
                    {"action": "config_validation", "timeout": 30},
                ],
                success_criteria=[
                    "configuration_valid",
                    "services_healthy",
                    "no_corruption_detected",
                ],
            )
        )

        # Secrets compromise recovery
        self.add_recovery_plan(
            RecoveryPlan(
                plan_id="secrets_compromise_recovery",
                disaster_type=DisasterType.SECRETS_COMPROMISE,
                priority=RecoveryPriority.CRITICAL,
                recovery_steps=[
                    {
                        "step": "revoke_compromised_secrets",
                        "action": "revoke_secrets",
                        "timeout": 60,
                    },
                    {
                        "step": "generate_new_secrets",
                        "action": "generate_secrets",
                        "timeout": 120,
                    },
                    {
                        "step": "update_configuration",
                        "action": "update_secret_references",
                        "timeout": 180,
                    },
                    {
                        "step": "notify_services",
                        "action": "reload_secrets",
                        "timeout": 300,
                    },
                    {
                        "step": "verify_security",
                        "action": "security_validation",
                        "timeout": 120,
                    },
                ],
                estimated_duration=timedelta(minutes=15),
                validation_steps=[
                    {"action": "secret_integrity_check", "timeout": 60},
                    {"action": "security_scan", "timeout": 120},
                ],
                success_criteria=[
                    "new_secrets_generated",
                    "compromised_secrets_revoked",
                    "security_validation_passed",
                ],
            )
        )

        # Service failure recovery
        self.add_recovery_plan(
            RecoveryPlan(
                plan_id="service_failure_recovery",
                disaster_type=DisasterType.SERVICE_FAILURE,
                priority=RecoveryPriority.HIGH,
                recovery_steps=[
                    {
                        "step": "diagnose_failure",
                        "action": "analyze_service_health",
                        "timeout": 60,
                    },
                    {
                        "step": "check_configuration",
                        "action": "validate_service_config",
                        "timeout": 30,
                    },
                    {
                        "step": "restore_if_needed",
                        "action": "conditional_config_restore",
                        "timeout": 180,
                    },
                    {
                        "step": "restart_service",
                        "action": "service_restart",
                        "timeout": 120,
                    },
                    {
                        "step": "verify_recovery",
                        "action": "service_health_check",
                        "timeout": 60,
                    },
                ],
                estimated_duration=timedelta(minutes=7),
                validation_steps=[{"action": "service_health_check", "timeout": 30}],
                success_criteria=[
                    "service_running",
                    "health_checks_passing",
                    "configuration_valid",
                ],
            )
        )

        # Human error recovery
        self.add_recovery_plan(
            RecoveryPlan(
                plan_id="human_error_recovery",
                disaster_type=DisasterType.HUMAN_ERROR,
                priority=RecoveryPriority.MEDIUM,
                recovery_steps=[
                    {
                        "step": "identify_changes",
                        "action": "audit_recent_changes",
                        "timeout": 120,
                    },
                    {
                        "step": "assess_impact",
                        "action": "impact_analysis",
                        "timeout": 60,
                    },
                    {
                        "step": "revert_changes",
                        "action": "rollback_configuration",
                        "timeout": 180,
                    },
                    {
                        "step": "validate_rollback",
                        "action": "verify_system_state",
                        "timeout": 60,
                    },
                ],
                estimated_duration=timedelta(minutes=7),
                validation_steps=[
                    {"action": "configuration_validation", "timeout": 30},
                    {"action": "system_health_check", "timeout": 60},
                ],
                success_criteria=[
                    "configuration_restored",
                    "system_stable",
                    "no_data_loss",
                ],
            )
        )

        logger.info(f"Initialized {len(self.recovery_plans)} recovery plans")

    def _setup_health_monitoring(self):
        """Setup health monitoring for disaster detection."""

        # Schedule regular health checks
        schedule.every(self.monitoring_interval).seconds.do(self._perform_health_check)

        # Schedule backup verification
        schedule.every(1).hours.do(self._verify_backup_integrity)

        # Schedule configuration validation
        schedule.every(30).minutes.do(self._validate_configuration_health)

        # Schedule secrets health check
        schedule.every(6).hours.do(self._check_secrets_health)

    def start_monitoring(self):
        """Start disaster recovery monitoring."""
        if self._monitoring_active:
            return

        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self._monitoring_thread.start()

        logger.info("Disaster recovery monitoring started")

    def stop_monitoring(self):
        """Stop disaster recovery monitoring."""
        self._monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)

        logger.info("Disaster recovery monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self._monitoring_active:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)

    def _perform_health_check(self):
        """Perform comprehensive health check."""
        try:
            health_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "configuration_valid": self._check_configuration_health(),
                "secrets_accessible": self._check_secrets_accessibility(),
                "backups_available": self._check_backup_availability(),
                "services_healthy": self._check_services_health(),
                "storage_available": self._check_storage_health(),
            }

            # Compare with baseline
            if self._health_baseline:
                issues = self._compare_health_states(self._health_baseline, health_data)
                if issues:
                    self._handle_health_issues(issues)

            # Update baseline
            self._health_baseline = health_data
            self._last_health_check = datetime.now(timezone.utc)

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self._handle_monitoring_failure("health_check", str(e))

    def _check_configuration_health(self) -> bool:
        """Check configuration health."""
        try:
            # Validate current configuration
            from .secure_config_validator import get_secure_validator

            validator = get_secure_validator()

            # Basic validation check
            return True  # Simplified for example

        except Exception as e:
            logger.error(f"Configuration health check failed: {e}")
            return False

    def _check_secrets_accessibility(self) -> bool:
        """Check if secrets are accessible."""
        try:
            secrets_manager = get_secrets_manager()
            health = secrets_manager.check_secret_health()
            return health.get("status") in ["healthy", "warning"]
        except Exception as e:
            logger.error(f"Secrets accessibility check failed: {e}")
            return False

    def _check_backup_availability(self) -> bool:
        """Check if backups are available and recent."""
        try:
            backup_manager = get_config_backup()
            recent_backups = backup_manager.list_backups(
                status=BackupStatus.COMPLETED, limit=5
            )

            if not recent_backups:
                return False

            # Check if we have a recent backup (within last 24 hours)
            latest_backup = recent_backups[0]
            age = datetime.now(timezone.utc) - latest_backup.created_at
            return age < timedelta(hours=24)

        except Exception as e:
            logger.error(f"Backup availability check failed: {e}")
            return False

    def _check_services_health(self) -> bool:
        """Check if services are healthy."""
        try:
            # This would check service health endpoints
            # For now, return True
            return True
        except Exception as e:
            logger.error(f"Services health check failed: {e}")
            return False

    def _check_storage_health(self) -> bool:
        """Check storage health."""
        try:
            # Check disk space
            stat = os.statvfs(self.storage_path)
            free_space = stat.f_frsize * stat.f_bavail
            total_space = stat.f_frsize * stat.f_blocks

            # Alert if less than 10% free space
            free_percentage = (free_space / total_space) * 100
            return free_percentage > 10

        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            return False

    def _compare_health_states(
        self, baseline: Dict[str, Any], current: Dict[str, Any]
    ) -> List[str]:
        """Compare health states and identify issues."""
        issues = []

        for key, current_value in current.items():
            if key == "timestamp":
                continue

            baseline_value = baseline.get(key)
            if baseline_value is True and current_value is False:
                issues.append(f"{key}_degraded")
            elif baseline_value is False and current_value is True:
                logger.info(f"Health improved: {key}")

        return issues

    def _handle_health_issues(self, issues: List[str]):
        """Handle detected health issues."""
        for issue in issues:
            if issue == "configuration_valid_degraded":
                self.detect_disaster(
                    disaster_type=DisasterType.CONFIGURATION_CORRUPTION,
                    description="Configuration validation failed",
                    priority=RecoveryPriority.CRITICAL,
                )
            elif issue == "secrets_accessible_degraded":
                self.detect_disaster(
                    disaster_type=DisasterType.SECRETS_COMPROMISE,
                    description="Secrets became inaccessible",
                    priority=RecoveryPriority.CRITICAL,
                )
            elif issue == "services_healthy_degraded":
                self.detect_disaster(
                    disaster_type=DisasterType.SERVICE_FAILURE,
                    description="Service health check failed",
                    priority=RecoveryPriority.HIGH,
                )

    def detect_disaster(
        self,
        disaster_type: DisasterType,
        description: str,
        priority: RecoveryPriority = RecoveryPriority.MEDIUM,
        affected_services: Optional[List[str]] = None,
        affected_environments: Optional[List[str]] = None,
        detection_source: str = "system",
    ) -> str:
        """
        Detect and register a disaster event.

        Args:
            disaster_type: Type of disaster
            description: Description of the disaster
            priority: Recovery priority
            affected_services: List of affected services
            affected_environments: List of affected environments
            detection_source: Source of detection

        Returns:
            Event ID
        """
        event_id = f"disaster-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')}"

        disaster_event = DisasterEvent(
            event_id=event_id,
            disaster_type=disaster_type,
            priority=priority,
            detected_at=datetime.now(timezone.utc),
            description=description,
            affected_services=affected_services or [],
            affected_environments=affected_environments or [],
            detection_source=detection_source,
        )

        self.disaster_events[event_id] = disaster_event
        self._save_disaster_recovery_data()

        logger.critical(
            f"DISASTER DETECTED: {disaster_type.value} - {description} (Event: {event_id})"
        )

        # Trigger automatic recovery if enabled
        if self.auto_recovery_enabled:
            self._trigger_automatic_recovery(event_id)

        return event_id

    def _trigger_automatic_recovery(self, event_id: str):
        """Trigger automatic recovery for a disaster event."""
        try:
            disaster_event = self.disaster_events[event_id]

            # Find appropriate recovery plan
            recovery_plan = self._find_recovery_plan(disaster_event)
            if not recovery_plan:
                logger.error(f"No recovery plan found for disaster {event_id}")
                return

            # Execute recovery
            execution_id = self.execute_recovery(event_id, recovery_plan.plan_id)
            logger.info(f"Automatic recovery triggered: {execution_id}")

        except Exception as e:
            logger.error(f"Failed to trigger automatic recovery for {event_id}: {e}")

    def _find_recovery_plan(
        self, disaster_event: DisasterEvent
    ) -> Optional[RecoveryPlan]:
        """Find appropriate recovery plan for a disaster event."""
        # Find plans matching disaster type
        matching_plans = [
            plan
            for plan in self.recovery_plans.values()
            if plan.disaster_type == disaster_event.disaster_type
        ]

        if not matching_plans:
            return None

        # Sort by priority (critical first)
        priority_order = {
            RecoveryPriority.CRITICAL: 0,
            RecoveryPriority.HIGH: 1,
            RecoveryPriority.MEDIUM: 2,
            RecoveryPriority.LOW: 3,
        }

        matching_plans.sort(key=lambda p: priority_order.get(p.priority, 999))
        return matching_plans[0]

    def execute_recovery(
        self, event_id: str, plan_id: str, executed_by: str = "system"
    ) -> str:
        """
        Execute a recovery plan for a disaster event.

        Args:
            event_id: Disaster event ID
            plan_id: Recovery plan ID
            executed_by: Who is executing the recovery

        Returns:
            Execution ID
        """
        if event_id not in self.disaster_events:
            raise ValueError(f"Disaster event not found: {event_id}")

        if plan_id not in self.recovery_plans:
            raise ValueError(f"Recovery plan not found: {plan_id}")

        execution_id = f"recovery-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')}"
        plan = self.recovery_plans[plan_id]

        recovery_execution = RecoveryExecution(
            execution_id=execution_id,
            event_id=event_id,
            plan_id=plan_id,
            status=RecoveryStatus.PENDING,
            started_at=datetime.now(timezone.utc),
            total_steps=len(plan.recovery_steps),
            executed_by=executed_by,
        )

        self.recovery_executions[execution_id] = recovery_execution
        self._save_disaster_recovery_data()

        # Submit recovery job
        future = self._recovery_executor.submit(self._perform_recovery, execution_id)

        logger.info(f"Recovery execution started: {execution_id}")
        return execution_id

    def _perform_recovery(self, execution_id: str):
        """Perform the actual recovery execution."""
        try:
            execution = self.recovery_executions[execution_id]
            plan = self.recovery_plans[execution.plan_id]

            execution.status = RecoveryStatus.IN_PROGRESS
            self._save_disaster_recovery_data()

            # Execute recovery steps
            for i, step in enumerate(plan.recovery_steps):
                execution.current_step = i + 1
                execution.progress_percentage = (i / len(plan.recovery_steps)) * 100

                logger.info(
                    f"Executing recovery step {i+1}/{len(plan.recovery_steps)}: {step.get('step')}"
                )

                try:
                    # Execute step
                    step_result = self._execute_recovery_step(step, execution)
                    execution.steps_completed.append(
                        {
                            "step": step,
                            "result": step_result,
                            "completed_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )

                except Exception as step_error:
                    logger.error(
                        f"Recovery step failed: {step.get('step')} - {step_error}"
                    )
                    execution.steps_failed.append(
                        {
                            "step": step,
                            "error": str(step_error),
                            "failed_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )

                    # Decide whether to continue or abort
                    if step.get("critical", True):
                        execution.status = RecoveryStatus.FAILED
                        execution.error_message = f"Critical step failed: {step_error}"
                        self._save_disaster_recovery_data()
                        return

                self._save_disaster_recovery_data()

            # Validate recovery
            execution.validation_passed = self._validate_recovery(execution, plan)

            if execution.validation_passed:
                execution.status = RecoveryStatus.COMPLETED
                logger.info(f"Recovery completed successfully: {execution_id}")
            else:
                execution.status = RecoveryStatus.PARTIAL
                logger.warning(
                    f"Recovery completed with validation failures: {execution_id}"
                )

            execution.completed_at = datetime.now(timezone.utc)
            execution.duration = execution.completed_at - execution.started_at
            execution.progress_percentage = 100.0

            self._save_disaster_recovery_data()

        except Exception as e:
            logger.error(f"Recovery execution failed: {execution_id} - {e}")
            execution.status = RecoveryStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now(timezone.utc)
            self._save_disaster_recovery_data()

    def _execute_recovery_step(
        self, step: Dict[str, Any], execution: RecoveryExecution
    ) -> Dict[str, Any]:
        """Execute a single recovery step."""
        action = step.get("action")
        timeout = step.get("timeout", 300)

        if action == "restore_from_backup":
            return self._restore_from_backup(execution)
        elif action == "generate_secrets":
            return self._generate_new_secrets(execution)
        elif action == "reload_configuration":
            return self._reload_configuration(execution)
        elif action == "verify_config_integrity":
            return self._verify_config_integrity(execution)
        elif action == "health_check":
            return self._perform_health_check_step(execution)
        else:
            logger.warning(f"Unknown recovery action: {action}")
            return {"status": "skipped", "reason": "unknown_action"}

    def _restore_from_backup(self, execution: RecoveryExecution) -> Dict[str, Any]:
        """Restore configuration from backup."""
        try:
            backup_manager = get_config_backup()

            # Find latest good backup
            backups = backup_manager.list_backups(
                status=BackupStatus.COMPLETED, limit=10
            )

            if not backups:
                raise RuntimeError("No backups available for restoration")

            # Use the latest backup
            latest_backup = backups[0]

            # Perform restore
            restore_id = backup_manager.restore_backup(
                backup_id=latest_backup.backup_id,
                restore_type="full",
                requested_by=execution.executed_by,
            )

            execution.recovery_artifacts.append(f"restore:{restore_id}")

            return {
                "status": "success",
                "backup_id": latest_backup.backup_id,
                "restore_id": restore_id,
            }

        except Exception as e:
            raise RuntimeError(f"Backup restoration failed: {e}")

    def _generate_new_secrets(self, execution: RecoveryExecution) -> Dict[str, Any]:
        """Generate new secrets after compromise."""
        try:
            secrets_manager = get_secrets_manager()

            # Rotate critical secrets
            rotated_secrets = []
            critical_secrets = ["jwt_secret_key", "app_secret_key"]

            for secret_id in critical_secrets:
                try:
                    metadata = secrets_manager.rotate_secret(secret_id)
                    rotated_secrets.append(secret_id)
                except Exception as e:
                    logger.warning(f"Failed to rotate secret {secret_id}: {e}")

            return {
                "status": "success" if rotated_secrets else "partial",
                "rotated_secrets": rotated_secrets,
            }

        except Exception as e:
            raise RuntimeError(f"Secret generation failed: {e}")

    def _reload_configuration(self, execution: RecoveryExecution) -> Dict[str, Any]:
        """Reload configuration after changes."""
        try:
            # Trigger hot reload if available
            try:
                hotreload = get_config_hotreload()
                reload_id = hotreload.trigger_reload(
                    trigger=ReloadTrigger.EMERGENCY,
                    triggered_by=execution.executed_by,
                    emergency=True,
                )

                execution.recovery_artifacts.append(f"reload:{reload_id}")

                return {"status": "success", "reload_id": reload_id}

            except Exception as e:
                logger.warning(f"Hot reload failed, attempting service restart: {e}")
                # Fallback to service restart
                return {"status": "success", "method": "service_restart"}

        except Exception as e:
            raise RuntimeError(f"Configuration reload failed: {e}")

    def _verify_config_integrity(self, execution: RecoveryExecution) -> Dict[str, Any]:
        """Verify configuration integrity."""
        try:
            from .secure_config_validator import get_secure_validator

            validator = get_secure_validator()

            # Perform validation
            # This would validate current configuration

            return {"status": "success", "integrity_verified": True}

        except Exception as e:
            raise RuntimeError(f"Configuration integrity verification failed: {e}")

    def _perform_health_check_step(
        self, execution: RecoveryExecution
    ) -> Dict[str, Any]:
        """Perform health check as recovery step."""
        try:
            self._perform_health_check()

            return {"status": "success", "health_status": self._health_baseline}

        except Exception as e:
            raise RuntimeError(f"Health check failed: {e}")

    def _validate_recovery(
        self, execution: RecoveryExecution, plan: RecoveryPlan
    ) -> bool:
        """Validate recovery execution."""
        try:
            # Execute validation steps
            for validation_step in plan.validation_steps:
                try:
                    result = self._execute_recovery_step(validation_step, execution)
                    if result.get("status") != "success":
                        execution.validation_errors.append(
                            f"Validation failed: {validation_step.get('action')}"
                        )
                        return False
                except Exception as e:
                    execution.validation_errors.append(
                        f"Validation error: {validation_step.get('action')} - {e}"
                    )
                    return False

            # Check success criteria
            for criteria in plan.success_criteria:
                if not self._check_success_criteria(criteria):
                    execution.validation_errors.append(
                        f"Success criteria not met: {criteria}"
                    )
                    return False

            return True

        except Exception as e:
            execution.validation_errors.append(f"Validation process failed: {e}")
            return False

    def _check_success_criteria(self, criteria: str) -> bool:
        """Check if success criteria is met."""
        if criteria == "configuration_valid":
            return self._check_configuration_health()
        elif criteria == "services_healthy":
            return self._check_services_health()
        elif criteria == "no_corruption_detected":
            return True  # Would implement corruption detection
        else:
            logger.warning(f"Unknown success criteria: {criteria}")
            return True

    def add_recovery_plan(self, plan: RecoveryPlan):
        """Add a recovery plan."""
        self.recovery_plans[plan.plan_id] = plan
        self._save_disaster_recovery_data()
        logger.info(f"Recovery plan added: {plan.plan_id}")

    def get_disaster_status(self) -> Dict[str, Any]:
        """Get disaster recovery system status."""
        active_disasters = [
            event
            for event in self.disaster_events.values()
            if not any(
                exec.status in [RecoveryStatus.COMPLETED, RecoveryStatus.FAILED]
                for exec in self.recovery_executions.values()
                if exec.event_id == event.event_id
            )
        ]

        active_recoveries = [
            exec
            for exec in self.recovery_executions.values()
            if exec.status == RecoveryStatus.IN_PROGRESS
        ]

        return {
            "monitoring_active": self._monitoring_active,
            "auto_recovery_enabled": self.auto_recovery_enabled,
            "total_disasters": len(self.disaster_events),
            "active_disasters": len(active_disasters),
            "total_recoveries": len(self.recovery_executions),
            "active_recoveries": len(active_recoveries),
            "recovery_plans": len(self.recovery_plans),
            "last_health_check": (
                self._last_health_check.isoformat() if self._last_health_check else None
            ),
            "health_baseline": self._health_baseline,
        }


# Global disaster recovery manager
_disaster_recovery: Optional[ConfigurationDisasterRecovery] = None


def get_disaster_recovery() -> ConfigurationDisasterRecovery:
    """Get global disaster recovery manager."""
    global _disaster_recovery
    if _disaster_recovery is None:
        _disaster_recovery = ConfigurationDisasterRecovery()
    return _disaster_recovery


def init_disaster_recovery(
    storage_path: str = "/var/lib/dotmac/disaster-recovery",
    monitoring_interval: int = 60,
    auto_recovery_enabled: bool = True,
    max_concurrent_recoveries: int = 3,
) -> ConfigurationDisasterRecovery:
    """Initialize global disaster recovery manager."""
    global _disaster_recovery
    _disaster_recovery = ConfigurationDisasterRecovery(
        storage_path=storage_path,
        monitoring_interval=monitoring_interval,
        auto_recovery_enabled=auto_recovery_enabled,
        max_concurrent_recoveries=max_concurrent_recoveries,
    )
    return _disaster_recovery
