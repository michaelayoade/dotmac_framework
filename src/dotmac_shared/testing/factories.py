"""
Core Factory System for Test Data Generation

Implements the Factory pattern for creating consistent test data with relationship
management and multi-tenant isolation support.

Key Features:
- Abstract BaseFactory with standard lifecycle methods
- FactoryRegistry for centralized factory management
- RelationshipManager for complex entity dependencies
- TenantIsolatedFactory for multi-tenant test scenarios
- Automatic cleanup and dependency resolution
"""
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Optional, TypeVar
from uuid import uuid4

from dotmac_shared.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

T = TypeVar("T")
FactoryType = TypeVar("FactoryType", bound="BaseFactory")


class FactoryError(Exception):
    """Base exception for factory-related errors."""

    pass


class DependencyError(FactoryError):
    """Exception raised when factory dependencies cannot be resolved."""

    pass


class RelationshipError(FactoryError):
    """Exception raised when entity relationships cannot be established."""

    pass


@dataclass
class FactoryMetadata:
    """Metadata for factory registration and management."""

    name: str
    entity_type: type
    dependencies: set[str] = field(default_factory=set)
    provides: set[str] = field(default_factory=set)
    tenant_isolated: bool = False
    cleanup_order: int = 100  # Lower numbers cleaned up first


@dataclass
class RelationshipDefinition:
    """Defines a relationship between entities."""

    name: str
    source_factory: str
    target_factory: str
    relationship_type: str  # one_to_one, one_to_many, many_to_many
    foreign_key: Optional[str] = None
    back_reference: Optional[str] = None
    cascade_delete: bool = True
    required: bool = True


