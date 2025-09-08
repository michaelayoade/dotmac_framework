"""IPAM services package."""

try:
    from .ipam_service import IPAMService
except ImportError as e:
    import warnings

    warnings.warn(f"IPAM service not available: {e}", stacklevel=2)
    IPAMService = None

__all__ = ["IPAMService"]
