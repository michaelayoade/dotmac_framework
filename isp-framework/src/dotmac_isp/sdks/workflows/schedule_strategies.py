"""
Schedule calculation strategies for enhanced scheduler.

REFACTORED: Extracted from scheduler.py to reduce CronScheduler._calculate_next_run 
complexity from 14→3 using Strategy pattern.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

try:
    from croniter import croniter
    CRONITER_AVAILABLE = True
except ImportError:
    CRONITER_AVAILABLE = False


class ScheduleCalculationStrategy(ABC):
    """Base strategy for schedule calculation."""
    
    @abstractmethod
    def calculate_next_run(self, schedule, current_time: datetime) -> Optional[datetime]:
        """Calculate next run time for the schedule."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get strategy name for logging."""
        pass


class CronScheduleStrategy(ScheduleCalculationStrategy):
    """Strategy for cron-based schedule calculation."""
    
    def calculate_next_run(self, schedule, current_time: datetime) -> Optional[datetime]:
        """Calculate next run using cron expression."""
        if not CRONITER_AVAILABLE:
            logger.error("croniter not available for cron schedule calculation")
            return None
            
        if not schedule.cron_expression:
            logger.warning("No cron expression provided for cron schedule",
                         schedule_id=getattr(schedule, 'id', 'unknown'))
            return None
        
        try:
            cron = croniter(schedule.cron_expression, current_time)
            next_run = cron.get_next(datetime)
            
            # Check end time constraint
            if schedule.end_time and next_run > schedule.end_time:
                logger.info("Next cron run exceeds end time",
                           schedule_id=getattr(schedule, 'id', 'unknown'),
                           next_run=next_run,
                           end_time=schedule.end_time)
                return None
                
            return next_run
        except Exception as e:
            logger.error("Error calculating cron next run",
                        schedule_id=getattr(schedule, 'id', 'unknown'),
                        cron_expression=schedule.cron_expression,
                        error=str(e))
            return None
    
    def get_strategy_name(self) -> str:
        return "Cron Schedule"


class IntervalScheduleStrategy(ScheduleCalculationStrategy):
    """Strategy for interval-based schedule calculation."""
    
    def calculate_next_run(self, schedule, current_time: datetime) -> Optional[datetime]:
        """Calculate next run using interval seconds."""
        if not schedule.interval_seconds:
            logger.warning("No interval seconds provided for interval schedule",
                         schedule_id=getattr(schedule, 'id', 'unknown'))
            return None
        
        if schedule.interval_seconds <= 0:
            logger.warning("Invalid interval seconds for interval schedule",
                         schedule_id=getattr(schedule, 'id', 'unknown'),
                         interval=schedule.interval_seconds)
            return None
        
        # Calculate next run from current time
        next_run = current_time + timedelta(seconds=schedule.interval_seconds)
        
        # Check end time constraint
        if schedule.end_time and next_run > schedule.end_time:
            logger.info("Next interval run exceeds end time",
                       schedule_id=getattr(schedule, 'id', 'unknown'),
                       next_run=next_run,
                       end_time=schedule.end_time)
            return None
            
        return next_run
    
    def get_strategy_name(self) -> str:
        return "Interval Schedule"


class OneTimeScheduleStrategy(ScheduleCalculationStrategy):
    """Strategy for one-time schedule calculation."""
    
    def calculate_next_run(self, schedule, current_time: datetime) -> Optional[datetime]:
        """Calculate next run for one-time schedule."""
        if not schedule.start_time:
            logger.warning("No start time provided for one-time schedule",
                         schedule_id=getattr(schedule, 'id', 'unknown'))
            return None
        
        # One-time schedules only run if start time is in the future
        if schedule.start_time > current_time:
            return schedule.start_time
        else:
            # One-time job in the past, should not run again
            logger.debug("One-time schedule start time has passed",
                        schedule_id=getattr(schedule, 'id', 'unknown'),
                        start_time=schedule.start_time,
                        current_time=current_time)
            return None
    
    def get_strategy_name(self) -> str:
        return "One-Time Schedule"


