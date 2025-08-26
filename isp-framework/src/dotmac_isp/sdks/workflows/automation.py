"""
Automation SDK for rule-based automation and event-driven workflows.

This module provides comprehensive automation capabilities including:
- Rule definition and execution
- Event-driven automation
- Condition evaluation
- Action orchestration
- Policy enforcement
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import structlog
from pydantic import BaseModel, Field, ConfigDict

from ..contracts.common_schemas import (
    ExecutionContext,
    ExecutionStatus,
    OperationMetadata,
    RetryPolicy,
    TimeoutPolicy,
    ErrorInfo,
    Priority,
)

logger = structlog.get_logger(__name__)


class TriggerType(str, Enum):
    """Automation trigger types."""

    EVENT = "event"
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"
    CONDITION = "condition"
    MANUAL = "manual"
    THRESHOLD = "threshold"
    STATE_CHANGE = "state_change"


class ActionType(str, Enum):
    """Automation action types."""

    EXECUTE_TASK = "execute_task"
    SEND_NOTIFICATION = "send_notification"
    UPDATE_STATE = "update_state"
    TRIGGER_WORKFLOW = "trigger_workflow"
    API_CALL = "api_call"
    SCRIPT = "script"
    EMAIL = "email"
    WEBHOOK = "webhook"


class ConditionOperator(str, Enum):
    """Condition operators."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    REGEX = "regex"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


class AutomationTrigger(BaseModel):
    """Automation trigger definition."""

    trigger_type: TriggerType = Field(..., description="Trigger type")
    event_pattern: Optional[str] = Field(None, description="Event pattern to match")
    schedule_expression: Optional[str] = Field(
        None, description="Cron schedule expression"
    )
    webhook_path: Optional[str] = Field(None, description="Webhook endpoint path")
    condition_expression: Optional[str] = Field(
        None, description="Condition expression"
    )
    threshold_config: Dict[str, Any] = Field(
        default_factory=dict, description="Threshold configuration"
    )

    model_config = ConfigDict(extra="allow")

class AutomationCondition(BaseModel):
    """Automation condition definition."""

    field: str = Field(..., description="Field to evaluate")
    operator: ConditionOperator = Field(..., description="Condition operator")
    value: Any = Field(..., description="Value to compare against")
    data_type: Optional[str] = Field(None, description="Expected data type")

    model_config = ConfigDict(extra="forbid")

class AutomationAction(BaseModel):
    """Automation action definition."""

    id: str = Field(..., description="Action identifier")
    action_type: ActionType = Field(..., description="Action type")
    name: str = Field(..., description="Action name")
    description: Optional[str] = Field(None, description="Action description")

    # Action configuration
    target: Optional[str] = Field(None, description="Action target")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Action parameters"
    )
    input_mapping: Dict[str, str] = Field(
        default_factory=dict, description="Input mapping"
    )
    output_mapping: Dict[str, str] = Field(
        default_factory=dict, description="Output mapping"
    )

    # Execution policies
    retry_policy: Optional[RetryPolicy] = Field(None, description="Retry policy")
    timeout_policy: Optional[TimeoutPolicy] = Field(None, description="Timeout policy")

    # Conditional execution
    condition: Optional[AutomationCondition] = Field(
        None, description="Execution condition"
    )

    model_config = ConfigDict(extra="allow")

class AutomationRule(BaseModel):
    """Automation rule definition."""

    id: str = Field(..., description="Rule identifier")
    name: str = Field(..., description="Rule name")
    description: Optional[str] = Field(None, description="Rule description")

    # Rule configuration
    trigger: AutomationTrigger = Field(..., description="Rule trigger")
    conditions: List[AutomationCondition] = Field(
        default_factory=list, description="Rule conditions"
    )
    actions: List[AutomationAction] = Field(..., description="Rule actions")

    # Rule settings
    enabled: bool = Field(True, description="Rule enabled status")
    priority: Priority = Field(Priority.NORMAL, description="Rule priority")

    # Execution limits
    max_executions_per_hour: Optional[int] = Field(
        None, description="Max executions per hour"
    )
    max_executions_per_day: Optional[int] = Field(
        None, description="Max executions per day"
    )

    # Metadata
    tenant_id: str = Field(..., description="Tenant identifier")
    metadata: OperationMetadata = Field(default_factory=OperationMetadata)

    model_config = ConfigDict(extra="allow")

@dataclass
class AutomationExecution:
    """Runtime execution state of an automation rule."""

    execution_id: str
    rule_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    trigger_data: Dict[str, Any] = field(default_factory=dict)
    context: Optional[ExecutionContext] = None
    action_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    error: Optional[ErrorInfo] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "rule_id": self.rule_id,
            "status": self.status.value,
            "trigger_data": self.trigger_data,
            "context": self.context.model_dump() if self.context else None,
            "action_results": self.action_results,
            "error": self.error.model_dump() if self.error else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }


