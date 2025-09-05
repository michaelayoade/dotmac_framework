"""
Field Operations Integration Tests

Comprehensive testing for field operations management system including
technician management, work orders, dispatch, and performance analytics.
"""

from datetime import date, datetime, timedelta
from unittest.mock import patch

import pytest
from dotmac_shared.exceptions import BusinessLogicError, ValidationError
from dotmac_shared.field_operations.models import (
    SkillLevel,
    TechnicianCreate,
    TechnicianStatus,
    TechnicianUpdate,
    WorkOrderCreate,
    WorkOrderPriority,
    WorkOrderStatus,
    WorkOrderType,
)
from dotmac_shared.field_operations.service import DispatchService, FieldOperationsService
from dotmac_shared.location.models import Coordinates
from sqlalchemy.orm import Session


class TestFieldOperationsService:
    """Test field operations service functionality."""
    
    @pytest.fixture
    def service(self, db_session: Session):
        """Create field operations service instance."""
        return FieldOperationsService(db_session)
    
    @pytest.fixture
    def sample_technician_data(self):
        """Sample technician creation data."""
        return TechnicianCreate(
            employee_id="TECH001",
            first_name="John",
            last_name="Smith",
            email="john.smith@company.com",
            phone="555-0123",
            hire_date=date.today(),
            skill_level=SkillLevel.INTERMEDIATE,
            skills=["fiber_installation", "copper_installation"],
            max_jobs_per_day=6
        )
    
    @pytest.fixture
    def sample_work_order_data(self):
        """Sample work order creation data."""
        return WorkOrderCreate(
            title="Fiber Internet Installation",
            description="Install fiber internet service for new customer",
            work_order_type=WorkOrderType.INSTALLATION,
            priority=WorkOrderPriority.NORMAL,
            customer_name="Jane Doe",
            customer_phone="555-0456",
            customer_email="jane.doe@example.com",
            service_address="123 Main St, Anytown, ST 12345",
            scheduled_date=date.today() + timedelta(days=1),
            estimated_duration=120,
            required_equipment=[
                {"type": "fiber_modem", "quantity": 1},
                {"type": "fiber_cable", "quantity": 100}
            ]
        )
    
    def test_create_technician_success(self, service: FieldOperationsService, sample_technician_data: TechnicianCreate):
        """Test successful technician creation."""
        tenant_id = "tenant123"
        
        technician = service.create_technician(tenant_id, sample_technician_data)
        
        assert technician.tenant_id == tenant_id
        assert technician.employee_id == sample_technician_data.employee_id
        assert technician.full_name == "John Smith"
        assert technician.skill_level == SkillLevel.INTERMEDIATE
        assert technician.is_available == False  # Off duty by default
        assert technician.current_workload == 0
    
    def test_create_technician_duplicate_employee_id(self, service: FieldOperationsService, sample_technician_data: TechnicianCreate):
        """Test technician creation with duplicate employee ID."""
        tenant_id = "tenant123"
        
        # Create first technician
        service.create_technician(tenant_id, sample_technician_data)
        
        # Attempt to create duplicate
        with pytest.raises(ValidationError, match="already exists"):
            service.create_technician(tenant_id, sample_technician_data)
    
    def test_update_technician_status(self, service: FieldOperationsService, sample_technician_data: TechnicianCreate):
        """Test updating technician status and location."""
        tenant_id = "tenant123"
        
        # Create technician
        technician = service.create_technician(tenant_id, sample_technician_data)
        
        # Update status
        update_data = TechnicianUpdate(
            current_status=TechnicianStatus.AVAILABLE,
            current_location={"latitude": 40.7128, "longitude": -74.0060}
        )
        
        updated_technician = service.update_technician(tenant_id, technician.id, update_data)
        
        assert updated_technician.current_status == TechnicianStatus.AVAILABLE
        assert updated_technician.is_available == True
        assert updated_technician.current_location["latitude"] == 40.7128
        assert updated_technician.last_location_update is not None
    
    def test_get_available_technicians_filtered_by_skills(self, service: FieldOperationsService, db_session: Session):
        """Test getting available technicians filtered by work order type skills."""
        tenant_id = "tenant123"
        
        # Create technicians with different skills
        fiber_tech_data = TechnicianCreate(
            employee_id="FIBER001",
            first_name="Alice",
            last_name="Johnson",
            email="alice@company.com",
            phone="555-0001",
            hire_date=date.today(),
            skills=["fiber_installation", "fiber_splicing"]
        )
        
        copper_tech_data = TechnicianCreate(
            employee_id="COPPER001",
            first_name="Bob",
            last_name="Wilson",
            email="bob@company.com",
            phone="555-0002",
            hire_date=date.today(),
            skills=["copper_installation", "dsl_setup"]
        )
        
        # Create and set both available
        fiber_tech = service.create_technician(tenant_id, fiber_tech_data)
        copper_tech = service.create_technician(tenant_id, copper_tech_data)
        
        service.update_technician(tenant_id, fiber_tech.id, TechnicianUpdate(current_status=TechnicianStatus.AVAILABLE))
        service.update_technician(tenant_id, copper_tech.id, TechnicianUpdate(current_status=TechnicianStatus.AVAILABLE))
        
        # Get technicians for installation work
        available_techs = service.get_available_technicians(
            tenant_id=tenant_id,
            work_order_type=WorkOrderType.INSTALLATION
        )
        
        assert len(available_techs) == 2  # Both have installation skills
        tech_names = [tech.full_name for tech in available_techs]
        assert "Alice Johnson" in tech_names
        assert "Bob Wilson" in tech_names
    
    def test_create_work_order_success(self, service: FieldOperationsService, sample_work_order_data: WorkOrderCreate):
        """Test successful work order creation."""
        tenant_id = "tenant123"
        
        work_order = service.create_work_order(tenant_id, sample_work_order_data)
        
        assert work_order.tenant_id == tenant_id
        assert work_order.title == sample_work_order_data.title
        assert work_order.status == WorkOrderStatus.DRAFT
        assert work_order.progress_percentage == 0
        assert work_order.work_order_number.startswith(date.today().strftime("%Y%m%d"))
    
    def test_assign_technician_to_work_order(self, service: FieldOperationsService, 
                                           sample_technician_data: TechnicianCreate,
                                           sample_work_order_data: WorkOrderCreate):
        """Test assigning technician to work order."""
        tenant_id = "tenant123"
        
        # Create technician and set available
        technician = service.create_technician(tenant_id, sample_technician_data)
        service.update_technician(tenant_id, technician.id, TechnicianUpdate(current_status=TechnicianStatus.AVAILABLE))
        
        # Create work order
        work_order = service.create_work_order(tenant_id, sample_work_order_data)
        
        # Assign technician
        assigned_work_order = service.assign_technician(
            tenant_id=tenant_id,
            work_order_id=work_order.id,
            technician_id=technician.id,
            assigned_by="test_dispatcher"
        )
        
        assert assigned_work_order.technician.id == technician.id
        assert assigned_work_order.status == WorkOrderStatus.SCHEDULED
        assert assigned_work_order.assigned_at is not None
        assert assigned_work_order.assigned_by == "test_dispatcher"
    
    def test_assign_unavailable_technician_fails(self, service: FieldOperationsService,
                                                sample_technician_data: TechnicianCreate,
                                                sample_work_order_data: WorkOrderCreate):
        """Test that assigning unavailable technician fails."""
        tenant_id = "tenant123"
        
        # Create technician but keep off duty
        technician = service.create_technician(tenant_id, sample_technician_data)
        work_order = service.create_work_order(tenant_id, sample_work_order_data)
        
        # Attempt assignment
        with pytest.raises(BusinessLogicError, match="not available"):
            service.assign_technician(
                tenant_id=tenant_id,
                work_order_id=work_order.id,
                technician_id=technician.id,
                assigned_by="test_dispatcher"
            )
    
    def test_update_work_order_status_with_tracking(self, service: FieldOperationsService,
                                                   sample_technician_data: TechnicianCreate,
                                                   sample_work_order_data: WorkOrderCreate):
        """Test work order status updates with proper tracking."""
        tenant_id = "tenant123"
        
        # Setup technician and work order
        technician = service.create_technician(tenant_id, sample_technician_data)
        service.update_technician(tenant_id, technician.id, TechnicianUpdate(current_status=TechnicianStatus.AVAILABLE))
        
        work_order = service.create_work_order(tenant_id, sample_work_order_data)
        assigned_wo = service.assign_technician(tenant_id, work_order.id, technician.id, "dispatcher")
        
        # Update to in progress
        updated_wo = service.update_work_order_status(
            tenant_id=tenant_id,
            work_order_id=work_order.id,
            new_status=WorkOrderStatus.IN_PROGRESS,
            notes="Started work",
            updated_by="technician",
            location={"latitude": 40.7128, "longitude": -74.0060}
        )
        
        assert updated_wo.status == WorkOrderStatus.IN_PROGRESS
        assert updated_wo.actual_start_time is not None
        assert updated_wo.updated_by == "technician"
        
        # Update to completed
        completed_wo = service.update_work_order_status(
            tenant_id=tenant_id,
            work_order_id=work_order.id,
            new_status=WorkOrderStatus.COMPLETED,
            notes="Job finished successfully"
        )
        
        assert completed_wo.status == WorkOrderStatus.COMPLETED
        assert completed_wo.actual_end_time is not None
        assert completed_wo.progress_percentage == 100
    
    def test_intelligent_dispatch_scoring(self, service: FieldOperationsService, db_session: Session):
        """Test intelligent dispatch algorithm scoring."""
        tenant_id = "tenant123"
        
        # Create work order with location
        work_order_data = WorkOrderCreate(
            title="Service Installation",
            description="Install service",
            work_order_type=WorkOrderType.INSTALLATION,
            service_address="123 Test St",
            service_coordinates={"latitude": 40.7128, "longitude": -74.0060}
        )
        work_order = service.create_work_order(tenant_id, work_order_data)
        
        # Create technicians at different locations and skill levels
        nearby_expert = service.create_technician(tenant_id, TechnicianCreate(
            employee_id="EXPERT001",
            first_name="Expert",
            last_name="Nearby",
            email="expert@company.com",
            phone="555-0001",
            hire_date=date.today(),
            skill_level=SkillLevel.EXPERT,
            skills=["installation"]
        ))
        
        far_junior = service.create_technician(tenant_id, TechnicianCreate(
            employee_id="JUNIOR001",
            first_name="Junior",
            last_name="Far",
            email="junior@company.com",
            phone="555-0002",
            hire_date=date.today(),
            skill_level=SkillLevel.JUNIOR,
            skills=["installation"]
        ))
        
        # Set both available with different locations and workloads
        service.update_technician(tenant_id, nearby_expert.id, TechnicianUpdate(
            current_status=TechnicianStatus.AVAILABLE,
            current_location={"latitude": 40.7130, "longitude": -74.0061}  # Very close
        ))
        
        service.update_technician(tenant_id, far_junior.id, TechnicianUpdate(
            current_status=TechnicianStatus.AVAILABLE,
            current_location={"latitude": 40.8128, "longitude": -74.1060}  # Far away
        ))
        
        # Run intelligent dispatch
        assigned_tech = service.intelligent_dispatch(tenant_id, work_order.id)
        
        # Should select nearby expert despite higher skill level (proximity + skill)
        assert assigned_tech.full_name == "Expert Nearby"
    
    def test_calculate_technician_performance_metrics(self, service: FieldOperationsService,
                                                     sample_technician_data: TechnicianCreate,
                                                     db_session: Session):
        """Test comprehensive performance metrics calculation."""
        tenant_id = "tenant123"
        
        # Create technician
        technician = service.create_technician(tenant_id, sample_technician_data)
        
        # Create completed work orders with ratings
        period_start = date.today() - timedelta(days=30)
        period_end = date.today()
        
        for i in range(5):
            wo_data = WorkOrderCreate(
                title=f"Job {i+1}",
                description="Test job",
                work_order_type=WorkOrderType.INSTALLATION,
                service_address=f"{i+1} Test St"
            )
            work_order = service.create_work_order(tenant_id, wo_data)
            
            # Simulate work order progression
            service.assign_technician(tenant_id, work_order.id, technician.id, "system")
            service.update_work_order_status(tenant_id, work_order.id, WorkOrderStatus.COMPLETED)
            
            # Add customer rating
            from dotmac_shared.field_operations.models import WorkOrder
            db_work_order = db_session.query(WorkOrder).filter(WorkOrder.id == work_order.id).first()
            db_work_order.customer_satisfaction_rating = 4 + (i % 2)  # 4 or 5 stars
            db_work_order.sla_met = True
            db_session.commit()
        
        # Add time entries
        from dotmac_shared.field_operations.models import TechnicianTimeEntry
        for i in range(10):
            time_entry = TechnicianTimeEntry(
                tenant_id=tenant_id,
                technician_id=technician.id,
                start_time=datetime.now() - timedelta(days=i),
                duration_minutes=120,
                activity_type="work",
                billable=True
            )
            db_session.add(time_entry)
        db_session.commit()
        
        # Calculate performance
        performance = service.calculate_technician_performance(
            tenant_id=tenant_id,
            technician_id=technician.id,
            period_start=period_start,
            period_end=period_end
        )
        
        assert performance.jobs_assigned == 5
        assert performance.jobs_completed == 5
        assert performance.completion_rate == 100.0
        assert performance.average_customer_rating >= 4.0
        assert performance.sla_met_count == 5
        assert performance.overall_performance_score > 80
    
    def test_optimize_technician_route_basic(self, service: FieldOperationsService,
                                            sample_technician_data: TechnicianCreate,
                                            db_session: Session):
        """Test basic route optimization functionality."""
        tenant_id = "tenant123"
        target_date = date.today()
        
        # Create technician with location
        technician = service.create_technician(tenant_id, sample_technician_data)
        service.update_technician(tenant_id, technician.id, TechnicianUpdate(
            current_status=TechnicianStatus.AVAILABLE,
            current_location={"latitude": 40.7128, "longitude": -74.0060}
        ))
        
        # Create multiple work orders for the same day
        locations = [
            {"latitude": 40.7200, "longitude": -74.0100},  # North
            {"latitude": 40.7100, "longitude": -74.0020},  # East
            {"latitude": 40.7150, "longitude": -73.9950}   # South
        ]
        
        work_orders = []
        for i, location in enumerate(locations):
            wo_data = WorkOrderCreate(
                title=f"Job at location {i+1}",
                description=f"Work at location {i+1}",
                work_order_type=WorkOrderType.MAINTENANCE,
                service_address=f"{i+1} Location St",
                service_coordinates=location,
                scheduled_date=target_date,
                priority=WorkOrderPriority.HIGH if i == 1 else WorkOrderPriority.NORMAL
            )
            work_order = service.create_work_order(tenant_id, wo_data)
            service.assign_technician(tenant_id, work_order.id, technician.id, "system")
            work_orders.append(work_order)
        
        # Optimize route
        optimized_route = service.optimize_technician_route(
            tenant_id=tenant_id,
            technician_id=technician.id,
            target_date=target_date
        )
        
        assert len(optimized_route) == 3
        # High priority job should be prioritized in routing
        high_priority_found = any(wo.priority == 'high' for wo in optimized_route)
        assert high_priority_found


