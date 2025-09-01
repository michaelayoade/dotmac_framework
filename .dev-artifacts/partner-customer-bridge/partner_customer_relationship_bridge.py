"""
Partner-Customer Relationship Bridge
Connects Management Partners to ISP customers across multiple tenants with unified visibility
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Set
from enum import Enum
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import json
import asyncio

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.database.base import Base
from dotmac_isp.shared.base_service import BaseService


class PartnerTenantRole(str, Enum):
    OWNER = "owner"                    # Partner owns the tenant
    MANAGER = "manager"                # Partner manages the tenant
    RESELLER = "reseller"             # Partner sells services within tenant
    CONSULTANT = "consultant"          # Partner provides consulting services
    TECHNICAL_SUPPORT = "technical_support"  # Partner provides technical support


class CustomerEngagementLevel(str, Enum):
    DIRECT = "direct"                 # Partner directly manages customer
    SUPERVISED = "supervised"         # Partner oversees local reseller
    REFERRAL_ONLY = "referral_only"  # Partner only made referral
    SUPPORT_ONLY = "support_only"    # Partner only provides support


class RelationshipStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class CustomerLifecycleStage(str, Enum):
    PROSPECT = "prospect"
    LEAD = "lead"
    CUSTOMER = "customer"
    CHURNED = "churned"
    WIN_BACK = "win_back"


class PartnerTenantAssociation(Base):
    """Database model for partner-tenant relationships"""
    __tablename__ = "partner_tenant_associations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    role = Column(String(50), default=PartnerTenantRole.MANAGER.value)
    
    # Relationship details
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    status = Column(String(50), default=RelationshipStatus.ACTIVE.value)
    
    # Permissions and access
    permissions = Column(JSON, default=dict)
    access_level = Column(String(50), default="standard")
    
    # Performance tracking
    customers_managed = Column(Integer, default=0)
    revenue_attributed = Column(Numeric(12, 2), default=0.00)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON, default=dict)


class PartnerCustomerRelationship(Base):
    """Database model for partner-customer relationships across tenants"""
    __tablename__ = "partner_customer_relationships"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(String(100), nullable=False, index=True)
    customer_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    
    # Relationship details
    engagement_level = Column(String(50), default=CustomerEngagementLevel.DIRECT.value)
    lifecycle_stage = Column(String(50), default=CustomerLifecycleStage.PROSPECT.value)
    relationship_start = Column(DateTime, default=datetime.utcnow)
    
    # Attribution tracking
    acquisition_source = Column(String(100), nullable=True)  # How customer was acquired
    revenue_share_percentage = Column(Numeric(5, 4), default=0.0000)  # 0.0000 to 1.0000
    lifetime_value = Column(Numeric(12, 2), default=0.00)
    
    # Performance metrics
    satisfaction_score = Column(Numeric(3, 2), nullable=True)  # 0.00 to 10.00
    support_tickets_count = Column(Integer, default=0)
    last_interaction_date = Column(DateTime, nullable=True)
    
    # Status tracking
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Metadata and notes
    notes = Column(Text, nullable=True)
    metadata = Column(JSON, default=dict)


class PartnerTenantMetrics(BaseModel):
    partner_id: str
    tenant_id: str
    tenant_name: str
    period_start: datetime
    period_end: datetime
    
    # Customer metrics
    total_customers: int = Field(ge=0)
    new_customers: int = Field(ge=0)
    churned_customers: int = Field(ge=0)
    active_customers: int = Field(ge=0)
    
    # Revenue metrics
    total_revenue: float = Field(ge=0)
    recurring_revenue: float = Field(ge=0)
    one_time_revenue: float = Field(ge=0)
    attributed_revenue: float = Field(ge=0)
    
    # Performance metrics
    customer_satisfaction: Optional[float] = Field(None, ge=0, le=10)
    support_resolution_time_hours: Optional[float] = Field(None, ge=0)
    service_uptime_percentage: Optional[float] = Field(None, ge=0, le=100)
    
    # Growth metrics
    customer_growth_rate: float = 0.0
    revenue_growth_rate: float = 0.0
    market_penetration: Optional[float] = Field(None, ge=0, le=100)


class CrossTenantCustomerView(BaseModel):
    customer_id: str
    customer_name: str
    customer_email: str
    tenant_id: str
    tenant_name: str
    
    # Relationship info
    partner_engagement_level: CustomerEngagementLevel
    lifecycle_stage: CustomerLifecycleStage
    relationship_duration_days: int = Field(ge=0)
    
    # Financial info
    monthly_recurring_revenue: float = Field(ge=0)
    lifetime_value: float = Field(ge=0)
    revenue_share: float = Field(ge=0, le=1)
    
    # Performance info
    satisfaction_score: Optional[float] = Field(None, ge=0, le=10)
    last_interaction: Optional[datetime] = None
    support_tickets_30d: int = Field(ge=0)
    
    # Service info
    services: List[Dict[str, Any]] = []
    service_status: str = "active"


class PartnerPerformanceAggregation(BaseModel):
    partner_id: str
    partner_name: str
    reporting_period: Dict[str, datetime]
    
    # Aggregated metrics across all tenants
    total_tenants_managed: int = Field(ge=0)
    total_customers_across_tenants: int = Field(ge=0)
    total_revenue_attributed: float = Field(ge=0)
    
    # Performance averages
    average_customer_satisfaction: Optional[float] = Field(None, ge=0, le=10)
    average_revenue_per_customer: float = Field(ge=0)
    average_customer_lifetime_value: float = Field(ge=0)
    
    # Tenant-specific breakdowns
    tenant_performance: List[PartnerTenantMetrics] = []
    top_performing_tenants: List[str] = []
    underperforming_tenants: List[str] = []
    
    # Trends and insights
    growth_trends: Dict[str, float] = {}
    recommendations: List[str] = []


class PartnerCustomerBridgeService(BaseService):
    """Service for managing partner-customer relationships across tenants"""
    
    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db, tenant_id)
        self.tenant_cache = {}  # Cache for tenant information
    
    @standard_exception_handler
    async def establish_partner_tenant_relationship(
        self, 
        partner_id: str, 
        tenant_id: str, 
        role: PartnerTenantRole,
        permissions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Establish relationship between partner and tenant"""
        
        # Check if relationship already exists
        existing = await self._get_partner_tenant_association(partner_id, tenant_id)
        if existing:
            return {"status": "exists", "association_id": existing.id}
        
        # Create new association
        association = PartnerTenantAssociation(
            partner_id=partner_id,
            tenant_id=tenant_id,
            role=role.value,
            permissions=permissions or self._get_default_permissions(role),
            access_level=self._determine_access_level(role)
        )
        
        self.db.add(association)
        await self.db.flush()
        
        return {
            "status": "created",
            "association_id": str(association.id),
            "partner_id": partner_id,
            "tenant_id": tenant_id,
            "role": role.value,
            "permissions": association.permissions,
            "created_at": association.created_at.isoformat()
        }
    
    @standard_exception_handler
    async def link_customer_to_partner(
        self,
        partner_id: str,
        customer_id: str, 
        tenant_id: str,
        engagement_level: CustomerEngagementLevel,
        revenue_share_percentage: float = 0.0,
        acquisition_source: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create link between partner and customer"""
        
        # Validate partner has access to tenant
        partner_tenant = await self._get_partner_tenant_association(partner_id, tenant_id)
        if not partner_tenant:
            raise ValueError(f"Partner {partner_id} does not have access to tenant {tenant_id}")
        
        # Check if relationship already exists
        existing = await self._get_partner_customer_relationship(partner_id, customer_id, tenant_id)
        if existing:
            return {"status": "exists", "relationship_id": existing.id}
        
        # Create new relationship
        relationship = PartnerCustomerRelationship(
            partner_id=partner_id,
            customer_id=customer_id,
            tenant_id=tenant_id,
            engagement_level=engagement_level.value,
            revenue_share_percentage=revenue_share_percentage,
            acquisition_source=acquisition_source
        )
        
        self.db.add(relationship)
        await self.db.flush()
        
        # Update partner tenant association customer count
        partner_tenant.customers_managed += 1
        
        await self.db.commit()
        
        return {
            "status": "created",
            "relationship_id": str(relationship.id),
            "partner_id": partner_id,
            "customer_id": customer_id,
            "tenant_id": tenant_id,
            "engagement_level": engagement_level.value,
            "created_at": relationship.created_at.isoformat()
        }
    
    @standard_exception_handler
    async def get_partner_customers_across_tenants(
        self, 
        partner_id: str,
        include_inactive: bool = False,
        tenant_filter: Optional[List[str]] = None
    ) -> List[CrossTenantCustomerView]:
        """Get all customers associated with a partner across all their tenants"""
        
        # Get partner's tenant associations
        tenant_associations = await self._get_partner_tenants(partner_id)
        if not tenant_associations:
            return []
        
        # Filter tenants if specified
        tenant_ids = [assoc.tenant_id for assoc in tenant_associations]
        if tenant_filter:
            tenant_ids = [tid for tid in tenant_ids if tid in tenant_filter]
        
        # Get customer relationships across tenants
        customer_relationships = await self._get_partner_customer_relationships(
            partner_id, 
            tenant_ids, 
            include_inactive
        )
        
        # Build customer views
        customer_views = []
        for relationship in customer_relationships:
            # Get customer details from tenant
            customer_data = await self._get_customer_details(
                relationship.customer_id, 
                relationship.tenant_id
            )
            
            if customer_data:
                customer_view = CrossTenantCustomerView(
                    customer_id=relationship.customer_id,
                    customer_name=customer_data.get("name", "Unknown"),
                    customer_email=customer_data.get("email", ""),
                    tenant_id=relationship.tenant_id,
                    tenant_name=await self._get_tenant_name(relationship.tenant_id),
                    partner_engagement_level=CustomerEngagementLevel(relationship.engagement_level),
                    lifecycle_stage=CustomerLifecycleStage(relationship.lifecycle_stage),
                    relationship_duration_days=(datetime.utcnow() - relationship.relationship_start).days,
                    monthly_recurring_revenue=customer_data.get("monthly_recurring_revenue", 0.0),
                    lifetime_value=float(relationship.lifetime_value or 0.0),
                    revenue_share=float(relationship.revenue_share_percentage or 0.0),
                    satisfaction_score=float(relationship.satisfaction_score) if relationship.satisfaction_score else None,
                    last_interaction=relationship.last_interaction_date,
                    support_tickets_30d=relationship.support_tickets_count,
                    services=customer_data.get("services", []),
                    service_status=customer_data.get("service_status", "active")
                )
                customer_views.append(customer_view)
        
        return customer_views
    
    @standard_exception_handler
    async def get_partner_tenant_metrics(
        self, 
        partner_id: str,
        period_start: datetime,
        period_end: datetime,
        tenant_ids: Optional[List[str]] = None
    ) -> List[PartnerTenantMetrics]:
        """Get performance metrics for partner across their tenants"""
        
        # Get partner's tenants
        if tenant_ids is None:
            tenant_associations = await self._get_partner_tenants(partner_id)
            tenant_ids = [assoc.tenant_id for assoc in tenant_associations]
        
        metrics_list = []
        
        for tenant_id in tenant_ids:
            # Get customer relationships for this tenant
            relationships = await self._get_partner_customer_relationships(
                partner_id, [tenant_id], include_inactive=False
            )
            
            # Calculate metrics
            total_customers = len(relationships)
            active_customers = len([r for r in relationships if r.is_active])
            
            # Get revenue data from tenant
            revenue_data = await self._get_tenant_revenue_data(
                partner_id, tenant_id, period_start, period_end
            )
            
            # Calculate growth metrics
            previous_period_start = period_start - (period_end - period_start)
            previous_revenue_data = await self._get_tenant_revenue_data(
                partner_id, tenant_id, previous_period_start, period_start
            )
            
            revenue_growth_rate = 0.0
            if previous_revenue_data["total_revenue"] > 0:
                revenue_growth_rate = (
                    (revenue_data["total_revenue"] - previous_revenue_data["total_revenue"]) /
                    previous_revenue_data["total_revenue"]
                )
            
            tenant_metrics = PartnerTenantMetrics(
                partner_id=partner_id,
                tenant_id=tenant_id,
                tenant_name=await self._get_tenant_name(tenant_id),
                period_start=period_start,
                period_end=period_end,
                total_customers=total_customers,
                new_customers=revenue_data.get("new_customers", 0),
                churned_customers=revenue_data.get("churned_customers", 0),
                active_customers=active_customers,
                total_revenue=revenue_data["total_revenue"],
                recurring_revenue=revenue_data["recurring_revenue"],
                one_time_revenue=revenue_data["one_time_revenue"],
                attributed_revenue=revenue_data["attributed_revenue"],
                customer_satisfaction=revenue_data.get("customer_satisfaction"),
                support_resolution_time_hours=revenue_data.get("support_resolution_time_hours"),
                service_uptime_percentage=revenue_data.get("service_uptime_percentage"),
                revenue_growth_rate=revenue_growth_rate
            )
            
            metrics_list.append(tenant_metrics)
        
        return metrics_list
    
    @standard_exception_handler
    async def update_customer_lifecycle_stage(
        self,
        partner_id: str,
        customer_id: str,
        tenant_id: str,
        new_stage: CustomerLifecycleStage,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update customer lifecycle stage in partner relationship"""
        
        relationship = await self._get_partner_customer_relationship(partner_id, customer_id, tenant_id)
        if not relationship:
            raise ValueError(f"No relationship found between partner {partner_id} and customer {customer_id}")
        
        old_stage = relationship.lifecycle_stage
        relationship.lifecycle_stage = new_stage.value
        relationship.updated_at = datetime.utcnow()
        
        if notes:
            existing_notes = relationship.notes or ""
            relationship.notes = f"{existing_notes}\n[{datetime.utcnow().isoformat()}] Stage change: {old_stage} -> {new_stage.value}\nNotes: {notes}"
        
        await self.db.commit()
        
        return {
            "partner_id": partner_id,
            "customer_id": customer_id,
            "tenant_id": tenant_id,
            "old_stage": old_stage,
            "new_stage": new_stage.value,
            "updated_at": relationship.updated_at.isoformat()
        }
    
    @standard_exception_handler
    async def track_partner_customer_interaction(
        self,
        partner_id: str,
        customer_id: str,
        tenant_id: str,
        interaction_type: str,
        outcome: Optional[str] = None,
        satisfaction_impact: Optional[float] = None
    ) -> Dict[str, Any]:
        """Track interaction between partner and customer"""
        
        relationship = await self._get_partner_customer_relationship(partner_id, customer_id, tenant_id)
        if not relationship:
            raise ValueError(f"No relationship found between partner {partner_id} and customer {customer_id}")
        
        # Update last interaction
        relationship.last_interaction_date = datetime.utcnow()
        
        # Update satisfaction score if provided
        if satisfaction_impact is not None:
            current_satisfaction = float(relationship.satisfaction_score or 7.0)
            new_satisfaction = max(0.0, min(10.0, current_satisfaction + satisfaction_impact))
            relationship.satisfaction_score = new_satisfaction
        
        # Add interaction to metadata
        if "interactions" not in relationship.metadata:
            relationship.metadata["interactions"] = []
        
        interaction_record = {
            "type": interaction_type,
            "timestamp": datetime.utcnow().isoformat(),
            "outcome": outcome,
            "satisfaction_impact": satisfaction_impact
        }
        
        relationship.metadata["interactions"].append(interaction_record)
        
        await self.db.commit()
        
        return {
            "interaction_recorded": True,
            "interaction_type": interaction_type,
            "outcome": outcome,
            "satisfaction_score": float(relationship.satisfaction_score) if relationship.satisfaction_score else None,
            "recorded_at": relationship.last_interaction_date.isoformat()
        }
    
    async def _get_partner_tenant_association(self, partner_id: str, tenant_id: str) -> Optional[PartnerTenantAssociation]:
        """Get partner-tenant association"""
        # Mock implementation - would use actual SQLAlchemy query
        return None
    
    async def _get_partner_customer_relationship(self, partner_id: str, customer_id: str, tenant_id: str) -> Optional[PartnerCustomerRelationship]:
        """Get partner-customer relationship"""
        # Mock implementation - would use actual SQLAlchemy query
        return None
    
    async def _get_partner_tenants(self, partner_id: str) -> List[PartnerTenantAssociation]:
        """Get all tenants associated with a partner"""
        # Mock implementation
        return []
    
    async def _get_partner_customer_relationships(
        self, 
        partner_id: str, 
        tenant_ids: List[str], 
        include_inactive: bool
    ) -> List[PartnerCustomerRelationship]:
        """Get all customer relationships for partner across specified tenants"""
        # Mock implementation
        return []
    
    async def _get_customer_details(self, customer_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get customer details from specific tenant"""
        # Mock implementation - would query tenant-specific customer data
        return {
            "name": "Sample Customer",
            "email": "customer@example.com", 
            "monthly_recurring_revenue": 99.99,
            "services": [
                {"name": "Fiber 100Mbps", "status": "active", "mrr": 99.99}
            ],
            "service_status": "active"
        }
    
    async def _get_tenant_name(self, tenant_id: str) -> str:
        """Get tenant name from tenant ID"""
        if tenant_id not in self.tenant_cache:
            # Mock implementation - would query tenant data
            self.tenant_cache[tenant_id] = f"ISP Tenant {tenant_id[-4:]}"
        return self.tenant_cache[tenant_id]
    
    async def _get_tenant_revenue_data(
        self, 
        partner_id: str, 
        tenant_id: str, 
        period_start: datetime, 
        period_end: datetime
    ) -> Dict[str, Any]:
        """Get revenue data for partner from specific tenant"""
        # Mock implementation - would query actual revenue data
        return {
            "total_revenue": 50000.00,
            "recurring_revenue": 45000.00,
            "one_time_revenue": 5000.00,
            "attributed_revenue": 12500.00,  # 25% attribution
            "new_customers": 15,
            "churned_customers": 2,
            "customer_satisfaction": 8.4,
            "support_resolution_time_hours": 4.2,
            "service_uptime_percentage": 99.7
        }
    
    def _get_default_permissions(self, role: PartnerTenantRole) -> Dict[str, Any]:
        """Get default permissions based on role"""
        permissions_map = {
            PartnerTenantRole.OWNER: {
                "customer_management": "full",
                "revenue_visibility": "full", 
                "analytics_access": "full",
                "billing_access": "full",
                "support_access": "full"
            },
            PartnerTenantRole.MANAGER: {
                "customer_management": "full",
                "revenue_visibility": "full",
                "analytics_access": "full", 
                "billing_access": "readonly",
                "support_access": "full"
            },
            PartnerTenantRole.RESELLER: {
                "customer_management": "assigned_only",
                "revenue_visibility": "attributed_only",
                "analytics_access": "limited",
                "billing_access": "none",
                "support_access": "assigned_only"
            },
            PartnerTenantRole.CONSULTANT: {
                "customer_management": "readonly", 
                "revenue_visibility": "summary_only",
                "analytics_access": "full",
                "billing_access": "none",
                "support_access": "readonly"
            },
            PartnerTenantRole.TECHNICAL_SUPPORT: {
                "customer_management": "support_only",
                "revenue_visibility": "none",
                "analytics_access": "support_only",
                "billing_access": "none", 
                "support_access": "full"
            }
        }
        
        return permissions_map.get(role, {})
    
    def _determine_access_level(self, role: PartnerTenantRole) -> str:
        """Determine access level based on role"""
        access_levels = {
            PartnerTenantRole.OWNER: "admin",
            PartnerTenantRole.MANAGER: "manager",
            PartnerTenantRole.RESELLER: "standard",
            PartnerTenantRole.CONSULTANT: "readonly",
            PartnerTenantRole.TECHNICAL_SUPPORT: "support"
        }
        
        return access_levels.get(role, "standard")


__all__ = [
    "PartnerTenantRole",
    "CustomerEngagementLevel", 
    "RelationshipStatus",
    "CustomerLifecycleStage",
    "PartnerTenantAssociation",
    "PartnerCustomerRelationship",
    "PartnerTenantMetrics",
    "CrossTenantCustomerView",
    "PartnerPerformanceAggregation",
    "PartnerCustomerBridgeService"
]