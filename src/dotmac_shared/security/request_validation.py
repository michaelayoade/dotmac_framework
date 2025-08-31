"""
Comprehensive Request Validation and Schema Enforcement
Provides input validation, schema enforcement, and data sanitization for API requests

SECURITY: This module ensures all incoming requests are validated against schemas
and sanitized to prevent injection attacks and malformed data processing
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type, Union

import email_validator
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError, field_validator, ConfigDict
from pydantic._internal._model_construction import complete_model_class

logger = logging.getLogger(__name__)


class ValidationSeverity:
    """Validation severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SecurityValidationError(HTTPException):
    """Custom security validation error"""

    def __init__(self, detail: str, field: str = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Validation failed",
                "message": detail,
                "field": field,
                "type": "security_validation",
            },
        )


class SchemaValidationError(HTTPException):
    """Custom schema validation error"""

    def __init__(self, detail: str, errors: List[Dict] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Schema validation failed",
                "message": detail,
                "validation_errors": errors or [],
                "type": "schema_validation",
            },
        )


class SecurityValidators:
    """
    Security-focused validators for common input types
    """

    # Security patterns
    SQL_INJECTION_PATTERNS = [
        r"('|(\")|;|--)|(\b(ALTER|CREATE|DELETE|DROP|EXEC(UTE)?|INSERT( +INTO)?|MERGE|SELECT|UNION|UPDATE)\b)",
        r"\b(AND|OR)\b.*(=|<|>|\bLIKE\b)",
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"onload\s*=",
        r"onerror\s*=",
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"data:text/html",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
    ]

    PATH_TRAVERSAL_PATTERNS = [r"\.\./", r"\.\.\\\\", r"~/"]

    @classmethod
    def validate_no_sql_injection(cls, value: str) -> str:
        """Validate that input doesn't contain SQL injection patterns"""
        if not isinstance(value, str):
            return value

        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"SQL injection attempt detected: {value[:50]}...")
                raise SecurityValidationError(
                    "Input contains potentially malicious SQL patterns",
                    field="input_validation",
                )

        return value

    @classmethod
    def validate_no_xss(cls, value: str) -> str:
        """Validate that input doesn't contain XSS patterns"""
        if not isinstance(value, str):
            return value

        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"XSS attempt detected: {value[:50]}...")
                raise SecurityValidationError(
                    "Input contains potentially malicious script patterns",
                    field="input_validation",
                )

        return value

    @classmethod
    def validate_no_path_traversal(cls, value: str) -> str:
        """Validate that input doesn't contain path traversal patterns"""
        if not isinstance(value, str):
            return value

        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, value):
                logger.warning(f"Path traversal attempt detected: {value}")
                raise SecurityValidationError(
                    "Input contains path traversal patterns", field="path_validation"
                )

        return value

    @classmethod
    def validate_safe_filename(cls, value: str) -> str:
        """Validate that filename is safe"""
        if not isinstance(value, str):
            return value

        # Check for path traversal
        cls.validate_no_path_traversal(value)

        # Check for reserved names (Windows)
        reserved_names = [
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        ]
        if value.upper().split(".")[0] in reserved_names:
            raise SecurityValidationError(
                "Filename uses reserved name", field="filename"
            )

        # Check for dangerous characters
        dangerous_chars = ["<", ">", ":", '"', "|", "?", "*", "\x00"]
        if any(char in value for char in dangerous_chars):
            raise SecurityValidationError(
                "Filename contains dangerous characters", field="filename"
            )

        return value

    @classmethod
    def validate_uuid_format(cls, value: str) -> str:
        """Validate UUID format"""
        uuid_pattern = (
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        )
        if not re.match(uuid_pattern, value, re.IGNORECASE):
            raise SecurityValidationError("Invalid UUID format", field="uuid")

        return value

    @classmethod
    def validate_email_secure(cls, value: str) -> str:
        """Secure email validation"""
        try:
            # Use email-validator library for robust validation
            validated_email = email_validator.validate_email(value)
            return validated_email.email
        except email_validator.EmailNotValidError as e:
            raise SecurityValidationError(
                f"Invalid email format: {str(e)}", field="email"
            )

    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        """Validate phone number format"""
        # Remove all non-digit characters for validation
        digits_only = re.sub(r"\D", "", value)

        # Check if it's a reasonable length (7-15 digits)
        if len(digits_only) < 7 or len(digits_only) > 15:
            raise SecurityValidationError("Invalid phone number length", field="phone")

        # Check for valid international format
        phone_pattern = (
            r"^(\+?1-?)?(\([0-9]{3}\)|[0-9]{3})[\s.-]?[0-9]{3}[\s.-]?[0-9]{4}$"
        )
        if not re.match(phone_pattern, value.strip()):
            # Try international format
            intl_pattern = r"^\+?[1-9]\d{6,14}$"
            if not re.match(intl_pattern, digits_only):
                raise SecurityValidationError(
                    "Invalid phone number format", field="phone"
                )

        return value


