"""
Tariff SDK - policy + pricing rules → produces a PolicyIntent (device-agnostic)
"""

from datetime import datetime
from dotmac_services.core.datetime_utils import utc_now, utc_now_iso
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import (
    PolicyIntentError,
    PricingRuleError,
    TariffError,
)


class PricingModel(Enum):
    """Pricing model types."""
    FLAT_RATE = "flat_rate"
    USAGE_BASED = "usage_based"
    TIERED = "tiered"
    VOLUME_DISCOUNT = "volume_discount"
    TIME_OF_USE = "time_of_use"
    DYNAMIC = "dynamic"


class PolicyIntentType(Enum):
    """Policy intent types."""
    QOS = "qos"
    BANDWIDTH = "bandwidth"
    TRAFFIC_SHAPING = "traffic_shaping"
    ACCESS_CONTROL = "access_control"
    ROUTING = "routing"
    FIREWALL = "firewall"
    MONITORING = "monitoring"


class TariffService:
    """In-memory service for tariff and pricing operations."""

    def __init__(self):
        self._tariff_plans: Dict[str, Dict[str, Any]] = {}
        self._pricing_rules: Dict[str, Dict[str, Any]] = {}
        self._policy_templates: Dict[str, Dict[str, Any]] = {}
        self._policy_intents: Dict[str, Dict[str, Any]] = {}
        self._discount_rules: Dict[str, Dict[str, Any]] = {}
        self._tax_rules: Dict[str, Dict[str, Any]] = {}

    async def create_tariff_plan(self, **kwargs) -> Dict[str, Any]:
        """Create tariff plan."""
        plan_id = kwargs.get("plan_id") or str(uuid4())

        plan = {
            "plan_id": plan_id,
            "name": kwargs["name"],
            "description": kwargs.get("description", ""),
            "service_type": kwargs["service_type"],  # data, voice, video
            "pricing_model": kwargs["pricing_model"],
            "base_price": Decimal(str(kwargs.get("base_price", "0.00"))),
            "currency": kwargs.get("currency", "USD"),
            "billing_cycle": kwargs.get("billing_cycle", "monthly"),
            "pricing_rules": kwargs.get("pricing_rules", []),
            "policy_templates": kwargs.get("policy_templates", []),
            "discount_eligibility": kwargs.get("discount_eligibility", {}),
            "tax_category": kwargs.get("tax_category", "standard"),
            "effective_date": kwargs.get("effective_date", utc_now().isoformat()),
            "expiry_date": kwargs.get("expiry_date"),
            "status": kwargs.get("status", "active"),
            "metadata": kwargs.get("metadata", {}),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        # Validate tariff plan
        self._validate_tariff_plan(plan)

        self._tariff_plans[plan_id] = plan
        return plan

    def _validate_tariff_plan(self, plan: Dict[str, Any]):
        """Validate tariff plan."""
        if not plan.get("name"):
            raise TariffError("Tariff plan name is required")

        if not plan.get("service_type"):
            raise TariffError("Service type is required")

        valid_models = [model.value for model in PricingModel]
        if plan["pricing_model"] not in valid_models:
            raise TariffError(f"Invalid pricing model. Must be one of: {valid_models}")

        if plan["base_price"] < 0:
            raise TariffError("Base price cannot be negative")

    async def create_pricing_rule(self, **kwargs) -> Dict[str, Any]:
        """Create pricing rule."""
        rule_id = kwargs.get("rule_id") or str(uuid4())

        rule = {
            "rule_id": rule_id,
            "name": kwargs["name"],
            "rule_type": kwargs["rule_type"],  # usage_tier, time_based, volume_discount
            "conditions": kwargs.get("conditions", {}),
            "pricing_formula": kwargs.get("pricing_formula", {}),
            "unit_price": Decimal(str(kwargs.get("unit_price", "0.00"))),
            "unit_type": kwargs.get("unit_type", "GB"),  # GB, minutes, sessions
            "tier_thresholds": kwargs.get("tier_thresholds", []),
            "time_periods": kwargs.get("time_periods", []),
            "volume_breaks": kwargs.get("volume_breaks", []),
            "overage_rate": Decimal(str(kwargs.get("overage_rate", "0.00"))),
            "minimum_charge": Decimal(str(kwargs.get("minimum_charge", "0.00"))),
            "maximum_charge": Decimal(str(kwargs.get("maximum_charge", "999999.99"))),
            "rounding_rules": kwargs.get("rounding_rules", {}),
            "effective_date": kwargs.get("effective_date", utc_now().isoformat()),
            "expiry_date": kwargs.get("expiry_date"),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
        }

        # Validate pricing rule
        self._validate_pricing_rule(rule)

        self._pricing_rules[rule_id] = rule
        return rule

    def _validate_pricing_rule(self, rule: Dict[str, Any]):
        """Validate pricing rule."""
        if not rule.get("name"):
            raise PricingRuleError("Pricing rule name is required")

        if not rule.get("rule_type"):
            raise PricingRuleError("Rule type is required")

        if rule["unit_price"] < 0:
            raise PricingRuleError("Unit price cannot be negative")

        if rule["minimum_charge"] < 0:
            raise PricingRuleError("Minimum charge cannot be negative")

    async def create_policy_template(self, **kwargs) -> Dict[str, Any]:
        """Create policy template."""
        template_id = kwargs.get("template_id") or str(uuid4())

        template = {
            "template_id": template_id,
            "name": kwargs["name"],
            "description": kwargs.get("description", ""),
            "policy_type": kwargs["policy_type"],
            "service_type": kwargs.get("service_type"),
            "policy_rules": kwargs.get("policy_rules", {}),
            "parameters": kwargs.get("parameters", {}),
            "conditions": kwargs.get("conditions", {}),
            "actions": kwargs.get("actions", {}),
            "priority": kwargs.get("priority", 100),
            "device_agnostic": kwargs.get("device_agnostic", True),
            "vendor_mappings": kwargs.get("vendor_mappings", {}),
            "validation_rules": kwargs.get("validation_rules", {}),
            "status": kwargs.get("status", "active"),
            "version": kwargs.get("version", "1.0.0"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        self._policy_templates[template_id] = template
        return template

    async def calculate_pricing(
        self,
        tariff_plan_id: str,
        usage_data: Dict[str, Any],
        billing_period: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Calculate pricing based on tariff plan and usage."""
        if tariff_plan_id not in self._tariff_plans:
            raise TariffError(f"Tariff plan not found: {tariff_plan_id}")

        plan = self._tariff_plans[tariff_plan_id]

        # Initialize calculation
        calculation = {
            "tariff_plan_id": tariff_plan_id,
            "plan_name": plan["name"],
            "base_price": float(plan["base_price"]),
            "usage_charges": [],
            "total_usage_charges": 0.0,
            "discounts": [],
            "total_discounts": 0.0,
            "taxes": [],
            "total_taxes": 0.0,
            "subtotal": 0.0,
            "total_amount": 0.0,
            "currency": plan["currency"],
            "billing_period": billing_period,
            "calculated_at": utc_now().isoformat(),
        }

        # Calculate base charges
        subtotal = plan["base_price"]

        # Apply pricing rules
        for rule_id in plan.get("pricing_rules", []):
            if rule_id in self._pricing_rules:
                rule = self._pricing_rules[rule_id]
                usage_charge = await self._apply_pricing_rule(rule, usage_data)
                if usage_charge:
                    calculation["usage_charges"].append(usage_charge)
                    subtotal += Decimal(str(usage_charge["amount"]))

        calculation["total_usage_charges"] = float(sum(
            Decimal(str(charge["amount"])) for charge in calculation["usage_charges"]
        ))
        calculation["subtotal"] = float(subtotal)

        # Apply discounts
        discounts = await self._calculate_discounts(plan, subtotal, usage_data)
        calculation["discounts"] = discounts
        calculation["total_discounts"] = sum(discount["amount"] for discount in discounts)

        # Calculate taxes
        taxable_amount = subtotal - Decimal(str(calculation["total_discounts"]))
        taxes = await self._calculate_taxes(plan, taxable_amount)
        calculation["taxes"] = taxes
        calculation["total_taxes"] = sum(tax["amount"] for tax in taxes)

        # Final total
        calculation["total_amount"] = float(
            taxable_amount + Decimal(str(calculation["total_taxes"]))
        )

        return calculation

    async def _apply_pricing_rule(
        self,
        rule: Dict[str, Any],
        usage_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Apply pricing rule to usage data."""
        rule_type = rule["rule_type"]
        unit_type = rule["unit_type"]

        # Get usage amount for this unit type
        usage_amount = usage_data.get(unit_type.lower(), 0)
        if usage_amount <= 0:
            return None

        charge_amount = Decimal("0.00")

        if rule_type == "flat_rate":
            charge_amount = rule["unit_price"] * Decimal(str(usage_amount))

        elif rule_type == "tiered":
            charge_amount = self._calculate_tiered_pricing(rule, usage_amount)

        elif rule_type == "volume_discount":
            charge_amount = self._calculate_volume_discount_pricing(rule, usage_amount)

        elif rule_type == "time_based":
            charge_amount = self._calculate_time_based_pricing(rule, usage_data)

        # Apply minimum and maximum charges
        if charge_amount < rule["minimum_charge"]:
            charge_amount = rule["minimum_charge"]
        elif charge_amount > rule["maximum_charge"]:
            charge_amount = rule["maximum_charge"]

        return {
            "rule_id": rule["rule_id"],
            "rule_name": rule["name"],
            "rule_type": rule_type,
            "unit_type": unit_type,
            "usage_amount": usage_amount,
            "unit_price": float(rule["unit_price"]),
            "amount": float(charge_amount),
        }

    def _calculate_tiered_pricing(self, rule: Dict[str, Any], usage_amount: float) -> Decimal:
        """Calculate tiered pricing."""
        total_charge = Decimal("0.00")
        remaining_usage = Decimal(str(usage_amount))

        tiers = rule.get("tier_thresholds", [])
        for i, tier in enumerate(tiers):
            tier_limit = Decimal(str(tier["limit"]))
            tier_price = Decimal(str(tier["price"]))

            if remaining_usage <= 0:
                break

            if i == len(tiers) - 1:  # Last tier
                tier_usage = remaining_usage
            else:
                tier_usage = min(remaining_usage, tier_limit)

            total_charge += tier_usage * tier_price
            remaining_usage -= tier_usage

        return total_charge

    def _calculate_volume_discount_pricing(self, rule: Dict[str, Any], usage_amount: float) -> Decimal:
        """Calculate volume discount pricing."""
        base_charge = rule["unit_price"] * Decimal(str(usage_amount))

        volume_breaks = rule.get("volume_breaks", [])
        for volume_break in sorted(volume_breaks, key=lambda x: x["threshold"], reverse=True):
            if usage_amount >= volume_break["threshold"]:
                discount_rate = Decimal(str(volume_break["discount_rate"]))
                return base_charge * (1 - discount_rate / 100)

        return base_charge

    def _calculate_time_based_pricing(self, rule: Dict[str, Any], usage_data: Dict[str, Any]) -> Decimal:
        """Calculate time-based pricing."""
        total_charge = Decimal("0.00")

        time_periods = rule.get("time_periods", [])
        for period in time_periods:
            period_usage = usage_data.get(f"{rule['unit_type'].lower()}_{period['period']}", 0)
            if period_usage > 0:
                period_price = Decimal(str(period["price"]))
                total_charge += Decimal(str(period_usage)) * period_price

        return total_charge

    async def _calculate_discounts(
        self,
        plan: Dict[str, Any],
        subtotal: Decimal,
        usage_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Calculate applicable discounts."""
        discounts = []

        # Apply discount rules based on eligibility
        discount_eligibility = plan.get("discount_eligibility", {})

        for discount_type, discount_config in discount_eligibility.items():
            if discount_config.get("enabled", False):
                discount_amount = self._calculate_discount_amount(
                    discount_type, discount_config, subtotal, usage_data
                )

                if discount_amount > 0:
                    discounts.append({
                        "type": discount_type,
                        "description": discount_config.get("description", ""),
                        "amount": float(discount_amount),
                        "percentage": float((discount_amount / subtotal) * 100) if subtotal > 0 else 0,
                    })

        return discounts

    def _calculate_discount_amount(
        self,
        discount_type: str,
        discount_config: Dict[str, Any],
        subtotal: Decimal,
        usage_data: Dict[str, Any]
    ) -> Decimal:
        """Calculate discount amount."""
        if discount_config.get("type") == "percentage":
            return subtotal * (Decimal(str(discount_config["value"])) / 100)
        elif discount_config.get("type") == "fixed":
            return Decimal(str(discount_config["value"]))

        return Decimal("0.00")

    async def _calculate_taxes(
        self,
        plan: Dict[str, Any],
        taxable_amount: Decimal
    ) -> List[Dict[str, Any]]:
        """Calculate applicable taxes."""
        taxes = []
        tax_category = plan.get("tax_category", "standard")

        # Simple tax calculation (can be extended with complex tax rules)
        if tax_category == "standard":
            tax_rate = Decimal("0.10")  # 10% tax
            tax_amount = taxable_amount * tax_rate

            taxes.append({
                "type": "sales_tax",
                "description": "Standard Sales Tax",
                "rate": float(tax_rate * 100),
                "amount": float(tax_amount),
            })

        return taxes

    async def generate_policy_intent(
        self,
        tariff_plan_id: str,
        service_instance_id: str,
        customer_profile: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Generate policy intent from tariff plan."""
        if tariff_plan_id not in self._tariff_plans:
            raise TariffError(f"Tariff plan not found: {tariff_plan_id}")

        plan = self._tariff_plans[tariff_plan_id]
        intent_id = str(uuid4())

        # Generate policy intents from templates
        policy_intents = []

        for template_id in plan.get("policy_templates", []):
            if template_id in self._policy_templates:
                template = self._policy_templates[template_id]

                intent = {
                    "intent_id": str(uuid4()),
                    "template_id": template_id,
                    "policy_type": template["policy_type"],
                    "service_type": template.get("service_type"),
                    "parameters": self._resolve_policy_parameters(
                        template["parameters"],
                        plan,
                        customer_profile
                    ),
                    "conditions": template["conditions"],
                    "actions": template["actions"],
                    "priority": template["priority"],
                    "device_agnostic": template["device_agnostic"],
                    "vendor_mappings": template["vendor_mappings"],
                }

                policy_intents.append(intent)

        policy_intent = {
            "intent_id": intent_id,
            "tariff_plan_id": tariff_plan_id,
            "service_instance_id": service_instance_id,
            "customer_id": customer_profile.get("customer_id"),
            "policy_intents": policy_intents,
            "metadata": {
                "plan_name": plan["name"],
                "service_type": plan["service_type"],
                "pricing_model": plan["pricing_model"],
            },
            "generated_at": utc_now().isoformat(),
            "status": "generated",
            "version": "1.0.0",
        }

        self._policy_intents[intent_id] = policy_intent
        return policy_intent

    def _resolve_policy_parameters(
        self,
        template_parameters: Dict[str, Any],
        plan: Dict[str, Any],
        customer_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve policy parameters from template, plan, and customer data."""
        resolved_params = {}

        for param_name, param_config in template_parameters.items():
            if isinstance(param_config, dict) and "source" in param_config:
                source = param_config["source"]

                if source == "plan":
                    resolved_params[param_name] = plan.get(param_config["field"])
                elif source == "customer":
                    resolved_params[param_name] = customer_profile.get(param_config["field"])
                elif source == "static":
                    resolved_params[param_name] = param_config["value"]
                else:
                    resolved_params[param_name] = param_config.get("default")
            else:
                resolved_params[param_name] = param_config

        return resolved_params


class TariffSDK:
    """Minimal, reusable SDK for tariff and policy intent management."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = TariffService()

    async def create_tariff_plan(
        self,
        name: str,
        service_type: str,
        pricing_model: str,
        base_price: float = 0.0,
        currency: str = "USD",
        **kwargs
    ) -> Dict[str, Any]:
        """Create tariff plan."""
        plan = await self._service.create_tariff_plan(
            name=name,
            service_type=service_type,
            pricing_model=pricing_model,
            base_price=base_price,
            currency=currency,
            tenant_id=self.tenant_id,
            **kwargs
        )

        return {
            "plan_id": plan["plan_id"],
            "name": plan["name"],
            "description": plan["description"],
            "service_type": plan["service_type"],
            "pricing_model": plan["pricing_model"],
            "base_price": float(plan["base_price"]),
            "currency": plan["currency"],
            "billing_cycle": plan["billing_cycle"],
            "status": plan["status"],
            "effective_date": plan["effective_date"],
            "created_at": plan["created_at"],
        }

    async def create_pricing_rule(
        self,
        name: str,
        rule_type: str,
        unit_price: float,
        unit_type: str = "GB",
        **kwargs
    ) -> Dict[str, Any]:
        """Create pricing rule."""
        rule = await self._service.create_pricing_rule(
            name=name,
            rule_type=rule_type,
            unit_price=unit_price,
            unit_type=unit_type,
            **kwargs
        )

        return {
            "rule_id": rule["rule_id"],
            "name": rule["name"],
            "rule_type": rule["rule_type"],
            "unit_price": float(rule["unit_price"]),
            "unit_type": rule["unit_type"],
            "tier_thresholds": rule["tier_thresholds"],
            "volume_breaks": rule["volume_breaks"],
            "status": rule["status"],
            "created_at": rule["created_at"],
        }

    async def create_policy_template(
        self,
        name: str,
        policy_type: str,
        policy_rules: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create policy template."""
        template = await self._service.create_policy_template(
            name=name,
            policy_type=policy_type,
            policy_rules=policy_rules,
            parameters=parameters or {},
            **kwargs
        )

        return {
            "template_id": template["template_id"],
            "name": template["name"],
            "description": template["description"],
            "policy_type": template["policy_type"],
            "service_type": template["service_type"],
            "policy_rules": template["policy_rules"],
            "parameters": template["parameters"],
            "device_agnostic": template["device_agnostic"],
            "status": template["status"],
            "version": template["version"],
            "created_at": template["created_at"],
        }

    async def calculate_service_pricing(
        self,
        tariff_plan_id: str,
        usage_data: Dict[str, Any],
        billing_period: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Calculate service pricing."""
        calculation = await self._service.calculate_pricing(
            tariff_plan_id=tariff_plan_id,
            usage_data=usage_data,
            billing_period=billing_period
        )

        return {
            "tariff_plan_id": calculation["tariff_plan_id"],
            "plan_name": calculation["plan_name"],
            "pricing_breakdown": {
                "base_price": calculation["base_price"],
                "usage_charges": calculation["usage_charges"],
                "total_usage_charges": calculation["total_usage_charges"],
                "subtotal": calculation["subtotal"],
            },
            "adjustments": {
                "discounts": calculation["discounts"],
                "total_discounts": calculation["total_discounts"],
                "taxes": calculation["taxes"],
                "total_taxes": calculation["total_taxes"],
            },
            "total_amount": calculation["total_amount"],
            "currency": calculation["currency"],
            "billing_period": calculation["billing_period"],
            "calculated_at": calculation["calculated_at"],
        }

    async def generate_policy_intent(
        self,
        tariff_plan_id: str,
        service_instance_id: str,
        customer_profile: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Generate device-agnostic policy intent."""
        intent = await self._service.generate_policy_intent(
            tariff_plan_id=tariff_plan_id,
            service_instance_id=service_instance_id,
            customer_profile=customer_profile,
            **kwargs
        )

        return {
            "intent_id": intent["intent_id"],
            "tariff_plan_id": intent["tariff_plan_id"],
            "service_instance_id": intent["service_instance_id"],
            "customer_id": intent["customer_id"],
            "policy_intents": [
                {
                    "intent_id": pi["intent_id"],
                    "policy_type": pi["policy_type"],
                    "service_type": pi["service_type"],
                    "parameters": pi["parameters"],
                    "conditions": pi["conditions"],
                    "actions": pi["actions"],
                    "priority": pi["priority"],
                    "device_agnostic": pi["device_agnostic"],
                }
                for pi in intent["policy_intents"]
            ],
            "metadata": intent["metadata"],
            "generated_at": intent["generated_at"],
            "status": intent["status"],
            "version": intent["version"],
        }

    async def get_tariff_plans(
        self,
        service_type: Optional[str] = None,
        status: str = "active"
    ) -> List[Dict[str, Any]]:
        """Get tariff plans."""
        plans = list(self._service._tariff_plans.values())

        if service_type:
            plans = [p for p in plans if p["service_type"] == service_type]

        if status:
            plans = [p for p in plans if p["status"] == status]

        return [
            {
                "plan_id": plan["plan_id"],
                "name": plan["name"],
                "service_type": plan["service_type"],
                "pricing_model": plan["pricing_model"],
                "base_price": float(plan["base_price"]),
                "currency": plan["currency"],
                "billing_cycle": plan["billing_cycle"],
                "status": plan["status"],
                "effective_date": plan["effective_date"],
            }
            for plan in plans
        ]

    async def validate_policy_intent(self, intent_id: str) -> Dict[str, Any]:
        """Validate policy intent."""
        if intent_id not in self._service._policy_intents:
            raise PolicyIntentError(f"Policy intent not found: {intent_id}")

        intent = self._service._policy_intents[intent_id]

        validation_result = {
            "intent_id": intent_id,
            "valid": True,
            "errors": [],
            "warnings": [],
            "policy_count": len(intent["policy_intents"]),
        }

        # Validate each policy intent
        for policy_intent in intent["policy_intents"]:
            # Check required parameters
            if not policy_intent.get("parameters"):
                validation_result["errors"].append(
                    f"Policy {policy_intent['intent_id']} missing parameters"
                )
                validation_result["valid"] = False

            # Check policy type
            if not policy_intent.get("policy_type"):
                validation_result["errors"].append(
                    f"Policy {policy_intent['intent_id']} missing policy type"
                )
                validation_result["valid"] = False

        return validation_result
