"""
Benchmark Comparison and Analysis Module

Provides comprehensive comparison capabilities for benchmark results across
different time periods, environments, configurations, and code versions.
"""

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from ..utils.decorators import standard_exception_handler


class ComparisonType(Enum):
    """Types of benchmark comparisons"""

    TIME_PERIOD = "time_period"
    ENVIRONMENT = "environment"
    VERSION = "version"
    CONFIGURATION = "configuration"
    BASELINE = "baseline"


class ChangeSignificance(Enum):
    """Significance levels for benchmark changes"""

    INSIGNIFICANT = "insignificant"
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


@dataclass
class BenchmarkDiff:
    """Difference between two benchmark measurements"""

    metric_name: str
    old_value: float
    new_value: float
    absolute_change: float
    percentage_change: float
    significance: ChangeSignificance
    is_improvement: bool
    confidence_level: float


@dataclass
class ComparisonResult:
    """Complete comparison result between benchmark sets"""

    comparison_type: ComparisonType
    comparison_name: str
    baseline_name: str
    target_name: str
    execution_time: float
    total_metrics_compared: int
    improved_metrics: int
    degraded_metrics: int
    unchanged_metrics: int
    overall_performance_change: float
    significant_changes: list[BenchmarkDiff]
    all_diffs: list[BenchmarkDiff]
    summary: str
    recommendations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    comparison_timestamp: datetime = field(default_factory=datetime.utcnow)


class BenchmarkComparisonConfig(BaseModel):
    """Configuration for benchmark comparisons"""

    insignificant_threshold: float = Field(default=2.0, ge=0.1, le=10.0)
    minor_threshold: float = Field(default=5.0, ge=1.0, le=20.0)
    moderate_threshold: float = Field(default=15.0, ge=5.0, le=50.0)
    major_threshold: float = Field(default=30.0, ge=15.0, le=100.0)
    minimum_confidence: float = Field(default=0.7, ge=0.5, le=1.0)
    include_insignificant_changes: bool = False
    normalize_by_environment: bool = True
    apply_statistical_filters: bool = True
    outlier_detection_enabled: bool = True
    group_related_metrics: bool = True


