"""
Saga Orchestration Framework

Provides distributed transaction management with compensation patterns
for complex multi-service operations.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union
from uuid import uuid4, UUID

from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from .exceptions import SagaError, ErrorContext

Base = declarative_base()


class SagaStatus(Enum):
    """Status of saga execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    COMPENSATION_FAILED = "compensation_failed"


class StepStatus(Enum):
    """Status of individual saga steps"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    COMPENSATION_FAILED = "compensation_failed"


@dataclass
class SagaContext:
    """Context passed between saga steps"""
    saga_id: str
    tenant_id: str
    user_id: Optional[str] = None
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    shared_data: Dict[str, Any] = field(default_factory=dict)
    step_results: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def set_step_result(self, step_name: str, result: Any) -> None:
        """Set result from a step"""
        self.step_results[step_name] = result
    
    def get_step_result(self, step_name: str) -> Any:
        """Get result from a previous step"""
        return self.step_results.get(step_name)
    
    def set_shared_data(self, key: str, value: Any) -> None:
        """Set shared data that persists across steps"""
        self.shared_data[key] = value
    
    def get_shared_data(self, key: str, default: Any = None) -> Any:
        """Get shared data"""
        return self.shared_data.get(key, default)


class SagaStep(ABC):
    """Abstract base class for saga steps"""
    
    def __init__(
        self, 
        name: str, 
        timeout_seconds: int = 30,
        retry_count: int = 3,
        compensation_required: bool = True
    ):
        self.name = name
        self.timeout_seconds = timeout_seconds
        self.retry_count = retry_count
        self.compensation_required = compensation_required
    
    @abstractmethod
    async def execute(self, context: SagaContext) -> Any:
        """Execute the step"""
        pass
    
    @abstractmethod
    async def compensate(self, context: SagaContext) -> None:
        """Compensate/rollback the step"""
        pass
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if step should be retried"""
        if attempt >= self.retry_count:
            return False
        
        # Don't retry certain types of errors
        from .exceptions import BusinessLogicError
        if isinstance(error, (ValueError, TypeError, BusinessLogicError)):
            return False
        
        return True
    
    def get_retry_delay(self, attempt: int) -> float:
        """Calculate retry delay"""
        base_delay = 1.0
        max_delay = 10.0
        delay = base_delay * (2 ** (attempt - 1))
        return min(delay, max_delay)


class CompensationHandler(ABC):
    """Handler for custom compensation logic"""
    
    @abstractmethod
    async def compensate(
        self, 
        context: SagaContext, 
        failed_step: str,
        completed_steps: List[str]
    ) -> None:
        """Execute compensation logic"""
        pass


class SagaDefinition:
    """Definition of a saga with its steps and configuration"""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        timeout_seconds: int = 300,
        compensation_handler: Optional[CompensationHandler] = None
    ):
        self.name = name
        self.description = description
        self.timeout_seconds = timeout_seconds
        self.compensation_handler = compensation_handler
        self.steps: List[SagaStep] = []
    
    def add_step(self, step: SagaStep) -> 'SagaDefinition':
        """Add a step to the saga"""
        self.steps.append(step)
        return self
    
    def add_steps(self, steps: List[SagaStep]) -> 'SagaDefinition':
        """Add multiple steps to the saga"""
        self.steps.extend(steps)
        return self


