"""
Tenant-Scoped Business Metrics
Advanced business metrics collection and dashboard generation for multi-tenant environments
"""

import json
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum

from ..core.logging import get_logger
from ..tenant.identity import TenantContext
from .metrics_schema import UnifiedMetricsRegistry, MetricDefinition, MetricType, MetricCategory

logger = get_logger(__name__)


class BusinessMetricType(str, Enum):
    """Types of business metrics"""
    USAGE = "usage"                 # Resource usage metrics
    PERFORMANCE = "performance"     # Performance KPIs
    FINANCIAL = "financial"         # Revenue, billing metrics
    USER_ENGAGEMENT = "user_engagement"  # User activity metrics
    OPERATIONAL = "operational"     # Operational efficiency metrics
    COMPLIANCE = "compliance"       # Compliance and audit metrics


class MetricGranularity(str, Enum):
    """Metric collection granularity"""
    REAL_TIME = "real_time"        # Real-time metrics
    MINUTE = "minute"              # Per-minute aggregation
    HOUR = "hour"                  # Hourly aggregation
    DAY = "day"                    # Daily aggregation
    WEEK = "week"                  # Weekly aggregation
    MONTH = "month"                # Monthly aggregation


@dataclass
class BusinessMetricSpec:
    """Specification for a business metric"""
    name: str
    business_type: BusinessMetricType
    description: str
    calculation: str               # Formula or aggregation method
    dimensions: List[str]          # Metric dimensions (tenant_id, plan, region, etc.)
    granularity: MetricGranularity
    sla_thresholds: Dict[str, float] = field(default_factory=dict)
    alert_conditions: List[str] = field(default_factory=list)
    dashboard_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SLODefinition:
    """Service Level Objective definition"""
    name: str
    description: str
    metric_name: str
    target_value: float
    comparison: str  # ">=", "<=", "==", "!=", ">", "<"
    window: str     # "1h", "24h", "7d", "30d"
    error_budget: float = 0.1  # 10% error budget by default
    severity: str = "warning"  # "info", "warning", "critical"


