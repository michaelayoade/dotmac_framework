"""
ISP Framework Models
Centralized import of all ISP models to ensure they are registered with SQLAlchemy
"""

# Import base classes first
from dotmac_isp.shared.database.base import Base, BaseModel

# Import module models one by one to avoid conflicts
_imported_modules = set()

def _safe_import(module_name):
    """Safely import models avoiding duplicates"""
    if module_name in _imported_modules:
        return
    _imported_modules.add(module_name)
    
    try:
        if module_name == "identity":
            from dotmac_isp.modules.identity import models as identity_models
        elif module_name == "services":
            from dotmac_isp.modules.services import models as services_models  
        elif module_name == "billing":
            from dotmac_isp.modules.billing import models as billing_models
        elif module_name == "analytics":
            from dotmac_isp.modules.analytics import models as analytics_models
        elif module_name == "captive_portal":
            from dotmac_isp.modules.captive_portal import models as portal_models
        elif module_name == "gis":
            from dotmac_isp.modules.gis import models as gis_models
        elif module_name == "portal_management":
            from dotmac_isp.modules.portal_management import models as portal_mgmt_models
        elif module_name == "resellers":
            from dotmac_isp.modules.resellers import models as resellers_models
    except ImportError as e:
        print(f"Warning: Could not import {module_name} models: {e}")

# Import all modules
for module in ["identity", "services", "billing", "analytics", "captive_portal", "gis", "portal_management", "resellers"]:
    _safe_import(module)

# Export commonly used classes
__all__ = [
    "Base",
    "BaseModel",
]