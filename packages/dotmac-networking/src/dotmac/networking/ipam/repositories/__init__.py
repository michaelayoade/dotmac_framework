"""IPAM repositories package."""

try:
    from .ipam_repository import IPAMRepository
except ImportError as e:
    import warnings

    warnings.warn(f"IPAM repository not available: {e}", stacklevel=2)
    IPAMRepository = None

__all__ = ["IPAMRepository"]
