#!/usr/bin/env python3
"""
Performance Benchmarking Suite Example

Demonstrates comprehensive usage of the DotMac performance benchmarking framework
including system metrics, API benchmarking, database profiling, regression detection,
and CI/CD integration.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Configure logging for example tracking
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('performance_benchmarking_example.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Import the benchmarking suite
from dotmac_shared.benchmarking import (
    # Profilers
    ApiEndpointBenchmarker,
    ApiLoadTestConfig,
    BenchmarkComparator,
    BenchmarkComparisonConfig,
    BenchmarkConfig,
    DatabaseBenchmarkConfig,
    DatabaseQueryBenchmarker,
    # Core components
    PerformanceBenchmarkManager,
    # CI/CD
    PerformancePipelineRunner,
    PipelineConfig,
    RegressionDetectionConfig,
    # Analysis
    RegressionDetector,
    SystemMetricsCollector,
    create_benchmark_suite,
    run_comprehensive_benchmark,
)


async def example_1_basic_benchmarking():
    """Example 1: Basic performance benchmarking with system metrics"""

    print("🔄 Example 1: Basic Performance Benchmarking")
    print("=" * 60)

    # Create benchmark manager
    manager = PerformanceBenchmarkManager()
    config = BenchmarkConfig(
        warmup_iterations=5, test_iterations=20, concurrent_execution=False, collect_system_resources=True
    )

    # Define a simple benchmark function
    async def cpu_intensive_task():
        """Simulate CPU-intensive work"""
        total = 0
        for i in range(100000):
            total += i * i
        return total

    # Run benchmark
    print("Running CPU-intensive benchmark...")
    results = await manager.execute_benchmark(config, cpu_intensive_task)

    # Display results
    print("📊 Benchmark Results:")
    print(f"   Average time: {results.average_execution_time:.4f}s")
    print(f"   Min time: {results.min_execution_time:.4f}s")
    print(f"   Max time: {results.max_execution_time:.4f}s")
    print(f"   P95 time: {results.p95_execution_time:.4f}s")
    print(f"   Standard deviation: {results.execution_time_std_dev:.4f}s")

    if results.resource_usage:
        print(f"   CPU usage: {results.resource_usage.get('cpu_percent', 0):.1f}%")
        print(f"   Memory usage: {results.resource_usage.get('memory_percent', 0):.1f}%")

    print("✅ Example 1 completed\n")


async def example_2_system_metrics():
    """Example 2: System-wide metrics collection"""

    print("🔄 Example 2: System Metrics Collection")
    print("=" * 60)

    # Create system metrics collector
    collector = SystemMetricsCollector(collection_interval=0.5, history_size=100)

    # Start collection
    print("Starting system metrics collection for 10 seconds...")
    await collector.start_collection()

    # Let it collect while doing some work
    for i in range(10):
        # Simulate varying workload
        work_amount = (i % 3 + 1) * 50000
        sum(x * x for x in range(work_amount))
        await asyncio.sleep(1)

        # Get current metrics
        current = collector.get_current_metrics()
        print(f"   Second {i+1}: CPU {current.cpu_percent:.1f}%, Memory {current.memory_percent:.1f}%")

    # Establish baseline
    baseline = collector.establish_baseline(duration_seconds=5)
    print("\n📊 Baseline Metrics:")
    for metric, value in baseline.items():
        print(f"   {metric}: {value:.2f}")

    # Stop collection
    collector.stop_collection()
    print("✅ Example 2 completed\n")


async def example_3_api_benchmarking():
    """Example 3: API endpoint benchmarking"""

    print("🔄 Example 3: API Endpoint Benchmarking")
    print("=" * 60)

    # Note: This example uses httpbin.org as a test API
    api_base_url = "https://httpbin.org"

    # Create API benchmarker
    benchmarker = ApiEndpointBenchmarker(api_base_url)

    # Define test requests
    test_requests = [
        {"method": "GET", "path": "/status/200", "name": "health_check", "expected_status": 200},
        {"method": "GET", "path": "/delay/1", "name": "delayed_response", "expected_status": 200},
        {"method": "POST", "path": "/post", "name": "post_data", "json": {"test": "data"}, "expected_status": 200},
    ]

    # Configure load test
    config = ApiLoadTestConfig(concurrent_users=5, duration_seconds=20, ramp_up_seconds=5, requests_per_user=10)

    print(f"Running API load test with {config.concurrent_users} concurrent users for {config.duration_seconds}s...")

    # Run load test
    results = await benchmarker.run_load_test(test_requests, config, "example_api_test")

    # Display results
    print("📊 API Benchmark Results:")
    print(f"   Total requests: {results.total_requests}")
    print(f"   Successful requests: {results.successful_requests}")
    print(f"   Failed requests: {results.failed_requests}")
    print(f"   Requests per second: {results.requests_per_second:.2f}")
    print(f"   Average response time: {results.average_response_time:.3f}s")
    print(f"   P95 response time: {results.p95_response_time:.3f}s")
    print(f"   Error rate: {results.error_rate:.2f}%")

    if results.endpoint_results:
        print("   Endpoint breakdown:")
        for endpoint, endpoint_result in results.endpoint_results.items():
            print(f"     {endpoint}: {endpoint_result.get('avg_response_time', 0):.3f}s avg")

    print("✅ Example 3 completed\n")


async def example_4_database_benchmarking():
    """Example 4: Database query benchmarking"""

    print("🔄 Example 4: Database Query Benchmarking")
    print("=" * 60)

    # Use SQLite for this example
    database_url = "sqlite:///./example_benchmark.db"

    # Create database benchmarker
    config = DatabaseBenchmarkConfig(
        database_url=database_url, concurrent_connections=3, warmup_queries=10, test_duration_seconds=30
    )

    benchmarker = DatabaseQueryBenchmarker(config)

    try:
        # Create test table
        with benchmarker.session_factory() as session:
            session.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name TEXT, value INTEGER)")
            session.execute("INSERT OR REPLACE INTO test_table (id, name, value) VALUES (1, 'test1', 100)")
            session.execute("INSERT OR REPLACE INTO test_table (id, name, value) VALUES (2, 'test2', 200)")
            session.commit()

        # Define test queries
        test_queries = [
            ("simple_select", "SELECT * FROM test_table WHERE id = 1", {}),
            ("aggregate_query", "SELECT COUNT(*), AVG(value) FROM test_table", {}),
            (
                "insert_query",
                "INSERT INTO test_table (name, value) VALUES ('temp', 999); DELETE FROM test_table WHERE name = 'temp'",
                {},
            ),
        ]

        print(f"Running database benchmarks with {config.concurrent_connections} connections...")

        # Run benchmarks
        results = await benchmarker.benchmark_query_set(test_queries, "example_db_test")

        # Display results
        print("📊 Database Benchmark Results:")
        print(f"   Total queries: {results.total_queries}")
        print(f"   Successful queries: {results.successful_queries}")
        print(f"   Failed queries: {results.failed_queries}")
        print(f"   Queries per second: {results.queries_per_second:.2f}")
        print(f"   Average response time: {results.avg_response_time:.4f}s")
        print(f"   P95 response time: {results.p95_response_time:.4f}s")
        print(f"   Connection pool utilization: {results.connection_pool_metrics.pool_utilization:.1f}%")

        # Show per-query breakdown
        if results.query_metrics:
            print("   Query breakdown:")
            query_times = {}
            for metric in results.query_metrics:
                query_id = metric.query_id.split("_")[0]  # Get base query name
                if query_id not in query_times:
                    query_times[query_id] = []
                query_times[query_id].append(metric.execution_time)

            for query_id, times in query_times.items():
                avg_time = sum(times) / len(times)
                print(f"     {query_id}: {avg_time:.4f}s avg")

        print("✅ Example 4 completed")

    finally:
        benchmarker.cleanup()
        # Clean up test database
        if os.path.exists("example_benchmark.db"):
            os.remove("example_benchmark.db")

    print()


async def example_5_regression_detection():
    """Example 5: Regression detection and analysis"""

    print("🔄 Example 5: Regression Detection")
    print("=" * 60)

    # Create regression detector
    config = RegressionDetectionConfig(baseline_days=7, regression_threshold_percent=15.0, minimum_data_points=5)

    detector = RegressionDetector(config)

    # Simulate historical data
    print("Adding simulated historical benchmark data...")

    base_time = datetime.utcnow() - timedelta(days=10)

    # Add baseline data (good performance)
    for i in range(20):
        timestamp = base_time + timedelta(hours=i * 6)
        # Simulate stable API response times around 100ms with some variance
        api_time = 100 + (i % 3) * 5  # 100-110ms
        database_time = 50 + (i % 2) * 3  # 50-53ms

        detector.add_benchmark_result("api_test", "response_time", api_time, timestamp, "production")
        detector.add_benchmark_result("database_test", "query_time", database_time, timestamp, "production")

    # Add recent data with regression
    recent_base = datetime.utcnow() - timedelta(hours=12)
    for i in range(5):
        timestamp = recent_base + timedelta(hours=i * 2)
        # Simulate performance regression - 30% slower
        api_time = 130 + (i % 2) * 5  # 130-135ms (regression!)
        database_time = 52 + (i % 2) * 2  # 52-54ms (stable)

        detector.add_benchmark_result("api_test", "response_time", api_time, timestamp, "production")
        detector.add_benchmark_result("database_test", "query_time", database_time, timestamp, "production")

    # Analyze for regressions
    print("Analyzing for performance regressions...")

    # Check API test
    api_analysis = detector.detect_regression("api_test", "response_time", "production")
    print("📊 API Test Analysis:")
    print(f"   Current value: {api_analysis.current_value:.1f}ms")
    print(f"   Baseline value: {api_analysis.baseline_value:.1f}ms")
    print(f"   Change: {api_analysis.percentage_change:+.1f}%")
    print(f"   Severity: {api_analysis.severity.value}")
    print(f"   Trend: {api_analysis.trend.value}")
    print(f"   Confidence: {api_analysis.confidence_level:.1f}")

    if api_analysis.recommendations:
        print("   Recommendations:")
        for rec in api_analysis.recommendations:
            print(f"     • {rec}")

    # Check database test
    db_analysis = detector.detect_regression("database_test", "query_time", "production")
    print("\n📊 Database Test Analysis:")
    print(f"   Current value: {db_analysis.current_value:.1f}ms")
    print(f"   Baseline value: {db_analysis.baseline_value:.1f}ms")
    print(f"   Change: {db_analysis.percentage_change:+.1f}%")
    print(f"   Severity: {db_analysis.severity.value}")
    print(f"   Trend: {db_analysis.trend.value}")

    # Get overall performance summary
    summary = detector.get_performance_summary()
    print("\n📋 Overall Performance Summary:")
    print(f"   Health score: {summary['health_score']}%")
    print(f"   Total metrics: {summary['total_metrics']}")
    print(f"   Status: {summary['status']}")

    if summary.get("worst_regressions"):
        print("   Worst regressions:")
        for regression in summary["worst_regressions"][:2]:
            print(f"     • {regression['test']}: {regression['change_percent']:+.1f}% ({regression['severity']})")

    print("✅ Example 5 completed\n")


async def example_6_comparison_analysis():
    """Example 6: Benchmark comparison analysis"""

    print("🔄 Example 6: Benchmark Comparison Analysis")
    print("=" * 60)

    # Create benchmark comparator
    comparator = BenchmarkComparator(BenchmarkComparisonConfig())

    # Simulate baseline results (version 1.0)
    baseline_results = {
        "api_response_time": 120.5,
        "database_query_time": 45.2,
        "memory_usage_mb": 256.8,
        "cpu_usage_percent": 35.2,
        "throughput_rps": 850.3,
    }

    # Simulate current results (version 1.1) - some improvements, some regressions
    current_results = {
        "api_response_time": 110.2,  # 8.5% improvement
        "database_query_time": 52.8,  # 16.8% regression
        "memory_usage_mb": 245.1,  # 4.5% improvement
        "cpu_usage_percent": 38.9,  # 10.5% regression
        "throughput_rps": 920.7,  # 8.3% improvement
    }

    print("Comparing current performance against baseline...")

    # Perform comparison
    comparison = comparator.compare_benchmark_sets(baseline_results, current_results, "v1.0_baseline", "v1.1_current")

    # Display results
    print("📊 Comparison Results:")
    print(f"   Overall change: {comparison.overall_performance_change:+.1f}%")
    print(f"   Metrics compared: {comparison.total_metrics_compared}")
    print(f"   Improved: {comparison.improved_metrics}")
    print(f"   Degraded: {comparison.degraded_metrics}")
    print(f"   Unchanged: {comparison.unchanged_metrics}")
    print(f"   Summary: {comparison.summary}")

    if comparison.significant_changes:
        print("\n🔍 Significant Changes:")
        for change in comparison.significant_changes:
            direction = "↑" if change.is_improvement else "↓"
            print(
                f"   {change.metric_name}: {change.old_value:.1f} → {change.new_value:.1f} "
                f"({change.percentage_change:+.1f}%) {direction} {change.significance.value}"
            )

    if comparison.recommendations:
        print("\n💡 Recommendations:")
        for rec in comparison.recommendations:
            print(f"   • {rec}")

    print("✅ Example 6 completed\n")


async def example_7_ci_cd_integration():
    """Example 7: CI/CD Pipeline Integration"""

    print("🔄 Example 7: CI/CD Pipeline Integration")
    print("=" * 60)

    # Create pipeline configuration
    pipeline_config = PipelineConfig(
        pipeline_name="example_performance_pipeline",
        timeout_minutes=5,  # Short timeout for example
        enable_system_metrics=True,
        enable_api_benchmarks=False,  # Disabled for this example
        enable_database_benchmarks=False,  # Disabled for this example
        enable_regression_analysis=True,
        system_metrics_duration=10,  # 10 seconds for example
        output_directory="./example_benchmark_results",
    )

    print(f"Running performance pipeline: {pipeline_config.pipeline_name}")
    print(f"Timeout: {pipeline_config.timeout_minutes} minutes")

    # Create and run pipeline
    runner = PerformancePipelineRunner(pipeline_config)

    try:
        result = await runner.run_pipeline()

        # Display results
        print("📊 Pipeline Results:")
        print(f"   Pipeline ID: {result.pipeline_id}")
        print(f"   Status: {result.status.value}")
        print(f"   Execution time: {result.total_execution_time:.1f}s")
        print(f"   Performance score: {result.overall_performance_score:.1f}%")
        print(f"   Regression detected: {result.regression_detected}")
        print(f"   Critical issues: {len(result.critical_issues)}")

        print("\n📋 Stage Results:")
        for stage in result.stages:
            status_icon = "✅" if stage.status.value == "success" else "❌" if stage.status.value == "failed" else "⏸️"
            print(f"   {stage.stage.value}: {status_icon} ({stage.execution_time:.1f}s)")

            if stage.errors:
                for error in stage.errors[:2]:  # Show first 2 errors
                    print(f"     ❌ {error}")

        if result.recommendations:
            print("\n💡 Recommendations:")
            for rec in result.recommendations[:3]:  # Show first 3
                print(f"   • {rec}")

        if result.artifacts:
            print(f"\n📎 Generated artifacts: {len(result.artifacts)}")
            for artifact in result.artifacts[:3]:  # Show first 3
                print(f"   • {artifact}")

        print("✅ Example 7 completed")

    except Exception as e:
        print(f"❌ Pipeline failed: {e}")

    print()


async def example_8_factory_functions():
    """Example 8: Using factory functions for quick setup"""

    print("🔄 Example 8: Factory Functions")
    print("=" * 60)

    # Create complete benchmark suite
    print("Creating comprehensive benchmark suite...")

    suite = create_benchmark_suite(
        api_base_url="https://httpbin.org",  # Using httpbin for demo
        enable_system_metrics=True,
        enable_regression_detection=True,
    )

    print(f"Created suite with components: {list(suite.keys())}")

    # Run comprehensive benchmark
    print("Running comprehensive benchmark...")

    try:
        results = await run_comprehensive_benchmark(suite, "factory_example")

        print("📊 Comprehensive Benchmark Results:")
        print(f"   Test name: {results['test_name']}")
        print(f"   Timestamp: {results['timestamp']}")
        print(f"   Components tested: {list(results['components'].keys())}")

        # Show system metrics if available
        if "system_metrics" in results["components"]:
            metrics = results["components"]["system_metrics"]
            print("   System metrics:")
            print(f"     CPU: {metrics.get('cpu_percent', 0):.1f}%")
            print(f"     Memory: {metrics.get('memory_percent', 0):.1f}%")

        # Show API results if available
        if "api_benchmark" in results["components"]:
            api_results = results["components"]["api_benchmark"]
            print("   API benchmark:")
            print(f"     Requests per second: {api_results.get('requests_per_second', 0):.2f}")
            print(f"     Average response time: {api_results.get('average_response_time', 0):.3f}s")

        print("✅ Example 8 completed")

    except Exception as e:
        print(f"❌ Comprehensive benchmark failed: {e}")

    finally:
        # Cleanup components
        if "system_metrics" in suite:
            suite["system_metrics"].stop_collection()
        if "database_benchmarker" in suite:
            suite["database_benchmarker"].cleanup()

    print()


async def main():
    """Run all examples"""

    print("🚀 DotMac Performance Benchmarking Suite Examples")
    print("=" * 80)
    print()

    examples = [
        example_1_basic_benchmarking,
        example_2_system_metrics,
        example_3_api_benchmarking,
        example_4_database_benchmarking,
        example_5_regression_detection,
        example_6_comparison_analysis,
        example_7_ci_cd_integration,
        example_8_factory_functions,
    ]

    logger.info("Starting performance benchmarking examples")

    for i, example in enumerate(examples, 1):
        example_name = example.__name__
        try:
            logger.info(f"Running {example_name}")
            await example()
            logger.info(f"Completed {example_name} successfully")
        except Exception as e:
            logger.error(f"Example {example_name} failed: {e}", exc_info=True)
            print(f"❌ Example {i} failed: {e}")
            print()

    logger.info("All performance benchmarking examples completed")
    print("🎉 All examples completed!")
    print()
    print("Next steps:")
    print("• Integrate benchmarking into your CI/CD pipeline")
    print("• Set up automated regression detection")
    print("• Configure performance alerts and notifications")
    print("• Create custom benchmark tests for your specific use cases")


if __name__ == "__main__":
    asyncio.run(main())
