"""
Tests for business metrics and SLO monitoring.
"""

import pytest
from datetime import datetime, timedelta

from dotmac.observability.metrics.business import (
    BusinessMetricSpec,
    BusinessMetricType,
    TenantContext,
    TenantMetrics,
    SLOEvaluation,
    initialize_tenant_metrics,
)
from dotmac.observability.metrics.registry import MetricsRegistry


def test_business_metric_spec():
    """Test business metric specification."""
    spec = BusinessMetricSpec(
        name="login_success_rate",
        metric_type=BusinessMetricType.SUCCESS_RATE,
        description="User login success rate",
        slo_target=0.99,
        alert_threshold=0.95,
    )
    
    assert spec.name == "login_success_rate"
    assert spec.metric_type == BusinessMetricType.SUCCESS_RATE
    assert spec.slo_target == 0.99
    assert spec.alert_threshold == 0.95
    assert spec.critical_threshold == 0.95 * 0.9  # 90% of alert threshold
    assert spec.labels == ["tenant_id", "service"]  # Default labels


def test_business_metric_spec_validation():
    """Test business metric spec validation."""
    # Should raise error if SLO target <= alert threshold
    with pytest.raises(ValueError, match="SLO target must be higher than alert threshold"):
        BusinessMetricSpec(
            name="bad_spec",
            metric_type=BusinessMetricType.SUCCESS_RATE,
            description="Bad spec",
            slo_target=0.90,
            alert_threshold=0.95,
        )
    
    # Should raise error if alert threshold <= critical threshold
    with pytest.raises(ValueError, match="Alert threshold must be higher than critical threshold"):
        BusinessMetricSpec(
            name="bad_spec2",
            metric_type=BusinessMetricType.SUCCESS_RATE,
            description="Bad spec",
            slo_target=0.99,
            alert_threshold=0.90,
            critical_threshold=0.95,
        )


def test_tenant_context():
    """Test tenant context creation and conversion to labels."""
    context = TenantContext(
        tenant_id="tenant-123",
        service="auth-service",
        region="us-east-1",
        environment="production",
        additional_labels={"team": "platform"},
    )
    
    labels = context.to_labels()
    
    assert labels["tenant_id"] == "tenant-123"
    assert labels["service"] == "auth-service"
    assert labels["region"] == "us-east-1"
    assert labels["environment"] == "production"
    assert labels["team"] == "platform"


def test_tenant_metrics_initialization():
    """Test tenant metrics initialization."""
    registry = MetricsRegistry("test-service", enable_prometheus=False)
    
    tenant_metrics = TenantMetrics(
        service_name="test-service",
        metrics_registry=registry,
        enable_dashboards=False,
        enable_slo_monitoring=True,
    )
    
    assert tenant_metrics.service_name == "test-service"
    assert tenant_metrics.metrics_registry == registry
    assert tenant_metrics.enable_slo_monitoring is True
    
    # Should have default business metrics registered
    business_metrics = tenant_metrics.get_business_metrics_info()
    assert len(business_metrics) > 0
    assert "login_success_rate" in business_metrics
    assert "api_request_success_rate" in business_metrics


def test_tenant_metrics_register_business_metric():
    """Test registering business metrics."""
    registry = MetricsRegistry("test-service", enable_prometheus=False)
    tenant_metrics = TenantMetrics("test-service", registry)
    
    spec = BusinessMetricSpec(
        name="custom_success_rate",
        metric_type=BusinessMetricType.SUCCESS_RATE,
        description="Custom success rate",
        slo_target=0.98,
        alert_threshold=0.95,
    )
    
    success = tenant_metrics.register_business_metric(spec)
    assert success is True
    
    # Check it's registered
    business_metrics = tenant_metrics.get_business_metrics_info()
    assert "custom_success_rate" in business_metrics
    
    # Check underlying metrics were created
    registry_metrics = registry.list_metrics()
    assert "custom_success_rate_total" in registry_metrics
    assert "custom_success_rate_success" in registry_metrics


