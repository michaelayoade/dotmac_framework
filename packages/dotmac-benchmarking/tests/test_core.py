"""
Tests for core benchmarking functionality.
"""

import asyncio

import pytest

from dotmac_benchmarking.core import (
    BenchmarkResult,
    BenchmarkRunner,
    time_async_function,
    time_function,
)


class TestBenchmarkResult:
    """Test BenchmarkResult dataclass."""

    def test_from_durations_basic(self):
        """Test creating BenchmarkResult from durations."""
        durations = [0.1, 0.2, 0.15, 0.3, 0.25]
        result = BenchmarkResult.from_durations("test", durations)

        assert result.label == "test"
        assert result.samples == 5
        assert result.durations == durations
        assert result.min_duration == 0.1
        assert result.max_duration == 0.3
        assert 0.2 == pytest.approx(result.avg_duration, abs=0.01)
        assert result.timestamp is not None

    def test_from_durations_empty(self):
        """Test error handling for empty durations."""
        with pytest.raises(ValueError, match="Durations list cannot be empty"):
            BenchmarkResult.from_durations("test", [])

    def test_from_durations_single(self):
        """Test with single duration."""
        durations = [0.5]
        result = BenchmarkResult.from_durations("single", durations)

        assert result.samples == 1
        assert result.avg_duration == 0.5
        assert result.min_duration == 0.5
        assert result.max_duration == 0.5
        assert result.p50_duration == 0.5
        assert result.p95_duration == 0.5
        assert result.p99_duration == 0.5

    def test_with_metadata(self):
        """Test including metadata."""
        metadata = {"version": "1.0", "config": "test"}
        result = BenchmarkResult.from_durations("test", [0.1], metadata)

        assert result.metadata == metadata


class TestBenchmarkRunner:
    """Test BenchmarkRunner class."""

    @pytest.mark.asyncio
    async def test_basic_benchmark(self):
        """Test basic benchmarking functionality."""
        runner = BenchmarkRunner()

        async def test_function():
            await asyncio.sleep(0.01)
            return "test"

        result = await runner.run("sleep_test", test_function, samples=3)

        assert result.label == "sleep_test"
        assert result.samples == 3
        assert result.avg_duration >= 0.01
        assert len(result.durations) == 3
        assert len(runner.get_results()) == 1

    @pytest.mark.asyncio
    async def test_with_warmup(self):
        """Test benchmarking with warmup iterations."""
        runner = BenchmarkRunner()
        call_count = 0

        async def counting_function():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.001)

        result = await runner.run(
            "warmup_test",
            counting_function,
            samples=2,
            warmup=3
        )

        assert result.samples == 2
        assert call_count == 5  # 3 warmup + 2 samples

    @pytest.mark.asyncio
    async def test_invalid_samples(self):
        """Test error handling for invalid sample count."""
        runner = BenchmarkRunner()

        async def dummy():
            pass

        with pytest.raises(ValueError, match="Samples must be positive"):
            await runner.run("test", dummy, samples=0)

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that benchmark timing is recorded even when function raises."""
        runner = BenchmarkRunner()

        async def failing_function():
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await runner.run("fail_test", failing_function, samples=1)

        # Should still have recorded the timing data
        results = runner.get_results()
        assert len(results) == 1
        assert results[0].avg_duration >= 0.01

    def test_compare_results(self):
        """Test comparing benchmark results."""
        runner = BenchmarkRunner()

        # Create mock results
        result1 = BenchmarkResult.from_durations("fast", [0.1, 0.1, 0.1])
        result2 = BenchmarkResult.from_durations("slow", [0.2, 0.2, 0.2])

        comparison = runner.compare([result1, result2])

        assert comparison["baseline"]["label"] == "fast"
        assert comparison["baseline"]["avg_duration"] == 0.1
        assert len(comparison["comparisons"]) == 1

        comp = comparison["comparisons"][0]
        assert comp["label"] == "slow"
        assert comp["ratio"] == 2.0
        assert comp["percent_slower"] == 100.0
        assert comp["is_faster"] is False

    def test_compare_insufficient_results(self):
        """Test error when comparing insufficient results."""
        runner = BenchmarkRunner()

        with pytest.raises(ValueError, match="Need at least 2 results to compare"):
            runner.compare([])

    async def test_compare_default_none(self):
        """Test compare with results=None uses internal results."""
        runner = BenchmarkRunner()
        
        async def dummy_async_function():
            await asyncio.sleep(0.01)
            
        async def slow_dummy_async_function():
            await asyncio.sleep(0.02)
            
        await runner.run("test1", dummy_async_function, samples=2)
        await runner.run("test2", slow_dummy_async_function, samples=2)
        
        # Test with explicit results=None
        comparison = runner.compare(results=None)
        
        assert "baseline" in comparison
        assert "comparisons" in comparison
        assert len(comparison["comparisons"]) == 1
        
        # Should be same as calling without arguments
        comparison_default = runner.compare()
        assert comparison == comparison_default

    def test_clear_results(self):
        """Test clearing stored results."""
        runner = BenchmarkRunner()
        result = BenchmarkResult.from_durations("test", [0.1])
        runner._results.append(result)

        assert len(runner.get_results()) == 1
        runner.clear_results()
        assert len(runner.get_results()) == 0


class TestTimingFunctions:
    """Test standalone timing functions."""

    def test_time_function(self):
        """Test timing a sync function."""
        def slow_function():
            import time
            time.sleep(0.01)

        duration = time_function(slow_function)
        assert duration >= 0.01

    @pytest.mark.asyncio
    async def test_time_async_function(self):
        """Test timing an async function."""
        async def slow_async_function():
            await asyncio.sleep(0.01)

        duration = await time_async_function(slow_async_function)
        assert duration >= 0.01
