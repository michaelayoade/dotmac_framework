"""
Core utilities for DotMac Business Logic package.
"""

from .exceptions import (  # Base, Utilities, File, Integration, Task, Validation exceptions
    BillingError,
    BusinessLogicError,
    DatabaseConnectionError,
    ErrorCategory,
    ErrorHandler,
    ErrorSeverity,
    ExternalServiceError,
    FileProcessingError,
    FileSizeLimitExceededError,
    InsufficientFundsError,
    IntegrationError,
    InvalidAmountError,
    InvalidFileTypeError,
    InvoiceNotFoundError,
    PaymentProcessingError,
    RequiredFieldError,
    TaskError,
    TaskExecutionError,
    TaskTimeoutError,
    TemplateRenderingError,
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
