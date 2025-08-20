"""
CLI for DotMac Core Events management.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import asyncclick as aclick
import click
import structlog
from tabulate import tabulate

from ..models.envelope import EventEnvelope
from ..persistence.outbox import OutboxStatus, OutboxStore
from ..sdks.event_bus import EventBusSDK
from ..security.tenant_auth import TenantAuthorizer

logger = structlog.get_logger(__name__)


class EventsCLIContext:
    """CLI context for events operations."""

    def __init__(self):
        self.event_bus: Optional[EventBusSDK] = None
        self.outbox_store: Optional[OutboxStore] = None
        self.tenant_authorizer: Optional[TenantAuthorizer] = None
        self.tenant_id: Optional[str] = None
        self.config: Dict[str, Any] = {}

    def load_config(self, config_path: str):
        """Load configuration from file."""
        try:
            with open(config_path) as f:
                self.config = json.load(f)
        except Exception as e:
            click.echo(f"Failed to load config: {e}", err=True)
            sys.exit(1)

    async def initialize(self):
        """Initialize CLI components."""
        # Initialize event bus, outbox store, etc. based on config
        # This would be implemented based on actual configuration
        pass


# CLI Groups
@aclick.group()
@aclick.option("--config", "-c", default="events_config.json", help="Configuration file path")
@aclick.option("--tenant-id", "-t", help="Tenant ID for operations")
@aclick.option("--verbose", "-v", is_flag=True, help="Verbose output")
@aclick.pass_context
async def cli(ctx, config, tenant_id, verbose):
    """DotMac Core Events CLI."""

    # Setup logging
    if verbose:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
        )

    # Initialize context
    ctx.ensure_object(EventsCLIContext)
    ctx.obj.tenant_id = tenant_id

    # Load config if exists
    if Path(config).exists():
        ctx.obj.load_config(config)

    # Initialize components
    await ctx.obj.initialize()


# Events Commands
@cli.group()
async def events():
    """Event publishing and management commands."""
    pass


@events.command()
@aclick.option("--type", "-t", "event_type", required=True, help="Event type")
@aclick.option("--data", "-d", required=True, help="Event data (JSON string)")
@aclick.option("--partition-key", "-p", help="Partition key for ordering")
@aclick.option("--source", "-s", help="Event source")
@aclick.option("--correlation-id", help="Correlation ID")
@aclick.option("--idempotency-key", help="Idempotency key")
@aclick.option("--output", "-o", type=click.Choice(["json", "table"]), default="table", help="Output format")
@aclick.pass_context
async def publish(ctx, event_type, data, partition_key, source, correlation_id, idempotency_key, output):
    """Publish an event."""

    if not ctx.obj.tenant_id:
        click.echo("Error: Tenant ID required. Use --tenant-id or set in config.", err=True)
        return

    try:
        # Parse event data
        event_data = json.loads(data)

        # Create event envelope
        envelope = EventEnvelope.create(
            event_type=event_type,
            data=event_data,
            tenant_id=ctx.obj.tenant_id,
            source=source,
            correlation_id=correlation_id
        )

        # Publish event
        if ctx.obj.event_bus:
            result = await ctx.obj.event_bus.publish(
                event_type=event_type,
                data=event_data,
                partition_key=partition_key,
                idempotency_key=idempotency_key
            )

            if output == "json":
                click.echo(json.dumps({
                    "event_id": envelope.id,
                    "status": "published",
                    "topic": envelope.get_topic_name(),
                    "result": result
                }, indent=2))
            else:
                click.echo("✅ Event published successfully")
                click.echo(f"   Event ID: {envelope.id}")
                click.echo(f"   Topic: {envelope.get_topic_name()}")
                click.echo("   Status: published")
        else:
            click.echo("Error: Event bus not configured", err=True)

    except json.JSONDecodeError:
        click.echo("Error: Invalid JSON data", err=True)
    except Exception as e:
        click.echo(f"Error: Failed to publish event: {e}", err=True)


@events.command()
@aclick.option("--output", "-o", type=click.Choice(["json", "table"]), default="table", help="Output format")
@aclick.pass_context
async def list_topics(ctx, output):
    """List available topics."""

    if not ctx.obj.tenant_id:
        click.echo("Error: Tenant ID required", err=True)
        return

    try:
        if not ctx.obj.event_bus:
            click.echo("Error: Event bus not configured", err=True)
            return

        topics = await ctx.obj.event_bus.list_topics(tenant_id=ctx.obj.tenant_id)

        if output == "json":
            click.echo(json.dumps(topics, indent=2))
        elif topics:
            click.echo("📋 Available Topics:")
            for topic in topics:
                click.echo(f"   • {topic}")
        else:
            click.echo("No topics found for tenant")

    except Exception as e:
        click.echo(f"Error: Failed to list topics: {e}", err=True)


@events.command()
@aclick.argument("topic_name")
@aclick.option("--output", "-o", type=click.Choice(["json", "table"]), default="table", help="Output format")
@aclick.pass_context
async def topic_info(ctx, topic_name, output):
    """Get topic information."""

    try:
        if not ctx.obj.event_bus:
            click.echo("Error: Event bus not configured", err=True)
            return

        info = await ctx.obj.event_bus.get_topic_info(topic_name)

        if output == "json":
            click.echo(json.dumps(info, indent=2))
        else:
            click.echo(f"📊 Topic: {topic_name}")
            click.echo(f"   Partitions: {info.get('partition_count', 'N/A')}")
            click.echo(f"   Messages: {info.get('message_count', 'N/A')}")
            click.echo(f"   Consumer Groups: {len(info.get('consumer_groups', []))}")
            if info.get("retention_hours"):
                click.echo(f"   Retention: {info['retention_hours']} hours")

    except Exception as e:
        click.echo(f"Error: Failed to get topic info: {e}", err=True)


# Consumer Commands
@cli.group()
async def consumers():
    """Consumer group management commands."""
    pass


@consumers.command()
@aclick.option("--topic", help="Filter by topic")
@aclick.option("--output", "-o", type=click.Choice(["json", "table"]), default="table", help="Output format")
@aclick.pass_context
async def list_groups(ctx, topic, output):
    """List consumer groups."""

    if not ctx.obj.tenant_id:
        click.echo("Error: Tenant ID required", err=True)
        return

    try:
        if not ctx.obj.event_bus:
            click.echo("Error: Event bus not configured", err=True)
            return

        groups = await ctx.obj.event_bus.list_consumer_groups(
            tenant_id=ctx.obj.tenant_id,
            topic=topic
        )

        if output == "json":
            click.echo(json.dumps(groups, indent=2))
        elif groups:
            click.echo("👥 Consumer Groups:")
            for group in groups:
                click.echo(f"   • {group}")
        else:
            click.echo("No consumer groups found")

    except Exception as e:
        click.echo(f"Error: Failed to list consumer groups: {e}", err=True)


@consumers.command()
@aclick.argument("group_name")
@aclick.option("--output", "-o", type=click.Choice(["json", "table"]), default="table", help="Output format")
@aclick.pass_context
async def lag(ctx, group_name, output):
    """Get consumer group lag."""

    try:
        if not ctx.obj.event_bus:
            click.echo("Error: Event bus not configured", err=True)
            return

        lag_info = await ctx.obj.event_bus.get_consumer_lag(group_name)

        if output == "json":
            click.echo(json.dumps(lag_info, indent=2, default=str))
        else:
            total_lag = lag_info.get("total_lag", 0)
            click.echo(f"📈 Consumer Group: {group_name}")
            click.echo(f"   Total Lag: {total_lag} messages")

            partition_lags = lag_info.get("partition_lags", {})
            if partition_lags:
                click.echo("   Partition Lags:")
                for partition, lag in partition_lags.items():
                    click.echo(f"     Partition {partition}: {lag} messages")

            if lag_info.get("last_updated"):
                click.echo(f"   Last Updated: {lag_info['last_updated']}")

    except Exception as e:
        click.echo(f"Error: Failed to get consumer lag: {e}", err=True)


# Replay Commands
@cli.group()
async def replay():
    """Event replay commands."""
    pass


@replay.command()
@aclick.argument("topic")
@aclick.argument("consumer_group")
@aclick.option("--from-time", help="Start timestamp (ISO format)")
@aclick.option("--to-time", help="End timestamp (ISO format)")
@aclick.option("--max-events", type=int, default=1000, help="Maximum events to replay")
@aclick.option("--output", "-o", type=click.Choice(["json", "table"]), default="table", help="Output format")
@aclick.pass_context
async def start(ctx, topic, consumer_group, from_time, to_time, max_events, output):
    """Start event replay."""

    if not ctx.obj.tenant_id:
        click.echo("Error: Tenant ID required", err=True)
        return

    try:
        if not ctx.obj.event_bus:
            click.echo("Error: Event bus not configured", err=True)
            return

        # Parse timestamps
        from_timestamp = None
        to_timestamp = None

        if from_time:
            from_timestamp = datetime.fromisoformat(from_time.replace("Z", "+00:00"))
        if to_time:
            to_timestamp = datetime.fromisoformat(to_time.replace("Z", "+00:00"))

        # Start replay
        result = await ctx.obj.event_bus.replay_events(
            topic=topic,
            consumer_group=consumer_group,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            max_events=max_events,
            tenant_id=ctx.obj.tenant_id
        )

        if output == "json":
            click.echo(json.dumps(result, indent=2, default=str))
        else:
            click.echo("🔄 Replay started")
            click.echo(f"   Replay ID: {result['replay_id']}")
            click.echo(f"   Status: {result['status']}")
            click.echo(f"   Events Count: {result['events_count']}")
            if result.get("estimated_duration_seconds"):
                click.echo(f"   Estimated Duration: {result['estimated_duration_seconds']}s")

    except ValueError as e:
        click.echo(f"Error: Invalid timestamp format: {e}", err=True)
    except Exception as e:
        click.echo(f"Error: Failed to start replay: {e}", err=True)


@replay.command()
@aclick.argument("replay_id")
@aclick.option("--output", "-o", type=click.Choice(["json", "table"]), default="table", help="Output format")
@aclick.pass_context
async def status(ctx, replay_id, output):
    """Get replay status."""

    if not ctx.obj.tenant_id:
        click.echo("Error: Tenant ID required", err=True)
        return

    try:
        if not ctx.obj.event_bus:
            click.echo("Error: Event bus not configured", err=True)
            return

        status_info = await ctx.obj.event_bus.get_replay_status(
            replay_id,
            tenant_id=ctx.obj.tenant_id
        )

        if output == "json":
            click.echo(json.dumps(status_info, indent=2, default=str))
        else:
            click.echo(f"📊 Replay: {replay_id}")
            click.echo(f"   Status: {status_info.get('status', 'unknown')}")
            click.echo(f"   Events Replayed: {status_info.get('events_replayed', 0)}")

            progress = status_info.get("progress", {})
            if progress:
                click.echo(f"   Progress: {progress.get('percentage', 0)}%")

            if status_info.get("started_at"):
                click.echo(f"   Started: {status_info['started_at']}")
            if status_info.get("completed_at"):
                click.echo(f"   Completed: {status_info['completed_at']}")

            errors = status_info.get("errors", [])
            if errors:
                click.echo(f"   Errors: {len(errors)}")
                for error in errors[:3]:  # Show first 3 errors
                    click.echo(f"     • {error}")

    except Exception as e:
        click.echo(f"Error: Failed to get replay status: {e}", err=True)


# Outbox Commands
@cli.group()
async def outbox():
    """Outbox management commands."""
    pass


@outbox.command()
@aclick.option("--status", type=click.Choice(["pending", "published", "failed", "expired"]), help="Filter by status")
@aclick.option("--limit", type=int, default=50, help="Maximum entries to show")
@aclick.option("--output", "-o", type=click.Choice(["json", "table"]), default="table", help="Output format")
@aclick.pass_context
async def list_entries(ctx, status, limit, output):
    """List outbox entries."""

    if not ctx.obj.tenant_id:
        click.echo("Error: Tenant ID required", err=True)
        return

    try:
        if not ctx.obj.outbox_store:
            click.echo("Error: Outbox store not configured", err=True)
            return

        # Get entries based on status
        if status == "pending":
            entries = await ctx.obj.outbox_store.get_pending_entries(limit, ctx.obj.tenant_id)
        elif status == "failed":
            entries = await ctx.obj.outbox_store.get_failed_entries(limit)
            # Filter by tenant
            entries = [e for e in entries if e.tenant_id == ctx.obj.tenant_id]
        else:
            entries = await ctx.obj.outbox_store.get_pending_entries(limit, ctx.obj.tenant_id)

        if output == "json":
            entries_data = [
                {
                    "id": e.id,
                    "envelope_id": e.envelope_id,
                    "topic": e.topic,
                    "status": e.status.value,
                    "created_at": e.created_at.isoformat(),
                    "retry_count": e.retry_count,
                    "last_error": e.last_error
                }
                for e in entries
            ]
            click.echo(json.dumps(entries_data, indent=2))
        elif entries:
            table_data = []
            for entry in entries:
                table_data.append([
                    entry.id[:12] + "...",
                    entry.envelope_id[:12] + "...",
                    entry.topic,
                    entry.status.value,
                    entry.created_at.strftime("%Y-%m-%d %H:%M"),
                    entry.retry_count,
                    entry.last_error[:30] + "..." if entry.last_error else ""
                ])

            headers = ["Entry ID", "Envelope ID", "Topic", "Status", "Created", "Retries", "Error"]
            click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
        else:
            click.echo("No outbox entries found")

    except Exception as e:
        click.echo(f"Error: Failed to list outbox entries: {e}", err=True)


@outbox.command()
@aclick.option("--output", "-o", type=click.Choice(["json", "table"]), default="table", help="Output format")
@aclick.pass_context
async def stats(ctx, output):
    """Get outbox statistics."""

    try:
        if not ctx.obj.outbox_store:
            click.echo("Error: Outbox store not configured", err=True)
            return

        stats = await ctx.obj.outbox_store.get_stats()

        if output == "json":
            click.echo(json.dumps(stats, indent=2))
        else:
            click.echo("📊 Outbox Statistics")
            click.echo(f"   Total Entries: {stats.get('total_entries', 0)}")

            by_status = stats.get("by_status", {})
            click.echo("   By Status:")
            for status, count in by_status.items():
                click.echo(f"     {status.title()}: {count}")

            avg_time = stats.get("avg_publish_time_seconds", 0)
            click.echo(f"   Avg Publish Time: {avg_time:.2f}s")

            top_tenants = stats.get("top_tenants_by_pending", [])
            if top_tenants:
                click.echo("   Top Tenants (by pending):")
                for tenant in top_tenants[:5]:
                    click.echo(f"     {tenant['tenant_id']}: {tenant['count']}")

    except Exception as e:
        click.echo(f"Error: Failed to get outbox stats: {e}", err=True)


@outbox.command()
@aclick.argument("entry_id")
@aclick.pass_context
async def retry(ctx, entry_id):
    """Retry failed outbox entry."""

    if not ctx.obj.tenant_id:
        click.echo("Error: Tenant ID required", err=True)
        return

    try:
        if not ctx.obj.outbox_store:
            click.echo("Error: Outbox store not configured", err=True)
            return

        # Get entry and verify access
        entry = await ctx.obj.outbox_store.get_entry(entry_id)
        if not entry:
            click.echo("Error: Outbox entry not found", err=True)
            return

        if entry.tenant_id != ctx.obj.tenant_id:
            click.echo("Error: Access denied to outbox entry", err=True)
            return

        if entry.status != OutboxStatus.FAILED:
            click.echo("Error: Entry is not in failed status", err=True)
            return

        # Reset to pending
        success = await ctx.obj.outbox_store.update_status(entry_id, OutboxStatus.PENDING)

        if success:
            click.echo(f"✅ Outbox entry {entry_id} queued for retry")
        else:
            click.echo("❌ Failed to queue entry for retry", err=True)

    except Exception as e:
        click.echo(f"Error: Failed to retry outbox entry: {e}", err=True)


# Metrics Commands
@cli.command()
@aclick.option("--output", "-o", type=click.Choice(["json", "table"]), default="table", help="Output format")
@aclick.pass_context
async def metrics(ctx, output):
    """Get events metrics."""

    if not ctx.obj.tenant_id:
        click.echo("Error: Tenant ID required", err=True)
        return

    try:
        if not ctx.obj.event_bus:
            click.echo("Error: Event bus not configured", err=True)
            return

        metrics = await ctx.obj.event_bus.get_metrics(tenant_id=ctx.obj.tenant_id)

        if output == "json":
            click.echo(json.dumps(metrics, indent=2, default=str))
        else:
            click.echo(f"📈 Events Metrics (Tenant: {ctx.obj.tenant_id})")
            click.echo(f"   Events Published: {metrics.get('events_published_total', 0)}")
            click.echo(f"   Events Consumed: {metrics.get('events_consumed_total', 0)}")
            click.echo(f"   Publish Errors: {metrics.get('publish_errors_total', 0)}")
            click.echo(f"   Consumer Lag: {metrics.get('consumer_lag_total', 0)}")

            if metrics.get("last_updated"):
                click.echo(f"   Last Updated: {metrics['last_updated']}")

    except Exception as e:
        click.echo(f"Error: Failed to get metrics: {e}", err=True)


# Utility Commands
@cli.command()
@aclick.argument("config_file", type=click.Path())
async def init_config(config_file):
    """Initialize configuration file."""

    config = {
        "event_bus": {
            "adapter": "redis",
            "connection": {
                "host": "localhost",
                "port": 6379,
                "db": 0
            }
        },
        "outbox": {
            "enabled": True,
            "database_url": "postgresql://user:pass@localhost/events"
        },
        "tenant_auth": {
            "secret_key": "your-secret-key-here",
            "token_ttl_hours": 24
        }
    }

    try:
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)

        click.echo(f"✅ Configuration file created: {config_file}")
        click.echo("Please update the configuration with your actual settings.")

    except Exception as e:
        click.echo(f"Error: Failed to create config file: {e}", err=True)


if __name__ == "__main__":
    cli()
