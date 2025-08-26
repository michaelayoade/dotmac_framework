import logging

logger = logging.getLogger(__name__)

"""
Service Generator Templates

ARCHITECTURE IMPROVEMENT: Provides code generation tools to create standardized
services that follow the BaseTenantService pattern. Ensures consistency across
all new services and prevents the creation of legacy patterns.
"""

import os
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ServiceConfig:
    """Configuration for service generation."""
    module_name: str
    service_name: str
    model_name: str
    tenant_aware: bool = True
    async_operations: bool = True
    include_crud: bool = True
    include_business_rules: bool = True
    custom_methods: Optional[Dict[str, str]] = None


class ServiceGenerator:
    """
    Generates standardized service classes following DotMac patterns.
    
    PATTERN: Template Method + Code Generation
    - Enforces standardized service patterns
    - Prevents legacy pattern creation
    - Generates consistent CRUD operations
    - Includes validation and business rules
    - Creates async-compatible services
    
    Features:
    - BaseTenantService inheritance
    - Async/await patterns
    - Schema validation
    - Business rule hooks
    - Error handling
    - Logging integration
    """
    
    BASE_SERVICE_TEMPLATE = '''"""Service layer for {module_name} operations."""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

from dotmac_isp.shared.base_service import {base_class}
from dotmac_isp.modules.{module_name} import schemas
from dotmac_isp.modules.{module_name}.models import {model_name}
from dotmac_isp.shared.exceptions import (
    ServiceError,
    EntityNotFoundError,
    ValidationError,
    BusinessRuleError,
)


class {service_name}({base_class}[{model_name}, schemas.{model_name}Create, schemas.{model_name}Update, schemas.{model_name}Response]):
    """Service for {module_name} operations."""
    
    def __init__(self, db: Session{tenant_param}):
        super().__init__(
            db=db,
            model_class={model_name},
            create_schema=schemas.{model_name}Create,
            update_schema=schemas.{model_name}Update,
            response_schema=schemas.{model_name}Response,{tenant_init}
        )
{business_rules}
{custom_methods}
'''

    BUSINESS_RULES_TEMPLATE = '''
    async def _validate_create_rules(self, data: schemas.{model_name}Create) -> None:
        """Validate business rules for {model_name} creation."""
        """Business validation rules are implemented via the business_rules system.
        Override this method to add entity-specific validation logic.
        """
        # Entity-specific validation logic goes here
        pass
    
    async def _validate_update_rules(self, entity: {model_name}, data: schemas.{model_name}Update) -> None:
        """Validate business rules for {model_name} updates."""
        """Business validation rules are implemented via the business_rules system.
        Override this method to add update-specific validation logic.
        """
        # Update-specific validation logic goes here
        pass
    
    async def _validate_delete_rules(self, entity: {model_name}) -> None:
        """Validate business rules for {model_name} deletion."""
        """Business validation rules are implemented via the business_rules system.
        Override this method to add deletion-specific validation logic.
        """
        # Deletion-specific validation logic goes here
        pass
'''

    CUSTOM_METHOD_TEMPLATE = '''
    async def {method_name}(self{params}) -> {return_type}:
        """
        {docstring}
        """
        try:
            """Implementation for {method_name} method.
            Add your custom business logic here.
            """
            # Custom business logic implementation
            {implementation}
        except Exception as e:
            self._logger.error(f"Error in {method_name}: {{e}}")
            raise ServiceError(f"Failed to {method_name}: {{e}}")
'''

    def generate_service(self, config: ServiceConfig) -> str:
        """
        Generate service code from configuration.
        
        Args:
            config: Service configuration
            
        Returns:
            Generated service code
        """
        # Determine base class
        base_class = "BaseTenantService" if config.tenant_aware else "BaseService"
        
        # Tenant parameters
        tenant_param = ", tenant_id: str" if config.tenant_aware else ""
        tenant_init = "\n            tenant_id=tenant_id" if config.tenant_aware else ""
        
        # Business rules
        business_rules = ""
        if config.include_business_rules:
            business_rules = self.BUSINESS_RULES_TEMPLATE.format(
                model_name=config.model_name
            )
        
        # Custom methods
        custom_methods = ""
        if config.custom_methods:
            for method_name, method_config in config.custom_methods.items():
                custom_methods += self.CUSTOM_METHOD_TEMPLATE.format(
                    method_name=method_name,
                    params=method_config.get('params', ''),
                    return_type=method_config.get('return_type', 'Any'),
                    docstring=method_config.get('docstring', f'{method_name} operation'),
                    implementation=method_config.get('implementation', 'pass')
                )
        
        # Generate service code
        service_code = self.BASE_SERVICE_TEMPLATE.format(
            module_name=config.module_name,
            service_name=config.service_name,
            model_name=config.model_name,
            base_class=base_class,
            tenant_param=tenant_param,
            tenant_init=tenant_init,
            business_rules=business_rules,
            custom_methods=custom_methods
        )
        
        return service_code
    
    def generate_schema_template(self, config: ServiceConfig) -> str:
        """Generate Pydantic schema templates."""
        return f'''"""Pydantic schemas for {config.module_name} operations."""

from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


class {config.model_name}Base(BaseModel, ConfigDict):
    """Base {config.model_name} schema."""
    # Implementation needed: Add common fields shared between create/update/response schemas
    # Examples:
    # name: str = Field(..., description="Entity name")
    # description: Optional[str] = Field(None, description="Entity description")
    # is_active: bool = Field(True, description="Whether entity is active")
    pass


class {config.model_name}Create({config.model_name}Base):
    """Schema for creating {config.model_name}."""
    # Implementation needed: Add fields required for entity creation
    # Examples:
    # email: EmailStr = Field(..., description="User email address")
    # password: str = Field(..., min_length=8, description="User password")
    # tags: List[str] = Field(default_factory=list, description="Entity tags")
    pass


class {config.model_name}Update(BaseModel):
    """Schema for updating {config.model_name}."""
    # Implementation needed: Add optional fields for entity updates
    # All fields should be Optional for partial updates
    # Examples:
    # name: Optional[str] = Field(None, description="Updated name")
    # description: Optional[str] = Field(None, description="Updated description")
    # is_active: Optional[bool] = Field(None, description="Updated active status")
    pass


class {config.model_name}Response({config.model_name}Base):
    """Schema for {config.model_name} responses."""
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    {"tenant_id: str" if config.tenant_aware else ""}
    
    model_config = ConfigDict(from_attributes=True)
'''

    def generate_model_template(self, config: ServiceConfig) -> str:
        """Generate SQLAlchemy model template."""
        base_class = "TenantMixin" if config.tenant_aware else "Base"
        imports = "from dotmac_isp.shared.models import TenantMixin" if config.tenant_aware else "from dotmac_isp.shared.models import Base"
        
        return f'''"""SQLAlchemy models for {config.module_name}."""

from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, UUID as SQLUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4
import enum

{imports}


class {config.model_name}({base_class}):
    """SQLAlchemy model for {config.model_name}."""
    
    __tablename__ = '{config.module_name}_{config.model_name.lower()}s'
    
    # Implementation needed: Define database columns for this model
    # All tenant-aware models automatically include: id, tenant_id, created_at, updated_at
    # Add entity-specific fields below:
    # 
    # Examples:
    # name = Column(String(255), nullable=False, index=True)
    # description = Column(Text, nullable=True)
    # status = Column(Enum(EntityStatus), nullable=False, default=EntityStatus.ACTIVE)
    # priority = Column(Integer, nullable=False, default=1)
    # metadata_json = Column(JSON, nullable=True)
    # 
    # Relationships:
    # parent_id = Column(SQLUUID, ForeignKey('parent_table.id'), nullable=True)
    # parent = relationship('ParentModel', back_populates='children')
    pass  # Remove this once fields are added
    
    def __repr__(self):
        return f"<{config.model_name}(id={{self.id}})>"
'''

    def create_service_files(self, config: ServiceConfig, base_path: str) -> Dict[str, str]:
        """
        Create all service-related files.
        
        Args:
            config: Service configuration
            base_path: Base path for file creation
            
        Returns:
            Dictionary of file paths and their content
        """
        files = {}
        
        # Create module directory path
        module_path = Path(base_path) / "modules" / config.module_name
        
        # Service file
        service_file = module_path / "service.py"
        files[str(service_file)] = self.generate_service(config)
        
        # Schema file
        schema_file = module_path / "schemas.py"
        files[str(schema_file)] = self.generate_schema_template(config)
        
        # Model file
        model_file = module_path / "models.py"
        files[str(model_file)] = self.generate_model_template(config)
        
        # Router template
        router_file = module_path / "router.py"
        files[str(router_file)] = self.generate_router_template(config)
        
        # __init__.py
        init_file = module_path / "__init__.py"
        files[str(init_file)] = f'"""Module for {config.module_name} operations."""'
        
        return files
    
    def generate_router_template(self, config: ServiceConfig) -> str:
        """Generate FastAPI router template."""
        return f'''"""FastAPI router for {config.module_name} endpoints."""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dotmac_isp.core.database import get_db
from dotmac_isp.shared.auth import get_current_user
from . import schemas
from .service import {config.service_name}

router = APIRouter(prefix="/{config.module_name}", tags=["{config.module_name}"])


@router.post("/", response_model=schemas.{config.model_name}Response)
async def create_{config.model_name.lower()}(
    {config.model_name.lower()}_data: schemas.{config.model_name}Create,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new {config.model_name.lower()}."""
    service = {config.service_name}(db{"tenant_id=current_user.tenant_id" if config.tenant_aware else ""})
    return await service.create({config.model_name.lower()}_data)


@router.get("/", response_model=List[schemas.{config.model_name}Response])
async def list_{config.model_name.lower()}s(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List {config.model_name.lower()}s."""
    service = {config.service_name}(db{"tenant_id=current_user.tenant_id" if config.tenant_aware else ""})
    return await service.list(limit=limit, offset=skip)


@router.get("/{{id}}", response_model=schemas.{config.model_name}Response)
async def get_{config.model_name.lower()}(
    id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get {config.model_name.lower()} by ID."""
    service = {config.service_name}(db{"tenant_id=current_user.tenant_id" if config.tenant_aware else ""})
    result = await service.get_by_id(id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="{config.model_name} not found"
        )
    return result


@router.put("/{{id}}", response_model=schemas.{config.model_name}Response)
async def update_{config.model_name.lower()}(
    id: UUID,
    update_data: schemas.{config.model_name}Update,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update {config.model_name.lower()}."""
    service = {config.service_name}(db{"tenant_id=current_user.tenant_id" if config.tenant_aware else ""})
    return await service.update(id, update_data)


@router.delete("/{{id}}")
async def delete_{config.model_name.lower()}(
    id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete {config.model_name.lower()}."""
    service = {config.service_name}(db{"tenant_id=current_user.tenant_id" if config.tenant_aware else ""})
    success = await service.delete(id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="{config.model_name} not found"
        )
    return {{"message": "{config.model_name} deleted successfully"}}
'''

    def write_files(self, files: Dict[str, str]) -> None:
        """
        Write generated files to disk.
        
        Args:
            files: Dictionary of file paths and content
        """
        for file_path, content in files.items():
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(content)
            logger.info(f"Generated: {file_path}")


# CLI Interface
def generate_service_from_cli():
    """Generate service from command line input."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate standardized DotMac service')
    parser.add_argument('module_name', help='Module name (e.g., inventory)')
    parser.add_argument('model_name', help='Model name (e.g., Product)')
    parser.add_argument('--service-name', help='Service name (defaults to ModelNameService)')
    parser.add_argument('--no-tenant', action='store_true', help='Disable tenant awareness')
    parser.add_argument('--base-path', default='src/dotmac_isp', help='Base path for generation')
    
    args = parser.parse_args()
    
    config = ServiceConfig(
        module_name=args.module_name,
        service_name=args.service_name or f"{args.model_name}Service",
        model_name=args.model_name,
        tenant_aware=not args.no_tenant,
    )
    
    generator = ServiceGenerator()
    files = generator.create_service_files(config, args.base_path)
    generator.write_files(files)
    
    logger.info(f"Generated service for {config.model_name} in {config.module_name} module")
    logger.info("Next steps:")
    logger.info("1. Update module/__init__.py to include new service")
    logger.info("2. Add router to main app.py")
    logger.info("3. Create database migration")
    logger.info("4. Add tests")


if __name__ == "__main__":
    generate_service_from_cli()