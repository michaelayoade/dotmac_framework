"""
DotMac File Service - Document Generation Hub.

This package provides comprehensive file generation capabilities including:
- PDF document generation with ReportLab
- Excel and CSV export functionality
- Template-based content generation with Jinja2
- Image processing and chart generation
- Multi-tenant file storage abstraction
- Async background processing for large files
"""

# Core imports with graceful handling of missing dependencies
try:
    from .core.generators import CSVGenerator, ExcelGenerator, PDFGenerator
except (ImportError, ValueError) as e:
    # Log warning but don't fail - generators may need optional dependencies
    # ValueError can occur from pandas/numpy compatibility issues
    import warnings

    warnings.warn(f"File generators not available due to missing dependencies: {e}")
    PDFGenerator = ExcelGenerator = CSVGenerator = None

try:
    from .core.templates import TemplateEngine
except (ImportError, ValueError) as e:
    import warnings

    warnings.warn(f"Template engine not available due to dependencies: {e}")
    TemplateEngine = None

try:
    from .core.processors import ImageProcessor
except (ImportError, ValueError) as e:
    import warnings

    warnings.warn(f"Image processor not available: {e}")
    ImageProcessor = None

try:
    from .storage.backends import LocalFileStorage, S3FileStorage, StorageBackend
except ImportError as e:
    import warnings

    warnings.warn(f"Storage backends not fully available: {e}")
    StorageBackend = LocalFileStorage = S3FileStorage = None

try:
    from .adapters.isp_adapter import ISPFileAdapter
except (ImportError, ValueError):
    ISPFileAdapter = None

try:
    from .adapters.management_adapter import ManagementPlatformAdapter
except (ImportError, ValueError):
    ManagementPlatformAdapter = None

# Cache integration (should always be available)
from .cache_integration import (
    CacheServiceFileStorage,
    CacheServiceTemplateStore,
    FileServiceCacheIntegrationFactory,
)

# Version info
__version__ = "1.0.0"
__author__ = "DotMac Team"
__email__ = "dev@dotmac.com"

# Main exports
__all__ = [
    # Core generators
    "PDFGenerator",
    "ExcelGenerator",
    "CSVGenerator",
    # Template system
    "TemplateEngine",
    # Image processing
    "ImageProcessor",
    # Storage backends
    "StorageBackend",
    "LocalFileStorage",
    "S3FileStorage",
    # Platform adapters
    "ISPFileAdapter",
    "ManagementPlatformAdapter",
    # Version info
    "__version__",
]

# Configuration defaults
DEFAULT_CONFIG = {
    "storage": {
        "backend": "local",
        "local_path": "/tmp/dotmac_files",
        "max_file_size": 100 * 1024 * 1024,  # 100MB
    },
    "pdf": {
        "page_size": "letter",
        "margins": 72,  # 1 inch
        "font_family": "Helvetica",
        "font_size": 12,
    },
    "excel": {
        "default_sheet_name": "Data",
        "auto_fit_columns": True,
        "freeze_panes": True,
    },
    "templates": {
        "cache_ttl": 3600,  # 1 hour
        "auto_escape": True,
        "template_dir": "templates",
    },
    "image": {
        "max_dimensions": (2048, 2048),
        "compression_quality": 85,
        "thumbnail_size": (150, 150),
    },
    "async": {
        "enabled": True,
        "max_concurrent_jobs": 10,
        "job_timeout": 300,  # 5 minutes
    },
}


def get_version():
    """Get package version."""
    return __version__


def get_config():
    """Get default configuration."""
    return DEFAULT_CONFIG.copy()
