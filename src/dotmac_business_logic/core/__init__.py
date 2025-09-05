"""
Core utilities for DotMac Business Logic package.
"""

from .exceptions import (
    BillingError,
    # Base exceptions
    BusinessLogicError,
    DatabaseConnectionError,
    ErrorCategory,
    # Utilities
    ErrorHandler,
    ErrorSeverity,
    ExternalServiceError,
    # File exceptions
    FileProcessingError,
    FileSizeLimitExceededError,
    InsufficientFundsError,
    # Integration exceptions
    IntegrationError,
    InvalidAmountError,
    InvalidFileTypeError,
    InvoiceNotFoundError,
    PaymentProcessingError,
    RequiredFieldError,
    # Task exceptions
    TaskError,
    TaskExecutionError,
    TaskTimeoutError,
    TemplateRenderingError,
    # Validation exceptions
    ValidationError,
    WorkflowError,
)

__all__ = [
    # Base
    "BusinessLogicError",
    "ErrorSeverity",
    "ErrorCategory",
    # Billing
    "BillingError",
    "InvalidAmountError",
    "InsufficientFundsError",
    "PaymentProcessingError",
    "InvoiceNotFoundError",
    # Tasks
    "TaskError",
    "TaskExecutionError",
    "TaskTimeoutError",
    "WorkflowError",
    # Files
    "FileProcessingError",
    "InvalidFileTypeError",
    "FileSizeLimitExceededError",
    "TemplateRenderingError",
    # Integration
    "IntegrationError",
    "ExternalServiceError",
    "DatabaseConnectionError",
    # Validation
    "ValidationError",
    "RequiredFieldError",
    # Utilities
    "ErrorHandler",
]
