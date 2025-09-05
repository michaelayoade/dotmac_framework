"""
Database Performance and Load Testing Framework

Comprehensive testing utilities for database performance including:
- Load testing with concurrent connections
- Query performance benchmarking
- Connection pool stress testing
- Memory usage monitoring
- Throughput measurement
- Latency analysis
- Resource utilization tracking
"""

import asyncio
import statistics
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import psutil
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from ...api.exception_handlers import standard_exception_handler
from ...core.logging import get_logger

logger = get_logger(__name__)


class PerformanceTestType(str, Enum):
    """Types of performance tests"""

    LOAD_TEST = "load_test"
    STRESS_TEST = "stress_test"
    SPIKE_TEST = "spike_test"
    ENDURANCE_TEST = "endurance_test"
    QUERY_BENCHMARK = "query_benchmark"
    CONNECTION_POOL = "connection_pool"
    MEMORY_USAGE = "memory_usage"
    THROUGHPUT = "throughput"


@dataclass
class PerformanceMetrics:
    """Performance test metrics"""

    test_name: str
    test_type: PerformanceTestType
    duration_seconds: float
    total_operations: int
    successful_operations: int
    failed_operations: int
    operations_per_second: float
    average_response_time: float
    min_response_time: float
    max_response_time: float
    percentile_95_response_time: float
    percentile_99_response_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    active_connections: int
    connection_pool_size: int
    errors: list[str] = field(default_factory=list)


@dataclass
class LoadTestConfig:
    """Configuration for load testing"""

    concurrent_users: int = 10
    duration_seconds: float = 60
    operations_per_user: int = 100
    ramp_up_time: float = 5.0
    ramp_down_time: float = 5.0
    think_time_seconds: float = 0.1


