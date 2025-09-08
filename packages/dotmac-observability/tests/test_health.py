"""
Tests for health monitoring functionality.
"""

import asyncio

import pytest

from dotmac_observability import HealthMonitor, HealthStatus


@pytest.mark.asyncio
async def test_health_monitor_all_passing():
    """Test health monitor with all checks passing."""
    monitor = HealthMonitor()

    async def healthy_check():
        return True

    monitor.add_check("test1", healthy_check, required=True)
    monitor.add_check("test2", healthy_check, required=False)

    results = await monitor.run_checks()

    assert results["status"] == HealthStatus.HEALTHY.value
    assert results["summary"]["total"] == 2
    assert results["summary"]["healthy"] == 2
    assert results["summary"]["required"] == 1
    assert results["summary"]["required_healthy"] == 1


@pytest.mark.asyncio
async def test_health_monitor_required_failing():
    """Test health monitor with required check failing."""
    monitor = HealthMonitor()

    async def healthy_check():
        return True

    async def unhealthy_check():
        return False

    monitor.add_check("healthy", healthy_check, required=False)
    monitor.add_check("unhealthy", unhealthy_check, required=True)

    results = await monitor.run_checks()

    assert results["status"] == HealthStatus.UNHEALTHY.value
    assert results["summary"]["required_healthy"] == 0


@pytest.mark.asyncio
async def test_health_monitor_optional_failing():
    """Test health monitor with optional check failing."""
    monitor = HealthMonitor()

    async def healthy_check():
        return True

    async def unhealthy_check():
        return False

    monitor.add_check("healthy", healthy_check, required=True)
    monitor.add_check("unhealthy", unhealthy_check, required=False)

    results = await monitor.run_checks()

    assert results["status"] == HealthStatus.HEALTHY.value  # Overall healthy since no required checks failed
    assert results["summary"]["required_healthy"] == 1
    assert results["summary"]["healthy"] == 1  # Only required check counted as healthy


@pytest.mark.asyncio
async def test_health_monitor_timeout():
    """Test health monitor with check timing out."""
    monitor = HealthMonitor()

    async def slow_check():
        await asyncio.sleep(2.0)  # Sleep longer than timeout
        return True

    monitor.add_check("slow", slow_check, required=True, timeout=0.1)

    results = await monitor.run_checks()

    assert results["status"] == HealthStatus.UNHEALTHY.value

    assert "slow" in results["checks"]
    slow_check_result = results["checks"]["slow"]
    assert slow_check_result["status"] == HealthStatus.TIMEOUT.value
    assert "timed out" in slow_check_result["error"]


@pytest.mark.asyncio
async def test_health_monitor_exception():
    """Test health monitor with check raising exception."""
    monitor = HealthMonitor()

    async def failing_check():
        raise ValueError("Something went wrong")

    monitor.add_check("failing", failing_check, required=True)

    results = await monitor.run_checks()

    assert results["status"] == HealthStatus.UNHEALTHY.value

    assert "failing" in results["checks"]
    failing_check_result = results["checks"]["failing"]
    assert failing_check_result["status"] == HealthStatus.UNHEALTHY.value
    assert "Something went wrong" in failing_check_result["error"]


@pytest.mark.asyncio
async def test_health_monitor_empty():
    """Test health monitor with no checks."""
    monitor = HealthMonitor()

    results = await monitor.run_checks()

    assert results["status"] == HealthStatus.UNKNOWN.value
    assert results["summary"]["total"] == 0
    assert len(results["checks"]) == 0


@pytest.mark.asyncio
async def test_health_monitor_last_results():
    """Test getting last results from health monitor."""
    monitor = HealthMonitor()

    async def healthy_check():
        return True

    monitor.add_check("test", healthy_check)

    # Initially no results
    assert monitor.get_last_results() is None

    # Run checks
    results1 = await monitor.run_checks()

    # Should get cached results
    results2 = monitor.get_last_results()
    assert results1 == results2


def test_health_check_metadata():
    """Test health check metadata is preserved."""
    monitor = HealthMonitor()

    async def test_check():
        return True

    monitor.add_check(
        "metadata_test", test_check, required=False, timeout=10.0, description="A test check"
    )

    check_config = monitor._checks["metadata_test"]
    assert check_config["required"] is False
    assert check_config["timeout"] == 10.0
    assert check_config["description"] == "A test check"