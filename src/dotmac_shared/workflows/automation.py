"""
Automation workflow implementation.

Provides event-driven automation workflows based on rules and triggers.
"""

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from .base import BaseWorkflow, WorkflowResult
from .exceptions import WorkflowValidationError


class TriggerType(str, Enum):
    """Types of automation triggers."""

    EVENT = "event"
    SCHEDULE = "schedule"
    CONDITION = "condition"
    WEBHOOK = "webhook"
    MANUAL = "manual"


class AutomationRule:
    """
    Defines an automation rule with trigger conditions and actions.
    """

    def __init__(
        self,
        name: str,
        trigger_type: TriggerType,
        conditions: Dict[str, Any] = None,
        actions: List[Dict[str, Any]] = None,
        enabled: bool = True,
        priority: int = 100,
        metadata: Dict[str, Any] = None,
    ):
        self.name = name
        self.trigger_type = trigger_type
        self.conditions = conditions or {}
        self.actions = actions or []
        self.enabled = enabled
        self.priority = priority
        self.metadata = metadata or {}
        self.created_at = datetime.now(timezone.utc)
        self.last_triggered = None
        self.trigger_count = 0

    def matches(self, event_data: Dict[str, Any]) -> bool:
        """Check if this rule matches the given event data."""
        if not self.enabled:
            return False

        # Simple condition matching - can be extended with complex logic
        for condition_key, expected_value in self.conditions.items():
            actual_value = event_data.get(condition_key)

            if isinstance(expected_value, list):
                if actual_value not in expected_value:
                    return False
            elif isinstance(expected_value, dict):
                # Handle operators like {'>=': 100}, {'contains': 'error'}
                if not self._check_condition_operators(actual_value, expected_value):
                    return False
            elif expected_value != actual_value:
                return False

        return True

    def _check_condition_operators(
        self, actual_value: Any, condition: Dict[str, Any]
    ) -> bool:
        """Check condition with operators."""
        for operator, expected in condition.items():
            if operator == ">=":
                return actual_value >= expected
            elif operator == "<=":
                return actual_value <= expected
            elif operator == ">":
                return actual_value > expected
            elif operator == "<":
                return actual_value < expected
            elif operator == "!=":
                return actual_value != expected
            elif operator == "contains":
                return expected in str(actual_value)
            elif operator == "startswith":
                return str(actual_value).startswith(str(expected))
            elif operator == "endswith":
                return str(actual_value).endswith(str(expected))
            elif operator == "in":
                return actual_value in expected
            elif operator == "not_in":
                return actual_value not in expected
        return False


