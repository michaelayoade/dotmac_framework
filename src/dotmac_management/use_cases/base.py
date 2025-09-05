"""
Base Use Case Classes
Abstract base classes for implementing use cases
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, Optional, TypeVar

from dotmac_shared.core.logging import get_logger
from dotmac_shared.exceptions import ExceptionContext

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")

logger = get_logger(__name__)


class UseCaseStatus(str, Enum):
    """Use case execution status"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class UseCaseResult(Generic[TOutput]):
    """Standardized use case result"""

    success: bool
    status: UseCaseStatus
    data: Optional[TOutput] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class UseCaseContext:
    """Execution context for use cases"""

    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    permissions: dict[str, Any] = None

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = {}


class UseCase(ABC, Generic[TInput, TOutput]):
    """
    Abstract base class for all use cases.

    A use case represents a single business operation or workflow
    that orchestrates multiple services and infrastructure components
    to achieve a specific business goal.
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    async def execute(
        self, input_data: TInput, context: Optional[UseCaseContext] = None
    ) -> UseCaseResult[TOutput]:
        """
        Execute the use case with the given input data.

        Args:
            input_data: The input data required for the use case
            context: Execution context with user, tenant, and request info

        Returns:
            UseCaseResult containing the operation result
        """
        pass

    async def validate_input(self, input_data: TInput) -> bool:
        """
        Validate the input data before execution.
        Override in subclasses for specific validation logic.

        Args:
            input_data: The input data to validate

        Returns:
            True if valid, False otherwise
        """
        return True

    async def can_execute(self, context: Optional[UseCaseContext] = None) -> bool:
        """
        Check if the use case can be executed in the given context.
        Override in subclasses for permission and business rule checks.

        Args:
            context: Execution context

        Returns:
            True if execution is allowed, False otherwise
        """
        return True

    def _create_success_result(
        self, data: TOutput, metadata: Optional[dict[str, Any]] = None
    ) -> UseCaseResult[TOutput]:
        """Create a successful use case result"""
        return UseCaseResult(
            success=True,
            status=UseCaseStatus.COMPLETED,
            data=data,
            metadata=metadata or {},
        )

    def _create_error_result(
        self,
        error: str,
        error_code: Optional[str] = None,
        status: UseCaseStatus = UseCaseStatus.FAILED,
        metadata: Optional[dict[str, Any]] = None,
    ) -> UseCaseResult[TOutput]:
        """Create a failed use case result"""
        return UseCaseResult(
            success=False,
            status=status,
            error=error,
            error_code=error_code,
            metadata=metadata or {},
        )


class TransactionalUseCase(UseCase[TInput, TOutput], ABC):
    """
    Base class for use cases that require transactional behavior.
    Provides automatic rollback capabilities for complex operations.
    """

    def __init__(self):
        super().__init__()
        self._rollback_actions = []

    async def execute(
        self, input_data: TInput, context: Optional[UseCaseContext] = None
    ) -> UseCaseResult[TOutput]:
        """
        Execute the use case with transaction support.
        Automatically rolls back on failure.
        """
        try:
            if not await self.validate_input(input_data):
                return self._create_error_result(
                    "Input validation failed", error_code="INVALID_INPUT"
                )

            if not await self.can_execute(context):
                return self._create_error_result(
                    "Execution not allowed", error_code="EXECUTION_DENIED"
                )

            # Clear any previous rollback actions
            self._rollback_actions.clear()

            # Execute the main transaction
            result = await self._execute_transaction(input_data, context)

            if not result.success:
                await self._rollback()

            return result

        except ExceptionContext.LIFECYCLE_EXCEPTIONS as e:
            self.logger.error(f"Use case execution failed: {e}")
            await self._rollback()
            return self._create_error_result(str(e), error_code="EXECUTION_ERROR")

    @abstractmethod
    async def _execute_transaction(
        self, input_data: TInput, context: Optional[UseCaseContext] = None
    ) -> UseCaseResult[TOutput]:
        """
        Execute the main transactional logic.
        Register rollback actions using add_rollback_action().
        """
        pass

    def add_rollback_action(self, action):
        """
        Add a rollback action to be executed if the transaction fails.
        Actions are executed in reverse order (last in, first out).

        Args:
            action: Async callable that performs rollback
        """
        self._rollback_actions.append(action)

    async def _rollback(self):
        """Execute all rollback actions in reverse order"""
        self.logger.warning(f"Rolling back {len(self._rollback_actions)} actions")

        for action in reversed(self._rollback_actions):
            try:
                await action()
            except ExceptionContext.LIFECYCLE_EXCEPTIONS as e:
                self.logger.error(f"Rollback action failed: {e}")

        self._rollback_actions.clear()


class CompositeUseCase(UseCase[TInput, TOutput], ABC):
    """
    Base class for use cases that compose multiple other use cases.
    Provides orchestration capabilities for complex business workflows.
    """

    def __init__(self):
        super().__init__()
        self._child_use_cases = []

    def add_use_case(self, use_case: UseCase, condition=None):
        """
        Add a child use case to the composition.

        Args:
            use_case: The use case to add
            condition: Optional condition function to determine if use case should run
        """
        self._child_use_cases.append({"use_case": use_case, "condition": condition})

    async def _execute_child_use_cases(
        self, context: Optional[UseCaseContext] = None
    ) -> dict[str, UseCaseResult]:
        """Execute all child use cases and return their results"""
        results = {}

        for _i, child_config in enumerate(self._child_use_cases):
            use_case = child_config["use_case"]
            condition = child_config["condition"]

            # Check condition if provided
            if condition and not await condition(context):
                continue

            child_name = use_case.__class__.__name__
            try:
                # Note: Child use cases may need their own input data
                # This is a simplified version - implement input mapping in subclasses
                result = await use_case.execute(None, context)
                results[child_name] = result

                # Stop on first failure unless configured otherwise
                if not result.success and self._should_stop_on_failure():
                    break

            except ExceptionContext.LIFECYCLE_EXCEPTIONS as e:
                self.logger.error(f"Child use case {child_name} failed: {e}")
                results[child_name] = UseCaseResult(
                    success=False, status=UseCaseStatus.FAILED, error=str(e)
                )

                if self._should_stop_on_failure():
                    break

        return results

    def _should_stop_on_failure(self) -> bool:
        """
        Override to control whether execution should stop on first child failure.
        Default is True for safety.
        """
        return True