def test_tenant_metrics_record_success_rate():
    """Test recording success rate business metric."""
    registry = MetricsRegistry("test-service", enable_prometheus=False)
    tenant_metrics = TenantMetrics("test-service", registry)
    
    spec = BusinessMetricSpec(
        name="test_success_rate",
        metric_type=BusinessMetricType.SUCCESS_RATE,
        description="Test success rate",
        slo_target=0.99,
        alert_threshold=0.95,
    )
    
    tenant_metrics.register_business_metric(spec)
    
    context = TenantContext(tenant_id="tenant-123", service="test-service")
    
    # Record successful operation
    tenant_metrics.record_business_metric("test_success_rate", 1, context)
    
    # Record failed operation
    tenant_metrics.record_business_metric("test_success_rate", 0, context)
    
    # Should not raise any exceptions


def test_tenant_metrics_record_latency():
    """Test recording latency business metric."""
    registry = MetricsRegistry("test-service", enable_prometheus=False)
    tenant_metrics = TenantMetrics("test-service", registry)
    
    spec = BusinessMetricSpec(
        name="api_latency",
        metric_type=BusinessMetricType.LATENCY,
        description="API latency",
        slo_target=0.5,  # 500ms
        alert_threshold=1.0,  # 1s
        unit="s",
    )
    
    tenant_metrics.register_business_metric(spec)
    
    context = TenantContext(tenant_id="tenant-123", service="api")
    
    # Record latency values
    tenant_metrics.record_business_metric("api_latency", 0.3, context)
    tenant_metrics.record_business_metric("api_latency", 0.8, context)
    
    # Check histogram metric was created
    registry_metrics = registry.list_metrics()
    assert "api_latency" in registry_metrics


def test_tenant_metrics_evaluate_slos():
    """Test SLO evaluation."""
    registry = MetricsRegistry("test-service", enable_prometheus=False)
    tenant_metrics = TenantMetrics("test-service", registry, enable_slo_monitoring=True)
    
    context = TenantContext(tenant_id="tenant-123", service="test-service")
    
    # Evaluate SLOs (uses mock data in implementation)
    evaluations = tenant_metrics.evaluate_slos(context)
    
    assert len(evaluations) > 0
    
    # Check default business metrics have evaluations
    assert "login_success_rate" in evaluations
    
    evaluation = evaluations["login_success_rate"]
    assert isinstance(evaluation, SLOEvaluation)
    assert evaluation.metric_name == "login_success_rate"
    assert evaluation.tenant_context == context
    assert evaluation.current_value >= 0
    assert evaluation.current_value <= 1
    assert evaluation.slo_target > 0
    assert evaluation.alert_threshold > 0
    assert evaluation.evaluation_time is not None


def test_tenant_metrics_disabled_slo_monitoring():
    """Test SLO evaluation when disabled."""
    registry = MetricsRegistry("test-service", enable_prometheus=False)
    tenant_metrics = TenantMetrics("test-service", registry, enable_slo_monitoring=False)
    
    context = TenantContext(tenant_id="tenant-123", service="test-service")
    
    evaluations = tenant_metrics.evaluate_slos(context)
    assert len(evaluations) == 0


def test_tenant_metrics_slo_history():
    """Test SLO history tracking."""
    registry = MetricsRegistry("test-service", enable_prometheus=False)
    tenant_metrics = TenantMetrics("test-service", registry, enable_slo_monitoring=True)
    
    context = TenantContext(tenant_id="tenant-123", service="test-service")
    
    # Evaluate SLOs multiple times
    tenant_metrics.evaluate_slos(context)
    tenant_metrics.evaluate_slos(context)
    
    # Get history
    history = tenant_metrics.get_slo_history("login_success_rate", hours=24)
    assert len(history) == 2
    
    for evaluation in history:
        assert isinstance(evaluation, SLOEvaluation)
        assert evaluation.metric_name == "login_success_rate"


