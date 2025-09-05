"""
DotMac Observability - Convenience Import Aliases

This module provides backward-compatible imports for tests and existing code
that expects dotmac.observability instead of dotmac.platform.observability.
"""
try:
    # Map compatibility functions
    def setup_observability(*args, **kwargs):
        from ..platform.observability import initialize_observability_service

        return initialize_observability_service(*args, **kwargs)

    def get_tracer(*args, **kwargs):
        try:
            from ..platform.observability.tracing import get_tracer as platform_get_tracer

            return platform_get_tracer(*args, **kwargs)
        except ImportError:
            return None

    def get_meter(*args, **kwargs):
        try:
            from ..platform.observability.metrics import MetricsRegistry

            return (
                MetricsRegistry.get_instance()
                if hasattr(MetricsRegistry, "get_instance")
                else MetricsRegistry()
            )
        except ImportError:
            return None

    def get_logger(name=None, *args, **kwargs):
        try:
            from ..platform.observability.logging import LoggingManager

            manager = LoggingManager()
            service_name = name or kwargs.get("service_name", "dotmac-service")
            return manager.get_logger(service_name, *args, **kwargs)
        except ImportError:
            import logging

            return logging.getLogger(name or "dotmac")

    _observability_available = True
except ImportError:
    _observability_available = False

    # Stub implementations for when platform.observability is not available
    def setup_observability(*args, **kwargs):
        """Stub setup_observability function."""
        return {"status": "stub", "message": "Observability not available"}

    def get_tracer(*args, **kwargs):
        """Stub get_tracer function."""

        class StubTracer:
            def start_span(self, *args, **kwargs):
                class StubSpan:
                    def __enter__(self):
                        return self

                    def __exit__(self, *args):
                        pass

                    def set_attribute(self, *args, **kwargs) -> None:
                        pass

                return StubSpan()

        return StubTracer()

    def get_meter(*args, **kwargs):
        """Stub get_meter function."""

        class StubMeter:
            def create_counter(self, *args, **kwargs):
                class StubCounter:
                    def add(self, *args, **kwargs) -> None:
                        pass

                return StubCounter()

            def create_histogram(self, *args, **kwargs):
                class StubHistogram:
                    def record(self, *args, **kwargs) -> None:
                        pass

                return StubHistogram()

        return StubMeter()

    def get_logger(*args, **kwargs):
        """Stub get_logger function."""
        import logging

        return logging.getLogger("dotmac.observability.stub")


# Export common functions
__all__ = ["setup_observability", "get_tracer", "get_meter", "get_logger"]
