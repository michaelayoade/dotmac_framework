"""
DotMac Performance Benchmarking Suite

Comprehensive performance benchmarking and monitoring framework providing:
- System-wide performance metrics collection  
- API endpoint load testing and benchmarking
- Database query performance profiling
- Regression detection and trend analysis
- Benchmark comparison and analysis
- CI/CD integration for automated performance testing

Quick Start:
    from dotmac_shared.benchmarking import PerformanceBenchmarkManager, BenchmarkConfig
    
    manager = PerformanceBenchmarkManager()
    config = BenchmarkConfig(warmup_iterations=10)
    
    results = await manager.execute_benchmark(
        config, 
        your_benchmark_function, 
        *args, 
        **kwargs
    )
"""

# Core benchmarking components
from .core.benchmark_manager import (
    PerformanceBenchmarkManager,
    BenchmarkConfig,
    BenchmarkMetrics,
    BenchmarkType
)

# System metrics collection
from .collectors.system_metrics import (
    SystemMetricsCollector,
    SystemMetrics,
    ResourceUsage,
    MetricsCollectionConfig
)

# API benchmarking
from .profilers.api_benchmark import (
    ApiEndpointBenchmarker,
    ApiLoadTestConfig,
    ApiRequest,
    ApiLoadTestResults
)

# Database benchmarking
from .profilers.database_benchmark import (
    DatabaseQueryBenchmarker,
    DatabaseBenchmarkConfig,
    DatabaseBenchmarkResults,
    QueryMetrics
)

# Regression analysis
from .analyzers.regression_detector import (
    RegressionDetector,
    RegressionDetectionConfig,
    RegressionAnalysis,
    RegressionSeverity,
    PerformanceTrend
)

# Benchmark comparison
from .analyzers.benchmark_comparator import (
    BenchmarkComparator,
    BenchmarkComparisonConfig,
    ComparisonResult,
    BenchmarkDiff,
    ComparisonType
)

# CI/CD integration
from .cicd.pipeline_runner import (
    PerformancePipelineRunner,
    PipelineConfig,
    PipelineResult,
    PipelineStage,
    PipelineStatus
)

from .cicd.github_integration import (
    GitHubPerformanceCI,
    GitHubBenchmarkConfig
)

__version__ = "1.0.0"

__all__ = [
    # Core components
    'PerformanceBenchmarkManager',
    'BenchmarkConfig',
    'BenchmarkMetrics',
    'BenchmarkType',
    
    # System metrics
    'SystemMetricsCollector',
    'SystemMetrics',
    'ResourceUsage',
    'MetricsCollectionConfig',
    
    # API benchmarking
    'ApiEndpointBenchmarker',
    'ApiLoadTestConfig',
    'ApiRequest',
    'ApiLoadTestResults',
    
    # Database benchmarking
    'DatabaseQueryBenchmarker',
    'DatabaseBenchmarkConfig',
    'DatabaseBenchmarkResults',
    'QueryMetrics',
    
    # Regression analysis
    'RegressionDetector',
    'RegressionDetectionConfig',
    'RegressionAnalysis',
    'RegressionSeverity',
    'PerformanceTrend',
    
    # Comparison
    'BenchmarkComparator',
    'BenchmarkComparisonConfig',
    'ComparisonResult',
    'BenchmarkDiff',
    'ComparisonType',
    
    # CI/CD
    'PerformancePipelineRunner',
    'PipelineConfig',
    'PipelineResult',
    'PipelineStage',
    'PipelineStatus',
    'GitHubPerformanceCI',
    'GitHubBenchmarkConfig'
]


def create_benchmark_suite(
    api_base_url: str = None,
    database_url: str = None,
    enable_system_metrics: bool = True,
    enable_regression_detection: bool = True
) -> dict:
    """
    Factory function to create a complete benchmarking suite with sensible defaults.
    
    Args:
        api_base_url: Base URL for API benchmarking (optional)
        database_url: Database connection URL for DB benchmarking (optional)
        enable_system_metrics: Whether to collect system metrics
        enable_regression_detection: Whether to enable regression analysis
    
    Returns:
        Dictionary containing configured benchmarking components
    """
    suite = {}
    
    # Core benchmark manager
    suite['manager'] = PerformanceBenchmarkManager()
    
    # System metrics collector
    if enable_system_metrics:
        suite['system_metrics'] = SystemMetricsCollector()
    
    # API benchmarker
    if api_base_url:
        suite['api_benchmarker'] = ApiEndpointBenchmarker(api_base_url)
    
    # Database benchmarker
    if database_url:
        db_config = DatabaseBenchmarkConfig(database_url=database_url)
        suite['database_benchmarker'] = DatabaseQueryBenchmarker(db_config)
    
    # Regression detector
    if enable_regression_detection:
        regression_config = RegressionDetectionConfig()
        suite['regression_detector'] = RegressionDetector(regression_config)
    
    # Benchmark comparator
    suite['comparator'] = BenchmarkComparator(BenchmarkComparisonConfig())
    
    return suite


async def run_comprehensive_benchmark(
    suite_components: dict,
    test_name: str = "comprehensive_benchmark"
) -> dict:
    """
    Run a comprehensive benchmark using all available components.
    
    Args:
        suite_components: Dictionary from create_benchmark_suite()
        test_name: Name for the benchmark run
    
    Returns:
        Dictionary containing all benchmark results
    """
    results = {
        'test_name': test_name,
        'timestamp': BenchmarkMetrics.get_timestamp(),
        'components': {}
    }
    
    # System metrics
    if 'system_metrics' in suite_components:
        collector = suite_components['system_metrics']
        await collector.start_collection()
        # Let it collect for a short period
        import asyncio
        await asyncio.sleep(10)
        results['components']['system_metrics'] = collector.get_current_metrics()
        collector.stop_collection()
    
    # API benchmarks
    if 'api_benchmarker' in suite_components:
        benchmarker = suite_components['api_benchmarker']
        # Run basic health check benchmark
        test_requests = [{
            "method": "GET",
            "path": "/health",
            "name": "health_check"
        }]
        config = ApiLoadTestConfig(concurrent_users=5, duration_seconds=30)
        api_results = await benchmarker.run_load_test(test_requests, config, f"{test_name}_api")
        results['components']['api_benchmark'] = api_results.__dict__
    
    # Database benchmarks
    if 'database_benchmarker' in suite_components:
        benchmarker = suite_components['database_benchmarker']
        test_queries = [
            ("health_check", "SELECT 1 as health_check", {}),
            ("timestamp_query", "SELECT CURRENT_TIMESTAMP", {})
        ]
        db_results = await benchmarker.benchmark_query_set(test_queries, f"{test_name}_db")
        results['components']['database_benchmark'] = db_results.__dict__
    
    return results