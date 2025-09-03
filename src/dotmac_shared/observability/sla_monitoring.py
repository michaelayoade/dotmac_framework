"""
SLA monitoring and performance baseline tracking for DotMac services.
Provides comprehensive SLA compliance monitoring with historical baselines.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics
import json

from opentelemetry import trace, metrics

from .logging import get_logger, business_logger
from .otel import get_meter

logger = get_logger("dotmac.sla_monitoring")

# Get OpenTelemetry meter for SigNoz metrics
meter = get_meter(__name__)

# SLA SigNoz metrics using OpenTelemetry
sla_uptime_gauge = meter.create_gauge(
    'dotmac_sla_uptime_percent',
    description='Service uptime percentage for SLA tracking'
)

sla_response_time_histogram = meter.create_histogram(
    'dotmac_sla_response_time_seconds',
    description='Response time for SLA tracking',
    unit='s'
)

sla_breach_counter = meter.create_counter(
    'dotmac_sla_breach_total',
    description='Total SLA breaches'
)

sla_error_budget_remaining_gauge = meter.create_gauge(
    'dotmac_sla_error_budget_remaining_percent',
    description='Remaining error budget percentage'
)

performance_baseline_score_gauge = meter.create_gauge(
    'dotmac_performance_baseline_score',
    description='Performance baseline score (0-100)'
)

performance_deviation_gauge = meter.create_gauge(
    'dotmac_performance_deviation_percent',
    description='Performance deviation from baseline'
)

@dataclass
class SLATarget:
    """SLA target definition."""
    service_name: str
    tier: str  # e.g., "standard", "premium", "enterprise"
    uptime_percent: float  # e.g., 99.9
    response_time_ms: float  # e.g., 500
    error_rate_percent: float  # e.g., 1.0
    measurement_period_hours: int = 24
    error_budget_percent: float = None  # Calculated from uptime_percent
    
    def __post_init__(self):
        if self.error_budget_percent is None:
            self.error_budget_percent = 100 - self.uptime_percent

@dataclass
class PerformanceBaseline:
    """Performance baseline configuration."""
    metric_name: str
    component: str
    baseline_value: float
    tolerance_percent: float  # Acceptable deviation percentage
    measurement_window_hours: int = 24
    update_frequency_hours: int = 168  # Weekly
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def is_within_tolerance(self, current_value: float) -> bool:
        """Check if current value is within tolerance."""
        deviation = abs(current_value - self.baseline_value) / self.baseline_value * 100
        return deviation <= self.tolerance_percent
    
    def calculate_deviation_percent(self, current_value: float) -> float:
        """Calculate deviation percentage from baseline."""
        return (current_value - self.baseline_value) / self.baseline_value * 100

@dataclass
class SLAMeasurement:
    """Individual SLA measurement."""
    service_name: str
    tier: str
    timestamp: datetime
    uptime_percent: float
    avg_response_time_ms: float
    error_rate_percent: float
    is_breach: bool
    breach_details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceMeasurement:
    """Individual performance measurement."""
    metric_name: str
    component: str
    timestamp: datetime
    value: float
    baseline_deviation_percent: float
    is_anomaly: bool

class SLAMonitor:
    """
    Comprehensive SLA monitoring and baseline tracking system.
    
    Features:
    - Multi-tier SLA tracking with customizable targets
    - Error budget monitoring and alerting
    - Performance baseline establishment and drift detection
    - Historical trend analysis
    - Automated SLA reporting
    """
    
    def __init__(self):
        self.sla_targets: Dict[str, Dict[str, SLATarget]] = defaultdict(dict)  # service -> tier -> target
        self.performance_baselines: Dict[str, Dict[str, PerformanceBaseline]] = defaultdict(dict)  # metric -> component -> baseline
        
        # Historical data storage
        self.sla_measurements: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.performance_measurements: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        
        # Current SLA status
        self.current_sla_status: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(lambda: defaultdict(dict))
        
        # Error budget tracking
        self.error_budgets: Dict[str, Dict[str, float]] = defaultdict(dict)  # service -> tier -> remaining_percent
        
        # Initialize default SLA targets
        self._initialize_default_sla_targets()
        self._initialize_default_baselines()
        
        # Initialize background tasks flag (don't start them automatically)
        self._background_tasks_started = False
    
    def start_background_tasks(self):
        """Start background monitoring tasks. Call this when event loop is available."""
        if self._background_tasks_started:
            return
        
        self._background_tasks_started = True
        
        # Start monitoring tasks
        asyncio.create_task(self._sla_measurement_task())
        asyncio.create_task(self._baseline_monitoring_task())
        asyncio.create_task(self._sla_reporting_task())
        asyncio.create_task(self._error_budget_monitoring_task())
    
    def _initialize_default_sla_targets(self):
        """Initialize default SLA targets for DotMac services."""
        default_targets = [
            # API SLA Targets
            SLATarget("api_management", "standard", 99.9, 500, 1.0),
            SLATarget("api_management", "premium", 99.95, 300, 0.5),
            SLATarget("api_management", "enterprise", 99.99, 200, 0.1),
            
            # Database SLA Targets
            SLATarget("database", "standard", 99.95, 100, 0.1),
            SLATarget("database", "premium", 99.99, 50, 0.05),
            
            # Cache SLA Targets
            SLATarget("cache", "standard", 99.5, 10, 2.0),
            SLATarget("cache", "premium", 99.9, 5, 1.0),
            
            # Partner Portal SLA Targets
            SLATarget("partner_portal", "standard", 99.0, 1000, 2.0),
            SLATarget("partner_portal", "premium", 99.5, 750, 1.5),
            
            # Payment Processing SLA Targets
            SLATarget("payment_processing", "standard", 99.9, 2000, 0.1),
            SLATarget("payment_processing", "premium", 99.95, 1500, 0.05),
        ]
        
        for target in default_targets:
            self.sla_targets[target.service_name][target.tier] = target
    
    def _initialize_default_baselines(self):
        """Initialize default performance baselines."""
        default_baselines = [
            # API Performance Baselines
            PerformanceBaseline("response_time_p95", "api", 500.0, 20.0),
            PerformanceBaseline("request_rate", "api", 1000.0, 50.0),
            PerformanceBaseline("error_rate", "api", 1.0, 100.0),
            
            # Database Performance Baselines
            PerformanceBaseline("query_duration_p95", "database", 100.0, 25.0),
            PerformanceBaseline("connection_pool_usage", "database", 50.0, 30.0),
            PerformanceBaseline("slow_queries_per_hour", "database", 10.0, 50.0),
            
            # System Resource Baselines
            PerformanceBaseline("cpu_usage_avg", "system", 60.0, 25.0),
            PerformanceBaseline("memory_usage_avg", "system", 70.0, 20.0),
            PerformanceBaseline("disk_io_rate", "system", 1000.0, 40.0),
            
            # Business Process Baselines
            PerformanceBaseline("tenant_provisioning_time", "business", 300.0, 30.0),
            PerformanceBaseline("commission_calculation_time", "business", 60.0, 50.0),
            PerformanceBaseline("partner_onboarding_time", "business", 1800.0, 25.0),
        ]
        
        for baseline in default_baselines:
            self.performance_baselines[baseline.metric_name][baseline.component] = baseline
    
    async def _sla_measurement_task(self):
        """Background task to measure SLA compliance."""
        while True:
            try:
                await asyncio.sleep(60)  # Measure every minute
                
                for service_name, tiers in self.sla_targets.items():
                    for tier, target in tiers.items():
                        measurement = await self._measure_sla_compliance(service_name, tier, target)
                        
                        # Store measurement
                        key = f"{service_name}:{tier}"
                        self.sla_measurements[key].append(measurement)
                        
                        # Update current status
                        self.current_sla_status[service_name][tier] = {
                            "uptime_percent": measurement.uptime_percent,
                            "avg_response_time_ms": measurement.avg_response_time_ms,
                            "error_rate_percent": measurement.error_rate_percent,
                            "is_breach": measurement.is_breach,
                            "last_updated": measurement.timestamp
                        }
                        
                        # Update SigNoz metrics
                        sla_uptime_gauge.set(
                            measurement.uptime_percent,
                            attributes={
                                "service": service_name,
                                "tier": tier,
                                "period": "1h"
                            }
                        )
                        
                        sla_response_time_histogram.record(
                            measurement.avg_response_time_ms / 1000,  # Convert to seconds
                            attributes={
                                "service": service_name,
                                "tier": tier
                            }
                        )
                        
                        if measurement.is_breach:
                            sla_breach_counter.add(
                                1,
                                attributes={
                                    "service": service_name,
                                    "tier": tier,
                                    "breach_type": self._determine_breach_type(measurement, target)
                                }
                            )
                            
                            business_logger.warning(
                                f"SLA breach detected: {service_name} ({tier})",
                                service=service_name,
                                tier=tier,
                                uptime=measurement.uptime_percent,
                                target_uptime=target.uptime_percent,
                                response_time=measurement.avg_response_time_ms,
                                target_response_time=target.response_time_ms
                            )
                
            except Exception as e:
                logger.error("Error in SLA measurement task", error=str(e))
    
    async def _measure_sla_compliance(self, service_name: str, tier: str, target: SLATarget) -> SLAMeasurement:
        """Measure SLA compliance for a specific service and tier."""
        now = datetime.now(timezone.utc)
        
        # This would implement actual SLA measurement logic
        # For now, we'll simulate the measurements
        
        # Simulate uptime measurement (would query actual service health)
        uptime_percent = await self._calculate_uptime_percent(service_name, target.measurement_period_hours)
        
        # Simulate response time measurement (would query actual metrics)
        avg_response_time_ms = await self._calculate_avg_response_time(service_name, target.measurement_period_hours)
        
        # Simulate error rate measurement (would query actual error metrics)
        error_rate_percent = await self._calculate_error_rate_percent(service_name, target.measurement_period_hours)
        
        # Determine if this is a breach
        is_breach = (
            uptime_percent < target.uptime_percent or
            avg_response_time_ms > target.response_time_ms or
            error_rate_percent > target.error_rate_percent
        )
        
        breach_details = {}
        if is_breach:
            breach_details = {
                "uptime_breach": uptime_percent < target.uptime_percent,
                "response_time_breach": avg_response_time_ms > target.response_time_ms,
                "error_rate_breach": error_rate_percent > target.error_rate_percent
            }
        
        return SLAMeasurement(
            service_name=service_name,
            tier=tier,
            timestamp=now,
            uptime_percent=uptime_percent,
            avg_response_time_ms=avg_response_time_ms,
            error_rate_percent=error_rate_percent,
            is_breach=is_breach,
            breach_details=breach_details
        )
    
    async def _baseline_monitoring_task(self):
        """Background task to monitor performance against baselines."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                for metric_name, components in self.performance_baselines.items():
                    for component, baseline in components.items():
                        current_value = await self._get_current_performance_value(metric_name, component)
                        if current_value is None:
                            continue
                        
                        deviation_percent = baseline.calculate_deviation_percent(current_value)
                        is_anomaly = not baseline.is_within_tolerance(current_value)
                        
                        # Create measurement
                        measurement = PerformanceMeasurement(
                            metric_name=metric_name,
                            component=component,
                            timestamp=datetime.now(timezone.utc),
                            value=current_value,
                            baseline_deviation_percent=deviation_percent,
                            is_anomaly=is_anomaly
                        )
                        
                        # Store measurement
                        key = f"{metric_name}:{component}"
                        self.performance_measurements[key].append(measurement)
                        
                        # Update SigNoz metrics
                        baseline_score = max(0, 100 - abs(deviation_percent))
                        performance_baseline_score_gauge.set(
                            baseline_score,
                            attributes={
                                "metric_type": metric_name,
                                "component": component
                            }
                        )
                        
                        performance_deviation_gauge.set(
                            deviation_percent,
                            attributes={
                                "metric_type": metric_name,
                                "component": component
                            }
                        )
                        
                        # Alert on anomalies
                        if is_anomaly:
                            logger.warning(
                                f"Performance baseline anomaly detected: {metric_name} ({component})",
                                metric=metric_name,
                                component=component,
                                current_value=current_value,
                                baseline_value=baseline.baseline_value,
                                deviation_percent=deviation_percent,
                                tolerance_percent=baseline.tolerance_percent
                            )
                
            except Exception as e:
                logger.error("Error in baseline monitoring task", error=str(e))
    
    async def _error_budget_monitoring_task(self):
        """Background task to monitor error budgets."""
        while True:
            try:
                await asyncio.sleep(3600)  # Check hourly
                
                for service_name, tiers in self.sla_targets.items():
                    for tier, target in tiers.items():
                        remaining_budget = await self._calculate_error_budget_remaining(service_name, tier, target)
                        
                        # Store current budget
                        self.error_budgets[service_name][tier] = remaining_budget
                        
                        # Update Prometheus metric
                        SLA_ERROR_BUDGET_REMAINING.labels(
                            service=service_name,
                            tier=tier,
                            period="30d"
                        ).set(remaining_budget)
                        
                        # Alert on low error budget
                        if remaining_budget < 10.0:  # Less than 10% remaining
                            business_logger.critical(
                                f"Low error budget warning: {service_name} ({tier})",
                                service=service_name,
                                tier=tier,
                                remaining_budget_percent=remaining_budget,
                                target_uptime=target.uptime_percent
                            )
                        elif remaining_budget < 25.0:  # Less than 25% remaining
                            business_logger.warning(
                                f"Error budget alert: {service_name} ({tier})",
                                service=service_name,
                                tier=tier,
                                remaining_budget_percent=remaining_budget
                            )
                
            except Exception as e:
                logger.error("Error in error budget monitoring", error=str(e))
    
    async def _sla_reporting_task(self):
        """Background task to generate SLA reports."""
        while True:
            try:
                # Generate daily reports at midnight
                await asyncio.sleep(3600)  # Check every hour
                
                now = datetime.now(timezone.utc)
                if now.hour == 0:  # Midnight UTC
                    await self._generate_daily_sla_report()
                
                # Generate weekly reports on Sundays
                if now.weekday() == 6 and now.hour == 1:  # Sunday at 1 AM
                    await self._generate_weekly_sla_report()
                
                # Generate monthly reports on the 1st of each month
                if now.day == 1 and now.hour == 2:  # 1st of month at 2 AM
                    await self._generate_monthly_sla_report()
                
            except Exception as e:
                logger.error("Error in SLA reporting task", error=str(e))
    
    # Placeholder methods for actual metric collection
    # These would be implemented to query your actual monitoring systems
    
    async def _calculate_uptime_percent(self, service_name: str, period_hours: int) -> float:
        """Calculate uptime percentage for the given period."""
        # Simulate uptime calculation
        import random
        return 99.0 + random.uniform(0, 1.0)
    
    async def _calculate_avg_response_time(self, service_name: str, period_hours: int) -> float:
        """Calculate average response time for the given period."""
        # Simulate response time calculation
        import random
        base_time = {"api_management": 300, "database": 50, "cache": 5}.get(service_name, 200)
        return base_time + random.uniform(-50, 100)
    
    async def _calculate_error_rate_percent(self, service_name: str, period_hours: int) -> float:
        """Calculate error rate percentage for the given period."""
        # Simulate error rate calculation
        import random
        return random.uniform(0.1, 2.0)
    
    async def _get_current_performance_value(self, metric_name: str, component: str) -> Optional[float]:
        """Get current performance value for a metric."""
        # Simulate performance value retrieval
        import random
        
        baselines = {
            "response_time_p95": 500,
            "request_rate": 1000,
            "error_rate": 1,
            "query_duration_p95": 100,
            "connection_pool_usage": 50,
            "cpu_usage_avg": 60,
            "memory_usage_avg": 70
        }
        
        if metric_name in baselines:
            base_value = baselines[metric_name]
            return base_value + random.uniform(-base_value * 0.3, base_value * 0.3)
        
        return None
    
    async def _calculate_error_budget_remaining(self, service_name: str, tier: str, target: SLATarget) -> float:
        """Calculate remaining error budget percentage."""
        # This would implement actual error budget calculation
        # For now, simulate the calculation
        import random
        return random.uniform(20, 90)
    
    def _determine_breach_type(self, measurement: SLAMeasurement, target: SLATarget) -> str:
        """Determine the type of SLA breach."""
        if measurement.uptime_percent < target.uptime_percent:
            return "uptime"
        elif measurement.avg_response_time_ms > target.response_time_ms:
            return "response_time"
        elif measurement.error_rate_percent > target.error_rate_percent:
            return "error_rate"
        else:
            return "unknown"
    
    async def _generate_daily_sla_report(self):
        """Generate daily SLA compliance report."""
        business_logger.info("Generating daily SLA report")
        
        report_data = {
            "date": datetime.now(timezone.utc).date().isoformat(),
            "services": {}
        }
        
        for service_name, tiers in self.current_sla_status.items():
            report_data["services"][service_name] = tiers
        
        # Store report (would typically save to database or file)
        logger.info("Daily SLA report generated", report=json.dumps(report_data, indent=2))
    
    async def _generate_weekly_sla_report(self):
        """Generate weekly SLA compliance report."""
        business_logger.info("Generating weekly SLA report")
    
    async def _generate_monthly_sla_report(self):
        """Generate monthly SLA compliance report."""
        business_logger.info("Generating monthly SLA report")
    
    def get_sla_status(self, service_name: str = None, tier: str = None) -> Dict[str, Any]:
        """Get current SLA status."""
        if service_name and tier:
            return self.current_sla_status.get(service_name, {}).get(tier, {})
        elif service_name:
            return self.current_sla_status.get(service_name, {})
        else:
            return dict(self.current_sla_status)
    
    def get_performance_baseline_status(self, metric_name: str = None, component: str = None) -> Dict[str, Any]:
        """Get performance baseline status."""
        if metric_name and component:
            baseline = self.performance_baselines.get(metric_name, {}).get(component)
            if baseline:
                key = f"{metric_name}:{component}"
                recent_measurements = list(self.performance_measurements[key])[-10:]  # Last 10 measurements
                return {
                    "baseline_value": baseline.baseline_value,
                    "tolerance_percent": baseline.tolerance_percent,
                    "recent_measurements": [
                        {
                            "timestamp": m.timestamp.isoformat(),
                            "value": m.value,
                            "deviation_percent": m.baseline_deviation_percent,
                            "is_anomaly": m.is_anomaly
                        }
                        for m in recent_measurements
                    ]
                }
        
        return {}
    
    def add_sla_target(self, target: SLATarget):
        """Add a new SLA target."""
        self.sla_targets[target.service_name][target.tier] = target
    
    def add_performance_baseline(self, baseline: PerformanceBaseline):
        """Add a new performance baseline."""
        self.performance_baselines[baseline.metric_name][baseline.component] = baseline


# Global SLA monitor instance
sla_monitor = SLAMonitor()

# Convenience functions
def get_sla_status(service_name: str = None, tier: str = None) -> Dict[str, Any]:
    """Get current SLA status."""
    return sla_monitor.get_sla_status(service_name, tier)

def get_performance_baseline_status(metric_name: str = None, component: str = None) -> Dict[str, Any]:
    """Get performance baseline status."""
    return sla_monitor.get_performance_baseline_status(metric_name, component)

def add_custom_sla_target(service_name: str, tier: str, uptime_percent: float, 
                         response_time_ms: float, error_rate_percent: float):
    """Add a custom SLA target."""
    target = SLATarget(service_name, tier, uptime_percent, response_time_ms, error_rate_percent)
    sla_monitor.add_sla_target(target)

def add_custom_baseline(metric_name: str, component: str, baseline_value: float, 
                       tolerance_percent: float):
    """Add a custom performance baseline."""
    baseline = PerformanceBaseline(metric_name, component, baseline_value, tolerance_percent)
    sla_monitor.add_performance_baseline(baseline)