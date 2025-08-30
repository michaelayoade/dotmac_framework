"""
Platform adapters for observability integration.
"""

# Import adapters with graceful handling
try:
    from .isp_adapter import ISPObservabilityAdapter
except ImportError as e:
    import warnings

    warnings.warn(f"ISP observability adapter not available: {e}")
    ISPObservabilityAdapter = None

try:
    from .management_adapter import ManagementPlatformAdapter
except ImportError as e:
    import warnings

    warnings.warn(f"Management platform adapter not available: {e}")
    ManagementPlatformAdapter = None

__all__ = [
    "ISPObservabilityAdapter",
    "ManagementPlatformAdapter",
]
