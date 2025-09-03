"""
Integration tests for the observability package.
"""

import pytest
from unittest.mock import patch

from dotmac.observability import (
    create_default_config,
    initialize_otel,
    initialize_metrics_registry,
    initialize_tenant_metrics,
    BusinessMetricSpec,
    BusinessMetricType,
    TenantContext,
    Environment,
    get_observability_health,
)


@pytest.mark.integration
def test_full_observability_setup():
    """Test complete observability setup flow."""
    # Create configuration
    config = create_default_config(
        service_name="integration-test",
        environment=Environment.DEVELOPMENT,
        service_version="1.0.0",
    )
    
    assert config.service_name == "integration-test"
    assert config.environment == Environment.DEVELOPMENT
    
    # Initialize OpenTelemetry (without actual OTEL deps)
    with patch('dotmac.observability.bootstrap.OTEL_AVAILABLE', False):
        bootstrap = initialize_otel(config)
        assert not bootstrap.is_initialized
    
    # Initialize metrics registry
    with patch('dotmac.observability.metrics.registry.PROMETHEUS_AVAILABLE', False):
        metrics_registry = initialize_metrics_registry(
            service_name="integration-test",
            enable_prometheus=False,
        )
        
        assert metrics_registry.service_name == "integration-test"
        assert len(metrics_registry.list_metrics()) > 0
    
    # Initialize tenant metrics
    tenant_metrics = initialize_tenant_metrics(
        service_name="integration-test",
        metrics_registry=metrics_registry,
        enable_slo_monitoring=True,
    )
    
    assert tenant_metrics.service_name == "integration-test"
    assert tenant_metrics.enable_slo_monitoring is True
    
    # Register custom business metric
    custom_spec = BusinessMetricSpec(
        name="integration_test_success",
        metric_type=BusinessMetricType.SUCCESS_RATE,
        description="Integration test success rate",
        slo_target=0.99,
        alert_threshold=0.95,
    )
    
    success = tenant_metrics.register_business_metric(custom_spec)
    assert success is True
    
    # Record some metrics
    context = TenantContext(tenant_id="test-tenant", service="integration-test")
    
    # Record successful operations
    for _ in range(10):
        tenant_metrics.record_business_metric("integration_test_success", 1, context)
    
    # Record one failure
    tenant_metrics.record_business_metric("integration_test_success", 0, context)
    
    # Evaluate SLOs
    evaluations = tenant_metrics.evaluate_slos(context)
    assert len(evaluations) > 0
    assert "integration_test_success" in evaluations
    
    evaluation = evaluations["integration_test_success"]
    assert evaluation.metric_name == "integration_test_success"
    assert evaluation.tenant_context == context


@pytest.mark.integration
def test_health_monitoring_integration():
    """Test health monitoring integration."""
    # Setup components
    config = create_default_config("health-test", Environment.DEVELOPMENT)
    
    with patch('dotmac.observability.bootstrap.OTEL_AVAILABLE', False):
        bootstrap = initialize_otel(config)
    
    with patch('dotmac.observability.metrics.registry.PROMETHEUS_AVAILABLE', False):
        metrics_registry = initialize_metrics_registry("health-test")
    
    tenant_metrics = initialize_tenant_metrics(
        "health-test", 
        metrics_registry,
        enable_slo_monitoring=True,
    )
    
    # Get overall health
    health = get_observability_health(
        otel_bootstrap=bootstrap,
        metrics_registry=metrics_registry,
        tenant_metrics=tenant_metrics,
    )
    
    assert health.status is not None
    assert len(health.checks) == 3  # OTEL, metrics registry, tenant metrics
    assert health.timestamp is not None
    
    # Check individual components
    check_names = [check.name for check in health.checks]
    assert "opentelemetry" in check_names
    assert "metrics_registry" in check_names  
    assert "tenant_metrics" in check_names
    
    # Get health summary
    summary = health.summary
    assert "overall_status" in summary
    assert "total_checks" in summary
    assert "status_breakdown" in summary


@pytest.mark.integration  
def test_metrics_end_to_end():
    """Test end-to-end metrics flow."""
    # Setup
    with patch('dotmac.observability.metrics.registry.PROMETHEUS_AVAILABLE', False):
        metrics_registry = initialize_metrics_registry("e2e-test")
        
        tenant_metrics = initialize_tenant_metrics(
            "e2e-test",
            metrics_registry,
        )
        
        # Create tenant context
        context = TenantContext(
            tenant_id="e2e-tenant",
            service="e2e-test",
            region="us-west-2",
            environment="development",
        )
        
        # Record various business metrics using defaults
        tenant_metrics.record_business_metric("login_success_rate", 1, context)
        tenant_metrics.record_business_metric("api_request_success_rate", 1, context)
        tenant_metrics.record_business_metric("api_response_latency", 0.25, context)
        
        # Record some failures
        tenant_metrics.record_business_metric("login_success_rate", 0, context)
        tenant_metrics.record_business_metric("api_request_success_rate", 0, context)
        
        # Check that underlying metrics were recorded
        registry_metrics = metrics_registry.list_metrics()
        assert "login_success_rate_total" in registry_metrics
        assert "login_success_rate_success" in registry_metrics
        assert "api_request_success_rate_total" in registry_metrics
        assert "api_response_latency" in registry_metrics
        
        # Get metrics info
        metrics_info = metrics_registry.get_metrics_info()
        assert len(metrics_info) > 0
        
        # Evaluate SLOs
        evaluations = tenant_metrics.evaluate_slos(context)
        assert len(evaluations) > 0


