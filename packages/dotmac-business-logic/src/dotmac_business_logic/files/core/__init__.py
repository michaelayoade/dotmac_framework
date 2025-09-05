"""
Core file generation components.
"""
try:
    from .generators import CSVGenerator, ExcelGenerator, PDFGenerator
except (ImportError, ValueError) as e:
    # ValueError can occur from pandas/numpy compatibility issues
    import warnings

    warnings.warn(f"File generators not available: {e}")
    PDFGenerator = ExcelGenerator = CSVGenerator = None

try:
    from .templates import TemplateEngine
except (ImportError, ValueError) as e:
    import warnings

    warnings.warn(f"Template engine not available: {e}")
    TemplateEngine = None

try:
    from .processors import ImageProcessor
except (ImportError, ValueError) as e:
    import warnings

    warnings.warn(f"Image processor not available: {e}")
    ImageProcessor = None

__all__ = [
    "PDFGenerator",
    "ExcelGenerator",
    "CSVGenerator",
    "TemplateEngine",
    "ImageProcessor",
]
