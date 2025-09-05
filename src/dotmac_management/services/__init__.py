"""Service layer package.

This package intentionally avoids importing submodules at import time to prevent
test discovery/import issues when optional services are not present.
Import submodules directly, e.g.:

from dotmac_management.services.tenant_provisioning import TenantProvisioningService
"""
__all__ = []
