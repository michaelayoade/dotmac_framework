"""
Performance and Transaction Integration Tests - Load testing, database transactions, and performance benchmarks.
Tests system performance under load, transaction management, and resource utilization patterns.
"""
import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from tests.utilities.integration_test_base import (
    PerformanceIntegrationTestBase,
    TransactionIntegrationTestBase,
)


class TestDatabaseTransactionPerformance(TransactionIntegrationTestBase):
    """Test database transaction performance and concurrency patterns."""

    def setup_method(self):
        """Setup transaction performance testing."""
        super().setup_method()

        # Create transaction manager with performance settings
        self.transaction_manager = self.create_transaction_manager(
            max_retries=3,
            retry_delay=0.1  # Fast retry for testing
        )

        # Create mock database operations
        self.db_operations = {
            "read_operation": AsyncMock(),
            "write_operation": AsyncMock(),
            "complex_query": AsyncMock(),
            "batch_insert": AsyncMock()
        }

        # Setup operation responses
        self.db_operations["read_operation"].return_value = {"id": "record-123", "data": "test"}
        self.db_operations["write_operation"].return_value = {"inserted": True, "id": "new-123"}
        self.db_operations["complex_query"].return_value = [{"id": f"result-{i}"} for i in range(10)]
        self.db_operations["batch_insert"].return_value = {"inserted_count": 100}

    @pytest.mark.asyncio
    async def test_concurrent_transaction_performance(self):
        """Test concurrent transaction performance under load."""
        async def transaction_operation(operation_id: int, context: dict[str, Any]):
            """Simulate a database transaction operation."""
            session = self.create_mock_async_session(f"session-{operation_id}")

            async with self.mock_database_transaction(session):
                # Simulate database operations
                await self.db_operations["read_operation"](f"read-{operation_id}")
                await self.db_operations["write_operation"](f"write-{operation_id}")
                await asyncio.sleep(0.01)  # Simulate processing time

                return {
                    "operation_id": operation_id,
                    "session_id": f"session-{operation_id}",
                    "status": "completed"
                }

        # Run concurrent transactions
        metrics = await self.simulate_concurrent_operations(
            operation_factory=transaction_operation,
            concurrency_level=10,
            operation_count=50,
            context={"test_type": "transaction_performance"}
        )

        # Performance assertions
        self.assert_performance_within_limits(
            test_id=metrics["test_id"],
            max_average_duration=0.5,  # Max 0.5 seconds per transaction
            min_success_rate=95.0      # At least 95% success rate
        )

        # Verify database operations were called
        assert self.db_operations["read_operation"].call_count == 50
        assert self.db_operations["write_operation"].call_count == 50

    @pytest.mark.asyncio
    async def test_transaction_retry_performance(self):
        """Test transaction retry mechanism performance."""
        retry_count = 0

        def flaky_database_operation():
            nonlocal retry_count
            retry_count += 1

            # Fail first two attempts, succeed on third
            if retry_count <= 2:
                raise Exception(f"Database timeout #{retry_count}")

            return {"success": True, "attempts": retry_count}

        # Create retry policy
        self.create_retry_policy("flaky_db_op", max_attempts=3, backoff_factor=1.2)

        start_time = time.time()
        result = await self.execute_with_retry(flaky_database_operation, "flaky_db_op")
        end_time = time.time()

        # Verify retry worked
        assert result["success"] is True
        assert result["attempts"] == 3

        # Verify performance (should complete reasonably quickly)
        total_time = end_time - start_time
        assert total_time < 1.0  # Should complete in less than 1 second

        # Verify retry policy was used
        policy = self.retry_policies["flaky_db_op"]
        assert policy["current_attempt"] == 3
        assert len(policy["delays"]) == 2

    @pytest.mark.asyncio
    async def test_distributed_transaction_performance(self):
        """Test distributed transaction (saga) performance."""
        # Create services for distributed transaction
        services = {
            "payment_service": self.create_integration_service("payment_service"),
            "inventory_service": self.create_integration_service("inventory_service"),
            "shipping_service": self.create_integration_service("shipping_service")
        }

        self.create_service_registry(services)

        # Setup service responses with simulated delays
        async def slow_payment_operation(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms delay
            return {"payment_id": "pay-123", "status": "completed"}

        async def slow_inventory_operation(*args, **kwargs):
            await asyncio.sleep(0.03)  # 30ms delay
            return {"reservation_id": "res-123", "status": "reserved"}

        async def slow_shipping_operation(*args, **kwargs):
            await asyncio.sleep(0.02)  # 20ms delay
            return {"shipment_id": "ship-123", "status": "scheduled"}

        # Replace mock responses with delayed operations
        self.service_registry["payment_service"].process = slow_payment_operation
        self.service_registry["inventory_service"].process = slow_inventory_operation
        self.service_registry["shipping_service"].process = slow_shipping_operation

        operations = [
            {"service": "payment_service", "method": "process", "kwargs": {"amount": 100.00}},
            {"service": "inventory_service", "method": "process", "kwargs": {"items": ["item-1"]}},
            {"service": "shipping_service", "method": "process", "kwargs": {"address": "123 Main St"}}
        ]

        start_time = time.time()
        result = await self.simulate_distributed_transaction(operations)
        end_time = time.time()

        # Verify transaction completed
        assert result["status"] == "completed"
        assert len(result["completed_operations"]) == 3

        # Verify performance (should complete in reasonable time)
        total_time = end_time - start_time
        assert total_time < 0.2  # Should complete in less than 200ms (operations run sequentially)

    @pytest.mark.asyncio
    async def test_database_connection_pool_performance(self):
        """Test database connection pool performance simulation."""
        # Create connection pool mock
        connection_pool = Mock()
        connection_pool.get_connection = AsyncMock()
        connection_pool.return_connection = AsyncMock()
        connection_pool.pool_size = 10
        connection_pool.active_connections = 0

        async def database_operation_with_pool(operation_id: int, context: dict[str, Any]):
            """Simulate database operation using connection pool."""
            # Get connection from pool
            connection = await connection_pool.get_connection()
            connection_pool.active_connections += 1

            try:
                # Simulate database operation
                await asyncio.sleep(0.01)  # Database operation time
                await self.db_operations["read_operation"](f"pool-op-{operation_id}")

                return {
                    "operation_id": operation_id,
                    "connection_id": f"conn-{operation_id % 10}",  # Simulate pool reuse
                    "status": "completed"
                }
            finally:
                # Return connection to pool
                await connection_pool.return_connection(connection)
                connection_pool.active_connections -= 1

        # Test connection pool under load
        metrics = await self.simulate_concurrent_operations(
            operation_factory=database_operation_with_pool,
            concurrency_level=15,  # More concurrent ops than pool size
            operation_count=100,
            context={"pool_size": 10}
        )

        # Performance assertions
        self.assert_performance_within_limits(
            test_id=metrics["test_id"],
            max_average_duration=0.1,  # Max 100ms per operation
            min_success_rate=100.0     # All operations should succeed
        )

        # Verify connection pool usage
        assert connection_pool.get_connection.call_count == 100
        assert connection_pool.return_connection.call_count == 100


class TestServicePerformanceBenchmarks(PerformanceIntegrationTestBase):
    """Test service performance benchmarks and load testing."""

    def setup_method(self):
        """Setup service performance testing."""
        super().setup_method()

        # Create performance-critical services
        self.perf_services = {
            "api_service": self.create_api_service(),
            "cache_service": self.create_cache_service(),
            "data_service": self.create_data_service(),
            "search_service": self.create_search_service()
        }

        # Create resource monitor
        self.resource_monitor = self.create_resource_monitor()

    def create_api_service(self) -> Mock:
        """Create API service mock with performance characteristics."""
        service = Mock()
        service.name = "api_service"

        # Add performance-sensitive methods
        service.handle_request = AsyncMock()
        service.process_batch = AsyncMock()
        service.validate_input = AsyncMock()

        # Setup realistic response times
        async def slow_handle_request(*args, **kwargs):
            await asyncio.sleep(0.02)  # 20ms response time
            return {"status": "success", "data": {"processed": True}}

        service.handle_request.side_effect = slow_handle_request
        service.validate_input.return_value = {"valid": True}

        return service

    def create_cache_service(self) -> Mock:
        """Create cache service mock."""
        service = Mock()
        service.name = "cache_service"

        service.get = AsyncMock()
        service.set = AsyncMock()
        service.delete = AsyncMock()
        service.clear = AsyncMock()

        # Setup cache hit/miss simulation
        cache_data = {}

        async def cache_get(key):
            await asyncio.sleep(0.001)  # 1ms cache access time
            return cache_data.get(key)

        async def cache_set(key, value):
            await asyncio.sleep(0.001)
            cache_data[key] = value
            return True

        service.get.side_effect = cache_get
        service.set.side_effect = cache_set

        return service

    def create_data_service(self) -> Mock:
        """Create data service mock."""
        service = Mock()
        service.name = "data_service"

        service.fetch_data = AsyncMock()
        service.process_data = AsyncMock()
        service.store_data = AsyncMock()

        # Setup data processing with realistic delays
        async def fetch_data(query):
            await asyncio.sleep(0.05)  # 50ms database query
            return [{"id": i, "data": f"record-{i}"} for i in range(10)]

        service.fetch_data.side_effect = fetch_data

        return service

    def create_search_service(self) -> Mock:
        """Create search service mock."""
        service = Mock()
        service.name = "search_service"

        service.search = AsyncMock()
        service.index_document = AsyncMock()
        service.faceted_search = AsyncMock()

        # Setup search with variable response times
        async def search_operation(query):
            # Complex queries take longer
            delay = 0.01 if len(query) < 10 else 0.03
            await asyncio.sleep(delay)

            return {
                "results": [{"id": i, "score": 0.9 - i*0.1} for i in range(5)],
                "total": 5,
                "took_ms": delay * 1000
            }

        service.search.side_effect = search_operation

        return service

    @pytest.mark.asyncio
    async def test_api_service_load_performance(self):
        """Test API service performance under load."""
        api_service = self.perf_services["api_service"]

        async def api_request_operation(operation_id: int, context: dict[str, Any]):
            """Simulate API request."""
            request_data = {
                "id": operation_id,
                "endpoint": "/api/users",
                "method": "GET",
                "params": {"limit": 10}
            }

            # Validate and handle request
            validation_result = await api_service.validate_input(request_data)
            if validation_result["valid"]:
                response = await api_service.handle_request(request_data)
                return response
            else:
                return {"status": "error", "message": "Invalid request"}

        # Run load test
        metrics = await self.simulate_concurrent_operations(
            operation_factory=api_request_operation,
            concurrency_level=20,
            operation_count=200,
            context={"load_test": "api_performance"}
        )

        # API performance assertions
        self.assert_performance_within_limits(
            test_id=metrics["test_id"],
            max_average_duration=0.1,    # Max 100ms average response time
            min_success_rate=99.0,       # 99% success rate
            max_operations_per_second=500 # Max throughput limit
        )

        # Verify API service was called appropriately
        assert api_service.handle_request.call_count == 200
        assert api_service.validate_input.call_count == 200

    @pytest.mark.asyncio
    async def test_cache_performance_patterns(self):
        """Test cache service performance patterns."""
        cache_service = self.perf_services["cache_service"]

        async def cache_operation(operation_id: int, context: dict[str, Any]):
            """Simulate cache operations with read/write patterns."""
            key = f"cache_key_{operation_id % 50}"  # Create key collisions for realistic testing

            # 70% reads, 30% writes
            if operation_id % 10 < 7:
                # Read operation
                value = await cache_service.get(key)
                if value is None:
                    # Cache miss - simulate fetch from source
                    value = f"data_for_{key}"
                    await cache_service.set(key, value)
                return {"operation": "read", "cache_hit": value is not None}
            else:
                # Write operation
                value = f"updated_data_{operation_id}"
                await cache_service.set(key, value)
                return {"operation": "write", "key": key}

        # Test cache performance
        metrics = await self.simulate_concurrent_operations(
            operation_factory=cache_operation,
            concurrency_level=25,
            operation_count=1000,
            context={"cache_test": "read_write_pattern"}
        )

        # Cache performance assertions
        self.assert_performance_within_limits(
            test_id=metrics["test_id"],
            max_average_duration=0.01,  # Cache operations should be very fast
            min_success_rate=99.5       # Cache should be highly reliable
        )

        # Verify cache usage patterns
        assert cache_service.get.call_count >= 700  # Approximately 70% reads
        assert cache_service.set.call_count >= 300  # Writes + cache misses

    @pytest.mark.asyncio
    async def test_data_processing_pipeline_performance(self):
        """Test data processing pipeline performance."""
        data_service = self.perf_services["data_service"]
        cache_service = self.perf_services["cache_service"]

        # Setup data processing pipeline
        async def data_pipeline_operation(operation_id: int, context: dict[str, Any]):
            """Simulate data processing pipeline."""
            query = f"SELECT * FROM table WHERE id > {operation_id * 100}"

            # Check cache first
            cache_key = f"query_result_{hash(query) % 1000}"
            cached_result = await cache_service.get(cache_key)

            if cached_result:
                return {"source": "cache", "records": len(cached_result)}

            # Fetch from database
            raw_data = await data_service.fetch_data(query)

            # Process data
            await data_service.process_data(raw_data)

            # Store in cache
            await cache_service.set(cache_key, raw_data)

            return {"source": "database", "records": len(raw_data)}

        # Test pipeline performance
        metrics = await self.simulate_concurrent_operations(
            operation_factory=data_pipeline_operation,
            concurrency_level=15,
            operation_count=100,
            context={"pipeline_test": "data_processing"}
        )

        # Pipeline performance assertions
        self.assert_performance_within_limits(
            test_id=metrics["test_id"],
            max_average_duration=0.15,  # Max 150ms for pipeline operation
            min_success_rate=98.0       # 98% success rate for data pipeline
        )

    @pytest.mark.asyncio
    async def test_search_performance_under_load(self):
        """Test search service performance under various query loads."""
        search_service = self.perf_services["search_service"]

        # Define different query patterns
        query_patterns = [
            "simple",           # Simple queries (fast)
            "complex search term with multiple words",  # Complex queries (slower)
            "user",             # Common term (cached)
            "very specific and unique search term that rarely appears"  # Specific queries
        ]

        async def search_operation(operation_id: int, context: dict[str, Any]):
            """Simulate search operations."""
            query = query_patterns[operation_id % len(query_patterns)]

            # Execute search
            results = await search_service.search(query)

            return {
                "query_length": len(query),
                "results_count": results["total"],
                "response_time": results["took_ms"]
            }

        # Test search performance
        metrics = await self.simulate_concurrent_operations(
            operation_factory=search_operation,
            concurrency_level=30,
            operation_count=400,
            context={"search_test": "mixed_queries"}
        )

        # Search performance assertions
        self.assert_performance_within_limits(
            test_id=metrics["test_id"],
            max_average_duration=0.05,  # Max 50ms average search time
            min_success_rate=99.0       # 99% search success rate
        )

        assert search_service.search.call_count == 400


class TestResourceUtilizationMonitoring(PerformanceIntegrationTestBase):
    """Test resource utilization monitoring and performance metrics."""

    def setup_method(self):
        """Setup resource monitoring tests."""
        super().setup_method()

        # Create resource monitors for different components
        self.monitors = {
            "database_monitor": self.create_database_monitor(),
            "cache_monitor": self.create_cache_monitor(),
            "api_monitor": self.create_api_monitor()
        }

        # Create performance metrics collector
        self.metrics_collector = self.create_metrics_collector()

    def create_database_monitor(self) -> Mock:
        """Create database resource monitor."""
        monitor = Mock()
        monitor.name = "database_monitor"

        monitor.get_connection_count = Mock(return_value=15)
        monitor.get_active_queries = Mock(return_value=8)
        monitor.get_slow_queries = Mock(return_value=2)
        monitor.get_deadlock_count = Mock(return_value=0)
        monitor.get_table_stats = Mock(return_value={"tables": 50, "total_size_mb": 1024})

        return monitor

    def create_cache_monitor(self) -> Mock:
        """Create cache resource monitor."""
        monitor = Mock()
        monitor.name = "cache_monitor"

        monitor.get_hit_ratio = Mock(return_value=0.85)
        monitor.get_memory_usage = Mock(return_value={"used_mb": 256, "max_mb": 512})
        monitor.get_eviction_count = Mock(return_value=10)
        monitor.get_key_count = Mock(return_value=10000)

        return monitor

    def create_api_monitor(self) -> Mock:
        """Create API resource monitor."""
        monitor = Mock()
        monitor.name = "api_monitor"

        monitor.get_request_rate = Mock(return_value=150.5)  # requests per second
        monitor.get_error_rate = Mock(return_value=0.02)     # 2% error rate
        monitor.get_response_times = Mock(return_value={
            "p50": 45.2,
            "p90": 78.5,
            "p95": 95.1,
            "p99": 150.3
        })
        monitor.get_active_connections = Mock(return_value=25)

        return monitor

    def create_metrics_collector(self) -> Mock:
        """Create metrics collector service."""
        collector = Mock()
        collector.name = "metrics_collector"

        collector.collect_metrics = AsyncMock()
        collector.store_metrics = AsyncMock()
        collector.check_thresholds = AsyncMock()
        collector.generate_alerts = AsyncMock()

        return collector

    @pytest.mark.asyncio
    async def test_resource_monitoring_integration(self):
        """Test integration of resource monitoring across components."""
        # Collect metrics from all monitors
        all_metrics = {}

        # Database metrics
        db_metrics = {
            "connections": self.monitors["database_monitor"].get_connection_count(),
            "active_queries": self.monitors["database_monitor"].get_active_queries(),
            "slow_queries": self.monitors["database_monitor"].get_slow_queries(),
            "deadlocks": self.monitors["database_monitor"].get_deadlock_count()
        }
        all_metrics["database"] = db_metrics

        # Cache metrics
        cache_metrics = {
            "hit_ratio": self.monitors["cache_monitor"].get_hit_ratio(),
            "memory_usage": self.monitors["cache_monitor"].get_memory_usage(),
            "evictions": self.monitors["cache_monitor"].get_eviction_count(),
            "keys": self.monitors["cache_monitor"].get_key_count()
        }
        all_metrics["cache"] = cache_metrics

        # API metrics
        api_metrics = {
            "request_rate": self.monitors["api_monitor"].get_request_rate(),
            "error_rate": self.monitors["api_monitor"].get_error_rate(),
            "response_times": self.monitors["api_monitor"].get_response_times(),
            "connections": self.monitors["api_monitor"].get_active_connections()
        }
        all_metrics["api"] = api_metrics

        # Store metrics
        await self.metrics_collector.store_metrics(all_metrics)

        # Check performance thresholds
        await self.metrics_collector.check_thresholds(all_metrics)

        # Verify metrics collection
        self.metrics_collector.store_metrics.assert_called_once_with(all_metrics)
        self.metrics_collector.check_thresholds.assert_called_once_with(all_metrics)

        # Verify metric values are reasonable
        assert db_metrics["connections"] == 15
        assert db_metrics["deadlocks"] == 0
        assert cache_metrics["hit_ratio"] == 0.85
        assert api_metrics["error_rate"] == 0.02

    @pytest.mark.asyncio
    async def test_performance_threshold_alerting(self):
        """Test performance threshold monitoring and alerting."""
        # Setup critical metrics that breach thresholds
        critical_metrics = {
            "database": {
                "connections": 95,      # High connection count
                "slow_queries": 15,     # Too many slow queries
                "deadlocks": 3          # Deadlocks detected
            },
            "cache": {
                "hit_ratio": 0.45,     # Low cache hit ratio
                "memory_usage": {"used_mb": 480, "max_mb": 512}  # High memory usage
            },
            "api": {
                "error_rate": 0.15,    # High error rate (15%)
                "response_times": {"p95": 500.0}  # Slow response times
            }
        }

        # Setup threshold checking to return alerts
        self.metrics_collector.check_thresholds.return_value = {
            "alerts": [
                {"level": "critical", "component": "database", "metric": "connections", "value": 95},
                {"level": "warning", "component": "cache", "metric": "hit_ratio", "value": 0.45},
                {"level": "critical", "component": "api", "metric": "error_rate", "value": 0.15}
            ]
        }

        # Process metrics and check thresholds
        await self.metrics_collector.store_metrics(critical_metrics)
        threshold_results = await self.metrics_collector.check_thresholds(critical_metrics)

        # Generate alerts for threshold breaches
        await self.metrics_collector.generate_alerts(threshold_results["alerts"])

        # Verify alert generation
        self.metrics_collector.generate_alerts.assert_called_once()

        # Verify alert content
        alerts = threshold_results["alerts"]
        assert len(alerts) == 3

        critical_alerts = [a for a in alerts if a["level"] == "critical"]
        assert len(critical_alerts) == 2  # Database connections and API error rate

    @pytest.mark.asyncio
    async def test_performance_regression_detection(self):
        """Test detection of performance regressions over time."""
        # Setup historical performance baseline
        baseline_metrics = {
            "api_response_time_p95": 85.0,
            "cache_hit_ratio": 0.90,
            "database_query_time_avg": 15.0,
            "error_rate": 0.01
        }

        # Setup current performance metrics (showing regression)
        current_metrics = {
            "api_response_time_p95": 125.0,  # 47% slower
            "cache_hit_ratio": 0.75,         # 17% worse
            "database_query_time_avg": 25.0, # 67% slower
            "error_rate": 0.03               # 200% higher
        }

        # Setup regression detection
        self.metrics_collector.detect_regression = AsyncMock()
        regression_results = {
            "regressions": [
                {
                    "metric": "api_response_time_p95",
                    "baseline": 85.0,
                    "current": 125.0,
                    "change_percent": 47.1,
                    "severity": "high"
                },
                {
                    "metric": "database_query_time_avg",
                    "baseline": 15.0,
                    "current": 25.0,
                    "change_percent": 66.7,
                    "severity": "critical"
                }
            ]
        }

        self.metrics_collector.detect_regression.return_value = regression_results

        # Detect regressions
        result = await self.metrics_collector.detect_regression(baseline_metrics, current_metrics)

        # Verify regression detection
        self.metrics_collector.detect_regression.assert_called_once_with(baseline_metrics, current_metrics)

        # Verify regression results
        assert len(result["regressions"]) == 2
        assert any(r["severity"] == "critical" for r in result["regressions"])
        assert any(r["change_percent"] > 60 for r in result["regressions"])