class BenchmarkComparator:
    """Advanced benchmark comparison and analysis engine"""

    def __init__(self, config: BenchmarkComparisonConfig):
        self.config = config

    @standard_exception_handler
    def compare_benchmark_sets(
        self,
        baseline_results: dict[str, float],
        target_results: dict[str, float],
        baseline_name: str = "baseline",
        target_name: str = "target",
        comparison_type: ComparisonType = ComparisonType.BASELINE,
    ) -> ComparisonResult:
        """Compare two sets of benchmark results"""
        start_time = datetime.utcnow()

        # Find common metrics
        common_metrics = set(baseline_results.keys()) & set(target_results.keys())

        if not common_metrics:
            return self._create_empty_comparison(
                baseline_name, target_name, comparison_type, "No common metrics found"
            )

        # Calculate differences for each metric
        all_diffs = []
        significant_changes = []

        for metric_name in common_metrics:
            diff = self._calculate_metric_diff(
                metric_name, baseline_results[metric_name], target_results[metric_name]
            )
            all_diffs.append(diff)

            if self._is_significant_change(diff):
                significant_changes.append(diff)

        # Calculate summary statistics
        improved_count = sum(1 for d in all_diffs if d.is_improvement)
        degraded_count = sum(
            1
            for d in all_diffs
            if not d.is_improvement
            and d.significance != ChangeSignificance.INSIGNIFICANT
        )
        unchanged_count = len(all_diffs) - improved_count - degraded_count

        # Calculate overall performance change
        percentage_changes = [
            d.percentage_change
            for d in all_diffs
            if d.significance != ChangeSignificance.INSIGNIFICANT
        ]
        overall_change = (
            statistics.mean(percentage_changes) if percentage_changes else 0.0
        )

        # Generate summary and recommendations
        summary = self._generate_comparison_summary(all_diffs, overall_change)
        recommendations = self._generate_comparison_recommendations(
            all_diffs, overall_change
        )

        execution_time = (datetime.utcnow() - start_time).total_seconds()

        return ComparisonResult(
            comparison_type=comparison_type,
            comparison_name=f"{baseline_name} vs {target_name}",
            baseline_name=baseline_name,
            target_name=target_name,
            execution_time=execution_time,
            total_metrics_compared=len(all_diffs),
            improved_metrics=improved_count,
            degraded_metrics=degraded_count,
            unchanged_metrics=unchanged_count,
            overall_performance_change=overall_change,
            significant_changes=significant_changes,
            all_diffs=all_diffs,
            summary=summary,
            recommendations=recommendations,
        )

    @standard_exception_handler
    def compare_time_series(
        self,
        time_series_data: dict[datetime, dict[str, float]],
        baseline_period_days: int = 7,
        comparison_window_days: int = 1,
    ) -> list[ComparisonResult]:
        """Compare recent performance against historical baseline"""
        if len(time_series_data) < 2:
            return []

        # Sort data by timestamp
        sorted_timestamps = sorted(time_series_data.keys())

        # Define baseline period (older data)
        baseline_end = (
            sorted_timestamps[-comparison_window_days - 1]
            if len(sorted_timestamps) > comparison_window_days
            else sorted_timestamps[-2]
        )
        baseline_start = baseline_end - timedelta(days=baseline_period_days)

        # Define comparison period (recent data)
        comparison_start = (
            sorted_timestamps[-comparison_window_days]
            if len(sorted_timestamps) > comparison_window_days
            else sorted_timestamps[-1]
        )

        # Aggregate baseline data
        baseline_data = {}
        baseline_timestamps = [
            ts for ts in sorted_timestamps if baseline_start <= ts <= baseline_end
        ]

        if baseline_timestamps:
            for metric_name in time_series_data[baseline_timestamps[0]].keys():
                values = [
                    time_series_data[ts].get(metric_name, 0)
                    for ts in baseline_timestamps
                    if metric_name in time_series_data[ts]
                ]
                if values:
                    baseline_data[metric_name] = statistics.median(
                        values
                    )  # Use median for robustness

        # Aggregate comparison data
        comparison_data = {}
        comparison_timestamps = [
            ts for ts in sorted_timestamps if ts >= comparison_start
        ]

        if comparison_timestamps:
            for metric_name in time_series_data[comparison_timestamps[0]].keys():
                values = [
                    time_series_data[ts].get(metric_name, 0)
                    for ts in comparison_timestamps
                    if metric_name in time_series_data[ts]
                ]
                if values:
                    comparison_data[metric_name] = statistics.median(values)

        # Perform comparison
        if baseline_data and comparison_data:
            result = self.compare_benchmark_sets(
                baseline_data,
                comparison_data,
                f"baseline_{baseline_period_days}d",
                f"recent_{comparison_window_days}d",
                ComparisonType.TIME_PERIOD,
            )
            return [result]

        return []

    @standard_exception_handler
    def compare_environments(
        self,
        environment_results: dict[str, dict[str, float]],
        reference_environment: Optional[str] = None,
    ) -> list[ComparisonResult]:
        """Compare performance across different environments"""
        if len(environment_results) < 2:
            return []

        environments = list(environment_results.keys())

        # Use specified reference or first environment as baseline
        if reference_environment and reference_environment in environments:
            baseline_env = reference_environment
        else:
            baseline_env = environments[0]

        results = []

        for env in environments:
            if env != baseline_env:
                result = self.compare_benchmark_sets(
                    environment_results[baseline_env],
                    environment_results[env],
                    f"env_{baseline_env}",
                    f"env_{env}",
                    ComparisonType.ENVIRONMENT,
                )
                results.append(result)

        return results

    @standard_exception_handler
    def compare_versions(
        self,
        version_results: dict[str, dict[str, float]],
        version_order: Optional[list[str]] = None,
    ) -> list[ComparisonResult]:
        """Compare performance across different versions"""
        if len(version_results) < 2:
            return []

        # Sort versions if order provided, otherwise use keys
        versions = version_order if version_order else sorted(version_results.keys())

        results = []

        # Compare each version with the previous one
        for i in range(1, len(versions)):
            prev_version = versions[i - 1]
            curr_version = versions[i]

            if prev_version in version_results and curr_version in version_results:
                result = self.compare_benchmark_sets(
                    version_results[prev_version],
                    version_results[curr_version],
                    f"version_{prev_version}",
                    f"version_{curr_version}",
                    ComparisonType.VERSION,
                )
                results.append(result)

        return results

    @standard_exception_handler
    def generate_comparison_report(
        self, comparison_results: list[ComparisonResult], include_details: bool = True
    ) -> dict[str, Any]:
        """Generate comprehensive comparison report"""
        if not comparison_results:
            return {
                "status": "no_comparisons",
                "message": "No comparison results available",
            }

        # Overall statistics
        total_comparisons = len(comparison_results)
        total_metrics = sum(r.total_metrics_compared for r in comparison_results)

        # Performance trends
        improving_comparisons = sum(
            1 for r in comparison_results if r.overall_performance_change < -2
        )
        degrading_comparisons = sum(
            1 for r in comparison_results if r.overall_performance_change > 2
        )
        stable_comparisons = (
            total_comparisons - improving_comparisons - degrading_comparisons
        )

        # Critical issues
        critical_issues = []
        for result in comparison_results:
            critical_changes = [
                d
                for d in result.significant_changes
                if d.significance == ChangeSignificance.CRITICAL
            ]
            for change in critical_changes:
                critical_issues.append(
                    {
                        "comparison": result.comparison_name,
                        "metric": change.metric_name,
                        "change_percent": change.percentage_change,
                        "is_improvement": change.is_improvement,
                    }
                )

        # Summary metrics
        summary_stats = {
            "total_comparisons": total_comparisons,
            "total_metrics_analyzed": total_metrics,
            "improving_comparisons": improving_comparisons,
            "degrading_comparisons": degrading_comparisons,
            "stable_comparisons": stable_comparisons,
            "critical_issues_count": len(critical_issues),
        }

        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "summary": summary_stats,
            "performance_trend": self._determine_overall_trend(comparison_results),
            "critical_issues": critical_issues,
            "recommendations": self._generate_report_recommendations(
                comparison_results
            ),
        }

        if include_details:
            report["detailed_comparisons"] = [
                {
                    "comparison_name": r.comparison_name,
                    "type": r.comparison_type.value,
                    "overall_change": r.overall_performance_change,
                    "metrics_compared": r.total_metrics_compared,
                    "improved": r.improved_metrics,
                    "degraded": r.degraded_metrics,
                    "significant_changes": len(r.significant_changes),
                    "summary": r.summary,
                }
                for r in comparison_results
            ]

        return report

    def _calculate_metric_diff(
        self, metric_name: str, old_value: float, new_value: float
    ) -> BenchmarkDiff:
        """Calculate difference between two metric values"""
        absolute_change = new_value - old_value
        percentage_change = (absolute_change / old_value) * 100 if old_value != 0 else 0

        # Determine significance
        abs_percentage = abs(percentage_change)
        if abs_percentage >= self.config.major_threshold:
            significance = (
                ChangeSignificance.CRITICAL
                if abs_percentage >= 50
                else ChangeSignificance.MAJOR
            )
        elif abs_percentage >= self.config.moderate_threshold:
            significance = ChangeSignificance.MODERATE
        elif abs_percentage >= self.config.minor_threshold:
            significance = ChangeSignificance.MINOR
        else:
            significance = ChangeSignificance.INSIGNIFICANT

        # Determine if change is improvement (lower is generally better for performance metrics)
        is_improvement = absolute_change < 0

        # Calculate confidence (simplified)
        confidence_level = (
            min(1.0, abs_percentage / self.config.minor_threshold)
            if abs_percentage > 0
            else 0.0
        )

        return BenchmarkDiff(
            metric_name=metric_name,
            old_value=old_value,
            new_value=new_value,
            absolute_change=absolute_change,
            percentage_change=percentage_change,
            significance=significance,
            is_improvement=is_improvement,
            confidence_level=confidence_level,
        )

    def _is_significant_change(self, diff: BenchmarkDiff) -> bool:
        """Determine if a change is significant based on configuration"""
        if (
            not self.config.include_insignificant_changes
            and diff.significance == ChangeSignificance.INSIGNIFICANT
        ):
            return False

        return diff.confidence_level >= self.config.minimum_confidence

    def _generate_comparison_summary(
        self, diffs: list[BenchmarkDiff], overall_change: float
    ) -> str:
        """Generate human-readable summary of comparison"""
        if not diffs:
            return "No metrics were compared."

        improved = sum(
            1
            for d in diffs
            if d.is_improvement and d.significance != ChangeSignificance.INSIGNIFICANT
        )
        degraded = sum(
            1
            for d in diffs
            if not d.is_improvement
            and d.significance != ChangeSignificance.INSIGNIFICANT
        )

        if abs(overall_change) < 2:
            trend = "stable"
        elif overall_change < 0:
            trend = "improved"
        else:
            trend = "degraded"

        return (
            f"Performance has {trend} overall ({overall_change:+.1f}%) with "
            f"{improved} improved and {degraded} degraded metrics out of {len(diffs)} compared."
        )

    def _generate_comparison_recommendations(
        self, diffs: list[BenchmarkDiff], overall_change: float
    ) -> list[str]:
        """Generate recommendations based on comparison results"""
        recommendations = []

        critical_diffs = [
            d for d in diffs if d.significance == ChangeSignificance.CRITICAL
        ]
        major_diffs = [d for d in diffs if d.significance == ChangeSignificance.MAJOR]

        if critical_diffs:
            critical_degraded = [d for d in critical_diffs if not d.is_improvement]
            if critical_degraded:
                recommendations.append(
                    f"🚨 CRITICAL: {len(critical_degraded)} metrics show severe performance degradation"
                )
                recommendations.append(
                    "Immediate investigation and potential rollback required"
                )

        if major_diffs:
            major_degraded = [d for d in major_diffs if not d.is_improvement]
            if major_degraded:
                recommendations.append(
                    f"⚠️ MAJOR: {len(major_degraded)} metrics show significant performance regression"
                )

        if overall_change > 10:
            recommendations.append(
                "📈 Overall performance has degraded - review recent changes"
            )
        elif overall_change < -10:
            recommendations.append("✅ Overall performance has improved significantly")

        # Specific metric recommendations
        slow_queries = [
            d
            for d in diffs
            if "query" in d.metric_name.lower()
            and not d.is_improvement
            and d.significance
            in [ChangeSignificance.MAJOR, ChangeSignificance.CRITICAL]
        ]
        if slow_queries:
            recommendations.append(
                "🔍 Database query performance has degraded - review query optimizations"
            )

        high_memory = [
            d
            for d in diffs
            if "memory" in d.metric_name.lower()
            and not d.is_improvement
            and d.significance
            in [ChangeSignificance.MAJOR, ChangeSignificance.CRITICAL]
        ]
        if high_memory:
            recommendations.append(
                "💾 Memory usage has increased significantly - check for memory leaks"
            )

        if not recommendations:
            recommendations.append("✅ Performance comparison looks healthy")

        return recommendations

    def _determine_overall_trend(
        self, comparison_results: list[ComparisonResult]
    ) -> str:
        """Determine overall performance trend across all comparisons"""
        if not comparison_results:
            return "unknown"

        avg_change = statistics.mean(
            [r.overall_performance_change for r in comparison_results]
        )

        if avg_change > 10:
            return "significantly_degraded"
        elif avg_change > 2:
            return "degraded"
        elif avg_change < -10:
            return "significantly_improved"
        elif avg_change < -2:
            return "improved"
        else:
            return "stable"

    def _generate_report_recommendations(
        self, comparison_results: list[ComparisonResult]
    ) -> list[str]:
        """Generate high-level recommendations for the entire report"""
        recommendations = []

        critical_count = sum(
            len(
                [
                    d
                    for d in r.significant_changes
                    if d.significance == ChangeSignificance.CRITICAL
                ]
            )
            for r in comparison_results
        )
        if critical_count > 0:
            recommendations.append(
                f"🚨 {critical_count} critical performance issues detected across all comparisons"
            )

        degrading_comparisons = sum(
            1 for r in comparison_results if r.overall_performance_change > 5
        )
        if degrading_comparisons > len(comparison_results) * 0.5:
            recommendations.append(
                "📉 Majority of comparisons show performance degradation - review recent changes"
            )

        if not recommendations:
            recommendations.append(
                "✅ Performance comparisons show stable or improving trends"
            )

        return recommendations

    def _create_empty_comparison(
        self,
        baseline_name: str,
        target_name: str,
        comparison_type: ComparisonType,
        reason: str,
    ) -> ComparisonResult:
        """Create empty comparison result for error cases"""
        return ComparisonResult(
            comparison_type=comparison_type,
            comparison_name=f"{baseline_name} vs {target_name}",
            baseline_name=baseline_name,
            target_name=target_name,
            execution_time=0.0,
            total_metrics_compared=0,
            improved_metrics=0,
            degraded_metrics=0,
            unchanged_metrics=0,
            overall_performance_change=0.0,
            significant_changes=[],
            all_diffs=[],
            summary=reason,
            recommendations=[f"Unable to perform comparison: {reason}"],
        )
