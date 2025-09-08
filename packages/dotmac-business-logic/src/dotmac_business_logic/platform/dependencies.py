"""
Dependencies facade for business logic.

Provides clean abstraction over platform dependency injection
with graceful fallbacks for standalone usage.
"""

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class DependenciesFallback:
    """Fallback dependency provider when platform dependencies unavailable."""

    def get_standard_deps(self) -> dict[str, Any]:
        """Provide fallback standard dependencies."""
        logger.debug("Using fallback standard dependencies")
        return {
            "current_user": None,
            "db_session": None,
            "tenant_context": None,
        }

    def get_paginated_deps(self) -> dict[str, Any]:
        """Provide fallback paginated dependencies."""
        logger.debug("Using fallback paginated dependencies")
        return {
            "skip": 0,
            "limit": 50,
            "current_user": None,
            "db_session": None,
            "tenant_context": None,
        }


class DependenciesFacade:
    """Facade for dependency injection with platform integration."""

    def __init__(self) -> None:
        """Initialize dependencies facade."""
        self._platform_available = False
        self._fallback = DependenciesFallback()
        self._initialize_platform_deps()

    def _initialize_platform_deps(self) -> None:
        """Try to initialize platform dependencies."""
        try:
            # Try platform application dependencies first
            from dotmac.application.dependencies import (
                get_paginated_deps as platform_paginated,
            )
            from dotmac.application.dependencies import (
                get_standard_deps as platform_standard,
            )

            self._get_standard_deps = platform_standard
            self._get_paginated_deps = platform_paginated
            self._platform_available = True
            logger.debug("Platform application dependencies initialized")
        except ImportError:
            try:
                # Fallback to shared dependencies if available
                from dotmac_shared.api.dependencies import (
                    get_paginated_deps as shared_paginated,
                )
                from dotmac_shared.api.dependencies import (
                    get_standard_deps as shared_standard,
                )

                self._get_standard_deps = shared_standard
                self._get_paginated_deps = shared_paginated
                self._platform_available = True
                logger.debug("Shared API dependencies initialized (fallback)")
            except ImportError:
                # Use local fallback
                self._get_standard_deps = self._fallback.get_standard_deps
                self._get_paginated_deps = self._fallback.get_paginated_deps
                logger.warning("No platform dependencies available, using fallback")

    def get_standard_deps(self) -> Callable:
        """Get standard dependencies function."""
        return self._get_standard_deps

    def get_paginated_deps(self) -> Callable:
        """Get paginated dependencies function."""
        return self._get_paginated_deps

    @property
    def platform_available(self) -> bool:
        """Check if platform dependencies are available."""
        return self._platform_available


# Global instance
_dependencies_facade: DependenciesFacade | None = None


def get_dependencies_facade() -> DependenciesFacade:
    """Get or create global dependencies facade."""
    global _dependencies_facade
    if _dependencies_facade is None:
        _dependencies_facade = DependenciesFacade()
    return _dependencies_facade