class ConditionEvaluator:
    """Evaluates automation conditions."""

    def evaluate_condition(
        self, condition: AutomationCondition, data: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a single condition using strategy pattern.
        
        REFACTORED: Replaced 14-complexity if-elif chain with strategy pattern call.
        Complexity reduced from 14→3.
        """
        from .condition_strategies import create_condition_engine
        
        field_value = self._get_field_value(condition.field, data)
        expected_value = condition.value
        
        condition_engine = create_condition_engine()
        return condition_engine.evaluate_condition(
            condition.operator, field_value, expected_value
        )

    def evaluate_conditions(
        self, conditions: List[AutomationCondition], data: Dict[str, Any]
    ) -> bool:
        """Evaluate multiple conditions (AND logic)."""
        return all(self.evaluate_condition(condition, data) for condition in conditions)

    def _get_field_value(self, field_path: str, data: Dict[str, Any]) -> Any:
        """Get field value using dot notation."""
        keys = field_path.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value


class ActionExecutor:
    """Executes automation actions."""

    def __init__(self):
        """  Init   operation."""
        self.action_handlers: Dict[ActionType, Callable] = {}
        self.custom_handlers: Dict[str, Callable] = {}

    def register_action_handler(self, action_type: ActionType, handler: Callable):
        """Register an action handler."""
        self.action_handlers[action_type] = handler

    def register_custom_handler(self, handler_name: str, handler: Callable):
        """Register a custom action handler."""
        self.custom_handlers[handler_name] = handler

    async def execute_action(
        self,
        action: AutomationAction,
        trigger_data: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """Execute a single action."""
        try:
            # Check action condition
            if action.condition:
                evaluator = ConditionEvaluator()
                if not evaluator.evaluate_condition(action.condition, trigger_data):
                    return {"status": "skipped", "reason": "condition_not_met"}

            # Prepare input data
            input_data = self._prepare_input_data(action, trigger_data, context)

            # Get handler
            handler = self._get_action_handler(action)
            if not handler:
                raise ValueError(
                    f"No handler found for action type: {action.action_type}"
                )

            # Execute with timeout
            timeout = None
            if action.timeout_policy and action.timeout_policy.execution_timeout:
                timeout = action.timeout_policy.execution_timeout

            if timeout:
                result = await asyncio.wait_for(
                    handler(action, input_data, context), timeout=timeout
                )
            else:
                result = await handler(action, input_data, context)

            # Map output data
            output_data = self._map_output_data(action, result)

            return {
                "status": "completed",
                "result": output_data,
                "action_id": action.id,
            }

        except Exception as e:
            logger.error(
                "Action execution failed",
                action_id=action.id,
                action_type=action.action_type,
                error=str(e),
            )

            return {
                "status": "failed",
                "error": {
                    "type": type(e).__name__,
                    "message": str(e),
                },
                "action_id": action.id,
            }

    def _get_action_handler(self, action: AutomationAction) -> Optional[Callable]:
        """Get action handler."""
        # Check for custom handler first
        if action.target and action.target in self.custom_handlers:
            return self.custom_handlers[action.target]

        # Check for built-in handler
        return self.action_handlers.get(action.action_type)

    def _prepare_input_data(
        self,
        action: AutomationAction,
        trigger_data: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """Prepare input data for action execution."""
        input_data = action.parameters.model_copy()

        # Apply input mapping
        for target_field, source_field in action.input_mapping.items():
            if source_field in trigger_data:
                input_data[target_field] = trigger_data[source_field]
            elif source_field in context.variables:
                input_data[target_field] = context.variables[source_field]

        return input_data

    def _map_output_data(self, action: AutomationAction, result: Any) -> Dict[str, Any]:
        """Map action output data."""
        if not action.output_mapping:
            return result if isinstance(result, dict) else {"result": result}

        if not isinstance(result, dict):
            result = {"result": result}

        output_data = {}
        for target_field, source_field in action.output_mapping.items():
            if source_field in result:
                output_data[target_field] = result[source_field]

        return output_data


class AutomationEngine:
    """Automation execution engine."""

    def __init__(self):
        """  Init   operation."""
        self.condition_evaluator = ConditionEvaluator()
        self.action_executor = ActionExecutor()
        self.event_listeners: Dict[str, List[str]] = {}  # pattern -> rule_ids

    async def process_trigger(
        self,
        rule: AutomationRule,
        trigger_data: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
    ) -> str:
        """Process automation trigger and execute rule."""
        execution_id = str(uuid.uuid4())

        if not context:
            context = ExecutionContext(
                execution_id=execution_id,
                tenant_id=rule.tenant_id,
                variables=trigger_data.model_copy(),
            )

        execution = AutomationExecution(
            execution_id=execution_id,
            rule_id=rule.id,
            trigger_data=trigger_data,
            context=context,
            started_at=datetime.now(timezone.utc),
        )

        try:
            execution.status = ExecutionStatus.RUNNING

            # Evaluate rule conditions
            if rule.conditions:
                if not self.condition_evaluator.evaluate_conditions(
                    rule.conditions, trigger_data
                ):
                    execution.status = ExecutionStatus.SKIPPED
                    execution.completed_at = datetime.now(timezone.utc)

                    logger.info(
                        "Automation rule skipped - conditions not met",
                        rule_id=rule.id,
                        execution_id=execution_id,
                    )

                    return execution_id

            # Execute actions
            for action in rule.actions:
                action_result = await self.action_executor.execute_action(
                    action, trigger_data, context
                )
                execution.action_results[action.id] = action_result

                # Update context variables with action results
                if (
                    action_result.get("status") == "completed"
                    and "result" in action_result
                ):
                    context.variables.update(action_result["result"])

            execution.status = ExecutionStatus.COMPLETED
            execution.completed_at = datetime.now(timezone.utc)

            logger.info(
                "Automation rule executed successfully",
                rule_id=rule.id,
                execution_id=execution_id,
                actions_count=len(rule.actions),
            )

        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error = ErrorInfo(
                error_type=type(e).__name__,
                message=str(e),
                timestamp=datetime.now(timezone.utc),
            )
            execution.completed_at = datetime.now(timezone.utc)

            logger.error(
                "Automation rule execution failed",
                rule_id=rule.id,
                execution_id=execution_id,
                error=str(e),
            )

        return execution_id

    def register_event_listener(self, event_pattern: str, rule_id: str):
        """Register event listener for a rule."""
        if event_pattern not in self.event_listeners:
            self.event_listeners[event_pattern] = []

        if rule_id not in self.event_listeners[event_pattern]:
            self.event_listeners[event_pattern].append(rule_id)

    def unregister_event_listener(self, event_pattern: str, rule_id: str):
        """Unregister event listener for a rule."""
        if event_pattern in self.event_listeners:
            if rule_id in self.event_listeners[event_pattern]:
                self.event_listeners[event_pattern].remove(rule_id)

            if not self.event_listeners[event_pattern]:
                del self.event_listeners[event_pattern]

    def get_matching_rules(self, event_type: str) -> List[str]:
        """Get rule IDs that match an event type."""
        matching_rules = []

        for pattern, rule_ids in self.event_listeners.items():
            if self._matches_pattern(event_type, pattern):
                matching_rules.extend(rule_ids)

        return matching_rules

    def _matches_pattern(self, event_type: str, pattern: str) -> bool:
        """Check if event type matches pattern."""
        import fnmatch

        return fnmatch.fnmatch(event_type, pattern)


class AutomationSDK:
    """SDK for automation management and execution."""

    def __init__(self, tenant_id: str, storage_adapter=None):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self.storage_adapter = storage_adapter
        self.engine = AutomationEngine()
        self.rules: Dict[str, AutomationRule] = {}
        self.executions: Dict[str, AutomationExecution] = {}
        self.execution_counters: Dict[str, Dict[str, int]] = (
            {}
        )  # rule_id -> {hour: count, day: count}

        logger.info("AutomationSDK initialized", tenant_id=tenant_id)

    async def create_rule(self, rule: AutomationRule) -> str:
        """Create a new automation rule."""
        rule.tenant_id = self.tenant_id
        rule.metadata.updated_at = datetime.now(timezone.utc)

        self.rules[rule.id] = rule

        # Register event listeners
        if (
            rule.trigger.trigger_type == TriggerType.EVENT
            and rule.trigger.event_pattern
        ):
            self.engine.register_event_listener(rule.trigger.event_pattern, rule.id)

        if self.storage_adapter:
            await self.storage_adapter.store_rule(rule)

        logger.info(
            "Automation rule created",
            rule_id=rule.id,
            tenant_id=self.tenant_id,
        )

        return rule.id

    async def update_rule(self, rule: AutomationRule) -> bool:
        """Update an existing automation rule."""
        if rule.id not in self.rules:
            return False

        old_rule = self.rules[rule.id]

        # Update event listeners if pattern changed
        if (
            old_rule.trigger.trigger_type == TriggerType.EVENT
            and old_rule.trigger.event_pattern != rule.trigger.event_pattern
        ):

            if old_rule.trigger.event_pattern:
                self.engine.unregister_event_listener(
                    old_rule.trigger.event_pattern, rule.id
                )

            if rule.trigger.event_pattern:
                self.engine.register_event_listener(rule.trigger.event_pattern, rule.id)

        rule.tenant_id = self.tenant_id
        rule.metadata.updated_at = datetime.now(timezone.utc)
        self.rules[rule.id] = rule

        if self.storage_adapter:
            await self.storage_adapter.store_rule(rule)

        logger.info(
            "Automation rule updated",
            rule_id=rule.id,
            tenant_id=self.tenant_id,
        )

        return True

    async def delete_rule(self, rule_id: str) -> bool:
        """Delete an automation rule."""
        rule = self.rules.get(rule_id)
        if not rule:
            return False

        # Unregister event listeners
        if (
            rule.trigger.trigger_type == TriggerType.EVENT
            and rule.trigger.event_pattern
        ):
            self.engine.unregister_event_listener(rule.trigger.event_pattern, rule_id)

        del self.rules[rule_id]

        if self.storage_adapter:
            await self.storage_adapter.delete_rule(rule_id)

        logger.info(
            "Automation rule deleted",
            rule_id=rule_id,
            tenant_id=self.tenant_id,
        )

        return True

    async def trigger_rule(
        self,
        rule_id: str,
        trigger_data: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
    ) -> Optional[str]:
        """Manually trigger an automation rule."""
        rule = self.rules.get(rule_id)
        if not rule or not rule.enabled:
            return None

        # Check execution limits
        if not self._check_execution_limits(rule):
            logger.warning(
                "Automation rule execution limit exceeded",
                rule_id=rule_id,
                tenant_id=self.tenant_id,
            )
            return None

        execution_id = await self.engine.process_trigger(rule, trigger_data, context)
        self._update_execution_counters(rule_id)

        return execution_id

    async def process_event(
        self, event_type: str, event_data: Dict[str, Any]
    ) -> List[str]:
        """Process an event and trigger matching rules."""
        matching_rule_ids = self.engine.get_matching_rules(event_type)
        execution_ids = []

        for rule_id in matching_rule_ids:
            rule = self.rules.get(rule_id)
            if not rule or not rule.enabled:
                continue

            # Check execution limits
            if not self._check_execution_limits(rule):
                continue

            # Prepare trigger data
            trigger_data = {
                "event_type": event_type,
                "event_data": event_data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            execution_id = await self.engine.process_trigger(rule, trigger_data)
            execution_ids.append(execution_id)
            self._update_execution_counters(rule_id)

        return execution_ids

    def _check_execution_limits(self, rule: AutomationRule) -> bool:
        """Check if rule execution limits are exceeded."""
        if not rule.max_executions_per_hour and not rule.max_executions_per_day:
            return True

        now = datetime.now(timezone.utc)
        hour_key = now.strftime("%Y-%m-%d-%H")
        day_key = now.strftime("%Y-%m-%d")

        counters = self.execution_counters.get(rule.id, {})

        if rule.max_executions_per_hour:
            hour_count = counters.get(f"hour_{hour_key}", 0)
            if hour_count >= rule.max_executions_per_hour:
                return False

        if rule.max_executions_per_day:
            day_count = counters.get(f"day_{day_key}", 0)
            if day_count >= rule.max_executions_per_day:
                return False

        return True

    def _update_execution_counters(self, rule_id: str):
        """Update execution counters for rate limiting."""
        now = datetime.now(timezone.utc)
        hour_key = now.strftime("%Y-%m-%d-%H")
        day_key = now.strftime("%Y-%m-%d")

        if rule_id not in self.execution_counters:
            self.execution_counters[rule_id] = {}

        counters = self.execution_counters[rule_id]
        counters[f"hour_{hour_key}"] = counters.get(f"hour_{hour_key}", 0) + 1
        counters[f"day_{day_key}"] = counters.get(f"day_{day_key}", 0) + 1

        # Clean up old counters (keep last 48 hours)
        cutoff = now - timedelta(hours=48)
        keys_to_remove = []

        for key in counters:
            if key.startswith("hour_"):
                key_time = datetime.strptime(key[5:], "%Y-%m-%d-%H")
                if key_time < cutoff:
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            del counters[key]

    def register_action_handler(self, action_type: ActionType, handler: Callable):
        """Register an action handler."""
        self.engine.action_executor.register_action_handler(action_type, handler)

    def register_custom_handler(self, handler_name: str, handler: Callable):
        """Register a custom action handler."""
        self.engine.action_executor.register_custom_handler(handler_name, handler)

    async def get_execution(self, execution_id: str) -> Optional[AutomationExecution]:
        """Get automation execution by ID."""
        return self.executions.get(execution_id)

    async def list_rules(self, enabled_only: bool = False) -> List[AutomationRule]:
        """List automation rules."""
        rules = list(self.rules.values())

        if enabled_only:
            rules = [rule for rule in rules if rule.enabled]

        return rules
