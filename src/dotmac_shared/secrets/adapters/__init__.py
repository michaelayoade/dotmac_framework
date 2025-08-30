"""
Platform adapters for secrets integration.
"""

try:
    from .isp_adapter import ISPSecretsAdapter
except ImportError as e:
    import warnings

    warnings.warn(f"ISP secrets adapter not available: {e}")
    ISPSecretsAdapter = None

try:
    from .management_adapter import ManagementPlatformSecretsAdapter
except ImportError as e:
    import warnings

    warnings.warn(f"Management platform secrets adapter not available: {e}")
    ManagementPlatformSecretsAdapter = None

__all__ = [
    "ISPSecretsAdapter",
    "ManagementPlatformSecretsAdapter",
]
