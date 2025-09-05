"""
Field Operations Service Layer

Business logic for field operations management, technician dispatch,
work order processing, and performance tracking.

Integrates with existing location services, project management, and notification systems.
"""

from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..api.exception_handlers import standard_exception_handler
from ..core.exceptions import BusinessLogicError, NotFoundError, ValidationError
from ..database import get_db_session
from ..location.core import LocationService
from ..location.models import Coordinates
from .models import (
    PerformanceMetrics,
    SkillLevel,
    Technician,
    TechnicianCreate,
    TechnicianPerformance,
    TechnicianResponse,
    TechnicianStatus,
    TechnicianTimeEntry,
    TechnicianUpdate,
    WorkOrder,
    WorkOrderCreate,
    WorkOrderDetailResponse,
    WorkOrderPriority,
    WorkOrderResponse,
    WorkOrderStatus,
    WorkOrderStatusHistory,
    WorkOrderType,
)


class FieldOperationsService:
    """Core service for field operations management."""

    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or get_db_session()
        self.location_service = LocationService()

    # Technician Management

    @standard_exception_handler
    def create_technician(self, tenant_id: str, technician_data: TechnicianCreate) -> TechnicianResponse:
        """Create a new technician."""
        # Check if employee_id already exists
        existing = (
            self.db.query(Technician)
            .filter(and_(Technician.tenant_id == tenant_id, Technician.employee_id == technician_data.employee_id))
            .first()
        )

        if existing:
            raise ValidationError(f"Employee ID {technician_data.employee_id} already exists")

        # Create technician
        technician = Technician(tenant_id=tenant_id, **technician_data.model_dump(exclude_unset=True))

        self.db.add(technician)
        self.db.commit()
        self.db.refresh(technician)

        return TechnicianResponse.model_validate(technician)

    @standard_exception_handler
    def get_technician(self, tenant_id: str, technician_id: UUID) -> TechnicianResponse:
        """Get technician by ID."""
        technician = (
            self.db.query(Technician)
            .filter(and_(Technician.tenant_id == tenant_id, Technician.id == technician_id))
            .first()
        )

        if not technician:
            raise NotFoundError(f"Technician {technician_id} not found")

        return TechnicianResponse.model_validate(technician)

    @standard_exception_handler
    def update_technician(
        self, tenant_id: str, technician_id: UUID, update_data: TechnicianUpdate
    ) -> TechnicianResponse:
        """Update technician information."""
        technician = (
            self.db.query(Technician)
            .filter(and_(Technician.tenant_id == tenant_id, Technician.id == technician_id))
            .first()
        )

        if not technician:
            raise NotFoundError(f"Technician {technician_id} not found")

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(technician, field, value)

        # Update location timestamp if location changed
        if update_data.current_location:
            technician.last_location_update = datetime.now(timezone.utc)

        technician.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(technician)

        return TechnicianResponse.model_validate(technician)

    @standard_exception_handler
    def get_available_technicians(
        self,
        tenant_id: str,
        work_order_type: Optional[WorkOrderType] = None,
        location: Optional[Coordinates] = None,
        radius_km: float = 50.0,
    ) -> list[TechnicianResponse]:
        """Get available technicians, optionally filtered by skills and location."""
        query = self.db.query(Technician).filter(
            and_(
                Technician.tenant_id == tenant_id,
                Technician.current_status.in_([TechnicianStatus.AVAILABLE, TechnicianStatus.TRAVELING]),
            )
        )

        # Filter by work order type skills if specified
        if work_order_type:
            skill_mapping = {
                WorkOrderType.INSTALLATION: ["installation", "fiber_installation", "copper_installation"],
                WorkOrderType.REPAIR: ["repair", "troubleshooting", "maintenance"],
                WorkOrderType.MAINTENANCE: ["maintenance", "preventive_maintenance"],
                WorkOrderType.UPGRADE: ["upgrade", "equipment_upgrade", "service_upgrade"],
            }

            required_skills = skill_mapping.get(work_order_type, [])
            if required_skills:
                # Find technicians with any of the required skills
                for skill in required_skills:
                    query = query.filter(Technician.skills.any(skill))

        technicians = query.all()

        # Filter by location if specified
        if location and technicians:
            nearby_technicians = []
            for tech in technicians:
                if tech.current_location:
                    tech_coords = Coordinates(
                        latitude=tech.current_location.get("latitude", 0),
                        longitude=tech.current_location.get("longitude", 0),
                    )
                    distance = self.location_service.calculate_distance(location, tech_coords)
                    if distance <= radius_km:
                        nearby_technicians.append(tech)
            technicians = nearby_technicians

        return [TechnicianResponse.model_validate(tech) for tech in technicians]

    # Work Order Management

    @standard_exception_handler
    def create_work_order(self, tenant_id: str, work_order_data: WorkOrderCreate) -> WorkOrderResponse:
        """Create a new work order."""
        # Generate work order number
        work_order_number = self._generate_work_order_number(tenant_id)

        work_order = WorkOrder(
            tenant_id=tenant_id, work_order_number=work_order_number, **work_order_data.model_dump(exclude_unset=True)
        )

        self.db.add(work_order)
        self.db.commit()
        self.db.refresh(work_order)

        # Create initial status history entry
        self._create_status_history(work_order, None, WorkOrderStatus.DRAFT, "Work order created")

        return WorkOrderResponse.model_validate(work_order)

    @standard_exception_handler
    def assign_technician(
        self, tenant_id: str, work_order_id: UUID, technician_id: UUID, assigned_by: str
    ) -> WorkOrderResponse:
        """Assign a technician to a work order."""
        # Get work order
        work_order = (
            self.db.query(WorkOrder)
            .filter(and_(WorkOrder.tenant_id == tenant_id, WorkOrder.id == work_order_id))
            .first()
        )

        if not work_order:
            raise NotFoundError(f"Work order {work_order_id} not found")

        # Get technician
        technician = (
            self.db.query(Technician)
            .filter(and_(Technician.tenant_id == tenant_id, Technician.id == technician_id))
            .first()
        )

        if not technician:
            raise NotFoundError(f"Technician {technician_id} not found")

        # Check technician availability
        if not technician.is_available:
            raise BusinessLogicError(f"Technician {technician.full_name} is not available")

        # Assign technician
        old_status = work_order.status
        work_order.technician_id = technician_id
        work_order.assigned_at = datetime.now(timezone.utc)
        work_order.assigned_by = assigned_by
        work_order.status = WorkOrderStatus.SCHEDULED

        self.db.commit()

        # Create status history
        self._create_status_history(
            work_order, old_status, WorkOrderStatus.SCHEDULED, f"Assigned to {technician.full_name}"
        )

        return WorkOrderResponse.model_validate(work_order)

    @standard_exception_handler
    def update_work_order_status(
        self,
        tenant_id: str,
        work_order_id: UUID,
        new_status: WorkOrderStatus,
        notes: Optional[str] = None,
        updated_by: Optional[str] = None,
        location: Optional[dict[str, float]] = None,
    ) -> WorkOrderResponse:
        """Update work order status with tracking."""
        work_order = (
            self.db.query(WorkOrder)
            .filter(and_(WorkOrder.tenant_id == tenant_id, WorkOrder.id == work_order_id))
            .first()
        )

        if not work_order:
            raise NotFoundError(f"Work order {work_order_id} not found")

        old_status = work_order.status

        # Update status and related fields
        work_order.status = new_status
        work_order.updated_by = updated_by

        # Handle status-specific logic
        if new_status == WorkOrderStatus.IN_PROGRESS and not work_order.actual_start_time:
            work_order.actual_start_time = datetime.now(timezone.utc)
        elif new_status == WorkOrderStatus.ON_SITE and not work_order.on_site_arrival_time:
            work_order.on_site_arrival_time = datetime.now(timezone.utc)
        elif new_status == WorkOrderStatus.COMPLETED:
            if not work_order.actual_end_time:
                work_order.actual_end_time = datetime.now(timezone.utc)
            work_order.progress_percentage = 100

            # Update technician job count
            if work_order.technician:
                work_order.technician.jobs_completed_today += 1
                work_order.technician.jobs_completed_week += 1
                work_order.technician.jobs_completed_month += 1

        self.db.commit()

        # Create status history
        self._create_status_history(work_order, old_status, new_status, notes, location)

        return WorkOrderResponse.model_validate(work_order)

    @standard_exception_handler
    def get_work_order_detail(self, tenant_id: str, work_order_id: UUID) -> WorkOrderDetailResponse:
        """Get detailed work order information."""
        work_order = (
            self.db.query(WorkOrder)
            .filter(and_(WorkOrder.tenant_id == tenant_id, WorkOrder.id == work_order_id))
            .first()
        )

        if not work_order:
            raise NotFoundError(f"Work order {work_order_id} not found")

        return WorkOrderDetailResponse.model_validate(work_order)

    @standard_exception_handler
    def get_technician_work_orders(
        self,
        tenant_id: str,
        technician_id: UUID,
        status_filter: Optional[list[WorkOrderStatus]] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[WorkOrderResponse]:
        """Get work orders for a specific technician."""
        query = self.db.query(WorkOrder).filter(
            and_(WorkOrder.tenant_id == tenant_id, WorkOrder.technician_id == technician_id)
        )

        if status_filter:
            query = query.filter(WorkOrder.status.in_(status_filter))

        if date_from:
            query = query.filter(WorkOrder.scheduled_date >= date_from)

        if date_to:
            query = query.filter(WorkOrder.scheduled_date <= date_to)

        work_orders = query.order_by(WorkOrder.scheduled_date, WorkOrder.scheduled_time_start).all()

        return [WorkOrderResponse.model_validate(wo) for wo in work_orders]

    # Smart Dispatch System

    @standard_exception_handler
    def intelligent_dispatch(self, tenant_id: str, work_order_id: UUID) -> TechnicianResponse:
        """Intelligently assign the best technician for a work order."""
        work_order = (
            self.db.query(WorkOrder)
            .filter(and_(WorkOrder.tenant_id == tenant_id, WorkOrder.id == work_order_id))
            .first()
        )

        if not work_order:
            raise NotFoundError(f"Work order {work_order_id} not found")

        # Get work order location
        work_location = None
        if work_order.service_coordinates:
            work_location = Coordinates(
                latitude=work_order.service_coordinates["latitude"],
                longitude=work_order.service_coordinates["longitude"],
            )

        # Get available technicians
        available_techs = self.get_available_technicians(
            tenant_id=tenant_id, work_order_type=work_order.work_order_type, location=work_location, radius_km=100.0
        )

        if not available_techs:
            raise BusinessLogicError("No available technicians found for this work order")

        # Score technicians based on multiple factors
        best_technician = self._score_technicians_for_work_order(work_order, available_techs, work_location)

        # Assign the best technician
        self.assign_technician(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            technician_id=best_technician.id,
            assigned_by="SYSTEM_AUTO_DISPATCH",
        )

        return best_technician

    def _score_technicians_for_work_order(
        self, work_order: WorkOrder, technicians: list[TechnicianResponse], work_location: Optional[Coordinates]
    ) -> TechnicianResponse:
        """Score technicians for work order assignment."""
        scored_technicians = []

        for tech in technicians:
            score = 0

            # Distance factor (closer is better) - 30% weight
            if work_location and tech.current_location:
                tech_coords = Coordinates(
                    latitude=tech.current_location["latitude"], longitude=tech.current_location["longitude"]
                )
                distance = self.location_service.calculate_distance(work_location, tech_coords)
                distance_score = max(0, 100 - (distance * 2))  # Lose 2 points per km
                score += distance_score * 0.3

            # Workload factor (less busy is better) - 25% weight
            workload_score = 100 - tech.current_workload
            score += workload_score * 0.25

            # Skill level factor - 20% weight
            skill_scores = {
                SkillLevel.EXPERT: 100,
                SkillLevel.SPECIALIST: 95,
                SkillLevel.SENIOR: 80,
                SkillLevel.INTERMEDIATE: 60,
                SkillLevel.JUNIOR: 40,
                SkillLevel.TRAINEE: 20,
            }
            skill_score = skill_scores.get(tech.skill_level, 40)
            score += skill_score * 0.20

            # Performance factor - 15% weight
            performance_score = tech.completion_rate * 100
            score += performance_score * 0.15

            # Customer rating factor - 10% weight
            rating_score = (tech.average_job_rating or 4.0) * 20  # Convert 5-star to 100 scale
            score += rating_score * 0.10

            scored_technicians.append((tech, score))

        # Sort by score and return the best technician
        scored_technicians.sort(key=lambda x: x[1], reverse=True)
        return scored_technicians[0][0]

    # Performance Analytics

    @standard_exception_handler
    def calculate_technician_performance(
        self, tenant_id: str, technician_id: UUID, period_start: date, period_end: date
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics for a technician."""
        # Get work orders in period
        work_orders = (
            self.db.query(WorkOrder)
            .filter(
                and_(
                    WorkOrder.tenant_id == tenant_id,
                    WorkOrder.technician_id == technician_id,
                    WorkOrder.scheduled_date >= period_start,
                    WorkOrder.scheduled_date <= period_end,
                )
            )
            .all()
        )

        # Calculate metrics
        jobs_assigned = len(work_orders)
        jobs_completed = len([wo for wo in work_orders if wo.status == WorkOrderStatus.COMPLETED])
        jobs_cancelled = len([wo for wo in work_orders if wo.status == WorkOrderStatus.CANCELLED])

        completion_rate = (jobs_completed / jobs_assigned * 100) if jobs_assigned > 0 else 0

        # Time metrics
        time_entries = (
            self.db.query(TechnicianTimeEntry)
            .filter(
                and_(
                    TechnicianTimeEntry.tenant_id == tenant_id,
                    TechnicianTimeEntry.technician_id == technician_id,
                    TechnicianTimeEntry.start_time >= datetime.combine(period_start, datetime.min.time()),
                    TechnicianTimeEntry.start_time <= datetime.combine(period_end, datetime.max.time()),
                )
            )
            .all()
        )

        total_work_hours = sum(entry.duration_minutes or 0 for entry in time_entries) / 60
        billable_hours = sum(entry.duration_minutes or 0 for entry in time_entries if entry.billable) / 60

        # Quality metrics
        completed_with_rating = [
            wo for wo in work_orders if wo.status == WorkOrderStatus.COMPLETED and wo.customer_satisfaction_rating
        ]
        average_customer_rating = None
        if completed_with_rating:
            average_customer_rating = sum(wo.customer_satisfaction_rating for wo in completed_with_rating) / len(
                completed_with_rating
            )

        # SLA metrics
        sla_met = len([wo for wo in work_orders if wo.sla_met is True])
        sla_missed = len([wo for wo in work_orders if wo.sla_met is False])

        # Calculate overall performance score
        overall_score = self._calculate_performance_score(
            completion_rate, average_customer_rating, sla_met, sla_missed, jobs_assigned
        )

        # Create or update performance record
        performance = TechnicianPerformance(
            tenant_id=tenant_id,
            technician_id=technician_id,
            period_start=period_start,
            period_end=period_end,
            period_type="custom",
            jobs_assigned=jobs_assigned,
            jobs_completed=jobs_completed,
            jobs_cancelled=jobs_cancelled,
            completion_rate=completion_rate,
            total_work_hours=total_work_hours,
            billable_hours=billable_hours,
            average_customer_rating=average_customer_rating,
            sla_met_count=sla_met,
            sla_missed_count=sla_missed,
            overall_performance_score=overall_score,
        )

        self.db.add(performance)
        self.db.commit()

        return PerformanceMetrics.model_validate(performance)

    def _calculate_performance_score(
        self, completion_rate: float, avg_rating: Optional[float], sla_met: int, sla_missed: int, total_jobs: int
    ) -> int:
        """Calculate overall performance score (0-100)."""
        if total_jobs == 0:
            return 0

        score = 0

        # Completion rate (40% weight)
        score += completion_rate * 0.4

        # Customer satisfaction (30% weight)
        if avg_rating:
            rating_score = (avg_rating / 5.0) * 100
            score += rating_score * 0.3
        else:
            score += 70 * 0.3  # Default if no ratings

        # SLA performance (30% weight)
        sla_total = sla_met + sla_missed
        if sla_total > 0:
            sla_score = (sla_met / sla_total) * 100
            score += sla_score * 0.3
        else:
            score += 80 * 0.3  # Default if no SLA data

        return min(100, max(0, int(score)))

    # Route Optimization

    @standard_exception_handler
    def optimize_technician_route(
        self, tenant_id: str, technician_id: UUID, target_date: date
    ) -> list[WorkOrderResponse]:
        """Optimize work order sequence for a technician's day."""
        # Get technician's work orders for the day
        work_orders = (
            self.db.query(WorkOrder)
            .filter(
                and_(
                    WorkOrder.tenant_id == tenant_id,
                    WorkOrder.technician_id == technician_id,
                    WorkOrder.scheduled_date == target_date,
                    WorkOrder.status.in_([WorkOrderStatus.SCHEDULED, WorkOrderStatus.DISPATCHED]),
                )
            )
            .all()
        )

        if len(work_orders) <= 1:
            return [WorkOrderResponse.model_validate(wo) for wo in work_orders]

        # Get technician's starting location
        technician = self.db.query(Technician).filter(Technician.id == technician_id).first()

        if not technician or not technician.current_location:
            # Return orders sorted by priority if no location data
            work_orders.sort(key=lambda wo: (wo.priority.value, wo.scheduled_time_start or datetime.min.time()))
            return [WorkOrderResponse.model_validate(wo) for wo in work_orders]

        # Use simple nearest-neighbor optimization for now
        # In production, integrate with advanced routing algorithms
        optimized_orders = self._optimize_route_nearest_neighbor(work_orders, technician.current_location)

        return [WorkOrderResponse.model_validate(wo) for wo in optimized_orders]

    def _optimize_route_nearest_neighbor(
        self, work_orders: list[WorkOrder], start_location: dict[str, float]
    ) -> list[WorkOrder]:
        """Simple nearest-neighbor route optimization."""
        if not work_orders:
            return []

        current_location = Coordinates(latitude=start_location["latitude"], longitude=start_location["longitude"])

        unvisited = work_orders.copy()
        route = []

        while unvisited:
            nearest_order = None
            min_distance = float("inf")

            for order in unvisited:
                if order.service_coordinates:
                    order_location = Coordinates(
                        latitude=order.service_coordinates["latitude"], longitude=order.service_coordinates["longitude"]
                    )
                    distance = self.location_service.calculate_distance(current_location, order_location)

                    # Factor in priority (higher priority reduces effective distance)
                    priority_multiplier = {
                        WorkOrderPriority.EMERGENCY: 0.1,
                        WorkOrderPriority.URGENT: 0.3,
                        WorkOrderPriority.HIGH: 0.7,
                        WorkOrderPriority.NORMAL: 1.0,
                        WorkOrderPriority.LOW: 1.3,
                    }

                    effective_distance = distance * priority_multiplier.get(order.priority, 1.0)

                    if effective_distance < min_distance:
                        min_distance = effective_distance
                        nearest_order = order

            if nearest_order:
                route.append(nearest_order)
                unvisited.remove(nearest_order)

                if nearest_order.service_coordinates:
                    current_location = Coordinates(
                        latitude=nearest_order.service_coordinates["latitude"],
                        longitude=nearest_order.service_coordinates["longitude"],
                    )

        return route

    # Utility Methods

    def _generate_work_order_number(self, tenant_id: str) -> str:
        """Generate unique work order number."""
        today = date.today()
        date_prefix = today.strftime("%Y%m%d")

        # Count existing work orders for today
        count = (
            self.db.query(WorkOrder)
            .filter(and_(WorkOrder.tenant_id == tenant_id, WorkOrder.work_order_number.like(f"{date_prefix}%")))
            .count()
        )

        return f"{date_prefix}-{count + 1:04d}"

    def _create_status_history(
        self,
        work_order: WorkOrder,
        from_status: Optional[WorkOrderStatus],
        to_status: WorkOrderStatus,
        notes: Optional[str] = None,
        location: Optional[dict[str, float]] = None,
    ):
        """Create work order status history entry."""
        history = WorkOrderStatusHistory(
            tenant_id=work_order.tenant_id,
            work_order_id=work_order.id,
            from_status=from_status,
            to_status=to_status,
            notes=notes,
            changed_by=work_order.updated_by or "SYSTEM",
            location=location,
        )

        self.db.add(history)
        self.db.commit()


class DispatchService:
    """Advanced dispatch and scheduling service."""

    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or get_db_session()
        self.field_service = FieldOperationsService(db_session)

    @standard_exception_handler
    def emergency_dispatch(self, tenant_id: str, work_order_id: UUID) -> TechnicianResponse:
        """Emergency dispatch - find nearest available technician immediately."""
        work_order = (
            self.db.query(WorkOrder)
            .filter(and_(WorkOrder.tenant_id == tenant_id, WorkOrder.id == work_order_id))
            .first()
        )

        if not work_order:
            raise NotFoundError(f"Work order {work_order_id} not found")

        # Update priority to emergency
        work_order.priority = WorkOrderPriority.EMERGENCY

        # Get work order location
        work_location = None
        if work_order.service_coordinates:
            work_location = Coordinates(
                latitude=work_order.service_coordinates["latitude"],
                longitude=work_order.service_coordinates["longitude"],
            )

        # Find nearest available technician within 150km
        available_techs = self.field_service.get_available_technicians(
            tenant_id=tenant_id, location=work_location, radius_km=150.0
        )

        if not available_techs:
            raise BusinessLogicError("No technicians available for emergency dispatch")

        # Select closest technician
        best_tech = available_techs[0]  # Already sorted by distance in get_available_technicians

        # Assign immediately
        self.field_service.assign_technician(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            technician_id=best_tech.id,
            assigned_by="EMERGENCY_DISPATCH",
        )

        # Update status to dispatched
        self.field_service.update_work_order_status(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            new_status=WorkOrderStatus.DISPATCHED,
            notes="Emergency dispatch - immediate assignment",
            updated_by="EMERGENCY_DISPATCH",
        )

        return best_tech
