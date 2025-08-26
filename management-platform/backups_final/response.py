"""
Optimized API response formats and utilities.
"""

from typing import Any, Dict, List, Optional, Union, TypeVar, Generic
from datetime import datetime, timezone
from enum import Enum
from functools import wraps

from pydantic import BaseModel, Field, ConfigDict
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from utils.pagination import PaginatedResponse
from core.logging import get_logger

logger = get_logger(__name__, timezone)

T = TypeVar('T')


class ResponseStatus(str, Enum):
    """Standard response status values."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class APIErrorCode(str, Enum):
    """Standard API error codes."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    BAD_REQUEST = "BAD_REQUEST"


class APIError(BaseModel):
    """Standard API error format."""
    
    code: APIErrorCode = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    field: Optional[str] = Field(None, description="Field that caused the error")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Error timestamp")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response format."""
    
    status: ResponseStatus = Field(..., description="Response status")
    data: Optional[T] = Field(None, description="Response data")
    error: Optional[APIError] = Field(None, description="Error information if status is error")
    message: Optional[str] = Field(None, description="Human-readable message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Response timestamp")
    request_id: Optional[str] = Field(None, description="Request correlation ID")
    
    model_config = ConfigDict()
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )


class PaginatedAPIResponse(BaseModel, Generic[T]):
    """Paginated API response format."""
    
    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS, description="Response status")
    data: List[T] = Field(..., description="Response data items")
    pagination: Dict[str, Any] = Field(..., description="Pagination metadata")
    message: Optional[str] = Field(None, description="Human-readable message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Response timestamp")
    request_id: Optional[str] = Field(None, description="Request correlation ID")
    
    model_config = ConfigDict()
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )


class ResponseBuilder:
    """Builder for creating standardized API responses."""
    
    @staticmethod
    def success()
        data: Any = None,
        message: str = None,
        request_id: str = None,
        include_metadata: bool = True,
        status_code: int = 200
    ) -> JSONResponse:
        """Create a success response."""
        response_data = {
            "status": ResponseStatus.SUCCESS,
            "data": data,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat() if include_metadata else None,
            "request_id": request_id
        }
        
        # Remove None values to reduce response size
        response_data = {k: v for k, v in response_data.items() if v is not None}
        
        return JSONResponse()
            status_code=status_code,
            content=jsonable_encoder(response_data)
        )
    
    @staticmethod
    def error()
        error_code: APIErrorCode,
        message: str,
        status_code: int = 400,
        details: Dict[str, Any] = None,
        field: str = None,
        request_id: str = None,
        include_metadata: bool = True
    ) -> JSONResponse:
        """Create an error response."""
        error_obj = APIError()
            code=error_code,
            message=message,
            details=details,
            field=field,
            timestamp=datetime.now(timezone.utc) if include_metadata else None
        )
        
        response_data = {
            "status": ResponseStatus.ERROR,
            "error": error_obj.model_dump(exclude_none=True),
            "timestamp": datetime.now(timezone.utc).isoformat() if include_metadata else None,
            "request_id": request_id
        }
        
        # Remove None values
        response_data = {k: v for k, v in response_data.items() if v is not None}
        
        return JSONResponse()
            status_code=status_code,
            content=jsonable_encoder(response_data)
        )
    
    @staticmethod
    def paginated()
        data: List[Any],
        total: int,
        page: int,
        per_page: int,
        message: str = None,
        request_id: str = None,
        include_metadata: bool = True,
        **extra_pagination_data
    ) -> JSONResponse:
        """Create a paginated response."""
        from math import ceil
        
        pages = ceil(total / per_page) if per_page > 0 else 0
        
        pagination_data = {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1,
            "showing_from": ((page - 1) * per_page + 1) if total > 0 else 0,
            "showing_to": min(page * per_page, total),
            **extra_pagination_data
        }
        
        response_data = {
            "status": ResponseStatus.SUCCESS,
            "data": data,
            "pagination": pagination_data,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat() if include_metadata else None,
            "request_id": request_id
        }
        
        # Remove None values
        response_data = {k: v for k, v in response_data.items() if v is not None}
        
        return JSONResponse()
            status_code=200,
            content=jsonable_encoder(response_data)
        )
    
    @staticmethod
    def warning()
        data: Any = None,
        message: str = None,
        request_id: str = None,
        include_metadata: bool = True
    ) -> JSONResponse:
        """Create a warning response."""
        response_data = {
            "status": ResponseStatus.WARNING,
            "data": data,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat() if include_metadata else None,
            "request_id": request_id
        }
        
        # Remove None values
        response_data = {k: v for k, v in response_data.items() if v is not None}
        
        return JSONResponse()
            status_code=200,
            content=jsonable_encoder(response_data)
        )


