"""
Core models and data classes for background operations, idempotency, and saga workflows.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class OperationStatus(str, Enum):
    """Status of an operation or idempotency key."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"


class SagaStepStatus(str, Enum):
    """Status of an individual saga step."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    SKIPPED = "skipped"


@dataclass
class IdempotencyKey:
    """
    Represents an idempotency key for ensuring operations run only once.
    
    This is used to prevent duplicate operations when clients retry requests
    or when network issues cause multiple submissions.
    """
    key: str
    tenant_id: str
    user_id: Optional[str]
    operation_type: str
    created_at: datetime
    expires_at: datetime
    status: OperationStatus = OperationStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Ensure timestamps have timezone info."""
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
        if self.expires_at.tzinfo is None:
            self.expires_at = self.expires_at.replace(tzinfo=timezone.utc)
    
    def is_expired(self) -> bool:
        """Check if this idempotency key has expired."""
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_completed(self) -> bool:
        """Check if the operation is completed."""
        return self.status == OperationStatus.COMPLETED
    
    def is_failed(self) -> bool:
        """Check if the operation has failed."""
        return self.status == OperationStatus.FAILED
    
    def is_in_progress(self) -> bool:
        """Check if the operation is currently in progress."""
        return self.status == OperationStatus.IN_PROGRESS
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "key": self.key,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "operation_type": self.operation_type,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "status": self.status.value,
            "result": json.dumps(self.result) if self.result is not None else None,
            "error": self.error,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IdempotencyKey":
        """Create from dictionary from storage."""
        result = None
        if data.get("result"):
            try:
                result = json.loads(data["result"])
            except (json.JSONDecodeError, TypeError):
                result = data["result"]
        
        return cls(
            key=data["key"],
            tenant_id=data["tenant_id"],
            user_id=data.get("user_id"),
            operation_type=data["operation_type"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            status=OperationStatus(data["status"]),
            result=result,
            error=data.get("error"),
        )


@dataclass
class SagaStep:
    """
    Represents a single step in a saga workflow.
    
    Each step has an operation to perform and optionally a compensation
    operation to undo the work if the saga needs to be rolled back.
    """
    step_id: str
    name: str
    operation: str
    parameters: Dict[str, Any]
    compensation_operation: Optional[str] = None
    compensation_parameters: Optional[Dict[str, Any]] = None
    status: SagaStepStatus = SagaStepStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self) -> None:
        """Initialize default values and validate timestamps."""
        if not self.step_id:
            self.step_id = str(uuid4())
        
        if self.compensation_parameters is None:
            self.compensation_parameters = {}
        
        # Ensure timestamps have timezone info
        if self.started_at and self.started_at.tzinfo is None:
            self.started_at = self.started_at.replace(tzinfo=timezone.utc)
        if self.completed_at and self.completed_at.tzinfo is None:
            self.completed_at = self.completed_at.replace(tzinfo=timezone.utc)
    
    def can_retry(self) -> bool:
        """Check if this step can be retried."""
        return self.retry_count < self.max_retries
    
    def is_completed(self) -> bool:
        """Check if this step is completed successfully."""
        return self.status == SagaStepStatus.COMPLETED
    
    def is_failed(self) -> bool:
        """Check if this step has failed."""
        return self.status == SagaStepStatus.FAILED
    
    def can_compensate(self) -> bool:
        """Check if this step can be compensated."""
        return (
            self.compensation_operation is not None 
            and self.status == SagaStepStatus.COMPLETED
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "step_id": self.step_id,
            "name": self.name,
            "operation": self.operation,
            "parameters": self.parameters,
            "compensation_operation": self.compensation_operation,
            "compensation_parameters": self.compensation_parameters,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SagaStep":
        """Create from dictionary from storage."""
        started_at = None
        completed_at = None
        
        if data.get("started_at"):
            started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            completed_at = datetime.fromisoformat(data["completed_at"])
        
        return cls(
            step_id=data["step_id"],
            name=data["name"],
            operation=data["operation"],
            parameters=data["parameters"],
            compensation_operation=data.get("compensation_operation"),
            compensation_parameters=data.get("compensation_parameters", {}),
            status=SagaStepStatus(data["status"]),
            result=data.get("result"),
            error=data.get("error"),
            started_at=started_at,
            completed_at=completed_at,
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
        )


@dataclass 
class SagaWorkflow:
    """
    Represents a saga workflow - a sequence of steps that can be
    executed with compensation if any step fails.
    
    Sagas provide distributed transaction capabilities by ensuring
    that if any step fails, all previously completed steps are
    compensated (undone).
    """
    saga_id: str
    tenant_id: str
    workflow_type: str
    steps: List[SagaStep]
    status: OperationStatus = OperationStatus.PENDING
    current_step: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    idempotency_key: Optional[str] = None
    timeout_seconds: int = 7200  # 2 hours default
    
    def __post_init__(self) -> None:
        """Initialize default values and validate timestamps."""
        if not self.saga_id:
            self.saga_id = str(uuid4())
        
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc)
        if not self.updated_at:
            self.updated_at = self.created_at
            
        # Ensure timestamps have timezone info
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
        if self.updated_at.tzinfo is None:
            self.updated_at = self.updated_at.replace(tzinfo=timezone.utc)
    
    def get_current_step(self) -> Optional[SagaStep]:
        """Get the current step being executed."""
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None
    
    def advance_step(self) -> bool:
        """Advance to the next step. Returns True if advanced, False if at end."""
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self.updated_at = datetime.now(timezone.utc)
            return True
        return False
    
    def is_completed(self) -> bool:
        """Check if the saga is completed successfully."""
        return self.status == OperationStatus.COMPLETED
    
    def is_failed(self) -> bool:
        """Check if the saga has failed."""
        return self.status == OperationStatus.FAILED
    
    def needs_compensation(self) -> bool:
        """Check if the saga needs compensation."""
        return self.status in [OperationStatus.FAILED, OperationStatus.COMPENSATING]
    
    def get_completed_steps(self) -> List[SagaStep]:
        """Get all completed steps (for compensation)."""
        return [step for step in self.steps if step.is_completed()]
    
    def is_timed_out(self) -> bool:
        """Check if the saga has timed out."""
        if not self.created_at:
            return False
        
        elapsed = datetime.now(timezone.utc) - self.created_at
        return elapsed.total_seconds() > self.timeout_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "saga_id": self.saga_id,
            "tenant_id": self.tenant_id,
            "workflow_type": self.workflow_type,
            "steps": [step.to_dict() for step in self.steps],
            "status": self.status.value,
            "current_step": self.current_step,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "idempotency_key": self.idempotency_key,
            "timeout_seconds": self.timeout_seconds,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SagaWorkflow":
        """Create from dictionary from storage."""
        created_at = None
        updated_at = None
        
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])
        
        steps = [SagaStep.from_dict(step_data) for step_data in data.get("steps", [])]
        
        return cls(
            saga_id=data["saga_id"],
            tenant_id=data["tenant_id"],
            workflow_type=data["workflow_type"],
            steps=steps,
            status=OperationStatus(data.get("status", OperationStatus.PENDING)),
            current_step=data.get("current_step", 0),
            created_at=created_at,
            updated_at=updated_at,
            idempotency_key=data.get("idempotency_key"),
            timeout_seconds=data.get("timeout_seconds", 7200),
        )


