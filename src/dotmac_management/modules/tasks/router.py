"""
Task Management and Monitoring API Endpoints

Provides comprehensive API endpoints for monitoring and managing background tasks,
workflows, and task system operations. Includes real-time progress tracking,
task cancellation, retry operations, and system health monitoring.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID
import asyncio

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query

from dotmac_shared.tasks import (
    TaskEngine, TaskQueue, WorkflowOrchestrator, TaskMonitor,
    TaskStatus, TaskPriority, TaskResult
)
from dotmac_shared.tasks.decorators import standard_exception_handler
from dotmac_shared.auth import get_current_tenant_id
from dotmac_shared.dependencies import get_redis_client

from .schemas import (
    TaskStatusResponse, WorkflowStatusResponse, QueueStatsResponse,
    WorkerStatsResponse, SystemHealthResponse, TaskCancelRequest,
    TaskRetryRequest, BulkTaskOperationRequest, TaskQueryRequest,
    TaskListResponse, WorkflowListResponse, BulkOperationResponse,
    TaskMetricsResponse, TaskProgressMessage, WorkflowProgressMessage,
    SystemMetricsMessage
)

router = APIRouter(tags=["Task Management"])


# Dependency Functions
async def get_task_engine() -> TaskEngine:
    """Get task engine instance"""
    redis_client = await get_redis_client()
    return TaskEngine(redis_client)


async def get_task_monitor() -> TaskMonitor:
    """Get task monitor instance"""
    redis_client = await get_redis_client()
    return TaskMonitor(redis_client)


async def get_workflow_orchestrator() -> WorkflowOrchestrator:
    """Get workflow orchestrator instance"""
    redis_client = await get_redis_client()
    return WorkflowOrchestrator(redis_client)


# Task Status and Information Endpoints
@router.get("/status/{task_id}", response_model=TaskStatusResponse)
@standard_exception_handler
async def get_task_status(
    task_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    engine: TaskEngine = Depends(get_task_engine)
) -> TaskStatusResponse:
    """Get detailed status information for a specific task"""
    
    task_data = await engine.get_task_status(task_id, tenant_id)
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskStatusResponse(**task_data)


@router.post("/query", response_model=TaskListResponse)
@standard_exception_handler
async def query_tasks(
    query: TaskQueryRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    engine: TaskEngine = Depends(get_task_engine)
) -> TaskListResponse:
    """Query tasks with advanced filtering and pagination"""
    
    # Build filters from query
    filters = {}
    if query.status:
        filters["status"] = query.status
    if query.priority:
        filters["priority"] = query.priority
    if query.task_type:
        filters["task_type"] = query.task_type
    if query.user_id:
        filters["user_id"] = query.user_id
    if query.created_after:
        filters["created_after"] = query.created_after
    if query.created_before:
        filters["created_before"] = query.created_before
    
    # Query tasks with total count
    result = await engine.query_tasks(
        tenant_id=query.tenant_id or tenant_id,
        filters=filters,
        limit=query.limit,
        offset=query.offset,
        order_by=query.order_by,
        order_direction=query.order_direction
    )
    
    tasks = [TaskStatusResponse(**task) for task in result["tasks"]]
    
    return TaskListResponse(
        tasks=tasks,
        total_count=result["total_count"],
        page_info={
            "limit": query.limit,
            "offset": query.offset,
            "has_next": len(tasks) == query.limit,
            "has_previous": query.offset > 0
        },
        filters_applied=filters
    )


@router.get("/list", response_model=List[TaskStatusResponse])
@standard_exception_handler
async def list_tasks(
    tenant_id: str = Depends(get_current_tenant_id),
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by task priority"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of tasks to return"),
    offset: int = Query(0, ge=0, description="Number of tasks to skip"),
    engine: TaskEngine = Depends(get_task_engine)
) -> List[TaskStatusResponse]:
    """List tasks with basic filtering (legacy endpoint)"""
    
    filters = {}
    if status:
        filters["status"] = status
    if priority:
        filters["priority"] = priority
    
    result = await engine.query_tasks(
        tenant_id=tenant_id,
        filters=filters,
        limit=limit,
        offset=offset
    )
    
    return [TaskStatusResponse(**task) for task in result["tasks"]]


@router.get("/workflows/{workflow_id}", response_model=WorkflowStatusResponse)
@standard_exception_handler
async def get_workflow_status(
    workflow_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    orchestrator: WorkflowOrchestrator = Depends(get_workflow_orchestrator)
) -> WorkflowStatusResponse:
    """Get detailed status information for a specific workflow"""
    
    workflow_data = await orchestrator.get_workflow_status(workflow_id, tenant_id)
    if not workflow_data:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return WorkflowStatusResponse(**workflow_data)


@router.get("/workflows", response_model=WorkflowListResponse)
@standard_exception_handler
async def list_workflows(
    tenant_id: str = Depends(get_current_tenant_id),
    status: Optional[str] = Query(None, description="Filter by workflow status"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    orchestrator: WorkflowOrchestrator = Depends(get_workflow_orchestrator)
) -> WorkflowListResponse:
    """List workflows with optional filtering"""
    
    result = await orchestrator.query_workflows(
        tenant_id=tenant_id,
        status_filter=status,
        limit=limit,
        offset=offset
    )
    
    workflows = [WorkflowStatusResponse(**workflow) for workflow in result["workflows"]]
    
    return WorkflowListResponse(
        workflows=workflows,
        total_count=result["total_count"],
        page_info={
            "limit": limit,
            "offset": offset,
            "has_next": len(workflows) == limit,
            "has_previous": offset > 0
        },
        filters_applied={"status": status} if status else {}
    )


# Task Management Operations
@router.post("/cancel/{task_id}")
@standard_exception_handler
async def cancel_task(
    task_id: str,
    request: TaskCancelRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    engine: TaskEngine = Depends(get_task_engine)
) -> Dict[str, Any]:
    """Cancel a running or pending task"""
    
    success = await engine.cancel_task(
        task_id=task_id,
        tenant_id=tenant_id,
        reason=request.reason,
        force=request.force
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Task cannot be cancelled")
    
    return {
        "message": "Task cancelled successfully",
        "task_id": task_id,
        "cancelled_at": datetime.now(timezone.utc).isoformat()
    }


@router.post("/retry/{task_id}")
@standard_exception_handler
async def retry_task(
    task_id: str,
    request: TaskRetryRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    engine: TaskEngine = Depends(get_task_engine)
) -> Dict[str, Any]:
    """Retry a failed task"""
    
    new_task_id = await engine.retry_task(
        task_id=task_id,
        tenant_id=tenant_id,
        reset_retry_count=request.reset_retry_count,
        priority=request.priority
    )
    
    if not new_task_id:
        raise HTTPException(status_code=400, detail="Task cannot be retried")
    
    return {
        "message": "Task retry initiated",
        "original_task_id": task_id,
        "new_task_id": new_task_id,
        "retried_at": datetime.now(timezone.utc).isoformat()
    }


@router.delete("/delete/{task_id}")
@standard_exception_handler
async def delete_task(
    task_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    engine: TaskEngine = Depends(get_task_engine)
) -> Dict[str, Any]:
    """Delete a task and its associated data"""
    
    success = await engine.delete_task(task_id, tenant_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "message": "Task deleted successfully",
        "task_id": task_id,
        "deleted_at": datetime.now(timezone.utc).isoformat()
    }


@router.post("/bulk-operation", response_model=BulkOperationResponse)
@standard_exception_handler
async def bulk_task_operation(
    request: BulkTaskOperationRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    engine: TaskEngine = Depends(get_task_engine)
) -> BulkOperationResponse:
    """Perform bulk operations on multiple tasks"""
    
    start_time = datetime.now(timezone.utc)
    
    results = await engine.bulk_operation(
        task_ids=request.task_ids,
        operation=request.operation,
        tenant_id=tenant_id,
        parameters=request.parameters or {}
    )
    
    end_time = datetime.now(timezone.utc)
    processing_time = (end_time - start_time).total_seconds()
    
    return BulkOperationResponse(
        operation=request.operation,
        requested_tasks=len(request.task_ids),
        successful_operations=len([r for r in results if r["success"]]),
        failed_operations=len([r for r in results if not r["success"]]),
        processing_time=processing_time,
        results=results,
        processed_at=end_time
    )


# System Monitoring and Statistics
@router.get("/stats/queue", response_model=QueueStatsResponse)
@standard_exception_handler
async def get_queue_stats(
    tenant_id: Optional[str] = Depends(get_current_tenant_id),
    monitor: TaskMonitor = Depends(get_task_monitor)
) -> QueueStatsResponse:
    """Get queue statistics and metrics"""
    
    stats = await monitor.get_queue_stats(tenant_id)
    return QueueStatsResponse(**stats)


@router.get("/stats/workers", response_model=WorkerStatsResponse)
@standard_exception_handler
async def get_worker_stats(
    monitor: TaskMonitor = Depends(get_task_monitor)
) -> WorkerStatsResponse:
    """Get worker statistics and performance metrics"""
    
    stats = await monitor.get_worker_stats()
    return WorkerStatsResponse(**stats)


@router.get("/health", response_model=SystemHealthResponse)
@standard_exception_handler
async def get_system_health(
    monitor: TaskMonitor = Depends(get_task_monitor)
) -> SystemHealthResponse:
    """Get overall system health and status"""
    
    health = await monitor.get_system_health()
    return SystemHealthResponse(**health)


@router.get("/metrics", response_model=TaskMetricsResponse)
@standard_exception_handler
async def get_detailed_metrics(
    tenant_id: Optional[str] = Depends(get_current_tenant_id),
    hours: int = Query(24, ge=1, le=168, description="Hours of metrics to retrieve"),
    monitor: TaskMonitor = Depends(get_task_monitor)
) -> TaskMetricsResponse:
    """Get detailed metrics and analytics"""
    
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)
    
    metrics = await monitor.get_detailed_metrics(
        tenant_id=tenant_id,
        start_time=start_time,
        end_time=end_time
    )
    
    return TaskMetricsResponse(
        period={
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "hours": hours
        },
        tenant_id=tenant_id,
        task_volume=metrics.get("task_volume", {}),
        completion_rate=metrics.get("completion_rate", {}),
        error_trends=metrics.get("error_trends", {}),
        processing_times=metrics.get("processing_times", {}),
        queue_depths=metrics.get("queue_depths", {}),
        throughput=metrics.get("throughput", {}),
        resource_utilization=metrics.get("resource_utilization", {}),
        cost_metrics=metrics.get("cost_metrics", {})
    )


# Real-time WebSocket Endpoints
@router.websocket("/ws/progress/{task_id}")
async def websocket_task_progress(
    websocket: WebSocket,
    task_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    monitor: TaskMonitor = Depends(get_task_monitor)
):
    """WebSocket endpoint for real-time task progress updates"""
    
    await websocket.accept()
    
    try:
        while True:
            # Get current task status and progress
            task_data = await monitor.get_task_progress(task_id, tenant_id)
            
            if not task_data:
                await websocket.send_json({
                    "error": "Task not found",
                    "task_id": task_id
                })
                break
            
            message = TaskProgressMessage(
                task_id=task_id,
                status=task_data["status"],
                progress=task_data["progress"],
                error=task_data.get("error"),
                timestamp=datetime.now(timezone.utc)
            )
            await websocket.send_json(message.model_dump())
            
            # Break if task is completed or failed
            if task_data["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                break
            
            # Wait before next update
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "error": str(e),
            "task_id": task_id
        })


@router.websocket("/ws/workflow/{workflow_id}")
async def websocket_workflow_progress(
    websocket: WebSocket,
    workflow_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    orchestrator: WorkflowOrchestrator = Depends(get_workflow_orchestrator)
):
    """WebSocket endpoint for real-time workflow progress updates"""
    
    await websocket.accept()
    
    try:
        while True:
            # Get current workflow status
            workflow_data = await orchestrator.get_workflow_progress(workflow_id, tenant_id)
            
            if not workflow_data:
                await websocket.send_json({
                    "error": "Workflow not found",
                    "workflow_id": workflow_id
                })
                break
            
            message = WorkflowProgressMessage(
                workflow_id=workflow_id,
                status=workflow_data["status"],
                current_step=workflow_data.get("current_step"),
                progress=workflow_data["progress"],
                completed_steps=workflow_data["completed_steps"],
                total_steps=workflow_data["total_steps"],
                timestamp=datetime.now(timezone.utc)
            )
            await websocket.send_json(message.model_dump())
            
            # Break if workflow is completed or failed
            if workflow_data["status"] in ["completed", "failed", "cancelled"]:
                break
            
            # Wait before next update
            await asyncio.sleep(2)
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "error": str(e),
            "workflow_id": workflow_id
        })


@router.websocket("/ws/system-metrics")
async def websocket_system_metrics(
    websocket: WebSocket,
    monitor: TaskMonitor = Depends(get_task_monitor)
):
    """WebSocket endpoint for real-time system metrics"""
    
    await websocket.accept()
    
    try:
        while True:
            # Get current system metrics
            metrics = await monitor.get_real_time_metrics()
            
            message = SystemMetricsMessage(
                timestamp=datetime.now(timezone.utc),
                queue_depth=metrics["queue_depth"],
                active_tasks=metrics["active_tasks"],
                worker_utilization=metrics["worker_utilization"],
                error_rate=metrics["error_rate"],
                throughput=metrics["throughput"],
                memory_usage=metrics.get("memory_usage", {})
            )
            await websocket.send_json(message.model_dump())
            
            # Wait before next update
            await asyncio.sleep(5)
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "error": str(e)
        })


# Admin Endpoints (require admin permissions)
@router.post("/admin/purge-completed")
@standard_exception_handler
async def purge_completed_tasks(
    older_than_days: int = Query(7, ge=1, le=365),
    dry_run: bool = Query(False),
    tenant_id: Optional[str] = Depends(get_current_tenant_id),
    engine: TaskEngine = Depends(get_task_engine)
) -> Dict[str, Any]:
    """Purge completed tasks older than specified days"""
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    
    result = await engine.purge_completed_tasks(
        cutoff_date=cutoff_date,
        tenant_id=tenant_id,
        dry_run=dry_run
    )
    
    return {
        "message": "Purge operation completed" if not dry_run else "Dry run completed",
        "cutoff_date": cutoff_date.isoformat(),
        "tasks_affected": result["count"],
        "dry_run": dry_run,
        "processed_at": datetime.now(timezone.utc).isoformat()
    }


@router.post("/admin/reset-dead-letter")
@standard_exception_handler
async def reset_dead_letter_queue(
    tenant_id: Optional[str] = Depends(get_current_tenant_id),
    engine: TaskEngine = Depends(get_task_engine)
) -> Dict[str, Any]:
    """Reset dead letter queue and move tasks back to main queue"""
    
    result = await engine.reset_dead_letter_queue(tenant_id)
    
    return {
        "message": "Dead letter queue reset completed",
        "tasks_moved": result["count"],
        "processed_at": datetime.now(timezone.utc).isoformat()
    }