"""
Tasks Module Router - DRY Migration
Task management endpoints using RouterFactory patterns.
"""

from typing import Any
from uuid import UUID

from fastapi import Depends, Query
from pydantic import BaseModel, Field

from dotmac.application import RouterFactory, standard_exception_handler
from dotmac_shared.api.dependencies import (
    PaginatedDependencies,
    StandardDependencies,
    get_paginated_deps,
    get_standard_deps,
)

# === Task Schemas ===


class TaskAssignmentRequest(BaseModel):
    """Request schema for task assignment."""

    assignee_id: UUID = Field(..., description="User ID to assign task to")
    due_date: str | None = Field(None, description="Task due date")
    priority: str = Field("medium", description="Task priority")


class TaskStatusUpdateRequest(BaseModel):
    """Request schema for task status updates."""

    status: str = Field(..., description="New task status")
    completion_notes: str | None = Field(None, description="Completion notes")
    progress_percentage: int | None = Field(
        None, ge=0, le=100, description="Progress percentage"
    )


# === Main Tasks Router ===

tasks_router = RouterFactory.create_standard_router(
    prefix="/tasks",
    tags=["tasks"],
)


# === Task Management ===


@tasks_router.get("/list", response_model=list[dict[str, Any]])
@standard_exception_handler
async def list_tasks(
    status: str | None = Query(None, description="Filter by task status"),
    priority: str | None = Query(None, description="Filter by task priority"),
    assignee_id: UUID | None = Query(None, description="Filter by assignee"),
    category: str | None = Query(None, description="Filter by task category"),
    deps: PaginatedDependencies = Depends(get_paginated_deps),
) -> list[dict[str, Any]]:
    """List tasks with filtering options."""
    # Mock implementation
    tasks = [
        {
            "id": "task-001",
            "title": "Update system configurations",
            "description": "Review and update all system configuration files",
            "status": status or "pending",
            "priority": priority or "medium",
            "category": category or "maintenance",
            "assignee_id": str(assignee_id) if assignee_id else "user-123",
            "created_at": "2025-01-15T10:00:00Z",
            "due_date": "2025-01-20T18:00:00Z",
            "progress_percentage": 25,
        },
        {
            "id": "task-002",
            "title": "Deploy new feature",
            "description": "Deploy the latest feature release to production",
            "status": "in_progress",
            "priority": "high",
            "category": "deployment",
            "assignee_id": "user-456",
            "created_at": "2025-01-14T14:30:00Z",
            "due_date": "2025-01-16T12:00:00Z",
            "progress_percentage": 75,
        },
    ]

    return tasks[: deps.pagination.size]


@tasks_router.post("/{task_id}/assign", response_model=dict[str, Any])
@standard_exception_handler
async def assign_task(
    task_id: str,
    assignment_request: TaskAssignmentRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Assign a task to a user."""
    return {
        "task_id": task_id,
        "assignee_id": str(assignment_request.assignee_id),
        "due_date": assignment_request.due_date,
        "priority": assignment_request.priority,
        "assigned_by": deps.user_id,
        "assigned_at": "2025-01-15T10:30:00Z",
        "status": "assigned",
        "message": "Task assigned successfully",
    }


@tasks_router.post("/{task_id}/status", response_model=dict[str, Any])
@standard_exception_handler
async def update_task_status(
    task_id: str,
    status_request: TaskStatusUpdateRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Update task status and progress."""
    return {
        "task_id": task_id,
        "status": status_request.status,
        "progress_percentage": status_request.progress_percentage,
        "completion_notes": status_request.completion_notes,
        "updated_by": deps.user_id,
        "updated_at": "2025-01-15T10:30:00Z",
        "message": "Task status updated successfully",
    }


# === Health Check ===


@tasks_router.get("/health", response_model=dict[str, Any])
@standard_exception_handler
async def task_service_health(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Check task service health."""
    return {
        "status": "healthy",
        "active_tasks": 125,
        "completed_today": 23,
        "overdue_tasks": 5,
        "service_uptime": "99.9%",
    }


# Export the router
__all__ = ["tasks_router"]
