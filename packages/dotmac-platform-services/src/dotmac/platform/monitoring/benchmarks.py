"""
Benchmarking and performance tracking for platform monitoring.

Provides comprehensive benchmarking capabilities including:
- Performance benchmark execution
- Results collection and analysis
- Benchmark suite management
- Integration with monitoring systems
"""

import asyncio
import statistics
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


class BenchmarkStatus(str, Enum):
    """Benchmark execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BenchmarkType(str, Enum):
    """Types of benchmarks."""
    PERFORMANCE = "performance"
    LOAD = "load"
    STRESS = "stress"
    ENDURANCE = "endurance"
    SPIKE = "spike"
    MEMORY = "memory"
    CPU = "cpu"
    NETWORK = "network"
    DATABASE = "database"


@dataclass
class BenchmarkMetric:
    """Individual benchmark metric."""
    name: str
    value: Union[int, float]
    unit: str
    category: str = "general"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class BenchmarkResult:
    """Results from a benchmark execution."""
    id: str
    name: str
    benchmark_type: BenchmarkType
    status: BenchmarkStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[timedelta] = None
    metrics: List[BenchmarkMetric] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.end_time and self.start_time:
            self.duration = self.end_time - self.start_time

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        if self.duration:
            return self.duration.total_seconds()
        return 0.0

    def add_metric(self, name: str, value: Union[int, float], unit: str, **kwargs):
        """Add a metric to the results."""
        metric = BenchmarkMetric(name=name, value=value, unit=unit, **kwargs)
        self.metrics.append(metric)

    def get_metric(self, name: str) -> Optional[BenchmarkMetric]:
        """Get a specific metric by name."""
        for metric in self.metrics:
            if metric.name == name:
                return metric
        return None

    def get_metrics_by_category(self, category: str) -> List[BenchmarkMetric]:
        """Get all metrics in a specific category."""
        return [metric for metric in self.metrics if metric.category == category]


class PerformanceBenchmark(ABC):
    """Abstract base class for performance benchmarks."""

    def __init__(self, name: str, benchmark_type: BenchmarkType, metadata: Optional[Dict[str, Any]] = None):
        self.name = name
        self.benchmark_type = benchmark_type
        self.metadata = metadata or {}
        self.logger = logger.bind(benchmark=name)

    @abstractmethod
    async def setup(self) -> bool:
        """Setup benchmark environment."""
        pass

    @abstractmethod
    async def execute(self) -> Dict[str, Any]:
        """Execute the benchmark and return raw results."""
        pass

    @abstractmethod
    async def teardown(self):
        """Cleanup benchmark environment."""
        pass

    async def run(self) -> BenchmarkResult:
        """Run the complete benchmark lifecycle."""
        result = BenchmarkResult(
            id=str(uuid4()),
            name=self.name,
            benchmark_type=self.benchmark_type,
            status=BenchmarkStatus.PENDING,
            start_time=datetime.utcnow(),
            metadata=self.metadata.copy()
        )

        try:
            self.logger.info("Starting benchmark setup")
            result.status = BenchmarkStatus.RUNNING

            # Setup
            setup_success = await self.setup()
            if not setup_success:
                raise Exception("Benchmark setup failed")

            # Execute
            self.logger.info("Executing benchmark")
            raw_results = await self.execute()

            # Process results
            await self._process_results(result, raw_results)

            result.status = BenchmarkStatus.COMPLETED
            result.end_time = datetime.utcnow()

            self.logger.info(
                "Benchmark completed successfully",
                duration_seconds=result.duration_seconds,
                metrics_count=len(result.metrics)
            )

        except asyncio.CancelledError:
            result.status = BenchmarkStatus.CANCELLED
            result.end_time = datetime.utcnow()
            result.error_message = "Benchmark was cancelled"
            self.logger.warning("Benchmark cancelled")
        except Exception as e:
            result.status = BenchmarkStatus.FAILED
            result.end_time = datetime.utcnow()
            result.error_message = str(e)
            self.logger.error("Benchmark failed", error=str(e))
        finally:
            try:
                await self.teardown()
            except Exception as e:
                self.logger.error("Benchmark teardown failed", error=str(e))

        return result

    async def _process_results(self, result: BenchmarkResult, raw_results: Dict[str, Any]):
        """Process raw benchmark results into structured metrics."""
        # Default processing - can be overridden by subclasses
        for key, value in raw_results.items():
            if isinstance(value, (int, float)):
                result.add_metric(key, value, "units", category="benchmark")


class CPUBenchmark(PerformanceBenchmark):
    """CPU performance benchmark."""

    def __init__(self, duration_seconds: int = 10, threads: int = 1):
        super().__init__("CPU Benchmark", BenchmarkType.CPU)
        self.duration_seconds = duration_seconds
        self.threads = threads

    async def setup(self) -> bool:
        """Setup CPU benchmark."""
        self.logger.info(
            "Setting up CPU benchmark",
            duration=self.duration_seconds,
            threads=self.threads
        )
        return True

    async def execute(self) -> Dict[str, Any]:
        """Execute CPU intensive operations."""
        start_time = time.perf_counter()
        iterations = 0

        end_time = start_time + self.duration_seconds

        # CPU intensive loop
        while time.perf_counter() < end_time:
            # Simple CPU work
            for _ in range(1000):
                _ = sum(i * i for i in range(100))
            iterations += 1000

        execution_time = time.perf_counter() - start_time
        operations_per_second = iterations / execution_time

        return {
            "iterations": iterations,
            "execution_time_seconds": execution_time,
            "operations_per_second": operations_per_second,
            "threads_used": self.threads
        }

    async def teardown(self):
        """Cleanup CPU benchmark."""
        self.logger.info("CPU benchmark teardown complete")


class MemoryBenchmark(PerformanceBenchmark):
    """Memory allocation and access benchmark."""

    def __init__(self, allocation_mb: int = 100, iterations: int = 1000):
        super().__init__("Memory Benchmark", BenchmarkType.MEMORY)
        self.allocation_mb = allocation_mb
        self.iterations = iterations
        self.allocated_data = []

    async def setup(self) -> bool:
        """Setup memory benchmark."""
        self.logger.info(
            "Setting up memory benchmark",
            allocation_mb=self.allocation_mb,
            iterations=self.iterations
        )
        return True

    async def execute(self) -> Dict[str, Any]:
        """Execute memory operations."""
        # Allocation benchmark
        allocation_start = time.perf_counter()

        for _ in range(self.iterations):
            # Allocate 1KB chunks
            data = bytearray(1024)
            self.allocated_data.append(data)

        allocation_time = time.perf_counter() - allocation_start

        # Access benchmark
        access_start = time.perf_counter()

        total_bytes_accessed = 0
        for data in self.allocated_data:
            # Simple access pattern
            for i in range(0, len(data), 64):  # Every 64th byte
                data[i] = i % 256
                total_bytes_accessed += 1

        access_time = time.perf_counter() - access_start

        return {
            "allocated_chunks": len(self.allocated_data),
            "allocated_mb": len(self.allocated_data) / 1024,  # Convert KB to MB
            "allocation_time_seconds": allocation_time,
            "access_time_seconds": access_time,
            "bytes_accessed": total_bytes_accessed,
            "allocation_rate_mb_per_second": (len(self.allocated_data) / 1024) / allocation_time,
            "access_rate_mb_per_second": (total_bytes_accessed / 1024 / 1024) / access_time
        }

    async def teardown(self):
        """Cleanup memory benchmark."""
        self.allocated_data.clear()
        self.logger.info("Memory benchmark teardown complete")


class NetworkBenchmark(PerformanceBenchmark):
    """Network latency and throughput benchmark."""

    def __init__(self, target_host: str = "8.8.8.8", port: int = 53, iterations: int = 10):
        super().__init__("Network Benchmark", BenchmarkType.NETWORK)
        self.target_host = target_host
        self.port = port
        self.iterations = iterations

    async def setup(self) -> bool:
        """Setup network benchmark."""
        self.logger.info(
            "Setting up network benchmark",
            target=f"{self.target_host}:{self.port}",
            iterations=self.iterations
        )
        return True

    async def execute(self) -> Dict[str, Any]:
        """Execute network operations."""
        latencies = []
        successful_connections = 0

        for _ in range(self.iterations):
            try:
                start_time = time.perf_counter()

                # Simple TCP connection test
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.target_host, self.port),
                    timeout=5.0
                )

                latency = time.perf_counter() - start_time
                latencies.append(latency * 1000)  # Convert to milliseconds
                successful_connections += 1

                writer.close()
                await writer.wait_closed()

            except Exception as e:
                self.logger.warning("Connection failed", error=str(e))

        if latencies:
            avg_latency = statistics.mean(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            median_latency = statistics.median(latencies)
        else:
            avg_latency = min_latency = max_latency = median_latency = 0

        return {
            "total_attempts": self.iterations,
            "successful_connections": successful_connections,
            "success_rate": successful_connections / self.iterations,
            "average_latency_ms": avg_latency,
            "min_latency_ms": min_latency,
            "max_latency_ms": max_latency,
            "median_latency_ms": median_latency
        }

    async def teardown(self):
        """Cleanup network benchmark."""
        self.logger.info("Network benchmark teardown complete")


@dataclass
class BenchmarkSuiteConfig:
    """Configuration for benchmark suite."""
    name: str
    description: str = ""
    timeout_seconds: int = 300
    parallel_execution: bool = False
    retry_failed: bool = False
    retry_count: int = 1


class BenchmarkSuite:
    """Collection of benchmarks that can be run together."""

    def __init__(self, config: BenchmarkSuiteConfig):
        self.config = config
        self.benchmarks: List[PerformanceBenchmark] = []
        self.results: List[BenchmarkResult] = []
        self.logger = logger.bind(suite=config.name)

    def add_benchmark(self, benchmark: PerformanceBenchmark):
        """Add a benchmark to the suite."""
        self.benchmarks.append(benchmark)
        self.logger.info("Benchmark added to suite", benchmark=benchmark.name)

    async def run_all(self) -> List[BenchmarkResult]:
        """Run all benchmarks in the suite."""
        self.logger.info(
            "Starting benchmark suite execution",
            benchmark_count=len(self.benchmarks),
            parallel=self.config.parallel_execution
        )

        self.results.clear()

        if self.config.parallel_execution:
            results = await self._run_parallel()
        else:
            results = await self._run_sequential()

        self.results.extend(results)

        successful = sum(1 for r in results if r.status == BenchmarkStatus.COMPLETED)
        self.logger.info(
            "Benchmark suite execution completed",
            total=len(results),
            successful=successful,
            failed=len(results) - successful
        )

        return results

    async def _run_sequential(self) -> List[BenchmarkResult]:
        """Run benchmarks sequentially."""
        results = []

        for benchmark in self.benchmarks:
            try:
                result = await asyncio.wait_for(
                    benchmark.run(),
                    timeout=self.config.timeout_seconds
                )
                results.append(result)

                # Retry logic for failed benchmarks
                if (result.status == BenchmarkStatus.FAILED and
                    self.config.retry_failed and
                    self.config.retry_count > 0):

                    for retry in range(self.config.retry_count):
                        self.logger.info(
                            "Retrying failed benchmark",
                            benchmark=benchmark.name,
                            retry=retry + 1
                        )
                        retry_result = await asyncio.wait_for(
                            benchmark.run(),
                            timeout=self.config.timeout_seconds
                        )
                        if retry_result.status == BenchmarkStatus.COMPLETED:
                            results[-1] = retry_result  # Replace failed result
                            break

            except asyncio.TimeoutError:
                self.logger.error(
                    "Benchmark timed out",
                    benchmark=benchmark.name,
                    timeout=self.config.timeout_seconds
                )
                # Create timeout result
                timeout_result = BenchmarkResult(
                    id=str(uuid4()),
                    name=benchmark.name,
                    benchmark_type=benchmark.benchmark_type,
                    status=BenchmarkStatus.FAILED,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    error_message="Benchmark execution timed out"
                )
                results.append(timeout_result)

        return results

    async def _run_parallel(self) -> List[BenchmarkResult]:
        """Run benchmarks in parallel."""
        async def run_with_timeout(benchmark):
            try:
                return await asyncio.wait_for(
                    benchmark.run(),
                    timeout=self.config.timeout_seconds
                )
            except asyncio.TimeoutError:
                return BenchmarkResult(
                    id=str(uuid4()),
                    name=benchmark.name,
                    benchmark_type=benchmark.benchmark_type,
                    status=BenchmarkStatus.FAILED,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    error_message="Benchmark execution timed out"
                )

        tasks = [run_with_timeout(benchmark) for benchmark in self.benchmarks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = BenchmarkResult(
                    id=str(uuid4()),
                    name=self.benchmarks[i].name,
                    benchmark_type=self.benchmarks[i].benchmark_type,
                    status=BenchmarkStatus.FAILED,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    error_message=str(result)
                )
                final_results.append(error_result)
            else:
                final_results.append(result)

        return final_results

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for the benchmark suite results."""
        if not self.results:
            return {}

        total = len(self.results)
        completed = sum(1 for r in self.results if r.status == BenchmarkStatus.COMPLETED)
        failed = sum(1 for r in self.results if r.status == BenchmarkStatus.FAILED)
        cancelled = sum(1 for r in self.results if r.status == BenchmarkStatus.CANCELLED)

        durations = [r.duration_seconds for r in self.results if r.duration_seconds > 0]
        if durations:
            avg_duration = statistics.mean(durations)
            min_duration = min(durations)
            max_duration = max(durations)
        else:
            avg_duration = min_duration = max_duration = 0

        return {
            "total_benchmarks": total,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "success_rate": completed / total if total > 0 else 0,
            "average_duration_seconds": avg_duration,
            "min_duration_seconds": min_duration,
            "max_duration_seconds": max_duration,
            "total_metrics": sum(len(r.metrics) for r in self.results)
        }


