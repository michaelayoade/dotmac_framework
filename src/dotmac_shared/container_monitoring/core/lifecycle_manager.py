"""
Container Lifecycle Manager

Manages container lifecycle operations including start, stop, restart,
and scale operations with proper event tracking and error handling.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

from docker.errors import DockerException

import docker


class LifecycleAction(str, Enum):
    """Container lifecycle actions"""

    START = "start"
    STOP = "stop"
    RESTART = "restart"
    PAUSE = "pause"
    UNPAUSE = "unpause"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    KILL = "kill"
    REMOVE = "remove"


class LifecycleEventType(str, Enum):
    """Lifecycle event types"""

    ACTION_STARTED = "action_started"
    ACTION_COMPLETED = "action_completed"
    ACTION_FAILED = "action_failed"
    STATE_CHANGED = "state_changed"


@dataclass
class LifecycleEvent:
    """Container lifecycle event"""

    event_id: UUID = field(default_factory=uuid4)
    container_id: str = ""
    action: Optional[LifecycleAction] = None
    event_type: LifecycleEventType = LifecycleEventType.ACTION_STARTED
    timestamp: datetime = field(default_factory=datetime.utcnow)
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None


@dataclass
class LifecycleResult:
    """Result of lifecycle operation"""

    success: bool
    action: LifecycleAction
    container_id: str
    events: List[LifecycleEvent] = field(default_factory=list)
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContainerLifecycleManager:
    """
    Container lifecycle management service

    Manages container operations including:
    - Basic lifecycle (start, stop, restart)
    - Advanced operations (pause, scale)
    - Event tracking and auditing
    - Error handling and recovery
    """

    def __init__(
        self,
        default_timeout: int = 30,
        stop_timeout: int = 10,
        event_callback: Optional[Callable[[LifecycleEvent], None]] = None,
    ):
        self.default_timeout = default_timeout
        self.stop_timeout = stop_timeout
        self.event_callback = event_callback

        self.docker_client = docker.from_env()
        self.logger = logging.getLogger(__name__)

    async def manage_container_lifecycle(
        self, container_id: str, action: LifecycleAction, **kwargs
    ) -> LifecycleResult:
        """
        Execute lifecycle action on container

        Args:
            container_id: Docker container ID or name
            action: Lifecycle action to perform
            **kwargs: Additional action-specific parameters

        Returns:
            LifecycleResult with operation status and events
        """
        start_time = datetime.utcnow()
        result = LifecycleResult(
            success=False, action=action, container_id=container_id
        )

        # Emit action started event
        start_event = LifecycleEvent(
            container_id=container_id,
            action=action,
            event_type=LifecycleEventType.ACTION_STARTED,
            message=f"Starting {action.value} operation",
        )
        result.events.append(start_event)
        await self._emit_event(start_event)

        try:
            container = self.docker_client.containers.get(container_id)

            # Execute the requested action
            success = await self._execute_action(container, action, result, **kwargs)

            # Calculate duration
            result.duration_seconds = (datetime.utcnow() - start_time).total_seconds()

            if success:
                result.success = True
                completion_event = LifecycleEvent(
                    container_id=container_id,
                    action=action,
                    event_type=LifecycleEventType.ACTION_COMPLETED,
                    message=f"Successfully completed {action.value} operation",
                    metadata={"duration_seconds": result.duration_seconds},
                )
                result.events.append(completion_event)
                await self._emit_event(completion_event)
            else:
                result.success = False
                result.error = "Action execution failed"

        except docker.errors.NotFound:
            error_msg = f"Container {container_id} not found"
            result.error = error_msg
            await self._emit_error_event(container_id, action, error_msg, result)

        except DockerException as e:
            error_msg = f"Docker error: {str(e)}"
            result.error = error_msg
            await self._emit_error_event(container_id, action, error_msg, result)

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            result.error = error_msg
            self.logger.exception(f"Lifecycle management failed for {container_id}")
            await self._emit_error_event(container_id, action, error_msg, result)

        return result

    async def _execute_action(
        self,
        container: docker.models.containers.Container,
        action: LifecycleAction,
        result: LifecycleResult,
        **kwargs,
    ) -> bool:
        """Execute specific lifecycle action"""
        try:
            if action == LifecycleAction.START:
                return await self._start_container(container, result, **kwargs)
            elif action == LifecycleAction.STOP:
                return await self._stop_container(container, result, **kwargs)
            elif action == LifecycleAction.RESTART:
                return await self._restart_container(container, result, **kwargs)
            elif action == LifecycleAction.PAUSE:
                return await self._pause_container(container, result, **kwargs)
            elif action == LifecycleAction.UNPAUSE:
                return await self._unpause_container(container, result, **kwargs)
            elif action == LifecycleAction.SCALE_UP:
                return await self._scale_up_container(container, result, **kwargs)
            elif action == LifecycleAction.SCALE_DOWN:
                return await self._scale_down_container(container, result, **kwargs)
            elif action == LifecycleAction.KILL:
                return await self._kill_container(container, result, **kwargs)
            elif action == LifecycleAction.REMOVE:
                return await self._remove_container(container, result, **kwargs)
            else:
                result.error = f"Unknown action: {action}"
                return False

        except Exception as e:
            result.error = f"Action execution failed: {str(e)}"
            return False

    async def _start_container(
        self,
        container: docker.models.containers.Container,
        result: LifecycleResult,
        **kwargs,
    ) -> bool:
        """Start container"""
        try:
            container.reload()
            if container.status == "running":
                result.metadata["already_running"] = True
                return True

            container.start()

            # Wait for container to be running
            timeout = kwargs.get("timeout", self.default_timeout)
            await self._wait_for_status(container, "running", timeout)

            await self._emit_state_change_event(
                container.id, "started", "Container started successfully"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to start container {container.id}: {e}")
            return False

    async def _stop_container(
        self,
        container: docker.models.containers.Container,
        result: LifecycleResult,
        **kwargs,
    ) -> bool:
        """Stop container"""
        try:
            container.reload()
            if container.status in ["stopped", "exited"]:
                result.metadata["already_stopped"] = True
                return True

            timeout = kwargs.get("timeout", self.stop_timeout)
            container.stop(timeout=timeout)

            await self._wait_for_status(container, ["stopped", "exited"], timeout + 5)

            await self._emit_state_change_event(
                container.id, "stopped", "Container stopped successfully"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to stop container {container.id}: {e}")
            return False

    async def _restart_container(
        self,
        container: docker.models.containers.Container,
        result: LifecycleResult,
        **kwargs,
    ) -> bool:
        """Restart container"""
        try:
            timeout = kwargs.get("timeout", self.default_timeout)
            container.restart(timeout=timeout)

            await self._wait_for_status(container, "running", timeout + 10)

            await self._emit_state_change_event(
                container.id, "restarted", "Container restarted successfully"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to restart container {container.id}: {e}")
            return False

    async def _pause_container(
        self,
        container: docker.models.containers.Container,
        result: LifecycleResult,
        **kwargs,
    ) -> bool:
        """Pause container"""
        try:
            container.reload()
            if container.status == "paused":
                result.metadata["already_paused"] = True
                return True

            container.pause()
            await self._wait_for_status(container, "paused", 10)

            await self._emit_state_change_event(
                container.id, "paused", "Container paused successfully"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to pause container {container.id}: {e}")
            return False

    async def _unpause_container(
        self,
        container: docker.models.containers.Container,
        result: LifecycleResult,
        **kwargs,
    ) -> bool:
        """Unpause container"""
        try:
            container.reload()
            if container.status == "running":
                result.metadata["not_paused"] = True
                return True

            container.unpause()
            await self._wait_for_status(container, "running", 10)

            await self._emit_state_change_event(
                container.id, "unpaused", "Container unpaused successfully"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to unpause container {container.id}: {e}")
            return False

    async def _scale_up_container(
        self,
        container: docker.models.containers.Container,
        result: LifecycleResult,
        **kwargs,
    ) -> bool:
        """Scale up container (placeholder for actual scaling logic)"""
        try:
            # This would typically involve:
            # 1. Creating additional container instances
            # 2. Load balancer configuration
            # 3. Service discovery updates

            replicas = kwargs.get("replicas", 1)
            result.metadata["scale_operation"] = {
                "action": "scale_up",
                "additional_replicas": replicas,
            }

            await self._emit_state_change_event(
                container.id, "scaled_up", f"Container scaled up by {replicas} replicas"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to scale up container {container.id}: {e}")
            return False

    async def _scale_down_container(
        self,
        container: docker.models.containers.Container,
        result: LifecycleResult,
        **kwargs,
    ) -> bool:
        """Scale down container (placeholder for actual scaling logic)"""
        try:
            # This would typically involve:
            # 1. Gracefully stopping excess container instances
            # 2. Load balancer reconfiguration
            # 3. Service discovery updates

            replicas = kwargs.get("replicas", 1)
            result.metadata["scale_operation"] = {
                "action": "scale_down",
                "removed_replicas": replicas,
            }

            await self._emit_state_change_event(
                container.id,
                "scaled_down",
                f"Container scaled down by {replicas} replicas",
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to scale down container {container.id}: {e}")
            return False

    async def _kill_container(
        self,
        container: docker.models.containers.Container,
        result: LifecycleResult,
        **kwargs,
    ) -> bool:
        """Kill container forcefully"""
        try:
            container.reload()
            if container.status in ["stopped", "exited"]:
                result.metadata["already_stopped"] = True
                return True

            signal = kwargs.get("signal", "SIGKILL")
            container.kill(signal=signal)

            await self._wait_for_status(container, ["stopped", "exited"], 15)

            await self._emit_state_change_event(
                container.id, "killed", f"Container killed with {signal}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to kill container {container.id}: {e}")
            return False

    async def _remove_container(
        self,
        container: docker.models.containers.Container,
        result: LifecycleResult,
        **kwargs,
    ) -> bool:
        """Remove container"""
        try:
            force = kwargs.get("force", False)
            remove_volumes = kwargs.get("remove_volumes", False)

            container.remove(force=force, v=remove_volumes)

            result.metadata["removal_options"] = {
                "force": force,
                "remove_volumes": remove_volumes,
            }

            await self._emit_state_change_event(
                container.id, "removed", "Container removed successfully"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to remove container {container.id}: {e}")
            return False

    async def _wait_for_status(
        self,
        container: docker.models.containers.Container,
        target_status: str | List[str],
        timeout: int,
    ) -> bool:
        """Wait for container to reach target status"""
        if isinstance(target_status, str):
            target_status = [target_status]

        end_time = datetime.utcnow().timestamp() + timeout

        while datetime.utcnow().timestamp() < end_time:
            try:
                container.reload()
                if container.status in target_status:
                    return True
            except DockerException:
                pass
            await asyncio.sleep(1)

        return False

    async def _emit_event(self, event: LifecycleEvent) -> None:
        """Emit lifecycle event"""
        if self.event_callback:
            try:
                if asyncio.iscoroutinefunction(self.event_callback):
                    await self.event_callback(event)
                else:
                    self.event_callback(event)
            except Exception as e:
                self.logger.error(f"Event callback failed: {e}")

        self.logger.info(
            f"Lifecycle event: {event.event_type.value} - "
            f"{event.container_id} - {event.message}"
        )

    async def _emit_state_change_event(
        self, container_id: str, new_state: str, message: str
    ) -> None:
        """Emit state change event"""
        event = LifecycleEvent(
            container_id=container_id,
            event_type=LifecycleEventType.STATE_CHANGED,
            message=message,
            metadata={"new_state": new_state},
        )
        await self._emit_event(event)

    async def _emit_error_event(
        self,
        container_id: str,
        action: LifecycleAction,
        error_message: str,
        result: LifecycleResult,
    ) -> None:
        """Emit error event"""
        error_event = LifecycleEvent(
            container_id=container_id,
            action=action,
            event_type=LifecycleEventType.ACTION_FAILED,
            message=error_message,
            success=False,
            error=error_message,
        )
        result.events.append(error_event)
        await self._emit_event(error_event)


# Convenience function for direct usage
async def manage_container_lifecycle(
    container_id: str, action: LifecycleAction, **kwargs
) -> bool:
    """
    Manage container lifecycle with default settings

    Args:
        container_id: Docker container ID or name
        action: Lifecycle action to perform
        **kwargs: Additional action-specific parameters

    Returns:
        True if operation succeeded, False otherwise
    """
    manager = ContainerLifecycleManager()
    result = await manager.manage_container_lifecycle(container_id, action, **kwargs)
    return result.success
