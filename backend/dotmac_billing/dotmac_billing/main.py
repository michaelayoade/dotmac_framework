"""
DotMac Billing Service - Main Application
Provides billing, invoicing, payment processing, and financial management.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import config
from .core.exceptions import BillingError

# Import SDKs
from .sdks import (
    InvoiceSDK,
    PaymentSDK,
    TaxSDK,
    CreditSDK,
    MandateSDK,
    RevenueSDK,
    DunningSDK,
    DebtSDK,
    AdjustmentSDK,
    CustomerPaymentPortalSDK,
    PaymentProfileSDK,
    RecurringBillingSDK,
    PrepaidSDK,
    PostpaidSDK,
    UsageSDK,
    PricingSDK,
    DiscountSDK,
    LedgerSDK,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAPI tags metadata
tags_metadata = [
    {
        "name": "Health",
        "description": "Service health and status monitoring",
    },
    {
        "name": "Invoices",
        "description": "Invoice generation, management, and delivery",
    },
    {
        "name": "Payments",
        "description": "Payment processing, methods, and transactions",
    },
    {
        "name": "Subscriptions",
        "description": "Recurring billing and subscription management",
    },
    {
        "name": "Credits",
        "description": "Credit management, limits, and scoring",
    },
    {
        "name": "Taxes",
        "description": "Tax calculation, rates, and compliance",
    },
    {
        "name": "Revenue",
        "description": "Revenue recognition and reporting",
    },
    {
        "name": "Collections",
        "description": "Dunning processes and debt collection",
    },
    {
        "name": "Pricing",
        "description": "Product pricing, plans, and rate cards",
    },
    {
        "name": "Usage",
        "description": "Usage tracking and metered billing",
    },
    {
        "name": "Discounts",
        "description": "Discount rules, promotions, and coupons",
    },
    {
        "name": "Ledger",
        "description": "Financial ledger and accounting entries",
    },
    {
        "name": "Adjustments",
        "description": "Billing adjustments and corrections",
    },
    {
        "name": "Portal",
        "description": "Customer payment portal and self-service",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting DotMac Billing Service...")
    
    # Initialize service components
    logger.info(f"Service initialized with tenant: {config.tenant_id}")
    
    yield
    
    # Cleanup
    logger.info("Shutting down DotMac Billing Service...")


# Create FastAPI application with comprehensive documentation
app = FastAPI(
    title="DotMac Billing Service",
    description="""
    **Enterprise Billing and Revenue Management Service**

    The DotMac Billing Service provides comprehensive billing and financial management for ISPs:

    ## 💰 Core Features

    ### Invoice Management
    - Automated invoice generation
    - Custom invoice templates
    - Multi-currency support
    - PDF generation and delivery
    - Invoice scheduling and batching
    - Credit notes and adjustments

    ### Payment Processing
    - Multiple payment methods (card, bank, wallet)
    - Payment gateway integration
    - Recurring payment management
    - Payment retry logic
    - Refund processing
    - Payment reconciliation

    ### Subscription Billing
    - Flexible billing cycles
    - Plan management
    - Upgrades and downgrades
    - Proration calculations
    - Trial periods
    - Pause and resume functionality

    ### Usage-Based Billing
    - Metered service tracking
    - Usage aggregation
    - Tiered pricing models
    - Overage charges
    - Real-time rating
    - CDR processing

    ### Tax Management
    - Automated tax calculation
    - Multi-jurisdiction support
    - Tax exemptions
    - VAT/GST compliance
    - Tax reporting
    - Rate updates

    ### Credit & Collections
    - Credit limit management
    - Credit scoring
    - Payment terms
    - Dunning workflows
    - Debt collection
    - Write-offs

    ### Revenue Management
    - Revenue recognition
    - Deferred revenue
    - Revenue reporting
    - MRR/ARR tracking
    - Churn analysis
    - Revenue forecasting

    ### Financial Controls
    - General ledger integration
    - Journal entries
    - Account reconciliation
    - Audit trails
    - Financial reporting
    - Compliance management

    ## 🚀 Integration

    - **Database**: PostgreSQL for transaction data
    - **Cache**: Redis for rate calculations
    - **Events**: Real-time billing events
    - **Payment Gateways**: Stripe, PayPal, etc.
    - **Tax Services**: Avalara, TaxJar integration
    - **Accounting**: QuickBooks, SAP integration

    ## 📊 API Standards

    - RESTful API design
    - JSON request/response format
    - Idempotent payment operations
    - Comprehensive error responses
    - Webhook notifications
    - PCI DSS compliance

    **Base URL**: `/api/v1`
    **Version**: 1.0.0
    """,
    version="1.0.0",
    openapi_tags=tags_metadata,
    servers=[
        {
            "url": "/",
            "description": "Current server"
        },
        {
            "url": "https://billing.dotmac.com",
            "description": "Production Billing Service"
        },
        {
            "url": "https://staging-billing.dotmac.com",
            "description": "Staging Billing Service"
        }
    ],
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    contact={
        "name": "DotMac Billing Team",
        "email": "billing-support@dotmac.com",
        "url": "https://docs.dotmac.com/billing",
    },
    lifespan=lifespan,
    docs_url="/docs" if config.debug else None,
    redoc_url="/redoc" if config.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(BillingError)
async def billing_error_handler(request, exc: BillingError):
    """Handle billing-specific errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": str(exc),
            "details": exc.details,
            "request_id": request.headers.get("X-Request-ID"),
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "request_id": request.headers.get("X-Request-ID"),
        }
    )


