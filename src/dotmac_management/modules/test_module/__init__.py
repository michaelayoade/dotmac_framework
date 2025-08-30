"""Test module to demonstrate standardized structure."""

try:
    from .router import router

    __all__ = ["router"]
except ImportError:
    __all__ = []
