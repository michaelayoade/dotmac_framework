#!/usr/bin/env python3
"""
DotMac API Gateway Service with Full SignOz/OpenTelemetry Instrumentation
Example of comprehensive observability integration.
"""

import os
import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel

# Import observability
from dotmac_sdk_core.observability import (
    init_telemetry,
    get_telemetry,
    trace_method,
    record_event
)

# Initialize telemetry
telemetry = init_telemetry(
    service_name="dotmac-api-gateway",
    service_version="1.0.0",
    environment=os.getenv("ENVIRONMENT", "development"),
    otel_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
    custom_attributes={
        "service.type": "gateway",
        "service.framework": "fastapi",
        "deployment.region": os.getenv("REGION", "us-east-1")
    }
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with telemetry."""
    # Startup
    with telemetry.span("app.startup") as span:
        span.set_attribute("app.name", "api-gateway")
        span.add_event("Initializing service dependencies")
        
        # Initialize database connections, caches, etc.
        await initialize_dependencies()
        
        # Record startup event
        record_event(
            "service_started",
            tenant_id="system",
            attributes={"service": "api-gateway"}
        )
        
        print("API Gateway started with SignOz instrumentation")
    
    yield
    
    # Shutdown
    with telemetry.span("app.shutdown") as span:
        span.add_event("Shutting down service")
        
        # Cleanup resources
        await cleanup_dependencies()
        
        # Shutdown telemetry
        telemetry.shutdown()
        
        print("API Gateway shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="DotMac API Gateway with SignOz",
    description="Fully instrumented API Gateway",
    version="1.0.0",
    lifespan=lifespan
)

# Instrument FastAPI with OpenTelemetry
telemetry.instrument_fastapi(app)
telemetry.instrument_httpx()
telemetry.instrument_asyncio()


# Custom middleware for request tracking
@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    """Add observability context to all requests."""
    start_time = time.time()
    
    # Extract request metadata
    tenant_id = request.headers.get("X-Tenant-ID", "default")
    user_id = request.headers.get("X-User-ID", "anonymous")
    request_id = request.headers.get("X-Request-ID", generate_request_id())
    
    # Set baggage for distributed context
    from opentelemetry import baggage
    ctx = baggage.set_baggage("tenant_id", tenant_id)
    ctx = baggage.set_baggage("user_id", user_id, ctx)
    ctx = baggage.set_baggage("request_id", request_id, ctx)
    
    # Add to current span
    telemetry.set_span_attribute("tenant.id", tenant_id)
    telemetry.set_span_attribute("user.id", user_id)
    telemetry.set_span_attribute("request.id", request_id)
    
    try:
        # Process request
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        telemetry.request_duration.labels(
            service="api-gateway",
            method=request.method,
            endpoint=request.url.path,
            tenant_id=tenant_id
        ).observe(duration)
        
        telemetry.request_counter.labels(
            service="api-gateway",
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
            tenant_id=tenant_id
        ).inc()
        
        # Add response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.3f}"
        
        return response
        
    except Exception as e:
        # Record error
        telemetry.get_current_span().record_exception(e)
        
        telemetry.request_counter.labels(
            service="api-gateway",
            method=request.method,
            endpoint=request.url.path,
            status=500,
            tenant_id=tenant_id
        ).inc()
        
        raise


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint with dependency checks."""
    with telemetry.span("health_check") as span:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "api-gateway",
            "version": "1.0.0",
            "checks": {}
        }
        
        # Check database
        db_healthy = await check_database_health()
        health_status["checks"]["database"] = "healthy" if db_healthy else "unhealthy"
        span.set_attribute("health.database", db_healthy)
        
        # Check Redis
        redis_healthy = await check_redis_health()
        health_status["checks"]["redis"] = "healthy" if redis_healthy else "unhealthy"
        span.set_attribute("health.redis", redis_healthy)
        
        # Check downstream services
        services_healthy = await check_services_health()
        health_status["checks"]["services"] = "healthy" if services_healthy else "degraded"
        span.set_attribute("health.services", services_healthy)
        
        # Determine overall health
        if not (db_healthy and redis_healthy):
            health_status["status"] = "unhealthy"
            span.set_attribute("health.overall", "unhealthy")
            return JSONResponse(status_code=503, content=health_status)
        
        if not services_healthy:
            health_status["status"] = "degraded"
            span.set_attribute("health.overall", "degraded")
        
        span.set_attribute("health.overall", health_status["status"])
        return health_status


# Example business endpoint with tracing
class PaymentRequest(BaseModel):
    tenant_id: str
    amount: float
    currency: str = "USD"
    payment_method: str = "credit_card"


@app.post("/api/v1/payments")
@trace_method("process_payment")
async def process_payment(payment: PaymentRequest):
    """Process payment with comprehensive observability."""
    with telemetry.span("payment.validation") as span:
        span.set_attribute("payment.amount", payment.amount)
        span.set_attribute("payment.currency", payment.currency)
        span.set_attribute("payment.method", payment.payment_method)
        
        # Validate payment
        if payment.amount <= 0:
            span.set_attribute("validation.error", "Invalid amount")
            raise HTTPException(status_code=400, detail="Invalid payment amount")
        
        span.add_event("Payment validated")
    
    with telemetry.span("payment.fraud_check") as span:
        # Simulate fraud check
        await asyncio.sleep(0.1)  # Simulate API call
        fraud_score = 0.2  # Mock score
        
        span.set_attribute("fraud.score", fraud_score)
        span.add_event("Fraud check completed", {"score": fraud_score})
        
        if fraud_score > 0.8:
            span.set_attribute("fraud.blocked", True)
            record_event(
                "payment_blocked",
                tenant_id=payment.tenant_id,
                status="fraud_detected",
                attributes={"amount": payment.amount}
            )
            raise HTTPException(status_code=403, detail="Payment blocked")
    
    with telemetry.span("payment.processing") as span:
        # Process payment
        await asyncio.sleep(0.2)  # Simulate processing
        
        transaction_id = generate_transaction_id()
        span.set_attribute("transaction.id", transaction_id)
        
        # Record business event
        record_event(
            "payment_processed",
            tenant_id=payment.tenant_id,
            status="success",
            attributes={
                "amount": payment.amount,
                "currency": payment.currency,
                "transaction_id": transaction_id
            }
        )
        
        span.add_event("Payment processed successfully")
        
        return {
            "status": "success",
            "transaction_id": transaction_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "timestamp": datetime.utcnow().isoformat()
        }


