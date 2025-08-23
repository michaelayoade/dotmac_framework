"""Ansible integration database models."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates

from dotmac_isp.shared.database.base import TenantModel
from dotmac_isp.shared.database.base import StatusMixin, AuditMixin


class PlaybookType(str, Enum):
    """Ansible playbook types."""

    DEVICE_PROVISIONING = "device_provisioning"
    CONFIGURATION_DEPLOYMENT = "configuration_deployment"
    FIRMWARE_UPDATE = "firmware_update"
    BACKUP_CONFIGURATION = "backup_configuration"
    HEALTH_CHECK = "health_check"
    SECURITY_AUDIT = "security_audit"
    TROUBLESHOOTING = "troubleshooting"
    MAINTENANCE = "maintenance"
    CUSTOM = "custom"


class ExecutionStatus(str, Enum):
    """Playbook execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class InventoryType(str, Enum):
    """Device inventory types."""

    STATIC = "static"
    DYNAMIC = "dynamic"
    DATABASE = "database"
    CUSTOM_SCRIPT = "custom_script"


class TaskStatus(str, Enum):
    """Automation task status."""

    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnsiblePlaybook(TenantModel, StatusMixin, AuditMixin):
    """Ansible playbook model."""

    __tablename__ = "ansible_playbooks"

    # Playbook identification
    name = Column(String(255), nullable=False, index=True)
    playbook_type = Column(SQLEnum(PlaybookType), nullable=False, index=True)
    version = Column(String(50), nullable=False, default="1.0")

    # Playbook content
    playbook_content = Column(Text, nullable=False)
    playbook_variables = Column(JSON, nullable=True)  # Default variables
    requirements = Column(JSON, nullable=True)  # Required Ansible collections/roles

    # Target configuration
    target_device_types = Column(JSON, nullable=True)  # List of supported device types
    target_vendors = Column(JSON, nullable=True)  # List of supported vendors
    target_os_versions = Column(JSON, nullable=True)  # Supported OS versions

    # Execution settings
    timeout_minutes = Column(Integer, default=30, nullable=False)
    max_parallel_hosts = Column(Integer, default=10, nullable=False)
    gather_facts = Column(Boolean, default=True, nullable=False)
    check_mode_enabled = Column(Boolean, default=False, nullable=False)

    # Validation and testing
    syntax_validated = Column(Boolean, default=False, nullable=False)
    last_tested = Column(DateTime(timezone=True), nullable=True)
    test_results = Column(JSON, nullable=True)

    # Usage tracking
    execution_count = Column(Integer, default=0, nullable=False)
    last_executed = Column(DateTime(timezone=True), nullable=True)
    success_rate = Column(Integer, default=0, nullable=False)  # Percentage

    # Additional metadata
    description = Column(Text, nullable=True)
    documentation = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    executions = relationship(
        "PlaybookExecution", back_populates="playbook", cascade="all, delete-orphan"
    )
    templates = relationship("ConfigurationTemplate", back_populates="playbook")

    def __repr__(self):
        return f"<AnsiblePlaybook(name='{self.name}', type='{self.playbook_type}')>"


