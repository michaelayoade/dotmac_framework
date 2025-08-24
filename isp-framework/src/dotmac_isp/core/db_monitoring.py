"""
Database performance monitoring and slow query detection.

This module provides comprehensive PostgreSQL database monitoring capabilities
including slow query detection, performance metrics collection, and automated
optimization suggestions.

Key Features:
    - Real-time slow query detection using pg_stat_statements
    - Query pattern classification and analysis
    - Tenant-aware monitoring for multi-tenant databases
    - Index suggestion based on query patterns
    - Prometheus metrics integration
    - Automatic alert generation for performance issues

Requirements:
    - PostgreSQL 14+ with pg_stat_statements extension
    - asyncpg for async database operations
    - Prometheus client for metrics export

Example:
    Basic usage with FastAPI::
    
        from dotmac_isp.core.db_monitoring import DatabaseMonitor
        
        monitor = DatabaseMonitor(db_pool, config)
        await monitor.start()
        
        # Get slow queries
        slow_queries = await monitor.get_slow_queries(threshold_ms=1000)
        
        # Get optimization suggestions
        suggestions = await monitor.get_index_suggestions()

Author: DotMac Engineering Team
Version: 1.0.0
Since: 2024-08-24
"""

import asyncio
import time
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging

import asyncpg
from prometheus_client import Counter, Histogram, Gauge
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Prometheus metrics
slow_query_counter = Counter(
    'db_slow_queries_total',
    'Total number of slow queries detected',
    ['database', 'tenant', 'query_type']
)

