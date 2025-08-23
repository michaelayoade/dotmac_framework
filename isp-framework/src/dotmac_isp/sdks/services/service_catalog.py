"""
Service Catalog SDK - definitions/plans/add-ons/bundles
"""

from datetime import datetime
from dotmac_isp.sdks.core.datetime_utils import utc_now, utc_now_iso
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import (
    AddOnError,
    BundleError,
    ServiceDefinitionError,
    ServicePlanError,
)


class ServiceCatalogService:
    """In-memory service for service catalog operations."""

    def __init__(self):
        self._service_definitions: Dict[str, Dict[str, Any]] = {}
        self._service_plans: Dict[str, Dict[str, Any]] = {}
        self._bundles: Dict[str, Dict[str, Any]] = {}
        self._addons: Dict[str, Dict[str, Any]] = {}
        self._categories: Dict[str, Dict[str, Any]] = {}

    async def create_service_definition(self, **kwargs) -> Dict[str, Any]:
        """Create service definition."""
        definition_id = kwargs.get("definition_id") or str(uuid4())

        definition = {
            "definition_id": definition_id,
            "name": kwargs["name"],
            "description": kwargs.get("description", ""),
            "category_id": kwargs.get("category_id"),
            "service_type": kwargs["service_type"],  # data, voice, video, bundle
            "technical_specs": kwargs.get("technical_specs", {}),
            "provisioning_requirements": kwargs.get("provisioning_requirements", []),
            "dependencies": kwargs.get("dependencies", []),
            "compatibility_rules": kwargs.get("compatibility_rules", {}),
            "metadata": kwargs.get("metadata", {}),
            "status": kwargs.get("status", "draft"),  # draft, published, deprecated
            "version": kwargs.get("version", "1.0.0"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
            "created_by": kwargs.get("created_by"),
        }

        # Validate service definition
        self._validate_service_definition(definition)

        self._service_definitions[definition_id] = definition
        return definition

    def _validate_service_definition(self, definition: Dict[str, Any]):
        """Validate service definition."""
        if not definition.get("name"):
            raise ServiceDefinitionError("Service name is required")

        if not definition.get("service_type"):
            raise ServiceDefinitionError("Service type is required")

        valid_types = ["data", "voice", "video", "bundle", "addon"]
        if definition["service_type"] not in valid_types:
            raise ServiceDefinitionError(
                f"Invalid service type. Must be one of: {valid_types}"
            )

        # Validate dependencies exist
        for dep_id in definition.get("dependencies", []):
            if dep_id not in self._service_definitions:
                raise ServiceDefinitionError(f"Dependency service not found: {dep_id}")

    async def create_service_plan(self, **kwargs) -> Dict[str, Any]:
        """Create service plan."""
        plan_id = kwargs.get("plan_id") or str(uuid4())

        plan = {
            "plan_id": plan_id,
            "definition_id": kwargs["definition_id"],
            "name": kwargs["name"],
            "description": kwargs.get("description", ""),
            "plan_type": kwargs.get(
                "plan_type", "standard"
            ),  # standard, premium, enterprise
            "billing_cycle": kwargs.get(
                "billing_cycle", "monthly"
            ),  # monthly, yearly, one-time
            "base_price": Decimal(str(kwargs.get("base_price", "0.00"))),
            "currency": kwargs.get("currency", "USD"),
            "setup_fee": Decimal(str(kwargs.get("setup_fee", "0.00"))),
            "termination_fee": Decimal(str(kwargs.get("termination_fee", "0.00"))),
            "minimum_term_months": kwargs.get("minimum_term_months", 1),
            "auto_renew": kwargs.get("auto_renew", True),
            "features": kwargs.get("features", {}),
            "limits": kwargs.get("limits", {}),
            "sla_terms": kwargs.get("sla_terms", {}),
            "eligibility_rules": kwargs.get("eligibility_rules", {}),
            "promotional_pricing": kwargs.get("promotional_pricing", []),
            "status": kwargs.get("status", "active"),  # active, inactive, deprecated
            "effective_date": kwargs.get("effective_date", utc_now().isoformat()),
            "expiry_date": kwargs.get("expiry_date"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        # Validate service plan
        self._validate_service_plan(plan)

        self._service_plans[plan_id] = plan
        return plan

    def _validate_service_plan(self, plan: Dict[str, Any]):
        """Validate service plan."""
        if not plan.get("definition_id"):
            raise ServicePlanError("Service definition ID is required")

        if plan["definition_id"] not in self._service_definitions:
            raise ServicePlanError(
                f"Service definition not found: {plan['definition_id']}"
            )

        if not plan.get("name"):
            raise ServicePlanError("Plan name is required")

        if plan["base_price"] < 0:
            raise ServicePlanError("Base price cannot be negative")

        valid_cycles = ["monthly", "yearly", "one-time", "usage-based"]
        if plan["billing_cycle"] not in valid_cycles:
            raise ServicePlanError(
                f"Invalid billing cycle. Must be one of: {valid_cycles}"
            )

    async def create_bundle(self, **kwargs) -> Dict[str, Any]:
        """Create service bundle."""
        bundle_id = kwargs.get("bundle_id") or str(uuid4())

        bundle = {
            "bundle_id": bundle_id,
            "name": kwargs["name"],
            "description": kwargs.get("description", ""),
            "bundle_type": kwargs.get(
                "bundle_type", "fixed"
            ),  # fixed, flexible, custom
            "included_services": kwargs.get("included_services", []),
            "optional_services": kwargs.get("optional_services", []),
            "bundle_price": Decimal(str(kwargs.get("bundle_price", "0.00"))),
            "discount_type": kwargs.get(
                "discount_type", "percentage"
            ),  # percentage, fixed
            "discount_value": Decimal(str(kwargs.get("discount_value", "0.00"))),
            "currency": kwargs.get("currency", "USD"),
            "minimum_services": kwargs.get("minimum_services", 1),
            "maximum_services": kwargs.get("maximum_services"),
            "compatibility_matrix": kwargs.get("compatibility_matrix", {}),
            "bundle_rules": kwargs.get("bundle_rules", {}),
            "promotional_terms": kwargs.get("promotional_terms", {}),
            "status": kwargs.get("status", "active"),
            "effective_date": kwargs.get("effective_date", utc_now().isoformat()),
            "expiry_date": kwargs.get("expiry_date"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        # Validate bundle
        self._validate_bundle(bundle)

        self._bundles[bundle_id] = bundle
        return bundle

    def _validate_bundle(self, bundle: Dict[str, Any]):
        """Validate service bundle."""
        if not bundle.get("name"):
            raise BundleError("Bundle name is required")

        # Validate included services exist
        for service_plan_id in bundle.get("included_services", []):
            if service_plan_id not in self._service_plans:
                raise BundleError(f"Included service plan not found: {service_plan_id}")

        # Validate optional services exist
        for service_plan_id in bundle.get("optional_services", []):
            if service_plan_id not in self._service_plans:
                raise BundleError(f"Optional service plan not found: {service_plan_id}")

        if bundle["minimum_services"] < 1:
            raise BundleError("Minimum services must be at least 1")

        if (
            bundle.get("maximum_services")
            and bundle["maximum_services"] < bundle["minimum_services"]
        ):
            raise BundleError("Maximum services cannot be less than minimum services")

    async def create_addon(self, **kwargs) -> Dict[str, Any]:
        """Create service add-on."""
        addon_id = kwargs.get("addon_id") or str(uuid4())

        addon = {
            "addon_id": addon_id,
            "name": kwargs["name"],
            "description": kwargs.get("description", ""),
            "addon_type": kwargs.get(
                "addon_type", "feature"
            ),  # feature, capacity, support
            "compatible_services": kwargs.get("compatible_services", []),
            "compatible_plans": kwargs.get("compatible_plans", []),
            "price": Decimal(str(kwargs.get("price", "0.00"))),
            "billing_cycle": kwargs.get("billing_cycle", "monthly"),
            "currency": kwargs.get("currency", "USD"),
            "setup_fee": Decimal(str(kwargs.get("setup_fee", "0.00"))),
            "features": kwargs.get("features", {}),
            "limits": kwargs.get("limits", {}),
            "dependencies": kwargs.get("dependencies", []),
            "exclusions": kwargs.get("exclusions", []),
            "auto_provision": kwargs.get("auto_provision", False),
            "status": kwargs.get("status", "active"),
            "effective_date": kwargs.get("effective_date", utc_now().isoformat()),
            "expiry_date": kwargs.get("expiry_date"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        # Validate add-on
        self._validate_addon(addon)

        self._addons[addon_id] = addon
        return addon

    def _validate_addon(self, addon: Dict[str, Any]):
        """Validate service add-on."""
        if not addon.get("name"):
            raise AddOnError("Add-on name is required")

        # Validate compatible services exist
        for service_id in addon.get("compatible_services", []):
            if service_id not in self._service_definitions:
                raise AddOnError(f"Compatible service not found: {service_id}")

        # Validate compatible plans exist
        for plan_id in addon.get("compatible_plans", []):
            if plan_id not in self._service_plans:
                raise AddOnError(f"Compatible plan not found: {plan_id}")

        if addon["price"] < 0:
            raise AddOnError("Add-on price cannot be negative")

    async def calculate_bundle_price(
        self, bundle_id: str, selected_services: List[str]
    ) -> Dict[str, Any]:
        """Calculate bundle pricing."""
        if bundle_id not in self._bundles:
            raise BundleError(f"Bundle not found: {bundle_id}")

        bundle = self._bundles[bundle_id]

        # Calculate individual service prices
        individual_total = Decimal("0.00")
        service_prices = []

        for service_plan_id in selected_services:
            if service_plan_id not in self._service_plans:
                raise BundleError(f"Service plan not found: {service_plan_id}")

            plan = self._service_plans[service_plan_id]
            individual_total += plan["base_price"]
            service_prices.append(
                {
                    "plan_id": service_plan_id,
                    "plan_name": plan["name"],
                    "price": float(plan["base_price"]),
                }
            )

        # Apply bundle pricing
        bundle_price = bundle["bundle_price"]
        if bundle_price > 0:
            # Fixed bundle price
            final_price = bundle_price
            discount_amount = individual_total - bundle_price
        else:
            # Apply discount to individual total
            if bundle["discount_type"] == "percentage":
                discount_amount = individual_total * (bundle["discount_value"] / 100)
            else:
                discount_amount = bundle["discount_value"]

            final_price = individual_total - discount_amount

        return {
            "bundle_id": bundle_id,
            "bundle_name": bundle["name"],
            "selected_services": service_prices,
            "individual_total": float(individual_total),
            "discount_amount": float(discount_amount),
            "final_price": float(final_price),
            "currency": bundle["currency"],
            "discount_percentage": (
                float((discount_amount / individual_total) * 100)
                if individual_total > 0
                else 0
            ),
        }


class ServiceCatalogSDK:
    """Minimal, reusable SDK for service catalog management."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = ServiceCatalogService()

    async def create_service_definition(
        self,
        name: str,
        service_type: str,
        description: Optional[str] = None,
        category_id: Optional[str] = None,
        technical_specs: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create service definition."""
        definition = await self._service.create_service_definition(
            name=name,
            service_type=service_type,
            description=description,
            category_id=category_id,
            technical_specs=technical_specs or {},
            tenant_id=self.tenant_id,
            **kwargs,
        )

        return {
            "definition_id": definition["definition_id"],
            "name": definition["name"],
            "description": definition["description"],
            "service_type": definition["service_type"],
            "category_id": definition["category_id"],
            "technical_specs": definition["technical_specs"],
            "status": definition["status"],
            "version": definition["version"],
            "created_at": definition["created_at"],
        }

    async def create_service_plan(
        self,
        definition_id: str,
        name: str,
        base_price: float,
        billing_cycle: str = "monthly",
        currency: str = "USD",
        **kwargs,
    ) -> Dict[str, Any]:
        """Create service plan."""
        plan = await self._service.create_service_plan(
            definition_id=definition_id,
            name=name,
            base_price=base_price,
            billing_cycle=billing_cycle,
            currency=currency,
            **kwargs,
        )

        return {
            "plan_id": plan["plan_id"],
            "definition_id": plan["definition_id"],
            "name": plan["name"],
            "description": plan["description"],
            "plan_type": plan["plan_type"],
            "billing_cycle": plan["billing_cycle"],
            "base_price": float(plan["base_price"]),
            "currency": plan["currency"],
            "setup_fee": float(plan["setup_fee"]),
            "minimum_term_months": plan["minimum_term_months"],
            "features": plan["features"],
            "limits": plan["limits"],
            "status": plan["status"],
            "created_at": plan["created_at"],
        }

    async def create_bundle(
        self,
        name: str,
        included_services: List[str],
        bundle_price: Optional[float] = None,
        discount_value: float = 0.0,
        discount_type: str = "percentage",
        **kwargs,
    ) -> Dict[str, Any]:
        """Create service bundle."""
        bundle = await self._service.create_bundle(
            name=name,
            included_services=included_services,
            bundle_price=bundle_price,
            discount_value=discount_value,
            discount_type=discount_type,
            **kwargs,
        )

        return {
            "bundle_id": bundle["bundle_id"],
            "name": bundle["name"],
            "description": bundle["description"],
            "bundle_type": bundle["bundle_type"],
            "included_services": bundle["included_services"],
            "optional_services": bundle["optional_services"],
            "bundle_price": float(bundle["bundle_price"]),
            "discount_type": bundle["discount_type"],
            "discount_value": float(bundle["discount_value"]),
            "currency": bundle["currency"],
            "status": bundle["status"],
            "created_at": bundle["created_at"],
        }

    async def create_addon(
        self,
        name: str,
        addon_type: str,
        price: float,
        compatible_services: Optional[List[str]] = None,
        compatible_plans: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create service add-on."""
        addon = await self._service.create_addon(
            name=name,
            addon_type=addon_type,
            price=price,
            compatible_services=compatible_services or [],
            compatible_plans=compatible_plans or [],
            **kwargs,
        )

        return {
            "addon_id": addon["addon_id"],
            "name": addon["name"],
            "description": addon["description"],
            "addon_type": addon["addon_type"],
            "compatible_services": addon["compatible_services"],
            "compatible_plans": addon["compatible_plans"],
            "price": float(addon["price"]),
            "billing_cycle": addon["billing_cycle"],
            "currency": addon["currency"],
            "features": addon["features"],
            "status": addon["status"],
            "created_at": addon["created_at"],
        }

    async def get_service_catalog(
        self,
        category_id: Optional[str] = None,
        service_type: Optional[str] = None,
        status: str = "published",
    ) -> Dict[str, Any]:
        """Get service catalog."""
        definitions = list(self._service._service_definitions.values())

        # Filter by criteria
        if category_id:
            definitions = [
                d for d in definitions if d.get("category_id") == category_id
            ]

        if service_type:
            definitions = [d for d in definitions if d["service_type"] == service_type]

        if status:
            definitions = [d for d in definitions if d["status"] == status]

        # Get associated plans for each definition
        catalog_items = []
        for definition in definitions:
            plans = [
                plan
                for plan in self._service._service_plans.values()
                if plan["definition_id"] == definition["definition_id"]
                and plan["status"] == "active"
            ]

            catalog_items.append(
                {
                    "definition": {
                        "definition_id": definition["definition_id"],
                        "name": definition["name"],
                        "description": definition["description"],
                        "service_type": definition["service_type"],
                        "category_id": definition["category_id"],
                    },
                    "plans": [
                        {
                            "plan_id": plan["plan_id"],
                            "name": plan["name"],
                            "plan_type": plan["plan_type"],
                            "base_price": float(plan["base_price"]),
                            "billing_cycle": plan["billing_cycle"],
                            "currency": plan["currency"],
                            "features": plan["features"],
                        }
                        for plan in plans
                    ],
                }
            )

        return {
            "catalog_items": catalog_items,
            "total_services": len(catalog_items),
            "generated_at": utc_now().isoformat(),
        }

    async def calculate_bundle_pricing(
        self, bundle_id: str, selected_services: List[str]
    ) -> Dict[str, Any]:
        """Calculate bundle pricing."""
        pricing = await self._service.calculate_bundle_price(
            bundle_id, selected_services
        )

        return {
            "bundle_id": pricing["bundle_id"],
            "bundle_name": pricing["bundle_name"],
            "selected_services": pricing["selected_services"],
            "pricing": {
                "individual_total": pricing["individual_total"],
                "discount_amount": pricing["discount_amount"],
                "final_price": pricing["final_price"],
                "currency": pricing["currency"],
                "discount_percentage": pricing["discount_percentage"],
            },
            "calculated_at": utc_now().isoformat(),
        }

    async def get_compatible_addons(self, service_plan_id: str) -> List[Dict[str, Any]]:
        """Get compatible add-ons for a service plan."""
        if service_plan_id not in self._service._service_plans:
            raise ServicePlanError(f"Service plan not found: {service_plan_id}")

        plan = self._service._service_plans[service_plan_id]
        definition_id = plan["definition_id"]

        compatible_addons = []
        for addon in self._service._addons.values():
            if addon["status"] != "active":
                continue

            # Check if addon is compatible with this service or plan
            if (
                definition_id in addon["compatible_services"]
                or service_plan_id in addon["compatible_plans"]
            ):

                compatible_addons.append(
                    {
                        "addon_id": addon["addon_id"],
                        "name": addon["name"],
                        "description": addon["description"],
                        "addon_type": addon["addon_type"],
                        "price": float(addon["price"]),
                        "billing_cycle": addon["billing_cycle"],
                        "currency": addon["currency"],
                        "features": addon["features"],
                    }
                )

        return compatible_addons

    async def validate_service_combination(
        self, service_plans: List[str], addons: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Validate service combination compatibility."""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "recommendations": [],
        }

        # Validate all plans exist
        for plan_id in service_plans:
            if plan_id not in self._service._service_plans:
                validation_result["valid"] = False
                validation_result["errors"].append(f"Service plan not found: {plan_id}")

        # Validate add-ons if provided
        if addons:
            for addon_id in addons:
                if addon_id not in self._service._addons:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"Add-on not found: {addon_id}")
                else:
                    addon = self._service._addons[addon_id]
                    # Check compatibility
                    compatible = False
                    for plan_id in service_plans:
                        if plan_id in addon["compatible_plans"]:
                            compatible = True
                            break

                    if not compatible:
                        validation_result["valid"] = False
                        validation_result["errors"].append(
                            f"Add-on {addon_id} not compatible with selected services"
                        )

        return validation_result
