"""
Logging facade for business logic.

Provides clean abstraction over platform logging with fallbacks.
"""

import logging


class LoggerFacade:
    """Facade for logging with platform integration."""

    def __init__(self) -> None:
        """Initialize logger facade."""
        self._platform_logger_available = False
        self._initialize_logger()

    def _initialize_logger(self) -> None:
        """Try to initialize platform logger."""
        try:
            from dotmac_shared.core.logging import get_logger

            self._get_logger = get_logger
            self._platform_logger_available = True
        except ImportError:
            # Use standard logging as fallback
            self._get_logger = logging.getLogger

    def get_logger(self, name: str | None = None) -> logging.Logger:
        """Get logger instance with platform integration."""
        if name is None:
            name = __name__

        return self._get_logger(name)

    @property
    def platform_logger_available(self) -> bool:
        """Check if platform logger is available."""
        return self._platform_logger_available


# Global instance
_logger_facade: LoggerFacade | None = None


def get_logger_facade() -> LoggerFacade:
    """Get or create global logger facade."""
    global _logger_facade
    if _logger_facade is None:
        _logger_facade = LoggerFacade()
    return _logger_facade


def get_logger(name: str | None = None) -> logging.Logger:
    """Convenience function to get logger."""
    facade = get_logger_facade()
    return facade.get_logger(name)