# Health check endpoint
@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Check service health and dependencies",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "dotmac_billing",
                        "version": "1.0.0",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "dependencies": {
                            "database": "healthy",
                            "redis": "healthy",
                            "payment_gateway": "healthy",
                        }
                    }
                }
            }
        },
        503: {
            "description": "Service is unhealthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "service": "dotmac_billing",
                        "version": "1.0.0",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "dependencies": {
                            "database": "healthy",
                            "redis": "unhealthy",
                            "payment_gateway": "healthy",
                        }
                    }
                }
            }
        }
    }
)
async def health_check() -> Dict[str, Any]:
    """Check service health status."""
    # In production, would check actual dependencies
    return {
        "status": "healthy",
        "service": "dotmac_billing",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "dependencies": {
            "database": "healthy",
            "redis": "healthy",
            "payment_gateway": "healthy",
        }
    }


# API version endpoint
@app.get(
    "/version",
    tags=["Health"],
    summary="Get API version",
    description="Get the current API version and build information",
    responses={
        200: {
            "description": "Version information",
            "content": {
                "application/json": {
                    "example": {
                        "version": "1.0.0",
                        "api_version": "v1",
                        "build_date": "2024-01-15",
                        "git_commit": "abc123def",
                        "features": {
                            "recurring_billing": True,
                            "usage_billing": True,
                            "tax_calculation": True,
                            "multi_currency": True,
                        }
                    }
                }
            }
        }
    }
)
async def get_version() -> Dict[str, Any]:
    """Get API version information."""
    return {
        "version": "1.0.0",
        "api_version": "v1",
        "build_date": "2024-01-15",
        "git_commit": "abc123def",
        "features": {
            "recurring_billing": True,
            "usage_billing": True,
            "tax_calculation": True,
            "multi_currency": True,
        }
    }


# Billing statistics endpoint
@app.get(
    "/stats",
    tags=["Health"],
    summary="Get billing statistics",
    description="Get current billing service statistics and metrics",
    responses={
        200: {
            "description": "Billing statistics",
            "content": {
                "application/json": {
                    "example": {
                        "invoices_today": 1250,
                        "payments_today": 980,
                        "revenue_today": 45670.50,
                        "active_subscriptions": 15420,
                        "pending_payments": 320,
                        "failed_payments": 45,
                    }
                }
            }
        }
    }
)
async def get_stats() -> Dict[str, Any]:
    """Get billing service statistics."""
    # In production, would fetch actual statistics
    return {
        "invoices_today": 1250,
        "payments_today": 980,
        "revenue_today": 45670.50,
        "active_subscriptions": 15420,
        "pending_payments": 320,
        "failed_payments": 45,
    }


# Import and include API routers
# Note: These would be implemented in separate files
# from .api import invoices, payments, subscriptions, taxes, credits, revenue, pricing

# Example router includes (to be implemented):
# app.include_router(invoices.router, prefix="/api/v1/invoices", tags=["Invoices"])
# app.include_router(payments.router, prefix="/api/v1/payments", tags=["Payments"])
# app.include_router(subscriptions.router, prefix="/api/v1/subscriptions", tags=["Subscriptions"])
# app.include_router(taxes.router, prefix="/api/v1/taxes", tags=["Taxes"])
# app.include_router(credits.router, prefix="/api/v1/credits", tags=["Credits"])
# app.include_router(revenue.router, prefix="/api/v1/revenue", tags=["Revenue"])
# app.include_router(pricing.router, prefix="/api/v1/pricing", tags=["Pricing"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "dotmac_billing.main:app",
        host="0.0.0.0",
        port=8002,
        reload=config.debug,
        log_level="info" if not config.debug else "debug",
    )