"""API endpoints for receiving cross-platform events."""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from mgmt.shared.database import get_async_session


logger = logging.getLogger(__name__, timezone)

router = APIRouter(prefix="/api/v1/events", tags=["Cross-Platform Events"])


class CrossPlatformEventData(BaseModel):
    """Cross-platform event data model."""
    event_id: str
    correlation_id: Optional[str] = None
    event_type: str
    severity: str = "info"
    
    # Source information
    source: str
    source_component: str
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Temporal information
    timestamp: datetime
    event_version: str = "1.0"
    
    # Event content
    title: str
    description: Optional[str] = None
    event_data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Cross-platform tracking
    target_platform: Optional[str] = None
    related_events: List[str] = Field(default_factory=list)
    
    # Audit fields
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None
    
    # Performance tracking
    processing_time_ms: Optional[float] = None
    response_code: Optional[int] = None


class EventBatchRequest(BaseModel):
    """Batch event submission request."""
    source: str
    tenant_id: Optional[str] = None
    events: List[CrossPlatformEventData]


class EventStreamService:
    """Service for processing cross-platform events."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def process_event(self, event: CrossPlatformEventData) -> bool:
        """Process a single cross-platform event."""
        try:
            logger.debug(f"Processing event: {event.event_type} from {event.source}")
            
            # Route event based on type
            if event.event_type.startswith("config_"):
                await self._handle_config_event(event)
            elif event.event_type.startswith("plugin_"):
                await self._handle_plugin_event(event)
            elif event.event_type.startswith("health_"):
                await self._handle_health_event(event)
            elif event.event_type in ["authentication_success", "authentication_failure", "authorization_denied", "security_violation"]:
                await self._handle_security_event(event)
            elif event.event_type in ["user_action", "data_access", "admin_action", "compliance_event"]:
                await self._handle_audit_event(event)
            else:
                await self._handle_generic_event(event)
            
            # Store event in audit log
            await self._store_event_in_audit_log(event)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing event {event.event_id}: {str(e)}")
            return False
    
    async def _handle_config_event(self, event: CrossPlatformEventData):
        """Handle configuration-related events."""
        if event.event_type == "config_applied" and event.tenant_id:
            # Update deployment record with config application status
            from mgmt.services.kubernetes_orchestrator.service import KubernetesOrchestrator
            
            orchestrator = KubernetesOrchestrator(self.session)
            deployment = await orchestrator.get_tenant_deployment(event.tenant_id)
            
            if deployment:
                config_version = event.event_data.get("config_version")
                success = event.event_data.get("success", False)
                
                if success:
                    deployment.last_config_applied = config_version
                    deployment.last_config_applied_at = event.timestamp
                else:
                    errors = event.event_data.get("errors", [])
                    deployment.last_config_error = "; ".join(errors)
                    deployment.last_config_error_at = event.timestamp
                
                await self.session.commit()
                logger.info(f"Updated deployment config status for {event.tenant_id}: {config_version}")
    
    async def _handle_plugin_event(self, event: CrossPlatformEventData):
        """Handle plugin-related events."""
        if event.event_type == "plugin_usage_recorded" and event.tenant_id:
            # Record plugin usage
            from mgmt.services.plugin_licensing.service import PluginLicensingService
            
            licensing_service = PluginLicensingService(self.session)
            plugin_id = event.event_data.get("plugin_id")
            
            if plugin_id:
                try:
                    # Extract usage data from event
                    usage_data = event.event_data.get("details", {})
                    metric_name = usage_data.get("metric_name", "general_usage")
                    usage_count = usage_data.get("usage_count", 1)
                    
                    await licensing_service.record_plugin_usage()
                        tenant_id=event.tenant_id,
                        plugin_id=plugin_id,
                        metric_name=metric_name,
                        usage_count=usage_count,
                        timestamp=event.timestamp,
                        metadata=usage_data
                    )
                    
                    logger.debug(f"Recorded plugin usage: {plugin_id} for {event.tenant_id}")
                    
                except Exception as e:
                    logger.warning(f"Failed to record plugin usage from event: {e}")
    
    async def _handle_health_event(self, event: CrossPlatformEventData):
        """Handle health-related events."""
        if event.tenant_id:
            # Record external health report
            from mgmt.services.saas_monitoring.service import SaaSMonitoringService
            
            monitoring_service = SaaSMonitoringService(self.session)
            component = event.event_data.get("component", event.source_component)
            status = event.event_data.get("status", "unknown")
            metrics = event.event_data.get("metrics", {})
            
            await monitoring_service.record_external_health_report()
                tenant_id=event.tenant_id,
                component=component,
                status=status,
                metrics=metrics,
                details=event.description,
                timestamp=event.timestamp
            )
            
            logger.debug(f"Recorded health status: {component} = {status} for {event.tenant_id}")
    
    async def _handle_security_event(self, event: CrossPlatformEventData):
        """Handle security-related events."""
        # Security events are primarily for audit and alerting
        severity_map = {
            "authentication_failure": "warning",
            "authorization_denied": "warning", 
            "security_violation": "critical"
        }
        
        if event.event_type in severity_map:
            # Could trigger alerts or security monitoring
            logger.info(f"Security event: {event.event_type} from {event.source} for tenant {event.tenant_id}")
    
    async def _handle_audit_event(self, event: CrossPlatformEventData):
        """Handle audit trail events."""
        # Audit events are stored in the audit log for compliance
        logger.debug(f"Audit event: {event.action} on {event.resource_type}/{event.resource_id} by {event.user_id}")
    
    async def _handle_generic_event(self, event: CrossPlatformEventData):
        """Handle generic events."""
        logger.debug(f"Generic event: {event.event_type} from {event.source}")
    
    async def _store_event_in_audit_log(self, event: CrossPlatformEventData):
        """Store event in the audit log."""
        # This would typically store in a dedicated audit log table
        # For now, we'll log it for audit purposes
        audit_data = {
            "event_id": event.event_id,
            "tenant_id": event.tenant_id,
            "user_id": event.user_id,
            "action": event.action or event.event_type,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "source": event.source,
            "timestamp": event.timestamp.isoformat(),
            "details": {
                "title": event.title,
                "description": event.description,
                "event_data": event.event_data,
                "severity": event.severity
            }
        }
        
        logger.info(f"AUDIT: {audit_data}")


def get_tenant_id_from_header(x_tenant_id: Optional[str] = Header(None) -> Optional[str]:
    """Extract tenant ID from header (optional for events)."""
    return x_tenant_id


@router.post("/stream", status_code=status.HTTP_202_ACCEPTED)
async def receive_event_stream():
    event: CrossPlatformEventData,
    session: AsyncSession = Depends(get_async_session),
    tenant_id: Optional[str] = Depends(get_tenant_id_from_header)
):
    """Receive single cross-platform event."""
    try:
        logger.debug(f"Received event: {event.event_type} from {event.source}")
        
        # Override tenant_id from header if provided
        if tenant_id and not event.tenant_id:
            event.tenant_id = tenant_id
        
        event_service = EventStreamService(session)
        success = await event_service.process_event(event)
        
        if success:
            return {
                "status": "accepted",
                "event_id": event.event_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException()
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process event"
            )
        
    except Exception as e:
        logger.error(f"Error receiving event: {str(e)}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while processing event"
        )


@router.post("/batch", status_code=status.HTTP_202_ACCEPTED)
async def receive_event_batch():
    batch: EventBatchRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Receive batch of cross-platform events."""
    try:
        logger.info(f"Received event batch: {len(batch.events)} events from {batch.source}")
        
        event_service = EventStreamService(session)
        processed_count = 0
        failed_events = []
        
        for event in batch.events:
            # Set tenant_id from batch if not in event
            if batch.tenant_id and not event.tenant_id:
                event.tenant_id = batch.tenant_id
            
            try:
                success = await event_service.process_event(event)
                if success:
                    processed_count += 1
                else:
                    failed_events.append(event.event_id)
            except Exception as e:
                logger.error(f"Error processing event {event.event_id}: {e}")
                failed_events.append(event.event_id)
        
        return {
            "status": "batch_processed",
            "total_events": len(batch.events),
            "processed_count": processed_count,
            "failed_count": len(failed_events),
            "failed_events": failed_events,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing event batch: {str(e)}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while processing event batch"
        )


@router.get("/audit/{tenant_id}")
async def get_audit_trail():
    tenant_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session)
):
    """Get audit trail for tenant."""
    try:
        # This would query the audit log table
        # For now, return a placeholder response
        return {
            "tenant_id": tenant_id,
            "audit_trail": [],
            "total_events": 0,
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "event_type": event_type,
                "user_id": user_id,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting audit trail: {str(e)}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while getting audit trail"
        )


@router.get("/correlation/{correlation_id}")
async def get_correlated_events():
    correlation_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """Get all events with the same correlation ID."""
    try:
        # This would query events by correlation_id
        # For now, return a placeholder response
        return {
            "correlation_id": correlation_id,
            "events": [],
            "event_count": 0,
            "platforms": []
        }
        
    except Exception as e:
        logger.error(f"Error getting correlated events: {str(e)}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while getting correlated events"
        )