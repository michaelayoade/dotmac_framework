"""
Performance Benchmarking Manager

Central orchestrator for comprehensive performance benchmarking including:
- System-wide performance metrics collection
- API endpoint benchmarking
- Database query profiling
- Memory and CPU monitoring
- Benchmark comparison and regression detection
"""

import asyncio
import time
import json
import statistics
from typing import Any, Dict, List, Optional, Union, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
from pathlib import Path
import uuid

from ...core.logging import get_logger
from ..utils import standard_exception_handler
from ...tenant.identity import TenantContext

logger = get_logger(__name__)


class BenchmarkType(str, Enum):
    """Types of performance benchmarks"""
    API_ENDPOINT = "api_endpoint"
    DATABASE_QUERY = "database_query"
    SYSTEM_RESOURCE = "system_resource"
    MEMORY_USAGE = "memory_usage"
    CPU_PERFORMANCE = "cpu_performance"
    NETWORK_LATENCY = "network_latency"
    CUSTOM = "custom"


class BenchmarkStatus(str, Enum):
    """Benchmark execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BenchmarkMetrics:
    """Performance metrics from benchmark execution"""
    benchmark_id: str
    benchmark_type: BenchmarkType
    name: str
    description: str
    
    # Timing metrics
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    
    # Performance metrics
    operations_count: int
    operations_per_second: float
    average_response_time: float
    min_response_time: float
    max_response_time: float
    percentile_50: float
    percentile_95: float
    percentile_99: float
    
    # Resource metrics
    peak_memory_mb: float = 0.0
    average_cpu_percent: float = 0.0
    peak_cpu_percent: float = 0.0
    
    # Quality metrics
    success_rate: float = 100.0
    error_count: int = 0
    errors: List[str] = field(default_factory=list)
    
    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_measurements: List[float] = field(default_factory=list)


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark execution"""
    name: str
    benchmark_type: BenchmarkType
    description: str = ""
    
    # Execution parameters
    iterations: int = 1000
    concurrent_workers: int = 1
    warmup_iterations: int = 10
    cooldown_seconds: float = 1.0
    timeout_seconds: float = 300.0
    
    # Resource monitoring
    monitor_memory: bool = True
    monitor_cpu: bool = True
    monitor_network: bool = False
    
    # Data collection
    collect_raw_data: bool = True
    store_results: bool = True
    
    # Tenant context
    tenant_context: Optional[TenantContext] = None
    
    # Custom parameters
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkSuite:
    """Collection of related benchmarks"""
    name: str
    description: str
    benchmarks: List[BenchmarkConfig]
    parallel_execution: bool = False
    suite_metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceBenchmarkManager:
    """
    Central manager for performance benchmarking across the entire system.
    
    Features:
    - Unified benchmark execution and management
    - Resource monitoring during benchmark runs
    - Results comparison and regression detection
    - Automated benchmark scheduling
    - Multi-tenant benchmark isolation
    - Performance baseline establishment
    """
    
    def __init__(self, results_storage_path: Optional[str] = None):
        self.results_storage_path = Path(results_storage_path or "benchmark_results")
        self.results_storage_path.mkdir(parents=True, exist_ok=True)
        
        self.active_benchmarks: Dict[str, BenchmarkStatus] = {}
        self.benchmark_history: List[BenchmarkMetrics] = []
        self.baselines: Dict[str, BenchmarkMetrics] = {}
        
        # Resource monitoring
        self._resource_monitors: Dict[str, Any] = {}
        self._monitoring_active = False
    
    @standard_exception_handler
    async def execute_benchmark(
        self,
        config: BenchmarkConfig,
        benchmark_function: Callable,
        *args,
        **kwargs
    ) -> BenchmarkMetrics:
        """
        Execute a single performance benchmark.
        
        Args:
            config: Benchmark configuration
            benchmark_function: Function to benchmark
            *args, **kwargs: Arguments for benchmark function
            
        Returns:
            Detailed performance metrics
        """
        benchmark_id = str(uuid.uuid4())
        logger.info(f"Starting benchmark: {config.name} (ID: {benchmark_id})")
        
        self.active_benchmarks[benchmark_id] = BenchmarkStatus.RUNNING
        
        try:
            # Start resource monitoring
            await self._start_resource_monitoring(benchmark_id, config)
            
            # Execute warmup iterations
            if config.warmup_iterations > 0:
                logger.debug(f"Warming up with {config.warmup_iterations} iterations")
                await self._execute_warmup(benchmark_function, config, *args, **kwargs)
            
            # Execute main benchmark
            start_time = datetime.now(timezone.utc)
            measurements = await self._execute_benchmark_iterations(
                benchmark_function, config, *args, **kwargs
            )
            end_time = datetime.now(timezone.utc)
            
            # Stop resource monitoring and collect metrics
            resource_metrics = await self._stop_resource_monitoring(benchmark_id)
            
            # Calculate performance metrics
            metrics = self._calculate_metrics(
                benchmark_id, config, start_time, end_time, measurements, resource_metrics
            )
            
            # Store results
            if config.store_results:
                await self._store_benchmark_results(metrics)
            
            self.benchmark_history.append(metrics)
            self.active_benchmarks[benchmark_id] = BenchmarkStatus.COMPLETED
            
            logger.info(f"✅ Benchmark completed: {config.name}")
            logger.info(f"   Operations/sec: {metrics.operations_per_second:.2f}")
            logger.info(f"   Avg response time: {metrics.average_response_time:.4f}s")
            logger.info(f"   95th percentile: {metrics.percentile_95:.4f}s")
            
            return metrics
        
        except Exception as e:
            logger.error(f"Benchmark {config.name} failed: {e}")
            self.active_benchmarks[benchmark_id] = BenchmarkStatus.FAILED
            
            # Create error metrics
            error_metrics = BenchmarkMetrics(
                benchmark_id=benchmark_id,
                benchmark_type=config.benchmark_type,
                name=config.name,
                description=config.description,
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                duration_seconds=0.0,
                operations_count=0,
                operations_per_second=0.0,
                average_response_time=0.0,
                min_response_time=0.0,
                max_response_time=0.0,
                percentile_50=0.0,
                percentile_95=0.0,
                percentile_99=0.0,
                error_count=1,
                errors=[str(e)],
                success_rate=0.0
            )
            
            return error_metrics
    
    @standard_exception_handler
    async def execute_benchmark_suite(
        self,
        suite: BenchmarkSuite,
        benchmark_functions: Dict[str, Callable]
    ) -> Dict[str, BenchmarkMetrics]:
        """
        Execute a complete benchmark suite.
        
        Args:
            suite: Benchmark suite configuration
            benchmark_functions: Dictionary mapping benchmark names to functions
            
        Returns:
            Dictionary of benchmark results
        """
        logger.info(f"Executing benchmark suite: {suite.name}")
        logger.info(f"Benchmarks: {len(suite.benchmarks)}")
        
        results = {}
        
        if suite.parallel_execution:
            # Execute benchmarks in parallel
            tasks = []
            for config in suite.benchmarks:
                if config.name in benchmark_functions:
                    task = self.execute_benchmark(config, benchmark_functions[config.name])
                    tasks.append((config.name, task))
            
            # Wait for all benchmarks to complete
            for benchmark_name, task in tasks:
                try:
                    result = await task
                    results[benchmark_name] = result
                except Exception as e:
                    logger.error(f"Parallel benchmark {benchmark_name} failed: {e}")
        else:
            # Execute benchmarks sequentially
            for config in suite.benchmarks:
                if config.name in benchmark_functions:
                    try:
                        result = await self.execute_benchmark(
                            config, benchmark_functions[config.name]
                        )
                        results[config.name] = result
                        
                        # Cooldown between benchmarks
                        if config.cooldown_seconds > 0:
                            await asyncio.sleep(config.cooldown_seconds)
                    
                    except Exception as e:
                        logger.error(f"Sequential benchmark {config.name} failed: {e}")
        
        logger.info(f"✅ Benchmark suite completed: {suite.name}")
        return results
    
    async def _execute_warmup(
        self,
        benchmark_function: Callable,
        config: BenchmarkConfig,
        *args,
        **kwargs
    ):
        """Execute warmup iterations to stabilize performance"""
        
        for _ in range(config.warmup_iterations):
            try:
                if asyncio.iscoroutinefunction(benchmark_function):
                    await benchmark_function(*args, **kwargs)
                else:
                    benchmark_function(*args, **kwargs)
            except Exception as e:
                logger.debug(f"Warmup iteration failed: {e}")
    
    async def _execute_benchmark_iterations(
        self,
        benchmark_function: Callable,
        config: BenchmarkConfig,
        *args,
        **kwargs
    ) -> List[float]:
        """Execute the main benchmark iterations"""
        
        measurements = []
        errors = []
        
        if config.concurrent_workers > 1:
            # Concurrent execution
            semaphore = asyncio.Semaphore(config.concurrent_workers)
            
            async def worker():
                async with semaphore:
                    start_time = time.perf_counter()
                    try:
                        if asyncio.iscoroutinefunction(benchmark_function):
                            await benchmark_function(*args, **kwargs)
                        else:
                            benchmark_function(*args, **kwargs)
                        
                        duration = time.perf_counter() - start_time
                        return duration, None
                    
                    except Exception as e:
                        duration = time.perf_counter() - start_time
                        return duration, str(e)
            
            # Create tasks for all iterations
            tasks = [worker() for _ in range(config.iterations)]
            
            # Execute with timeout
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=config.timeout_seconds
                )
                
                for result in results:
                    if isinstance(result, tuple):
                        duration, error = result
                        measurements.append(duration)
                        if error:
                            errors.append(error)
                    elif isinstance(result, Exception):
                        errors.append(str(result))
            
            except asyncio.TimeoutError:
                logger.error(f"Benchmark {config.name} timed out after {config.timeout_seconds}s")
                errors.append("Benchmark timed out")
        
        else:
            # Sequential execution
            for iteration in range(config.iterations):
                start_time = time.perf_counter()
                try:
                    if asyncio.iscoroutinefunction(benchmark_function):
                        await benchmark_function(*args, **kwargs)
                    else:
                        benchmark_function(*args, **kwargs)
                    
                    duration = time.perf_counter() - start_time
                    measurements.append(duration)
                
                except Exception as e:
                    duration = time.perf_counter() - start_time
                    measurements.append(duration)
                    errors.append(str(e))
                    logger.debug(f"Iteration {iteration} failed: {e}")
                
                # Check for timeout
                if time.perf_counter() - start_time > config.timeout_seconds:
                    logger.error(f"Benchmark {config.name} timed out")
                    errors.append("Individual iteration timed out")
                    break
        
        # Store errors for metrics calculation
        config.parameters["errors"] = errors
        
        return measurements
    
    def _calculate_metrics(
        self,
        benchmark_id: str,
        config: BenchmarkConfig,
        start_time: datetime,
        end_time: datetime,
        measurements: List[float],
        resource_metrics: Dict[str, float]
    ) -> BenchmarkMetrics:
        """Calculate comprehensive performance metrics"""
        
        if not measurements:
            measurements = [0.0]  # Prevent division by zero
        
        duration_seconds = (end_time - start_time).total_seconds()
        operations_count = len(measurements)
        
        # Calculate timing statistics
        avg_response_time = statistics.mean(measurements)
        min_response_time = min(measurements)
        max_response_time = max(measurements)
        
        # Calculate percentiles
        sorted_measurements = sorted(measurements)
        percentile_50 = self._calculate_percentile(sorted_measurements, 50)
        percentile_95 = self._calculate_percentile(sorted_measurements, 95)
        percentile_99 = self._calculate_percentile(sorted_measurements, 99)
        
        # Calculate success rate
        errors = config.parameters.get("errors", [])
        error_count = len(errors)
        success_rate = ((operations_count - error_count) / operations_count * 100) if operations_count > 0 else 0
        
        # Operations per second
        operations_per_second = operations_count / duration_seconds if duration_seconds > 0 else 0
        
        return BenchmarkMetrics(
            benchmark_id=benchmark_id,
            benchmark_type=config.benchmark_type,
            name=config.name,
            description=config.description,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
            operations_count=operations_count,
            operations_per_second=operations_per_second,
            average_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            percentile_50=percentile_50,
            percentile_95=percentile_95,
            percentile_99=percentile_99,
            peak_memory_mb=resource_metrics.get("peak_memory_mb", 0.0),
            average_cpu_percent=resource_metrics.get("avg_cpu_percent", 0.0),
            peak_cpu_percent=resource_metrics.get("peak_cpu_percent", 0.0),
            success_rate=success_rate,
            error_count=error_count,
            errors=errors[:50],  # Limit error list size
            metadata={
                "config": {
                    "iterations": config.iterations,
                    "concurrent_workers": config.concurrent_workers,
                    "warmup_iterations": config.warmup_iterations
                },
                "tenant_context": {
                    "tenant_id": config.tenant_context.tenant_id if config.tenant_context else None
                }
            },
            raw_measurements=measurements if config.collect_raw_data else []
        )
    
    def _calculate_percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile value from sorted measurements"""
        if not sorted_values:
            return 0.0
        
        index = int(len(sorted_values) * percentile / 100)
        if index >= len(sorted_values):
            index = len(sorted_values) - 1
        return sorted_values[index]
    
    async def _start_resource_monitoring(self, benchmark_id: str, config: BenchmarkConfig):
        """Start monitoring system resources during benchmark"""
        if not (config.monitor_memory or config.monitor_cpu):
            return
        
        self._monitoring_active = True
        
        async def monitor_resources():
            measurements = {
                "memory_samples": [],
                "cpu_samples": []
            }
            
            import psutil
            
            while self._monitoring_active:
                try:
                    if config.monitor_memory:
                        memory_info = psutil.virtual_memory()
                        measurements["memory_samples"].append(memory_info.used / (1024 * 1024))  # MB
                    
                    if config.monitor_cpu:
                        cpu_percent = psutil.cpu_percent(interval=0.1)
                        measurements["cpu_samples"].append(cpu_percent)
                    
                    await asyncio.sleep(0.5)  # Sample every 500ms
                
                except Exception as e:
                    logger.debug(f"Resource monitoring error: {e}")
            
            self._resource_monitors[benchmark_id] = measurements
        
        # Start monitoring in background
        asyncio.create_task(monitor_resources())
    
    async def _stop_resource_monitoring(self, benchmark_id: str) -> Dict[str, float]:
        """Stop resource monitoring and return metrics"""
        self._monitoring_active = False
        
        # Give monitoring task time to finish
        await asyncio.sleep(0.1)
        
        measurements = self._resource_monitors.get(benchmark_id, {})
        
        metrics = {}
        
        if "memory_samples" in measurements and measurements["memory_samples"]:
            memory_samples = measurements["memory_samples"]
            metrics["peak_memory_mb"] = max(memory_samples)
            metrics["avg_memory_mb"] = statistics.mean(memory_samples)
        
        if "cpu_samples" in measurements and measurements["cpu_samples"]:
            cpu_samples = measurements["cpu_samples"]
            metrics["peak_cpu_percent"] = max(cpu_samples)
            metrics["avg_cpu_percent"] = statistics.mean(cpu_samples)
        
        # Clean up monitoring data
        if benchmark_id in self._resource_monitors:
            del self._resource_monitors[benchmark_id]
        
        return metrics
    
    async def _store_benchmark_results(self, metrics: BenchmarkMetrics):
        """Store benchmark results to persistent storage"""
        try:
            timestamp = metrics.start_time.strftime("%Y%m%d_%H%M%S")
            filename = f"{metrics.name}_{timestamp}_{metrics.benchmark_id[:8]}.json"
            filepath = self.results_storage_path / filename
            
            # Convert metrics to JSON-serializable format
            metrics_dict = {
                "benchmark_id": metrics.benchmark_id,
                "benchmark_type": metrics.benchmark_type.value,
                "name": metrics.name,
                "description": metrics.description,
                "start_time": metrics.start_time.isoformat(),
                "end_time": metrics.end_time.isoformat(),
                "duration_seconds": metrics.duration_seconds,
                "operations_count": metrics.operations_count,
                "operations_per_second": metrics.operations_per_second,
                "average_response_time": metrics.average_response_time,
                "min_response_time": metrics.min_response_time,
                "max_response_time": metrics.max_response_time,
                "percentile_50": metrics.percentile_50,
                "percentile_95": metrics.percentile_95,
                "percentile_99": metrics.percentile_99,
                "peak_memory_mb": metrics.peak_memory_mb,
                "average_cpu_percent": metrics.average_cpu_percent,
                "peak_cpu_percent": metrics.peak_cpu_percent,
                "success_rate": metrics.success_rate,
                "error_count": metrics.error_count,
                "errors": metrics.errors,
                "metadata": metrics.metadata,
                "raw_measurements": metrics.raw_measurements
            }
            
            with open(filepath, 'w') as f:
                json.dump(metrics_dict, f, indent=2)
            
            logger.debug(f"Benchmark results stored: {filepath}")
        
        except Exception as e:
            logger.error(f"Failed to store benchmark results: {e}")
    
    @standard_exception_handler
    async def compare_with_baseline(
        self,
        current_metrics: BenchmarkMetrics,
        baseline_name: Optional[str] = None,
        regression_threshold: float = 0.1  # 10% performance degradation
    ) -> Dict[str, Any]:
        """
        Compare current benchmark results with established baseline.
        
        Args:
            current_metrics: Current benchmark metrics
            baseline_name: Name of baseline to compare against
            regression_threshold: Threshold for regression detection (0.1 = 10%)
            
        Returns:
            Comparison results with regression analysis
        """
        if baseline_name is None:
            baseline_name = current_metrics.name
        
        if baseline_name not in self.baselines:
            logger.warning(f"No baseline found for {baseline_name}, setting current as baseline")
            self.baselines[baseline_name] = current_metrics
            return {"status": "baseline_set", "baseline": baseline_name}
        
        baseline = self.baselines[baseline_name]
        
        # Calculate performance differences
        comparisons = {
            "operations_per_second": {
                "baseline": baseline.operations_per_second,
                "current": current_metrics.operations_per_second,
                "change_percent": self._calculate_change_percent(
                    baseline.operations_per_second, current_metrics.operations_per_second
                ),
                "better": current_metrics.operations_per_second > baseline.operations_per_second
            },
            "average_response_time": {
                "baseline": baseline.average_response_time,
                "current": current_metrics.average_response_time,
                "change_percent": self._calculate_change_percent(
                    baseline.average_response_time, current_metrics.average_response_time
                ),
                "better": current_metrics.average_response_time < baseline.average_response_time
            },
            "percentile_95": {
                "baseline": baseline.percentile_95,
                "current": current_metrics.percentile_95,
                "change_percent": self._calculate_change_percent(
                    baseline.percentile_95, current_metrics.percentile_95
                ),
                "better": current_metrics.percentile_95 < baseline.percentile_95
            },
            "memory_usage": {
                "baseline": baseline.peak_memory_mb,
                "current": current_metrics.peak_memory_mb,
                "change_percent": self._calculate_change_percent(
                    baseline.peak_memory_mb, current_metrics.peak_memory_mb
                ),
                "better": current_metrics.peak_memory_mb < baseline.peak_memory_mb
            }
        }
        
        # Detect regressions
        regressions = []
        improvements = []
        
        for metric_name, data in comparisons.items():
            change_percent = abs(data["change_percent"])
            if change_percent > regression_threshold * 100:  # Convert to percentage
                if data["better"]:
                    improvements.append({
                        "metric": metric_name,
                        "improvement_percent": change_percent,
                        "baseline": data["baseline"],
                        "current": data["current"]
                    })
                else:
                    regressions.append({
                        "metric": metric_name,
                        "regression_percent": change_percent,
                        "baseline": data["baseline"],
                        "current": data["current"]
                    })
        
        return {
            "status": "compared",
            "baseline_name": baseline_name,
            "baseline_date": baseline.start_time.isoformat(),
            "current_date": current_metrics.start_time.isoformat(),
            "comparisons": comparisons,
            "regressions": regressions,
            "improvements": improvements,
            "overall_performance": "degraded" if regressions else ("improved" if improvements else "stable")
        }
    
    def _calculate_change_percent(self, baseline: float, current: float) -> float:
        """Calculate percentage change from baseline to current"""
        if baseline == 0:
            return 0.0
        return ((current - baseline) / baseline) * 100
    
    def get_benchmark_summary(self) -> Dict[str, Any]:
        """Get summary of all benchmark executions"""
        
        if not self.benchmark_history:
            return {"total": 0, "summary": "No benchmarks executed"}
        
        total_benchmarks = len(self.benchmark_history)
        successful_benchmarks = sum(1 for b in self.benchmark_history if b.success_rate > 95)
        
        # Calculate average metrics
        avg_ops_per_second = statistics.mean([b.operations_per_second for b in self.benchmark_history])
        avg_response_time = statistics.mean([b.average_response_time for b in self.benchmark_history])
        
        # Benchmark types breakdown
        type_breakdown = {}
        for benchmark in self.benchmark_history:
            benchmark_type = benchmark.benchmark_type.value
            if benchmark_type not in type_breakdown:
                type_breakdown[benchmark_type] = 0
            type_breakdown[benchmark_type] += 1
        
        return {
            "total_benchmarks": total_benchmarks,
            "successful_benchmarks": successful_benchmarks,
            "success_rate": (successful_benchmarks / total_benchmarks * 100) if total_benchmarks > 0 else 0,
            "average_operations_per_second": avg_ops_per_second,
            "average_response_time": avg_response_time,
            "benchmark_types": type_breakdown,
            "baselines_established": len(self.baselines),
            "active_benchmarks": len([b for b in self.active_benchmarks.values() if b == BenchmarkStatus.RUNNING])
        }