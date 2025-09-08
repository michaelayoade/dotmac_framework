"""
DotMac Business Logic Framework

This module provides policy-as-code and idempotency/saga patterns for
consistent business rule management across the platform.

Key Components:
- Policy Engine: Declarative business rules with versioning
- Idempotency Manager: Ensures operations can be safely retried
- Saga Coordinator: Manages distributed transactions across services
- Rule Evaluator: Type-safe policy evaluation framework
"""

from .exceptions import (BusinessLogicError, IdempotencyError,
                         PolicyViolationError, RuleEvaluationError, SagaError)
from .idempotency import (IdempotencyKey, IdempotencyManager,
                          IdempotentOperation, OperationResult,
                          OperationStatus)
from .policies import (BusinessPolicy, PolicyContext, PolicyEngine,
                       PolicyRegistry, PolicyResult, RuleEvaluator)
# Policy engines are available through lazy loading in policies module
from .sagas import (CompensationHandler, SagaContext, SagaCoordinator,
                    SagaDefinition, SagaStatus, SagaStep)

__all__ = [
    # Policy Framework
    "PolicyEngine",
    "PolicyResult",
    "PolicyContext",
    "RuleEvaluator",
    "BusinessPolicy",
    "PolicyRegistry",
    # Idempotency
    "IdempotencyManager",
    "IdempotencyKey",
    "IdempotentOperation",
    "OperationResult",
    "OperationStatus",
    # Sagas
    "SagaCoordinator",
    "SagaStep",
    "SagaDefinition",
    "CompensationHandler",
    "SagaContext",
    "SagaStatus",
    # Exceptions
    "BusinessLogicError",
    "PolicyViolationError",
    "IdempotencyError",
    "SagaError",
    "RuleEvaluationError",
]