class PlaybookExecution(TenantModel, AuditMixin):
    """Playbook execution tracking model."""

    __tablename__ = "playbook_executions"

    playbook_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ansible_playbooks.id"),
        nullable=False,
        index=True,
    )

    # Execution identification
    execution_id = Column(String(100), nullable=False, unique=True, index=True)
    job_name = Column(String(255), nullable=True)

    # Execution configuration
    inventory_content = Column(Text, nullable=False)  # Inventory used for execution
    extra_variables = Column(JSON, nullable=True)  # Runtime variables
    limit_hosts = Column(JSON, nullable=True)  # Limited host list
    tags = Column(JSON, nullable=True)  # Playbook tags to run
    skip_tags = Column(JSON, nullable=True)  # Playbook tags to skip

    # Execution status and timing
    status = Column(
        SQLEnum(ExecutionStatus),
        default=ExecutionStatus.PENDING,
        nullable=False,
        index=True,
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Results and logging
    stdout_log = Column(Text, nullable=True)  # Standard output
    stderr_log = Column(Text, nullable=True)  # Error output
    return_code = Column(Integer, nullable=True)

    # Task statistics
    total_hosts = Column(Integer, default=0, nullable=False)
    successful_hosts = Column(Integer, default=0, nullable=False)
    failed_hosts = Column(Integer, default=0, nullable=False)
    unreachable_hosts = Column(Integer, default=0, nullable=False)
    skipped_hosts = Column(Integer, default=0, nullable=False)

    # Detailed results
    host_results = Column(JSON, nullable=True)  # Per-host results
    task_results = Column(JSON, nullable=True)  # Per-task results
    changed_hosts = Column(JSON, nullable=True)  # List of hosts with changes

    # Additional metadata
    triggered_by = Column(
        String(100), nullable=True
    )  # manual, scheduled, webhook, etc.
    environment = Column(String(50), nullable=True)  # development, staging, production
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    playbook = relationship("AnsiblePlaybook", back_populates="executions")

    def __repr__(self):
        return f"<PlaybookExecution(id='{self.execution_id}', status='{self.status}', playbook='{self.playbook.name if self.playbook else 'Unknown'}')>"


class DeviceInventory(TenantModel, StatusMixin, AuditMixin):
    """Ansible inventory management model."""

    __tablename__ = "device_inventories"

    # Inventory identification
    name = Column(String(255), nullable=False, index=True)
    inventory_type = Column(SQLEnum(InventoryType), nullable=False, index=True)

    # Inventory configuration
    inventory_content = Column(Text, nullable=True)  # Static inventory content
    inventory_script = Column(Text, nullable=True)  # Dynamic inventory script
    update_interval = Column(Integer, nullable=True)  # Update interval in minutes

    # Group and host variables
    group_variables = Column(JSON, nullable=True)  # Global group variables
    host_variables = Column(JSON, nullable=True)  # Host-specific variables

    # Auto-discovery settings
    auto_discovery_enabled = Column(Boolean, default=False, nullable=False)
    discovery_filters = Column(JSON, nullable=True)  # Filters for auto-discovery

    # Validation and testing
    last_validated = Column(DateTime(timezone=True), nullable=True)
    validation_errors = Column(JSON, nullable=True)
    host_count = Column(Integer, default=0, nullable=False)
    reachable_hosts = Column(Integer, default=0, nullable=False)

    # Additional metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<DeviceInventory(name='{self.name}', type='{self.inventory_type}', hosts={self.host_count})>"


class ConfigurationTemplate(TenantModel, StatusMixin, AuditMixin):
    """Configuration template model for device automation."""

    __tablename__ = "configuration_templates"

    playbook_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ansible_playbooks.id"),
        nullable=True,
        index=True,
    )

    # Template identification
    name = Column(String(255), nullable=False, index=True)
    template_type = Column(
        String(50), nullable=False, index=True
    )  # jinja2, yaml, json, etc.
    device_type = Column(String(50), nullable=True, index=True)
    vendor = Column(String(100), nullable=True, index=True)

    # Template content
    template_content = Column(Text, nullable=False)
    default_variables = Column(JSON, nullable=True)
    required_variables = Column(JSON, nullable=True)  # List of required variable names

    # Validation settings
    validation_schema = Column(JSON, nullable=True)  # JSON schema for validation
    syntax_validated = Column(Boolean, default=False, nullable=False)
    last_validated = Column(DateTime(timezone=True), nullable=True)
    validation_errors = Column(JSON, nullable=True)

    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False)
    last_used = Column(DateTime(timezone=True), nullable=True)

    # Additional metadata
    description = Column(Text, nullable=True)
    documentation = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    playbook = relationship("AnsiblePlaybook", back_populates="templates")

    def __repr__(self):
        return (
            f"<ConfigurationTemplate(name='{self.name}', type='{self.template_type}')>"
        )


class AutomationTask(TenantModel, StatusMixin, AuditMixin):
    """Automation task scheduling and tracking model."""

    __tablename__ = "automation_tasks"

    playbook_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ansible_playbooks.id"),
        nullable=False,
        index=True,
    )
    inventory_id = Column(
        UUID(as_uuid=True),
        ForeignKey("device_inventories.id"),
        nullable=True,
        index=True,
    )

    # Task identification
    name = Column(String(255), nullable=False, index=True)
    task_type = Column(
        String(50), nullable=False, index=True
    )  # scheduled, triggered, manual

    # Scheduling configuration
    schedule_enabled = Column(Boolean, default=False, nullable=False)
    schedule_cron = Column(String(100), nullable=True)  # Cron expression
    schedule_timezone = Column(String(50), default="UTC", nullable=False)

    # Trigger configuration
    trigger_events = Column(
        JSON, nullable=True
    )  # List of events that trigger this task
    trigger_conditions = Column(JSON, nullable=True)  # Conditions for triggering

    # Execution settings
    max_concurrent_executions = Column(Integer, default=1, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    retry_delay_minutes = Column(Integer, default=5, nullable=False)

    # Task variables and configuration
    task_variables = Column(JSON, nullable=True)  # Task-specific variables
    notification_settings = Column(JSON, nullable=True)  # Notification configuration

    # Execution tracking
    last_execution_id = Column(String(100), nullable=True)
    last_executed = Column(DateTime(timezone=True), nullable=True)
    last_status = Column(SQLEnum(ExecutionStatus), nullable=True)
    execution_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)

    # Additional metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    playbook = relationship("AnsiblePlaybook")
    inventory = relationship("DeviceInventory")

    def __repr__(self):
        return f"<AutomationTask(name='{self.name}', type='{self.task_type}', status='{self.status}')>"