# Circuit breaker example with observability
class CircuitBreakerService:
    """Service with circuit breaker pattern and observability."""
    
    def __init__(self):
        self.failure_count = 0
        self.failure_threshold = 5
        self.is_open = False
        self.last_failure_time = None
    
    @trace_method("external_api_call")
    async def call_external_api(self, endpoint: str):
        """Call external API with circuit breaker."""
        if self.is_open:
            if time.time() - self.last_failure_time > 60:  # 60 second timeout
                self.is_open = False
                self.failure_count = 0
                telemetry.add_span_event("Circuit breaker reset")
            else:
                telemetry.set_span_attribute("circuit_breaker.state", "open")
                raise HTTPException(status_code=503, detail="Service temporarily unavailable")
        
        try:
            # Simulate API call
            with telemetry.span("http.request", attributes={"http.url": endpoint}):
                await asyncio.sleep(0.1)
                
                # Simulate occasional failures
                import random
                if random.random() < 0.1:
                    raise Exception("API call failed")
                
                return {"data": "success"}
                
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            telemetry.set_span_attribute("circuit_breaker.failures", self.failure_count)
            
            if self.failure_count >= self.failure_threshold:
                self.is_open = True
                telemetry.add_span_event("Circuit breaker opened")
                record_event(
                    "circuit_breaker_opened",
                    tenant_id="system",
                    status="open",
                    attributes={"service": endpoint}
                )
            
            raise


circuit_breaker = CircuitBreakerService()


@app.get("/api/v1/external")
async def call_external_service():
    """Endpoint demonstrating circuit breaker with observability."""
    return await circuit_breaker.call_external_api("https://api.example.com/data")


# Batch processing with observability
@app.post("/api/v1/batch")
async def process_batch(items: list):
    """Process batch of items with detailed tracing."""
    with telemetry.span("batch.processing") as span:
        span.set_attribute("batch.size", len(items))
        span.add_event("Batch processing started")
        
        results = []
        errors = []
        
        for i, item in enumerate(items):
            with telemetry.span(f"batch.item.{i}") as item_span:
                item_span.set_attribute("item.index", i)
                item_span.set_attribute("item.id", item.get("id"))
                
                try:
                    # Process item
                    await asyncio.sleep(0.01)  # Simulate processing
                    results.append({"id": item.get("id"), "status": "success"})
                    
                except Exception as e:
                    item_span.record_exception(e)
                    errors.append({"id": item.get("id"), "error": str(e)})
        
        span.set_attribute("batch.success_count", len(results))
        span.set_attribute("batch.error_count", len(errors))
        span.add_event("Batch processing completed")
        
        # Record batch metrics
        record_event(
            "batch_processed",
            tenant_id="system",
            status="completed",
            attributes={
                "total": len(items),
                "success": len(results),
                "errors": len(errors)
            }
        )
        
        return {
            "processed": len(results),
            "errors": len(errors),
            "results": results,
            "error_details": errors
        }


# WebSocket with observability
from fastapi import WebSocket
import json


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint with tracing."""
    await websocket.accept()
    
    connection_id = generate_request_id()
    
    with telemetry.span("websocket.connection") as span:
        span.set_attribute("connection.id", connection_id)
        span.set_attribute("connection.type", "websocket")
        
        # Update active connections gauge
        telemetry.set_connection_gauge("websocket", 1)
        
        try:
            while True:
                # Receive message
                data = await websocket.receive_text()
                
                with telemetry.span("websocket.message") as msg_span:
                    msg_span.set_attribute("message.size", len(data))
                    
                    # Process message
                    response = {"echo": data, "timestamp": time.time()}
                    
                    # Send response
                    await websocket.send_json(response)
                    
                    msg_span.add_event("Message processed")
                    
        except Exception as e:
            span.record_exception(e)
        finally:
            telemetry.set_connection_gauge("websocket", 0)


# Helper functions
async def initialize_dependencies():
    """Initialize service dependencies."""
    # Initialize database, cache, etc.
    await asyncio.sleep(0.1)  # Simulate initialization


async def cleanup_dependencies():
    """Cleanup service dependencies."""
    # Close connections, flush buffers, etc.
    await asyncio.sleep(0.1)  # Simulate cleanup


async def check_database_health() -> bool:
    """Check database health."""
    await asyncio.sleep(0.01)  # Simulate check
    return True


async def check_redis_health() -> bool:
    """Check Redis health."""
    await asyncio.sleep(0.01)  # Simulate check
    return True


async def check_services_health() -> bool:
    """Check downstream services health."""
    await asyncio.sleep(0.01)  # Simulate check
    return True


def generate_request_id() -> str:
    """Generate unique request ID."""
    import uuid
    return str(uuid.uuid4())


def generate_transaction_id() -> str:
    """Generate unique transaction ID."""
    import uuid
    return f"TXN-{uuid.uuid4().hex[:12].upper()}"


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - [%(trace_id)s] - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        }
    )