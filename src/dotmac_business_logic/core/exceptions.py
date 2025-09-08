"""
Standardized exception handling patterns for DotMac Business Logic package.
Provides consistent error handling across tasks, billing, and files modules.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""

    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    SECURITY = "security"
    SYSTEM = "system"


class BusinessLogicError(Exception):
    """Base exception for all business logic errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        category: ErrorCategory = ErrorCategory.BUSINESS_LOGIC,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[dict[str, Any]] = None,
        retry_able: bool = False,
        user_message: Optional[str] = None,
    ):
        super().__init__(message)
        self.error_id = str(uuid4())
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.retry_able = retry_able
        self.user_message = user_message or "An error occurred while processing your request."
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_id": self.error_id,
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "retry_able": self.retry_able,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "type": self.__class__.__name__,
        }


# Billing-specific exceptions
class BillingError(BusinessLogicError):
    """Base exception for billing-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.BUSINESS_LOGIC, **kwargs)


class InvalidAmountError(BillingError):
    """Raised when an invalid monetary amount is provided."""

    def __init__(self, amount: Any, **kwargs):
        message = f"Invalid amount: {amount}. Amount must be a positive number."
        super().__init__(
            message,
            error_code="INVALID_AMOUNT",
            severity=ErrorSeverity.MEDIUM,
            context={"invalid_amount": str(amount)},
            user_message="Please enter a valid amount.",
            **kwargs,
        )


class InsufficientFundsError(BillingError):
    """Raised when there are insufficient funds for a transaction."""

    def __init__(self, required_amount: Any, available_amount: Any, **kwargs):
        message = f"Insufficient funds. Required: {required_amount}, Available: {available_amount}"
        super().__init__(
            message,
            error_code="INSUFFICIENT_FUNDS",
            severity=ErrorSeverity.HIGH,
            context={
                "required_amount": str(required_amount),
                "available_amount": str(available_amount),
            },
            user_message="Insufficient funds for this transaction.",
            **kwargs,
        )


class PaymentProcessingError(BillingError):
    """Raised when payment processing fails."""

    def __init__(self, gateway_error: Optional[str] = None, **kwargs):
        message = f"Payment processing failed: {gateway_error or 'Unknown error'}"
        super().__init__(
            message,
            error_code="PAYMENT_PROCESSING_ERROR",
            severity=ErrorSeverity.HIGH,
            retry_able=True,
            context={"gateway_error": gateway_error},
            user_message="Payment processing failed. Please try again.",
            **kwargs,
        )


class InvoiceNotFoundError(BillingError):
    """Raised when an invoice cannot be found."""

    def __init__(self, invoice_id: str, **kwargs):
        message = f"Invoice not found: {invoice_id}"
        super().__init__(
            message,
            error_code="INVOICE_NOT_FOUND",
            severity=ErrorSeverity.MEDIUM,
            context={"invoice_id": invoice_id},
            user_message="The requested invoice could not be found.",
            **kwargs,
        )


# Task-specific exceptions
class TaskError(BusinessLogicError):
    """Base exception for task-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.SYSTEM, **kwargs)


class TaskExecutionError(TaskError):
    """Raised when task execution fails."""

    def __init__(self, task_id: str, original_error: Optional[Exception] = None, **kwargs):
        message = f"Task execution failed: {task_id}"
        if original_error:
            message += f" - {str(original_error)}"

        super().__init__(
            message,
            error_code="TASK_EXECUTION_ERROR",
            severity=ErrorSeverity.HIGH,
            retry_able=True,
            context={
                "task_id": task_id,
                "original_error": str(original_error) if original_error else None,
            },
            **kwargs,
        )


class TaskTimeoutError(TaskError):
    """Raised when a task exceeds its timeout."""

    def __init__(self, task_id: str, timeout_seconds: int, **kwargs):
        message = f"Task timed out after {timeout_seconds} seconds: {task_id}"
        super().__init__(
            message,
            error_code="TASK_TIMEOUT",
            severity=ErrorSeverity.HIGH,
            retry_able=True,
            context={"task_id": task_id, "timeout_seconds": timeout_seconds},
            user_message="The operation is taking longer than expected. Please try again.",
            **kwargs,
        )


