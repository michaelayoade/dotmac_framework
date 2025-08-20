"""
CLI commands for workflow migration management.
"""

import json
from typing import Optional

import asyncclick as click
import structlog
from tabulate import tabulate

from ..migration.workflow_migration import (
    ChangeType,
    MigrationStatus,
    WorkflowChange,
    WorkflowMigrationManager,
)
from .base import cli, get_event_bus, get_tenant_context

logger = structlog.get_logger(__name__)


@cli.group()
async def migration():
    """Workflow migration management commands."""
    pass


@migration.command()
@click.option("--workflow-id", required=True, help="Workflow ID to migrate")
@click.option("--from-version", required=True, help="Source version")
@click.option("--to-version", required=True, help="Target version")
@click.option("--changes-file", required=True, help="JSON file containing changes")
@click.option("--strategy", default="gradual", type=click.Choice(["gradual", "immediate"]),
              help="Migration strategy")
@click.option("--output", default="table", type=click.Choice(["json", "table"]), help="Output format")
async def plan(workflow_id: str, from_version: str, to_version: str,
               changes_file: str, strategy: str, output: str):
    """Create a migration plan for workflow definition changes."""
    try:
        tenant_id = get_tenant_context()
        event_bus = await get_event_bus()
        migration_manager = WorkflowMigrationManager(event_bus)

        # Load changes from file
        with open(changes_file) as f:
            changes_data = json.load(f)

        # Parse changes
        changes = []
        for change_data in changes_data.get("changes", []):
            change = WorkflowChange(
                change_type=ChangeType(change_data["change_type"]),
                path=change_data["path"],
                old_value=change_data.get("old_value"),
                new_value=change_data.get("new_value"),
                description=change_data["description"],
                breaking=change_data.get("breaking", False),
                rollback_action=change_data.get("rollback_action")
            )
            changes.append(change)

        click.echo(f"Creating migration plan for workflow {workflow_id}")
        click.echo(f"From version {from_version} to {to_version}")
        click.echo(f"Changes: {len(changes)}")

        # Create migration plan
        plan = await migration_manager.create_migration_plan(
            workflow_id=workflow_id,
            from_version=from_version,
            to_version=to_version,
            tenant_id=tenant_id,
            changes=changes,
            migration_strategy=strategy,
            created_by="cli_user"
        )

        # Format output
        if output == "json":
            click.echo(json.dumps(plan.dict(), indent=2, default=str))
        else:
            data = [
                ["Migration ID", plan.migration_id],
                ["Workflow ID", plan.workflow_id],
                ["From Version", plan.from_version],
                ["To Version", plan.to_version],
                ["Strategy", plan.migration_strategy],
                ["Changes Count", len(plan.changes)],
                ["Breaking Changes", len([c for c in plan.changes if c.breaking])],
                ["Pre-checks", len(plan.pre_migration_checks)],
                ["Post-checks", len(plan.post_migration_checks)],
                ["Created At", plan.created_at.isoformat()]
            ]
            click.echo(tabulate(data, headers=["Field", "Value"], tablefmt="grid"))

            # Show changes summary
            if plan.changes:
                click.echo("\nChanges Summary:")
                changes_data = []
                for change in plan.changes:
                    changes_data.append([
                        change.change_type.value,
                        change.path,
                        change.description,
                        "✓" if change.breaking else ""
                    ])
                click.echo(tabulate(changes_data,
                                  headers=["Type", "Path", "Description", "Breaking"],
                                  tablefmt="grid"))

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


@migration.command()
@click.argument("migration_id")
@click.option("--dry-run", is_flag=True, help="Simulate migration without applying changes")
@click.option("--output", default="table", type=click.Choice(["json", "table"]), help="Output format")
async def execute(migration_id: str, dry_run: bool, output: str):
    """Execute a migration plan."""
    try:
        event_bus = await get_event_bus()
        migration_manager = WorkflowMigrationManager(event_bus)

        if dry_run:
            click.echo(f"Executing migration {migration_id} in DRY RUN mode")
        else:
            click.echo(f"Executing migration {migration_id}")

        # Execute migration
        execution = await migration_manager.execute_migration(migration_id, dry_run=dry_run)

        # Format output
        if output == "json":
            click.echo(json.dumps(execution.dict(), indent=2, default=str))
        else:
            data = [
                ["Execution ID", execution.execution_id],
                ["Migration ID", execution.migration_id],
                ["Status", execution.status.value],
                ["Started At", execution.started_at.isoformat() if execution.started_at else "N/A"],
                ["Completed At", execution.completed_at.isoformat() if execution.completed_at else "N/A"],
                ["Affected Runs", len(execution.affected_runs)],
                ["Dry Run", dry_run],
                ["Error", execution.error_message or "None"]
            ]
            click.echo(tabulate(data, headers=["Field", "Value"], tablefmt="grid"))

            # Show progress if available
            if execution.progress:
                click.echo("\nProgress:")
                for phase, progress in execution.progress.items():
                    if isinstance(progress, dict) and "total" in progress and "completed" in progress:
                        click.echo(f"  {phase}: {progress['completed']}/{progress['total']}")

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


