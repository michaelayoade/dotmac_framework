"""
IPAM Network Planning - Advanced network planning and subnet management.
"""

import ipaddress
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from ..core.models import NetworkType

    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    NetworkType = None


class SubnetPurpose(str, Enum):
    """Subnet allocation purposes."""

    CUSTOMER = "customer"
    INFRASTRUCTURE = "infrastructure"
    MANAGEMENT = "management"
    DMZ = "dmz"
    VOICE = "voice"
    GUEST = "guest"
    IOT = "iot"
    RESERVED = "reserved"


class IPPoolType(str, Enum):
    """IP pool types for different services."""

    DHCP = "dhcp"
    STATIC = "static"
    VIP = "vip"  # Virtual IP
    NAT = "nat"
    LOOPBACK = "loopback"
    POINT_TO_POINT = "point_to_point"


@dataclass
class SubnetRequirement:
    """Subnet allocation requirement."""

    purpose: SubnetPurpose
    min_hosts: int
    max_hosts: Optional[int] = None
    preferred_size: Optional[int] = None  # Preferred subnet size (prefix length)
    growth_factor: float = 1.2  # Growth allowance multiplier
    priority: int = 1  # Higher number = higher priority
    location: Optional[str] = None
    vlan_id: Optional[int] = None
    tags: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IPPool:
    """IP address pool definition."""

    pool_id: str
    pool_type: IPPoolType
    start_ip: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
    end_ip: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
    purpose: str
    network_id: str
    reserved_count: int = 0
    description: Optional[str] = None
    tags: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_addresses(self) -> int:
        """Calculate total addresses in pool."""
        return int(self.end_ip) - int(self.start_ip) + 1

    @property
    def available_addresses(self) -> int:
        """Calculate available addresses in pool."""
        return max(0, self.total_addresses - self.reserved_count)


@dataclass
class NetworkHierarchy:
    """Network hierarchy node."""

    network_id: str
    parent_id: Optional[str]
    cidr: str
    level: int
    children: List["NetworkHierarchy"] = field(default_factory=list)
    allocated_subnets: List[str] = field(default_factory=list)

    @property
    def network(self) -> ipaddress.ip_network:
        """Get network object."""
        return ipaddress.ip_network(self.cidr)

    @property
    def available_space(self) -> int:
        """Calculate available address space."""
        total = self.network.num_addresses
        allocated = sum(
            ipaddress.ip_network(subnet).num_addresses
            for subnet in self.allocated_subnets
        )
        return total - allocated


