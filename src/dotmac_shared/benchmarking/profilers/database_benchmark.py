"""
Database Query Performance Profiling Module

Provides comprehensive database query benchmarking and profiling capabilities
including query execution time analysis, connection pool monitoring,
transaction performance, and database-specific optimizations.
"""

import asyncio
import time
import statistics
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from decimal import Decimal

import psutil
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from pydantic import BaseModel, Field

from ..utils.decorators import standard_exception_handler


@dataclass
class QueryMetrics:
    """Individual query execution metrics"""
    query_id: str
    query_text: str
    execution_time: float
    rows_affected: int
    rows_returned: int
    cpu_usage_during: float
    memory_usage_during: float
    connection_time: float
    transaction_time: Optional[float] = None
    explain_plan: Optional[str] = None
    cache_hit_ratio: Optional[float] = None
    lock_wait_time: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConnectionPoolMetrics:
    """Database connection pool performance metrics"""
    pool_size: int
    checked_in_connections: int
    checked_out_connections: int
    overflow_connections: int
    invalid_connections: int
    connection_creation_rate: float
    connection_pool_timeout_count: int
    avg_connection_lifetime: float
    peak_connections: int
    pool_utilization: float


@dataclass
class DatabaseBenchmarkResults:
    """Comprehensive database benchmark results"""
    test_name: str
    execution_time: float
    total_queries: int
    successful_queries: int
    failed_queries: int
    queries_per_second: float
    avg_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    min_response_time: float
    max_response_time: float
    std_dev_response_time: float
    query_metrics: List[QueryMetrics]
    connection_pool_metrics: ConnectionPoolMetrics
    resource_usage: Dict[str, float]
    error_details: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class DatabaseBenchmarkConfig(BaseModel):
    """Configuration for database benchmarking"""
    database_url: str
    concurrent_connections: int = Field(default=10, ge=1, le=100)
    warmup_queries: int = Field(default=50, ge=0)
    test_duration_seconds: int = Field(default=60, ge=10)
    query_timeout_seconds: int = Field(default=30, ge=1)
    enable_query_logging: bool = False
    enable_explain_plans: bool = False
    enable_transaction_testing: bool = True
    connection_pool_size: int = Field(default=20, ge=5)
    connection_pool_overflow: int = Field(default=10, ge=0)
    collect_system_metrics: bool = True
    query_cache_enabled: bool = True
    isolation_level: str = "READ_COMMITTED"


