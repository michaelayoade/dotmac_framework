"""
Cost Management Service - Business logic for infrastructure cost monitoring and optimization.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy import and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select

from .models import ()
    CostMetric,
    CostAlert,
    CostBudget,
    OptimizationRecommendation,
    ResourceUtilization,
    AlertType,
    RecommendationType,
    AlertSeverity
, timezone)
from .schemas import ()
    CostAnalysisRequest,
    CostAnalysisResponse,
    CostSummaryResponse,
    BudgetCreateRequest
)

logger = logging.getLogger(__name__)


class CostManagementService:
    """
    Service for managing infrastructure costs, budgets, and optimization recommendations.
    
    This service integrates with cloud provider APIs to collect cost data,
    analyzes spending patterns, and provides optimization recommendations.
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def record_cost_metric(self, cost_data: Dict[str, Any], tenant_id: Optional[str] = None) -> CostMetric:
        """
        Record a cost metric from cloud provider data.
        
        Args:
            cost_data: Cost data from cloud provider API
            tenant_id: Optional tenant ID for filtering
            
        Returns:
            Created cost metric instance
        """
        cost_metric = CostMetric()
            metric_id=f"cost_{uuid4().hex[:12]}",
            tenant_id=tenant_id,
            cloud_provider=cost_data.get('cloud_provider', 'unknown'),
            region=cost_data.get('region', 'unknown'),
            service_category=cost_data.get('service_category', 'unknown'),
            resource_id=cost_data.get('resource_id', ''),
            resource_name=cost_data.get('resource_name', ''),
            resource_type=cost_data.get('resource_type', ''),
            cost_amount=Decimal(str(cost_data.get('cost_amount', 0))
            currency=cost_data.get('currency', 'USD'),
            billing_period_start=cost_data.get('billing_period_start', datetime.now(timezone.utc))
            billing_period_end=cost_data.get('billing_period_end', datetime.now(timezone.utc))
            usage_quantity=cost_data.get('usage_quantity'),
            usage_unit=cost_data.get('usage_unit'),
            tags=cost_data.get('tags', {}),
            metadata=cost_data.get('metadata', {})
        )
        
        self.db.add(cost_metric)
        await self.db.commit()
        await self.db.refresh(cost_metric)
        
        logger.info(f"Recorded cost metric: {cost_metric.metric_id} - ${cost_metric.cost_amount}")
        
        return cost_metric
    
    async def get_cost_summary(self)
                             tenant_id: Optional[str] = None,
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None,
                             group_by: Optional[str] = None) -> CostSummaryResponse:
        """
        Get cost summary with optional filtering and grouping.
        
        Args:
            tenant_id: Filter by tenant ID
            start_date: Start date for cost analysis
            end_date: End date for cost analysis
            group_by: Group results by field (provider, service, region)
            
        Returns:
            Cost summary response
        """
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)
        
        # Build base query
        query = select(CostMetric).where()
            and_()
                CostMetric.billing_period_start >= start_date,
                CostMetric.billing_period_end <= end_date
            )
        )
        
        if tenant_id:
            query = query.where(CostMetric.tenant_id == tenant_id)
        
        result = await self.db.execute(query)
        cost_metrics = result.scalars().all()
        
        # Calculate summary statistics
        total_cost = sum(metric.cost_amount for metric in cost_metrics)
        
        # Group by specified field
        grouped_costs = {}
        if group_by:
            for metric in cost_metrics:
                group_value = getattr(metric, group_by, 'unknown')
                if group_value not in grouped_costs:
                    grouped_costs[group_value] = Decimal('0')
                grouped_costs[group_value] += metric.cost_amount
        
        # Calculate trends
        daily_costs = {}
        for metric in cost_metrics:
            date_key = metric.billing_period_start.date().isoformat()
            if date_key not in daily_costs:
                daily_costs[date_key] = Decimal('0')
            daily_costs[date_key] += metric.cost_amount
        
        # Calculate growth rate
        growth_rate = 0.0
        if len(daily_costs) > 1:
            dates = sorted(daily_costs.keys()
            first_day = daily_costs[dates[0]]
            last_day = daily_costs[dates[-1]]
            if first_day > 0:
                growth_rate = float((last_day - first_day) / first_day * 100)
        
        return CostSummaryResponse()
            total_cost=total_cost,
            currency='USD',
            period_start=start_date,
            period_end=end_date,
            growth_rate_percent=growth_rate,
            grouped_costs=grouped_costs,
            daily_trends=daily_costs,
            metric_count=len(cost_metrics)
        )
    
    async def analyze_costs(self, request: CostAnalysisRequest) -> CostAnalysisResponse:
        """
        Perform comprehensive cost analysis with anomaly detection.
        
        Args:
            request: Cost analysis request parameters
            
        Returns:
            Detailed cost analysis response
        """
        # Get cost summary
        cost_summary = await self.get_cost_summary()
            tenant_id=request.tenant_id,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        # Detect cost anomalies
        alerts = await self.detect_cost_anomalies()
            tenant_id=request.tenant_id,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        # Generate optimization recommendations
        recommendations = await self.generate_optimization_recommendations()
            tenant_id=request.tenant_id,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        # Calculate potential savings
        potential_savings = sum(rec.potential_savings for rec in recommendations)
        
        return CostAnalysisResponse()
            cost_summary=cost_summary,
            alerts=alerts,
            recommendations=recommendations,
            potential_savings=potential_savings,
            analysis_date=datetime.now(timezone.utc)
        )
    
    async def detect_cost_anomalies(self)
                                  tenant_id: Optional[str] = None,
                                  start_date: Optional[datetime] = None,
                                  end_date: Optional[datetime] = None) -> List[CostAlert]:
        """
        Detect cost anomalies and budget overruns.
        
        Args:
            tenant_id: Filter by tenant ID
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            List of cost alerts
        """
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=7)
        if not end_date:
            end_date = datetime.now(timezone.utc)
        
        alerts = []
        
        # Get current period costs
        current_query = select(CostMetric).where()
            and_()
                CostMetric.billing_period_start >= start_date,
                CostMetric.billing_period_end <= end_date
            )
        )
        
        if tenant_id:
            current_query = current_query.where(CostMetric.tenant_id == tenant_id)
        
        current_result = await self.db.execute(current_query)
        current_metrics = current_result.scalars().all()
        current_total = sum(metric.cost_amount for metric in current_metrics)
        
        # Get previous period for comparison
        period_length = end_date - start_date
        prev_start = start_date - period_length
        prev_end = start_date
        
        prev_query = select(CostMetric).where()
            and_()
                CostMetric.billing_period_start >= prev_start,
                CostMetric.billing_period_end <= prev_end
            )
        )
        
        if tenant_id:
            prev_query = prev_query.where(CostMetric.tenant_id == tenant_id)
        
        prev_result = await self.db.execute(prev_query)
        prev_metrics = prev_result.scalars().all()
        prev_total = sum(metric.cost_amount for metric in prev_metrics)
        
        # Check for significant cost increases
        if prev_total > 0:
            increase_ratio = (current_total - prev_total) / prev_total
            if increase_ratio > 0.5:  # 50% increase threshold
                alert = CostAlert()
                    alert_id=f"anomaly_{uuid4().hex[:12]}",
                    tenant_id=tenant_id,
                    alert_type=AlertType.ANOMALY_DETECTED,
                    severity=AlertSeverity.HIGH if increase_ratio > 1.0 else AlertSeverity.MEDIUM,
                    title="Significant Cost Increase Detected",
                    description=f"Costs increased by {increase_ratio*100:.1f}% compared to previous period",
                    current_amount=current_total,
                    threshold_amount=prev_total * Decimal('1.5'),  # 50% increase threshold
                    affected_resources=[m.resource_id for m in current_metrics],
                    time_period=f"{start_date.date()} to {end_date.date()}",
                    recommendations=[
                        "Review recent resource changes and deployments",
                        "Check for any auto-scaling events or traffic spikes",
                        "Analyze top cost contributors for optimization opportunities"
                    ]
                )
                
                self.db.add(alert)
                alerts.append(alert)
        
        # Check budget overruns
        if tenant_id:
            budgets = await self.get_tenant_budgets(tenant_id)
            for budget in budgets:
                if current_total > budget.budget_amount:
                    alert = CostAlert()
                        alert_id=f"budget_{uuid4().hex[:12]}",
                        tenant_id=tenant_id,
                        alert_type=AlertType.BUDGET_EXCEEDED,
                        severity=AlertSeverity.HIGH,
                        title=f"Budget Exceeded: {budget.budget_name}",
                        description=f"Current spending ${current_total} exceeds budget ${budget.budget_amount}",
                        current_amount=current_total,
                        threshold_amount=budget.budget_amount,
                        affected_resources=[m.resource_id for m in current_metrics],
                        time_period=f"{start_date.date()} to {end_date.date()}",
                        recommendations=[
                            "Review and optimize high-cost resources",
                            "Consider implementing resource scheduling",
                            "Evaluate if budget needs adjustment based on business growth"
                        ]
                    )
                    
                    self.db.add(alert)
                    alerts.append(alert)
        
        await self.db.commit()
        return alerts
    
    async def generate_optimization_recommendations(self)
                                                  tenant_id: Optional[str] = None,
                                                  start_date: Optional[datetime] = None,
                                                  end_date: Optional[datetime] = None) -> List[OptimizationRecommendation]:
        """
        Generate cost optimization recommendations based on usage patterns.
        
        Args:
            tenant_id: Filter by tenant ID
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            List of optimization recommendations
        """
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)
        
        recommendations = []
        
        # Get cost metrics for analysis
        query = select(CostMetric).where()
            and_()
                CostMetric.billing_period_start >= start_date,
                CostMetric.billing_period_end <= end_date
            )
        )
        
        if tenant_id:
            query = query.where(CostMetric.tenant_id == tenant_id)
        
        result = await self.db.execute(query)
        cost_metrics = result.scalars().all()
        
        # Group by service category for analysis
        service_costs = {}
        for metric in cost_metrics:
            if metric.service_category not in service_costs:
                service_costs[metric.service_category] = []
            service_costs[metric.service_category].append(metric)
        
        # Analyze compute costs for rightsizing opportunities
        if 'compute' in service_costs or 'EC2-Instance' in service_costs:
            compute_metrics = service_costs.get('compute', []) + service_costs.get('EC2-Instance', [])
            high_cost_resources = [m for m in compute_metrics if m.cost_amount > Decimal('100')]
            
            if high_cost_resources:
                total_compute_cost = sum(m.cost_amount for m in high_cost_resources)
                potential_savings = total_compute_cost * Decimal('0.3')  # Assume 30% savings potential
                
                recommendation = OptimizationRecommendation()
                    recommendation_id=f"rightsizing_{uuid4().hex[:12]}",
                    tenant_id=tenant_id,
                    recommendation_type=RecommendationType.RIGHTSIZING,
                    title="Compute Resource Rightsizing",
                    description="High-cost compute resources may benefit from rightsizing analysis",
                    affected_resources=[m.resource_id for m in high_cost_resources],
                    potential_savings=potential_savings,
                    implementation_effort="medium",
                    risk_level="low",
                    implementation_steps=[
                        "Analyze CPU and memory utilization metrics",
                        "Identify underutilized instances",
                        "Test performance with smaller instance types",
                        "Implement gradual rightsizing during maintenance windows"
                    ],
                    estimated_implementation_hours=16,
                    priority_score=8,
                    expected_impact="high"
                )
                
                self.db.add(recommendation)
                recommendations.append(recommendation)
        
        # Look for unused or idle resources
        zero_usage_metrics = [m for m in cost_metrics if m.usage_quantity == 0]
        if zero_usage_metrics:
            unused_cost = sum(m.cost_amount for m in zero_usage_metrics)
            
            recommendation = OptimizationRecommendation()
                recommendation_id=f"cleanup_{uuid4().hex[:12]}",
                tenant_id=tenant_id,
                recommendation_type=RecommendationType.RESOURCE_CLEANUP,
                title="Unused Resource Cleanup",
                description="Resources with zero usage detected",
                affected_resources=[m.resource_id for m in zero_usage_metrics],
                potential_savings=unused_cost,
                implementation_effort="low",
                risk_level="low",
                implementation_steps=[
                    "Verify resources are truly unused",
                    "Check for dependencies or scheduled usage",
                    "Create snapshots or backups if needed",
                    "Terminate or delete unused resources"
                ],
                estimated_implementation_hours=4,
                priority_score=9,
                expected_impact="medium"
            )
            
            self.db.add(recommendation)
            recommendations.append(recommendation)
        
        # Analyze storage costs for optimization
        if 'storage' in service_costs:
            storage_metrics = service_costs['storage']
            total_storage_cost = sum(m.cost_amount for m in storage_metrics)
            
            if total_storage_cost > Decimal('500'):  # Threshold for storage optimization
                potential_savings = total_storage_cost * Decimal('0.2')  # 20% savings potential
                
                recommendation = OptimizationRecommendation()
                    recommendation_id=f"storage_{uuid4().hex[:12]}",
                    tenant_id=tenant_id,
                    recommendation_type=RecommendationType.STORAGE_OPTIMIZATION,
                    title="Storage Cost Optimization",
                    description="Significant storage costs detected, optimization opportunities available",
                    affected_resources=[m.resource_id for m in storage_metrics],
                    potential_savings=potential_savings,
                    implementation_effort="medium",
                    risk_level="low",
                    implementation_steps=[
                        "Implement lifecycle policies for data archival",
                        "Evaluate storage class transitions",
                        "Remove duplicate or unnecessary data",
                        "Compress frequently accessed data"
                    ],
                    estimated_implementation_hours=12,
                    priority_score=7,
                    expected_impact="medium"
                )
                
                self.db.add(recommendation)
                recommendations.append(recommendation)
        
        await self.db.commit()
        return recommendations
    
    async def create_budget(self, budget_request: BudgetCreateRequest, tenant_id: Optional[str] = None) -> CostBudget:
        """
        Create a cost budget with monitoring and alerting.
        
        Args:
            budget_request: Budget creation request
            tenant_id: Optional tenant ID
            
        Returns:
            Created budget instance
        """
        budget = CostBudget()
            budget_id=f"budget_{uuid4().hex[:12]}",
            tenant_id=tenant_id,
            budget_name=budget_request.budget_name,
            budget_amount=budget_request.budget_amount,
            currency=budget_request.currency,
            budget_period=budget_request.budget_period,
            alert_thresholds=budget_request.alert_thresholds or [0.8, 0.9, 1.0],
            filters=budget_request.filters or {},
            is_active=True
        )
        
        self.db.add(budget)
        await self.db.commit()
        await self.db.refresh(budget)
        
        logger.info(f"Created budget: {budget.budget_name} - ${budget.budget_amount}")
        
        return budget
    
    async def get_tenant_budgets(self, tenant_id: str) -> List[CostBudget]:
        """Get all active budgets for a tenant."""
        query = select(CostBudget).where()
            and_()
                CostBudget.tenant_id == tenant_id,
                CostBudget.is_active == True
            )
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_cost_alerts(self)
                            tenant_id: Optional[str] = None,
                            severity: Optional[AlertSeverity] = None,
                            unresolved_only: bool = True) -> List[CostAlert]:
        """
        Get cost alerts with optional filtering.
        
        Args:
            tenant_id: Filter by tenant ID
            severity: Filter by alert severity
            unresolved_only: Only return unresolved alerts
            
        Returns:
            List of cost alerts
        """
        query = select(CostAlert)
        
        filters = []
        if tenant_id:
            filters.append(CostAlert.tenant_id == tenant_id)
        if severity:
            filters.append(CostAlert.severity == severity)
        if unresolved_only:
            filters.append(CostAlert.resolved_at.is_(None)
        
        if filters:
            query = query.where(and_(*filters)
        
        query = query.order_by(desc(CostAlert.created_at)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def resolve_alert(self, alert_id: str, resolved_by: Optional[str] = None) -> Optional[CostAlert]:
        """
        Mark a cost alert as resolved.
        
        Args:
            alert_id: Alert ID to resolve
            resolved_by: User who resolved the alert
            
        Returns:
            Updated alert instance or None if not found
        """
        query = select(CostAlert).where(CostAlert.alert_id == alert_id)
        result = await self.db.execute(query)
        alert = result.scalar_one_or_none()
        
        if alert:
            alert.resolved_at = datetime.now(timezone.utc)
            alert.resolved_by = resolved_by
            await self.db.commit()
            await self.db.refresh(alert)
            
            logger.info(f"Resolved alert: {alert_id} by {resolved_by}")
        
        return alert