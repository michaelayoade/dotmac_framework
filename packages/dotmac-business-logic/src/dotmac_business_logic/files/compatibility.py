"""
Compatibility layer for numpy and other optional dependencies.
Handles version mismatches gracefully with fallbacks.
"""

import sys
import warnings

warnings.filterwarnings(
    "ignore", category=UserWarning, message=".*numpy.dtype size changed.*"
)


def suppress_numpy_warnings():
    """Suppress numpy compatibility warnings during import."""
    if "numpy" in sys.modules:
        # Suppress dtype warnings
        warnings.filterwarnings("ignore", message=".*numpy.dtype size changed.*")


def safe_numpy_import():
    """Safely import numpy with fallbacks."""
    try:
        suppress_numpy_warnings()
        import numpy as np

        return np
    except ImportError:
        return None
    except Exception as e:
        warnings.warn(f"Numpy compatibility issue: {e}", UserWarning, stacklevel=2)
        return None


def safe_matplotlib_import():
    """Safely import matplotlib with fallbacks."""
    try:
        import matplotlib

        # Suppress Axes3D warnings
        warnings.filterwarnings("ignore", message=".*Unable to import Axes3D.*")
        return matplotlib
    except ImportError:
        return None
    except Exception as e:
        warnings.warn(f"Matplotlib compatibility issue: {e}", UserWarning, stacklevel=2)
        return None


# Initialize compatibility layer
suppress_numpy_warnings()