class SagaRecord(Base):
    """Database model for saga execution tracking"""
    
    __tablename__ = "saga_executions"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    saga_name = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=True)
    correlation_id = Column(String(100), nullable=False, index=True)
    
    # Execution tracking
    status = Column(String(30), nullable=False, default=SagaStatus.PENDING.value, index=True)
    current_step = Column(String(100), nullable=True)
    current_step_index = Column(Integer, default=0, nullable=False)
    total_steps = Column(Integer, default=0, nullable=False)
    
    # Context and results
    context_data = Column(JSON, default={}, nullable=False)
    step_results = Column(JSON, default={}, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    timeout_at = Column(DateTime, nullable=False)
    
    # Metadata
    metadata = Column(JSON, default={}, nullable=False)


class SagaStepRecord(Base):
    """Database model for individual step execution tracking"""
    
    __tablename__ = "saga_step_executions"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    saga_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    step_name = Column(String(100), nullable=False)
    step_index = Column(Integer, nullable=False)
    
    # Execution tracking
    status = Column(String(30), nullable=False, default=StepStatus.PENDING.value)
    attempt_count = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    
    # Results and errors
    result_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Compensation tracking
    compensation_required = Column(Boolean, default=True, nullable=False)
    compensated_at = Column(DateTime, nullable=True)


class SagaCoordinator:
    """Main saga orchestration coordinator"""
    
    def __init__(self, db_session_factory: Callable[[], Session]):
        self.db_session_factory = db_session_factory
        self._saga_definitions: Dict[str, SagaDefinition] = {}
    
    def register_saga(self, definition: SagaDefinition) -> None:
        """Register a saga definition"""
        self._saga_definitions[definition.name] = definition
    
    async def execute_saga(
        self,
        saga_name: str,
        context: SagaContext,
        initial_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a saga from start to finish"""
        
        definition = self._saga_definitions.get(saga_name)
        if not definition:
            raise ValueError(f"Saga definition '{saga_name}' not found")
        
        # Merge initial data into context
        if initial_data:
            context.shared_data.update(initial_data)
        
        with self.db_session_factory() as db:
            # Create saga record
            saga_record = self._create_saga_record(db, saga_name, definition, context)
            context.saga_id = str(saga_record.id)
            
            try:
                # Execute all steps
                await self._execute_saga_steps(db, saga_record, definition, context)
                
                # Mark saga as completed
                saga_record.status = SagaStatus.COMPLETED.value
                saga_record.completed_at = datetime.utcnow()
                db.commit()
                
                return {
                    "saga_id": str(saga_record.id),
                    "status": SagaStatus.COMPLETED.value,
                    "step_results": context.step_results,
                    "shared_data": context.shared_data
                }
                
            except Exception as e:
                # Handle saga failure
                return await self._handle_saga_failure(
                    db, saga_record, definition, context, str(e)
                )
    
    async def resume_saga(
        self, 
        saga_id: str,
        from_step: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resume a failed or interrupted saga"""
        
        with self.db_session_factory() as db:
            saga_record = db.query(SagaRecord).filter(
                SagaRecord.id == UUID(saga_id)
            ).first()
            
            if not saga_record:
                raise ValueError(f"Saga '{saga_id}' not found")
            
            definition = self._saga_definitions.get(saga_record.saga_name)
            if not definition:
                raise ValueError(f"Saga definition '{saga_record.saga_name}' not found")
            
            # Reconstruct context
            context = SagaContext(
                saga_id=saga_id,
                tenant_id=saga_record.tenant_id,
                user_id=saga_record.user_id,
                correlation_id=saga_record.correlation_id,
                shared_data=saga_record.context_data,
                step_results=saga_record.step_results
            )
            
            try:
                # Resume from specified step or current step
                start_index = saga_record.current_step_index
                if from_step:
                    start_index = next(
                        (i for i, step in enumerate(definition.steps) 
                         if step.name == from_step), 
                        start_index
                    )
                
                await self._execute_saga_steps(
                    db, saga_record, definition, context, start_index
                )
                
                # Mark saga as completed
                saga_record.status = SagaStatus.COMPLETED.value
                saga_record.completed_at = datetime.utcnow()
                db.commit()
                
                return {
                    "saga_id": saga_id,
                    "status": SagaStatus.COMPLETED.value,
                    "step_results": context.step_results,
                    "shared_data": context.shared_data
                }
                
            except Exception as e:
                return await self._handle_saga_failure(
                    db, saga_record, definition, context, str(e)
                )
    
    async def _execute_saga_steps(
        self,
        db: Session,
        saga_record: SagaRecord,
        definition: SagaDefinition,
        context: SagaContext,
        start_index: int = 0
    ) -> None:
        """Execute saga steps sequentially"""
        
        saga_record.status = SagaStatus.RUNNING.value
        saga_record.started_at = datetime.utcnow()
        saga_record.total_steps = len(definition.steps)
        db.commit()
        
        for i in range(start_index, len(definition.steps)):
            step = definition.steps[i]
            
            # Update current step
            saga_record.current_step = step.name
            saga_record.current_step_index = i
            db.commit()
            
            # Execute step
            await self._execute_step(db, saga_record, step, context, i)
            
            # Update saga context in database
            saga_record.context_data = context.shared_data
            saga_record.step_results = context.step_results
            db.commit()
            
            # Check for timeout
            if datetime.utcnow() > saga_record.timeout_at:
                raise TimeoutError(f"Saga '{definition.name}' timed out")
    
    async def _execute_step(
        self,
        db: Session,
        saga_record: SagaRecord,
        step: SagaStep,
        context: SagaContext,
        step_index: int
    ) -> None:
        """Execute a single saga step with retry logic"""
        
        # Create step record
        step_record = SagaStepRecord(
            saga_id=saga_record.id,
            step_name=step.name,
            step_index=step_index,
            max_attempts=step.retry_count,
            compensation_required=step.compensation_required
        )
        db.add(step_record)
        db.commit()
        db.refresh(step_record)
        
        attempt = 0
        last_error = None
        
        while attempt < step.retry_count:
            attempt += 1
            step_record.attempt_count = attempt
            step_record.status = StepStatus.RUNNING.value
            step_record.started_at = datetime.utcnow()
            db.commit()
            
            try:
                # Execute step with timeout
                result = await asyncio.wait_for(
                    step.execute(context),
                    timeout=step.timeout_seconds
                )
                
                # Step completed successfully
                step_record.status = StepStatus.COMPLETED.value
                step_record.completed_at = datetime.utcnow()
                step_record.result_data = {"result": result} if result else {}
                db.commit()
                
                # Store result in context
                context.set_step_result(step.name, result)
                return
                
            except Exception as e:
                last_error = e
                step_record.error_message = str(e)
                
                # Check if we should retry
                if attempt < step.retry_count and step.should_retry(e, attempt):
                    step_record.status = StepStatus.FAILED.value
                    db.commit()
                    
                    # Wait before retry
                    retry_delay = step.get_retry_delay(attempt)
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    # Step failed permanently
                    step_record.status = StepStatus.FAILED.value
                    db.commit()
                    raise e
    
    async def _handle_saga_failure(
        self,
        db: Session,
        saga_record: SagaRecord,
        definition: SagaDefinition,
        context: SagaContext,
        error_message: str
    ) -> Dict[str, Any]:
        """Handle saga failure with compensation"""
        
        saga_record.status = SagaStatus.FAILED.value
        saga_record.error_message = error_message
        db.commit()
        
        try:
            # Start compensation process
            saga_record.status = SagaStatus.COMPENSATING.value
            db.commit()
            
            await self._compensate_saga(db, saga_record, definition, context)
            
            # Compensation successful
            saga_record.status = SagaStatus.COMPENSATED.value
            saga_record.completed_at = datetime.utcnow()
            db.commit()
            
            return {
                "saga_id": str(saga_record.id),
                "status": SagaStatus.COMPENSATED.value,
                "error": error_message,
                "step_results": context.step_results,
                "shared_data": context.shared_data
            }
            
        except Exception as comp_error:
            # Compensation failed
            saga_record.status = SagaStatus.COMPENSATION_FAILED.value
            saga_record.error_message = f"Original error: {error_message}. Compensation error: {str(comp_error)}"
            saga_record.completed_at = datetime.utcnow()
            db.commit()
            
            error_context = ErrorContext(
                operation="saga_compensation",
                resource_type="saga",
                resource_id=str(saga_record.id),
                tenant_id=saga_record.tenant_id,
                user_id=saga_record.user_id,
                correlation_id=saga_record.correlation_id
            )
            
            raise SagaError(
                message=f"Saga compensation failed: {str(comp_error)}",
                saga_id=str(saga_record.id),
                step_name=saga_record.current_step,
                compensation_failed=True,
                context=error_context,
                original_error=error_message,
                compensation_error=str(comp_error)
            )
    
    async def _compensate_saga(
        self,
        db: Session,
        saga_record: SagaRecord,
        definition: SagaDefinition,
        context: SagaContext
    ) -> None:
        """Compensate completed saga steps in reverse order"""
        
        # Get completed steps that require compensation
        completed_steps = db.query(SagaStepRecord).filter(
            SagaStepRecord.saga_id == saga_record.id,
            SagaStepRecord.status == StepStatus.COMPLETED.value,
            SagaStepRecord.compensation_required == True
        ).order_by(SagaStepRecord.step_index.desc()).all()
        
        # Use custom compensation handler if available
        if definition.compensation_handler:
            completed_step_names = [step.step_name for step in completed_steps]
            await definition.compensation_handler.compensate(
                context, saga_record.current_step, completed_step_names
            )
            return
        
        # Default compensation: reverse order of completed steps
        for step_record in completed_steps:
            # Find the step definition
            step_def = next(
                (s for s in definition.steps if s.name == step_record.step_name),
                None
            )
            
            if step_def:
                try:
                    step_record.status = StepStatus.COMPENSATING.value
                    db.commit()
                    
                    await step_def.compensate(context)
                    
                    step_record.status = StepStatus.COMPENSATED.value
                    step_record.compensated_at = datetime.utcnow()
                    db.commit()
                    
                except Exception as e:
                    step_record.status = StepStatus.COMPENSATION_FAILED.value
                    step_record.error_message = f"Compensation failed: {str(e)}"
                    db.commit()
                    raise e
    
    def _create_saga_record(
        self,
        db: Session,
        saga_name: str,
        definition: SagaDefinition,
        context: SagaContext
    ) -> SagaRecord:
        """Create a new saga execution record"""
        
        timeout_at = datetime.utcnow() + timedelta(seconds=definition.timeout_seconds)
        
        record = SagaRecord(
            saga_name=saga_name,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            correlation_id=context.correlation_id,
            context_data=context.shared_data,
            step_results=context.step_results,
            timeout_at=timeout_at,
            metadata=context.metadata
        )
        
        db.add(record)
        db.commit()
        db.refresh(record)
        
        return record
    
    def get_saga_status(
        self, 
        db: Session, 
        saga_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get saga execution status"""
        
        saga_record = db.query(SagaRecord).filter(
            SagaRecord.id == UUID(saga_id)
        ).first()
        
        if not saga_record:
            return None
        
        # Get step statuses
        step_records = db.query(SagaStepRecord).filter(
            SagaStepRecord.saga_id == saga_record.id
        ).order_by(SagaStepRecord.step_index).all()
        
        steps = []
        for step_record in step_records:
            steps.append({
                "name": step_record.step_name,
                "index": step_record.step_index,
                "status": step_record.status,
                "attempt_count": step_record.attempt_count,
                "started_at": step_record.started_at.isoformat() if step_record.started_at else None,
                "completed_at": step_record.completed_at.isoformat() if step_record.completed_at else None,
                "error_message": step_record.error_message,
                "compensated_at": step_record.compensated_at.isoformat() if step_record.compensated_at else None
            })
        
        return {
            "saga_id": str(saga_record.id),
            "saga_name": saga_record.saga_name,
            "status": saga_record.status,
            "current_step": saga_record.current_step,
            "progress": f"{saga_record.current_step_index}/{saga_record.total_steps}",
            "created_at": saga_record.created_at.isoformat(),
            "updated_at": saga_record.updated_at.isoformat(),
            "started_at": saga_record.started_at.isoformat() if saga_record.started_at else None,
            "completed_at": saga_record.completed_at.isoformat() if saga_record.completed_at else None,
            "timeout_at": saga_record.timeout_at.isoformat(),
            "error_message": saga_record.error_message,
            "steps": steps,
            "step_results": saga_record.step_results,
            "shared_data": saga_record.context_data
        }