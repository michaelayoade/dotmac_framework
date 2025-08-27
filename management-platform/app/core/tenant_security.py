"""
Tenant Security Integration for Management Platform
Integrates Row Level Security and tenant middleware for the management platform
"""

import os
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine

# Import shared security components
import sys
sys.path.append('/home/dotmac_framework/shared')

from security.row_level_security import RLSPolicyManager, setup_complete_rls
from security.tenant_middleware import (
    create_tenant_isolation_middleware,
    create_database_tenant_middleware,
    get_tenant_from_header,
    get_user_from_jwt,
    DatabaseTenantMiddleware
)

logger = logging.getLogger(__name__)

# Global instances
rls_manager: Optional[RLSPolicyManager] = None
db_tenant_middleware: Optional[DatabaseTenantMiddleware] = None

async def init_management_tenant_security(engine: Engine, session: Session) -> Dict[str, Any]:
    """
    Initialize tenant security for Management Platform
    Note: Management Platform primarily manages tenants rather than being multi-tenant itself,
    but still needs security for tenant data segregation
    """
    global rls_manager, db_tenant_middleware
    
    try:
        # Initialize RLS manager
        rls_manager = RLSPolicyManager(engine)
        
        # For Management Platform, we focus on tenant data segregation
        # rather than full multi-tenancy since it manages the tenants themselves
        
        # Create audit infrastructure
        audit_table_created = await rls_manager.create_audit_log_table()
        audit_functions_created = (
            await rls_manager.create_tenant_isolation_function() and
            await rls_manager.create_audit_trigger_function()
        )
        
        # Initialize database tenant middleware
        db_tenant_middleware = create_database_tenant_middleware(rls_manager)
        
        logger.info("✅ Management Platform tenant security initialized")
        return {
            'success': True,
            'rls_manager_created': rls_manager is not None,
            'db_middleware_created': db_tenant_middleware is not None,
            'audit_table_created': audit_table_created,
            'audit_functions_created': audit_functions_created,
            'note': 'Management Platform configured for tenant data segregation'
        }
        
    except Exception as e:
        logger.error(f"❌ Management Platform tenant security initialization failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def get_management_rls_manager() -> Optional[RLSPolicyManager]:
    """Get the RLS manager for Management Platform"""
    return rls_manager

def get_management_db_middleware() -> Optional[DatabaseTenantMiddleware]:
    """Get the database tenant middleware for Management Platform"""
    return db_tenant_middleware

def extract_management_context_from_request(request: Request) -> str:
    """
    Extract management context from request
    
    For Management Platform, this represents the administrative context
    rather than a traditional tenant ID
    """
    # Try header first (for API requests)
    admin_context = request.headers.get('x-admin-context')
    if admin_context:
        return admin_context
    
    # Try to extract from JWT token
    try:
        # This would integrate with your JWT implementation
        # For now, use a default management context
        return os.getenv('MANAGEMENT_CONTEXT_ID', 'dotmac-management-01')
    except:
        return os.getenv('MANAGEMENT_CONTEXT_ID', 'dotmac-management-01')

def extract_admin_user_from_request(request: Request) -> Optional[str]:
    """Extract admin user ID from request"""
    # Try header first
    admin_id = request.headers.get('x-admin-id')
    if admin_id:
        return admin_id
    
    # Try to extract from JWT token
    try:
        # This would integrate with your JWT implementation
        return None
    except:
        return None

def add_management_tenant_security_middleware(app: FastAPI) -> None:
    """
    Add tenant security middleware to Management Platform
    
    Note: This is lighter than full multi-tenant middleware since
    Management Platform manages tenants rather than being multi-tenant
    """
    # Create basic isolation middleware for audit trails
    tenant_middleware = create_tenant_isolation_middleware(
        get_tenant_func=extract_management_context_from_request,
        get_user_func=extract_admin_user_from_request,
        exempt_paths=[
            '/docs',
            '/redoc',
            '/openapi.json',
            '/health',
            '/metrics',
            '/api/auth',
            '/api/health'
        ],
        strict_mode=False  # Less strict for management interface
    )
    
    # Add middleware to app
    app.middleware("http")(tenant_middleware)
    logger.info("✅ Management Platform security middleware added")

# Dependency for getting audit-aware database sessions
async def get_management_db_session(
    request: Request,
    session: Session = Depends()
) -> Session:
    """
    Get a database session with proper audit context set for Management Platform
    """
    if not db_tenant_middleware:
        # If middleware not available, return regular session but log warning
        logger.warning("Database audit middleware not available - using regular session")
        yield session
        return
    
    context_id = extract_management_context_from_request(request)
    admin_id = extract_admin_user_from_request(request)
    client_ip = request.client.host if request.client else None
    
    # Use context manager to ensure proper audit context
    async with db_tenant_middleware.tenant_session(
        session=session,
        tenant_id=context_id,  # Using context as tenant for audit purposes
        user_id=admin_id,
        client_ip=client_ip
    ) as audit_session:
        yield audit_session

# Security validation functions for Management Platform
async def validate_tenant_data_segregation() -> Dict[str, Any]:
    """
    Validate that tenant data is properly segregated in Management Platform
    """
    if not rls_manager:
        return {'error': 'RLS manager not initialized'}
    
    try:
        from database import get_session
        
        async with get_session() as session:
            # Check tenant table isolation
            status = await rls_manager.get_rls_status(session)
            
            return {
                'management_platform_security': 'active',
                'audit_infrastructure': 'enabled',
                'tenant_data_segregation': status
            }
    except Exception as e:
        return {'error': str(e)}

async def get_management_security_status() -> Dict[str, Any]:
    """Get current security status for Management Platform"""
    if not rls_manager:
        return {'error': 'Security manager not initialized'}
    
    try:
        from database import get_session
        
        async with get_session() as session:
            status = await rls_manager.get_rls_status(session)
            
            return {
                'platform': 'management',
                'security_type': 'tenant_data_segregation',
                'rls_status': status,
                'audit_enabled': True,
                'middleware_active': db_tenant_middleware is not None
            }
    except Exception as e:
        return {'error': str(e)}