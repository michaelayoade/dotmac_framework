"""
Tenant repository for multi-tenant operations.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.tenant import (
    Tenant, 
    TenantConfiguration, 
    TenantInvitation,
    TenantStatus
)
from models.billing import UsageRecord  # Using billing model for usage metrics
from repositories.base import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    """Repository for tenant operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, Tenant)
    
    async def get_by_name(self, name: str) -> Optional[Tenant]:
        """Get tenant by name."""
        return await self.get_by_field("name", name)
    
    async def get_by_slug(self, slug: str) -> Optional[Tenant]:
        """Get tenant by slug."""
        return await self.get_by_field("slug", slug)
    
    async def get_by_domain(self, domain: str) -> Optional[Tenant]:
        """Get tenant by custom domain."""
        return await self.get_by_field("custom_domain", domain)
    
    async def get_with_configurations(self, tenant_id: UUID) -> Optional[Tenant]:
        """Get tenant with configurations loaded."""
        return await self.get_by_id(
            tenant_id, 
            relationships=["configurations", "users"]
        )
    
    async def get_active_tenants(
        self, 
        skip: int = 0,
        limit: int = 100
    ) -> List[Tenant]:
        """Get active tenants."""
        return await self.list(
            skip=skip,
            limit=limit,
            filters={"status": TenantStatus.ACTIVE},
            order_by="-created_at"
        )
    
    async def get_tenants_by_status(
        self, 
        status: TenantStatus,
        skip: int = 0,
        limit: int = 100
    ) -> List[Tenant]:
        """Get tenants by status."""
        return await self.list(
            skip=skip,
            limit=limit,
            filters={"status": status},
            order_by="-created_at"
        )
    
    
    async def search_tenants(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tenant]:
        """Search tenants by name, email, or slug."""
        return await self.search(
            search_term=search_term,
            search_fields=["name", "slug", "contact_email"],
            skip=skip,
            limit=limit,
            filters=filters
        )
    
    async def get_tenants_with_relationships(
        self,
        skip: int = 0,
        limit: int = 100,
        include_configs: bool = False,
        include_users: bool = False,
        include_invitations: bool = False,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tenant]:
        """Get tenants with related data in one query to prevent N+1."""
        relationships = []
        
        if include_configs:
            relationships.append("configurations")
        if include_users:
            relationships.append("users")
        if include_invitations:
            relationships.append("invitations")
        
        return await self.list(
            skip=skip,
            limit=limit,
            filters=filters,
            relationships=relationships,
            order_by="-created_at"
        )
    
    async def get_tenants_summary_bulk(
        self,
        tenant_ids: List[UUID]
    ) -> Dict[UUID, Dict[str, Any]]:
        """Get bulk tenant summary data to prevent N+1 queries."""
        # Get tenants
        tenants_query = select(Tenant).where(
            Tenant.id.in_(tenant_ids),
            Tenant.is_deleted == False
        )
        
        result = await self.db.execute(tenants_query)
        tenants = {t.id: t for t in result.scalars().all()}
        
        # Get user counts for all tenants in one query
        from models.user import User
        user_counts_query = select(
            User.tenant_id,
            func.count(User.id).label('user_count')
        ).where(
            User.tenant_id.in_(tenant_ids),
            User.is_deleted == False
        ).group_by(User.tenant_id)
        
        result = await self.db.execute(user_counts_query)
        user_counts = {row.tenant_id: row.user_count for row in result}
        
        # Get subscription info for all tenants in one query
        from models.billing import Subscription
        subscriptions_query = select(
            Subscription.tenant_id,
            Subscription.status,
            Subscription.monthly_amount_cents
        ).where(
            Subscription.tenant_id.in_(tenant_ids),
            Subscription.is_active == True,
            Subscription.is_deleted == False
        )
        
        result = await self.db.execute(subscriptions_query)
        subscriptions = {row.tenant_id: {
            'status': row.status,
            'monthly_revenue': row.monthly_amount_cents / 100 if row.monthly_amount_cents else 0
        } for row in result}
        
        # Build summary
        summary = {}
        for tenant_id, tenant in tenants.items():
            summary[tenant_id] = {
                'id': tenant.id,
                'name': tenant.name,
                'slug': tenant.slug,
                'status': tenant.status,
                'created_at': tenant.created_at,
                'users_count': user_counts.get(tenant_id, 0),
                'health_score': 95,  # Placeholder - would come from monitoring service
                'monthly_revenue': subscriptions.get(tenant_id, {}).get('monthly_revenue', 0),
                'subscription_status': subscriptions.get(tenant_id, {}).get('status', None)
            }
        
        return summary
    
    async def get_tenant_count_by_status(self) -> Dict[str, int]:
        """Get tenant counts grouped by status."""
        query = select(
            Tenant.status,
            func.count(Tenant.id).label('count')
        ).where(
            Tenant.is_deleted == False
        ).group_by(Tenant.status)
        
        result = await self.db.execute(query)
        return {row.status: row.count for row in result}
    
    async def update_status(
        self, 
        tenant_id: UUID, 
        new_status: TenantStatus,
        user_id: Optional[str] = None
    ) -> Optional[Tenant]:
        """Update tenant status with proper timestamp handling."""
        from datetime import datetime
        
        update_data = {"status": new_status}
        
        # Note: activated_at, suspended_at, cancelled_at fields don't exist in current schema
        # This would need to be added to future migrations if timestamps are needed
        
        return await self.update(tenant_id, update_data, user_id)
    
    async def check_slug_availability(self, slug: str, exclude_id: Optional[UUID] = None) -> bool:
        """Check if slug is available."""
        query = select(func.count(Tenant.id)).where(
            Tenant.slug == slug,
            Tenant.is_deleted == False
        )
        
        if exclude_id:
            query = query.where(Tenant.id != exclude_id)
        
        result = await self.db.execute(query)
        return result.scalar() == 0


