"""Platform adapters for portal ID collision checking."""

from .isp_adapter import ISPPortalIdCollisionChecker
from .management_adapter import ManagementPortalIdCollisionChecker

__all__ = ["ISPPortalIdCollisionChecker", "ManagementPortalIdCollisionChecker"]