@pytest.mark.integration
def test_different_environments():
    """Test configuration for different environments."""
    environments = [
        Environment.DEVELOPMENT,
        Environment.STAGING,
        Environment.PRODUCTION,
        Environment.TEST,
    ]
    
    for env in environments:
        config = create_default_config(
            service_name=f"test-{env.value}",
            environment=env,
        )
        
        assert config.environment == env
        assert config.service_name == f"test-{env.value}"
        
        # Development should have different sampling
        if env == Environment.DEVELOPMENT:
            assert config.trace_sampler_ratio == 1.0
        else:
            assert config.trace_sampler_ratio == 0.1
        
        # All should have appropriate exporters
        assert len(config.tracing_exporters) > 0
        assert len(config.metrics_exporters) > 0


@pytest.mark.integration
def test_custom_resource_attributes():
    """Test custom resource attributes flow."""
    custom_attrs = {
        "deployment.mode": "kubernetes",
        "service.namespace": "dotmac-system",
        "service.instance.id": "pod-123",
        "team": "platform",
    }
    
    config = create_default_config(
        service_name="custom-attrs-test",
        environment=Environment.PRODUCTION,
        custom_resource_attributes=custom_attrs,
    )
    
    attributes = config.get_resource_attributes()
    
    # Should have standard attributes
    assert attributes["service.name"] == "custom-attrs-test"
    assert attributes["deployment.environment"] == "production"
    
    # Should have custom attributes
    for key, value in custom_attrs.items():
        assert attributes[key] == value


@pytest.mark.integration
def test_tenant_scoped_metrics():
    """Test tenant-scoped metrics isolation."""
    with patch('dotmac.observability.metrics.registry.PROMETHEUS_AVAILABLE', False):
        registry = initialize_metrics_registry("multi-tenant-test")
        tenant_metrics = initialize_tenant_metrics("multi-tenant-test", registry)
        
        # Create multiple tenant contexts
        tenant_a = TenantContext(tenant_id="tenant-a", service="test")
        tenant_b = TenantContext(tenant_id="tenant-b", service="test")
        
        # Record metrics for different tenants
        tenant_metrics.record_business_metric("login_success_rate", 1, tenant_a)
        tenant_metrics.record_business_metric("login_success_rate", 0, tenant_b)
        
        # Evaluate SLOs for each tenant
        slos_a = tenant_metrics.evaluate_slos(tenant_a)
        slos_b = tenant_metrics.evaluate_slos(tenant_b)
        
        # Both should have evaluations
        assert len(slos_a) > 0
        assert len(slos_b) > 0
        
        # Should be for correct tenants
        for eval_name, evaluation in slos_a.items():
            assert evaluation.tenant_context.tenant_id == "tenant-a"
            
        for eval_name, evaluation in slos_b.items():
            assert evaluation.tenant_context.tenant_id == "tenant-b"


@pytest.mark.integration
def test_business_metric_lifecycle():
    """Test complete business metric lifecycle."""
    with patch('dotmac.observability.metrics.registry.PROMETHEUS_AVAILABLE', False):
        registry = initialize_metrics_registry("lifecycle-test")
        tenant_metrics = initialize_tenant_metrics("lifecycle-test", registry)
        
        # Define custom business metric
        spec = BusinessMetricSpec(
            name="order_processing_success",
            metric_type=BusinessMetricType.SUCCESS_RATE,
            description="Order processing success rate",
            slo_target=0.995,
            alert_threshold=0.99,
            labels=["tenant_id", "service", "region"],
        )
        
        # Register the metric
        success = tenant_metrics.register_business_metric(spec)
        assert success is True
        
        # Verify it's in the registry
        business_metrics = tenant_metrics.get_business_metrics_info()
        assert "order_processing_success" in business_metrics
        
        metric_info = business_metrics["order_processing_success"]
        assert metric_info["type"] == "success_rate"
        assert metric_info["slo_target"] == 0.995
        
        # Record data over time
        context = TenantContext(
            tenant_id="ecommerce-tenant",
            service="orders",
            region="us-east-1",
        )
        
        # Simulate 1000 successful orders
        for _ in range(1000):
            tenant_metrics.record_business_metric("order_processing_success", 1, context)
        
        # Simulate 2 failed orders
        for _ in range(2):
            tenant_metrics.record_business_metric("order_processing_success", 0, context)
        
        # Evaluate SLOs
        evaluations = tenant_metrics.evaluate_slos(context)
        evaluation = evaluations["order_processing_success"]
        
        assert evaluation.metric_name == "order_processing_success"
        assert evaluation.slo_target == 0.995
        assert evaluation.alert_threshold == 0.99
        
        # Track history
        history = tenant_metrics.get_slo_history("order_processing_success", hours=1)
        assert len(history) >= 1