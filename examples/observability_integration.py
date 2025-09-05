"""
Example: Complete DotMac Framework Observability Integration

This example shows how to integrate the new OpenTelemetry observability stack
with your existing FastAPI application and SigNoz monitoring.

Usage:
    1. Copy .env.observability.example to .env
    2. Configure your SigNoz endpoints
    3. Run: python examples/observability_integration.py
"""

import os
import sys

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Import DotMac observability components
# Business logic imports (example)
from dotmac_management.models.partner import Partner, PartnerCustomer
from dotmac_shared.database.session import create_async_database_engine, get_async_db
from dotmac_shared.observability import get_logger, setup_observability, traced_db_operation

# Initialize FastAPI app
app = FastAPI(
    title="DotMac Observability Example",
    description="Demo of production-ready observability integration",
    version="1.0.0",
)

# Get enhanced logger
logger = get_logger("dotmac.example")


@app.on_event("startup")
async def startup_event():
    """Initialize observability on startup."""
    # Create database engine
    engine = create_async_database_engine()

    # Setup complete observability stack
    setup_observability(app, engine)

    logger.info("Application started with full observability")


# Example API endpoints with observability


@app.get("/health")
async def health_check():
    """Health check endpoint (excluded from tracing)."""
    return {"status": "healthy", "service": "dotmac-example"}


@app.get("/partners")
async def list_partners(
    limit: int = 10,
    db: AsyncSession = Depends(get_async_db),
):
    """List partners with automatic tracing and metrics."""
    logger.info("Fetching partners list", limit=limit)

    try:
        # This query will be automatically traced and monitored
        from sqlalchemy import select

        result = await db.execute(select(Partner).limit(limit))
        partners = result.scalars().all()

        logger.info("Partners fetched successfully", count=len(partners))
        return {"partners": [p.to_dict() for p in partners]}

    except Exception as e:
        logger.error("Failed to fetch partners", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get("/partners/{partner_id}/customers")
async def get_partner_customers(
    partner_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """Get partner customers with custom tracing."""

    # Custom operation tracing
    @traced_db_operation("get_partner_customers")
    async def fetch_partner_customers(session: AsyncSession, pid: str):
        from sqlalchemy import select

        result = await session.execute(select(PartnerCustomer).where(PartnerCustomer.partner_id == pid))
        return result.scalars().all()

    logger.info("Fetching partner customers", partner_id=partner_id)

    try:
        customers = await fetch_partner_customers(db, partner_id)

        # Log business metrics
        from dotmac_shared.observability import record_tenant_operation

        record_tenant_operation(
            operation_type="get_partner_customers",
            duration_ms=50.0,  # Would be calculated in real implementation
            tenant_id=partner_id,
        )

        logger.info("Partner customers retrieved", partner_id=partner_id, customer_count=len(customers))

        return {"customers": [c.to_dict() for c in customers]}

    except Exception as e:
        logger.error("Failed to fetch partner customers", partner_id=partner_id, error=str(e))
        raise HTTPException(status_code=404, detail="Partner not found") from e


@app.post("/partners/{partner_id}/metrics")
async def record_business_metrics(partner_id: str, metrics_data: dict):
    """Example of custom business metrics recording."""
    from dotmac_shared.observability import commission_calculation_counter, get_tracer, partner_customer_counter

    tracer = get_tracer("dotmac.business")

    with tracer.start_as_current_span("record_business_metrics") as span:
        span.set_attribute("partner_id", partner_id)
        span.set_attribute("metrics.type", metrics_data.get("type", "unknown"))

        # Record custom metrics based on business logic
        if metrics_data.get("type") == "commission":
            commission_calculation_counter.add(1, {"partner_id": partner_id, "type": "manual_entry"})

        elif metrics_data.get("type") == "customer_event":
            partner_customer_counter.add(
                1, {"partner_id": partner_id, "event_type": metrics_data.get("event", "unknown")}
            )

        logger.info("Business metrics recorded", partner_id=partner_id, metrics_type=metrics_data.get("type"))

        return {"status": "recorded", "partner_id": partner_id}


@app.get("/debug/trace")
async def debug_trace_context():
    """Debug endpoint to show trace context information."""
    from opentelemetry import baggage, trace

    span = trace.get_current_span()
    span_context = span.get_span_context()

    current_baggage = baggage.get_all()

    return {
        "trace_id": format(span_context.trace_id, "032x") if span_context.is_valid else None,
        "span_id": format(span_context.span_id, "016x") if span_context.is_valid else None,
        "baggage": dict(current_baggage),
        "is_recording": span.is_recording(),
    }


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv(".env.observability.example")

    # Run with uvicorn
    uvicorn.run("observability_integration:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