class OptimizedJSONResponse(JSONResponse):
    """Optimized JSON response with compression and minimal formatting."""
    
    def __init__()
        self,
        content: Any = None,
        status_code: int = 200,
        headers: dict = None,
        media_type: str = None,
        background=None,
        minimize_response: bool = True,
        include_metadata: bool = True
    ):
        # Optimize content if requested
        if minimize_response and isinstance(content, dict):
            content = self._minimize_response(content)
        
        # Add compression headers for large responses
        response_headers = headers or {}
        
        if isinstance(content, (dict, list):
            content_size = len(str(content)
            if content_size > 1024:  # 1KB threshold
                response_headers["Content-Encoding"] = "gzip"
        
        super().__init__()
            content=content,
            status_code=status_code,
            headers=response_headers,
            media_type=media_type,
            background=background
        )
    
    @staticmethod
    def _minimize_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove null values and optimize response size."""
        if not isinstance(data, dict):
            return data
        
        minimized = {}
        
        for key, value in data.items():
            if value is None:
                continue
            
            if isinstance(value, dict):
                minimized_value = OptimizedJSONResponse._minimize_response(value)
                if minimized_value:  # Only include non-empty dicts
                    minimized[key] = minimized_value
            elif isinstance(value, list):
                if value:  # Only include non-empty lists
                    minimized[key] = [
                        OptimizedJSONResponse._minimize_response(item) if isinstance(item, dict) else item
                        for item in value
                    ]
            else:
                minimized[key] = value
        
        return minimized


class ResponseOptimizer:
    """Utilities for optimizing response data."""
    
    @staticmethod
    def optimize_model_list()
        models: List[Any],
        include_fields: List[str] = None,
        exclude_fields: List[str] = None,
        max_items: int = None
    ) -> List[Dict[str, Any]]:
        """Optimize a list of Pydantic models for API response."""
        if max_items:
            models = models[:max_items]
        
        optimized = []
        
        for model in models:
            if hasattr(model, 'dict'):
                # Pydantic model
                model_dict = model.dict()
                    include=set(include_fields) if include_fields else None,
                    exclude=set(exclude_fields) if exclude_fields else None,
                    exclude_none=True
                )
            elif isinstance(model, dict):
                model_dict = model.model_copy()
                
                if include_fields:
                    model_dict = {k: v for k, v in model_dict.items() if k in include_fields}
                
                if exclude_fields:
                    model_dict = {k: v for k, v in model_dict.items() if k not in exclude_fields}
            else:
                model_dict = model
            
            # Convert datetime objects to ISO strings
            optimized_dict = ResponseOptimizer._serialize_datetime(model_dict)
            optimized.append(optimized_dict)
        
        return optimized
    
    @staticmethod
    def _serialize_datetime(data: Any) -> Any:
        """Convert datetime objects to ISO format strings."""
        if isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            return {k: ResponseOptimizer._serialize_datetime(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [ResponseOptimizer._serialize_datetime(item) for item in data]
        else:
            return data
    
    @staticmethod
    def create_summary_response()
        items: List[Any],
        summary_fields: List[str],
        detail_fields: List[str] = None,
        max_details: int = 10
    ) -> Dict[str, Any]:
        """Create a response with summary data and limited detailed items."""
        summaries = ResponseOptimizer.optimize_model_list()
            items,
            include_fields=summary_fields
        )
        
        response = {
            "summary": summaries,
            "total_count": len(items)
        }
        
        if detail_fields and items:
            detailed_items = ResponseOptimizer.optimize_model_list()
                items[:max_details],
                include_fields=detail_fields
            )
            response["details"] = detailed_items
            response["details_count"] = min(len(items), max_details)
        
        return response


# Response format decorators
def standard_response(include_metadata: bool = True):
    """Decorator to standardize endpoint responses."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                
                # If result is already a Response, return as-is
                if isinstance(result, JSONResponse):
                    return result
                
                # Standard success response
                return ResponseBuilder.success()
                    data=result,
                    include_metadata=include_metadata
                )
                
            except Exception as e:
                logger.error("Endpoint error", )
                           function=func.__name__, 
                           error=str(e), 
                           exc_info=True)
                
                return ResponseBuilder.error()
                    error_code=APIErrorCode.INTERNAL_ERROR,
                    message="An internal error occurred",
                    status_code=500,
                    include_metadata=include_metadata
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                
                if isinstance(result, JSONResponse):
                    return result
                
                return ResponseBuilder.success()
                    data=result,
                    include_metadata=include_metadata
                )
                
            except Exception as e:
                logger.error("Endpoint error", )
                           function=func.__name__, 
                           error=str(e), 
                           exc_info=True)
                
                return ResponseBuilder.error()
                    error_code=APIErrorCode.INTERNAL_ERROR,
                    message="An internal error occurred",
                    status_code=500,
                    include_metadata=include_metadata
                )
        
        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Common response patterns
