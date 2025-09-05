from datetime import datetime
from typing import Any, Optional

from dotmac_analytics import AnalyticsClient
from dotmac_billing import CommissionService, PricingService
from dotmac_communications import CommunicationsClient
from dotmac_identity import CustomerService, ResellerService
from dotmac_services import ProvisioningService
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from portal import CustomerManagement, ResellerDashboard, WhiteLabelPortal
from pydantic import BaseModel
from services import (
    CommissionServiceLocal,
    ProvisioningServiceLocal,
    ResellerServiceLocal,
)

app = FastAPI(title="DotMac Reseller Portal")

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# External service clients
reseller_service = ResellerService()
customer_service = CustomerService()
commission_service = CommissionService()
pricing_service = PricingService()
provisioning_service = ProvisioningService()
analytics_client = AnalyticsClient()
communications_client = CommunicationsClient()

# Portal components
dashboard = ResellerDashboard()
customer_mgmt = CustomerManagement()
white_label = WhiteLabelPortal()

# Local services
reseller_svc = ResellerServiceLocal()
commission_svc = CommissionServiceLocal()
provisioning_svc = ProvisioningServiceLocal()


class ResellerCreate(BaseModel):
    company_name: str
    contact_name: str
    email: str
    phone: str
    address: dict[str, str]
    tier: str = "bronze"  # bronze, silver, gold, platinum
    commission_rate: float = 0.10
    white_label_enabled: bool = False


class CustomerCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    address: dict[str, str]
    service_plan: str
    reseller_reference: Optional[str] = None


class ServiceProvisionRequest(BaseModel):
    customer_id: str
    service_type: str  # broadband, voip, hosting
    plan: str
    installation_address: dict[str, str]
    requested_date: Optional[datetime] = None


class WhiteLabelUpdate(BaseModel):
    primary_color: str
    secondary_color: str
    logo_url: Optional[str] = None
    company_name: str
    domain: Optional[str] = None
    custom_css: Optional[str] = None


# Reseller Management
@app.post("/resellers")
async def create_reseller(reseller_data: ResellerCreate):
    """Onboard new partner/reseller"""
    try:
        # Create reseller in identity plane
        reseller = await reseller_service.create_reseller(reseller_data.model_dump())

        # Set up commission structure
        await commission_service.setup_reseller_commissions(
            reseller.id, reseller_data.tier, reseller_data.commission_rate
        )

        # Initialize white-label if enabled
        if reseller_data.white_label_enabled:
            await white_label.initialize_portal(
                reseller.id,
                {"company_name": reseller_data.company_name, "primary_color": "#007bff", "secondary_color": "#6c757d"},
            )

        # Send welcome communications
        await communications_client.send_notification(
            {
                "channel": "email",
                "to": reseller_data.email,
                "template": "reseller_welcome",
                "data": {
                    "company_name": reseller_data.company_name,
                    "login_url": f"/portal/{reseller.id}",
                    "tier": reseller_data.tier,
                },
            }
        )

        # Track analytics
        await analytics_client.track_event(
            "reseller_onboarded",
            {"reseller_id": reseller.id, "tier": reseller_data.tier, "white_label": reseller_data.white_label_enabled},
        )

        return {"reseller_id": reseller.id, "portal_url": f"/portal/{reseller.id}", "status": "created"}

    except Exception as e:
        raise HTTPException(500, f"Failed to create reseller: {e!s}") from e


@app.get("/resellers/me")
async def get_reseller_profile(reseller_id: str = Depends(get_current_reseller)):
    """Get current reseller profile"""
    reseller = await reseller_service.get_reseller(reseller_id)

    # Get additional metrics
    metrics = await analytics_client.get_reseller_metrics(reseller_id)

    return {
        "reseller": reseller,
        "metrics": {
            "total_customers": metrics["customer_count"],
            "monthly_revenue": metrics["mrr"],
            "commission_earned": metrics["total_commission"],
        },
    }


