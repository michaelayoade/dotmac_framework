import logging
from typing import Any, Dict

from dotmac_analytics import track_event
from dotmac_core_events import EventBus
from fastapi import FastAPI, Request
from providers import email, sms, whatsapp
from pydantic import BaseModel

app = FastAPI(title="DotMac Communications Service")
event_bus = EventBus()

class NotificationRequest(BaseModel):
    channel: str  # email, sms, whatsapp
    to: str
    template: str
    vars: Dict[str, Any] = {}

# Event handlers for automatic notifications
@event_bus.on("customer.onboarded")
async def send_welcome(payload):
    """Send welcome messages when customer onboards"""
    try:
        await email.send(
            to=payload["email"],
            template="welcome",
            data=payload
        )
        await sms.send(
            to=payload["phone"],
            body=f"Hi {payload['name']}, your service is now active!"
        )
        await track_event("notification.sent", {
            "channel": "email_sms",
            "template": "welcome",
            "customer_id": payload.get("id")
        })
    except Exception as e:
        logging.exception(f"Failed to send welcome notification: {e}")

@event_bus.on("notification.send")
async def handle_notification_event(payload):
    """Handle generic notification events"""
    try:
        await send_notification_internal(payload)
    except Exception as e:
        logging.exception(f"Failed to handle notification event: {e}")

# API Routes
@app.post("/send")
async def send_notification(req: NotificationRequest):
    """Send notification via specified channel"""
    return await send_notification_internal(req.dict())

async def send_notification_internal(data: dict):
    """Internal notification sending logic"""
    channel = data["channel"]
    driver = {
        "email": email,
        "sms": sms,
        "whatsapp": whatsapp,
    }.get(channel)

    if not driver:
        return {"error": f"Unknown channel: {channel}"}

    try:
        msg_id = await driver.send(data["to"], data["template"], data["vars"])
        await track_event("notification.sent", {
            "msg_id": msg_id,
            "channel": channel,
            "template": data["template"]
        })
        return {"status": "sent", "msg_id": msg_id}
    except Exception as e:
        logging.exception(f"Failed to send {channel} notification: {e}")
        return {"error": str(e)}

@app.post("/webhooks/{channel}")
async def handle_webhook(channel: str, request: Request):
    """Handle inbound webhooks from providers"""
    raw_body = await request.body()

    provider = {
        "twilio": sms,
        "whatsapp": whatsapp,
        "email": email,
    }.get(channel)

    if not provider:
        return {"error": f"Unknown webhook channel: {channel}"}

    try:
        result = await provider.handle_webhook(raw_body)
        await track_event("notification.received", {
            "channel": channel,
            "data": result
        })
        return {"status": "processed", "data": result}
    except Exception as e:
        logging.exception(f"Failed to process {channel} webhook: {e}")
        return {"error": str(e)}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "communications"}

if __name__ == "__main__":
    import uvicorn

from dotmac_shared.api.exception_handlers import standard_exception_handler

    uvicorn.run(app, host="127.0.0.1", port=8000)