@migration.command()
@click.argument("execution_id")
@click.option("--reason", default="Manual rollback", help="Reason for rollback")
@click.option("--output", default="table", type=click.Choice(["json", "table"]), help="Output format")
async def rollback(execution_id: str, reason: str, output: str):
    """Rollback a migration execution."""
    try:
        event_bus = await get_event_bus()
        migration_manager = WorkflowMigrationManager(event_bus)

        click.echo(f"Rolling back migration execution {execution_id}")
        click.echo(f"Reason: {reason}")

        # Execute rollback
        success = await migration_manager.rollback_migration(execution_id, reason)

        # Get updated execution status
        execution = await migration_manager.get_migration_status(execution_id)

        if success:
            click.echo("✅ Rollback completed successfully")
        else:
            click.echo("❌ Rollback failed")

        # Format output
        if output == "json" and execution:
            click.echo(json.dumps(execution.dict(), indent=2, default=str))
        elif execution:
            data = [
                ["Execution ID", execution.execution_id],
                ["Status", execution.status.value],
                ["Rollback Success", "✅" if success else "❌"],
                ["Error", execution.error_message or "None"]
            ]
            click.echo(tabulate(data, headers=["Field", "Value"], tablefmt="grid"))

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


@migration.command()
@click.argument("execution_id")
@click.option("--output", default="table", type=click.Choice(["json", "table"]), help="Output format")
async def status(execution_id: str, output: str):
    """Get migration execution status."""
    try:
        event_bus = await get_event_bus()
        migration_manager = WorkflowMigrationManager(event_bus)

        # Get execution status
        execution = await migration_manager.get_migration_status(execution_id)

        if not execution:
            click.echo(f"Migration execution {execution_id} not found", err=True)
            return

        # Format output
        if output == "json":
            click.echo(json.dumps(execution.dict(), indent=2, default=str))
        else:
            data = [
                ["Execution ID", execution.execution_id],
                ["Migration ID", execution.migration_id],
                ["Status", execution.status.value],
                ["Started At", execution.started_at.isoformat() if execution.started_at else "N/A"],
                ["Completed At", execution.completed_at.isoformat() if execution.completed_at else "N/A"],
                ["Duration", f"{(execution.completed_at - execution.started_at).total_seconds():.1f}s"
                           if execution.started_at and execution.completed_at else "N/A"],
                ["Affected Runs", len(execution.affected_runs)],
                ["Has Rollback Point", "✅" if execution.rollback_point else "❌"],
                ["Error", execution.error_message or "None"]
            ]
            click.echo(tabulate(data, headers=["Field", "Value"], tablefmt="grid"))

            # Show progress details
            if execution.progress:
                click.echo("\nProgress Details:")
                for phase, progress in execution.progress.items():
                    if isinstance(progress, dict):
                        click.echo(f"  {phase}:")
                        for key, value in progress.items():
                            click.echo(f"    {key}: {value}")
                    else:
                        click.echo(f"  {phase}: {progress}")

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


@migration.command()
@click.option("--workflow-id", help="Filter by workflow ID")
@click.option("--status", type=click.Choice([s.value for s in MigrationStatus]),
              help="Filter by status")
@click.option("--limit", default=20, type=int, help="Maximum number of results")
@click.option("--output", default="table", type=click.Choice(["json", "table"]), help="Output format")
async def list(workflow_id: Optional[str], status: Optional[str], limit: int, output: str):
    """List migration executions."""
    try:
        tenant_id = get_tenant_context()
        event_bus = await get_event_bus()
        migration_manager = WorkflowMigrationManager(event_bus)

        # Get executions
        migration_status = MigrationStatus(status) if status else None
        executions = await migration_manager.list_migrations(
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            status=migration_status
        )

        # Limit results
        executions = executions[:limit]

        if not executions:
            click.echo("No migrations found")
            return

        # Format output
        if output == "json":
            click.echo(json.dumps([e.dict() for e in executions], indent=2, default=str))
        else:
            data = []
            for execution in executions:
                plan = migration_manager.migration_plans.get(execution.migration_id)
                data.append([
                    execution.execution_id[:8],
                    plan.workflow_id if plan else "N/A",
                    f"{plan.from_version} → {plan.to_version}" if plan else "N/A",
                    execution.status.value,
                    execution.started_at.strftime("%Y-%m-%d %H:%M") if execution.started_at else "N/A",
                    f"{(execution.completed_at - execution.started_at).total_seconds():.1f}s"
                    if execution.started_at and execution.completed_at else "N/A",
                    len(execution.affected_runs)
                ])

            click.echo(tabulate(data,
                              headers=["Exec ID", "Workflow", "Version", "Status", "Started", "Duration", "Runs"],
                              tablefmt="grid"))

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


