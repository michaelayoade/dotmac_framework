#!/usr/bin/env python3
"""
DotMac Framework Critical Fixes Action Plan
Provides specific code examples and fixes for critical issues
"""

# CRITICAL FIX 1: SQL Injection in Tenant Middleware
# File: /home/dotmac_framework/src/dotmac_shared/security/tenant_middleware.py

sql_injection_fix = """
# BEFORE (VULNERABLE):
await session.execute(f"SELECT set_config('app.current_tenant_id', '{tenant_id}', false);")

# AFTER (SECURE):
from sqlalchemy import text

await session.execute(
    text("SELECT set_config('app.current_tenant_id', :tenant_id, false)"),
    {"tenant_id": tenant_id}
)

# Or even better, create a dedicated function:
async def set_tenant_context(session: AsyncSession, tenant_id: str, user_id: str = None):
    \"\"\"Securely set tenant context with parameterized queries\"\"\"
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, false)"),
        {"tenant_id": tenant_id}
    )
    
    if user_id:
        await session.execute(
            text("SELECT set_config('app.current_user_id', :user_id, false)"),
            {"user_id": user_id}
        )
"""

# CRITICAL FIX 2: Remove Hardcoded Secrets
hardcoded_secrets_fix = """
# BEFORE (INSECURE):
PASSWORD = "admin123"
API_KEY = "sk-123456789"

# AFTER (SECURE):
import os
from dotmac.core.config import settings

# Use environment variables
PASSWORD = os.getenv("ADMIN_PASSWORD")
API_KEY = os.getenv("API_KEY")

# Or use Pydantic settings
from pydantic_settings import BaseSettings

class SecuritySettings(BaseSettings):
    admin_password: str
    api_key: str
    jwt_secret: str
    
    class Config:
        env_prefix = "DOTMAC_"
        case_sensitive = False
"""

# ARCHITECTURE FIX 1: Base Repository Pattern
base_repository_pattern = """
# Create: /home/dotmac_framework/src/dotmac_shared/repositories/base.py

from abc import ABC, abstractmethod
from typing import Any, Generic, List, Optional, TypeVar, Dict
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from dotmac.core.exceptions import NotFoundError, ValidationError

ModelType = TypeVar("ModelType")

class BaseRepository(Generic[ModelType], ABC):
    \"\"\"
    Base repository class providing common CRUD operations.
    
    This class should be inherited by all repository classes to ensure
    consistent patterns and error handling across the framework.
    \"\"\"
    
    def __init__(self, session: AsyncSession, model_class: type[ModelType]):
        self.session = session
        self.model_class = model_class
    
    async def get_by_id(self, id: UUID) -> Optional[ModelType]:
        \"\"\"Get a single record by ID\"\"\"
        try:
            result = await self.session.execute(
                select(self.model_class).where(self.model_class.id == id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching {self.model_class.__name__} by ID {id}: {e}")
            raise
    
    async def get_all(
        self, 
        limit: int = 100, 
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        \"\"\"Get all records with pagination and optional filters\"\"\"
        try:
            query = select(self.model_class)
            
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model_class, field):
                        query = query.where(getattr(self.model_class, field) == value)
            
            query = query.offset(offset).limit(limit)
            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching {self.model_class.__name__} records: {e}")
            raise
    
    async def create(self, **kwargs) -> ModelType:
        \"\"\"Create a new record\"\"\"
        try:
            instance = self.model_class(**kwargs)
            self.session.add(instance)
            await self.session.flush()
            await self.session.refresh(instance)
            return instance
        except Exception as e:
            logger.error(f"Error creating {self.model_class.__name__}: {e}")
            raise ValidationError(f"Failed to create {self.model_class.__name__}")
    
    async def update(self, id: UUID, **kwargs) -> ModelType:
        \"\"\"Update a record by ID\"\"\"
        try:
            stmt = (
                update(self.model_class)
                .where(self.model_class.id == id)
                .values(**kwargs)
                .returning(self.model_class)
            )
            result = await self.session.execute(stmt)
            instance = result.scalar_one_or_none()
            
            if not instance:
                raise NotFoundError(f"{self.model_class.__name__} with ID {id} not found")
            
            return instance
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating {self.model_class.__name__} {id}: {e}")
            raise ValidationError(f"Failed to update {self.model_class.__name__}")
    
    async def delete(self, id: UUID) -> bool:
        \"\"\"Delete a record by ID\"\"\"
        try:
            result = await self.session.execute(
                delete(self.model_class).where(self.model_class.id == id)
            )
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting {self.model_class.__name__} {id}: {e}")
            raise


# Example usage in existing repositories:
class CustomerRepository(BaseRepository[Customer]):
    \"\"\"Customer repository with base functionality\"\"\"
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Customer)
    
    async def get_by_email(self, email: str) -> Optional[Customer]:
        \"\"\"Get customer by email address\"\"\"
        try:
            result = await self.session.execute(
                select(Customer).where(Customer.email == email)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching customer by email {email}: {e}")
            raise
"""