@app.put("/resellers/me/branding")
async def update_white_label_config(
    config: WhiteLabelUpdate,
    reseller_id: str = Depends(get_current_reseller),
):
    """Update white-label portal configuration"""
    try:
        updated_config = await white_label.update_branding(reseller_id, config.model_dump())

        # Track branding update
        await analytics_client.track_event(
            "white_label_updated", {"reseller_id": reseller_id, "has_custom_domain": bool(config.domain)}
        )

        return {"status": "updated", "config": updated_config}

    except Exception as e:
        raise HTTPException(500, f"Failed to update branding: {e!s}") from e


@app.get("/resellers/hierarchy")
async def get_reseller_hierarchy(reseller_id: str = Depends(get_current_reseller)):
    """Get sub-reseller hierarchy"""
    hierarchy = await reseller_svc.get_hierarchy(reseller_id)
    return {"hierarchy": hierarchy}


# Customer Management (on behalf)
@app.post("/customers")
async def create_customer_for_reseller(
    customer_data: CustomerCreate,
    reseller_id: str = Depends(get_current_reseller),
):
    """Create customer on behalf of reseller"""
    try:
        # Create customer with reseller association
        customer = await customer_service.create_customer(
            {**customer_data.model_dump(), "reseller_id": reseller_id, "created_by": "reseller"}
        )

        # Set up commission tracking for this customer
        await commission_service.setup_customer_commission(customer.id, reseller_id)

        # Provision initial service if specified
        if customer_data.service_plan:
            provision_result = await provisioning_svc.provision_service(
                {"customer_id": customer.id, "reseller_id": reseller_id, "service_plan": customer_data.service_plan}
            )

        # Track customer creation
        await analytics_client.track_event(
            "reseller_customer_created",
            {"reseller_id": reseller_id, "customer_id": customer.id, "service_plan": customer_data.service_plan},
        )

        return {
            "customer_id": customer.id,
            "provision_id": provision_result.get("provision_id") if customer_data.service_plan else None,
            "status": "created",
        }

    except Exception as e:
        raise HTTPException(500, f"Failed to create customer: {e!s}") from e