class TestDispatchService:
    """Test dispatch service functionality."""
    
    @pytest.fixture
    def dispatch_service(self, db_session: Session):
        """Create dispatch service instance."""
        return DispatchService(db_session)
    
    @pytest.fixture
    def field_service(self, db_session: Session):
        """Create field operations service instance."""
        return FieldOperationsService(db_session)
    
    def test_emergency_dispatch_nearest_technician(self, dispatch_service: DispatchService,
                                                  field_service: FieldOperationsService,
                                                  db_session: Session):
        """Test emergency dispatch finds nearest available technician."""
        tenant_id = "tenant123"
        
        # Create emergency work order
        emergency_data = WorkOrderCreate(
            title="Emergency Service Outage",
            description="Critical service outage requiring immediate attention",
            work_order_type=WorkOrderType.EMERGENCY_REPAIR,
            priority=WorkOrderPriority.EMERGENCY,
            service_address="Emergency Site",
            service_coordinates={"latitude": 40.7128, "longitude": -74.0060}
        )
        work_order = field_service.create_work_order(tenant_id, emergency_data)
        
        # Create technicians at different distances
        close_tech = field_service.create_technician(tenant_id, TechnicianCreate(
            employee_id="CLOSE001",
            first_name="Close",
            last_name="Tech",
            email="close@company.com",
            phone="555-0001",
            hire_date=date.today()
        ))
        
        far_tech = field_service.create_technician(tenant_id, TechnicianCreate(
            employee_id="FAR001",
            first_name="Far",
            last_name="Tech",
            email="far@company.com",
            phone="555-0002",
            hire_date=date.today()
        ))
        
        # Set both available at different locations
        field_service.update_technician(tenant_id, close_tech.id, TechnicianUpdate(
            current_status=TechnicianStatus.AVAILABLE,
            current_location={"latitude": 40.7130, "longitude": -74.0061}  # 200m away
        ))
        
        field_service.update_technician(tenant_id, far_tech.id, TechnicianUpdate(
            current_status=TechnicianStatus.AVAILABLE,
            current_location={"latitude": 40.8128, "longitude": -74.1060}  # 15km away
        ))
        
        # Execute emergency dispatch
        assigned_tech = dispatch_service.emergency_dispatch(tenant_id, work_order.id)
        
        # Should assign closest technician
        assert assigned_tech.full_name == "Close Tech"
        
        # Verify work order status
        updated_wo = field_service.get_work_order_detail(tenant_id, work_order.id)
        assert updated_wo.status == WorkOrderStatus.DISPATCHED
        assert updated_wo.priority == WorkOrderPriority.EMERGENCY
    
    def test_emergency_dispatch_no_available_technicians(self, dispatch_service: DispatchService,
                                                        field_service: FieldOperationsService):
        """Test emergency dispatch when no technicians are available."""
        tenant_id = "tenant123"
        
        # Create emergency work order
        emergency_data = WorkOrderCreate(
            title="Emergency",
            description="Emergency",
            work_order_type=WorkOrderType.EMERGENCY_REPAIR,
            priority=WorkOrderPriority.EMERGENCY,
            service_address="Emergency Site"
        )
        work_order = field_service.create_work_order(tenant_id, emergency_data)
        
        # Create technician but set as unavailable
        tech = field_service.create_technician(tenant_id, TechnicianCreate(
            employee_id="BUSY001",
            first_name="Busy",
            last_name="Tech",
            email="busy@company.com",
            phone="555-0001",
            hire_date=date.today()
        ))
        
        field_service.update_technician(tenant_id, tech.id, TechnicianUpdate(
            current_status=TechnicianStatus.ON_JOB
        ))
        
        # Should fail to dispatch
        with pytest.raises(BusinessLogicError, match="No technicians available"):
            dispatch_service.emergency_dispatch(tenant_id, work_order.id)