class DatabaseQueryBenchmarker:
    """Database query performance benchmarking and profiling"""
    
    def __init__(self, config: DatabaseBenchmarkConfig):
        self.config = config
        self.engine: Optional[Engine] = None
        self.session_factory: Optional[sessionmaker] = None
        self._setup_database_connection()
        
    def _setup_database_connection(self):
        """Setup database connection with performance optimizations"""
        self.engine = create_engine(
            self.config.database_url,
            poolclass=QueuePool,
            pool_size=self.config.connection_pool_size,
            max_overflow=self.config.connection_pool_overflow,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=self.config.enable_query_logging,
            isolation_level=self.config.isolation_level
        )
        
        self.session_factory = sessionmaker(
            bind=self.engine,
            expire_on_commit=False
        )

    @standard_exception_handler
    async def benchmark_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        query_id: str = None,
        iterations: int = 100
    ) -> List[QueryMetrics]:
        """Benchmark a single query with multiple iterations"""
        if not query_id:
            query_id = f"query_{hash(query) % 10000}"
            
        metrics = []
        
        for i in range(iterations):
            start_time = time.perf_counter()
            cpu_before = psutil.cpu_percent()
            memory_before = psutil.virtual_memory().percent
            
            with self.session_factory() as session:
                connection_start = time.perf_counter()
                
                try:
                    # Execute query
                    result = session.execute(text(query), parameters or {})
                    rows_returned = result.rowcount if hasattr(result, 'rowcount') else 0
                    rows_affected = result.rowcount if hasattr(result, 'rowcount') else 0
                    
                    # Get explain plan if enabled
                    explain_plan = None
                    if self.config.enable_explain_plans and query.strip().upper().startswith('SELECT'):
                        explain_result = session.execute(text(f"EXPLAIN ANALYZE {query}"), parameters or {})
                        explain_plan = '\n'.join([str(row) for row in explain_result])
                    
                    session.commit()
                    
                except Exception as e:
                    session.rollback()
                    rows_returned = 0
                    rows_affected = 0
                    explain_plan = f"Error: {str(e)}"
                
                connection_time = time.perf_counter() - connection_start
            
            execution_time = time.perf_counter() - start_time
            cpu_after = psutil.cpu_percent()
            memory_after = psutil.virtual_memory().percent
            
            metrics.append(QueryMetrics(
                query_id=f"{query_id}_{i}",
                query_text=query,
                execution_time=execution_time,
                rows_affected=rows_affected,
                rows_returned=rows_returned,
                cpu_usage_during=cpu_after - cpu_before,
                memory_usage_during=memory_after - memory_before,
                connection_time=connection_time,
                explain_plan=explain_plan
            ))
            
            # Small delay between iterations
            await asyncio.sleep(0.01)
        
        return metrics

    @standard_exception_handler
    async def benchmark_query_set(
        self,
        queries: List[Tuple[str, str, Optional[Dict[str, Any]]]],
        test_name: str = "query_set_benchmark"
    ) -> DatabaseBenchmarkResults:
        """Benchmark a set of queries with concurrent execution"""
        start_time = time.perf_counter()
        all_metrics = []
        errors = []
        
        # Warmup phase
        if self.config.warmup_queries > 0:
            await self._run_warmup_queries(queries[:1])
        
        # Concurrent execution
        semaphore = asyncio.Semaphore(self.config.concurrent_connections)
        tasks = []
        
        for query_id, query, params in queries:
            task = self._execute_query_with_semaphore(
                semaphore, query, params, query_id
            )
            tasks.append(task)
        
        # Execute all queries concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                errors.append({
                    "error": str(result),
                    "type": type(result).__name__,
                    "timestamp": datetime.utcnow().isoformat()
                })
            elif isinstance(result, list):
                all_metrics.extend(result)
        
        total_time = time.perf_counter() - start_time
        
        # Calculate statistics
        execution_times = [m.execution_time for m in all_metrics]
        successful_queries = len(all_metrics)
        failed_queries = len(errors)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(all_metrics, errors)
        
        return DatabaseBenchmarkResults(
            test_name=test_name,
            execution_time=total_time,
            total_queries=len(queries),
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            queries_per_second=successful_queries / total_time if total_time > 0 else 0,
            avg_response_time=statistics.mean(execution_times) if execution_times else 0,
            p50_response_time=statistics.median(execution_times) if execution_times else 0,
            p95_response_time=self._percentile(execution_times, 0.95) if execution_times else 0,
            p99_response_time=self._percentile(execution_times, 0.99) if execution_times else 0,
            min_response_time=min(execution_times) if execution_times else 0,
            max_response_time=max(execution_times) if execution_times else 0,
            std_dev_response_time=statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
            query_metrics=all_metrics,
            connection_pool_metrics=self._get_connection_pool_metrics(),
            resource_usage=self._get_resource_usage(),
            error_details=errors,
            recommendations=recommendations
        )

    @standard_exception_handler
    async def benchmark_transactions(
        self,
        transaction_operations: List[List[Tuple[str, Optional[Dict[str, Any]]]]],
        test_name: str = "transaction_benchmark"
    ) -> DatabaseBenchmarkResults:
        """Benchmark database transactions with rollback scenarios"""
        start_time = time.perf_counter()
        all_metrics = []
        errors = []
        
        for i, operations in enumerate(transaction_operations):
            transaction_start = time.perf_counter()
            
            with self.session_factory() as session:
                try:
                    session.begin()
                    
                    for j, (query, params) in enumerate(operations):
                        query_start = time.perf_counter()
                        result = session.execute(text(query), params or {})
                        query_time = time.perf_counter() - query_start
                        
                        all_metrics.append(QueryMetrics(
                            query_id=f"txn_{i}_query_{j}",
                            query_text=query,
                            execution_time=query_time,
                            rows_affected=result.rowcount if hasattr(result, 'rowcount') else 0,
                            rows_returned=result.rowcount if hasattr(result, 'rowcount') else 0,
                            cpu_usage_during=0,  # Would need separate monitoring
                            memory_usage_during=0,  # Would need separate monitoring
                            connection_time=0,
                            transaction_time=time.perf_counter() - transaction_start
                        ))
                    
                    session.commit()
                    
                except Exception as e:
                    session.rollback()
                    errors.append({
                        "transaction_id": i,
                        "error": str(e),
                        "type": type(e).__name__,
                        "timestamp": datetime.utcnow().isoformat()
                    })
        
        total_time = time.perf_counter() - start_time
        
        # Calculate statistics
        execution_times = [m.execution_time for m in all_metrics]
        successful_queries = len(all_metrics)
        failed_queries = len(errors)
        
        return DatabaseBenchmarkResults(
            test_name=test_name,
            execution_time=total_time,
            total_queries=sum(len(ops) for ops in transaction_operations),
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            queries_per_second=successful_queries / total_time if total_time > 0 else 0,
            avg_response_time=statistics.mean(execution_times) if execution_times else 0,
            p50_response_time=statistics.median(execution_times) if execution_times else 0,
            p95_response_time=self._percentile(execution_times, 0.95) if execution_times else 0,
            p99_response_time=self._percentile(execution_times, 0.99) if execution_times else 0,
            min_response_time=min(execution_times) if execution_times else 0,
            max_response_time=max(execution_times) if execution_times else 0,
            std_dev_response_time=statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
            query_metrics=all_metrics,
            connection_pool_metrics=self._get_connection_pool_metrics(),
            resource_usage=self._get_resource_usage(),
            error_details=errors,
            recommendations=self._generate_recommendations(all_metrics, errors)
        )

    @standard_exception_handler
    async def benchmark_connection_scaling(
        self,
        test_queries: List[Tuple[str, str, Optional[Dict[str, Any]]]],
        connection_ranges: List[int] = None
    ) -> Dict[int, DatabaseBenchmarkResults]:
        """Test database performance under different connection pool sizes"""
        if connection_ranges is None:
            connection_ranges = [1, 5, 10, 20, 50, 100]
        
        results = {}
        original_config = self.config.concurrent_connections
        
        for connection_count in connection_ranges:
            # Update configuration
            self.config.concurrent_connections = connection_count
            
            # Run benchmark
            result = await self.benchmark_query_set(
                test_queries,
                f"connection_scaling_{connection_count}"
            )
            results[connection_count] = result
            
            # Brief pause between tests
            await asyncio.sleep(2)
        
        # Restore original configuration
        self.config.concurrent_connections = original_config
        
        return results

    async def _execute_query_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        query: str,
        parameters: Optional[Dict[str, Any]],
        query_id: str
    ) -> List[QueryMetrics]:
        """Execute a query with semaphore control"""
        async with semaphore:
            return await self.benchmark_query(query, parameters, query_id, 1)

    async def _run_warmup_queries(self, queries: List[Tuple[str, str, Optional[Dict[str, Any]]]]):
        """Run warmup queries to stabilize performance"""
        for _ in range(self.config.warmup_queries):
            for _, query, params in queries:
                with self.session_factory() as session:
                    try:
                        session.execute(text(query), params or {})
                        session.commit()
                    except:
                        session.rollback()
                await asyncio.sleep(0.001)

    def _get_connection_pool_metrics(self) -> ConnectionPoolMetrics:
        """Get current connection pool metrics"""
        pool = self.engine.pool
        
        return ConnectionPoolMetrics(
            pool_size=pool.size(),
            checked_in_connections=pool.checkedin(),
            checked_out_connections=pool.checkedout(),
            overflow_connections=pool.overflow(),
            invalid_connections=pool.invalidated(),
            connection_creation_rate=0,  # Would need tracking
            connection_pool_timeout_count=0,  # Would need tracking  
            avg_connection_lifetime=0,  # Would need tracking
            peak_connections=pool.checkedout() + pool.checkedin(),
            pool_utilization=(pool.checkedout() / (pool.size() + pool.overflow())) * 100 if pool.size() > 0 else 0
        )

    def _get_resource_usage(self) -> Dict[str, float]:
        """Get current system resource usage"""
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_io_read": psutil.disk_io_counters().read_bytes if psutil.disk_io_counters() else 0,
            "disk_io_write": psutil.disk_io_counters().write_bytes if psutil.disk_io_counters() else 0,
            "network_sent": psutil.net_io_counters().bytes_sent if psutil.net_io_counters() else 0,
            "network_recv": psutil.net_io_counters().bytes_recv if psutil.net_io_counters() else 0
        }

    def _generate_recommendations(
        self,
        metrics: List[QueryMetrics],
        errors: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate performance recommendations based on metrics"""
        recommendations = []
        
        if not metrics:
            return ["No successful queries to analyze"]
        
        execution_times = [m.execution_time for m in metrics]
        avg_time = statistics.mean(execution_times)
        
        # Slow query detection
        slow_queries = [m for m in metrics if m.execution_time > 5.0]
        if slow_queries:
            recommendations.append(f"Found {len(slow_queries)} slow queries (>5s). Consider optimization or indexing.")
        
        # High variance detection
        if len(execution_times) > 1:
            std_dev = statistics.stdev(execution_times)
            if std_dev > avg_time * 0.5:
                recommendations.append("High variance in query execution times. Check for resource contention.")
        
        # Error rate analysis
        total_operations = len(metrics) + len(errors)
        error_rate = (len(errors) / total_operations) * 100 if total_operations > 0 else 0
        if error_rate > 5:
            recommendations.append(f"High error rate ({error_rate:.1f}%). Review query syntax and database constraints.")
        
        # Connection pool utilization
        pool_metrics = self._get_connection_pool_metrics()
        if pool_metrics.pool_utilization > 80:
            recommendations.append("High connection pool utilization. Consider increasing pool size.")
        
        # Performance baseline
        if avg_time > 1.0:
            recommendations.append("Average query time exceeds 1 second. Review query complexity and database design.")
        
        return recommendations

    @staticmethod
    def _percentile(data: List[float], percentile: float) -> float:
        """Calculate percentile value from a list of numbers"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int(percentile * (len(sorted_data) - 1))
        return sorted_data[index]

    def cleanup(self):
        """Cleanup database resources"""
        if self.engine:
            self.engine.dispose()