class AutomationWorkflow(BaseWorkflow):
    """
    Automation workflow that executes actions based on rules and events.
    """

    def __init__(
        self,
        automation_name: str,
        rules: List[AutomationRule] = None,
        workflow_id: Optional[str] = None,
    ):
        self.automation_name = automation_name
        self.rules = rules or []
        self.action_handlers: Dict[str, Callable] = {}

        # Generate steps from rules
        steps = [f"execute_rule_{rule.name}" for rule in self.rules]

        super().__init__(
            workflow_id=workflow_id or f"automation_{automation_name}",
            workflow_type="automation",
            steps=steps,
        )

    def add_rule(self, rule: AutomationRule):
        """Add an automation rule."""
        self.rules.append(rule)
        self.steps.append(f"execute_rule_{rule.name}")

    def remove_rule(self, rule_name: str):
        """Remove an automation rule by name."""
        self.rules = [rule for rule in self.rules if rule.name != rule_name]
        self.steps = [f"execute_rule_{rule.name}" for rule in self.rules]

    def register_action_handler(self, action_type: str, handler: Callable):
        """Register a handler for a specific action type."""
        self.action_handlers[action_type] = handler

    async def trigger(self, event_data: Dict[str, Any]) -> List[WorkflowResult]:
        """
        Trigger automation based on event data.

        Args:
            event_data: Event data to match against rules

        Returns:
            List of workflow results for triggered actions
        """
        results = []

        # Find matching rules
        matching_rules = [rule for rule in self.rules if rule.matches(event_data)]

        # Sort by priority
        matching_rules.sort(key=lambda x: x.priority)

        # Execute actions for matching rules
        for rule in matching_rules:
            rule.last_triggered = datetime.now(timezone.utc)
            rule.trigger_count += 1

            result = await self._execute_rule_actions(rule, event_data)
            results.append(result)

        return results

    async def execute_step(self, step_name: str) -> WorkflowResult:
        """Execute a step (rule) in the automation workflow."""
        # Extract rule name from step name
        if not step_name.startswith("execute_rule_"):
            return WorkflowResult(
                success=False,
                step_name=step_name,
                error="Invalid step name",
                message=f"Expected step to start with 'execute_rule_', got '{step_name}'",
            )

        rule_name = step_name[len("execute_rule_") :]
        rule = next((r for r in self.rules if r.name == rule_name), None)

        if not rule:
            return WorkflowResult(
                success=False,
                step_name=step_name,
                error="Rule not found",
                message=f"Rule '{rule_name}' not found",
            )

        return await self._execute_rule_actions(rule, {})

    async def _execute_rule_actions(
        self, rule: AutomationRule, event_data: Dict[str, Any]
    ) -> WorkflowResult:
        """Execute all actions for a rule."""
        executed_actions = []
        errors = []

        for action in rule.actions:
            try:
                action_type = action.get("type")
                action_handler = self.action_handlers.get(action_type)

                if not action_handler:
                    errors.append(f"No handler for action type '{action_type}'")
                    continue

                # Execute action handler
                action_result = await self._call_action_handler(
                    action_handler, action, event_data
                )

                executed_actions.append(
                    {"type": action_type, "result": action_result, "success": True}
                )

            except Exception as e:
                error_msg = f"Action '{action.get('type')}' failed: {str(e)}"
                errors.append(error_msg)
                executed_actions.append(
                    {"type": action.get("type"), "error": str(e), "success": False}
                )

        success = len(errors) == 0
        return WorkflowResult(
            success=success,
            step_name=f"execute_rule_{rule.name}",
            data={
                "rule_name": rule.name,
                "executed_actions": executed_actions,
                "action_count": len(rule.actions),
                "success_count": len([a for a in executed_actions if a["success"]]),
                "error_count": len(errors),
            },
            error="; ".join(errors) if errors else None,
            message=f"Executed {len(executed_actions)} actions for rule '{rule.name}'",
        )

    async def _call_action_handler(
        self, handler: Callable, action: Dict[str, Any], event_data: Dict[str, Any]
    ) -> Any:
        """Call an action handler, handling both sync and async functions."""
        if asyncio.iscoroutinefunction(handler):
            return await handler(action, event_data)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: handler(action, event_data))


# Built-in action handlers
async def log_action_handler(action: Dict[str, Any], event_data: Dict[str, Any]) -> str:
    """Built-in handler for logging actions."""
    message = action.get("message", "Automation triggered")
    level = action.get("level", "info")

    # In a real implementation, this would use proper logging
    print(f"[{level.upper()}] {message} - Event: {event_data}")

    return f"Logged message at {level} level"


async def notification_action_handler(
    action: Dict[str, Any], event_data: Dict[str, Any]
) -> str:
    """Built-in handler for notification actions."""
    recipient = action.get("recipient", "system")
    message = action.get("message", "Automation notification")

    # In a real implementation, this would send actual notifications
    print(f"NOTIFICATION to {recipient}: {message}")

    return f"Notification sent to {recipient}"


async def webhook_action_handler(
    action: Dict[str, Any], event_data: Dict[str, Any]
) -> str:
    """Built-in handler for webhook actions."""
    url = action.get("url", "")
    method = action.get("method", "POST")

    # In a real implementation, this would make HTTP requests
    print(f"WEBHOOK {method} to {url} with data: {event_data}")

    return f"Webhook {method} request to {url}"


# Factory functions
def create_automation_workflow(
    name: str, rules: List[AutomationRule] = None
) -> AutomationWorkflow:
    """Create an automation workflow with built-in action handlers."""
    workflow = AutomationWorkflow(name, rules)

    # Register built-in handlers
    workflow.register_action_handler("log", log_action_handler)
    workflow.register_action_handler("notification", notification_action_handler)
    workflow.register_action_handler("webhook", webhook_action_handler)

    return workflow


def create_simple_rule(
    name: str,
    conditions: Dict[str, Any],
    actions: List[Dict[str, Any]],
    enabled: bool = True,
) -> AutomationRule:
    """Create a simple automation rule."""
    return AutomationRule(
        name=name,
        trigger_type=TriggerType.EVENT,
        conditions=conditions,
        actions=actions,
        enabled=enabled,
    )
