"""
Standardized router patterns following ISP framework conventions.
"""

from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union
from uuid import UUID
import functools

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..core.exceptions import (
    EntityNotFoundError, ValidationError, BusinessRuleError, ServiceError
)

ServiceType = TypeVar("ServiceType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
ResponseSchemaType = TypeVar("ResponseSchemaType", bound=BaseModel)


def standard_exception_handler(func: Callable) -> Callable:
    """
    Decorator for standard exception handling in management platform routers.
    Maps service exceptions to appropriate HTTP responses.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except EntityNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except BusinessRuleError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e)
            )
        except ServiceError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
        except Exception as e:
            # Log the unexpected error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred"
            )
    return wrapper


class StandardRouterMethods:
    """
    Standard CRUD router methods following ISP framework patterns.
    """
    
    @staticmethod
    def create_endpoint(
        service_class: Type[ServiceType],
        create_schema: Type[CreateSchemaType],
        response_schema: Type[ResponseSchemaType],
        tenant_context: bool = True
    ) -> Callable:
        """Create standardized create endpoint."""
        @standard_exception_handler
        async def endpoint(
            data: create_schema,
            db: AsyncSession,
            user_id: str,
            tenant_id: Optional[str] = None
        ) -> response_schema:
            if tenant_context and tenant_id:
                service = service_class(db, tenant_id)
            else:
                service = service_class(db)
            
            return await service.create(data, user_id)
        
        return endpoint
    
    @staticmethod
    def get_endpoint(
        service_class: Type[ServiceType],
        response_schema: Type[ResponseSchemaType],
        tenant_context: bool = True
    ) -> Callable:
        """Create standardized get endpoint."""
        @standard_exception_handler
        async def endpoint(
            entity_id: UUID,
            db: AsyncSession,
            user_id: str,
            tenant_id: Optional[str] = None
        ) -> response_schema:
            if tenant_context and tenant_id:
                service = service_class(db, tenant_id)
            else:
                service = service_class(db)
            
            entity = await service.get_by_id(entity_id, user_id)
            if not entity:
                raise EntityNotFoundError(f"Entity with ID {entity_id} not found")
            
            return entity
        
        return endpoint
    
    @staticmethod
    def update_endpoint(
        service_class: Type[ServiceType],
        update_schema: Type[UpdateSchemaType],
        response_schema: Type[ResponseSchemaType],
        tenant_context: bool = True
    ) -> Callable:
        """Create standardized update endpoint."""
        @standard_exception_handler
        async def endpoint(
            entity_id: UUID,
            data: update_schema,
            db: AsyncSession,
            user_id: str,
            tenant_id: Optional[str] = None
        ) -> response_schema:
            if tenant_context and tenant_id:
                service = service_class(db, tenant_id)
            else:
                service = service_class(db)
            
            updated_entity = await service.update(entity_id, data, user_id)
            if not updated_entity:
                raise EntityNotFoundError(f"Entity with ID {entity_id} not found")
            
            return updated_entity
        
        return endpoint
    
    @staticmethod
    def delete_endpoint(
        service_class: Type[ServiceType],
        tenant_context: bool = True
    ) -> Callable:
        """Create standardized delete endpoint."""
        @standard_exception_handler
        async def endpoint(
            entity_id: UUID,
            db: AsyncSession,
            user_id: str,
            tenant_id: Optional[str] = None,
            soft_delete: bool = True
        ) -> Dict[str, str]:
            if tenant_context and tenant_id:
                service = service_class(db, tenant_id)
            else:
                service = service_class(db)
            
            deleted = await service.delete(entity_id, user_id, soft_delete)
            if not deleted:
                raise EntityNotFoundError(f"Entity with ID {entity_id} not found")
            
            return {"message": "Entity deleted successfully"}
        
        return endpoint
    
    @staticmethod
    def list_endpoint(
        service_class: Type[ServiceType],
        response_schema: Type[ResponseSchemaType],
        tenant_context: bool = True
    ) -> Callable:
        """Create standardized list endpoint."""
        @standard_exception_handler
        async def endpoint(
            db: AsyncSession,
            user_id: str,
            tenant_id: Optional[str] = None,
            skip: int = 0,
            limit: int = 100,
            filters: Optional[Dict[str, Any]] = None,
            order_by: Optional[str] = None
        ) -> List[response_schema]:
            if tenant_context and tenant_id:
                service = service_class(db, tenant_id)
            else:
                service = service_class(db)
            
            return await service.list(
                skip=skip,
                limit=limit,
                filters=filters,
                order_by=order_by,
                user_id=user_id
            )
        
        return endpoint


def get_tenant_id_dependency() -> str:
    """
    Dependency for extracting tenant ID from request context.
    This would be implemented based on the management platform's auth system.
    """
    # Placeholder implementation
    return "default-tenant"


def get_user_id_dependency() -> str:
    """
    Dependency for extracting user ID from request context.
    This would be implemented based on the management platform's auth system.
    """
    # Placeholder implementation  
    return "default-user"


# Router pattern templates for common use cases
class StandardRouterPattern:
    """
    Template class for creating standardized routers following ISP framework patterns.
    """
    
    @staticmethod
    def create_crud_router(
        service_class: Type[ServiceType],
        create_schema: Type[CreateSchemaType],
        update_schema: Type[UpdateSchemaType], 
        response_schema: Type[ResponseSchemaType],
        prefix: str,
        tags: List[str],
        tenant_context: bool = True
    ):
        """
        Create a complete CRUD router with standard patterns.
        
        This follows the same patterns as the ISP framework routers.
        """
        from fastapi import APIRouter, Depends
        
        router = APIRouter(prefix=prefix, tags=tags)
        
        # Create endpoint
        create_func = StandardRouterMethods.create_endpoint(
            service_class, create_schema, response_schema, tenant_context
        )
        
        # Get endpoint
        get_func = StandardRouterMethods.get_endpoint(
            service_class, response_schema, tenant_context
        )
        
        # Update endpoint
        update_func = StandardRouterMethods.update_endpoint(
            service_class, update_schema, response_schema, tenant_context
        )
        
        # Delete endpoint
        delete_func = StandardRouterMethods.delete_endpoint(
            service_class, tenant_context
        )
        
        # List endpoint
        list_func = StandardRouterMethods.list_endpoint(
            service_class, response_schema, tenant_context
        )
        
        # Register endpoints with the router
        # Define the create endpoint function
        async def create_endpoint(
            data: create_schema,
            db: AsyncSession = Depends(),
            user_id: str = Depends(get_user_id_dependency),
            tenant_id: str = Depends(get_tenant_id_dependency) if tenant_context else None
        ):
            return await create_func(data, db, user_id, tenant_id)
        
        router.post("/", response_model=response_schema)(create_endpoint)
        
        # Define the get endpoint function
        async def get_endpoint(
            entity_id: UUID,
            db: AsyncSession = Depends(),
            user_id: str = Depends(get_user_id_dependency),
            tenant_id: str = Depends(get_tenant_id_dependency) if tenant_context else None
        ):
            return await get_func(entity_id, db, user_id, tenant_id)
        
        router.get("/{entity_id}", response_model=response_schema)(get_endpoint)
        
        # Define the update endpoint function
        async def update_endpoint(
            entity_id: UUID,
            data: update_schema,
            db: AsyncSession = Depends(),
            user_id: str = Depends(get_user_id_dependency),
            tenant_id: str = Depends(get_tenant_id_dependency) if tenant_context else None
        ):
            return await update_func(entity_id, data, db, user_id, tenant_id)
        
        router.put("/{entity_id}", response_model=response_schema)(update_endpoint)
        
        # Define the delete endpoint function
        async def delete_endpoint(
            entity_id: UUID,
            db: AsyncSession = Depends(),
            user_id: str = Depends(get_user_id_dependency),
            tenant_id: str = Depends(get_tenant_id_dependency) if tenant_context else None
        ):
            return await delete_func(entity_id, db, user_id, tenant_id)
        
        router.delete("/{entity_id}")(delete_endpoint)
        
        # Define the list endpoint function
        async def list_endpoint(
            db: AsyncSession = Depends(),
            user_id: str = Depends(get_user_id_dependency),
            tenant_id: str = Depends(get_tenant_id_dependency) if tenant_context else None,
            skip: int = 0,
            limit: int = 100
        ):
            return await list_func(db, user_id, tenant_id, skip, limit)
        
        router.get("/", response_model=List[response_schema])(list_endpoint)
        
        return router