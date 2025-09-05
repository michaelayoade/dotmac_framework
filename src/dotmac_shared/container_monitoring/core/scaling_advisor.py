"""
Scaling Advisor

Analyzes performance metrics and provides intelligent auto-scaling
recommendations based on customer growth patterns and resource utilization.
"""

import asyncio
import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from .metrics_collector import MetricsSnapshot, SystemMetrics


class ScalingAction(str, Enum):
    """Scaling recommendations"""

    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    SCALE_OUT = "scale_out"  # Horizontal scaling (add instances)
    SCALE_IN = "scale_in"  # Horizontal scaling (remove instances)
    NO_ACTION = "no_action"
    OPTIMIZE = "optimize"  # Configuration optimization


class ScalingReason(str, Enum):
    """Reasons for scaling recommendations"""

    HIGH_CPU = "high_cpu"
    HIGH_MEMORY = "high_memory"
    HIGH_DISK = "high_disk"
    HIGH_REQUEST_RATE = "high_request_rate"
    HIGH_ERROR_RATE = "high_error_rate"
    LOW_UTILIZATION = "low_utilization"
    CUSTOMER_GROWTH = "customer_growth"
    PEAK_HOURS = "peak_hours"
    COST_OPTIMIZATION = "cost_optimization"
    PERFORMANCE_DEGRADATION = "performance_degradation"


class ScalingUrgency(str, Enum):
    """Urgency levels for scaling actions"""

    CRITICAL = "critical"  # Immediate action required
    HIGH = "high"  # Action needed within hours
    MEDIUM = "medium"  # Action needed within days
    LOW = "low"  # Optional optimization


