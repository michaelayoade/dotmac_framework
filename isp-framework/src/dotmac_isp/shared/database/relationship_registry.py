import logging

logger = logging.getLogger(__name__)

"""Relationship registry for handling cross-module SQLAlchemy relationships.

This module provides a way to register and configure cross-module relationships
after all models have been loaded, avoiding circular import and model resolution issues.
"""

from typing import Dict, List, Callable, Any
from sqlalchemy.orm import relationship


class RelationshipRegistry:
    """Registry for deferred cross-module relationships."""
    
    def __init__(self):
        self._deferred_relationships: List[Callable] = []
        self._configured = False
    
    def register_relationship(self, model_class: type, attr_name: str, relationship_fn: Callable):
        """Register a relationship to be configured later.
        
        Args:
            model_class: The SQLAlchemy model class
            attr_name: The attribute name for the relationship
            relationship_fn: Function that returns the relationship when called
        """
        def configure_relationship():
            if not hasattr(model_class, attr_name):
                setattr(model_class, attr_name, relationship_fn())
        
        self._deferred_relationships.append(configure_relationship)
    
    def configure_all_relationships(self):
        """Configure all registered relationships."""
        if self._configured:
            return
        
        for configure_fn in self._deferred_relationships:
            try:
                configure_fn()
            except Exception as e:
logger.warning(f"Warning: Failed to configure relationship: {e}")
        
        self._configured = True
    
    def reset(self):
        """Reset the registry (mainly for testing)."""
        self._deferred_relationships.clear()
        self._configured = False


# Global registry instance
relationship_registry = RelationshipRegistry()


def register_cross_module_relationship(model_class: type, attr_name: str):
    """Decorator for registering cross-module relationships.
    
    Usage:
        @register_cross_module_relationship(WorkOrder, 'project')
        def create_work_order_project_relationship():
            return relationship(
                "InstallationProject",
                foreign_keys=[WorkOrder.project_id],
                back_populates="work_orders",
                lazy="select"
            )
    """
    def decorator(relationship_fn):
        relationship_registry.register_relationship(model_class, attr_name, relationship_fn)
        return relationship_fn
    return decorator