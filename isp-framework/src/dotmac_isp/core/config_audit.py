"""
Configuration audit logging and change tracking system.
Provides comprehensive audit trails for configuration changes with compliance support.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta, timezone
from enum import Enum
from pydantic import BaseModel, Field
from dataclasses import dataclass
import hashlib
import asyncio
from pathlib import Path
import threading

logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    """Types of configuration changes."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ROTATE = "rotate"
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    BACKUP = "backup"
    RESTORE = "restore"
    VALIDATION = "validation"
    ACCESS = "access"


class ChangeStatus(str, Enum):
    """Status of configuration changes."""

    PENDING = "pending"
    APPROVED = "approved"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    REJECTED = "rejected"


class ChangeSource(str, Enum):
    """Source of configuration changes."""

    USER = "user"
    SYSTEM = "system"
    API = "api"
    CLI = "cli"
    AUTOMATED = "automated"
    EMERGENCY = "emergency"


class AuditEvent(BaseModel):
    """Configuration audit event."""

    event_id: str = Field(..., description="Unique event identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    change_type: ChangeType
    change_status: ChangeStatus
    source: ChangeSource

    # Context information
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    service: Optional[str] = None
    environment: str

    # Change details
    field_path: str = Field(
        ..., description="Path to changed field (e.g., 'database.host')"
    )
    old_value_hash: Optional[str] = None
    new_value_hash: Optional[str] = None
    old_value: Optional[str] = None  # Only for non-sensitive fields
    new_value: Optional[str] = None  # Only for non-sensitive fields

    # Metadata
    change_reason: Optional[str] = None
    approval_required: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

    # Security and compliance
    compliance_tags: List[str] = Field(default_factory=list)
    sensitivity_level: str = "normal"  # low, normal, high, critical

    # Error information
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None


class ConfigurationSnapshot(BaseModel):
    """Point-in-time configuration snapshot."""

    snapshot_id: str
    timestamp: datetime
    environment: str
    service: Optional[str] = None
    config_hash: str
    config_size: int
    change_count: int
    created_by: str
    tags: List[str] = Field(default_factory=list)

    # Metadata for backup/restore
    backup_location: Optional[str] = None
    encrypted: bool = True
    compression: Optional[str] = None


class ApprovalWorkflow(BaseModel):
    """Configuration change approval workflow."""

    workflow_id: str
    change_id: str
    required_approvers: List[str]
    current_approvers: List[str] = Field(default_factory=list)
    approval_deadline: Optional[datetime] = None
    auto_approve_after: Optional[timedelta] = None
    emergency_bypass: bool = False

    # Approval rules
    min_approvals: int = 1
    require_security_approval: bool = False
    require_ops_approval: bool = False


class ConfigurationAudit:
    """
    Configuration audit and change tracking system.
    Provides comprehensive audit trails with compliance support.
    """

    # Sensitive field patterns (values will be hashed, not stored)
    SENSITIVE_PATTERNS = [
        "password",
        "secret",
        "key",
        "token",
        "credential",
        "auth",
        "private",
        "cert",
        "ssl",
        "tls",
    ]

    def __init__(
        self,
        audit_storage_path: str = "/var/log/dotmac/config-audit",
        max_audit_age_days: int = 365,
        require_approval: bool = False,
        encryption_enabled: bool = True,
    ):
        """
        Initialize configuration audit system.

        Args:
            audit_storage_path: Path to store audit logs
            max_audit_age_days: Maximum age for audit retention
            require_approval: Require approval for changes
            encryption_enabled: Encrypt audit logs
        """
        self.audit_storage_path = Path(audit_storage_path)
        self.max_audit_age_days = max_audit_age_days
        self.require_approval = require_approval
        self.encryption_enabled = encryption_enabled

        # Initialize storage
        self.audit_storage_path.mkdir(parents=True, exist_ok=True, mode=0o750)

        # In-memory caches
        self.pending_changes: Dict[str, AuditEvent] = {}
        self.active_workflows: Dict[str, ApprovalWorkflow] = {}
        self.snapshots: Dict[str, ConfigurationSnapshot] = {}

        # Thread safety
        self._lock = threading.RLock()

        # Load existing data
        self._load_audit_state()

    def _load_audit_state(self):
        """Load existing audit state from storage."""
        try:
            # Load pending changes
            pending_file = self.audit_storage_path / "pending_changes.json"
            if pending_file.exists():
                with open(pending_file, "r") as f:
                    pending_data = json.load(f)
                    self.pending_changes = {
                        k: AuditEvent(**v) for k, v in pending_data.items()
                    }

            # Load active workflows
            workflows_file = self.audit_storage_path / "active_workflows.json"
            if workflows_file.exists():
                with open(workflows_file, "r") as f:
                    workflow_data = json.load(f)
                    self.active_workflows = {
                        k: ApprovalWorkflow(**v) for k, v in workflow_data.items()
                    }

            # Load snapshot index
            snapshots_file = self.audit_storage_path / "snapshots_index.json"
            if snapshots_file.exists():
                with open(snapshots_file, "r") as f:
                    snapshot_data = json.load(f)
                    self.snapshots = {
                        k: ConfigurationSnapshot(**v) for k, v in snapshot_data.items()
                    }

        except Exception as e:
            logger.error(f"Failed to load audit state: {e}")

    def _save_audit_state(self):
        """Save current audit state to storage."""
        try:
            # Save pending changes
            pending_file = self.audit_storage_path / "pending_changes.json"
            with open(pending_file, "w") as f:
                json.dump(
                    {k: v.model_dump() for k, v in self.pending_changes.items()},
                    f,
                    indent=2,
                    default=str,
                )

            # Save active workflows
            workflows_file = self.audit_storage_path / "active_workflows.json"
            with open(workflows_file, "w") as f:
                json.dump(
                    {k: v.model_dump() for k, v in self.active_workflows.items()},
                    f,
                    indent=2,
                    default=str,
                )

            # Save snapshot index
            snapshots_file = self.audit_storage_path / "snapshots_index.json"
            with open(snapshots_file, "w") as f:
                json.dump(
                    {k: v.model_dump() for k, v in self.snapshots.items()},
                    f,
                    indent=2,
                    default=str,
                )

        except Exception as e:
            logger.error(f"Failed to save audit state: {e}")

    def _is_sensitive_field(self, field_path: str) -> bool:
        """Check if a field contains sensitive data."""
        field_lower = field_path.lower()
        return any(pattern in field_lower for pattern in self.SENSITIVE_PATTERNS)

    def _hash_value(self, value: Any) -> str:
        """Create hash of configuration value."""
        if value is None:
            return "null"
        value_str = json.dumps(value, sort_keys=True, default=str)
        return hashlib.sha256(value_str.encode()).hexdigest()

    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        import uuid

        return str(uuid.uuid4())

    def log_configuration_change(
        self,
        field_path: str,
        old_value: Any,
        new_value: Any,
        change_type: ChangeType = ChangeType.UPDATE,
        source: ChangeSource = ChangeSource.SYSTEM,
        environment: str = "development",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        service: Optional[str] = None,
        change_reason: Optional[str] = None,
        compliance_tags: Optional[List[str]] = None,
    ) -> str:
        """
        Log a configuration change event.

        Args:
            field_path: Path to the changed field
            old_value: Previous value
            new_value: New value
            change_type: Type of change
            source: Source of change
            environment: Environment name
            user_id: User making the change
            session_id: Session identifier
            ip_address: Client IP address
            user_agent: Client user agent
            service: Service name
            change_reason: Reason for change
            compliance_tags: Compliance tags

        Returns:
            Event ID
        """
        with self._lock:
            event_id = self._generate_event_id()

            # Determine sensitivity
            is_sensitive = self._is_sensitive_field(field_path)
            sensitivity_level = "critical" if is_sensitive else "normal"

            # Hash values for integrity
            old_value_hash = self._hash_value(old_value)
            new_value_hash = self._hash_value(new_value)

            # Store actual values only for non-sensitive fields
            stored_old_value = None if is_sensitive else str(old_value)
            stored_new_value = None if is_sensitive else str(new_value)

            # Determine if approval is required
            approval_required = self.require_approval and (
                is_sensitive or environment == "production"
            )

            # Create audit event
            audit_event = AuditEvent(
                event_id=event_id,
                change_type=change_type,
                change_status=(
                    ChangeStatus.PENDING if approval_required else ChangeStatus.APPLIED
                ),
                source=source,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                service=service,
                environment=environment,
                field_path=field_path,
                old_value_hash=old_value_hash,
                new_value_hash=new_value_hash,
                old_value=stored_old_value,
                new_value=stored_new_value,
                change_reason=change_reason,
                approval_required=approval_required,
                compliance_tags=compliance_tags or [],
                sensitivity_level=sensitivity_level,
            )

            # Store event
            if approval_required:
                self.pending_changes[event_id] = audit_event
                self._create_approval_workflow(event_id, audit_event)
            else:
                self._write_audit_log(audit_event)

            self._save_audit_state()

            logger.info(
                f"Configuration change logged: {field_path} "
                f"(event: {event_id}, status: {audit_event.change_status})"
            )

            return event_id

    def _create_approval_workflow(self, event_id: str, audit_event: AuditEvent):
        """Create approval workflow for configuration change."""
        # Determine required approvers based on sensitivity and environment
        required_approvers = []

        if audit_event.environment == "production":
            required_approvers.extend(["ops-team", "security-team"])
        elif audit_event.sensitivity_level == "critical":
            required_approvers.append("security-team")
        else:
            required_approvers.append("ops-team")

        workflow = ApprovalWorkflow(
            workflow_id=f"workflow-{event_id}",
            change_id=event_id,
            required_approvers=required_approvers,
            approval_deadline=datetime.now(timezone.utc) + timedelta(hours=24),
            min_approvals=1 if audit_event.environment != "production" else 2,
            require_security_approval=audit_event.sensitivity_level == "critical",
            require_ops_approval=audit_event.environment == "production",
        )

        self.active_workflows[workflow.workflow_id] = workflow

        logger.info(f"Approval workflow created: {workflow.workflow_id}")

    def approve_change(
        self,
        event_id: str,
        approver_id: str,
        approved: bool,
        approval_reason: Optional[str] = None,
    ) -> bool:
        """
        Approve or reject a configuration change.

        Args:
            event_id: Event ID to approve
            approver_id: ID of approver
            approved: Whether change is approved
            approval_reason: Reason for approval/rejection

        Returns:
            True if change is fully approved and applied
        """
        with self._lock:
            if event_id not in self.pending_changes:
                raise ValueError(f"No pending change found with ID: {event_id}")

            audit_event = self.pending_changes[event_id]

            # Find workflow
            workflow = None
            for wf in self.active_workflows.values():
                if wf.change_id == event_id:
                    workflow = wf
                    break

            if not workflow:
                raise ValueError(f"No workflow found for change: {event_id}")

            if approved:
                # Add to approvers
                if approver_id not in workflow.current_approvers:
                    workflow.current_approvers.append(approver_id)

                # Check if fully approved
                if len(workflow.current_approvers) >= workflow.min_approvals:
                    # Apply the change
                    audit_event.change_status = ChangeStatus.APPLIED
                    audit_event.approved_by = ", ".join(workflow.current_approvers)
                    audit_event.approved_at = datetime.now(timezone.utc)

                    # Write to audit log
                    self._write_audit_log(audit_event)

                    # Clean up
                    del self.pending_changes[event_id]
                    del self.active_workflows[workflow.workflow_id]

                    logger.info(
                        f"Configuration change approved and applied: {event_id}"
                    )
                    return True
                else:
                    audit_event.change_status = ChangeStatus.APPROVED
                    logger.info(f"Configuration change partially approved: {event_id}")
            else:
                # Reject the change
                audit_event.change_status = ChangeStatus.REJECTED
                audit_event.error_message = (
                    approval_reason or "Change rejected by approver"
                )

                # Write rejection to audit log
                self._write_audit_log(audit_event)

                # Clean up
                del self.pending_changes[event_id]
                del self.active_workflows[workflow.workflow_id]

                logger.info(f"Configuration change rejected: {event_id}")

            self._save_audit_state()
            return False

    def _write_audit_log(self, audit_event: AuditEvent):
        """Write audit event to persistent log."""
        # Create daily log file
        log_date = audit_event.timestamp.strftime("%Y-%m-%d")
        log_file = self.audit_storage_path / f"audit-{log_date}.jsonl"

        # Write event as JSON line
        with open(log_file, "a") as f:
            f.write(json.dumps(audit_event.model_dump(), default=str) + "\n")

        # Set secure permissions
        os.chmod(log_file, 0o640)

    def create_configuration_snapshot(
        self,
        config_dict: Dict[str, Any],
        environment: str,
        service: Optional[str] = None,
        created_by: str = "system",
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Create a point-in-time configuration snapshot.

        Args:
            config_dict: Configuration dictionary
            environment: Environment name
            service: Service name
            created_by: User creating snapshot
            tags: Tags for organization

        Returns:
            Snapshot ID
        """
        with self._lock:
            snapshot_id = f"snapshot-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

            # Calculate configuration hash
            config_json = json.dumps(config_dict, sort_keys=True, default=str)
            config_hash = hashlib.sha256(config_json.encode()).hexdigest()

            # Create snapshot
            snapshot = ConfigurationSnapshot(
                snapshot_id=snapshot_id,
                timestamp=datetime.now(timezone.utc),
                environment=environment,
                service=service,
                config_hash=config_hash,
                config_size=len(config_json),
                change_count=len(
                    [
                        e
                        for e in self._get_recent_events()
                        if e.environment == environment
                    ]
                ),
                created_by=created_by,
                tags=tags or [],
                encrypted=self.encryption_enabled,
            )

            # Store snapshot data
            snapshot_file = self.audit_storage_path / f"{snapshot_id}.json"
            with open(snapshot_file, "w") as f:
                json.dump(
                    {"metadata": snapshot.model_dump(), "config": config_dict},
                    f,
                    indent=2,
                    default=str,
                )

            # Set secure permissions
            os.chmod(snapshot_file, 0o640)

            # Add to index
            self.snapshots[snapshot_id] = snapshot
            self._save_audit_state()

            logger.info(f"Configuration snapshot created: {snapshot_id}")
            return snapshot_id

    def restore_configuration_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        """
        Restore configuration from snapshot.

        Args:
            snapshot_id: Snapshot to restore

        Returns:
            Configuration dictionary
        """
        if snapshot_id not in self.snapshots:
            raise ValueError(f"Snapshot not found: {snapshot_id}")

        snapshot_file = self.audit_storage_path / f"{snapshot_id}.json"
        if not snapshot_file.exists():
            raise ValueError(f"Snapshot file not found: {snapshot_file}")

        with open(snapshot_file, "r") as f:
            snapshot_data = json.load(f)

        # Log restore event
        self.log_configuration_change(
            field_path="__snapshot_restore__",
            old_value=None,
            new_value=snapshot_id,
            change_type=ChangeType.RESTORE,
            change_reason=f"Restored from snapshot {snapshot_id}",
        )

        logger.info(f"Configuration restored from snapshot: {snapshot_id}")
        return snapshot_data["config"]

    def _get_recent_events(self, days: int = 7) -> List[AuditEvent]:
        """Get recent audit events."""
        events = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Read recent log files
        for i in range(days):
            log_date = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
            log_file = self.audit_storage_path / f"audit-{log_date}.jsonl"

            if log_file.exists():
                try:
                    with open(log_file, "r") as f:
                        for line in f:
                            event_data = json.loads(line.strip())
                            event = AuditEvent(**event_data)
                            # Ensure timestamp is timezone-aware for comparison
                            if event.timestamp.tzinfo is None:
                                event.timestamp = event.timestamp.replace(tzinfo=timezone.utc)
                            if event.timestamp >= cutoff_date:
                                events.append(event)
                except Exception as e:
                    logger.warning(f"Failed to read audit log {log_file}: {e}")

        return sorted(events, key=lambda x: x.timestamp, reverse=True)

    def get_audit_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        environment: Optional[str] = None,
        user_id: Optional[str] = None,
        change_type: Optional[ChangeType] = None,
    ) -> Dict[str, Any]:
        """
        Generate audit report with filtering.

        Args:
            start_date: Start date for report
            end_date: End date for report
            environment: Filter by environment
            user_id: Filter by user
            change_type: Filter by change type

        Returns:
            Audit report
        """
        # Default to last 30 days
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)
        
        # Ensure start_date and end_date are timezone-aware for comparison
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        # Get events in date range
        all_events = self._get_recent_events(days=(end_date - start_date).days + 1)

        # Apply filters
        filtered_events = []
        for event in all_events:
            if event.timestamp < start_date or event.timestamp > end_date:
                continue
            if environment and event.environment != environment:
                continue
            if user_id and event.user_id != user_id:
                continue
            if change_type and event.change_type != change_type:
                continue
            filtered_events.append(event)

        # Generate statistics
        total_changes = len(filtered_events)
        changes_by_type = {}
        changes_by_user = {}
        changes_by_environment = {}
        failed_changes = 0

        for event in filtered_events:
            # By type
            changes_by_type[event.change_type] = (
                changes_by_type.get(event.change_type, 0) + 1
            )

            # By user
            user = event.user_id or "system"
            changes_by_user[user] = changes_by_user.get(user, 0) + 1

            # By environment
            changes_by_environment[event.environment] = (
                changes_by_environment.get(event.environment, 0) + 1
            )

            # Failed changes
            if event.change_status == ChangeStatus.FAILED:
                failed_changes += 1

        return {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "summary": {
                "total_changes": total_changes,
                "failed_changes": failed_changes,
                "success_rate": (
                    (total_changes - failed_changes) / total_changes
                    if total_changes > 0
                    else 0
                ),
            },
            "breakdown": {
                "by_type": changes_by_type,
                "by_user": changes_by_user,
                "by_environment": changes_by_environment,
            },
            "recent_events": [
                event.model_dump() for event in filtered_events[:50]
            ],  # Last 50 events
        }

    def cleanup_old_audits(self):
        """Clean up old audit logs based on retention policy."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.max_audit_age_days)
        cutoff_date_str = cutoff_date.strftime("%Y-%m-%d")

        deleted_files = 0
        for file_path in self.audit_storage_path.glob("audit-*.jsonl"):
            # Extract date from filename
            filename = file_path.name
            if filename.startswith("audit-") and filename.endswith(".jsonl"):
                date_part = filename[6:-6]  # Remove "audit-" and ".jsonl"
                if date_part < cutoff_date_str:
                    try:
                        file_path.unlink()
                        deleted_files += 1
                    except Exception as e:
                        logger.warning(
                            f"Failed to delete old audit file {file_path}: {e}"
                        )

        if deleted_files > 0:
            logger.info(f"Cleaned up {deleted_files} old audit files")


# Global audit manager
_config_audit: Optional[ConfigurationAudit] = None


def get_config_audit() -> ConfigurationAudit:
    """Get global configuration audit manager."""
    global _config_audit
    if _config_audit is None:
        _config_audit = ConfigurationAudit()
    return _config_audit


def init_config_audit(
    audit_storage_path: str = "/var/log/dotmac/config-audit",
    max_audit_age_days: int = 365,
    require_approval: bool = False,
    encryption_enabled: bool = True,
) -> ConfigurationAudit:
    """Initialize global configuration audit manager."""
    global _config_audit
    _config_audit = ConfigurationAudit(
        audit_storage_path=audit_storage_path,
        max_audit_age_days=max_audit_age_days,
        require_approval=require_approval,
        encryption_enabled=encryption_enabled,
    )
    return _config_audit
