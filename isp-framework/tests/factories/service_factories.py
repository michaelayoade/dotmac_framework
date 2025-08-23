"""Factories for service-related test data."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
import factory
from faker import Faker

from .base import (
    BaseFactory,
    TenantMixin,
    TimestampMixin,
    AuditMixin,
    random_decimal,
)

fake = Faker()


class ServicePlanFactory(BaseFactory, TenantMixin, TimestampMixin):
    """Factory for ServicePlan test data."""
    
    class Meta:
        model = None
    
    # Plan identification
    plan_code = factory.LazyAttribute(lambda obj: fake.bothify("PLAN-???###"))
    plan_name = factory.LazyAttribute(lambda obj: fake.catch_phrase())
    
    # Plan details
    service_type = "internet"  # internet, voip, tv, bundle
    description = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=200))
    
    # Pricing
    monthly_price = factory.LazyFunction(lambda: random_decimal(25.0, 300.0))
    setup_fee = factory.LazyFunction(lambda: random_decimal(0.0, 150.0))
    early_termination_fee = factory.LazyFunction(lambda: random_decimal(0.0, 200.0))
    
    # Service specifications (for internet)
    bandwidth_down = factory.LazyAttribute(lambda obj: fake.random_int(10, 1000) if obj.service_type == "internet" else None)
    bandwidth_up = factory.LazyAttribute(lambda obj: obj.bandwidth_down // 10 if obj.bandwidth_down else None)
    data_allowance = factory.LazyAttribute(lambda obj: "unlimited")
    
    # Contract terms
    contract_term_months = factory.LazyAttribute(lambda obj: fake.random_element([12, 24, 36]))
    is_business_plan = factory.LazyAttribute(lambda obj: fake.boolean(chance_of_getting_true=30))
    
    # Availability
    is_available = True
    available_from = factory.LazyFunction(lambda: date.today() - timedelta(days=365))
    available_until = None
    
    @classmethod
    def create_residential_internet(cls, **kwargs):
        """Create a residential internet plan."""
        plan_data = kwargs.copy()
        plan_data.update({
            'service_type': 'internet',
            'is_business_plan': False,
            'bandwidth_down': fake.random_element([25, 50, 100, 200, 500]),
            'plan_name': f"Residential Internet {plan_data.get('bandwidth_down', 100)}Mbps",
        })
        plan_data['bandwidth_up'] = plan_data['bandwidth_down'] // 10
        return cls.create(**plan_data)
    
    @classmethod
    def create_business_internet(cls, **kwargs):
        """Create a business internet plan."""
        plan_data = kwargs.copy()
        plan_data.update({
            'service_type': 'internet',
            'is_business_plan': True,
            'bandwidth_down': fake.random_element([100, 200, 500, 1000]),
            'plan_name': f"Business Internet {plan_data.get('bandwidth_down', 100)}Mbps",
            'monthly_price': random_decimal(100.0, 800.0),
        })
        plan_data['bandwidth_up'] = plan_data['bandwidth_down'] // 5  # Better upload for business
        return cls.create(**plan_data)


class ServiceInstanceFactory(BaseFactory, TenantMixin, TimestampMixin, AuditMixin):
    """Factory for ServiceInstance test data."""
    
    class Meta:
        model = None
    
    # Service identification
    service_id = factory.LazyAttribute(lambda obj: fake.bothify("SVC-######"))
    customer_id = factory.LazyFunction(lambda: str(uuid4()))
    service_plan_id = factory.LazyFunction(lambda: str(uuid4()))
    
    # Service details
    service_name = factory.LazyAttribute(lambda obj: fake.catch_phrase())
    service_type = "internet"
    
    # Status and lifecycle
    status = "active"
    provisioning_status = "completed"
    activation_date = factory.LazyFunction(lambda: date.today() - timedelta(days=fake.random_int(1, 365)))
    suspension_date = None
    termination_date = None
    
    # Billing information
    monthly_recurring_charge = factory.LazyFunction(lambda: random_decimal(25.0, 300.0))
    billing_cycle = "monthly"
    next_billing_date = factory.LazyFunction(lambda: date.today() + timedelta(days=30))
    
    # Technical specifications
    bandwidth_down = factory.LazyAttribute(lambda obj: fake.random_int(25, 1000))
    bandwidth_up = factory.LazyAttribute(lambda obj: obj.bandwidth_down // 10)
    static_ip_count = 0
    
    # Location and installation
    installation_address = factory.LazyAttribute(lambda obj: fake.address())
    installation_date = factory.LazyAttribute(lambda obj: obj.activation_date)
    technician_notes = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=500))
    
    # Equipment
    modem_serial = factory.LazyAttribute(lambda obj: fake.bothify("MDM-???######"))
    router_serial = factory.LazyAttribute(lambda obj: fake.bothify("RTR-???######") if fake.boolean() else None)
    
    # Support information
    assigned_technician_id = factory.LazyFunction(lambda: str(uuid4()) if fake.boolean() else None)
    
    @classmethod
    def create_suspended(cls, **kwargs):
        """Create a suspended service instance."""
        service_data = kwargs.copy()
        service_data.update({
            'status': 'suspended',
            'suspension_date': date.today() - timedelta(days=fake.random_int(1, 30)),
            'provisioning_status': 'suspended',
        })
        return cls.create(**service_data)
    
    @classmethod
    def create_terminated(cls, **kwargs):
        """Create a terminated service instance."""
        service_data = kwargs.copy()
        termination_date = date.today() - timedelta(days=fake.random_int(1, 90))
        service_data.update({
            'status': 'terminated',
            'termination_date': termination_date,
            'provisioning_status': 'deprovisioned',
        })
        return cls.create(**service_data)
    
    @classmethod
    def create_business_service(cls, **kwargs):
        """Create a business service instance."""
        service_data = kwargs.copy()
        service_data.update({
            'bandwidth_down': fake.random_element([100, 200, 500, 1000]),
            'static_ip_count': fake.random_int(1, 8),
            'monthly_recurring_charge': random_decimal(200.0, 1000.0),
        })
        service_data['bandwidth_up'] = service_data['bandwidth_down'] // 5
        return cls.create(**service_data)


class ServiceChangeOrderFactory(BaseFactory, TenantMixin, TimestampMixin, AuditMixin):
    """Factory for ServiceChangeOrder test data."""
    
    class Meta:
        model = None
    
    # Change order identification
    change_order_number = factory.LazyAttribute(lambda obj: fake.bothify("CHG-######"))
    service_instance_id = factory.LazyFunction(lambda: str(uuid4()))
    customer_id = factory.LazyFunction(lambda: str(uuid4()))
    
    # Change details
    change_type = "upgrade"  # upgrade, downgrade, suspension, termination, modification
    requested_date = factory.LazyFunction(lambda: date.today())
    scheduled_date = factory.LazyFunction(lambda: date.today() + timedelta(days=fake.random_int(1, 30)))
    completed_date = None
    
    # Change specifications
    old_plan_id = factory.LazyFunction(lambda: str(uuid4()))
    new_plan_id = factory.LazyFunction(lambda: str(uuid4()))
    change_reason = factory.LazyAttribute(lambda obj: fake.sentence())
    
    # Status tracking
    status = "pending"  # pending, approved, scheduled, in_progress, completed, cancelled
    approval_required = factory.LazyAttribute(lambda obj: fake.boolean(chance_of_getting_true=60))
    approved_by = factory.LazyFunction(lambda: str(uuid4()) if fake.boolean() else None)
    approval_date = None
    
    # Technical details
    requires_site_visit = factory.LazyAttribute(lambda obj: fake.boolean(chance_of_getting_true=30))
    estimated_duration_hours = factory.LazyAttribute(lambda obj: fake.random_int(1, 8))
    
    # Financial impact
    one_time_charge = factory.LazyFunction(lambda: random_decimal(0.0, 200.0))
    monthly_charge_change = factory.LazyFunction(lambda: random_decimal(-100.0, 200.0))
    
    @classmethod
    def create_upgrade(cls, **kwargs):
        """Create a service upgrade change order."""
        change_data = kwargs.copy()
        change_data.update({
            'change_type': 'upgrade',
            'monthly_charge_change': random_decimal(10.0, 100.0),
            'one_time_charge': random_decimal(0.0, 50.0),
        })
        return cls.create(**change_data)
    
    @classmethod
    def create_downgrade(cls, **kwargs):
        """Create a service downgrade change order."""
        change_data = kwargs.copy()
        change_data.update({
            'change_type': 'downgrade',
            'monthly_charge_change': random_decimal(-100.0, -10.0),
            'one_time_charge': Decimal('0.00'),
        })
        return cls.create(**change_data)


class ServiceOutageFactory(BaseFactory, TenantMixin, TimestampMixin):
    """Factory for ServiceOutage test data."""
    
    class Meta:
        model = None
    
    # Outage identification
    outage_id = factory.LazyAttribute(lambda obj: fake.bothify("OUT-######"))
    
    # Affected services
    service_instance_id = factory.LazyFunction(lambda: str(uuid4()) if fake.boolean() else None)
    affected_customer_count = factory.LazyAttribute(lambda obj: fake.random_int(1, 1000))
    
    # Outage details
    outage_type = factory.LazyAttribute(lambda obj: fake.random_element(["planned", "unplanned"]))
    severity = factory.LazyAttribute(lambda obj: fake.random_element(["low", "medium", "high", "critical"]))
    
    # Timeline
    started_at = factory.LazyFunction(lambda: datetime.utcnow() - timedelta(hours=fake.random_int(1, 48)))
    estimated_resolution = factory.LazyAttribute(lambda obj: obj.started_at + timedelta(hours=fake.random_int(1, 24)))
    resolved_at = None
    
    # Description and cause
    title = factory.LazyAttribute(lambda obj: fake.catch_phrase())
    description = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=500))
    root_cause = factory.LazyAttribute(lambda obj: fake.sentence() if fake.boolean() else None)
    
    # Status
    status = "active"  # active, resolved, investigating
    
    # Geographic impact
    affected_areas = factory.LazyAttribute(lambda obj: [fake.city() for _ in range(fake.random_int(1, 3))])
    
    @classmethod
    def create_resolved(cls, **kwargs):
        """Create a resolved outage."""
        outage_data = kwargs.copy()
        start_time = datetime.utcnow() - timedelta(hours=fake.random_int(2, 48))
        resolution_time = start_time + timedelta(hours=fake.random_int(1, 12))
        
        outage_data.update({
            'status': 'resolved',
            'started_at': start_time,
            'resolved_at': resolution_time,
            'root_cause': fake.sentence(),
        })
        return cls.create(**outage_data)
    
    @classmethod
    def create_critical_outage(cls, **kwargs):
        """Create a critical outage."""
        outage_data = kwargs.copy()
        outage_data.update({
            'severity': 'critical',
            'outage_type': 'unplanned',
            'affected_customer_count': fake.random_int(500, 5000),
            'title': 'Critical Network Infrastructure Failure',
        })
        return cls.create(**outage_data)