@dataclass
class BackgroundOperation:
    """
    Represents a background operation that can be tracked and monitored.
    
    This provides a unified view of operations whether they're simple
    idempotent operations or complex saga workflows.
    """
    operation_id: str
    tenant_id: str
    user_id: Optional[str]
    operation_type: str
    status: OperationStatus
    created_at: datetime
    updated_at: datetime
    saga_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Ensure timestamps have timezone info."""
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
        if self.updated_at.tzinfo is None:
            self.updated_at = self.updated_at.replace(tzinfo=timezone.utc)
    
    def is_saga_operation(self) -> bool:
        """Check if this is a saga-based operation."""
        return self.saga_id is not None
    
    def is_idempotent_operation(self) -> bool:
        """Check if this is an idempotent operation."""
        return self.idempotency_key is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "operation_id": self.operation_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "operation_type": self.operation_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "saga_id": self.saga_id,
            "idempotency_key": self.idempotency_key,
            "result": self.result,
            "error": self.error,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BackgroundOperation":
        """Create from dictionary from storage."""
        return cls(
            operation_id=data["operation_id"],
            tenant_id=data["tenant_id"],
            user_id=data.get("user_id"),
            operation_type=data["operation_type"],
            status=OperationStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            saga_id=data.get("saga_id"),
            idempotency_key=data.get("idempotency_key"),
            result=data.get("result"),
            error=data.get("error"),
        )


@dataclass
class SagaHistoryEntry:
    """
    Represents a single entry in the saga execution history.
    
    This is used for auditing and debugging saga workflows.
    """
    timestamp: datetime
    step_id: str
    step_name: str
    status: SagaStepStatus
    error: Optional[str] = None
    retry_count: int = 0
    
    def __post_init__(self) -> None:
        """Ensure timestamp has timezone info."""
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "step_id": self.step_id,
            "step_name": self.step_name,
            "status": self.status.value,
            "error": self.error,
            "retry_count": self.retry_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SagaHistoryEntry":
        """Create from dictionary from storage."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            step_id=data["step_id"],
            step_name=data["step_name"],
            status=SagaStepStatus(data["status"]),
            error=data.get("error"),
            retry_count=data.get("retry_count", 0),
        )