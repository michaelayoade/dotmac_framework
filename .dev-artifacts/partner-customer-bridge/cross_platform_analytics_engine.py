"""
Cross-Platform Analytics Engine
Enable partners to see performance across all their tenants with unified analytics and insights
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
import asyncio
import json
import statistics
from collections import defaultdict

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.database.base import Base
from dotmac_isp.shared.base_service import BaseService
from .partner_customer_relationship_bridge import (
    PartnerCustomerBridgeService, 
    PartnerTenantMetrics,
    CrossTenantCustomerView
)


class AnalyticsTimeframe(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class MetricType(str, Enum):
    REVENUE = "revenue"
    CUSTOMERS = "customers"
    PERFORMANCE = "performance"
    SATISFACTION = "satisfaction"
    GROWTH = "growth"
    OPERATIONAL = "operational"


class AggregationMethod(str, Enum):
    SUM = "sum"
    AVERAGE = "average"
    MEDIAN = "median"
    MAX = "max"
    MIN = "min"
    COUNT = "count"
    PERCENTAGE = "percentage"


class TrendDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    VOLATILE = "volatile"


class TenantPerformanceRank(BaseModel):
    tenant_id: str
    tenant_name: str
    rank: int = Field(ge=1)
    score: float = Field(ge=0, le=100)
    key_metrics: Dict[str, float] = {}
    strengths: List[str] = []
    improvement_areas: List[str] = []


class CrossTenantMetric(BaseModel):
    metric_name: str
    metric_type: MetricType
    timeframe: AnalyticsTimeframe
    aggregation_method: AggregationMethod
    
    # Values across tenants
    total_value: float
    average_value: float
    tenant_values: Dict[str, float] = {}  # tenant_id -> value
    
    # Trend analysis
    trend_direction: TrendDirection
    trend_percentage: float
    previous_period_value: Optional[float] = None
    
    # Statistical analysis
    std_deviation: Optional[float] = None
    min_value: float
    max_value: float
    median_value: Optional[float] = None


class CrossTenantDashboard(BaseModel):
    partner_id: str
    partner_name: str
    report_period: Dict[str, datetime]
    generated_at: datetime
    
    # Summary metrics
    total_tenants: int = Field(ge=0)
    total_customers: int = Field(ge=0)  
    total_revenue: float = Field(ge=0)
    total_attributed_revenue: float = Field(ge=0)
    
    # Performance overview
    average_customer_satisfaction: Optional[float] = Field(None, ge=0, le=10)
    average_revenue_per_tenant: float = Field(ge=0)
    average_customers_per_tenant: float = Field(ge=0)
    
    # Cross-tenant metrics
    key_metrics: List[CrossTenantMetric] = []
    
    # Tenant rankings
    tenant_rankings: List[TenantPerformanceRank] = []
    
    # Insights and recommendations  
    performance_insights: List[str] = []
    growth_opportunities: List[str] = []
    risk_alerts: List[str] = []


class CrossTenantComparison(BaseModel):
    comparison_id: str
    partner_id: str
    tenant_ids: List[str]
    comparison_period: Dict[str, datetime]
    
    # Comparative metrics
    revenue_comparison: Dict[str, float] = {}
    customer_comparison: Dict[str, int] = {}
    growth_comparison: Dict[str, float] = {}
    satisfaction_comparison: Dict[str, float] = {}
    
    # Rankings
    revenue_ranking: List[str] = []  # tenant_ids ranked by revenue
    growth_ranking: List[str] = []   # tenant_ids ranked by growth
    satisfaction_ranking: List[str] = []  # tenant_ids ranked by satisfaction
    
    # Insights
    top_performers: List[str] = []
    underperformers: List[str] = []
    improvement_recommendations: Dict[str, List[str]] = {}


class RevenueAttribution(BaseModel):
    partner_id: str
    tenant_id: str
    customer_id: str
    attribution_period: Dict[str, datetime]
    
    # Attribution details
    total_customer_revenue: float = Field(ge=0)
    attributed_revenue: float = Field(ge=0)
    attribution_percentage: float = Field(ge=0, le=1)
    
    # Attribution factors
    acquisition_attribution: float = Field(ge=0, le=1)  # Credit for acquiring customer
    management_attribution: float = Field(ge=0, le=1)   # Credit for ongoing management
    support_attribution: float = Field(ge=0, le=1)      # Credit for support activities
    growth_attribution: float = Field(ge=0, le=1)       # Credit for revenue growth
    
    # Revenue breakdown
    monthly_recurring_revenue: float = Field(ge=0)
    one_time_revenue: float = Field(ge=0)
    upsell_revenue: float = Field(ge=0)


class TenantBenchmarking(BaseModel):
    partner_id: str
    tenant_id: str
    benchmarking_period: Dict[str, datetime]
    
    # Peer comparisons (against other tenants in same partner portfolio)
    revenue_percentile: float = Field(ge=0, le=100)
    customer_count_percentile: float = Field(ge=0, le=100)
    growth_percentile: float = Field(ge=0, le=100)
    satisfaction_percentile: float = Field(ge=0, le=100)
    
    # Industry benchmarks (if available)
    industry_revenue_comparison: Optional[float] = None
    industry_growth_comparison: Optional[float] = None
    
    # Performance gaps
    performance_gaps: List[str] = []
    improvement_potential: Dict[str, float] = {}


class CrossPlatformAnalyticsService(BaseService):
    """Service for cross-platform analytics across partner tenants"""
    
    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db, tenant_id)
        self.bridge_service = PartnerCustomerBridgeService(db, tenant_id)
        self.metric_calculations = self._initialize_metric_calculations()
    
    def _initialize_metric_calculations(self) -> Dict[str, Dict[str, Any]]:
        """Initialize metric calculation configurations"""
        return {
            "revenue_metrics": {
                "total_revenue": {"aggregation": AggregationMethod.SUM, "type": MetricType.REVENUE},
                "average_revenue": {"aggregation": AggregationMethod.AVERAGE, "type": MetricType.REVENUE},
                "revenue_growth": {"aggregation": AggregationMethod.PERCENTAGE, "type": MetricType.GROWTH}
            },
            "customer_metrics": {
                "total_customers": {"aggregation": AggregationMethod.SUM, "type": MetricType.CUSTOMERS},
                "new_customers": {"aggregation": AggregationMethod.SUM, "type": MetricType.CUSTOMERS},
                "churned_customers": {"aggregation": AggregationMethod.SUM, "type": MetricType.CUSTOMERS},
                "customer_growth_rate": {"aggregation": AggregationMethod.PERCENTAGE, "type": MetricType.GROWTH}
            },
            "performance_metrics": {
                "customer_satisfaction": {"aggregation": AggregationMethod.AVERAGE, "type": MetricType.SATISFACTION},
                "service_uptime": {"aggregation": AggregationMethod.AVERAGE, "type": MetricType.PERFORMANCE},
                "support_resolution_time": {"aggregation": AggregationMethod.AVERAGE, "type": MetricType.OPERATIONAL}
            }
        }
    
    @standard_exception_handler
    async def generate_cross_tenant_dashboard(
        self, 
        partner_id: str,
        period_start: datetime,
        period_end: datetime,
        tenant_filter: Optional[List[str]] = None
    ) -> CrossTenantDashboard:
        """Generate comprehensive cross-tenant analytics dashboard"""
        
        # Get tenant metrics
        tenant_metrics = await self.bridge_service.get_partner_tenant_metrics(
            partner_id, period_start, period_end, tenant_filter
        )
        
        if not tenant_metrics:
            raise ValueError(f"No tenant metrics found for partner {partner_id}")
        
        # Calculate summary metrics
        total_tenants = len(tenant_metrics)
        total_customers = sum(tm.total_customers for tm in tenant_metrics)
        total_revenue = sum(tm.total_revenue for tm in tenant_metrics)
        total_attributed_revenue = sum(tm.attributed_revenue for tm in tenant_metrics)
        
        # Calculate averages
        avg_customer_satisfaction = None
        satisfactions = [tm.customer_satisfaction for tm in tenant_metrics if tm.customer_satisfaction is not None]
        if satisfactions:
            avg_customer_satisfaction = statistics.mean(satisfactions)
        
        avg_revenue_per_tenant = total_revenue / total_tenants if total_tenants > 0 else 0
        avg_customers_per_tenant = total_customers / total_tenants if total_tenants > 0 else 0
        
        # Generate cross-tenant metrics
        key_metrics = await self._generate_cross_tenant_metrics(tenant_metrics, period_start, period_end)
        
        # Generate tenant rankings
        tenant_rankings = await self._generate_tenant_rankings(tenant_metrics)
        
        # Generate insights
        insights = await self._generate_performance_insights(tenant_metrics, key_metrics)
        
        dashboard = CrossTenantDashboard(
            partner_id=partner_id,
            partner_name=await self._get_partner_name(partner_id),
            report_period={"start": period_start, "end": period_end},
            generated_at=datetime.utcnow(),
            total_tenants=total_tenants,
            total_customers=total_customers,
            total_revenue=total_revenue,
            total_attributed_revenue=total_attributed_revenue,
            average_customer_satisfaction=avg_customer_satisfaction,
            average_revenue_per_tenant=avg_revenue_per_tenant,
            average_customers_per_tenant=avg_customers_per_tenant,
            key_metrics=key_metrics,
            tenant_rankings=tenant_rankings,
            performance_insights=insights["performance_insights"],
            growth_opportunities=insights["growth_opportunities"],
            risk_alerts=insights["risk_alerts"]
        )
        
        return dashboard
    
    @standard_exception_handler
    async def compare_tenant_performance(
        self,
        partner_id: str,
        tenant_ids: List[str],
        period_start: datetime,
        period_end: datetime
    ) -> CrossTenantComparison:
        """Compare performance across specific tenants"""
        
        # Get metrics for specified tenants
        tenant_metrics = await self.bridge_service.get_partner_tenant_metrics(
            partner_id, period_start, period_end, tenant_ids
        )
        
        # Build comparison data
        revenue_comparison = {}
        customer_comparison = {}
        growth_comparison = {}
        satisfaction_comparison = {}
        
        for tm in tenant_metrics:
            revenue_comparison[tm.tenant_id] = tm.total_revenue
            customer_comparison[tm.tenant_id] = tm.total_customers
            growth_comparison[tm.tenant_id] = tm.revenue_growth_rate
            if tm.customer_satisfaction is not None:
                satisfaction_comparison[tm.tenant_id] = tm.customer_satisfaction
        
        # Generate rankings
        revenue_ranking = sorted(tenant_ids, key=lambda tid: revenue_comparison.get(tid, 0), reverse=True)
        growth_ranking = sorted(tenant_ids, key=lambda tid: growth_comparison.get(tid, 0), reverse=True)
        satisfaction_ranking = sorted(
            [tid for tid in tenant_ids if tid in satisfaction_comparison], 
            key=lambda tid: satisfaction_comparison[tid], 
            reverse=True
        )
        
        # Identify top performers and underperformers
        top_performers = []
        underperformers = []
        
        for tenant_id in tenant_ids:
            revenue_rank = revenue_ranking.index(tenant_id) + 1
            growth_rank = growth_ranking.index(tenant_id) + 1 if tenant_id in growth_ranking else len(tenant_ids)
            
            avg_rank = (revenue_rank + growth_rank) / 2
            
            if avg_rank <= len(tenant_ids) * 0.3:  # Top 30%
                top_performers.append(tenant_id)
            elif avg_rank >= len(tenant_ids) * 0.7:  # Bottom 30%
                underperformers.append(tenant_id)
        
        # Generate improvement recommendations
        improvement_recommendations = {}
        for tenant_id in underperformers:
            recommendations = await self._generate_tenant_improvement_recommendations(
                tenant_id, tenant_metrics, revenue_ranking, growth_ranking
            )
            improvement_recommendations[tenant_id] = recommendations
        
        comparison = CrossTenantComparison(
            comparison_id=f"comp_{partner_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            partner_id=partner_id,
            tenant_ids=tenant_ids,
            comparison_period={"start": period_start, "end": period_end},
            revenue_comparison=revenue_comparison,
            customer_comparison=customer_comparison,
            growth_comparison=growth_comparison,
            satisfaction_comparison=satisfaction_comparison,
            revenue_ranking=revenue_ranking,
            growth_ranking=growth_ranking,
            satisfaction_ranking=satisfaction_ranking,
            top_performers=top_performers,
            underperformers=underperformers,
            improvement_recommendations=improvement_recommendations
        )
        
        return comparison
    
    @standard_exception_handler
    async def calculate_revenue_attribution(
        self,
        partner_id: str,
        customer_id: str,
        tenant_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> RevenueAttribution:
        """Calculate detailed revenue attribution for a specific customer"""
        
        # Get customer relationship details
        customers = await self.bridge_service.get_partner_customers_across_tenants(
            partner_id, include_inactive=False, tenant_filter=[tenant_id]
        )
        
        customer_view = None
        for customer in customers:
            if customer.customer_id == customer_id:
                customer_view = customer
                break
        
        if not customer_view:
            raise ValueError(f"Customer {customer_id} not found for partner {partner_id} in tenant {tenant_id}")
        
        # Calculate attribution factors
        acquisition_attribution = 0.0
        management_attribution = 0.0
        support_attribution = 0.0
        growth_attribution = 0.0
        
        # Acquisition attribution (if partner acquired the customer)
        if customer_view.partner_engagement_level in ["direct", "supervised"]:
            acquisition_attribution = 0.3  # 30% for acquisition
        
        # Management attribution (ongoing customer management)
        if customer_view.partner_engagement_level == "direct":
            management_attribution = 0.4  # 40% for direct management
        elif customer_view.partner_engagement_level == "supervised":
            management_attribution = 0.2  # 20% for supervised management
        
        # Support attribution (based on support activities)
        if customer_view.support_tickets_30d > 0:
            support_attribution = 0.15  # 15% for active support
        
        # Growth attribution (if customer revenue has grown)
        # This would be calculated based on historical revenue data
        growth_attribution = 0.1  # 10% default for retention and growth
        
        # Calculate total attribution percentage
        total_attribution = min(1.0, acquisition_attribution + management_attribution + support_attribution + growth_attribution)
        
        # Calculate revenue values
        total_customer_revenue = customer_view.monthly_recurring_revenue * (
            (period_end - period_start).days / 30
        )  # Approximate monthly revenue for period
        
        attributed_revenue = total_customer_revenue * customer_view.revenue_share * total_attribution
        
        attribution = RevenueAttribution(
            partner_id=partner_id,
            tenant_id=tenant_id,
            customer_id=customer_id,
            attribution_period={"start": period_start, "end": period_end},
            total_customer_revenue=total_customer_revenue,
            attributed_revenue=attributed_revenue,
            attribution_percentage=total_attribution,
            acquisition_attribution=acquisition_attribution,
            management_attribution=management_attribution,
            support_attribution=support_attribution,
            growth_attribution=growth_attribution,
            monthly_recurring_revenue=customer_view.monthly_recurring_revenue,
            one_time_revenue=0.0,  # Would be calculated from actual data
            upsell_revenue=0.0     # Would be calculated from actual data
        )
        
        return attribution
    
    @standard_exception_handler
    async def benchmark_tenant_performance(
        self,
        partner_id: str,
        tenant_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> TenantBenchmarking:
        """Benchmark tenant performance against partner's other tenants"""
        
        # Get all tenant metrics for partner
        all_tenant_metrics = await self.bridge_service.get_partner_tenant_metrics(
            partner_id, period_start, period_end
        )
        
        # Find target tenant metrics
        target_tenant = None
        for tm in all_tenant_metrics:
            if tm.tenant_id == tenant_id:
                target_tenant = tm
                break
        
        if not target_tenant:
            raise ValueError(f"Tenant {tenant_id} metrics not found")
        
        # Calculate percentiles
        revenue_values = [tm.total_revenue for tm in all_tenant_metrics]
        customer_values = [tm.total_customers for tm in all_tenant_metrics]
        growth_values = [tm.revenue_growth_rate for tm in all_tenant_metrics]
        satisfaction_values = [tm.customer_satisfaction for tm in all_tenant_metrics if tm.customer_satisfaction is not None]
        
        revenue_percentile = self._calculate_percentile(target_tenant.total_revenue, revenue_values)
        customer_percentile = self._calculate_percentile(target_tenant.total_customers, customer_values)
        growth_percentile = self._calculate_percentile(target_tenant.revenue_growth_rate, growth_values)
        
        satisfaction_percentile = 50.0  # Default if no satisfaction data
        if target_tenant.customer_satisfaction is not None and satisfaction_values:
            satisfaction_percentile = self._calculate_percentile(target_tenant.customer_satisfaction, satisfaction_values)
        
        # Identify performance gaps
        performance_gaps = []
        improvement_potential = {}
        
        if revenue_percentile < 25:
            performance_gaps.append("Revenue significantly below peer average")
            improvement_potential["revenue"] = statistics.median(revenue_values) - target_tenant.total_revenue
        
        if customer_percentile < 25:
            performance_gaps.append("Customer count below peer average")
            improvement_potential["customers"] = statistics.median(customer_values) - target_tenant.total_customers
        
        if growth_percentile < 25:
            performance_gaps.append("Growth rate lagging behind peers")
            improvement_potential["growth"] = statistics.median(growth_values) - target_tenant.revenue_growth_rate
        
        benchmarking = TenantBenchmarking(
            partner_id=partner_id,
            tenant_id=tenant_id,
            benchmarking_period={"start": period_start, "end": period_end},
            revenue_percentile=revenue_percentile,
            customer_count_percentile=customer_percentile,
            growth_percentile=growth_percentile,
            satisfaction_percentile=satisfaction_percentile,
            performance_gaps=performance_gaps,
            improvement_potential=improvement_potential
        )
        
        return benchmarking
    
    async def _generate_cross_tenant_metrics(
        self, 
        tenant_metrics: List[PartnerTenantMetrics],
        period_start: datetime,
        period_end: datetime
    ) -> List[CrossTenantMetric]:
        """Generate cross-tenant aggregated metrics"""
        
        metrics = []
        
        # Revenue metrics
        revenue_values = {tm.tenant_id: tm.total_revenue for tm in tenant_metrics}
        revenue_metric = CrossTenantMetric(
            metric_name="Total Revenue",
            metric_type=MetricType.REVENUE,
            timeframe=AnalyticsTimeframe.MONTHLY,  # Based on period
            aggregation_method=AggregationMethod.SUM,
            total_value=sum(revenue_values.values()),
            average_value=statistics.mean(revenue_values.values()) if revenue_values else 0,
            tenant_values=revenue_values,
            trend_direction=TrendDirection.UP,  # Would be calculated from historical data
            trend_percentage=5.2,  # Mock trend
            std_deviation=statistics.stdev(revenue_values.values()) if len(revenue_values) > 1 else None,
            min_value=min(revenue_values.values()) if revenue_values else 0,
            max_value=max(revenue_values.values()) if revenue_values else 0,
            median_value=statistics.median(revenue_values.values()) if revenue_values else None
        )
        metrics.append(revenue_metric)
        
        # Customer metrics
        customer_values = {tm.tenant_id: float(tm.total_customers) for tm in tenant_metrics}
        customer_metric = CrossTenantMetric(
            metric_name="Total Customers",
            metric_type=MetricType.CUSTOMERS,
            timeframe=AnalyticsTimeframe.MONTHLY,
            aggregation_method=AggregationMethod.SUM,
            total_value=sum(customer_values.values()),
            average_value=statistics.mean(customer_values.values()) if customer_values else 0,
            tenant_values=customer_values,
            trend_direction=TrendDirection.UP,
            trend_percentage=3.1,  # Mock trend
            std_deviation=statistics.stdev(customer_values.values()) if len(customer_values) > 1 else None,
            min_value=min(customer_values.values()) if customer_values else 0,
            max_value=max(customer_values.values()) if customer_values else 0,
            median_value=statistics.median(customer_values.values()) if customer_values else None
        )
        metrics.append(customer_metric)
        
        # Satisfaction metrics
        satisfaction_values = {
            tm.tenant_id: tm.customer_satisfaction 
            for tm in tenant_metrics 
            if tm.customer_satisfaction is not None
        }
        
        if satisfaction_values:
            satisfaction_metric = CrossTenantMetric(
                metric_name="Customer Satisfaction",
                metric_type=MetricType.SATISFACTION,
                timeframe=AnalyticsTimeframe.MONTHLY,
                aggregation_method=AggregationMethod.AVERAGE,
                total_value=sum(satisfaction_values.values()),
                average_value=statistics.mean(satisfaction_values.values()),
                tenant_values=satisfaction_values,
                trend_direction=TrendDirection.STABLE,
                trend_percentage=0.5,  # Mock trend
                std_deviation=statistics.stdev(satisfaction_values.values()) if len(satisfaction_values) > 1 else None,
                min_value=min(satisfaction_values.values()),
                max_value=max(satisfaction_values.values()),
                median_value=statistics.median(satisfaction_values.values())
            )
            metrics.append(satisfaction_metric)
        
        return metrics
    
    async def _generate_tenant_rankings(self, tenant_metrics: List[PartnerTenantMetrics]) -> List[TenantPerformanceRank]:
        """Generate tenant performance rankings"""
        
        rankings = []
        
        # Calculate composite scores for each tenant
        tenant_scores = []
        for tm in tenant_metrics:
            # Normalize metrics to 0-100 scale
            revenue_score = min(100, (tm.total_revenue / 100000) * 100) if tm.total_revenue else 0
            customer_score = min(100, (tm.total_customers / 100) * 100) if tm.total_customers else 0
            growth_score = min(100, max(0, (tm.revenue_growth_rate + 1) * 50))  # Convert growth to 0-100
            satisfaction_score = tm.customer_satisfaction * 10 if tm.customer_satisfaction else 50  # Convert to 0-100
            
            # Weighted composite score
            composite_score = (
                revenue_score * 0.4 +      # 40% weight on revenue
                customer_score * 0.3 +     # 30% weight on customers
                growth_score * 0.2 +       # 20% weight on growth
                satisfaction_score * 0.1   # 10% weight on satisfaction
            )
            
            tenant_scores.append({
                'tenant_id': tm.tenant_id,
                'tenant_name': tm.tenant_name,
                'composite_score': composite_score,
                'revenue_score': revenue_score,
                'customer_score': customer_score,
                'growth_score': growth_score,
                'satisfaction_score': satisfaction_score
            })
        
        # Sort by composite score
        tenant_scores.sort(key=lambda x: x['composite_score'], reverse=True)
        
        # Create ranking objects
        for rank, tenant_data in enumerate(tenant_scores, 1):
            strengths = []
            improvement_areas = []
            
            # Identify strengths (scores above 75)
            if tenant_data['revenue_score'] > 75:
                strengths.append("Strong revenue performance")
            if tenant_data['customer_score'] > 75:
                strengths.append("High customer acquisition")
            if tenant_data['growth_score'] > 75:
                strengths.append("Excellent growth rate")
            if tenant_data['satisfaction_score'] > 75:
                strengths.append("High customer satisfaction")
            
            # Identify improvement areas (scores below 40)
            if tenant_data['revenue_score'] < 40:
                improvement_areas.append("Revenue generation")
            if tenant_data['customer_score'] < 40:
                improvement_areas.append("Customer acquisition")
            if tenant_data['growth_score'] < 40:
                improvement_areas.append("Growth acceleration")
            if tenant_data['satisfaction_score'] < 40:
                improvement_areas.append("Customer satisfaction")
            
            ranking = TenantPerformanceRank(
                tenant_id=tenant_data['tenant_id'],
                tenant_name=tenant_data['tenant_name'],
                rank=rank,
                score=tenant_data['composite_score'],
                key_metrics={
                    "revenue_score": tenant_data['revenue_score'],
                    "customer_score": tenant_data['customer_score'],
                    "growth_score": tenant_data['growth_score'],
                    "satisfaction_score": tenant_data['satisfaction_score']
                },
                strengths=strengths,
                improvement_areas=improvement_areas
            )
            rankings.append(ranking)
        
        return rankings
    
    async def _generate_performance_insights(
        self, 
        tenant_metrics: List[PartnerTenantMetrics],
        cross_tenant_metrics: List[CrossTenantMetric]
    ) -> Dict[str, List[str]]:
        """Generate performance insights and recommendations"""
        
        insights = {
            "performance_insights": [],
            "growth_opportunities": [],
            "risk_alerts": []
        }
        
        # Performance insights
        total_revenue = sum(tm.total_revenue for tm in tenant_metrics)
        total_customers = sum(tm.total_customers for tm in tenant_metrics)
        
        if total_revenue > 500000:
            insights["performance_insights"].append(
                f"Strong portfolio performance with ${total_revenue:,.0f} total revenue across {len(tenant_metrics)} tenants"
            )
        
        avg_growth = statistics.mean([tm.revenue_growth_rate for tm in tenant_metrics])
        if avg_growth > 0.1:
            insights["performance_insights"].append(f"Healthy growth rate of {avg_growth:.1%} average across tenants")
        
        # Growth opportunities
        low_growth_tenants = [tm for tm in tenant_metrics if tm.revenue_growth_rate < 0.05]
        if low_growth_tenants:
            insights["growth_opportunities"].append(
                f"{len(low_growth_tenants)} tenants showing low growth - consider targeted improvement initiatives"
            )
        
        high_satisfaction_tenants = [tm for tm in tenant_metrics if tm.customer_satisfaction and tm.customer_satisfaction > 8.5]
        if high_satisfaction_tenants:
            insights["growth_opportunities"].append(
                f"{len(high_satisfaction_tenants)} tenants with high satisfaction scores - potential for upselling"
            )
        
        # Risk alerts
        declining_tenants = [tm for tm in tenant_metrics if tm.revenue_growth_rate < -0.05]
        if declining_tenants:
            insights["risk_alerts"].append(
                f"⚠️ {len(declining_tenants)} tenants showing revenue decline - immediate attention required"
            )
        
        low_satisfaction_tenants = [tm for tm in tenant_metrics if tm.customer_satisfaction and tm.customer_satisfaction < 6.0]
        if low_satisfaction_tenants:
            insights["risk_alerts"].append(
                f"⚠️ {len(low_satisfaction_tenants)} tenants with low customer satisfaction - churn risk"
            )
        
        return insights
    
    async def _generate_tenant_improvement_recommendations(
        self,
        tenant_id: str,
        tenant_metrics: List[PartnerTenantMetrics],
        revenue_ranking: List[str],
        growth_ranking: List[str]
    ) -> List[str]:
        """Generate improvement recommendations for underperforming tenant"""
        
        recommendations = []
        
        # Find tenant metrics
        tenant_metric = None
        for tm in tenant_metrics:
            if tm.tenant_id == tenant_id:
                tenant_metric = tm
                break
        
        if not tenant_metric:
            return recommendations
        
        # Revenue-based recommendations
        revenue_rank = revenue_ranking.index(tenant_id) + 1
        if revenue_rank > len(revenue_ranking) * 0.7:
            recommendations.append("Focus on customer acquisition and retention strategies")
            recommendations.append("Review pricing strategy for competitive positioning")
        
        # Growth-based recommendations
        if tenant_metric.revenue_growth_rate < 0:
            recommendations.append("Urgent: Address revenue decline with customer success initiatives")
        elif tenant_metric.revenue_growth_rate < 0.05:
            recommendations.append("Implement growth acceleration programs and upselling campaigns")
        
        # Satisfaction-based recommendations
        if tenant_metric.customer_satisfaction and tenant_metric.customer_satisfaction < 7.0:
            recommendations.append("Improve customer satisfaction through enhanced support and service quality")
        
        # Customer-based recommendations
        if tenant_metric.new_customers < tenant_metric.churned_customers:
            recommendations.append("Critical: Customer acquisition rate below churn rate - review onboarding process")
        
        return recommendations
    
    def _calculate_percentile(self, value: float, values: List[float]) -> float:
        """Calculate percentile rank of value within values list"""
        if not values:
            return 50.0
        
        sorted_values = sorted(values)
        rank = sorted_values.index(value) if value in sorted_values else len([v for v in sorted_values if v < value])
        
        return (rank / len(values)) * 100
    
    async def _get_partner_name(self, partner_id: str) -> str:
        """Get partner name from partner ID"""
        # Mock implementation - would query actual partner data
        return f"Partner {partner_id[-4:].upper()}"


__all__ = [
    "AnalyticsTimeframe",
    "MetricType", 
    "AggregationMethod",
    "TrendDirection",
    "TenantPerformanceRank",
    "CrossTenantMetric",
    "CrossTenantDashboard",
    "CrossTenantComparison",
    "RevenueAttribution",
    "TenantBenchmarking",
    "CrossPlatformAnalyticsService"
]