class WorkflowError(TaskError):
    """Raised when workflow execution fails."""

    def __init__(self, workflow_id: str, failed_step: Optional[str] = None, **kwargs):
        message = f"Workflow failed: {workflow_id}"
        if failed_step:
            message += f" at step: {failed_step}"

        super().__init__(
            message,
            error_code="WORKFLOW_ERROR",
            severity=ErrorSeverity.HIGH,
            context={"workflow_id": workflow_id, "failed_step": failed_step},
            **kwargs,
        )


# File-specific exceptions
class FileProcessingError(BusinessLogicError):
    """Base exception for file processing errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.SYSTEM, **kwargs)


class InvalidFileTypeError(FileProcessingError):
    """Raised when an invalid file type is provided."""

    def __init__(self, filename: str, allowed_types: list[str], **kwargs):
        message = f"Invalid file type: {filename}. Allowed types: {', '.join(allowed_types)}"
        super().__init__(
            message,
            error_code="INVALID_FILE_TYPE",
            severity=ErrorSeverity.MEDIUM,
            context={"filename": filename, "allowed_types": allowed_types},
            user_message=f"Please upload a file with one of these types: {', '.join(allowed_types)}",
            **kwargs,
        )


class FileSizeLimitExceededError(FileProcessingError):
    """Raised when file size exceeds the limit."""

    def __init__(self, filename: str, file_size: int, max_size: int, **kwargs):
        message = f"File size limit exceeded: {filename} ({file_size} bytes > {max_size} bytes)"
        super().__init__(
            message,
            error_code="FILE_SIZE_LIMIT_EXCEEDED",
            severity=ErrorSeverity.MEDIUM,
            context={
                "filename": filename,
                "file_size": file_size,
                "max_size": max_size,
            },
            user_message=f"File is too large. Maximum size allowed is {max_size // 1024 // 1024}MB.",
            **kwargs,
        )


class TemplateRenderingError(FileProcessingError):
    """Raised when template rendering fails."""

    def __init__(self, template_name: str, original_error: Optional[Exception] = None, **kwargs):
        message = f"Template rendering failed: {template_name}"
        if original_error:
            message += f" - {str(original_error)}"

        super().__init__(
            message,
            error_code="TEMPLATE_RENDERING_ERROR",
            severity=ErrorSeverity.HIGH,
            context={
                "template_name": template_name,
                "original_error": str(original_error) if original_error else None,
            },
            user_message="Document generation failed. Please try again.",
            **kwargs,
        )


# Integration exceptions
class IntegrationError(BusinessLogicError):
    """Base exception for integration errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.INTEGRATION, **kwargs)


class ExternalServiceError(IntegrationError):
    """Raised when external service communication fails."""

    def __init__(self, service_name: str, status_code: Optional[int] = None, **kwargs):
        message = f"External service error: {service_name}"
        if status_code:
            message += f" (HTTP {status_code})"

        super().__init__(
            message,
            error_code="EXTERNAL_SERVICE_ERROR",
            severity=ErrorSeverity.HIGH,
            retry_able=True,
            context={"service_name": service_name, "status_code": status_code},
            user_message="External service is temporarily unavailable. Please try again.",
            **kwargs,
        )


class DatabaseConnectionError(IntegrationError):
    """Raised when database connection fails."""

    def __init__(self, database_name: Optional[str] = None, **kwargs):
        message = "Database connection failed"
        if database_name:
            message += f": {database_name}"

        super().__init__(
            message,
            error_code="DATABASE_CONNECTION_ERROR",
            severity=ErrorSeverity.CRITICAL,
            retry_able=True,
            context={"database_name": database_name},
            user_message="Database is temporarily unavailable. Please try again later.",
            **kwargs,
        )


