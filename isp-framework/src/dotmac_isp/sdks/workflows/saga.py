"""
Saga SDK for implementing distributed transaction patterns and compensation logic.

This module provides comprehensive saga pattern capabilities including:
- Saga definition and execution
- Compensation logic management
- Transaction coordination
- Failure recovery and rollback
- Distributed transaction monitoring
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

import structlog
from pydantic import BaseModel, Field, field_validator

from ..contracts.common_schemas import (
    ExecutionContext,
    ExecutionStatus,
    OperationMetadata,
    RetryPolicy,
    TimeoutPolicy,
    ErrorInfo,
    ConfigDict
)

logger = structlog.get_logger(__name__)


class SagaStepType(str, Enum):
    """Saga step types."""

    TRANSACTION = "transaction"
    COMPENSATION = "compensation"
    VALIDATION = "validation"
    NOTIFICATION = "notification"


class SagaStatus(str, Enum):
    """Saga execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CompensationStrategy(str, Enum):
    """Compensation strategies."""

    REVERSE_ORDER = "reverse_order"
    PARALLEL = "parallel"
    CUSTOM = "custom"


class SagaStep(BaseModel):
    """Saga step definition."""

    id: str = Field(..., description="Step identifier")
    name: str = Field(..., description="Step name")
    step_type: SagaStepType = Field(..., description="Step type")
    description: Optional[str] = Field(None, description="Step description")

    # Execution configuration
    transaction_handler: Optional[str] = Field(None, description="Transaction handler")
    compensation_handler: Optional[str] = Field(
        None, description="Compensation handler"
    )
    validation_handler: Optional[str] = Field(None, description="Validation handler")

    # Input/Output mapping
    input_mapping: Dict[str, str] = Field(
        default_factory=dict, description="Input mapping"
    )
    output_mapping: Dict[str, str] = Field(
        default_factory=dict, description="Output mapping"
    )

    # Dependencies
    depends_on: List[str] = Field(default_factory=list, description="Step dependencies")

    # Policies
    retry_policy: Optional[RetryPolicy] = Field(None, description="Retry policy")
    timeout_policy: Optional[TimeoutPolicy] = Field(None, description="Timeout policy")

    # Compensation configuration
    compensatable: bool = Field(True, description="Whether step can be compensated")
    compensation_timeout: Optional[float] = Field(
        None, description="Compensation timeout"
    )

    # Step data
    step_data: Dict[str, Any] = Field(
        default_factory=dict, description="Step-specific data"
    )

    model_config = ConfigDict(extra="allow")

class SagaDefinition(BaseModel):
    """Saga definition with steps and compensation logic."""

    id: str = Field(..., description="Saga identifier")
    name: str = Field(..., description="Saga name")
    version: str = Field("1.0", description="Saga version")
    description: Optional[str] = Field(None, description="Saga description")

    # Steps configuration
    steps: List[SagaStep] = Field(..., description="Saga steps")
    compensation_strategy: CompensationStrategy = Field(
        CompensationStrategy.REVERSE_ORDER, description="Compensation strategy"
    )

    # Saga settings
    timeout_seconds: Optional[float] = Field(None, description="Overall saga timeout")
    max_retries: int = Field(3, ge=0, description="Maximum retry attempts")

    # Metadata
    tenant_id: str = Field(..., description="Tenant identifier")
    metadata: OperationMetadata = Field(default_factory=OperationMetadata)

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, v):
        """Validate Steps operation."""
        if not v:
            raise ValueError("Saga must have at least one step")

        step_ids = {step.id for step in v}

        # Validate dependencies
        for step in v:
            for dep in step.depends_on:
                if dep not in step_ids:
                    raise ValueError(
                        f"Step '{step.id}' depends on non-existent step '{dep}'"
                    )

        return v

    model_config = ConfigDict(extra="allow")

@dataclass
class SagaStepExecution:
    """Runtime execution state of a saga step."""

    step_id: str
    execution_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    transaction_result: Optional[Dict[str, Any]] = None
    compensation_result: Optional[Dict[str, Any]] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[ErrorInfo] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    compensated_at: Optional[datetime] = None
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_id": self.step_id,
            "execution_id": self.execution_id,
            "status": self.status.value,
            "transaction_result": self.transaction_result,
            "compensation_result": self.compensation_result,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error": self.error.model_dump() if self.error else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "compensated_at": (
                self.compensated_at.isoformat() if self.compensated_at else None
            ),
            "retry_count": self.retry_count,
        }


