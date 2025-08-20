#!/usr/bin/env python3
"""
Setup default dashboards and alerts in SignOz for DotMac Platform.
Creates comprehensive monitoring dashboards for all services.
"""

import json
import requests
import time
import logging
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SignOzDashboardSetup:
    """Sets up SignOz dashboards and alerts for DotMac Platform."""
    
    def __init__(self, signoz_url: str = "http://localhost:3301"):
        self.signoz_url = signoz_url.rstrip('/')
        self.api_url = f"{signoz_url}/api/v1"
        self.headers = {"Content-Type": "application/json"}
        
    def wait_for_signoz(self, max_retries: int = 30):
        """Wait for SignOz to be ready."""
        logger.info("Waiting for SignOz to be ready...")
        
        for i in range(max_retries):
            try:
                response = requests.get(f"{self.api_url}/health", timeout=5)
                if response.status_code == 200:
                    logger.info("✓ SignOz is ready")
                    return True
            except:
                pass
            
            time.sleep(2)
        
        logger.error("✗ SignOz is not responding")
        return False
    
    def create_service_dashboard(self, service_name: str) -> Dict:
        """Create a comprehensive dashboard for a service."""
        return {
            "title": f"{service_name.title()} Service Dashboard",
            "description": f"Complete observability for {service_name} service",
            "tags": ["service", service_name, "dotmac"],
            "variables": [
                {
                    "name": "tenant_id",
                    "displayName": "Tenant",
                    "type": "query",
                    "query": "SELECT DISTINCT tenant_id FROM signoz_traces.distributed_signoz_index_v2",
                    "default": "all"
                },
                {
                    "name": "time_range",
                    "displayName": "Time Range",
                    "type": "time",
                    "default": "15m"
                }
            ],
            "layout": [
                {"i": "1", "x": 0, "y": 0, "w": 6, "h": 4},
                {"i": "2", "x": 6, "y": 0, "w": 6, "h": 4},
                {"i": "3", "x": 0, "y": 4, "w": 4, "h": 4},
                {"i": "4", "x": 4, "y": 4, "w": 4, "h": 4},
                {"i": "5", "x": 8, "y": 4, "w": 4, "h": 4},
                {"i": "6", "x": 0, "y": 8, "w": 12, "h": 6},
                {"i": "7", "x": 0, "y": 14, "w": 6, "h": 4},
                {"i": "8", "x": 6, "y": 14, "w": 6, "h": 4},
            ],
            "widgets": [
                # Request Rate
                {
                    "id": "1",
                    "title": "Request Rate",
                    "panelType": "TIME_SERIES",
                    "query": {
                        "queryType": "clickhouse",
                        "query": f"""
                            SELECT 
                                toStartOfMinute(timestamp) as time,
                                count(*) as requests_per_minute
                            FROM signoz_traces.distributed_signoz_index_v2
                            WHERE serviceName = 'dotmac-{service_name}'
                                AND timestamp >= now() - INTERVAL {{time_range}}
                            GROUP BY time
                            ORDER BY time
                        """
                    }
                },
                
                # Error Rate
                {
                    "id": "2",
                    "title": "Error Rate %",
                    "panelType": "TIME_SERIES",
                    "query": {
                        "queryType": "clickhouse",
                        "query": f"""
                            SELECT 
                                toStartOfMinute(timestamp) as time,
                                sum(CASE WHEN statusCode >= 400 THEN 1 ELSE 0 END) * 100.0 / count(*) as error_rate
                            FROM signoz_traces.distributed_signoz_index_v2
                            WHERE serviceName = 'dotmac-{service_name}'
                                AND timestamp >= now() - INTERVAL {{time_range}}
                            GROUP BY time
                            ORDER BY time
                        """
                    }
                },
                
                # P95 Latency
                {
                    "id": "3",
                    "title": "P95 Latency (ms)",
                    "panelType": "VALUE",
                    "query": {
                        "queryType": "clickhouse",
                        "query": f"""
                            SELECT 
                                quantile(0.95)(durationNano) / 1000000 as p95_latency_ms
                            FROM signoz_traces.distributed_signoz_index_v2
                            WHERE serviceName = 'dotmac-{service_name}'
                                AND timestamp >= now() - INTERVAL {{time_range}}
                        """
                    }
                },
                
                # Active Users
                {
                    "id": "4",
                    "title": "Active Users",
                    "panelType": "VALUE",
                    "query": {
                        "queryType": "clickhouse",
                        "query": f"""
                            SELECT 
                                count(DISTINCT stringTagMap['user.id']) as active_users
                            FROM signoz_traces.distributed_signoz_index_v2
                            WHERE serviceName = 'dotmac-{service_name}'
                                AND timestamp >= now() - INTERVAL {{time_range}}
                        """
                    }
                },
                
                # Throughput
                {
                    "id": "5",
                    "title": "Throughput (req/s)",
                    "panelType": "VALUE",
                    "query": {
                        "queryType": "clickhouse",
                        "query": f"""
                            SELECT 
                                count(*) / ({{time_range}} * 60) as requests_per_second
                            FROM signoz_traces.distributed_signoz_index_v2
                            WHERE serviceName = 'dotmac-{service_name}'
                                AND timestamp >= now() - INTERVAL {{time_range}}
                        """
                    }
                },
                
                # Latency Distribution
                {
                    "id": "6",
                    "title": "Latency Distribution",
                    "panelType": "TIME_SERIES",
                    "query": {
                        "queryType": "clickhouse",
                        "query": f"""
                            SELECT 
                                toStartOfMinute(timestamp) as time,
                                quantile(0.50)(durationNano) / 1000000 as p50,
                                quantile(0.95)(durationNano) / 1000000 as p95,
                                quantile(0.99)(durationNano) / 1000000 as p99
                            FROM signoz_traces.distributed_signoz_index_v2
                            WHERE serviceName = 'dotmac-{service_name}'
                                AND timestamp >= now() - INTERVAL {{time_range}}
                            GROUP BY time
                            ORDER BY time
                        """
                    }
                },
                
                # Top Endpoints
                {
                    "id": "7",
                    "title": "Top Endpoints by Count",
                    "panelType": "TABLE",
                    "query": {
                        "queryType": "clickhouse",
                        "query": f"""
                            SELECT 
                                stringTagMap['http.route'] as endpoint,
                                count(*) as requests,
                                avg(durationNano) / 1000000 as avg_latency_ms,
                                sum(CASE WHEN statusCode >= 400 THEN 1 ELSE 0 END) as errors
                            FROM signoz_traces.distributed_signoz_index_v2
                            WHERE serviceName = 'dotmac-{service_name}'
                                AND timestamp >= now() - INTERVAL {{time_range}}
                            GROUP BY endpoint
                            ORDER BY requests DESC
                            LIMIT 10
                        """
                    }
                },
                
                # Error Distribution
                {
                    "id": "8",
                    "title": "Error Distribution",
                    "panelType": "PIE_CHART",
                    "query": {
                        "queryType": "clickhouse",
                        "query": f"""
                            SELECT 
                                statusCode,
                                count(*) as count
                            FROM signoz_traces.distributed_signoz_index_v2
                            WHERE serviceName = 'dotmac-{service_name}'
                                AND statusCode >= 400
                                AND timestamp >= now() - INTERVAL {{time_range}}
                            GROUP BY statusCode
                        """
                    }
                }
            ]
        }
    
    def create_platform_overview_dashboard(self) -> Dict:
        """Create platform-wide overview dashboard."""
        return {
            "title": "DotMac Platform Overview",
            "description": "High-level view of entire DotMac platform",
            "tags": ["platform", "overview", "dotmac"],
            "layout": [
                {"i": "1", "x": 0, "y": 0, "w": 3, "h": 2},
                {"i": "2", "x": 3, "y": 0, "w": 3, "h": 2},
                {"i": "3", "x": 6, "y": 0, "w": 3, "h": 2},
                {"i": "4", "x": 9, "y": 0, "w": 3, "h": 2},
                {"i": "5", "x": 0, "y": 2, "w": 12, "h": 6},
                {"i": "6", "x": 0, "y": 8, "w": 6, "h": 4},
                {"i": "7", "x": 6, "y": 8, "w": 6, "h": 4},
            ],
            "widgets": [
                # Total Requests
                {
                    "id": "1",
                    "title": "Total Requests",
                    "panelType": "VALUE",
                    "query": {
                        "queryType": "clickhouse",
                        "query": """
                            SELECT count(*) as total_requests
                            FROM signoz_traces.distributed_signoz_index_v2
                            WHERE timestamp >= now() - INTERVAL 5 MINUTE
                        """
                    }
                },
                
                # Error Rate
                {
                    "id": "2",
                    "title": "Platform Error Rate",
                    "panelType": "VALUE",
                    "query": {
                        "queryType": "clickhouse",
                        "query": """
                            SELECT 
                                sum(CASE WHEN statusCode >= 400 THEN 1 ELSE 0 END) * 100.0 / count(*) as error_rate
                            FROM signoz_traces.distributed_signoz_index_v2
                            WHERE timestamp >= now() - INTERVAL 5 MINUTE
                        """
                    }
                },
                
                # Active Services
                {
                    "id": "3",
                    "title": "Active Services",
                    "panelType": "VALUE",
                    "query": {
                        "queryType": "clickhouse",
                        "query": """
                            SELECT count(DISTINCT serviceName) as active_services
                            FROM signoz_traces.distributed_signoz_index_v2
                            WHERE timestamp >= now() - INTERVAL 5 MINUTE
                        """
                    }
                },
                
                # Active Tenants
                {
                    "id": "4",
                    "title": "Active Tenants",
                    "panelType": "VALUE",
                    "query": {
                        "queryType": "clickhouse",
                        "query": """
                            SELECT count(DISTINCT stringTagMap['tenant.id']) as active_tenants
                            FROM signoz_traces.distributed_signoz_index_v2
                            WHERE timestamp >= now() - INTERVAL 5 MINUTE
                        """
                    }
                },
                
                # Service Health Map
                {
                    "id": "5",
                    "title": "Service Health Status",
                    "panelType": "TIME_SERIES",
                    "query": {
                        "queryType": "clickhouse",
                        "query": """
                            SELECT 
                                toStartOfMinute(timestamp) as time,
                                serviceName,
                                sum(CASE WHEN statusCode >= 400 THEN 1 ELSE 0 END) * 100.0 / count(*) as error_rate
                            FROM signoz_traces.distributed_signoz_index_v2
                            WHERE timestamp >= now() - INTERVAL 30 MINUTE
                            GROUP BY time, serviceName
                            ORDER BY time
                        """
                    }
                },
                
                # Top Services by Volume
                {
                    "id": "6",
                    "title": "Top Services by Request Volume",
                    "panelType": "BAR_CHART",
                    "query": {
                        "queryType": "clickhouse",
                        "query": """
                            SELECT 
                                serviceName,
                                count(*) as requests
                            FROM signoz_traces.distributed_signoz_index_v2
                            WHERE timestamp >= now() - INTERVAL 1 HOUR
                            GROUP BY serviceName
                            ORDER BY requests DESC
                        """
                    }
                },
                
                # Slowest Services
                {
                    "id": "7",
                    "title": "Slowest Services (P95)",
                    "panelType": "BAR_CHART",
                    "query": {
                        "queryType": "clickhouse",
                        "query": """
                            SELECT 
                                serviceName,
                                quantile(0.95)(durationNano) / 1000000 as p95_latency_ms
                            FROM signoz_traces.distributed_signoz_index_v2
                            WHERE timestamp >= now() - INTERVAL 1 HOUR
                            GROUP BY serviceName
                            ORDER BY p95_latency_ms DESC
                        """
                    }
                }
            ]
        }
    
    def create_business_metrics_dashboard(self) -> Dict:
        """Create business metrics dashboard."""
        return {
            "title": "Business Metrics Dashboard",
            "description": "Key business KPIs and metrics",
            "tags": ["business", "kpi", "revenue"],
            "widgets": [
                {
                    "id": "1",
                    "title": "Revenue Today",
                    "panelType": "VALUE",
                    "query": {
                        "queryType": "metric",
                        "metric": "business.revenue.total",
                        "aggregation": "sum",
                        "filters": {
                            "time": "today"
                        }
                    }
                },
                {
                    "id": "2",
                    "title": "New Subscriptions",
                    "panelType": "TIME_SERIES",
                    "query": {
                        "queryType": "metric",
                        "metric": "business.events.count",
                        "aggregation": "sum",
                        "groupBy": ["event.type"],
                        "filters": {
                            "event.type": "subscription_created"
                        }
                    }
                },
                {
                    "id": "3",
                    "title": "Payment Success Rate",
                    "panelType": "GAUGE",
                    "query": {
                        "queryType": "metric",
                        "metric": "business.events.count",
                        "aggregation": "rate",
                        "filters": {
                            "event.type": "payment_*"
                        }
                    }
                },
                {
                    "id": "4",
                    "title": "Active Customers by Tier",
                    "panelType": "PIE_CHART",
                    "query": {
                        "queryType": "clickhouse",
                        "query": """
                            SELECT 
                                stringTagMap['customer.tier'] as tier,
                                count(DISTINCT stringTagMap['customer.id']) as customers
                            FROM signoz_traces.distributed_signoz_index_v2
                            WHERE timestamp >= now() - INTERVAL 24 HOUR
                            GROUP BY tier
                        """
                    }
                }
            ]
        }
    
    def create_alerts(self) -> List[Dict]:
        """Create default alert rules."""
        return [
            # High Error Rate Alert
            {
                "alert": "HighErrorRate",
                "expr": """
                    SELECT 
                        serviceName,
                        sum(CASE WHEN statusCode >= 500 THEN 1 ELSE 0 END) * 100.0 / count(*) as error_rate
                    FROM signoz_traces.distributed_signoz_index_v2
                    WHERE timestamp >= now() - INTERVAL 5 MINUTE
                    GROUP BY serviceName
                    HAVING error_rate > 10
                """,
                "for": "5m",
                "labels": {
                    "severity": "critical",
                    "team": "platform"
                },
                "annotations": {
                    "summary": "High error rate detected in {{ $labels.serviceName }}",
                    "description": "Service {{ $labels.serviceName }} has {{ $value }}% error rate"
                }
            },
            
            # High Latency Alert
            {
                "alert": "HighLatency",
                "expr": """
                    SELECT 
                        serviceName,
                        quantile(0.95)(durationNano) / 1000000 as p95_latency_ms
                    FROM signoz_traces.distributed_signoz_index_v2
                    WHERE timestamp >= now() - INTERVAL 5 MINUTE
                    GROUP BY serviceName
                    HAVING p95_latency_ms > 1000
                """,
                "for": "5m",
                "labels": {
                    "severity": "warning",
                    "team": "platform"
                },
                "annotations": {
                    "summary": "High latency in {{ $labels.serviceName }}",
                    "description": "P95 latency is {{ $value }}ms"
                }
            },
            
            # Service Down Alert
            {
                "alert": "ServiceDown",
                "expr": """
                    SELECT 
                        serviceName,
                        count(*) as requests
                    FROM signoz_traces.distributed_signoz_index_v2
                    WHERE timestamp >= now() - INTERVAL 2 MINUTE
                    GROUP BY serviceName
                    HAVING requests = 0
                """,
                "for": "2m",
                "labels": {
                    "severity": "critical",
                    "team": "platform"
                },
                "annotations": {
                    "summary": "Service {{ $labels.serviceName }} is down",
                    "description": "No requests received from {{ $labels.serviceName }} in last 2 minutes"
                }
            },
            
            # Payment Failures Alert
            {
                "alert": "PaymentFailures",
                "expr": """
                    SELECT 
                        count(*) as failed_payments
                    FROM signoz_traces.distributed_signoz_index_v2
                    WHERE stringTagMap['event.type'] = 'payment_failed'
                        AND timestamp >= now() - INTERVAL 5 MINUTE
                    HAVING failed_payments > 5
                """,
                "for": "1m",
                "labels": {
                    "severity": "critical",
                    "team": "billing"
                },
                "annotations": {
                    "summary": "Multiple payment failures detected",
                    "description": "{{ $value }} payment failures in last 5 minutes"
                }
            }
        ]
    
    def setup_all(self):
        """Setup all dashboards and alerts."""
        if not self.wait_for_signoz():
            logger.error("SignOz is not available, exiting")
            return False
        
        logger.info("Setting up SignOz dashboards and alerts...")
        
        # Create dashboards for each service
        services = [
            "api-gateway", "identity", "billing", "services",
            "networking", "analytics", "core-ops", "core-events",
            "platform", "devtools"
        ]
        
        for service in services:
            try:
                dashboard = self.create_service_dashboard(service)
                response = requests.post(
                    f"{self.api_url}/dashboards",
                    json=dashboard,
                    headers=self.headers
                )
                if response.status_code in [200, 201]:
                    logger.info(f"✓ Created dashboard for {service}")
                else:
                    logger.warning(f"✗ Failed to create dashboard for {service}: {response.text}")
            except Exception as e:
                logger.error(f"✗ Error creating dashboard for {service}: {e}")
        
        # Create platform overview dashboard
        try:
            platform_dashboard = self.create_platform_overview_dashboard()
            response = requests.post(
                f"{self.api_url}/dashboards",
                json=platform_dashboard,
                headers=self.headers
            )
            if response.status_code in [200, 201]:
                logger.info("✓ Created platform overview dashboard")
        except Exception as e:
            logger.error(f"✗ Error creating platform dashboard: {e}")
        
        # Create business metrics dashboard
        try:
            business_dashboard = self.create_business_metrics_dashboard()
            response = requests.post(
                f"{self.api_url}/dashboards",
                json=business_dashboard,
                headers=self.headers
            )
            if response.status_code in [200, 201]:
                logger.info("✓ Created business metrics dashboard")
        except Exception as e:
            logger.error(f"✗ Error creating business dashboard: {e}")
        
        # Create alerts
        alerts = self.create_alerts()
        for alert in alerts:
            try:
                response = requests.post(
                    f"{self.api_url}/alerts",
                    json=alert,
                    headers=self.headers
                )
                if response.status_code in [200, 201]:
                    logger.info(f"✓ Created alert: {alert['alert']}")
                else:
                    logger.warning(f"✗ Failed to create alert {alert['alert']}: {response.text}")
            except Exception as e:
                logger.error(f"✗ Error creating alert {alert['alert']}: {e}")
        
        logger.info("\n✅ SignOz setup complete!")
        logger.info("📊 Access dashboards at: http://localhost:3301")
        
        return True


if __name__ == "__main__":
    setup = SignOzDashboardSetup()
    setup.setup_all()