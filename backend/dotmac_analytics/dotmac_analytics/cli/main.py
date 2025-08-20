"""
Main CLI interface for DotMac Analytics.
"""

import asyncio
from datetime import datetime, timedelta
from dotmac_analytics.core.datetime_utils import utc_now, utc_now_iso
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..core.config import get_config
from ..core.database import check_connection, create_tables, init_database
from ..models.enums import EventType, MetricType
from ..sdk.client import AnalyticsClient

app = typer.Typer(help="DotMac Analytics CLI")
console = Console()

# Global options
tenant_id_option = typer.Option("default", help="Tenant ID")
verbose_option = typer.Option(False, "--verbose", "-v", help="Enable verbose output")


@app.command()
def health(
    tenant_id: str = tenant_id_option,
    verbose: bool = verbose_option
):
    """Check analytics service health."""
    try:
        config = get_config()

        # Check database connection
        db_healthy = check_connection()

        # Check configuration
        config_errors = config.validate()

        # Create health table
        table = Table(title="Analytics Health Check")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="yellow")

        table.add_row(
            "Database",
            "✅ Healthy" if db_healthy else "❌ Unhealthy",
            "Connection successful" if db_healthy else "Connection failed"
        )

        table.add_row(
            "Configuration",
            "✅ Healthy" if not config_errors else "❌ Unhealthy",
            "Valid" if not config_errors else f"{len(config_errors)} errors"
        )

        console.print(table)

        if config_errors and verbose:
            console.print("\n[red]Configuration Errors:[/red]")
            for error in config_errors:
                console.print(f"  • {error}")

        overall_status = "healthy" if db_healthy and not config_errors else "unhealthy"
        console.print(f"\n[bold]Overall Status:[/bold] {overall_status}")

    except Exception as e:
        console.print(f"[red]Health check failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def init_db(
    tenant_id: str = tenant_id_option,
    force: bool = typer.Option(False, "--force", help="Force database initialization")
):
    """Initialize database tables."""
    try:
        console.print("[yellow]Initializing database...[/yellow]")

        init_database()
        create_tables()

        console.print("[green]✅ Database initialized successfully[/green]")

    except Exception as e:
        console.print(f"[red]Database initialization failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def init_tenant(
    tenant_id: str = tenant_id_option
):
    """Initialize tenant-specific resources."""
    async def _init_tenant():
        try:
            console.print(f"[yellow]Initializing tenant: {tenant_id}...[/yellow]")

            with AnalyticsClient(tenant_id) as client:
                result = await client.initialize_tenant()

                if result["status"] == "initialized":
                    console.print(f"[green]✅ Tenant {tenant_id} initialized successfully[/green]")

                    if result.get("created_metrics"):
                        console.print("\n[cyan]Created default metrics:[/cyan]")
                        for metric in result["created_metrics"]:
                            console.print(f"  • {metric}")
                else:
                    console.print(f"[red]❌ Tenant initialization failed: {result.get('error')}[/red]")
                    raise typer.Exit(1)

        except Exception as e:
            console.print(f"[red]Tenant initialization failed: {e}[/red]")
            raise typer.Exit(1)

    asyncio.run(_init_tenant())


@app.command()
def track_event(
    event_name: str = typer.Argument(..., help="Event name"),
    event_type: str = typer.Option("custom", help="Event type"),
    user_id: Optional[str] = typer.Option(None, help="User ID"),
    properties: Optional[str] = typer.Option(None, help="Event properties (JSON)"),
    tenant_id: str = tenant_id_option
):
    """Track an analytics event."""
    async def _track_event():
        try:
            import json

            # Parse properties if provided
            event_properties = {}
            if properties:
                event_properties = json.loads(properties)

            with AnalyticsClient(tenant_id) as client:
                result = await client.events.track(
                    event_type=EventType(event_type),
                    event_name=event_name,
                    user_id=user_id,
                    properties=event_properties
                )

                console.print("[green]✅ Event tracked successfully[/green]")
                console.print(f"Event ID: {result['event_id']}")
                console.print(f"Timestamp: {result['timestamp']}")

        except Exception as e:
            console.print(f"[red]Event tracking failed: {e}[/red]")
            raise typer.Exit(1)

    asyncio.run(_track_event())


@app.command()
def create_metric(
    name: str = typer.Argument(..., help="Metric name"),
    display_name: str = typer.Argument(..., help="Display name"),
    metric_type: str = typer.Option("counter", help="Metric type"),
    description: Optional[str] = typer.Option(None, help="Metric description"),
    unit: Optional[str] = typer.Option(None, help="Unit of measurement"),
    tenant_id: str = tenant_id_option
):
    """Create a new metric."""
    async def _create_metric():
        try:
            with AnalyticsClient(tenant_id) as client:
                result = await client.metrics.create_metric(
                    name=name,
                    display_name=display_name,
                    metric_type=MetricType(metric_type),
                    description=description,
                    unit=unit
                )

                console.print("[green]✅ Metric created successfully[/green]")
                console.print(f"Metric ID: {result['metric_id']}")
                console.print(f"Name: {result['name']}")
                console.print(f"Type: {result['metric_type']}")

        except Exception as e:
            console.print(f"[red]Metric creation failed: {e}[/red]")
            raise typer.Exit(1)

    asyncio.run(_create_metric())


