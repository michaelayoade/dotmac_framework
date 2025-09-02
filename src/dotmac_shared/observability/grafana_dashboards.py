"""
Grafana dashboard configurations for DotMac monitoring.
Provides comprehensive dashboard definitions for operations teams.
"""

import json
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

@dataclass
class Panel:
    """Grafana panel configuration."""
    title: str
    type: str
    targets: List[Dict[str, Any]]
    gridPos: Dict[str, int]
    options: Dict[str, Any] = None
    fieldConfig: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert panel to Grafana JSON format."""
        panel_dict = {
            "id": hash(self.title) % 1000,  # Simple ID generation
            "title": self.title,
            "type": self.type,
            "targets": self.targets,
            "gridPos": self.gridPos,
        }
        
        if self.options:
            panel_dict["options"] = self.options
        if self.fieldConfig:
            panel_dict["fieldConfig"] = self.fieldConfig
            
        return panel_dict

@dataclass
class Dashboard:
    """Grafana dashboard configuration."""
    title: str
    panels: List[Panel]
    tags: List[str]
    time: Dict[str, str] = None
    refresh: str = "30s"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert dashboard to Grafana JSON format."""
        return {
            "id": None,
            "title": self.title,
            "tags": self.tags,
            "style": "dark",
            "timezone": "utc",
            "panels": [panel.to_dict() for panel in self.panels],
            "time": self.time or {"from": "now-1h", "to": "now"},
            "refresh": self.refresh,
            "schemaVersion": 27,
            "version": 1,
            "links": [],
        }

