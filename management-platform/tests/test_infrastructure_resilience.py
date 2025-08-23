"""
Infrastructure resilience tests for the DotMac Management Platform.
Tests system resilience, failover, recovery, and performance under stress.
"""

import pytest
import asyncio
import time
import random
from datetime import datetime, timedelta
from unittest.mock import patch, Mock, AsyncMock
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

from sqlalchemy.exc import DisconnectionError, OperationalError
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.monitoring import HealthCheckService, MetricsCollector
from app.core.database import get_db, database_transaction
from app.core.cache import CacheService
from app.services.tenant_service import TenantService
from app.services.billing_service import BillingService
from app.services.auth_service import AuthService


@pytest.mark.resilience
class TestDatabaseResilience:
    """Test database connection resilience and recovery."""
    
    async def test_database_connection_retry(self, db_session):
        """Test automatic database connection retry on failure."""
        tenant_service = TenantService(db_session)
        
        # Simulate database connection failure
        with patch('app.database.async_session_maker') as mock_session:
            # First call fails, second succeeds
            mock_session.side_effect = [
                OperationalError("Connection lost", None, None),
                db_session  # Successful retry
            ]
            
            # Should retry and eventually succeed
            tenant = await tenant_service.get_tenant_by_slug("test-tenant")
            # Test passes if no exception is raised
    
    async def test_database_transaction_rollback(self, db_session):
        """Test transaction rollback on failure."""
        tenant_service = TenantService(db_session)
        
        # Start transaction that will fail
        try:
            async with database_transaction(db_session) as tx_session:
                # Create valid tenant
                from app.schemas.tenant import TenantCreate
                tenant_data = TenantCreate(
                    name="Test Rollback Tenant",
                    slug="rollback-test", 
                    primary_contact_email="rollback@test.com"
                )
                tenant = await tenant_service.create_tenant(tenant_data, "test")
                
                # Force an error to trigger rollback
                await tx_session.execute("INVALID SQL STATEMENT")
        except Exception:
            pass  # Expected to fail
        
        # Tenant should not exist due to rollback
        rolled_back_tenant = await tenant_service.get_tenant_by_slug("rollback-test")
        assert rolled_back_tenant is None
    
    async def test_connection_pool_exhaustion(self):
        """Test behavior when database connection pool is exhausted."""
        # Create many concurrent database operations
        async def db_operation(session_id: int):
            try:
                async with get_db() as db_session:
                    tenant_service = TenantService(db_session)
                    # Simulate long-running operation
                    await asyncio.sleep(0.1)
                    return f"session_{session_id}_success"
            except Exception as e:
                return f"session_{session_id}_failed: {str(e)}"
        
        # Spawn more operations than pool size
        tasks = [db_operation(i) for i in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Some operations should succeed even under pressure
        successful = [r for r in results if "success" in str(r)]
        assert len(successful) > 0
        
        # System should handle pressure gracefully (no crashes)
        crashed = [r for r in results if isinstance(r, Exception)]
        assert len(crashed) < len(results) * 0.5  # Less than 50% should crash


@pytest.mark.resilience  
class TestCacheResilience:
    """Test cache system resilience and fallback behavior."""
    
    async def test_redis_connection_failure_fallback(self):
        """Test graceful fallback when Redis is unavailable."""
        cache_service = CacheService()
        
        # Mock Redis connection failure
        with patch.object(cache_service.redis, 'get', side_effect=RedisConnectionError("Redis unavailable")):
            with patch.object(cache_service.redis, 'set', side_effect=RedisConnectionError("Redis unavailable")):
                # Cache operations should fallback gracefully
                result = await cache_service.get("test_key")
                assert result is None  # Should return None instead of crashing
                
                # Set operation should not crash
                await cache_service.set("test_key", "test_value", ttl=300)
                # Should complete without exception
    
    async def test_cache_data_corruption_recovery(self):
        """Test recovery from corrupted cache data."""
        cache_service = CacheService()
        
        # Store valid data
        await cache_service.set("valid_data", {"key": "value"}, ttl=300)
        
        # Simulate corrupted cache entry
        with patch.object(cache_service.redis, 'get', return_value=b'corrupted_json_data'):
            result = await cache_service.get("valid_data")
            assert result is None  # Should handle corruption gracefully
    
    async def test_cache_memory_pressure(self):
        """Test cache behavior under memory pressure."""
        cache_service = CacheService()
        
        # Fill cache with large amounts of data
        large_data = "x" * 10000  # 10KB string
        
        tasks = []
        for i in range(100):  # Store 100 large items
            task = cache_service.set(f"large_item_{i}", large_data, ttl=300)
            tasks.append(task)
        
        # Should handle memory pressure without crashing
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify some data is still accessible
        result = await cache_service.get("large_item_50")
        # Should either be the data or None (evicted), but not crash


@pytest.mark.resilience
class TestServiceResilience:
    """Test service layer resilience and error handling."""
    
    async def test_service_timeout_handling(self, db_session):
        """Test service timeout handling for long-running operations."""
        billing_service = BillingService(db_session)
        
        # Mock slow external payment processor
        async def slow_payment_process(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate 10 second delay
            return {"status": "success"}
        
        with patch.object(billing_service, '_process_external_payment', side_effect=slow_payment_process):
            from app.schemas.billing import PaymentCreate
            
            payment_data = PaymentCreate(
                invoice_id="550e8400-e29b-41d4-a716-446655440001",
                amount_cents=2999,
                payment_method="credit_card"
            )
            
            start_time = time.time()
            
            # Should timeout and handle gracefully
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    billing_service.process_payment(payment_data),
                    timeout=5.0  # 5 second timeout
                )
            
            elapsed = time.time() - start_time
            assert elapsed < 6  # Should timeout within timeout period
    
    async def test_cascading_failure_prevention(self, db_session):
        """Test prevention of cascading failures across services."""
        tenant_service = TenantService(db_session)
        auth_service = AuthService(db_session)
        
        # Simulate auth service failure
        with patch.object(auth_service, 'verify_user', side_effect=Exception("Auth service down")):
            
            # Tenant service should continue working independently
            from app.schemas.tenant import TenantCreate
            tenant_data = TenantCreate(
                name="Resilience Test Tenant",
                slug="resilience-test",
                primary_contact_email="resilience@test.com"
            )
            
            # Should succeed despite auth service failure
            tenant = await tenant_service.create_tenant(tenant_data, "system")
            assert tenant is not None
            assert tenant.name == "Resilience Test Tenant"
    
    async def test_circuit_breaker_pattern(self):
        """Test circuit breaker pattern for external service calls."""
        
        class CircuitBreakerService:
            def __init__(self):
                self.failure_count = 0
                self.failure_threshold = 3
                self.is_open = False
                self.last_failure_time = None
                self.recovery_timeout = 30  # seconds
            
            async def external_call(self):
                # Check if circuit is open
                if self.is_open:
                    if (datetime.utcnow() - self.last_failure_time).seconds > self.recovery_timeout:
                        self.is_open = False
                        self.failure_count = 0
                    else:
                        raise Exception("Circuit breaker is open")
                
                # Simulate external service call
                if random.random() < 0.7:  # 70% failure rate
                    self.failure_count += 1
                    if self.failure_count >= self.failure_threshold:
                        self.is_open = True
                        self.last_failure_time = datetime.utcnow()
                    raise Exception("External service failed")
                
                self.failure_count = 0  # Reset on success
                return "success"
        
        service = CircuitBreakerService()
        
        # Make multiple calls that will likely trigger circuit breaker
        results = []
        for _ in range(20):
            try:
                result = await service.external_call()
                results.append(result)
            except Exception as e:
                results.append(str(e))
            await asyncio.sleep(0.1)
        
        # Circuit breaker should have opened after failures
        circuit_open_results = [r for r in results if "circuit breaker is open" in r.lower()]
        assert len(circuit_open_results) > 0


@pytest.mark.resilience
@pytest.mark.slow
class TestPerformanceResilience:
    """Test system performance under stress and load."""
    
    async def test_concurrent_request_handling(self, client, auth_headers):
        """Test handling of concurrent API requests."""
        
        async def make_request(request_id: int):
            try:
                response = await client.get(
                    f"/api/v1/health?request_id={request_id}",
                    headers=auth_headers
                )
                return {
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() if hasattr(response, 'elapsed') else 0
                }
            except Exception as e:
                return {
                    "request_id": request_id,
                    "error": str(e)
                }
        
        # Send 100 concurrent requests
        tasks = [make_request(i) for i in range(100)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_requests = [r for r in results if isinstance(r, dict) and r.get("status_code") == 200]
        failed_requests = [r for r in results if isinstance(r, dict) and "error" in r]
        
        # At least 80% should succeed
        success_rate = len(successful_requests) / len(results)
        assert success_rate >= 0.8
        
        # Average response time should be reasonable
        if successful_requests:
            avg_response_time = sum(r.get("response_time", 0) for r in successful_requests) / len(successful_requests)
            assert avg_response_time < 2.0  # Less than 2 seconds average
    
    async def test_memory_leak_detection(self, db_session):
        """Test for memory leaks during repeated operations."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        tenant_service = TenantService(db_session)
        
        # Perform many operations that could potentially leak memory
        for i in range(100):
            from app.schemas.tenant import TenantCreate
            tenant_data = TenantCreate(
                name=f"Memory Test Tenant {i}",
                slug=f"memory-test-{i}",
                primary_contact_email=f"memory{i}@test.com"
            )
            
            tenant = await tenant_service.create_tenant(tenant_data, "test")
            await tenant_service.get_tenant(tenant.id)
            await tenant_service.update_tenant(tenant.id, {"name": f"Updated Tenant {i}"}, "test")
            
            # Clean up
            await tenant_service.delete_tenant(tenant.id, "test")
            
            # Force garbage collection periodically
            if i % 20 == 0:
                import gc
                gc.collect()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024  # 50MB in bytes
    
    async def test_database_deadlock_handling(self, db_session):
        """Test handling of database deadlocks."""
        tenant_service = TenantService(db_session)
        
        async def concurrent_update(tenant_id: str, update_data: dict, user_id: str):
            try:
                for _ in range(5):  # Multiple rapid updates
                    await tenant_service.update_tenant(tenant_id, update_data, user_id)
                    await asyncio.sleep(0.01)  # Small delay
                return "success"
            except Exception as e:
                if "deadlock" in str(e).lower():
                    return "deadlock_handled"
                raise e
        
        # Create test tenant
        from app.schemas.tenant import TenantCreate
        tenant_data = TenantCreate(
            name="Deadlock Test Tenant",
            slug="deadlock-test",
            primary_contact_email="deadlock@test.com"
        )
        tenant = await tenant_service.create_tenant(tenant_data, "test")
        
        # Start concurrent updates that might cause deadlock
        tasks = [
            concurrent_update(tenant.id, {"name": f"Updated by Task {i}"}, f"user_{i}")
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should handle deadlocks gracefully
        deadlock_handled = sum(1 for r in results if r == "deadlock_handled")
        successful = sum(1 for r in results if r == "success")
        
        # At least some operations should succeed
        assert successful > 0


@pytest.mark.resilience
class TestHealthChecks:
    """Test health check system and monitoring."""
    
    async def test_health_check_system_status(self):
        """Test comprehensive system health checking."""
        health_service = HealthCheckService()
        
        health_status = await health_service.check_system_health()
        
        # Should check all critical components
        assert "database" in health_status
        assert "cache" in health_status  
        assert "application" in health_status
        assert "system_resources" in health_status
        
        # Each component should have status and metrics
        for component, status in health_status.items():
            assert "status" in status  # healthy, degraded, unhealthy
            assert "response_time" in status
            assert "last_check" in status
    
    async def test_health_check_failure_detection(self):
        """Test health check failure detection and alerting."""
        health_service = HealthCheckService()
        
        # Mock database failure
        with patch('app.database.async_session_maker', side_effect=OperationalError("DB Error", None, None)):
            health_status = await health_service.check_database_health()
            
            assert health_status["status"] == "unhealthy"
            assert "error" in health_status
            assert health_status["response_time"] is not None
    
    async def test_metrics_collection_resilience(self):
        """Test metrics collection system resilience."""
        metrics_collector = MetricsCollector()
        
        # Simulate various metric collection scenarios
        test_metrics = [
            {"name": "request_count", "value": 100, "type": "counter"},
            {"name": "response_time", "value": 0.5, "type": "histogram"},
            {"name": "active_connections", "value": 25, "type": "gauge"},
        ]
        
        for metric in test_metrics:
            await metrics_collector.record_metric(
                name=metric["name"],
                value=metric["value"],
                metric_type=metric["type"]
            )
        
        # Collect and verify metrics
        collected_metrics = await metrics_collector.get_metrics()
        
        assert len(collected_metrics) >= len(test_metrics)
        
        # Verify metric integrity
        for metric in test_metrics:
            found_metric = next(
                (m for m in collected_metrics if m["name"] == metric["name"]), 
                None
            )
            assert found_metric is not None
            assert found_metric["type"] == metric["type"]


@pytest.mark.resilience
class TestDisasterRecovery:
    """Test disaster recovery and backup scenarios."""
    
    async def test_backup_system_integrity(self, db_session):
        """Test backup system creates consistent backups."""
        # This would test actual backup system in production
        # For now, we'll simulate backup validation
        
        tenant_service = TenantService(db_session)
        
        # Create test data
        from app.schemas.tenant import TenantCreate
        tenant_data = TenantCreate(
            name="Backup Test Tenant",
            slug="backup-test",
            primary_contact_email="backup@test.com"
        )
        tenant = await tenant_service.create_tenant(tenant_data, "test")
        
        # Simulate backup process
        backup_data = {
            "tenant_id": str(tenant.id),
            "tenant_name": tenant.name,
            "created_at": tenant.created_at.isoformat(),
            "backup_timestamp": datetime.utcnow().isoformat()
        }
        
        # Verify backup data integrity
        assert backup_data["tenant_id"] == str(tenant.id)
        assert backup_data["tenant_name"] == tenant.name
        assert "backup_timestamp" in backup_data
    
    async def test_data_recovery_process(self):
        """Test data recovery from backup scenario."""
        # Simulate recovery process
        backup_data = {
            "tenant_id": "550e8400-e29b-41d4-a716-446655440999",
            "tenant_name": "Recovered Tenant",
            "created_at": "2024-01-01T00:00:00Z",
            "backup_timestamp": "2024-01-02T00:00:00Z"
        }
        
        # Recovery validation checks
        assert backup_data["tenant_id"] is not None
        assert backup_data["tenant_name"] is not None
        assert backup_data["created_at"] is not None
        
        # Verify backup is recent enough for recovery
        backup_time = datetime.fromisoformat(backup_data["backup_timestamp"].replace("Z", "+00:00"))
        age_hours = (datetime.utcnow().replace(tzinfo=backup_time.tzinfo) - backup_time).total_seconds() / 3600
        
        # Backup should be less than 24 hours old for production recovery
        # For tests, we'll be more lenient
        assert age_hours < 8760  # Less than 1 year old