# Validation exceptions
class ValidationError(BusinessLogicError):
    """Base exception for validation errors."""

    def __init__(
        self,
        message: str,
        field_errors: Optional[dict[str, list[str]]] = None,
        **kwargs,
    ):
        super().__init__(message, category=ErrorCategory.VALIDATION, **kwargs)
        self.field_errors = field_errors or {}

    def to_dict(self) -> dict[str, Any]:
        """Include field errors in dictionary representation."""
        result = super().to_dict()
        result["field_errors"] = self.field_errors
        return result


class RequiredFieldError(ValidationError):
    """Raised when a required field is missing."""

    def __init__(self, field_name: str, **kwargs):
        message = f"Required field missing: {field_name}"
        super().__init__(
            message,
            error_code="REQUIRED_FIELD_ERROR",
            severity=ErrorSeverity.MEDIUM,
            field_errors={field_name: ["This field is required."]},
            context={"field_name": field_name},
            user_message=f"Please provide a value for {field_name}.",
            **kwargs,
        )


# Error handling utilities
class ErrorHandler:
    """Centralized error handling and logging."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def handle_error(
        self,
        error: Exception,
        context: Optional[dict[str, Any]] = None,
        notify_user: bool = True,
    ) -> dict[str, Any]:
        """Handle an error with appropriate logging and user notification."""

        if isinstance(error, BusinessLogicError):
            # Business logic error - structured handling
            error_dict = error.to_dict()
            if context:
                error_dict["context"].update(context)

            # Log based on severity
            if error.severity == ErrorSeverity.CRITICAL:
                self.logger.critical("Critical error occurred", extra=error_dict)
            elif error.severity == ErrorSeverity.HIGH:
                self.logger.error("High severity error occurred", extra=error_dict)
            elif error.severity == ErrorSeverity.MEDIUM:
                self.logger.warning("Medium severity error occurred", extra=error_dict)
            else:
                self.logger.info("Low severity error occurred", extra=error_dict)

            return {
                "error_id": error.error_id,
                "message": error.user_message if notify_user else error.message,
                "error_code": error.error_code,
                "retry_able": error.retry_able,
                "severity": error.severity.value,
            }

        else:
            # Unexpected error - wrap in generic business logic error
            wrapped_error = BusinessLogicError(
                message=f"Unexpected error: {str(error)}",
                error_code="UNEXPECTED_ERROR",
                severity=ErrorSeverity.CRITICAL,
                context=context or {},
                original_error=str(error),
            )

            self.logger.error("Unexpected error occurred", extra=wrapped_error.to_dict())

            return {
                "error_id": wrapped_error.error_id,
                "message": wrapped_error.user_message if notify_user else str(error),
                "error_code": wrapped_error.error_code,
                "retry_able": False,
                "severity": ErrorSeverity.CRITICAL.value,
            }

    def should_retry(self, error: Exception) -> bool:
        """Determine if an error should trigger a retry."""
        if isinstance(error, BusinessLogicError):
            return error.retry_able

        # Default retry logic for common exceptions
        retry_able_exceptions = (ConnectionError, TimeoutError, OSError)

        return isinstance(error, retry_able_exceptions)

    def get_error_metrics(self, errors: list[Exception]) -> dict[str, Any]:
        """Generate error metrics for monitoring."""
        if not errors:
            return {"total_errors": 0}

        categories = {}
        severities = {}
        retry_able_count = 0

        for error in errors:
            if isinstance(error, BusinessLogicError):
                category = error.category.value
                severity = error.severity.value

                categories[category] = categories.get(category, 0) + 1
                severities[severity] = severities.get(severity, 0) + 1

                if error.retry_able:
                    retry_able_count += 1
            else:
                categories["unknown"] = categories.get("unknown", 0) + 1
                severities["unknown"] = severities.get("unknown", 0) + 1

        return {
            "total_errors": len(errors),
            "by_category": categories,
            "by_severity": severities,
            "retry_able_count": retry_able_count,
            "retry_able_percentage": (retry_able_count / len(errors)) * 100,
        }