@app.command()
def record_metric(
    metric_id: str = typer.Argument(..., help="Metric ID or name"),
    value: float = typer.Argument(..., help="Metric value"),
    tenant_id: str = tenant_id_option
):
    """Record a metric value."""
    async def _record_metric():
        try:
            with AnalyticsClient(tenant_id) as client:
                result = await client.metrics.record_value(
                    metric_id=metric_id,
                    value=value
                )

                console.print("[green]✅ Metric value recorded successfully[/green]")
                console.print(f"Value ID: {result['value_id']}")
                console.print(f"Value: {result['value']}")
                console.print(f"Timestamp: {result['timestamp']}")

        except Exception as e:
            console.print(f"[red]Metric recording failed: {e}[/red]")
            raise typer.Exit(1)

    asyncio.run(_record_metric())


@app.command()
def list_metrics(
    metric_type: Optional[str] = typer.Option(None, help="Filter by metric type"),
    limit: int = typer.Option(10, help="Number of metrics to show"),
    tenant_id: str = tenant_id_option
):
    """List metrics."""
    async def _list_metrics():
        try:
            with AnalyticsClient(tenant_id) as client:
                filter_type = MetricType(metric_type) if metric_type else None
                metrics = await client.metrics.get_metrics(
                    metric_type=filter_type,
                    limit=limit
                )

                if not metrics:
                    console.print("[yellow]No metrics found[/yellow]")
                    return

                table = Table(title=f"Metrics for Tenant: {tenant_id}")
                table.add_column("Name", style="cyan")
                table.add_column("Display Name", style="green")
                table.add_column("Type", style="yellow")
                table.add_column("Unit", style="blue")
                table.add_column("Created", style="magenta")

                for metric in metrics:
                    table.add_row(
                        metric["name"],
                        metric["display_name"],
                        metric["metric_type"],
                        metric.get("unit", "N/A"),
                        metric["created_at"].strftime("%Y-%m-%d %H:%M")
                    )

                console.print(table)

        except Exception as e:
            console.print(f"[red]Failed to list metrics: {e}[/red]")
            raise typer.Exit(1)

    asyncio.run(_list_metrics())


@app.command()
def query_events(
    event_name: Optional[str] = typer.Option(None, help="Filter by event name"),
    user_id: Optional[str] = typer.Option(None, help="Filter by user ID"),
    hours: int = typer.Option(24, help="Hours to look back"),
    limit: int = typer.Option(10, help="Number of events to show"),
    tenant_id: str = tenant_id_option
):
    """Query recent events."""
    async def _query_events():
        try:
            start_time = utc_now() - timedelta(hours=hours)

            with AnalyticsClient(tenant_id) as client:
                events = await client.events.get_events(
                    event_name=event_name,
                    user_id=user_id,
                    start_time=start_time,
                    limit=limit
                )

                if not events:
                    console.print("[yellow]No events found[/yellow]")
                    return

                table = Table(title=f"Recent Events for Tenant: {tenant_id}")
                table.add_column("Event Name", style="cyan")
                table.add_column("Type", style="green")
                table.add_column("User ID", style="yellow")
                table.add_column("Timestamp", style="magenta")

                for event in events:
                    table.add_row(
                        event["event_name"],
                        event["event_type"],
                        event.get("user_id", "N/A"),
                        event["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                    )

                console.print(table)

        except Exception as e:
            console.print(f"[red]Failed to query events: {e}[/red]")
            raise typer.Exit(1)

    asyncio.run(_query_events())


@app.command()
def stats(
    tenant_id: str = tenant_id_option
):
    """Show analytics statistics."""
    async def _show_stats():
        try:
            with AnalyticsClient(tenant_id) as client:
                # Get basic statistics
                health = await client.health_check()

                console.print(Panel.fit(
                    f"[bold]Analytics Statistics[/bold]\n\n"
                    f"Tenant ID: {tenant_id}\n"
                    f"Status: {health['status']}\n"
                    f"Database: {health['database']}\n"
                    f"Configuration: {health['configuration']}",
                    title="DotMac Analytics",
                    border_style="blue"
                ))

        except Exception as e:
            console.print(f"[red]Failed to get statistics: {e}[/red]")
            raise typer.Exit(1)

    asyncio.run(_show_stats())


def main():
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    main()
