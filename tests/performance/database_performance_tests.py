"""
Database Performance Testing Framework
Comprehensive database performance testing under various load conditions
"""
import asyncio
import asyncpg
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import json
import random
import uuid

import psutil
import pytest


@dataclass
class DatabaseBenchmark:
    """Database benchmark configuration"""
    name: str
    query: str
    parameters: List[Any]
    expected_max_time_ms: float
    category: str  # 'read', 'write', 'transaction', 'analytics'


class DatabasePerformanceTestSuite:
    """Comprehensive database performance testing suite"""
    
    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config
        self.pool = None
        self.test_data = {}
        
    async def initialize(self):
        """Initialize database connection pool and test data"""
        self.pool = await asyncpg.create_pool(
            host=self.db_config["host"],
            port=self.db_config["port"],
            user=self.db_config["user"], 
            password=self.db_config["password"],
            database=self.db_config["database"],
            min_size=10,
            max_size=100,
            command_timeout=30
        )
        
        await self._setup_test_data()
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.pool:
            await self._cleanup_test_data()
            await self.pool.close()

    @pytest.mark.performance
    @pytest.mark.database
    async def test_read_performance_under_load(self, concurrent_users: int = 100, duration: int = 300):
        """Test database read performance under concurrent load"""
        print(f"📖 Testing read performance: {concurrent_users} concurrent users for {duration}s")
        
        read_benchmarks = [
            DatabaseBenchmark(
                name="customer_lookup_by_email",
                query="SELECT * FROM customers WHERE email = $1",
                parameters=["test_user_{}@example.com"],
                expected_max_time_ms=50.0,
                category="read"
            ),
            DatabaseBenchmark(
                name="service_plans_active",
                query="SELECT * FROM service_plans WHERE active = true ORDER BY price",
                parameters=[],
                expected_max_time_ms=100.0,
                category="read"
            ),
            DatabaseBenchmark(
                name="customer_invoice_history",
                query="""SELECT i.*, c.email FROM invoices i 
                         JOIN customers c ON i.customer_id = c.id 
                         WHERE i.customer_id = $1 
                         ORDER BY i.created_at DESC LIMIT 10""",
                parameters=["customer_{}"],
                expected_max_time_ms=150.0,
                category="read"
            ),
            DatabaseBenchmark(
                name="usage_analytics_monthly",
                query="""SELECT DATE_TRUNC('day', timestamp) as day,
                         SUM(bytes_used) as total_bytes,
                         COUNT(*) as session_count
                         FROM usage_records 
                         WHERE customer_id = $1 AND timestamp >= $2
                         GROUP BY DATE_TRUNC('day', timestamp)
                         ORDER BY day DESC""",
                parameters=["customer_{}", datetime.now() - timedelta(days=30)],
                expected_max_time_ms=500.0,
                category="analytics"
            )
        ]
        
        # Run concurrent read workload
        tasks = []
        for i in range(concurrent_users):
            task = asyncio.create_task(
                self._read_workload_worker(read_benchmarks, duration, worker_id=i)
            )
            tasks.append(task)
        
        # Monitor database during test
        monitoring_task = asyncio.create_task(
            self._monitor_database_stats(duration)
        )
        
        # Execute test
        worker_results = await asyncio.gather(*tasks)
        db_stats = await monitoring_task
        
        # Analyze results
        return self._analyze_read_performance_results(worker_results, db_stats, read_benchmarks)

    @pytest.mark.performance
    @pytest.mark.database  
    async def test_write_performance_under_load(self, concurrent_writers: int = 50, duration: int = 300):
        """Test database write performance under concurrent load"""
        print(f"✍️ Testing write performance: {concurrent_writers} concurrent writers for {duration}s")
        
        write_benchmarks = [
            DatabaseBenchmark(
                name="insert_usage_record",
                query="""INSERT INTO usage_records (customer_id, bytes_used, timestamp, session_id) 
                         VALUES ($1, $2, $3, $4)""",
                parameters=["customer_{}", "random_bytes", "timestamp", "session_{}"],
                expected_max_time_ms=100.0,
                category="write"
            ),
            DatabaseBenchmark(
                name="update_customer_last_activity",
                query="UPDATE customers SET last_activity = $1, updated_at = $1 WHERE id = $2",
                parameters=["timestamp", "customer_{}"],
                expected_max_time_ms=75.0,
                category="write"
            ),
            DatabaseBenchmark(
                name="insert_audit_log",
                query="""INSERT INTO audit_logs (customer_id, action, details, timestamp, ip_address) 
                         VALUES ($1, $2, $3, $4, $5)""",
                parameters=["customer_{}", "action", "{}", "timestamp", "192.168.1.{}"],
                expected_max_time_ms=50.0,
                category="write"
            )
        ]
        
        # Run concurrent write workload
        tasks = []
        for i in range(concurrent_writers):
            task = asyncio.create_task(
                self._write_workload_worker(write_benchmarks, duration, worker_id=i)
            )
            tasks.append(task)
        
        # Monitor lock contention and write performance
        monitoring_task = asyncio.create_task(
            self._monitor_write_performance(duration)
        )
        
        # Execute test
        writer_results = await asyncio.gather(*tasks)
        write_stats = await monitoring_task
        
        return self._analyze_write_performance_results(writer_results, write_stats, write_benchmarks)

    @pytest.mark.performance
    @pytest.mark.database
    async def test_transaction_performance_under_load(self, concurrent_transactions: int = 30, duration: int = 300):
        """Test complex transaction performance under load"""
        print(f"🔄 Testing transaction performance: {concurrent_transactions} concurrent transactions for {duration}s")
        
        transaction_scenarios = [
            {
                "name": "customer_billing_transaction",
                "operations": [
                    "BEGIN;",
                    "UPDATE customers SET balance = balance - $1 WHERE id = $2;",
                    "INSERT INTO transactions (customer_id, amount, transaction_type, timestamp) VALUES ($2, $1, 'charge', $3);",
                    "INSERT INTO invoices (customer_id, amount, due_date, status) VALUES ($2, $1, $4, 'pending');",
                    "COMMIT;"
                ],
                "expected_max_time_ms": 250.0
            },
            {
                "name": "service_provisioning_transaction", 
                "operations": [
                    "BEGIN;",
                    "INSERT INTO service_instances (customer_id, service_plan_id, status, created_at) VALUES ($1, $2, 'provisioning', $3);",
                    "UPDATE service_plans SET active_subscriptions = active_subscriptions + 1 WHERE id = $2;",
                    "INSERT INTO provisioning_tasks (service_instance_id, task_type, status) VALUES (currval('service_instances_id_seq'), 'network_setup', 'pending');",
                    "COMMIT;"
                ],
                "expected_max_time_ms": 300.0
            },
            {
                "name": "usage_aggregation_transaction",
                "operations": [
                    "BEGIN;",
                    """INSERT INTO daily_usage_summary (customer_id, date, total_bytes, session_count)
                       SELECT customer_id, DATE($1), SUM(bytes_used), COUNT(*)
                       FROM usage_records 
                       WHERE customer_id = $2 AND DATE(timestamp) = DATE($1)
                       GROUP BY customer_id
                       ON CONFLICT (customer_id, date) DO UPDATE 
                       SET total_bytes = EXCLUDED.total_bytes, session_count = EXCLUDED.session_count;""",
                    "DELETE FROM usage_records WHERE customer_id = $2 AND DATE(timestamp) = DATE($1);",
                    "COMMIT;"
                ],
                "expected_max_time_ms": 500.0
            }
        ]
        
        # Run concurrent transactions
        tasks = []
        for i in range(concurrent_transactions):
            task = asyncio.create_task(
                self._transaction_workload_worker(transaction_scenarios, duration, worker_id=i)
            )
            tasks.append(task)
        
        # Monitor transaction locks and deadlocks
        monitoring_task = asyncio.create_task(
            self._monitor_transaction_performance(duration)
        )
        
        # Execute test
        transaction_results = await asyncio.gather(*tasks)
        transaction_stats = await monitoring_task
        
        return self._analyze_transaction_performance_results(transaction_results, transaction_stats, transaction_scenarios)

    @pytest.mark.performance
    @pytest.mark.database
    async def test_connection_pool_performance(self, max_connections: int = 200, ramp_up_time: int = 60):
        """Test connection pool behavior under increasing load"""
        print(f"🏊 Testing connection pool: ramping to {max_connections} connections over {ramp_up_time}s")
        
        connection_pool_results = {
            "connection_acquisition_times": [],
            "pool_exhaustion_events": [],
            "connection_lifecycle": [],
            "error_rates_by_load": []
        }
        
        # Ramp up connections gradually
        ramp_step = 10
        current_connections = 0
        
        active_tasks = []
        
        while current_connections < max_connections:
            # Add new connections
            new_connections = min(ramp_step, max_connections - current_connections)
            
            for i in range(new_connections):
                task = asyncio.create_task(
                    self._connection_lifecycle_worker(connection_pool_results, current_connections + i)
                )
                active_tasks.append(task)
            
            current_connections += new_connections
            
            # Measure current pool state
            pool_state = await self._measure_pool_state()
            connection_pool_results["connection_lifecycle"].append({
                "timestamp": datetime.now().isoformat(),
                "active_connections": current_connections,
                "pool_size": pool_state["size"],
                "available_connections": pool_state["available"]
            })
            
            print(f"📈 Ramped to {current_connections} connections, pool size: {pool_state['size']}")
            
            await asyncio.sleep(ramp_up_time / (max_connections / ramp_step))
        
        # Let connections run for observation period
        await asyncio.sleep(120)
        
        # Cleanup
        for task in active_tasks:
            task.cancel()
        
        await asyncio.gather(*active_tasks, return_exceptions=True)
        
        return self._analyze_connection_pool_results(connection_pool_results, max_connections)

    @pytest.mark.performance 
    @pytest.mark.database
    async def test_query_optimization_analysis(self):
        """Analyze and test query optimization performance"""
        print("🔍 Running query optimization analysis...")
        
        # Complex queries that need optimization analysis
        optimization_queries = [
            {
                "name": "unoptimized_customer_analytics",
                "query": """
                SELECT c.*, 
                       (SELECT COUNT(*) FROM invoices WHERE customer_id = c.id) as invoice_count,
                       (SELECT SUM(amount) FROM transactions WHERE customer_id = c.id) as total_spent,
                       (SELECT MAX(timestamp) FROM usage_records WHERE customer_id = c.id) as last_usage
                FROM customers c 
                WHERE c.tier = $1
                ORDER BY c.created_at DESC
                """,
                "optimization_hints": ["Add indexes on foreign keys", "Consider materialized view for aggregations"]
            },
            {
                "name": "heavy_reporting_query",
                "query": """
                SELECT 
                    DATE_TRUNC('month', u.timestamp) as month,
                    c.tier,
                    COUNT(DISTINCT c.id) as active_customers,
                    SUM(u.bytes_used) as total_usage,
                    AVG(u.bytes_used) as avg_usage_per_session
                FROM usage_records u
                JOIN customers c ON u.customer_id = c.id
                WHERE u.timestamp >= $1
                GROUP BY DATE_TRUNC('month', u.timestamp), c.tier
                ORDER BY month DESC, c.tier
                """,
                "optimization_hints": ["Partition usage_records by month", "Add composite index on (timestamp, customer_id)"]
            }
        ]
        
        results = {}
        
        for query_spec in optimization_queries:
            print(f"🎯 Analyzing query: {query_spec['name']}")
            
            # Test query performance with EXPLAIN ANALYZE
            query_plan = await self._analyze_query_execution_plan(query_spec["query"])
            
            # Benchmark query performance
            performance_metrics = await self._benchmark_query_performance(
                query_spec["query"], iterations=10
            )
            
            # Check for missing indexes
            index_recommendations = await self._analyze_missing_indexes(query_spec["query"])
            
            results[query_spec["name"]] = {
                "execution_plan": query_plan,
                "performance_metrics": performance_metrics,
                "index_recommendations": index_recommendations,
                "optimization_hints": query_spec["optimization_hints"]
            }
        
        return results

    async def _setup_test_data(self):
        """Setup test data for database performance tests"""
        print("🏗️ Setting up database test data...")
        
        async with self.pool.acquire() as connection:
            # Create test customers
            for i in range(10000):
                await connection.execute("""
                    INSERT INTO customers (id, email, first_name, last_name, tier, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (id) DO NOTHING
                """, 
                f"customer_{i}",
                f"test_user_{i}@example.com", 
                f"User{i}",
                "Test",
                random.choice(["basic", "premium", "enterprise"]),
                datetime.now() - timedelta(days=random.randint(1, 365))
                )
            
            # Create test usage records (large dataset)
            for i in range(100000):
                await connection.execute("""
                    INSERT INTO usage_records (customer_id, bytes_used, timestamp, session_id)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT DO NOTHING
                """,
                f"customer_{random.randint(0, 9999)}",
                random.randint(1000000, 1000000000),  # 1MB to 1GB
                datetime.now() - timedelta(minutes=random.randint(1, 525600)),  # Last year
                str(uuid.uuid4())
                )
        
        print("✅ Test data setup complete")

    async def _read_workload_worker(self, benchmarks: List[DatabaseBenchmark], 
                                   duration: int, worker_id: int) -> Dict[str, Any]:
        """Worker for read performance testing"""
        start_time = time.time()
        results = {
            "worker_id": worker_id,
            "total_queries": 0,
            "errors": 0,
            "benchmark_results": {}
        }
        
        for benchmark in benchmarks:
            results["benchmark_results"][benchmark.name] = {
                "response_times": [],
                "errors": 0,
                "executions": 0
            }
        
        while time.time() - start_time < duration:
            benchmark = random.choice(benchmarks)
            
            try:
                # Prepare parameters
                params = self._prepare_benchmark_parameters(benchmark.parameters, worker_id)
                
                query_start = time.time()
                async with self.pool.acquire() as connection:
                    await connection.fetchrow(benchmark.query, *params)
                
                response_time = (time.time() - query_start) * 1000
                
                results["benchmark_results"][benchmark.name]["response_times"].append(response_time)
                results["benchmark_results"][benchmark.name]["executions"] += 1
                results["total_queries"] += 1
                
            except Exception as e:
                results["benchmark_results"][benchmark.name]["errors"] += 1
                results["errors"] += 1
            
            await asyncio.sleep(random.uniform(0.01, 0.1))  # Variable think time
        
        return results

    async def _write_workload_worker(self, benchmarks: List[DatabaseBenchmark], 
                                    duration: int, worker_id: int) -> Dict[str, Any]:
        """Worker for write performance testing"""
        start_time = time.time()
        results = {
            "worker_id": worker_id,
            "total_writes": 0,
            "errors": 0,
            "benchmark_results": {}
        }
        
        for benchmark in benchmarks:
            results["benchmark_results"][benchmark.name] = {
                "response_times": [],
                "errors": 0,
                "executions": 0
            }
        
        while time.time() - start_time < duration:
            benchmark = random.choice(benchmarks)
            
            try:
                params = self._prepare_benchmark_parameters(benchmark.parameters, worker_id)
                
                write_start = time.time()
                async with self.pool.acquire() as connection:
                    await connection.execute(benchmark.query, *params)
                
                response_time = (time.time() - write_start) * 1000
                
                results["benchmark_results"][benchmark.name]["response_times"].append(response_time)
                results["benchmark_results"][benchmark.name]["executions"] += 1
                results["total_writes"] += 1
                
            except Exception as e:
                results["benchmark_results"][benchmark.name]["errors"] += 1
                results["errors"] += 1
            
            await asyncio.sleep(random.uniform(0.05, 0.2))  # Think time for writes
        
        return results

    async def _transaction_workload_worker(self, scenarios: List[Dict], 
                                         duration: int, worker_id: int) -> Dict[str, Any]:
        """Worker for transaction performance testing"""
        start_time = time.time()
        results = {
            "worker_id": worker_id,
            "total_transactions": 0,
            "successful_transactions": 0,
            "failed_transactions": 0,
            "deadlocks": 0,
            "scenario_results": {}
        }
        
        for scenario in scenarios:
            results["scenario_results"][scenario["name"]] = {
                "response_times": [],
                "success_count": 0,
                "failure_count": 0
            }
        
        while time.time() - start_time < duration:
            scenario = random.choice(scenarios)
            
            try:
                transaction_start = time.time()
                async with self.pool.acquire() as connection:
                    # Execute transaction operations
                    for operation in scenario["operations"]:
                        if operation.strip() == "BEGIN;":
                            await connection.execute("BEGIN")
                        elif operation.strip() == "COMMIT;":
                            await connection.execute("COMMIT")
                        else:
                            params = self._prepare_transaction_parameters(operation, worker_id)
                            await connection.execute(operation, *params)
                
                response_time = (time.time() - transaction_start) * 1000
                
                results["scenario_results"][scenario["name"]]["response_times"].append(response_time)
                results["scenario_results"][scenario["name"]]["success_count"] += 1
                results["successful_transactions"] += 1
                
            except Exception as e:
                if "deadlock" in str(e).lower():
                    results["deadlocks"] += 1
                
                results["scenario_results"][scenario["name"]]["failure_count"] += 1
                results["failed_transactions"] += 1
                
                # Rollback on error
                try:
                    async with self.pool.acquire() as connection:
                        await connection.execute("ROLLBACK")
                except:
                    pass
            
            results["total_transactions"] += 1
            await asyncio.sleep(random.uniform(0.1, 0.5))  # Transaction think time
        
        return results

    def _prepare_benchmark_parameters(self, param_templates: List[str], worker_id: int) -> List[Any]:
        """Prepare parameters for benchmark queries"""
        params = []
        
        for template in param_templates:
            if template == "customer_{}":
                params.append(f"customer_{random.randint(0, 9999)}")
            elif template == "test_user_{}@example.com":
                params.append(f"test_user_{random.randint(0, 9999)}@example.com")
            elif template == "random_bytes":
                params.append(random.randint(1000000, 100000000))
            elif template == "timestamp":
                params.append(datetime.now())
            elif template == "session_{}":
                params.append(f"session_{worker_id}_{int(time.time())}")
            elif isinstance(template, datetime):
                params.append(template)
            else:
                params.append(template)
        
        return params

    def _analyze_read_performance_results(self, worker_results: List[Dict], 
                                        db_stats: Dict, benchmarks: List[DatabaseBenchmark]) -> Dict[str, Any]:
        """Analyze read performance test results"""
        analysis = {
            "summary": {
                "total_queries": sum(w["total_queries"] for w in worker_results),
                "total_errors": sum(w["errors"] for w in worker_results),
                "queries_per_second": sum(w["total_queries"] for w in worker_results) / 300,  # duration
                "error_rate": sum(w["errors"] for w in worker_results) / sum(w["total_queries"] for w in worker_results)
            },
            "benchmark_analysis": {},
            "database_stats": db_stats,
            "performance_grade": "A"
        }
        
        # Analyze each benchmark
        for benchmark in benchmarks:
            all_response_times = []
            total_executions = 0
            total_errors = 0
            
            for worker in worker_results:
                benchmark_data = worker["benchmark_results"][benchmark.name]
                all_response_times.extend(benchmark_data["response_times"])
                total_executions += benchmark_data["executions"]
                total_errors += benchmark_data["errors"]
            
            if all_response_times:
                analysis["benchmark_analysis"][benchmark.name] = {
                    "avg_response_time_ms": statistics.mean(all_response_times),
                    "p50_response_time_ms": statistics.median(all_response_times),
                    "p95_response_time_ms": statistics.quantiles(all_response_times, n=20)[18],
                    "p99_response_time_ms": statistics.quantiles(all_response_times, n=100)[98],
                    "max_response_time_ms": max(all_response_times),
                    "total_executions": total_executions,
                    "error_rate": total_errors / total_executions if total_executions > 0 else 0,
                    "meets_sla": statistics.mean(all_response_times) <= benchmark.expected_max_time_ms
                }
        
        return analysis

    async def _monitor_database_stats(self, duration: int) -> Dict[str, Any]:
        """Monitor database statistics during performance test"""
        stats = {
            "connection_count": [],
            "active_queries": [],
            "lock_waits": [],
            "cache_hit_ratio": [],
            "timestamps": []
        }
        
        interval = 10
        for _ in range(0, duration, interval):
            timestamp = datetime.now().isoformat()
            
            async with self.pool.acquire() as connection:
                # Get connection count
                conn_count = await connection.fetchval(
                    "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
                )
                
                # Get cache hit ratio
                cache_stats = await connection.fetchrow("""
                    SELECT round(sum(blks_hit)*100/sum(blks_hit+blks_read), 2) as cache_hit_ratio
                    FROM pg_stat_database WHERE datname = current_database()
                """)
                
                stats["timestamps"].append(timestamp)
                stats["connection_count"].append(conn_count)
                stats["cache_hit_ratio"].append(cache_stats["cache_hit_ratio"] or 0)
            
            await asyncio.sleep(interval)
        
        return stats