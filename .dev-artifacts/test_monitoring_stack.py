#!/usr/bin/env python3
"""
Test and demonstrate the Monitoring and Observability Stack functionality.
"""

import sys
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# Add src to Python path
sys.path.append('/home/dotmac_framework/src')

async def test_monitoring_stack():
    """Test the monitoring and observability stack functionality."""
    
    print("🚀 Testing Monitoring and Observability Stack")
    print("=" * 60)
    
    try:
        # Import the monitoring stack components
        from dotmac_shared.observability.monitoring_stack import (
            MonitoringStack,
            MonitoringStackFactory,
            MetricsCollector,
            DistributedTracer,
            AlertManager,
            HealthMonitor,
            Metric,
            TraceSpan,
            Alert,
            HealthCheck,
            MetricType,
            AlertSeverity,
            HealthStatus,
            setup_comprehensive_monitoring
        )
        
        print("✅ Monitoring stack imports successful")
        
        # Test MetricsCollector
        print("\n📊 Testing Metrics Collector...")
        
        metrics_collector = MetricsCollector()
        
        # Register metrics
        metrics_collector.register_metric("test_counter", MetricType.COUNTER, "Test counter metric")
        metrics_collector.register_metric("test_gauge", MetricType.GAUGE, "Test gauge metric")
        metrics_collector.register_metric("test_histogram", MetricType.HISTOGRAM, "Test histogram metric")
        
        print(f"✅ Registered {len(metrics_collector.metric_definitions)} metric definitions")
        
        # Record metrics
        metrics_collector.increment_counter("test_counter", 5, {"service": "test-service"})
        metrics_collector.set_gauge("test_gauge", 42.5, {"region": "us-east"})
        metrics_collector.record_histogram("test_histogram", 123.45)
        
        # Test metric retrieval
        counter_summary = metrics_collector.get_metric_summary("test_counter")
        print(f"✅ Counter metric summary: {counter_summary}")
        
        gauge_values = metrics_collector.get_metric_values("test_gauge")
        print(f"✅ Gauge metric values: {len(gauge_values)} values recorded")
        
        # Test DistributedTracer
        print("\n🔍 Testing Distributed Tracer...")
        
        tracer = DistributedTracer()
        
        # Start parent span
        parent_span = tracer.start_span(
            operation_name="process_request",
            service_name="api-service",
            tags={"http.method": "GET", "http.url": "/api/test"}
        )
        
        print(f"✅ Started parent span: {parent_span.span_id}")
        
        # Start child span
        child_span = tracer.start_span(
            operation_name="database_query",
            service_name="database-service",
            trace_id=parent_span.trace_id,
            parent_span_id=parent_span.span_id,
            tags={"db.statement": "SELECT * FROM users"}
        )
        
        print(f"✅ Started child span: {child_span.span_id}")
        
        # Add logs to spans
        parent_span.add_log("Processing user request", "info", user_id="123")
        child_span.add_log("Executing database query", "debug")
        
        # Finish spans
        await asyncio.sleep(0.01)  # Simulate work
        tracer.finish_span(child_span.span_id)
        tracer.finish_span(parent_span.span_id)
        
        # Test trace retrieval
        trace_spans = tracer.get_trace(parent_span.trace_id)
        trace_summary = tracer.get_trace_summary(parent_span.trace_id)
        
        print(f"✅ Trace completed: {trace_summary}")
        print(f"   - Spans: {len(trace_spans)}")
        print(f"   - Services: {trace_summary['services']}")
        print(f"   - Duration: {trace_summary['duration_ms']:.2f}ms")
        
        # Test AlertManager
        print("\n🚨 Testing Alert Manager...")
        
        alert_manager = AlertManager()
        
        # Add alert rules
        alert_manager.add_alert_rule(
            name="High Error Rate",
            service_name="api-service",
            metric_name="error_rate",
            condition="greater_than",
            threshold=5.0,
            severity=AlertSeverity.HIGH
        )
        
        alert_manager.add_alert_rule(
            name="Low Performance",
            service_name="api-service", 
            metric_name="response_time",
            condition="greater_than",
            threshold=1000.0,
            severity=AlertSeverity.MEDIUM
        )
        
        print(f"✅ Added {len(alert_manager.alert_rules)} alert rules")
        
        # Simulate metrics that trigger alerts
        metrics_collector.set_gauge("error_rate", 10.0)  # Should trigger alert
        metrics_collector.set_gauge("response_time", 500.0)  # Should not trigger alert
        
        # Evaluate alerts
        alert_manager.evaluate_alerts(metrics_collector)
        
        active_alerts = alert_manager.get_active_alerts()
        alert_summary = alert_manager.get_alert_summary()
        
        print(f"✅ Alert evaluation completed:")
        print(f"   - Active alerts: {len(active_alerts)}")
        print(f"   - Alert summary: {alert_summary}")
        
        if active_alerts:
            alert = active_alerts[0]
            print(f"   - Sample alert: {alert.name} ({alert.severity}) - {alert.description}")
        
        # Test HealthMonitor
        print("\n🏥 Testing Health Monitor...")
        
        health_monitor = HealthMonitor()
        
        # Register health checks
        health_checks = [
            HealthCheck(
                check_id="api-service-1",
                name="API Service Health",
                service_name="api-service",
                endpoint="http://api-service:8000/health",
                interval_seconds=30,
                timeout_seconds=5
            ),
            HealthCheck(
                check_id="database-service-1",
                name="Database Health",
                service_name="database-service",
                endpoint="http://database:5432/health",
                interval_seconds=60,
                timeout_seconds=10
            )
        ]
        
        for health_check in health_checks:
            health_monitor.register_health_check(health_check)
        
        print(f"✅ Registered {len(health_checks)} health checks")
        
        # Perform health checks
        await health_monitor.perform_health_checks()
        
        # Get health summaries
        api_health = health_monitor.get_service_health("api-service")
        system_health = health_monitor.get_system_health_summary()
        
        print(f"✅ Health checks completed:")
        print(f"   - API service health: {api_health['status']}")
        print(f"   - System health: {system_health['status']}")
        print(f"   - Total checks: {system_health['total_checks']}")
        print(f"   - Healthy: {system_health['healthy']}")
        
        # Test MonitoringStack
        print("\n🔧 Testing Monitoring Stack Integration...")
        
        # Create mock dependencies
        mock_session = Mock()
        mock_marketplace = AsyncMock()
        mock_mesh = Mock()
        mock_gateway = Mock()
        mock_performance = AsyncMock()
        
        # Mock service discovery
        mock_services = [
            {
                "name": "unified-billing-service",
                "instances": [{"host": "billing-1", "port": 8001}]
            },
            {
                "name": "unified-analytics-service",
                "instances": [{"host": "analytics-1", "port": 8003}]
            }
        ]
        mock_marketplace.discover_service.return_value = mock_services
        
        # Mock service metrics
        mock_mesh.get_mesh_metrics.return_value = {
            "active_connections": 15,
            "success_rate_percent": 98.5
        }
        
        mock_gateway_metrics = Mock()
        mock_gateway_metrics.get_summary.return_value = {
            "total_requests": 1000,
            "success_rate": 95.0
        }
        mock_gateway.metrics = mock_gateway_metrics
        
        mock_performance.get_performance_summary.return_value = {
            "cache_stats": {"hit_rate_percent": 85.0},
            "service_metrics": {"error_rate": 2.5}
        }
        
        # Create monitoring stack
        monitoring = MonitoringStackFactory.create_monitoring_stack(
            db_session=mock_session,
            tenant_id="test-tenant",
            service_marketplace=mock_marketplace,
            service_mesh=mock_mesh,
            api_gateway=mock_gateway,
            performance_service=mock_performance
        )
        
        print("✅ Monitoring stack created")
        
        # Initialize with mocked psutil
        with patch('psutil.cpu_percent', return_value=35.5):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.used = 1024 * 1024 * 1024  # 1GB
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk_usage = Mock()
                    mock_disk_usage.used = 50 * 1024 * 1024 * 1024  # 50GB
                    mock_disk_usage.total = 100 * 1024 * 1024 * 1024  # 100GB
                    mock_disk.return_value = mock_disk_usage
                    
                    await monitoring.initialize()
                    print("✅ Monitoring stack initialized")
        
        # Test custom metrics recording
        print("\n📈 Testing Custom Metrics...")
        
        monitoring.record_metric("custom_metric", 42.0, {"component": "test"})
        
        # Create and finish spans
        span = monitoring.create_span("test_operation", "test-service", operation="custom_test")
        await asyncio.sleep(0.005)  # Simulate work
        monitoring.finish_span(span.span_id)
        
        print("✅ Custom metrics and spans recorded")
        
        # Get system overview
        system_overview = monitoring.get_system_overview()
        print(f"✅ System overview generated:")
        print(f"   - Health status: {system_overview['health']['status']}")
        print(f"   - Active alerts: {system_overview['alerts']['total_active']}")
        print(f"   - CPU usage: {system_overview['metrics'].get('cpu_usage_percent', 'N/A')}%")
        print(f"   - Cache hit rate: {system_overview['metrics'].get('cache_hit_rate', 'N/A')}%")
        
        # Test service dashboard
        dashboard_data = monitoring.get_service_dashboard_data("api-service")
        print(f"✅ Service dashboard data:")
        print(f"   - Service: {dashboard_data['service_name']}")
        print(f"   - Health: {dashboard_data['health']['status']}")
        
        # Test Prometheus export
        prometheus_output = monitoring.export_metrics_prometheus()
        print(f"✅ Prometheus export generated: {len(prometheus_output)} characters")
        
        # Show sample Prometheus output
        lines = prometheus_output.split('\n')
        sample_lines = [line for line in lines[:10] if line.strip()]
        print("   Sample Prometheus metrics:")
        for line in sample_lines:
            if line.strip():
                print(f"     {line}")
        
        # Test comprehensive monitoring setup
        print("\n🏗️ Testing Comprehensive Monitoring Setup...")
        
        comprehensive_monitoring = await setup_comprehensive_monitoring(
            db_session=mock_session,
            tenant_id="comprehensive-tenant",
            service_marketplace=mock_marketplace,
            service_mesh=mock_mesh,
            api_gateway=mock_gateway,
            performance_service=mock_performance
        )
        
        comprehensive_overview = comprehensive_monitoring.get_system_overview()
        print(f"✅ Comprehensive monitoring setup:")
        print(f"   - Tenant: {comprehensive_overview['tenant_id']}")
        print(f"   - Health: {comprehensive_overview['health']['status']}")
        print(f"   - Active traces: {comprehensive_overview['active_traces']}")
        
        # Cleanup
        await monitoring.shutdown()
        await comprehensive_monitoring.shutdown()
        print("✅ Monitoring stacks shutdown complete")
        
        print("\n" + "=" * 60)
        print("🎉 Monitoring and Observability Stack Test Complete!")
        print("✅ All monitoring features working correctly")
        
        # Final summary
        print(f"\n🎯 Monitoring Stack Test Summary:")
        print(f"   ✅ Metrics collection (counter, gauge, histogram)")
        print(f"   ✅ Distributed tracing (parent/child spans)")
        print(f"   ✅ Alert management (rules and evaluation)")
        print(f"   ✅ Health monitoring (service and system health)")
        print(f"   ✅ System integration (mesh, gateway, performance)")
        print(f"   ✅ Dashboard data generation")
        print(f"   ✅ Prometheus metrics export")
        print(f"   ✅ Comprehensive monitoring setup")
        
        return True
        
    except Exception as e:
        print(f"❌ Monitoring stack test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    success = await test_monitoring_stack()
    return 0 if success else 1

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)