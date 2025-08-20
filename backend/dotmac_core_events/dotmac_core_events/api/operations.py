"""
Operations API for advanced event management operations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field

from ..sdks.event_bus import EventBusSDK
from ..security.auth import get_current_tenant, require_permissions

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/operations", tags=["operations"])


# Request/Response Models
class DLQReplayRequest(BaseModel):
    """Request to replay messages from DLQ."""
    topic: str = Field(..., description="Topic to replay messages from")
    consumer_group: Optional[str] = Field(None, description="Consumer group filter")
    message_ids: Optional[List[str]] = Field(None, description="Specific message IDs to replay")
    max_messages: int = Field(100, ge=1, le=1000, description="Maximum messages to replay")
    filter_criteria: Optional[Dict[str, Any]] = Field(None, description="Additional filter criteria")


class DLQReplayResponse(BaseModel):
    """Response from DLQ replay operation."""
    replay_id: str = Field(..., description="Unique replay operation ID")
    topic: str = Field(..., description="Topic being replayed")
    messages_found: int = Field(..., description="Number of messages found in DLQ")
    messages_replayed: int = Field(..., description="Number of messages successfully replayed")
    messages_failed: int = Field(..., description="Number of messages that failed replay")
    started_at: datetime = Field(..., description="Replay start time")
    completed_at: Optional[datetime] = Field(None, description="Replay completion time")
    status: str = Field(..., description="Replay status")


class StepRetryRequest(BaseModel):
    """Request to retry a workflow step."""
    workflow_id: str = Field(..., description="Workflow ID")
    step_id: str = Field(..., description="Step ID to retry")
    retry_config: Optional[Dict[str, Any]] = Field(None, description="Custom retry configuration")
    force: bool = Field(False, description="Force retry even if step succeeded")


class StepSkipRequest(BaseModel):
    """Request to skip a workflow step."""
    workflow_id: str = Field(..., description="Workflow ID")
    step_id: str = Field(..., description="Step ID to skip")
    skip_reason: str = Field(..., description="Reason for skipping step")
    mock_result: Optional[Dict[str, Any]] = Field(None, description="Mock result data for skipped step")


class SchedulePauseRequest(BaseModel):
    """Request to pause a schedule."""
    schedule_id: str = Field(..., description="Schedule ID to pause")
    pause_reason: str = Field(..., description="Reason for pausing")
    pause_until: Optional[datetime] = Field(None, description="Auto-resume time")


class ScheduleResumeRequest(BaseModel):
    """Request to resume a schedule."""
    schedule_id: str = Field(..., description="Schedule ID to resume")
    resume_reason: str = Field(..., description="Reason for resuming")


class RunCancelRequest(BaseModel):
    """Request to cancel a workflow run."""
    workflow_id: str = Field(..., description="Workflow ID to cancel")
    run_id: Optional[str] = Field(None, description="Specific run ID (latest if not provided)")
    cancel_reason: str = Field(..., description="Reason for cancellation")
    force: bool = Field(False, description="Force cancel even if run is completing")


class OperationResponse(BaseModel):
    """Generic operation response."""
    operation_id: str = Field(..., description="Unique operation ID")
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Operation message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DLQManager:
    """Manager for DLQ operations."""

    def __init__(self, event_bus: EventBusSDK):
        self.event_bus = event_bus
        self.active_replays = {}

    async def replay_messages(
        self,
        tenant_id: str,
        request: DLQReplayRequest
    ) -> DLQReplayResponse:
        """Replay messages from DLQ."""
        replay_id = str(uuid4())
        started_at = datetime.now(timezone.utc)

        try:
            # Get DLQ messages
            dlq_messages = await self._get_dlq_messages(
                tenant_id=tenant_id,
                topic=request.topic,
                consumer_group=request.consumer_group,
                message_ids=request.message_ids,
                max_messages=request.max_messages,
                filter_criteria=request.filter_criteria
            )

            messages_found = len(dlq_messages)
            messages_replayed = 0
            messages_failed = 0

            # Track replay operation
            self.active_replays[replay_id] = {
                "tenant_id": tenant_id,
                "topic": request.topic,
                "started_at": started_at,
                "status": "running",
                "messages_found": messages_found,
                "messages_replayed": 0,
                "messages_failed": 0
            }

            # Publish replay started event
            await self.event_bus.publish(
                event_type="dlq.replay.started",
                data={
                    "replay_id": replay_id,
                    "tenant_id": tenant_id,
                    "topic": request.topic,
                    "messages_found": messages_found
                },
                partition_key=tenant_id
            )

            # Replay messages
            for message in dlq_messages:
                try:
                    # Republish message to original topic
                    result = await self.event_bus.publish(
                        event_type=message.get("original_event_type", "dlq.replayed"),
                        data=message.get("data", {}),
                        partition_key=message.get("partition_key"),
                        metadata=message.get("metadata")
                    )

                    if result.get("status") == "published":
                        messages_replayed += 1
                    else:
                        messages_failed += 1

                except Exception as e:
                    logger.error("Failed to replay message",
                               replay_id=replay_id,
                               message_id=message.get("id"),
                               error=str(e))
                    messages_failed += 1

            completed_at = datetime.now(timezone.utc)
            status = "completed" if messages_failed == 0 else "completed_with_errors"

            # Update replay tracking
            self.active_replays[replay_id].update({
                "status": status,
                "messages_replayed": messages_replayed,
                "messages_failed": messages_failed,
                "completed_at": completed_at
            })

            # Publish replay completed event
            await self.event_bus.publish(
                event_type="dlq.replay.completed",
                data={
                    "replay_id": replay_id,
                    "tenant_id": tenant_id,
                    "topic": request.topic,
                    "messages_replayed": messages_replayed,
                    "messages_failed": messages_failed,
                    "duration_seconds": (completed_at - started_at).total_seconds()
                },
                partition_key=tenant_id
            )

            return DLQReplayResponse(
                replay_id=replay_id,
                topic=request.topic,
                messages_found=messages_found,
                messages_replayed=messages_replayed,
                messages_failed=messages_failed,
                started_at=started_at,
                completed_at=completed_at,
                status=status
            )

        except Exception as e:
            logger.error("DLQ replay failed", replay_id=replay_id, error=str(e))

            # Update replay tracking
            if replay_id in self.active_replays:
                self.active_replays[replay_id]["status"] = "failed"

            # Publish replay failed event
            await self.event_bus.publish(
                event_type="dlq.replay.failed",
                data={
                    "replay_id": replay_id,
                    "tenant_id": tenant_id,
                    "topic": request.topic,
                    "error": str(e)
                },
                partition_key=tenant_id
            )

            raise HTTPException(status_code=500, detail=f"DLQ replay failed: {str(e)}")

    async def _get_dlq_messages(
        self,
        tenant_id: str,
        topic: str,
        consumer_group: Optional[str] = None,
        message_ids: Optional[List[str]] = None,
        max_messages: int = 100,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get messages from DLQ."""
        # This would integrate with the actual DLQ storage
        # For now, return mock data
        messages = []

        for i in range(min(max_messages, 10)):  # Mock up to 10 messages
            message = {
                "id": f"dlq_msg_{i}",
                "original_event_type": f"test.event.{i}",
                "data": {"test_data": f"value_{i}"},
                "partition_key": tenant_id,
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "failure_reason": "Processing timeout",
                "retry_count": 3,
                "tenant_id": tenant_id,
                "topic": topic
            }

            # Apply filters
            if message_ids and message["id"] not in message_ids:
                continue

            if filter_criteria:
                # Apply custom filters
                if not self._matches_filter(message, filter_criteria):
                    continue

            messages.append(message)

        return messages

    def _matches_filter(self, message: Dict[str, Any], criteria: Dict[str, Any]) -> bool:
        """Check if message matches filter criteria."""
        for key, value in criteria.items():
            if key not in message:
                return False
            if message[key] != value:
                return False
        return True


