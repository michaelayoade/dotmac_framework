"""
Policy-as-Code Framework

Provides declarative business rule management with versioning, validation,
and consistent evaluation across the DotMac platform.
"""

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .exceptions import ErrorContext, PolicyViolationError, RuleEvaluationError


class PolicyResult(Enum):
    """Policy evaluation results"""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class RuleOperator(Enum):
    """Supported rule operators"""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX_MATCH = "regex_match"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    BETWEEN = "between"
    NOT_BETWEEN = "not_between"


@dataclass
class PolicyContext:
    """Context for policy evaluation"""

    tenant_id: str
    user_id: Optional[str] = None
    operation: str = ""
    resource_type: str = ""
    resource_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for evaluation"""
        return {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "operation": self.operation,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            **self.metadata,
        }


class PolicyRule(BaseModel):
    """Individual policy rule definition"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    field_path: str = Field(..., min_length=1)  # e.g., "customer.plan_type"
    operator: RuleOperator
    expected_value: Any
    error_message: Optional[str] = None
    is_active: bool = True
    weight: float = Field(default=1.0, ge=0.0, le=10.0)

    def evaluate(self, context_data: dict[str, Any]) -> bool:
        """Evaluate rule against context data"""
        try:
            actual_value = self._get_field_value(context_data, self.field_path)
            return self._apply_operator(actual_value, self.operator, self.expected_value)
        except Exception as e:
            raise RuleEvaluationError(
                message=f"Failed to evaluate rule '{self.name}': {str(e)}",
                rule_name=self.name,
                evaluation_context=context_data,
            ) from e

    def _get_field_value(self, data: dict[str, Any], field_path: str) -> Any:
        """Extract field value using dot notation path"""
        keys = field_path.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            elif hasattr(value, key):
                value = getattr(value, key)
            else:
                return None

        return value

    def _apply_operator(self, actual: Any, operator: RuleOperator, expected: Any) -> bool:
        """Apply operator to compare actual vs expected values"""
        if operator == RuleOperator.EQUALS:
            return actual == expected
        elif operator == RuleOperator.NOT_EQUALS:
            return actual != expected
        elif operator == RuleOperator.GREATER_THAN:
            return actual is not None and actual > expected
        elif operator == RuleOperator.GREATER_THAN_OR_EQUAL:
            return actual is not None and actual >= expected
        elif operator == RuleOperator.LESS_THAN:
            return actual is not None and actual < expected
        elif operator == RuleOperator.LESS_THAN_OR_EQUAL:
            return actual is not None and actual <= expected
        elif operator == RuleOperator.IN:
            return actual in expected if isinstance(expected, (list, tuple, set)) else False
        elif operator == RuleOperator.NOT_IN:
            return actual not in expected if isinstance(expected, (list, tuple, set)) else True
        elif operator == RuleOperator.CONTAINS:
            return expected in actual if hasattr(actual, "__contains__") else False
        elif operator == RuleOperator.NOT_CONTAINS:
            return expected not in actual if hasattr(actual, "__contains__") else True
        elif operator == RuleOperator.IS_NULL:
            return actual is None
        elif operator == RuleOperator.IS_NOT_NULL:
            return actual is not None
        elif operator == RuleOperator.BETWEEN:
            if isinstance(expected, (list, tuple)) and len(expected) == 2:
                return actual is not None and expected[0] <= actual <= expected[1]
            return False
        elif operator == RuleOperator.NOT_BETWEEN:
            if isinstance(expected, (list, tuple)) and len(expected) == 2:
                return actual is None or not (expected[0] <= actual <= expected[1])
            return True
        elif operator == RuleOperator.REGEX_MATCH:
            import re

            return bool(re.match(str(expected), str(actual))) if actual is not None else False
        else:
            raise ValueError(f"Unsupported operator: {operator}")


