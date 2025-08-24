"""Factories for identity-related test data."""

from uuid import uuid4
import factory
from faker import Faker

from .base import (
    BaseFactory,
    TenantMixin,
    TimestampMixin,
    AuditMixin,
    random_email,
    random_phone,
    customer_number_generator,
)

fake = Faker()


class CustomerFactory(BaseFactory, TenantMixin, TimestampMixin, AuditMixin):
    """Factory for Customer test data."""
    
    class Meta:
        """Class for Meta operations."""
        model = None
    
    # Customer identification
    customer_number = factory.LazyFunction(customer_number_generator)
    portal_id = factory.LazyAttribute(lambda obj: f"P{fake.bothify('?#?#?#?#')}")
    
    # Personal information
    first_name = factory.LazyAttribute(lambda obj: fake.first_name())
    last_name = factory.LazyAttribute(lambda obj: fake.last_name())
    middle_name = factory.LazyAttribute(lambda obj: fake.first_name() if fake.boolean() else None)
    
    # Contact information
    email_primary = factory.LazyAttribute(lambda obj: random_email())
    email_secondary = factory.LazyAttribute(lambda obj: random_email() if fake.boolean() else None)
    phone_primary = factory.LazyAttribute(lambda obj: random_phone())
    phone_secondary = factory.LazyAttribute(lambda obj: random_phone() if fake.boolean() else None)
    
    # Customer classification
    customer_type = "residential"  # residential, business, enterprise
    account_status = "active"
    credit_rating = factory.LazyAttribute(lambda obj: fake.random_element(["excellent", "good", "fair", "poor"]))
    
    # Preferences
    preferred_contact_method = "email"
    billing_cycle_preference = "monthly"
    paperless_billing = True
    marketing_opt_in = factory.LazyAttribute(lambda obj: fake.boolean())
    
    # Service information
    service_start_date = factory.LazyAttribute(lambda obj: fake.date_this_year())
    account_manager_id = factory.LazyFunction(lambda: str(uuid4()) if fake.boolean() else None)
    
    @classmethod
    def create_business(cls, **kwargs):
        """Create a business customer."""
        customer_data = kwargs.copy()
        customer_data.update({
            'customer_type': 'business',
            'billing_cycle_preference': 'monthly',
        })
        return cls.create(**customer_data)
    
    @classmethod
    def create_enterprise(cls, **kwargs):
        """Create an enterprise customer."""
        customer_data = kwargs.copy()
        customer_data.update({
            'customer_type': 'enterprise',
            'billing_cycle_preference': 'quarterly',
            'account_manager_id': str(uuid4()),  # Enterprise customers always have account managers
        })
        return cls.create(**customer_data)


class CustomerAddressFactory(BaseFactory, TenantMixin, TimestampMixin):
    """Factory for CustomerAddress test data."""
    
    class Meta:
        """Class for Meta operations."""
        model = None
    
    customer_id = factory.LazyFunction(lambda: str(uuid4()))
    
    # Address type
    address_type = "billing"  # billing, service, mailing
    
    # Address components
    street_address_1 = factory.LazyAttribute(lambda obj: fake.street_address())
    street_address_2 = factory.LazyAttribute(lambda obj: fake.secondary_address() if fake.boolean() else None)
    city = factory.LazyAttribute(lambda obj: fake.city())
    state_province = factory.LazyAttribute(lambda obj: fake.state_abbr())
    postal_code = factory.LazyAttribute(lambda obj: fake.zipcode())
    country = "US"
    
    # Address metadata
    is_primary = True
    is_verified = factory.LazyAttribute(lambda obj: fake.boolean(chance_of_getting_true=80))
    verification_date = factory.LazyAttribute(lambda obj: fake.date_this_year() if obj.is_verified else None)
    
    # Geographic coordinates (for service address)
    latitude = factory.LazyAttribute(lambda obj: fake.latitude() if obj.address_type == "service" else None)
    longitude = factory.LazyAttribute(lambda obj: fake.longitude() if obj.address_type == "service" else None)
    
    @classmethod
    def create_service_address(cls, **kwargs):
        """Create a service address with coordinates."""
        address_data = kwargs.copy()
        address_data.update({
            'address_type': 'service',
            'latitude': fake.latitude(),
            'longitude': fake.longitude(),
        })
        return cls.create(**address_data)


class UserFactory(BaseFactory, TenantMixin, TimestampMixin):
    """Factory for User test data."""
    
    class Meta:
        """Class for Meta operations."""
        model = None
    
    # User identification
    username = factory.LazyAttribute(lambda obj: fake.user_name())
    email = factory.LazyAttribute(lambda obj: random_email())
    portal_id = factory.LazyAttribute(lambda obj: f"U{fake.bothify('?#?#?#?#')}")
    
    # Personal information
    first_name = factory.LazyAttribute(lambda obj: fake.first_name())
    last_name = factory.LazyAttribute(lambda obj: fake.last_name())
    full_name = factory.LazyAttribute(lambda obj: f"{obj.first_name} {obj.last_name}")
    
    # Authentication
    password_hash = factory.LazyAttribute(lambda obj: fake.sha256())
    is_active = True
    is_verified = factory.LazyAttribute(lambda obj: fake.boolean(chance_of_getting_true=90))
    email_verified = factory.LazyAttribute(lambda obj: fake.boolean(chance_of_getting_true=85))
    
    # Authorization
    role = "user"
    permissions = factory.LazyAttribute(lambda obj: ["read", "write"] if obj.role != "admin" else ["read", "write", "admin"])
    
    # Profile information
    phone_number = factory.LazyAttribute(lambda obj: random_phone())
    timezone = factory.LazyAttribute(lambda obj: fake.timezone())
    locale = "en_US"
    
    # Timestamps
    last_login = factory.LazyAttribute(lambda obj: fake.date_time_this_month())
    password_changed_at = factory.LazyAttribute(lambda obj: fake.date_time_this_year())
    
    @classmethod
    def create_admin(cls, **kwargs):
        """Create an admin user."""
        user_data = kwargs.copy()
        user_data.update({
            'role': 'admin',
            'permissions': ['read', 'write', 'admin', 'super_admin'],
            'is_verified': True,
            'email_verified': True,
        })
        return cls.create(**user_data)
    
    @classmethod
    def create_customer_user(cls, **kwargs):
        """Create a customer portal user."""
        user_data = kwargs.copy()
        user_data.update({
            'role': 'customer',
            'permissions': ['read', 'write'],
        })
        return cls.create(**user_data)