def test_initialize_tenant_metrics():
    """Test initialize_tenant_metrics function."""
    registry = MetricsRegistry("test-service", enable_prometheus=False)
    
    tenant_metrics = initialize_tenant_metrics(
        service_name="test-service",
        metrics_registry=registry,
        enable_dashboards=True,
        enable_slo_monitoring=True,
    )
    
    assert isinstance(tenant_metrics, TenantMetrics)
    assert tenant_metrics.service_name == "test-service"
    assert tenant_metrics.metrics_registry == registry
    assert tenant_metrics.enable_dashboards is True
    assert tenant_metrics.enable_slo_monitoring is True


def test_slo_evaluation_properties():
    """Test SLO evaluation properties."""
    context = TenantContext(tenant_id="tenant-123", service="test")
    
    evaluation = SLOEvaluation(
        metric_name="test_metric",
        tenant_context=context,
        current_value=0.92,
        slo_target=0.95,
        alert_threshold=0.90,
        critical_threshold=0.85,
        is_healthy=False,
        is_warning=True,
        is_critical=False,
        error_budget_consumed=60.0,
        error_budget_remaining=40.0,
        evaluation_window=300,
        sample_count=100,
    )
    
    assert evaluation.metric_name == "test_metric"
    assert evaluation.current_value == 0.92
    assert evaluation.is_healthy is False
    assert evaluation.is_warning is True
    assert evaluation.is_critical is False
    assert evaluation.error_budget_consumed == 60.0
    assert evaluation.error_budget_remaining == 40.0


def test_business_metric_types():
    """Test different business metric types registration."""
    registry = MetricsRegistry("test-service", enable_prometheus=False)
    tenant_metrics = TenantMetrics("test-service", registry)
    
    # Test different metric types
    specs = [
        BusinessMetricSpec(
            name="throughput_test",
            metric_type=BusinessMetricType.THROUGHPUT,
            description="Throughput test",
            slo_target=1000,
            alert_threshold=800,
        ),
        BusinessMetricSpec(
            name="error_rate_test",
            metric_type=BusinessMetricType.ERROR_RATE,
            description="Error rate test",
            slo_target=0.01,
            alert_threshold=0.05,
        ),
        BusinessMetricSpec(
            name="availability_test",
            metric_type=BusinessMetricType.AVAILABILITY,
            description="Availability test",
            slo_target=0.999,
            alert_threshold=0.995,
        ),
        BusinessMetricSpec(
            name="custom_test",
            metric_type=BusinessMetricType.CUSTOM,
            description="Custom test",
            slo_target=100,
            alert_threshold=80,
        ),
    ]
    
    for spec in specs:
        success = tenant_metrics.register_business_metric(spec)
        assert success is True
    
    # All should be registered
    business_metrics = tenant_metrics.get_business_metrics_info()
    for spec in specs:
        assert spec.name in business_metrics


def test_record_different_metric_types():
    """Test recording values for different business metric types."""
    registry = MetricsRegistry("test-service", enable_prometheus=False)
    tenant_metrics = TenantMetrics("test-service", registry)
    
    context = TenantContext(tenant_id="tenant-123", service="test")
    
    # Register and record each type
    specs = [
        ("throughput_test", BusinessMetricType.THROUGHPUT, 150),
        ("error_rate_test", BusinessMetricType.ERROR_RATE, 1),  # Error occurred
        ("availability_test", BusinessMetricType.AVAILABILITY, 0.999),
        ("custom_test", BusinessMetricType.CUSTOM, 85),
    ]
    
    for name, metric_type, value in specs:
        # For error rate metric, use different thresholds (lower is better)
        if metric_type == BusinessMetricType.ERROR_RATE:
            spec = BusinessMetricSpec(
                name=name,
                metric_type=metric_type,
                description=f"{name} description",
                slo_target=0.01,    # Target: 1% error rate
                alert_threshold=0.05,  # Alert: 5% error rate
            )
        else:
            spec = BusinessMetricSpec(
                name=name,
                metric_type=metric_type,
                description=f"{name} description",
                slo_target=100,
                alert_threshold=80,
            )
        
        tenant_metrics.register_business_metric(spec)
        tenant_metrics.record_business_metric(name, value, context)
        
        # Should not raise exceptions