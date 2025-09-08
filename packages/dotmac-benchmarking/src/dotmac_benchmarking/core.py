"""
Core benchmarking framework.

Provides the main BenchmarkRunner class for executing and analyzing performance benchmarks.
"""

import statistics
import time
from collections.abc import Awaitable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass
class BenchmarkResult:
    """Result from a single benchmark execution."""

    label: str
    samples: int
    durations: list[float]
    avg_duration: float
    min_duration: float
    max_duration: float
    p50_duration: float
    p95_duration: float
    p99_duration: float
    total_duration: float
    timestamp: str
    metadata: dict[str, Any]

    @classmethod
    def from_durations(
        cls,
        label: str,
        durations: list[float],
        metadata: dict[str, Any] | None = None
    ) -> "BenchmarkResult":
        """Create BenchmarkResult from timing measurements."""
        if not durations:
            raise ValueError("Durations list cannot be empty")

        sorted_durations = sorted(durations)
        samples = len(durations)

        return cls(
            label=label,
            samples=samples,
            durations=durations,
            avg_duration=statistics.mean(durations),
            min_duration=min(durations),
            max_duration=max(durations),
            p50_duration=sorted_durations[int(samples * 0.5)],
            p95_duration=sorted_durations[int(samples * 0.95)] if samples > 1 else sorted_durations[0],
            p99_duration=sorted_durations[int(samples * 0.99)] if samples > 1 else sorted_durations[0],
            total_duration=sum(durations),
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {}
        )


class BenchmarkRunner:
    """
    Core benchmark runner for timing function executions.
    
    Provides methods to run benchmarks with multiple samples and compare results.
    """

    def __init__(self) -> None:
        """Initialize the benchmark runner."""
        self._results: list[BenchmarkResult] = []

    async def run(
        self,
        label: str,
        fn: Callable[[], Awaitable[Any]],
        *,
        samples: int = 3,
        warmup: int = 0,
        metadata: dict[str, Any] | None = None
    ) -> BenchmarkResult:
        """
        Run a benchmark with multiple samples.
        
        Args:
            label: Name/description for this benchmark
            fn: Async function to benchmark
            samples: Number of samples to collect (default: 3)
            warmup: Number of warmup iterations (default: 0)  
            metadata: Optional metadata to include in results
            
        Returns:
            BenchmarkResult containing timing statistics
            
        Example:
            async def my_function():
                await asyncio.sleep(0.1)
                return "done"
            
            runner = BenchmarkRunner()
            result = await runner.run("sleep_test", my_function, samples=5)
            print(f"Average: {result.avg_duration:.3f}s")
        """
        if samples <= 0:
            raise ValueError("Samples must be positive")

        # Warmup iterations
        for _ in range(warmup):
            await fn()

        durations = []

        # Collect timing samples
        try:
            for _ in range(samples):
                start_time = time.perf_counter()
                try:
                    await fn()
                finally:
                    duration = time.perf_counter() - start_time
                    durations.append(duration)
        except Exception as e:
            # Even if function raises an exception, create result from collected samples
            if durations:
                result = BenchmarkResult.from_durations(label, durations, metadata)
                self._results.append(result)
            raise e

        result = BenchmarkResult.from_durations(label, durations, metadata)
        self._results.append(result)

        return result

    def compare(self, results: list[BenchmarkResult] | None = None) -> dict[str, Any]:
        """
        Compare benchmark results.
        
        Args:
            results: List of results to compare (uses stored results if None)
            
        Returns:
            Comparison report with statistics and relative performance
        """
        if results is None:
            results = self._results

        if len(results) < 2:
            raise ValueError("Need at least 2 results to compare")

        # Find fastest result as baseline
        baseline = min(results, key=lambda r: r.avg_duration)

        comparison = {
            "baseline": {
                "label": baseline.label,
                "avg_duration": baseline.avg_duration
            },
            "comparisons": []
        }

        for result in results:
            if result.label == baseline.label:
                continue

            ratio = result.avg_duration / baseline.avg_duration
            percent_slower = (ratio - 1.0) * 100

            comparison["comparisons"].append({
                "label": result.label,
                "avg_duration": result.avg_duration,
                "ratio": ratio,
                "percent_slower": percent_slower,
                "is_faster": ratio < 1.0
            })

        return comparison

    def get_results(self) -> list[BenchmarkResult]:
        """Get all stored benchmark results."""
        return self._results.copy()

    def clear_results(self) -> None:
        """Clear all stored benchmark results."""
        self._results.clear()


def time_function(fn: Callable[[], Any]) -> float:
    """
    Time a synchronous function execution.
    
    Args:
        fn: Function to time
        
    Returns:
        Execution duration in seconds
    """
    start_time = time.perf_counter()
    fn()
    return time.perf_counter() - start_time


async def time_async_function(fn: Callable[[], Awaitable[Any]]) -> float:
    """
    Time an asynchronous function execution.
    
    Args:
        fn: Async function to time
        
    Returns:
        Execution duration in seconds
    """
    start_time = time.perf_counter()
    await fn()
    return time.perf_counter() - start_time
