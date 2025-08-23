"""
Example performance tests using pytest-benchmark and load testing concepts.

This demonstrates best practices for testing:
- Benchmark critical operations
- Memory usage testing
- Concurrent operation testing
- Performance regression detection
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List
from uuid import uuid4

import pytest
import pytest_asyncio
import psutil
from httpx import AsyncClient


# Performance test fixtures
@pytest.fixture
def performance_sample_data():
    """Sample data for performance testing."""
    return {
        'email': f'perf_test_{uuid4()}@example.com',
        'first_name': 'Performance',
        'last_name': 'Test',
        'tenant_id': 'perf-tenant'
    }


@pytest_asyncio.fixture
async def performance_client():
    """HTTP client for performance testing."""
    async with AsyncClient(base_url="http://localhost:8000") as client:
        yield client


# Benchmark tests
@pytest.mark.performance
@pytest.mark.benchmark
class TestModelPerformance:
    """Performance tests for data models."""
    
    def test_customer_model_creation_benchmark(self, benchmark, performance_sample_data):
        """Benchmark customer model creation."""
        from pydantic import BaseModel, Field
        from typing import Optional
        
        class Customer(BaseModel):
            id: Optional[str] = Field(default_factory=lambda: str(uuid4()))
            email: str
            first_name: str
            last_name: str
            tenant_id: str
        
        def create_customer():
            return Customer(**performance_sample_data)
        
        result = benchmark(create_customer)
        assert result.email == performance_sample_data['email']
        
        # Performance assertion - should create model in under 1ms
        assert benchmark.stats.mean < 0.001
    
    def test_customer_model_validation_benchmark(self, benchmark):
        """Benchmark customer model validation."""
        from pydantic import BaseModel, Field, validator
        from typing import Optional
        
        class Customer(BaseModel):
            id: Optional[str] = Field(default_factory=lambda: str(uuid4()))
            email: str
            first_name: str
            last_name: str
            tenant_id: str
            
            @validator('email')
            def validate_email_domain(cls, v):
                if '@' not in v:
                    raise ValueError('Invalid email')
                return v
            
            @validator('first_name', 'last_name')
            def validate_names(cls, v):
                if len(v) < 1:
                    raise ValueError('Name too short')
                return v
        
        test_data = {
            'email': 'benchmark@example.com',
            'first_name': 'Benchmark',
            'last_name': 'User',
            'tenant_id': 'bench-tenant'
        }
        
        def validate_customer():
            return Customer(**test_data)
        
        result = benchmark(validate_customer)
        assert result.email == 'benchmark@example.com'
    
    def test_json_serialization_benchmark(self, benchmark):
        """Benchmark JSON serialization."""
        from pydantic import BaseModel
        
        class Customer(BaseModel):
            id: str
            email: str
            first_name: str
            last_name: str
            tenant_id: str
            created_at: datetime
        
        customer = Customer(
            id=str(uuid4()),
            email='serialize@example.com',
            first_name='Serialize',
            last_name='Test',
            tenant_id='serialize-tenant',
            created_at=datetime.now()
        )
        
        def serialize_customer():
            return customer.json()
        
        result = benchmark(serialize_customer)
        assert isinstance(result, str)
        assert 'serialize@example.com' in result


@pytest.mark.performance
@pytest.mark.benchmark
class TestDatabasePerformance:
    """Performance tests for database operations."""
    
    @pytest.mark.asyncio
    async def test_database_connection_benchmark(self, benchmark):
        """Benchmark database connection time."""
        import asyncpg
        import os
        
        database_url = os.getenv("TEST_DATABASE_URL")
        if not database_url:
            pytest.skip("No database URL provided")
        
        async def connect_to_database():
            conn = await asyncpg.connect(database_url)
            await conn.close()
        
        def sync_connect():
            return asyncio.run(connect_to_database())
        
        benchmark(sync_connect)
        
        # Connection should establish quickly
        assert benchmark.stats.mean < 0.1  # 100ms
    
    @pytest.mark.asyncio
    async def test_simple_query_benchmark(self, benchmark):
        """Benchmark simple database query."""
        import asyncpg
        import os
        
        database_url = os.getenv("TEST_DATABASE_URL")
        if not database_url:
            pytest.skip("No database URL provided")
        
        async def run_simple_query():
            conn = await asyncpg.connect(database_url)
            try:
                result = await conn.fetchval("SELECT 1")
                return result
            finally:
                await conn.close()
        
        def sync_query():
            return asyncio.run(run_simple_query())
        
        result = benchmark(sync_query)
        assert result == 1
        
        # Simple query should be fast
        assert benchmark.stats.mean < 0.05  # 50ms


@pytest.mark.performance 
@pytest.mark.asyncio
class TestAsyncPerformance:
    """Performance tests for async operations."""
    
    async def test_concurrent_operations_performance(self, benchmark):
        """Test performance of concurrent operations."""
        
        async def async_operation(delay: float):
            await asyncio.sleep(delay)
            return "completed"
        
        async def run_concurrent_operations():
            tasks = [async_operation(0.01) for _ in range(10)]
            return await asyncio.gather(*tasks)
        
        def run_test():
            return asyncio.run(run_concurrent_operations())
        
        result = benchmark(run_test)
        assert len(result) == 10
        assert all(r == "completed" for r in result)
        
        # Concurrent operations should be faster than sequential
        # 10 * 0.01 = 0.1s sequential, should be much faster concurrent
        assert benchmark.stats.mean < 0.05
    
    async def test_sequential_vs_concurrent_benchmark(self):
        """Compare sequential vs concurrent operation performance."""
        
        async def async_operation(delay: float):
            await asyncio.sleep(delay)
            return "completed"
        
        # Measure sequential execution
        start_time = time.time()
        sequential_results = []
        for _ in range(5):
            result = await async_operation(0.02)
            sequential_results.append(result)
        sequential_time = time.time() - start_time
        
        # Measure concurrent execution
        start_time = time.time()
        tasks = [async_operation(0.02) for _ in range(5)]
        concurrent_results = await asyncio.gather(*tasks)
        concurrent_time = time.time() - start_time
        
        # Concurrent should be significantly faster
        assert concurrent_time < sequential_time * 0.5
        assert len(sequential_results) == len(concurrent_results) == 5


@pytest.mark.performance
@pytest.mark.memory
class TestMemoryUsage:
    """Test memory usage patterns."""
    
    def test_memory_usage_customer_creation(self):
        """Test memory usage during customer creation."""
        from pydantic import BaseModel
        from typing import List
        
        class Customer(BaseModel):
            id: str
            email: str
            first_name: str
            last_name: str
            tenant_id: str
        
        # Measure memory before
        process = psutil.Process()
        memory_before = process.memory_info().rss
        
        # Create many customers
        customers: List[Customer] = []
        for i in range(1000):
            customer = Customer(
                id=str(uuid4()),
                email=f'memory_test_{i}@example.com',
                first_name=f'User{i}',
                last_name='Test',
                tenant_id='memory-tenant'
            )
            customers.append(customer)
        
        # Measure memory after
        memory_after = process.memory_info().rss
        memory_used = (memory_after - memory_before) / 1024 / 1024  # MB
        
        # Should not use excessive memory (less than 50MB for 1000 customers)
        assert memory_used < 50
        assert len(customers) == 1000
    
    def test_memory_leak_detection(self):
        """Test for memory leaks in repeated operations."""
        from pydantic import BaseModel
        
        class Customer(BaseModel):
            id: str
            email: str
            first_name: str
            last_name: str
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Perform operations multiple times
        for iteration in range(10):
            # Create and destroy many objects
            customers = []
            for i in range(100):
                customer = Customer(
                    id=str(uuid4()),
                    email=f'leak_test_{iteration}_{i}@example.com',
                    first_name=f'User{i}',
                    last_name='Test'
                )
                customers.append(customer)
            
            # Clear references
            customers.clear()
            del customers
        
        final_memory = process.memory_info().rss
        memory_growth = (final_memory - initial_memory) / 1024 / 1024  # MB
        
        # Should not have significant memory growth (less than 10MB)
        assert memory_growth < 10


@pytest.mark.performance
@pytest.mark.stress
class TestStressAndLoad:
    """Stress testing and load testing."""
    
    def test_high_volume_data_processing(self, benchmark):
        """Test processing high volume of data."""
        
        def process_large_dataset():
            # Simulate processing large dataset
            data = []
            for i in range(10000):
                record = {
                    'id': str(uuid4()),
                    'email': f'volume_test_{i}@example.com',
                    'created_at': datetime.now(),
                    'score': i * 1.5
                }
                data.append(record)
            
            # Process data (sort by score)
            sorted_data = sorted(data, key=lambda x: x['score'], reverse=True)
            return len(sorted_data)
        
        result = benchmark(process_large_dataset)
        assert result == 10000
        
        # Should complete within reasonable time
        assert benchmark.stats.mean < 1.0  # 1 second
    
    @pytest.mark.asyncio
    async def test_concurrent_client_simulation(self):
        """Simulate multiple concurrent clients."""
        
        async def simulate_client(client_id: int):
            """Simulate a single client's operations."""
            operations = []
            
            # Simulate various operations with delays
            for op in range(5):
                start_time = time.time()
                
                # Simulate different operation types
                if op % 3 == 0:
                    await asyncio.sleep(0.01)  # Fast operation
                elif op % 3 == 1:
                    await asyncio.sleep(0.05)  # Medium operation
                else:
                    await asyncio.sleep(0.02)  # Database operation
                
                end_time = time.time()
                operations.append({
                    'client_id': client_id,
                    'operation': op,
                    'duration': end_time - start_time
                })
            
            return operations
        
        # Simulate 20 concurrent clients
        start_time = time.time()
        tasks = [simulate_client(i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Verify results
        total_operations = sum(len(client_ops) for client_ops in results)
        assert total_operations == 100  # 20 clients * 5 operations
        
        # Should complete much faster than sequential (20 * 5 * avg_delay)
        expected_sequential_time = 20 * 5 * 0.027  # Average delay
        assert total_time < expected_sequential_time * 0.5
    
    def test_thread_pool_performance(self, benchmark):
        """Test thread pool performance for CPU-bound operations."""
        
        def cpu_intensive_operation(n: int):
            """Simulate CPU-intensive operation."""
            result = 0
            for i in range(n):
                result += i ** 2
            return result
        
        def run_with_thread_pool():
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(cpu_intensive_operation, 1000) for _ in range(8)]
                results = [future.result() for future in futures]
            return results
        
        results = benchmark(run_with_thread_pool)
        assert len(results) == 8
        
        # Should complete within reasonable time
        assert benchmark.stats.mean < 0.5  # 500ms


@pytest.mark.performance
@pytest.mark.regression
class TestPerformanceRegression:
    """Performance regression testing."""
    
    def test_customer_creation_performance_baseline(self, benchmark):
        """Baseline performance test for customer creation."""
        from pydantic import BaseModel
        
        class Customer(BaseModel):
            id: str
            email: str
            first_name: str
            last_name: str
            tenant_id: str
        
        def create_100_customers():
            customers = []
            for i in range(100):
                customer = Customer(
                    id=str(uuid4()),
                    email=f'baseline_{i}@example.com',
                    first_name=f'User{i}',
                    last_name='Test',
                    tenant_id='baseline-tenant'
                )
                customers.append(customer)
            return customers
        
        result = benchmark(create_100_customers)
        assert len(result) == 100
        
        # Store baseline - in real scenario, you'd compare with previous runs
        baseline_time = benchmark.stats.mean
        
        # Should meet performance baseline (adjust as needed)
        assert baseline_time < 0.05  # 50ms for 100 customers
    
    @pytest.mark.parametrize("record_count", [100, 500, 1000])
    def test_scalability_performance(self, benchmark, record_count):
        """Test performance scaling with different data sizes."""
        
        def process_records(count: int):
            records = []
            for i in range(count):
                record = {
                    'id': str(uuid4()),
                    'data': f'record_{i}',
                    'timestamp': datetime.now()
                }
                records.append(record)
            
            # Process records (simple aggregation)
            total_length = sum(len(r['data']) for r in records)
            return total_length
        
        result = benchmark(process_records, record_count)
        assert result > 0
        
        # Performance should scale reasonably
        time_per_record = benchmark.stats.mean / record_count
        assert time_per_record < 0.0001  # 0.1ms per record


@pytest.mark.performance
@pytest.mark.integration
@pytest.mark.asyncio
class TestAPIPerformance:
    """Performance tests for API endpoints."""
    
    async def test_api_response_time(self, performance_client):
        """Test API response time."""
        # Test health endpoint response time
        start_time = time.time()
        response = await performance_client.get("/health")
        response_time = time.time() - start_time
        
        assert response.status_code in [200, 503]
        assert response_time < 0.1  # 100ms
    
    async def test_concurrent_api_requests(self, performance_client):
        """Test concurrent API request performance."""
        
        async def make_request():
            response = await performance_client.get("/health")
            return response.status_code
        
        # Make 20 concurrent requests
        start_time = time.time()
        tasks = [make_request() for _ in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Count successful requests
        successful_requests = sum(1 for r in results if r in [200, 503])
        assert successful_requests >= 15  # At least 75% success rate
        
        # Should handle concurrent requests efficiently
        assert total_time < 2.0  # 2 seconds for 20 requests
        
        # Average request time should be reasonable
        avg_request_time = total_time / 20
        assert avg_request_time < 0.2  # 200ms average


# Performance test utilities
class PerformanceMonitor:
    """Utility class for monitoring performance during tests."""
    
    def __init__(self):
        self.start_time = None
        self.start_memory = None
        self.measurements = []
    
    def start(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        process = psutil.Process()
        self.start_memory = process.memory_info().rss
    
    def checkpoint(self, label: str):
        """Record a performance checkpoint."""
        current_time = time.time()
        process = psutil.Process()
        current_memory = process.memory_info().rss
        
        measurement = {
            'label': label,
            'elapsed_time': current_time - self.start_time,
            'memory_mb': (current_memory - self.start_memory) / 1024 / 1024
        }
        self.measurements.append(measurement)
        return measurement
    
    def get_report(self) -> Dict:
        """Get performance report."""
        return {
            'total_time': self.measurements[-1]['elapsed_time'] if self.measurements else 0,
            'peak_memory': max((m['memory_mb'] for m in self.measurements), default=0),
            'checkpoints': self.measurements
        }


@pytest.mark.performance
def test_performance_monitor_utility():
    """Test the performance monitoring utility."""
    monitor = PerformanceMonitor()
    monitor.start()
    
    # Simulate some work
    time.sleep(0.1)
    checkpoint1 = monitor.checkpoint("after_sleep")
    
    # Simulate more work
    data = [i**2 for i in range(1000)]
    checkpoint2 = monitor.checkpoint("after_computation")
    
    report = monitor.get_report()
    
    assert checkpoint1['elapsed_time'] >= 0.1
    assert checkpoint2['elapsed_time'] > checkpoint1['elapsed_time']
    assert report['total_time'] >= 0.1
    assert len(report['checkpoints']) == 2