# ARCHITECTURE FIX 2: Base Service Pattern
base_service_pattern = """
# Create: /home/dotmac_framework/src/dotmac_shared/services/base.py

from abc import ABC
import logging
from typing import Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from dotmac.core.exceptions import DotMacError, ValidationError, NotFoundError

logger = logging.getLogger(__name__)

class BaseService(ABC):
    \"\"\"
    Base service class providing common functionality and error handling.
    
    All service classes should inherit from this to ensure consistent
    patterns across the framework.
    \"\"\"
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            await self.session.commit()
        else:
            await self.session.rollback()
            self.logger.error(f"Service operation failed: {exc_val}")
    
    def _validate_required_fields(self, data: dict, required_fields: list[str]) -> None:
        \"\"\"Validate that required fields are present\"\"\"
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
    
    def _log_operation(self, operation: str, entity_id: Optional[UUID] = None, **context):
        \"\"\"Log service operations with context\"\"\"
        log_data = {"operation": operation, "service": self.__class__.__name__}
        if entity_id:
            log_data["entity_id"] = str(entity_id)
        log_data.update(context)
        self.logger.info("Service operation", extra=log_data)
    
    async def _handle_service_error(self, operation: str, error: Exception) -> None:
        \"\"\"Standardized error handling for service operations\"\"\"
        self.logger.error(
            f"Service error in {operation}: {str(error)}",
            exc_info=True,
            extra={"operation": operation, "service": self.__class__.__name__}
        )
        
        if isinstance(error, DotMacError):
            raise
        else:
            raise DotMacError(f"Service operation '{operation}' failed") from error


# Example usage in existing services:
class BillingService(BaseService):
    \"\"\"Billing service with standardized patterns\"\"\"
    
    def __init__(self, session: AsyncSession, billing_repo: BillingRepository):
        super().__init__(session)
        self.billing_repo = billing_repo
    
    async def create_invoice(self, customer_id: UUID, line_items: list[dict]) -> Invoice:
        \"\"\"Create invoice with proper error handling\"\"\"
        try:
            self._validate_required_fields(
                {"customer_id": customer_id, "line_items": line_items},
                ["customer_id", "line_items"]
            )
            
            self._log_operation("create_invoice", customer_id=customer_id)
            
            async with self:
                invoice = await self.billing_repo.create_invoice(
                    customer_id=customer_id,
                    line_items=line_items
                )
                
                self._log_operation("invoice_created", entity_id=invoice.id)
                return invoice
                
        except Exception as e:
            await self._handle_service_error("create_invoice", e)
"""

