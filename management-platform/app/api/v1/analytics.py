"""
Analytics API endpoints
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.core.auth import get_current_active_user
from app.core.deps import CurrentUser

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Analytics Models (temporary - should be moved to proper models)
class PartnerPerformance(BaseModel):
    partner_id: str = Field(..., description="Partner ID")
    partner_name: str = Field(..., description="Partner name")
    tier: str = Field(..., description="Partner tier")
    sales_count: int = Field(..., description="Number of sales")
    revenue: float = Field(..., description="Total revenue")
    commission: float = Field(..., description="Commission earned")
    performance_score: float = Field(..., description="Performance score")
    trend: str = Field(..., description="Performance trend")

class MonthlyCommission(BaseModel):
    month: str = Field(..., description="Month")
    total_commission: float = Field(..., description="Total commission")
    partners_paid: int = Field(..., description="Number of partners paid")
    average_commission: float = Field(..., description="Average commission")

class GrowthMetric(BaseModel):
    period: str = Field(..., description="Time period")
    new_partners: int = Field(..., description="New partners added")
    churned_partners: int = Field(..., description="Partners churned")
    net_growth: int = Field(..., description="Net growth")

class ChannelMetrics(BaseModel):
    total_partners: int = Field(..., description="Total partners")
    active_partners: int = Field(..., description="Active partners")
    pending_approvals: int = Field(..., description="Pending approvals")
    total_revenue: float = Field(..., description="Total revenue")
    commission_payout: float = Field(..., description="Commission payout")
    avg_deal_size: float = Field(..., description="Average deal size")
    conversion_rate: float = Field(..., description="Conversion rate")
    partner_satisfaction: float = Field(..., description="Partner satisfaction")
    territory_coverage: float = Field(..., description="Territory coverage")
    top_performers: List[PartnerPerformance] = Field(..., description="Top performers")
    revenue_by_tier: Dict[str, float] = Field(..., description="Revenue by tier")
    commission_by_month: List[MonthlyCommission] = Field(..., description="Commission by month")
    partner_growth: List[GrowthMetric] = Field(..., description="Partner growth")

class ChannelMetricsResponse(BaseModel):
    success: bool = True
    data: ChannelMetrics

class CommissionTrendData(BaseModel):
    period: str = Field(..., description="Time period")
    total_commission: float = Field(..., description="Total commission")
    approved_commission: float = Field(..., description="Approved commission")
    paid_commission: float = Field(..., description="Paid commission")
    pending_commission: float = Field(..., description="Pending commission")

class CommissionTrendsResponse(BaseModel):
    success: bool = True
    data: List[CommissionTrendData]

class PartnerGrowthData(BaseModel):
    period: str = Field(..., description="Time period")
    new_partners: int = Field(..., description="New partners")
    total_partners: int = Field(..., description="Total partners")
    churn_rate: float = Field(..., description="Churn rate")
    growth_rate: float = Field(..., description="Growth rate")

class PartnerGrowthResponse(BaseModel):
    success: bool = True
    data: List[PartnerGrowthData]

class SalesForecastData(BaseModel):
    period: str = Field(..., description="Forecast period")
    predicted_sales: float = Field(..., description="Predicted sales")
    confidence_interval: List[float] = Field(..., description="Confidence interval")
    factors: Dict[str, float] = Field(..., description="Contributing factors")

class SalesForecastResponse(BaseModel):
    success: bool = True
    data: List[SalesForecastData]

class TerritoryPerformanceData(BaseModel):
    territory: str = Field(..., description="Territory name")
    partners_count: int = Field(..., description="Number of partners")
    revenue: float = Field(..., description="Territory revenue")
    commission: float = Field(..., description="Territory commission")
    market_penetration: float = Field(..., description="Market penetration")
    satisfaction_score: float = Field(..., description="Satisfaction score")

class TerritoryPerformanceResponse(BaseModel):
    success: bool = True
    data: List[TerritoryPerformanceData]

# Mock data for development/testing
MOCK_CHANNEL_METRICS = ChannelMetrics(
    total_partners=156,
    active_partners=142,
    pending_approvals=8,
    total_revenue=1850000.0,
    commission_payout=185000.0,
    avg_deal_size=12500.0,
    conversion_rate=0.68,
    partner_satisfaction=4.2,
    territory_coverage=0.85,
    top_performers=[
        PartnerPerformance(
            partner_id="partner-001",
            partner_name="Acme ISP Solutions",
            tier="GOLD",
            sales_count=45,
            revenue=562500.0,
            commission=56250.0,
            performance_score=95.2,
            trend="up"
        ),
        PartnerPerformance(
            partner_id="partner-002",
            partner_name="TechNet Partners",
            tier="SILVER",
            sales_count=32,
            revenue=400000.0,
            commission=40000.0,
            performance_score=88.7,
            trend="stable"
        ),
        PartnerPerformance(
            partner_id="partner-004",
            partner_name="NetworkPro Solutions",
            tier="GOLD",
            sales_count=38,
            revenue=475000.0,
            commission=47500.0,
            performance_score=91.3,
            trend="up"
        )
    ],
    revenue_by_tier={
        "DIAMOND": 750000.0,
        "PLATINUM": 520000.0,
        "GOLD": 380000.0,
        "SILVER": 200000.0,
        "BRONZE": 50000.0
    },
    commission_by_month=[
        MonthlyCommission(
            month="2024-01",
            total_commission=45000.0,
            partners_paid=128,
            average_commission=351.56
        ),
        MonthlyCommission(
            month="2024-02",
            total_commission=52000.0,
            partners_paid=135,
            average_commission=385.19
        ),
        MonthlyCommission(
            month="2024-03",
            total_commission=48000.0,
            partners_paid=142,
            average_commission=338.03
        )
    ],
    partner_growth=[
        GrowthMetric(
            period="2024-Q1",
            new_partners=25,
            churned_partners=3,
            net_growth=22
        ),
        GrowthMetric(
            period="2024-Q2",
            new_partners=18,
            churned_partners=5,
            net_growth=13
        )
    ]
)

MOCK_COMMISSION_TRENDS = [
    CommissionTrendData(
        period="2024-01",
        total_commission=45000.0,
        approved_commission=42000.0,
        paid_commission=40000.0,
        pending_commission=3000.0
    ),
    CommissionTrendData(
        period="2024-02",
        total_commission=52000.0,
        approved_commission=48000.0,
        paid_commission=45000.0,
        pending_commission=4000.0
    ),
    CommissionTrendData(
        period="2024-03",
        total_commission=48000.0,
        approved_commission=45000.0,
        paid_commission=42000.0,
        pending_commission=3000.0
    )
]

MOCK_PARTNER_GROWTH = [
    PartnerGrowthData(
        period="2024-01",
        new_partners=8,
        total_partners=128,
        churn_rate=0.02,
        growth_rate=0.065
    ),
    PartnerGrowthData(
        period="2024-02",
        new_partners=12,
        total_partners=135,
        churn_rate=0.015,
        growth_rate=0.055
    ),
    PartnerGrowthData(
        period="2024-03",
        new_partners=9,
        total_partners=142,
        churn_rate=0.022,
        growth_rate=0.052
    )
]

MOCK_TERRITORY_PERFORMANCE = [
    TerritoryPerformanceData(
        territory="North America",
        partners_count=65,
        revenue=950000.0,
        commission=95000.0,
        market_penetration=0.78,
        satisfaction_score=4.3
    ),
    TerritoryPerformanceData(
        territory="Europe",
        partners_count=42,
        revenue=580000.0,
        commission=58000.0,
        market_penetration=0.65,
        satisfaction_score=4.1
    ),
    TerritoryPerformanceData(
        territory="Asia-Pacific",
        partners_count=35,
        revenue=320000.0,
        commission=32000.0,
        market_penetration=0.45,
        satisfaction_score=3.9
    )
]

@router.get("/channel-metrics", response_model=ChannelMetricsResponse)
async def get_channel_metrics(
    period: str = Query("30d", description="Time period"),
    territory: Optional[str] = Query(None, description="Filter by territory"),
    tier: Optional[str] = Query(None, description="Filter by partner tier"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Get channel metrics and KPIs."""
    
    # In a real implementation, this would filter data based on parameters
    metrics = MOCK_CHANNEL_METRICS
    
    # Apply territory filter if specified
    if territory:
        # Filter top_performers, revenue_by_tier, etc. based on territory
        # This is a simplified mock implementation
        pass
    
    # Apply tier filter if specified
    if tier:
        # Filter data based on partner tier
        # This is a simplified mock implementation
        pass
    
    return ChannelMetricsResponse(data=metrics)

