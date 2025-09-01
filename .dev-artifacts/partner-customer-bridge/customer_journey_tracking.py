"""
Customer Journey Tracking Across Tenants
Enables partners to track customer journeys across all their tenant deployments
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc
from pydantic import BaseModel, Field, validator
import json

from dotmac_isp.shared.base_service import BaseService
from dotmac_isp.shared.database.base import TenantAwareTable
from dotmac_shared.database.mixins import TimestampMixin, SoftDeleteMixin


class JourneyStage(str, Enum):
    LEAD = "lead"
    PROSPECT = "prospect"
    CUSTOMER = "customer"
    ACTIVE_SERVICE = "active_service"
    SUPPORT = "support"
    RENEWAL = "renewal"
    EXPANSION = "expansion"
    CHURN_RISK = "churn_risk"
    CHURNED = "churned"


class TouchpointType(str, Enum):
    WEB_VISIT = "web_visit"
    EMAIL_OPEN = "email_open"
    EMAIL_CLICK = "email_click"
    PHONE_CALL = "phone_call"
    SUPPORT_TICKET = "support_ticket"
    PAYMENT = "payment"
    SERVICE_ACTIVATION = "service_activation"
    CONTRACT_RENEWAL = "contract_renewal"
    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"
    COMPLAINT = "complaint"
    REFERRAL = "referral"


class CustomerJourneyTouchpoint(BaseModel):
    """Individual touchpoint in customer journey"""
    id: str
    customer_id: str
    tenant_id: str
    partner_id: str
    touchpoint_type: TouchpointType
    stage: JourneyStage
    timestamp: datetime
    channel: str
    source: str
    metadata: Dict[str, Any] = {}
    revenue_impact: Optional[float] = None
    conversion_value: Optional[float] = None
    satisfaction_score: Optional[int] = None
    
    class Config:
        use_enum_values = True


class CustomerJourneyPath(BaseModel):
    """Complete customer journey path across all touchpoints"""
    customer_id: str
    tenant_id: str
    partner_id: str
    journey_start: datetime
    current_stage: JourneyStage
    stages_completed: List[JourneyStage]
    touchpoints: List[CustomerJourneyTouchpoint]
    total_touchpoints: int
    conversion_touchpoints: int
    revenue_touchpoints: int
    satisfaction_scores: List[int]
    avg_satisfaction: float
    journey_duration_days: int
    stage_progression: List[Dict[str, Any]]
    funnel_metrics: Dict[str, Any]
    
    class Config:
        use_enum_values = True


class JourneyAnalytics(BaseModel):
    """Analytics for customer journeys across tenants"""
    partner_id: str
    analysis_period: Dict[str, datetime]
    tenant_analytics: Dict[str, Any]
    cross_tenant_metrics: Dict[str, Any]
    journey_performance: Dict[str, Any]
    conversion_analytics: Dict[str, Any]
    satisfaction_analytics: Dict[str, Any]
    revenue_attribution: Dict[str, Any]


class CustomerJourneyTrackingService(BaseService):
    """Service for tracking customer journeys across all partner tenants"""
    
    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db, tenant_id)
        self.journey_stages = list(JourneyStage)
        self.touchpoint_types = list(TouchpointType)
    
    async def track_touchpoint(
        self, 
        customer_id: str, 
        partner_id: str, 
        tenant_id: str,
        touchpoint_data: Dict[str, Any]
    ) -> CustomerJourneyTouchpoint:
        """Track a new customer touchpoint"""
        
        # Determine current stage based on touchpoint
        current_stage = self._determine_stage_from_touchpoint(
            touchpoint_data.get('touchpoint_type'),
            touchpoint_data.get('metadata', {})
        )
        
        # Calculate revenue/conversion impact
        revenue_impact = await self._calculate_revenue_impact(
            customer_id, tenant_id, touchpoint_data
        )
        
        touchpoint = CustomerJourneyTouchpoint(
            id=f"tp_{customer_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            customer_id=customer_id,
            tenant_id=tenant_id,
            partner_id=partner_id,
            touchpoint_type=touchpoint_data['touchpoint_type'],
            stage=current_stage,
            timestamp=touchpoint_data.get('timestamp', datetime.utcnow()),
            channel=touchpoint_data.get('channel', 'unknown'),
            source=touchpoint_data.get('source', 'direct'),
            metadata=touchpoint_data.get('metadata', {}),
            revenue_impact=revenue_impact,
            conversion_value=touchpoint_data.get('conversion_value'),
            satisfaction_score=touchpoint_data.get('satisfaction_score')
        )
        
        # Store in database (would use proper SQLAlchemy model)
        await self._store_touchpoint(touchpoint)
        
        # Update journey progression
        await self._update_journey_progression(customer_id, tenant_id, current_stage)
        
        return touchpoint
    
    async def get_customer_journey(self, customer_id: str, tenant_id: str) -> CustomerJourneyPath:
        """Get complete journey for a specific customer"""
        
        # Get all touchpoints for customer
        touchpoints = await self._get_customer_touchpoints(customer_id, tenant_id)
        
        if not touchpoints:
            return None
        
        # Analyze journey progression
        stages_completed = self._analyze_stage_progression(touchpoints)
        stage_progression = self._build_stage_progression(touchpoints)
        funnel_metrics = self._calculate_funnel_metrics(touchpoints)
        
        # Calculate satisfaction metrics
        satisfaction_scores = [
            tp.satisfaction_score for tp in touchpoints 
            if tp.satisfaction_score is not None
        ]
        avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0
        
        # Calculate journey duration
        journey_start = min(tp.timestamp for tp in touchpoints)
        journey_duration = (datetime.utcnow() - journey_start).days
        
        return CustomerJourneyPath(
            customer_id=customer_id,
            tenant_id=tenant_id,
            partner_id=touchpoints[0].partner_id,
            journey_start=journey_start,
            current_stage=touchpoints[-1].stage,
            stages_completed=stages_completed,
            touchpoints=touchpoints,
            total_touchpoints=len(touchpoints),
            conversion_touchpoints=len([tp for tp in touchpoints if tp.conversion_value]),
            revenue_touchpoints=len([tp for tp in touchpoints if tp.revenue_impact]),
            satisfaction_scores=satisfaction_scores,
            avg_satisfaction=avg_satisfaction,
            journey_duration_days=journey_duration,
            stage_progression=stage_progression,
            funnel_metrics=funnel_metrics
        )
    
    async def get_partner_journey_analytics(
        self, 
        partner_id: str, 
        date_range: Optional[Dict[str, datetime]] = None
    ) -> JourneyAnalytics:
        """Get comprehensive journey analytics for a partner across all tenants"""
        
        if not date_range:
            date_range = {
                'start': datetime.utcnow() - timedelta(days=30),
                'end': datetime.utcnow()
            }
        
        # Get partner's tenants
        partner_tenants = await self._get_partner_tenants(partner_id)
        
        # Analyze journeys for each tenant
        tenant_analytics = {}
        for tenant_id in partner_tenants:
            tenant_analytics[tenant_id] = await self._analyze_tenant_journeys(
                tenant_id, date_range
            )
        
        # Cross-tenant aggregated metrics
        cross_tenant_metrics = self._aggregate_cross_tenant_metrics(tenant_analytics)
        
        # Journey performance analysis
        journey_performance = self._analyze_journey_performance(tenant_analytics)
        
        # Conversion analytics
        conversion_analytics = self._analyze_conversion_patterns(tenant_analytics)
        
        # Satisfaction analytics
        satisfaction_analytics = self._analyze_satisfaction_trends(tenant_analytics)
        
        # Revenue attribution
        revenue_attribution = self._calculate_revenue_attribution(tenant_analytics)
        
        return JourneyAnalytics(
            partner_id=partner_id,
            analysis_period=date_range,
            tenant_analytics=tenant_analytics,
            cross_tenant_metrics=cross_tenant_metrics,
            journey_performance=journey_performance,
            conversion_analytics=conversion_analytics,
            satisfaction_analytics=satisfaction_analytics,
            revenue_attribution=revenue_attribution
        )
    
    async def get_journey_benchmarks(self, partner_id: str) -> Dict[str, Any]:
        """Get journey benchmarks comparing partner performance to industry standards"""
        
        partner_analytics = await self.get_partner_journey_analytics(partner_id)
        
        # Industry benchmarks (would come from aggregated data)
        industry_benchmarks = {
            'avg_journey_duration': 45,  # days
            'conversion_rate': 0.15,     # 15%
            'avg_touchpoints_to_convert': 12,
            'satisfaction_score': 7.5,   # out of 10
            'stage_progression_rates': {
                'lead_to_prospect': 0.30,
                'prospect_to_customer': 0.25,
                'customer_to_active': 0.85,
                'retention_rate': 0.88
            }
        }
        
        # Compare partner metrics to benchmarks
        partner_metrics = partner_analytics.cross_tenant_metrics
        
        benchmarks = {
            'journey_duration': {
                'partner_avg': partner_metrics.get('avg_journey_duration', 0),
                'industry_avg': industry_benchmarks['avg_journey_duration'],
                'performance_ratio': (
                    partner_metrics.get('avg_journey_duration', 0) / 
                    industry_benchmarks['avg_journey_duration']
                ) if partner_metrics.get('avg_journey_duration') else 0,
                'performance_status': self._get_performance_status(
                    partner_metrics.get('avg_journey_duration', 0),
                    industry_benchmarks['avg_journey_duration'],
                    'lower_is_better'
                )
            },
            'conversion_rate': {
                'partner_rate': partner_metrics.get('conversion_rate', 0),
                'industry_avg': industry_benchmarks['conversion_rate'],
                'performance_ratio': (
                    partner_metrics.get('conversion_rate', 0) / 
                    industry_benchmarks['conversion_rate']
                ) if partner_metrics.get('conversion_rate') else 0,
                'performance_status': self._get_performance_status(
                    partner_metrics.get('conversion_rate', 0),
                    industry_benchmarks['conversion_rate'],
                    'higher_is_better'
                )
            },
            'satisfaction_score': {
                'partner_avg': partner_metrics.get('avg_satisfaction', 0),
                'industry_avg': industry_benchmarks['satisfaction_score'],
                'performance_ratio': (
                    partner_metrics.get('avg_satisfaction', 0) / 
                    industry_benchmarks['satisfaction_score']
                ) if partner_metrics.get('avg_satisfaction') else 0,
                'performance_status': self._get_performance_status(
                    partner_metrics.get('avg_satisfaction', 0),
                    industry_benchmarks['satisfaction_score'],
                    'higher_is_better'
                )
            }
        }
        
        return {
            'partner_id': partner_id,
            'benchmark_period': partner_analytics.analysis_period,
            'benchmarks': benchmarks,
            'improvement_opportunities': self._identify_improvement_opportunities(benchmarks),
            'strengths': self._identify_strengths(benchmarks)
        }
    
    async def get_journey_funnel_analysis(self, partner_id: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Analyze customer journey funnel conversion rates"""
        
        # Define funnel stages
        funnel_stages = [
            JourneyStage.LEAD,
            JourneyStage.PROSPECT, 
            JourneyStage.CUSTOMER,
            JourneyStage.ACTIVE_SERVICE
        ]
        
        # Get funnel data
        if tenant_id:
            funnel_data = await self._get_tenant_funnel_data(tenant_id, funnel_stages)
        else:
            funnel_data = await self._get_partner_funnel_data(partner_id, funnel_stages)
        
        # Calculate conversion rates
        funnel_analysis = {
            'stages': [],
            'overall_conversion_rate': 0,
            'bottlenecks': [],
            'optimization_opportunities': []
        }
        
        for i, stage in enumerate(funnel_stages):
            stage_data = {
                'stage': stage.value,
                'count': funnel_data.get(stage.value, 0),
                'conversion_rate': 0,
                'drop_off_rate': 0
            }
            
            if i < len(funnel_stages) - 1:
                current_count = funnel_data.get(stage.value, 0)
                next_count = funnel_data.get(funnel_stages[i + 1].value, 0)
                
                if current_count > 0:
                    conversion_rate = next_count / current_count
                    drop_off_rate = 1 - conversion_rate
                    
                    stage_data['conversion_rate'] = conversion_rate
                    stage_data['drop_off_rate'] = drop_off_rate
                    
                    # Identify bottlenecks (drop-off > 70%)
                    if drop_off_rate > 0.70:
                        funnel_analysis['bottlenecks'].append({
                            'from_stage': stage.value,
                            'to_stage': funnel_stages[i + 1].value,
                            'drop_off_rate': drop_off_rate,
                            'severity': 'high' if drop_off_rate > 0.80 else 'medium'
                        })
            
            funnel_analysis['stages'].append(stage_data)
        
        # Calculate overall conversion rate
        lead_count = funnel_data.get(JourneyStage.LEAD.value, 0)
        active_count = funnel_data.get(JourneyStage.ACTIVE_SERVICE.value, 0)
        
        if lead_count > 0:
            funnel_analysis['overall_conversion_rate'] = active_count / lead_count
        
        # Identify optimization opportunities
        funnel_analysis['optimization_opportunities'] = self._identify_funnel_optimizations(
            funnel_analysis['stages'], funnel_analysis['bottlenecks']
        )
        
        return funnel_analysis
    
    def _determine_stage_from_touchpoint(self, touchpoint_type: str, metadata: Dict[str, Any]) -> JourneyStage:
        """Determine customer stage based on touchpoint type"""
        
        stage_mapping = {
            TouchpointType.WEB_VISIT: JourneyStage.LEAD,
            TouchpointType.EMAIL_OPEN: JourneyStage.LEAD,
            TouchpointType.EMAIL_CLICK: JourneyStage.PROSPECT,
            TouchpointType.PHONE_CALL: JourneyStage.PROSPECT,
            TouchpointType.SERVICE_ACTIVATION: JourneyStage.ACTIVE_SERVICE,
            TouchpointType.PAYMENT: JourneyStage.CUSTOMER,
            TouchpointType.SUPPORT_TICKET: JourneyStage.SUPPORT,
            TouchpointType.CONTRACT_RENEWAL: JourneyStage.RENEWAL,
            TouchpointType.UPGRADE: JourneyStage.EXPANSION,
            TouchpointType.COMPLAINT: JourneyStage.CHURN_RISK
        }
        
        return stage_mapping.get(touchpoint_type, JourneyStage.LEAD)
    
    async def _calculate_revenue_impact(
        self, 
        customer_id: str, 
        tenant_id: str, 
        touchpoint_data: Dict[str, Any]
    ) -> Optional[float]:
        """Calculate revenue impact of a touchpoint"""
        
        touchpoint_type = touchpoint_data.get('touchpoint_type')
        
        # Direct revenue touchpoints
        if touchpoint_type == TouchpointType.PAYMENT:
            return touchpoint_data.get('amount', 0)
        elif touchpoint_type == TouchpointType.UPGRADE:
            return touchpoint_data.get('upgrade_value', 0)
        elif touchpoint_type == TouchpointType.CONTRACT_RENEWAL:
            return touchpoint_data.get('renewal_value', 0)
        
        # Indirect revenue impact (attribution model)
        elif touchpoint_type in [TouchpointType.EMAIL_CLICK, TouchpointType.PHONE_CALL]:
            # Get customer's lifetime value and attribute portion to touchpoint
            customer_ltv = await self._get_customer_lifetime_value(customer_id, tenant_id)
            return customer_ltv * 0.05  # 5% attribution for high-intent touchpoints
        
        return None
    
    def _get_performance_status(self, partner_value: float, benchmark_value: float, direction: str) -> str:
        """Get performance status compared to benchmark"""
        
        if partner_value == 0:
            return 'no_data'
        
        ratio = partner_value / benchmark_value
        
        if direction == 'higher_is_better':
            if ratio >= 1.2:
                return 'excellent'
            elif ratio >= 1.0:
                return 'good'
            elif ratio >= 0.8:
                return 'needs_improvement'
            else:
                return 'poor'
        else:  # lower_is_better
            if ratio <= 0.8:
                return 'excellent'
            elif ratio <= 1.0:
                return 'good'
            elif ratio <= 1.2:
                return 'needs_improvement'
            else:
                return 'poor'
    
    async def _store_touchpoint(self, touchpoint: CustomerJourneyTouchpoint):
        """Store touchpoint in database"""
        # Implementation would use proper SQLAlchemy model
        pass
    
    async def _get_customer_touchpoints(self, customer_id: str, tenant_id: str) -> List[CustomerJourneyTouchpoint]:
        """Get all touchpoints for a customer"""
        # Implementation would query database
        return []
    
    async def _get_partner_tenants(self, partner_id: str) -> List[str]:
        """Get all tenant IDs for a partner"""
        # Implementation would query database
        return []
    
    async def _analyze_tenant_journeys(self, tenant_id: str, date_range: Dict[str, datetime]) -> Dict[str, Any]:
        """Analyze journeys for a specific tenant"""
        # Implementation would analyze tenant data
        return {}
    
    def _aggregate_cross_tenant_metrics(self, tenant_analytics: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate metrics across all tenants"""
        # Implementation would aggregate tenant data
        return {}
    
    def _analyze_journey_performance(self, tenant_analytics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze journey performance patterns"""
        return {}
    
    def _analyze_conversion_patterns(self, tenant_analytics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze conversion patterns across journeys"""
        return {}
    
    def _analyze_satisfaction_trends(self, tenant_analytics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze customer satisfaction trends"""
        return {}
    
    def _calculate_revenue_attribution(self, tenant_analytics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate revenue attribution across touchpoints"""
        return {}
    
    async def _get_customer_lifetime_value(self, customer_id: str, tenant_id: str) -> float:
        """Get customer lifetime value"""
        return 0.0