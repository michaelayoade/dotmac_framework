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

from .policies import (
    PolicyEngine,
    PolicyResult,
    PolicyContext,
    RuleEvaluator,
    BusinessPolicy,
    PolicyRegistry
)
from .idempotency import (
    IdempotencyManager,
    IdempotencyKey,
    IdempotentOperation,
    OperationResult,
    OperationStatus
)
from .sagas import (
    SagaCoordinator,
    SagaStep,
    SagaDefinition,
    CompensationHandler,
    SagaContext,
    SagaStatus
)
from .exceptions import (
    BusinessLogicError,
    PolicyViolationError,
    IdempotencyError,
    SagaError,
    RuleEvaluationError
)

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