@dataclass
class ScalingRecommendation:
    """Scaling recommendation with detailed analysis"""

    container_id: str
    isp_id: Optional[UUID] = None
    action: ScalingAction = ScalingAction.NO_ACTION
    urgency: ScalingUrgency = ScalingUrgency.LOW
    reason: ScalingReason = ScalingReason.LOW_UTILIZATION
    confidence: float = 0.0  # 0.0 - 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Scaling details
    current_resources: dict[str, Any] = field(default_factory=dict)
    recommended_resources: dict[str, Any] = field(default_factory=dict)
    estimated_cost_impact: Optional[float] = None
    estimated_performance_impact: Optional[float] = None

    # Analysis details
    metrics_analyzed: int = 0
    analysis_period_hours: int = 0
    trend_analysis: dict[str, str] = field(default_factory=dict)
    threshold_violations: list[str] = field(default_factory=list)

    # Implementation guidance
    suggested_implementation: str = ""
    rollback_plan: str = ""
    monitoring_recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert recommendation to dictionary"""
        return {
            "container_id": self.container_id,
            "isp_id": str(self.isp_id) if self.isp_id else None,
            "action": self.action.value,
            "urgency": self.urgency.value,
            "reason": self.reason.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "current_resources": self.current_resources,
            "recommended_resources": self.recommended_resources,
            "estimated_cost_impact": self.estimated_cost_impact,
            "estimated_performance_impact": self.estimated_performance_impact,
            "metrics_analyzed": self.metrics_analyzed,
            "analysis_period_hours": self.analysis_period_hours,
            "trend_analysis": self.trend_analysis,
            "threshold_violations": self.threshold_violations,
            "suggested_implementation": self.suggested_implementation,
            "rollback_plan": self.rollback_plan,
            "monitoring_recommendations": self.monitoring_recommendations,
        }


@dataclass
class ScalingThresholds:
    """Configurable thresholds for scaling decisions"""

    # CPU thresholds (percentage)
    cpu_scale_up_threshold: float = 80.0
    cpu_scale_down_threshold: float = 20.0
    cpu_critical_threshold: float = 95.0

    # Memory thresholds (percentage)
    memory_scale_up_threshold: float = 85.0
    memory_scale_down_threshold: float = 30.0
    memory_critical_threshold: float = 95.0

    # Disk thresholds (percentage)
    disk_scale_up_threshold: float = 90.0
    disk_critical_threshold: float = 98.0

    # Application thresholds
    error_rate_threshold: float = 5.0  # percentage
    response_time_threshold: float = 2.0  # seconds
    request_rate_growth_threshold: float = 50.0  # percentage increase

    # Sustained threshold periods (minutes)
    sustained_violation_period: int = 15
    scale_down_cooldown_period: int = 60


class ScalingAdvisor:
    """
    Intelligent scaling advisor for container resources

    Analyzes metrics trends and provides scaling recommendations based on:
    - Resource utilization patterns
    - Application performance metrics
    - Customer growth trends
    - Cost optimization opportunities
    - Performance degradation indicators
    """

    def __init__(
        self,
        thresholds: Optional[ScalingThresholds] = None,
        analysis_window_hours: int = 24,
        trend_analysis_points: int = 12,
        enable_cost_analysis: bool = True,
        enable_predictive_scaling: bool = True,
    ):
        self.thresholds = thresholds or ScalingThresholds()
        self.analysis_window_hours = analysis_window_hours
        self.trend_analysis_points = trend_analysis_points
        self.enable_cost_analysis = enable_cost_analysis
        self.enable_predictive_scaling = enable_predictive_scaling

        self.logger = logging.getLogger(__name__)
        self._historical_recommendations: dict[str, list[ScalingRecommendation]] = {}

    async def recommend_scaling(
        self,
        isp_id: UUID,
        metrics: MetricsSnapshot,
        historical_metrics: Optional[list[MetricsSnapshot]] = None,
    ) -> ScalingRecommendation:
        """
        Generate scaling recommendation based on metrics analysis

        Args:
            isp_id: ISP/tenant identifier
            metrics: Current metrics snapshot
            historical_metrics: Historical metrics for trend analysis

        Returns:
            ScalingRecommendation with detailed analysis and guidance
        """
        recommendation = ScalingRecommendation(
            container_id=metrics.container_id,
            isp_id=isp_id,
            analysis_period_hours=self.analysis_window_hours,
        )

        try:
            # Prepare historical data
            if not historical_metrics:
                historical_metrics = []

            recommendation.metrics_analyzed = len(historical_metrics) + 1

            # Perform comprehensive analysis
            analyses = await asyncio.gather(
                self._analyze_resource_utilization(
                    metrics, historical_metrics, recommendation
                ),
                self._analyze_application_performance(
                    metrics, historical_metrics, recommendation
                ),
                self._analyze_growth_trends(
                    metrics, historical_metrics, recommendation
                ),
                self._analyze_cost_optimization(
                    metrics, historical_metrics, recommendation
                ),
                return_exceptions=True,
            )

            # Determine final recommendation
            await self._determine_final_recommendation(recommendation, analyses)

            # Store recommendation history
            await self._store_recommendation(recommendation)

        except Exception as e:
            self.logger.error(
                f"Scaling analysis failed for {metrics.container_id}: {e}"
            )
            recommendation.action = ScalingAction.NO_ACTION
            recommendation.confidence = 0.0
            recommendation.suggested_implementation = f"Analysis failed: {str(e)}"

        return recommendation

    async def _analyze_resource_utilization(
        self,
        current_metrics: MetricsSnapshot,
        historical_metrics: list[MetricsSnapshot],
        recommendation: ScalingRecommendation,
    ) -> dict[str, Any]:
        """Analyze resource utilization patterns"""
        analysis = {
            "cpu_analysis": {},
            "memory_analysis": {},
            "disk_analysis": {},
            "violations": [],
        }

        if not current_metrics.system_metrics:
            return analysis

        sys_metrics = current_metrics.system_metrics

        # Current resource analysis
        recommendation.current_resources = {
            "cpu_percent": sys_metrics.cpu_percent,
            "memory_percent": sys_metrics.memory_percent,
            "disk_percent": sys_metrics.disk_percent,
            "memory_bytes": sys_metrics.memory_usage_bytes,
            "memory_limit_bytes": sys_metrics.memory_limit_bytes,
        }

        # CPU Analysis
        cpu_trend = self._calculate_trend(
            [
                m.system_metrics.cpu_percent
                for m in historical_metrics[-10:]
                if m.system_metrics
            ]
        )

        analysis["cpu_analysis"] = {
            "current": sys_metrics.cpu_percent,
            "trend": cpu_trend,
            "threshold_violations": [],
        }

        if sys_metrics.cpu_percent >= self.thresholds.cpu_critical_threshold:
            analysis["violations"].append("cpu_critical")
            analysis["cpu_analysis"]["threshold_violations"].append("critical")
        elif sys_metrics.cpu_percent >= self.thresholds.cpu_scale_up_threshold:
            analysis["violations"].append("cpu_high")
            analysis["cpu_analysis"]["threshold_violations"].append("scale_up")
        elif sys_metrics.cpu_percent <= self.thresholds.cpu_scale_down_threshold:
            analysis["cpu_analysis"]["threshold_violations"].append("scale_down")

        # Memory Analysis
        memory_trend = self._calculate_trend(
            [
                m.system_metrics.memory_percent
                for m in historical_metrics[-10:]
                if m.system_metrics
            ]
        )

        analysis["memory_analysis"] = {
            "current": sys_metrics.memory_percent,
            "trend": memory_trend,
            "threshold_violations": [],
        }

        if sys_metrics.memory_percent >= self.thresholds.memory_critical_threshold:
            analysis["violations"].append("memory_critical")
            analysis["memory_analysis"]["threshold_violations"].append("critical")
        elif sys_metrics.memory_percent >= self.thresholds.memory_scale_up_threshold:
            analysis["violations"].append("memory_high")
            analysis["memory_analysis"]["threshold_violations"].append("scale_up")
        elif sys_metrics.memory_percent <= self.thresholds.memory_scale_down_threshold:
            analysis["memory_analysis"]["threshold_violations"].append("scale_down")

        # Disk Analysis
        if sys_metrics.disk_percent >= self.thresholds.disk_critical_threshold:
            analysis["violations"].append("disk_critical")
        elif sys_metrics.disk_percent >= self.thresholds.disk_scale_up_threshold:
            analysis["violations"].append("disk_high")

        analysis["disk_analysis"] = {
            "current": sys_metrics.disk_percent,
            "threshold_violations": [],
        }

        recommendation.threshold_violations.extend(analysis["violations"])

        return analysis

    async def _analyze_application_performance(
        self,
        current_metrics: MetricsSnapshot,
        historical_metrics: list[MetricsSnapshot],
        recommendation: ScalingRecommendation,
    ) -> dict[str, Any]:
        """Analyze application performance patterns"""
        analysis = {
            "performance_analysis": {},
            "error_analysis": {},
            "load_analysis": {},
            "violations": [],
        }

        if not current_metrics.application_metrics:
            return analysis

        app_metrics = current_metrics.application_metrics

        # Error rate analysis
        if app_metrics.error_rate >= self.thresholds.error_rate_threshold:
            analysis["violations"].append("high_error_rate")
            analysis["error_analysis"]["threshold_violation"] = True

        # Response time analysis
        if app_metrics.response_time_avg >= self.thresholds.response_time_threshold:
            analysis["violations"].append("slow_response_time")
            analysis["performance_analysis"]["threshold_violation"] = True

        # Load trend analysis
        request_rates = [
            m.application_metrics.request_rate
            for m in historical_metrics[-10:]
            if m.application_metrics and m.application_metrics.request_rate > 0
        ]

        if len(request_rates) >= 2:
            load_trend = self._calculate_trend(request_rates)
            analysis["load_analysis"]["trend"] = load_trend

            # Check for rapid growth
            if len(request_rates) >= 5:
                recent_avg = statistics.mean(request_rates[-3:])
                older_avg = (
                    statistics.mean(request_rates[-6:-3])
                    if len(request_rates) >= 6
                    else request_rates[0]
                )

                if older_avg > 0:
                    growth_rate = ((recent_avg - older_avg) / older_avg) * 100
                    if growth_rate >= self.thresholds.request_rate_growth_threshold:
                        analysis["violations"].append("rapid_load_growth")
                        analysis["load_analysis"]["growth_rate"] = growth_rate

        recommendation.threshold_violations.extend(analysis["violations"])

        return analysis

    async def _analyze_growth_trends(
        self,
        current_metrics: MetricsSnapshot,
        historical_metrics: list[MetricsSnapshot],
        recommendation: ScalingRecommendation,
    ) -> dict[str, Any]:
        """Analyze customer growth and usage trends"""
        analysis = {"growth_indicators": {}, "usage_patterns": {}, "predictions": {}}

        if len(historical_metrics) < 5:
            analysis["insufficient_data"] = True
            return analysis

        # Analyze resource usage trends over time
        cpu_values = [
            m.system_metrics.cpu_percent for m in historical_metrics if m.system_metrics
        ]
        memory_values = [
            m.system_metrics.memory_percent
            for m in historical_metrics
            if m.system_metrics
        ]

        if cpu_values:
            cpu_trend = self._calculate_trend(cpu_values)
            analysis["growth_indicators"]["cpu_trend"] = cpu_trend
            recommendation.trend_analysis["cpu"] = self._trend_to_string(cpu_trend)

        if memory_values:
            memory_trend = self._calculate_trend(memory_values)
            analysis["growth_indicators"]["memory_trend"] = memory_trend
            recommendation.trend_analysis["memory"] = self._trend_to_string(
                memory_trend
            )

        # Predictive analysis for next period
        if self.enable_predictive_scaling and len(historical_metrics) >= 10:
            try:
                predicted_cpu = self._predict_next_value(cpu_values[-10:])
                predicted_memory = self._predict_next_value(memory_values[-10:])

                analysis["predictions"] = {
                    "predicted_cpu": predicted_cpu,
                    "predicted_memory": predicted_memory,
                }

                # Check if predictions exceed thresholds
                if (
                    predicted_cpu
                    and predicted_cpu >= self.thresholds.cpu_scale_up_threshold
                ):
                    analysis["growth_indicators"]["predicted_cpu_violation"] = True
                if (
                    predicted_memory
                    and predicted_memory >= self.thresholds.memory_scale_up_threshold
                ):
                    analysis["growth_indicators"]["predicted_memory_violation"] = True

            except Exception as e:
                self.logger.debug(f"Prediction analysis failed: {e}")

        return analysis

    async def _analyze_cost_optimization(
        self,
        current_metrics: MetricsSnapshot,
        historical_metrics: list[MetricsSnapshot],
        recommendation: ScalingRecommendation,
    ) -> dict[str, Any]:
        """Analyze cost optimization opportunities"""
        analysis = {"cost_analysis": {}, "optimization_opportunities": []}

        if not self.enable_cost_analysis or not current_metrics.system_metrics:
            return analysis

        sys_metrics = current_metrics.system_metrics

        # Identify underutilized resources
        if (
            sys_metrics.cpu_percent <= self.thresholds.cpu_scale_down_threshold
            and sys_metrics.memory_percent
            <= self.thresholds.memory_scale_down_threshold
        ):
            analysis["optimization_opportunities"].append("underutilized_resources")

            # Estimate cost savings
            current_cost = self._estimate_current_cost(sys_metrics)
            optimized_cost = current_cost * 0.7  # Rough 30% reduction estimate

            analysis["cost_analysis"] = {
                "current_estimated_cost": current_cost,
                "optimized_estimated_cost": optimized_cost,
                "potential_savings": current_cost - optimized_cost,
            }

            recommendation.estimated_cost_impact = optimized_cost - current_cost

        # Check for over-provisioning
        if len(historical_metrics) >= 10:
            recent_cpu_avg = statistics.mean(
                [
                    m.system_metrics.cpu_percent
                    for m in historical_metrics[-10:]
                    if m.system_metrics
                ]
            )
            recent_memory_avg = statistics.mean(
                [
                    m.system_metrics.memory_percent
                    for m in historical_metrics[-10:]
                    if m.system_metrics
                ]
            )

            if recent_cpu_avg <= 30 and recent_memory_avg <= 40:
                analysis["optimization_opportunities"].append("over_provisioned")

        return analysis

    async def _determine_final_recommendation(
        self, recommendation: ScalingRecommendation, analyses: list[Any]
    ) -> None:
        """Determine final scaling recommendation based on all analyses"""

        # Extract valid analyses
        valid_analyses = [a for a in analyses if isinstance(a, dict)]

        # Collect all violations
        all_violations = []
        for analysis in valid_analyses:
            if "violations" in analysis:
                all_violations.extend(analysis["violations"])

        # Determine action based on violations and trends
        critical_violations = [v for v in all_violations if "critical" in v]
        high_violations = [
            v
            for v in all_violations
            if v
            in [
                "cpu_high",
                "memory_high",
                "disk_high",
                "high_error_rate",
                "slow_response_time",
                "rapid_load_growth",
            ]
        ]

        if critical_violations:
            recommendation.action = ScalingAction.SCALE_UP
            recommendation.urgency = ScalingUrgency.CRITICAL
            recommendation.reason = self._violation_to_reason(critical_violations[0])
            recommendation.confidence = 0.95

        elif high_violations:
            recommendation.action = ScalingAction.SCALE_UP
            recommendation.urgency = ScalingUrgency.HIGH
            recommendation.reason = self._violation_to_reason(high_violations[0])
            recommendation.confidence = 0.85

        elif self._should_scale_down(all_violations, recommendation.trend_analysis):
            recommendation.action = ScalingAction.SCALE_DOWN
            recommendation.urgency = ScalingUrgency.MEDIUM
            recommendation.reason = ScalingReason.LOW_UTILIZATION
            recommendation.confidence = 0.70

        elif self._has_optimization_opportunity(valid_analyses):
            recommendation.action = ScalingAction.OPTIMIZE
            recommendation.urgency = ScalingUrgency.LOW
            recommendation.reason = ScalingReason.COST_OPTIMIZATION
            recommendation.confidence = 0.60

        else:
            recommendation.action = ScalingAction.NO_ACTION
            recommendation.urgency = ScalingUrgency.LOW
            recommendation.confidence = 0.80

        # Generate implementation guidance
        await self._generate_implementation_guidance(recommendation, valid_analyses)

    def _should_scale_down(
        self, violations: list[str], trend_analysis: dict[str, str]
    ) -> bool:
        """Determine if scaling down is appropriate"""
        # Check for sustained low utilization
        low_cpu = any(
            "cpu" in trend and "decreasing" in trend.lower()
            for trend in trend_analysis.values()
        )
        low_memory = any(
            "memory" in trend and "decreasing" in trend.lower()
            for trend in trend_analysis.values()
        )

        no_high_violations = not any(
            v in violations
            for v in [
                "cpu_high",
                "memory_high",
                "high_error_rate",
                "slow_response_time",
            ]
        )

        return (low_cpu or low_memory) and no_high_violations

    def _has_optimization_opportunity(self, analyses: list[dict[str, Any]]) -> bool:
        """Check if there are optimization opportunities"""
        for analysis in analyses:
            if "optimization_opportunities" in analysis:
                return len(analysis["optimization_opportunities"]) > 0
        return False

    async def _generate_implementation_guidance(
        self, recommendation: ScalingRecommendation, analyses: list[dict[str, Any]]
    ) -> None:
        """Generate implementation guidance for the recommendation"""

        if recommendation.action == ScalingAction.SCALE_UP:
            if recommendation.urgency == ScalingUrgency.CRITICAL:
                recommendation.suggested_implementation = (
                    "IMMEDIATE: Increase CPU/Memory limits by 50-100%. "
                    "Consider horizontal scaling if vertical scaling is limited."
                )
                recommendation.rollback_plan = (
                    "Monitor for 30 minutes. If issues persist, "
                    "scale back and investigate application bottlenecks."
                )
            else:
                recommendation.suggested_implementation = (
                    "Gradually increase resources by 25-50% during low-traffic period. "
                    "Monitor impact before full implementation."
                )
                recommendation.rollback_plan = (
                    "Revert resource limits if performance doesn't improve "
                    "within 2 hours or costs increase significantly."
                )

        elif recommendation.action == ScalingAction.SCALE_DOWN:
            recommendation.suggested_implementation = (
                "Reduce resource allocation by 20-30% during off-peak hours. "
                "Monitor closely for performance degradation."
            )
            recommendation.rollback_plan = (
                "Immediately restore previous resource levels if "
                "performance metrics deteriorate."
            )

        elif recommendation.action == ScalingAction.OPTIMIZE:
            recommendation.suggested_implementation = (
                "Review application configuration, optimize database queries, "
                "and implement caching where appropriate."
            )
            recommendation.rollback_plan = (
                "Keep backup of current configuration. "
                "Revert optimizations if stability is affected."
            )

        # Add monitoring recommendations
        recommendation.monitoring_recommendations = [
            "Monitor CPU and Memory usage every 5 minutes",
            "Track application response times and error rates",
            "Set up alerts for threshold violations",
            "Review scaling decision after 24 hours",
        ]

        if recommendation.urgency in [ScalingUrgency.CRITICAL, ScalingUrgency.HIGH]:
            recommendation.monitoring_recommendations.extend(
                [
                    "Enable real-time monitoring during scaling operation",
                    "Have rollback procedure ready",
                    "Monitor customer impact metrics",
                ]
            )

    async def _store_recommendation(
        self, recommendation: ScalingRecommendation
    ) -> None:
        """Store recommendation in history"""
        container_id = recommendation.container_id

        if container_id not in self._historical_recommendations:
            self._historical_recommendations[container_id] = []

        self._historical_recommendations[container_id].append(recommendation)

        # Keep only recent recommendations (last 30 days)
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=30)
        self._historical_recommendations[container_id] = [
            rec
            for rec in self._historical_recommendations[container_id]
            if rec.timestamp > cutoff_time
        ]

    def get_recommendation_history(
        self, container_id: str, days: int = 7
    ) -> list[ScalingRecommendation]:
        """Get historical recommendations for container"""
        if container_id not in self._historical_recommendations:
            return []

        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        return [
            rec
            for rec in self._historical_recommendations[container_id]
            if rec.timestamp > cutoff_time
        ]

    # Utility methods
    def _calculate_trend(self, values: list[float]) -> float:
        """Calculate trend using simple linear regression slope"""
        if len(values) < 2:
            return 0.0

        try:
            n = len(values)
            x_values = list(range(n))

            x_mean = statistics.mean(x_values)
            y_mean = statistics.mean(values)

            numerator = sum(
                (x - x_mean) * (y - y_mean) for x, y in zip(x_values, values)
            )
            denominator = sum((x - x_mean) ** 2 for x in x_values)

            return numerator / denominator if denominator != 0 else 0.0

        except Exception:
            return 0.0

    def _trend_to_string(self, trend: float) -> str:
        """Convert trend value to descriptive string"""
        if abs(trend) < 0.1:
            return "stable"
        elif trend > 0:
            return "increasing" if trend > 1.0 else "slightly_increasing"
        else:
            return "decreasing" if trend < -1.0 else "slightly_decreasing"

    def _predict_next_value(self, values: list[float]) -> Optional[float]:
        """Simple linear prediction for next value"""
        if len(values) < 3:
            return None

        try:
            trend = self._calculate_trend(values)
            return values[-1] + trend
        except Exception:
            return None

    def _violation_to_reason(self, violation: str) -> ScalingReason:
        """Convert violation string to scaling reason"""
        violation_mapping = {
            "cpu_critical": ScalingReason.HIGH_CPU,
            "cpu_high": ScalingReason.HIGH_CPU,
            "memory_critical": ScalingReason.HIGH_MEMORY,
            "memory_high": ScalingReason.HIGH_MEMORY,
            "disk_critical": ScalingReason.HIGH_DISK,
            "disk_high": ScalingReason.HIGH_DISK,
            "high_error_rate": ScalingReason.HIGH_ERROR_RATE,
            "slow_response_time": ScalingReason.PERFORMANCE_DEGRADATION,
            "rapid_load_growth": ScalingReason.CUSTOMER_GROWTH,
        }
        return violation_mapping.get(violation, ScalingReason.HIGH_CPU)

    def _estimate_current_cost(self, sys_metrics: SystemMetrics) -> float:
        """Rough cost estimation based on resource usage"""
        # This would be implemented with actual pricing models
        # For now, return a placeholder calculation
        cpu_cost = sys_metrics.cpu_count * 0.05  # $0.05 per vCPU per hour
        memory_cost = (
            sys_metrics.memory_limit_bytes / (1024**3)
        ) * 0.01  # $0.01 per GB per hour
        return cpu_cost + memory_cost


# Convenience function for direct usage
async def recommend_scaling(
    isp_id: UUID,
    metrics: MetricsSnapshot,
    historical_metrics: Optional[list[MetricsSnapshot]] = None,
) -> ScalingRecommendation:
    """
    Generate scaling recommendation with default settings

    Args:
        isp_id: ISP/tenant identifier
        metrics: Current metrics snapshot
        historical_metrics: Historical metrics for trend analysis

    Returns:
        ScalingRecommendation with detailed analysis
    """
    advisor = ScalingAdvisor()
    return await advisor.recommend_scaling(isp_id, metrics, historical_metrics)
