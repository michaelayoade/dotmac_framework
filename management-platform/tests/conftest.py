"""
AI-First Testing Configuration and Fixtures
===========================================

This module provides testing infrastructure optimized for AI-written software,
focusing on business outcomes and system behavior rather than implementation details.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import AsyncGenerator, Generator, Dict, Any, List

import pytest
import pytest_asyncio
from hypothesis import settings, HealthCheck
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AI-First Testing Configuration
# ==============================
# Configure Hypothesis for AI-appropriate property-based testing
settings.register_profile(
    "ai_first",
    max_examples=50,  # Reasonable number of examples for AI-generated edge cases
    deadline=10000,   # 10 second deadline for complex business logic
    suppress_health_check=[
        HealthCheck.too_slow,  # AI-generated tests may be complex
        HealthCheck.data_too_large,  # Business scenarios can be large
    ]
)
settings.load_profile("ai_first")


# Test Database Setup
# ===================

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine for AI-first testing."""
    # Use in-memory SQLite for fast AI test execution
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,  # Reduce noise in AI test output
    )
    
    yield engine
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide clean database session for each test."""
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    
    async with async_session() as session:
        # Begin transaction
        await session.begin()
        
        try:
            yield session
        finally:
            # Always rollback to ensure test isolation
            await session.rollback()


# AI-First Test Data Factories
# =============================

class AITestDataFactory:
    """Factory for generating AI-appropriate test data with business realism."""
    
    @staticmethod
    def create_tenant_id() -> str:
        """Generate realistic tenant ID."""
        return f"tenant-{uuid.uuid4().hex[:8]}"
    
    @staticmethod
    def create_plugin_catalog_data(**overrides) -> Dict[str, Any]:
        """Generate realistic plugin catalog data."""
        base_data = {
            "plugin_id": f"plugin-{uuid.uuid4().hex[:8]}",
            "plugin_name": "Advanced Analytics Suite",
            "plugin_version": "1.0.0",
            "plugin_description": "Comprehensive analytics and reporting tools",
            "category": "analytics",
            "monthly_price": Decimal("49.99"),
            "annual_price": Decimal("499.99"),
            "has_usage_billing": True,
            "usage_metrics": ["api_calls", "reports_generated", "data_exports"],
            "usage_rates": {
                "api_calls": 0.001,
                "reports_generated": 1.99,
                "data_exports": 0.50
            },
            "trial_days": 14,
            "is_active": True,
            "is_public": True
        }
        base_data.update(overrides)
        return base_data
    
    @staticmethod
    def create_subscription_data(tenant_id: str, plugin_id: str, **overrides) -> Dict[str, Any]:
        """Generate realistic plugin subscription data."""
        base_data = {
            "tenant_id": tenant_id,
            "plugin_id": plugin_id,
            "starts_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=30),
            "is_trial": False,
            "monthly_price": Decimal("49.99"),
            "billing_cycle": "monthly",
            "usage_limits": {
                "api_calls": 10000,
                "reports_generated": 100,
                "data_exports": 50
            },
            "current_usage": {
                "api_calls": 0,
                "reports_generated": 0,
                "data_exports": 0
            }
        }
        base_data.update(overrides)
        return base_data


@pytest.fixture
def ai_test_factory():
    """Provide AI test data factory."""
    return AITestDataFactory()


# Performance Test Configuration
# ==============================

@pytest.fixture
def performance_config():
    """Configuration for performance invariant tests."""
    return {
        "max_response_time": 1.0,  # 1 second max for API responses
        "max_average_response_time": 0.2,  # 200ms average
        "concurrent_requests": 10,  # Test concurrency level
        "load_duration": 30,  # 30 seconds load test
    }


# Contract Testing Setup
# ======================

@pytest.fixture
def api_contract_base_url():
    """Base URL for API contract testing."""
    return "http://test"


@pytest.fixture
def licensing_api_endpoints():
    """Plugin licensing API endpoints for contract testing."""
    return {
        "validate_license": "/api/v1/plugin-licensing/validate/{tenant_id}",
        "report_usage": "/api/v1/plugin-licensing/usage",
        "health_status": "/api/v1/plugin-licensing/health-status",
        "tenant_subscriptions": "/api/v1/plugin-licensing/tenant/{tenant_id}/subscriptions",
        "usage_summary": "/api/v1/plugin-licensing/usage-summary/{tenant_id}/{plugin_id}"
    }


# Event Loop Configuration
# =========================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Test Environment Markers
# =========================

def pytest_configure(config):
    """Configure pytest with AI-first testing markers."""
    # Add AI-first testing markers
    config.addinivalue_line(
        "markers", 
        "ai_validation: AI-safe tests that validate business behavior and outcomes"
    )
    config.addinivalue_line(
        "markers",
        "revenue_protection: Tests that protect revenue-generating functionality"
    )
    config.addinivalue_line(
        "markers",
        "tenant_isolation: Tests that validate multi-tenant data isolation"
    )
    config.addinivalue_line(
        "markers",
        "business_invariants: Tests that validate business rules and constraints"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection for AI-first testing approach."""
    for item in items:
        # Add default markers based on test path and name
        if "revenue" in str(item.fspath) or "billing" in item.name:
            item.add_marker(pytest.mark.revenue_protection)
        
        if "tenant" in str(item.fspath) or "isolation" in item.name:
            item.add_marker(pytest.mark.tenant_isolation)
        
        if "property" in item.name or "invariant" in item.name:
            item.add_marker(pytest.mark.ai_validation)