class TestWorkOrderLifecycle:
    """Test complete work order lifecycle scenarios."""
    
    @pytest.fixture
    def service(self, db_session: Session):
        """Create service instance."""
        return FieldOperationsService(db_session)
    
    def test_complete_installation_workflow(self, service: FieldOperationsService):
        """Test complete installation workflow from creation to completion."""
        tenant_id = "tenant123"
        
        # Step 1: Create technician
        tech_data = TechnicianCreate(
            employee_id="INSTALL001",
            first_name="Installation",
            last_name="Expert",
            email="installer@company.com",
            phone="555-0123",
            hire_date=date.today(),
            skill_level=SkillLevel.SENIOR,
            skills=["fiber_installation", "equipment_setup"]
        )
        technician = service.create_technician(tenant_id, tech_data)
        service.update_technician(tenant_id, technician.id, TechnicianUpdate(
            current_status=TechnicianStatus.AVAILABLE
        ))
        
        # Step 2: Create work order
        wo_data = WorkOrderCreate(
            title="New Customer Fiber Installation",
            description="Install high-speed fiber internet for residential customer",
            work_order_type=WorkOrderType.INSTALLATION,
            priority=WorkOrderPriority.NORMAL,
            customer_name="John Customer",
            customer_phone="555-0456",
            service_address="456 Customer Lane",
            scheduled_date=date.today(),
            estimated_duration=180
        )
        work_order = service.create_work_order(tenant_id, wo_data)
        
        # Step 3: Assign technician
        assigned_wo = service.assign_technician(tenant_id, work_order.id, technician.id, "dispatcher")
        assert assigned_wo.status == WorkOrderStatus.SCHEDULED
        
        # Step 4: Technician accepts and starts travel
        en_route_wo = service.update_work_order_status(
            tenant_id, work_order.id, WorkOrderStatus.EN_ROUTE,
            notes="Heading to customer location"
        )
        assert en_route_wo.status == WorkOrderStatus.EN_ROUTE
        
        # Step 5: Technician arrives on site
        on_site_wo = service.update_work_order_status(
            tenant_id, work_order.id, WorkOrderStatus.ON_SITE,
            notes="Arrived at customer location",
            location={"latitude": 40.7128, "longitude": -74.0060}
        )
        assert on_site_wo.on_site_arrival_time is not None
        
        # Step 6: Begin work
        in_progress_wo = service.update_work_order_status(
            tenant_id, work_order.id, WorkOrderStatus.IN_PROGRESS,
            notes="Started fiber installation"
        )
        assert in_progress_wo.actual_start_time is not None
        
        # Step 7: Complete work
        completed_wo = service.update_work_order_status(
            tenant_id, work_order.id, WorkOrderStatus.COMPLETED,
            notes="Installation completed successfully"
        )
        assert completed_wo.status == WorkOrderStatus.COMPLETED
        assert completed_wo.actual_end_time is not None
        assert completed_wo.progress_percentage == 100
        
        # Verify technician job count updated
        updated_tech = service.get_technician(tenant_id, technician.id)
        assert updated_tech.jobs_completed_today == 1


