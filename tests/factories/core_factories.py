"""
Factory Boy factories for core DotMac models.
"""
import os
import sys
from uuid import uuid4

# Adjust path for core package imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../packages/dotmac-core/src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../packages/dotmac-platform-services/src'))

import factory
from factory import Faker, LazyAttribute, LazyFunction

from dotmac.core import BaseModel
from dotmac.models import TenantContext

# Restore path after imports
sys.path = sys.path[2:]


class TenantContextFactory(factory.Factory):
    """Factory for TenantContext model."""

    class Meta:
        model = TenantContext

    tenant_id = LazyFunction(lambda: str(uuid4()))
    tenant_name = Faker('company')
    domain = LazyAttribute(lambda obj: f"{obj.tenant_name.lower().replace(' ', '-')}.example.com")
    is_active = True
    metadata = factory.Dict({
        'plan': 'professional',
        'created_by': 'system',
        'region': 'us-east-1'
    })


class TestTenantContextFactory(TenantContextFactory):
    """Factory for test tenant context with predictable data."""

    tenant_id = "test-tenant-123"
    tenant_name = "Test Company"
    domain = "test.example.com"
    is_active = True
    metadata = factory.Dict({
        'plan': 'test',
        'created_by': 'test-system'
    })


class TestModelFactory(factory.Factory):
    """Generic factory for testing BaseModel functionality."""

    class Meta:
        model = BaseModel

    # BaseModel is abstract, so this factory is for testing inheritance
