"""API router for managing channel plugins."""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from dotmac_isp.core.database import get_db
from dotmac_isp.shared.auth import get_current_user, get_current_tenant_id
from dotmac_isp.shared.exceptions import EntityNotFoundError, ValidationError
from dotmac_isp.shared.schemas import SuccessResponse, ErrorResponse

from .plugin_service import ChannelPluginService
from .channel_plugins.base import ChannelMessage

logger = logging.getLogger(__name__, timezone)

router = APIRouter(prefix="/omnichannel/channels", tags=["channel-plugins"])


# ===== REQUEST/RESPONSE SCHEMAS =====


class ChannelConfigurationRequest(BaseModel):
    """Request schema for channel configuration."""

    channel_id: str
    configuration: Dict[str, Any]


class ChannelMessageRequest(BaseModel):
    """Request schema for sending messages."""

    channel_id: str
    content: str
    message_type: str = "text"
    recipient_id: str
    sender_id: Optional[str] = None
    attachments: List[Dict[str, str]] = []
    metadata: Dict[str, Any] = {}


class ChannelInfoResponse(BaseModel):
    """Response schema for channel information."""

    id: str
    channel_id: str
    channel_name: str
    capabilities: List[str]
    is_configured: bool
    health_status: str
    configuration_schema: Dict[str, Any]


class HealthCheckResponse(BaseModel):
    """Response schema for health checks."""

    channel_name: str
    is_healthy: bool
    last_check: Optional[datetime] = None
    error_message: Optional[str] = None


# ===== CHANNEL MANAGEMENT ENDPOINTS =====


@router.post("/register", response_model=SuccessResponse)
async def register_available_plugins(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Register all available channel plugins for the tenant."""
    try:
        service = ChannelPluginService(db, tenant_id)
        count = await service.register_available_plugins()

        return SuccessResponse(
            message=f"Successfully registered {count} channel plugins",
            data={"registered_count": count},
        )

    except Exception as e:
        logger.error(f"Failed to register plugins for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Plugin registration failed: {str(e)}",
        )


@router.get("/", response_model=List[ChannelInfoResponse])
async def get_available_channels(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Get all available channels for the tenant."""
    try:
        service = ChannelPluginService(db, tenant_id)
        channels = service.get_available_channels()

        return [ChannelInfoResponse(**channel) for channel in channels]

    except Exception as e:
        logger.error(f"Failed to get channels for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve channels: {str(e)}",
        )


@router.post("/configure", response_model=SuccessResponse)
async def configure_channel(
    config_request: ChannelConfigurationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Configure a channel with the provided settings."""
    try:
        service = ChannelPluginService(db, tenant_id)

        success = await service.configure_channel(
            config_request.channel_id, config_request.configuration
        )

        if success:
            return SuccessResponse(
                message=f"Successfully configured channel {config_request.channel_id}",
                data={"channel_id": config_request.channel_id},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Channel configuration failed",
            )

    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(
            f"Channel configuration failed for {config_request.channel_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Configuration failed: {str(e)}",
        )


@router.post("/send-message", response_model=Dict[str, Any])
async def send_message(
    message_request: ChannelMessageRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Send a message through a specific channel."""
    try:
        service = ChannelPluginService(db, tenant_id)

        # Create channel message
        channel_message = ChannelMessage(
            content=message_request.content,
            message_type=message_request.message_type,
            sender_id=message_request.sender_id or current_user.email,
            recipient_id=message_request.recipient_id,
            attachments=message_request.attachments,
            metadata=message_request.metadata,
        )

        result = await service.send_message(message_request.channel_id, channel_message)

        return result

    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to send message via {message_request.channel_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Message sending failed: {str(e)}",
        )


@router.get("/capabilities/{channel_id}")
async def get_channel_capabilities(
    channel_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Get capabilities of a specific channel."""
    try:
        service = ChannelPluginService(db, tenant_id)
        capabilities = service.get_channel_capabilities(channel_id)

        return {"channel_id": channel_id, "capabilities": capabilities}

    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get capabilities for {channel_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve capabilities: {str(e)}",
        )


@router.get("/by-capability/{capability}")
async def get_channels_by_capability(
    capability: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Get all channels that support a specific capability."""
    try:
        service = ChannelPluginService(db, tenant_id)
        channels = service.get_channels_by_capability(capability)

        return {"capability": capability, "channels": channels}

    except Exception as e:
        logger.error(f"Failed to get channels by capability {capability}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve channels: {str(e)}",
        )


@router.post("/health-check", response_model=Dict[str, HealthCheckResponse])
async def health_check_all_channels(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Perform health checks on all configured channels."""
    try:
        service = ChannelPluginService(db, tenant_id)
        results = await service.health_check_all_channels()

        return {
            channel_id: HealthCheckResponse(**result)
            for channel_id, result in results.items()
        }

    except Exception as e:
        logger.error(f"Health check failed for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}",
        )


@router.post("/{channel_id}/disable", response_model=SuccessResponse)
async def disable_channel(
    channel_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Disable a channel configuration."""
    try:
        service = ChannelPluginService(db, tenant_id)
        success = service.disable_channel(channel_id)

        if success:
            return SuccessResponse(
                message=f"Successfully disabled channel {channel_id}",
                data={"channel_id": channel_id},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to disable channel",
            )

    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to disable channel {channel_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Channel disable failed: {str(e)}",
        )


# ===== WEBHOOK ENDPOINTS =====


@router.post("/webhook/{channel_id}")
async def handle_webhook(
    channel_id: str,
    webhook_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Handle incoming webhooks from communication channels."""
    try:
        # Note: Webhooks typically don't have standard auth, so we need to handle tenant identification differently
        # For now, we'll use a simple approach - in production you'd want to validate webhook signatures

        # You might extract tenant info from webhook data or use channel-specific validation
        # For this example, we'll need to implement tenant resolution logic

        logger.info(f"Received webhook for channel {channel_id}")

        # Basic tenant resolution from channel configuration
        # In a real system, you'd look up the channel's tenant from the database
        tenant_id = "default-tenant"  # Simple fallback for now
        return JSONResponse(
            content={
                "status": "received",
                "channel_id": channel_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Webhook handling failed for {channel_id}: {e}")
        return JSONResponse(
            content={"error": str(e)}, status_code=status.HTTP_400_BAD_REQUEST
        )


@router.get("/webhook/{channel_id}")
async def webhook_verification(
    channel_id: str,
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
):
    """Handle webhook verification (e.g., for Facebook/WhatsApp)."""
    try:
        # This is a simplified webhook verification
        # In production, you'd validate the verify_token against your configuration

        if hub_mode == "subscribe" and hub_challenge:
            logger.info(f"Webhook verification for channel {channel_id}")
            return hub_challenge

        return JSONResponse(
            content={"error": "Invalid verification request"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    except Exception as e:
        logger.error(f"Webhook verification failed for {channel_id}: {e}")
        return JSONResponse(
            content={"error": str(e)}, status_code=status.HTTP_400_BAD_REQUEST
        )
