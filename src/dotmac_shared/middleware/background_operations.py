"""
DEPRECATED: Background Operations Middleware for DotMac Framework.

This module has been moved to the standalone dotmac.tasks package.

Migration Guide:
    Old (deprecated):
        from dotmac_shared.middleware.background_operations import BackgroundOperationsManager
    
    New:
        from dotmac.tasks import BackgroundOperationsManager

Installation:
    pip install dotmac-tasks[redis]

The new package provides:
- Enhanced idempotency with Redis persistence
- Improved saga orchestration with better error handling
- Distributed locking for concurrent execution prevention
- Comprehensive metrics and observability hooks
"""

import warnings
import logging
from typing import TYPE_CHECKING

# Issue deprecation warning on module import
warnings.warn(
    "dotmac_shared.middleware.background_operations is deprecated. "
    "Use 'dotmac.tasks' package instead. "
    "Install with: pip install dotmac-tasks[redis]",
    DeprecationWarning,
    stacklevel=2
)

logger = logging.getLogger(__name__)


# Define import mapping for lazy loading
_IMPORT_MAP = {
    'OperationStatus': 'dotmac.tasks:OperationStatus',
    'SagaStepStatus': 'dotmac.tasks:SagaStepStatus',
    'IdempotencyKey': 'dotmac.tasks:IdempotencyKey',
    'SagaStep': 'dotmac.tasks:SagaStep',
    'SagaWorkflow': 'dotmac.tasks:SagaWorkflow',
    'BackgroundOperation': 'dotmac.tasks:BackgroundOperation',
    'BackgroundOperationsManager': 'dotmac.tasks:BackgroundOperationsManager',
    'BackgroundOperationsMiddleware': 'dotmac.tasks:BackgroundOperationsMiddleware',
    'MemoryStorage': 'dotmac.tasks:MemoryStorage',
    'add_background_operations_middleware': 'dotmac.tasks:add_background_operations_middleware',
    'get_idempotency_key': 'dotmac.tasks:get_idempotency_key',
    'is_idempotent_request': 'dotmac.tasks:is_idempotent_request',
    'set_operation_result': 'dotmac.tasks:set_operation_result',
}


def _issue_deprecation_warning(name: str) -> None:
    """Issue a deprecation warning for a specific import."""
    warnings.warn(
        f"{name} has been moved to dotmac.tasks package. "
        f"Use 'from dotmac.tasks import {name}' instead.",
        DeprecationWarning,
        stacklevel=3
    )


def _lazy_import(name: str):
    """Lazy import with deprecation warnings."""
    if name not in _IMPORT_MAP:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
    
    _issue_deprecation_warning(name)
    
    module_path, class_name = _IMPORT_MAP[name].split(':')
    try:
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)
    except ImportError as e:
        raise ImportError(
            f"Failed to import {name} from {module_path}. "
            f"Make sure dotmac-tasks is installed: pip install dotmac-tasks[redis]"
        ) from e


def __getattr__(name: str):
    """Module-level __getattr__ for lazy loading."""
    return _lazy_import(name)


# Try to import everything from dotmac.tasks for backward compatibility
try:
    from dotmac.tasks import *  # noqa: F401, F403
except ImportError:
    # Create placeholder classes that raise helpful errors when dotmac.tasks is not installed
    class _MissingDependency:
        def __init__(self, name):
            self.name = name
            
        def __call__(self, *args, **kwargs):
            raise ImportError(
                f"{self.name} requires dotmac-tasks package. "
                f"Install with: pip install dotmac-tasks[redis]"
            )
        
        def __getattr__(self, attr):
            raise ImportError(
                f"{self.name}.{attr} requires dotmac-tasks package. "
                f"Install with: pip install dotmac-tasks[redis]"
            )
    
    # Create placeholder objects for all exports
    for key in _IMPORT_MAP:
        locals()[key] = _MissingDependency(key)
