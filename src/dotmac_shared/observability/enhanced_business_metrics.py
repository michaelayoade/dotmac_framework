"""
Enhanced business metrics monitoring with anomaly detection and SLA tracking.
Builds upon existing business metrics with advanced monitoring capabilities.
"""

import time
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics

from prometheus_client import Counter, Histogram, Gauge, Info
from opentelemetry import trace

from .business_metrics import business_metrics
from .logging import get_logger, business_logger
from .otel import get_meter

logger = get_logger("dotmac.enhanced_business_metrics")

# Enhanced Prometheus business metrics
REVENUE_METRICS = Counter(
    'dotmac_revenue_total_usd',
    'Total revenue processed',
    ['revenue_type', 'partner_id', 'tenant_id']
)

CUSTOMER_LIFECYCLE = Counter(
    'dotmac_customer_lifecycle_events_total',
    'Customer lifecycle events',
    ['event_type', 'partner_id', 'service_tier']
)

PARTNER_PERFORMANCE = Gauge(
    'dotmac_partner_performance_score',
    'Partner performance score (0-100)',
    ['partner_id']
)

SLA_COMPLIANCE = Gauge(
    'dotmac_sla_compliance_percent',
    'SLA compliance percentage',
    ['service_type', 'sla_tier']
)

BUSINESS_KPI = Gauge(
    'dotmac_business_kpi',
    'Business KPI metrics',
    ['kpi_name', 'category']
)

ANOMALY_SCORE = Gauge(
    'dotmac_anomaly_score',
    'Anomaly detection score (0-1)',
    ['metric_type', 'entity_id']
)

TENANT_HEALTH_SCORE = Gauge(
    'dotmac_tenant_health_score',
    'Tenant health score (0-100)',
    ['tenant_id']
)

COMMISSION_METRICS = Histogram(
    'dotmac_commission_amounts_usd',
    'Commission amounts processed',
    ['partner_id', 'commission_type'],
    buckets=(10, 50, 100, 250, 500, 1000, 2500, 5000, 10000)
)

CHURN_PREDICTION = Gauge(
    'dotmac_churn_risk_score',
    'Customer churn risk score (0-1)',
    ['customer_id', 'risk_category']
)

SYSTEM_AVAILABILITY = Gauge(
    'dotmac_system_availability_percent',
    'System availability percentage',
    ['component', 'tenant_id']
)

