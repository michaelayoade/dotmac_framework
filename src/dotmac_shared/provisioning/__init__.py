"""
DotMac Shared Provisioning Services

Container provisioning system supporting automated ISP Framework deployment
with 4-minute deployment business requirement.

Key Features:
- Automated container creation from ISP Framework template
- Environment variable injection (database URLs, tenant configs)
- Resource allocation based on customer count (50-10,000 customers)
- Container health validation during provisioning
- Rollback capability if provisioning fails

Usage:
    from dotmac_shared.provisioning import provision_isp_container  # noqa: F401

    result = await provision_isp_container(
        isp_id=UUID("..."),
        customer_count=500,
        config=ISPConfig(...)
    )
"""

from .core.exceptions import (
    ProvisioningError,
    ResourceCalculationError,
    RollbackError,
    ValidationError,
)
from .core.provisioner import ProvisioningResult, provision_isp_container
from .core.validators import HealthStatus, validate_container_health

__version__ = "1.0.0"
__all__ = [
    "provision_isp_container",
    "validate_container_health",
    "ProvisioningResult",
    "HealthStatus",
    "ProvisioningError",
    "ValidationError",
    "RollbackError",
    "ResourceCalculationError",
]
