"""
Partner Dashboard API endpoints
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.partner import Partner, PartnerCustomer, Commission
from app.schemas.partner import PartnerDashboardResponse, CommissionSummary
from app.core.security import get_current_partner
from app.core.commission import CommissionCalculator
from app.core.territory import TerritoryValidator

router = APIRouter(prefix="/partners/{partner_id}/dashboard", tags=["partner-dashboard"])


class DashboardMetrics(BaseModel):
    customers_total: int = Field(..., description="Total number of customers")
    customers_active: int = Field(..., description="Number of active customers")
    customers_this_month: int = Field(..., description="New customers this month")
    revenue: Dict[str, float] = Field(..., description="Revenue breakdown")
    commissions: Dict[str, float] = Field(..., description="Commission breakdown")
    targets: Dict[str, Dict[str, float]] = Field(..., description="Performance targets")


class RecentCustomer(BaseModel):
    id: str
    name: str
    service: str
    signup_date: datetime
    status: str
    revenue: float
    commission: float


class SalesGoal(BaseModel):
    id: str
    title: str
    target: float
    current: float
    progress: float
    deadline: datetime
    status: str


@router.get("", response_model=PartnerDashboardResponse)
async def get_partner_dashboard(
    partner_id: str,
    db: Session = Depends(get_db),
    current_partner: Partner = Depends(get_current_partner)
) -> PartnerDashboardResponse:
    """
    Get comprehensive partner dashboard data
    """
    
    # Verify partner access
    if current_partner.id != partner_id:
        raise HTTPException(status_code=403, detail="Access denied to partner data")
    
    # Get partner details
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # Calculate date ranges
    now = datetime.utcnow()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (start_of_month - timedelta(days=1)).replace(day=1)
    last_month_end = start_of_month - timedelta(seconds=1)
    
    # Get customer metrics
    customers_query = db.query(PartnerCustomer).filter(
        PartnerCustomer.partner_id == partner_id
    )
    
    customers_total = customers_query.count()
    customers_active = customers_query.filter(
        PartnerCustomer.status == "active"
    ).count()
    customers_this_month = customers_query.filter(
        PartnerCustomer.created_at >= start_of_month
    ).count()
    
    # Calculate revenue metrics
    revenue_total = db.query(db.func.sum(PartnerCustomer.mrr)).filter(
        PartnerCustomer.partner_id == partner_id,
        PartnerCustomer.status == "active"
    ).scalar() or 0.0
    
    revenue_this_month = db.query(db.func.sum(PartnerCustomer.mrr)).filter(
        PartnerCustomer.partner_id == partner_id,
        PartnerCustomer.created_at >= start_of_month,
        PartnerCustomer.status == "active"
    ).scalar() or 0.0
    
    revenue_last_month = db.query(db.func.sum(PartnerCustomer.mrr)).filter(
        PartnerCustomer.partner_id == partner_id,
        PartnerCustomer.created_at.between(last_month_start, last_month_end),
        PartnerCustomer.status == "active"
    ).scalar() or 0.0
    
    # Calculate growth rate
    revenue_growth = 0.0
    if revenue_last_month > 0:
        revenue_growth = ((revenue_this_month - revenue_last_month) / revenue_last_month) * 100
    
    # Get commission data
    commission_calculator = CommissionCalculator()
    
    commissions_query = db.query(Commission).filter(
        Commission.partner_id == partner_id
    )
    
    commission_earned = commissions_query.filter(
        Commission.status == "paid"
    ).with_entities(db.func.sum(Commission.amount)).scalar() or 0.0
    
    commission_pending = commissions_query.filter(
        Commission.status == "pending"
    ).with_entities(db.func.sum(Commission.amount)).scalar() or 0.0
    
    commission_this_month = commissions_query.filter(
        Commission.created_at >= start_of_month
    ).with_entities(db.func.sum(Commission.amount)).scalar() or 0.0
    
    # Get recent customers
    recent_customers_data = db.query(PartnerCustomer).filter(
        PartnerCustomer.partner_id == partner_id
    ).order_by(PartnerCustomer.created_at.desc()).limit(10).all()
    
    recent_customers = []
    for customer in recent_customers_data:
        # Calculate commission for this customer
        commission_amount = commission_calculator.calculate_customer_commission(
            customer, partner
        )
        
        recent_customers.append(RecentCustomer(
            id=customer.id,
            name=customer.name,
            service=customer.service_plan,
            signup_date=customer.created_at,
            status=customer.status,
            revenue=customer.mrr,
            commission=commission_amount
        ))
    
    # Get sales goals (from partner configuration)
    sales_goals = [
        SalesGoal(
            id="monthly-customers",
            title="Monthly New Customers",
            target=partner.monthly_customer_target,
            current=customers_this_month,
            progress=(customers_this_month / partner.monthly_customer_target * 100) if partner.monthly_customer_target > 0 else 0,
            deadline=now.replace(day=31, hour=23, minute=59, second=59) if now.month != 12 else now.replace(year=now.year+1, month=1, day=31, hour=23, minute=59, second=59),
            status="active" if customers_this_month < partner.monthly_customer_target else "completed"
        ),
        SalesGoal(
            id="monthly-revenue",
            title="Monthly Revenue Target", 
            target=partner.monthly_revenue_target,
            current=revenue_this_month,
            progress=(revenue_this_month / partner.monthly_revenue_target * 100) if partner.monthly_revenue_target > 0 else 0,
            deadline=now.replace(day=31, hour=23, minute=59, second=59) if now.month != 12 else now.replace(year=now.year+1, month=1, day=31, hour=23, minute=59, second=59),
            status="active" if revenue_this_month < partner.monthly_revenue_target else "completed"
        )
    ]
    
    return PartnerDashboardResponse(
        partner={
            "id": partner.id,
            "name": partner.company_name,
            "partner_code": partner.partner_code,
            "territory": partner.territory,
            "join_date": partner.created_at.isoformat(),
            "status": partner.status,
            "tier": partner.tier,
            "contact": {
                "name": partner.contact_name,
                "email": partner.contact_email,
                "phone": partner.contact_phone
            }
        },
        performance={
            "customers_total": customers_total,
            "customers_active": customers_active,
            "customers_this_month": customers_this_month,
            "revenue": {
                "total": revenue_total,
                "this_month": revenue_this_month,
                "last_month": revenue_last_month,
                "growth": revenue_growth
            },
            "commissions": {
                "earned": commission_earned,
                "pending": commission_pending,
                "this_month": commission_this_month,
                "last_payout": partner.last_payout_amount or 0.0,
                "next_payout_date": partner.next_payout_date.isoformat() if partner.next_payout_date else None
            },
            "targets": {
                "monthly_customers": {
                    "current": customers_this_month,
                    "target": partner.monthly_customer_target,
                    "unit": "customers"
                },
                "monthly_revenue": {
                    "current": revenue_this_month,
                    "target": partner.monthly_revenue_target,
                    "unit": "revenue"
                },
                "quarterly_growth": {
                    "current": revenue_growth,
                    "target": partner.growth_target or 10.0,
                    "unit": "percentage"
                }
            }
        },
        recent_customers=recent_customers,
        sales_goals=sales_goals
    )


@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    partner_id: str,
    period: str = Query("month", regex="^(day|week|month|quarter|year)$"),
    db: Session = Depends(get_db),
    current_partner: Partner = Depends(get_current_partner)
) -> DashboardMetrics:
    """
    Get specific dashboard metrics for a time period
    """
    
    if current_partner.id != partner_id:
        raise HTTPException(status_code=403, detail="Access denied to partner data")
    
    # Calculate date range based on period
    now = datetime.utcnow()
    if period == "day":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "quarter":
        quarter_start_month = ((now.month - 1) // 3) * 3 + 1
        start_date = now.replace(month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:  # year
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get metrics for the period
    customers_total = db.query(PartnerCustomer).filter(
        PartnerCustomer.partner_id == partner_id
    ).count()
    
    customers_active = db.query(PartnerCustomer).filter(
        PartnerCustomer.partner_id == partner_id,
        PartnerCustomer.status == "active"
    ).count()
    
    customers_this_period = db.query(PartnerCustomer).filter(
        PartnerCustomer.partner_id == partner_id,
        PartnerCustomer.created_at >= start_date
    ).count()
    
    # Revenue calculations
    revenue_total = db.query(db.func.sum(PartnerCustomer.mrr)).filter(
        PartnerCustomer.partner_id == partner_id,
        PartnerCustomer.status == "active"
    ).scalar() or 0.0
    
    revenue_this_period = db.query(db.func.sum(PartnerCustomer.mrr)).filter(
        PartnerCustomer.partner_id == partner_id,
        PartnerCustomer.created_at >= start_date,
        PartnerCustomer.status == "active"
    ).scalar() or 0.0
    
    # Commission calculations
    commission_earned = db.query(db.func.sum(Commission.amount)).filter(
        Commission.partner_id == partner_id,
        Commission.status == "paid"
    ).scalar() or 0.0
    
    commission_pending = db.query(db.func.sum(Commission.amount)).filter(
        Commission.partner_id == partner_id,
        Commission.status == "pending"
    ).scalar() or 0.0
    
    commission_this_period = db.query(db.func.sum(Commission.amount)).filter(
        Commission.partner_id == partner_id,
        Commission.created_at >= start_date
    ).scalar() or 0.0
    
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    
    return DashboardMetrics(
        customers_total=customers_total,
        customers_active=customers_active,
        customers_this_month=customers_this_period,
        revenue={
            "total": revenue_total,
            "this_period": revenue_this_period,
            "average_per_customer": revenue_total / customers_active if customers_active > 0 else 0.0
        },
        commissions={
            "earned": commission_earned,
            "pending": commission_pending,
            "this_period": commission_this_period,
            "average_rate": (commission_earned / revenue_total) if revenue_total > 0 else 0.0
        },
        targets={
            "monthly_customers": {
                "current": customers_this_period if period == "month" else 0,
                "target": partner.monthly_customer_target if partner else 0,
                "achievement_rate": (customers_this_period / partner.monthly_customer_target * 100) if partner and partner.monthly_customer_target > 0 else 0
            },
            "monthly_revenue": {
                "current": revenue_this_period if period == "month" else 0,
                "target": partner.monthly_revenue_target if partner else 0,
                "achievement_rate": (revenue_this_period / partner.monthly_revenue_target * 100) if partner and partner.monthly_revenue_target > 0 else 0
            }
        }
    )