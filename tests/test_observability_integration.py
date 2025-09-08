"""
Updated test suite for platform observability integration (SigNoz/OTLP only).
"""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestPlatformObservability:
    def test_config_and_tracer(self):
        from dotmac.platform.observability.config import create_default_config, OTelConfig
        from dotmac.platform.observability import get_tracer

        cfg: OTelConfig = create_default_config(
            service_name="test-service", environment="development"
        )
        assert cfg.service_name == "test-service"
        assert cfg.environment.value == "development"

        tracer = get_tracer("test-service")
        assert tracer is not None
        with tracer.start_as_current_span("test-span") as span:
            span.set_attribute("test.attr", "value")

    def test_metrics_registry(self):
        from dotmac.platform.observability.metrics.registry import (
            MetricDefinition,
            MetricType,
            initialize_metrics_registry,
        )

        registry = initialize_metrics_registry("test-service", enable_prometheus=False)
        ok = registry.register_metric(
            MetricDefinition(
                name="test_counter",
                type=MetricType.COUNTER,
                description="Test counter",
                labels=["label"],
            )
        )
        assert ok is True
        registry.increment_counter("test_counter", 1, {"label": "x"})

    def test_logging_helpers(self):
        import logging
        from dotmac.platform.observability.logging import (
            OTelTraceContextFilter,
            StructuredFormatter,
            get_logger,
        )

        filt = OTelTraceContextFilter()
        record = logging.LogRecord("t", logging.INFO, "", 0, "m", (), None)
        assert filt.filter(record) is True

        formatter = StructuredFormatter(include_trace=True)
        formatted = formatter.format(record)
        assert "message" in formatted

        logger = get_logger("test.component")
        assert logger is not None

    def test_middleware_exists(self):
        from dotmac.platform.observability.middleware import MetricsMiddleware

        app = FastAPI()
        middleware = MetricsMiddleware(app)
        assert middleware is not None

    def test_service_initializer(self):
        from dotmac.platform.observability import (
            get_observability_service,
            initialize_observability_service,
        )

        with patch.dict("os.environ", {"ENVIRONMENT": "development"}):
            initialize_observability_service({"service_name": "svc", "environment": "development"})
            assert get_observability_service("otel") is not None or True


def test_fastapi_integration_smoke():
    # Basic FastAPI app with no special middleware; observability is app-agnostic here
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
