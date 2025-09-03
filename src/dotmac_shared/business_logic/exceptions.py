"""
Business Logic Framework Exceptions

Provides structured exception hierarchy for business rule violations,
idempotency conflicts, and saga orchestration failures.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels for business logic violations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for business logic errors"""
    operation: str
    resource_type: str
    resource_id: str
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = None


class BusinessLogicError(Exception):
    """Base exception for all business logic errors"""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        context: Optional[ErrorContext] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context
        self.severity = severity
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "severity": self.severity.value,
            "context": {
                "operation": self.context.operation if self.context else None,
                "resource_type": self.context.resource_type if self.context else None,
                "resource_id": self.context.resource_id if self.context else None,
                "tenant_id": self.context.tenant_id if self.context else None,
                "user_id": self.context.user_id if self.context else None,
                "correlation_id": self.context.correlation_id if self.context else None,
                "metadata": self.context.metadata if self.context else {}
            },
            "details": self.details
        }


class PolicyViolationError(BusinessLogicError):
    """Raised when a business policy is violated"""
    
    def __init__(
        self,
        message: str,
        policy_name: str,
        violated_rules: List[str],
        context: Optional[ErrorContext] = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code=f"POLICY_VIOLATION_{policy_name.upper()}",
            context=context,
            severity=severity,
            details={
                "policy_name": policy_name,
                "violated_rules": violated_rules,
                **kwargs
            }
        )
        self.policy_name = policy_name
        self.violated_rules = violated_rules


class RuleEvaluationError(BusinessLogicError):
    """Raised when a business rule cannot be evaluated"""
    
    def __init__(
        self,
        message: str,
        rule_name: str,
        evaluation_context: Dict[str, Any],
        context: Optional[ErrorContext] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code=f"RULE_EVALUATION_ERROR_{rule_name.upper()}",
            context=context,
            severity=ErrorSeverity.MEDIUM,
            details={
                "rule_name": rule_name,
                "evaluation_context": evaluation_context,
                **kwargs
            }
        )
        self.rule_name = rule_name
        self.evaluation_context = evaluation_context


class IdempotencyError(BusinessLogicError):
    """Raised when idempotency constraints are violated"""
    
    def __init__(
        self,
        message: str,
        idempotency_key: str,
        operation: str,
        conflict_reason: str,
        context: Optional[ErrorContext] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="IDEMPOTENCY_VIOLATION",
            context=context,
            severity=ErrorSeverity.HIGH,
            details={
                "idempotency_key": idempotency_key,
                "operation": operation,
                "conflict_reason": conflict_reason,
                **kwargs
            }
        )
        self.idempotency_key = idempotency_key
        self.operation = operation
        self.conflict_reason = conflict_reason


class SagaError(BusinessLogicError):
    """Raised when saga orchestration fails"""
    
    def __init__(
        self,
        message: str,
        saga_id: str,
        step_name: Optional[str] = None,
        compensation_failed: bool = False,
        context: Optional[ErrorContext] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="SAGA_ORCHESTRATION_ERROR",
            context=context,
            severity=ErrorSeverity.CRITICAL if compensation_failed else ErrorSeverity.HIGH,
            details={
                "saga_id": saga_id,
                "step_name": step_name,
                "compensation_failed": compensation_failed,
                **kwargs
            }
        )
        self.saga_id = saga_id
        self.step_name = step_name
        self.compensation_failed = compensation_failed


class PlanEligibilityError(PolicyViolationError):
    """Raised when plan eligibility requirements are not met"""
    
    def __init__(
        self,
        message: str,
        plan_name: str,
        customer_id: str,
        failed_requirements: List[str],
        context: Optional[ErrorContext] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            policy_name="plan_eligibility",
            violated_rules=failed_requirements,
            context=context,
            severity=ErrorSeverity.MEDIUM,
            customer_id=customer_id,
            plan_name=plan_name,
            failed_requirements=failed_requirements,
            **kwargs
        )
        self.plan_name = plan_name
        self.customer_id = customer_id
        self.failed_requirements = failed_requirements


class CommissionPolicyError(PolicyViolationError):
    """Raised when commission policy rules are violated"""
    
    def __init__(
        self,
        message: str,
        commission_config_id: str,
        partner_id: str,
        violated_constraints: List[str],
        context: Optional[ErrorContext] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            policy_name="commission_rules",
            violated_rules=violated_constraints,
            context=context,
            severity=ErrorSeverity.HIGH,
            commission_config_id=commission_config_id,
            partner_id=partner_id,
            violated_constraints=violated_constraints,
            **kwargs
        )
        self.commission_config_id = commission_config_id
        self.partner_id = partner_id
        self.violated_constraints = violated_constraints


class LicensingError(PolicyViolationError):
    """Raised when software licensing constraints are violated"""
    
    def __init__(
        self,
        message: str,
        license_type: str,
        tenant_id: str,
        usage_limit: int,
        current_usage: int,
        context: Optional[ErrorContext] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            policy_name="licensing_limits",
            violated_rules=[f"usage_limit_exceeded"],
            context=context,
            severity=ErrorSeverity.HIGH,
            license_type=license_type,
            tenant_id=tenant_id,
            usage_limit=usage_limit,
            current_usage=current_usage,
            **kwargs
        )
        self.license_type = license_type
        self.tenant_id = tenant_id
        self.usage_limit = usage_limit
        self.current_usage = current_usage


class ProvisioningError(BusinessLogicError):
    """Raised when service or tenant provisioning fails"""
    
    def __init__(
        self,
        message: str,
        provisioning_type: str,  # 'tenant' or 'service'
        target_id: str,
        step_failed: Optional[str] = None,
        rollback_required: bool = True,
        context: Optional[ErrorContext] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code=f"{provisioning_type.upper()}_PROVISIONING_ERROR",
            context=context,
            severity=ErrorSeverity.HIGH,
            details={
                "provisioning_type": provisioning_type,
                "target_id": target_id,
                "step_failed": step_failed,
                "rollback_required": rollback_required,
                **kwargs
            }
        )
        self.provisioning_type = provisioning_type
        self.target_id = target_id
        self.step_failed = step_failed
        self.rollback_required = rollback_required


class BillingRunError(BusinessLogicError):
    """Raised when billing run operations fail"""
    
    def __init__(
        self,
        message: str,
        billing_period: str,
        tenant_id: Optional[str] = None,
        customer_count: int = 0,
        failed_customers: List[str] = None,
        context: Optional[ErrorContext] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="BILLING_RUN_ERROR",
            context=context,
            severity=ErrorSeverity.CRITICAL,
            details={
                "billing_period": billing_period,
                "tenant_id": tenant_id,
                "customer_count": customer_count,
                "failed_customers": failed_customers or [],
                **kwargs
            }
        )
        self.billing_period = billing_period
        self.tenant_id = tenant_id
        self.customer_count = customer_count
        self.failed_customers = failed_customers or []