class BaseSecureModel(BaseModel):
    """
    Base Pydantic model with security validations
    """

    model_config = ConfigDict(
        # Security configurations
        validate_assignment=True,
        use_enum_values=True,
        extra="forbid",  # Prevent additional fields
        str_max_length=10000,  # Prevent extremely long strings
        str_strip_whitespace=True
    )

    @field_validator("*", mode="before")
    @classmethod
    def validate_security(cls, v, info=None):
        """Apply security validations to all string fields"""
        if isinstance(v, str) and len(v) > 0:
            # Apply basic security validations
            v = SecurityValidators.validate_no_sql_injection(v)
            v = SecurityValidators.validate_no_xss(v)

            # Apply field-specific validations based on field name
            field_name = info.field_name if info and info.field_name else ""
            if "filename" in field_name.lower():
                v = SecurityValidators.validate_safe_filename(v)
            elif "path" in field_name.lower():
                v = SecurityValidators.validate_no_path_traversal(v)
            elif field_name.lower() in ["id", "user_id", "tenant_id"] and len(v) == 36:
                v = SecurityValidators.validate_uuid_format(v)

        return v


# Common secure models
class SecureStringField(BaseModel):
    """Secure string field with comprehensive validation"""

    value: str = Field(..., min_length=1, max_length=1000)

    @field_validator("value")
    @classmethod
    def validate_secure_string(cls, v):
        return SecurityValidators.validate_no_sql_injection(
            SecurityValidators.validate_no_xss(v)
        )


class SecureEmailField(BaseModel):
    """Secure email field"""

    email: str = Field(..., max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        return SecurityValidators.validate_email_secure(v)


class SecurePhoneField(BaseModel):
    """Secure phone field"""

    phone: str = Field(..., max_length=20)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        return SecurityValidators.validate_phone_number(v)


class SecureFileUpload(BaseModel):
    """Secure file upload validation"""

    filename: str = Field(..., max_length=255)
    content_type: str = Field(..., max_length=100)
    size: int = Field(..., ge=1, le=100_000_000)  # Max 100MB

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v):
        return SecurityValidators.validate_safe_filename(v)

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v):
        allowed_types = [
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "application/pdf",
            "text/plain",
            "text/csv",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ]

        if v not in allowed_types:
            raise SecurityValidationError(
                f"File type not allowed: {v}", field="content_type"
            )

        return v


