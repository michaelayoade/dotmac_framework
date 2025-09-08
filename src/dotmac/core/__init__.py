from pkgutil import extend_path

# Allow merging with packaged dotmac-core implementation
__path__ = extend_path(__path__, __name__)

# Re-export commonly used utilities if available (for compatibility)
try:  # pragma: no cover
    from .logging import get_logger  # type: ignore
except Exception:  # noqa: BLE001
    pass

try:  # pragma: no cover
    from .decorators import (  # type: ignore
        retry_on_failure,
        standard_exception_handler,
    )
except Exception:  # noqa: BLE001
    pass

__all__: list[str] = []
