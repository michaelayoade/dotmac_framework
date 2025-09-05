"""
Resource calculation adapter for optimal container resource allocation.
"""

import math
from typing import Optional

import structlog

from ..core.exceptions import ResourceCalculationError
from ..core.models import FeatureFlags, PlanType, ResourceRequirements

logger = structlog.get_logger(__name__)


class ResourceCalculator:
    """Calculates optimal resource allocation based on customer count and requirements."""

    # Base resource configurations by plan type
    BASE_RESOURCES = {
        PlanType.STANDARD: {
            "cpu_cores": 0.5,
            "memory_gb": 1.0,
            "storage_gb": 5.0,
            "max_connections": 25,
            "max_concurrent_requests": 15,
        },
        PlanType.PREMIUM: {
            "cpu_cores": 1.0,
            "memory_gb": 2.0,
            "storage_gb": 10.0,
            "max_connections": 50,
            "max_concurrent_requests": 30,
        },
        PlanType.ENTERPRISE: {
            "cpu_cores": 2.0,
            "memory_gb": 4.0,
            "storage_gb": 20.0,
            "max_connections": 100,
            "max_concurrent_requests": 60,
        },
    }

    # Scaling factors for customer count
    SCALING_FACTORS = {
        "cpu_per_1000_customers": 0.2,  # Additional CPU cores per 1000 customers
        "memory_per_500_customers": 0.5,  # Additional GB RAM per 500 customers
        "storage_per_1000_customers": 2.0,  # Additional GB storage per 1000 customers
        "connections_per_customer": 0.05,  # Database connections per customer
        "requests_per_100_customers": 2,  # Concurrent requests per 100 customers
    }

    # Feature-specific resource multipliers
    FEATURE_MULTIPLIERS = {
        "analytics_dashboard": {"cpu": 1.3, "memory": 1.5, "storage": 1.2},
        "api_webhooks": {"cpu": 1.1, "memory": 1.2, "storage": 1.0},
        "bulk_operations": {"cpu": 1.4, "memory": 1.3, "storage": 1.1},
        "advanced_reporting": {"cpu": 1.2, "memory": 1.4, "storage": 1.3},
        "multi_language": {"cpu": 1.1, "memory": 1.1, "storage": 1.2},
    }

    # Absolute limits
    LIMITS = {
        "max_cpu_cores": 16.0,
        "max_memory_gb": 64.0,
        "max_storage_gb": 500.0,
        "max_connections": 2000,
        "max_concurrent_requests": 1000,
    }

    async def calculate_optimal_resources(
        self,
        customer_count: int,
        plan_type: PlanType = PlanType.STANDARD,
        feature_flags: Optional[FeatureFlags] = None,
    ) -> ResourceRequirements:
        """
        Calculate optimal resource allocation based on requirements.

        Args:
            customer_count: Expected number of customers
            plan_type: Service plan type
            feature_flags: Enabled features

        Returns:
            ResourceRequirements with optimal allocation

        Raises:
            ResourceCalculationError: If calculation fails or exceeds limits
        """

        try:
            logger.info(
                "Calculating optimal resources",
                customer_count=customer_count,
                plan_type=plan_type.value,
            )

            # Start with base resources for plan type
            base_resources = self.BASE_RESOURCES.get(plan_type, self.BASE_RESOURCES[PlanType.STANDARD])

            # Calculate base requirements
            cpu_cores = base_resources["cpu_cores"]
            memory_gb = base_resources["memory_gb"]
            storage_gb = base_resources["storage_gb"]
            max_connections = base_resources["max_connections"]
            max_concurrent_requests = base_resources["max_concurrent_requests"]

            # Apply customer count scaling
            cpu_cores += (customer_count / 1000) * self.SCALING_FACTORS["cpu_per_1000_customers"]
            memory_gb += (customer_count / 500) * self.SCALING_FACTORS["memory_per_500_customers"]
            storage_gb += (customer_count / 1000) * self.SCALING_FACTORS["storage_per_1000_customers"]
            max_connections += int(customer_count * self.SCALING_FACTORS["connections_per_customer"])
            max_concurrent_requests += int(customer_count / 100) * self.SCALING_FACTORS["requests_per_100_customers"]

            # Apply feature multipliers
            if feature_flags:
                feature_multiplier = self._calculate_feature_multipliers(feature_flags)
                cpu_cores *= feature_multiplier["cpu"]
                memory_gb *= feature_multiplier["memory"]
                storage_gb *= feature_multiplier["storage"]

            # Round to valid increments
            cpu_cores = self._round_cpu(cpu_cores)
            memory_gb = self._round_memory(memory_gb)
            storage_gb = self._round_storage(storage_gb)

            # Apply limits
            cpu_cores = min(cpu_cores, self.LIMITS["max_cpu_cores"])
            memory_gb = min(memory_gb, self.LIMITS["max_memory_gb"])
            storage_gb = min(storage_gb, self.LIMITS["max_storage_gb"])
            max_connections = min(max_connections, self.LIMITS["max_connections"])
            max_concurrent_requests = min(max_concurrent_requests, self.LIMITS["max_concurrent_requests"])

            # Create resource requirements
            resources = ResourceRequirements(
                cpu_cores=cpu_cores,
                memory_gb=memory_gb,
                storage_gb=storage_gb,
                max_connections=max_connections,
                max_concurrent_requests=max_concurrent_requests,
            )

            logger.info(
                "Resource calculation completed",
                cpu_cores=cpu_cores,
                memory_gb=memory_gb,
                storage_gb=storage_gb,
                max_connections=max_connections,
            )

            return resources

        except Exception as e:
            raise ResourceCalculationError(
                f"Failed to calculate optimal resources: {e}",
                customer_count=customer_count,
                requested_resources={"plan_type": plan_type.value},
            ) from e

    def _calculate_feature_multipliers(self, feature_flags: FeatureFlags) -> dict[str, float]:
        """Calculate resource multipliers based on enabled features."""

        multipliers = {"cpu": 1.0, "memory": 1.0, "storage": 1.0}

        # Check each feature and apply multipliers
        if feature_flags.analytics_dashboard:
            self._apply_multiplier(multipliers, self.FEATURE_MULTIPLIERS["analytics_dashboard"])

        if feature_flags.api_webhooks:
            self._apply_multiplier(multipliers, self.FEATURE_MULTIPLIERS["api_webhooks"])

        if feature_flags.bulk_operations:
            self._apply_multiplier(multipliers, self.FEATURE_MULTIPLIERS["bulk_operations"])

        if feature_flags.advanced_reporting:
            self._apply_multiplier(multipliers, self.FEATURE_MULTIPLIERS["advanced_reporting"])

        if feature_flags.multi_language:
            self._apply_multiplier(multipliers, self.FEATURE_MULTIPLIERS["multi_language"])

        logger.debug(
            "Feature multipliers calculated",
            cpu=multipliers["cpu"],
            memory=multipliers["memory"],
            storage=multipliers["storage"],
        )

        return multipliers

    def _apply_multiplier(self, base_multipliers: dict[str, float], feature_multipliers: dict[str, float]) -> None:
        """Apply feature multipliers to base multipliers."""
        base_multipliers["cpu"] *= feature_multipliers["cpu"]
        base_multipliers["memory"] *= feature_multipliers["memory"]
        base_multipliers["storage"] *= feature_multipliers["storage"]

    def _round_cpu(self, cpu_cores: float) -> float:
        """Round CPU cores to valid increments (0.1 core increments)."""
        return round(cpu_cores * 10) / 10

    def _round_memory(self, memory_gb: float) -> float:
        """Round memory to valid increments (0.5 GB increments)."""
        return math.ceil(memory_gb * 2) / 2

    def _round_storage(self, storage_gb: float) -> float:
        """Round storage to valid increments (1 GB increments)."""
        return math.ceil(storage_gb)

    async def estimate_cost(
        self,
        resources: ResourceRequirements,
        region: str = "us-east-1",
        hours_per_month: int = 730,
    ) -> dict[str, float]:
        """
        Estimate monthly cost for resource allocation.

        Args:
            resources: Resource requirements to cost
            region: Deployment region
            hours_per_month: Hours per month (default: 730)

        Returns:
            Dictionary with cost breakdown
        """

        # Simplified cost model (would integrate with actual pricing APIs)
        HOURLY_RATES = {
            "cpu_per_core": 0.048,  # $0.048/hour per CPU core
            "memory_per_gb": 0.012,  # $0.012/hour per GB RAM
            "storage_per_gb": 0.002,  # $0.002/hour per GB storage
        }

        cpu_cost = resources.cpu_cores * HOURLY_RATES["cpu_per_core"] * hours_per_month
        memory_cost = resources.memory_gb * HOURLY_RATES["memory_per_gb"] * hours_per_month
        storage_cost = resources.storage_gb * HOURLY_RATES["storage_per_gb"] * hours_per_month

        total_cost = cpu_cost + memory_cost + storage_cost

        return {
            "cpu_cost": round(cpu_cost, 2),
            "memory_cost": round(memory_cost, 2),
            "storage_cost": round(storage_cost, 2),
            "total_monthly_cost": round(total_cost, 2),
            "currency": "USD",
            "region": region,
        }

    async def recommend_plan_type(self, customer_count: int, required_features: Optional[list] = None) -> PlanType:
        """
        Recommend optimal plan type based on requirements.

        Args:
            customer_count: Number of customers
            required_features: List of required feature names

        Returns:
            Recommended plan type
        """

        # Basic recommendation logic
        if customer_count <= 100:
            recommended = PlanType.STANDARD
        elif customer_count <= 1000:
            recommended = PlanType.PREMIUM
        else:
            recommended = PlanType.ENTERPRISE

        # Check if required features necessitate higher plan
        if required_features:
            enterprise_features = {"bulk_operations", "api_webhooks", "multi_language"}
            premium_features = {"analytics_dashboard", "advanced_reporting"}

            if any(feature in enterprise_features for feature in required_features):
                recommended = PlanType.ENTERPRISE
            elif any(feature in premium_features for feature in required_features):
                if recommended == PlanType.STANDARD:
                    recommended = PlanType.PREMIUM

        logger.info(
            "Plan type recommended",
            customer_count=customer_count,
            required_features=required_features,
            recommended_plan=recommended.value,
        )

        return recommended

    async def validate_resource_limits(self, resources: ResourceRequirements) -> bool:
        """
        Validate that resource requirements are within acceptable limits.

        Args:
            resources: Resource requirements to validate

        Returns:
            True if valid, False otherwise

        Raises:
            ResourceCalculationError: If resources exceed hard limits
        """

        errors = []

        if resources.cpu_cores > self.LIMITS["max_cpu_cores"]:
            errors.append(f"CPU cores ({resources.cpu_cores}) exceed maximum ({self.LIMITS['max_cpu_cores']})")

        if resources.memory_gb > self.LIMITS["max_memory_gb"]:
            errors.append(f"Memory ({resources.memory_gb}GB) exceeds maximum ({self.LIMITS['max_memory_gb']}GB)")

        if resources.storage_gb > self.LIMITS["max_storage_gb"]:
            errors.append(f"Storage ({resources.storage_gb}GB) exceeds maximum ({self.LIMITS['max_storage_gb']}GB)")

        if resources.max_connections > self.LIMITS["max_connections"]:
            errors.append(
                f"Max connections ({resources.max_connections}) exceed maximum ({self.LIMITS['max_connections']})"
            )

        if errors:
            raise ResourceCalculationError(
                f"Resource limits exceeded: {'; '.join(errors)}",
                requested_resources=resources.model_dump(),
            )

        return True