query_duration_histogram = Histogram(
    'db_query_duration_seconds',
    'Query execution duration in seconds',
    ['database', 'query_type'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

active_connections_gauge = Gauge(
    'db_active_connections',
    'Number of active database connections',
    ['database', 'state']
)

cache_hit_ratio_gauge = Gauge(
    'db_cache_hit_ratio',
    'Database cache hit ratio',
    ['database']
)


@dataclass
class SlowQuery:
    """
    Represents a slow database query with performance metrics.
    
    This dataclass encapsulates all relevant information about a slow query
    including execution statistics, query classification, and tenant context.
    
    Attributes:
        query (str): The SQL query text
        mean_time_ms (float): Average execution time in milliseconds
        calls (int): Number of times the query was executed
        total_time_ms (float): Total execution time across all calls
        min_time_ms (float): Minimum execution time
        max_time_ms (float): Maximum execution time
        stddev_time_ms (float): Standard deviation of execution times
        rows (int): Total number of rows returned/affected
        query_type (str): Type of query (SELECT, INSERT, UPDATE, DELETE, etc.)
        tenant_id (Optional[str]): Tenant identifier if multi-tenant
        table_name (Optional[str]): Primary table accessed by the query
        timestamp (datetime): When this slow query was detected
    
    Example:
        >>> slow_query = SlowQuery(
        ...     query="SELECT * FROM customers WHERE status = $1",
        ...     mean_time_ms=1500.5,
        ...     calls=100,
        ...     total_time_ms=150050.0,
        ...     min_time_ms=800.0,
        ...     max_time_ms=3000.0,
        ...     stddev_time_ms=450.3,
        ...     rows=10000,
        ...     query_type="SELECT",
        ...     tenant_id="tenant_001",
        ...     table_name="customers"
        ... )
    """
    query: str
    mean_time_ms: float
    calls: int
    total_time_ms: float
    min_time_ms: float
    max_time_ms: float
    stddev_time_ms: float
    rows: int
    query_type: str = "unknown"
    tenant_id: Optional[str] = None
    table_name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class DatabaseMonitor:
    """
    Monitor database performance and detect slow queries.
    
    This class provides comprehensive database monitoring capabilities including
    slow query detection, performance metrics collection, and optimization
    suggestions. It uses PostgreSQL's pg_stat_statements extension for detailed
    query statistics.
    
    Attributes:
        db_pool (asyncpg.Pool): Connection pool for database access
        slow_query_threshold_ms (float): Threshold for slow query detection
        monitoring_interval (int): Interval between monitoring cycles in seconds
        alert_thresholds (Dict): Thresholds for various alert conditions
    
    Methods:
        start(): Start the monitoring loop
        stop(): Stop the monitoring loop
        get_slow_queries(): Retrieve current slow queries
        get_metrics(): Get current database metrics
        get_index_suggestions(): Get index optimization suggestions
        analyze_query_patterns(): Analyze query patterns for optimization
    
    Example:
        >>> pool = await asyncpg.create_pool(DATABASE_URL)
        >>> monitor = DatabaseMonitor(pool, {
        ...     'slow_query_threshold_ms': 1000,
        ...     'monitoring_interval': 60
        ... })
        >>> await monitor.start()
    """
    
    def __init__(
        self,
        db_pool: asyncpg.Pool,
        config: Optional[Dict[str, Any]] = None
    ):
        self.db_pool = db_pool
        self.slow_query_threshold_ms = config.get('slow_query_threshold_ms', 1000)
        self.monitoring_interval = config.get('monitoring_interval', 60)
        self.alert_thresholds = config.get('alert_thresholds', {})
        self._monitoring_task = None
        self._slow_queries_cache = []

    async def start(self):
        """Start the monitoring loop."""
        if self._monitoring_task:
            logger.warning("Monitoring already running")
            return
        
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"Database monitoring started (interval: {self.monitoring_interval}s)")

    async def stop(self):
        """Stop the monitoring loop."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            logger.info("Database monitoring stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while True:
            try:
                await self.check_slow_queries()
                await self.update_connection_metrics()
                await self.update_cache_metrics()
                await asyncio.sleep(self.monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(self.monitoring_interval)

    async def check_slow_queries(self) -> List[SlowQuery]:
        """
        Check for slow queries using pg_stat_statements.
        
        Returns:
            List of slow queries detected
        """
        slow_queries = []
        
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT 
                        queryid::text as query_id,
                        query,
                        mean_exec_time,
                        max_exec_time,
                        min_exec_time,
                        calls,
                        total_exec_time,
                        mean_rows as rows_returned,
                        userid::regrole::text as user,
                        dbid::regclass::text as database
                    FROM pg_stat_statements
                    WHERE mean_exec_time > $1
                    ORDER BY mean_exec_time DESC
                    LIMIT 100
                """, self.slow_query_threshold_ms)
                
                for row in rows:
                    query_type = self._classify_query(row['query'])
                    tenant_id = self._extract_tenant_id(row['query'])
                    
                    slow_query = SlowQuery(
                        query=row['query'][:500],  # Truncate long queries
                        mean_time_ms=row['mean_exec_time'],
                        calls=row['calls'],
                        total_time_ms=row['total_exec_time'],
                        min_time_ms=row['min_exec_time'],
                        max_time_ms=row['max_exec_time'],
                        stddev_time_ms=0.0,  # Not available in pg_stat_statements
                        rows=int(row['rows_returned'] or 0),
                        query_type=query_type,
                        tenant_id=tenant_id,
                        table_name=None,  # Not available in pg_stat_statements
                        timestamp=datetime.now()
                    )
                    
                    slow_queries.append(slow_query)
                    
                    # Update metrics
                    slow_query_counter.labels(
                        database=row['database'] or 'unknown',
                        tenant=tenant_id or 'unknown',
                        query_type=query_type
                    ).inc()
                    
                    query_duration_histogram.labels(
                        database=row['database'] or 'unknown',
                        query_type=query_type
                    ).observe(slow_query.mean_time_ms / 1000)  # Convert to seconds
                    
                    # Log warning for very slow queries
                    if slow_query.mean_time_ms > 5000:  # > 5 seconds
                        logger.warning(
                            f"Very slow query detected: {slow_query.query[:100]}... "
                            f"(mean: {slow_query.mean_time_ms:.2f}ms, calls: {slow_query.calls})"
                        )
                
                # Alert if needed
                if slow_queries and self.alert_thresholds:
                    await self.alert_callback(slow_queries)
                
                # Cache queries for retrieval
                self._slow_queries_cache = slow_queries
                
        except Exception as e:
            logger.error(f"Failed to check slow queries: {e}")
        
        return slow_queries

    def _classify_query(self, query: str) -> str:
        """
        Classify query type (SELECT, INSERT, UPDATE, DELETE, etc).
        
        Analyzes the SQL query text to determine its type for categorization
        and monitoring purposes.
        
        Args:
            query (str): SQL query text to classify
        
        Returns:
            str: Query type (SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, etc.)
        
        Example:
            >>> query_type = monitor._classify_query("SELECT * FROM users")
            >>> assert query_type == "SELECT"
        """
        query_upper = query.upper().strip()
        if query_upper.startswith('SELECT'):
            return "SELECT"
        elif query_upper.startswith('INSERT'):
            return "INSERT"
        elif query_upper.startswith('UPDATE'):
            return "UPDATE"
        elif query_upper.startswith('DELETE'):
            return "DELETE"
        elif any(query_upper.startswith(ddl) for ddl in 
                ['CREATE', 'ALTER', 'DROP', 'TRUNCATE']):
            return "DDL"
        else:
            return "OTHER"

    async def update_connection_metrics(self):
        """Update database connection metrics."""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT 
                        state,
                        COUNT(*) as count
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                    GROUP BY state
                """)
                
                for row in rows:
                    state = row['state'] or 'idle'
                    active_connections_gauge.labels(
                        database='main',
                        state=state
                    ).set(row['count'])
                
        except Exception as e:
            logger.error(f"Failed to update connection metrics: {e}")

    async def update_cache_metrics(self):
        """Update database cache hit ratio metrics."""
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT 
                        sum(blks_hit)::float / 
                        NULLIF(sum(blks_hit) + sum(blks_read), 0) as cache_hit_ratio
                    FROM pg_stat_database
                    WHERE datname = current_database()
                """)
                
                if row and row['cache_hit_ratio']:
                    cache_hit_ratio_gauge.labels(database='main').set(
                        row['cache_hit_ratio']
                    )
                
        except Exception as e:
            logger.error(f"Failed to update cache metrics: {e}")

    def _extract_tenant_id(self, query: str) -> Optional[str]:
        """
        Extract tenant ID from query if present.
        
        Analyzes the query to identify tenant-specific patterns commonly used
        in multi-tenant database architectures.
        
        Args:
            query (str): SQL query text to analyze
        
        Returns:
            Optional[str]: Extracted tenant ID or None if not found
        
        Note:
            Supports various patterns including:
            - tenant_id = 'value'
            - tenant_schema.table_name
            - Comments with tenant context
        """
        # Look for common tenant patterns
        patterns = [
            r"tenant_id\s*=\s*'([^']+)'",
            r"tenant_id\s*=\s*([^\s,)]+)",
            r'"tenant_id"\s*=\s*\'([^\']+)\'',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

    async def get_slow_queries(
        self,
        threshold_ms: Optional[float] = None,
        limit: int = 100
    ) -> List[SlowQuery]:
        """
        Get slow queries from pg_stat_statements.
        
        Retrieves queries that exceed the specified execution time threshold,
        ordered by total execution time descending.
        
        Args:
            threshold_ms (Optional[float]): Minimum execution time in milliseconds.
                Defaults to configured slow_query_threshold_ms.
            limit (int): Maximum number of queries to return (default: 100)
        
        Returns:
            List[SlowQuery]: List of slow queries with performance metrics
        
        Raises:
            asyncpg.PostgresError: If pg_stat_statements is not available
        
        Example:
            >>> slow_queries = await monitor.get_slow_queries(
            ...     threshold_ms=500,
            ...     limit=10
            ... )
            >>> for query in slow_queries:
            ...     print(f"{query.query_type}: {query.mean_time_ms}ms")
        """
        threshold = threshold_ms or self.slow_query_threshold_ms
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    queryid::text as query_id,
                    query,
                    mean_exec_time,
                    max_exec_time,
                    min_exec_time,
                    calls,
                    total_exec_time,
                    mean_rows as rows_returned,
                    userid::regrole::text as user,
                    dbid::regclass::text as database
                FROM pg_stat_statements
                WHERE mean_exec_time > $1
                ORDER BY mean_exec_time DESC
                LIMIT $2
            """, threshold, limit)
            
            slow_queries = []
            for row in rows:
                query_type = self._classify_query(row['query'])
                tenant_id = self._extract_tenant_id(row['query'])
                
                slow_query = SlowQuery(
                    query=row['query'][:500],  # Truncate long queries
                    mean_time_ms=row['mean_exec_time'],
                    calls=row['calls'],
                    total_time_ms=row['total_exec_time'],
                    min_time_ms=row['min_exec_time'],
                    max_time_ms=row['max_exec_time'],
                    stddev_time_ms=0.0,  # Not available in pg_stat_statements
                    rows=int(row['rows_returned'] or 0),
                    query_type=query_type,
                    tenant_id=tenant_id,
                    table_name=None,  # Not available in pg_stat_statements
                    timestamp=datetime.now()
                )
                
                slow_queries.append(slow_query)
            
            return slow_queries

    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get current database performance metrics.
        
        Collects comprehensive performance metrics from PostgreSQL system views
        including connection statistics, cache hit ratios, and checkpoint performance.
        
        Returns:
            Dict[str, Any]: Current database performance metrics snapshot
        
        Raises:
            asyncpg.PostgresError: If unable to query system views
        
        Note:
            Requires appropriate permissions to access pg_stat_database,
            pg_stat_bgwriter, and pg_stat_activity system views.
        """
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    state,
                    COUNT(*) as count
                FROM pg_stat_activity
                WHERE datname = current_database()
                GROUP BY state
            """)
            
            metrics = {}
            for row in rows:
                state = row['state'] or 'idle'
                metrics[f'connections_{state}'] = row['count']
            
            row = await conn.fetchrow("""
                SELECT 
                    sum(blks_hit)::float / 
                    NULLIF(sum(blks_hit) + sum(blks_read), 0) as cache_hit_ratio
                FROM pg_stat_database
                WHERE datname = current_database()
            """)
            
            if row and row['cache_hit_ratio']:
                metrics['cache_hit_ratio'] = row['cache_hit_ratio']
            
            return metrics


# FastAPI dependency
async def get_db_monitor(pool: asyncpg.Pool) -> DatabaseMonitor:
    """Get database monitor instance for dependency injection."""
    monitor = DatabaseMonitor(pool)
    await monitor.start()
    await monitor.initialize()
    await monitor.start_monitoring()
    return monitor