@dataclass
class SagaExecution:
    """Runtime execution state of a saga."""

    execution_id: str
    saga_id: str
    saga_version: str
    status: SagaStatus = SagaStatus.PENDING
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    context: Optional[ExecutionContext] = None
    step_executions: Dict[str, SagaStepExecution] = field(default_factory=dict)
    completed_steps: Set[str] = field(default_factory=set)
    failed_steps: Set[str] = field(default_factory=set)
    compensated_steps: Set[str] = field(default_factory=set)
    error: Optional[ErrorInfo] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    compensation_started_at: Optional[datetime] = None
    compensation_completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "saga_id": self.saga_id,
            "saga_version": self.saga_version,
            "status": self.status.value,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "context": self.context.model_dump() if self.context else None,
            "step_executions": {
                k: v.to_dict() for k, v in self.step_executions.items()
            },
            "completed_steps": list(self.completed_steps),
            "failed_steps": list(self.failed_steps),
            "compensated_steps": list(self.compensated_steps),
            "error": self.error.model_dump() if self.error else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "compensation_started_at": (
                self.compensation_started_at.isoformat()
                if self.compensation_started_at
                else None
            ),
            "compensation_completed_at": (
                self.compensation_completed_at.isoformat()
                if self.compensation_completed_at
                else None
            ),
        }


