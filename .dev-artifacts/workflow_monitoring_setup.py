#!/usr/bin/env python3
"""
Phase 4: Comprehensive Monitoring and Alerting Setup

This module provides production-ready monitoring and alerting for the 
workflow orchestration system, including:
- Prometheus metrics collection
- Grafana dashboard configuration
- Health check monitoring
- Alert rules and thresholds
- Performance monitoring
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass, asdict

@dataclass
class MetricDefinition:
    """Definition of a metric to be collected"""
    name: str
    type: str  # counter, gauge, histogram, summary
    description: str
    labels: List[str]
    alert_rules: List[Dict[str, Any]] = None

@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    condition: str
    severity: str  # critical, warning, info
    duration: str  # 5m, 10m, 1h
    description: str
    runbook_url: str = ""

class WorkflowMonitoringSetup:
    """Setup and configure monitoring for workflow orchestration"""
    
    def __init__(self):
        self.metrics_definitions = self._define_workflow_metrics()
        self.alert_rules = self._define_alert_rules()
        self.dashboard_config = self._create_grafana_dashboard()
    
    def _define_workflow_metrics(self) -> List[MetricDefinition]:
        """Define all workflow-related metrics to collect"""
        
        return [
            # Saga Execution Metrics
            MetricDefinition(
                name="workflow_saga_executions_total",
                type="counter", 
                description="Total number of saga executions",
                labels=["saga_name", "tenant_id", "status"],
                alert_rules=[
                    {
                        "name": "HighSagaFailureRate",
                        "condition": "rate(workflow_saga_executions_total{status=\"failed\"}[5m]) > 0.1",
                        "severity": "warning",
                        "duration": "5m"
                    }
                ]
            ),
            
            MetricDefinition(
                name="workflow_saga_duration_seconds",
                type="histogram",
                description="Duration of saga executions in seconds",
                labels=["saga_name", "status"],
                alert_rules=[
                    {
                        "name": "SlowSagaExecution", 
                        "condition": "histogram_quantile(0.95, workflow_saga_duration_seconds) > 300",
                        "severity": "warning",
                        "duration": "10m"
                    }
                ]
            ),
            
            MetricDefinition(
                name="workflow_saga_steps_total",
                type="counter",
                description="Total number of saga steps executed",
                labels=["saga_name", "step_name", "status"],
                alert_rules=[]
            ),
            
            MetricDefinition(
                name="workflow_saga_compensations_total",
                type="counter", 
                description="Total number of compensation actions executed",
                labels=["saga_name", "step_name"],
                alert_rules=[
                    {
                        "name": "HighCompensationRate",
                        "condition": "rate(workflow_saga_compensations_total[10m]) > 0.05",
                        "severity": "critical",
                        "duration": "5m"
                    }
                ]
            ),
            
            # Idempotency Metrics
            MetricDefinition(
                name="workflow_idempotent_operations_total",
                type="counter",
                description="Total number of idempotent operations",
                labels=["operation_type", "tenant_id", "status"],
                alert_rules=[]
            ),
            
            MetricDefinition(
                name="workflow_idempotency_cache_hits_total",
                type="counter",
                description="Total number of idempotency cache hits",
                labels=["operation_type"],
                alert_rules=[]
            ),
            
            MetricDefinition(
                name="workflow_idempotent_operation_duration_seconds",
                type="histogram",
                description="Duration of idempotent operations in seconds",
                labels=["operation_type", "from_cache"],
                alert_rules=[]
            ),
            
            # Health Check Metrics
            MetricDefinition(
                name="workflow_component_health",
                type="gauge",
                description="Health status of workflow components (1=healthy, 0=unhealthy)",
                labels=["component", "instance"],
                alert_rules=[
                    {
                        "name": "WorkflowComponentUnhealthy",
                        "condition": "workflow_component_health == 0",
                        "severity": "critical",
                        "duration": "1m"
                    }
                ]
            ),
            
            MetricDefinition(
                name="workflow_health_check_duration_seconds",
                type="histogram", 
                description="Duration of health checks in seconds",
                labels=["component"],
                alert_rules=[]
            ),
            
            # Database Metrics
            MetricDefinition(
                name="workflow_database_connections_active",
                type="gauge",
                description="Number of active database connections for workflow operations",
                labels=["pool_name"],
                alert_rules=[
                    {
                        "name": "HighDatabaseConnections",
                        "condition": "workflow_database_connections_active > 50",
                        "severity": "warning", 
                        "duration": "5m"
                    }
                ]
            ),
            
            MetricDefinition(
                name="workflow_database_query_duration_seconds",
                type="histogram",
                description="Duration of workflow database queries in seconds", 
                labels=["table", "operation"],
                alert_rules=[
                    {
                        "name": "SlowWorkflowQueries",
                        "condition": "histogram_quantile(0.95, workflow_database_query_duration_seconds) > 1",
                        "severity": "warning",
                        "duration": "10m"
                    }
                ]
            ),
        ]
    
    def _define_alert_rules(self) -> List[AlertRule]:
        """Define comprehensive alert rules for workflow monitoring"""
        
        return [
            # Critical System Alerts
            AlertRule(
                name="WorkflowSystemDown",
                condition="up{job=\"workflow-orchestration\"} == 0",
                severity="critical",
                duration="1m", 
                description="Workflow orchestration system is down",
                runbook_url="/runbooks/workflow-system-recovery"
            ),
            
            AlertRule(
                name="WorkflowDatabaseConnectionFailure",
                condition="workflow_database_connections_active == 0",
                severity="critical",
                duration="2m",
                description="Unable to connect to workflow database",
                runbook_url="/runbooks/database-connectivity"
            ),
            
            # Performance Alerts
            AlertRule(
                name="HighWorkflowLatency",
                condition="histogram_quantile(0.95, rate(workflow_saga_duration_seconds_bucket[5m])) > 600",
                severity="warning", 
                duration="10m",
                description="Workflow execution latency is high (>10 minutes for 95th percentile)",
                runbook_url="/runbooks/performance-optimization"
            ),
            
            AlertRule(
                name="WorkflowThroughputLow",
                condition="rate(workflow_saga_executions_total[5m]) < 0.1",
                severity="warning",
                duration="15m", 
                description="Workflow execution throughput is unusually low",
                runbook_url="/runbooks/throughput-investigation"
            ),
            
            # Business Logic Alerts
            AlertRule(
                name="HighSagaFailureRate",
                condition="rate(workflow_saga_executions_total{status=\"failed\"}[10m]) / rate(workflow_saga_executions_total[10m]) > 0.05",
                severity="warning",
                duration="5m",
                description="Saga failure rate exceeds 5%",
                runbook_url="/runbooks/saga-failure-investigation"
            ),
            
            AlertRule(
                name="CriticalSagaFailureRate", 
                condition="rate(workflow_saga_executions_total{status=\"failed\"}[5m]) / rate(workflow_saga_executions_total[5m]) > 0.20",
                severity="critical",
                duration="2m",
                description="Saga failure rate exceeds 20% - critical business impact",
                runbook_url="/runbooks/critical-saga-failures"
            ),
            
            AlertRule(
                name="IdempotencyViolation",
                condition="increase(workflow_idempotent_operations_total{status=\"duplicate_detected\"}[1h]) > 10",
                severity="warning",
                duration="5m",
                description="High number of idempotency violations detected",
                runbook_url="/runbooks/idempotency-violations"
            ),
            
            # Capacity Alerts
            AlertRule(
                name="WorkflowQueueBacklog",
                condition="workflow_saga_executions_total{status=\"pending\"} > 100",
                severity="warning",
                duration="10m", 
                description="Workflow execution queue has significant backlog",
                runbook_url="/runbooks/capacity-scaling"
            ),
            
            AlertRule(
                name="WorkflowMemoryHigh",
                condition="process_resident_memory_bytes{job=\"workflow-orchestration\"} > 2e9",
                severity="warning",
                duration="5m",
                description="Workflow orchestration process memory usage is high (>2GB)",
                runbook_url="/runbooks/memory-optimization"
            ),
        ]
    
    def _create_grafana_dashboard(self) -> Dict[str, Any]:
        """Create Grafana dashboard configuration for workflow monitoring"""
        
        return {
            "dashboard": {
                "id": None,
                "title": "Workflow Orchestration Monitoring",
                "tags": ["workflow", "orchestration", "dotmac"],
                "timezone": "UTC",
                "refresh": "30s",
                "schemaVersion": 30,
                "version": 1,
                "panels": [
                    {
                        "id": 1,
                        "title": "Saga Execution Overview",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "sum(rate(workflow_saga_executions_total[5m]))",
                                "legendFormat": "Executions/sec"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "ops",
                                "thresholds": {
                                    "steps": [
                                        {"color": "green", "value": None},
                                        {"color": "yellow", "value": 0.5},
                                        {"color": "red", "value": 2}
                                    ]
                                }
                            }
                        },
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
                    },
                    
                    {
                        "id": 2, 
                        "title": "Saga Success Rate",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "sum(rate(workflow_saga_executions_total{status=\"completed\"}[5m])) / sum(rate(workflow_saga_executions_total[5m])) * 100",
                                "legendFormat": "Success Rate %"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percent",
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": None},
                                        {"color": "yellow", "value": 95},
                                        {"color": "green", "value": 99}
                                    ]
                                }
                            }
                        },
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
                    },
                    
                    {
                        "id": 3,
                        "title": "Saga Execution Duration",
                        "type": "graph", 
                        "targets": [
                            {
                                "expr": "histogram_quantile(0.50, rate(workflow_saga_duration_seconds_bucket[5m]))",
                                "legendFormat": "p50"
                            },
                            {
                                "expr": "histogram_quantile(0.95, rate(workflow_saga_duration_seconds_bucket[5m]))",
                                "legendFormat": "p95"
                            },
                            {
                                "expr": "histogram_quantile(0.99, rate(workflow_saga_duration_seconds_bucket[5m]))",
                                "legendFormat": "p99"
                            }
                        ],
                        "yAxes": [
                            {"unit": "s"},
                            {"show": False}
                        ],
                        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8}
                    },
                    
                    {
                        "id": 4,
                        "title": "Component Health Status",
                        "type": "table",
                        "targets": [
                            {
                                "expr": "workflow_component_health",
                                "format": "table",
                                "instant": True
                            }
                        ],
                        "transformations": [
                            {
                                "id": "organize",
                                "options": {
                                    "excludeByName": {"Time": True, "__name__": True},
                                    "renameByName": {
                                        "component": "Component",
                                        "instance": "Instance", 
                                        "Value": "Health Status"
                                    }
                                }
                            }
                        ],
                        "fieldConfig": {
                            "overrides": [
                                {
                                    "matcher": {"id": "byName", "options": "Health Status"},
                                    "properties": [
                                        {
                                            "id": "mappings",
                                            "value": [
                                                {"options": {"0": {"text": "Unhealthy", "color": "red"}}, "type": "value"},
                                                {"options": {"1": {"text": "Healthy", "color": "green"}}, "type": "value"}
                                            ]
                                        }
                                    ]
                                }
                            ]
                        },
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16}
                    },
                    
                    {
                        "id": 5,
                        "title": "Idempotency Cache Hit Rate",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "sum(rate(workflow_idempotency_cache_hits_total[5m])) / sum(rate(workflow_idempotent_operations_total[5m])) * 100",
                                "legendFormat": "Cache Hit Rate %"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percent",
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": None},
                                        {"color": "yellow", "value": 60},
                                        {"color": "green", "value": 80}
                                    ]
                                }
                            }
                        },
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16}
                    }
                ]
            }
        }
    
    def generate_prometheus_config(self) -> str:
        """Generate Prometheus configuration for workflow monitoring"""
        
        config = {
            "global": {
                "scrape_interval": "15s",
                "evaluation_interval": "15s"
            },
            "rule_files": [
                "/etc/prometheus/rules/workflow_alerts.yml"
            ],
            "scrape_configs": [
                {
                    "job_name": "workflow-orchestration",
                    "static_configs": [
                        {
                            "targets": ["localhost:8001"]
                        }
                    ],
                    "scrape_interval": "15s",
                    "metrics_path": "/metrics",
                    "scrape_timeout": "10s"
                },
                {
                    "job_name": "workflow-health",
                    "static_configs": [
                        {
                            "targets": ["localhost:8001"] 
                        }
                    ],
                    "scrape_interval": "30s",
                    "metrics_path": "/api/workflows/health",
                    "scrape_timeout": "5s"
                }
            ],
            "alerting": {
                "alertmanagers": [
                    {
                        "static_configs": [
                            {
                                "targets": ["alertmanager:9093"]
                            }
                        ]
                    }
                ]
            }
        }
        
        return json.dumps(config, indent=2)
    
    def generate_alert_rules_config(self) -> str:
        """Generate Prometheus alert rules configuration"""
        
        groups = []
        
        # Critical alerts group
        critical_rules = []
        warning_rules = []
        
        for rule in self.alert_rules:
            rule_config = {
                "alert": rule.name,
                "expr": rule.condition,
                "for": rule.duration,
                "labels": {
                    "severity": rule.severity
                },
                "annotations": {
                    "summary": rule.description,
                    "runbook_url": rule.runbook_url
                }
            }
            
            if rule.severity == "critical":
                critical_rules.append(rule_config)
            else:
                warning_rules.append(rule_config)
        
        if critical_rules:
            groups.append({
                "name": "workflow.critical",
                "rules": critical_rules
            })
        
        if warning_rules:
            groups.append({
                "name": "workflow.warning", 
                "rules": warning_rules
            })
        
        config = {"groups": groups}
        return json.dumps(config, indent=2)
    
    def generate_monitoring_setup_script(self) -> str:
        """Generate shell script to set up monitoring infrastructure"""
        
        return '''#!/bin/bash
# Workflow Orchestration Monitoring Setup Script

set -e

echo "🚀 Setting up workflow orchestration monitoring..."

# Create directories
mkdir -p /etc/prometheus/rules
mkdir -p /etc/grafana/provisioning/dashboards
mkdir -p /etc/grafana/provisioning/datasources

# Generate Prometheus configuration
echo "📊 Configuring Prometheus..."
cat > /etc/prometheus/prometheus.yml << 'EOF'
''' + self.generate_prometheus_config() + '''
EOF

# Generate alert rules
echo "🚨 Setting up alert rules..."
cat > /etc/prometheus/rules/workflow_alerts.yml << 'EOF'
''' + self.generate_alert_rules_config() + '''
EOF

# Generate Grafana datasource configuration
echo "📈 Configuring Grafana datasources..."
cat > /etc/grafana/provisioning/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF

# Generate Grafana dashboard configuration  
echo "📋 Setting up Grafana dashboards..."
cat > /etc/grafana/provisioning/dashboards/workflow-monitoring.json << 'EOF'
''' + json.dumps(self.dashboard_config, indent=2) + '''
EOF

# Set permissions
chmod 644 /etc/prometheus/prometheus.yml
chmod 644 /etc/prometheus/rules/workflow_alerts.yml
chmod 644 /etc/grafana/provisioning/datasources/prometheus.yml
chmod 644 /etc/grafana/provisioning/dashboards/workflow-monitoring.json

echo "✅ Workflow monitoring setup complete!"
echo ""
echo "🔧 Next steps:"
echo "1. Restart Prometheus: systemctl restart prometheus"
echo "2. Restart Grafana: systemctl restart grafana-server"
echo "3. Configure alerting channels in Grafana"
echo "4. Set up notification endpoints (Slack, PagerDuty, etc.)"
echo ""
echo "📊 Monitoring endpoints:"
echo "- Grafana: http://localhost:3000"
echo "- Prometheus: http://localhost:9090"
echo "- Workflow Health: http://localhost:8001/api/workflows/health"
echo "- Metrics: http://localhost:8001/metrics"
'''

    def save_monitoring_configs(self, output_dir: str = ".dev-artifacts/monitoring"):
        """Save all monitoring configurations to files"""
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save Prometheus config
        with open(output_path / "prometheus.yml", "w") as f:
            f.write(self.generate_prometheus_config())
        
        # Save alert rules
        with open(output_path / "workflow_alerts.yml", "w") as f:
            f.write(self.generate_alert_rules_config())
        
        # Save Grafana dashboard
        with open(output_path / "workflow-dashboard.json", "w") as f:
            f.write(json.dumps(self.dashboard_config, indent=2))
        
        # Save setup script
        with open(output_path / "setup-monitoring.sh", "w") as f:
            f.write(self.generate_monitoring_setup_script())
        
        # Make setup script executable
        os.chmod(output_path / "setup-monitoring.sh", 0o755)
        
        print(f"✅ Monitoring configurations saved to {output_path}")
        print(f"📁 Files created:")
        print(f"  - prometheus.yml")
        print(f"  - workflow_alerts.yml") 
        print(f"  - workflow-dashboard.json")
        print(f"  - setup-monitoring.sh")


def main():
    """Set up workflow orchestration monitoring"""
    
    print("🚀 Phase 4: Setting up comprehensive workflow monitoring...")
    
    setup = WorkflowMonitoringSetup()
    setup.save_monitoring_configs()
    
    print("\n📊 Monitoring Components Created:")
    print(f"  • {len(setup.metrics_definitions)} metric definitions")
    print(f"  • {len(setup.alert_rules)} alert rules")
    print(f"  • 1 Grafana dashboard with {len(setup.dashboard_config['dashboard']['panels'])} panels")
    print(f"  • Prometheus configuration with scraping and alerting")
    
    print("\n🎯 Key Monitoring Features:")
    print("  • Saga execution tracking and performance metrics")
    print("  • Idempotency operation monitoring and cache hit rates") 
    print("  • Component health checks and availability monitoring")
    print("  • Database performance and connection monitoring")
    print("  • Comprehensive alerting with runbook integration")
    
    print("\n🚀 Ready for production deployment!")


if __name__ == "__main__":
    main()