@dataclass
class MetricHistory:
    """Container for historical metric data."""
    values: deque = field(default_factory=lambda: deque(maxlen=1000))
    timestamps: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def add_value(self, value: float, timestamp: Optional[datetime] = None):
        """Add a metric value with timestamp."""
        if timestamp is None:
            timestamp = datetime.utcnow()
        self.values.append(value)
        self.timestamps.append(timestamp)
    
    def get_recent_values(self, minutes: int = 60) -> List[float]:
        """Get values from the last N minutes."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        recent_values = []
        for i, timestamp in enumerate(self.timestamps):
            if timestamp >= cutoff:
                recent_values.append(self.values[i])
        return recent_values
    
    @property
    def mean(self) -> float:
        """Calculate mean of all values."""
        return statistics.mean(self.values) if self.values else 0.0
    
    @property
    def std_dev(self) -> float:
        """Calculate standard deviation."""
        return statistics.stdev(self.values) if len(self.values) > 1 else 0.0


@dataclass
class SLATarget:
    """SLA target configuration."""
    name: str
    target_percent: float
    measurement_window_minutes: int
    grace_period_minutes: int = 5
    
    def is_breach(self, current_percent: float, duration_minutes: int) -> bool:
        """Check if current performance constitutes an SLA breach."""
        if current_percent >= self.target_percent:
            return False
        return duration_minutes > self.grace_period_minutes


@dataclass
class AnomalyThreshold:
    """Anomaly detection threshold configuration."""
    metric_name: str
    std_dev_multiplier: float = 2.0
    minimum_samples: int = 10
    alert_threshold: float = 0.8
    
    def detect_anomaly(self, current_value: float, history: MetricHistory) -> float:
        """Detect anomaly and return anomaly score (0-1)."""
        if len(history.values) < self.minimum_samples:
            return 0.0
        
        mean = history.mean
        std_dev = history.std_dev
        
        if std_dev == 0:
            return 0.0
        
        # Calculate z-score
        z_score = abs(current_value - mean) / std_dev
        
        # Convert to anomaly score (0-1)
        anomaly_score = min(z_score / self.std_dev_multiplier, 1.0)
        
        return anomaly_score


class EnhancedBusinessMetricsCollector:
    """
    Enhanced business metrics collector with anomaly detection and SLA monitoring.
    """
    
    def __init__(self):
        self.metric_histories: Dict[str, MetricHistory] = defaultdict(MetricHistory)
        self.sla_targets = self._initialize_sla_targets()
        self.anomaly_thresholds = self._initialize_anomaly_thresholds()
        
        # Partner performance tracking
        self.partner_metrics: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.tenant_health_cache: Dict[str, float] = {}
        
        # Start background monitoring tasks
        asyncio.create_task(self._business_metrics_collector())
        asyncio.create_task(self._sla_monitor())
        asyncio.create_task(self._anomaly_detector())
        asyncio.create_task(self._partner_performance_calculator())
        asyncio.create_task(self._tenant_health_monitor())
    
    def _initialize_sla_targets(self) -> Dict[str, SLATarget]:
        """Initialize SLA targets."""
        return {
            "api_availability": SLATarget("API Availability", 99.9, 60),
            "api_response_time": SLATarget("API Response Time", 95.0, 15),
            "database_availability": SLATarget("Database Availability", 99.95, 30),
            "payment_processing": SLATarget("Payment Processing", 99.5, 10),
            "customer_portal": SLATarget("Customer Portal", 99.0, 60),
            "partner_portal": SLATarget("Partner Portal", 99.0, 60),
        }
    
    def _initialize_anomaly_thresholds(self) -> Dict[str, AnomalyThreshold]:
        """Initialize anomaly detection thresholds."""
        return {
            "revenue": AnomalyThreshold("revenue", 2.5, 20),
            "customer_acquisitions": AnomalyThreshold("customer_acquisitions", 2.0, 15),
            "commission_amounts": AnomalyThreshold("commission_amounts", 2.0, 10),
            "error_rate": AnomalyThreshold("error_rate", 1.5, 10, 0.6),
            "response_time": AnomalyThreshold("response_time", 2.0, 20),
            "churn_rate": AnomalyThreshold("churn_rate", 1.5, 30, 0.7),
        }
    
    async def _business_metrics_collector(self):
        """Background task to collect and process business metrics."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                # Collect current business metrics
                await self._collect_revenue_metrics()
                await self._collect_customer_metrics()
                await self._collect_partner_metrics()
                await self._calculate_business_kpis()
                
            except Exception as e:
                logger.error("Error collecting business metrics", error=str(e))
    
    async def _collect_revenue_metrics(self):
        """Collect and process revenue metrics."""
        try:
            # This would typically query your database for recent revenue data
            # For now, we'll simulate the collection
            
            # Record revenue processing rates
            current_time = datetime.utcnow()
            
            # Simulated revenue calculation - replace with actual data
            # total_revenue = await self._get_total_revenue_last_hour()
            # REVENUE_METRICS.labels(
            #     revenue_type="recurring",
            #     partner_id="all",
            #     tenant_id="all"
            # ).inc(total_revenue)
            
            business_logger.info("Revenue metrics collection completed")
            
        except Exception as e:
            logger.error("Error collecting revenue metrics", error=str(e))
    
    async def _collect_customer_metrics(self):
        """Collect customer lifecycle and activity metrics."""
        try:
            # Customer acquisition metrics
            # new_customers_count = await self._get_new_customers_last_hour()
            
            # Customer retention metrics
            # churn_events = await self._get_churn_events_last_hour()
            
            # Activity metrics
            # active_customers = await self._get_active_customers_last_hour()
            
            business_logger.info("Customer metrics collection completed")
            
        except Exception as e:
            logger.error("Error collecting customer metrics", error=str(e))
    
    async def _collect_partner_metrics(self):
        """Collect partner performance and activity metrics."""
        try:
            # Partner performance calculation
            # partners = await self._get_active_partners()
            
            # for partner in partners:
            #     performance_score = await self._calculate_partner_performance(partner.id)
            #     PARTNER_PERFORMANCE.labels(partner_id=partner.id).set(performance_score)
            
            business_logger.info("Partner metrics collection completed")
            
        except Exception as e:
            logger.error("Error collecting partner metrics", error=str(e))
    
    async def _calculate_business_kpis(self):
        """Calculate and update business KPI metrics."""
        try:
            # Monthly Recurring Revenue (MRR)
            # mrr = await self._calculate_mrr()
            # BUSINESS_KPI.labels(kpi_name="mrr", category="revenue").set(mrr)
            
            # Customer Acquisition Cost (CAC)
            # cac = await self._calculate_cac()
            # BUSINESS_KPI.labels(kpi_name="cac", category="acquisition").set(cac)
            
            # Lifetime Value (LTV)
            # ltv = await self._calculate_ltv()
            # BUSINESS_KPI.labels(kpi_name="ltv", category="retention").set(ltv)
            
            # Net Promoter Score (NPS) - if available
            # nps = await self._calculate_nps()
            # BUSINESS_KPI.labels(kpi_name="nps", category="satisfaction").set(nps)
            
            business_logger.info("Business KPI calculation completed")
            
        except Exception as e:
            logger.error("Error calculating business KPIs", error=str(e))
    
    async def _sla_monitor(self):
        """Monitor SLA compliance."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                for sla_name, target in self.sla_targets.items():
                    current_performance = await self._measure_sla_performance(sla_name)
                    
                    SLA_COMPLIANCE.labels(
                        service_type=sla_name,
                        sla_tier="standard"
                    ).set(current_performance)
                    
                    # Check for SLA breach
                    if target.is_breach(current_performance, 5):  # 5 minutes
                        business_logger.critical(
                            f"SLA breach detected for {sla_name}",
                            sla_name=sla_name,
                            current_performance=current_performance,
                            target=target.target_percent
                        )
                
            except Exception as e:
                logger.error("Error monitoring SLA", error=str(e))
    
    async def _anomaly_detector(self):
        """Background anomaly detection."""
        while True:
            try:
                await asyncio.sleep(120)  # Check every 2 minutes
                
                for metric_name, threshold in self.anomaly_thresholds.items():
                    # Get current metric value
                    current_value = await self._get_current_metric_value(metric_name)
                    if current_value is None:
                        continue
                    
                    # Get metric history
                    history = self.metric_histories[metric_name]
                    history.add_value(current_value)
                    
                    # Detect anomaly
                    anomaly_score = threshold.detect_anomaly(current_value, history)
                    
                    # Update Prometheus metric
                    ANOMALY_SCORE.labels(
                        metric_type=metric_name,
                        entity_id="global"
                    ).set(anomaly_score)
                    
                    # Alert if anomaly score is high
                    if anomaly_score >= threshold.alert_threshold:
                        business_logger.warning(
                            f"Anomaly detected in {metric_name}",
                            metric_name=metric_name,
                            current_value=current_value,
                            anomaly_score=anomaly_score,
                            mean=history.mean,
                            std_dev=history.std_dev
                        )
                
            except Exception as e:
                logger.error("Error in anomaly detection", error=str(e))
    
    async def _partner_performance_calculator(self):
        """Calculate partner performance scores."""
        while True:
            try:
                await asyncio.sleep(1800)  # Update every 30 minutes
                
                # partners = await self._get_all_partners()
                # 
                # for partner in partners:
                #     score = await self._calculate_comprehensive_partner_score(partner.id)
                #     PARTNER_PERFORMANCE.labels(partner_id=partner.id).set(score)
                #     
                #     if score < 60:  # Performance threshold
                #         business_logger.warning(
                #             "Poor partner performance detected",
                #             partner_id=partner.id,
                #             performance_score=score
                #         )
                
            except Exception as e:
                logger.error("Error calculating partner performance", error=str(e))
    
    async def _tenant_health_monitor(self):
        """Monitor tenant health and system availability."""
        while True:
            try:
                await asyncio.sleep(900)  # Update every 15 minutes
                
                # tenants = await self._get_all_tenants()
                # 
                # for tenant in tenants:
                #     health_score = await self._calculate_tenant_health_score(tenant.id)
                #     TENANT_HEALTH_SCORE.labels(tenant_id=tenant.id).set(health_score)
                #     
                #     # Check system availability for tenant
                #     availability = await self._check_tenant_system_availability(tenant.id)
                #     SYSTEM_AVAILABILITY.labels(
                #         component="overall",
                #         tenant_id=tenant.id
                #     ).set(availability)
                
            except Exception as e:
                logger.error("Error monitoring tenant health", error=str(e))
    
    async def _measure_sla_performance(self, sla_name: str) -> float:
        """Measure current SLA performance."""
        # This would implement actual SLA measurement logic
        # For now, return a simulated value
        import random
        return 99.0 + random.uniform(0, 1.0)
    
    async def _get_current_metric_value(self, metric_name: str) -> Optional[float]:
        """Get current value for a specific metric."""
        # This would implement actual metric collection logic
        # For now, return simulated values
        import random
        
        if metric_name == "revenue":
            return random.uniform(1000, 5000)
        elif metric_name == "customer_acquisitions":
            return random.randint(5, 50)
        elif metric_name == "error_rate":
            return random.uniform(0.1, 2.0)
        elif metric_name == "response_time":
            return random.uniform(50, 500)
        
        return None
    
    def record_business_event(
        self,
        event_type: str,
        tenant_id: Optional[str] = None,
        partner_id: Optional[str] = None,
        amount: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a business event with comprehensive tracking."""
        span = trace.get_current_span()
        
        if span.is_recording():
            span.add_event(f"business_event.{event_type}", {
                "tenant.id": tenant_id or "unknown",
                "partner.id": partner_id or "unknown",
                "event.amount": amount or 0,
                "event.metadata": str(metadata) if metadata else ""
            })
        
        # Log business event
        business_logger.info(
            f"Business event recorded: {event_type}",
            event_type=event_type,
            tenant_id=tenant_id,
            partner_id=partner_id,
            amount=amount,
            metadata=metadata
        )
        
        # Record specific metrics based on event type
        if event_type == "revenue_processed" and amount:
            REVENUE_METRICS.labels(
                revenue_type="transaction",
                partner_id=partner_id or "unknown",
                tenant_id=tenant_id or "unknown"
            ).inc(amount)
        
        elif event_type in ["customer_signup", "customer_churn"]:
            CUSTOMER_LIFECYCLE.labels(
                event_type=event_type,
                partner_id=partner_id or "unknown",
                service_tier=metadata.get("service_tier", "unknown") if metadata else "unknown"
            ).inc()
        
        elif event_type == "commission_calculated" and amount:
            COMMISSION_METRICS.labels(
                partner_id=partner_id or "unknown",
                commission_type=metadata.get("commission_type", "standard") if metadata else "standard"
            ).observe(amount)