class WorkflowOperationsManager:
    """Manager for workflow operations."""

    def __init__(self, event_bus: EventBusSDK):
        self.event_bus = event_bus
        self.active_operations = {}

    async def retry_step(
        self,
        tenant_id: str,
        request: StepRetryRequest
    ) -> OperationResponse:
        """Retry a workflow step."""
        operation_id = str(uuid4())

        try:
            # Publish step retry command
            await self.event_bus.publish(
                event_type="command.step.retry",
                data={
                    "operation_id": operation_id,
                    "workflow_id": request.workflow_id,
                    "step_id": request.step_id,
                    "retry_config": request.retry_config or {},
                    "force": request.force,
                    "tenant_id": tenant_id,
                    "requested_at": datetime.now(timezone.utc).isoformat()
                },
                partition_key=tenant_id
            )

            logger.info("Step retry requested",
                       operation_id=operation_id,
                       workflow_id=request.workflow_id,
                       step_id=request.step_id)

            return OperationResponse(
                operation_id=operation_id,
                status="requested",
                message=f"Step retry requested for workflow {request.workflow_id}, step {request.step_id}",
                details={
                    "workflow_id": request.workflow_id,
                    "step_id": request.step_id,
                    "force": request.force
                }
            )

        except Exception as e:
            logger.error("Step retry failed",
                        workflow_id=request.workflow_id,
                        step_id=request.step_id,
                        error=str(e))
            raise HTTPException(status_code=500, detail=f"Step retry failed: {str(e)}")

    async def skip_step(
        self,
        tenant_id: str,
        request: StepSkipRequest
    ) -> OperationResponse:
        """Skip a workflow step."""
        operation_id = str(uuid4())

        try:
            # Publish step skip command
            await self.event_bus.publish(
                event_type="command.step.skip",
                data={
                    "operation_id": operation_id,
                    "workflow_id": request.workflow_id,
                    "step_id": request.step_id,
                    "skip_reason": request.skip_reason,
                    "mock_result": request.mock_result or {},
                    "tenant_id": tenant_id,
                    "requested_at": datetime.now(timezone.utc).isoformat()
                },
                partition_key=tenant_id
            )

            logger.info("Step skip requested",
                       operation_id=operation_id,
                       workflow_id=request.workflow_id,
                       step_id=request.step_id,
                       reason=request.skip_reason)

            return OperationResponse(
                operation_id=operation_id,
                status="requested",
                message=f"Step skip requested for workflow {request.workflow_id}, step {request.step_id}",
                details={
                    "workflow_id": request.workflow_id,
                    "step_id": request.step_id,
                    "skip_reason": request.skip_reason
                }
            )

        except Exception as e:
            logger.error("Step skip failed",
                        workflow_id=request.workflow_id,
                        step_id=request.step_id,
                        error=str(e))
            raise HTTPException(status_code=500, detail=f"Step skip failed: {str(e)}")

    async def cancel_run(
        self,
        tenant_id: str,
        request: RunCancelRequest
    ) -> OperationResponse:
        """Cancel a workflow run."""
        operation_id = str(uuid4())

        try:
            # Publish run cancel command
            await self.event_bus.publish(
                event_type="command.run.cancel",
                data={
                    "operation_id": operation_id,
                    "workflow_id": request.workflow_id,
                    "run_id": request.run_id,
                    "cancel_reason": request.cancel_reason,
                    "force": request.force,
                    "tenant_id": tenant_id,
                    "requested_at": datetime.now(timezone.utc).isoformat()
                },
                partition_key=tenant_id
            )

            logger.info("Run cancel requested",
                       operation_id=operation_id,
                       workflow_id=request.workflow_id,
                       run_id=request.run_id,
                       reason=request.cancel_reason)

            return OperationResponse(
                operation_id=operation_id,
                status="requested",
                message=f"Run cancel requested for workflow {request.workflow_id}",
                details={
                    "workflow_id": request.workflow_id,
                    "run_id": request.run_id,
                    "cancel_reason": request.cancel_reason,
                    "force": request.force
                }
            )

        except Exception as e:
            logger.error("Run cancel failed",
                        workflow_id=request.workflow_id,
                        error=str(e))
            raise HTTPException(status_code=500, detail=f"Run cancel failed: {str(e)}")


