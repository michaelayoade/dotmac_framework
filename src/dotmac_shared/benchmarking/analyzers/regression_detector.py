"""
Performance Regression Detection Module

Provides advanced regression detection and analysis capabilities for performance
benchmarks, including trend analysis, statistical change detection, and
automated alerting for performance degradations.
"""

import statistics
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Union
from enum import Enum

from pydantic import BaseModel, Field

from ..utils.decorators import standard_exception_handler


class RegressionSeverity(Enum):
    """Severity levels for performance regressions"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"


class PerformanceTrend(Enum):
    """Performance trend indicators"""
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    VOLATILE = "volatile"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class BenchmarkDataPoint:
    """Single benchmark measurement data point"""
    timestamp: datetime
    metric_value: float
    test_name: str
    environment: str = "default"
    build_id: Optional[str] = None
    commit_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegressionAnalysis:
    """Analysis result for performance regression detection"""
    test_name: str
    metric_name: str
    severity: RegressionSeverity
    trend: PerformanceTrend
    current_value: float
    baseline_value: float
    percentage_change: float
    absolute_change: float
    confidence_level: float
    detection_timestamp: datetime
    analysis_period_days: int
    data_points_analyzed: int
    statistical_significance: float
    recommendations: List[str] = field(default_factory=list)
    trend_data: List[BenchmarkDataPoint] = field(default_factory=list)


class RegressionDetectionConfig(BaseModel):
    """Configuration for regression detection"""
    baseline_days: int = Field(default=30, ge=7, le=90)
    minimum_data_points: int = Field(default=10, ge=3)
    regression_threshold_percent: float = Field(default=10.0, ge=1.0, le=100.0)
    critical_threshold_percent: float = Field(default=25.0, ge=5.0, le=200.0)
    statistical_confidence: float = Field(default=0.95, ge=0.8, le=0.99)
    noise_filter_enabled: bool = True
    trend_analysis_window: int = Field(default=14, ge=3, le=60)
    volatility_threshold: float = Field(default=20.0, ge=5.0, le=100.0)
    enable_seasonal_adjustment: bool = False
    outlier_detection_enabled: bool = True
    outlier_threshold_std_devs: float = Field(default=2.0, ge=1.0, le=4.0)


class RegressionDetector:
    """Advanced performance regression detection and analysis"""
    
    def __init__(self, config: RegressionDetectionConfig):
        self.config = config
        self.historical_data: Dict[str, List[BenchmarkDataPoint]] = {}
        self.baselines: Dict[str, float] = {}
        
    @standard_exception_handler
    def add_benchmark_result(
        self,
        test_name: str,
        metric_name: str,
        value: float,
        timestamp: datetime = None,
        environment: str = "default",
        build_id: str = None,
        commit_hash: str = None,
        metadata: Dict[str, Any] = None
    ):
        """Add a new benchmark result for regression analysis"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        data_point = BenchmarkDataPoint(
            timestamp=timestamp,
            metric_value=value,
            test_name=test_name,
            environment=environment,
            build_id=build_id,
            commit_hash=commit_hash,
            metadata=metadata or {}
        )
        
        key = f"{test_name}:{metric_name}:{environment}"
        
        if key not in self.historical_data:
            self.historical_data[key] = []
        
        self.historical_data[key].append(data_point)
        
        # Keep data within retention period
        self._cleanup_old_data(key)
        
        # Update baseline if needed
        self._update_baseline(key)
    
    @standard_exception_handler
    def detect_regression(
        self,
        test_name: str,
        metric_name: str,
        environment: str = "default"
    ) -> RegressionAnalysis:
        """Detect performance regression for a specific test metric"""
        key = f"{test_name}:{metric_name}:{environment}"
        
        if key not in self.historical_data:
            return self._create_insufficient_data_analysis(test_name, metric_name)
        
        data_points = self.historical_data[key]
        
        if len(data_points) < self.config.minimum_data_points:
            return self._create_insufficient_data_analysis(test_name, metric_name)
        
        # Get current and baseline values
        current_value = data_points[-1].metric_value
        baseline_value = self._get_baseline_value(key)
        
        # Calculate change metrics
        percentage_change = ((current_value - baseline_value) / baseline_value) * 100
        absolute_change = current_value - baseline_value
        
        # Determine severity
        severity = self._calculate_regression_severity(percentage_change)
        
        # Analyze trend
        trend = self._analyze_trend(data_points)
        
        # Calculate statistical significance
        statistical_significance = self._calculate_statistical_significance(data_points, baseline_value)
        
        # Calculate confidence level
        confidence_level = self._calculate_confidence_level(data_points, baseline_value, current_value)
        
        # Generate recommendations
        recommendations = self._generate_regression_recommendations(
            severity, trend, percentage_change, data_points
        )
        
        return RegressionAnalysis(
            test_name=test_name,
            metric_name=metric_name,
            severity=severity,
            trend=trend,
            current_value=current_value,
            baseline_value=baseline_value,
            percentage_change=percentage_change,
            absolute_change=absolute_change,
            confidence_level=confidence_level,
            detection_timestamp=datetime.utcnow(),
            analysis_period_days=self.config.baseline_days,
            data_points_analyzed=len(data_points),
            statistical_significance=statistical_significance,
            recommendations=recommendations,
            trend_data=data_points[-self.config.trend_analysis_window:] if len(data_points) >= self.config.trend_analysis_window else data_points
        )
    
    @standard_exception_handler
    def analyze_all_metrics(self) -> List[RegressionAnalysis]:
        """Analyze all tracked metrics for regressions"""
        analyses = []
        
        for key in self.historical_data.keys():
            test_name, metric_name, environment = key.split(':', 2)
            analysis = self.detect_regression(test_name, metric_name, environment)
            analyses.append(analysis)
        
        # Sort by severity and confidence
        analyses.sort(
            key=lambda x: (x.severity.value, x.confidence_level),
            reverse=True
        )
        
        return analyses
    
    @standard_exception_handler
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary across all metrics"""
        analyses = self.analyze_all_metrics()
        
        if not analyses:
            return {"status": "no_data", "message": "No performance data available"}
        
        # Count by severity
        severity_counts = {}
        for severity in RegressionSeverity:
            severity_counts[severity.value] = sum(1 for a in analyses if a.severity == severity)
        
        # Count by trend
        trend_counts = {}
        for trend in PerformanceTrend:
            trend_counts[trend.value] = sum(1 for a in analyses if a.trend == trend)
        
        # Calculate overall health score (0-100)
        total_tests = len(analyses)
        regression_tests = sum(1 for a in analyses if a.severity != RegressionSeverity.NONE)
        health_score = ((total_tests - regression_tests) / total_tests) * 100 if total_tests > 0 else 100
        
        # Get worst regressions
        worst_regressions = [a for a in analyses if a.severity in [RegressionSeverity.HIGH, RegressionSeverity.CRITICAL]][:5]
        
        return {
            "status": "analyzed",
            "total_metrics": total_tests,
            "health_score": round(health_score, 1),
            "severity_breakdown": severity_counts,
            "trend_breakdown": trend_counts,
            "worst_regressions": [
                {
                    "test": r.test_name,
                    "metric": r.metric_name,
                    "severity": r.severity.value,
                    "change_percent": round(r.percentage_change, 1)
                }
                for r in worst_regressions
            ],
            "recommendations": self._get_summary_recommendations(analyses)
        }
    
    def _cleanup_old_data(self, key: str):
        """Remove data points older than the retention period"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.config.baseline_days * 2)
        self.historical_data[key] = [
            dp for dp in self.historical_data[key] 
            if dp.timestamp >= cutoff_date
        ]
    
    def _update_baseline(self, key: str):
        """Update baseline value for a metric"""
        data_points = self.historical_data[key]
        
        if len(data_points) < self.config.minimum_data_points:
            return
        
        # Use data from baseline period
        baseline_cutoff = datetime.utcnow() - timedelta(days=self.config.baseline_days)
        baseline_points = [
            dp for dp in data_points 
            if dp.timestamp <= baseline_cutoff
        ]
        
        if len(baseline_points) >= self.config.minimum_data_points:
            values = [dp.metric_value for dp in baseline_points]
            
            # Filter outliers if enabled
            if self.config.outlier_detection_enabled:
                values = self._remove_outliers(values)
            
            # Use median for more robust baseline
            self.baselines[key] = statistics.median(values) if values else data_points[0].metric_value
        else:
            # Use all available data if insufficient baseline data
            values = [dp.metric_value for dp in data_points]
            self.baselines[key] = statistics.median(values)
    
    def _get_baseline_value(self, key: str) -> float:
        """Get baseline value for comparison"""
        if key in self.baselines:
            return self.baselines[key]
        
        # Calculate baseline from available data
        data_points = self.historical_data[key]
        values = [dp.metric_value for dp in data_points[:-1]]  # Exclude current value
        
        if not values:
            return data_points[0].metric_value
        
        return statistics.median(values)
    
    def _calculate_regression_severity(self, percentage_change: float) -> RegressionSeverity:
        """Determine regression severity based on percentage change"""
        abs_change = abs(percentage_change)
        
        if abs_change >= self.config.critical_threshold_percent:
            return RegressionSeverity.CRITICAL
        elif abs_change >= self.config.regression_threshold_percent * 2:
            return RegressionSeverity.HIGH
        elif abs_change >= self.config.regression_threshold_percent:
            return RegressionSeverity.MEDIUM
        elif abs_change >= self.config.regression_threshold_percent * 0.5:
            return RegressionSeverity.LOW
        else:
            return RegressionSeverity.NONE
    
    def _analyze_trend(self, data_points: List[BenchmarkDataPoint]) -> PerformanceTrend:
        """Analyze performance trend over time"""
        if len(data_points) < 5:
            return PerformanceTrend.INSUFFICIENT_DATA
        
        # Use recent data for trend analysis
        recent_points = data_points[-self.config.trend_analysis_window:] if len(data_points) >= self.config.trend_analysis_window else data_points
        values = [dp.metric_value for dp in recent_points]
        
        # Calculate trend using linear regression
        x = list(range(len(values)))
        slope = self._calculate_trend_slope(x, values)
        
        # Calculate volatility
        volatility = (statistics.stdev(values) / statistics.mean(values)) * 100 if len(values) > 1 and statistics.mean(values) != 0 else 0
        
        if volatility > self.config.volatility_threshold:
            return PerformanceTrend.VOLATILE
        elif abs(slope) < 0.01:  # Very small slope
            return PerformanceTrend.STABLE
        elif slope > 0:
            return PerformanceTrend.DEGRADING  # Assuming higher values = worse performance
        else:
            return PerformanceTrend.IMPROVING
    
    def _calculate_trend_slope(self, x: List[int], y: List[float]) -> float:
        """Calculate trend slope using least squares regression"""
        n = len(x)
        if n < 2:
            return 0
        
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        return slope
    
    def _calculate_statistical_significance(self, data_points: List[BenchmarkDataPoint], baseline: float) -> float:
        """Calculate statistical significance of observed change"""
        if len(data_points) < 3:
            return 0.0
        
        values = [dp.metric_value for dp in data_points]
        
        try:
            # Simple t-test approximation
            mean_val = statistics.mean(values)
            std_dev = statistics.stdev(values) if len(values) > 1 else 1.0
            n = len(values)
            
            t_stat = abs(mean_val - baseline) / (std_dev / (n ** 0.5))
            
            # Rough approximation of p-value for t-test
            if t_stat > 2.576:  # 99% confidence
                return 0.99
            elif t_stat > 1.960:  # 95% confidence
                return 0.95
            elif t_stat > 1.645:  # 90% confidence
                return 0.90
            else:
                return max(0.0, 1.0 - (t_stat / 1.645) * 0.90)
        except:
            return 0.0
    
    def _calculate_confidence_level(self, data_points: List[BenchmarkDataPoint], baseline: float, current: float) -> float:
        """Calculate confidence level in the regression detection"""
        factors = []
        
        # Data quantity factor
        data_factor = min(1.0, len(data_points) / (self.config.minimum_data_points * 2))
        factors.append(data_factor)
        
        # Change magnitude factor
        change_percent = abs(((current - baseline) / baseline) * 100) if baseline != 0 else 0
        magnitude_factor = min(1.0, change_percent / self.config.regression_threshold_percent)
        factors.append(magnitude_factor)
        
        # Consistency factor (low variance = higher confidence)
        values = [dp.metric_value for dp in data_points]
        if len(values) > 1:
            cv = statistics.stdev(values) / statistics.mean(values) if statistics.mean(values) != 0 else 1.0
            consistency_factor = max(0.0, 1.0 - cv)
        else:
            consistency_factor = 0.5
        factors.append(consistency_factor)
        
        # Overall confidence is geometric mean of factors
        confidence = (np.prod(factors) ** (1.0 / len(factors))) if factors else 0.0
        return min(1.0, confidence)
    
    def _remove_outliers(self, values: List[float]) -> List[float]:
        """Remove statistical outliers from values"""
        if len(values) < 4:
            return values
        
        mean_val = statistics.mean(values)
        std_dev = statistics.stdev(values)
        threshold = self.config.outlier_threshold_std_devs
        
        filtered_values = [
            v for v in values 
            if abs(v - mean_val) <= threshold * std_dev
        ]
        
        return filtered_values if len(filtered_values) >= 3 else values
    
    def _generate_regression_recommendations(
        self,
        severity: RegressionSeverity,
        trend: PerformanceTrend,
        percentage_change: float,
        data_points: List[BenchmarkDataPoint]
    ) -> List[str]:
        """Generate specific recommendations based on regression analysis"""
        recommendations = []
        
        if severity == RegressionSeverity.CRITICAL:
            recommendations.append("🚨 CRITICAL: Immediate investigation required - performance degraded significantly")
            recommendations.append("Consider rolling back recent changes or implementing emergency fixes")
        
        if severity in [RegressionSeverity.HIGH, RegressionSeverity.MEDIUM]:
            recommendations.append("⚠️ Performance regression detected - review recent code changes")
            
        if trend == PerformanceTrend.DEGRADING:
            recommendations.append("📉 Consistent performance decline - investigate underlying causes")
            
        if trend == PerformanceTrend.VOLATILE:
            recommendations.append("📊 High performance volatility - check for resource contention or environmental issues")
        
        if percentage_change > 0:  # Performance got worse
            recommendations.append("🔍 Analyze recent deployments, database changes, or infrastructure modifications")
            
        if len(data_points) < 20:
            recommendations.append("📈 Increase benchmark frequency for better trend analysis")
        
        return recommendations
    
    def _get_summary_recommendations(self, analyses: List[RegressionAnalysis]) -> List[str]:
        """Get high-level recommendations across all analyses"""
        recommendations = []
        
        critical_count = sum(1 for a in analyses if a.severity == RegressionSeverity.CRITICAL)
        high_count = sum(1 for a in analyses if a.severity == RegressionSeverity.HIGH)
        
        if critical_count > 0:
            recommendations.append(f"🚨 {critical_count} CRITICAL performance regressions require immediate attention")
        
        if high_count > 0:
            recommendations.append(f"⚠️ {high_count} HIGH severity regressions need investigation")
        
        volatile_count = sum(1 for a in analyses if a.trend == PerformanceTrend.VOLATILE)
        if volatile_count > 3:
            recommendations.append("📊 Multiple metrics showing volatility - check infrastructure stability")
        
        degrading_count = sum(1 for a in analyses if a.trend == PerformanceTrend.DEGRADING)
        if degrading_count > 2:
            recommendations.append("📉 Multiple metrics trending downward - review recent changes")
        
        if not recommendations:
            recommendations.append("✅ Performance is stable across all monitored metrics")
        
        return recommendations
    
    def _create_insufficient_data_analysis(self, test_name: str, metric_name: str) -> RegressionAnalysis:
        """Create analysis result for insufficient data scenarios"""
        return RegressionAnalysis(
            test_name=test_name,
            metric_name=metric_name,
            severity=RegressionSeverity.NONE,
            trend=PerformanceTrend.INSUFFICIENT_DATA,
            current_value=0.0,
            baseline_value=0.0,
            percentage_change=0.0,
            absolute_change=0.0,
            confidence_level=0.0,
            detection_timestamp=datetime.utcnow(),
            analysis_period_days=self.config.baseline_days,
            data_points_analyzed=0,
            statistical_significance=0.0,
            recommendations=["📊 Insufficient data for regression analysis - collect more benchmark data"]
        )