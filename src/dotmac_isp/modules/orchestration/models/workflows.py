"""
Workflow Orchestration Models.

Database models for workflow executions, steps, and state management.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class WorkflowStepStatus(str, Enum):
    """Individual workflow step status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRY = "retry"


class WorkflowExecution(Base):
    """Workflow execution tracking."""

    __tablename__ = "orchestration_workflows"

    id = Column(Integer, primary_key=True)
    workflow_id = Column(String(255), unique=True, nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Workflow definition
    workflow_type = Column(String(100), nullable=False)
    workflow_name = Column(String(255), nullable=False)
    workflow_version = Column(String(50), default="1.0")

    # Execution context
    status = Column(String(20), nullable=False, default=WorkflowStatus.PENDING)
    triggered_by = Column(String(255))
    trigger_event = Column(String(255))

    # Target context
    customer_id = Column(String(255), index=True)
    service_id = Column(String(255), index=True)
    device_id = Column(String(255), index=True)
    order_id = Column(String(255), index=True)

    # Execution parameters
    input_parameters = Column(JSON)
    output_results = Column(JSON)
    execution_context = Column(JSON)

    # Progress tracking
    total_steps = Column(Integer, default=0)
    completed_steps = Column(Integer, default=0)
    failed_steps = Column(Integer, default=0)
    progress_percentage = Column(Integer, default=0)

    # Timing information
    scheduled_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    estimated_duration_minutes = Column(Integer)
    actual_duration_seconds = Column(Integer)

    # Error handling
    error_message = Column(Text)
    error_details = Column(JSON)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Operational metadata
    priority = Column(String(20), default="normal")  # low, normal, high, urgent
    tags = Column(JSON)
    metadata = Column(JSON)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    steps = relationship(
        "WorkflowStep", back_populates="workflow", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert workflow to dictionary representation."""
        return {
            "workflow_id": self.workflow_id,
            "tenant_id": self.tenant_id,
            "workflow_type": self.workflow_type,
            "workflow_name": self.workflow_name,
            "workflow_version": self.workflow_version,
            "status": self.status,
            "triggered_by": self.triggered_by,
            "trigger_event": self.trigger_event,
            "customer_id": self.customer_id,
            "service_id": self.service_id,
            "device_id": self.device_id,
            "order_id": self.order_id,
            "input_parameters": self.input_parameters,
            "output_results": self.output_results,
            "execution_context": self.execution_context,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "progress_percentage": self.progress_percentage,
            "scheduled_at": self.scheduled_at.isoformat()
            if self.scheduled_at
            else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "actual_duration_seconds": self.actual_duration_seconds,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "priority": self.priority,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkflowStep(Base):
    """Individual workflow step execution."""

    __tablename__ = "orchestration_workflow_steps"

    id = Column(Integer, primary_key=True)
    step_id = Column(String(255), unique=True, nullable=False, index=True)
    workflow_id = Column(
        String(255), ForeignKey("orchestration_workflows.workflow_id"), nullable=False
    )
    tenant_id = Column(String(255), nullable=False, index=True)

    # Step definition
    step_name = Column(String(255), nullable=False)
    step_type = Column(String(100), nullable=False)
    step_order = Column(Integer, nullable=False)

    # Dependencies
    depends_on_steps = Column(JSON)  # List of step IDs this step depends on
    parallel_group = Column(String(100))  # Steps that can run in parallel

    # Execution details
    status = Column(String(20), nullable=False, default=WorkflowStepStatus.PENDING)
    service_class = Column(String(255))  # Python class to execute
    service_method = Column(String(100))  # Method to call
    input_parameters = Column(JSON)
    output_results = Column(JSON)

    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)
    timeout_seconds = Column(Integer, default=300)  # 5 minutes default

    # Error handling
    error_message = Column(Text)
    error_details = Column(JSON)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=2)

    # Conditional execution
    condition_expression = Column(
        Text
    )  # Expression to evaluate for conditional execution
    skip_on_failure = Column(
        String(10), default="false"
    )  # Skip if previous steps failed

    # Rollback information
    rollback_method = Column(String(100))  # Method to call for rollback
    rollback_parameters = Column(JSON)
    rollback_completed = Column(String(10), default="false")

    # Metadata
    step_metadata = Column(JSON)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workflow = relationship("WorkflowExecution", back_populates="steps")

    def to_dict(self) -> dict[str, Any]:
        """Convert step to dictionary representation."""
        return {
            "step_id": self.step_id,
            "workflow_id": self.workflow_id,
            "tenant_id": self.tenant_id,
            "step_name": self.step_name,
            "step_type": self.step_type,
            "step_order": self.step_order,
            "depends_on_steps": self.depends_on_steps,
            "parallel_group": self.parallel_group,
            "status": self.status,
            "service_class": self.service_class,
            "service_method": self.service_method,
            "input_parameters": self.input_parameters,
            "output_results": self.output_results,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "duration_seconds": self.duration_seconds,
            "timeout_seconds": self.timeout_seconds,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "condition_expression": self.condition_expression,
            "skip_on_failure": self.skip_on_failure,
            "rollback_method": self.rollback_method,
            "rollback_parameters": self.rollback_parameters,
            "rollback_completed": self.rollback_completed,
            "step_metadata": self.step_metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkflowTemplate(Base):
    """Workflow template definitions."""

    __tablename__ = "orchestration_workflow_templates"

    id = Column(Integer, primary_key=True)
    template_id = Column(String(255), unique=True, nullable=False)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Template definition
    template_name = Column(String(255), nullable=False)
    template_version = Column(String(50), default="1.0")
    workflow_type = Column(String(100), nullable=False)
    description = Column(Text)

    # Template configuration
    is_active = Column(String(10), default="true")
    is_system_template = Column(String(10), default="false")
    category = Column(String(100))

    # Step definitions
    step_definitions = Column(JSON)  # Complete step configuration
    parameter_schema = Column(JSON)  # Input parameter validation schema
    default_parameters = Column(JSON)  # Default parameter values

    # Execution settings
    estimated_duration_minutes = Column(Integer)
    max_concurrent_executions = Column(Integer, default=1)
    requires_approval = Column(String(10), default="false")

    # Metadata
    tags = Column(JSON)
    created_by = Column(String(255))
    template_metadata = Column(JSON)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
