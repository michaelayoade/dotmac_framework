"""Consolidated notification API router using focused sub-routers."""

from fastapi import APIRouter

from .routers.notification_router import router as notification_router
from .routers.template_router import router as template_router

# Additional routers would be imported here as they are created:
# from .routers.rule_router import router as rule_router
# from .routers.preference_router import router as preference_router
# from .routers.delivery_router import router as delivery_router
# from .routers.admin_router import router as admin_router

# Main router
router = APIRouter(prefix="/notifications", tags=["notifications"])

# Include sub-routers
router.include_router(notification_router, prefix="")
router.include_router(template_router, prefix="")

# Additional sub-routers would be included here:
# router.include_router(rule_router, prefix="/rules")
# router.include_router(preference_router, prefix="/preferences")
# router.include_router(delivery_router, prefix="/delivery")
# router.include_router(admin_router, prefix="/admin")

# Export the consolidated router
__all__ = ["router"]
