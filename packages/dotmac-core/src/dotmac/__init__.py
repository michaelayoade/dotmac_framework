"""DotMac Core Package - Namespace initializer."""

from pkgutil import extend_path

# Enable namespace package across dotmac-* packages
__path__ = extend_path(__path__, __name__)

# Minimal metadata (avoid re-exporting to prevent conflicts)
__version__ = "0.1.0-stub"