@router.get("/commission-trends", response_model=CommissionTrendsResponse)
async def get_commission_trends(
    period: str = Query("6m", description="Time period"),
    granularity: str = Query("month", description="Data granularity"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Get commission trends over time."""
    
    return CommissionTrendsResponse(data=MOCK_COMMISSION_TRENDS)

@router.get("/partner-growth", response_model=PartnerGrowthResponse)
async def get_partner_growth(
    period: str = Query("12m", description="Time period"),
    granularity: str = Query("month", description="Data granularity"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Get partner growth trends."""
    
    return PartnerGrowthResponse(data=MOCK_PARTNER_GROWTH)

@router.get("/sales-forecast", response_model=SalesForecastResponse)
async def get_sales_forecast(
    horizon: int = Query(6, ge=1, le=24, description="Forecast horizon in months"),
    confidence_level: float = Query(0.95, ge=0.8, le=0.99, description="Confidence level"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Get sales forecast based on historical data."""
    
    # Mock forecast data
    forecast_data = []
    base_date = datetime.now()
    
    for i in range(horizon):
        forecast_date = base_date + timedelta(days=30 * (i + 1))
        forecast_data.append(
            SalesForecastData(
                period=forecast_date.strftime("%Y-%m"),
                predicted_sales=850000.0 + (i * 15000),  # Growing trend
                confidence_interval=[800000.0 + (i * 12000), 900000.0 + (i * 18000)],
                factors={
                    "seasonal_trend": 0.15,
                    "partner_growth": 0.25,
                    "market_conditions": 0.20,
                    "historical_performance": 0.40
                }
            )
        )
    
    return SalesForecastResponse(data=forecast_data)

@router.get("/territory-performance", response_model=TerritoryPerformanceResponse)
async def get_territory_performance(
    period: str = Query("30d", description="Time period"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Get territory performance metrics."""
    
    return TerritoryPerformanceResponse(data=MOCK_TERRITORY_PERFORMANCE)

@router.get("/partner-satisfaction", response_model=Dict[str, any])
async def get_partner_satisfaction(
    period: str = Query("30d", description="Time period"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Get partner satisfaction metrics."""
    
    return {
        "success": True,
        "data": {
            "overall_satisfaction": 4.2,
            "satisfaction_by_tier": {
                "DIAMOND": 4.6,
                "PLATINUM": 4.4,
                "GOLD": 4.2,
                "SILVER": 4.0,
                "BRONZE": 3.8
            },
            "satisfaction_trends": [
                {"month": "2024-01", "score": 4.0},
                {"month": "2024-02", "score": 4.1},
                {"month": "2024-03", "score": 4.2}
            ],
            "satisfaction_factors": {
                "commission_timeliness": 4.3,
                "support_quality": 4.1,
                "platform_usability": 4.0,
                "training_quality": 4.2,
                "communication": 4.1
            },
            "nps_score": 65,
            "response_rate": 0.72
        }
    }

@router.get("/competitive-analysis", response_model=Dict[str, any])
async def get_competitive_analysis(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Get competitive analysis data."""
    
    return {
        "success": True,
        "data": {
            "market_position": {
                "rank": 3,
                "market_share": 0.12,
                "competitive_advantage": [
                    "Higher commission rates",
                    "Better support quality",
                    "Advanced analytics platform"
                ]
            },
            "competitor_comparison": [
                {
                    "competitor": "Competitor A",
                    "commission_rate": 0.08,
                    "our_rate": 0.10,
                    "advantage": "Higher rates"
                },
                {
                    "competitor": "Competitor B",
                    "support_rating": 3.8,
                    "our_rating": 4.2,
                    "advantage": "Better support"
                }
            ],
            "win_loss_analysis": {
                "wins": 45,
                "losses": 23,
                "win_rate": 0.66,
                "common_win_reasons": [
                    "Better commission structure",
                    "Superior platform features",
                    "Strong partner support"
                ],
                "common_loss_reasons": [
                    "Brand recognition",
                    "Existing relationships",
                    "Geographic coverage"
                ]
            }
        }
    }