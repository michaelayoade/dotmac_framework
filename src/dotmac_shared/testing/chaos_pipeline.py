"""
Automated chaos testing pipeline for continuous resilience validation
"""
import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from ..utils.datetime_utils import utc_now
from .chaos_monitoring import ChaosMonitor
from .chaos_scenarios import DotMacChaosScenarios
from .resilience_validator import ResilienceLevel, ResilienceValidator

logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    """Chaos testing pipeline stages"""

    PREPARATION = "preparation"
    BASELINE = "baseline"
    CHAOS_INJECTION = "chaos_injection"
    MONITORING = "monitoring"
    VALIDATION = "validation"
    RECOVERY = "recovery"
    REPORTING = "reporting"
    CLEANUP = "cleanup"


class PipelineStatus(str, Enum):
    """Pipeline execution status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduleType(str, Enum):
    """Pipeline schedule types"""

    MANUAL = "manual"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CONTINUOUS = "continuous"


@dataclass
class PipelineConfig:
    """Configuration for chaos testing pipeline"""

    name: str
    description: str = ""
    resilience_level: ResilienceLevel = ResilienceLevel.BASIC
    schedule_type: ScheduleType = ScheduleType.MANUAL
    schedule_time: Optional[time] = None
    target_environment: str = "staging"
    notification_webhooks: list[str] = field(default_factory=list)
    max_concurrent_experiments: int = 3
    abort_on_critical_failure: bool = True
    retention_days: int = 30

    # Experiment selection
    include_scenarios: list[str] = field(default_factory=list)
    exclude_scenarios: list[str] = field(default_factory=list)
    tenant_filter: Optional[str] = None

    # Monitoring thresholds
    max_error_rate: float = 0.10
    max_response_time_p99: float = 5000
    min_availability: float = 0.95


@dataclass
class PipelineRun:
    """Individual pipeline run instance"""

    id: str
    config_name: str
    status: PipelineStatus = PipelineStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_stage: Optional[PipelineStage] = None
    experiments_completed: int = 0
    experiments_failed: int = 0
    total_experiments: int = 0
    metrics: dict[str, Any] = field(default_factory=dict)
    alerts: list[str] = field(default_factory=list)
    error_message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.start_time:
            data["start_time"] = self.start_time.isoformat()
        if self.end_time:
            data["end_time"] = self.end_time.isoformat()
        return data


class ChaosPipeline:
    """Main chaos testing pipeline orchestrator"""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.chaos_scenarios = DotMacChaosScenarios()
        self.resilience_validator = ResilienceValidator()
        self.chaos_monitor = ChaosMonitor()

        self.current_run: Optional[PipelineRun] = None
        self.run_history: list[PipelineRun] = []
        self.scheduled_tasks = {}
        self._running = False

    async def start_pipeline(self) -> str:
        """Start the chaos testing pipeline"""
        if self.current_run and self.current_run.status == PipelineStatus.RUNNING:
            raise RuntimeError("Pipeline is already running")

        run_id = f"chaos_run_{utc_now().strftime('%Y%m%d_%H%M%S')}"
        self.current_run = PipelineRun(id=run_id, config_name=self.config.name, start_time=utc_now())

        logger.info(f"Starting chaos pipeline: {run_id}")

        try:
            await self._execute_pipeline()
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            self.current_run.status = PipelineStatus.FAILED
            self.current_run.error_message = str(e)
        finally:
            self.current_run.end_time = utc_now()
            self.run_history.append(self.current_run)

            # Keep only recent runs
            if len(self.run_history) > 100:
                self.run_history = self.run_history[-100:]

        return run_id

    async def _execute_pipeline(self):
        """Execute the complete pipeline"""
        stages = [
            (PipelineStage.PREPARATION, self._stage_preparation),
            (PipelineStage.BASELINE, self._stage_baseline),
            (PipelineStage.CHAOS_INJECTION, self._stage_chaos_injection),
            (PipelineStage.MONITORING, self._stage_monitoring),
            (PipelineStage.VALIDATION, self._stage_validation),
            (PipelineStage.RECOVERY, self._stage_recovery),
            (PipelineStage.REPORTING, self._stage_reporting),
            (PipelineStage.CLEANUP, self._stage_cleanup),
        ]

        self.current_run.status = PipelineStatus.RUNNING
        self.current_run.total_experiments = await self._count_planned_experiments()

        for stage, stage_func in stages:
            self.current_run.current_stage = stage
            logger.info(f"Executing pipeline stage: {stage}")

            try:
                await stage_func()
            except Exception as e:
                logger.error(f"Stage {stage} failed: {e}")

                if self.config.abort_on_critical_failure:
                    raise
                else:
                    # Continue with next stage
                    continue

        self.current_run.status = PipelineStatus.COMPLETED
        logger.info(f"Pipeline completed: {self.current_run.id}")

    async def _stage_preparation(self):
        """Preparation stage - setup environment and verify prerequisites"""
        logger.info("Pipeline stage: Preparation")

        # Start monitoring system
        await self.chaos_monitor.start()

        # Verify system readiness
        health = self.chaos_monitor.get_system_health()
        if not health["monitoring_active"]:
            raise RuntimeError("Monitoring system failed to start")

        # Initialize experiment tracking
        self.current_run.metrics["preparation"] = {"monitoring_started": True, "system_health": health}

    async def _stage_baseline(self):
        """Baseline stage - collect baseline metrics"""
        logger.info("Pipeline stage: Baseline")

        # Collect baseline metrics for 30 seconds
        baseline_start = utc_now()

        # Record baseline metrics
        self.chaos_monitor.record_metric("pipeline_baseline_start", 1, experiment_id=self.current_run.id)

        await asyncio.sleep(30)

        baseline_end = utc_now()

        # Calculate baseline summary
        baseline_metrics = {}
        key_metrics = ["error_rate", "response_time_avg", "throughput", "availability"]

        for metric in key_metrics:
            summary = self.chaos_monitor.metrics_collector.get_metric_summary(metric, since=baseline_start)
            baseline_metrics[metric] = summary

        self.current_run.metrics["baseline"] = {
            "collection_start": baseline_start.isoformat(),
            "collection_end": baseline_end.isoformat(),
            "duration_seconds": (baseline_end - baseline_start).total_seconds(),
            "metrics": baseline_metrics,
        }

    async def _stage_chaos_injection(self):
        """Chaos injection stage - run planned experiments"""
        logger.info("Pipeline stage: Chaos Injection")

        experiments = await self._plan_experiments()
        experiment_results = []

        # Run experiments with concurrency limit
        semaphore = asyncio.Semaphore(self.config.max_concurrent_experiments)

        async def run_experiment(scenario_name: str) -> dict[str, Any]:
            async with semaphore:
                try:
                    result = await self._run_scenario(scenario_name)
                    self.current_run.experiments_completed += 1
                    return {"scenario": scenario_name, "status": "success", "result": result}
                except Exception as e:
                    self.current_run.experiments_failed += 1
                    logger.error(f"Experiment {scenario_name} failed: {e}")
                    return {"scenario": scenario_name, "status": "failed", "error": str(e)}

        tasks = [run_experiment(scenario) for scenario in experiments]
        experiment_results = await asyncio.gather(*tasks, return_exceptions=True)

        self.current_run.metrics["chaos_injection"] = {
            "planned_experiments": len(experiments),
            "completed": self.current_run.experiments_completed,
            "failed": self.current_run.experiments_failed,
            "results": experiment_results,
        }

    async def _stage_monitoring(self):
        """Monitoring stage - analyze experiment impact"""
        logger.info("Pipeline stage: Monitoring")

        # Monitor for 60 seconds after chaos injection
        monitoring_start = utc_now()

        # Check for critical alerts
        alerts = self.chaos_monitor.alert_manager.get_active_alerts()
        critical_alerts = [a for a in alerts if a.severity.value in ["critical", "fatal"]]

        if critical_alerts and self.config.abort_on_critical_failure:
            raise RuntimeError(f"Critical alerts detected: {len(critical_alerts)}")

        await asyncio.sleep(60)

        monitoring_end = utc_now()

        # Collect post-chaos metrics
        post_chaos_metrics = {}
        key_metrics = ["error_rate", "response_time_avg", "throughput", "availability"]

        for metric in key_metrics:
            summary = self.chaos_monitor.metrics_collector.get_metric_summary(metric, since=monitoring_start)
            post_chaos_metrics[metric] = summary

        self.current_run.metrics["monitoring"] = {
            "monitoring_start": monitoring_start.isoformat(),
            "monitoring_end": monitoring_end.isoformat(),
            "critical_alerts": len(critical_alerts),
            "total_alerts": len(alerts),
            "post_chaos_metrics": post_chaos_metrics,
        }

    async def _stage_validation(self):
        """Validation stage - run resilience validation tests"""
        logger.info("Pipeline stage: Validation")

        # Run resilience validation
        validation_results = await self.resilience_validator.validate_resilience(level=self.config.resilience_level)

        # Generate validation report
        report = self.resilience_validator.generate_resilience_report(validation_results)

        self.current_run.metrics["validation"] = {
            "validation_results": [r.__dict__ for r in validation_results],
            "report": report,
        }

        # Check if validation passed
        failed_validations = [r for r in validation_results if r.result.value == "failed"]
        if failed_validations and self.config.abort_on_critical_failure:
            raise RuntimeError(f"Validation failed: {len(failed_validations)} tests failed")

    async def _stage_recovery(self):
        """Recovery stage - verify system recovery"""
        logger.info("Pipeline stage: Recovery")

        recovery_start = utc_now()

        # Wait for system to recover
        max_recovery_time = 300  # 5 minutes
        recovery_checks = 0

        while recovery_checks < max_recovery_time / 10:
            await asyncio.sleep(10)
            recovery_checks += 1

            # Check if system has recovered
            current_error_rate = self.chaos_monitor.metrics_collector.get_current_value("error_rate")
            current_availability = self.chaos_monitor.metrics_collector.get_current_value("availability")

            if (
                current_error_rate is not None
                and current_error_rate <= self.config.max_error_rate
                and current_availability is not None
                and current_availability >= self.config.min_availability
            ):
                break

        recovery_end = utc_now()
        recovery_time = (recovery_end - recovery_start).total_seconds()

        self.current_run.metrics["recovery"] = {
            "recovery_start": recovery_start.isoformat(),
            "recovery_end": recovery_end.isoformat(),
            "recovery_time_seconds": recovery_time,
            "recovery_successful": recovery_time < max_recovery_time,
        }

    async def _stage_reporting(self):
        """Reporting stage - generate and send reports"""
        logger.info("Pipeline stage: Reporting")

        # Generate comprehensive report
        report = await self._generate_pipeline_report()

        # Save report
        await self._save_report(report)

        # Send notifications
        await self._send_notifications(report)

        self.current_run.metrics["reporting"] = {
            "report_generated": True,
            "notifications_sent": len(self.config.notification_webhooks),
        }

    async def _stage_cleanup(self):
        """Cleanup stage - clean up resources"""
        logger.info("Pipeline stage: Cleanup")

        # Stop monitoring
        await self.chaos_monitor.stop()

        # Clean up old reports
        await self._cleanup_old_reports()

        self.current_run.metrics["cleanup"] = {"monitoring_stopped": True, "cleanup_completed": True}

    async def _count_planned_experiments(self) -> int:
        """Count total planned experiments"""
        experiments = await self._plan_experiments()
        return len(experiments)

    async def _plan_experiments(self) -> list[str]:
        """Plan which experiments to run"""
        all_scenarios = [
            "tenant_isolation_scenario",
            "isp_service_disruption_scenario",
            "billing_resilience_scenario",
            "multi_tenant_database_partition_scenario",
        ]

        # Apply include/exclude filters
        scenarios = all_scenarios

        if self.config.include_scenarios:
            scenarios = [s for s in scenarios if s in self.config.include_scenarios]

        if self.config.exclude_scenarios:
            scenarios = [s for s in scenarios if s not in self.config.exclude_scenarios]

        return scenarios

    async def _run_scenario(self, scenario_name: str) -> dict[str, Any]:
        """Run a specific chaos scenario"""
        logger.info(f"Running chaos scenario: {scenario_name}")

        if scenario_name == "tenant_isolation_scenario":
            tenant_id = self.config.tenant_filter or "test-tenant"
            return await self.chaos_scenarios.run_tenant_isolation_scenario(tenant_id)

        elif scenario_name == "isp_service_disruption_scenario":
            results = await self.chaos_scenarios.run_isp_service_disruption_scenario()
            return {"experiments": [r.to_dict() if hasattr(r, "to_dict") else str(r) for r in results]}

        elif scenario_name == "billing_resilience_scenario":
            results = await self.chaos_scenarios.run_billing_resilience_scenario()
            return {"experiments": [r.to_dict() if hasattr(r, "to_dict") else str(r) for r in results]}

        elif scenario_name == "multi_tenant_database_partition_scenario":
            tenant_ids = [self.config.tenant_filter] if self.config.tenant_filter else ["tenant-1", "tenant-2"]
            result = await self.chaos_scenarios.run_multi_tenant_database_partition_scenario(tenant_ids)
            return result.to_dict() if hasattr(result, "to_dict") else str(result)

        else:
            raise ValueError(f"Unknown scenario: {scenario_name}")

    async def _generate_pipeline_report(self) -> dict[str, Any]:
        """Generate comprehensive pipeline report"""
        if not self.current_run:
            raise RuntimeError("No current run to report on")

        duration = 0
        if self.current_run.start_time and self.current_run.end_time:
            duration = (self.current_run.end_time - self.current_run.start_time).total_seconds()

        return {
            "pipeline_run": self.current_run.to_dict(),
            "config": asdict(self.config),
            "summary": {
                "total_duration_seconds": duration,
                "experiments_planned": self.current_run.total_experiments,
                "experiments_completed": self.current_run.experiments_completed,
                "experiments_failed": self.current_run.experiments_failed,
                "success_rate": (self.current_run.experiments_completed / max(1, self.current_run.total_experiments))
                * 100,
            },
            "system_health": self.chaos_monitor.get_system_health(),
            "generated_at": utc_now().isoformat(),
        }

    async def _save_report(self, report: dict[str, Any]):
        """Save report to disk"""
        reports_dir = Path(".dev-artifacts/chaos-reports")
        reports_dir.mkdir(parents=True, exist_ok=True)

        report_file = reports_dir / f"chaos_report_{self.current_run.id}.json"

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Report saved: {report_file}")

    async def _send_notifications(self, report: dict[str, Any]):
        """Send notifications about pipeline results"""
        if not self.config.notification_webhooks:
            return

        # Create notification payload
        {
            "pipeline_run_id": self.current_run.id,
            "status": self.current_run.status.value,
            "summary": report["summary"],
            "timestamp": utc_now().isoformat(),
        }

        # In real implementation, this would send HTTP requests to webhooks
        logger.info(f"Would send notifications to {len(self.config.notification_webhooks)} webhooks")

    async def _cleanup_old_reports(self):
        """Clean up old report files"""
        reports_dir = Path(".dev-artifacts/chaos-reports")
        if not reports_dir.exists():
            return

        cutoff_date = utc_now() - timedelta(days=self.config.retention_days)

        for report_file in reports_dir.glob("chaos_report_*.json"):
            if report_file.stat().st_mtime < cutoff_date.timestamp():
                report_file.unlink()
                logger.info(f"Cleaned up old report: {report_file}")


class ChaosPipelineScheduler:
    """Scheduler for automated chaos testing pipelines"""

    def __init__(self):
        self.pipelines: dict[str, ChaosPipeline] = {}
        self.scheduled_tasks: dict[str, asyncio.Task] = {}
        self._running = False

    def register_pipeline(self, config: PipelineConfig) -> ChaosPipeline:
        """Register a new pipeline configuration"""
        pipeline = ChaosPipeline(config)
        self.pipelines[config.name] = pipeline
        logger.info(f"Registered pipeline: {config.name}")
        return pipeline

    async def start_scheduler(self):
        """Start the pipeline scheduler"""
        if self._running:
            return

        self._running = True
        logger.info("Starting chaos pipeline scheduler")

        # Start scheduled pipelines
        for name, pipeline in self.pipelines.items():
            if pipeline.config.schedule_type != ScheduleType.MANUAL:
                task = asyncio.create_task(self._schedule_pipeline(name))
                self.scheduled_tasks[name] = task

    async def stop_scheduler(self):
        """Stop the pipeline scheduler"""
        if not self._running:
            return

        self._running = False
        logger.info("Stopping chaos pipeline scheduler")

        # Cancel scheduled tasks
        for task in self.scheduled_tasks.values():
            task.cancel()

        await asyncio.gather(*self.scheduled_tasks.values(), return_exceptions=True)
        self.scheduled_tasks.clear()

    async def _schedule_pipeline(self, pipeline_name: str):
        """Schedule a pipeline based on its configuration"""
        pipeline = self.pipelines[pipeline_name]
        config = pipeline.config

        while self._running:
            try:
                next_run = self._calculate_next_run_time(config)

                if next_run:
                    wait_time = (next_run - utc_now()).total_seconds()
                    if wait_time > 0:
                        await asyncio.sleep(wait_time)

                if self._running:
                    logger.info(f"Starting scheduled pipeline: {pipeline_name}")
                    await pipeline.start_pipeline()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduled pipeline {pipeline_name}: {e}")
                # Wait before retrying
                await asyncio.sleep(300)  # 5 minutes

    def _calculate_next_run_time(self, config: PipelineConfig) -> Optional[datetime]:
        """Calculate next run time based on schedule configuration"""
        now = utc_now()

        if config.schedule_type == ScheduleType.DAILY:
            next_run = now.replace(
                hour=config.schedule_time.hour if config.schedule_time else 2,
                minute=config.schedule_time.minute if config.schedule_time else 0,
                second=0,
                microsecond=0,
            )
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run

        elif config.schedule_type == ScheduleType.WEEKLY:
            # Run on Sunday by default
            days_ahead = 6 - now.weekday()  # Sunday is 6
            if days_ahead <= 0:
                days_ahead += 7

            next_run = now.replace(
                hour=config.schedule_time.hour if config.schedule_time else 2,
                minute=config.schedule_time.minute if config.schedule_time else 0,
                second=0,
                microsecond=0,
            )
            next_run += timedelta(days=days_ahead)
            return next_run

        elif config.schedule_type == ScheduleType.MONTHLY:
            # Run on first day of next month
            if now.month == 12:
                next_run = now.replace(year=now.year + 1, month=1, day=1)
            else:
                next_run = now.replace(month=now.month + 1, day=1)

            next_run = next_run.replace(
                hour=config.schedule_time.hour if config.schedule_time else 2,
                minute=config.schedule_time.minute if config.schedule_time else 0,
                second=0,
                microsecond=0,
            )
            return next_run

        elif config.schedule_type == ScheduleType.CONTINUOUS:
            # Run every hour
            return now + timedelta(hours=1)

        return None  # Manual scheduling

    async def trigger_pipeline(self, pipeline_name: str) -> str:
        """Manually trigger a pipeline"""
        if pipeline_name not in self.pipelines:
            raise ValueError(f"Unknown pipeline: {pipeline_name}")

        pipeline = self.pipelines[pipeline_name]
        return await pipeline.start_pipeline()

    def get_pipeline_status(self, pipeline_name: str) -> Optional[dict[str, Any]]:
        """Get status of a pipeline"""
        if pipeline_name not in self.pipelines:
            return None

        pipeline = self.pipelines[pipeline_name]

        return {
            "name": pipeline_name,
            "config": asdict(pipeline.config),
            "current_run": pipeline.current_run.to_dict() if pipeline.current_run else None,
            "recent_runs": [run.to_dict() for run in pipeline.run_history[-5:]],
            "is_scheduled": pipeline_name in self.scheduled_tasks,
        }
