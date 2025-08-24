"""
State Machine SDK for managing state transitions and state-based workflows.

This module provides comprehensive state machine capabilities including:
- State definition and transition management
- Event-driven state changes
- Guard conditions and actions
- Hierarchical state machines
- State persistence and recovery
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import structlog
from pydantic import BaseModel, Field, field_validator

from ..contracts.common_schemas import (
    ExecutionContext,
    ExecutionStatus,
    OperationMetadata,
    ErrorInfo,
)

logger = structlog.get_logger(__name__)


class TransitionType(str, Enum):
    """State transition types."""

    AUTOMATIC = "automatic"
    EVENT_DRIVEN = "event_driven"
    CONDITIONAL = "conditional"
    MANUAL = "manual"
    TIMEOUT = "timeout"


class StateType(str, Enum):
    """State types."""

    SIMPLE = "simple"
    COMPOSITE = "composite"
    INITIAL = "initial"
    FINAL = "final"
    CHOICE = "choice"
    PARALLEL = "parallel"


class StateTransition(BaseModel):
    """State transition definition."""

    id: str = Field(..., description="Transition identifier")
    from_state: str = Field(..., description="Source state")
    to_state: str = Field(..., description="Target state")
    event: Optional[str] = Field(None, description="Triggering event")
    condition: Optional[str] = Field(None, description="Guard condition")
    action: Optional[str] = Field(None, description="Transition action")
    transition_type: TransitionType = Field(
        TransitionType.EVENT_DRIVEN, description="Transition type"
    )
    timeout_seconds: Optional[float] = Field(
        None, description="Timeout for automatic transitions"
    )
    priority: int = Field(0, description="Transition priority")

    class Config:
        """Class for Config operations."""
        extra = "allow"


class StateDefinition(BaseModel):
    """State definition."""

    id: str = Field(..., description="State identifier")
    name: str = Field(..., description="State name")
    state_type: StateType = Field(StateType.SIMPLE, description="State type")
    description: Optional[str] = Field(None, description="State description")

    # State actions
    entry_action: Optional[str] = Field(None, description="Entry action")
    exit_action: Optional[str] = Field(None, description="Exit action")
    do_action: Optional[str] = Field(None, description="Do action (while in state)")

    # Composite state configuration
    substates: List["StateDefinition"] = Field(
        default_factory=list, description="Sub-states"
    )
    initial_substate: Optional[str] = Field(None, description="Initial sub-state")

    # State data
    state_data: Dict[str, Any] = Field(
        default_factory=dict, description="State-specific data"
    )

    # Timeout configuration
    timeout_seconds: Optional[float] = Field(None, description="State timeout")
    timeout_transition: Optional[str] = Field(
        None, description="Timeout transition target"
    )

    class Config:
        """Class for Config operations."""
        extra = "allow"


class StateMachineDefinition(BaseModel):
    """State machine definition."""

    id: str = Field(..., description="State machine identifier")
    name: str = Field(..., description="State machine name")
    version: str = Field("1.0", description="State machine version")
    description: Optional[str] = Field(None, description="State machine description")

    # States and transitions
    states: List[StateDefinition] = Field(..., description="State definitions")
    transitions: List[StateTransition] = Field(..., description="State transitions")
    initial_state: str = Field(..., description="Initial state")
    final_states: List[str] = Field(default_factory=list, description="Final states")

    # Configuration
    context_schema: Dict[str, Any] = Field(
        default_factory=dict, description="Context schema"
    )

    # Metadata
    tenant_id: str = Field(..., description="Tenant identifier")
    metadata: OperationMetadata = Field(default_factory=OperationMetadata)

    @field_validator("states")
    @classmethod
    def validate_states(cls, v, info):
        """Validate States operation."""
        if not v:
            raise ValueError("State machine must have at least one state")

        state_ids = {state.id for state in v}

        # Validate initial state exists
        initial_state = info.data.get("initial_state")
        if initial_state and initial_state not in state_ids:
            raise ValueError(f"Initial state '{initial_state}' not found")

        # Validate final states exist
        final_states = info.data.get("final_states", [])
        for final_state in final_states:
            if final_state not in state_ids:
                raise ValueError(f"Final state '{final_state}' not found")

        return v

    @field_validator("transitions")
    @classmethod
    def validate_transitions(cls, v, info):
        """Validate Transitions operation."""
        states = info.data.get("states", [])
        state_ids = {state.id for state in states}

        for transition in v:
            if transition.from_state not in state_ids:
                raise ValueError(
                    f"Transition from unknown state: {transition.from_state}"
                )
            if transition.to_state not in state_ids:
                raise ValueError(f"Transition to unknown state: {transition.to_state}")

        return v

    class Config:
        """Class for Config operations."""
        extra = "allow"


@dataclass
class StateMachineExecution:
    """Runtime execution state of a state machine."""

    execution_id: str
    state_machine_id: str
    current_state: str
    previous_state: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.RUNNING
    context: Optional[ExecutionContext] = None
    state_data: Dict[str, Any] = field(default_factory=dict)
    transition_history: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[ErrorInfo] = None
    started_at: Optional[datetime] = None
    last_transition_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "state_machine_id": self.state_machine_id,
            "current_state": self.current_state,
            "previous_state": self.previous_state,
            "status": self.status.value,
            "context": self.context.dict() if self.context else None,
            "state_data": self.state_data,
            "transition_history": self.transition_history,
            "error": self.error.dict() if self.error else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_transition_at": (
                self.last_transition_at.isoformat() if self.last_transition_at else None
            ),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }


class StateMachineEngine:
    """State machine execution engine."""

    def __init__(self):
        """  Init   operation."""
        self.action_handlers: Dict[str, Callable] = {}
        self.condition_evaluators: Dict[str, Callable] = {}
        self.event_handlers: Dict[str, Callable] = {}

    def register_action_handler(self, action_name: str, handler: Callable):
        """Register an action handler."""
        self.action_handlers[action_name] = handler

    def register_condition_evaluator(self, condition_name: str, evaluator: Callable):
        """Register a condition evaluator."""
        self.condition_evaluators[condition_name] = evaluator

    def register_event_handler(self, event_name: str, handler: Callable):
        """Register an event handler."""
        self.event_handlers[event_name] = handler

    async def execute_action(
        self,
        action_name: str,
        execution: StateMachineExecution,
        action_data: Dict[str, Any] = None,
    ) -> bool:
        """Execute an action."""
        try:
            handler = self.action_handlers.get(action_name)
            if not handler:
                logger.warning(f"No handler found for action: {action_name}")
                return True

            await handler(execution, action_data or {})
            return True

        except Exception as e:
            logger.error(
                "Action execution failed",
                action=action_name,
                execution_id=execution.execution_id,
                error=str(e),
            )
            return False

    async def evaluate_condition(
        self,
        condition_expr: str,
        execution: StateMachineExecution,
        event_data: Dict[str, Any] = None,
    ) -> bool:
        """Evaluate a guard condition."""
        try:
            # Simple condition evaluation - can be extended
            if condition_expr in self.condition_evaluators:
                evaluator = self.condition_evaluators[condition_expr]
                return await evaluator(execution, event_data or {})

            # Safe evaluation using AST parsing instead of eval
            context = {
                "state_data": execution.state_data,
                "context": execution.context.variables if execution.context else {},
                "event_data": event_data or {},
            }

            # Use safe AST evaluation instead of eval
            from dotmac_isp.sdks.platform.security.ast_evaluator import SafeEvaluator

            evaluator = SafeEvaluator()
            return evaluator.evaluate(condition_expr, context)

        except Exception as e:
            logger.error(
                "Condition evaluation failed",
                condition=condition_expr,
                execution_id=execution.execution_id,
                error=str(e),
            )
            return False

    async def process_event(
        self,
        event_name: str,
        execution: StateMachineExecution,
        event_data: Dict[str, Any] = None,
    ):
        """Process an event."""
        handler = self.event_handlers.get(event_name)
        if handler:
            try:
                await handler(execution, event_data or {})
            except Exception as e:
                logger.error(
                    "Event handler failed",
                    event=event_name,
                    execution_id=execution.execution_id,
                    error=str(e),
                )


class StateMachine:
    """State machine runtime instance."""

    def __init__(self, definition: StateMachineDefinition, engine: StateMachineEngine):
        """  Init   operation."""
        self.definition = definition
        self.engine = engine
        self.state_map = {state.id: state for state in definition.states}
        self.transitions_from = self._build_transition_map()

    def _build_transition_map(self) -> Dict[str, List[StateTransition]]:
        """Build transition map for efficient lookup."""
        transitions_map = {}
        for transition in self.definition.transitions:
            if transition.from_state not in transitions_map:
                transitions_map[transition.from_state] = []
            transitions_map[transition.from_state].append(transition)

        # Sort by priority
        for transitions in transitions_map.values():
            transitions.sort(key=lambda t: t.priority, reverse=True)

        return transitions_map

    async def start_execution(
        self,
        execution_id: str,
        context: Optional[ExecutionContext] = None,
    ) -> StateMachineExecution:
        """Start state machine execution."""
        if not context:
            context = ExecutionContext(
                execution_id=execution_id,
                tenant_id=self.definition.tenant_id,
            )

        execution = StateMachineExecution(
            execution_id=execution_id,
            state_machine_id=self.definition.id,
            current_state=self.definition.initial_state,
            context=context,
            started_at=datetime.now(timezone.utc),
        )

        # Execute entry action for initial state
        initial_state = self.state_map[self.definition.initial_state]
        if initial_state.entry_action:
            await self.engine.execute_action(initial_state.entry_action, execution)

        logger.info(
            "State machine execution started",
            state_machine_id=self.definition.id,
            execution_id=execution_id,
            initial_state=self.definition.initial_state,
        )

        return execution

    async def process_event(
        self,
        execution: StateMachineExecution,
        event_name: str,
        event_data: Dict[str, Any] = None,
    ) -> bool:
        """Process an event and potentially trigger state transitions."""
        if execution.status != ExecutionStatus.RUNNING:
            return False

        try:
            # Process event with engine
            await self.engine.process_event(event_name, execution, event_data)

            # Find applicable transitions
            applicable_transitions = await self._find_applicable_transitions(
                execution, event_name, event_data
            )

            if not applicable_transitions:
                logger.debug(
                    "No applicable transitions found",
                    current_state=execution.current_state,
                    event=event_name,
                    execution_id=execution.execution_id,
                )
                return False

            # Execute first applicable transition
            transition = applicable_transitions[0]
            return await self._execute_transition(execution, transition, event_data)

        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error = ErrorInfo(
                error_type=type(e).__name__,
                message=str(e),
                timestamp=datetime.now(timezone.utc),
            )
            execution.completed_at = datetime.now(timezone.utc)

            logger.error(
                "Event processing failed",
                event=event_name,
                execution_id=execution.execution_id,
                error=str(e),
            )
            return False

    async def _find_applicable_transitions(
        self,
        execution: StateMachineExecution,
        event_name: str,
        event_data: Dict[str, Any] = None,
    ) -> List[StateTransition]:
        """Find transitions applicable to the current state and event."""
        current_state = execution.current_state
        transitions = self.transitions_from.get(current_state, [])
        applicable = []

        for transition in transitions:
            # Check event match
            if transition.event and transition.event != event_name:
                continue

            # Check guard condition
            if transition.condition:
                if not await self.engine.evaluate_condition(
                    transition.condition, execution, event_data
                ):
                    continue

            applicable.append(transition)

        return applicable

    async def _execute_transition(
        self,
        execution: StateMachineExecution,
        transition: StateTransition,
        event_data: Dict[str, Any] = None,
    ) -> bool:
        """Execute a state transition."""
        try:
            from_state = self.state_map[transition.from_state]
            to_state = self.state_map[transition.to_state]

            # Execute exit action
            if from_state.exit_action:
                await self.engine.execute_action(from_state.exit_action, execution)

            # Execute transition action
            if transition.action:
                await self.engine.execute_action(
                    transition.action, execution, event_data
                )

            # Update execution state
            execution.previous_state = execution.current_state
            execution.current_state = transition.to_state
            execution.last_transition_at = datetime.now(timezone.utc)

            # Record transition in history
            execution.transition_history.append(
                {
                    "transition_id": transition.id,
                    "from_state": transition.from_state,
                    "to_state": transition.to_state,
                    "event": transition.event,
                    "timestamp": execution.last_transition_at.isoformat(),
                    "event_data": event_data,
                }
            )

            # Execute entry action
            if to_state.entry_action:
                await self.engine.execute_action(to_state.entry_action, execution)

            # Check if reached final state
            if transition.to_state in self.definition.final_states:
                execution.status = ExecutionStatus.COMPLETED
                execution.completed_at = datetime.now(timezone.utc)

            logger.info(
                "State transition executed",
                transition_id=transition.id,
                from_state=transition.from_state,
                to_state=transition.to_state,
                execution_id=execution.execution_id,
            )

            return True

        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error = ErrorInfo(
                error_type=type(e).__name__,
                message=str(e),
                timestamp=datetime.now(timezone.utc),
            )
            execution.completed_at = datetime.now(timezone.utc)

            logger.error(
                "Transition execution failed",
                transition_id=transition.id,
                execution_id=execution.execution_id,
                error=str(e),
            )
            return False

    async def force_transition(
        self,
        execution: StateMachineExecution,
        to_state: str,
        reason: str = "manual",
    ) -> bool:
        """Force a transition to a specific state."""
        if to_state not in self.state_map:
            return False

        try:
            from_state = self.state_map[execution.current_state]
            target_state = self.state_map[to_state]

            # Execute exit action
            if from_state.exit_action:
                await self.engine.execute_action(from_state.exit_action, execution)

            # Update execution state
            execution.previous_state = execution.current_state
            execution.current_state = to_state
            execution.last_transition_at = datetime.now(timezone.utc)

            # Record forced transition
            execution.transition_history.append(
                {
                    "transition_id": f"forced_{uuid.uuid4()}",
                    "from_state": execution.previous_state,
                    "to_state": to_state,
                    "event": "forced_transition",
                    "reason": reason,
                    "timestamp": execution.last_transition_at.isoformat(),
                }
            )

            # Execute entry action
            if target_state.entry_action:
                await self.engine.execute_action(target_state.entry_action, execution)

            # Check if reached final state
            if to_state in self.definition.final_states:
                execution.status = ExecutionStatus.COMPLETED
                execution.completed_at = datetime.now(timezone.utc)

            logger.info(
                "Forced state transition",
                from_state=execution.previous_state,
                to_state=to_state,
                reason=reason,
                execution_id=execution.execution_id,
            )

            return True

        except Exception as e:
            logger.error(
                "Forced transition failed",
                to_state=to_state,
                execution_id=execution.execution_id,
                error=str(e),
            )
            return False


class StateMachineSDK:
    """SDK for state machine management and execution."""

    def __init__(self, tenant_id: str, storage_adapter=None):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self.storage_adapter = storage_adapter
        self.engine = StateMachineEngine()
        self.definitions: Dict[str, StateMachineDefinition] = {}
        self.executions: Dict[str, StateMachineExecution] = {}
        self.state_machines: Dict[str, StateMachine] = {}

        logger.info("StateMachineSDK initialized", tenant_id=tenant_id)

    async def create_state_machine(self, definition: StateMachineDefinition) -> str:
        """Create a new state machine definition."""
        definition.tenant_id = self.tenant_id
        definition.metadata.updated_at = datetime.now(timezone.utc)

        self.definitions[definition.id] = definition
        self.state_machines[definition.id] = StateMachine(definition, self.engine)

        if self.storage_adapter:
            await self.storage_adapter.store_state_machine(definition)

        logger.info(
            "State machine created",
            state_machine_id=definition.id,
            tenant_id=self.tenant_id,
        )

        return definition.id

    async def start_execution(
        self,
        state_machine_id: str,
        context: Optional[ExecutionContext] = None,
    ) -> str:
        """Start state machine execution."""
        state_machine = self.state_machines.get(state_machine_id)
        if not state_machine:
            raise ValueError(f"State machine {state_machine_id} not found")

        execution_id = str(uuid.uuid4())

        if not context:
            context = ExecutionContext(
                execution_id=execution_id,
                tenant_id=self.tenant_id,
            )

        execution = await state_machine.start_execution(execution_id, context)
        self.executions[execution_id] = execution

        if self.storage_adapter:
            await self.storage_adapter.store_execution(execution)

        logger.info(
            "State machine execution started",
            state_machine_id=state_machine_id,
            execution_id=execution_id,
            tenant_id=self.tenant_id,
        )

        return execution_id

    async def send_event(
        self,
        execution_id: str,
        event_name: str,
        event_data: Dict[str, Any] = None,
    ) -> bool:
        """Send an event to a state machine execution."""
        execution = self.executions.get(execution_id)
        if not execution:
            return False

        state_machine = self.state_machines.get(execution.state_machine_id)
        if not state_machine:
            return False

        result = await state_machine.process_event(execution, event_name, event_data)

        if self.storage_adapter:
            await self.storage_adapter.store_execution(execution)

        return result

    async def force_transition(
        self,
        execution_id: str,
        to_state: str,
        reason: str = "manual",
    ) -> bool:
        """Force a state machine to transition to a specific state."""
        execution = self.executions.get(execution_id)
        if not execution:
            return False

        state_machine = self.state_machines.get(execution.state_machine_id)
        if not state_machine:
            return False

        result = await state_machine.force_transition(execution, to_state, reason)

        if self.storage_adapter:
            await self.storage_adapter.store_execution(execution)

        return result

    async def get_execution(self, execution_id: str) -> Optional[StateMachineExecution]:
        """Get state machine execution by ID."""
        return self.executions.get(execution_id)

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a state machine execution."""
        execution = self.executions.get(execution_id)
        if not execution:
            return False

        if execution.status == ExecutionStatus.RUNNING:
            execution.status = ExecutionStatus.CANCELLED
            execution.completed_at = datetime.now(timezone.utc)

            if self.storage_adapter:
                await self.storage_adapter.store_execution(execution)

            logger.info(
                "State machine execution cancelled",
                execution_id=execution_id,
                tenant_id=self.tenant_id,
            )
            return True

        return False

    def register_action_handler(self, action_name: str, handler: Callable):
        """Register an action handler."""
        self.engine.register_action_handler(action_name, handler)

    def register_condition_evaluator(self, condition_name: str, evaluator: Callable):
        """Register a condition evaluator."""
        self.engine.register_condition_evaluator(condition_name, evaluator)

    def register_event_handler(self, event_name: str, handler: Callable):
        """Register an event handler."""
        self.engine.register_event_handler(event_name, handler)

    async def get_state_machine_status(self, state_machine_id: str) -> Dict[str, Any]:
        """Get state machine status information."""
        definition = self.definitions.get(state_machine_id)
        if not definition:
            return {}

        # Count executions by status
        executions = [
            e
            for e in self.executions.values()
            if e.state_machine_id == state_machine_id
        ]
        status_counts = {}
        for execution in executions:
            status = execution.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "state_machine_id": state_machine_id,
            "name": definition.name,
            "version": definition.version,
            "states_count": len(definition.states),
            "transitions_count": len(definition.transitions),
            "executions_count": len(executions),
            "status_counts": status_counts,
        }
