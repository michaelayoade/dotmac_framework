"""
ISP API router for multi-currency exchange functionality.

Provides exchange rate management endpoints for ISP applications.
"""

from fastapi import APIRouter

from dotmac_business_logic.billing.api.exchange_routes import router as exchange_router

router = APIRouter(prefix="/billing", tags=["ISP Billing - Currency Exchange"])

# Include the shared exchange routes
router.include_router(exchange_router)

# Export for main app
__all__ = ["router"]
