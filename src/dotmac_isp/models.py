"""
ISP Framework Models
Centralized import of all ISP models to ensure they are registered with SQLAlchemy
"""

import importlib

from dotmac_isp.shared.database.base import Base, BaseModel

_imported_modules = set()


def _safe_import(module_name):
    """Safely import models avoiding duplicates"""
    if module_name in _imported_modules:
        return
    _imported_modules.add(module_name)

    try:
        module_map = {
            "identity": "dotmac_isp.modules.identity.models",
            "services": "dotmac_isp.modules.services.models",
            "billing": "dotmac_isp.modules.billing.models",
            "analytics": "dotmac_isp.modules.analytics.models",
            "captive_portal": "dotmac_isp.modules.captive_portal.models",
            "gis": "dotmac_isp.modules.gis.models",
            "portal_management": "dotmac_isp.modules.portal_management.models",
            "resellers": "dotmac_isp.modules.resellers.models",
        }
        importlib.import_module(module_map[module_name])
    except Exception:
        # Module may be optional/not yet implemented; ignore import errors
        pass


# Import all modules
for module in [
    "identity",
    "services",
    "billing",
    "analytics",
    "captive_portal",
    "gis",
    "portal_management",
    "resellers",
]:
    _safe_import(module)

# Export commonly used classes
__all__ = [
    "Base",
    "BaseModel",
]
