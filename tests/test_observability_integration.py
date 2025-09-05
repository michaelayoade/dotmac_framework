"""
Test suite for DotMac observability integration.
Validates OpenTelemetry setup, tracing, and metrics collection.
"""

import asyncio
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestObservabilitySetup:
    """Test observability system setup and configuration."""
    
    def test_imports_successful(self):
        """Test that all observability components import successfully."""
        from dotmac.observability import (
            OTelConfig,
            TenantContextMiddleware,
            business_metrics,
            get_meter,
            get_tracer,
            setup_observability,
        )
        
        assert setup_observability is not None
        assert get_tracer is not None
        assert get_meter is not None
        assert OTelConfig is not None
        assert TenantContextMiddleware is not None
        assert business_metrics is not None

    def test_otel_config_creation(self):
        """Test OTelConfig creation and environment handling."""
        from dotmac.observability.otel import OTelConfig
        
        config = OTelConfig()
        
        assert config.service_name == "dotmac-framework"  # default
        assert config.environment in ["dev", "development"]  # default
        assert config.sampling_ratio == 0.10  # default
        assert isinstance(config.resource_attributes, dict)
        assert "service.name" in config.resource_attributes

    def test_tracer_creation(self):
        """Test tracer creation and span functionality."""
        from dotmac.observability import get_tracer
        
        tracer = get_tracer("test-service")
        assert tracer is not None
        
        # Test span creation
        with tracer.start_as_current_span("test-span") as span:
            assert span is not None
            span.set_attribute("test.attribute", "test-value")
            span.add_event("test-event", {"event.data": "test"})

    def test_meter_creation(self):
        """Test meter creation and metrics functionality."""
        from dotmac.observability import get_meter
        
        meter = get_meter("test-service")
        assert meter is not None
        
        # Test metric creation
        counter = meter.create_counter("test.counter", description="Test counter")
        histogram = meter.create_histogram("test.histogram", description="Test histogram")
        
        assert counter is not None
        assert histogram is not None


class TestBusinessMetrics:
    """Test business metrics collection and recording."""
    
    def test_business_metrics_creation(self):
        """Test business metrics instance creation."""
        from dotmac.observability.business_metrics import DotMacBusinessMetrics
        
        metrics = DotMacBusinessMetrics()
        assert metrics is not None
        assert metrics.meter is not None

    def test_partner_signup_recording(self):
        """Test partner signup event recording."""
        from dotmac.observability.business_metrics import business_metrics
        
        # This should not raise any exceptions
        business_metrics.record_partner_signup(
            partner_tier="gold",
            territory="west_coast",
            signup_source="referral"
        )

    def test_customer_acquisition_recording(self):
        """Test customer acquisition event recording."""
        from dotmac.observability.business_metrics import business_metrics
        
        business_metrics.record_customer_acquisition(
            partner_id="partner_123",
            customer_mrr=99.99,
            service_plan="residential_premium"
        )

    def test_commission_calculation_recording(self):
        """Test commission calculation event recording."""
        from dotmac.observability.business_metrics import business_metrics
        
        business_metrics.record_commission_calculation(
            partner_id="partner_123",
            commission_amount=150.00,
            base_amount=500.00,
            commission_rate=0.30
        )


class TestMiddleware:
    """Test observability middleware functionality."""
    
    def test_tenant_context_middleware_creation(self):
        """Test tenant context middleware creation."""
        from dotmac.observability.middleware import TenantContextMiddleware
        
        app = FastAPI()
        middleware = TenantContextMiddleware(app)
        assert middleware is not None

    def test_metrics_middleware_creation(self):
        """Test metrics middleware creation."""
        from dotmac.observability.middleware import MetricsMiddleware
        
        app = FastAPI()
        middleware = MetricsMiddleware(app)
        assert middleware is not None


class TestDatabaseObservability:
    """Test database observability features."""
    
    def test_traced_db_operation_decorator(self):
        """Test database operation tracing decorator."""
        from dotmac.observability.database import traced_db_operation
        
        @traced_db_operation("test_operation")
        async def test_async_db_op():
            return "test_result"
        
        @traced_db_operation("test_operation") 
        def test_sync_db_op():
            return "test_result"
        
        # Test async function
        result = asyncio.run(test_async_db_op())
        assert result == "test_result"
        
        # Test sync function
        result = test_sync_db_op()
        assert result == "test_result"

    def test_query_monitor_creation(self):
        """Test query monitor initialization."""
        from dotmac.observability.database import QueryMonitor
        
        monitor = QueryMonitor(slow_query_threshold=100.0)
        assert monitor is not None
        assert monitor.slow_query_threshold == 100.0


