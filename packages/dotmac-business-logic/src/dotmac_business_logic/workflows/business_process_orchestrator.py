"""
Business Process Orchestrator - Coordinates complex multi-workflow business processes.

This orchestrator manages the execution of multiple interconnected workflows,
handling dependencies, parallel execution, and cross-workflow data flow.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BusinessWorkflow, BusinessWorkflowResult, BusinessWorkflowStatus


class ProcessStatus(str, Enum):
    """Business process orchestration status."""
    
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIALLY_COMPLETED = "partially_completed"


class WorkflowDependencyType(str, Enum):
    """Types of workflow dependencies."""
    
    SEQUENCE = "sequence"  # B must run after A completes
    PARALLEL = "parallel"  # A and B can run simultaneously
    CONDITIONAL = "conditional"  # B runs only if A meets condition
    COMPENSATION = "compensation"  # B runs to compensate for A's failure
    SYNCHRONIZATION = "synchronization"  # Wait for multiple workflows


class WorkflowDefinition(BaseModel):
    """Definition of a workflow in the business process."""
    
    workflow_id: str = Field(..., description="Unique workflow identifier")
    workflow_type: str = Field(..., description="Type of workflow to instantiate")
    workflow_class: str = Field(..., description="Workflow class name")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Workflow parameters")
    dependencies: List[str] = Field(default_factory=list, description="Prerequisite workflow IDs")
    dependency_type: WorkflowDependencyType = Field(default=WorkflowDependencyType.SEQUENCE)
    condition: Optional[str] = Field(None, description="Condition for conditional dependencies")
    timeout_seconds: Optional[int] = Field(None, description="Workflow timeout")
    retry_count: int = Field(0, description="Number of retries on failure")
    compensation_workflow: Optional[str] = Field(None, description="Compensation workflow ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ProcessDefinition(BaseModel):
    """Definition of a complete business process."""
    
    process_id: str = Field(..., description="Unique process identifier")
    name: str = Field(..., description="Process name")
    description: str = Field(..., description="Process description")
    version: str = Field("1.0", description="Process version")
    workflows: List[WorkflowDefinition] = Field(..., description="Workflow definitions")
    global_timeout_seconds: Optional[int] = Field(None, description="Global process timeout")
    rollback_on_failure: bool = Field(True, description="Rollback all workflows on failure")
    parallel_execution_limit: int = Field(10, description="Max parallel workflows")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Process metadata")


class WorkflowExecution(BaseModel):
    """Runtime execution state of a workflow."""
    
    workflow_id: str
    workflow_instance: Optional[BusinessWorkflow] = None
    status: BusinessWorkflowStatus = BusinessWorkflowStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    results: List[BusinessWorkflowResult] = Field(default_factory=list)
    error: Optional[str] = None
    retry_count: int = 0
    dependencies_met: bool = False
    output_data: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True


class ProcessExecutionRequest(BaseModel):
    """Request to execute a business process."""
    
    process_definition: ProcessDefinition = Field(..., description="Process definition to execute")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input data for process")
    context: Dict[str, Any] = Field(default_factory=dict, description="Execution context")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    trace_id: Optional[str] = Field(None, description="Distributed tracing ID")


class BusinessProcessOrchestrator:
    """
    Orchestrates complex business processes with multiple workflows.
    
    Features:
    - Dependency management and execution ordering
    - Parallel workflow execution with limits
    - Conditional workflow execution
    - Compensation and rollback handling
    - Cross-workflow data flow
    - Process monitoring and logging
    - Timeout and retry handling
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        workflow_factory: Optional[Dict[str, Callable]] = None,
        max_parallel_executions: int = 10,
        default_timeout: int = 3600  # 1 hour
    ):
        self.db_session = db_session
        self.workflow_factory = workflow_factory or {}
        self.max_parallel_executions = max_parallel_executions
        self.default_timeout = default_timeout
        
        # Runtime state
        self.active_processes: Dict[str, ProcessExecution] = {}
        self.execution_semaphore = asyncio.Semaphore(max_parallel_executions)
    
    async def execute_process(
        self, request: ProcessExecutionRequest
    ) -> ProcessExecution:
        """Execute a complete business process."""
        execution_id = str(uuid.uuid4())
        
        process_execution = ProcessExecution(
            execution_id=execution_id,
            process_definition=request.process_definition,
            input_data=request.input_data,
            context=request.context,
            status=ProcessStatus.PENDING,
            workflow_executions={},
            output_data={},
            error=None,
            start_time=None,
            end_time=None
        )
        
        self.active_processes[execution_id] = process_execution
        
        try:
            # Validate process definition
            await self._validate_process_definition(request.process_definition)
            
            # Initialize workflow executions
            await self._initialize_workflow_executions(process_execution)
            
            # Execute the process
            process_execution.status = ProcessStatus.RUNNING
            process_execution.start_time = datetime.now(timezone.utc)
            
            await self._execute_process_workflows(process_execution)
            
            # Determine final status
            if process_execution.status == ProcessStatus.RUNNING:
                if all(
                    wf.status == BusinessWorkflowStatus.COMPLETED
                    for wf in process_execution.workflow_executions.values()
                ):
                    process_execution.status = ProcessStatus.COMPLETED
                else:
                    process_execution.status = ProcessStatus.PARTIALLY_COMPLETED
            
            process_execution.end_time = datetime.now(timezone.utc)
            
        except Exception as e:
            process_execution.status = ProcessStatus.FAILED
            process_execution.error = str(e)
            process_execution.end_time = datetime.now(timezone.utc)
            
            # Handle rollback if configured
            if request.process_definition.rollback_on_failure:
                await self._rollback_process(process_execution)
        
        finally:
            # Clean up from active processes
            if execution_id in self.active_processes:
                del self.active_processes[execution_id]
        
        return process_execution
    
    async def _validate_process_definition(
        self, definition: ProcessDefinition
    ) -> None:
        """Validate process definition for correctness."""
        workflow_ids = {wf.workflow_id for wf in definition.workflows}
        
        # Check for duplicate workflow IDs
        if len(workflow_ids) != len(definition.workflows):
            raise ValueError("Duplicate workflow IDs in process definition")
        
        # Validate dependencies
        for workflow in definition.workflows:
            for dep_id in workflow.dependencies:
                if dep_id not in workflow_ids:
                    raise ValueError(f"Workflow {workflow.workflow_id} depends on unknown workflow {dep_id}")
        
        # Check for circular dependencies
        await self._check_circular_dependencies(definition.workflows)
        
        # Validate workflow classes exist
        for workflow in definition.workflows:
            if workflow.workflow_class not in self.workflow_factory:
                raise ValueError(f"Unknown workflow class: {workflow.workflow_class}")
    
    async def _check_circular_dependencies(
        self, workflows: List[WorkflowDefinition]
    ) -> None:
        """Check for circular dependencies in workflow definitions."""
        # Build dependency graph
        graph = {wf.workflow_id: set(wf.dependencies) for wf in workflows}
        
        # Use DFS to detect cycles
        visited = set()
        recursion_stack = set()
        
        async def has_cycle(node: str) -> bool:
            visited.add(node)
            recursion_stack.add(node)
            
            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    if await has_cycle(neighbor):
                        return True
                elif neighbor in recursion_stack:
                    return True
            
            recursion_stack.remove(node)
            return False
        
        for workflow_id in graph:
            if workflow_id not in visited:
                if await has_cycle(workflow_id):
                    raise ValueError(f"Circular dependency detected involving workflow {workflow_id}")
    
    async def _initialize_workflow_executions(
        self, process_execution: ProcessExecution
    ) -> None:
        """Initialize workflow execution states."""
        for workflow_def in process_execution.process_definition.workflows:
            execution = WorkflowExecution(
                workflow_id=workflow_def.workflow_id,
                workflow_instance=None,
                status=BusinessWorkflowStatus.PENDING,
                dependencies_met=len(workflow_def.dependencies) == 0
            )
            
            process_execution.workflow_executions[workflow_def.workflow_id] = execution
    
    async def _execute_process_workflows(
        self, process_execution: ProcessExecution
    ) -> None:
        """Execute all workflows in the process with proper ordering."""
        max_iterations = len(process_execution.workflow_executions) * 2  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Find workflows ready to execute
            ready_workflows = await self._find_ready_workflows(process_execution)
            
            if not ready_workflows:
                # Check if all workflows are completed or failed
                all_done = all(
                    wf.status in [BusinessWorkflowStatus.COMPLETED, BusinessWorkflowStatus.FAILED, BusinessWorkflowStatus.CANCELLED]
                    for wf in process_execution.workflow_executions.values()
                )
                
                if all_done:
                    break
                
                # Wait for running workflows to complete
                running_workflows = [
                    wf for wf in process_execution.workflow_executions.values()
                    if wf.status == BusinessWorkflowStatus.RUNNING
                ]
                
                if running_workflows:
                    # Wait a short time for workflows to progress
                    await asyncio.sleep(0.1)
                    continue
                else:
                    # No workflows ready and none running - possible deadlock
                    break
            
            # Execute ready workflows
            await self._execute_ready_workflows(process_execution, ready_workflows)
            
            # Update dependencies
            await self._update_workflow_dependencies(process_execution)
    
    async def _find_ready_workflows(
        self, process_execution: ProcessExecution
    ) -> List[WorkflowDefinition]:
        """Find workflows that are ready to execute."""
        ready = []
        
        for workflow_def in process_execution.process_definition.workflows:
            execution = process_execution.workflow_executions[workflow_def.workflow_id]
            
            # Skip if already running or completed
            if execution.status != BusinessWorkflowStatus.PENDING:
                continue
            
            # Check if dependencies are met
            if not execution.dependencies_met:
                continue
            
            # Check conditional dependencies
            if workflow_def.dependency_type == WorkflowDependencyType.CONDITIONAL:
                if not await self._evaluate_condition(
                    workflow_def.condition, process_execution
                ):
                    continue
            
            ready.append(workflow_def)
        
        return ready
    
    async def _execute_ready_workflows(
        self, process_execution: ProcessExecution,
        ready_workflows: List[WorkflowDefinition]
    ) -> None:
        """Execute workflows that are ready to run."""
        # Group workflows by dependency type for execution strategy
        parallel_workflows = [
            wf for wf in ready_workflows
            if wf.dependency_type == WorkflowDependencyType.PARALLEL
        ]
        
        sequential_workflows = [
            wf for wf in ready_workflows
            if wf.dependency_type != WorkflowDependencyType.PARALLEL
        ]
        
        # Execute parallel workflows concurrently
        if parallel_workflows:
            tasks = []
            for workflow_def in parallel_workflows:
                task = asyncio.create_task(
                    self._execute_single_workflow(process_execution, workflow_def)
                )
                tasks.append(task)
            
            # Wait for parallel workflows with limit
            semaphore_tasks = []
            for task in tasks:
                semaphore_task = asyncio.create_task(
                    self._execute_with_semaphore(task)
                )
                semaphore_tasks.append(semaphore_task)
            
            await asyncio.gather(*semaphore_tasks, return_exceptions=True)
        
        # Execute sequential workflows one by one
        for workflow_def in sequential_workflows:
            await self._execute_single_workflow(process_execution, workflow_def)
    
    async def _execute_with_semaphore(self, task: asyncio.Task) -> Any:
        """Execute task with semaphore to limit parallel executions."""
        async with self.execution_semaphore:
            return await task
    
    async def _execute_single_workflow(
        self, process_execution: ProcessExecution,
        workflow_def: WorkflowDefinition
    ) -> None:
        """Execute a single workflow."""
        execution = process_execution.workflow_executions[workflow_def.workflow_id]
        
        try:
            # Create workflow instance
            workflow_class = self.workflow_factory[workflow_def.workflow_class]
            
            # Prepare parameters with cross-workflow data
            parameters = await self._prepare_workflow_parameters(
                workflow_def, process_execution
            )
            
            # Instantiate workflow
            workflow_instance = workflow_class(
                **parameters,
                db_session=self.db_session
            )
            
            execution.workflow_instance = workflow_instance
            execution.status = BusinessWorkflowStatus.RUNNING
            execution.start_time = datetime.now(timezone.utc)
            
            # Execute workflow with timeout
            timeout = workflow_def.timeout_seconds or self.default_timeout
            
            try:
                # Execute all workflow steps
                results = await asyncio.wait_for(
                    workflow_instance.execute(),
                    timeout=timeout
                )
                
                execution.results = results
                execution.status = BusinessWorkflowStatus.COMPLETED
                
                # Extract output data for cross-workflow use
                execution.output_data = await self._extract_workflow_output(
                    workflow_instance, results
                )
                
            except asyncio.TimeoutError:
                execution.status = BusinessWorkflowStatus.FAILED
                execution.error = f"Workflow timed out after {timeout} seconds"
                
            except Exception as e:
                execution.status = BusinessWorkflowStatus.FAILED
                execution.error = str(e)
                
                # Handle retry logic
                if execution.retry_count < workflow_def.retry_count:
                    execution.retry_count += 1
                    execution.status = BusinessWorkflowStatus.PENDING
                    execution.dependencies_met = True  # Keep ready for retry
            
            execution.end_time = datetime.now(timezone.utc)
            
            # Handle compensation workflows on failure
            if (execution.status == BusinessWorkflowStatus.FAILED and
                workflow_def.compensation_workflow):
                await self._trigger_compensation_workflow(
                    process_execution, workflow_def.compensation_workflow
                )
            
        except Exception as e:
            execution.status = BusinessWorkflowStatus.FAILED
            execution.error = f"Failed to execute workflow: {e}"
            execution.end_time = datetime.now(timezone.utc)
    
    async def _prepare_workflow_parameters(
        self, workflow_def: WorkflowDefinition,
        process_execution: ProcessExecution
    ) -> Dict[str, Any]:
        """Prepare parameters for workflow execution with cross-workflow data."""
        parameters = workflow_def.parameters.copy()
        
        # Add global process input data
        parameters.update(process_execution.input_data)
        
        # Add context
        parameters.update(process_execution.context)
        
        # Add outputs from completed dependencies
        for dep_id in workflow_def.dependencies:
            dep_execution = process_execution.workflow_executions[dep_id]
            if dep_execution.status == BusinessWorkflowStatus.COMPLETED:
                # Prefix dependency outputs to avoid conflicts
                for key, value in dep_execution.output_data.items():
                    parameters[f"{dep_id}_{key}"] = value
        
        return parameters
    
    async def _extract_workflow_output(
        self, workflow_instance: BusinessWorkflow,
        results: List[BusinessWorkflowResult]
    ) -> Dict[str, Any]:
        """Extract output data from completed workflow."""
        output = {}
        
        # Extract data from workflow results
        for result in results:
            if result.success and result.data:
                output.update(result.data)
        
        # Extract key workflow state if available
        if hasattr(workflow_instance, 'get_output_data'):
            custom_output = await workflow_instance.get_output_data()
            output.update(custom_output)
        
        return output
    
    async def _update_workflow_dependencies(
        self, process_execution: ProcessExecution
    ) -> None:
        """Update workflow dependency status based on completed workflows."""
        for workflow_def in process_execution.process_definition.workflows:
            execution = process_execution.workflow_executions[workflow_def.workflow_id]
            
            # Skip if already processed
            if execution.status != BusinessWorkflowStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            dependencies_met = True
            for dep_id in workflow_def.dependencies:
                dep_execution = process_execution.workflow_executions[dep_id]
                if dep_execution.status != BusinessWorkflowStatus.COMPLETED:
                    dependencies_met = False
                    break
            
            execution.dependencies_met = dependencies_met
    
    async def _evaluate_condition(
        self, condition: Optional[str],
        process_execution: ProcessExecution
    ) -> bool:
        """Evaluate conditional dependency."""
        if not condition:
            return True
        
        # Simple condition evaluation - in production, use a proper expression engine
        try:
            # Create evaluation context with workflow outputs
            context = {}
            for wf_id, execution in process_execution.workflow_executions.items():
                if execution.status == BusinessWorkflowStatus.COMPLETED:
                    context[wf_id] = execution.output_data
            
            # Basic condition evaluation (extend as needed)
            # Example: "customer_onboarding.customer_type == 'business'"
            if "==" in condition:
                left, right = condition.split("==", 1)
                left = left.strip()
                right = right.strip().strip("'\"")
                
                # Navigate nested context
                value = context
                for part in left.split("."):
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        return False
                
                return str(value) == right
            
            return True
            
        except Exception:
            # Default to True if condition evaluation fails
            return True
    
    async def _trigger_compensation_workflow(
        self, process_execution: ProcessExecution,
        compensation_workflow_id: str
    ) -> None:
        """Trigger a compensation workflow."""
        if compensation_workflow_id in process_execution.workflow_executions:
            execution = process_execution.workflow_executions[compensation_workflow_id]
            if execution.status == BusinessWorkflowStatus.PENDING:
                execution.dependencies_met = True  # Force compensation to run
    
    async def _rollback_process(
        self, process_execution: ProcessExecution
    ) -> None:
        """Rollback completed workflows in reverse order."""
        # Get completed workflows in reverse completion order
        completed_workflows = [
            (execution.end_time, wf_id, execution)
            for wf_id, execution in process_execution.workflow_executions.items()
            if (execution.status == BusinessWorkflowStatus.COMPLETED and
                execution.end_time is not None)
        ]
        
        # Sort by end time in descending order (most recent first)
        completed_workflows.sort(key=lambda x: x[0], reverse=True)
        
        # Attempt rollback for each workflow
        for _, wf_id, execution in completed_workflows:
            if execution.workflow_instance and hasattr(execution.workflow_instance, 'rollback'):
                try:
                    await execution.workflow_instance.rollback()
                except Exception as e:
                    # Log rollback failure but continue with other workflows
                    process_execution.output_data[f"{wf_id}_rollback_error"] = str(e)
    
    async def pause_process(self, process_id: str) -> bool:
        """Pause a running process."""
        if process_id in self.active_processes:
            process_execution = self.active_processes[process_id]
            if process_execution.status == ProcessStatus.RUNNING:
                process_execution.status = ProcessStatus.PAUSED
                return True
        return False
    
    async def resume_process(self, process_id: str) -> bool:
        """Resume a paused process."""
        if process_id in self.active_processes:
            process_execution = self.active_processes[process_id]
            if process_execution.status == ProcessStatus.PAUSED:
                process_execution.status = ProcessStatus.RUNNING
                # Continue execution
                await self._execute_process_workflows(process_execution)
                return True
        return False
    
    async def cancel_process(self, process_id: str) -> bool:
        """Cancel a running or paused process."""
        if process_id in self.active_processes:
            process_execution = self.active_processes[process_id]
            if process_execution.status in [ProcessStatus.RUNNING, ProcessStatus.PAUSED]:
                process_execution.status = ProcessStatus.CANCELLED
                process_execution.end_time = datetime.now(timezone.utc)
                
                # Cancel running workflows
                for execution in process_execution.workflow_executions.values():
                    if execution.status == BusinessWorkflowStatus.RUNNING:
                        execution.status = BusinessWorkflowStatus.CANCELLED
                        if execution.workflow_instance and hasattr(execution.workflow_instance, 'cancel'):
                            try:
                                await execution.workflow_instance.cancel()
                            except Exception:
                                pass  # Ignore cancellation errors
                
                return True
        return False
    
    def get_process_status(self, process_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a process."""
        if process_id in self.active_processes:
            process_execution = self.active_processes[process_id]
            return {
                "process_id": process_id,
                "status": process_execution.status,
                "start_time": process_execution.start_time,
                "end_time": process_execution.end_time,
                "error": process_execution.error,
                "workflows": {
                    wf_id: {
                        "status": execution.status,
                        "start_time": execution.start_time,
                        "end_time": execution.end_time,
                        "error": execution.error,
                        "retry_count": execution.retry_count
                    }
                    for wf_id, execution in process_execution.workflow_executions.items()
                }
            }
        return None


class ProcessExecution(BaseModel):
    """Runtime execution state of a business process."""
    
    execution_id: str
    process_definition: ProcessDefinition
    input_data: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    status: ProcessStatus = ProcessStatus.PENDING
    workflow_executions: Dict[str, WorkflowExecution] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed = True


# Pre-defined process templates
class ProcessTemplates:
    """Pre-defined business process templates."""
    
    @staticmethod
    def customer_onboarding_with_service_provisioning() -> ProcessDefinition:
        """Complete customer onboarding with service provisioning process."""
        return ProcessDefinition(
            process_id="customer_onboarding_full",
            name="Customer Onboarding with Service Provisioning",
            description="End-to-end customer onboarding including service activation",
            workflows=[
                WorkflowDefinition(
                    workflow_id="customer_onboarding",
                    workflow_type="customer_onboarding",
                    workflow_class="CustomerOnboardingWorkflow",
                    parameters={},
                    dependencies=[],
                    dependency_type=WorkflowDependencyType.SEQUENCE
                ),
                WorkflowDefinition(
                    workflow_id="service_provisioning",
                    workflow_type="service_provisioning", 
                    workflow_class="ServiceProvisioningWorkflow",
                    parameters={},
                    dependencies=["customer_onboarding"],
                    dependency_type=WorkflowDependencyType.SEQUENCE,
                    condition="customer_onboarding.onboarding_success == true"
                ),
                WorkflowDefinition(
                    workflow_id="billing_setup",
                    workflow_type="billing_process",
                    workflow_class="BillingProcessWorkflow",
                    parameters={},
                    dependencies=["service_provisioning"],
                    dependency_type=WorkflowDependencyType.SEQUENCE
                )
            ]
        )
    
    @staticmethod
    def payment_processing_with_billing_update() -> ProcessDefinition:
        """Payment processing with billing system update process."""
        return ProcessDefinition(
            process_id="payment_with_billing",
            name="Payment Processing with Billing Update",
            description="Process payment and update billing records",
            workflows=[
                WorkflowDefinition(
                    workflow_id="payment_processing",
                    workflow_type="payment_processing",
                    workflow_class="PaymentProcessingWorkflow",
                    parameters={},
                    dependencies=[],
                    dependency_type=WorkflowDependencyType.SEQUENCE
                ),
                WorkflowDefinition(
                    workflow_id="invoice_generation",
                    workflow_type="invoice_generation",
                    workflow_class="InvoiceGenerationWorkflow",
                    parameters={},
                    dependencies=["payment_processing"],
                    dependency_type=WorkflowDependencyType.SEQUENCE,
                    condition="payment_processing.payment_status == 'settled'"
                )
            ]
        )
    
    @staticmethod
    def customer_offboarding_complete() -> ProcessDefinition:
        """Complete customer offboarding process."""
        return ProcessDefinition(
            process_id="customer_offboarding_complete",
            name="Complete Customer Offboarding",
            description="Full customer offboarding with service deactivation and final billing",
            workflows=[
                WorkflowDefinition(
                    workflow_id="service_deactivation",
                    workflow_type="service_provisioning",
                    workflow_class="ServiceProvisioningWorkflow",
                    parameters={"action": "deactivate"},
                    dependencies=[],
                    dependency_type=WorkflowDependencyType.SEQUENCE
                ),
                WorkflowDefinition(
                    workflow_id="final_billing",
                    workflow_type="billing_process",
                    workflow_class="BillingProcessWorkflow",
                    parameters={"billing_type": "final"},
                    dependencies=["service_deactivation"],
                    dependency_type=WorkflowDependencyType.SEQUENCE
                ),
                WorkflowDefinition(
                    workflow_id="customer_offboarding",
                    workflow_type="customer_offboarding",
                    workflow_class="CustomerOffboardingWorkflow",
                    parameters={},
                    dependencies=["final_billing"],
                    dependency_type=WorkflowDependencyType.SEQUENCE
                )
            ]
        )