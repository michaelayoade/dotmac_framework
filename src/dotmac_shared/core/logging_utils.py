"""
DRY logging utilities to reduce logging pattern duplication.
Provides standardized logging patterns across the platform.
"""

import functools
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Optional

from dotmac_shared.core.logging import get_logger


class LoggingPatterns:
    """
    DRY utility class for common logging patterns.
    Reduces duplication of logging code across the platform.
    """

    @staticmethod
    def log_operation_start(
        logger,
        operation: str,
        entity_id: Optional[str] = None,
        tz: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Standard logging for operation start.

        Args:
            logger: Logger instance
            operation: Operation name (e.g., "tenant provisioning", "user creation")
            entity_id: Entity identifier (e.g., tenant_id, user_id)
            **kwargs: Additional context data

        Returns:
            Correlation ID for tracking
        """
        import secrets

        correlation_id = f"{operation.replace(' ', '-')}-{secrets.token_hex(8)}"

        context = {"correlation_id": correlation_id}
        if entity_id:
            context["entity_id"] = entity_id
        context.update(kwargs)

        logger.info(f"🚀 Starting {operation}", extra=context)
        return correlation_id

    @staticmethod
    def log_operation_success(
        logger,
        operation: str,
        entity_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **kwargs,
    ):
        """Standard logging for operation success"""
        context = {}
        if entity_id:
            context["entity_id"] = entity_id
        if correlation_id:
            context["correlation_id"] = correlation_id
        context.update(kwargs)

        logger.info(f"✅ {operation.capitalize()} completed successfully", extra=context)

    @staticmethod
    def log_operation_error(
        logger,
        operation: str,
        error: Exception,
        entity_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **kwargs,
    ):
        """Standard logging for operation errors"""
        context = {"error_type": type(error).__name__, "error_message": str(error)}
        if entity_id:
            context["entity_id"] = entity_id
        if correlation_id:
            context["correlation_id"] = correlation_id
        context.update(kwargs)

        logger.error(f"❌ {operation.capitalize()} failed: {error}", extra=context)

    @staticmethod
    def log_validation_error(logger, field: str, error: str, entity_id: Optional[str] = None, **kwargs):
        """Standard logging for validation errors"""
        context = {"validation_field": field, "validation_error": error}
        if entity_id:
            context["entity_id"] = entity_id
        context.update(kwargs)

        logger.warning(f"⚠️ Validation error for {field}: {error}", extra=context)

    @staticmethod
    def log_external_api_call(
        logger,
        service: str,
        operation: str,
        status_code: Optional[int] = None,
        duration: Optional[float] = None,
        **kwargs,
    ):
        """Standard logging for external API calls"""
        context = {"external_service": service, "api_operation": operation}
        if status_code:
            context["status_code"] = status_code
        if duration:
            context["duration_ms"] = round(duration * 1000, 2)
        context.update(kwargs)

        if status_code and status_code >= 400:
            logger.warning(
                f"⚠️ {service} API call failed: {operation} ({status_code})",
                extra=context,
            )
        else:
            logger.info(f"🔗 {service} API call: {operation}", extra=context)

    @staticmethod
    def log_tenant_action(logger, action: str, tenant_id: str, user_id: Optional[str] = None, **kwargs):
        """Standard logging for tenant-scoped actions"""
        context = {"tenant_id": tenant_id, "tenant_action": action}
        if user_id:
            context["user_id"] = user_id
        context.update(kwargs)

        logger.info(f"🏢 Tenant action: {action} (tenant: {tenant_id})", extra=context)

    @staticmethod
    def log_security_event(
        logger,
        event: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        **kwargs,
    ):
        """Standard logging for security events"""
        context = {
            "security_event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if user_id:
            context["user_id"] = user_id
        if ip_address:
            context["ip_address"] = ip_address
        context.update(kwargs)

        logger.warning(f"🔒 Security event: {event}", extra=context)


def log_operation(operation_name: str):
    """
    Decorator for automatic operation logging with error handling.

    Usage:
        @log_operation("user creation")
        async def create_user(user_data):
            # function implementation
            return user
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            logger = get_logger(func.__module__)

            # Try to extract entity ID from kwargs
            entity_id = kwargs.get("entity_id") or kwargs.get("user_id") or kwargs.get("tenant_id")

            correlation_id = LoggingPatterns.log_operation_start(
                logger, operation_name, entity_id, function=func.__name__
            )

            try:
                result = await func(*args, **kwargs)
                LoggingPatterns.log_operation_success(logger, operation_name, entity_id, correlation_id)
                return result
            except Exception as e:
                LoggingPatterns.log_operation_error(logger, operation_name, e, entity_id, correlation_id)
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            logger = get_logger(func.__module__)

            entity_id = kwargs.get("entity_id") or kwargs.get("user_id") or kwargs.get("tenant_id")

            correlation_id = LoggingPatterns.log_operation_start(
                logger, operation_name, entity_id, function=func.__name__
            )

            try:
                result = func(*args, **kwargs)
                LoggingPatterns.log_operation_success(logger, operation_name, entity_id, correlation_id)
                return result
            except Exception as e:
                LoggingPatterns.log_operation_error(logger, operation_name, e, entity_id, correlation_id)
                raise

        return async_wrapper if functools.iscoroutinefunction(func) else sync_wrapper

    return decorator


def log_external_api(service_name: str):
    """
    Decorator for automatic external API call logging.

    Usage:
        @log_external_api("Coolify")
        async def create_application(config):
            # API call implementation
            return response
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            logger = get_logger(func.__module__)

            start_time = datetime.now(timezone.utc)

            try:
                result = await func(*args, **kwargs)

                duration = (datetime.now(timezone.utc) - start_time).total_seconds()

                # Try to extract status code from result
                status_code = None
                if isinstance(result, dict):
                    status_code = result.get("status_code") or result.get("code")

                LoggingPatterns.log_external_api_call(logger, service_name, func.__name__, status_code, duration)

                return result
            except Exception as e:
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                LoggingPatterns.log_external_api_call(logger, service_name, func.__name__, 500, duration, error=str(e))
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            logger = get_logger(func.__module__)

            start_time = datetime.now(timezone.utc)

            try:
                result = func(*args, **kwargs)

                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                status_code = None
                if isinstance(result, dict):
                    status_code = result.get("status_code") or result.get("code")

                LoggingPatterns.log_external_api_call(logger, service_name, func.__name__, status_code, duration)

                return result
            except Exception as e:
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                LoggingPatterns.log_external_api_call(logger, service_name, func.__name__, 500, duration, error=str(e))
                raise

        return async_wrapper if functools.iscoroutinefunction(func) else sync_wrapper

    return decorator


# Export for easy importing
__all__ = ["LoggingPatterns", "log_operation", "log_external_api"]