class TenantConfigurationRepository(BaseRepository[TenantConfiguration]):
    """Repository for tenant configuration operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, TenantConfiguration)
    
    async def get_tenant_configurations(
        self, 
        tenant_id: UUID,
        category: Optional[str] = None,
        active_only: bool = True
    ) -> List[TenantConfiguration]:
        """Get configurations for a tenant."""
        filters = {"tenant_id": tenant_id}
        
        if category:
            filters["category"] = category
        
        if active_only:
            filters["is_active"] = True
        
        return await self.list(
            filters=filters,
            order_by="category"
        )
    
    async def get_configuration_by_key(
        self, 
        tenant_id: UUID, 
        category: str, 
        key: str
    ) -> Optional[TenantConfiguration]:
        """Get specific configuration by key."""
        query = select(TenantConfiguration).where(
            TenantConfiguration.tenant_id == tenant_id,
            TenantConfiguration.category == category,
            TenantConfiguration.key == key,
            TenantConfiguration.is_active == True,
            TenantConfiguration.is_deleted == False
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def upsert_configuration(
        self, 
        tenant_id: UUID,
        category: str,
        key: str,
        value: Any,
        user_id: Optional[str] = None
    ) -> TenantConfiguration:
        """Create or update a configuration."""
        existing = await self.get_configuration_by_key(tenant_id, category, key)
        
        if existing:
            return await self.update(
                existing.id,
                {"value": value},
                user_id
            )
        else:
            return await self.create({
                "tenant_id": tenant_id,
                "category": category,
                "key": key,
                "value": value
            }, user_id)
    
    async def bulk_update_configurations(
        self,
        tenant_id: UUID,
        configurations: List[Dict[str, Any]],
        user_id: Optional[str] = None
    ) -> List[TenantConfiguration]:
        """Bulk update configurations without N+1 queries."""
        from sqlalchemy import and_
        from sqlalchemy.dialects.postgresql import insert
        
        # First, get all existing configurations in one query
        existing_keys = [(config["category"], config["key"]) for config in configurations]
        
        query = select(TenantConfiguration).where(
            and_(
                TenantConfiguration.tenant_id == tenant_id,
                TenantConfiguration.is_active == True,
                TenantConfiguration.is_deleted == False
            )
        )
        
        # Filter by categories and keys
        if existing_keys:
            or_conditions = []
            for category, key in existing_keys:
                or_conditions.append(
                    and_(
                        TenantConfiguration.category == category,
                        TenantConfiguration.key == key
                    )
                )
            from sqlalchemy import or_
            query = query.where(or_(*or_conditions))
        
        result = await self.db.execute(query)
        existing_configs = {(c.category, c.key): c for c in result.scalars().all()}
        
        # Prepare bulk operations
        updates = []
        inserts = []
        
        for config_data in configurations:
            category = config_data["category"]
            key = config_data["key"]
            value = config_data["value"]
            
            if (category, key) in existing_configs:
                # Update existing
                config = existing_configs[(category, key)]
                updates.append({
                    "id": config.id,
                    "value": value,
                    "updated_by": user_id
                })
            else:
                # Insert new
                inserts.append({
                    "tenant_id": tenant_id,
                    "category": category,
                    "key": key,
                    "value": value,
                    "created_by": user_id,
                    "updated_by": user_id
                })
        
        # Perform bulk operations
        if updates:
            for update_data in updates:
                config_id = update_data.pop("id")
                await self.update(config_id, update_data, user_id)
        
        if inserts:
            await self.bulk_create(inserts, user_id)
        
        # Return updated configurations
        return await self.get_tenant_configurations(tenant_id)


class TenantInvitationRepository(BaseRepository[TenantInvitation]):
    """Repository for tenant invitation operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, TenantInvitation)
    
    async def get_by_token(self, invitation_token: str) -> Optional[TenantInvitation]:
        """Get invitation by token."""
        return await self.get_by_field("invitation_token", invitation_token)
    
    async def get_tenant_invitations(
        self, 
        tenant_id: UUID,
        pending_only: bool = True
    ) -> List[TenantInvitation]:
        """Get invitations for a tenant."""
        filters = {"tenant_id": tenant_id}
        
        if pending_only:
            filters["is_accepted"] = False
        
        return await self.list(
            filters=filters,
            order_by="-created_at",
            relationships=["invited_by_user"]
        )
    
    async def get_invitations_by_email(
        self, 
        email: str,
        tenant_id: Optional[UUID] = None
    ) -> List[TenantInvitation]:
        """Get invitations by email."""
        filters = {"email": email}
        
        if tenant_id:
            filters["tenant_id"] = tenant_id
        
        return await self.list(
            filters=filters,
            order_by="-created_at"
        )
    
    async def accept_invitation(
        self, 
        invitation_id: UUID, 
        user_id: UUID
    ) -> bool:
        """Accept a tenant invitation."""
        from datetime import datetime
        return await self.update(
            invitation_id,
            {
                "is_accepted": True,
                "accepted_at": datetime.now(timezone.utc),
                "accepted_by": user_id
            }
        ) is not None


