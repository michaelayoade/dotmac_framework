#!/usr/bin/env python3
"""
Simple script to create a test ISP tenant through the management platform.
This demonstrates the container-per-tenant SaaS architecture.
"""

import asyncio
import sys
import os
sys.path.append('/home/dotmac_framework/management-platform')

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.models.tenant import Tenant, TenantStatus
from app.database import Base
import uuid

DATABASE_URL = "postgresql+asyncpg://dotmac_admin:dotmac_secure_2024@localhost:5434/mgmt_platform"

async def create_test_tenant():
    """Create a test ISP tenant directly in the database."""
    
    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # Create test tenant
            test_tenant = Tenant(
                id=uuid.uuid4(),
                name="Demo ISP Company",
                slug="demo-isp",
                description="Demo ISP tenant for testing the container-per-tenant architecture",
                contact_email="admin@demo-isp.com",
                contact_name="Demo Admin",
                contact_phone="+1-555-0123",
                status=TenantStatus.PENDING.value,
                settings={
                    "theme": "dark",
                    "notifications_enabled": True,
                    "max_users": 100,
                    "features": ["billing", "monitoring", "automation"]
                }
            )
            
            session.add(test_tenant)
            await session.commit()
            await session.refresh(test_tenant)
            
            print(f"✅ Successfully created tenant: {test_tenant.name}")
            print(f"   - ID: {test_tenant.id}")
            print(f"   - Slug: {test_tenant.slug}")
            print(f"   - Status: {test_tenant.status}")
            print(f"   - Container Name: {test_tenant.get_container_name()}")
            print(f"   - URL: {test_tenant.get_container_url()}")
            print(f"   - Active: {test_tenant.is_active}")
            print(f"   - Can Deploy: {test_tenant.can_deploy}")
            
            # Update status to active
            test_tenant.status = TenantStatus.ACTIVE.value
            await session.commit()
            
            print(f"\n✅ Updated tenant status to: {test_tenant.status}")
            print(f"   - Active: {test_tenant.is_active}")
            print(f"   - Can Deploy: {test_tenant.can_deploy}")
            
            return test_tenant
            
    except Exception as e:
        print(f"❌ Error creating tenant: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_test_tenant())