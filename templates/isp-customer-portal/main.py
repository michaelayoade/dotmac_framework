from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from dotmac_communications import SupportChatService
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from portal import (
    BillingPortal,
    Dashboard,
    NetworkPortal,
    ServicesPortal,
    SupportPortal,
)
from pydantic import BaseModel
from services import BillingServiceLocal, CustomerServiceLocal, SupportServiceLocal

from dotmac_billing import InvoiceService, PaymentService, UsageService
from dotmac_identity import AuthService, CustomerService
from dotmac_networking import DiagnosticsService, OutageService
from dotmac_services import ServiceManagementService


app = FastAPI(title="DotMac Customer Portal")

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# External service clients
customer_service = CustomerService()
auth_service = AuthService()
invoice_service = InvoiceService()
payment_service = PaymentService()
usage_service = UsageService()
service_mgmt = ServiceManagementService()
diagnostics_service = DiagnosticsService()
outage_service = OutageService()
support_chat = SupportChatService()

# Portal components
dashboard = Dashboard()
billing_portal = BillingPortal()
services_portal = ServicesPortal()
support_portal = SupportPortal()
network_portal = NetworkPortal()

# Local services
customer_svc = CustomerServiceLocal()
billing_svc = BillingServiceLocal()
support_svc = SupportServiceLocal()

class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[Dict[str, str]] = None
    notification_preferences: Optional[Dict[str, bool]] = None

class PaymentRequest(BaseModel):
    amount: float
    payment_method_id: str
    invoice_id: Optional[str] = None

class ServiceChangeRequest(BaseModel):
    service_id: str
    new_plan: str
    effective_date: Optional[datetime] = None
    reason: Optional[str] = None

class SupportTicketCreate(BaseModel):
    subject: str
    description: str
    category: str  # billing, technical, service
    priority: str = "normal"  # low, normal, high, urgent
    attachments: Optional[List[str]] = None

class NotificationPreferences(BaseModel):
    email_billing: bool = True
    email_service: bool = True
    email_marketing: bool = False
    sms_outages: bool = True
    sms_billing: bool = False

# Dashboard & Overview
@app.get("/dashboard", response_class=HTMLResponse)
async def customer_dashboard(
    request: Request,
    customer_id: str = Depends(get_current_customer)
):
    """Customer overview dashboard"""
    dashboard_data = await dashboard.get_overview(customer_id)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "customer": dashboard_data["customer"],
        "services": dashboard_data["services"],
        "recent_invoices": dashboard_data["recent_invoices"],
        "usage_summary": dashboard_data["usage_summary"],
        "notifications": dashboard_data["notifications"]
    })

@app.get("/account")
async def get_account_info(customer_id: str = Depends(get_current_customer)):
    """Get customer account information"""
    customer = await customer_service.get_customer(customer_id)

    return {
        "customer": customer,
        "notification_preferences": await customer_svc.get_notification_preferences(customer_id),
        "payment_methods": await payment_service.get_customer_payment_methods(customer_id)
    }

@app.put("/account/profile")
async def update_profile(
    profile_data: ProfileUpdate,
    customer_id: str = Depends(get_current_customer)
):
    """Update customer profile"""
    try:
        updated_customer = await customer_service.update_customer(
            customer_id,
            profile_data.dict(exclude_none=True)
        )

        return {"status": "updated", "customer": updated_customer}

    except Exception as e:
        raise HTTPException(500, f"Failed to update profile: {e!s}")

# Billing & Payments
@app.get("/billing/invoices", response_class=HTMLResponse)
async def billing_invoices(
    request: Request,
    customer_id: str = Depends(get_current_customer),
    limit: int = 12
):
    """Invoice history page"""
    invoices = await invoice_service.get_customer_invoices(customer_id, limit=limit)

    return templates.TemplateResponse("billing.html", {
        "request": request,
        "invoices": invoices,
        "customer_id": customer_id
    })