class DatabasePerformanceTester:
    """
    Comprehensive database performance testing framework.

    Features:
    - Load testing with gradual ramp-up
    - Stress testing to find breaking points
    - Query performance benchmarking
    - Connection pool optimization testing
    - Resource utilization monitoring
    - Throughput and latency measurement
    - Performance regression detection
    """

    def __init__(self, database_url: str, pool_size: int = 20, max_overflow: int = 30):
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow

        # Create engine with connection pooling
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,  # 1 hour
            echo=False,
        )

        self.SessionLocal = sessionmaker(bind=self.engine)
        self.test_results: list[PerformanceMetrics] = []
        self._monitoring_active = False
        self._resource_metrics = []

    @standard_exception_handler
    async def run_load_test(
        self,
        model_class: type,
        test_data: list[dict],
        config: LoadTestConfig,
        operations: Optional[list[Callable]] = None,
    ) -> PerformanceMetrics:
        """
        Run comprehensive load test with gradual ramp-up.

        Args:
            model_class: SQLAlchemy model class to test
            test_data: Test data for operations
            config: Load test configuration
            operations: Custom operations to perform (default: CRUD)

        Returns:
            Performance metrics from load test
        """
        logger.info(f"Starting load test for {model_class.__name__}")
        logger.info(f"Config: {config.concurrent_users} users, {config.duration_seconds}s duration")

        # Start resource monitoring
        self._start_resource_monitoring()

        start_time = time.time()
        response_times = []
        successful_ops = 0
        failed_ops = 0
        errors = []

        # Default CRUD operations if none provided
        if operations is None:
            operations = [
                self._create_operation(model_class),
                self._read_operation(model_class),
                self._update_operation(model_class),
                self._delete_operation(model_class),
            ]

        async def user_session(user_id: int, start_delay: float):
            """Simulate individual user session"""
            await asyncio.sleep(start_delay)

            session_successful = 0
            session_failed = 0
            session_response_times = []

            for op_num in range(config.operations_per_user):
                operation_start = time.time()

                try:
                    # Select random operation and data
                    operation = operations[op_num % len(operations)]
                    data = test_data[op_num % len(test_data)] if test_data else {}

                    # Execute operation
                    await self._execute_performance_operation(operation, data)

                    response_time = time.time() - operation_start
                    session_response_times.append(response_time)
                    session_successful += 1

                    # Think time between operations
                    if config.think_time_seconds > 0:
                        await asyncio.sleep(config.think_time_seconds)

                except Exception as e:
                    session_failed += 1
                    errors.append(f"User {user_id}, Op {op_num}: {str(e)}")
                    logger.warning(f"Operation failed for user {user_id}: {e}")

            return session_successful, session_failed, session_response_times

        # Calculate ramp-up delays
        ramp_up_delays = [(i * config.ramp_up_time / config.concurrent_users) for i in range(config.concurrent_users)]

        # Start user sessions
        tasks = [user_session(i, delay) for i, delay in enumerate(ramp_up_delays)]

        # Wait for completion or timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=config.duration_seconds + config.ramp_up_time + config.ramp_down_time + 30,
            )

            # Aggregate results
            for result in results:
                if isinstance(result, tuple):
                    user_successful, user_failed, user_response_times = result
                    successful_ops += user_successful
                    failed_ops += user_failed
                    response_times.extend(user_response_times)
                elif isinstance(result, Exception):
                    failed_ops += config.operations_per_user
                    errors.append(f"User session failed: {str(result)}")

        except asyncio.TimeoutError:
            errors.append("Load test timed out")
            logger.warning("Load test timed out")

        # Stop resource monitoring
        resource_metrics = self._stop_resource_monitoring()

        execution_time = time.time() - start_time
        total_operations = successful_ops + failed_ops

        # Calculate performance metrics
        metrics = PerformanceMetrics(
            test_name=f"load_test_{model_class.__name__}",
            test_type=PerformanceTestType.LOAD_TEST,
            duration_seconds=execution_time,
            total_operations=total_operations,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            operations_per_second=total_operations / execution_time if execution_time > 0 else 0,
            average_response_time=statistics.mean(response_times) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            max_response_time=max(response_times) if response_times else 0,
            percentile_95_response_time=self._calculate_percentile(response_times, 95),
            percentile_99_response_time=self._calculate_percentile(response_times, 99),
            memory_usage_mb=resource_metrics.get("max_memory_mb", 0),
            cpu_usage_percent=resource_metrics.get("avg_cpu_percent", 0),
            active_connections=self._get_active_connections(),
            connection_pool_size=self.pool_size,
            errors=errors[:50],  # Limit error list size
        )

        self.test_results.append(metrics)
        logger.info(f"Load test completed: {successful_ops}/{total_operations} successful ops")
        return metrics

    @standard_exception_handler
    async def run_stress_test(
        self,
        model_class: type,
        test_data: list[dict],
        max_users: int = 100,
        increment: int = 10,
        duration_per_level: float = 30,
    ) -> list[PerformanceMetrics]:
        """
        Run stress test to find system breaking point.

        Gradually increases load until system fails or performance degrades.
        """
        logger.info(f"Starting stress test for {model_class.__name__}")

        stress_results = []
        current_users = increment

        while current_users <= max_users:
            logger.info(f"Stress testing with {current_users} concurrent users")

            config = LoadTestConfig(
                concurrent_users=current_users,
                duration_seconds=duration_per_level,
                operations_per_user=50,
                ramp_up_time=5.0,
                think_time_seconds=0.05,
            )

            try:
                metrics = await self.run_load_test(model_class, test_data, config)
                metrics.test_name = f"stress_test_{current_users}_users"
                metrics.test_type = PerformanceTestType.STRESS_TEST
                stress_results.append(metrics)

                # Check for failure conditions
                failure_rate = (
                    metrics.failed_operations / metrics.total_operations if metrics.total_operations > 0 else 0
                )
                if failure_rate > 0.1:  # 10% failure rate
                    logger.warning(f"High failure rate ({failure_rate:.2%}) at {current_users} users")
                    break

                if metrics.percentile_95_response_time > 5.0:  # 5 second response time
                    logger.warning(
                        f"High response time ({metrics.percentile_95_response_time:.2f}s) at {current_users} users"
                    )
                    break

            except Exception as e:
                logger.error(f"Stress test failed at {current_users} users: {e}")
                break

            current_users += increment

        logger.info(f"Stress test completed. Maximum sustainable load: {current_users - increment} users")
        return stress_results

    @standard_exception_handler
    async def benchmark_queries(
        self,
        queries: list[tuple[str, str]],  # (name, query)
        iterations: int = 1000,
    ) -> dict[str, PerformanceMetrics]:
        """
        Benchmark query performance.

        Args:
            queries: List of (name, query) tuples to benchmark
            iterations: Number of iterations per query

        Returns:
            Dictionary of query performance metrics
        """
        logger.info(f"Benchmarking {len(queries)} queries with {iterations} iterations each")

        benchmark_results = {}

        for query_name, query_sql in queries:
            logger.info(f"Benchmarking query: {query_name}")

            response_times = []
            successful_ops = 0
            failed_ops = 0
            errors = []

            start_time = time.time()

            for i in range(iterations):
                operation_start = time.time()

                try:
                    with self.SessionLocal() as session:
                        result = session.execute(text(query_sql))
                        result.fetchall()  # Ensure full result retrieval

                    response_time = time.time() - operation_start
                    response_times.append(response_time)
                    successful_ops += 1

                except Exception as e:
                    failed_ops += 1
                    errors.append(f"Iteration {i}: {str(e)}")
                    if len(errors) < 10:  # Log first few errors
                        logger.warning(f"Query {query_name} failed on iteration {i}: {e}")

            execution_time = time.time() - start_time
            total_operations = successful_ops + failed_ops

            metrics = PerformanceMetrics(
                test_name=f"query_benchmark_{query_name}",
                test_type=PerformanceTestType.QUERY_BENCHMARK,
                duration_seconds=execution_time,
                total_operations=total_operations,
                successful_operations=successful_ops,
                failed_operations=failed_ops,
                operations_per_second=total_operations / execution_time if execution_time > 0 else 0,
                average_response_time=statistics.mean(response_times) if response_times else 0,
                min_response_time=min(response_times) if response_times else 0,
                max_response_time=max(response_times) if response_times else 0,
                percentile_95_response_time=self._calculate_percentile(response_times, 95),
                percentile_99_response_time=self._calculate_percentile(response_times, 99),
                memory_usage_mb=0,  # Not tracked for query benchmarks
                cpu_usage_percent=0,
                active_connections=1,
                connection_pool_size=self.pool_size,
                errors=errors[:10],
            )

            benchmark_results[query_name] = metrics
            self.test_results.append(metrics)

        return benchmark_results

    @standard_exception_handler
    async def test_connection_pool_performance(
        self,
        concurrent_connections: int = 50,
        operations_per_connection: int = 10,
        pool_sizes: Optional[list[int]] = None,
    ) -> list[PerformanceMetrics]:
        """Test connection pool performance with different configurations"""

        if pool_sizes is None:
            pool_sizes = [5, 10, 20, 30]

        pool_results = []

        for pool_size in pool_sizes:
            logger.info(f"Testing connection pool with size {pool_size}")

            # Create new engine with specific pool size
            test_engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=pool_size,
                pool_pre_ping=True,
                echo=False,
            )

            TestSessionLocal = sessionmaker(bind=test_engine)

            async def connection_worker(worker_id: int):
                """Worker that performs database operations"""
                worker_times = []
                worker_successful = 0
                worker_failed = 0

                for _op in range(operations_per_connection):
                    op_start = time.time()

                    try:
                        with TestSessionLocal() as session:
                            # Simple query to test connection acquisition
                            result = session.execute(text("SELECT 1"))
                            result.fetchone()

                        worker_times.append(time.time() - op_start)
                        worker_successful += 1

                    except Exception as e:
                        worker_failed += 1
                        logger.warning(f"Connection worker {worker_id} failed: {e}")

                return worker_successful, worker_failed, worker_times

            # Start monitoring
            self._start_resource_monitoring()
            start_time = time.time()

            # Run concurrent connections
            tasks = [connection_worker(i) for i in range(concurrent_connections)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Stop monitoring
            resource_metrics = self._stop_resource_monitoring()
            execution_time = time.time() - start_time

            # Aggregate results
            total_successful = 0
            total_failed = 0
            all_response_times = []

            for result in results:
                if isinstance(result, tuple):
                    successful, failed, times = result
                    total_successful += successful
                    total_failed += failed
                    all_response_times.extend(times)

            total_operations = total_successful + total_failed

            metrics = PerformanceMetrics(
                test_name=f"connection_pool_{pool_size}",
                test_type=PerformanceTestType.CONNECTION_POOL,
                duration_seconds=execution_time,
                total_operations=total_operations,
                successful_operations=total_successful,
                failed_operations=total_failed,
                operations_per_second=total_operations / execution_time if execution_time > 0 else 0,
                average_response_time=statistics.mean(all_response_times) if all_response_times else 0,
                min_response_time=min(all_response_times) if all_response_times else 0,
                max_response_time=max(all_response_times) if all_response_times else 0,
                percentile_95_response_time=self._calculate_percentile(all_response_times, 95),
                percentile_99_response_time=self._calculate_percentile(all_response_times, 99),
                memory_usage_mb=resource_metrics.get("max_memory_mb", 0),
                cpu_usage_percent=resource_metrics.get("avg_cpu_percent", 0),
                active_connections=concurrent_connections,
                connection_pool_size=pool_size,
            )

            pool_results.append(metrics)
            self.test_results.append(metrics)

            # Clean up test engine
            test_engine.dispose()

        return pool_results

    def _create_operation(self, model_class: type) -> Callable:
        """Create a database insert operation"""

        def create_op(data: dict):
            with self.SessionLocal() as session:
                record = model_class(**data)
                session.add(record)
                session.commit()
                return record.id if hasattr(record, "id") else True

        return create_op

    def _read_operation(self, model_class: type) -> Callable:
        """Create a database select operation"""

        def read_op(data: dict):
            with self.SessionLocal() as session:
                return session.query(model_class).first()

        return read_op

    def _update_operation(self, model_class: type) -> Callable:
        """Create a database update operation"""

        def update_op(data: dict):
            with self.SessionLocal() as session:
                record = session.query(model_class).first()
                if record and data:
                    for key, value in data.items():
                        if hasattr(record, key):
                            setattr(record, key, value)
                    session.commit()
                return record

        return update_op

    def _delete_operation(self, model_class: type) -> Callable:
        """Create a database delete operation"""

        def delete_op(data: dict):
            with self.SessionLocal() as session:
                record = session.query(model_class).first()
                if record:
                    session.delete(record)
                    session.commit()
                return True

        return delete_op

    async def _execute_performance_operation(self, operation: Callable, data: dict):
        """Execute a performance operation"""
        if asyncio.iscoroutinefunction(operation):
            return await operation(data)
        else:
            return operation(data)

    def _start_resource_monitoring(self):
        """Start monitoring system resources"""
        self._monitoring_active = True
        self._resource_metrics = []

        def monitor():
            while self._monitoring_active:
                try:
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory_info = psutil.virtual_memory()

                    self._resource_metrics.append(
                        {
                            "timestamp": time.time(),
                            "cpu_percent": cpu_percent,
                            "memory_mb": memory_info.used / (1024 * 1024),
                        }
                    )

                except Exception as e:
                    logger.warning(f"Resource monitoring error: {e}")

                time.sleep(1)

        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()

    def _stop_resource_monitoring(self) -> dict[str, float]:
        """Stop resource monitoring and return metrics"""
        self._monitoring_active = False

        if self._resource_metrics:
            cpu_values = [m["cpu_percent"] for m in self._resource_metrics]
            memory_values = [m["memory_mb"] for m in self._resource_metrics]

            return {
                "avg_cpu_percent": statistics.mean(cpu_values),
                "max_cpu_percent": max(cpu_values),
                "avg_memory_mb": statistics.mean(memory_values),
                "max_memory_mb": max(memory_values),
            }

        return {"avg_cpu_percent": 0, "max_cpu_percent": 0, "avg_memory_mb": 0, "max_memory_mb": 0}

    def _get_active_connections(self) -> int:
        """Get number of active database connections"""
        try:
            pool = self.engine.pool
            return pool.checkedout()
        except AttributeError:
            return 0

    def _calculate_percentile(self, values: list[float], percentile: int) -> float:
        """Calculate percentile value"""
        if not values:
            return 0

        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        if index >= len(sorted_values):
            index = len(sorted_values) - 1
        return sorted_values[index]

    def get_performance_summary(self) -> dict[str, Any]:
        """Get summary of all performance test results"""

        if not self.test_results:
            return {"total": 0, "summary": "No performance tests run"}

        # Overall statistics
        total_tests = len(self.test_results)
        total_operations = sum(r.total_operations for r in self.test_results)
        total_successful = sum(r.successful_operations for r in self.test_results)

        # Performance metrics
        avg_ops_per_second = statistics.mean([r.operations_per_second for r in self.test_results])
        avg_response_time = statistics.mean([r.average_response_time for r in self.test_results])

        # Break down by test type
        type_breakdown = {}
        for result in self.test_results:
            test_type = result.test_type.value
            if test_type not in type_breakdown:
                type_breakdown[test_type] = {"count": 0, "avg_ops_per_sec": [], "avg_response_time": []}

            type_breakdown[test_type]["count"] += 1
            type_breakdown[test_type]["avg_ops_per_sec"].append(result.operations_per_second)
            type_breakdown[test_type]["avg_response_time"].append(result.average_response_time)

        # Calculate averages for each type
        for _, data in type_breakdown.items():
            data["avg_ops_per_sec"] = statistics.mean(data["avg_ops_per_sec"]) if data["avg_ops_per_sec"] else 0
            data["avg_response_time"] = statistics.mean(data["avg_response_time"]) if data["avg_response_time"] else 0

        return {
            "total_tests": total_tests,
            "total_operations": total_operations,
            "total_successful": total_successful,
            "success_rate": (total_successful / total_operations * 100) if total_operations > 0 else 0,
            "average_ops_per_second": avg_ops_per_second,
            "average_response_time": avg_response_time,
            "test_type_breakdown": type_breakdown,
        }


# Convenience functions


async def quick_performance_test(
    database_url: str, model_class: type, test_data: list[dict], concurrent_users: int = 10, duration_seconds: int = 30
) -> dict[str, Any]:
    """
    Quick performance test for a model class.

    Returns basic performance metrics and recommendations.
    """
    tester = DatabasePerformanceTester(database_url)

    config = LoadTestConfig(
        concurrent_users=concurrent_users, duration_seconds=duration_seconds, operations_per_user=20
    )

    metrics = await tester.run_load_test(model_class, test_data, config)

    # Generate performance recommendations
    recommendations = []

    if metrics.operations_per_second < 100:
        recommendations.append("Consider adding database indexes")

    if metrics.average_response_time > 0.5:
        recommendations.append("Query optimization may be needed")

    if metrics.failed_operations > 0:
        recommendations.append("Investigate connection pool configuration")

    return {"metrics": metrics, "recommendations": recommendations, "summary": tester.get_performance_summary()}