class SagaEngine:
    """Saga execution engine."""

    def __init__(self):
        """  Init   operation."""
        self.transaction_handlers: Dict[str, Callable] = {}
        self.compensation_handlers: Dict[str, Callable] = {}
        self.validation_handlers: Dict[str, Callable] = {}

    def register_transaction_handler(self, handler_name: str, handler: Callable):
        """Register a transaction handler."""
        self.transaction_handlers[handler_name] = handler

    def register_compensation_handler(self, handler_name: str, handler: Callable):
        """Register a compensation handler."""
        self.compensation_handlers[handler_name] = handler

    def register_validation_handler(self, handler_name: str, handler: Callable):
        """Register a validation handler."""
        self.validation_handlers[handler_name] = handler

    async def execute_transaction(  # noqa: C901
        self,
        step: SagaStep,
        step_execution: SagaStepExecution,
        context: ExecutionContext,
    ) -> bool:
        """Execute a transaction step."""
        try:
            step_execution.status = ExecutionStatus.RUNNING
            step_execution.started_at = datetime.now(timezone.utc)

            if step.step_type == SagaStepType.TRANSACTION:
                if not step.transaction_handler:
                    raise ValueError(f"Transaction step {step.id} missing handler")

                handler = self.transaction_handlers.get(step.transaction_handler)
                if not handler:
                    raise ValueError(
                        f"Transaction handler {step.transaction_handler} not registered"
                    )

                # Prepare input data
                input_data = self._prepare_input_data(step, context)
                step_execution.input_data = input_data

                # Execute with timeout
                timeout = None
                if step.timeout_policy and step.timeout_policy.execution_timeout:
                    timeout = step.timeout_policy.execution_timeout

                if timeout:
                    result = await asyncio.wait_for(
                        handler(input_data, context), timeout=timeout
                    )
                else:
                    result = await handler(input_data, context)

                # Store result
                step_execution.transaction_result = result
                step_execution.output_data = self._map_output_data(step, result)

                # Update context
                context.variables.update(step_execution.output_data)

            elif step.step_type == SagaStepType.VALIDATION:
                if step.validation_handler:
                    handler = self.validation_handlers.get(step.validation_handler)
                    if handler:
                        input_data = self._prepare_input_data(step, context)
                        result = await handler(input_data, context)
                        if not result:
                            raise ValueError("Validation failed")

            step_execution.status = ExecutionStatus.COMPLETED
            step_execution.completed_at = datetime.now(timezone.utc)

            logger.info(
                "Saga step executed successfully",
                step_id=step.id,
                execution_id=step_execution.execution_id,
            )

            return True

        except Exception as e:
            step_execution.status = ExecutionStatus.FAILED
            step_execution.completed_at = datetime.now(timezone.utc)
            step_execution.error = ErrorInfo(
                error_type=type(e).__name__,
                message=str(e),
                timestamp=datetime.now(timezone.utc),
            )

            logger.error(
                "Saga step execution failed",
                step_id=step.id,
                execution_id=step_execution.execution_id,
                error=str(e),
            )
            return False

    async def execute_compensation(
        self,
        step: SagaStep,
        step_execution: SagaStepExecution,
        context: ExecutionContext,
    ) -> bool:
        """Execute compensation for a step."""
        try:
            if not step.compensatable:
                logger.info(
                    "Step not compensatable, skipping",
                    step_id=step.id,
                    execution_id=step_execution.execution_id,
                )
                return True

            if not step.compensation_handler:
                logger.warning(
                    "No compensation handler for step",
                    step_id=step.id,
                    execution_id=step_execution.execution_id,
                )
                return True

            handler = self.compensation_handlers.get(step.compensation_handler)
            if not handler:
                raise ValueError(
                    f"Compensation handler {step.compensation_handler} not registered"
                )

            # Prepare compensation data
            compensation_data = {
                "transaction_result": step_execution.transaction_result,
                "step_data": step.step_data,
                "context_variables": context.variables,
            }

            # Execute with timeout
            timeout = step.compensation_timeout or 30.0

            result = await asyncio.wait_for(
                handler(compensation_data, context), timeout=timeout
            )

            step_execution.compensation_result = result
            step_execution.compensated_at = datetime.now(timezone.utc)

            logger.info(
                "Saga step compensated successfully",
                step_id=step.id,
                execution_id=step_execution.execution_id,
            )

            return True

        except Exception as e:
            logger.error(
                "Saga step compensation failed",
                step_id=step.id,
                execution_id=step_execution.execution_id,
                error=str(e),
            )
            return False

    def _prepare_input_data(
        self, step: SagaStep, context: ExecutionContext
    ) -> Dict[str, Any]:
        """Prepare input data for step execution."""
        input_data = step.step_data.model_copy()

        # Apply input mapping
        for target_field, source_field in step.input_mapping.items():
            if source_field in context.variables:
                input_data[target_field] = context.variables[source_field]

        return input_data

    def _map_output_data(self, step: SagaStep, result: Any) -> Dict[str, Any]:
        """Map step output data."""
        if not step.output_mapping:
            return result if isinstance(result, dict) else {"result": result}

        if not isinstance(result, dict):
            result = {"result": result}

        output_data = {}
        for target_field, source_field in step.output_mapping.items():
            if source_field in result:
                output_data[target_field] = result[source_field]

        return output_data