@app.get("/billing/usage")
async def get_usage_details(
    customer_id: str = Depends(get_current_customer),
    service_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Get detailed usage information"""
    if not start_date:
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
    if not end_date:
        end_date = datetime.now(timezone.utc)

    usage_data = await usage_service.get_customer_usage(
        customer_id,
        service_id,
        start_date,
        end_date
    )

    return {
        "usage": usage_data,
        "period": {"start": start_date, "end": end_date},
        "summary": await usage_service.get_usage_summary(customer_id)
    }

@app.post("/billing/payments")
async def make_payment(
    payment_request: PaymentRequest,
    customer_id: str = Depends(get_current_customer)
):
    """Process customer payment"""
    try:
        # Process payment through billing plane
        payment_result = await payment_service.process_payment({
            "customer_id": customer_id,
            "amount": payment_request.amount,
            "payment_method_id": payment_request.payment_method_id,
            "invoice_id": payment_request.invoice_id
        })

        return {
            "payment_id": payment_result["payment_id"],
            "status": payment_result["status"],
            "receipt_url": payment_result.get("receipt_url")
        }

    except Exception as e:
        raise HTTPException(500, f"Payment failed: {e!s}")

@app.put("/billing/autopay")
async def setup_autopay(
    payment_method_id: str,
    customer_id: str = Depends(get_current_customer)
):
    """Setup automatic payments"""
    try:
        autopay_result = await payment_service.setup_autopay(
            customer_id,
            payment_method_id
        )

        return {"status": "enabled", "autopay_id": autopay_result["autopay_id"]}

    except Exception as e:
        raise HTTPException(500, f"Autopay setup failed: {e!s}")

@app.get("/billing/statements")
async def download_statements(
    customer_id: str = Depends(get_current_customer),
    year: Optional[int] = None,
    month: Optional[int] = None
):
    """Download billing statements"""
    statements = await billing_svc.get_statements(customer_id, year, month)

    return {"statements": statements}

# Service Management
@app.get("/services", response_class=HTMLResponse)
async def customer_services(
    request: Request,
    customer_id: str = Depends(get_current_customer)
):
    """Active services page"""
    services = await service_mgmt.get_customer_services(customer_id)
    available_upgrades = await services_portal.get_available_upgrades(customer_id)

    return templates.TemplateResponse("services.html", {
        "request": request,
        "services": services,
        "available_upgrades": available_upgrades
    })

@app.post("/services/upgrade")
async def request_service_upgrade(
    upgrade_request: ServiceChangeRequest,
    customer_id: str = Depends(get_current_customer)
):
    """Request service upgrade"""
    try:
        # Validate upgrade eligibility
        eligibility = await services_portal.check_upgrade_eligibility(
            customer_id,
            upgrade_request.service_id,
            upgrade_request.new_plan
        )

        if not eligibility["eligible"]:
            raise HTTPException(400, f"Upgrade not allowed: {eligibility['reason']}")

        # Submit upgrade request
        upgrade_result = await service_mgmt.request_service_change({
            "customer_id": customer_id,
            "service_id": upgrade_request.service_id,
            "change_type": "upgrade",
            "new_plan": upgrade_request.new_plan,
            "effective_date": upgrade_request.effective_date,
            "reason": upgrade_request.reason
        })

        return {
            "request_id": upgrade_result["request_id"],
            "status": "pending_approval",
            "effective_date": upgrade_result["effective_date"]
        }

    except Exception as e:
        raise HTTPException(500, f"Upgrade request failed: {e!s}")

@app.post("/services/downgrade")
async def request_service_downgrade(
    downgrade_request: ServiceChangeRequest,
    customer_id: str = Depends(get_current_customer)
):
    """Request service downgrade"""
    try:
        downgrade_result = await service_mgmt.request_service_change({
            "customer_id": customer_id,
            "service_id": downgrade_request.service_id,
            "change_type": "downgrade",
            "new_plan": downgrade_request.new_plan,
            "effective_date": downgrade_request.effective_date,
            "reason": downgrade_request.reason
        })

        return {
            "request_id": downgrade_result["request_id"],
            "status": "pending_approval",
            "effective_date": downgrade_result["effective_date"]
        }

    except Exception as e:
        raise HTTPException(500, f"Downgrade request failed: {e!s}")

@app.put("/services/{service_id}/suspend")
async def suspend_service(
    service_id: str,
    suspension_reason: str,
    customer_id: str = Depends(get_current_customer)
):
    """Suspend service (vacation hold, etc.)"""
    try:
        suspension_result = await service_mgmt.suspend_service({
            "customer_id": customer_id,
            "service_id": service_id,
            "reason": suspension_reason,
            "requested_by": "customer"
        })

        return {
            "suspension_id": suspension_result["suspension_id"],
            "status": "suspended",
            "reactivation_date": suspension_result.get("reactivation_date")
        }

    except Exception as e:
        raise HTTPException(500, f"Service suspension failed: {e!s}")

@app.get("/services/{service_id}/usage")
async def get_service_usage(
    service_id: str,
    customer_id: str = Depends(get_current_customer),
    days: int = 30
):
    """Get usage details for specific service"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    end_date = datetime.now(timezone.utc)

    usage_data = await usage_service.get_service_usage(
        service_id,
        start_date,
        end_date
    )

    return {
        "service_id": service_id,
        "usage": usage_data,
        "period_days": days
    }

# Support & Messaging
@app.get("/support/tickets", response_class=HTMLResponse)
async def support_tickets(
    request: Request,
    customer_id: str = Depends(get_current_customer)
):
    """Support tickets page"""
    tickets = await support_svc.get_customer_tickets(customer_id)

    return templates.TemplateResponse("support.html", {
        "request": request,
        "tickets": tickets,
        "customer_id": customer_id
    })

@app.post("/support/tickets")
async def create_support_ticket(
    ticket_data: SupportTicketCreate,
    customer_id: str = Depends(get_current_customer)
):
    """Create new support ticket"""
    try:
        ticket = await support_svc.create_ticket({
            **ticket_data.dict(),
            "customer_id": customer_id,
            "source": "customer_portal"
        })

        return {
            "ticket_id": ticket.id,
            "ticket_number": ticket.number,
            "status": "open"
        }

    except Exception as e:
        raise HTTPException(500, f"Failed to create ticket: {e!s}")

@app.get("/support/tickets/{ticket_id}")
async def get_ticket_details(
    ticket_id: str,
    customer_id: str = Depends(get_current_customer)
):
    """Get support ticket details"""
    ticket = await support_svc.get_ticket(ticket_id)

    # Verify ownership
    if ticket.customer_id != customer_id:
        raise HTTPException(404, "Ticket not found")

    return {
        "ticket": ticket,
        "messages": await support_svc.get_ticket_messages(ticket_id)
    }

@app.post("/support/tickets/{ticket_id}/reply")
async def reply_to_ticket(
    ticket_id: str,
    message: str,
    customer_id: str = Depends(get_current_customer)
):
    """Reply to support ticket"""
    try:
        # Verify ticket ownership
        ticket = await support_svc.get_ticket(ticket_id)
        if ticket.customer_id != customer_id:
            raise HTTPException(404, "Ticket not found")

        reply = await support_svc.add_ticket_message({
            "ticket_id": ticket_id,
            "message": message,
            "sender_type": "customer",
            "sender_id": customer_id
        })

        return {"message_id": reply.id, "status": "sent"}

    except Exception as e:
        raise HTTPException(500, f"Failed to send reply: {e!s}")

@app.get("/support/chat")
async def get_live_chat(customer_id: str = Depends(get_current_customer)):
    """Get live chat session"""
    chat_session = await support_chat.get_or_create_session(customer_id)

    return {
        "session_id": chat_session["session_id"],
        "status": chat_session["status"],
        "agent_available": chat_session.get("agent_available", False)
    }

# Network & Diagnostics
@app.get("/network/status")
async def get_connection_status(customer_id: str = Depends(get_current_customer)):
    """Get network connection status"""
    # Get customer services
    services = await service_mgmt.get_customer_services(customer_id)
    network_services = [s for s in services if s.service_type == "broadband"]

    status_data = []
    for service in network_services:
        status = await diagnostics_service.get_connection_status(service.id)
        status_data.append({
            "service_id": service.id,
            "service_name": service.name,
            "status": status["status"],
            "last_online": status.get("last_online"),
            "ip_address": status.get("ip_address")
        })

    return {"connections": status_data}

@app.post("/network/speedtest")
async def run_speed_test(
    service_id: str,
    customer_id: str = Depends(get_current_customer)
):
    """Initiate speed test for service"""
    try:
        # Verify service ownership
        service = await service_mgmt.get_service(service_id)
        if service.customer_id != customer_id:
            raise HTTPException(404, "Service not found")

        speedtest_result = await diagnostics_service.run_speed_test(service_id)

        return {
            "test_id": speedtest_result["test_id"],
            "status": "running",
            "estimated_duration": "60 seconds"
        }

    except Exception as e:
        raise HTTPException(500, f"Speed test failed: {e!s}")

@app.get("/network/outages")
async def get_known_outages(customer_id: str = Depends(get_current_customer)):
    """Get known outages affecting customer"""
    customer = await customer_service.get_customer(customer_id)
    outages = await outage_service.get_outages_for_area(customer.service_address)

    return {
        "outages": outages,
        "affected_services": await outage_service.get_affected_services(customer_id)
    }

@app.post("/network/troubleshoot")
async def run_diagnostics(
    service_id: str,
    issue_type: str,
    customer_id: str = Depends(get_current_customer)
):
    """Run diagnostic tools"""
    try:
        # Verify service ownership
        service = await service_mgmt.get_service(service_id)
        if service.customer_id != customer_id:
            raise HTTPException(404, "Service not found")

        diagnostic_result = await diagnostics_service.run_diagnostics({
            "service_id": service_id,
            "issue_type": issue_type,
            "initiated_by": "customer"
        })

        return {
            "diagnostic_id": diagnostic_result["diagnostic_id"],
            "results": diagnostic_result["results"],
            "recommendations": diagnostic_result.get("recommendations", [])
        }

    except Exception as e:
        raise HTTPException(500, f"Diagnostics failed: {e!s}")

# Notifications & Alerts
@app.get("/notifications")
async def get_notifications(
    customer_id: str = Depends(get_current_customer),
    unread_only: bool = False,
    limit: int = 50
):
    """Get customer notifications"""
    filters = {"customer_id": customer_id}
    if unread_only:
        filters["read"] = False

    notifications = await customer_svc.get_notifications(filters, limit)

    return {
        "notifications": notifications,
        "unread_count": await customer_svc.get_unread_count(customer_id)
    }

@app.put("/notifications/preferences")
async def update_notification_preferences(
    preferences: NotificationPreferences,
    customer_id: str = Depends(get_current_customer)
):
    """Update notification preferences"""
    try:
        updated_prefs = await customer_svc.update_notification_preferences(
            customer_id,
            preferences.dict()
        )

        return {"status": "updated", "preferences": updated_prefs}

    except Exception as e:
        raise HTTPException(500, f"Failed to update preferences: {e!s}")

@app.post("/notifications/mark-read")
async def mark_notifications_read(
    notification_ids: List[str],
    customer_id: str = Depends(get_current_customer)
):
    """Mark notifications as read"""
    await customer_svc.mark_notifications_read(customer_id, notification_ids)

    return {"status": "marked_read", "count": len(notification_ids)}

# Authentication helper (simplified)
async def get_current_customer() -> str:
    """Get current authenticated customer ID"""
    # This would integrate with your auth system
    return "customer_123"  # Placeholder

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "customer-portal"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