class GrafanaDashboardGenerator:
    """Generator for DotMac Grafana dashboards."""
    
    def __init__(self):
        self.datasource = "prometheus"  # Default Prometheus datasource
    
    def create_api_performance_dashboard(self) -> Dashboard:
        """Create API performance monitoring dashboard."""
        panels = [
            # Request Rate
            Panel(
                title="API Request Rate",
                type="stat",
                targets=[{
                    "expr": "sum(rate(dotmac_http_requests_total[5m]))",
                    "refId": "A",
                    "datasource": self.datasource
                }],
                gridPos={"h": 8, "w": 6, "x": 0, "y": 0},
                options={
                    "reduceOptions": {
                        "calcs": ["lastNotNull"],
                        "fields": "",
                        "values": False
                    },
                    "orientation": "auto",
                    "textMode": "auto",
                    "colorMode": "value"
                }
            ),
            
            # Error Rate
            Panel(
                title="API Error Rate",
                type="stat", 
                targets=[{
                    "expr": "sum(rate(dotmac_http_requests_total{status_code=~\"4..|5..\"}[5m])) / sum(rate(dotmac_http_requests_total[5m])) * 100",
                    "refId": "A",
                    "datasource": self.datasource
                }],
                gridPos={"h": 8, "w": 6, "x": 6, "y": 0},
                options={
                    "reduceOptions": {
                        "calcs": ["lastNotNull"]
                    },
                    "colorMode": "value",
                    "graphMode": "area"
                },
                fieldConfig={
                    "defaults": {
                        "unit": "percent",
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": None},
                                {"color": "yellow", "value": 2},
                                {"color": "red", "value": 5}
                            ]
                        }
                    }
                }
            ),
            
            # Response Time P95
            Panel(
                title="API Response Time P95",
                type="stat",
                targets=[{
                    "expr": "histogram_quantile(0.95, sum(rate(dotmac_http_request_duration_seconds_bucket[5m])) by (le))",
                    "refId": "A", 
                    "datasource": self.datasource
                }],
                gridPos={"h": 8, "w": 6, "x": 12, "y": 0},
                fieldConfig={
                    "defaults": {
                        "unit": "s",
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": None},
                                {"color": "yellow", "value": 1},
                                {"color": "red", "value": 5}
                            ]
                        }
                    }
                }
            ),
            
            # Active Requests
            Panel(
                title="Active Requests",
                type="stat",
                targets=[{
                    "expr": "sum(dotmac_http_requests_active)",
                    "refId": "A",
                    "datasource": self.datasource
                }],
                gridPos={"h": 8, "w": 6, "x": 18, "y": 0}
            ),
            
            # Request Rate Timeline
            Panel(
                title="Request Rate by Endpoint",
                type="timeseries",
                targets=[{
                    "expr": "sum(rate(dotmac_http_requests_total[5m])) by (endpoint)",
                    "refId": "A",
                    "datasource": self.datasource,
                    "legendFormat": "{{endpoint}}"
                }],
                gridPos={"h": 8, "w": 12, "x": 0, "y": 8}
            ),
            
            # Error Rate by Endpoint
            Panel(
                title="Error Rate by Endpoint",
                type="timeseries",
                targets=[{
                    "expr": "sum(rate(dotmac_http_requests_total{status_code=~\"4..|5..\"}[5m])) by (endpoint) / sum(rate(dotmac_http_requests_total[5m])) by (endpoint) * 100",
                    "refId": "A",
                    "datasource": self.datasource,
                    "legendFormat": "{{endpoint}}"
                }],
                gridPos={"h": 8, "w": 12, "x": 12, "y": 8},
                fieldConfig={
                    "defaults": {
                        "unit": "percent"
                    }
                }
            ),
            
            # Response Time Heatmap
            Panel(
                title="Response Time Distribution",
                type="heatmap",
                targets=[{
                    "expr": "sum(rate(dotmac_http_request_duration_seconds_bucket[5m])) by (le)",
                    "refId": "A",
                    "datasource": self.datasource,
                    "format": "heatmap",
                    "legendFormat": "{{le}}"
                }],
                gridPos={"h": 8, "w": 24, "x": 0, "y": 16}
            )
        ]
        
        return Dashboard(
            title="DotMac API Performance",
            panels=panels,
            tags=["dotmac", "api", "performance"],
            refresh="15s"
        )
    
    def create_system_health_dashboard(self) -> Dashboard:
        """Create system health monitoring dashboard."""
        panels = [
            # CPU Usage
            Panel(
                title="CPU Usage",
                type="gauge",
                targets=[{
                    "expr": "dotmac_cpu_usage_percent",
                    "refId": "A",
                    "datasource": self.datasource
                }],
                gridPos={"h": 8, "w": 6, "x": 0, "y": 0},
                fieldConfig={
                    "defaults": {
                        "unit": "percent",
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": None},
                                {"color": "yellow", "value": 70},
                                {"color": "red", "value": 90}
                            ]
                        }
                    }
                }
            ),
            
            # Memory Usage
            Panel(
                title="Memory Usage",
                type="gauge", 
                targets=[{
                    "expr": "dotmac_memory_usage_bytes{type=\"used\"} / dotmac_memory_usage_bytes{type=\"total\"} * 100",
                    "refId": "A",
                    "datasource": self.datasource
                }],
                gridPos={"h": 8, "w": 6, "x": 6, "y": 0},
                fieldConfig={
                    "defaults": {
                        "unit": "percent",
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": None},
                                {"color": "yellow", "value": 80},
                                {"color": "red", "value": 90}
                            ]
                        }
                    }
                }
            ),
            
            # Database Connections
            Panel(
                title="Database Connections",
                type="stat",
                targets=[{
                    "expr": "sum(dotmac_database_connections_active)",
                    "refId": "A",
                    "datasource": self.datasource
                }],
                gridPos={"h": 8, "w": 6, "x": 12, "y": 0}
            ),
            
            # Thread Count
            Panel(
                title="Thread Count",
                type="stat",
                targets=[{
                    "expr": "dotmac_thread_count",
                    "refId": "A",
                    "datasource": self.datasource
                }],
                gridPos={"h": 8, "w": 6, "x": 18, "y": 0}
            ),
            
            # System Resource Timeline
            Panel(
                title="System Resources Over Time",
                type="timeseries",
                targets=[
                    {
                        "expr": "dotmac_cpu_usage_percent",
                        "refId": "A",
                        "datasource": self.datasource,
                        "legendFormat": "CPU %"
                    },
                    {
                        "expr": "dotmac_memory_usage_bytes{type=\"used\"} / dotmac_memory_usage_bytes{type=\"total\"} * 100",
                        "refId": "B", 
                        "datasource": self.datasource,
                        "legendFormat": "Memory %"
                    }
                ],
                gridPos={"h": 8, "w": 24, "x": 0, "y": 8},
                fieldConfig={
                    "defaults": {
                        "unit": "percent"
                    }
                }
            ),
            
            # Garbage Collection
            Panel(
                title="Garbage Collection Events",
                type="timeseries",
                targets=[{
                    "expr": "rate(dotmac_gc_collections_total[5m])",
                    "refId": "A",
                    "datasource": self.datasource,
                    "legendFormat": "Gen {{generation}}"
                }],
                gridPos={"h": 8, "w": 12, "x": 0, "y": 16}
            ),
            
            # Cache Performance
            Panel(
                title="Cache Hit Ratio",
                type="stat",
                targets=[{
                    "expr": "dotmac_cache_hit_ratio",
                    "refId": "A",
                    "datasource": self.datasource
                }],
                gridPos={"h": 8, "w": 12, "x": 12, "y": 16},
                fieldConfig={
                    "defaults": {
                        "unit": "percentunit",
                        "thresholds": {
                            "steps": [
                                {"color": "red", "value": None},
                                {"color": "yellow", "value": 0.7},
                                {"color": "green", "value": 0.9}
                            ]
                        }
                    }
                }
            )
        ]
        
        return Dashboard(
            title="DotMac System Health",
            panels=panels,
            tags=["dotmac", "system", "health"]
        )
    
    def create_business_metrics_dashboard(self) -> Dashboard:
        """Create business metrics monitoring dashboard."""
        panels = [
            # Total Revenue
            Panel(
                title="Total Revenue (24h)",
                type="stat",
                targets=[{
                    "expr": "increase(dotmac_revenue_total_usd[24h])",
                    "refId": "A",
                    "datasource": self.datasource
                }],
                gridPos={"h": 8, "w": 6, "x": 0, "y": 0},
                fieldConfig={
                    "defaults": {
                        "unit": "currencyUSD"
                    }
                }
            ),
            
            # Customer Acquisitions
            Panel(
                title="New Customers (24h)",
                type="stat",
                targets=[{
                    "expr": "increase(dotmac_customer_lifecycle_events_total{event_type=\"customer_signup\"}[24h])",
                    "refId": "A",
                    "datasource": self.datasource
                }],
                gridPos={"h": 8, "w": 6, "x": 6, "y": 0}
            ),
            
            # Partner Performance Average
            Panel(
                title="Average Partner Performance",
                type="stat",
                targets=[{
                    "expr": "avg(dotmac_partner_performance_score)",
                    "refId": "A",
                    "datasource": self.datasource
                }],
                gridPos={"h": 8, "w": 6, "x": 12, "y": 0},
                fieldConfig={
                    "defaults": {
                        "thresholds": {
                            "steps": [
                                {"color": "red", "value": None},
                                {"color": "yellow", "value": 60},
                                {"color": "green", "value": 80}
                            ]
                        }
                    }
                }
            ),
            
            # SLA Compliance
            Panel(
                title="Overall SLA Compliance",
                type="stat",
                targets=[{
                    "expr": "avg(dotmac_sla_compliance_percent)",
                    "refId": "A",
                    "datasource": self.datasource
                }],
                gridPos={"h": 8, "w": 6, "x": 18, "y": 0},
                fieldConfig={
                    "defaults": {
                        "unit": "percent",
                        "thresholds": {
                            "steps": [
                                {"color": "red", "value": None},
                                {"color": "yellow", "value": 98},
                                {"color": "green", "value": 99.5}
                            ]
                        }
                    }
                }
            ),
            
            # Revenue Timeline
            Panel(
                title="Revenue Trend",
                type="timeseries",
                targets=[{
                    "expr": "sum(rate(dotmac_revenue_total_usd[1h])) by (revenue_type)",
                    "refId": "A",
                    "datasource": self.datasource,
                    "legendFormat": "{{revenue_type}}"
                }],
                gridPos={"h": 8, "w": 12, "x": 0, "y": 8},
                fieldConfig={
                    "defaults": {
                        "unit": "currencyUSD"
                    }
                }
            ),
            
            # Customer Activity
            Panel(
                title="Customer Lifecycle Events",
                type="timeseries",
                targets=[{
                    "expr": "sum(rate(dotmac_customer_lifecycle_events_total[1h])) by (event_type)",
                    "refId": "A",
                    "datasource": self.datasource,
                    "legendFormat": "{{event_type}}"
                }],
                gridPos={"h": 8, "w": 12, "x": 12, "y": 8}
            ),
            
            # Partner Performance Distribution
            Panel(
                title="Partner Performance Distribution",
                type="histogram",
                targets=[{
                    "expr": "dotmac_partner_performance_score",
                    "refId": "A",
                    "datasource": self.datasource
                }],
                gridPos={"h": 8, "w": 12, "x": 0, "y": 16}
            ),
            
            # Commission Amounts
            Panel(
                title="Commission Distribution",
                type="timeseries",
                targets=[{
                    "expr": "histogram_quantile(0.5, sum(rate(dotmac_commission_amounts_usd_bucket[1h])) by (le))",
                    "refId": "A",
                    "datasource": self.datasource,
                    "legendFormat": "P50"
                }, {
                    "expr": "histogram_quantile(0.95, sum(rate(dotmac_commission_amounts_usd_bucket[1h])) by (le))",
                    "refId": "B",
                    "datasource": self.datasource,
                    "legendFormat": "P95"
                }],
                gridPos={"h": 8, "w": 12, "x": 12, "y": 16},
                fieldConfig={
                    "defaults": {
                        "unit": "currencyUSD"
                    }
                }
            )
        ]
        
        return Dashboard(
            title="DotMac Business Metrics",
            panels=panels,
            tags=["dotmac", "business", "kpi"]
        )
    
    def create_database_performance_dashboard(self) -> Dashboard:
        """Create database performance monitoring dashboard."""
        panels = [
            # Query Rate
            Panel(
                title="Query Rate",
                type="stat",
                targets=[{
                    "expr": "sum(rate(db_queries_total[5m]))",
                    "refId": "A",
                    "datasource": self.datasource
                }],
                gridPos={"h": 8, "w": 6, "x": 0, "y": 0}
            ),
            
            # Slow Queries
            Panel(
                title="Slow Queries",
                type="stat",
                targets=[{
                    "expr": "sum(rate(dotmac_db_slow_queries_total[5m]))",
                    "refId": "A",
                    "datasource": self.datasource
                }],
                gridPos={"h": 8, "w": 6, "x": 6, "y": 0},
                fieldConfig={
                    "defaults": {
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": None},
                                {"color": "yellow", "value": 5},
                                {"color": "red", "value": 20}
                            ]
                        }
                    }
                }
            ),
            
            # Connection Pool Usage
            Panel(
                title="Connection Pool Usage",
                type="gauge",
                targets=[{
                    "expr": "dotmac_database_connections_active / 100 * 100",  # Assuming max 100 connections
                    "refId": "A",
                    "datasource": self.datasource
                }],
                gridPos={"h": 8, "w": 6, "x": 12, "y": 0},
                fieldConfig={
                    "defaults": {
                        "unit": "percent",
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": None},
                                {"color": "yellow", "value": 70},
                                {"color": "red", "value": 90}
                            ]
                        }
                    }
                }
            ),
            
            # N+1 Detections
            Panel(
                title="N+1 Query Detections",
                type="stat",
                targets=[{
                    "expr": "sum(rate(dotmac_db_n_plus_one_detected[5m]))",
                    "refId": "A", 
                    "datasource": self.datasource
                }],
                gridPos={"h": 8, "w": 6, "x": 18, "y": 0},
                fieldConfig={
                    "defaults": {
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": None},
                                {"color": "yellow", "value": 1},
                                {"color": "red", "value": 5}
                            ]
                        }
                    }
                }
            ),
            
            # Query Duration by Operation
            Panel(
                title="Query Duration by Operation",
                type="timeseries",
                targets=[{
                    "expr": "histogram_quantile(0.95, sum(rate(dotmac_db_operation_duration_ms_bucket[5m])) by (le, operation))",
                    "refId": "A",
                    "datasource": self.datasource,
                    "legendFormat": "{{operation}} P95"
                }],
                gridPos={"h": 8, "w": 24, "x": 0, "y": 8},
                fieldConfig={
                    "defaults": {
                        "unit": "ms"
                    }
                }
            )
        ]
        
        return Dashboard(
            title="DotMac Database Performance",
            panels=panels,
            tags=["dotmac", "database", "performance"]
        )
    
    def create_tenant_monitoring_dashboard(self) -> Dashboard:
        """Create tenant-specific monitoring dashboard."""
        panels = [
            # Tenant Health Scores
            Panel(
                title="Tenant Health Scores",
                type="table",
                targets=[{
                    "expr": "dotmac_tenant_health_score",
                    "refId": "A",
                    "datasource": self.datasource,
                    "format": "table"
                }],
                gridPos={"h": 8, "w": 12, "x": 0, "y": 0}
            ),
            
            # Tenant Activity
            Panel(
                title="Tenant Activity Rate",
                type="timeseries",
                targets=[{
                    "expr": "sum(rate(dotmac_tenant_activity_total[5m])) by (tenant_id)",
                    "refId": "A",
                    "datasource": self.datasource,
                    "legendFormat": "{{tenant_id}}"
                }],
                gridPos={"h": 8, "w": 12, "x": 12, "y": 0}
            ),
            
            # System Availability by Tenant
            Panel(
                title="System Availability by Tenant",
                type="heatmap",
                targets=[{
                    "expr": "dotmac_system_availability_percent",
                    "refId": "A",
                    "datasource": self.datasource,
                    "format": "heatmap"
                }],
                gridPos={"h": 8, "w": 24, "x": 0, "y": 8}
            )
        ]
        
        return Dashboard(
            title="DotMac Tenant Monitoring",
            panels=panels,
            tags=["dotmac", "tenant", "multitenancy"]
        )
    
    def get_all_dashboards(self) -> List[Dashboard]:
        """Get all available dashboards."""
        return [
            self.create_api_performance_dashboard(),
            self.create_system_health_dashboard(),
            self.create_business_metrics_dashboard(), 
            self.create_database_performance_dashboard(),
            self.create_tenant_monitoring_dashboard()
        ]
    
    def export_dashboard_json(self, dashboard: Dashboard) -> str:
        """Export dashboard as JSON string."""
        return json.dumps(dashboard.to_dict(), indent=2)
    
    def export_all_dashboards(self) -> Dict[str, str]:
        """Export all dashboards as JSON strings."""
        return {
            dashboard.title: self.export_dashboard_json(dashboard)
            for dashboard in self.get_all_dashboards()
        }


# Global dashboard generator
dashboard_generator = GrafanaDashboardGenerator()

def create_dashboard_files(output_dir: str = "./grafana_dashboards"):
    """Create dashboard JSON files for import into Grafana."""
    import os
    
    os.makedirs(output_dir, exist_ok=True)
    
    for dashboard in dashboard_generator.get_all_dashboards():
        filename = f"{dashboard.title.lower().replace(' ', '_')}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(dashboard_generator.export_dashboard_json(dashboard))
        
        print(f"Created dashboard: {filepath}")