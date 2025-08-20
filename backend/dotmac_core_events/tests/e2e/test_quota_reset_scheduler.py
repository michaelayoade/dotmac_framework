"""
End-to-end test for quota reset scheduler functionality.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock

import pytest
import structlog

from dotmac_core_events.models.envelope import EventEnvelope
from dotmac_core_events.sdks.event_bus import EventBusSDK

logger = structlog.get_logger(__name__)


class QuotaManager:
    """Quota management system."""

    def __init__(self):
        self.quotas = {}
        self.usage = {}
        self.reset_history = []

    def set_quota(self, tenant_id: str, resource_type: str, limit: int, reset_period: str = "monthly"):
        """Set quota for a tenant and resource type."""
        key = f"{tenant_id}:{resource_type}"
        self.quotas[key] = {
            "tenant_id": tenant_id,
            "resource_type": resource_type,
            "limit": limit,
            "reset_period": reset_period,
            "created_at": datetime.now(timezone.utc),
            "last_reset": datetime.now(timezone.utc)
        }

        # Initialize usage
        if key not in self.usage:
            self.usage[key] = 0

    def get_quota(self, tenant_id: str, resource_type: str) -> Optional[Dict[str, Any]]:
        """Get quota information."""
        key = f"{tenant_id}:{resource_type}"
        if key not in self.quotas:
            return None

        quota = self.quotas[key].copy()
        quota["current_usage"] = self.usage.get(key, 0)
        quota["remaining"] = max(0, quota["limit"] - quota["current_usage"])
        quota["utilization"] = quota["current_usage"] / quota["limit"] if quota["limit"] > 0 else 0

        return quota

    def consume_quota(self, tenant_id: str, resource_type: str, amount: int = 1) -> bool:
        """Consume quota and return whether successful."""
        key = f"{tenant_id}:{resource_type}"

        if key not in self.quotas:
            return False

        current_usage = self.usage.get(key, 0)
        quota_limit = self.quotas[key]["limit"]

        if current_usage + amount > quota_limit:
            return False  # Quota exceeded

        self.usage[key] = current_usage + amount
        return True

    def reset_quota(self, tenant_id: str, resource_type: str) -> Dict[str, Any]:
        """Reset quota usage for a tenant and resource type."""
        key = f"{tenant_id}:{resource_type}"

        if key not in self.quotas:
            raise ValueError(f"Quota not found for {tenant_id}:{resource_type}")

        old_usage = self.usage.get(key, 0)
        self.usage[key] = 0
        self.quotas[key]["last_reset"] = datetime.now(timezone.utc)

        reset_record = {
            "tenant_id": tenant_id,
            "resource_type": resource_type,
            "old_usage": old_usage,
            "reset_at": self.quotas[key]["last_reset"],
            "quota_limit": self.quotas[key]["limit"]
        }

        self.reset_history.append(reset_record)

        logger.info("Quota reset", tenant_id=tenant_id, resource_type=resource_type, old_usage=old_usage)
        return reset_record

    def get_quotas_for_reset(self, reset_period: str) -> List[Dict[str, Any]]:
        """Get quotas that need to be reset based on period."""
        now = datetime.now(timezone.utc)
        quotas_to_reset = []

        for key, quota in self.quotas.items():
            if quota["reset_period"] != reset_period:
                continue

            last_reset = quota["last_reset"]

            # Determine if reset is due
            reset_due = False

            if reset_period == "daily":
                reset_due = now.date() > last_reset.date()
            elif reset_period == "weekly":
                # Reset on Monday
                days_since_reset = (now - last_reset).days
                reset_due = days_since_reset >= 7 or (now.weekday() == 0 and last_reset.weekday() != 0)
            elif reset_period == "monthly":
                reset_due = now.month != last_reset.month or now.year != last_reset.year
            elif reset_period == "yearly":
                reset_due = now.year != last_reset.year

            if reset_due:
                quota_info = quota.copy()
                quota_info["current_usage"] = self.usage.get(key, 0)
                quotas_to_reset.append(quota_info)

        return quotas_to_reset


class QuotaResetScheduler:
    """Scheduler for quota resets."""

    def __init__(self, event_bus: EventBusSDK, quota_manager: QuotaManager):
        self.event_bus = event_bus
        self.quota_manager = quota_manager
        self.running = False
        self.reset_tasks = {}
        self.reset_stats = {
            "total_resets": 0,
            "successful_resets": 0,
            "failed_resets": 0,
            "last_run": None
        }

    async def start(self):
        """Start the quota reset scheduler."""
        self.running = True

        # Schedule different reset periods
        self.reset_tasks = {
            "daily": asyncio.create_task(self._schedule_daily_resets()),
            "weekly": asyncio.create_task(self._schedule_weekly_resets()),
            "monthly": asyncio.create_task(self._schedule_monthly_resets())
        }

        logger.info("Quota reset scheduler started")

    async def stop(self):
        """Stop the quota reset scheduler."""
        self.running = False

        for task in self.reset_tasks.values():
            task.cancel()

        await asyncio.gather(*self.reset_tasks.values(), return_exceptions=True)

        logger.info("Quota reset scheduler stopped")

    async def trigger_reset(self, reset_period: str = "all"):
        """Manually trigger quota reset for testing."""
        if reset_period == "all":
            periods = ["daily", "weekly", "monthly", "yearly"]
        else:
            periods = [reset_period]

        for period in periods:
            await self._process_quota_resets(period)

    async def _schedule_daily_resets(self):
        """Schedule daily quota resets."""
        while self.running:
            try:
                # Run at midnight UTC
                now = datetime.now(timezone.utc)
                next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                sleep_seconds = (next_midnight - now).total_seconds()

                # For testing, use shorter intervals
                sleep_seconds = min(sleep_seconds, 1.0)  # Max 1 second for tests

                await asyncio.sleep(sleep_seconds)

                if self.running:
                    await self._process_quota_resets("daily")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in daily reset scheduler", error=str(e))
                await asyncio.sleep(60)  # Wait before retrying

    async def _schedule_weekly_resets(self):
        """Schedule weekly quota resets."""
        while self.running:
            try:
                # Run on Monday at midnight UTC
                now = datetime.now(timezone.utc)
                days_until_monday = (7 - now.weekday()) % 7
                if days_until_monday == 0 and now.hour == 0 and now.minute == 0:
                    days_until_monday = 7  # Next Monday

                next_monday = (now + timedelta(days=days_until_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
                sleep_seconds = (next_monday - now).total_seconds()

                # For testing, use shorter intervals
                sleep_seconds = min(sleep_seconds, 2.0)  # Max 2 seconds for tests

                await asyncio.sleep(sleep_seconds)

                if self.running:
                    await self._process_quota_resets("weekly")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in weekly reset scheduler", error=str(e))
                await asyncio.sleep(120)  # Wait before retrying

    async def _schedule_monthly_resets(self):
        """Schedule monthly quota resets."""
        while self.running:
            try:
                # Run on the first day of each month at midnight UTC
                now = datetime.now(timezone.utc)

                if now.month == 12:
                    next_month = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                else:
                    next_month = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)

                sleep_seconds = (next_month - now).total_seconds()

                # For testing, use shorter intervals
                sleep_seconds = min(sleep_seconds, 3.0)  # Max 3 seconds for tests

                await asyncio.sleep(sleep_seconds)

                if self.running:
                    await self._process_quota_resets("monthly")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in monthly reset scheduler", error=str(e))
                await asyncio.sleep(300)  # Wait before retrying

    async def _process_quota_resets(self, reset_period: str):
        """Process quota resets for a given period."""
        try:
            self.reset_stats["last_run"] = datetime.now(timezone.utc)

            # Get quotas that need reset
            quotas_to_reset = self.quota_manager.get_quotas_for_reset(reset_period)

            if not quotas_to_reset:
                logger.debug("No quotas to reset", period=reset_period)
                return

            logger.info("Processing quota resets", period=reset_period, count=len(quotas_to_reset))

            # Publish batch reset started event
            await self.event_bus.publish(
                event_type="quota.reset.batch.started",
                data={
                    "reset_period": reset_period,
                    "quota_count": len(quotas_to_reset),
                    "started_at": self.reset_stats["last_run"].isoformat()
                }
            )

            successful_resets = 0
            failed_resets = 0

            # Process each quota reset
            for quota in quotas_to_reset:
                try:
                    # Reset the quota
                    reset_record = self.quota_manager.reset_quota(
                        quota["tenant_id"],
                        quota["resource_type"]
                    )

                    # Publish individual reset event
                    await self.event_bus.publish(
                        event_type="quota.reset.completed",
                        data={
                            "tenant_id": quota["tenant_id"],
                            "resource_type": quota["resource_type"],
                            "old_usage": reset_record["old_usage"],
                            "quota_limit": reset_record["quota_limit"],
                            "reset_period": reset_period,
                            "reset_at": reset_record["reset_at"].isoformat()
                        },
                        partition_key=quota["tenant_id"]
                    )

                    successful_resets += 1
                    self.reset_stats["successful_resets"] += 1

                except Exception as e:
                    logger.error("Failed to reset quota",
                               tenant_id=quota["tenant_id"],
                               resource_type=quota["resource_type"],
                               error=str(e))

                    # Publish reset failed event
                    await self.event_bus.publish(
                        event_type="quota.reset.failed",
                        data={
                            "tenant_id": quota["tenant_id"],
                            "resource_type": quota["resource_type"],
                            "reset_period": reset_period,
                            "error": str(e),
                            "failed_at": datetime.now(timezone.utc).isoformat()
                        },
                        partition_key=quota["tenant_id"]
                    )

                    failed_resets += 1
                    self.reset_stats["failed_resets"] += 1

            # Publish batch reset completed event
            await self.event_bus.publish(
                event_type="quota.reset.batch.completed",
                data={
                    "reset_period": reset_period,
                    "total_quotas": len(quotas_to_reset),
                    "successful_resets": successful_resets,
                    "failed_resets": failed_resets,
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }
            )

            self.reset_stats["total_resets"] += len(quotas_to_reset)

            logger.info("Quota reset batch completed",
                       period=reset_period,
                       successful=successful_resets,
                       failed=failed_resets)

        except Exception as e:
            logger.error("Error processing quota resets", period=reset_period, error=str(e))

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        return self.reset_stats.copy()


@pytest.fixture
async def event_bus():
    """Create mock event bus."""
    bus = AsyncMock(spec=EventBusSDK)
    bus.published_events = []

    async def mock_publish(event_type, data, **kwargs):
        envelope = EventEnvelope.create(
            event_type=event_type,
            data=data,
            tenant_id=data.get("tenant_id", "system")
        )
        bus.published_events.append(envelope)
        return {"status": "published", "message_id": f"msg_{len(bus.published_events)}"}

    bus.publish = mock_publish
    return bus


@pytest.fixture
def quota_manager():
    """Create quota manager."""
    return QuotaManager()


@pytest.fixture
async def quota_scheduler(event_bus, quota_manager):
    """Create quota reset scheduler."""
    scheduler = QuotaResetScheduler(event_bus, quota_manager)
    yield scheduler
    if scheduler.running:
        await scheduler.stop()


class TestQuotaResetScheduler:
    """Test quota reset scheduler functionality."""

    @pytest.mark.asyncio
    async def test_quota_management_basic(self, quota_manager):
        """Test basic quota management operations."""

        # Set quota
        quota_manager.set_quota("tenant_1", "api_calls", 1000, "monthly")

        # Get quota
        quota = quota_manager.get_quota("tenant_1", "api_calls")
        assert quota is not None
        assert quota["limit"] == 1000
        assert quota["current_usage"] == 0
        assert quota["remaining"] == 1000
        assert quota["utilization"] == 0.0

        # Consume quota
        success = quota_manager.consume_quota("tenant_1", "api_calls", 100)
        assert success is True

        # Check updated quota
        quota = quota_manager.get_quota("tenant_1", "api_calls")
        assert quota["current_usage"] == 100
        assert quota["remaining"] == 900
        assert quota["utilization"] == 0.1

        # Try to exceed quota
        success = quota_manager.consume_quota("tenant_1", "api_calls", 1000)
        assert success is False  # Should fail

        # Usage should remain unchanged
        quota = quota_manager.get_quota("tenant_1", "api_calls")
        assert quota["current_usage"] == 100

    @pytest.mark.asyncio
    async def test_quota_reset(self, quota_manager):
        """Test quota reset functionality."""

        # Set up quota and consume some
        quota_manager.set_quota("tenant_2", "storage_gb", 500, "daily")
        quota_manager.consume_quota("tenant_2", "storage_gb", 200)

        # Verify usage
        quota = quota_manager.get_quota("tenant_2", "storage_gb")
        assert quota["current_usage"] == 200

        # Reset quota
        reset_record = quota_manager.reset_quota("tenant_2", "storage_gb")

        # Verify reset
        assert reset_record["old_usage"] == 200
        assert reset_record["tenant_id"] == "tenant_2"
        assert reset_record["resource_type"] == "storage_gb"

        # Check quota after reset
        quota = quota_manager.get_quota("tenant_2", "storage_gb")
        assert quota["current_usage"] == 0
        assert quota["remaining"] == 500

        # Verify reset history
        assert len(quota_manager.reset_history) == 1
        assert quota_manager.reset_history[0]["old_usage"] == 200

    @pytest.mark.asyncio
    async def test_scheduler_manual_trigger(self, quota_scheduler, quota_manager, event_bus):
        """Test manual quota reset trigger."""

        # Set up multiple quotas
        quota_manager.set_quota("tenant_1", "api_calls", 1000, "daily")
        quota_manager.set_quota("tenant_2", "storage_gb", 500, "daily")
        quota_manager.set_quota("tenant_3", "bandwidth_mb", 2000, "weekly")

        # Consume some quota
        quota_manager.consume_quota("tenant_1", "api_calls", 300)
        quota_manager.consume_quota("tenant_2", "storage_gb", 150)
        quota_manager.consume_quota("tenant_3", "bandwidth_mb", 800)

        # Manually trigger daily resets
        await quota_scheduler.trigger_reset("daily")

        # Verify quotas were reset
        quota1 = quota_manager.get_quota("tenant_1", "api_calls")
        quota2 = quota_manager.get_quota("tenant_2", "storage_gb")
        quota3 = quota_manager.get_quota("tenant_3", "bandwidth_mb")

        assert quota1["current_usage"] == 0  # Reset
        assert quota2["current_usage"] == 0  # Reset
        assert quota3["current_usage"] == 800  # Not reset (weekly period)

        # Check events were published
        reset_events = [e for e in event_bus.published_events if e.type == "quota.reset.completed"]
        assert len(reset_events) == 2  # Only daily quotas reset

        batch_events = [e for e in event_bus.published_events if e.type == "quota.reset.batch.completed"]
        assert len(batch_events) == 1
        assert batch_events[0].data["successful_resets"] == 2

    @pytest.mark.asyncio
    async def test_scheduler_automatic_execution(self, quota_scheduler, quota_manager, event_bus):
        """Test automatic scheduler execution."""

        # Set up quotas
        quota_manager.set_quota("tenant_auto", "requests", 100, "daily")
        quota_manager.consume_quota("tenant_auto", "requests", 50)

        # Start scheduler
        await quota_scheduler.start()

        # Wait for scheduler to run (short interval for testing)
        await asyncio.sleep(1.5)

        # Stop scheduler
        await quota_scheduler.stop()

        # Verify quota was reset
        quota = quota_manager.get_quota("tenant_auto", "requests")
        assert quota["current_usage"] == 0

        # Verify events were published
        reset_events = [e for e in event_bus.published_events if e.type == "quota.reset.completed"]
        assert len(reset_events) >= 1

    @pytest.mark.asyncio
    async def test_scheduler_error_handling(self, quota_scheduler, quota_manager, event_bus):
        """Test scheduler error handling."""

        # Mock quota manager to raise exception
        original_reset = quota_manager.reset_quota

        def failing_reset(tenant_id, resource_type):
            if tenant_id == "failing_tenant":
                raise Exception("Simulated reset failure")
            return original_reset(tenant_id, resource_type)

        quota_manager.reset_quota = failing_reset

        # Set up quotas - one that will fail, one that will succeed
        quota_manager.set_quota("failing_tenant", "api_calls", 1000, "daily")
        quota_manager.set_quota("success_tenant", "api_calls", 1000, "daily")

        quota_manager.consume_quota("failing_tenant", "api_calls", 100)
        quota_manager.consume_quota("success_tenant", "api_calls", 200)

        # Trigger reset
        await quota_scheduler.trigger_reset("daily")

        # Check that successful tenant was reset
        success_quota = quota_manager.get_quota("success_tenant", "api_calls")
        assert success_quota["current_usage"] == 0

        # Check that failing tenant was not reset
        failing_quota = quota_manager.get_quota("failing_tenant", "api_calls")
        assert failing_quota["current_usage"] == 100

        # Verify error events were published
        failed_events = [e for e in event_bus.published_events if e.type == "quota.reset.failed"]
        assert len(failed_events) == 1
        assert failed_events[0].data["tenant_id"] == "failing_tenant"

        # Check stats
        stats = quota_scheduler.get_stats()
        assert stats["failed_resets"] == 1
        assert stats["successful_resets"] == 1

    @pytest.mark.asyncio
    async def test_multiple_reset_periods(self, quota_scheduler, quota_manager, event_bus):
        """Test handling of multiple reset periods."""

        # Set up quotas with different periods
        quota_manager.set_quota("daily_tenant", "api_calls", 1000, "daily")
        quota_manager.set_quota("weekly_tenant", "storage_gb", 500, "weekly")
        quota_manager.set_quota("monthly_tenant", "bandwidth_mb", 2000, "monthly")

        # Consume quota
        quota_manager.consume_quota("daily_tenant", "api_calls", 300)
        quota_manager.consume_quota("weekly_tenant", "storage_gb", 150)
        quota_manager.consume_quota("monthly_tenant", "bandwidth_mb", 800)

        # Trigger all resets
        await quota_scheduler.trigger_reset("all")

        # Verify all quotas were reset
        daily_quota = quota_manager.get_quota("daily_tenant", "api_calls")
        weekly_quota = quota_manager.get_quota("weekly_tenant", "storage_gb")
        monthly_quota = quota_manager.get_quota("monthly_tenant", "bandwidth_mb")

        assert daily_quota["current_usage"] == 0
        assert weekly_quota["current_usage"] == 0
        assert monthly_quota["current_usage"] == 0

        # Check that separate batch events were published for each period
        batch_events = [e for e in event_bus.published_events if e.type == "quota.reset.batch.completed"]
        reset_periods = {event.data["reset_period"] for event in batch_events}
        assert "daily" in reset_periods
        assert "weekly" in reset_periods
        assert "monthly" in reset_periods

    @pytest.mark.asyncio
    async def test_concurrent_scheduler_operations(self, quota_scheduler, quota_manager, event_bus):
        """Test concurrent scheduler operations."""

        # Set up multiple quotas
        for i in range(5):
            quota_manager.set_quota(f"tenant_{i}", "api_calls", 1000, "daily")
            quota_manager.consume_quota(f"tenant_{i}", "api_calls", 100 * (i + 1))

        # Start scheduler
        await quota_scheduler.start()

        # Trigger manual reset while scheduler is running
        manual_task = asyncio.create_task(quota_scheduler.trigger_reset("daily"))

        # Wait for both to complete
        await asyncio.sleep(2.0)
        await manual_task

        # Stop scheduler
        await quota_scheduler.stop()

        # Verify all quotas were reset
        for i in range(5):
            quota = quota_manager.get_quota(f"tenant_{i}", "api_calls")
            assert quota["current_usage"] == 0

        # Verify events were published (may have duplicates due to concurrent execution)
        reset_events = [e for e in event_bus.published_events if e.type == "quota.reset.completed"]
        assert len(reset_events) >= 5  # At least one reset per tenant

    @pytest.mark.asyncio
    async def test_scheduler_stats_tracking(self, quota_scheduler, quota_manager):
        """Test scheduler statistics tracking."""

        # Set up quotas
        quota_manager.set_quota("stats_tenant_1", "api_calls", 1000, "daily")
        quota_manager.set_quota("stats_tenant_2", "storage_gb", 500, "daily")

        # Initial stats
        stats = quota_scheduler.get_stats()
        assert stats["total_resets"] == 0
        assert stats["successful_resets"] == 0
        assert stats["failed_resets"] == 0
        assert stats["last_run"] is None

        # Trigger reset
        await quota_scheduler.trigger_reset("daily")

        # Check updated stats
        stats = quota_scheduler.get_stats()
        assert stats["total_resets"] == 2
        assert stats["successful_resets"] == 2
        assert stats["failed_resets"] == 0
        assert stats["last_run"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
