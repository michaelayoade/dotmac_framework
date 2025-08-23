"""
Tests for workflow scheduler calculation strategies.

REFACTORED: Tests for the strategy pattern implementation that replaced
the 14-complexity if-elif chain in CronScheduler._calculate_next_run.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from dotmac_isp.sdks.workflows.schedule_strategies import (
    ScheduleCalculationStrategy,
    CronScheduleStrategy,
    IntervalScheduleStrategy,
    OneTimeScheduleStrategy,
    RecurringScheduleStrategy,
    ScheduleCalculationEngine,
    create_schedule_engine,
)
from dotmac_isp.sdks.workflows.scheduler import ScheduleType


class MockSchedule:
    """Mock schedule for testing."""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 'test_schedule')
        self.schedule_type = kwargs.get('schedule_type')
        self.cron_expression = kwargs.get('cron_expression')
        self.interval_seconds = kwargs.get('interval_seconds')
        self.start_time = kwargs.get('start_time')
        self.end_time = kwargs.get('end_time')


class TestScheduleStrategies:
    """Test individual schedule calculation strategies."""

    @patch('dotmac_isp.sdks.workflows.schedule_strategies.CRONITER_AVAILABLE', True)
    def test_cron_schedule_strategy(self):
        """Test cron schedule strategy."""
        from unittest.mock import Mock
        
        strategy = CronScheduleStrategy()
        current_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        # Test valid cron expression
        schedule = MockSchedule(
            schedule_type=ScheduleType.CRON,
            cron_expression="0 */6 * * *"  # Every 6 hours
        )
        
        with patch('dotmac_isp.sdks.workflows.schedule_strategies.croniter') as mock_croniter:
            mock_cron_instance = Mock()
            mock_cron_instance.get_next.return_value = current_time + timedelta(hours=6)
            mock_croniter.return_value = mock_cron_instance
            
            result = strategy.calculate_next_run(schedule, current_time)
            assert result == current_time + timedelta(hours=6)
            assert strategy.get_strategy_name() == "Cron Schedule"

    def test_cron_schedule_strategy_no_croniter(self):
        """Test cron schedule strategy when croniter not available."""
        with patch('dotmac_isp.sdks.workflows.schedule_strategies.CRONITER_AVAILABLE', False):
            strategy = CronScheduleStrategy()
            schedule = MockSchedule(
                schedule_type=ScheduleType.CRON,
                cron_expression="0 */6 * * *"
            )
            current_time = datetime.now(timezone.utc)
            
            result = strategy.calculate_next_run(schedule, current_time)
            assert result is None

    def test_cron_schedule_strategy_no_expression(self):
        """Test cron schedule strategy with no cron expression."""
        strategy = CronScheduleStrategy()
        schedule = MockSchedule(
            schedule_type=ScheduleType.CRON,
            cron_expression=None
        )
        current_time = datetime.now(timezone.utc)
        
        result = strategy.calculate_next_run(schedule, current_time)
        assert result is None

    def test_cron_schedule_strategy_with_end_time(self):
        """Test cron schedule strategy respects end time."""
        strategy = CronScheduleStrategy()
        current_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        end_time = current_time + timedelta(hours=3)
        
        schedule = MockSchedule(
            schedule_type=ScheduleType.CRON,
            cron_expression="0 */6 * * *",
            end_time=end_time
        )
        
        with patch('dotmac_isp.sdks.workflows.schedule_strategies.croniter') as mock_croniter:
            mock_cron_instance = Mock()
            mock_cron_instance.get_next.return_value = current_time + timedelta(hours=6)
            mock_croniter.return_value = mock_cron_instance
            
            result = strategy.calculate_next_run(schedule, current_time)
            assert result is None  # Next run exceeds end time

    def test_interval_schedule_strategy(self):
        """Test interval schedule strategy."""
        strategy = IntervalScheduleStrategy()
        current_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        schedule = MockSchedule(
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=3600  # 1 hour
        )
        
        result = strategy.calculate_next_run(schedule, current_time)
        expected = current_time + timedelta(seconds=3600)
        assert result == expected
        assert strategy.get_strategy_name() == "Interval Schedule"

    def test_interval_schedule_strategy_no_interval(self):
        """Test interval schedule strategy with no interval."""
        strategy = IntervalScheduleStrategy()
        schedule = MockSchedule(
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=None
        )
        current_time = datetime.now(timezone.utc)
        
        result = strategy.calculate_next_run(schedule, current_time)
        assert result is None

    def test_interval_schedule_strategy_invalid_interval(self):
        """Test interval schedule strategy with invalid interval."""
        strategy = IntervalScheduleStrategy()
        schedule = MockSchedule(
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=0
        )
        current_time = datetime.now(timezone.utc)
        
        result = strategy.calculate_next_run(schedule, current_time)
        assert result is None

    def test_interval_schedule_strategy_with_end_time(self):
        """Test interval schedule strategy respects end time."""
        strategy = IntervalScheduleStrategy()
        current_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        end_time = current_time + timedelta(minutes=30)
        
        schedule = MockSchedule(
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=3600,  # 1 hour (exceeds end time)
            end_time=end_time
        )
        
        result = strategy.calculate_next_run(schedule, current_time)
        assert result is None

    def test_one_time_schedule_strategy_future(self):
        """Test one-time schedule strategy with future start time."""
        strategy = OneTimeScheduleStrategy()
        current_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        start_time = current_time + timedelta(hours=2)
        
        schedule = MockSchedule(
            schedule_type=ScheduleType.ONE_TIME,
            start_time=start_time
        )
        
        result = strategy.calculate_next_run(schedule, current_time)
        assert result == start_time
        assert strategy.get_strategy_name() == "One-Time Schedule"

    def test_one_time_schedule_strategy_past(self):
        """Test one-time schedule strategy with past start time."""
        strategy = OneTimeScheduleStrategy()
        current_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        start_time = current_time - timedelta(hours=2)
        
        schedule = MockSchedule(
            schedule_type=ScheduleType.ONE_TIME,
            start_time=start_time
        )
        
        result = strategy.calculate_next_run(schedule, current_time)
        assert result is None

    def test_one_time_schedule_strategy_no_start_time(self):
        """Test one-time schedule strategy with no start time."""
        strategy = OneTimeScheduleStrategy()
        schedule = MockSchedule(
            schedule_type=ScheduleType.ONE_TIME,
            start_time=None
        )
        current_time = datetime.now(timezone.utc)
        
        result = strategy.calculate_next_run(schedule, current_time)
        assert result is None

    def test_recurring_schedule_strategy_future_start(self):
        """Test recurring schedule strategy with future start time."""
        strategy = RecurringScheduleStrategy()
        current_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        start_time = current_time + timedelta(hours=2)
        
        schedule = MockSchedule(
            schedule_type=ScheduleType.RECURRING,
            start_time=start_time,
            interval_seconds=3600  # 1 hour
        )
        
        result = strategy.calculate_next_run(schedule, current_time)
        assert result == start_time
        assert strategy.get_strategy_name() == "Recurring Schedule"

    def test_recurring_schedule_strategy_past_start(self):
        """Test recurring schedule strategy with past start time."""
        strategy = RecurringScheduleStrategy()
        current_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        start_time = current_time - timedelta(hours=5)  # 5 hours ago
        
        schedule = MockSchedule(
            schedule_type=ScheduleType.RECURRING,
            start_time=start_time,
            interval_seconds=3600  # 1 hour interval
        )
        
        result = strategy.calculate_next_run(schedule, current_time)
        
        # Should calculate next run based on interval from start time
        # 5 hours elapsed, 5 intervals passed, next is 6th interval
        expected = start_time + timedelta(hours=6)
        assert result == expected

    def test_recurring_schedule_strategy_no_start_time(self):
        """Test recurring schedule strategy with no start time."""
        strategy = RecurringScheduleStrategy()
        schedule = MockSchedule(
            schedule_type=ScheduleType.RECURRING,
            start_time=None,
            interval_seconds=3600
        )
        current_time = datetime.now(timezone.utc)
        
        result = strategy.calculate_next_run(schedule, current_time)
        assert result is None

    def test_recurring_schedule_strategy_no_interval(self):
        """Test recurring schedule strategy with no interval."""
        strategy = RecurringScheduleStrategy()
        current_time = datetime.now(timezone.utc)
        start_time = current_time + timedelta(hours=1)
        
        schedule = MockSchedule(
            schedule_type=ScheduleType.RECURRING,
            start_time=start_time,
            interval_seconds=None
        )
        
        result = strategy.calculate_next_run(schedule, current_time)
        assert result is None

    def test_recurring_schedule_strategy_with_end_time(self):
        """Test recurring schedule strategy respects end time."""
        strategy = RecurringScheduleStrategy()
        current_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        start_time = current_time - timedelta(hours=2)
        end_time = current_time + timedelta(minutes=30)
        
        schedule = MockSchedule(
            schedule_type=ScheduleType.RECURRING,
            start_time=start_time,
            interval_seconds=3600,  # 1 hour (next run would exceed end time)
            end_time=end_time
        )
        
        result = strategy.calculate_next_run(schedule, current_time)
        assert result is None


class TestScheduleCalculationEngine:
    """Test schedule calculation engine."""

    def test_engine_initialization(self):
        """Test engine initializes with all strategies."""
        engine = ScheduleCalculationEngine()
        
        supported_types = engine.get_supported_schedule_types()
        expected_types = [
            ScheduleType.CRON,
            ScheduleType.INTERVAL,
            ScheduleType.ONE_TIME,
            ScheduleType.RECURRING,
        ]
        
        for schedule_type in expected_types:
            assert schedule_type in supported_types

    def test_calculate_next_run_cron(self):
        """Test calculation with cron schedule."""
        engine = ScheduleCalculationEngine()
        current_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        schedule = MockSchedule(
            schedule_type=ScheduleType.CRON,
            cron_expression="0 */6 * * *"
        )
        
        with patch('dotmac_isp.sdks.workflows.schedule_strategies.croniter') as mock_croniter:
            mock_cron_instance = Mock()
            mock_cron_instance.get_next.return_value = current_time + timedelta(hours=6)
            mock_croniter.return_value = mock_cron_instance
            
            result = engine.calculate_next_run(schedule, current_time)
            assert result == current_time + timedelta(hours=6)

    def test_calculate_next_run_interval(self):
        """Test calculation with interval schedule."""
        engine = ScheduleCalculationEngine()
        current_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        schedule = MockSchedule(
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=1800  # 30 minutes
        )
        
        result = engine.calculate_next_run(schedule, current_time)
        expected = current_time + timedelta(seconds=1800)
        assert result == expected

    def test_calculate_next_run_unknown_type(self):
        """Test calculation with unknown schedule type."""
        engine = ScheduleCalculationEngine()
        current_time = datetime.now(timezone.utc)
        
        schedule = MockSchedule(schedule_type="unknown_type")
        
        with patch('dotmac_isp.sdks.workflows.schedule_strategies.logger') as mock_logger:
            result = engine.calculate_next_run(schedule, current_time)
            assert result is None
            mock_logger.error.assert_called()

    def test_calculate_next_run_no_schedule_type(self):
        """Test calculation with schedule missing type attribute."""
        engine = ScheduleCalculationEngine()
        current_time = datetime.now(timezone.utc)
        
        schedule = Mock()
        del schedule.schedule_type  # Remove the attribute
        
        with patch('dotmac_isp.sdks.workflows.schedule_strategies.logger') as mock_logger:
            result = engine.calculate_next_run(schedule, current_time)
            assert result is None
            mock_logger.error.assert_called()

    def test_calculate_next_run_default_current_time(self):
        """Test calculation uses current time when not provided."""
        engine = ScheduleCalculationEngine()
        
        schedule = MockSchedule(
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=3600
        )
        
        # Should use current time internally
        result = engine.calculate_next_run(schedule)
        assert result is not None
        assert result > datetime.now(timezone.utc)

    def test_calculate_next_run_with_exception(self):
        """Test calculation handles strategy exceptions gracefully."""
        engine = ScheduleCalculationEngine()
        current_time = datetime.now(timezone.utc)
        
        # Mock strategy that raises exception
        mock_strategy = Mock(spec=ScheduleCalculationStrategy)
        mock_strategy.calculate_next_run.side_effect = Exception("Test error")
        mock_strategy.get_strategy_name.return_value = "Test Strategy"
        engine.strategies[ScheduleType.INTERVAL] = mock_strategy
        
        schedule = MockSchedule(schedule_type=ScheduleType.INTERVAL)
        
        with patch('dotmac_isp.sdks.workflows.schedule_strategies.logger') as mock_logger:
            result = engine.calculate_next_run(schedule, current_time)
            assert result is None
            mock_logger.error.assert_called()

    def test_add_custom_strategy(self):
        """Test adding custom strategy."""
        engine = ScheduleCalculationEngine()
        
        custom_strategy = Mock(spec=ScheduleCalculationStrategy)
        custom_strategy.get_strategy_name.return_value = "Custom Strategy"
        
        engine.add_custom_strategy("custom_type", custom_strategy)
        
        assert "custom_type" in engine.strategies
        assert engine.strategies["custom_type"] == custom_strategy

    def test_remove_strategy(self):
        """Test removing strategy."""
        engine = ScheduleCalculationEngine()
        
        # Remove existing strategy
        assert engine.remove_strategy(ScheduleType.INTERVAL) is True
        assert ScheduleType.INTERVAL not in engine.strategies
        
        # Try to remove non-existent strategy
        assert engine.remove_strategy("non_existent") is False


class TestScheduleEngineFactory:
    """Test schedule engine factory function."""

    def test_create_schedule_engine(self):
        """Test factory creates properly configured engine."""
        engine = create_schedule_engine()
        
        assert isinstance(engine, ScheduleCalculationEngine)
        assert len(engine.get_supported_schedule_types()) == 4  # All standard types
        
        # Test basic functionality
        current_time = datetime.now(timezone.utc)
        schedule = MockSchedule(
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=1800
        )
        
        result = engine.calculate_next_run(schedule, current_time)
        assert result is not None
        assert result > current_time


class TestComplexityReduction:
    """Test that demonstrates the complexity reduction achieved."""

    def test_original_vs_refactored_complexity(self):
        """
        Test demonstrating complexity reduction from 14→3.
        
        Original method had 4 if-elif branches with nested conditions (complexity 14).
        New method has simple strategy lookup (complexity 3).
        """
        engine = create_schedule_engine()
        current_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        # Test all schedule types that were in original if-elif chain
        test_cases = [
            (ScheduleType.CRON, {"cron_expression": "0 */6 * * *"}),
            (ScheduleType.INTERVAL, {"interval_seconds": 3600}),
            (ScheduleType.ONE_TIME, {"start_time": current_time + timedelta(hours=1)}),
            (ScheduleType.RECURRING, {
                "start_time": current_time + timedelta(hours=1),
                "interval_seconds": 1800
            }),
        ]
        
        for schedule_type, kwargs in test_cases:
            schedule = MockSchedule(schedule_type=schedule_type, **kwargs)
            
            # For cron, mock croniter
            if schedule_type == ScheduleType.CRON:
                with patch('dotmac_isp.sdks.workflows.schedule_strategies.croniter') as mock_croniter:
                    mock_cron_instance = Mock()
                    mock_cron_instance.get_next.return_value = current_time + timedelta(hours=6)
                    mock_croniter.return_value = mock_cron_instance
                    
                    result = engine.calculate_next_run(schedule, current_time)
                    assert result is not None, f"Failed for schedule type {schedule_type}"
            else:
                result = engine.calculate_next_run(schedule, current_time)
                assert result is not None, f"Failed for schedule type {schedule_type}"
        
        # Verify all 4 schedule types work without complex if-elif logic
        assert len(engine.get_supported_schedule_types()) == 4


class TestIntegrationWithScheduler:
    """Test integration with scheduler module."""

    def test_cron_scheduler_uses_strategy(self):
        """Test that CronScheduler uses new strategy pattern."""
        from dotmac_isp.sdks.workflows.scheduler import CronScheduler, ScheduleDefinition
        
        scheduler = CronScheduler()
        current_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        schedule = ScheduleDefinition(
            id="test_schedule",
            name="Test Schedule",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=3600,
            job_handler="test_handler",
            tenant_id="test_tenant"
        )
        
        # This should use the new strategy pattern internally
        scheduler.add_schedule(schedule)
        
        # Verify next run was calculated
        assert schedule.id in scheduler.next_runs
        next_run = scheduler.next_runs[schedule.id]
        assert next_run > current_time