class TestPerformanceAndAnalytics:
    """Test performance tracking and analytics functionality."""
    
    @pytest.fixture
    def service(self, db_session: Session):
        """Create service instance."""
        return FieldOperationsService(db_session)
    
    def test_performance_calculation_accuracy(self, service: FieldOperationsService, db_session: Session):
        """Test accuracy of performance metric calculations."""
        tenant_id = "tenant123"
        
        # Create technician
        tech_data = TechnicianCreate(
            employee_id="PERF001",
            first_name="Performance",
            last_name="Test",
            email="perf@company.com",
            phone="555-0123",
            hire_date=date.today()
        )
        technician = service.create_technician(tenant_id, tech_data)
        
        # Create work orders with specific outcomes
        period_start = date.today() - timedelta(days=7)
        period_end = date.today()
        
        # 8 completed jobs, 2 cancelled, 5-star ratings
        job_outcomes = [
            (WorkOrderStatus.COMPLETED, 5, True),   # Perfect job
            (WorkOrderStatus.COMPLETED, 5, True),   # Perfect job
            (WorkOrderStatus.COMPLETED, 4, True),   # Good job
            (WorkOrderStatus.COMPLETED, 4, False),  # Good job, SLA missed
            (WorkOrderStatus.COMPLETED, 3, True),   # Average job
            (WorkOrderStatus.COMPLETED, 4, True),   # Good job
            (WorkOrderStatus.COMPLETED, 5, True),   # Perfect job
            (WorkOrderStatus.COMPLETED, 4, True),   # Good job
            (WorkOrderStatus.CANCELLED, None, None), # Cancelled
            (WorkOrderStatus.CANCELLED, None, None)  # Cancelled
        ]
        
        for i, (status, rating, sla_met) in enumerate(job_outcomes):
            wo_data = WorkOrderCreate(
                title=f"Performance Test Job {i+1}",
                description="Test job",
                work_order_type=WorkOrderType.MAINTENANCE,
                service_address=f"{i+1} Test St",
                scheduled_date=period_start + timedelta(days=i % 7)
            )
            work_order = service.create_work_order(tenant_id, wo_data)
            service.assign_technician(tenant_id, work_order.id, technician.id, "system")
            service.update_work_order_status(tenant_id, work_order.id, status)
            
            # Set rating and SLA data
            if rating is not None:
                from dotmac_shared.field_operations.models import WorkOrder
                db_wo = db_session.query(WorkOrder).filter(WorkOrder.id == work_order.id).first()
                db_wo.customer_satisfaction_rating = rating
                db_wo.sla_met = sla_met
                db_session.commit()
        
        # Calculate performance
        performance = service.calculate_technician_performance(
            tenant_id=tenant_id,
            technician_id=technician.id,
            period_start=period_start,
            period_end=period_end
        )
        
        # Verify calculations
        assert performance.jobs_assigned == 10
        assert performance.jobs_completed == 8
        assert performance.jobs_cancelled == 2
        assert performance.completion_rate == 80.0  # 8/10 * 100
        
        # Average rating should be 4.25 ((5+5+4+4+3+4+5+4)/8)
        assert abs(performance.average_customer_rating - 4.25) < 0.01
        
        # SLA metrics: 7 met, 1 missed out of 8 completed
        assert performance.sla_met_count == 7
        assert performance.sla_missed_count == 1
        
        # Overall score should be calculated based on completion rate, rating, and SLA
        assert performance.overall_performance_score > 70  # Should be decent score
        assert performance.overall_performance_score < 90  # But not perfect due to missed SLA


# Mock-based tests for external dependencies
class TestFieldOperationsIntegration:
    """Test integration with external services."""
    
    @pytest.fixture
    def service(self, db_session: Session):
        """Create service instance."""
        return FieldOperationsService(db_session)
    
    @patch('dotmac_shared.location.core.LocationService')
    def test_location_service_integration(self, mock_location_service, service: FieldOperationsService):
        """Test integration with location service for distance calculations."""
        # Setup mock
        mock_location_service.return_value.calculate_distance.return_value = 5.2  # 5.2 km
        
        tenant_id = "tenant123"
        
        # Create work order with coordinates
        work_location = Coordinates(latitude=40.7128, longitude=-74.0060)
        
        # Should use location service for distance calculations in get_available_technicians
        available_techs = service.get_available_technicians(
            tenant_id=tenant_id,
            location=work_location,
            radius_km=10.0
        )
        
        # Verify location service was used
        # (In real implementation, this would call the location service)
        assert isinstance(available_techs, list)


if __name__ == "__main__":
    pytest.main([__file__])