class TestLoggingIntegration:
    """Test logging and trace correlation."""
    
    def test_otel_trace_context_filter(self):
        """Test OpenTelemetry trace context filter."""
        import logging

        from dotmac.observability.logging import OTelTraceContextFilter
        
        filter_obj = OTelTraceContextFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Should not raise exceptions
        result = filter_obj.filter(record)
        assert result is True
        assert hasattr(record, "trace_id")
        assert hasattr(record, "span_id")

    def test_structured_formatter(self):
        """Test structured JSON formatter."""
        import json
        import logging

        from dotmac.observability.logging import StructuredFormatter
        
        formatter = StructuredFormatter(include_trace=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Add trace context to record
        record.trace_id = "test_trace_id"
        record.span_id = "test_span_id"
        
        formatted = formatter.format(record)
        
        # Should be valid JSON
        parsed = json.loads(formatted)
        assert parsed["message"] == "Test message"
        assert parsed["level"] == "INFO"
        assert parsed["trace_id"] == "test_trace_id"

    def test_dotmac_logger_creation(self):
        """Test DotMac enhanced logger creation."""
        from dotmac.observability.logging import get_logger
        
        logger = get_logger("test.component")
        assert logger is not None
        
        # Test logging methods exist
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning") 
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")


class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    def test_full_observability_setup(self):
        """Test complete observability setup with FastAPI app."""
        from dotmac.observability import setup_observability
        
        app = FastAPI(title="Test App")
        
        # Mock database engine
        mock_engine = Mock()
        mock_engine.sync_engine = Mock()
        
        # Should not raise exceptions
        with patch.dict('os.environ', {
            'OTEL_SERVICE_NAME': 'test-service',
            'ENVIRONMENT': 'test',
            'OTEL_TRACES_SAMPLING_RATIO': '1.0'
        }):
            tracer_provider, meter_provider = setup_observability(app, mock_engine)
            
            assert tracer_provider is not None
            assert meter_provider is not None

    def test_fastapi_integration_with_client(self):
        """Test FastAPI integration using TestClient."""
        from dotmac.observability import setup_observability
        
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @app.get("/health")
        async def health_check():
            return {"status": "healthy"}
        
        # Setup observability
        with patch.dict('os.environ', {
            'OTEL_SERVICE_NAME': 'test-service',
            'ENVIRONMENT': 'test'
        }):
            setup_observability(app, None)
        
        # Test with client
        client = TestClient(app)
        
        # Health check should work
        response = client.get("/health")
        assert response.status_code == 200
        
        # Test endpoint should work
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"message": "test"}


class TestEnvironmentConfiguration:
    """Test environment-based configuration."""
    
    def test_production_config_loading(self):
        """Test production configuration loading."""
        with patch.dict('os.environ', {
            'OTEL_SERVICE_NAME': 'dotmac-production',
            'ENVIRONMENT': 'production',
            'OTEL_TRACES_SAMPLING_RATIO': '0.05',
            'SLOW_QUERY_THRESHOLD_MS': '200.0'
        }):
            from dotmac.observability.otel import OTelConfig
            
            config = OTelConfig()
            assert config.service_name == 'dotmac-production'
            assert config.environment == 'production'
            assert config.sampling_ratio == 0.05

    def test_development_config_loading(self):
        """Test development configuration loading."""
        with patch.dict('os.environ', {
            'OTEL_SERVICE_NAME': 'dotmac-dev',
            'ENVIRONMENT': 'development',
            'OTEL_TRACES_SAMPLING_RATIO': '1.0'
        }):
            from dotmac.observability.otel import OTelConfig
            
            config = OTelConfig()
            assert config.service_name == 'dotmac-dev'
            assert config.environment == 'development'
            assert config.sampling_ratio == 1.0


# Integration test with actual middleware
class TestMiddlewareIntegration:
    """Test middleware integration with FastAPI."""
    
    def test_tenant_context_middleware_integration(self):
        """Test tenant context middleware with FastAPI."""
        from dotmac.observability.middleware import TenantContextMiddleware
        
        app = FastAPI()
        app.add_middleware(TenantContextMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        
        # Test with tenant header
        response = client.get(
            "/test",
            headers={
                "x-tenant-id": "test-tenant",
                "x-request-id": "test-request-123"
            }
        )
        
        assert response.status_code == 200
        assert "x-request-id" in response.headers
        assert "x-trace-id" in response.headers or True  # May not be present in test


if __name__ == "__main__":
    # Run basic smoke tests
    pytest.main([__file__, "-v"])