class RequestValidationMiddleware:
    """
    Middleware for request validation and security checks
    """

    def __init__(
        self,
        app,
        max_request_size: int = 10_000_000,  # 10MB
        max_json_depth: int = 10,
        validate_content_type: bool = True,
        allowed_content_types: Optional[List[str]] = None,
        exempt_paths: Optional[List[str]] = None,
    ):
        self.app = app
        self.max_request_size = max_request_size
        self.max_json_depth = max_json_depth
        self.validate_content_type = validate_content_type
        self.allowed_content_types = allowed_content_types or [
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
            "text/plain",
        ]
        self.exempt_paths = exempt_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
        ]

    def is_exempt(self, path: str) -> bool:
        """Check if path is exempt from validation"""
        return any(path.startswith(exempt) for exempt in self.exempt_paths)

    def validate_json_depth(self, obj: Any, current_depth: int = 0) -> None:
        """Validate JSON nesting depth to prevent DoS attacks"""
        if current_depth > self.max_json_depth:
            raise SecurityValidationError(
                f"JSON nesting too deep (max {self.max_json_depth})",
                field="json_structure",
            )

        if isinstance(obj, dict):
            for value in obj.values():
                self.validate_json_depth(value, current_depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                self.validate_json_depth(item, current_depth + 1)

    async def validate_request_size(self, request: Request) -> None:
        """Validate request size"""
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            raise SecurityValidationError(
                f"Request too large (max {self.max_request_size} bytes)",
                field="request_size",
            )

    async def validate_content_type_header(self, request: Request) -> None:
        """Validate content type"""
        if not self.validate_content_type:
            return

        content_type = request.headers.get("content-type", "").split(";")[0].strip()

        if request.method in ["POST", "PUT", "PATCH"] and content_type:
            if content_type not in self.allowed_content_types:
                raise SecurityValidationError(
                    f"Content type not allowed: {content_type}", field="content_type"
                )

    async def validate_request_body(self, request: Request) -> None:
        """Validate request body content"""
        if request.method not in ["POST", "PUT", "PATCH"]:
            return

        try:
            body = await request.body()
            if not body:
                return

            content_type = request.headers.get("content-type", "").split(";")[0].strip()

            if content_type == "application/json":
                # Parse and validate JSON
                try:
                    json_data = json.loads(body)
                    self.validate_json_depth(json_data)

                    # Additional JSON security checks
                    json_str = json.dumps(json_data)
                    if len(json_str) > self.max_request_size:
                        raise SecurityValidationError(
                            "JSON payload too large after parsing", field="json_size"
                        )

                except json.JSONDecodeError as e:
                    raise SecurityValidationError(
                        f"Invalid JSON: {str(e)}", field="json_format"
                    )

        except Exception as e:
            if isinstance(e, SecurityValidationError):
                raise
            logger.error(f"Request body validation error: {e}")
            raise SecurityValidationError(
                "Request body validation failed", field="request_body"
            )

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)

            # Skip exempt paths
            if self.is_exempt(request.url.path):
                await self.app(scope, receive, send)
                return

            try:
                # Validate request
                await self.validate_request_size(request)
                await self.validate_content_type_header(request)
                await self.validate_request_body(request)

                # Proceed with request
                await self.app(scope, receive, send)

            except SecurityValidationError as e:
                error_response = JSONResponse(
                    status_code=e.status_code, content=e.detail
                )
                await error_response(scope, receive, send)
            except Exception as e:
                logger.error(f"Request validation middleware error: {e}")
                error_response = JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "error": "Internal server error",
                        "message": "Request validation failed",
                    },
                )
                await error_response(scope, receive, send)
        else:
            await self.app(scope, receive, send)


# Exception handlers
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    errors = []

    for error in exc.errors():
        field = " -> ".join([str(loc) for loc in error["loc"]])
        errors.append(
            {
                "field": field,
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input"),
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation failed",
            "message": "Request data validation failed",
            "validation_errors": errors,
            "type": "validation_error",
        },
    )


# Factory functions
def create_request_validation_middleware(
    max_request_size: int = 10_000_000, **kwargs
) -> Callable:
    """Factory for creating request validation middleware"""

    def middleware_factory(app):
        return RequestValidationMiddleware(
            app=app, max_request_size=max_request_size, **kwargs
        )

    return middleware_factory