# TESTING FIX: Integration Test Framework
integration_testing_framework = """
# Create: /home/dotmac_framework/tests/integration/conftest.py

import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from dotmac.core.database import Base
from dotmac.core.config import Settings

@pytest.fixture(scope="session")
def event_loop():
    \"\"\"Create an instance of the default event loop for the test session.\"\"\"
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def postgres_container():
    \"\"\"Start PostgreSQL container for testing\"\"\"
    with PostgresContainer("postgres:15") as postgres:
        yield postgres

@pytest.fixture(scope="session") 
async def redis_container():
    \"\"\"Start Redis container for testing\"\"\"
    with RedisContainer("redis:7") as redis:
        yield redis

@pytest.fixture(scope="session")
async def test_engine(postgres_container):
    \"\"\"Create test database engine\"\"\"
    database_url = postgres_container.get_connection_url()
    engine = create_async_engine(database_url, echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    \"\"\"Create test database session\"\"\"
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    
    async with async_session() as session:
        # Start transaction
        trans = await session.begin()
        
        yield session
        
        # Rollback transaction to clean up
        await trans.rollback()

@pytest.fixture
async def test_settings(postgres_container, redis_container):
    \"\"\"Create test settings\"\"\"
    return Settings(
        database_url=postgres_container.get_connection_url(),
        redis_url=redis_container.get_connection_url(),
        environment="testing",
        jwt_secret="test-secret",
    )

# Example Integration Test:
# tests/integration/test_billing_workflow.py

import pytest
from uuid import uuid4
from dotmac.billing.models import Customer, Invoice
from dotmac.billing.services import BillingService
from dotmac.billing.repositories import BillingRepository

@pytest.mark.integration
class TestBillingWorkflow:
    \"\"\"Integration tests for complete billing workflows\"\"\"
    
    async def test_complete_billing_cycle(self, session, test_settings):
        \"\"\"Test complete billing cycle from customer creation to invoice generation\"\"\"
        # Arrange
        billing_repo = BillingRepository(session)
        billing_service = BillingService(session, billing_repo)
        
        customer_data = {
            "name": "Test Customer",
            "email": "test@example.com",
            "tenant_id": uuid4()
        }
        
        # Act - Create customer
        customer = await billing_repo.create_customer(**customer_data)
        assert customer.id is not None
        
        # Act - Create invoice
        line_items = [
            {"description": "Service A", "amount": 100.00},
            {"description": "Service B", "amount": 50.00}
        ]
        
        invoice = await billing_service.create_invoice(
            customer_id=customer.id,
            line_items=line_items
        )
        
        # Assert
        assert invoice.customer_id == customer.id
        assert len(invoice.line_items) == 2
        assert invoice.total == 150.00
        assert invoice.status == "draft"
        
        # Act - Process invoice
        processed_invoice = await billing_service.process_invoice(invoice.id)
        
        # Assert
        assert processed_invoice.status == "sent"
        assert processed_invoice.sent_at is not None
"""

# ERROR HANDLING FIX: Standardized Exception Handler
error_handling_fix = """
# Create: /home/dotmac_framework/src/dotmac_shared/api/exception_handlers.py

import logging
from typing import Union
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, NoResultFound
from pydantic import ValidationError

from dotmac.core.exceptions import (
    DotMacError,
    NotFoundError,
    ValidationError as DotMacValidationError,
    UnauthorizedError,
    ForbiddenError
)

logger = logging.getLogger(__name__)

async def dotmac_exception_handler(
    request: Request, 
    exc: DotMacError
) -> JSONResponse:
    \"\"\"Handle DotMac framework exceptions\"\"\"
    logger.error(
        f"DotMac exception: {exc}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__,
            "user_id": getattr(request.state, 'user_id', None),
            "tenant_id": getattr(request.state, 'tenant_id', None)
        }
    )
    
    status_code_map = {
        NotFoundError: status.HTTP_404_NOT_FOUND,
        DotMacValidationError: status.HTTP_400_BAD_REQUEST,
        UnauthorizedError: status.HTTP_401_UNAUTHORIZED,
        ForbiddenError: status.HTTP_403_FORBIDDEN,
    }
    
    status_code = status_code_map.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
                "code": status_code,
                "request_id": getattr(request.state, 'request_id', None)
            }
        }
    )

async def validation_exception_handler(
    request: Request, 
    exc: ValidationError
) -> JSONResponse:
    \"\"\"Handle Pydantic validation exceptions\"\"\"
    logger.warning(
        f"Validation error: {exc}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors()
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "type": "ValidationError",
                "message": "Request validation failed",
                "details": exc.errors(),
                "request_id": getattr(request.state, 'request_id', None)
            }
        }
    )

async def sqlalchemy_exception_handler(
    request: Request, 
    exc: Union[IntegrityError, NoResultFound]
) -> JSONResponse:
    \"\"\"Handle SQLAlchemy exceptions\"\"\"
    logger.error(
        f"Database error: {exc}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__
        }
    )
    
    if isinstance(exc, IntegrityError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": {
                    "type": "IntegrityError", 
                    "message": "Database constraint violation",
                    "request_id": getattr(request.state, 'request_id', None)
                }
            }
        )
    elif isinstance(exc, NoResultFound):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "type": "NotFound",
                    "message": "Resource not found",
                    "request_id": getattr(request.state, 'request_id', None)
                }
            }
        )

async def generic_exception_handler(
    request: Request, 
    exc: Exception
) -> JSONResponse:
    \"\"\"Handle unexpected exceptions\"\"\"
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__
        }
    )
    
    # Don't expose internal error details in production
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "InternalServerError",
                "message": "An internal error occurred",
                "request_id": getattr(request.state, 'request_id', None)
            }
        }
    )

# Register handlers in FastAPI app:
def register_exception_handlers(app):
    \"\"\"Register all exception handlers\"\"\"
    app.add_exception_handler(DotMacError, dotmac_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, sqlalchemy_exception_handler)
    app.add_exception_handler(NoResultFound, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
"""