class ScheduleOperationsManager:
    """Manager for schedule operations."""

    def __init__(self, event_bus: EventBusSDK):
        self.event_bus = event_bus
        self.paused_schedules = {}

    async def pause_schedule(
        self,
        tenant_id: str,
        request: SchedulePauseRequest
    ) -> OperationResponse:
        """Pause a schedule."""
        operation_id = str(uuid4())

        try:
            # Track paused schedule
            self.paused_schedules[request.schedule_id] = {
                "tenant_id": tenant_id,
                "pause_reason": request.pause_reason,
                "paused_at": datetime.now(timezone.utc),
                "pause_until": request.pause_until,
                "operation_id": operation_id
            }

            # Publish schedule pause command
            await self.event_bus.publish(
                event_type="command.schedule.pause",
                data={
                    "operation_id": operation_id,
                    "schedule_id": request.schedule_id,
                    "pause_reason": request.pause_reason,
                    "pause_until": request.pause_until.isoformat() if request.pause_until else None,
                    "tenant_id": tenant_id,
                    "requested_at": datetime.now(timezone.utc).isoformat()
                },
                partition_key=tenant_id
            )

            logger.info("Schedule pause requested",
                       operation_id=operation_id,
                       schedule_id=request.schedule_id,
                       reason=request.pause_reason)

            return OperationResponse(
                operation_id=operation_id,
                status="paused",
                message=f"Schedule {request.schedule_id} paused",
                details={
                    "schedule_id": request.schedule_id,
                    "pause_reason": request.pause_reason,
                    "pause_until": request.pause_until.isoformat() if request.pause_until else None
                }
            )

        except Exception as e:
            logger.error("Schedule pause failed",
                        schedule_id=request.schedule_id,
                        error=str(e))
            raise HTTPException(status_code=500, detail=f"Schedule pause failed: {str(e)}")

    async def resume_schedule(
        self,
        tenant_id: str,
        request: ScheduleResumeRequest
    ) -> OperationResponse:
        """Resume a schedule."""
        operation_id = str(uuid4())

        try:
            # Remove from paused schedules
            if request.schedule_id in self.paused_schedules:
                paused_info = self.paused_schedules.pop(request.schedule_id)
                pause_duration = datetime.now(timezone.utc) - paused_info["paused_at"]
            else:
                pause_duration = None

            # Publish schedule resume command
            await self.event_bus.publish(
                event_type="command.schedule.resume",
                data={
                    "operation_id": operation_id,
                    "schedule_id": request.schedule_id,
                    "resume_reason": request.resume_reason,
                    "pause_duration_seconds": pause_duration.total_seconds() if pause_duration else None,
                    "tenant_id": tenant_id,
                    "requested_at": datetime.now(timezone.utc).isoformat()
                },
                partition_key=tenant_id
            )

            logger.info("Schedule resume requested",
                       operation_id=operation_id,
                       schedule_id=request.schedule_id,
                       reason=request.resume_reason)

            return OperationResponse(
                operation_id=operation_id,
                status="resumed",
                message=f"Schedule {request.schedule_id} resumed",
                details={
                    "schedule_id": request.schedule_id,
                    "resume_reason": request.resume_reason,
                    "pause_duration_seconds": pause_duration.total_seconds() if pause_duration else None
                }
            )

        except Exception as e:
            logger.error("Schedule resume failed",
                        schedule_id=request.schedule_id,
                        error=str(e))
            raise HTTPException(status_code=500, detail=f"Schedule resume failed: {str(e)}")


