"""
Idempotency Framework

Provides idempotent operation management to ensure operations can be safely
retried without side effects across distributed services.
"""

import hashlib
import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Generic, Optional, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

from .exceptions import ErrorContext, IdempotencyError

T = TypeVar("T")
Base = declarative_base()


class OperationStatus(Enum):
    """Status of idempotent operations"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class IdempotencyKey(BaseModel):
    """Idempotency key with metadata"""

    key: str = Field(..., min_length=1, max_length=255)
    operation_type: str = Field(..., min_length=1, max_length=100)
    tenant_id: str = Field(..., min_length=1, max_length=100)
    user_id: Optional[str] = Field(None, max_length=100)
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    ttl_seconds: int = Field(
        default=3600, gt=0, le=86400
    )  # 1 hour default, max 24 hours

    @classmethod
    def generate(
        cls,
        operation_type: str,
        tenant_id: str,
        operation_data: dict[str, Any],
        user_id: Optional[str] = None,
        ttl_seconds: int = 3600,
    ) -> "IdempotencyKey":
        """Generate idempotency key from operation data"""

        # Create deterministic key from operation data
        key_data = {
            "operation_type": operation_type,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "data": operation_data,
        }

        # Sort and serialize for consistent hashing
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()

        return cls(
            key=f"{operation_type}:{tenant_id}:{key_hash[:16]}",
            operation_type=operation_type,
            tenant_id=tenant_id,
            user_id=user_id,
            ttl_seconds=ttl_seconds,
        )

    def __str__(self) -> str:
        return self.key


class IdempotentOperationRecord(Base):
    """Database model for idempotent operation tracking"""

    __tablename__ = "idempotent_operations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    idempotency_key = Column(String(255), unique=True, nullable=False, index=True)
    operation_type = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=True)
    correlation_id = Column(String(100), nullable=False, index=True)

    # Operation tracking
    status = Column(
        String(20), nullable=False, default=OperationStatus.PENDING.value, index=True
    )
    attempt_count = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)

    # Operation data and results
    operation_data = Column(JSON, nullable=True)
    result_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)

    # Metadata
    metadata = Column(JSON, default={}, nullable=False)


@dataclass
class OperationResult(Generic[T]):
    """Result of an idempotent operation"""

    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    status: OperationStatus = OperationStatus.COMPLETED
    attempt_count: int = 1
    execution_time_ms: int = 0
    from_cache: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "status": self.status.value,
            "attempt_count": self.attempt_count,
            "execution_time_ms": self.execution_time_ms,
            "from_cache": self.from_cache,
            "metadata": self.metadata,
        }


class IdempotentOperation(ABC, Generic[T]):
    """Abstract base class for idempotent operations"""

    def __init__(
        self,
        operation_type: str,
        max_attempts: int = 3,
        timeout_seconds: int = 300,
        ttl_seconds: int = 3600,
    ):
        self.operation_type = operation_type
        self.max_attempts = max_attempts
        self.timeout_seconds = timeout_seconds
        self.ttl_seconds = ttl_seconds

    @abstractmethod
    async def execute(
        self, operation_data: dict[str, Any], context: Optional[dict[str, Any]] = None
    ) -> T:
        """Execute the actual operation logic"""
        pass

    @abstractmethod
    def validate_operation_data(self, operation_data: dict[str, Any]) -> None:
        """Validate operation data before execution"""
        pass

    def should_retry(self, error: Exception, attempt_count: int) -> bool:
        """Determine if operation should be retried"""
        if attempt_count >= self.max_attempts:
            return False

        # Don't retry validation errors or business logic errors
        from .exceptions import BusinessLogicError

        if isinstance(error, (ValueError, TypeError, BusinessLogicError)):
            return False

        return True

    def get_retry_delay(self, attempt_count: int) -> float:
        """Calculate retry delay with exponential backoff"""
        base_delay = 1.0  # 1 second
        max_delay = 30.0  # 30 seconds

        delay = base_delay * (2 ** (attempt_count - 1))
        return min(delay, max_delay)


class IdempotencyManager:
    """Manager for idempotent operations with database persistence"""

    def __init__(self, db_session_factory: Callable[[], Session]):
        self.db_session_factory = db_session_factory
        self._operation_registry: dict[str, type] = {}

    def register_operation(self, operation_type: str, operation_class: type) -> None:
        """Register an operation type"""
        self._operation_registry[operation_type] = operation_class

    async def execute_idempotent(
        self,
        idempotency_key: IdempotencyKey,
        operation_data: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
    ) -> OperationResult:
        """Execute operation idempotently"""

        context = context or {}
        start_time = datetime.utcnow()

        # Get operation class
        operation_class = self._operation_registry.get(idempotency_key.operation_type)
        if not operation_class:
            raise ValueError(
                f"Unknown operation type: {idempotency_key.operation_type}"
            )

        with self.db_session_factory() as db:
            try:
                # Check for existing operation
                existing_op = self._get_operation_record(db, idempotency_key.key)

                if existing_op:
                    return await self._handle_existing_operation(
                        db, existing_op, operation_data, context, start_time
                    )

                # Create new operation record
                operation_record = self._create_operation_record(
                    db, idempotency_key, operation_data, context
                )

                # Execute operation
                return await self._execute_new_operation(
                    db,
                    operation_record,
                    operation_class,
                    operation_data,
                    context,
                    start_time,
                )

            except Exception as e:
                # Update operation record with failure
                if "operation_record" in locals():
                    self._update_operation_failure(db, operation_record, str(e))

                error_context = ErrorContext(
                    operation=idempotency_key.operation_type,
                    resource_type="idempotent_operation",
                    resource_id=idempotency_key.key,
                    tenant_id=idempotency_key.tenant_id,
                    user_id=idempotency_key.user_id,
                    correlation_id=idempotency_key.correlation_id,
                )

                raise IdempotencyError(
                    message=f"Idempotent operation failed: {str(e)}",
                    idempotency_key=idempotency_key.key,
                    operation=idempotency_key.operation_type,
                    conflict_reason="execution_failure",
                    context=error_context,
                ) from e

    def _get_operation_record(
        self, db: Session, idempotency_key: str
    ) -> Optional[IdempotentOperationRecord]:
        """Get existing operation record"""
        return (
            db.query(IdempotentOperationRecord)
            .filter(IdempotentOperationRecord.idempotency_key == idempotency_key)
            .first()
        )

    def _create_operation_record(
        self,
        db: Session,
        idempotency_key: IdempotencyKey,
        operation_data: dict[str, Any],
        context: dict[str, Any],
    ) -> IdempotentOperationRecord:
        """Create new operation record"""

        expires_at = datetime.utcnow() + timedelta(seconds=idempotency_key.ttl_seconds)

        record = IdempotentOperationRecord(
            idempotency_key=idempotency_key.key,
            operation_type=idempotency_key.operation_type,
            tenant_id=idempotency_key.tenant_id,
            user_id=idempotency_key.user_id,
            correlation_id=idempotency_key.correlation_id,
            operation_data=operation_data,
            expires_at=expires_at,
            metadata=context,
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        return record

    async def _execute_new_operation(
        self,
        db: Session,
        operation_record: IdempotentOperationRecord,
        operation_class: type,
        operation_data: dict[str, Any],
        context: dict[str, Any],
        start_time: datetime,
    ) -> OperationResult:
        """Execute new operation"""

        operation = operation_class()

        try:
            # Validate operation data
            operation.validate_operation_data(operation_data)

            # Mark as in progress
            operation_record.status = OperationStatus.IN_PROGRESS.value
            operation_record.started_at = datetime.utcnow()
            operation_record.attempt_count += 1
            db.commit()

            # Execute operation
            result = await operation.execute(operation_data, context)

            # Mark as completed
            execution_time = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )

            operation_record.status = OperationStatus.COMPLETED.value
            operation_record.completed_at = datetime.utcnow()
            operation_record.result_data = {"result": result} if result else {}
            db.commit()

            return OperationResult(
                success=True,
                data=result,
                status=OperationStatus.COMPLETED,
                attempt_count=operation_record.attempt_count,
                execution_time_ms=execution_time,
                from_cache=False,
            )

        except Exception as e:
            # Handle failure
            operation_record.status = OperationStatus.FAILED.value
            operation_record.error_message = str(e)
            db.commit()

            return OperationResult(
                success=False,
                error=str(e),
                status=OperationStatus.FAILED,
                attempt_count=operation_record.attempt_count,
                execution_time_ms=int(
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                ),
                from_cache=False,
            )

    async def _handle_existing_operation(
        self,
        db: Session,
        existing_op: IdempotentOperationRecord,
        operation_data: dict[str, Any],
        context: dict[str, Any],
        start_time: datetime,
    ) -> OperationResult:
        """Handle existing operation based on its status"""

        execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Check if operation has expired
        if datetime.utcnow() > existing_op.expires_at:
            error_context = ErrorContext(
                operation=existing_op.operation_type,
                resource_type="idempotent_operation",
                resource_id=existing_op.idempotency_key,
                tenant_id=existing_op.tenant_id,
                user_id=existing_op.user_id,
                correlation_id=existing_op.correlation_id,
            )

            raise IdempotencyError(
                message="Operation has expired",
                idempotency_key=existing_op.idempotency_key,
                operation=existing_op.operation_type,
                conflict_reason="operation_expired",
                context=error_context,
            )

        if existing_op.status == OperationStatus.COMPLETED.value:
            # Return cached result
            return OperationResult(
                success=True,
                data=existing_op.result_data.get("result")
                if existing_op.result_data
                else None,
                status=OperationStatus.COMPLETED,
                attempt_count=existing_op.attempt_count,
                execution_time_ms=execution_time,
                from_cache=True,
            )

        elif existing_op.status == OperationStatus.FAILED.value:
            # Check if we can retry
            if existing_op.attempt_count < existing_op.max_attempts:
                # Retry the operation
                operation_class = self._operation_registry[existing_op.operation_type]
                return await self._retry_operation(
                    db,
                    existing_op,
                    operation_class,
                    operation_data,
                    context,
                    start_time,
                )
            else:
                # Max attempts reached, return failure
                return OperationResult(
                    success=False,
                    error=existing_op.error_message,
                    status=OperationStatus.FAILED,
                    attempt_count=existing_op.attempt_count,
                    execution_time_ms=execution_time,
                    from_cache=True,
                )

        elif existing_op.status == OperationStatus.IN_PROGRESS.value:
            # Check for timeout
            if existing_op.started_at:
                elapsed = (datetime.utcnow() - existing_op.started_at).total_seconds()
                if elapsed > 300:  # 5 minute timeout
                    existing_op.status = OperationStatus.TIMEOUT.value
                    db.commit()

                    return OperationResult(
                        success=False,
                        error="Operation timed out",
                        status=OperationStatus.TIMEOUT,
                        attempt_count=existing_op.attempt_count,
                        execution_time_ms=execution_time,
                        from_cache=True,
                    )

            # Operation still in progress
            error_context = ErrorContext(
                operation=existing_op.operation_type,
                resource_type="idempotent_operation",
                resource_id=existing_op.idempotency_key,
                tenant_id=existing_op.tenant_id,
                user_id=existing_op.user_id,
                correlation_id=existing_op.correlation_id,
            )

            raise IdempotencyError(
                message="Operation already in progress",
                idempotency_key=existing_op.idempotency_key,
                operation=existing_op.operation_type,
                conflict_reason="operation_in_progress",
                context=error_context,
            )

        else:
            # Unknown status
            return OperationResult(
                success=False,
                error=f"Unknown operation status: {existing_op.status}",
                status=OperationStatus.FAILED,
                attempt_count=existing_op.attempt_count,
                execution_time_ms=execution_time,
                from_cache=True,
            )

    async def _retry_operation(
        self,
        db: Session,
        operation_record: IdempotentOperationRecord,
        operation_class: type,
        operation_data: dict[str, Any],
        context: dict[str, Any],
        start_time: datetime,
    ) -> OperationResult:
        """Retry a failed operation"""

        operation = operation_class()

        # Update attempt count and status
        operation_record.attempt_count += 1
        operation_record.status = OperationStatus.IN_PROGRESS.value
        operation_record.started_at = datetime.utcnow()
        operation_record.error_message = None
        db.commit()

        try:
            # Execute operation
            result = await operation.execute(operation_data, context)

            # Mark as completed
            execution_time = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )

            operation_record.status = OperationStatus.COMPLETED.value
            operation_record.completed_at = datetime.utcnow()
            operation_record.result_data = {"result": result} if result else {}
            db.commit()

            return OperationResult(
                success=True,
                data=result,
                status=OperationStatus.COMPLETED,
                attempt_count=operation_record.attempt_count,
                execution_time_ms=execution_time,
                from_cache=False,
            )

        except Exception as e:
            # Handle retry failure
            operation_record.status = OperationStatus.FAILED.value
            operation_record.error_message = str(e)
            db.commit()

            return OperationResult(
                success=False,
                error=str(e),
                status=OperationStatus.FAILED,
                attempt_count=operation_record.attempt_count,
                execution_time_ms=int(
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                ),
                from_cache=False,
            )

    def _update_operation_failure(
        self,
        db: Session,
        operation_record: IdempotentOperationRecord,
        error_message: str,
    ) -> None:
        """Update operation record with failure"""
        try:
            operation_record.status = OperationStatus.FAILED.value
            operation_record.error_message = error_message
            db.commit()
        except Exception:
            # Ignore database errors during error handling
            pass

    def cleanup_expired_operations(self, db: Session) -> int:
        """Clean up expired operation records"""
        now = datetime.utcnow()

        expired_ops = db.query(IdempotentOperationRecord).filter(
            IdempotentOperationRecord.expires_at < now
        )

        count = expired_ops.count()
        expired_ops.delete(synchronize_session=False)
        db.commit()

        return count

    def get_operation_status(
        self, db: Session, idempotency_key: str
    ) -> Optional[dict[str, Any]]:
        """Get operation status by idempotency key"""

        operation = self._get_operation_record(db, idempotency_key)
        if not operation:
            return None

        return {
            "idempotency_key": operation.idempotency_key,
            "operation_type": operation.operation_type,
            "status": operation.status,
            "attempt_count": operation.attempt_count,
            "max_attempts": operation.max_attempts,
            "created_at": operation.created_at.isoformat(),
            "updated_at": operation.updated_at.isoformat(),
            "started_at": operation.started_at.isoformat()
            if operation.started_at
            else None,
            "completed_at": operation.completed_at.isoformat()
            if operation.completed_at
            else None,
            "expires_at": operation.expires_at.isoformat(),
            "error_message": operation.error_message,
            "has_result": bool(operation.result_data),
        }
