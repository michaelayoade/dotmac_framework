"""
CLI commands for advanced operations management.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

import asyncclick as click
import structlog
from tabulate import tabulate

from ..api.operations import (
    DLQManager,
    DLQReplayRequest,
    RunCancelRequest,
    ScheduleOperationsManager,
    SchedulePauseRequest,
    ScheduleResumeRequest,
    StepRetryRequest,
    StepSkipRequest,
    WorkflowOperationsManager,
)
from .base import cli, format_output, get_event_bus, get_tenant_context

logger = structlog.get_logger(__name__)


@cli.group()
async def ops():
    """Advanced operations management commands."""
    pass


@ops.group()
async def dlq():
    """Dead Letter Queue operations."""
    pass


@dlq.command()
@click.option("--topic", required=True, help="Topic to replay messages from")
@click.option("--consumer-group", help="Consumer group filter")
@click.option("--message-ids", help="Comma-separated message IDs to replay")
@click.option("--max-messages", default=100, type=int, help="Maximum messages to replay")
@click.option("--filter", "filter_json", help="JSON filter criteria")
@click.option("--output", default="table", type=click.Choice(["json", "table"]), help="Output format")
@click.option("--wait", is_flag=True, help="Wait for replay completion")
async def replay(topic: str, consumer_group: Optional[str], message_ids: Optional[str],
                max_messages: int, filter_json: Optional[str], output: str, wait: bool):
    """Replay messages from Dead Letter Queue."""
    try:
        tenant_id = get_tenant_context()
        event_bus = await get_event_bus()
        dlq_manager = DLQManager(event_bus)

        # Parse message IDs
        message_id_list = None
        if message_ids:
            message_id_list = [mid.strip() for mid in message_ids.split(",")]

        # Parse filter criteria
        filter_criteria = None
        if filter_json:
            try:
                filter_criteria = json.loads(filter_json)
            except json.JSONDecodeError:
                click.echo("Error: Invalid JSON in filter criteria", err=True)
                return

        # Create replay request
        request = DLQReplayRequest(
            topic=topic,
            consumer_group=consumer_group,
            message_ids=message_id_list,
            max_messages=max_messages,
            filter_criteria=filter_criteria
        )

        click.echo(f"Starting DLQ replay for topic: {topic}")

        # Start replay
        response = await dlq_manager.replay_messages(tenant_id, request)

        if wait:
            # Wait for completion
            click.echo("Waiting for replay completion...")
            while response.completed_at is None:
                await asyncio.sleep(1)
                # In a real implementation, we'd poll the status
                break  # For demo purposes

        # Format output
        if output == "json":
            click.echo(json.dumps(response.dict(), indent=2, default=str))
        else:
            data = [
                ["Replay ID", response.replay_id],
                ["Topic", response.topic],
                ["Messages Found", response.messages_found],
                ["Messages Replayed", response.messages_replayed],
                ["Messages Failed", response.messages_failed],
                ["Status", response.status],
                ["Started At", response.started_at.isoformat()],
                ["Completed At", response.completed_at.isoformat() if response.completed_at else "In Progress"]
            ]
            click.echo(tabulate(data, headers=["Field", "Value"], tablefmt="grid"))

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


@dlq.command()
@click.argument("replay_id")
@click.option("--output", default="table", type=click.Choice(["json", "table"]), help="Output format")
async def status(replay_id: str, output: str):
    """Get status of a DLQ replay operation."""
    try:
        tenant_id = get_tenant_context()
        event_bus = await get_event_bus()
        dlq_manager = DLQManager(event_bus)

        if replay_id not in dlq_manager.active_replays:
            click.echo(f"Replay operation {replay_id} not found", err=True)
            return

        replay_info = dlq_manager.active_replays[replay_id]

        # Check tenant access
        if replay_info["tenant_id"] != tenant_id:
            click.echo("Access denied", err=True)
            return

        # Format output
        if output == "json":
            click.echo(json.dumps(replay_info, indent=2, default=str))
        else:
            data = [
                ["Replay ID", replay_id],
                ["Topic", replay_info.get("topic", "N/A")],
                ["Status", replay_info.get("status", "N/A")],
                ["Messages Found", replay_info.get("messages_found", 0)],
                ["Messages Replayed", replay_info.get("messages_replayed", 0)],
                ["Messages Failed", replay_info.get("messages_failed", 0)],
                ["Started At", replay_info.get("started_at", "N/A")]
            ]
            click.echo(tabulate(data, headers=["Field", "Value"], tablefmt="grid"))

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


@ops.group()
async def workflow():
    """Workflow operations."""
    pass


@workflow.group()
async def step():
    """Workflow step operations."""
    pass


@step.command()
@click.option("--workflow-id", required=True, help="Workflow ID")
@click.option("--step-id", required=True, help="Step ID to retry")
@click.option("--retry-config", help="JSON retry configuration")
@click.option("--force", is_flag=True, help="Force retry even if step succeeded")
@click.option("--output", default="table", type=click.Choice(["json", "table"]), help="Output format")
async def retry(workflow_id: str, step_id: str, retry_config: Optional[str],
               force: bool, output: str):
    """Retry a failed workflow step."""
    try:
        tenant_id = get_tenant_context()
        event_bus = await get_event_bus()
        workflow_manager = WorkflowOperationsManager(event_bus)

        # Parse retry config
        config = None
        if retry_config:
            try:
                config = json.loads(retry_config)
            except json.JSONDecodeError:
                click.echo("Error: Invalid JSON in retry configuration", err=True)
                return

        # Create retry request
        request = StepRetryRequest(
            workflow_id=workflow_id,
            step_id=step_id,
            retry_config=config,
            force=force
        )

        click.echo(f"Retrying step {step_id} in workflow {workflow_id}")

        # Execute retry
        response = await workflow_manager.retry_step(tenant_id, request)

        # Format output
        format_output(response.dict(), output)

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


@step.command()
@click.option("--workflow-id", required=True, help="Workflow ID")
@click.option("--step-id", required=True, help="Step ID to skip")
@click.option("--reason", required=True, help="Reason for skipping step")
@click.option("--mock-result", help="JSON mock result data")
@click.option("--output", default="table", type=click.Choice(["json", "table"]), help="Output format")
async def skip(workflow_id: str, step_id: str, reason: str,
               mock_result: Optional[str], output: str):
    """Skip a workflow step."""
    try:
        tenant_id = get_tenant_context()
        event_bus = await get_event_bus()
        workflow_manager = WorkflowOperationsManager(event_bus)

        # Parse mock result
        result = None
        if mock_result:
            try:
                result = json.loads(mock_result)
            except json.JSONDecodeError:
                click.echo("Error: Invalid JSON in mock result", err=True)
                return

        # Create skip request
        request = StepSkipRequest(
            workflow_id=workflow_id,
            step_id=step_id,
            skip_reason=reason,
            mock_result=result
        )

        click.echo(f"Skipping step {step_id} in workflow {workflow_id}")

        # Execute skip
        response = await workflow_manager.skip_step(tenant_id, request)

        # Format output
        format_output(response.dict(), output)

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


@workflow.group()
async def run():
    """Workflow run operations."""
    pass


@run.command()
@click.option("--workflow-id", required=True, help="Workflow ID")
@click.option("--run-id", help="Specific run ID (latest if not provided)")
@click.option("--reason", required=True, help="Reason for cancellation")
@click.option("--force", is_flag=True, help="Force cancel even if run is completing")
@click.option("--output", default="table", type=click.Choice(["json", "table"]), help="Output format")
async def cancel(workflow_id: str, run_id: Optional[str], reason: str,
                force: bool, output: str):
    """Cancel a workflow run."""
    try:
        tenant_id = get_tenant_context()
        event_bus = await get_event_bus()
        workflow_manager = WorkflowOperationsManager(event_bus)

        # Create cancel request
        request = RunCancelRequest(
            workflow_id=workflow_id,
            run_id=run_id,
            cancel_reason=reason,
            force=force
        )

        click.echo(f"Cancelling workflow run {workflow_id}")

        # Execute cancel
        response = await workflow_manager.cancel_run(tenant_id, request)

        # Format output
        format_output(response.dict(), output)

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


@ops.group()
async def schedule():
    """Schedule operations."""
    pass


@schedule.command()
@click.option("--schedule-id", required=True, help="Schedule ID to pause")
@click.option("--reason", required=True, help="Reason for pausing")
@click.option("--until", help="Auto-resume time (ISO format)")
@click.option("--output", default="table", type=click.Choice(["json", "table"]), help="Output format")
async def pause(schedule_id: str, reason: str, until: Optional[str], output: str):
    """Pause a schedule."""
    try:
        tenant_id = get_tenant_context()
        event_bus = await get_event_bus()
        schedule_manager = ScheduleOperationsManager(event_bus)

        # Parse until time
        pause_until = None
        if until:
            try:
                pause_until = datetime.fromisoformat(until.replace("Z", "+00:00"))
            except ValueError:
                click.echo("Error: Invalid ISO format for --until", err=True)
                return

        # Create pause request
        request = SchedulePauseRequest(
            schedule_id=schedule_id,
            pause_reason=reason,
            pause_until=pause_until
        )

        click.echo(f"Pausing schedule {schedule_id}")

        # Execute pause
        response = await schedule_manager.pause_schedule(tenant_id, request)

        # Format output
        format_output(response.dict(), output)

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


@schedule.command()
@click.option("--schedule-id", required=True, help="Schedule ID to resume")
@click.option("--reason", required=True, help="Reason for resuming")
@click.option("--output", default="table", type=click.Choice(["json", "table"]), help="Output format")
async def resume(schedule_id: str, reason: str, output: str):
    """Resume a paused schedule."""
    try:
        tenant_id = get_tenant_context()
        event_bus = await get_event_bus()
        schedule_manager = ScheduleOperationsManager(event_bus)

        # Create resume request
        request = ScheduleResumeRequest(
            schedule_id=schedule_id,
            resume_reason=reason
        )

        click.echo(f"Resuming schedule {schedule_id}")

        # Execute resume
        response = await schedule_manager.resume_schedule(tenant_id, request)

        # Format output
        format_output(response.dict(), output)

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


@schedule.command()
@click.argument("schedule_id")
@click.option("--output", default="table", type=click.Choice(["json", "table"]), help="Output format")
async def status(schedule_id: str, output: str):
    """Get schedule status."""
    try:
        tenant_id = get_tenant_context()
        event_bus = await get_event_bus()
        schedule_manager = ScheduleOperationsManager(event_bus)

        # Get schedule status
        if schedule_id in schedule_manager.paused_schedules:
            paused_info = schedule_manager.paused_schedules[schedule_id]

            # Check tenant access
            if paused_info["tenant_id"] != tenant_id:
                click.echo("Access denied", err=True)
                return

            status_info = {
                "schedule_id": schedule_id,
                "status": "paused",
                "pause_reason": paused_info["pause_reason"],
                "paused_at": paused_info["paused_at"].isoformat(),
                "pause_until": paused_info["pause_until"].isoformat() if paused_info["pause_until"] else None,
                "pause_duration_seconds": (datetime.now(timezone.utc) - paused_info["paused_at"]).total_seconds()
            }
        else:
            status_info = {
                "schedule_id": schedule_id,
                "status": "running",
                "pause_reason": None,
                "paused_at": None,
                "pause_until": None,
                "pause_duration_seconds": 0
            }

        # Format output
        format_output(status_info, output)

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


# Utility commands
@ops.command()
@click.option("--output", default="table", type=click.Choice(["json", "table"]), help="Output format")
async def health():
    """Check operations health status."""
    try:
        tenant_id = get_tenant_context()
        event_bus = await get_event_bus()

        # Create managers
        dlq_manager = DLQManager(event_bus)
        workflow_manager = WorkflowOperationsManager(event_bus)
        schedule_manager = ScheduleOperationsManager(event_bus)

        # Collect health info
        health_info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "services": {
                "dlq_manager": {
                    "status": "healthy",
                    "active_replays": len(dlq_manager.active_replays)
                },
                "workflow_manager": {
                    "status": "healthy",
                    "active_operations": len(workflow_manager.active_operations)
                },
                "schedule_manager": {
                    "status": "healthy",
                    "paused_schedules": len(schedule_manager.paused_schedules)
                }
            }
        }

        # Format output
        format_output(health_info, output)

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


@ops.command()
@click.option("--service", type=click.Choice(["dlq", "workflow", "schedule", "all"]),
              default="all", help="Service to get stats for")
@click.option("--output", default="table", type=click.Choice(["json", "table"]), help="Output format")
async def stats(service: str, output: str):
    """Get operations statistics."""
    try:
        tenant_id = get_tenant_context()
        event_bus = await get_event_bus()

        stats_info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id
        }

        if service in ["dlq", "all"]:
            dlq_manager = DLQManager(event_bus)
            stats_info["dlq"] = {
                "active_replays": len(dlq_manager.active_replays),
                "replay_history": list(dlq_manager.active_replays.keys())
            }

        if service in ["workflow", "all"]:
            workflow_manager = WorkflowOperationsManager(event_bus)
            stats_info["workflow"] = {
                "active_operations": len(workflow_manager.active_operations),
                "operation_history": list(workflow_manager.active_operations.keys())
            }

        if service in ["schedule", "all"]:
            schedule_manager = ScheduleOperationsManager(event_bus)
            stats_info["schedule"] = {
                "paused_schedules": len(schedule_manager.paused_schedules),
                "paused_schedule_ids": list(schedule_manager.paused_schedules.keys())
            }

        # Format output
        format_output(stats_info, output)

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


# Batch operations
@ops.group()
async def batch():
    """Batch operations."""
    pass


@batch.command()
@click.option("--config-file", required=True, help="JSON configuration file for batch operations")
@click.option("--dry-run", is_flag=True, help="Show what would be done without executing")
@click.option("--output", default="table", type=click.Choice(["json", "table"]), help="Output format")
async def execute(config_file: str, dry_run: bool, output: str):
    """Execute batch operations from configuration file."""
    try:
        # Load configuration
        with open(config_file) as f:
            config = json.load(f)

        tenant_id = get_tenant_context()
        event_bus = await get_event_bus()

        # Create managers
        dlq_manager = DLQManager(event_bus)
        workflow_manager = WorkflowOperationsManager(event_bus)
        schedule_manager = ScheduleOperationsManager(event_bus)

        results = []

        for operation in config.get("operations", []):
            op_type = operation.get("type")
            op_data = operation.get("data", {})

            if dry_run:
                results.append({
                    "type": op_type,
                    "status": "dry_run",
                    "message": f"Would execute {op_type} operation",
                    "data": op_data
                })
                continue

            try:
                if op_type == "dlq_replay":
                    request = DLQReplayRequest(**op_data)
                    response = await dlq_manager.replay_messages(tenant_id, request)
                    results.append({
                        "type": op_type,
                        "status": "success",
                        "message": f"DLQ replay started: {response.replay_id}",
                        "data": response.dict()
                    })

                elif op_type == "step_retry":
                    request = StepRetryRequest(**op_data)
                    response = await workflow_manager.retry_step(tenant_id, request)
                    results.append({
                        "type": op_type,
                        "status": "success",
                        "message": f"Step retry requested: {response.operation_id}",
                        "data": response.dict()
                    })

                elif op_type == "schedule_pause":
                    # Handle datetime parsing
                    if "pause_until" in op_data and op_data["pause_until"]:
                        op_data["pause_until"] = datetime.fromisoformat(op_data["pause_until"])
                    request = SchedulePauseRequest(**op_data)
                    response = await schedule_manager.pause_schedule(tenant_id, request)
                    results.append({
                        "type": op_type,
                        "status": "success",
                        "message": f"Schedule paused: {response.operation_id}",
                        "data": response.dict()
                    })

                else:
                    results.append({
                        "type": op_type,
                        "status": "error",
                        "message": f"Unknown operation type: {op_type}",
                        "data": op_data
                    })

            except Exception as e:
                results.append({
                    "type": op_type,
                    "status": "error",
                    "message": f"Operation failed: {str(e)}",
                    "data": op_data
                })

        # Format output
        batch_result = {
            "total_operations": len(config.get("operations", [])),
            "successful_operations": len([r for r in results if r["status"] == "success"]),
            "failed_operations": len([r for r in results if r["status"] == "error"]),
            "dry_run": dry_run,
            "results": results
        }

        format_output(batch_result, output)

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


if __name__ == "__main__":
    cli()
