"""
Reseller services for ISP Framework

Provides business logic for reseller management.
Leverages shared base service patterns for DRY implementation.
"""

import secrets
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, desc, func

from dotmac_shared.services.isp_base_service import ISPBaseService
from dotmac_shared.api.exception_handlers import standard_exception_handler

from .models import (
    ISPReseller, 
    ResellerApplication, 
    ResellerCustomer,
    ResellerOpportunity,
    ResellerCommission
)
from .schemas import (
    ResellerApplicationCreate,
    ResellerApplicationResponse,
    ResellerResponse
)


class ResellerApplicationService(ISPBaseService):
    """Service for managing reseller applications from website signup."""
    
    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(tenant_id, db)
    
    async def create_application(
        self, 
        application_data: ResellerApplicationCreate,
        ip_address: Optional[str] = None
    ) -> ResellerApplication:
        """
        Create new reseller application from website form.
        Generates application ID and sets up tracking.
        """
        
        # Generate unique application ID
        application_id = f"APP-{date.today().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"
        
        # Create application record
        application = ResellerApplication(
            application_id=application_id,
            application_status="submitted",
            **application_data.dict(),
            submitted_at=datetime.utcnow()
        )
        
        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)
        
        # TODO: Send notification email to admin
        # TODO: Send confirmation email to applicant
        
        return application
    
    async def get_pending_applications(self, limit: int = 50) -> List[ResellerApplication]:
        """Get applications pending review."""
        
        return self.db.query(ResellerApplication).filter(
            ResellerApplication.application_status.in_(["submitted", "under_review"])
        ).order_by(desc(ResellerApplication.submitted_at)).limit(limit).all()
    
    async def approve_application(
        self,
        application_id: str,
        reviewer_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approve reseller application and create reseller account.
        Returns both application and created reseller info.
        """
        
        application = self.db.query(ResellerApplication).filter_by(
            application_id=application_id
        ).first()
        
        if not application or not application.can_be_approved:
            raise ValueError("Application cannot be approved")
        
        # Create reseller from application
        reseller_service = ResellerService(self.db, self.tenant_id)
        reseller = await reseller_service.create_from_application(application)
        
        # Update application status
        application.application_status = "approved"
        application.reviewed_by = reviewer_id
        application.reviewed_at = datetime.utcnow()
        application.decision_date = date.today()
        application.approved_reseller_id = reseller.id
        application.review_notes = notes
        
        self.db.commit()
        
        # TODO: Send approval email with login credentials
        # TODO: Send welcome package
        
        return {
            "application": application,
            "reseller": reseller,
            "next_steps": [
                "Portal account creation",
                "Contract signing",
                "Training enrollment"
            ]
        }
    
    async def reject_application(
        self,
        application_id: str,
        reviewer_id: str,
        reason: str
    ) -> ResellerApplication:
        """Reject reseller application with reason."""
        
        application = self.db.query(ResellerApplication).filter_by(
            application_id=application_id
        ).first()
        
        if not application or not application.can_be_approved:
            raise ValueError("Application cannot be rejected")
        
        application.application_status = "rejected"
        application.reviewed_by = reviewer_id
        application.reviewed_at = datetime.utcnow()
        application.decision_date = date.today()
        application.decision_reason = reason
        
        self.db.commit()
        
        # TODO: Send rejection email
        
        return application


class ResellerService(ISPBaseService):
    """Service for managing active resellers."""
    
    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(tenant_id, db)
    
    async def create_from_application(
        self, 
        application: ResellerApplication
    ) -> ISPReseller:
        """Create reseller account from approved application."""
        
        # Generate reseller ID
        reseller_id = f"RES-{date.today().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"
        
        # Map application data to reseller fields
        reseller_data = {
            "reseller_id": reseller_id,
            "company_name": application.company_name,
            "legal_name": application.legal_company_name,
            "reseller_type": "authorized_dealer",  # Default type
            "reseller_status": "pending_approval",  # Requires additional setup
            
            # Contact information
            "primary_contact_name": application.contact_name,
            "primary_contact_email": application.contact_email,
            "primary_contact_phone": application.contact_phone,
            
            # Business details
            "website_url": application.website_url,
            "business_type": application.business_type,
            "years_in_business": application.years_in_business,
            
            # Partnership details from application
            "service_territories": application.desired_territories,
            "target_customer_segments": application.target_customer_segments,
            "estimated_monthly_customers": application.estimated_monthly_customers,
            
            # Default settings
            "portal_enabled": True,
            "commission_structure": "percentage",
            "base_commission_rate": Decimal("10.00"),  # Default 10%
            
            # Custom fields from application
            "custom_fields": {
                "application_id": application.application_id,
                "telecom_experience_years": application.telecom_experience_years,
                "business_description": application.business_description,
                "annual_revenue_range": application.annual_revenue_range
            }
        }
        
        reseller = ISPReseller(**reseller_data)
        self.db.add(reseller)
        self.db.commit()
        self.db.refresh(reseller)
        
        return reseller
    
    async def get_reseller_dashboard(self, reseller_id: UUID) -> Dict[str, Any]:
        """Get comprehensive dashboard data for reseller."""
        
        reseller = self.db.query(ISPReseller).filter_by(id=reseller_id).first()
        if not reseller:
            raise ValueError("Reseller not found")
        
        # Get performance metrics
        total_customers = self.db.query(ResellerCustomer).filter_by(
            reseller_id=reseller_id
        ).count()
        
        active_customers = self.db.query(ResellerCustomer).filter(
            and_(
                ResellerCustomer.reseller_id == reseller_id,
                ResellerCustomer.relationship_status == "active"
            )
        ).count()
        
        # Get commission data
        ytd_commissions = self.db.query(
            func.sum(ResellerCommission.commission_amount)
        ).filter(
            and_(
                ResellerCommission.reseller_id == reseller_id,
                ResellerCommission.earned_date >= date(date.today().year, 1, 1)
            )
        ).scalar() or Decimal("0.00")
        
        pending_commissions = self.db.query(
            func.sum(ResellerCommission.commission_amount)
        ).filter(
            and_(
                ResellerCommission.reseller_id == reseller_id,
                ResellerCommission.payment_status == "pending"
            )
        ).scalar() or Decimal("0.00")
        
        # Get active opportunities
        active_opportunities = self.db.query(ResellerOpportunity).filter(
            and_(
                ResellerOpportunity.reseller_id == reseller_id,
                ResellerOpportunity.stage.notin_(["closed_won", "closed_lost"])
            )
        ).count()
        
        return {
            "reseller_info": reseller,
            "metrics": {
                "total_customers": total_customers,
                "active_customers": active_customers,
                "ytd_commissions_earned": ytd_commissions,
                "pending_commission_payments": pending_commissions,
                "active_opportunities": active_opportunities,
                "conversion_rate": self._calculate_conversion_rate(reseller_id),
                "average_customer_value": self._calculate_avg_customer_value(reseller_id)
            },
            "goals": {
                "annual_quota": reseller.annual_quota,
                "quota_achievement": reseller.quota_achievement,
                "customers_needed_for_quota": self._customers_needed_for_quota(reseller)
            },
            "recent_activity": {
                "new_customers_this_month": self._get_new_customers_this_month(reseller_id),
                "recent_commissions": self._get_recent_commissions(reseller_id, limit=5),
                "upcoming_opportunities": self._get_upcoming_opportunities(reseller_id, limit=5)
            }
        }
    
    async def activate_reseller(
        self,
        reseller_id: UUID,
        activation_data: Dict[str, Any]
    ) -> ISPReseller:
        """Activate reseller after completing onboarding requirements."""
        
        reseller = self.db.query(ISPReseller).filter_by(id=reseller_id).first()
        if not reseller:
            raise ValueError("Reseller not found")
        
        # Update reseller with activation data
        reseller.reseller_status = "active"
        reseller.agreement_start_date = activation_data.get("agreement_start_date", date.today())
        reseller.agreement_end_date = activation_data.get("agreement_end_date")
        reseller.assigned_support_rep = activation_data.get("support_rep")
        
        # Set commission structure
        if "commission_rate" in activation_data:
            reseller.base_commission_rate = activation_data["commission_rate"]
        
        # Set quotas if provided
        if "annual_quota" in activation_data:
            reseller.annual_quota = activation_data["annual_quota"]
        
        self.db.commit()
        
        # TODO: Send activation email
        # TODO: Create portal login credentials
        
        return reseller
    
    def _calculate_conversion_rate(self, reseller_id: UUID) -> Optional[Decimal]:
        """Calculate opportunity to customer conversion rate."""
        
        total_opportunities = self.db.query(ResellerOpportunity).filter_by(
            reseller_id=reseller_id
        ).count()
        
        won_opportunities = self.db.query(ResellerOpportunity).filter(
            and_(
                ResellerOpportunity.reseller_id == reseller_id,
                ResellerOpportunity.stage == "closed_won"
            )
        ).count()
        
        if total_opportunities > 0:
            return Decimal(won_opportunities) / Decimal(total_opportunities) * 100
        return None
    
    def _calculate_avg_customer_value(self, reseller_id: UUID) -> Decimal:
        """Calculate average customer lifetime value."""
        
        avg_value = self.db.query(
            func.avg(ResellerCustomer.lifetime_value)
        ).filter_by(reseller_id=reseller_id).scalar()
        
        return avg_value or Decimal("0.00")
    
    def _customers_needed_for_quota(self, reseller: ISPReseller) -> Optional[int]:
        """Calculate customers needed to reach annual quota."""
        
        if not reseller.annual_quota:
            return None
        
        avg_customer_value = self._calculate_avg_customer_value(reseller.id)
        if avg_customer_value <= 0:
            return None
        
        remaining_quota = reseller.annual_quota - reseller.ytd_sales
        return int(remaining_quota / avg_customer_value)
    
    def _get_new_customers_this_month(self, reseller_id: UUID) -> int:
        """Get count of new customers added this month."""
        
        month_start = date.today().replace(day=1)
        return self.db.query(ResellerCustomer).filter(
            and_(
                ResellerCustomer.reseller_id == reseller_id,
                ResellerCustomer.relationship_start_date >= month_start
            )
        ).count()
    
    def _get_recent_commissions(self, reseller_id: UUID, limit: int = 5) -> List[ResellerCommission]:
        """Get recent commission records."""
        
        return self.db.query(ResellerCommission).filter_by(
            reseller_id=reseller_id
        ).order_by(desc(ResellerCommission.earned_date)).limit(limit).all()
    
    def _get_upcoming_opportunities(self, reseller_id: UUID, limit: int = 5) -> List[ResellerOpportunity]:
        """Get upcoming opportunities by expected close date."""
        
        return self.db.query(ResellerOpportunity).filter(
            and_(
                ResellerOpportunity.reseller_id == reseller_id,
                ResellerOpportunity.stage.notin_(["closed_won", "closed_lost"]),
                ResellerOpportunity.expected_close_date.isnot(None)
            )
        ).order_by(ResellerOpportunity.expected_close_date).limit(limit).all()


class ResellerCustomerService(ISPBaseService):
    """Service for managing reseller-customer relationships."""
    
    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(tenant_id, db)
    
    async def assign_customer_to_reseller(
        self,
        customer_id: UUID,
        reseller_id: UUID,
        assignment_data: Dict[str, Any]
    ) -> ResellerCustomer:
        """Assign customer to reseller with relationship tracking."""
        
        # Check if relationship already exists
        existing = self.db.query(ResellerCustomer).filter(
            and_(
                ResellerCustomer.customer_id == customer_id,
                ResellerCustomer.reseller_id == reseller_id
            )
        ).first()
        
        if existing:
            raise ValueError("Customer is already assigned to this reseller")
        
        relationship = ResellerCustomer(
            reseller_id=reseller_id,
            customer_id=customer_id,
            **assignment_data
        )
        
        self.db.add(relationship)
        self.db.commit()
        self.db.refresh(relationship)
        
        # Update reseller customer counts
        await self._update_reseller_metrics(reseller_id)
        
        return relationship
    
    async def _update_reseller_metrics(self, reseller_id: UUID):
        """Update reseller performance metrics."""
        
        reseller = self.db.query(ISPReseller).filter_by(id=reseller_id).first()
        if not reseller:
            return
        
        # Update customer counts
        total_customers = self.db.query(ResellerCustomer).filter_by(
            reseller_id=reseller_id
        ).count()
        
        active_customers = self.db.query(ResellerCustomer).filter(
            and_(
                ResellerCustomer.reseller_id == reseller_id,
                ResellerCustomer.relationship_status == "active"
            )
        ).count()
        
        reseller.total_customers = total_customers
        reseller.active_customers = active_customers
        
        self.db.commit()


# Export services
__all__ = [
    "ResellerApplicationService",
    "ResellerService",
    "ResellerCustomerService"
]