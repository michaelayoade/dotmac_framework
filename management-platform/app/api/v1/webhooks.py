"""
Webhook endpoints for external service integrations.
Handles Stripe, Twilio, SendGrid and other service webhooks.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Request, HTTPException, status, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services.stripe_service import StripeService
from core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Stripe webhook events.
    
    Processes payment, subscription, and invoice events from Stripe.
    """
    try:
        # Get raw request body
        payload = await request.body()
        
        if not stripe_signature:
            logger.error("Missing Stripe signature header")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing stripe-signature header"
            )
        
        # Process webhook with Stripe service
        stripe_service = StripeService(db)
        result = await stripe_service.process_webhook(payload, stripe_signature)
        
        logger.info(f"Stripe webhook processed: {result}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "success", "result": result}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stripe webhook processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )


@router.post("/twilio/sms")
async def twilio_sms_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Twilio SMS webhook events.
    
    Processes SMS delivery status and incoming messages.
    """
    try:
        form_data = await request.form()
        
        # Extract Twilio webhook data
        message_sid = form_data.get("MessageSid")
        message_status = form_data.get("MessageStatus")
        from_number = form_data.get("From")
        to_number = form_data.get("To")
        body = form_data.get("Body")
        
        logger.info(f"Twilio SMS webhook: {message_sid} - {message_status}")
        
        # Process based on webhook type
        if message_status:
            # Delivery status update
            await _handle_sms_status_update(
                message_sid, message_status, db
            )
        elif body and from_number:
            # Incoming SMS
            await _handle_incoming_sms(
                from_number, to_number, body, db
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "success"}
        )
        
    except Exception as e:
        logger.error(f"Twilio webhook processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SMS webhook processing failed"
        )


@router.post("/sendgrid/email")
async def sendgrid_email_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle SendGrid email webhook events.
    
    Processes email delivery, bounce, and engagement events.
    """
    try:
        events = await request.model_dump_json()
        
        for event in events:
            event_type = event.get("event")
            email = event.get("email")
            timestamp = event.get("timestamp")
            message_id = event.get("sg_message_id")
            
            logger.info(f"SendGrid webhook: {event_type} for {email}")
            
            # Process different event types
            if event_type in ["delivered", "bounce", "dropped", "deferred"]:
                await _handle_email_delivery_event(
                    message_id, event_type, email, timestamp, db
                )
            elif event_type in ["open", "click"]:
                await _handle_email_engagement_event(
                    message_id, event_type, email, timestamp, event, db
                )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "success", "processed": len(events)}
        )
        
    except Exception as e:
        logger.error(f"SendGrid webhook processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email webhook processing failed"
        )


@router.post("/github/deployment")
async def github_deployment_webhook(
    request: Request,
    x_github_event: str = Header(None, alias="x-github-event"),
    x_hub_signature_256: str = Header(None, alias="x-hub-signature-256"),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle GitHub deployment webhook events.
    
    Triggers automated deployments and updates deployment status.
    """
    try:
        payload = await request.model_dump_json()
        
        if x_github_event == "deployment":
            # Handle deployment creation
            deployment = payload.get("deployment", {})
            repository = payload.get("repository", {})
            
            deployment_id = deployment.get("id")
            environment = deployment.get("environment")
            ref = deployment.get("ref")
            repo_name = repository.get("full_name")
            
            logger.info(f"GitHub deployment webhook: {repo_name} - {environment} - {ref}")
            
            # Trigger deployment process
            await _handle_github_deployment(
                deployment_id, repo_name, environment, ref, db
            )
            
        elif x_github_event == "deployment_status":
            # Handle deployment status update
            deployment_status = payload.get("deployment_status", {})
            deployment = payload.get("deployment", {})
            
            status_state = deployment_status.get("state")
            deployment_id = deployment.get("id")
            
            logger.info(f"GitHub deployment status: {deployment_id} - {status_state}")
            
            await _handle_github_deployment_status(
                deployment_id, status_state, deployment_status, db
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "success"}
        )
        
    except Exception as e:
        logger.error(f"GitHub webhook processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub webhook processing failed"
        )


@router.post("/monitoring/alerts")
async def monitoring_alert_webhook(
    request: Request,
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle monitoring system alert webhooks.
    
    Processes alerts from Prometheus, Grafana, or other monitoring systems.
    """
    try:
        alert_data = await request.model_dump_json()
        
        # Verify authorization if configured
        # if not _verify_monitoring_webhook_auth(authorization):
        #     raise HTTPException(status_code=401, detail="Unauthorized")
        
        alerts = alert_data.get("alerts", [])
        
        for alert in alerts:
            alert_name = alert.get("labels", {}).get("alertname")
            status = alert.get("status")  # firing or resolved
            severity = alert.get("labels", {}).get("severity")
            instance = alert.get("labels", {}).get("instance")
            
            logger.warning(f"Monitoring alert: {alert_name} - {status} - {severity}")
            
            # Process alert
            await _handle_monitoring_alert(
                alert_name, status, severity, instance, alert, db
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "success", "processed": len(alerts)}
        )
        
    except Exception as e:
        logger.error(f"Monitoring webhook processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Alert webhook processing failed"
        )


# Helper functions

async def _handle_sms_status_update(
    message_sid: str, 
    status: str, 
    db: AsyncSession
):
    """Handle SMS delivery status update."""
    # Implementation would update SMS log status
    logger.info(f"SMS {message_sid} status updated to {status}")
    pass


async def _handle_incoming_sms(
    from_number: str,
    to_number: str, 
    body: str,
    db: AsyncSession
):
    """Handle incoming SMS message."""
    # Implementation would process incoming SMS
    logger.info(f"Incoming SMS from {from_number}: {body}")
    pass


async def _handle_email_delivery_event(
    message_id: str,
    event_type: str,
    email: str,
    timestamp: int,
    db: AsyncSession
):
    """Handle email delivery event."""
    # Implementation would update email log status
    logger.info(f"Email {message_id} to {email}: {event_type}")
    pass


async def _handle_email_engagement_event(
    message_id: str,
    event_type: str,
    email: str,
    timestamp: int,
    event_data: Dict[str, Any],
    db: AsyncSession
):
    """Handle email engagement event."""
    # Implementation would track email engagement
    logger.info(f"Email {message_id} engagement: {event_type}")
    pass


async def _handle_github_deployment(
    deployment_id: int,
    repo_name: str,
    environment: str,
    ref: str,
    db: AsyncSession
):
    """Handle GitHub deployment trigger."""
    # Implementation would trigger deployment process
    logger.info(f"Triggering deployment {deployment_id} for {repo_name}:{ref} to {environment}")
    pass


async def _handle_github_deployment_status(
    deployment_id: int,
    status_state: str,
    status_data: Dict[str, Any],
    db: AsyncSession
):
    """Handle GitHub deployment status update."""
    # Implementation would update deployment status
    logger.info(f"Deployment {deployment_id} status: {status_state}")
    pass


async def _handle_monitoring_alert(
    alert_name: str,
    status: str,
    severity: str,
    instance: str,
    alert_data: Dict[str, Any],
    db: AsyncSession
):
    """Handle monitoring system alert."""
    # Implementation would process monitoring alerts
    logger.warning(f"Alert {alert_name} on {instance}: {status} ({severity})")
    
    # Could trigger:
    # - Incident creation
    # - Notification to on-call team
    # - Auto-scaling actions
    # - Circuit breaker activation
    pass