# INPUT VALIDATION FIX: API Endpoint Validation
input_validation_fix = """
# Example: Secure API endpoint with proper validation
# File: /home/dotmac_framework/src/dotmac_isp/api/billing_router.py

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from uuid import UUID
from typing import Optional, List
from decimal import Decimal

from dotmac.core.dependencies import get_current_user, get_session
from dotmac.billing.services import BillingService
from dotmac.billing.models import User

router = APIRouter(prefix="/billing", tags=["billing"])

# Proper input validation schemas
class CreateInvoiceRequest(BaseModel):
    customer_id: UUID
    line_items: List[dict] = Field(min_items=1, max_items=100)
    due_date: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=500)
    
    @validator('line_items')
    def validate_line_items(cls, v):
        for item in v:
            if 'description' not in item or 'amount' not in item:
                raise ValueError('Each line item must have description and amount')
            if not isinstance(item['amount'], (int, float, Decimal)):
                raise ValueError('Amount must be numeric')
            if item['amount'] <= 0:
                raise ValueError('Amount must be positive')
        return v

class InvoiceResponse(BaseModel):
    id: UUID
    customer_id: UUID
    total: Decimal
    status: str
    created_at: str
    
    class Config:
        from_attributes = True

# SECURE: Properly validated endpoint
@router.post("/invoices", response_model=InvoiceResponse)
async def create_invoice(
    request: CreateInvoiceRequest,  # Pydantic validation
    current_user: User = Depends(get_current_user),  # Authentication
    session = Depends(get_session)  # Dependency injection
):
    \"\"\"Create a new invoice with proper validation and authentication\"\"\"
    
    # Additional business logic validation
    if not current_user.has_permission("billing:create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create invoices"
        )
    
    billing_service = BillingService(session)
    
    try:
        invoice = await billing_service.create_invoice(
            customer_id=request.customer_id,
            line_items=request.line_items,
            created_by=current_user.id
        )
        return InvoiceResponse.from_orm(invoice)
        
    except Exception as e:
        logger.error(f"Failed to create invoice: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create invoice"
        )

# BEFORE (INSECURE):
# @router.post("/invoices") 
# async def create_invoice(request: Request):
#     data = await request.json()  # No validation!
#     customer_id = data.get("customer_id")  # Could be None/invalid
#     # Direct database access without validation
"""

if __name__ == "__main__":
    print("DotMac Framework Critical Fixes Action Plan")
    print("=" * 50)
    print()
    print("This file contains specific code examples and fixes for:")
    print("1. SQL Injection vulnerabilities")  
    print("2. Hardcoded secrets removal")
    print("3. Base repository and service patterns")
    print("4. Integration testing framework")
    print("5. Standardized error handling")
    print("6. Secure API endpoint validation")
    print()
    print("Each fix includes BEFORE/AFTER examples and implementation guidance.")
    print("Refer to the comprehensive gap analysis report for complete details.")