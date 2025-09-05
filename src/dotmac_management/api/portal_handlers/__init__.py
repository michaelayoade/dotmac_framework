"""
Portal-specific API endpoints.
"""

from fastapi import APIRouter

from .master_admin import router as master_admin_router

portals_router = APIRouter()
portals_router = APIRouter()

# Include portal routers
portals_router.include_router(master_admin_router, prefix="/master-admin", tags=["Master Admin Portal"])

__all__ = ["portals_router"]