class TenantMetricsCollector:
    """
    Advanced business metrics collector for multi-tenant environments.
    
    Features:
    - Tenant-scoped metric collection
    - Business KPI tracking
    - SLA monitoring and alerting
    - Automated dashboard generation
    - Multi-dimensional analysis
    """
    
    def __init__(self, metrics_registry: UnifiedMetricsRegistry):
        self.metrics_registry = metrics_registry
        self.business_metrics: Dict[str, BusinessMetricSpec] = {}
        self.slo_definitions: Dict[str, SLODefinition] = {}
        self.tenant_metadata_cache = {}
        
        # Initialize standard business metrics
        self._register_standard_business_metrics()
    
    def register_business_metric(self, spec: BusinessMetricSpec) -> bool:
        """Register a business metric specification"""
        try:
            self.business_metrics[spec.name] = spec
            
            # Create underlying metric definition
            metric_def = MetricDefinition(
                name=f"business_{spec.name}",
                type=MetricType.GAUGE,  # Most business metrics are gauges
                category=MetricCategory.BUSINESS,
                description=spec.description,
                labels=spec.dimensions + ["business_type", "granularity"],
                tenant_scoped=True,
                help_text=f"{spec.description} - Calculation: {spec.calculation}"
            )
            
            self.metrics_registry.register_metric(metric_def)
            
            logger.info(f"Registered business metric: {spec.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register business metric {spec.name}: {e}")
            return False
    
    def collect_tenant_usage_metrics(
        self,
        tenant_context: TenantContext,
        usage_data: Dict[str, Union[int, float]]
    ):
        """Collect usage metrics for a tenant"""
        
        for metric_name, value in usage_data.items():
            full_metric_name = f"business_usage_{metric_name}"
            
            labels = {
                "business_type": BusinessMetricType.USAGE.value,
                "granularity": MetricGranularity.REAL_TIME.value,
                "metric_name": metric_name
            }
            
            # Add tenant metadata to labels
            labels.update(self._get_tenant_metadata_labels(tenant_context))
            
            self.metrics_registry.record_metric(
                f"business_usage_{metric_name}",
                value,
                labels,
                tenant_context
            )
    
    def collect_financial_metrics(
        self,
        tenant_context: TenantContext,
        financial_data: Dict[str, float]
    ):
        """Collect financial metrics for a tenant"""
        
        for metric_name, value in financial_data.items():
            labels = {
                "business_type": BusinessMetricType.FINANCIAL.value,
                "granularity": MetricGranularity.HOUR.value,
                "metric_name": metric_name,
                "currency": "USD"  # Default currency
            }
            
            labels.update(self._get_tenant_metadata_labels(tenant_context))
            
            self.metrics_registry.record_metric(
                f"business_financial_{metric_name}",
                value,
                labels,
                tenant_context
            )
    
    def collect_user_engagement_metrics(
        self,
        tenant_context: TenantContext,
        engagement_data: Dict[str, Union[int, float]]
    ):
        """Collect user engagement metrics for a tenant"""
        
        for metric_name, value in engagement_data.items():
            labels = {
                "business_type": BusinessMetricType.USER_ENGAGEMENT.value,
                "granularity": MetricGranularity.MINUTE.value,
                "metric_name": metric_name
            }
            
            labels.update(self._get_tenant_metadata_labels(tenant_context))
            
            self.metrics_registry.record_metric(
                f"business_engagement_{metric_name}",
                value,
                labels,
                tenant_context
            )
    
    def collect_performance_metrics(
        self,
        tenant_context: TenantContext,
        performance_data: Dict[str, float]
    ):
        """Collect performance KPI metrics for a tenant"""
        
        for metric_name, value in performance_data.items():
            labels = {
                "business_type": BusinessMetricType.PERFORMANCE.value,
                "granularity": MetricGranularity.MINUTE.value,
                "metric_name": metric_name
            }
            
            labels.update(self._get_tenant_metadata_labels(tenant_context))
            
            self.metrics_registry.record_metric(
                f"business_performance_{metric_name}",
                value,
                labels,
                tenant_context
            )
    
    def register_slo(self, slo: SLODefinition) -> bool:
        """Register a Service Level Objective"""
        try:
            self.slo_definitions[slo.name] = slo
            
            # Create SLO compliance metric
            slo_metric = MetricDefinition(
                name=f"slo_{slo.name}_compliance",
                type=MetricType.GAUGE,
                category=MetricCategory.BUSINESS,
                description=f"SLO compliance for {slo.name}",
                labels=["slo_name", "window", "severity"],
                tenant_scoped=True,
                help_text=f"Compliance percentage for SLO: {slo.description}"
            )
            
            self.metrics_registry.register_metric(slo_metric)
            
            logger.info(f"Registered SLO: {slo.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register SLO {slo.name}: {e}")
            return False
    
    def evaluate_slos(self, tenant_context: TenantContext) -> Dict[str, Dict[str, Any]]:
        """Evaluate all SLOs for a tenant"""
        
        slo_results = {}
        
        for slo_name, slo in self.slo_definitions.items():
            try:
                # This would typically query the metrics backend
                # For now, we'll generate mock compliance data
                compliance = self._calculate_slo_compliance(slo, tenant_context)
                
                slo_results[slo_name] = {
                    "compliance_percentage": compliance,
                    "target": slo.target_value,
                    "window": slo.window,
                    "error_budget_remaining": max(0, slo.error_budget - (1 - compliance/100)),
                    "status": "healthy" if compliance >= slo.target_value else "violated",
                    "severity": slo.severity
                }
                
                # Record SLO compliance metric
                labels = {
                    "slo_name": slo_name,
                    "window": slo.window,
                    "severity": slo.severity
                }
                
                self.metrics_registry.record_metric(
                    f"slo_{slo_name}_compliance",
                    compliance,
                    labels,
                    tenant_context
                )
                
            except Exception as e:
                logger.error(f"Failed to evaluate SLO {slo_name}: {e}")
                slo_results[slo_name] = {"error": str(e), "status": "error"}
        
        return slo_results
    
    def generate_tenant_dashboard_config(self, tenant_context: TenantContext) -> Dict[str, Any]:
        """Generate dashboard configuration for a tenant"""
        
        dashboard_config = {
            "tenant_id": tenant_context.tenant_id,
            "dashboard_title": f"Business Metrics - {tenant_context.tenant_id}",
            "generated_at": datetime.utcnow().isoformat(),
            "panels": [],
            "slos": []
        }
        
        # Add metric panels
        for metric_name, spec in self.business_metrics.items():
            panel_config = {
                "title": spec.name.replace("_", " ").title(),
                "type": self._get_panel_type(spec.business_type),
                "metric_query": f"{self.metrics_registry.service_name}_business_{metric_name}{{tenant_id=\"{tenant_context.tenant_id}\"}}",
                "description": spec.description,
                "unit": self._get_metric_unit(spec.business_type),
                "thresholds": spec.sla_thresholds,
                **spec.dashboard_config
            }
            dashboard_config["panels"].append(panel_config)
        
        # Add SLO panels
        for slo_name, slo in self.slo_definitions.items():
            slo_panel = {
                "title": f"SLO: {slo.name}",
                "type": "slostat",
                "metric_query": f"{self.metrics_registry.service_name}_slo_{slo_name}_compliance{{tenant_id=\"{tenant_context.tenant_id}\"}}",
                "target": slo.target_value,
                "window": slo.window,
                "description": slo.description
            }
            dashboard_config["slos"].append(slo_panel)
        
        return dashboard_config
    
    def _register_standard_business_metrics(self):
        """Register standard business metrics for all tenants"""
        
        standard_metrics = [
            BusinessMetricSpec(
                name="monthly_active_users",
                business_type=BusinessMetricType.USER_ENGAGEMENT,
                description="Monthly Active Users",
                calculation="count(distinct user_id) where last_activity >= now() - 30d",
                dimensions=["tenant_id", "plan", "region"],
                granularity=MetricGranularity.HOUR,
                sla_thresholds={"min": 1, "target": 100},
                dashboard_config={"panel_type": "stat", "color": "green"}
            ),
            BusinessMetricSpec(
                name="revenue_current_month",
                business_type=BusinessMetricType.FINANCIAL,
                description="Current Month Revenue",
                calculation="sum(billing_amount) where billing_date >= start_of_month",
                dimensions=["tenant_id", "plan", "currency"],
                granularity=MetricGranularity.HOUR,
                sla_thresholds={"min": 0},
                dashboard_config={"panel_type": "stat", "color": "blue", "format": "currency"}
            ),
            BusinessMetricSpec(
                name="api_success_rate",
                business_type=BusinessMetricType.PERFORMANCE,
                description="API Success Rate",
                calculation="(count(status_code < 400) / count(*)) * 100",
                dimensions=["tenant_id", "endpoint", "method"],
                granularity=MetricGranularity.MINUTE,
                sla_thresholds={"min": 95, "target": 99.9},
                dashboard_config={"panel_type": "gauge", "unit": "percent"}
            ),
            BusinessMetricSpec(
                name="storage_utilization",
                business_type=BusinessMetricType.USAGE,
                description="Storage Utilization",
                calculation="(used_storage_bytes / allocated_storage_bytes) * 100",
                dimensions=["tenant_id", "storage_type"],
                granularity=MetricGranularity.HOUR,
                sla_thresholds={"warning": 80, "critical": 95},
                dashboard_config={"panel_type": "gauge", "unit": "percent"}
            ),
            BusinessMetricSpec(
                name="support_ticket_resolution_time",
                business_type=BusinessMetricType.OPERATIONAL,
                description="Average Support Ticket Resolution Time",
                calculation="avg(resolution_time_hours) where status = 'resolved'",
                dimensions=["tenant_id", "priority", "category"],
                granularity=MetricGranularity.HOUR,
                sla_thresholds={"target": 24, "max": 72},
                dashboard_config={"panel_type": "stat", "unit": "hours"}
            )
        ]
        
        for metric_spec in standard_metrics:
            self.register_business_metric(metric_spec)
        
        # Register standard SLOs
        standard_slos = [
            SLODefinition(
                name="api_availability",
                description="API Availability",
                metric_name="api_success_rate",
                target_value=99.9,
                comparison=">=",
                window="24h",
                error_budget=0.001,
                severity="critical"
            ),
            SLODefinition(
                name="response_time",
                description="Response Time P95",
                metric_name="http_request_duration_seconds_p95",
                target_value=0.5,
                comparison="<=",
                window="1h",
                error_budget=0.1,
                severity="warning"
            )
        ]
        
        for slo in standard_slos:
            self.register_slo(slo)
    
    def _get_tenant_metadata_labels(self, tenant_context: TenantContext) -> Dict[str, str]:
        """Get tenant metadata labels for metrics"""
        
        labels = {}
        
        if tenant_context.metadata:
            labels["plan"] = str(tenant_context.metadata.get("plan", "unknown"))
            labels["region"] = str(tenant_context.metadata.get("region", "unknown"))
            labels["status"] = str(tenant_context.metadata.get("status", "unknown"))
        
        if tenant_context.subdomain:
            labels["subdomain"] = tenant_context.subdomain
        
        return labels
    
    def _calculate_slo_compliance(self, slo: SLODefinition, tenant_context: TenantContext) -> float:
        """Calculate SLO compliance percentage (mock implementation)"""
        # In a real implementation, this would query the metrics backend
        # and calculate compliance based on the SLO definition
        import random
        return random.uniform(95.0, 100.0)  # Mock compliance between 95-100%
    
    def _get_panel_type(self, business_type: BusinessMetricType) -> str:
        """Get dashboard panel type for business metric type"""
        panel_types = {
            BusinessMetricType.USAGE: "gauge",
            BusinessMetricType.PERFORMANCE: "graph",
            BusinessMetricType.FINANCIAL: "stat",
            BusinessMetricType.USER_ENGAGEMENT: "graph",
            BusinessMetricType.OPERATIONAL: "stat",
            BusinessMetricType.COMPLIANCE: "gauge"
        }
        return panel_types.get(business_type, "graph")
    
    def _get_metric_unit(self, business_type: BusinessMetricType) -> str:
        """Get default unit for business metric type"""
        units = {
            BusinessMetricType.USAGE: "percent",
            BusinessMetricType.PERFORMANCE: "ms",
            BusinessMetricType.FINANCIAL: "currency",
            BusinessMetricType.USER_ENGAGEMENT: "count",
            BusinessMetricType.OPERATIONAL: "hours",
            BusinessMetricType.COMPLIANCE: "percent"
        }
        return units.get(business_type, "")


