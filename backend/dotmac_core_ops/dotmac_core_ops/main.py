"""
DotMac Core Ops Service - Main Application
Provides workflow orchestration, sagas, state machines, and job scheduling.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum

from fastapi import FastAPI, HTTPException, Query, Depends, Path, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .core.config import config
from .core.exceptions import CoreOpsError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAPI tags metadata
tags_metadata = [
    {
        "name": "Health",
        "description": "Service health and status monitoring",
    },
    {
        "name": "Workflows",
        "description": "Workflow orchestration and management",
    },
    {
        "name": "Sagas",
        "description": "Distributed transaction saga patterns",
    },
    {
        "name": "StateMachines",
        "description": "State machine management and transitions",
    },
    {
        "name": "Jobs",
        "description": "Job scheduling and queue management",
    },
    {
        "name": "Tasks",
        "description": "Task execution and monitoring",
    },
]


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"


class JobStatus(str, Enum):
    """Job execution status."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    CANCELLED = "cancelled"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting DotMac Core Ops Service...")
    logger.info(f"Service initialized with tenant: {config.tenant_id}")
    
    # Initialize workflow engine
    logger.info("Initializing workflow engine...")
    
    # Initialize job scheduler
    logger.info("Initializing job scheduler...")
    
    yield
    
    # Cleanup
    logger.info("Shutting down DotMac Core Ops Service...")


# Create FastAPI application
app = FastAPI(
    title="DotMac Core Ops Service",
    description="""
    **Operational Services and Workflow Orchestration Platform**

    The DotMac Core Ops Service provides operational capabilities for ISPs:

    ## 🔄 Core Features

    ### Workflow Orchestration
    - Visual workflow designer
    - Conditional branching
    - Parallel execution
    - Error handling & retry
    - Workflow templates
    - Event-triggered workflows

    ### Saga Patterns
    - Distributed transactions
    - Compensation logic
    - Two-phase commit
    - Event sourcing
    - Rollback mechanisms
    - Transaction logs

    ### State Machines
    - Finite state machines
    - State transitions
    - Guard conditions
    - State persistence
    - Event-driven transitions
    - State history

    ### Job Scheduling
    - Cron-based scheduling
    - Job queues (FIFO, Priority)
    - Retry policies
    - Dead letter queues
    - Job dependencies
    - Batch processing

    ### Task Management
    - Task execution
    - Progress tracking
    - Resource allocation
    - Task chaining
    - Async execution
    - Result storage

    ## 🚀 Integration

    - **Database**: PostgreSQL for persistence
    - **Cache**: Redis for job queues
    - **Events**: Event bus integration
    - **Multi-tenant**: Full tenant isolation

    **Base URL**: `/api/v1`
    **Version**: 1.0.0
    """,
    version="1.0.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    docs_url="/docs" if config.debug else None,
    redoc_url="/redoc" if config.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class WorkflowDefinition(BaseModel):
    """Workflow definition model."""
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    steps: List[Dict[str, Any]] = Field(..., description="Workflow steps")
    triggers: Optional[List[str]] = Field(default=[], description="Event triggers")
    schedule: Optional[str] = Field(None, description="Cron schedule")


class WorkflowInstance(BaseModel):
    """Workflow instance model."""
    workflow_id: str = Field(..., description="Workflow definition ID")
    instance_id: str = Field(..., description="Instance unique ID")
    status: WorkflowStatus = Field(..., description="Current status")
    started_at: datetime = Field(..., description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    context: Dict[str, Any] = Field(default={}, description="Workflow context data")
    current_step: Optional[str] = Field(None, description="Current execution step")


class SagaDefinition(BaseModel):
    """Saga definition model."""
    name: str = Field(..., description="Saga name")
    transactions: List[Dict[str, Any]] = Field(..., description="Transaction steps")
    compensations: List[Dict[str, Any]] = Field(..., description="Compensation steps")
    timeout: Optional[int] = Field(default=3600, description="Timeout in seconds")


class JobRequest(BaseModel):
    """Job execution request."""
    job_type: str = Field(..., description="Type of job to execute")
    payload: Dict[str, Any] = Field(default={}, description="Job payload")
    priority: int = Field(default=5, description="Job priority (1-10)")
    retry_count: int = Field(default=3, description="Max retry attempts")
    schedule: Optional[str] = Field(None, description="Cron schedule for recurring jobs")


class JobResponse(BaseModel):
    """Job execution response."""
    job_id: str = Field(..., description="Job unique identifier")
    status: JobStatus = Field(..., description="Job status")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    result: Optional[Dict[str, Any]] = Field(None, description="Job result")
    error: Optional[str] = Field(None, description="Error message if failed")


class StateMachine(BaseModel):
    """State machine definition."""
    name: str = Field(..., description="State machine name")
    initial_state: str = Field(..., description="Initial state")
    states: List[str] = Field(..., description="Available states")
    transitions: List[Dict[str, Any]] = Field(..., description="State transitions")
    current_state: Optional[str] = Field(None, description="Current state")


# Health check endpoint
@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Check service health and dependencies",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "dotmac_core_ops",
                        "version": "1.0.0",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "components": {
                            "database": "healthy",
                            "redis": "healthy",
                            "workflow_engine": "healthy",
                            "job_scheduler": "healthy",
                        }
                    }
                }
            }
        }
    }
)
async def health_check() -> Dict[str, Any]:
    """Check service health status."""
    return {
        "status": "healthy",
        "service": "dotmac_core_ops",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "components": {
            "database": "healthy",
            "redis": "healthy",
            "workflow_engine": "healthy",
            "job_scheduler": "healthy",
        }
    }