class NetworkPlanner:
    """
    Advanced network planner for automated subnet allocation and management.

    Features:
    - Hierarchical subnet planning
    - IP pool management
    - Automatic subnet provisioning
    - Growth planning and forecasting
    - Conflict detection and resolution
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize network planner."""
        self.config = config or {}
        self.hierarchies: Dict[str, NetworkHierarchy] = {}
        self.ip_pools: Dict[str, Dict[str, IPPool]] = (
            {}
        )  # network_id -> pool_id -> pool

        # Default subnet sizes for different purposes
        self.default_subnet_sizes = {
            SubnetPurpose.CUSTOMER: 24,  # /24 for customer networks
            SubnetPurpose.INFRASTRUCTURE: 26,  # /26 for infrastructure
            SubnetPurpose.MANAGEMENT: 27,  # /27 for management
            SubnetPurpose.DMZ: 25,  # /25 for DMZ
            SubnetPurpose.VOICE: 26,  # /26 for VoIP
            SubnetPurpose.GUEST: 24,  # /24 for guest networks
            SubnetPurpose.IOT: 25,  # /25 for IoT devices
            SubnetPurpose.RESERVED: 28,  # /28 for reserved space
        }

        # Minimum growth factors
        self.min_growth_factors = {
            SubnetPurpose.CUSTOMER: 1.5,
            SubnetPurpose.INFRASTRUCTURE: 1.2,
            SubnetPurpose.MANAGEMENT: 1.1,
            SubnetPurpose.DMZ: 1.3,
            SubnetPurpose.VOICE: 1.4,
            SubnetPurpose.GUEST: 1.6,
            SubnetPurpose.IOT: 1.8,
            SubnetPurpose.RESERVED: 1.0,
        }

    def create_network_hierarchy(
        self, supernet: str, tenant_id: str, max_levels: int = 3
    ) -> NetworkHierarchy:
        """
        Create hierarchical network structure from supernet.

        Args:
            supernet: CIDR of the supernet
            tenant_id: Tenant identifier
            max_levels: Maximum hierarchy levels

        Returns:
            Root network hierarchy node
        """
        network = ipaddress.ip_network(supernet)

        hierarchy = NetworkHierarchy(
            network_id=f"{tenant_id}::{supernet}",
            parent_id=None,
            cidr=supernet,
            level=0,
        )

        self.hierarchies[hierarchy.network_id] = hierarchy
        return hierarchy

    def calculate_optimal_subnet_size(self, requirement: SubnetRequirement) -> int:
        """
        Calculate optimal subnet size for requirement.

        Args:
            requirement: Subnet requirement specification

        Returns:
            Optimal prefix length
        """
        if requirement.preferred_size:
            return requirement.preferred_size

        # Calculate required hosts with growth factor
        growth_factor = max(
            requirement.growth_factor,
            self.min_growth_factors.get(requirement.purpose, 1.2),
        )

        required_hosts = int(requirement.min_hosts * growth_factor)

        if requirement.max_hosts:
            required_hosts = min(required_hosts, requirement.max_hosts)

        # Calculate prefix length
        # Need to account for network and broadcast addresses
        total_addresses_needed = required_hosts + 2

        # Find smallest subnet that can accommodate the requirements
        prefix_length = 32 - math.ceil(math.log2(max(total_addresses_needed, 4)))

        # Ensure it doesn't exceed the default for this purpose
        default_prefix = self.default_subnet_sizes.get(requirement.purpose, 24)
        prefix_length = min(prefix_length, default_prefix)

        # Ensure reasonable bounds
        prefix_length = max(8, min(30, prefix_length))

        return prefix_length

    def plan_subnets(
        self, supernet: str, requirements: List[SubnetRequirement], tenant_id: str
    ) -> Dict[str, Any]:
        """
        Plan subnet allocation for given requirements.

        Args:
            supernet: CIDR of the supernet to subdivide
            requirements: List of subnet requirements
            tenant_id: Tenant identifier

        Returns:
            Subnet allocation plan
        """
        network = ipaddress.ip_network(supernet)

        # Sort requirements by priority (highest first) and then by size needed
        sorted_requirements = sorted(
            requirements,
            key=lambda r: (-r.priority, -self.calculate_optimal_subnet_size(r)),
        )

        allocated_subnets = []
        remaining_space = [network]
        allocation_failures = []

        for req in sorted_requirements:
            prefix_length = self.calculate_optimal_subnet_size(req)
            subnet_allocated = False

            # Try to allocate from available space
            for i, available_space in enumerate(remaining_space):
                try:
                    # Check if we can subdivide this space
                    if available_space.prefixlen <= prefix_length:
                        # Generate subnets of required size
                        subnets = list(
                            available_space.subnets(new_prefix=prefix_length)
                        )

                        if subnets:
                            # Allocate first available subnet
                            allocated_subnet = subnets[0]

                            allocated_subnets.append(
                                {
                                    "requirement": req,
                                    "cidr": str(allocated_subnet),
                                    "purpose": req.purpose,
                                    "size": prefix_length,
                                    "hosts_available": allocated_subnet.num_addresses
                                    - 2,
                                    "location": req.location,
                                    "vlan_id": req.vlan_id,
                                    "priority": req.priority,
                                    "tags": req.tags,
                                }
                            )

                            # Update remaining space
                            remaining_space[i : i + 1] = subnets[
                                1:
                            ]  # Replace with remaining subnets
                            subnet_allocated = True
                            break

                except ValueError as e:
                    # Cannot subdivide this space
                    continue

            if not subnet_allocated:
                allocation_failures.append(
                    {
                        "requirement": req,
                        "reason": "insufficient_space",
                        "required_size": prefix_length,
                        "available_spaces": [str(space) for space in remaining_space],
                    }
                )

        # Calculate utilization
        total_addresses = network.num_addresses
        allocated_addresses = sum(
            ipaddress.ip_network(subnet["cidr"]).num_addresses
            for subnet in allocated_subnets
        )
        remaining_addresses = sum(space.num_addresses for space in remaining_space)

        return {
            "supernet": supernet,
            "tenant_id": tenant_id,
            "total_addresses": total_addresses,
            "allocated_addresses": allocated_addresses,
            "remaining_addresses": remaining_addresses,
            "utilization_percent": round(
                (allocated_addresses / total_addresses) * 100, 2
            ),
            "allocated_subnets": allocated_subnets,
            "allocation_failures": allocation_failures,
            "remaining_space": [str(space) for space in remaining_space],
            "requirements_processed": len(sorted_requirements),
            "requirements_satisfied": len(allocated_subnets),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def create_ip_pools(
        self, network_id: str, cidr: str, pool_configs: List[Dict[str, Any]]
    ) -> Dict[str, IPPool]:
        """
        Create IP pools within a network.

        Args:
            network_id: Network identifier
            cidr: Network CIDR
            pool_configs: Pool configuration specifications

        Returns:
            Dictionary of created IP pools
        """
        network = ipaddress.ip_network(cidr)
        pools = {}

        if network_id not in self.ip_pools:
            self.ip_pools[network_id] = {}

        for config in pool_configs:
            pool_id = config["pool_id"]
            pool_type = IPPoolType(config["pool_type"])

            # Calculate pool range
            if "start_ip" in config and "end_ip" in config:
                start_ip = ipaddress.ip_address(config["start_ip"])
                end_ip = ipaddress.ip_address(config["end_ip"])
            else:
                # Auto-calculate based on percentage of network
                percentage = config.get("percentage", 10)  # Default 10%
                pool_size = int((network.num_addresses * percentage) / 100)

                # Start from beginning of usable range
                hosts = list(network.hosts())
                start_ip = hosts[0]
                end_ip = hosts[min(pool_size - 1, len(hosts) - 1)]

            # Validate IP range is within network
            if start_ip not in network or end_ip not in network:
                raise ValueError(
                    f"IP pool range {start_ip}-{end_ip} not within network {cidr}"
                )

            pool = IPPool(
                pool_id=pool_id,
                pool_type=pool_type,
                start_ip=start_ip,
                end_ip=end_ip,
                purpose=config.get("purpose", pool_type.value),
                network_id=network_id,
                reserved_count=config.get("reserved_count", 0),
                description=config.get("description"),
                tags=config.get("tags", {}),
            )

            pools[pool_id] = pool
            self.ip_pools[network_id][pool_id] = pool

        return pools

    def suggest_network_expansion(
        self,
        network_id: str,
        current_utilization: float,
        growth_rate_percent: float = 10.0,
        forecast_months: int = 12,
    ) -> Dict[str, Any]:
        """
        Suggest network expansion based on utilization and growth.

        Args:
            network_id: Network identifier
            current_utilization: Current utilization percentage
            growth_rate_percent: Expected monthly growth rate
            forecast_months: Months to forecast ahead

        Returns:
            Expansion recommendations
        """
        recommendations = []

        # Calculate projected utilization
        monthly_growth = growth_rate_percent / 100
        projected_utilization = (
            current_utilization * (1 + monthly_growth) ** forecast_months
        )

        # Define thresholds
        warning_threshold = 75.0
        critical_threshold = 85.0
        emergency_threshold = 95.0

        if projected_utilization > emergency_threshold:
            urgency = "emergency"
            action = "immediate_expansion"
        elif projected_utilization > critical_threshold:
            urgency = "critical"
            action = "planned_expansion"
        elif projected_utilization > warning_threshold:
            urgency = "warning"
            action = "monitoring_required"
        else:
            urgency = "normal"
            action = "no_action_needed"

        if projected_utilization > warning_threshold:
            # Calculate expansion size needed
            target_utilization = 60.0  # Target post-expansion utilization
            expansion_factor = projected_utilization / target_utilization

            recommendations.append(
                {
                    "type": "subnet_expansion",
                    "urgency": urgency,
                    "action": action,
                    "current_utilization": current_utilization,
                    "projected_utilization": round(projected_utilization, 2),
                    "expansion_factor": round(expansion_factor, 2),
                    "recommended_timeline": f"{max(1, forecast_months - 3)} months",
                    "description": f"Expand network capacity by {round((expansion_factor - 1) * 100, 1)}%",
                }
            )

        # Check for subnet consolidation opportunities
        if current_utilization < 30.0:
            recommendations.append(
                {
                    "type": "subnet_consolidation",
                    "urgency": "low",
                    "action": "consolidation_review",
                    "current_utilization": current_utilization,
                    "description": "Consider consolidating underutilized subnets",
                }
            )

        return {
            "network_id": network_id,
            "current_utilization": current_utilization,
            "projected_utilization": round(projected_utilization, 2),
            "forecast_months": forecast_months,
            "growth_rate": growth_rate_percent,
            "overall_status": urgency,
            "recommendations": recommendations,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def detect_subnet_conflicts(
        self, proposed_subnets: List[str], existing_subnets: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Detect conflicts between proposed and existing subnets.

        Args:
            proposed_subnets: List of proposed subnet CIDRs
            existing_subnets: List of existing subnet CIDRs

        Returns:
            List of detected conflicts
        """
        conflicts = []

        for proposed in proposed_subnets:
            try:
                proposed_net = ipaddress.ip_network(proposed)

                for existing in existing_subnets:
                    try:
                        existing_net = ipaddress.ip_network(existing)

                        if proposed_net.overlaps(existing_net):
                            conflicts.append(
                                {
                                    "type": "overlap",
                                    "proposed_subnet": proposed,
                                    "existing_subnet": existing,
                                    "severity": (
                                        "high"
                                        if proposed_net == existing_net
                                        else "medium"
                                    ),
                                    "description": f"Proposed subnet {proposed} overlaps with existing subnet {existing}",
                                }
                            )

                    except ValueError:
                        continue

            except ValueError:
                conflicts.append(
                    {
                        "type": "invalid_cidr",
                        "proposed_subnet": proposed,
                        "severity": "high",
                        "description": f"Invalid CIDR format: {proposed}",
                    }
                )

        return conflicts

    def optimize_subnet_allocation(
        self, requirements: List[SubnetRequirement], available_space: str
    ) -> Dict[str, Any]:
        """
        Optimize subnet allocation using advanced algorithms.

        Args:
            requirements: List of subnet requirements
            available_space: Available CIDR space

        Returns:
            Optimized allocation plan
        """
        # This is a simplified optimization - could be enhanced with:
        # - Genetic algorithms
        # - Simulated annealing
        # - Integer programming

        network = ipaddress.ip_network(available_space)

        # Try multiple allocation strategies
        strategies = ["priority_first", "size_first", "balanced"]

        best_plan = None
        best_score = -1

        for strategy in strategies:
            if strategy == "priority_first":
                sorted_reqs = sorted(requirements, key=lambda r: -r.priority)
            elif strategy == "size_first":
                sorted_reqs = sorted(requirements, key=lambda r: -r.min_hosts)
            else:  # balanced
                sorted_reqs = sorted(
                    requirements, key=lambda r: (-r.priority, -r.min_hosts)
                )

            plan = self.plan_subnets(available_space, sorted_reqs, "optimization")

            # Score the plan
            score = self._score_allocation_plan(plan)

            if score > best_score:
                best_score = score
                best_plan = plan
                best_plan["strategy"] = strategy

        best_plan["optimization_score"] = best_score
        return best_plan

    def _score_allocation_plan(self, plan: Dict[str, Any]) -> float:
        """Score an allocation plan for optimization."""
        # Scoring factors:
        # - Requirements satisfied (weight: 0.4)
        # - Space utilization (weight: 0.3)
        # - Priority satisfaction (weight: 0.3)

        total_reqs = plan["requirements_processed"]
        satisfied_reqs = plan["requirements_satisfied"]
        utilization = plan["utilization_percent"] / 100.0

        if total_reqs == 0:
            return 0.0

        satisfaction_score = satisfied_reqs / total_reqs
        utilization_score = min(utilization * 1.2, 1.0)  # Bonus for good utilization

        # Calculate priority satisfaction
        priority_score = 0.0
        if plan["allocated_subnets"]:
            total_priority = sum(
                subnet["priority"] for subnet in plan["allocated_subnets"]
            )
            max_possible_priority = sum(
                subnet["requirement"].priority for subnet in plan["allocated_subnets"]
            )
            if max_possible_priority > 0:
                priority_score = total_priority / max_possible_priority

        final_score = (
            satisfaction_score * 0.4 + utilization_score * 0.3 + priority_score * 0.3
        )

        return final_score
