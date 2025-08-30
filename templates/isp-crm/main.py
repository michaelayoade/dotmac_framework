from datetime import datetime
from typing import Any, Dict, Optional

from dotmac_analytics import AnalyticsClient
from dotmac_billing import QuoteService
from dotmac_communications import CommunicationsClient
from dotmac_core_events import EventBus
from dotmac_identity import CustomerService, LeadService
from fastapi import FastAPI, HTTPException
from orchestration import CustomerJourney, LeadFlow, SalesPipeline
from pydantic import BaseModel
from services import CampaignService, LeadService, OpportunityService

app = FastAPI(title="DotMac CRM Orchestration Service")
event_bus = EventBus()

# External service clients
customer_service = CustomerService()
quote_service = QuoteService()
analytics_client = AnalyticsClient()
communications_client = CommunicationsClient()

# Orchestration services
lead_flow = LeadFlow()
sales_pipeline = SalesPipeline()
customer_journey = CustomerJourney()

# CRM services
lead_svc = LeadService()
opportunity_svc = OpportunityService()
campaign_svc = CampaignService()

class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    source: str  # website, referral, cold_call, marketing
    notes: Optional[str] = None
    interest_level: str = "cold"  # cold, warm, hot

class OpportunityUpdate(BaseModel):
    stage: str  # lead, qualified, proposal, negotiation, closed_won, closed_lost
    value: Optional[float] = None
    close_date: Optional[datetime] = None
    notes: Optional[str] = None

class CampaignCreate(BaseModel):
    name: str
    type: str  # email, sms, whatsapp
    target_segment: Dict[str, Any]
    message_template: str
    schedule_date: Optional[datetime] = None

# Lead Management
@app.post("/leads")
async def create_lead(lead_data: LeadCreate):
    """Capture new lead from web forms, calls, etc."""
    try:
        # Create lead in CRM
        lead = await lead_svc.create_lead(lead_data.dict())

        # Start lead nurturing workflow
        await lead_flow.start_nurturing_sequence(lead.id, lead_data.source)

        # Track analytics
        await analytics_client.track_event("lead_created", {
            "lead_id": lead.id,
            "source": lead_data.source,
            "interest_level": lead_data.interest_level
        })

        # Emit event for other services
        await event_bus.emit("crm.lead.created", {
            "lead_id": lead.id,
            "email": lead_data.email,
            "phone": lead_data.phone,
            "source": lead_data.source
        })

        return {"lead_id": lead.id, "status": "created"}

    except Exception as e:
        raise HTTPException(500, f"Failed to create lead: {e!s}")

