#!/usr/bin/env python3
"""
DotMac Platform Website Backend
Handles payment verification and automatic tenant provisioning
"""

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

# Configuration
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
PAYSTACK_WEBHOOK_SECRET = os.getenv("PAYSTACK_WEBHOOK_SECRET")
HCAPTCHA_SECRET = os.getenv("HCAPTCHA_SECRET_KEY")
MANAGEMENT_API_URL = os.getenv("MANAGEMENT_API_URL", "https://mgmt.yourdomain.com")
MANAGEMENT_SERVICE_TOKEN = os.getenv("MANAGEMENT_SERVICE_TOKEN")
WEBSITE_DOMAIN = os.getenv("WEBSITE_DOMAIN", "yourdomain.com")

app = FastAPI(title="DotMac Platform Website", version="1.0.0")

# CORS for website domain only
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"https://{WEBSITE_DOMAIN}", f"https://www.{WEBSITE_DOMAIN}"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Captcha-Token"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="."), name="static")


@dataclass
class DemoConfig:
    """Demo tenant configuration"""

    ttl_hours: int = 4
    max_per_ip_per_day: int = 3
    features: list = None

    def __post_init__(self):
        if self.features is None:
            self.features = ["basic_billing", "basic_customers", "basic_support"]


class OrderCompleteRequest(BaseModel):
    """Payment completion request from website"""

    paystack_reference: str
    captcha_token: str

    # Tenant details (from checkout metadata)
    company_name: str
    subdomain: str
    admin_name: str
    admin_email: EmailStr
    plan: str = "starter"
    region: str = "us-east-1"


class DemoRequest(BaseModel):
    """Demo tenant request"""

    captcha_token: str
    admin_email: EmailStr
    company_name: str
    subdomain: Optional[str] = None  # Auto-generated if not provided


# In-memory demo tracking (use Redis in production)
DEMO_TRACKING = {}


async def verify_captcha(token: str) -> bool:
    """Verify hCaptcha token"""

    if not HCAPTCHA_SECRET or not token:
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://hcaptcha.com/siteverify", data={"secret": HCAPTCHA_SECRET, "response": token}
            )

            result = response.json()
            return result.get("success", False)

    except Exception as e:
        print(f"Captcha verification failed: {e}")
        return False


async def verify_paystack_transaction(reference: str) -> dict[str, Any]:
    """Verify Paystack transaction and get metadata"""

    if not PAYSTACK_SECRET_KEY:
        raise HTTPException(500, "Paystack not configured")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.paystack.co/transaction/verify/{reference}",
                headers={"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"},
                timeout=30,
            )

            if response.status_code != 200:
                raise HTTPException(400, f"Paystack API error: {response.status_code}")

            result = response.json()

            if not result.get("status"):
                raise HTTPException(400, f"Paystack verification failed: {result.get('message')}")

            data = result.get("data", {})

            if data.get("status") != "success":
                raise HTTPException(400, f"Payment not completed: {data.get('status')}")

            # Extract transaction details
            return {
                "customer_email": data.get("customer", {}).get("email"),
                "amount_paid": data.get("amount", 0) / 100,  # Convert from kobo to naira
                "currency": data.get("currency", "NGN"),
                "metadata": data.get("metadata", {}),
                "reference": data.get("reference"),
                "channel": data.get("channel"),
                "gateway_response": data.get("gateway_response"),
            }

    except httpx.RequestError as e:
        raise HTTPException(500, f"Paystack API unavailable: {e}")


async def call_management_api(endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
    """Call Management Platform API with service token"""

    if not MANAGEMENT_SERVICE_TOKEN:
        raise HTTPException(500, "Management API not configured")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MANAGEMENT_API_URL}{endpoint}",
                json=data,
                headers={
                    "Authorization": f"Bearer {MANAGEMENT_SERVICE_TOKEN}",
                    "Content-Type": "application/json",
                    "X-Service": "website-backend",
                },
                timeout=30,
            )

            if response.status_code not in [200, 201]:
                raise HTTPException(response.status_code, f"Management API error: {response.text}")

            return response.json()

    except httpx.RequestError as e:
        raise HTTPException(500, f"Management API unavailable: {e}")


def get_client_ip(request: Request) -> str:
    """Get client IP address"""
    return (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or request.headers.get("x-real-ip", "")
        or request.client.host
        or "unknown"
    )