class TenantUsageRepository(BaseRepository[UsageRecord]):
    """Repository for tenant usage records."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, UsageRecord)
    
    async def get_latest_usage(
        self, 
        tenant_id: UUID,
        metric_name: str
    ) -> Optional[UsageRecord]:
        """Get latest usage record for a tenant metric."""
        query = select(UsageRecord).where(
            UsageRecord.tenant_id == tenant_id,
            UsageRecord.metric_name == metric_name,
            UsageRecord.is_deleted == False
        ).order_by(UsageRecord.timestamp.desc()).limit(1)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_usage_range(
        self,
        tenant_id: UUID,
        start_date: str,
        end_date: str,
        metric_name: Optional[str] = None
    ) -> List[UsageRecord]:
        """Get usage records for a date range."""
        from datetime import datetime
        
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        
        query = select(UsageRecord).where(
            UsageRecord.tenant_id == tenant_id,
            UsageRecord.timestamp >= start,
            UsageRecord.timestamp <= end,
            UsageRecord.is_deleted == False
        )
        
        if metric_name:
            query = query.where(UsageRecord.metric_name == metric_name)
        
        query = query.order_by(UsageRecord.timestamp.asc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def record_usage(
        self,
        tenant_id: UUID,
        subscription_id: UUID,
        metric_name: str,
        quantity: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UsageRecord:
        """Record usage for a tenant."""
        from datetime import datetime
        
        usage_data = {
            "tenant_id": tenant_id,
            "subscription_id": subscription_id,
            "metric_name": metric_name,
            "quantity": quantity,
            "timestamp": datetime.now(timezone.utc),
            "metadata": metadata
        }
        
        return await self.create(usage_data)