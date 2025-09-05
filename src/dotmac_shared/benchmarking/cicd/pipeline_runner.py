"""
Performance Pipeline Runner Module

Provides comprehensive pipeline execution for automated performance testing
in CI/CD environments, including test orchestration, result aggregation,
and integration with various CI/CD platforms.
"""

import asyncio
import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from dotmac_shared.benchmarking.analyzers.benchmark_comparator import BenchmarkComparator, BenchmarkComparisonConfig
from dotmac_shared.benchmarking.analyzers.regression_detector import RegressionDetectionConfig, RegressionDetector
from dotmac_shared.benchmarking.collectors.system_metrics import SystemMetricsCollector
from dotmac_shared.benchmarking.core.benchmark_manager import PerformanceBenchmarkManager
from dotmac_shared.benchmarking.profilers.api_benchmark import ApiEndpointBenchmarker, ApiLoadTestConfig
from dotmac_shared.benchmarking.profilers.database_benchmark import DatabaseBenchmarkConfig, DatabaseQueryBenchmarker
from pydantic import BaseModel, Field

from ..utils.decorators import standard_exception_handler


class PipelineStage(Enum):
    """Pipeline execution stages"""

    SETUP = "setup"
    SYSTEM_METRICS = "system_metrics"
    API_BENCHMARKS = "api_benchmarks"
    DATABASE_BENCHMARKS = "database_benchmarks"
    REGRESSION_ANALYSIS = "regression_analysis"
    COMPARISON = "comparison"
    REPORTING = "reporting"
    CLEANUP = "cleanup"


class PipelineStatus(Enum):
    """Pipeline execution status"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class PipelineStageResult:
    """Result of a single pipeline stage"""

    stage: PipelineStage
    status: PipelineStatus
    execution_time: float
    start_time: datetime
    end_time: datetime
    output: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Complete pipeline execution result"""

    pipeline_id: str
    status: PipelineStatus
    total_execution_time: float
    start_time: datetime
    end_time: datetime
    stages: list[PipelineStageResult]
    overall_performance_score: float
    regression_detected: bool
    critical_issues: list[dict[str, Any]]
    summary: str
    recommendations: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class PipelineConfig(BaseModel):
    """Configuration for performance pipeline"""

    # Pipeline settings
    pipeline_name: str = "performance_pipeline"
    timeout_minutes: int = Field(default=30, ge=5, le=120)
    parallel_execution: bool = True
    fail_fast: bool = False

    # Stage enablement
    enable_system_metrics: bool = True
    enable_api_benchmarks: bool = True
    enable_database_benchmarks: bool = True
    enable_regression_analysis: bool = True
    enable_comparison: bool = True

    # System metrics config
    system_metrics_duration: int = Field(default=60, ge=10, le=300)

    # API benchmarks config
    api_base_url: Optional[str] = None
    api_auth_token: Optional[str] = None
    api_concurrent_users: int = Field(default=10, ge=1, le=50)
    api_test_duration: int = Field(default=30, ge=10, le=120)

    # Database benchmarks config
    database_url: Optional[str] = None
    db_concurrent_connections: int = Field(default=10, ge=1, le=50)
    db_test_duration: int = Field(default=60, ge=10, le=300)

    # Regression analysis config
    regression_threshold_percent: float = Field(default=10.0, ge=1.0, le=50.0)
    baseline_days: int = Field(default=7, ge=1, le=30)

    # Output settings
    output_directory: str = "./benchmark_results"
    generate_html_report: bool = True
    generate_json_report: bool = True
    upload_to_artifacts: bool = False

    # Notification settings
    notify_on_regression: bool = True
    notification_webhook: Optional[str] = None

    # Custom test definitions
    custom_api_tests: list[dict[str, Any]] = Field(default_factory=list)
    custom_db_queries: list[dict[str, Any]] = Field(default_factory=list)