def check_demo_rate_limit(ip: str) -> bool:
    """Check if IP has exceeded demo rate limit"""

    today = datetime.now().date()
    key = f"{ip}:{today}"

    if key not in DEMO_TRACKING:
        DEMO_TRACKING[key] = 0

    return DEMO_TRACKING[key] < DemoConfig.max_per_ip_per_day


def track_demo_request(ip: str):
    """Track demo request for rate limiting"""

    today = datetime.now().date()
    key = f"{ip}:{today}"
    DEMO_TRACKING[key] = DEMO_TRACKING.get(key, 0) + 1


@app.get("/", response_class=HTMLResponse)
async def serve_website():
    """Serve main website"""
    with open("index.html") as f:
        return HTMLResponse(f.read())


@app.post("/orders/complete")
async def complete_order(request: OrderCompleteRequest, background_tasks: BackgroundTasks, http_request: Request):
    """
    Complete paid order and automatically provision tenant

    Flow:
    1. Verify captcha
    2. Verify Stripe payment
    3. Call Management API to provision tenant
    4. Return magic link for admin access
    """

    try:
        # Verify captcha
        if not await verify_captcha(request.captcha_token):
            raise HTTPException(400, "Invalid captcha")

        # Verify Paystack payment
        payment_info = await verify_paystack_transaction(request.paystack_reference)

        # Extract plan from payment metadata (set during checkout)
        plan = payment_info["metadata"].get("plan", request.plan)

        # Call Management API to provision tenant
        tenant_data = {
            "company_name": request.company_name,
            "subdomain": request.subdomain,
            "admin_name": request.admin_name,
            "admin_email": request.admin_email,
            "plan": plan,
            "region": request.region,
            "source": "website_purchase",
            "payment_reference": request.paystack_reference,
            "payment_amount": payment_info["amount_paid"],
            "payment_currency": payment_info["currency"],
            "payment_channel": payment_info["channel"],
        }

        result = await call_management_api("/api/v1/tenants", tenant_data)

        tenant_id = result["data"]["tenant_id"]

        return {
            "success": True,
            "message": "Order completed! Your ISP platform is being provisioned.",
            "tenant_id": tenant_id,
            "status_url": f"{MANAGEMENT_API_URL}/api/v1/tenants/{tenant_id}/status",
            "estimated_time": "5-10 minutes",
            "next_steps": [
                "Your platform is being created automatically",
                "You'll receive an email with login details once ready",
                "Check your spam folder if you don't see the email",
                "Login and change your password immediately",
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Order completion failed: {e}")
        raise HTTPException(500, "Order processing failed")


@app.post("/demo/create")
async def create_demo(request: DemoRequest, background_tasks: BackgroundTasks, http_request: Request):
    """
    Create ephemeral demo tenant (4-24 hour TTL)

    Flow:
    1. Verify captcha and rate limiting
    2. Generate demo subdomain
    3. Call Management API with demo configuration
    4. Return instant access details
    """

    try:
        # Get client IP for rate limiting
        client_ip = get_client_ip(http_request)

        # Check rate limiting
        if not check_demo_rate_limit(client_ip):
            raise HTTPException(429, f"Demo limit exceeded. Max {DemoConfig.max_per_ip_per_day} demos per day per IP.")

        # Verify captcha
        if not await verify_captcha(request.captcha_token):
            raise HTTPException(400, "Invalid captcha")

        # Generate demo subdomain if not provided
        subdomain = request.subdomain
        if not subdomain:
            demo_id = secrets.token_hex(3)  # 6 characters
            subdomain = f"demo-{demo_id}"

        # Demo tenant configuration
        demo_config = DemoConfig()

        tenant_data = {
            "company_name": request.company_name,
            "subdomain": subdomain,
            "admin_name": "Demo Admin",
            "admin_email": request.admin_email,
            "plan": "demo",
            "region": "us-east-1",
            "source": "demo_request",
            "enabled_features": demo_config.features,
            "settings": {
                "demo_mode": True,
                "ttl_hours": demo_config.ttl_hours,
                "expires_at": (datetime.utcnow() + timedelta(hours=demo_config.ttl_hours)).isoformat(),
                "demo_restrictions": ["no_email_sends", "no_sms_sends", "no_destructive_ops", "masked_integrations"],
            },
        }

        # Call Management API
        result = await call_management_api("/api/v1/public/signup", tenant_data)

        # Track demo request
        track_demo_request(client_ip)

        tenant_id = result["data"]["tenant_id"]

        return {
            "success": True,
            "message": "Demo created! Your demo ISP platform will be ready in a few minutes.",
            "demo_id": tenant_id,
            "subdomain": subdomain,
            "status_url": f"{MANAGEMENT_API_URL}/api/v1/public/signup/{tenant_id}/status",
            "expires_in": f"{demo_config.ttl_hours} hours",
            "demo_restrictions": [
                "Limited to basic features",
                "No real email/SMS sending",
                "Demo data only - no real customer data",
                f"Expires automatically in {demo_config.ttl_hours} hours",
            ],
            "next_steps": [
                "Check the status URL for provisioning progress",
                "You'll receive login details via email once ready",
                "Explore the platform with pre-loaded demo data",
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Demo creation failed: {e}")
        raise HTTPException(500, "Demo creation failed")


@app.post("/webhooks/paystack")
async def paystack_webhook(request: Request):
    """
    Handle Paystack webhooks for payment verification
    """

    if not PAYSTACK_WEBHOOK_SECRET:
        raise HTTPException(500, "Paystack webhooks not configured")

    try:
        payload = await request.body()
        signature = request.headers.get("x-paystack-signature")

        # Verify webhook signature
        expected_signature = hmac.new(PAYSTACK_WEBHOOK_SECRET.encode("utf-8"), payload, hashlib.sha512).hexdigest()

        if not signature or signature != expected_signature:
            raise HTTPException(400, "Invalid webhook signature")

        event = json.loads(payload)
        event_type = event.get("event")
        data = event.get("data", {})

        # Handle payment success
        if event_type == "charge.success":
            # Enhanced audit logging
            payment_data = {
                "reference": data.get("reference"),
                "amount": data.get("amount", 0) / 100,  # Convert from kobo
                "currency": data.get("currency", "NGN"),
                "customer_email": data.get("customer", {}).get("email"),
                "channel": data.get("channel"),
                "metadata": data.get("metadata", {}),
                "timestamp": datetime.utcnow().isoformat(),
            }

            print(
                f"💰 Payment completed: {payment_data['reference']} - ₦{payment_data['amount']} {payment_data['currency']}"
            )

            # In production, you might want to:
            # 1. Store payment record in database
            # 2. Send confirmation email
            # 3. Trigger additional provisioning steps
            # 4. Update billing system

        elif event_type == "charge.dispute.create":
            print(f"⚠️  Payment dispute created: {data.get('reference')}")

        elif event_type == "transfer.failed":
            print(f"❌ Transfer failed: {data.get('reference')} - {data.get('reason')}")

        elif event_type == "subscription.create":
            print(f"🔄 Subscription created: {data.get('subscription_code')}")

        return {"received": True}

    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON payload")
    except Exception as e:
        print(f"Webhook processing error: {e}")
        raise HTTPException(500, "Webhook processing failed")


@app.get("/health")
async def health_check():
    """Health check endpoint"""

    return {
        "status": "healthy",
        "service": "dotmac-website-backend",
        "timestamp": datetime.utcnow().isoformat(),
        "integrations": {
            "paystack": bool(PAYSTACK_SECRET_KEY),
            "hcaptcha": bool(HCAPTCHA_SECRET),
            "management_api": bool(MANAGEMENT_SERVICE_TOKEN),
        },
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")

    print(
        f"""
🌐 DotMac Platform Website Backend
==================================

Starting server at: http://{host}:{port}
Management API: {MANAGEMENT_API_URL}

Features enabled:
• Payment processing: {'✅' if PAYSTACK_SECRET_KEY else '❌'} Paystack
• Captcha verification: {'✅' if HCAPTCHA_SECRET else '❌'} hCaptcha
• Management API: {'✅' if MANAGEMENT_SERVICE_TOKEN else '❌'} Token auth
• Demo provisioning: ✅ 4-hour TTL

Endpoints:
• POST /orders/complete - Payment → Auto provision
• POST /demo/create - Instant demo creation
• POST /webhooks/paystack - Payment verification
• GET /health - Health check

Press Ctrl+C to stop
"""
    )

    uvicorn.run("backend:app", host=host, port=port, reload=False)