class BenchmarkManager:
    """Central manager for coordinating benchmark execution and results."""

    def __init__(self):
        self.active_benchmarks: Dict[str, asyncio.Task] = {}
        self.benchmark_history: List[BenchmarkResult] = []
        self.suites: Dict[str, BenchmarkSuite] = {}
        self.logger = logger.bind(component="benchmark_manager")

    async def run_benchmark(self, benchmark: PerformanceBenchmark) -> BenchmarkResult:
        """Run a single benchmark."""
        task_id = str(uuid4())

        try:
            self.logger.info("Starting benchmark", benchmark=benchmark.name, task_id=task_id)

            # Create and store task
            task = asyncio.create_task(benchmark.run())
            self.active_benchmarks[task_id] = task

            # Wait for completion
            result = await task
            self.benchmark_history.append(result)

            self.logger.info(
                "Benchmark completed",
                benchmark=benchmark.name,
                task_id=task_id,
                status=result.status.value
            )

            return result

        except Exception as e:
            self.logger.error(
                "Benchmark execution failed",
                benchmark=benchmark.name,
                task_id=task_id,
                error=str(e)
            )
            raise
        finally:
            # Cleanup
            self.active_benchmarks.pop(task_id, None)

    def register_suite(self, suite: BenchmarkSuite):
        """Register a benchmark suite."""
        self.suites[suite.config.name] = suite
        self.logger.info("Benchmark suite registered", suite=suite.config.name)

    async def run_suite(self, suite_name: str) -> List[BenchmarkResult]:
        """Run a registered benchmark suite."""
        if suite_name not in self.suites:
            raise ValueError(f"Benchmark suite '{suite_name}' not found")

        suite = self.suites[suite_name]
        results = await suite.run_all()
        self.benchmark_history.extend(results)

        return results

    def get_active_benchmarks(self) -> List[str]:
        """Get list of currently running benchmarks."""
        return list(self.active_benchmarks.keys())

    async def cancel_benchmark(self, task_id: str) -> bool:
        """Cancel a running benchmark."""
        if task_id in self.active_benchmarks:
            task = self.active_benchmarks[task_id]
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            self.logger.info("Benchmark cancelled", task_id=task_id)
            return True

        return False

    def get_benchmark_history(
        self,
        limit: Optional[int] = None,
        benchmark_type: Optional[BenchmarkType] = None,
        status: Optional[BenchmarkStatus] = None
    ) -> List[BenchmarkResult]:
        """Get benchmark execution history with optional filters."""
        history = self.benchmark_history

        if benchmark_type:
            history = [r for r in history if r.benchmark_type == benchmark_type]

        if status:
            history = [r for r in history if r.status == status]

        # Sort by start time (newest first)
        history.sort(key=lambda r: r.start_time, reverse=True)

        if limit:
            history = history[:limit]

        return history

    def clear_history(self):
        """Clear benchmark execution history."""
        self.benchmark_history.clear()
        self.logger.info("Benchmark history cleared")
