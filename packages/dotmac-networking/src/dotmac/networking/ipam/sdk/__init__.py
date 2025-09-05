"""IPAM SDK package."""
try:
    from .ipam_sdk import IPAMSDK
except ImportError as e:
    import warnings

    warnings.warn(f"IPAM SDK not available: {e}")
    IPAMSDK = None

__all__ = ["IPAMSDK"]
