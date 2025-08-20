"""
DotMac Developer Tools - Comprehensive CLI and SDK generation platform.

This package provides automated service scaffolding, multi-language SDK generation,
developer portal management, and zero-trust security implementation for the DotMac ISP framework.
"""

from .core.config import DevToolsConfig, load_config
from .sdks.developer_portal import DeveloperPortalSDK
from .sdks.sdk_generator import SDKGeneratorSDK
from .sdks.service_generator import ServiceGeneratorSDK
from .sdks.zero_trust import ZeroTrustSecuritySDK

__version__ = "1.0.0"
__author__ = "DotMac Framework Team"
__description__ = "Developer tools and SDK generation for DotMac ISP framework"

__all__ = [
    'DevToolsConfig',
    'load_config',
    'ServiceGeneratorSDK',
    'SDKGeneratorSDK',
    'DeveloperPortalSDK',
    'ZeroTrustSecuritySDK'
]
