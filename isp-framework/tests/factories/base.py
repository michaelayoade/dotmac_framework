"""Base factory classes for test data generation."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import uuid4
import factory
from faker import Faker

fake = Faker()


class BaseFactory(factory.Factory):
    """Base factory with common fields for all models."""
    
    id = factory.LazyFunction(lambda: str(uuid4()))
    tenant_id = "00000000-0000-0000-0000-000000000001"  # Default test tenant
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
    status = "active"
    
    
class TenantMixin:
    """Mixin for tenant-aware factories."""
    
    tenant_id = "00000000-0000-0000-0000-000000000001"
    
    @classmethod
    def create_for_tenant(cls, tenant_id: str, **kwargs):
        """Create instance for specific tenant."""
        kwargs['tenant_id'] = tenant_id
        return cls.create(**kwargs)


class TimestampMixin:
    """Mixin for timestamp fields."""
    
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
    

class AuditMixin:
    """Mixin for audit fields."""
    
    created_by = factory.LazyFunction(lambda: str(uuid4()))
    updated_by = factory.LazyFunction(lambda: str(uuid4()))
    notes = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=200))


def random_decimal(min_value: float = 0.0, max_value: float = 1000.0, places: int = 2) -> Decimal:
    """Generate random decimal with specified precision."""
    return Decimal(str(round(fake.pyfloat(min_value=min_value, max_value=max_value), places)))


def random_phone() -> str:
    """Generate realistic phone number."""
    return fake.phone_number()


def random_email(domain: Optional[str] = None) -> str:
    """Generate realistic email address."""
    if domain:
        return fake.user_name() + "@" + domain
    return fake.email()


def random_date_in_range(start_date: date, end_date: date) -> date:
    """Generate random date within range."""
    return fake.date_between(start_date=start_date, end_date=end_date)


def random_datetime_in_range(start_date: datetime, end_date: datetime) -> datetime:
    """Generate random datetime within range."""
    return fake.date_time_between(start_date=start_date, end_date=end_date)


class SequentialValueFactory:
    """Factory for generating sequential values."""
    
    def __init__(self, prefix: str = "", start: int = 1, padding: int = 3):
        """  Init   operation."""
        self.prefix = prefix
        self.current = start
        self.padding = padding
    
    def __call__(self):
        """  Call   operation."""
        value = f"{self.prefix}{self.current:0{self.padding}d}"
        self.current += 1
        return value


# Common sequential generators
invoice_number_generator = SequentialValueFactory("INV-", 1001, 4)
customer_number_generator = SequentialValueFactory("CUST", 1001, 4) 
payment_number_generator = SequentialValueFactory("PAY-", 2001, 4)
ticket_number_generator = SequentialValueFactory("TKT-", 3001, 4)