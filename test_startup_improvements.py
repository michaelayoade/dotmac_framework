#!/usr/bin/env python3
"""
Test script for startup error handling and health check improvements.

Tests the new standardized startup error handling and comprehensive
health check systems across both platforms.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add shared modules to path
sys.path.insert(0, str(Path(__file__).parent / "shared"))

from startup.error_handling import (
    create_startup_manager,
    StartupPhase,
    StartupErrorSeverity,
    managed_startup
)
from health.comprehensive_checks import (
    setup_health_checker,
    HealthStatus,
    SystemResourcesHealthCheck,
    FilesystemHealthCheck
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_startup_error_handling():
    """Test the startup error handling system."""
    logger.info("🧪 Testing startup error handling system...")
    
    # Test successful startup
    async with managed_startup(
        service_name="Test Service",
        fail_on_critical=False,
        fail_on_high_severity=False
    ) as startup_manager:
        
        # Test successful operation
        async def successful_operation():
            await asyncio.sleep(0.1)  # Simulate work
            return "success"
        
        result = await startup_manager.execute_with_retry(
            operation=successful_operation,
            phase=StartupPhase.INITIALIZATION,
            component="Test Component",
            severity=StartupErrorSeverity.MEDIUM,
            max_retries=2
        )
        
        assert result.success, "Successful operation should succeed"
        assert result.metadata.get("result") == "success"
        logger.info("✅ Successful operation test passed")
        
        # Test operation with retries
        attempt_count = 0
        
        async def retry_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception(f"Simulated failure {attempt_count}")
            return f"success after {attempt_count} attempts"
        
        result = await startup_manager.execute_with_retry(
            operation=retry_operation,
            phase=StartupPhase.DATABASE,
            component="Retry Test Component",
            severity=StartupErrorSeverity.HIGH,
            max_retries=3
        )
        
        assert result.success, "Retry operation should eventually succeed"
        logger.info("✅ Retry operation test passed")
        
        # Test failed operation
        async def failed_operation():
            raise Exception("Persistent failure")
        
        result = await startup_manager.execute_with_retry(
            operation=failed_operation,
            phase=StartupPhase.CACHE,
            component="Failed Component",
            severity=StartupErrorSeverity.MEDIUM,
            max_retries=1
        )
        
        assert not result.success, "Failed operation should fail"
        assert len(result.errors) == 1
        logger.info("✅ Failed operation test passed")
        
        # Test startup manager state
        assert len(startup_manager.startup_errors) == 1, "Should have one startup error"
        assert startup_manager.should_continue_startup(), "Should continue startup with medium severity error"
        
        startup_manager.add_warning("Test warning")
        assert len(startup_manager.startup_warnings) == 1, "Should have one warning"
        
        startup_manager.add_metadata("test_key", "test_value")
        assert startup_manager.startup_metadata["test_key"] == "test_value"
        
        logger.info("✅ Startup manager state tests passed")
    
    logger.info("🎉 Startup error handling tests completed successfully!")


async def test_health_checks():
    """Test the comprehensive health check system."""
    logger.info("🧪 Testing comprehensive health check system...")
    
    # Create health checker
    health_checker = setup_health_checker(
        service_name="Test Service",
        additional_filesystem_paths=[".", "/tmp"]
    )
    
    assert health_checker.service_name == "Test Service"
    assert len(health_checker.health_checks) >= 2, "Should have at least system and filesystem checks"
    logger.info(f"✅ Health checker created with {len(health_checker.health_checks)} checks")
    
    # Test individual health check
    system_check = SystemResourcesHealthCheck()
    result = await system_check.run_check()
    
    assert result.component_name == "System Resources"
    assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
    assert len(result.metrics) > 0, "Should have system resource metrics"
    assert result.duration_ms >= 0
    logger.info(f"✅ System resources check: {result.status.value} ({result.duration_ms:.1f}ms)")
    
    # Test filesystem check
    filesystem_check = FilesystemHealthCheck(paths_to_check=[".", "/tmp"])
    result = await filesystem_check.run_check()
    
    assert result.component_name == "Filesystem"
    assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
    logger.info(f"✅ Filesystem check: {result.status.value} ({result.duration_ms:.1f}ms)")
    
    # Test running all checks
    all_results = await health_checker.run_all_checks(parallel=True)
    assert len(all_results) == len(health_checker.health_checks)
    logger.info(f"✅ All checks completed: {len(all_results)} results")
    
    # Test overall status
    overall_status = health_checker.get_overall_status(all_results)
    assert "overall_status" in overall_status
    assert "service_name" in overall_status
    assert "total_checks" in overall_status
    assert overall_status["total_checks"] == len(all_results)
    logger.info(f"✅ Overall status: {overall_status['overall_status']} ({overall_status['message']})")
    
    # Test specific check
    check_names = list(health_checker.health_checks.keys())
    if check_names:
        specific_result = await health_checker.run_check(check_names[0])
        assert specific_result.component_name == check_names[0]
        logger.info(f"✅ Specific check '{check_names[0]}' completed")
    
    # Test serialization
    for name, result in all_results.items():
        result_dict = result.to_dict()
        assert "component_name" in result_dict
        assert "status" in result_dict
        assert "timestamp" in result_dict
        logger.info(f"✅ Serialization test passed for {name}")
    
    logger.info("🎉 Health check tests completed successfully!")


async def test_integration():
    """Test integration between startup and health systems."""
    logger.info("🧪 Testing startup and health integration...")
    
    async with managed_startup(
        service_name="Integration Test Service",
        fail_on_critical=False
    ) as startup_manager:
        
        # Simulate setting up health checker during startup
        health_checker = setup_health_checker(
            service_name="Integration Test Service",
            additional_filesystem_paths=["."]
        )
        
        startup_manager.add_metadata("health_checks", len(health_checker.health_checks))
        
        # Simulate a service initialization
        async def init_service():
            await asyncio.sleep(0.1)
            return health_checker
        
        result = await startup_manager.execute_with_retry(
            operation=init_service,
            phase=StartupPhase.INITIALIZATION,
            component="Health Check System",
            severity=StartupErrorSeverity.HIGH,
            max_retries=2
        )
        
        assert result.success, "Health checker initialization should succeed"
        
        # Run health checks after startup
        health_results = await health_checker.run_all_checks()
        overall_status = health_checker.get_overall_status(health_results)
        
        logger.info(f"✅ Integration test: {overall_status['overall_status']} with {overall_status['total_checks']} checks")
        
        # Verify startup metadata includes health check info
        assert "health_checks" in startup_manager.startup_metadata
        assert startup_manager.startup_metadata["health_checks"] == len(health_checker.health_checks)
        
    logger.info("🎉 Integration tests completed successfully!")


async def main():
    """Run all tests."""
    logger.info("🚀 Starting startup and health check improvements tests...")
    
    try:
        await test_startup_error_handling()
        await test_health_checks()
        await test_integration()
        
        logger.info("🎉 All tests passed successfully!")
        logger.info("✅ Startup error handling and health check systems are working correctly")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())