# Global managers (would be dependency injected in production)
dlq_manager = None
workflow_ops_manager = None
schedule_ops_manager = None


def get_dlq_manager() -> DLQManager:
    """Get DLQ manager dependency."""
    global dlq_manager
    if dlq_manager is None:
        # In production, this would be properly injected
        from ..sdks.event_bus import EventBusSDK
        dlq_manager = DLQManager(EventBusSDK())
    return dlq_manager


def get_workflow_ops_manager() -> WorkflowOperationsManager:
    """Get workflow operations manager dependency."""
    global workflow_ops_manager
    if workflow_ops_manager is None:
        # In production, this would be properly injected
        from ..sdks.event_bus import EventBusSDK
        workflow_ops_manager = WorkflowOperationsManager(EventBusSDK())
    return workflow_ops_manager


def get_schedule_ops_manager() -> ScheduleOperationsManager:
    """Get schedule operations manager dependency."""
    global schedule_ops_manager
    if schedule_ops_manager is None:
        # In production, this would be properly injected
        from ..sdks.event_bus import EventBusSDK
        schedule_ops_manager = ScheduleOperationsManager(EventBusSDK())
    return schedule_ops_manager


# API Endpoints
@router.post("/dlq/replay", response_model=DLQReplayResponse)
async def replay_dlq_messages(
    request: DLQReplayRequest,
    tenant_id: str = Depends(get_current_tenant),
    dlq_mgr: DLQManager = Depends(get_dlq_manager),
    _: None = Depends(require_permissions(["events:dlq:replay"]))
):
    """Replay messages from Dead Letter Queue."""
    return await dlq_mgr.replay_messages(tenant_id, request)


