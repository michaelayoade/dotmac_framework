"""
Validation decorators for automatic input validation using Pydantic schemas.
"""

from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, Type, Union

from fastapi import HTTPException, Request
from pydantic import BaseModel, ValidationError


def validate_request(schema: Type[BaseModel], body_param: str = None):
    """
    Decorator to validate request data using Pydantic schema.
    
    Args:
        schema: Pydantic model class for validation
        body_param: Parameter name for request body (defaults to first param)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get function signature
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            
            # Determine which parameter contains the request data
            if body_param:
                if body_param not in param_names:
                    raise ValueError(f"Parameter {body_param} not found in function signature")
                param_index = param_names.index(body_param)
            else:
                # Use first non-Request parameter
                param_index = 0
                for i, (name, param) in enumerate(sig.parameters.items()):
                    if param.annotation != Request and not name.startswith('_'):
                        param_index = i
                        break
            
            # Validate the request data
            if param_index < len(args):
                request_data = args[param_index]
                try:
                    if isinstance(request_data, dict):
                        validated_data = schema(**request_data)
                    else:
                        # Assume it's already a Pydantic model or dict-like
                        validated_data = schema(**request_data.dict() if hasattr(request_data, 'dict') else request_data)
                    
                    # Replace the original data with validated data
                    new_args = list(args)
                    new_args[param_index] = validated_data
                    args = tuple(new_args)
                    
                except ValidationError as e:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "message": "Validation failed",
                            "errors": e.errors()
                        }
                    ) from e
            
            return await func(*args, **kwargs) if inspect.iscoroutinefunction(func) else func(*args, **kwargs)
        return wrapper
    return decorator


def validate_query_params(schema: Type[BaseModel]):
    """
    Decorator to validate query parameters using Pydantic schema.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            try:
                # Extract query parameters
                query_params = dict(request.query_params)
                validated_params = schema(**query_params)
                
                # Add validated params to kwargs
                kwargs['query_params'] = validated_params
                
            except ValidationError as e:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "message": "Query parameter validation failed",
                        "errors": e.errors()
                    }
                ) from e
            
            return await func(request, *args, **kwargs) if inspect.iscoroutinefunction(func) else func(request, *args, **kwargs)
        return wrapper
    return decorator


def validate_path_params(schema: Type[BaseModel]):
    """
    Decorator to validate path parameters using Pydantic schema.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Validate path parameters (usually in kwargs)
                validated_params = schema(**kwargs)
                
                # Update kwargs with validated data
                kwargs.update(validated_params.dict())
                
            except ValidationError as e:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "message": "Path parameter validation failed",
                        "errors": e.errors()
                    }
                ) from e
            
            return await func(*args, **kwargs) if inspect.iscoroutinefunction(func) else func(*args, **kwargs)
        return wrapper
    return decorator


def sanitize_input(
    fields: list[str] = None, 
    remove_html: bool = True,
    remove_sql_chars: bool = True,
    max_length: int = None
):
    """
    Decorator to sanitize input data before processing.
    
    Args:
        fields: List of field names to sanitize (None for all string fields)
        remove_html: Remove HTML tags
        remove_sql_chars: Remove common SQL injection characters
        max_length: Maximum length for string fields
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Find Pydantic models in arguments
            for i, arg in enumerate(args):
                if isinstance(arg, BaseModel):
                    sanitized_data = _sanitize_model_data(
                        arg, fields, remove_html, remove_sql_chars, max_length
                    )
                    args = list(args)
                    args[i] = type(arg)(**sanitized_data)
                    args = tuple(args)
            
            return await func(*args, **kwargs) if inspect.iscoroutinefunction(func) else func(*args, **kwargs)
        return wrapper
    return decorator


def _sanitize_model_data(
    model: BaseModel,
    fields: list[str] = None,
    remove_html: bool = True,
    remove_sql_chars: bool = True,
    max_length: int = None
) -> dict[str, Any]:
    """Sanitize data in a Pydantic model."""
    import re
    
    data = model.dict()
    
    for field_name, value in data.items():
        if fields and field_name not in fields:
            continue
            
        if isinstance(value, str):
            sanitized_value = value
            
            if remove_html:
                # Remove HTML tags
                sanitized_value = re.sub(r'<[^>]+>', '', sanitized_value)
            
            if remove_sql_chars:
                # Remove common SQL injection characters
                dangerous_chars = ['<', '>', '"', "'", ';', '--', '/*', '*/', 'xp_', 'sp_']
                for char in dangerous_chars:
                    sanitized_value = sanitized_value.replace(char, '')
            
            if max_length and len(sanitized_value) > max_length:
                sanitized_value = sanitized_value[:max_length]
            
            data[field_name] = sanitized_value.strip()
    
    return data


def require_permissions(permissions: list[str]):
    """
    Decorator to require specific permissions for endpoint access.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Check if user has required permissions
            user_permissions = getattr(request.state, 'user_permissions', [])
            
            if not any(perm in user_permissions for perm in permissions):
                raise HTTPException(
                    status_code=403,
                    detail={
                        "message": "Insufficient permissions",
                        "required_permissions": permissions
                    }
                )
            
            return await func(request, *args, **kwargs) if inspect.iscoroutinefunction(func) else func(request, *args, **kwargs)
        return wrapper
    return decorator


def rate_limit(requests_per_minute: int = 60, requests_per_hour: int = 1000):
    """
    Decorator for rate limiting endpoints.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Implementation would integrate with Redis for rate limiting
            # For now, just log the rate limit requirements
            client_ip = request.client.host if request.client else 'unknown'
            
            # This would be implemented with proper rate limiting logic
            # using Redis or similar storage
            
            return await func(request, *args, **kwargs) if inspect.iscoroutinefunction(func) else func(request, *args, **kwargs)
        return wrapper
    return decorator


# Export decorators
__all__ = [
    'validate_request',
    'validate_query_params', 
    'validate_path_params',
    'sanitize_input',
    'require_permissions',
    'rate_limit',
]