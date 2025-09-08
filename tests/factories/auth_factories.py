"""
Factory Boy factories for authentication models.
"""
import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4

# Adjust path for platform services imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../packages/dotmac-platform-services/src'))

import factory
from factory import Faker, LazyAttribute, LazyFunction

from dotmac.auth.models import AuthToken, SessionData, User

# Restore path after imports
sys.path = sys.path[1:]


class UserFactory(factory.Factory):
    """Factory for User model."""

    class Meta:
        model = User

    id = LazyFunction(lambda: str(uuid4()))
    email = Faker('email')
    username = LazyAttribute(lambda obj: obj.email.split('@')[0])
    is_active = True
    tenant_id = LazyFunction(lambda: str(uuid4()))
    roles = factory.List(['user'])
    metadata = factory.Dict({})
    created_at = LazyFunction(datetime.utcnow)
    updated_at = LazyAttribute(lambda obj: obj.created_at)


class AdminUserFactory(UserFactory):
    """Factory for admin user."""

    roles = factory.List(['admin', 'user'])
    username = 'admin'
    email = 'admin@test.com'


class SessionDataFactory(factory.Factory):
    """Factory for SessionData model."""

    class Meta:
        model = SessionData

    user_id = LazyFunction(lambda: str(uuid4()))
    tenant_id = LazyFunction(lambda: str(uuid4()))
    session_id = LazyFunction(lambda: str(uuid4()))
    expires_at = LazyFunction(lambda: datetime.utcnow() + timedelta(hours=24))
    metadata = factory.Dict({})


class AuthTokenFactory(factory.Factory):
    """Factory for AuthToken model."""

    class Meta:
        model = AuthToken

    token = LazyFunction(lambda: f"token_{uuid4().hex[:16]}")
    token_type = "bearer"
    expires_in = 3600  # 1 hour
    refresh_token = LazyFunction(lambda: f"refresh_{uuid4().hex[:16]}")
    scope = "read write"