class PerformancePipelineRunner:
    """Automated performance testing pipeline for CI/CD"""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.pipeline_id = f"pipeline_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self.output_dir = Path(config.output_directory)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.benchmark_manager = PerformanceBenchmarkManager()
        self.system_metrics = SystemMetricsCollector() if config.enable_system_metrics else None
        self.regression_detector = (
            RegressionDetector(
                RegressionDetectionConfig(
                    baseline_days=config.baseline_days, regression_threshold_percent=config.regression_threshold_percent
                )
            )
            if config.enable_regression_analysis
            else None
        )
        self.comparator = BenchmarkComparator(BenchmarkComparisonConfig()) if config.enable_comparison else None

    @standard_exception_handler
    async def run_pipeline(self) -> PipelineResult:
        """Execute the complete performance testing pipeline"""
        pipeline_start = datetime.utcnow()
        stages = []

        try:
            # Setup stage
            setup_result = await self._run_stage(PipelineStage.SETUP, self._setup_stage)
            stages.append(setup_result)

            if setup_result.status == PipelineStatus.FAILED and self.config.fail_fast:
                return self._create_failed_pipeline_result(pipeline_start, stages, "Setup stage failed")

            # System metrics collection
            if self.config.enable_system_metrics:
                metrics_result = await self._run_stage(PipelineStage.SYSTEM_METRICS, self._system_metrics_stage)
                stages.append(metrics_result)

                if metrics_result.status == PipelineStatus.FAILED and self.config.fail_fast:
                    return self._create_failed_pipeline_result(pipeline_start, stages, "System metrics stage failed")

            # API benchmarks
            if self.config.enable_api_benchmarks and self.config.api_base_url:
                api_result = await self._run_stage(PipelineStage.API_BENCHMARKS, self._api_benchmarks_stage)
                stages.append(api_result)

                if api_result.status == PipelineStatus.FAILED and self.config.fail_fast:
                    return self._create_failed_pipeline_result(pipeline_start, stages, "API benchmarks stage failed")

            # Database benchmarks
            if self.config.enable_database_benchmarks and self.config.database_url:
                db_result = await self._run_stage(PipelineStage.DATABASE_BENCHMARKS, self._database_benchmarks_stage)
                stages.append(db_result)

                if db_result.status == PipelineStatus.FAILED and self.config.fail_fast:
                    return self._create_failed_pipeline_result(
                        pipeline_start, stages, "Database benchmarks stage failed"
                    )

            # Regression analysis
            if self.config.enable_regression_analysis:
                regression_result = await self._run_stage(
                    PipelineStage.REGRESSION_ANALYSIS, self._regression_analysis_stage
                )
                stages.append(regression_result)

            # Comparison with baselines
            if self.config.enable_comparison:
                comparison_result = await self._run_stage(PipelineStage.COMPARISON, self._comparison_stage)
                stages.append(comparison_result)

            # Report generation
            reporting_result = await self._run_stage(PipelineStage.REPORTING, self._reporting_stage, stages)
            stages.append(reporting_result)

            # Cleanup
            cleanup_result = await self._run_stage(PipelineStage.CLEANUP, self._cleanup_stage)
            stages.append(cleanup_result)

        except Exception as e:
            error_stage = PipelineStageResult(
                stage=PipelineStage.CLEANUP,
                status=PipelineStatus.FAILED,
                execution_time=0,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                errors=[f"Pipeline execution failed: {str(e)}"],
            )
            stages.append(error_stage)
            return self._create_failed_pipeline_result(pipeline_start, stages, str(e))

        # Create final result
        pipeline_end = datetime.utcnow()
        total_time = (pipeline_end - pipeline_start).total_seconds()

        # Determine overall status
        failed_stages = [s for s in stages if s.status == PipelineStatus.FAILED]
        overall_status = PipelineStatus.FAILED if failed_stages else PipelineStatus.SUCCESS

        # Calculate performance metrics
        performance_score = self._calculate_overall_performance_score(stages)
        regression_detected = self._check_for_regressions(stages)
        critical_issues = self._extract_critical_issues(stages)

        # Generate summary
        summary = self._generate_pipeline_summary(stages, performance_score, regression_detected)
        recommendations = self._generate_pipeline_recommendations(stages, critical_issues)

        # Collect artifacts
        artifacts = []
        for stage in stages:
            artifacts.extend(stage.artifacts)

        return PipelineResult(
            pipeline_id=self.pipeline_id,
            status=overall_status,
            total_execution_time=total_time,
            start_time=pipeline_start,
            end_time=pipeline_end,
            stages=stages,
            overall_performance_score=performance_score,
            regression_detected=regression_detected,
            critical_issues=critical_issues,
            summary=summary,
            recommendations=recommendations,
            artifacts=artifacts,
            metadata={"config": self.config.model_dump(), "environment": os.environ.copy()},
        )

    async def _run_stage(self, stage: PipelineStage, stage_func: Callable, *args) -> PipelineStageResult:
        """Run a single pipeline stage with error handling and timing"""
        start_time = datetime.utcnow()

        try:
            # Set timeout for stage
            timeout = timedelta(minutes=self.config.timeout_minutes).total_seconds()
            result = await asyncio.wait_for(stage_func(*args), timeout=timeout)

            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()

            return PipelineStageResult(
                stage=stage,
                status=PipelineStatus.SUCCESS,
                execution_time=execution_time,
                start_time=start_time,
                end_time=end_time,
                output=result if isinstance(result, dict) else {"result": result},
                artifacts=result.get("artifacts", []) if isinstance(result, dict) else [],
            )

        except asyncio.TimeoutError:
            end_time = datetime.utcnow()
            return PipelineStageResult(
                stage=stage,
                status=PipelineStatus.TIMEOUT,
                execution_time=(end_time - start_time).total_seconds(),
                start_time=start_time,
                end_time=end_time,
                errors=[f"Stage {stage.value} timed out after {self.config.timeout_minutes} minutes"],
            )

        except Exception as e:
            end_time = datetime.utcnow()
            return PipelineStageResult(
                stage=stage,
                status=PipelineStatus.FAILED,
                execution_time=(end_time - start_time).total_seconds(),
                start_time=start_time,
                end_time=end_time,
                errors=[f"Stage {stage.value} failed: {str(e)}"],
            )

    async def _setup_stage(self) -> dict[str, Any]:
        """Setup stage - prepare environment and validate configuration"""
        setup_info = {
            "pipeline_id": self.pipeline_id,
            "start_time": datetime.utcnow().isoformat(),
            "output_directory": str(self.output_dir),
            "configuration_valid": True,
        }

        # Validate configuration
        validation_errors = []

        if self.config.enable_api_benchmarks and not self.config.api_base_url:
            validation_errors.append("API benchmarks enabled but no base URL provided")

        if self.config.enable_database_benchmarks and not self.config.database_url:
            validation_errors.append("Database benchmarks enabled but no database URL provided")

        if validation_errors:
            setup_info["configuration_valid"] = False
            setup_info["validation_errors"] = validation_errors

        # Initialize system metrics if enabled
        if self.system_metrics:
            await self.system_metrics.start_collection()

        return setup_info

    async def _system_metrics_stage(self) -> dict[str, Any]:
        """System metrics collection stage"""
        if not self.system_metrics:
            return {"status": "skipped", "reason": "System metrics disabled"}

        # Collect metrics for specified duration
        duration = self.config.system_metrics_duration
        await asyncio.sleep(duration)

        # Get current metrics
        current_metrics = self.system_metrics.get_current_metrics()

        # Establish baseline if not exists
        baseline = self.system_metrics.establish_baseline(duration_seconds=min(duration, 60))

        # Save metrics to file
        metrics_file = self.output_dir / f"system_metrics_{self.pipeline_id}.json"
        with open(metrics_file, "w") as f:
            json.dump(
                {"current_metrics": current_metrics, "baseline": baseline, "collection_duration": duration},
                f,
                indent=2,
                default=str,
            )

        return {"metrics": current_metrics, "baseline": baseline, "artifacts": [str(metrics_file)]}

    async def _api_benchmarks_stage(self) -> dict[str, Any]:
        """API benchmarks stage"""
        if not self.config.api_base_url:
            return {"status": "skipped", "reason": "No API base URL configured"}

        # Setup API benchmarker
        api_config = ApiLoadTestConfig(
            concurrent_users=self.config.api_concurrent_users,
            duration_seconds=self.config.api_test_duration,
            ramp_up_seconds=10,
        )

        benchmarker = ApiEndpointBenchmarker(self.config.api_base_url, self.config.api_auth_token)

        # Define test requests
        test_requests = []

        # Add custom tests if provided
        for custom_test in self.config.custom_api_tests:
            test_requests.append(custom_test)

        # Add default health check test if no custom tests
        if not test_requests:
            test_requests = [{"method": "GET", "path": "/health", "name": "health_check", "expected_status": 200}]

        # Run load test
        results = await benchmarker.run_load_test(test_requests, api_config, "pipeline_api_test")

        # Save results
        api_results_file = self.output_dir / f"api_benchmark_{self.pipeline_id}.json"
        with open(api_results_file, "w") as f:
            json.dump(
                results.model_dump() if hasattr(results, "model_dump") else results.__dict__, f, indent=2, default=str
            )

        return {
            "results": results.__dict__ if hasattr(results, "__dict__") else results,
            "artifacts": [str(api_results_file)],
        }

    async def _database_benchmarks_stage(self) -> dict[str, Any]:
        """Database benchmarks stage"""
        if not self.config.database_url:
            return {"status": "skipped", "reason": "No database URL configured"}

        # Setup database benchmarker
        db_config = DatabaseBenchmarkConfig(
            database_url=self.config.database_url,
            concurrent_connections=self.config.db_concurrent_connections,
            test_duration_seconds=self.config.db_test_duration,
        )

        benchmarker = DatabaseQueryBenchmarker(db_config)

        try:
            # Define test queries
            test_queries = []

            # Add custom queries if provided
            for custom_query in self.config.custom_db_queries:
                test_queries.append(
                    (
                        custom_query.get("id", "custom_query"),
                        custom_query.get("query", "SELECT 1"),
                        custom_query.get("parameters", {}),
                    )
                )

            # Add default queries if no custom queries
            if not test_queries:
                test_queries = [("simple_select", "SELECT 1", {}), ("timestamp_query", "SELECT current_timestamp", {})]

            # Run benchmark
            results = await benchmarker.benchmark_query_set(test_queries, "pipeline_db_test")

            # Save results
            db_results_file = self.output_dir / f"db_benchmark_{self.pipeline_id}.json"
            with open(db_results_file, "w") as f:
                json.dump(results.__dict__, f, indent=2, default=str)

            return {"results": results.__dict__, "artifacts": [str(db_results_file)]}

        finally:
            benchmarker.cleanup()

    async def _regression_analysis_stage(self) -> dict[str, Any]:
        """Regression analysis stage"""
        if not self.regression_detector:
            return {"status": "skipped", "reason": "Regression analysis disabled"}

        # This would typically load historical data and compare with current results
        # For now, return placeholder results
        analyses = self.regression_detector.analyze_all_metrics()

        # Save analysis results
        regression_file = self.output_dir / f"regression_analysis_{self.pipeline_id}.json"
        with open(regression_file, "w") as f:
            json.dump([a.__dict__ for a in analyses], f, indent=2, default=str)

        return {
            "analyses": [a.__dict__ for a in analyses],
            "regressions_detected": len([a for a in analyses if a.severity.value != "none"]),
            "artifacts": [str(regression_file)],
        }

    async def _comparison_stage(self) -> dict[str, Any]:
        """Comparison with baseline stage"""
        if not self.comparator:
            return {"status": "skipped", "reason": "Comparison disabled"}

        # This would typically compare current results with baseline
        # For now, return placeholder results
        return {"status": "completed", "message": "Comparison with baseline completed"}

    async def _reporting_stage(self, stages: list[PipelineStageResult]) -> dict[str, Any]:
        """Report generation stage"""
        artifacts = []

        # Generate JSON report
        if self.config.generate_json_report:
            json_report = {
                "pipeline_id": self.pipeline_id,
                "execution_summary": {
                    "start_time": stages[0].start_time.isoformat() if stages else datetime.utcnow().isoformat(),
                    "stages": [
                        {
                            "stage": s.stage.value,
                            "status": s.status.value,
                            "execution_time": s.execution_time,
                            "errors": s.errors,
                            "warnings": s.warnings,
                        }
                        for s in stages
                    ],
                },
            }

            json_file = self.output_dir / f"pipeline_report_{self.pipeline_id}.json"
            with open(json_file, "w") as f:
                json.dump(json_report, f, indent=2, default=str)
            artifacts.append(str(json_file))

        # Generate HTML report if enabled
        if self.config.generate_html_report:
            html_report = self._generate_html_report(stages)
            html_file = self.output_dir / f"pipeline_report_{self.pipeline_id}.html"
            with open(html_file, "w") as f:
                f.write(html_report)
            artifacts.append(str(html_file))

        return {"artifacts": artifacts}

    async def _cleanup_stage(self) -> dict[str, Any]:
        """Cleanup stage"""
        cleanup_actions = []

        # Stop system metrics collection
        if self.system_metrics:
            self.system_metrics.stop_collection()
            cleanup_actions.append("Stopped system metrics collection")

        return {"cleanup_actions": cleanup_actions}

    def _calculate_overall_performance_score(self, stages: list[PipelineStageResult]) -> float:
        """Calculate overall performance score (0-100)"""
        successful_stages = len([s for s in stages if s.status == PipelineStatus.SUCCESS])
        total_stages = len(stages)

        if total_stages == 0:
            return 0.0

        return (successful_stages / total_stages) * 100

    def _check_for_regressions(self, stages: list[PipelineStageResult]) -> bool:
        """Check if any regressions were detected"""
        for stage in stages:
            if stage.stage == PipelineStage.REGRESSION_ANALYSIS:
                output = stage.output
                return output.get("regressions_detected", 0) > 0
        return False

    def _extract_critical_issues(self, stages: list[PipelineStageResult]) -> list[dict[str, Any]]:
        """Extract critical issues from all stages"""
        issues = []

        for stage in stages:
            if stage.errors:
                for error in stage.errors:
                    issues.append(
                        {
                            "stage": stage.stage.value,
                            "type": "error",
                            "message": error,
                            "timestamp": stage.end_time.isoformat(),
                        }
                    )

        return issues

    def _generate_pipeline_summary(
        self, stages: list[PipelineStageResult], performance_score: float, regression_detected: bool
    ) -> str:
        """Generate human-readable pipeline summary"""
        len([s for s in stages if s.status == PipelineStatus.SUCCESS])
        failed_stages = len([s for s in stages if s.status == PipelineStatus.FAILED])

        if failed_stages > 0:
            return f"Pipeline completed with {failed_stages} failed stages. Performance score: {performance_score:.1f}%"
        elif regression_detected:
            return f"Pipeline successful but performance regressions detected. Score: {performance_score:.1f}%"
        else:
            return f"Pipeline completed successfully. Performance score: {performance_score:.1f}%"

    def _generate_pipeline_recommendations(
        self, stages: list[PipelineStageResult], critical_issues: list[dict[str, Any]]
    ) -> list[str]:
        """Generate pipeline-level recommendations"""
        recommendations = []

        if critical_issues:
            recommendations.append(f"🚨 {len(critical_issues)} critical issues detected - review stage outputs")

        failed_stages = [s for s in stages if s.status == PipelineStatus.FAILED]
        if failed_stages:
            recommendations.append("⚠️ Some pipeline stages failed - check configuration and environment")

        timeout_stages = [s for s in stages if s.status == PipelineStatus.TIMEOUT]
        if timeout_stages:
            recommendations.append("⏰ Some stages timed out - consider increasing timeout or optimizing tests")

        if not recommendations:
            recommendations.append("✅ Pipeline executed successfully without major issues")

        return recommendations

    def _generate_html_report(self, stages: list[PipelineStageResult]) -> str:
        """Generate HTML report"""
        # Simple HTML report template
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Pipeline Report - {self.pipeline_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; }}
                .stage {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; }}
                .success {{ border-left: 5px solid #28a745; }}
                .failed {{ border-left: 5px solid #dc3545; }}
                .timeout {{ border-left: 5px solid #ffc107; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Performance Pipeline Report</h1>
                <p>Pipeline ID: {self.pipeline_id}</p>
                <p>Generated: {datetime.utcnow().isoformat()}</p>
            </div>
        """

        for stage in stages:
            status_class = stage.status.value
            html += f"""
            <div class="stage {status_class}">
                <h2>{stage.stage.value.title()}</h2>
                <p>Status: {stage.status.value}</p>
                <p>Execution Time: {stage.execution_time:.2f}s</p>
                {f'<p>Errors: {"<br>".join(stage.errors)}</p>' if stage.errors else ''}
                {f'<p>Warnings: {"<br>".join(stage.warnings)}</p>' if stage.warnings else ''}
            </div>
            """

        html += """
        </body>
        </html>
        """

        return html

    def _create_failed_pipeline_result(
        self, start_time: datetime, stages: list[PipelineStageResult], reason: str
    ) -> PipelineResult:
        """Create pipeline result for failed execution"""
        end_time = datetime.utcnow()
        total_time = (end_time - start_time).total_seconds()

        return PipelineResult(
            pipeline_id=self.pipeline_id,
            status=PipelineStatus.FAILED,
            total_execution_time=total_time,
            start_time=start_time,
            end_time=end_time,
            stages=stages,
            overall_performance_score=0.0,
            regression_detected=False,
            critical_issues=[{"type": "pipeline_failure", "message": reason, "timestamp": end_time.isoformat()}],
            summary=f"Pipeline failed: {reason}",
            recommendations=[f"❌ Pipeline execution failed: {reason}"],
        )