class SagaSDK:
    """SDK for saga pattern implementation and execution."""

    def __init__(self, tenant_id: str, storage_adapter=None):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self.storage_adapter = storage_adapter
        self.engine = SagaEngine()
        self.saga_definitions: Dict[str, SagaDefinition] = {}
        self.saga_executions: Dict[str, SagaExecution] = {}

        logger.info("SagaSDK initialized", tenant_id=tenant_id)

    async def create_saga(self, saga_def: SagaDefinition) -> str:
        """Create a new saga definition."""
        saga_def.tenant_id = self.tenant_id
        saga_def.metadata.updated_at = datetime.now(timezone.utc)

        self.saga_definitions[saga_def.id] = saga_def

        if self.storage_adapter:
            await self.storage_adapter.store_saga(saga_def)

        logger.info(
            "Saga created",
            saga_id=saga_def.id,
            tenant_id=self.tenant_id,
        )

        return saga_def.id

    async def execute_saga(
        self,
        saga_id: str,
        input_data: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
    ) -> str:
        """Start saga execution."""
        saga_def = self.saga_definitions.get(saga_id)
        if not saga_def:
            raise ValueError(f"Saga {saga_id} not found")

        execution_id = str(uuid.uuid4())

        if not context:
            context = ExecutionContext(
                execution_id=execution_id,
                tenant_id=self.tenant_id,
                variables=input_data.model_copy(),
            )
        else:
            context.execution_id = execution_id
            context.variables.update(input_data)

        saga_execution = SagaExecution(
            execution_id=execution_id,
            saga_id=saga_id,
            saga_version=saga_def.version,
            input_data=input_data,
            context=context,
            started_at=datetime.now(timezone.utc),
        )

        self.saga_executions[execution_id] = saga_execution

        # Start execution asynchronously
        asyncio.create_task(self._execute_saga_async(saga_def, saga_execution))

        logger.info(
            "Saga execution started",
            saga_id=saga_id,
            execution_id=execution_id,
            tenant_id=self.tenant_id,
        )

        return execution_id

    async def _execute_saga_async(  # noqa: C901
        self,
        saga_def: SagaDefinition,
        saga_execution: SagaExecution,
    ):
        """Execute saga asynchronously."""
        try:
            saga_execution.status = SagaStatus.RUNNING

            # Build dependency graph
            step_map = {step.id: step for step in saga_def.steps}

            # Execute steps in dependency order
            executed_steps = []
            remaining_steps = saga_def.steps.model_copy()

            while remaining_steps and saga_execution.status == SagaStatus.RUNNING:
                # Find steps ready to execute
                ready_steps = []
                for step in remaining_steps:
                    if all(
                        dep in saga_execution.completed_steps for dep in step.depends_on
                    ):
                        ready_steps.append(step)

                if not ready_steps:
                    # Circular dependency or other issue
                    raise ValueError(
                        "No steps ready to execute - possible circular dependency"
                    )

                # Execute ready steps
                for step in ready_steps:
                    step_execution = SagaStepExecution(
                        step_id=step.id,
                        execution_id=saga_execution.execution_id,
                    )
                    saga_execution.step_executions[step.id] = step_execution

                    success = await self._execute_step_with_retry(
                        step, step_execution, saga_execution.context
                    )

                    if success:
                        saga_execution.completed_steps.add(step.id)
                        executed_steps.append(step)
                    else:
                        saga_execution.failed_steps.add(step.id)
                        saga_execution.status = SagaStatus.COMPENSATING
                        break

                    remaining_steps.remove(step)

                # If a step failed, start compensation
                if saga_execution.status == SagaStatus.COMPENSATING:
                    break

            # Complete saga or start compensation
            if saga_execution.status == SagaStatus.RUNNING:
                saga_execution.status = SagaStatus.COMPLETED
                saga_execution.output_data = saga_execution.context.variables.model_copy()
                saga_execution.completed_at = datetime.now(timezone.utc)
            else:
                # Execute compensation
                await self._execute_compensation(
                    saga_def, saga_execution, executed_steps
                )

            if self.storage_adapter:
                await self.storage_adapter.store_execution(saga_execution)

            logger.info(
                "Saga execution completed",
                saga_id=saga_def.id,
                execution_id=saga_execution.execution_id,
                status=saga_execution.status.value,
                tenant_id=self.tenant_id,
            )

        except Exception as e:
            saga_execution.status = SagaStatus.FAILED
            saga_execution.error = ErrorInfo(
                error_type=type(e).__name__,
                message=str(e),
                timestamp=datetime.now(timezone.utc),
            )
            saga_execution.completed_at = datetime.now(timezone.utc)

            logger.error(
                "Saga execution failed",
                saga_id=saga_def.id,
                execution_id=saga_execution.execution_id,
                error=str(e),
                tenant_id=self.tenant_id,
            )

    async def _execute_step_with_retry(
        self,
        step: SagaStep,
        step_execution: SagaStepExecution,
        context: ExecutionContext,
    ) -> bool:
        """Execute step with retry logic."""
        max_retries = 0
        if step.retry_policy:
            max_retries = step.retry_policy.max_attempts - 1

        for attempt in range(max_retries + 1):
            step_execution.retry_count = attempt

            success = await self.engine.execute_transaction(
                step, step_execution, context
            )

            if success:
                return True

            # Check if we should retry
            if attempt < max_retries and self._should_retry(step, step_execution):
                # Calculate delay
                delay = self._calculate_retry_delay(step.retry_policy, attempt)
                await asyncio.sleep(delay)
                continue
            else:
                return False

        return False

    async def _execute_compensation(  # noqa: C901
        self,
        saga_def: SagaDefinition,
        saga_execution: SagaExecution,
        executed_steps: List[SagaStep],
    ):
        """Execute compensation for completed steps."""
        saga_execution.compensation_started_at = datetime.now(timezone.utc)

        if saga_def.compensation_strategy == CompensationStrategy.REVERSE_ORDER:
            # Compensate in reverse order
            for step in reversed(executed_steps):
                if step.compensatable:
                    step_execution = saga_execution.step_executions[step.id]
                    success = await self.engine.execute_compensation(
                        step, step_execution, saga_execution.context
                    )

                    if success:
                        saga_execution.compensated_steps.add(step.id)

        elif saga_def.compensation_strategy == CompensationStrategy.PARALLEL:
            # Compensate in parallel
            compensation_tasks = []
            for step in executed_steps:
                if step.compensatable:
                    step_execution = saga_execution.step_executions[step.id]
                    task = self.engine.execute_compensation(
                        step, step_execution, saga_execution.context
                    )
                    compensation_tasks.append((step.id, task))

            if compensation_tasks:
                results = await asyncio.gather(
                    *[task for _, task in compensation_tasks], return_exceptions=True
                )

                for (step_id, _), success in zip(compensation_tasks, results):
                    if success and not isinstance(success, Exception):
                        saga_execution.compensated_steps.add(step_id)

        saga_execution.status = SagaStatus.COMPENSATED
        saga_execution.compensation_completed_at = datetime.now(timezone.utc)

    def _should_retry(self, step: SagaStep, step_execution: SagaStepExecution) -> bool:
        """Determine if step should be retried."""
        if not step.retry_policy:
            return False

        if not step_execution.error:
            return False

        error_type = step_execution.error.error_type.lower()
        retry_on = [err.lower() for err in step.retry_policy.retry_on]

        return any(retry_type in error_type for retry_type in retry_on)

    def _calculate_retry_delay(self, retry_policy: RetryPolicy, attempt: int) -> float:
        """Calculate retry delay with backoff."""
        delay = retry_policy.initial_delay * (retry_policy.backoff_multiplier**attempt)
        delay = min(delay, retry_policy.max_delay)

        if retry_policy.jitter:
            import secrets

            delay *= 0.5 + secrets.randbelow(1000000) / 1000000 * 0.5

        return delay

    async def get_execution(self, execution_id: str) -> Optional[SagaExecution]:
        """Get saga execution by ID."""
        return self.saga_executions.get(execution_id)

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running saga execution."""
        saga_execution = self.saga_executions.get(execution_id)
        if not saga_execution:
            return False

        if saga_execution.status in [SagaStatus.PENDING, SagaStatus.RUNNING]:
            saga_execution.status = SagaStatus.CANCELLED
            saga_execution.completed_at = datetime.now(timezone.utc)

            logger.info(
                "Saga execution cancelled",
                execution_id=execution_id,
                tenant_id=self.tenant_id,
            )
            return True

        return False

    def register_transaction_handler(self, handler_name: str, handler: Callable):
        """Register a transaction handler function."""
        self.engine.register_transaction_handler(handler_name, handler)

    def register_compensation_handler(self, handler_name: str, handler: Callable):
        """Register a compensation handler function."""
        self.engine.register_compensation_handler(handler_name, handler)

    def register_validation_handler(self, handler_name: str, handler: Callable):
        """Register a validation handler function."""
        self.engine.register_validation_handler(handler_name, handler)

    async def get_saga_status(self, saga_id: str) -> Dict[str, Any]:
        """Get saga status information."""
        saga_def = self.saga_definitions.get(saga_id)
        if not saga_def:
            return {}

        # Count executions by status
        executions = [e for e in self.saga_executions.values() if e.saga_id == saga_id]
        status_counts = {}
        for execution in executions:
            status = execution.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "saga_id": saga_id,
            "name": saga_def.name,
            "version": saga_def.version,
            "steps_count": len(saga_def.steps),
            "executions_count": len(executions),
            "status_counts": status_counts,
            "compensation_strategy": saga_def.compensation_strategy.value,
        }
