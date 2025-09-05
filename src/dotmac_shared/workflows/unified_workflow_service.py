"""
Unified Workflow Service
Consolidates workflow operations using DRY patterns from dotmac_shared
Eliminates code duplication between automation.py, task.py, and project workflows
"""

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from ..services_framework.core.base import BaseService

try:
    from ..core.decorators import async_retry, standard_exception_handler
except Exception:  # pragma: no cover - fallback if decorators not present
    def standard_exception_handler(func=None, *dargs, **dkwargs):  # type: ignore
        def _decorate(f):
            return f
        return _decorate if func is None else func

    def async_retry(*dargs, **dkwargs):  # type: ignore
        def _decorate(f):
            return f
        return _decorate
try:
    from ..monitoring.performance import performance_monitor
except Exception:  # pragma: no cover - fallback for environments without performance module
    def performance_monitor(_name: str):  # type: ignore
        def _decorator(func):
            return func
        return _decorator
import asyncio

from .base import BaseWorkflow, WorkflowResult
from .exceptions import WorkflowError, WorkflowTransientError, WorkflowValidationError

logger = logging.getLogger(__name__)


class WorkflowType(str, Enum):
    """Unified workflow types."""

    AUTOMATION = "automation"
    PROJECT = "project"
    TASK = "task"
    BUSINESS_RULE = "business_rule"
    INTEGRATION = "integration"


class TriggerType(str, Enum):
    """Unified trigger types."""

    EVENT = "event"
    SCHEDULE = "schedule"
    CONDITION = "condition"
    WEBHOOK = "webhook"
    MANUAL = "manual"
    API_CALL = "api_call"


class ActionType(str, Enum):
    """Unified action types."""

    NOTIFICATION = "notification"
    API_CALL = "api_call"
    DATABASE_UPDATE = "database_update"
    FILE_OPERATION = "file_operation"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    CUSTOM = "custom"