class TenantMetricsExporter:
    """
    Exports tenant metrics to various destinations.
    """
    
    def __init__(self, collector: TenantMetricsCollector):
        self.collector = collector
    
    def export_dashboard_json(self, tenant_context: TenantContext) -> str:
        """Export dashboard configuration as JSON"""
        dashboard_config = self.collector.generate_tenant_dashboard_config(tenant_context)
        return json.dumps(dashboard_config, indent=2)
    
    def export_grafana_dashboard(self, tenant_context: TenantContext) -> Dict[str, Any]:
        """Export dashboard in Grafana format"""
        base_config = self.collector.generate_tenant_dashboard_config(tenant_context)
        
        grafana_dashboard = {
            "dashboard": {
                "id": None,
                "title": base_config["dashboard_title"],
                "tags": ["dotmac", "tenant", tenant_context.tenant_id],
                "timezone": "browser",
                "refresh": "30s",
                "time": {"from": "now-1h", "to": "now"},
                "panels": []
            }
        }
        
        # Convert panels to Grafana format
        for i, panel in enumerate(base_config["panels"]):
            grafana_panel = {
                "id": i + 1,
                "title": panel["title"],
                "type": panel["type"],
                "targets": [{
                    "expr": panel["metric_query"],
                    "refId": "A"
                }],
                "gridPos": {"h": 8, "w": 12, "x": (i % 2) * 12, "y": (i // 2) * 8}
            }
            
            if panel.get("thresholds"):
                grafana_panel["thresholds"] = {
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "yellow", "value": panel["thresholds"].get("warning", 80)},
                        {"color": "red", "value": panel["thresholds"].get("critical", 95)}
                    ]
                }
            
            grafana_dashboard["dashboard"]["panels"].append(grafana_panel)
        
        return grafana_dashboard
    
    def export_prometheus_recording_rules(self, tenant_context: TenantContext) -> str:
        """Export Prometheus recording rules for tenant metrics"""
        
        rules = []
        for metric_name, spec in self.collector.business_metrics.items():
            rule = f"""
- record: tenant:{metric_name}:rate5m
  expr: rate({self.collector.metrics_registry.service_name}_business_{metric_name}{{tenant_id="{tenant_context.tenant_id}"}}[5m])
  labels:
    tenant_id: "{tenant_context.tenant_id}"
    metric_type: "business"
"""
            rules.append(rule)
        
        return "\n".join(rules)


# Global tenant metrics collector
tenant_metrics_collector = None


def get_tenant_metrics_collector() -> TenantMetricsCollector:
    """Get the global tenant metrics collector"""
    global tenant_metrics_collector
    if not tenant_metrics_collector:
        raise RuntimeError("Tenant metrics collector not initialized")
    return tenant_metrics_collector


def initialize_tenant_metrics(metrics_registry: UnifiedMetricsRegistry) -> TenantMetricsCollector:
    """Initialize the global tenant metrics collector"""
    global tenant_metrics_collector
    tenant_metrics_collector = TenantMetricsCollector(metrics_registry)
    return tenant_metrics_collector