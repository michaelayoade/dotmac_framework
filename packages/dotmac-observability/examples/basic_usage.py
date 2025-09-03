#!/usr/bin/env python3
"""
Basic usage example for dotmac.observability package.

This example demonstrates:
- Creating configuration for different environments
- Initializing OpenTelemetry and metrics
- Registering custom metrics
- Recording business metrics
- SLO evaluation
- Health monitoring
"""

import time
import random
from dotmac.observability import (
    # Configuration
    create_default_config,
    Environment,
    
    # Bootstrap
    initialize_otel,
    
    # Metrics
    initialize_metrics_registry,
    initialize_tenant_metrics,
    MetricDefinition,
    MetricType,
    BusinessMetricSpec,
    BusinessMetricType,
    TenantContext,
    
    # Health
    get_observability_health,
)


def main():
    print("🔭 DotMac Observability Example")
    print("=" * 40)
    
    # 1. Create configuration
    print("\n1. Creating configuration...")
    config = create_default_config(
        service_name="example-service",
        environment=Environment.DEVELOPMENT,
        service_version="1.0.0",
        custom_resource_attributes={
            "team": "platform",
            "region": "us-west-2",
            "deployment.mode": "example",
        },
    )
    print(f"   ✅ Config created for {config.service_name}")
    print(f"   📊 Environment: {config.environment}")
    print(f"   🏷️  Custom attributes: {len(config.custom_resource_attributes or {})}")
    
    # 2. Initialize OpenTelemetry
    print("\n2. Initializing OpenTelemetry...")
    otel_bootstrap = initialize_otel(config)
    print(f"   ✅ OTEL initialized: {otel_bootstrap.is_initialized}")
    if otel_bootstrap.is_initialized:
        print(f"   📡 Tracer available: {otel_bootstrap.tracer is not None}")
        print(f"   📊 Meter available: {otel_bootstrap.meter is not None}")
    else:
        print("   ℹ️  OTEL extras not installed, running in mock mode")
    
    # 3. Initialize metrics registry
    print("\n3. Initializing metrics registry...")
    metrics_registry = initialize_metrics_registry(
        service_name="example-service",
        enable_prometheus=False,  # Disable for example
    )
    print(f"   ✅ Metrics registry created")
    print(f"   📈 Default metrics: {len(metrics_registry.list_metrics())}")
    
    # Set OTEL meter if available
    if otel_bootstrap.meter:
        metrics_registry.set_otel_meter(otel_bootstrap.meter)
        print("   🔗 Connected to OpenTelemetry meter")
    
    # 4. Register custom metrics
    print("\n4. Registering custom metrics...")
    
    custom_metrics = [
        MetricDefinition(
            name="example_operations_total",
            type=MetricType.COUNTER,
            description="Total example operations",
            labels=["operation_type", "status"],
        ),
        MetricDefinition(
            name="example_operation_duration_seconds",
            type=MetricType.HISTOGRAM,
            description="Example operation duration",
            labels=["operation_type"],
            unit="s",
        ),
        MetricDefinition(
            name="example_queue_size",
            type=MetricType.GAUGE,
            description="Current queue size",
        ),
    ]
    
    for metric_def in custom_metrics:
        success = metrics_registry.register_metric(metric_def)
        print(f"   {'✅' if success else '❌'} {metric_def.name} ({metric_def.type.value})")
    
    # 5. Initialize tenant metrics for business monitoring
    print("\n5. Initializing tenant metrics...")
    tenant_metrics = initialize_tenant_metrics(
        service_name="example-service",
        metrics_registry=metrics_registry,
        enable_slo_monitoring=True,
    )
    print(f"   ✅ Tenant metrics initialized")
    print(f"   📊 Default business metrics: {len(tenant_metrics.get_business_metrics_info())}")
    
    # Register custom business metric
    custom_business_spec = BusinessMetricSpec(
        name="example_processing_success_rate",
        metric_type=BusinessMetricType.SUCCESS_RATE,
        description="Example processing success rate",
        slo_target=0.95,  # 95% target
        alert_threshold=0.90,  # Alert at 90%
        labels=["tenant_id", "service", "processor"],
    )
    
    success = tenant_metrics.register_business_metric(custom_business_spec)
    print(f"   {'✅' if success else '❌'} Custom business metric registered")
    
    # 6. Simulate operations and record metrics
    print("\n6. Simulating operations...")
    
    tenant_context = TenantContext(
        tenant_id="example-tenant",
        service="example-service",
        region="us-west-2",
        environment="development",
        additional_labels={"processor": "main"},
    )
    
    # Simulate 20 operations
    for i in range(20):
        operation_type = random.choice(["process", "validate", "transform"])
        
        # Simulate operation duration
        start_time = time.time()
        time.sleep(random.uniform(0.01, 0.1))  # 10-100ms
        duration = time.time() - start_time
        
        # Determine success (90% success rate)
        is_success = random.random() < 0.9
        status = "success" if is_success else "error"
        
        # Record system metrics
        metrics_registry.increment_counter("example_operations_total", 1, {
            "operation_type": operation_type,
            "status": status,
        })
        
        metrics_registry.observe_histogram("example_operation_duration_seconds", duration, {
            "operation_type": operation_type,
        })
        
        # Update queue size (simulate fluctuating load)
        queue_size = random.randint(0, 50)
        metrics_registry.set_gauge("example_queue_size", queue_size)
        
        # Record business metrics
        tenant_metrics.record_business_metric(
            "example_processing_success_rate",
            1 if is_success else 0,
            tenant_context
        )
        
        # Also record default business metrics
        tenant_metrics.record_business_metric(
            "api_request_success_rate",
            1 if is_success else 0,
            tenant_context
        )
        
        if i % 5 == 0:
            print(f"   📊 Completed {i+1}/20 operations...")
    
    print("   ✅ All operations completed")
    
    # 7. Evaluate SLOs
    print("\n7. Evaluating SLOs...")
    slo_evaluations = tenant_metrics.evaluate_slos(tenant_context)
    
    for metric_name, evaluation in slo_evaluations.items():
        status_emoji = "✅" if evaluation.is_healthy else ("⚠️" if evaluation.is_warning else "🚨")
        print(f"   {status_emoji} {metric_name}:")
        print(f"      Current: {evaluation.current_value:.1%}")
        print(f"      Target:  {evaluation.slo_target:.1%}")
        print(f"      Error Budget: {evaluation.error_budget_remaining:.1f}% remaining")
    
    # 8. Check system health
    print("\n8. Checking system health...")
    health = get_observability_health(
        otel_bootstrap=otel_bootstrap,
        metrics_registry=metrics_registry,
        tenant_metrics=tenant_metrics,
    )
    
    health_emoji = "✅" if health.is_healthy else "⚠️"
    print(f"   {health_emoji} Overall health: {health.status.value}")
    print(f"   🔍 Total checks: {len(health.checks)}")
    
    for check in health.checks:
        check_emoji = "✅" if check.status.value == "healthy" else "⚠️"
        print(f"   {check_emoji} {check.name}: {check.message}")
    
    # 9. Show metrics summary
    print("\n9. Metrics summary...")
    all_metrics = metrics_registry.list_metrics()
    print(f"   📊 Total registered metrics: {len(all_metrics)}")
    
    # Group by type
    metrics_info = metrics_registry.get_metrics_info()
    metric_types = {}
    for info in metrics_info.values():
        metric_type = info["type"]
        metric_types[metric_type] = metric_types.get(metric_type, 0) + 1
    
    for metric_type, count in metric_types.items():
        print(f"   📈 {metric_type}: {count} metrics")
    
    print(f"\n🎉 Example completed successfully!")
    print("\nNext steps:")
    print("- Install with extras: pip install 'dotmac-observability[all]'")
    print("- Check the /metrics endpoint in your web application")
    print("- Set up dashboard provisioning for SigNoz/Grafana")
    print("- Configure production exporters (OTLP/Jaeger)")


if __name__ == "__main__":
    main()