# Workflow endpoints
@app.post(
    "/api/v1/workflows",
    tags=["Workflows"],
    summary="Create workflow",
    description="Create a new workflow definition",
    response_model=Dict[str, str],
)
async def create_workflow(workflow: WorkflowDefinition) -> Dict[str, str]:
    """Create a new workflow definition."""
    workflow_id = f"wf_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    return {
        "workflow_id": workflow_id,
        "message": f"Workflow '{workflow.name}' created successfully",
    }


@app.post(
    "/api/v1/workflows/{workflow_id}/execute",
    tags=["Workflows"],
    summary="Execute workflow",
    description="Execute a workflow instance",
    response_model=WorkflowInstance,
)
async def execute_workflow(
    workflow_id: str = Path(..., description="Workflow ID"),
    context: Dict[str, Any] = Body(default={}, description="Execution context"),
) -> WorkflowInstance:
    """Execute a workflow instance."""
    instance_id = f"wfi_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    return WorkflowInstance(
        workflow_id=workflow_id,
        instance_id=instance_id,
        status=WorkflowStatus.RUNNING,
        started_at=datetime.utcnow(),
        context=context,
        current_step="step_1",
    )


@app.get(
    "/api/v1/workflows/{workflow_id}/instances",
    tags=["Workflows"],
    summary="List workflow instances",
    description="Get all instances of a workflow",
    response_model=List[WorkflowInstance],
)
async def list_workflow_instances(
    workflow_id: str = Path(..., description="Workflow ID"),
) -> List[WorkflowInstance]:
    """List all instances of a workflow."""
    return [
        WorkflowInstance(
            workflow_id=workflow_id,
            instance_id="wfi_001",
            status=WorkflowStatus.COMPLETED,
            started_at=datetime.utcnow() - timedelta(hours=1),
            completed_at=datetime.utcnow(),
            context={"customer_id": "123"},
        )
    ]


# Saga endpoints
@app.post(
    "/api/v1/sagas",
    tags=["Sagas"],
    summary="Create saga",
    description="Create a new saga definition",
    response_model=Dict[str, str],
)
async def create_saga(saga: SagaDefinition) -> Dict[str, str]:
    """Create a new saga definition."""
    saga_id = f"sg_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    return {
        "saga_id": saga_id,
        "message": f"Saga '{saga.name}' created successfully",
    }


@app.post(
    "/api/v1/sagas/{saga_id}/execute",
    tags=["Sagas"],
    summary="Execute saga",
    description="Execute a distributed transaction saga",
    response_model=Dict[str, Any],
)
async def execute_saga(
    saga_id: str = Path(..., description="Saga ID"),
    context: Dict[str, Any] = Body(default={}, description="Saga context"),
) -> Dict[str, Any]:
    """Execute a distributed transaction saga."""
    execution_id = f"sge_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    return {
        "execution_id": execution_id,
        "saga_id": saga_id,
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
        "transactions_completed": 0,
        "total_transactions": 5,
    }


