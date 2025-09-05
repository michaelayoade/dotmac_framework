"""
Builder Pattern for Complex Test Scenarios

Provides fluent APIs for building complex test data scenarios with:
- TestDataBuilder: Orchestrates multiple entity creation
- EntityBuilder: Builds individual entities with relationships
- RelationshipBuilder: Manages entity relationships
- ScenarioBuilder: Creates complete business scenarios
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Optional, TypeVar

from .factories import FactoryRegistry, RelationshipDefinition
from .generators import DataGenerator, DataType

logger = logging.getLogger(__name__)

T = TypeVar("T")
BuilderType = TypeVar("BuilderType", bound="BaseBuilder")


class BuilderError(Exception):
    """Base exception for builder-related errors."""

    pass


@dataclass
class BuildStep:
    """Represents a single step in the building process."""

    name: str
    factory_name: str
    attributes: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    post_build_hooks: list[Callable[[Any], None]] = field(default_factory=list)
    condition: Optional[Callable[[], bool]] = None


@dataclass
class ScenarioContext:
    """Context for scenario building with shared state."""

    entities: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    step_results: dict[str, Any] = field(default_factory=dict)


class BaseBuilder(ABC):
    """Abstract base class for all builders."""

    def __init__(
        self, registry: FactoryRegistry, generator: Optional[DataGenerator] = None
    ):
        """Initialize builder with factory registry and data generator."""
        self.registry = registry
        self.generator = generator or DataGenerator()
        self.steps: list[BuildStep] = []
        self.context = ScenarioContext()

    @abstractmethod
    def build(self) -> Any:
        """Execute the build process."""
        pass

    def _execute_steps(self) -> dict[str, Any]:
        """Execute all build steps in dependency order."""
        # Resolve dependencies
        execution_order = self._resolve_execution_order()
        results = {}

        for step_name in execution_order:
            step = next(s for s in self.steps if s.name == step_name)

            # Check condition if present
            if step.condition and not step.condition():
                logger.debug(f"Skipping step {step_name} due to condition")
                continue

            # Resolve attribute dependencies
            resolved_attrs = self._resolve_step_attributes(step)

            # Create entity using factory
            factory = self.registry.get_factory(step.factory_name)
            entity = factory.create(**resolved_attrs)

            # Store results
            results[step_name] = entity
            self.context.entities[step_name] = entity
            self.context.step_results[step_name] = entity

            # Run post-build hooks
            for hook in step.post_build_hooks:
                try:
                    hook(entity)
                except Exception as e:
                    logger.warning(f"Post-build hook failed for {step_name}: {e}")

            logger.debug(f"Built step {step_name}: {entity}")

        return results

    def _resolve_execution_order(self) -> list[str]:
        """Resolve step execution order based on dependencies."""
        # Simple topological sort
        visited = set()
        temp_visited = set()
        result = []

        def visit(step_name: str):
            if step_name in temp_visited:
                raise BuilderError(
                    f"Circular dependency detected involving {step_name}"
                )
            if step_name in visited:
                return

            temp_visited.add(step_name)

            # Find step
            step = next((s for s in self.steps if s.name == step_name), None)
            if not step:
                raise BuilderError(f"Step {step_name} not found")

            # Visit dependencies first
            for dep in step.dependencies:
                visit(dep)

            temp_visited.remove(step_name)
            visited.add(step_name)
            result.append(step_name)

        # Visit all steps
        for step in self.steps:
            if step.name not in visited:
                visit(step.name)

        return result

    def _resolve_step_attributes(self, step: BuildStep) -> dict[str, Any]:
        """Resolve step attributes including references to other entities."""
        resolved = deepcopy(step.attributes)

        for key, value in resolved.items():
            if (
                isinstance(value, str)
                and value.startswith("${")
                and value.endswith("}")
            ):
                # Reference to another entity or variable
                ref = value[2:-1]  # Remove ${ }

                if "." in ref:
                    entity_name, attr_name = ref.split(".", 1)
                    if entity_name in self.context.entities:
                        entity = self.context.entities[entity_name]
                        resolved[key] = getattr(entity, attr_name)
                    else:
                        raise BuilderError(
                            f"Entity {entity_name} not found for reference {ref}"
                        )
                else:
                    # Simple variable reference
                    if ref in self.context.variables:
                        resolved[key] = self.context.variables[ref]
                    elif ref in self.context.entities:
                        resolved[key] = self.context.entities[ref]
                    else:
                        raise BuilderError(f"Variable {ref} not found")

        return resolved


class EntityBuilder(BaseBuilder):
    """
    Builder for individual entities with fluent API.

    Provides methods to configure attributes, relationships,
    and validation rules for a single entity type.
    """

    def __init__(
        self,
        factory_name: str,
        registry: FactoryRegistry,
        generator: Optional[DataGenerator] = None,
    ):
        """Initialize entity builder for specific factory."""
        super().__init__(registry, generator)
        self.factory_name = factory_name
        self.attributes: dict[str, Any] = {}
        self.relationships: list[str] = []
        self.hooks: list[Callable[[Any], None]] = []
        self.validators: list[Callable[[Any], bool]] = []

    def with_attribute(self, name: str, value: Any) -> "EntityBuilder":
        """Set attribute value."""
        self.attributes[name] = value
        return self

    def with_generated_attribute(
        self, name: str, data_type: DataType, **kwargs
    ) -> "EntityBuilder":
        """Set attribute to generated value."""
        self.attributes[name] = self.generator.generate(data_type, **kwargs)
        return self

    def with_relationship(self, relationship_name: str) -> "EntityBuilder":
        """Add relationship."""
        self.relationships.append(relationship_name)
        return self

    def with_hook(self, hook: Callable[[Any], None]) -> "EntityBuilder":
        """Add post-build hook."""
        self.hooks.append(hook)
        return self

    def with_validator(self, validator: Callable[[Any], bool]) -> "EntityBuilder":
        """Add validation rule."""
        self.validators.append(validator)
        return self

    def build(self) -> Any:
        """Build the entity."""
        # Create entity
        factory = self.registry.get_factory(self.factory_name)
        entity = factory.create(**self.attributes)

        # Run hooks
        for hook in self.hooks:
            hook(entity)

        # Run validations
        for validator in self.validators:
            if not validator(entity):
                raise BuilderError(f"Validation failed for {self.factory_name}")

        return entity


class RelationshipBuilder(BaseBuilder):
    """
    Builder for creating entities with complex relationships.

    Handles parent-child relationships, many-to-many associations,
    and cascading entity creation.
    """

    def __init__(
        self, registry: FactoryRegistry, generator: Optional[DataGenerator] = None
    ):
        """Initialize relationship builder."""
        super().__init__(registry, generator)
        self.relationships: list[RelationshipDefinition] = []

    def one_to_one(
        self,
        source_factory: str,
        target_factory: str,
        name: str,
        foreign_key: Optional[str] = None,
    ) -> "RelationshipBuilder":
        """Define one-to-one relationship."""
        relationship = RelationshipDefinition(
            name=name,
            source_factory=source_factory,
            target_factory=target_factory,
            relationship_type="one_to_one",
            foreign_key=foreign_key,
        )
        self.relationships.append(relationship)
        return self

    def one_to_many(
        self,
        parent_factory: str,
        child_factory: str,
        name: str,
        foreign_key: str,
        children_count: int = 1,
    ) -> "RelationshipBuilder":
        """Define one-to-many relationship."""
        relationship = RelationshipDefinition(
            name=name,
            source_factory=parent_factory,
            target_factory=child_factory,
            relationship_type="one_to_many",
            foreign_key=foreign_key,
        )
        self.relationships.append(relationship)

        # Add steps for parent and children
        self.add_step(f"parent_{name}", parent_factory)
        for i in range(children_count):
            self.add_step(
                f"child_{name}_{i}",
                child_factory,
                dependencies=[f"parent_{name}"],
                attributes={foreign_key: f"${{parent_{name}.id}}"},
            )

        return self

    def many_to_many(
        self,
        left_factory: str,
        right_factory: str,
        name: str,
        left_count: int = 1,
        right_count: int = 1,
    ) -> "RelationshipBuilder":
        """Define many-to-many relationship."""
        relationship = RelationshipDefinition(
            name=name,
            source_factory=left_factory,
            target_factory=right_factory,
            relationship_type="many_to_many",
        )
        self.relationships.append(relationship)

        # Add steps for both sides
        for i in range(left_count):
            self.add_step(f"left_{name}_{i}", left_factory)
        for i in range(right_count):
            self.add_step(f"right_{name}_{i}", right_factory)

        return self

    def add_step(
        self,
        name: str,
        factory_name: str,
        attributes: Optional[dict[str, Any]] = None,
        dependencies: Optional[list[str]] = None,
        **kwargs,
    ) -> "RelationshipBuilder":
        """Add build step."""
        step = BuildStep(
            name=name,
            factory_name=factory_name,
            attributes=attributes or {},
            dependencies=dependencies or [],
            **kwargs,
        )
        self.steps.append(step)
        return self

    def build(self) -> dict[str, Any]:
        """Build all entities with relationships."""
        # Register relationships
        for relationship in self.relationships:
            self.registry.register_relationship(relationship)

        # Execute steps
        return self._execute_steps()


class ScenarioBuilder(BaseBuilder):
    """
    Builder for complete business scenarios.

    Orchestrates creation of multiple related entities to represent
    realistic business scenarios like customer onboarding, service
    provisioning, billing cycles, etc.
    """

    def __init__(
        self,
        name: str,
        registry: FactoryRegistry,
        generator: Optional[DataGenerator] = None,
    ):
        """Initialize scenario builder."""
        super().__init__(registry, generator)
        self.name = name
        self.description = ""
        self.preconditions: list[Callable[[], bool]] = []
        self.postconditions: list[Callable[[ScenarioContext], bool]] = []

    def describe(self, description: str) -> "ScenarioBuilder":
        """Set scenario description."""
        self.description = description
        return self

    def requires(self, condition: Callable[[], bool]) -> "ScenarioBuilder":
        """Add precondition."""
        self.preconditions.append(condition)
        return self

    def ensures(
        self, condition: Callable[[ScenarioContext], bool]
    ) -> "ScenarioBuilder":
        """Add postcondition."""
        self.postconditions.append(condition)
        return self

    def set_variable(self, name: str, value: Any) -> "ScenarioBuilder":
        """Set context variable."""
        self.context.variables[name] = value
        return self

    def add_step(self, name: str, factory_name: str, **kwargs) -> "ScenarioBuilder":
        """Add scenario step."""
        step = BuildStep(name=name, factory_name=factory_name, **kwargs)
        self.steps.append(step)
        return self

    def customer_onboarding_scenario(
        self, tenant_id: str, service_type: str = "basic_internet"
    ) -> "ScenarioBuilder":
        """Pre-built customer onboarding scenario."""
        return (
            self.set_variable("tenant_id", tenant_id)
            .set_variable("service_type", service_type)
            .add_step(
                "customer",
                "customer_factory",
                attributes={"tenant_id": "${tenant_id}", "status": "active"},
            )
            .add_step(
                "service",
                "service_factory",
                dependencies=["customer"],
                attributes={
                    "customer_id": "${customer.id}",
                    "service_type": "${service_type}",
                    "status": "active",
                },
            )
            .add_step(
                "billing_account",
                "billing_factory",
                dependencies=["customer"],
                attributes={"customer_id": "${customer.id}", "status": "active"},
            )
        )

    def service_provisioning_scenario(
        self, customer_id: str, equipment_count: int = 1
    ) -> "ScenarioBuilder":
        """Pre-built service provisioning scenario."""
        return (
            self.set_variable("customer_id", customer_id)
            .add_step(
                "service_order",
                "service_order_factory",
                attributes={"customer_id": "${customer_id}"},
            )
            .add_step(
                "network_device",
                "device_factory",
                dependencies=["service_order"],
                attributes={"service_order_id": "${service_order.id}"},
            )
        )

    def build(self) -> ScenarioContext:
        """Build complete scenario."""
        # Check preconditions
        for condition in self.preconditions:
            if not condition():
                raise BuilderError(f"Precondition failed for scenario {self.name}")

        # Execute steps
        results = self._execute_steps()

        # Update context
        self.context.entities.update(results)

        # Check postconditions
        for condition in self.postconditions:
            if not condition(self.context):
                raise BuilderError(f"Postcondition failed for scenario {self.name}")

        logger.info(f"Built scenario {self.name}: {len(results)} entities created")
        return self.context


class TestDataBuilder:
    """
    Main orchestrator for test data building.

    Provides high-level interface for creating test data using
    various builder patterns and strategies.
    """

    def __init__(
        self, registry: FactoryRegistry, generator: Optional[DataGenerator] = None
    ):
        """Initialize test data builder."""
        self.registry = registry
        self.generator = generator or DataGenerator()

    def entity(self, factory_name: str) -> EntityBuilder:
        """Create entity builder."""
        return EntityBuilder(factory_name, self.registry, self.generator)

    def relationship(self) -> RelationshipBuilder:
        """Create relationship builder."""
        return RelationshipBuilder(self.registry, self.generator)

    def scenario(self, name: str) -> ScenarioBuilder:
        """Create scenario builder."""
        return ScenarioBuilder(name, self.registry, self.generator)
