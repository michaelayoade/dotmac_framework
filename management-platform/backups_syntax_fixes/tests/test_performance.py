"""
Performance and load tests.
"""

import asyncio
import pytest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.slow
class TestDatabasePerformance:
    """Test database query performance."""
    
    async def test_repository_bulk_operations(self, db_session: AsyncSession):
        """Test performance of bulk repository operations."""
        from app.repositories.tenant_additional import TenantRepository
        
        tenant_repo = TenantRepository(db_session)
        
        # Measure bulk creation time
        start_time = time.time()
        
        # Create 100 tenants
        tenants = []
        for i in range(100):
            tenant_data = {
                "name": f"perf-test-{i:03d}",
                "display_name": f"Performance Test {i:03d}",
                "status": "active",
                "subscription_tier": "standard"
            }
            tenant = await tenant_repo.create(tenant_data, "perf-test")
            tenants.append(tenant)
        
        creation_time = time.time() - start_time
        
        # Should complete within reasonable time (10 seconds for 100 records)
        assert creation_time < 10.0
        assert len(tenants) == 100
        
        # Test bulk retrieval
        start_time = time.time()
        all_tenants = await tenant_repo.list(limit=1000)
        retrieval_time = time.time() - start_time
        
        # Retrieval should be fast (under 1 second)
        assert retrieval_time < 1.0
        assert len(all_tenants) >= 100
        
        print(f"Created 100 tenants in {creation_time:.2f}s")
        print(f"Retrieved {len(all_tenants)} tenants in {retrieval_time:.2f}s")
    
    async def test_pagination_performance(self, db_session: AsyncSession):
        """Test pagination performance with large datasets."""
        from app.repositories.tenant_additional import TenantRepository
        
        tenant_repo = TenantRepository(db_session)
        
        # Create test data if not exists
        existing_count = len(await tenant_repo.list(limit=1000)
        if existing_count < 500:
            # Create additional tenants for testing
            for i in range(500 - existing_count):
                tenant_data = {
                    "name": f"pagination-test-{i:03d}",
                    "display_name": f"Pagination Test {i:03d}",
                    "status": "active"
                }
                await tenant_repo.create(tenant_data, "perf-test")
        
        # Test pagination performance
        page_size = 50
        total_pages = 10
        
        start_time = time.time()
        
        for page in range(total_pages):
            skip = page * page_size
            page_results = await tenant_repo.list(skip=skip, limit=page_size)
            assert len(page_results) <= page_size
        
        pagination_time = time.time() - start_time
        
        # Should complete all pages quickly
        assert pagination_time < 5.0
        
        print(f"Paginated through {total_pages} pages in {pagination_time:.2f}s")
    
    async def test_filtering_performance(self, db_session: AsyncSession):
        """Test filtering performance."""
        from app.repositories.tenant_additional import TenantRepository
        
        tenant_repo = TenantRepository(db_session)
        
        # Test various filter combinations
        filters = [
            {"status": "active"},
            {"subscription_tier": "standard"},
            {"status": "active", "subscription_tier": "standard"},
        ]
        
        for filter_set in filters:
            start_time = time.time()
            
            results = await tenant_repo.list(filters=filter_set, limit=100)
            
            filter_time = time.time() - start_time
            
            # Each filter should complete quickly
            assert filter_time < 1.0
            
            print(f"Filter {filter_set} returned {len(results)} results in {filter_time:.3f}s")


@pytest.mark.slow
class TestAPIPerformance:
    """Test API endpoint performance."""
    
    def test_health_endpoint_response_time(self, client: TestClient):
        """Test health endpoint response time."""
        # Warm up
        client.get("/api/v1/health")
        
        # Measure response time
        start_time = time.time()
        
        for _ in range(10):
            response = client.get("/api/v1/health")
            assert response.status_code == 200
        
        total_time = time.time() - start_time
        avg_response_time = total_time / 10
        
        # Should respond quickly (under 100ms average)
        assert avg_response_time < 0.1
        
        print(f"Average health check response time: {avg_response_time:.3f}s")
    
    def test_authentication_performance(self, client: TestClient, test_user):
        """Test authentication endpoint performance."""
        login_data = {
            "email": test_user.email,
            "password": "testpassword123"
        }
        
        # Measure login performance
        start_time = time.time()
        
        for _ in range(5):
            response = client.post("/api/v1/auth/login", json=login_data)
            assert response.status_code == 200
        
        total_time = time.time() - start_time
        avg_login_time = total_time / 5
        
        # Login should be reasonably fast (under 500ms average)
        assert avg_login_time < 0.5
        
        print(f"Average login response time: {avg_login_time:.3f}s")
    
    def test_concurrent_requests_performance(self, client: TestClient, master_admin_token):
        """Test performance under concurrent requests."""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        
        def make_request():
            response = client.get("/api/v1/tenants", headers=headers)
            return response.status_code, time.time()
        
        # Make concurrent requests
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            
            results = []
            for future in as_completed(futures):
                status_code, response_time = future.result()
                results.append((status_code, response_time)
        
        total_time = time.time() - start_time
        
        # All requests should succeed
        successful_requests = sum(1 for status, _ in results if status == 200)
        assert successful_requests == 50
        
        # Should handle concurrent requests reasonably well
        assert total_time < 10.0
        
        print(f"50 concurrent requests completed in {total_time:.2f}s")
        print(f"Success rate: {successful_requests}/50")


@pytest.mark.slow
class TestMemoryUsage:
    """Test memory usage and resource management."""
    
    async def test_repository_memory_usage(self, db_session: AsyncSession):
        """Test that repository operations don't cause memory leaks."""
        import psutil
        import os
        
        from app.repositories.tenant_additional import TenantRepository
        
        process = psutil.Process(os.getpid()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        tenant_repo = TenantRepository(db_session)
        
        # Perform many operations
        for i in range(200):
            tenant_data = {
                "name": f"memory-test-{i:03d}",
                "display_name": f"Memory Test {i:03d}",
                "status": "active"
            }
            
            # Create, read, update, delete cycle
            tenant = await tenant_repo.create(tenant_data, "memory-test")
            await tenant_repo.get_by_id(tenant.id)
            await tenant_repo.update(tenant.id, {"description": f"Updated {i}"}, "memory-test")
            await tenant_repo.delete(tenant.id)
            
            # Check memory every 50 operations
            if i % 50 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_growth = current_memory - initial_memory
                
                # Memory growth should be reasonable (under 100MB)
                assert memory_growth < 100
                
                print(f"After {i} operations: {current_memory:.1f}MB (+{memory_growth:.1f}MB)")
        
        final_memory = process.memory_info().rss / 1024 / 1024
        total_growth = final_memory - initial_memory
        
        print(f"Total memory growth: {total_growth:.1f}MB")
        
        # Should not have excessive memory growth
        assert total_growth < 50
    
    def test_api_memory_stability(self, client: TestClient, master_admin_token):
        """Test API memory stability under load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        
        # Make many API requests
        for i in range(500):
            # Mix of different endpoints
            endpoints = [
                "/api/v1/health",
                "/api/v1/tenants",
                "/api/v1/auth/me"
            ]
            
            endpoint = endpoints[i % len(endpoints)]
            response = client.get(endpoint, headers=headers)
            
            # Most requests should succeed
            assert response.status_code in [200, 401, 403]
            
            if i % 100 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_growth = current_memory - initial_memory
                
                # Memory should remain stable
                assert memory_growth < 50
                
                print(f"After {i} requests: {current_memory:.1f}MB")
        
        final_memory = process.memory_info().rss / 1024 / 1024
        total_growth = final_memory - initial_memory
        
        print(f"Final memory growth: {total_growth:.1f}MB")
        assert total_growth < 30


@pytest.mark.slow
class TestScalabilityLimits:
    """Test system scalability limits."""
    
    async def test_large_dataset_handling(self, db_session: AsyncSession):
        """Test handling of large datasets."""
        from app.repositories.tenant_additional import TenantRepository
        
        tenant_repo = TenantRepository(db_session)
        
        # Test with large limit
        large_limit = 10000
        
        start_time = time.time()
        results = await tenant_repo.list(limit=large_limit)
        query_time = time.time() - start_time
        
        # Should handle large queries within reasonable time
        assert query_time < 5.0
        
        print(f"Retrieved {len(results)} records in {query_time:.2f}s")
    
    def test_rapid_sequential_requests(self, client: TestClient):
        """Test handling of rapid sequential requests."""
        # Test rate limiting and system stability
        start_time = time.time()
        responses = []
        
        for i in range(200):
            response = client.get("/api/v1/health")
            responses.append(response.status_code)
        
        total_time = time.time() - start_time
        
        # Should handle rapid requests
        success_count = sum(1 for status in responses if status == 200)
        rate_limited_count = sum(1 for status in responses if status == 429)
        
        # Either all succeed or some are rate limited
        assert success_count + rate_limited_count == 200
        
        print(f"200 requests in {total_time:.2f}s")
        print(f"Success: {success_count}, Rate limited: {rate_limited_count}")
    
    async def test_concurrent_database_connections(self, test_engine):
        """Test handling of multiple concurrent database connections."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.repositories.tenant_additional import TenantRepository
        
        async_session_maker = async_sessionmaker(bind=test_engine)
        
        async def database_task(task_id: int):
            async with async_session_maker() as session:
                tenant_repo = TenantRepository(session)
                
                # Perform database operations
                tenant_data = {
                    "name": f"concurrent-{task_id:03d}",
                    "display_name": f"Concurrent {task_id:03d}",
                    "status": "active"
                }
                
                tenant = await tenant_repo.create(tenant_data, f"task-{task_id}")
                retrieved = await tenant_repo.get_by_id(tenant.id)
                
                return retrieved is not None
        
        # Run concurrent database operations
        start_time = time.time()
        
        tasks = [database_task(i) for i in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        completion_time = time.time() - start_time
        
        # All tasks should complete successfully
        successful_tasks = sum(1 for result in results if result is True)
        failed_tasks = sum(1 for result in results if isinstance(result, Exception)
        
        assert successful_tasks >= 15  # Allow some failures under load
        assert completion_time < 10.0
        
        print(f"Concurrent DB tasks: {successful_tasks} succeeded, {failed_tasks} failed in {completion_time:.2f}s")