class BusinessPolicy(BaseModel):
    """Business policy definition with rules and metadata"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    description: Optional[str] = Field(None, max_length=1000)
    category: str = Field(..., min_length=1, max_length=50)

    # Policy evaluation settings
    default_result: PolicyResult = PolicyResult.DENY
    require_all_rules: bool = True  # AND vs OR logic

    # Rules and conditions
    rules: list[PolicyRule] = Field(default_factory=list)

    # Metadata
    effective_from: datetime
    effective_until: Optional[datetime] = None
    is_active: bool = True
    created_by: str
    tags: list[str] = Field(default_factory=list)

    # Computed fields
    policy_hash: Optional[str] = Field(default=None, exclude=True)

    def __post_init__(self):
        """Compute policy hash after initialization"""
        if self.policy_hash is None:
            self.policy_hash = self.compute_hash()

    def compute_hash(self) -> str:
        """Compute hash of policy for change detection"""
        policy_content = {
            "name": self.name,
            "version": self.version,
            "default_result": self.default_result.value,
            "require_all_rules": self.require_all_rules,
            "rules": [
                {
                    "name": rule.name,
                    "field_path": rule.field_path,
                    "operator": rule.operator.value,
                    "expected_value": rule.expected_value,
                    "weight": rule.weight,
                }
                for rule in self.rules
                if rule.is_active
            ],
        }
        content_str = json.dumps(policy_content, sort_keys=True, default=str)
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]

    def evaluate(self, context: PolicyContext, evaluation_data: dict[str, Any]) -> "PolicyEvaluationResult":
        """Evaluate policy against provided context and data"""

        # Check if policy is active and within effective period
        now = datetime.utcnow()
        if not self.is_active:
            return PolicyEvaluationResult(
                policy_name=self.name,
                result=PolicyResult.DENY,
                violated_rules=["policy_inactive"],
                evaluation_time=now,
                context=context,
            )

        if now < self.effective_from:
            return PolicyEvaluationResult(
                policy_name=self.name,
                result=PolicyResult.DENY,
                violated_rules=["policy_not_effective"],
                evaluation_time=now,
                context=context,
            )

        if self.effective_until and now > self.effective_until:
            return PolicyEvaluationResult(
                policy_name=self.name,
                result=PolicyResult.DENY,
                violated_rules=["policy_expired"],
                evaluation_time=now,
                context=context,
            )

        # Prepare evaluation context
        context_data = {**context.to_dict(), **evaluation_data}

        # Evaluate rules
        rule_results = []
        violated_rules = []
        passed_rules = []

        for rule in self.rules:
            if not rule.is_active:
                continue

            try:
                result = rule.evaluate(context_data)
                rule_results.append((rule.name, result, rule.weight))

                if result:
                    passed_rules.append(rule.name)
                else:
                    violated_rules.append(rule.name)

            except Exception:
                violated_rules.append(rule.name)
                rule_results.append((rule.name, False, rule.weight))

        # Determine final result based on require_all_rules setting
        if self.require_all_rules:
            # AND logic - all rules must pass → ALLOW when none violated
            final_result = PolicyResult.ALLOW if not violated_rules else PolicyResult.DENY
        else:
            # OR logic - at least one rule must pass
            final_result = PolicyResult.ALLOW if passed_rules else self.default_result

        return PolicyEvaluationResult(
            policy_name=self.name,
            policy_version=self.version,
            result=final_result,
            rule_results=rule_results,
            passed_rules=passed_rules,
            violated_rules=violated_rules,
            evaluation_time=now,
            context=context,
            total_weight=sum(weight for _, _, weight in rule_results),
            passed_weight=sum(weight for name, result, weight in rule_results if result),
        )


@dataclass
class PolicyEvaluationResult:
    """Result of policy evaluation"""

    policy_name: str
    result: PolicyResult
    violated_rules: list[str]
    evaluation_time: datetime
    context: PolicyContext
    policy_version: str = ""
    rule_results: list[tuple] = field(default_factory=list)  # (rule_name, passed, weight)
    passed_rules: list[str] = field(default_factory=list)
    total_weight: float = 0.0
    passed_weight: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate based on rule weights"""
        if self.total_weight == 0:
            return 0.0
        return self.passed_weight / self.total_weight

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for serialization"""
        return {
            "policy_name": self.policy_name,
            "policy_version": self.policy_version,
            "result": self.result.value,
            "success_rate": self.success_rate,
            "rule_results": self.rule_results,
            "passed_rules": self.passed_rules,
            "violated_rules": self.violated_rules,
            "evaluation_time": self.evaluation_time.isoformat(),
            "total_weight": self.total_weight,
            "passed_weight": self.passed_weight,
            "context": self.context.to_dict(),
            "metadata": self.metadata,
        }


class RuleEvaluator:
    """Type-safe rule evaluation with validation"""

    def __init__(self):
        self.custom_operators: dict[str, Callable] = {}

    def register_operator(self, name: str, func: Callable[[Any, Any], bool]) -> None:
        """Register custom operator function"""
        self.custom_operators[name] = func

    def validate_rule_syntax(self, rule: PolicyRule) -> list[str]:
        """Validate rule syntax and return any errors"""
        errors = []

        if not rule.field_path.strip():
            errors.append("Field path cannot be empty")

        if rule.operator in [RuleOperator.BETWEEN, RuleOperator.NOT_BETWEEN]:
            if not isinstance(rule.expected_value, (list, tuple)) or len(rule.expected_value) != 2:
                errors.append("BETWEEN operators require exactly 2 values")

        if rule.operator in [RuleOperator.IN, RuleOperator.NOT_IN]:
            if not isinstance(rule.expected_value, (list, tuple, set)):
                errors.append("IN operators require a list/tuple/set of values")

        return errors

    def test_rule(self, rule: PolicyRule, test_data: dict[str, Any]) -> dict[str, Any]:
        """Test rule evaluation with provided data"""
        try:
            result = rule.evaluate(test_data)
            return {
                "rule_name": rule.name,
                "passed": result,
                "test_data": test_data,
                "field_value": rule._get_field_value(test_data, rule.field_path),
                "expected_value": rule.expected_value,
                "operator": rule.operator.value,
            }
        except Exception as e:
            return {
                "rule_name": rule.name,
                "passed": False,
                "error": str(e),
                "test_data": test_data,
            }


class PolicyRegistry:
    """Registry for managing business policies with versioning"""

    def __init__(self):
        self.policies: dict[str, dict[str, BusinessPolicy]] = {}  # name -> version -> policy
        self.active_versions: dict[str, str] = {}  # name -> active_version

    def register_policy(self, policy: BusinessPolicy) -> None:
        """Register a business policy"""
        if policy.name not in self.policies:
            self.policies[policy.name] = {}

        self.policies[policy.name][policy.version] = policy

        # Set as active version if it's the first or if explicitly marked active
        if policy.name not in self.active_versions or policy.is_active:
            self.active_versions[policy.name] = policy.version

    def get_policy(self, name: str, version: Optional[str] = None) -> Optional[BusinessPolicy]:
        """Get policy by name and optional version"""
        if name not in self.policies:
            return None

        if version is None:
            version = self.active_versions.get(name)
            if version is None:
                return None

        return self.policies[name].get(version)

    def list_policies(self, category: Optional[str] = None) -> list[BusinessPolicy]:
        """List all active policies, optionally filtered by category"""
        policies = []

        for name, version in self.active_versions.items():
            policy = self.policies[name][version]
            if category is None or policy.category == category:
                policies.append(policy)

        return policies

    def get_policy_versions(self, name: str) -> list[str]:
        """Get all versions of a policy"""
        if name not in self.policies:
            return []
        return list(self.policies[name].keys())


class PolicyEngine:
    """Main policy evaluation engine"""

    def __init__(self, registry: Optional[PolicyRegistry] = None):
        self.registry = registry or PolicyRegistry()
        self.evaluator = RuleEvaluator()

    def evaluate_policy(
        self,
        policy_name: str,
        context: PolicyContext,
        evaluation_data: dict[str, Any],
        version: Optional[str] = None,
    ) -> PolicyEvaluationResult:
        """Evaluate a single policy"""
        policy = self.registry.get_policy(policy_name, version)

        if not policy:
            error_context = ErrorContext(
                operation=context.operation,
                resource_type=context.resource_type,
                resource_id=context.resource_id,
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                correlation_id=context.correlation_id,
            )
            raise PolicyViolationError(
                message=f"Policy '{policy_name}' not found",
                policy_name=policy_name,
                violated_rules=["policy_not_found"],
                context=error_context,
            )

        return policy.evaluate(context, evaluation_data)

    def evaluate_multiple_policies(
        self,
        policy_names: list[str],
        context: PolicyContext,
        evaluation_data: dict[str, Any],
        require_all_pass: bool = True,
    ) -> list[PolicyEvaluationResult]:
        """Evaluate multiple policies"""
        results = []

        for policy_name in policy_names:
            try:
                result = self.evaluate_policy(policy_name, context, evaluation_data)
                results.append(result)
            except Exception as e:
                # Create failed result
                failed_result = PolicyEvaluationResult(
                    policy_name=policy_name,
                    result=PolicyResult.DENY,
                    violated_rules=["evaluation_error"],
                    evaluation_time=datetime.utcnow(),
                    context=context,
                    metadata={"error": str(e)},
                )
                results.append(failed_result)

        # Check if we should raise exception for failures
        if require_all_pass:
            failed_policies = [r for r in results if r.result in [PolicyResult.DENY, PolicyResult.REQUIRE_APPROVAL]]

            if failed_policies:
                error_context = ErrorContext(
                    operation=context.operation,
                    resource_type=context.resource_type,
                    resource_id=context.resource_id,
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                    correlation_id=context.correlation_id,
                )

                all_violated_rules = []
                for result in failed_policies:
                    all_violated_rules.extend(result.violated_rules)

                raise PolicyViolationError(
                    message=f"Multiple policies failed: {[r.policy_name for r in failed_policies]}",
                    policy_name="multiple_policies",
                    violated_rules=all_violated_rules,
                    context=error_context,
                    failed_policies=[r.to_dict() for r in failed_policies],
                )

        return results
