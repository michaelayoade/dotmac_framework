"""
Basic usage examples for DotMac Audit API.

This module demonstrates common audit patterns with minimal code.
"""

from dotmac_shared.monitoring import (
    AuditEventType,
    AuditOutcome,
    create_audit_logger,
    init_audit_config,
)


def example_basic_audit_logging():
    """Example of basic audit event logging."""

    # Initialize configuration and logger
    config = init_audit_config()
    audit_logger = create_audit_logger("example-service", "tenant-123")

    # Log authentication event
    audit_logger.log_auth_event(
        event_type=AuditEventType.AUTH_LOGIN,
        actor_id="user@example.com",
        outcome=AuditOutcome.SUCCESS,
        message="User login successful",
    )

    # Log data access
    audit_logger.log_data_access(
        operation="create",
        resource_type="order",
        resource_id="order_456",
        actor_id="user@example.com",
        after_state={"total": 99.99, "status": "pending"},
    )

    # Query recent events
    events = audit_logger.query_events(limit=10)
    print(f"Found {len(events)} audit events")

    return audit_logger


def example_fastapi_integration():
    """Example of FastAPI integration (requires fastapi)."""

    try:
        from fastapi import FastAPI

        from dotmac_shared.monitoring import (
            AuditMiddleware,
            create_audit_api_router,
            init_audit_logger,
        )

        # Initialize audit logger
        audit_logger = init_audit_logger("api-service")

        # Create FastAPI app
        app = FastAPI(title="Audit Example API")

        # Add audit middleware
        app.add_middleware(AuditMiddleware, audit_logger=audit_logger)

        # Include audit API routes
        app.include_router(create_audit_api_router())

        @app.get("/")
        def root():
            return {"message": "API with audit logging"}

        return app

    except ImportError:
        print("FastAPI not available - install with: pip install fastapi")
        return None


if __name__ == "__main__":
    # Run basic example
    example_basic_audit_logging()

    # Show FastAPI integration
    app = example_fastapi_integration()
    if app:
        print("✅ FastAPI app with audit logging created")
        print("💡 Run with: uvicorn basic_usage:app --reload")
    else:
        print("⚠️ FastAPI integration example skipped")