@router.get("/dlq/replay/{replay_id}")
async def get_replay_status(
    replay_id: str = Path(..., description="Replay operation ID"),
    tenant_id: str = Depends(get_current_tenant),
    dlq_mgr: DLQManager = Depends(get_dlq_manager),
    _: None = Depends(require_permissions(["events:dlq:read"]))
):
    """Get status of a DLQ replay operation."""
    if replay_id not in dlq_mgr.active_replays:
        raise HTTPException(status_code=404, detail="Replay operation not found")

    replay_info = dlq_mgr.active_replays[replay_id]

    # Check tenant access
    if replay_info["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return replay_info


@router.post("/workflow/step/retry", response_model=OperationResponse)
async def retry_workflow_step(
    request: StepRetryRequest,
    tenant_id: str = Depends(get_current_tenant),
    workflow_mgr: WorkflowOperationsManager = Depends(get_workflow_ops_manager),
    _: None = Depends(require_permissions(["workflow:step:retry"]))
):
    """Retry a failed workflow step."""
    return await workflow_mgr.retry_step(tenant_id, request)


@router.post("/workflow/step/skip", response_model=OperationResponse)
async def skip_workflow_step(
    request: StepSkipRequest,
    tenant_id: str = Depends(get_current_tenant),
    workflow_mgr: WorkflowOperationsManager = Depends(get_workflow_ops_manager),
    _: None = Depends(require_permissions(["workflow:step:skip"]))
):
    """Skip a workflow step."""
    return await workflow_mgr.skip_step(tenant_id, request)


@router.post("/workflow/run/cancel", response_model=OperationResponse)
async def cancel_workflow_run(
    request: RunCancelRequest,
    tenant_id: str = Depends(get_current_tenant),
    workflow_mgr: WorkflowOperationsManager = Depends(get_workflow_ops_manager),
    _: None = Depends(require_permissions(["workflow:run:cancel"]))
):
    """Cancel a workflow run."""
    return await workflow_mgr.cancel_run(tenant_id, request)


@router.post("/schedule/pause", response_model=OperationResponse)
async def pause_schedule(
    request: SchedulePauseRequest,
    tenant_id: str = Depends(get_current_tenant),
    schedule_mgr: ScheduleOperationsManager = Depends(get_schedule_ops_manager),
    _: None = Depends(require_permissions(["schedule:pause"]))
):
    """Pause a schedule."""
    return await schedule_mgr.pause_schedule(tenant_id, request)


@router.post("/schedule/resume", response_model=OperationResponse)
async def resume_schedule(
    request: ScheduleResumeRequest,
    tenant_id: str = Depends(get_current_tenant),
    schedule_mgr: ScheduleOperationsManager = Depends(get_schedule_ops_manager),
    _: None = Depends(require_permissions(["schedule:resume"]))
):
    """Resume a paused schedule."""
    return await schedule_mgr.resume_schedule(tenant_id, request)


@router.get("/schedule/{schedule_id}/status")
async def get_schedule_status(
    schedule_id: str = Path(..., description="Schedule ID"),
    tenant_id: str = Depends(get_current_tenant),
    schedule_mgr: ScheduleOperationsManager = Depends(get_schedule_ops_manager),
    _: None = Depends(require_permissions(["schedule:read"]))
):
    """Get schedule status."""
    if schedule_id in schedule_mgr.paused_schedules:
        paused_info = schedule_mgr.paused_schedules[schedule_id]

        # Check tenant access
        if paused_info["tenant_id"] != tenant_id:
            raise HTTPException(status_code=403, detail="Access denied")

        return {
            "schedule_id": schedule_id,
            "status": "paused",
            "pause_reason": paused_info["pause_reason"],
            "paused_at": paused_info["paused_at"].isoformat(),
            "pause_until": paused_info["pause_until"].isoformat() if paused_info["pause_until"] else None,
            "pause_duration_seconds": (datetime.now(timezone.utc) - paused_info["paused_at"]).total_seconds()
        }
    else:
        return {
            "schedule_id": schedule_id,
            "status": "running",
            "pause_reason": None,
            "paused_at": None,
            "pause_until": None,
            "pause_duration_seconds": 0
        }
