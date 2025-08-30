"""
IPAM Repository - Database access layer for IPAM operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    from sqlalchemy import and_, asc, desc, func, or_
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import Session

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Session = None
    IntegrityError = Exception
    and_ = or_ = desc = asc = func = None

try:
    from ..core.exceptions import (
        AllocationNotFoundError,
        IPAMError,
        NetworkNotFoundError,
        ReservationNotFoundError,
    )
    from ..core.models import (
        AllocationStatus,
        IPAllocation,
        IPNetwork,
        IPReservation,
        NetworkType,
        ReservationStatus,
    )

    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    IPNetwork = IPAllocation = IPReservation = None
    NetworkType = AllocationStatus = ReservationStatus = None
    IPAMError = NetworkNotFoundError = AllocationNotFoundError = (
        ReservationNotFoundError
    ) = Exception


class IPAMRepository:
    """
    Repository pattern for IPAM database operations.

    Provides data access methods for networks, allocations, and reservations
    with proper error handling and tenant isolation.
    """

    def __init__(self, database_session: Session):
        """
        Initialize repository with database session.

        Args:
            database_session: SQLAlchemy session instance
        """
        if not SQLALCHEMY_AVAILABLE or not MODELS_AVAILABLE:
            raise ImportError("Repository requires SQLAlchemy and IPAM models")

        self.db = database_session

    # Network Repository Methods

    def create_network(self, **network_data) -> IPNetwork:
        """
        Create new network in database.

        Args:
            **network_data: Network attributes

        Returns:
            Created network object

        Raises:
            IPAMError: If creation fails
        """
        try:
            network = IPNetwork(**network_data)
            self.db.add(network)
            self.db.commit()
            self.db.refresh(network)
            return network
        except IntegrityError as e:
            self.db.rollback()
            raise IPAMError(f"Failed to create network: {e}")

    def get_network_by_id(self, tenant_id: str, network_id: str) -> Optional[IPNetwork]:
        """
        Get network by ID and tenant.

        Args:
            tenant_id: Tenant identifier
            network_id: Network identifier

        Returns:
            Network object or None if not found
        """
        return (
            self.db.query(IPNetwork)
            .filter(
                IPNetwork.tenant_id == tenant_id,
                IPNetwork.network_id == network_id,
                IPNetwork.is_active == True,
            )
            .first()
        )

    def get_networks_by_tenant(
        self,
        tenant_id: str,
        network_type: Optional[NetworkType] = None,
        site_id: Optional[str] = None,
        vlan_id: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[IPNetwork]:
        """
        Get networks for a tenant with optional filters.

        Args:
            tenant_id: Tenant identifier
            network_type: Optional network type filter
            site_id: Optional site filter
            vlan_id: Optional VLAN filter
            limit: Optional result limit
            offset: Result offset for pagination

        Returns:
            List of network objects
        """
        query = self.db.query(IPNetwork).filter(
            IPNetwork.tenant_id == tenant_id, IPNetwork.is_active == True
        )

        if network_type:
            query = query.filter(IPNetwork.network_type == network_type)

        if site_id:
            query = query.filter(IPNetwork.site_id == site_id)

        if vlan_id:
            query = query.filter(IPNetwork.vlan_id == vlan_id)

        query = query.order_by(IPNetwork.created_at.desc())

        if offset:
            query = query.offset(offset)

        if limit:
            query = query.limit(limit)

        return query.all()

    def update_network(
        self, tenant_id: str, network_id: str, **updates
    ) -> Optional[IPNetwork]:
        """
        Update network attributes.

        Args:
            tenant_id: Tenant identifier
            network_id: Network identifier
            **updates: Attributes to update

        Returns:
            Updated network object or None if not found
        """
        network = self.get_network_by_id(tenant_id, network_id)
        if not network:
            return None

        for key, value in updates.items():
            if hasattr(network, key):
                setattr(network, key, value)

        network.updated_at = datetime.utcnow()

        try:
            self.db.commit()
            self.db.refresh(network)
            return network
        except IntegrityError as e:
            self.db.rollback()
            raise IPAMError(f"Failed to update network: {e}")

    def delete_network(self, tenant_id: str, network_id: str) -> bool:
        """
        Soft delete network (mark as inactive).

        Args:
            tenant_id: Tenant identifier
            network_id: Network identifier

        Returns:
            True if deleted, False if not found
        """
        network = self.get_network_by_id(tenant_id, network_id)
        if not network:
            return False

        network.is_active = False
        network.updated_at = datetime.utcnow()

        self.db.commit()
        return True

    def get_overlapping_networks(self, tenant_id: str, cidr: str) -> List[IPNetwork]:
        """
        Find networks that overlap with given CIDR.

        Args:
            tenant_id: Tenant identifier
            cidr: CIDR to check for overlaps

        Returns:
            List of overlapping network objects
        """
        # This is a simplified check - in production you might want
        # to use database-specific IP range operators
        networks = self.get_networks_by_tenant(tenant_id)

        import ipaddress

        try:
            new_network = ipaddress.ip_network(cidr, strict=False)
            overlapping = []

            for network in networks:
                try:
                    existing_network = ipaddress.ip_network(network.cidr, strict=False)
                    if new_network.overlaps(existing_network):
                        overlapping.append(network)
                except ValueError:
                    continue

            return overlapping
        except ValueError:
            return []

    # Allocation Repository Methods

    def create_allocation(self, **allocation_data) -> IPAllocation:
        """
        Create new IP allocation in database.

        Args:
            **allocation_data: Allocation attributes

        Returns:
            Created allocation object

        Raises:
            IPAMError: If creation fails
        """
        try:
            allocation = IPAllocation(**allocation_data)
            self.db.add(allocation)
            self.db.commit()
            self.db.refresh(allocation)
            return allocation
        except IntegrityError as e:
            self.db.rollback()
            raise IPAMError(f"Failed to create allocation: {e}")

    def get_allocation_by_id(
        self, tenant_id: str, allocation_id: str
    ) -> Optional[IPAllocation]:
        """
        Get allocation by ID and tenant.

        Args:
            tenant_id: Tenant identifier
            allocation_id: Allocation identifier

        Returns:
            Allocation object or None if not found
        """
        return (
            self.db.query(IPAllocation)
            .filter(
                IPAllocation.tenant_id == tenant_id,
                IPAllocation.allocation_id == allocation_id,
            )
            .first()
        )

    def get_allocations_by_network(
        self,
        tenant_id: str,
        network_id: str,
        allocation_status: Optional[AllocationStatus] = None,
        include_expired: bool = False,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[IPAllocation]:
        """
        Get allocations for a network.

        Args:
            tenant_id: Tenant identifier
            network_id: Network UUID
            allocation_status: Optional status filter
            include_expired: Whether to include expired allocations
            limit: Optional result limit
            offset: Result offset for pagination

        Returns:
            List of allocation objects
        """
        # Get network to get UUID
        network = (
            self.db.query(IPNetwork)
            .filter(
                IPNetwork.tenant_id == tenant_id, IPNetwork.network_id == network_id
            )
            .first()
        )

        if not network:
            return []

        query = self.db.query(IPAllocation).filter(
            IPAllocation.tenant_id == tenant_id, IPAllocation.network_id == network.id
        )

        if allocation_status:
            query = query.filter(IPAllocation.allocation_status == allocation_status)

        if not include_expired:
            query = query.filter(
                or_(
                    IPAllocation.expires_at.is_(None),
                    IPAllocation.expires_at > datetime.utcnow(),
                )
            )

        query = query.order_by(IPAllocation.allocated_at.desc())

        if offset:
            query = query.offset(offset)

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_allocation_by_ip(
        self, tenant_id: str, ip_address: str
    ) -> Optional[IPAllocation]:
        """
        Get allocation by IP address.

        Args:
            tenant_id: Tenant identifier
            ip_address: IP address to look up

        Returns:
            Allocation object or None if not found
        """
        return (
            self.db.query(IPAllocation)
            .filter(
                IPAllocation.tenant_id == tenant_id,
                IPAllocation.ip_address == ip_address,
                IPAllocation.allocation_status == AllocationStatus.ALLOCATED,
            )
            .first()
        )

    def update_allocation(
        self, tenant_id: str, allocation_id: str, **updates
    ) -> Optional[IPAllocation]:
        """
        Update allocation attributes.

        Args:
            tenant_id: Tenant identifier
            allocation_id: Allocation identifier
            **updates: Attributes to update

        Returns:
            Updated allocation object or None if not found
        """
        allocation = self.get_allocation_by_id(tenant_id, allocation_id)
        if not allocation:
            return None

        for key, value in updates.items():
            if hasattr(allocation, key):
                setattr(allocation, key, value)

        allocation.updated_at = datetime.utcnow()

        try:
            self.db.commit()
            self.db.refresh(allocation)
            return allocation
        except IntegrityError as e:
            self.db.rollback()
            raise IPAMError(f"Failed to update allocation: {e}")

    def get_expired_allocations(
        self, tenant_id: str, limit: Optional[int] = None
    ) -> List[IPAllocation]:
        """
        Get expired allocations for cleanup.

        Args:
            tenant_id: Tenant identifier
            limit: Optional result limit

        Returns:
            List of expired allocation objects
        """
        query = (
            self.db.query(IPAllocation)
            .filter(
                IPAllocation.tenant_id == tenant_id,
                IPAllocation.allocation_status == AllocationStatus.ALLOCATED,
                IPAllocation.expires_at <= datetime.utcnow(),
            )
            .order_by(IPAllocation.expires_at.asc())
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    # Reservation Repository Methods

    def create_reservation(self, **reservation_data) -> IPReservation:
        """
        Create new IP reservation in database.

        Args:
            **reservation_data: Reservation attributes

        Returns:
            Created reservation object

        Raises:
            IPAMError: If creation fails
        """
        try:
            reservation = IPReservation(**reservation_data)
            self.db.add(reservation)
            self.db.commit()
            self.db.refresh(reservation)
            return reservation
        except IntegrityError as e:
            self.db.rollback()
            raise IPAMError(f"Failed to create reservation: {e}")

    def get_reservation_by_id(
        self, tenant_id: str, reservation_id: str
    ) -> Optional[IPReservation]:
        """
        Get reservation by ID and tenant.

        Args:
            tenant_id: Tenant identifier
            reservation_id: Reservation identifier

        Returns:
            Reservation object or None if not found
        """
        return (
            self.db.query(IPReservation)
            .filter(
                IPReservation.tenant_id == tenant_id,
                IPReservation.reservation_id == reservation_id,
            )
            .first()
        )

    def get_reservations_by_network(
        self,
        tenant_id: str,
        network_id: str,
        reservation_status: Optional[ReservationStatus] = None,
        include_expired: bool = False,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[IPReservation]:
        """
        Get reservations for a network.

        Args:
            tenant_id: Tenant identifier
            network_id: Network identifier
            reservation_status: Optional status filter
            include_expired: Whether to include expired reservations
            limit: Optional result limit
            offset: Result offset for pagination

        Returns:
            List of reservation objects
        """
        # Get network to get UUID
        network = (
            self.db.query(IPNetwork)
            .filter(
                IPNetwork.tenant_id == tenant_id, IPNetwork.network_id == network_id
            )
            .first()
        )

        if not network:
            return []

        query = self.db.query(IPReservation).filter(
            IPReservation.tenant_id == tenant_id, IPReservation.network_id == network.id
        )

        if reservation_status:
            query = query.filter(IPReservation.reservation_status == reservation_status)

        if not include_expired:
            query = query.filter(IPReservation.expires_at > datetime.utcnow())

        query = query.order_by(IPReservation.reserved_at.desc())

        if offset:
            query = query.offset(offset)

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_reservation_by_ip(
        self, tenant_id: str, ip_address: str
    ) -> Optional[IPReservation]:
        """
        Get reservation by IP address.

        Args:
            tenant_id: Tenant identifier
            ip_address: IP address to look up

        Returns:
            Reservation object or None if not found
        """
        return (
            self.db.query(IPReservation)
            .filter(
                IPReservation.tenant_id == tenant_id,
                IPReservation.ip_address == ip_address,
                IPReservation.reservation_status == ReservationStatus.RESERVED,
            )
            .first()
        )

    def update_reservation(
        self, tenant_id: str, reservation_id: str, **updates
    ) -> Optional[IPReservation]:
        """
        Update reservation attributes.

        Args:
            tenant_id: Tenant identifier
            reservation_id: Reservation identifier
            **updates: Attributes to update

        Returns:
            Updated reservation object or None if not found
        """
        reservation = self.get_reservation_by_id(tenant_id, reservation_id)
        if not reservation:
            return None

        for key, value in updates.items():
            if hasattr(reservation, key):
                setattr(reservation, key, value)

        reservation.updated_at = datetime.utcnow()

        try:
            self.db.commit()
            self.db.refresh(reservation)
            return reservation
        except IntegrityError as e:
            self.db.rollback()
            raise IPAMError(f"Failed to update reservation: {e}")

    def get_expired_reservations(
        self, tenant_id: str, limit: Optional[int] = None
    ) -> List[IPReservation]:
        """
        Get expired reservations for cleanup.

        Args:
            tenant_id: Tenant identifier
            limit: Optional result limit

        Returns:
            List of expired reservation objects
        """
        query = (
            self.db.query(IPReservation)
            .filter(
                IPReservation.tenant_id == tenant_id,
                IPReservation.reservation_status == ReservationStatus.RESERVED,
                IPReservation.expires_at <= datetime.utcnow(),
            )
            .order_by(IPReservation.expires_at.asc())
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    # Analytics and Reporting Methods

    def get_network_utilization_stats(
        self, tenant_id: str, network_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed network utilization statistics.

        Args:
            tenant_id: Tenant identifier
            network_id: Network identifier

        Returns:
            Dictionary with utilization statistics
        """
        network = self.get_network_by_id(tenant_id, network_id)
        if not network:
            raise NetworkNotFoundError(network_id)

        # Count allocations by status
        allocation_counts = (
            self.db.query(
                IPAllocation.allocation_status,
                func.count(IPAllocation.id).label("count"),
            )
            .filter(
                IPAllocation.tenant_id == tenant_id,
                IPAllocation.network_id == network.id,
            )
            .group_by(IPAllocation.allocation_status)
            .all()
        )

        # Count reservations by status
        reservation_counts = (
            self.db.query(
                IPReservation.reservation_status,
                func.count(IPReservation.id).label("count"),
            )
            .filter(
                IPReservation.tenant_id == tenant_id,
                IPReservation.network_id == network.id,
            )
            .group_by(IPReservation.reservation_status)
            .all()
        )

        # Calculate totals
        import ipaddress

        net = ipaddress.ip_network(network.cidr)
        total_addresses = net.num_addresses
        usable_addresses = (
            max(0, net.num_addresses - 2) if net.prefixlen < 30 else net.num_addresses
        )

        allocated_count = sum(
            count
            for status, count in allocation_counts
            if status == AllocationStatus.ALLOCATED
        )
        reserved_count = sum(
            count
            for status, count in reservation_counts
            if status == ReservationStatus.RESERVED
        )

        return {
            "network_id": network_id,
            "cidr": network.cidr,
            "total_addresses": total_addresses,
            "usable_addresses": usable_addresses,
            "allocated_count": allocated_count,
            "reserved_count": reserved_count,
            "available_count": usable_addresses - allocated_count - reserved_count,
            "utilization_percent": (
                round((allocated_count + reserved_count) / usable_addresses * 100, 2)
                if usable_addresses > 0
                else 0
            ),
            "allocation_breakdown": {
                str(status): count for status, count in allocation_counts
            },
            "reservation_breakdown": {
                str(status): count for status, count in reservation_counts
            },
        }

    def get_tenant_summary(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get summary statistics for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Dictionary with tenant summary statistics
        """
        # Network counts
        total_networks = (
            self.db.query(func.count(IPNetwork.id))
            .filter(IPNetwork.tenant_id == tenant_id, IPNetwork.is_active == True)
            .scalar()
        )

        networks_by_type = (
            self.db.query(
                IPNetwork.network_type, func.count(IPNetwork.id).label("count")
            )
            .filter(IPNetwork.tenant_id == tenant_id, IPNetwork.is_active == True)
            .group_by(IPNetwork.network_type)
            .all()
        )

        # Allocation counts
        total_allocations = (
            self.db.query(func.count(IPAllocation.id))
            .filter(IPAllocation.tenant_id == tenant_id)
            .scalar()
        )

        active_allocations = (
            self.db.query(func.count(IPAllocation.id))
            .filter(
                IPAllocation.tenant_id == tenant_id,
                IPAllocation.allocation_status == AllocationStatus.ALLOCATED,
            )
            .scalar()
        )

        # Reservation counts
        total_reservations = (
            self.db.query(func.count(IPReservation.id))
            .filter(IPReservation.tenant_id == tenant_id)
            .scalar()
        )

        active_reservations = (
            self.db.query(func.count(IPReservation.id))
            .filter(
                IPReservation.tenant_id == tenant_id,
                IPReservation.reservation_status == ReservationStatus.RESERVED,
            )
            .scalar()
        )

        return {
            "tenant_id": tenant_id,
            "networks": {
                "total": total_networks,
                "by_type": {
                    str(net_type): count for net_type, count in networks_by_type
                },
            },
            "allocations": {"total": total_allocations, "active": active_allocations},
            "reservations": {
                "total": total_reservations,
                "active": active_reservations,
            },
        }

    # Utility Methods

    def check_ip_conflict(self, tenant_id: str, ip_address: str) -> Optional[str]:
        """
        Check if IP address has any conflicts.

        Args:
            tenant_id: Tenant identifier
            ip_address: IP address to check

        Returns:
            Conflict type string or None if available
        """
        # Check allocations
        allocation = self.get_allocation_by_ip(tenant_id, ip_address)
        if allocation:
            return f"allocated:{allocation.allocation_id}"

        # Check reservations
        reservation = self.get_reservation_by_ip(tenant_id, ip_address)
        if reservation:
            return f"reserved:{reservation.reservation_id}"

        return None

    def cleanup_expired_resources(
        self, tenant_id: str, dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Clean up expired allocations and reservations.

        Args:
            tenant_id: Tenant identifier
            dry_run: If True, only return what would be cleaned up

        Returns:
            Cleanup summary
        """
        expired_allocations = self.get_expired_allocations(tenant_id)
        expired_reservations = self.get_expired_reservations(tenant_id)

        if not dry_run:
            # Update expired allocations
            for allocation in expired_allocations:
                allocation.allocation_status = AllocationStatus.EXPIRED
                allocation.updated_at = datetime.utcnow()

            # Update expired reservations
            for reservation in expired_reservations:
                reservation.reservation_status = ReservationStatus.EXPIRED
                reservation.updated_at = datetime.utcnow()

            self.db.commit()

        return {
            "dry_run": dry_run,
            "expired_allocations": len(expired_allocations),
            "expired_reservations": len(expired_reservations),
            "total_cleaned": len(expired_allocations) + len(expired_reservations),
        }