# Global enhanced business metrics collector
enhanced_business_metrics = EnhancedBusinessMetricsCollector()

# Convenience functions
def record_revenue_event(
    amount: float,
    revenue_type: str,
    tenant_id: Optional[str] = None,
    partner_id: Optional[str] = None
):
    """Record revenue processing event."""
    enhanced_business_metrics.record_business_event(
        event_type="revenue_processed",
        tenant_id=tenant_id,
        partner_id=partner_id,
        amount=amount,
        metadata={"revenue_type": revenue_type}
    )

def record_customer_lifecycle_event(
    event_type: str,
    partner_id: str,
    service_tier: str = "standard",
    tenant_id: Optional[str] = None
):
    """Record customer lifecycle event."""
    enhanced_business_metrics.record_business_event(
        event_type=event_type,
        tenant_id=tenant_id,
        partner_id=partner_id,
        metadata={"service_tier": service_tier}
    )

def record_commission_event(
    amount: float,
    partner_id: str,
    commission_type: str = "standard",
    tenant_id: Optional[str] = None
):
    """Record commission calculation event."""
    enhanced_business_metrics.record_business_event(
        event_type="commission_calculated",
        tenant_id=tenant_id,
        partner_id=partner_id,
        amount=amount,
        metadata={"commission_type": commission_type}
    )