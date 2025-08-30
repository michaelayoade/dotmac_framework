"""IPAM services package."""

try:
    from .ipam_service import IPAMService
except ImportError as e:
    import warnings

    warnings.warn(f"IPAM service not available: {e}")
    IPAMService = None

__all__ = ["IPAMService"]
