"""
Task-based workflow implementation.

Provides a simple task execution workflow for single-step operations.
"""

import asyncio
from collections.abc import Callable
from typing import Any, Optional

from .base import BaseWorkflow, WorkflowResult


class TaskWorkflow(BaseWorkflow):
    """
    Simple single-task workflow implementation.

    Useful for wrapping single operations in a workflow interface.
    """

    def __init__(
        self,
        task_name: str,
        task_function: Callable,
        task_args: tuple = (),
        task_kwargs: Optional[dict[str, Any]] = None,
        workflow_id: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ):
        super().__init__(
            workflow_id=workflow_id or f"task_{task_name}",
            workflow_type="task",
            steps=[task_name],
        )

        self.task_name = task_name
        self.task_function = task_function
        self.task_args = task_args
        self.task_kwargs = task_kwargs or {}
        self.timeout_seconds = timeout_seconds

    async def execute_step(self, step_name: str) -> WorkflowResult:
        """Execute the task function."""
        if step_name != self.task_name:
            return WorkflowResult(
                success=False,
                step_name=step_name,
                error="Invalid step name",
                message=f"Expected step '{self.task_name}', got '{step_name}'",
            )

        try:
            # Execute with optional timeout
            if self.timeout_seconds:
                result = await asyncio.wait_for(
                    self._execute_task_function(), timeout=self.timeout_seconds
                )
            else:
                result = await self._execute_task_function()

            return WorkflowResult(
                success=True,
                step_name=step_name,
                data={"result": result},
                message=f"Task '{self.task_name}' completed successfully",
            )

        except asyncio.TimeoutError:
            return WorkflowResult(
                success=False,
                step_name=step_name,
                error="Task timeout",
                message=f"Task '{self.task_name}' timed out after {self.timeout_seconds} seconds",
            )

        except Exception as e:
            return WorkflowResult(
                success=False,
                step_name=step_name,
                error=str(e),
                message=f"Task '{self.task_name}' failed: {str(e)}",
            )

    async def _execute_task_function(self) -> Any:
        """Execute the task function, handling both sync and async functions."""
        if asyncio.iscoroutinefunction(self.task_function):
            return await self.task_function(*self.task_args, **self.task_kwargs)
        else:
            # Run sync function in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, lambda: self.task_function(*self.task_args, **self.task_kwargs)
            )


class SequentialTaskWorkflow(BaseWorkflow):
    """
    Workflow that executes multiple tasks in sequence.

    Each task is a callable with its own arguments.
    """

    def __init__(
        self,
        tasks: list[dict[str, Any]],
        workflow_id: Optional[str] = None,
        stop_on_failure: bool = True,
    ):
        """
        Initialize sequential task workflow.

        Args:
            tasks: List of task definitions. Each task should have:
                   - 'name': Task name
                   - 'function': Callable to execute
                   - 'args': Tuple of positional arguments (optional)
                   - 'kwargs': Dict of keyword arguments (optional)
                   - 'timeout': Timeout in seconds (optional)
            workflow_id: Unique workflow identifier
            stop_on_failure: Whether to stop execution on first failure
        """
        task_names = [task["name"] for task in tasks]

        super().__init__(
            workflow_id=workflow_id or "sequential_tasks",
            workflow_type="sequential_tasks",
            steps=task_names,
        )

        self.tasks = {task["name"]: task for task in tasks}
        self.continue_on_step_failure = not stop_on_failure

    async def execute_step(self, step_name: str) -> WorkflowResult:
        """Execute a single task from the sequence."""
        if step_name not in self.tasks:
            return WorkflowResult(
                success=False,
                step_name=step_name,
                error="Task not found",
                message=f"Task '{step_name}' not found in workflow",
            )

        task = self.tasks[step_name]
        task_function = task["function"]
        task_args = task.get("args", ())
        task_kwargs = task.get("kwargs", {})
        timeout = task.get("timeout")

        try:
            # Execute with optional timeout
            if timeout:
                result = await asyncio.wait_for(
                    self._execute_task_function(task_function, task_args, task_kwargs),
                    timeout=timeout,
                )
            else:
                result = await self._execute_task_function(
                    task_function, task_args, task_kwargs
                )

            return WorkflowResult(
                success=True,
                step_name=step_name,
                data={"result": result},
                message=f"Task '{step_name}' completed successfully",
            )

        except asyncio.TimeoutError:
            return WorkflowResult(
                success=False,
                step_name=step_name,
                error="Task timeout",
                message=f"Task '{step_name}' timed out after {timeout} seconds",
            )

        except Exception as e:
            return WorkflowResult(
                success=False,
                step_name=step_name,
                error=str(e),
                message=f"Task '{step_name}' failed: {str(e)}",
            )

    async def _execute_task_function(
        self, function: Callable, args: tuple, kwargs: dict[str, Any]
    ) -> Any:
        """Execute a task function, handling both sync and async functions."""
        if asyncio.iscoroutinefunction(function):
            return await function(*args, **kwargs)
        else:
            # Run sync function in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: function(*args, **kwargs))


# Task workflow factory functions
def create_task_workflow(
    name: str, function: Callable, *args, timeout: Optional[int] = None, **kwargs
) -> TaskWorkflow:
    """
    Create a simple task workflow.

    Args:
        name: Task name
        function: Function to execute
        *args: Positional arguments for function
        timeout: Timeout in seconds
        **kwargs: Keyword arguments for function

    Returns:
        TaskWorkflow instance
    """
    return TaskWorkflow(
        task_name=name,
        task_function=function,
        task_args=args,
        task_kwargs=kwargs,
        timeout_seconds=timeout,
    )


def create_sequential_workflow(
    *tasks, workflow_id: Optional[str] = None, stop_on_failure: bool = True
) -> SequentialTaskWorkflow:
    """
    Create a sequential task workflow.

    Args:
        *tasks: Task definitions (name, function, args, kwargs)
        workflow_id: Workflow identifier
        stop_on_failure: Whether to stop on first failure

    Returns:
        SequentialTaskWorkflow instance
    """
    task_list = []

    for i, task in enumerate(tasks):
        if isinstance(task, dict):
            task_list.append(task)
        elif isinstance(task, tuple):
            # Handle (name, function) or (name, function, args) or (name, function, args, kwargs)
            task_dict = {"name": task[0], "function": task[1]}
            if len(task) > 2:
                task_dict["args"] = (
                    task[2] if isinstance(task[2], tuple) else (task[2],)
                )
            if len(task) > 3:
                task_dict["kwargs"] = task[3]
            task_list.append(task_dict)
        else:
            raise ValueError(f"Invalid task definition at index {i}: {task}")

    return SequentialTaskWorkflow(
        tasks=task_list, workflow_id=workflow_id, stop_on_failure=stop_on_failure
    )