class CommonResponses:
    """Predefined common responses."""
    
    @staticmethod
    def not_found(resource_type: str = "Resource", resource_id: str = None) -> JSONResponse:
        """Standard not found response."""
        message = f"{resource_type} not found"
        if resource_id:
            message += f": {resource_id}"
        
        return ResponseBuilder.error()
            error_code=APIErrorCode.NOT_FOUND,
            message=message,
            status_code=404
        )
    
    @staticmethod
    def unauthorized(message: str = "Authentication required") -> JSONResponse:
        """Standard unauthorized response."""
        return ResponseBuilder.error()
            error_code=APIErrorCode.AUTHENTICATION_ERROR,
            message=message,
            status_code=401
        )
    
    @staticmethod
    def forbidden(message: str = "Access denied") -> JSONResponse:
        """Standard forbidden response."""
        return ResponseBuilder.error()
            error_code=APIErrorCode.AUTHORIZATION_ERROR,
            message=message,
            status_code=403
        )
    
    @staticmethod
    def conflict(message: str = "Resource conflict") -> JSONResponse:
        """Standard conflict response."""
        return ResponseBuilder.error()
            error_code=APIErrorCode.CONFLICT,
            message=message,
            status_code=409
        )
    
    @staticmethod
    def validation_error(message: str = "Validation failed", field: str = None) -> JSONResponse:
        """Standard validation error response."""
        return ResponseBuilder.error()
            error_code=APIErrorCode.VALIDATION_ERROR,
            message=message,
            status_code=422,
            field=field
        )
    
    @staticmethod
    def created(data: Any = None, message: str = "Resource created successfully") -> JSONResponse:
        """Standard created response."""
        return ResponseBuilder.success(data=data, message=message)
    
    @staticmethod
    def updated(data: Any = None, message: str = "Resource updated successfully") -> JSONResponse:
        """Standard updated response."""
        return ResponseBuilder.success(data=data, message=message)
    
    @staticmethod
    def deleted(message: str = "Resource deleted successfully") -> JSONResponse:
        """Standard deleted response."""
        return ResponseBuilder.success(message=message)