class OrganizationFactory(BaseFactory, TenantMixin, TimestampMixin, AuditMixin):
    """Factory for Organization test data."""
    
    class Meta:
        """Class for Meta operations."""
        model = None
    
    # Organization identification
    name = factory.LazyAttribute(lambda obj: fake.company())
    legal_name = factory.LazyAttribute(lambda obj: f"{obj.name}, Inc.")
    organization_type = "corporation"  # corporation, llc, partnership, sole_proprietorship
    
    # Business information
    tax_id = factory.LazyAttribute(lambda obj: fake.bothify("##-#######"))
    duns_number = factory.LazyAttribute(lambda obj: fake.bothify("#########"))
    industry = factory.LazyAttribute(lambda obj: fake.catch_phrase())
    
    # Contact information
    primary_email = factory.LazyAttribute(lambda obj: f"info@{fake.domain_name()}")
    primary_phone = factory.LazyAttribute(lambda obj: random_phone())
    website = factory.LazyAttribute(lambda obj: f"https://www.{fake.domain_name()}")
    
    # Address (headquarters)
    headquarters_address = factory.LazyAttribute(lambda obj: fake.address())
    
    # Business details
    employee_count = factory.LazyAttribute(lambda obj: fake.random_int(1, 10000))
    annual_revenue = factory.LazyAttribute(lambda obj: fake.random_int(100000, 50000000))
    founded_date = factory.LazyAttribute(lambda obj: fake.date_between(start_date='-50y', end_date='today'))
    
    # Relationship information
    parent_organization_id = factory.LazyFunction(lambda: str(uuid4()) if fake.boolean(chance_of_getting_true=20) else None)
    account_manager_id = factory.LazyFunction(lambda: str(uuid4()))
    
    @classmethod
    def create_small_business(cls, **kwargs):
        """Create a small business organization."""
        org_data = kwargs.copy()
        org_data.update({
            'organization_type': 'llc',
            'employee_count': fake.random_int(1, 50),
            'annual_revenue': fake.random_int(100000, 2000000),
        })
        return cls.create(**org_data)
    
    @classmethod
    def create_enterprise(cls, **kwargs):
        """Create an enterprise organization."""
        org_data = kwargs.copy()
        org_data.update({
            'organization_type': 'corporation',
            'employee_count': fake.random_int(1000, 50000),
            'annual_revenue': fake.random_int(10000000, 1000000000),
        })
        return cls.create(**org_data)


class ContactFactory(BaseFactory, TenantMixin, TimestampMixin):
    """Factory for Contact test data."""
    
    class Meta:
        """Class for Meta operations."""
        model = None
    
    # Contact identification
    first_name = factory.LazyAttribute(lambda obj: fake.first_name())
    last_name = factory.LazyAttribute(lambda obj: fake.last_name())
    title = factory.LazyAttribute(lambda obj: fake.job())
    
    # Contact information
    email = factory.LazyAttribute(lambda obj: random_email())
    phone_work = factory.LazyAttribute(lambda obj: random_phone())
    phone_mobile = factory.LazyAttribute(lambda obj: random_phone() if fake.boolean() else None)
    
    # Relationship
    customer_id = factory.LazyFunction(lambda: str(uuid4()))
    organization_id = factory.LazyFunction(lambda: str(uuid4()) if fake.boolean() else None)
    
    # Contact type and preferences
    contact_type = "primary"  # primary, billing, technical, emergency
    is_primary = factory.LazyAttribute(lambda obj: obj.contact_type == "primary")
    preferred_contact_method = "email"
    
    # Authorization
    can_authorize_changes = factory.LazyAttribute(lambda obj: fake.boolean(chance_of_getting_true=70))
    can_view_billing = factory.LazyAttribute(lambda obj: fake.boolean(chance_of_getting_true=80))
    
    @classmethod
    def create_technical_contact(cls, **kwargs):
        """Create a technical contact."""
        contact_data = kwargs.copy()
        contact_data.update({
            'contact_type': 'technical',
            'title': 'IT Manager',
            'can_authorize_changes': True,
            'can_view_billing': False,
        })
        return cls.create(**contact_data)
    
    @classmethod
    def create_billing_contact(cls, **kwargs):
        """Create a billing contact."""
        contact_data = kwargs.copy()
        contact_data.update({
            'contact_type': 'billing',
            'title': 'Accounts Payable',
            'can_authorize_changes': False,
            'can_view_billing': True,
        })
        return cls.create(**contact_data)