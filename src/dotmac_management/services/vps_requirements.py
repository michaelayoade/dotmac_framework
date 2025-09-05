"""
VPS Requirements Calculator Service
Calculates hardware and software requirements for customer VPS based on plan and usage
"""

import math
from enum import Enum
from typing import Any

from dotmac_management.models.tenant import TenantPlan
from dotmac_shared.core.logging import get_logger

logger = get_logger(__name__)


class TrafficLevel(str, Enum):
    """Traffic level estimation"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class VPSRequirementsService:
    """
    Service for calculating VPS requirements based on ISP customer needs
    """

    def __init__(self):
        self.base_requirements = {
            TenantPlan.STARTER: {
                "min_cpu_cores": 2,
                "recommended_cpu_cores": 4,
                "min_ram_gb": 4,
                "recommended_ram_gb": 8,
                "min_storage_gb": 50,
                "recommended_storage_gb": 100,
                "base_bandwidth_mbps": 100,
                "setup_fee_usd": 500,
                "monthly_support_fee_usd": 200,
            },
            TenantPlan.PROFESSIONAL: {
                "min_cpu_cores": 4,
                "recommended_cpu_cores": 8,
                "min_ram_gb": 8,
                "recommended_ram_gb": 16,
                "min_storage_gb": 100,
                "recommended_storage_gb": 250,
                "base_bandwidth_mbps": 500,
                "setup_fee_usd": 1000,
                "monthly_support_fee_usd": 500,
            },
            TenantPlan.ENTERPRISE: {
                "min_cpu_cores": 8,
                "recommended_cpu_cores": 16,
                "min_ram_gb": 16,
                "recommended_ram_gb": 32,
                "min_storage_gb": 200,
                "recommended_storage_gb": 500,
                "base_bandwidth_mbps": 1000,
                "setup_fee_usd": 2000,
                "monthly_support_fee_usd": 800,
            },
            TenantPlan.CUSTOM: {
                "min_cpu_cores": 4,
                "recommended_cpu_cores": 8,
                "min_ram_gb": 8,
                "recommended_ram_gb": 16,
                "min_storage_gb": 100,
                "recommended_storage_gb": 250,
                "base_bandwidth_mbps": 500,
                "setup_fee_usd": 1500,
                "monthly_support_fee_usd": 600,
            },
        }

        self.traffic_multipliers = {
            TrafficLevel.LOW: {
                "cpu": 1.0,
                "ram": 1.0,
                "bandwidth": 1.0,
                "transfer": 1.0,
            },
            TrafficLevel.MEDIUM: {
                "cpu": 1.5,
                "ram": 1.3,
                "bandwidth": 2.0,
                "transfer": 3.0,
            },
            TrafficLevel.HIGH: {
                "cpu": 2.0,
                "ram": 1.8,
                "bandwidth": 3.0,
                "transfer": 5.0,
            },
        }

        # Customer scaling factors (per 100 customers)
        self.customer_scaling = {
            "cpu_per_100_customers": 0.5,
            "ram_per_100_customers_gb": 1.0,
            "storage_per_100_customers_gb": 5.0,
            "bandwidth_per_100_customers_mbps": 50,
        }

    async def calculate_requirements(
        self,
        plan: TenantPlan,
        expected_customers: int = 100,
        estimated_traffic: str = "low",
    ) -> dict[str, Any]:
        """
        Calculate VPS requirements based on plan and usage expectations

        Args:
            plan: Subscription plan
            expected_customers: Number of expected customers
            estimated_traffic: Traffic level estimate

        Returns:
            Dictionary with complete requirements and cost estimates
        """

        try:
            base_reqs = self.base_requirements[plan]
            traffic_level = TrafficLevel(estimated_traffic.lower())
            traffic_mult = self.traffic_multipliers[traffic_level]

            # Calculate customer scaling factor
            customer_scale_factor = max(1.0, expected_customers / 100)

            # Calculate CPU requirements
            base_cpu = base_reqs["min_cpu_cores"]
            scaled_cpu = base_cpu + (
                customer_scale_factor * self.customer_scaling["cpu_per_100_customers"]
            )
            min_cpu = math.ceil(scaled_cpu * traffic_mult["cpu"])
            recommended_cpu = math.ceil(min_cpu * 1.5)

            # Calculate RAM requirements
            base_ram = base_reqs["min_ram_gb"]
            scaled_ram = base_ram + (
                customer_scale_factor
                * self.customer_scaling["ram_per_100_customers_gb"]
            )
            min_ram = math.ceil(scaled_ram * traffic_mult["ram"])
            recommended_ram = math.ceil(min_ram * 1.5)

            # Calculate storage requirements
            base_storage = base_reqs["min_storage_gb"]
            scaled_storage = base_storage + (
                customer_scale_factor
                * self.customer_scaling["storage_per_100_customers_gb"]
            )
            min_storage = math.ceil(scaled_storage)
            recommended_storage = math.ceil(
                min_storage * 2
            )  # Extra space for logs, backups

            # Calculate bandwidth requirements
            base_bandwidth = base_reqs["base_bandwidth_mbps"]
            scaled_bandwidth = base_bandwidth + (
                customer_scale_factor
                * self.customer_scaling["bandwidth_per_100_customers_mbps"]
            )
            min_bandwidth = math.ceil(scaled_bandwidth * traffic_mult["bandwidth"])

            # Calculate monthly data transfer
            monthly_transfer_base = (
                expected_customers * 10
            )  # 10GB per customer per month base
            monthly_transfer = math.ceil(
                monthly_transfer_base * traffic_mult["transfer"]
            )

            # VPS provider cost estimates (USD per month)
            provider_costs = self._calculate_provider_costs(
                min_cpu, recommended_ram, recommended_storage, min_bandwidth
            )

            # Required network ports
            required_ports = [
                22,
                80,
                443,
                8000,
                8001,
            ]  # SSH, HTTP, HTTPS, ISP, Management
            if plan in [TenantPlan.PROFESSIONAL, TenantPlan.ENTERPRISE]:
                required_ports.extend([9090, 3000, 9093])  # Monitoring ports

            # Supported operating systems
            supported_os = [
                "Ubuntu 20.04 LTS",
                "Ubuntu 22.04 LTS",
                "Debian 11",
                "Debian 12",
                "CentOS 8 Stream",
                "Rocky Linux 8",
                "Rocky Linux 9",
            ]

            # Recommended VPS providers
            recommended_providers = [
                "DigitalOcean",
                "Linode",
                "Vultr",
                "Hetzner",
                "AWS EC2",
                "Google Cloud",
            ]

            requirements = {
                "plan": plan,
                "expected_customers": expected_customers,
                "min_cpu_cores": min_cpu,
                "recommended_cpu_cores": recommended_cpu,
                "min_ram_gb": min_ram,
                "recommended_ram_gb": recommended_ram,
                "min_storage_gb": min_storage,
                "recommended_storage_gb": recommended_storage,
                "min_bandwidth_mbps": min_bandwidth,
                "monthly_transfer_gb": monthly_transfer,
                "supported_os": supported_os,
                "required_ports": required_ports,
                "recommended_provider": recommended_providers,
                "estimated_monthly_cost_usd": provider_costs,
                "setup_fee_usd": base_reqs["setup_fee_usd"],
                "monthly_support_fee_usd": base_reqs["monthly_support_fee_usd"],
            }

            logger.info(
                f"Calculated VPS requirements for {plan} plan with {expected_customers} customers"
            )
            return requirements

        except Exception as e:
            logger.error(f"Failed to calculate VPS requirements: {e}")
            raise

    def _calculate_provider_costs(
        self, cpu_cores: int, ram_gb: int, storage_gb: int, bandwidth_mbps: int
    ) -> dict[str, int]:
        """
        Estimate monthly costs for different VPS providers

        Returns:
            Dictionary of provider -> estimated monthly cost in USD
        """

        # Base pricing models (simplified estimates)
        provider_pricing = {
            "DigitalOcean": {
                "cpu_cost_per_core": 8,
                "ram_cost_per_gb": 4,
                "storage_cost_per_gb": 0.15,
                "bandwidth_included_gb": 1000,
                "bandwidth_cost_per_gb": 0.01,
            },
            "Linode": {
                "cpu_cost_per_core": 7,
                "ram_cost_per_gb": 3.5,
                "storage_cost_per_gb": 0.12,
                "bandwidth_included_gb": 1000,
                "bandwidth_cost_per_gb": 0.01,
            },
            "Vultr": {
                "cpu_cost_per_core": 6,
                "ram_cost_per_gb": 3,
                "storage_cost_per_gb": 0.10,
                "bandwidth_included_gb": 1000,
                "bandwidth_cost_per_gb": 0.01,
            },
            "Hetzner": {
                "cpu_cost_per_core": 4,
                "ram_cost_per_gb": 2,
                "storage_cost_per_gb": 0.08,
                "bandwidth_included_gb": 20000,  # Much higher bandwidth
                "bandwidth_cost_per_gb": 0.01,
            },
            "AWS EC2": {
                "cpu_cost_per_core": 12,
                "ram_cost_per_gb": 6,
                "storage_cost_per_gb": 0.20,
                "bandwidth_included_gb": 100,
                "bandwidth_cost_per_gb": 0.09,
            },
            "Google Cloud": {
                "cpu_cost_per_core": 11,
                "ram_cost_per_gb": 5.5,
                "storage_cost_per_gb": 0.18,
                "bandwidth_included_gb": 200,
                "bandwidth_cost_per_gb": 0.08,
            },
        }

        estimated_costs = {}

        # Estimate monthly bandwidth usage (conservative)
        estimated_monthly_transfer_gb = (
            bandwidth_mbps * 24 * 30 * 0.1 / 8
        )  # 10% utilization

        for provider, pricing in provider_pricing.items():
            # Base instance cost
            cpu_cost = cpu_cores * pricing["cpu_cost_per_core"]
            ram_cost = ram_gb * pricing["ram_cost_per_gb"]
            storage_cost = storage_gb * pricing["storage_cost_per_gb"]

            # Bandwidth cost (if exceeding included)
            bandwidth_overage = max(
                0, estimated_monthly_transfer_gb - pricing["bandwidth_included_gb"]
            )
            bandwidth_cost = bandwidth_overage * pricing["bandwidth_cost_per_gb"]

            total_cost = cpu_cost + ram_cost + storage_cost + bandwidth_cost
            estimated_costs[provider] = math.ceil(total_cost)

        return estimated_costs

    def get_plan_features(self, plan: TenantPlan) -> dict[str, Any]:
        """
        Get plan-specific features and limitations

        Args:
            plan: Subscription plan

        Returns:
            Dictionary with plan features
        """

        plan_features = {
            TenantPlan.STARTER: {
                "max_customers": 500,
                "max_technicians": 5,
                "max_services": 10,
                "billing_module": False,
                "advanced_reporting": False,
                "api_access": "basic",
                "support_level": "email",
                "backup_frequency": "weekly",
                "integrations": ["basic"],
                "custom_branding": False,
            },
            TenantPlan.PROFESSIONAL: {
                "max_customers": 2000,
                "max_technicians": 15,
                "max_services": 50,
                "billing_module": True,
                "advanced_reporting": True,
                "api_access": "full",
                "support_level": "phone + email",
                "backup_frequency": "daily",
                "integrations": ["basic", "accounting", "payment"],
                "custom_branding": True,
            },
            TenantPlan.ENTERPRISE: {
                "max_customers": 10000,
                "max_technicians": 50,
                "max_services": 200,
                "billing_module": True,
                "advanced_reporting": True,
                "api_access": "full",
                "support_level": "dedicated + phone + email",
                "backup_frequency": "continuous",
                "integrations": ["all"],
                "custom_branding": True,
                "white_label": True,
                "sla": "99.9%",
            },
            TenantPlan.CUSTOM: {
                "max_customers": "unlimited",
                "max_technicians": "unlimited",
                "max_services": "unlimited",
                "billing_module": True,
                "advanced_reporting": True,
                "api_access": "full",
                "support_level": "dedicated + phone + email",
                "backup_frequency": "configurable",
                "integrations": ["custom"],
                "custom_branding": True,
                "white_label": True,
                "sla": "custom",
                "custom_development": True,
            },
        }

        return plan_features.get(plan, {})

    def validate_vps_specs(
        self, provided_specs: dict[str, Any], required_specs: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Validate if provided VPS specs meet requirements

        Args:
            provided_specs: Customer's actual VPS specifications
            required_specs: Calculated requirements

        Returns:
            Validation results with pass/fail status and recommendations
        """

        validation_results = {
            "overall_status": "pass",
            "checks": [],
            "warnings": [],
            "failures": [],
            "recommendations": [],
        }

        # CPU check
        provided_cpu = provided_specs.get("cpu_cores", 0)
        required_cpu = required_specs["min_cpu_cores"]
        if provided_cpu < required_cpu:
            validation_results["failures"].append(
                f"CPU: {provided_cpu} cores < {required_cpu} required"
            )
            validation_results["overall_status"] = "fail"
        elif provided_cpu < required_specs["recommended_cpu_cores"]:
            validation_results["warnings"].append(
                f"CPU: {provided_cpu} cores meets minimum but {required_specs['recommended_cpu_cores']} recommended"
            )
        else:
            validation_results["checks"].append(f"CPU: {provided_cpu} cores ✓")

        # RAM check
        provided_ram = provided_specs.get("ram_gb", 0)
        required_ram = required_specs["min_ram_gb"]
        if provided_ram < required_ram:
            validation_results["failures"].append(
                f"RAM: {provided_ram}GB < {required_ram}GB required"
            )
            validation_results["overall_status"] = "fail"
        elif provided_ram < required_specs["recommended_ram_gb"]:
            validation_results["warnings"].append(
                f"RAM: {provided_ram}GB meets minimum but {required_specs['recommended_ram_gb']}GB recommended"
            )
        else:
            validation_results["checks"].append(f"RAM: {provided_ram}GB ✓")

        # Storage check
        provided_storage = provided_specs.get("storage_gb", 0)
        required_storage = required_specs["min_storage_gb"]
        if provided_storage < required_storage:
            validation_results["failures"].append(
                f"Storage: {provided_storage}GB < {required_storage}GB required"
            )
            validation_results["overall_status"] = "fail"
        elif provided_storage < required_specs["recommended_storage_gb"]:
            validation_results["warnings"].append(
                f"Storage: {provided_storage}GB meets minimum but {required_specs['recommended_storage_gb']}GB recommended"
            )
        else:
            validation_results["checks"].append(f"Storage: {provided_storage}GB ✓")

        # Operating System check
        provided_os = provided_specs.get("operating_system", "")
        supported_os = required_specs["supported_os"]
        if not any(os.lower() in provided_os.lower() for os in supported_os):
            validation_results["warnings"].append(
                f"OS: '{provided_os}' not in supported list. Supported: {', '.join(supported_os)}"
            )
        else:
            validation_results["checks"].append(f"OS: {provided_os} ✓")

        # Add recommendations based on validation results
        if validation_results["overall_status"] == "fail":
            validation_results["recommendations"].append(
                "Upgrade VPS to meet minimum requirements before deployment"
            )
        elif validation_results["warnings"]:
            validation_results["recommendations"].append(
                "Consider upgrading to recommended specifications for better performance"
            )

        if (
            validation_results["overall_status"] == "pass"
            and not validation_results["warnings"]
        ):
            validation_results["recommendations"].append(
                "VPS specifications look good! Ready for deployment."
            )

        return validation_results