@app.get("/customers")
async def list_reseller_customers(
    reseller_id: str = Depends(get_current_reseller),
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List customers for this reseller"""
    filters = {"reseller_id": reseller_id}
    if status:
        filters["status"] = status

    customers = await customer_service.list_customers(filters, limit, offset)

    # Get revenue data for each customer
    customer_data = []
    for customer in customers:
        revenue = await analytics_client.get_customer_revenue(customer.id)
        customer_data.append({**customer.model_dump(), "mrr": revenue["mrr"], "total_revenue": revenue["total"]})

    return {"customers": customer_data}


@app.post("/customers/{customer_id}/services")
async def provision_service_for_customer(
    customer_id: str,
    service_request: ServiceProvisionRequest,
    reseller_id: str = Depends(get_current_reseller),
):
    """Provision additional service for customer"""
    try:
        # Verify customer belongs to reseller
        customer = await customer_service.get_customer(customer_id)
        if customer.reseller_id != reseller_id:
            raise HTTPException(403, "Customer not associated with reseller")

        # Provision service
        provision_result = await provisioning_service.provision_service(
            {**service_request.model_dump(), "reseller_id": reseller_id}
        )

        # Track provisioning
        await analytics_client.track_event(
            "reseller_service_provisioned",
            {
                "reseller_id": reseller_id,
                "customer_id": customer_id,
                "service_type": service_request.service_type,
                "plan": service_request.plan,
            },
        )

        return {
            "provision_id": provision_result["provision_id"],
            "status": "provisioning",
            "estimated_completion": provision_result.get("estimated_completion"),
        }

    except Exception as e:
        raise HTTPException(500, f"Failed to provision service: {e!s}") from e


@app.get("/customers/{customer_id}/billing")
async def get_customer_billing_for_reseller(
    customer_id: str,
    reseller_id: str = Depends(get_current_reseller),
):
    """Get customer billing information (reseller view)"""
    # Verify ownership
    customer = await customer_service.get_customer(customer_id)
    if customer.reseller_id != reseller_id:
        raise HTTPException(403, "Customer not associated with reseller")

    # Get billing data with commission information
    billing_data = await commission_service.get_customer_billing_summary(customer_id, reseller_id)

    return billing_data


# Sales & Commissions
@app.get("/dashboard/sales")
async def get_sales_dashboard(
    request: Request,
    reseller_id: str = Depends(get_current_reseller),
):
    """Sales dashboard (web interface)"""
    dashboard_data = await dashboard.get_sales_overview(reseller_id)

    return templates.TemplateResponse("dashboard.html", {"request": request, "data": dashboard_data})


@app.get("/commissions")
async def get_commission_history(
    reseller_id: str = Depends(get_current_reseller),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """Get commission history"""
    commissions = await commission_service.get_reseller_commissions(reseller_id, start_date, end_date)

    return {
        "commissions": commissions,
        "total_earned": sum(c["amount"] for c in commissions),
        "pending_payment": sum(c["amount"] for c in commissions if c["status"] == "pending"),
    }


@app.get("/reports/performance")
async def get_performance_report(
    reseller_id: str = Depends(get_current_reseller),
    period: str = "monthly",
):
    """Get reseller performance metrics"""
    metrics = await analytics_client.get_reseller_performance(reseller_id, period)

    return {"period": period, "metrics": metrics, "benchmarks": await analytics_client.get_tier_benchmarks(reseller_id)}


@app.post("/leads")
async def submit_lead_for_commission(
    lead_data: dict[str, Any],
    reseller_id: str = Depends(get_current_reseller),
):
    """Submit lead for commission tracking"""
    try:
        # Create lead with reseller attribution
        lead = await reseller_svc.create_attributed_lead(
            {**lead_data, "reseller_id": reseller_id, "source": "reseller_portal"}
        )

        # Track lead submission
        await analytics_client.track_event(
            "reseller_lead_submitted",
            {"reseller_id": reseller_id, "lead_id": lead.id, "estimated_value": lead_data.get("estimated_value")},
        )

        return {"lead_id": lead.id, "status": "submitted"}

    except Exception as e:
        raise HTTPException(500, f"Failed to submit lead: {e!s}") from e


# Provisioning Tools
@app.post("/provision/broadband")
async def self_service_provisioning(
    provision_request: ServiceProvisionRequest,
    reseller_id: str = Depends(get_current_reseller),
):
    """Self-service broadband provisioning"""
    try:
        # Validate reseller can provision this service
        can_provision = await reseller_svc.check_provisioning_rights(reseller_id, provision_request.service_type)

        if not can_provision:
            raise HTTPException(403, "Insufficient provisioning rights")

        # Start provisioning workflow
        provision_result = await provisioning_svc.start_self_service_provision(
            {**provision_request.model_dump(), "reseller_id": reseller_id}
        )

        return {
            "provision_id": provision_result["provision_id"],
            "status": "initiated",
            "next_steps": provision_result["next_steps"],
        }

    except Exception as e:
        raise HTTPException(500, f"Provisioning failed: {e!s}") from e


@app.get("/provision/status/{provision_id}")
async def get_provisioning_status(
    provision_id: str,
    reseller_id: str = Depends(get_current_reseller),
):
    """Get provisioning status"""
    status = await provisioning_service.get_provision_status(provision_id)

    # Verify reseller owns this provision request
    if status["reseller_id"] != reseller_id:
        raise HTTPException(403, "Provision request not found")

    return status


@app.get("/templates/services")
async def get_service_templates(reseller_id: str = Depends(get_current_reseller)):
    """Get available service templates for reseller"""
    templates = await reseller_svc.get_available_service_templates(reseller_id)
    return {"templates": templates}


# White-label Customer Portal
@app.get("/portal/config")
async def get_portal_config(reseller_id: str = Depends(get_current_reseller)):
    """Get white-label portal configuration"""
    config = await white_label.get_config(reseller_id)
    return config


@app.get("/portal/customer-facing")
async def get_customer_portal_url(reseller_id: str = Depends(get_current_reseller)):
    """Get customer-facing portal URL for this reseller"""
    portal_url = await white_label.get_customer_portal_url(reseller_id)
    return {"portal_url": portal_url}


# Authentication helper (simplified)
async def get_current_reseller() -> str:
    """Get current authenticated reseller ID"""
    # This would integrate with your auth system
    return "reseller_123"  # Placeholder


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "reseller-portal"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
