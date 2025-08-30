"""
Module Scaffolding Framework - Phase 2

This package provides tools for:
1. Module template system
2. Auto-discovery mechanism
3. Validation framework
4. CLI scaffolding tools
"""

from .cli import ScaffoldingCLI
from .discovery import ModuleDiscovery, ModuleRegistry
from .templates import ComponentTemplate, ModuleTemplate
from .validation import ModuleValidator, ValidationResult

__all__ = [
    "ModuleTemplate",
    "ComponentTemplate",
    "ModuleDiscovery",
    "ModuleRegistry",
    "ModuleValidator",
    "ValidationResult",
    "ScaffoldingCLI",
]