class WorkflowContext:
    """Unified workflow execution context."""

    def __init__(
        self,
        workflow_id: str,
        tenant_id: str,
        user_id: str,
        portal: Optional[str] = None,
        variables: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        self.workflow_id = workflow_id
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.portal = portal
        self.variables = variables or {}
        self.metadata = metadata or {}
        self.created_at = datetime.now(timezone.utc)

    def get(self, key: str, default: Any = None) -> Any:
        """Get variable value with fallback."""
        return self.variables.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set variable value."""
        self.variables[key] = value

    def update_metadata(self, key: str, value: Any) -> None:
        """Update metadata."""
        self.metadata[key] = value


class UnifiedWorkflowRule:
    """Unified rule definition for all workflow types."""

    def __init__(
        self,
        rule_id: str,
        name: str,
        workflow_type: WorkflowType,
        trigger_type: TriggerType,
        conditions: Optional[list[dict[str, Any]]] = None,
        actions: Optional[list[dict[str, Any]]] = None,
        enabled: bool = True,
        priority: int = 100,
        metadata: Optional[dict[str, Any]] = None,
    ):
        self.rule_id = rule_id
        self.name = name
        self.workflow_type = workflow_type
        self.trigger_type = trigger_type
        self.conditions = conditions or []
        self.actions = actions or []
        self.enabled = enabled
        self.priority = priority
        self.metadata = metadata or {}
        self.created_at = datetime.now(timezone.utc)
        self.last_executed = None
        self.execution_count = 0

    def matches(self, context: WorkflowContext) -> bool:
        """Check if rule matches the context."""
        if not self.enabled:
            return False

        for condition in self.conditions:
            if not self._evaluate_condition(condition, context):
                return False

        return True

    def _evaluate_condition(self, condition: dict[str, Any], context: WorkflowContext) -> bool:
        """Evaluate a single condition."""
        field = condition.get("field")
        operator = condition.get("operator", "equals")
        expected = condition.get("value")

        # Get actual value from context
        actual = self._get_context_value(context, field)

        # Apply operator
        if operator == "equals":
            return actual == expected
        elif operator == "not_equals":
            return actual != expected
        elif operator == "greater_than":
            return actual > expected
        elif operator == "less_than":
            return actual < expected
        elif operator == "contains":
            return expected in str(actual)
        elif operator == "exists":
            return actual is not None
        elif operator == "in":
            return actual in expected if isinstance(expected, list) else False
        else:
            logger.warning(f"Unknown operator: {operator}")
            return False

    def _get_context_value(self, context: WorkflowContext, field: str) -> Any:
        """Get value from context using dot notation."""
        if not field:
            return None

        parts = field.split(".")
        value = context

        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict):
                value = value.get(part)
            else:
                return None

        return value


class UnifiedWorkflowService(BaseService):
    """
    Unified service for all workflow operations.
    Implements DRY patterns and consolidates functionality.
    """

    def __init__(self):
        super().__init__("unified_workflow")
        self.rules: list[UnifiedWorkflowRule] = []
        self.action_handlers: dict[ActionType, Callable] = {}
        self.workflow_instances: dict[str, BaseWorkflow] = {}
        self._register_default_handlers()

    @standard_exception_handler
    @performance_monitor("workflow_service_init")
    async def initialize(self) -> bool:
        """Initialize the workflow service."""
        await super()._set_status(self.get_status(), "Initializing Unified Workflow Service")
        logger.info("Unified Workflow Service initialized")
        return True

    @standard_exception_handler
    @async_retry(max_attempts=3, delay=1.0)
    async def execute_workflow(
        self, workflow_type: WorkflowType, context: WorkflowContext, rules: Optional[list[UnifiedWorkflowRule]] = None
    ) -> list[WorkflowResult]:
        """Execute workflows based on type and context."""

        # Use provided rules or find matching ones
        applicable_rules = rules or self._find_matching_rules(workflow_type, context)

        if not applicable_rules:
            return []

        # Sort by priority
        applicable_rules.sort(key=lambda r: r.priority, reverse=True)

        results = []

        for rule in applicable_rules:
            try:
                if rule.matches(context):
                    result = await self._execute_rule(rule, context)
                    results.append(result)

                    # Update rule statistics
                    rule.last_executed = datetime.now(timezone.utc)
                    rule.execution_count += 1

            except (WorkflowValidationError, ValueError, KeyError, TypeError) as e:
                logger.error(f"Rule validation failed {rule.name}: {e}")
                results.append(
                    WorkflowResult(
                        success=False,
                        step_name=f"rule_{rule.rule_id}",
                        error=str(e),
                        message=f"Rule validation failed: {rule.name}",
                        code="validation_error",
                    )
                )
            except (WorkflowTransientError, TimeoutError, ConnectionError, asyncio.TimeoutError) as e:
                logger.error(f"Rule transient failure {rule.name}: {e}")
                results.append(
                    WorkflowResult(
                        success=False,
                        step_name=f"rule_{rule.rule_id}",
                        error=str(e),
                        message=f"Rule transient failure: {rule.name}",
                        code="transient_error",
                    )
                )
            except WorkflowError as e:
                logger.error(f"Rule execution error {rule.name}: {e}")
                results.append(
                    WorkflowResult(
                        success=False,
                        step_name=f"rule_{rule.rule_id}",
                        error=str(e),
                        message=f"Rule execution failed: {rule.name}",
                        code="workflow_error",
                    )
                )
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 - resilience boundary; logs and continues
                logger.error(f"Error executing rule {rule.name}: {e}")
                results.append(
                    WorkflowResult(
                        success=False,
                        step_name=f"rule_{rule.rule_id}",
                        error=str(e),
                        message=f"Rule execution failed: {rule.name}",
                        code="unexpected_error",
                    )
                )

        return results

    @standard_exception_handler
    async def shutdown(self) -> bool:
        await super()._set_status(self.get_status(), "Shutting down Unified Workflow Service")
        return True

    @standard_exception_handler
    async def health_check(self):
        # Minimal health details
        return {"status": "ok"}

    @standard_exception_handler
    async def create_workflow_instance(
        self, workflow_type: WorkflowType, workflow_id: str, steps: list[str], context: WorkflowContext
    ) -> str:
        """Create a new workflow instance."""

        instance = UnifiedWorkflowInstance(
            workflow_id=workflow_id, workflow_type=workflow_type, steps=steps, context=context
        )

        instance_id = str(uuid4())
        self.workflow_instances[instance_id] = instance

        logger.info(f"Created workflow instance {instance_id} of type {workflow_type}")
        return instance_id

    @standard_exception_handler
    async def execute_workflow_instance(self, instance_id: str) -> list[WorkflowResult]:
        """Execute a workflow instance."""

        instance = self.workflow_instances.get(instance_id)
        if not instance:
            raise WorkflowError(f"Workflow instance {instance_id} not found")

        return await instance.execute()

    @standard_exception_handler
    async def add_rule(self, rule: UnifiedWorkflowRule) -> None:
        """Add a workflow rule."""
        self.rules.append(rule)
        logger.info(f"Added workflow rule: {rule.name}")

    @standard_exception_handler
    async def remove_rule(self, rule_id: str) -> None:
        """Remove a workflow rule."""
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        logger.info(f"Removed workflow rule: {rule_id}")

    @standard_exception_handler
    def register_action_handler(self, action_type: ActionType, handler: Callable) -> None:
        """Register an action handler."""
        self.action_handlers[action_type] = handler
        logger.info(f"Registered action handler for: {action_type}")

    def _find_matching_rules(self, workflow_type: WorkflowType, context: WorkflowContext) -> list[UnifiedWorkflowRule]:
        """Find rules matching the workflow type."""
        return [rule for rule in self.rules if rule.workflow_type == workflow_type and rule.enabled]

    async def _execute_rule(self, rule: UnifiedWorkflowRule, context: WorkflowContext) -> WorkflowResult:
        """Execute a single rule."""

        executed_actions = []
        errors = []

        for action in rule.actions:
            try:
                action_type = ActionType(action.get("type", "custom"))
                handler = self.action_handlers.get(action_type)

                if not handler:
                    errors.append(f"No handler for action type: {action_type}")
                    continue

                action_result = await handler(action, context)
                executed_actions.append({"type": action_type, "result": action_result, "success": True})

            except (WorkflowValidationError, ValueError, KeyError, TypeError) as e:
                error_msg = f"Action {action.get('type')} validation failed: {str(e)}"
                errors.append(error_msg)
                executed_actions.append({"type": action.get("type"), "error": str(e), "success": False})
            except (WorkflowTransientError, TimeoutError, ConnectionError, asyncio.TimeoutError) as e:
                error_msg = f"Action {action.get('type')} transient failure: {str(e)}"
                errors.append(error_msg)
                executed_actions.append({"type": action.get("type"), "error": str(e), "success": False})
            except WorkflowError as e:
                error_msg = f"Action {action.get('type')} workflow error: {str(e)}"
                errors.append(error_msg)
                executed_actions.append({"type": action.get("type"), "error": str(e), "success": False})
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 - resilience boundary for action execution
                error_msg = f"Action {action.get('type')} failed: {str(e)}"
                errors.append(error_msg)
                executed_actions.append({"type": action.get("type"), "error": str(e), "success": False})

        success = len(errors) == 0
        return WorkflowResult(
            success=success,
            step_name=f"rule_{rule.rule_id}",
            data={
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "executed_actions": executed_actions,
                "success_count": len([a for a in executed_actions if a["success"]]),
                "error_count": len(errors),
            },
            error="; ".join(errors) if errors else None,
            message=f"Executed {len(executed_actions)} actions for rule: {rule.name}",
        )

    def _register_default_handlers(self):
        """Register default action handlers."""

        async def notification_handler(action: dict[str, Any], context: WorkflowContext) -> str:
            recipient = action.get("recipient", "system")
            message = action.get("message", "Workflow notification")
            logger.info(f"NOTIFICATION to {recipient}: {message}")
            return f"Notification sent to {recipient}"

        async def api_call_handler(action: dict[str, Any], context: WorkflowContext) -> dict[str, Any]:
            url = action.get("url", "")
            method = action.get("method", "GET")
            logger.info(f"API CALL {method} to {url}")
            return {"status": "called", "url": url, "method": method}

        async def database_update_handler(action: dict[str, Any], context: WorkflowContext) -> dict[str, Any]:
            table = action.get("table", "")
            operation = action.get("operation", "update")
            logger.info(f"DATABASE {operation} on {table}")
            return {"status": "updated", "table": table, "operation": operation}

        # Register handlers
        self.register_action_handler(ActionType.NOTIFICATION, notification_handler)
        self.register_action_handler(ActionType.API_CALL, api_call_handler)
        self.register_action_handler(ActionType.DATABASE_UPDATE, database_update_handler)


class UnifiedWorkflowInstance(BaseWorkflow):
    """Unified workflow instance that works with all workflow types."""

    def __init__(self, workflow_id: str, workflow_type: WorkflowType, steps: list[str], context: WorkflowContext):
        super().__init__(workflow_id, workflow_type.value, steps)
        self.workflow_type = workflow_type
        self.context = context

    @standard_exception_handler
    async def execute_step(self, step_name: str) -> WorkflowResult:
        """Execute a single step based on workflow type."""

        if self.workflow_type == WorkflowType.AUTOMATION:
            return await self._execute_automation_step(step_name)
        elif self.workflow_type == WorkflowType.PROJECT:
            return await self._execute_project_step(step_name)
        elif self.workflow_type == WorkflowType.TASK:
            return await self._execute_task_step(step_name)
        else:
            return await self._execute_generic_step(step_name)

    async def _execute_automation_step(self, step_name: str) -> WorkflowResult:
        """Execute automation-specific step."""
        logger.info(f"Executing automation step: {step_name}")
        return WorkflowResult(success=True, step_name=step_name, message=f"Automation step completed: {step_name}")

    async def _execute_project_step(self, step_name: str) -> WorkflowResult:
        """Execute project-specific step."""
        logger.info(f"Executing project step: {step_name}")
        return WorkflowResult(success=True, step_name=step_name, message=f"Project step completed: {step_name}")

    async def _execute_task_step(self, step_name: str) -> WorkflowResult:
        """Execute task-specific step."""
        logger.info(f"Executing task step: {step_name}")
        return WorkflowResult(success=True, step_name=step_name, message=f"Task step completed: {step_name}")

    async def _execute_generic_step(self, step_name: str) -> WorkflowResult:
        """Execute generic step."""
        logger.info(f"Executing generic step: {step_name}")
        return WorkflowResult(success=True, step_name=step_name, message=f"Generic step completed: {step_name}")


# Factory functions using DRY patterns
def create_automation_rule(
    rule_id: str, name: str, conditions: list[dict[str, Any]], actions: list[dict[str, Any]], **kwargs
) -> UnifiedWorkflowRule:
    """Create an automation rule."""
    return UnifiedWorkflowRule(
        rule_id=rule_id,
        name=name,
        workflow_type=WorkflowType.AUTOMATION,
        trigger_type=TriggerType.EVENT,
        conditions=conditions,
        actions=actions,
        **kwargs,
    )


def create_project_rule(
    rule_id: str, name: str, conditions: list[dict[str, Any]], actions: list[dict[str, Any]], **kwargs
) -> UnifiedWorkflowRule:
    """Create a project rule."""
    return UnifiedWorkflowRule(
        rule_id=rule_id,
        name=name,
        workflow_type=WorkflowType.PROJECT,
        trigger_type=TriggerType.EVENT,
        conditions=conditions,
        actions=actions,
        **kwargs,
    )


def create_business_rule(
    rule_id: str, name: str, conditions: list[dict[str, Any]], actions: list[dict[str, Any]], **kwargs
) -> UnifiedWorkflowRule:
    """Create a business rule."""
    return UnifiedWorkflowRule(
        rule_id=rule_id,
        name=name,
        workflow_type=WorkflowType.BUSINESS_RULE,
        trigger_type=TriggerType.CONDITION,
        conditions=conditions,
        actions=actions,
        **kwargs,
    )


# Singleton service instance
_unified_workflow_service: Optional[UnifiedWorkflowService] = None


async def get_unified_workflow_service() -> UnifiedWorkflowService:
    """Get the singleton workflow service instance."""
    global _unified_workflow_service

    if _unified_workflow_service is None:
        _unified_workflow_service = UnifiedWorkflowService()
        await _unified_workflow_service.initialize()

    return _unified_workflow_service
