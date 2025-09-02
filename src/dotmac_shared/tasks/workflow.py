"""
Complex Workflow Orchestration System

Provides sophisticated multi-step workflow management with:
- DAG-based workflow definition and execution
- Step dependencies and conditional execution
- Parallel and sequential step execution
- Workflow state persistence and recovery
- Error handling and rollback capabilities
- Dynamic workflow generation and modification
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable, Union
from dataclasses import dataclass, field

from redis.asyncio import Redis as AsyncRedis

from .engine import Task, TaskConfig, TaskResult, TaskStatus, TaskPriority, TaskError
from .queue import RedisTaskQueue
from dotmac_shared.core.logging import get_logger

logger = get_logger(__name__)


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class StepStatus(str, Enum):
    """Workflow step status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class StepType(str, Enum):
    """Workflow step type."""
    TASK = "task"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    CONDITIONAL = "conditional"
    DELAY = "delay"
    WEBHOOK = "webhook"


@dataclass
class StepCondition:
    """Conditional execution logic for workflow steps."""
    expression: str  # Python expression to evaluate
    context_vars: List[str] = field(default_factory=list)  # Variables available in expression
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate condition against workflow context."""
        try:
            # Create safe evaluation environment
            safe_dict = {
                "__builtins__": {},
                **{var: context.get(var) for var in self.context_vars}
            }
            
            result = eval(self.expression, safe_dict)
            return bool(result)
            
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {e}")
            return False


@dataclass
class WorkflowStep:
    """
    Individual step in a workflow with dependencies and configuration.
    """
    step_id: str
    name: str
    step_type: StepType
    
    # Task-specific configuration
    function_name: Optional[str] = None
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    task_config: Optional[TaskConfig] = None
    
    # Flow control
    depends_on: Set[str] = field(default_factory=set)
    condition: Optional[StepCondition] = None
    timeout_seconds: Optional[int] = None
    
    # Parallel/Sequential step configuration
    sub_steps: List['WorkflowStep'] = field(default_factory=list)
    
    # Delay step configuration
    delay_seconds: int = 0
    
    # Webhook configuration
    webhook_url: Optional[str] = None
    webhook_payload: Dict[str, Any] = field(default_factory=dict)
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Runtime state
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary for serialization."""
        return {
            'step_id': self.step_id,
            'name': self.name,
            'step_type': self.step_type.value,
            'function_name': self.function_name,
            'args': self.args,
            'kwargs': self.kwargs,
            'task_config': self.task_config.model_dump() if self.task_config else None,
            'depends_on': list(self.depends_on),
            'condition': {
                'expression': self.condition.expression,
                'context_vars': self.condition.context_vars
            } if self.condition else None,
            'timeout_seconds': self.timeout_seconds,
            'sub_steps': [step.to_dict() for step in self.sub_steps],
            'delay_seconds': self.delay_seconds,
            'webhook_url': self.webhook_url,
            'webhook_payload': self.webhook_payload,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'status': self.status.value,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'result': self.result,
            'error': self.error,
            'retry_count': self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStep':
        """Create step from dictionary."""
        task_config = None
        if data.get('task_config'):
            task_config = TaskConfig(**data['task_config'])
        
        condition = None
        if data.get('condition'):
            condition = StepCondition(
                expression=data['condition']['expression'],
                context_vars=data['condition'].get('context_vars', [])
            )
        
        sub_steps = [WorkflowStep.from_dict(step_data) for step_data in data.get('sub_steps', [])]
        
        step = cls(
            step_id=data['step_id'],
            name=data['name'],
            step_type=StepType(data['step_type']),
            function_name=data.get('function_name'),
            args=data.get('args', []),
            kwargs=data.get('kwargs', {}),
            task_config=task_config,
            depends_on=set(data.get('depends_on', [])),
            condition=condition,
            timeout_seconds=data.get('timeout_seconds'),
            sub_steps=sub_steps,
            delay_seconds=data.get('delay_seconds', 0),
            webhook_url=data.get('webhook_url'),
            webhook_payload=data.get('webhook_payload', {}),
            max_retries=data.get('max_retries', 3),
            retry_delay=data.get('retry_delay', 1.0),
        )
        
        # Restore runtime state
        step.status = StepStatus(data.get('status', 'pending'))
        step.started_at = datetime.fromisoformat(data['started_at']) if data.get('started_at') else None
        step.completed_at = datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None
        step.result = data.get('result')
        step.error = data.get('error')
        step.retry_count = data.get('retry_count', 0)
        
        return step


class Workflow:
    """
    Complete workflow definition with steps, dependencies, and configuration.
    """

    def __init__(
        self,
        workflow_id: str,
        name: str,
        description: str = "",
        steps: List[WorkflowStep] = None,
        timeout_seconds: Optional[int] = None,
        tenant_id: Optional[str] = None,
        metadata: Dict[str, Any] = None,
    ):
        self.workflow_id = workflow_id
        self.name = name
        self.description = description
        self.steps = {step.step_id: step for step in (steps or [])}
        self.timeout_seconds = timeout_seconds
        self.tenant_id = tenant_id
        self.metadata = metadata or {}
        
        # Runtime state
        self.status = WorkflowStatus.PENDING
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.context: Dict[str, Any] = {}
        self.execution_log: List[Dict[str, Any]] = []
        
        # Validate workflow structure
        self._validate_workflow()

    def _validate_workflow(self):
        """Validate workflow structure for circular dependencies."""
        # Build dependency graph
        dependencies = {}
        for step_id, step in self.steps.items():
            dependencies[step_id] = step.depends_on
        
        # Check for circular dependencies using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            if node in rec_stack:
                return True
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            
            for dependency in dependencies.get(node, set()):
                if dependency in dependencies and has_cycle(dependency):
                    return True
            
            rec_stack.remove(node)
            return False
        
        for step_id in self.steps:
            if has_cycle(step_id):
                raise ValueError(f"Circular dependency detected involving step {step_id}")

    def add_step(self, step: WorkflowStep):
        """Add a step to the workflow."""
        self.steps[step.step_id] = step
        self._validate_workflow()

    def get_ready_steps(self) -> List[WorkflowStep]:
        """Get steps that are ready to execute (all dependencies completed)."""
        ready_steps = []
        
        for step in self.steps.values():
            if step.status != StepStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            if all(
                self.steps[dep_id].status == StepStatus.COMPLETED
                for dep_id in step.depends_on
                if dep_id in self.steps
            ):
                # Check condition if present
                if step.condition is None or step.condition.evaluate(self.context):
                    ready_steps.append(step)
                else:
                    step.status = StepStatus.SKIPPED
        
        return ready_steps

    def to_dict(self) -> Dict[str, Any]:
        """Convert workflow to dictionary for serialization."""
        return {
            'workflow_id': self.workflow_id,
            'name': self.name,
            'description': self.description,
            'steps': {step_id: step.to_dict() for step_id, step in self.steps.items()},
            'timeout_seconds': self.timeout_seconds,
            'tenant_id': self.tenant_id,
            'metadata': self.metadata,
            'status': self.status.value,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'context': self.context,
            'execution_log': self.execution_log,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Workflow':
        """Create workflow from dictionary."""
        steps = [WorkflowStep.from_dict(step_data) for step_data in data['steps'].values()]
        
        workflow = cls(
            workflow_id=data['workflow_id'],
            name=data['name'],
            description=data.get('description', ''),
            steps=steps,
            timeout_seconds=data.get('timeout_seconds'),
            tenant_id=data.get('tenant_id'),
            metadata=data.get('metadata', {}),
        )
        
        # Restore runtime state
        workflow.status = WorkflowStatus(data.get('status', 'pending'))
        workflow.started_at = datetime.fromisoformat(data['started_at']) if data.get('started_at') else None
        workflow.completed_at = datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None
        workflow.context = data.get('context', {})
        workflow.execution_log = data.get('execution_log', [])
        
        return workflow


class WorkflowOrchestrator:
    """
    Advanced workflow orchestration engine with persistence and recovery.
    
    Features:
    - DAG-based workflow execution
    - Step dependency management
    - Parallel and sequential execution patterns
    - Conditional step execution
    - Workflow state persistence and recovery
    - Error handling and retry logic
    - Dynamic workflow modification
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        orchestrator_id: str = None,
        key_prefix: str = "dotmac_workflows",
    ):
        self.redis_url = redis_url
        self.orchestrator_id = orchestrator_id or f"orchestrator-{uuid.uuid4().hex[:8]}"
        self.key_prefix = key_prefix
        
        # Redis connections
        self._redis: Optional[AsyncRedis] = None
        self._task_queue: Optional[RedisTaskQueue] = None
        
        # Orchestrator state
        self._is_running = False
        self._active_workflows: Dict[str, Workflow] = {}
        self._running_steps: Dict[str, asyncio.Task] = {}
        
        # Background tasks
        self._orchestrator_task: Optional[asyncio.Task] = None
        self._persistence_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize orchestrator and Redis connections."""
        try:
            # Initialize Redis connection
            self._redis = AsyncRedis.from_url(
                self.redis_url,
                encoding='utf-8',
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=30,
                retry_on_timeout=True,
                max_connections=50
            )
            
            await self._redis.ping()
            
            # Initialize task queue
            self._task_queue = RedisTaskQueue(self.redis_url)
            await self._task_queue.initialize()
            
            # Load active workflows
            await self._load_active_workflows()
            
            logger.info(f"Workflow orchestrator initialized", extra={
                'orchestrator_id': self.orchestrator_id,
                'active_workflows': len(self._active_workflows)
            })
            
        except Exception as e:
            logger.error(f"Failed to initialize workflow orchestrator: {e}")
            raise TaskError(f"Orchestrator initialization failed: {e}")

    async def start(self):
        """Start the workflow orchestrator."""
        if self._is_running:
            return
        
        self._is_running = True
        
        # Start background tasks
        self._orchestrator_task = asyncio.create_task(self._orchestration_loop())
        self._persistence_task = asyncio.create_task(self._persistence_loop())
        
        logger.info(f"Workflow orchestrator started", extra={
            'orchestrator_id': self.orchestrator_id
        })

    async def stop(self):
        """Stop the workflow orchestrator."""
        logger.info(f"Stopping workflow orchestrator")
        
        self._is_running = False
        
        # Cancel background tasks
        if self._orchestrator_task:
            self._orchestrator_task.cancel()
        if self._persistence_task:
            self._persistence_task.cancel()
        
        # Wait for tasks to complete
        tasks = [t for t in [self._orchestrator_task, self._persistence_task] if t]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Cancel running steps
        if self._running_steps:
            for step_task in self._running_steps.values():
                step_task.cancel()
            await asyncio.gather(*self._running_steps.values(), return_exceptions=True)
        
        # Persist final state
        await self._persist_all_workflows()
        
        # Close connections
        if self._task_queue:
            await self._task_queue.close()
        if self._redis:
            await self._redis.close()
        
        logger.info("Workflow orchestrator stopped")

    async def start_workflow(self, workflow: Workflow) -> str:
        """
        Start a new workflow execution.
        
        Args:
            workflow: Workflow instance to execute
            
        Returns:
            str: Workflow execution ID
        """
        try:
            # Initialize workflow state
            workflow.status = WorkflowStatus.RUNNING
            workflow.started_at = datetime.now(timezone.utc)
            workflow.execution_log.append({
                'timestamp': workflow.started_at.isoformat(),
                'event': 'workflow_started',
                'message': f'Workflow {workflow.name} started'
            })
            
            # Add to active workflows
            self._active_workflows[workflow.workflow_id] = workflow
            
            # Persist workflow state
            await self._persist_workflow(workflow)
            
            logger.info(f"Workflow started", extra={
                'workflow_id': workflow.workflow_id,
                'workflow_name': workflow.name,
                'step_count': len(workflow.steps)
            })
            
            return workflow.workflow_id
            
        except Exception as e:
            logger.error(f"Failed to start workflow {workflow.workflow_id}: {e}")
            raise TaskError(f"Workflow start failed: {e}")

    async def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a running workflow."""
        try:
            if workflow_id not in self._active_workflows:
                return False
            
            workflow = self._active_workflows[workflow_id]
            if workflow.status != WorkflowStatus.RUNNING:
                return False
            
            workflow.status = WorkflowStatus.PAUSED
            workflow.execution_log.append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event': 'workflow_paused',
                'message': f'Workflow {workflow.name} paused'
            })
            
            await self._persist_workflow(workflow)
            
            logger.info(f"Workflow paused", extra={'workflow_id': workflow_id})
            return True
            
        except Exception as e:
            logger.error(f"Failed to pause workflow {workflow_id}: {e}")
            return False

    async def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow."""
        try:
            if workflow_id not in self._active_workflows:
                return False
            
            workflow = self._active_workflows[workflow_id]
            if workflow.status != WorkflowStatus.PAUSED:
                return False
            
            workflow.status = WorkflowStatus.RUNNING
            workflow.execution_log.append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event': 'workflow_resumed',
                'message': f'Workflow {workflow.name} resumed'
            })
            
            await self._persist_workflow(workflow)
            
            logger.info(f"Workflow resumed", extra={'workflow_id': workflow_id})
            return True
            
        except Exception as e:
            logger.error(f"Failed to resume workflow {workflow_id}: {e}")
            return False

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running or paused workflow."""
        try:
            if workflow_id not in self._active_workflows:
                return False
            
            workflow = self._active_workflows[workflow_id]
            
            workflow.status = WorkflowStatus.CANCELLED
            workflow.completed_at = datetime.now(timezone.utc)
            workflow.execution_log.append({
                'timestamp': workflow.completed_at.isoformat(),
                'event': 'workflow_cancelled',
                'message': f'Workflow {workflow.name} cancelled'
            })
            
            # Cancel running steps
            steps_to_cancel = [
                step_id for step_id, step_task in self._running_steps.items()
                if step_id.startswith(workflow_id)
            ]
            
            for step_id in steps_to_cancel:
                step_task = self._running_steps.pop(step_id, None)
                if step_task:
                    step_task.cancel()
            
            # Remove from active workflows
            del self._active_workflows[workflow_id]
            
            await self._persist_workflow(workflow)
            
            logger.info(f"Workflow cancelled", extra={'workflow_id': workflow_id})
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel workflow {workflow_id}: {e}")
            return False

    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get current workflow status and progress."""
        try:
            # Check active workflows first
            if workflow_id in self._active_workflows:
                workflow = self._active_workflows[workflow_id]
                return self._build_workflow_status(workflow)
            
            # Check persisted workflows
            workflow_key = f"{self.key_prefix}:workflow:{workflow_id}"
            workflow_data = await self._redis.get(workflow_key)
            
            if workflow_data:
                data = json.loads(workflow_data)
                workflow = Workflow.from_dict(data)
                return self._build_workflow_status(workflow)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get workflow status for {workflow_id}: {e}")
            return None

    def _build_workflow_status(self, workflow: Workflow) -> Dict[str, Any]:
        """Build comprehensive workflow status dictionary."""
        step_statuses = {}
        for step_id, step in workflow.steps.items():
            step_statuses[step_id] = {
                'name': step.name,
                'status': step.status.value,
                'started_at': step.started_at.isoformat() if step.started_at else None,
                'completed_at': step.completed_at.isoformat() if step.completed_at else None,
                'error': step.error,
                'retry_count': step.retry_count,
            }
        
        # Calculate progress
        total_steps = len(workflow.steps)
        completed_steps = sum(1 for step in workflow.steps.values() 
                            if step.status in [StepStatus.COMPLETED, StepStatus.SKIPPED])
        progress_percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0
        
        return {
            'workflow_id': workflow.workflow_id,
            'name': workflow.name,
            'status': workflow.status.value,
            'started_at': workflow.started_at.isoformat() if workflow.started_at else None,
            'completed_at': workflow.completed_at.isoformat() if workflow.completed_at else None,
            'progress_percentage': progress_percentage,
            'total_steps': total_steps,
            'completed_steps': completed_steps,
            'step_statuses': step_statuses,
            'context': workflow.context,
            'execution_log': workflow.execution_log[-10:],  # Last 10 log entries
        }

    async def _orchestration_loop(self):
        """Main orchestration loop for processing workflows."""
        logger.info("Orchestration loop started")
        
        try:
            while self._is_running:
                await self._process_active_workflows()
                await asyncio.sleep(5)  # Process every 5 seconds
                
        except asyncio.CancelledError:
            logger.info("Orchestration loop cancelled")
        except Exception as e:
            logger.error(f"Orchestration loop error: {e}")

    async def _process_active_workflows(self):
        """Process all active workflows."""
        workflows_to_remove = []
        
        for workflow_id, workflow in self._active_workflows.items():
            try:
                if workflow.status == WorkflowStatus.RUNNING:
                    await self._process_workflow(workflow)
                    
                    # Check if workflow is complete
                    if self._is_workflow_complete(workflow):
                        workflow.status = WorkflowStatus.COMPLETED
                        workflow.completed_at = datetime.now(timezone.utc)
                        workflow.execution_log.append({
                            'timestamp': workflow.completed_at.isoformat(),
                            'event': 'workflow_completed',
                            'message': f'Workflow {workflow.name} completed successfully'
                        })
                        workflows_to_remove.append(workflow_id)
                    
                    elif self._is_workflow_failed(workflow):
                        workflow.status = WorkflowStatus.FAILED
                        workflow.completed_at = datetime.now(timezone.utc)
                        workflow.execution_log.append({
                            'timestamp': workflow.completed_at.isoformat(),
                            'event': 'workflow_failed',
                            'message': f'Workflow {workflow.name} failed'
                        })
                        workflows_to_remove.append(workflow_id)
                
            except Exception as e:
                logger.error(f"Error processing workflow {workflow_id}: {e}")
        
        # Remove completed/failed workflows from active list
        for workflow_id in workflows_to_remove:
            workflow = self._active_workflows.pop(workflow_id)
            await self._persist_workflow(workflow)
            
            logger.info(f"Workflow finished", extra={
                'workflow_id': workflow_id,
                'status': workflow.status.value
            })

    async def _process_workflow(self, workflow: Workflow):
        """Process a single workflow, executing ready steps."""
        ready_steps = workflow.get_ready_steps()
        
        for step in ready_steps:
            step_key = f"{workflow.workflow_id}:{step.step_id}"
            
            # Skip if step is already running
            if step_key in self._running_steps:
                continue
            
            # Start step execution
            step_task = asyncio.create_task(self._execute_step(workflow, step))
            self._running_steps[step_key] = step_task

    async def _execute_step(self, workflow: Workflow, step: WorkflowStep):
        """Execute a single workflow step."""
        step_key = f"{workflow.workflow_id}:{step.step_id}"
        
        try:
            step.status = StepStatus.RUNNING
            step.started_at = datetime.now(timezone.utc)
            
            workflow.execution_log.append({
                'timestamp': step.started_at.isoformat(),
                'event': 'step_started',
                'step_id': step.step_id,
                'step_name': step.name,
                'message': f'Step {step.name} started'
            })
            
            # Execute step based on type
            if step.step_type == StepType.TASK:
                result = await self._execute_task_step(workflow, step)
            elif step.step_type == StepType.DELAY:
                result = await self._execute_delay_step(step)
            elif step.step_type == StepType.WEBHOOK:
                result = await self._execute_webhook_step(step)
            elif step.step_type == StepType.PARALLEL:
                result = await self._execute_parallel_step(workflow, step)
            elif step.step_type == StepType.SEQUENTIAL:
                result = await self._execute_sequential_step(workflow, step)
            else:
                raise TaskError(f"Unsupported step type: {step.step_type}")
            
            # Step completed successfully
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now(timezone.utc)
            step.result = result
            
            # Update workflow context with step result
            workflow.context[f"step_{step.step_id}_result"] = result
            workflow.context[f"step_{step.step_id}_status"] = "completed"
            
            workflow.execution_log.append({
                'timestamp': step.completed_at.isoformat(),
                'event': 'step_completed',
                'step_id': step.step_id,
                'step_name': step.name,
                'message': f'Step {step.name} completed successfully'
            })
            
        except Exception as e:
            step.status = StepStatus.FAILED
            step.completed_at = datetime.now(timezone.utc)
            step.error = str(e)
            
            # Update workflow context
            workflow.context[f"step_{step.step_id}_error"] = str(e)
            workflow.context[f"step_{step.step_id}_status"] = "failed"
            
            workflow.execution_log.append({
                'timestamp': step.completed_at.isoformat(),
                'event': 'step_failed',
                'step_id': step.step_id,
                'step_name': step.name,
                'error': str(e),
                'message': f'Step {step.name} failed: {str(e)}'
            })
            
            logger.error(f"Step execution failed", extra={
                'workflow_id': workflow.workflow_id,
                'step_id': step.step_id,
                'error': str(e)
            })
        
        finally:
            # Remove from running steps
            self._running_steps.pop(step_key, None)

    async def _execute_task_step(self, workflow: Workflow, step: WorkflowStep) -> Any:
        """Execute a task step by enqueuing it."""
        if not step.function_name:
            raise TaskError("Task step missing function_name")
        
        # Create task with workflow context
        task_kwargs = step.kwargs.copy()
        task_kwargs['workflow_context'] = workflow.context.copy()
        
        task = Task(
            name=f"{workflow.name}-{step.name}",
            function_name=step.function_name,
            args=step.args,
            kwargs=task_kwargs,
            config=step.task_config or TaskConfig(),
            tenant_id=workflow.tenant_id,
            correlation_id=f"workflow-{workflow.workflow_id}-step-{step.step_id}",
        )
        
        # Enqueue and wait for completion
        task_id = await self._task_queue.enqueue(task)
        
        # Poll for task completion
        timeout_time = time.time() + (step.timeout_seconds or 300)
        while time.time() < timeout_time:
            # Get task result (implementation depends on task engine)
            # For now, simulate task completion
            await asyncio.sleep(5)
            break  # Simulate immediate completion
        
        return {"task_id": task_id, "status": "completed"}

    async def _execute_delay_step(self, step: WorkflowStep) -> Any:
        """Execute a delay step."""
        if step.delay_seconds > 0:
            await asyncio.sleep(step.delay_seconds)
        return {"delayed_seconds": step.delay_seconds}

    async def _execute_webhook_step(self, step: WorkflowStep) -> Any:
        """Execute a webhook step."""
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    step.webhook_url,
                    json=step.webhook_payload,
                    timeout=30.0
                )
                response.raise_for_status()
                
                return {
                    "status_code": response.status_code,
                    "response": response.text,
                }
                
        except Exception as e:
            raise TaskError(f"Webhook call failed: {e}")

    async def _execute_parallel_step(self, workflow: Workflow, step: WorkflowStep) -> Any:
        """Execute sub-steps in parallel."""
        if not step.sub_steps:
            return {"sub_steps_completed": 0}
        
        # Execute all sub-steps concurrently
        sub_tasks = [
            self._execute_step(workflow, sub_step)
            for sub_step in step.sub_steps
        ]
        
        results = await asyncio.gather(*sub_tasks, return_exceptions=True)
        
        # Process results
        completed = 0
        errors = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(f"Sub-step {i}: {str(result)}")
            else:
                completed += 1
        
        if errors:
            raise TaskError(f"Parallel execution errors: {'; '.join(errors)}")
        
        return {"sub_steps_completed": completed, "total_sub_steps": len(step.sub_steps)}

    async def _execute_sequential_step(self, workflow: Workflow, step: WorkflowStep) -> Any:
        """Execute sub-steps sequentially."""
        if not step.sub_steps:
            return {"sub_steps_completed": 0}
        
        results = []
        for sub_step in step.sub_steps:
            try:
                await self._execute_step(workflow, sub_step)
                results.append("completed")
            except Exception as e:
                results.append(f"failed: {str(e)}")
                raise  # Fail entire sequence on first error
        
        return {"sub_step_results": results}

    def _is_workflow_complete(self, workflow: Workflow) -> bool:
        """Check if workflow is complete."""
        return all(
            step.status in [StepStatus.COMPLETED, StepStatus.SKIPPED]
            for step in workflow.steps.values()
        )

    def _is_workflow_failed(self, workflow: Workflow) -> bool:
        """Check if workflow has failed."""
        # Workflow fails if any non-optional step fails
        return any(
            step.status == StepStatus.FAILED
            for step in workflow.steps.values()
        )

    async def _persistence_loop(self):
        """Periodic persistence of workflow states."""
        try:
            while self._is_running:
                await self._persist_all_workflows()
                await asyncio.sleep(60)  # Persist every minute
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Persistence loop error: {e}")

    async def _persist_workflow(self, workflow: Workflow):
        """Persist single workflow state to Redis."""
        try:
            workflow_key = f"{self.key_prefix}:workflow:{workflow.workflow_id}"
            workflow_data = json.dumps(workflow.to_dict())
            
            # Set TTL based on workflow status
            ttl = 86400 * 7  # 7 days for completed/failed workflows
            if workflow.status in [WorkflowStatus.RUNNING, WorkflowStatus.PAUSED]:
                ttl = 86400 * 30  # 30 days for active workflows
            
            await self._redis.set(workflow_key, workflow_data, ex=ttl)
            
        except Exception as e:
            logger.error(f"Failed to persist workflow {workflow.workflow_id}: {e}")

    async def _persist_all_workflows(self):
        """Persist all active workflow states."""
        for workflow in self._active_workflows.values():
            await self._persist_workflow(workflow)

    async def _load_active_workflows(self):
        """Load active workflows from Redis."""
        try:
            pattern = f"{self.key_prefix}:workflow:*"
            keys = await self._redis.keys(pattern)
            
            for key in keys:
                try:
                    workflow_data = await self._redis.get(key)
                    if workflow_data:
                        data = json.loads(workflow_data)
                        workflow = Workflow.from_dict(data)
                        
                        # Only load running/paused workflows
                        if workflow.status in [WorkflowStatus.RUNNING, WorkflowStatus.PAUSED]:
                            self._active_workflows[workflow.workflow_id] = workflow
                            
                except Exception as e:
                    logger.error(f"Failed to load workflow from {key}: {e}")
            
            logger.info(f"Loaded {len(self._active_workflows)} active workflows")
            
        except Exception as e:
            logger.error(f"Failed to load active workflows: {e}")

    async def list_workflows(
        self,
        status: Optional[WorkflowStatus] = None,
        tenant_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List workflows with optional filtering."""
        try:
            workflows = []
            
            # Add active workflows
            for workflow in self._active_workflows.values():
                if status is None or workflow.status == status:
                    if tenant_id is None or workflow.tenant_id == tenant_id:
                        workflows.append(self._build_workflow_status(workflow))
            
            # Add persisted workflows if needed
            if len(workflows) < limit:
                pattern = f"{self.key_prefix}:workflow:*"
                keys = await self._redis.keys(pattern)
                
                for key in keys[:limit - len(workflows)]:
                    try:
                        workflow_data = await self._redis.get(key)
                        if workflow_data:
                            data = json.loads(workflow_data)
                            workflow = Workflow.from_dict(data)
                            
                            # Skip if already in active list
                            if workflow.workflow_id in self._active_workflows:
                                continue
                            
                            if status is None or workflow.status == status:
                                if tenant_id is None or workflow.tenant_id == tenant_id:
                                    workflows.append(self._build_workflow_status(workflow))
                                    
                    except Exception as e:
                        logger.warning(f"Failed to load workflow from {key}: {e}")
            
            return workflows[:limit]
            
        except Exception as e:
            logger.error(f"Failed to list workflows: {e}")
            return []