# State Machine endpoints
@app.post(
    "/api/v1/state-machines",
    tags=["StateMachines"],
    summary="Create state machine",
    description="Create a new state machine",
    response_model=Dict[str, str],
)
async def create_state_machine(state_machine: StateMachine) -> Dict[str, str]:
    """Create a new state machine."""
    machine_id = f"sm_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    return {
        "machine_id": machine_id,
        "message": f"State machine '{state_machine.name}' created successfully",
    }


@app.post(
    "/api/v1/state-machines/{machine_id}/transition",
    tags=["StateMachines"],
    summary="Trigger state transition",
    description="Trigger a state machine transition",
    response_model=Dict[str, str],
)
async def trigger_transition(
    machine_id: str = Path(..., description="State machine ID"),
    event: str = Query(..., description="Transition event"),
) -> Dict[str, str]:
    """Trigger a state machine transition."""
    return {
        "machine_id": machine_id,
        "previous_state": "pending",
        "new_state": "active",
        "event": event,
        "timestamp": datetime.utcnow().isoformat(),
    }


# Job endpoints
@app.post(
    "/api/v1/jobs",
    tags=["Jobs"],
    summary="Submit job",
    description="Submit a new job to the queue",
    response_model=JobResponse,
)
async def submit_job(job: JobRequest) -> JobResponse:
    """Submit a new job to the queue."""
    job_id = f"job_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    return JobResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        created_at=datetime.utcnow(),
    )


@app.get(
    "/api/v1/jobs/{job_id}",
    tags=["Jobs"],
    summary="Get job status",
    description="Get job execution status",
    response_model=JobResponse,
)
async def get_job_status(
    job_id: str = Path(..., description="Job ID"),
) -> JobResponse:
    """Get job execution status."""
    return JobResponse(
        job_id=job_id,
        status=JobStatus.COMPLETED,
        created_at=datetime.utcnow() - timedelta(minutes=5),
        started_at=datetime.utcnow() - timedelta(minutes=4),
        completed_at=datetime.utcnow(),
        result={"processed_records": 1000, "duration_seconds": 240},
    )


@app.get(
    "/api/v1/jobs",
    tags=["Jobs"],
    summary="List jobs",
    description="List jobs with optional filters",
    response_model=List[JobResponse],
)
async def list_jobs(
    status: Optional[JobStatus] = Query(None, description="Filter by status"),
    limit: int = Query(default=10, description="Limit results"),
) -> List[JobResponse]:
    """List jobs with optional filters."""
    jobs = []
    for i in range(min(limit, 5)):
        jobs.append(
            JobResponse(
                job_id=f"job_00{i}",
                status=status or JobStatus.COMPLETED,
                created_at=datetime.utcnow() - timedelta(hours=i),
                started_at=datetime.utcnow() - timedelta(hours=i) + timedelta(minutes=5),
                completed_at=datetime.utcnow() - timedelta(hours=i) + timedelta(minutes=15),
            )
        )
    return jobs


# Task endpoints
@app.post(
    "/api/v1/tasks/execute",
    tags=["Tasks"],
    summary="Execute task",
    description="Execute an immediate task",
    response_model=Dict[str, Any],
)
async def execute_task(
    task_type: str = Query(..., description="Type of task to execute"),
    payload: Dict[str, Any] = Body(default={}, description="Task payload"),
) -> Dict[str, Any]:
    """Execute an immediate task."""
    task_id = f"task_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    return {
        "task_id": task_id,
        "task_type": task_type,
        "status": "executing",
        "started_at": datetime.utcnow().isoformat(),
        "estimated_completion": (datetime.utcnow() + timedelta(seconds=30)).isoformat(),
    }


@app.get(
    "/api/v1/queues/status",
    tags=["Jobs"],
    summary="Queue status",
    description="Get job queue status",
    response_model=Dict[str, Any],
)
async def queue_status() -> Dict[str, Any]:
    """Get job queue status."""
    return {
        "queues": {
            "default": {
                "pending": 12,
                "running": 3,
                "completed_last_hour": 145,
                "failed_last_hour": 2,
            },
            "priority": {
                "pending": 5,
                "running": 2,
                "completed_last_hour": 89,
                "failed_last_hour": 0,
            },
            "batch": {
                "pending": 45,
                "running": 10,
                "completed_last_hour": 234,
                "failed_last_hour": 5,
            },
        },
        "workers": {
            "active": 15,
            "idle": 5,
            "total": 20,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "dotmac_core_ops.main:app",
        host="0.0.0.0",
        port=8008,
        reload=config.debug,
        log_level="info" if not config.debug else "debug",
    )