@app.get("/leads")
async def list_leads(
    status: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List leads with filters"""
    filters = {}
    if status:
        filters["status"] = status
    if source:
        filters["source"] = source

    leads = await lead_svc.list_leads(filters, limit, offset)
    return {"leads": leads, "total": len(leads)}

@app.put("/leads/{lead_id}/qualify")
async def qualify_lead(lead_id: str, qualification_notes: Optional[str] = None):
    """Convert lead to opportunity"""
    try:
        # Qualify lead
        opportunity = await lead_flow.qualify_lead(lead_id, qualification_notes)

        # Move to sales pipeline
        await sales_pipeline.add_opportunity(opportunity.id, "qualified")

        # Track conversion
        await analytics_client.track_event("lead_qualified", {
            "lead_id": lead_id,
            "opportunity_id": opportunity.id
        })

        return {"opportunity_id": opportunity.id, "stage": "qualified"}

    except Exception as e:
        raise HTTPException(500, f"Failed to qualify lead: {e!s}")

@app.put("/leads/{lead_id}/convert")
async def convert_opportunity(lead_id: str, customer_data: Dict[str, Any]):
    """Convert opportunity to customer"""
    try:
        # Get opportunity
        opportunity = await opportunity_svc.get_by_lead_id(lead_id)

        # Create customer in identity plane
        customer = await customer_service.create_customer(customer_data)

        # Update opportunity
        await opportunity_svc.mark_won(opportunity.id, customer.id)

        # Start customer journey
        await customer_journey.start_onboarding(customer.id)

        # Track conversion
        await analytics_client.track_event("opportunity_converted", {
            "opportunity_id": opportunity.id,
            "customer_id": customer.id,
            "value": opportunity.value
        })

        return {"customer_id": customer.id, "status": "converted"}

    except Exception as e:
        raise HTTPException(500, f"Failed to convert opportunity: {e!s}")

# Pipeline Management
@app.get("/pipeline")
async def get_pipeline():
    """Get visual pipeline view"""
    pipeline_data = await sales_pipeline.get_pipeline_overview()

    return {
        "stages": pipeline_data["stages"],
        "total_value": pipeline_data["total_value"],
        "conversion_rates": pipeline_data["conversion_rates"]
    }

@app.put("/opportunities/{opportunity_id}/stage")
async def move_opportunity_stage(opportunity_id: str, update_data: OpportunityUpdate):
    """Move opportunity through pipeline stages"""
    try:
        # Update opportunity
        opportunity = await opportunity_svc.update_stage(opportunity_id, update_data.dict())

        # Update pipeline
        await sales_pipeline.move_stage(opportunity_id, update_data.stage)

        # Handle stage-specific actions
        if update_data.stage == "proposal":
            # Auto-generate quote
            quote = await quote_service.create_quote({
                "customer_id": opportunity.customer_id,
                "opportunity_id": opportunity_id,
                "value": update_data.value
            })

        elif update_data.stage == "closed_won":
            # Start customer onboarding
            await customer_journey.start_onboarding(opportunity.customer_id)

        # Track pipeline movement
        await analytics_client.track_event("opportunity_stage_changed", {
            "opportunity_id": opportunity_id,
            "from_stage": opportunity.previous_stage,
            "to_stage": update_data.stage,
            "value": update_data.value
        })

        return {"status": "updated", "stage": update_data.stage}

    except Exception as e:
        raise HTTPException(500, f"Failed to update opportunity: {e!s}")

@app.post("/opportunities/{opportunity_id}/quote")
async def generate_quote(opportunity_id: str, quote_data: Dict[str, Any]):
    """Generate quote for opportunity"""
    try:
        # Get opportunity details
        opportunity = await opportunity_svc.get_by_id(opportunity_id)

        # Create quote via billing plane
        quote = await quote_service.create_quote({
            **quote_data,
            "opportunity_id": opportunity_id,
            "customer_id": opportunity.customer_id
        })

        # Send quote via communications
        await communications_client.send_notification({
            "channel": "email",
            "to": opportunity.email,
            "template": "quote_generated",
            "data": {
                "quote_id": quote.id,
                "amount": quote.total_amount,
                "quote_url": f"/quotes/{quote.id}"
            }
        })

        return {"quote_id": quote.id, "status": "sent"}

    except Exception as e:
        raise HTTPException(500, f"Failed to generate quote: {e!s}")

# Campaign Management
@app.post("/campaigns")
async def create_campaign(campaign_data: CampaignCreate):
    """Create marketing campaign"""
    try:
        # Create campaign
        campaign = await campaign_svc.create_campaign(campaign_data.dict())

        # Get target audience from analytics
        audience = await analytics_client.get_segment(campaign_data.target_segment)

        # Schedule campaign via communications
        for contact in audience:
            await communications_client.send_notification({
                "channel": campaign_data.type,
                "to": contact["email"] if campaign_data.type == "email" else contact["phone"],
                "template": campaign_data.message_template,
                "data": {"name": contact["name"]},
                "campaign_id": campaign.id
            })

        # Track campaign launch
        await analytics_client.track_event("campaign_launched", {
            "campaign_id": campaign.id,
            "type": campaign_data.type,
            "audience_size": len(audience)
        })

        return {"campaign_id": campaign.id, "audience_size": len(audience)}

    except Exception as e:
        raise HTTPException(500, f"Failed to create campaign: {e!s}")

@app.get("/campaigns/{campaign_id}/analytics")
async def get_campaign_analytics(campaign_id: str):
    """Get campaign performance analytics"""
    analytics = await analytics_client.get_campaign_metrics(campaign_id)

    return {
        "sent": analytics["sent"],
        "opened": analytics["opened"],
        "clicked": analytics["clicked"],
        "converted": analytics["converted"],
        "open_rate": analytics["open_rate"],
        "click_rate": analytics["click_rate"],
        "conversion_rate": analytics["conversion_rate"]
    }

# Customer 360 View
@app.get("/customers/{customer_id}/timeline")
async def get_customer_timeline(customer_id: str):
    """Get complete customer interaction timeline"""
    timeline = await customer_journey.get_timeline(customer_id)

    return {"timeline": timeline}

@app.get("/customers/{customer_id}/revenue")
async def get_customer_revenue(customer_id: str):
    """Get customer billing history and projections"""
    # Get billing data
    invoices = await quote_service.get_customer_invoices(customer_id)

    # Get revenue analytics
    revenue_data = await analytics_client.get_customer_revenue(customer_id)

    return {
        "total_revenue": revenue_data["total"],
        "monthly_recurring": revenue_data["mrr"],
        "projected_ltv": revenue_data["ltv"],
        "recent_invoices": invoices[:5]
    }

@app.get("/customers/{customer_id}/support")
async def get_customer_support(customer_id: str):
    """Get customer support ticket history"""
    # This would integrate with support desk service
    tickets = await get_support_tickets(customer_id)

    return {"tickets": tickets}

# Unified Inbox
@app.get("/inbox")
async def get_inbox(
    channel: Optional[str] = None,
    status: str = "unread",
    limit: int = 50
):
    """Get unified inbox messages"""
    messages = await communications_client.get_inbox_messages({
        "channel": channel,
        "status": status,
        "limit": limit
    })

    return {"messages": messages}

@app.post("/inbox/{message_id}/reply")
async def reply_to_message(message_id: str, reply_text: str):
    """Reply to inbox message via same channel"""
    try:
        # Get original message
        message = await communications_client.get_message(message_id)

        # Reply via same channel
        response = await communications_client.send_reply({
            "message_id": message_id,
            "channel": message["channel"],
            "to": message["from"],
            "text": reply_text
        })

        # Track interaction
        await analytics_client.track_event("inbox_reply_sent", {
            "message_id": message_id,
            "channel": message["channel"],
            "response_time_minutes": message["response_time_minutes"]
        })

        return {"status": "sent", "response_id": response["id"]}

    except Exception as e:
        raise HTTPException(500, f"Failed to reply: {e!s}")

@app.post("/customers/{customer_id}/message")
async def send_proactive_message(
    customer_id: str,
    channel: str,
    message: str,
    template: Optional[str] = None
):
    """Send proactive message to customer"""
    try:
        # Get customer contact info
        customer = await customer_service.get_customer(customer_id)

        # Send message
        response = await communications_client.send_notification({
            "channel": channel,
            "to": customer.email if channel == "email" else customer.phone,
            "template": template,
            "message": message,
            "customer_id": customer_id
        })

        # Track proactive outreach
        await analytics_client.track_event("proactive_message_sent", {
            "customer_id": customer_id,
            "channel": channel,
            "template": template
        })

        return {"status": "sent", "message_id": response["id"]}

    except Exception as e:
        raise HTTPException(500, f"Failed to send message: {e!s}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "crm"}

if __name__ == "__main__":
    import uvicorn

from dotmac_shared.api.exception_handlers import standard_exception_handler

    uvicorn.run(app, host="127.0.0.1", port=8000)