@migration.command()
@click.option("--workflow-id", required=True, help="Workflow ID")
@click.option("--from-version", required=True, help="Source version")
@click.option("--to-version", required=True, help="Target version")
@click.option("--output-file", help="Output file for changes template")
async def template(workflow_id: str, from_version: str, to_version: str,
                  output_file: Optional[str]):
    """Generate a template for migration changes."""
    try:
        # Generate template
        template = {
            "workflow_id": workflow_id,
            "from_version": from_version,
            "to_version": to_version,
            "description": f"Migration from {from_version} to {to_version}",
            "changes": [
                {
                    "change_type": "add_step",
                    "path": "$.steps[2]",
                    "old_value": None,
                    "new_value": {
                        "name": "new_validation_step",
                        "type": "validation",
                        "config": {}
                    },
                    "description": "Add new validation step",
                    "breaking": False,
                    "rollback_action": {
                        "type": "remove_step",
                        "path": "$.steps[2]"
                    }
                },
                {
                    "change_type": "modify_step",
                    "path": "$.steps[0].config.timeout",
                    "old_value": 30,
                    "new_value": 60,
                    "description": "Increase timeout for first step",
                    "breaking": False,
                    "rollback_action": {
                        "type": "set_value",
                        "path": "$.steps[0].config.timeout",
                        "value": 30
                    }
                }
            ]
        }

        template_json = json.dumps(template, indent=2)

        if output_file:
            with open(output_file, "w") as f:
                f.write(template_json)
            click.echo(f"Template written to {output_file}")
        else:
            click.echo(template_json)

        click.echo(f"\nTemplate generated for migration {workflow_id} {from_version} → {to_version}")
        click.echo("Available change types:")
        for change_type in ChangeType:
            click.echo(f"  - {change_type.value}")

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


@migration.command()
@click.argument("changes_file")
async def validate(changes_file: str):  # noqa: C901
    """Validate a migration changes file."""
    try:
        # Load and validate changes file
        with open(changes_file) as f:
            changes_data = json.load(f)

        # Basic validation
        required_fields = ["workflow_id", "from_version", "to_version", "changes"]
        missing_fields = [field for field in required_fields if field not in changes_data]

        if missing_fields:
            click.echo(f"❌ Missing required fields: {', '.join(missing_fields)}", err=True)
            return

        # Validate changes
        changes = changes_data.get("changes", [])
        if not changes:
            click.echo("❌ No changes specified", err=True)
            return

        validation_errors = []
        breaking_changes = 0

        for i, change_data in enumerate(changes):
            # Validate change structure
            required_change_fields = ["change_type", "path", "description"]
            missing_change_fields = [field for field in required_change_fields
                                   if field not in change_data]

            if missing_change_fields:
                validation_errors.append(f"Change {i}: Missing fields {', '.join(missing_change_fields)}")
                continue

            # Validate change type
            try:
                ChangeType(change_data["change_type"])
            except ValueError:
                validation_errors.append(f"Change {i}: Invalid change_type '{change_data['change_type']}'")

            # Count breaking changes
            if change_data.get("breaking", False):
                breaking_changes += 1

        # Report validation results
        if validation_errors:
            click.echo("❌ Validation failed:")
            for error in validation_errors:
                click.echo(f"  - {error}")
        else:
            click.echo("✅ Validation passed")

            # Show summary
            data = [
                ["Workflow ID", changes_data["workflow_id"]],
                ["From Version", changes_data["from_version"]],
                ["To Version", changes_data["to_version"]],
                ["Total Changes", len(changes)],
                ["Breaking Changes", breaking_changes],
                ["Non-breaking Changes", len(changes) - breaking_changes]
            ]
            click.echo(tabulate(data, headers=["Field", "Value"], tablefmt="grid"))

    except FileNotFoundError:
        click.echo(f"❌ File not found: {changes_file}", err=True)
    except json.JSONDecodeError as e:
        click.echo(f"❌ Invalid JSON: {str(e)}", err=True)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


if __name__ == "__main__":
    cli()