class BaseFactory(ABC):
    """
    Abstract base factory for creating test entities.

    Provides standard lifecycle methods and relationship management
    for consistent test data generation.
    """

    def __init__(self, registry: Optional["FactoryRegistry"] = None):
        """Initialize factory with optional registry."""
        self.registry = registry
        self._instances: list[Any] = []
        self._relationships: dict[str, Any] = {}
        self._metadata = self._create_metadata()
        self._cleanup_handlers: list[Callable[[], None]] = []

    @abstractmethod
    def _create_metadata(self) -> FactoryMetadata:
        """Create factory metadata for registration."""
        pass

    @abstractmethod
    def _create_instance(self, **kwargs) -> T:
        """Create a single instance of the entity."""
        pass

    @abstractmethod
    def _persist_instance(self, instance: T) -> T:
        """Persist instance to storage (database, etc.)."""
        pass

    def create(self, **kwargs) -> T:
        """
        Create and persist a new instance with the given attributes.

        Args:
            **kwargs: Attributes to override defaults

        Returns:
            Created and persisted instance
        """
        # Resolve dependencies first
        resolved_kwargs = self._resolve_dependencies(kwargs)

        # Create instance
        instance = self._create_instance(**resolved_kwargs)

        # Persist instance
        persisted_instance = self._persist_instance(instance)

        # Track for cleanup
        self._instances.append(persisted_instance)

        # Establish relationships
        self._establish_relationships(persisted_instance, resolved_kwargs)

        logger.debug(f"Created {self._metadata.name} instance: {persisted_instance}")
        return persisted_instance

    def create_batch(self, count: int, **kwargs) -> list[T]:
        """
        Create multiple instances with the same base attributes.

        Args:
            count: Number of instances to create
            **kwargs: Base attributes for all instances

        Returns:
            List of created instances
        """
        instances: list[T] = []
        for i in range(count):
            # Add sequence number to avoid collisions
            instance_kwargs = deepcopy(kwargs)
            instance_kwargs.setdefault("sequence", i)
            instances.append(self.create(**instance_kwargs))
        return instances

    def build(self, **kwargs) -> T:
        """
        Build instance without persisting (for testing object creation).

        Args:
            **kwargs: Attributes to override defaults

        Returns:
            Built but not persisted instance
        """
        resolved_kwargs = self._resolve_dependencies(kwargs)
        return self._create_instance(**resolved_kwargs)

    def cleanup(self) -> None:
        """Clean up all created instances."""
        try:
            for handler in reversed(self._cleanup_handlers):
                try:
                    handler()
                except Exception as e:
                    logger.warning(f"Cleanup handler failed: {e}")

            # Clean up instances
            for instance in reversed(self._instances):
                try:
                    self._cleanup_instance(instance)
                except Exception as e:
                    logger.warning(f"Failed to cleanup instance {instance}: {e}")

            self._instances.clear()
            self._relationships.clear()
            self._cleanup_handlers.clear()
        except Exception as e:
            logger.error(f"Factory cleanup failed: {e}")
            raise

    def add_cleanup_handler(self, handler: Callable[[], None]) -> None:
        """Add custom cleanup handler."""
        self._cleanup_handlers.append(handler)

    def _resolve_dependencies(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Resolve factory dependencies for relationships."""
        if not self.registry:
            return kwargs

        resolved = dict(kwargs)

        for dep_name in self._metadata.dependencies:
            if dep_name not in resolved:
                try:
                    dep_factory = self.registry.get_factory(dep_name)
                    dep_instance = dep_factory.create()
                    resolved[dep_name] = dep_instance
                except Exception as e:
                    if hasattr(self, "_required_dependencies") and dep_name in getattr(
                        self, "_required_dependencies", set()
                    ):
                        raise DependencyError(
                            f"Failed to resolve required dependency {dep_name}: {e}"
                        ) from e
                    logger.debug(f"Optional dependency {dep_name} not resolved: {e}")

        return resolved

    def _establish_relationships(self, instance: T, kwargs: dict[str, Any]) -> None:
        """Establish relationships for the created instance."""
        if not self.registry:
            return

        # This is a hook for subclasses to implement relationship logic
        pass

    def _cleanup_instance(self, instance: T) -> None:
        """Clean up a specific instance. Override in subclasses."""
        # Default implementation - subclasses should override
        # for database deletion, etc.
        pass

    @property
    def metadata(self) -> FactoryMetadata:
        """Get factory metadata."""
        return self._metadata

    @property
    def instances(self) -> list[T]:
        """Get all created instances."""
        return self._instances.copy()


class TenantIsolatedFactory(BaseFactory):
    """
    Base factory that provides tenant isolation for multi-tenant tests.

    Automatically handles tenant context and ensures data isolation
    between different tenant test scenarios.
    """

    def __init__(
        self,
        registry: Optional["FactoryRegistry"] = None,
        tenant_id: Optional[str] = None,
    ):
        """Initialize with tenant context."""
        super().__init__(registry)
        self.tenant_id = tenant_id or str(uuid4())

    def create(self, **kwargs) -> T:
        """Create instance with tenant context."""
        # Automatically add tenant_id to all created instances
        kwargs.setdefault("tenant_id", self.tenant_id)
        return super().create(**kwargs)

    def _create_tenant_context(self) -> dict[str, Any]:
        """Create tenant context for instance creation."""
        return {
            "tenant_id": self.tenant_id,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }


class RelationshipManager:
    """
    Manages complex relationships between factory-created entities.

    Handles dependency resolution, relationship establishment,
    and cleanup coordination across multiple factories.
    """

    def __init__(self):
        """Initialize relationship manager."""
        self.relationships: dict[str, RelationshipDefinition] = {}
        self.dependency_graph: dict[str, set[str]] = defaultdict(set)
        self._relationship_cache: dict[str, Any] = {}

    def register_relationship(self, definition: RelationshipDefinition) -> None:
        """Register a relationship definition."""
        self.relationships[definition.name] = definition

        # Update dependency graph
        self.dependency_graph[definition.source_factory].add(definition.target_factory)

        logger.debug(f"Registered relationship: {definition.name}")

    def resolve_dependencies(self, factory_name: str) -> list[str]:
        """Get dependency order for a factory."""
        visited = set()
        result = []

        def visit(name: str):
            if name in visited:
                return
            visited.add(name)

            for dependency in self.dependency_graph[name]:
                visit(dependency)
            result.append(name)

        visit(factory_name)
        return result[:-1]  # Exclude the factory itself

    def establish_relationship(
        self, relationship_name: str, source_instance: Any, target_instance: Any
    ) -> None:
        """Establish a specific relationship between instances."""
        if relationship_name not in self.relationships:
            raise RelationshipError(f"Unknown relationship: {relationship_name}")

        definition = self.relationships[relationship_name]
        try:
            if definition.relationship_type == "one_to_one":
                self._establish_one_to_one(definition, source_instance, target_instance)
            elif definition.relationship_type == "one_to_many":
                self._establish_one_to_many(
                    definition, source_instance, target_instance
                )
            elif definition.relationship_type == "many_to_many":
                self._establish_many_to_many(
                    definition, source_instance, target_instance
                )
            else:
                raise RelationshipError(
                    f"Unknown relationship type: {definition.relationship_type}"
                )

            # Cache for cleanup
            cache_key = (
                f"{relationship_name}_{id(source_instance)}_{id(target_instance)}"
            )
            self._relationship_cache[cache_key] = (
                definition,
                source_instance,
                target_instance,
            )
        except Exception as e:
            raise RelationshipError(
                f"Failed to establish relationship {relationship_name}: {e}"
            ) from e

    def _establish_one_to_one(
        self, definition: RelationshipDefinition, source: Any, target: Any
    ) -> None:
        """Establish one-to-one relationship."""
        if definition.foreign_key:
            setattr(source, definition.foreign_key, target.id)
        if definition.back_reference:
            setattr(target, definition.back_reference, source)

    def _establish_one_to_many(
        self, definition: RelationshipDefinition, source: Any, target: Any
    ) -> None:
        """Establish one-to-many relationship."""
        if definition.foreign_key:
            setattr(target, definition.foreign_key, source.id)
        if definition.back_reference:
            if not hasattr(source, definition.back_reference):
                setattr(source, definition.back_reference, [])
            getattr(source, definition.back_reference).append(target)

    def _establish_many_to_many(
        self, definition: RelationshipDefinition, source: Any, target: Any
    ) -> None:
        """Establish many-to-many relationship."""
        # This would typically involve a join table - implementation depends on ORM
        if definition.back_reference:
            if not hasattr(source, definition.back_reference):
                setattr(source, definition.back_reference, [])
            if not hasattr(target, definition.back_reference):
                setattr(target, definition.back_reference, [])
            getattr(source, definition.back_reference).append(target)
            getattr(target, definition.back_reference).append(source)


class FactoryRegistry:
    """
    Centralized registry for managing factories and their dependencies.

    Provides factory registration, dependency resolution, and coordinated
    cleanup across all registered factories.
    """

    def __init__(self):
        """Initialize factory registry."""
        self.factories: dict[str, BaseFactory] = {}
        self.metadata: dict[str, FactoryMetadata] = {}
        self.relationship_manager = RelationshipManager()
        self._cleanup_order: list[str] = []

    def register_factory(self, factory: BaseFactory) -> None:
        """Register a factory in the registry."""
        metadata = factory.metadata

        if metadata.name in self.factories:
            logger.warning(f"Factory {metadata.name} already registered, replacing")

        self.factories[metadata.name] = factory
        self.metadata[metadata.name] = metadata
        factory.registry = self  # Set back-reference

        # Update cleanup order
        self._update_cleanup_order()

        logger.debug(f"Registered factory: {metadata.name}")

    def get_factory(self, name: str) -> BaseFactory:
        """Get a factory by name."""
        if name not in self.factories:
            raise FactoryError(f"Factory {name} not registered")
        return self.factories[name]

    def create_instance(self, factory_name: str, **kwargs) -> Any:
        """Create instance using named factory."""
        factory = self.get_factory(factory_name)
        return factory.create(**kwargs)

    def cleanup_all(self) -> None:
        """Clean up all factories in proper dependency order."""
        for factory_name in self._cleanup_order:
            try:
                factory = self.factories[factory_name]
                factory.cleanup()
                logger.debug(f"Cleaned up factory: {factory_name}")
            except Exception as e:
                logger.error(f"Failed to cleanup factory {factory_name}: {e}")

    def register_relationship(self, definition: RelationshipDefinition) -> None:
        """Register a relationship definition."""
        self.relationship_manager.register_relationship(definition)

    def _update_cleanup_order(self) -> None:
        """Update cleanup order based on dependencies and cleanup priorities."""
        # Sort by cleanup order (lower numbers first)
        self._cleanup_order = sorted(
            self.metadata.keys(), key=lambda name: self.metadata[name].cleanup_order
        )

    @contextmanager
    def factory_session(self):
        """Context manager for automatic factory cleanup."""
        try:
            yield self
        finally:
            self.cleanup_all()


# Global registry instance
_global_registry = FactoryRegistry()


def register_factory(factory: BaseFactory) -> None:
    """Register factory in global registry."""
    _global_registry.register_factory(factory)


def get_factory(name: str) -> BaseFactory:
    """Get factory from global registry."""
    return _global_registry.get_factory(name)


def create_factory(factory_type: str, **kwargs) -> Any:
    """Create instance using global registry."""
    return _global_registry.create_instance(factory_type, **kwargs)


def cleanup_all_factories() -> None:
    """Clean up all global factories."""
    _global_registry.cleanup_all()