class RecurringScheduleStrategy(ScheduleCalculationStrategy):
    """Strategy for recurring schedule calculation."""
    
    def calculate_next_run(self, schedule, current_time: datetime) -> Optional[datetime]:
        """Calculate next run for recurring schedule."""
        if not schedule.start_time:
            logger.warning("No start time provided for recurring schedule",
                         schedule_id=getattr(schedule, 'id', 'unknown'))
            return None
            
        if not schedule.interval_seconds:
            logger.warning("No interval seconds provided for recurring schedule",
                         schedule_id=getattr(schedule, 'id', 'unknown'))
            return None
        
        if schedule.interval_seconds <= 0:
            logger.warning("Invalid interval seconds for recurring schedule",
                         schedule_id=getattr(schedule, 'id', 'unknown'),
                         interval=schedule.interval_seconds)
            return None
        
        # If start time is in the future, use that
        if schedule.start_time > current_time:
            return schedule.start_time
        
        # Calculate next occurrence based on interval from start time
        elapsed_seconds = (current_time - schedule.start_time).total_seconds()
        intervals_passed = int(elapsed_seconds // schedule.interval_seconds)
        next_run = schedule.start_time + timedelta(
            seconds=(intervals_passed + 1) * schedule.interval_seconds
        )
        
        # Check end time constraint
        if schedule.end_time and next_run > schedule.end_time:
            logger.info("Next recurring run exceeds end time",
                       schedule_id=getattr(schedule, 'id', 'unknown'),
                       next_run=next_run,
                       end_time=schedule.end_time)
            return None
            
        return next_run
    
    def get_strategy_name(self) -> str:
        return "Recurring Schedule"


class ScheduleCalculationEngine:
    """
    Engine for calculating schedule run times using Strategy pattern.
    
    REFACTORED: Replaces the 14-complexity if-elif chain in CronScheduler._calculate_next_run
    with a simple strategy lookup (Complexity: 3).
    """
    
    def __init__(self):
        """Initialize with all available schedule calculation strategies."""
        from .scheduler import ScheduleType
        
        self.strategies = {
            ScheduleType.CRON: CronScheduleStrategy(),
            ScheduleType.INTERVAL: IntervalScheduleStrategy(),
            ScheduleType.ONE_TIME: OneTimeScheduleStrategy(),
            ScheduleType.RECURRING: RecurringScheduleStrategy(),
        }
    
    def calculate_next_run(self, schedule, current_time: datetime = None) -> Optional[datetime]:
        """
        Calculate next run time using appropriate strategy.
        
        COMPLEXITY REDUCTION: This method replaces the original 14-complexity 
        if-elif chain with simple strategy lookup (Complexity: 3).
        
        Args:
            schedule: Schedule definition with type and timing configuration
            current_time: Current time for calculation (defaults to UTC now)
            
        Returns:
            Next run datetime or None if schedule should not run again
        """
        # Step 1: Get current time and validate schedule (Complexity: 1)
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        if not hasattr(schedule, 'schedule_type'):
            logger.error("Schedule missing schedule_type attribute")
            return None
        
        # Step 2: Get strategy for schedule type (Complexity: 1)
        strategy = self.strategies.get(schedule.schedule_type)
        if not strategy:
            logger.error("Unknown schedule type",
                        schedule_type=schedule.schedule_type,
                        schedule_id=getattr(schedule, 'id', 'unknown'))
            return None
        
        # Step 3: Calculate using strategy (Complexity: 1)
        try:
            next_run = strategy.calculate_next_run(schedule, current_time)
            
            if next_run:
                logger.debug("Schedule next run calculated",
                           schedule_id=getattr(schedule, 'id', 'unknown'),
                           schedule_type=schedule.schedule_type,
                           strategy=strategy.get_strategy_name(),
                           next_run=next_run)
            
            return next_run
        except Exception as e:
            logger.error("Schedule calculation failed",
                        schedule_id=getattr(schedule, 'id', 'unknown'),
                        schedule_type=schedule.schedule_type,
                        strategy=strategy.get_strategy_name(),
                        error=str(e))
            return None
    
    def get_supported_schedule_types(self) -> list:
        """Get list of supported schedule types."""
        return list(self.strategies.keys())
    
    def add_custom_strategy(self, schedule_type: str, strategy: ScheduleCalculationStrategy) -> None:
        """Add a custom schedule calculation strategy."""
        self.strategies[schedule_type] = strategy
        logger.info("Added custom schedule strategy",
                   schedule_type=schedule_type,
                   strategy_name=strategy.get_strategy_name())
    
    def remove_strategy(self, schedule_type: str) -> bool:
        """Remove a schedule calculation strategy."""
        if schedule_type in self.strategies:
            del self.strategies[schedule_type]
            logger.info("Removed schedule strategy", schedule_type=schedule_type)
            return True
        return False


def create_schedule_engine() -> ScheduleCalculationEngine:
    """
    Factory function to create a configured schedule calculation engine.
    
    This is the main entry point for replacing the 14-complexity schedule calculation.
    
    Returns:
        Configured schedule calculation engine
    """
    return ScheduleCalculationEngine()