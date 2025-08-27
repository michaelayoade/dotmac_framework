"""
Performance Optimization Module
Implements advanced performance optimizations for the DotMac Management Platform
"""

import time
import asyncio
import functools
import inspect
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import json
import hashlib
import logging
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class PerformanceMetrics:
    """Collect and track performance metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.request_counts: Dict[str, int] = {}
        self.error_counts: Dict[str, int] = {}
    
    def record_request_time(self, endpoint: str, duration: float):
        """Record request processing time"""
        if endpoint not in self.metrics:
            self.metrics[endpoint] = []
        
        self.metrics[endpoint].append(duration)
        
        # Keep only last 1000 measurements
        if len(self.metrics[endpoint]) > 1000:
            self.metrics[endpoint] = self.metrics[endpoint][-1000:]
        
        # Increment request count
        self.request_counts[endpoint] = self.request_counts.get(endpoint, 0) + 1
    
    def record_error(self, endpoint: str):
        """Record error for endpoint"""
        self.error_counts[endpoint] = self.error_counts.get(endpoint, 0) + 1
    
    def get_stats(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics"""
        if endpoint:
            times = self.metrics.get(endpoint, [])
            if not times:
                return {}
            
            return {
                'endpoint': endpoint,
                'request_count': self.request_counts.get(endpoint, 0),
                'error_count': self.error_counts.get(endpoint, 0),
                'avg_response_time': sum(times) / len(times),
                'min_response_time': min(times),
                'max_response_time': max(times),
                'p95_response_time': self._percentile(times, 0.95),
                'p99_response_time': self._percentile(times, 0.99),
                'error_rate': self.error_counts.get(endpoint, 0) / max(self.request_counts.get(endpoint, 1), 1)
            }
        
        # Return overall stats
        all_stats = {}
        for ep in self.metrics:
            all_stats[ep] = self.get_stats(ep)
        
        return all_stats
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int(percentile * len(sorted_data))
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        return sorted_data[index]

# Global performance metrics instance
performance_metrics = PerformanceMetrics()

class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to track request performance"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Get endpoint path
        endpoint = request.url.path
        
        try:
            response = await call_next(request)
            
            # Record successful request
            duration = time.time() - start_time
            performance_metrics.record_request_time(endpoint, duration)
            
            # Add performance headers
            response.headers["X-Response-Time"] = f"{duration:.4f}s"
            
            return response
            
        except Exception as e:
            # Record error
            performance_metrics.record_error(endpoint)
            duration = time.time() - start_time
            performance_metrics.record_request_time(endpoint, duration)
            raise

class DatabaseOptimizer:
    """Database performance optimization utilities"""
    
    @staticmethod
    async def analyze_query_performance(db: AsyncSession) -> Dict[str, Any]:
        """Analyze database query performance"""
        
        # Get slow queries
        slow_queries_sql = """
        SELECT 
            query,
            calls,
            total_time,
            mean_time,
            rows,
            100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
        FROM pg_stat_statements 
        ORDER BY total_time DESC
        LIMIT 20;
        """
        
        try:
            result = await db.execute(text(slow_queries_sql))
            slow_queries = [dict(row._mapping) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching slow queries: {e}")
            slow_queries = []
        
        # Get index usage
        index_usage_sql = """
        SELECT 
            t.tablename,
            indexname,
            c.reltuples AS num_rows,
            pg_size_pretty(pg_relation_size(quote_ident(t.tablename)::text)) AS table_size,
            pg_size_pretty(pg_relation_size(quote_ident(indexrelname)::text)) AS index_size,
            idx_scan AS number_of_scans,
            idx_tup_read AS tuples_read,
            idx_tup_fetch AS tuples_fetched
        FROM pg_tables t
        LEFT OUTER JOIN pg_class c ON c.relname = t.tablename
        LEFT OUTER JOIN (
            SELECT 
                c.relname AS ctablename,
                ipg.relname AS indexname,
                idx_scan,
                idx_tup_read,
                idx_tup_fetch,
                indexrelname
            FROM pg_index x
            JOIN pg_class c ON c.oid = x.indrelid
            JOIN pg_class ipg ON ipg.oid = x.indexrelid
            JOIN pg_stat_all_indexes psai ON x.indexrelid = psai.indexrelid
        ) AS foo ON t.tablename = foo.ctablename
        WHERE t.schemaname = 'public'
        ORDER BY number_of_scans DESC;
        """
        
        try:
            result = await db.execute(text(index_usage_sql))
            index_usage = [dict(row._mapping) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching index usage: {e}")
            index_usage = []
        
        # Get connection stats
        connection_stats_sql = """
        SELECT 
            state,
            COUNT(*) as count
        FROM pg_stat_activity 
        WHERE datname = current_database()
        GROUP BY state;
        """
        
        try:
            result = await db.execute(text(connection_stats_sql))
            connection_stats = [dict(row._mapping) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching connection stats: {e}")
            connection_stats = []
        
        return {
            'slow_queries': slow_queries,
            'index_usage': index_usage,
            'connection_stats': connection_stats,
            'analysis_time': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    async def optimize_table(db: AsyncSession, table_name: str) -> Dict[str, Any]:
        """Optimize specific table"""
        
        results = {}
        
        try:
            # Analyze table
            await db.execute(text(f"ANALYZE {table_name};"))
            results['analyze'] = 'completed'
            
            # Get table stats
            table_stats_sql = f"""
            SELECT 
                pg_size_pretty(pg_total_relation_size('{table_name}')) AS total_size,
                pg_size_pretty(pg_relation_size('{table_name}')) AS table_size,
                (SELECT reltuples::bigint FROM pg_class WHERE relname = '{table_name}') AS estimated_rows
            """
            
            result = await db.execute(text(table_stats_sql))
            table_stats = dict(result.fetchone()._mapping)
            results['table_stats'] = table_stats
            
            await db.commit()
            
        except Exception as e:
            await db.rollback()
            results['error'] = str(e)
            logger.error(f"Error optimizing table {table_name}: {e}")
        
        return results

def performance_monitor(func_name: Optional[str] = None):
    """Decorator to monitor function performance"""
    
    def decorator(func: Callable) -> Callable:
        name = func_name or f"{func.__module__}.{func.__name__}"
        
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    performance_metrics.record_request_time(name, duration)
                    return result
                except Exception as e:
                    performance_metrics.record_error(name)
                    duration = time.time() - start_time
                    performance_metrics.record_request_time(name, duration)
                    raise
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    performance_metrics.record_request_time(name, duration)
                    return result
                except Exception as e:
                    performance_metrics.record_error(name)
                    duration = time.time() - start_time
                    performance_metrics.record_request_time(name, duration)
                    raise
            return sync_wrapper
    
    return decorator

class QueryCache:
    """Simple in-memory query result cache"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.cache: Dict[str, Any] = {}
        self.timestamps: Dict[str, float] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
    
    def _generate_key(self, query: str, params: Any = None) -> str:
        """Generate cache key from query and parameters"""
        key_data = f"{query}:{params}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        if key not in self.timestamps:
            return True
        return (time.time() - self.timestamps[key]) > self.default_ttl
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.timestamps.items()
            if (current_time - timestamp) > self.default_ttl
        ]
        
        for key in expired_keys:
            self.cache.pop(key, None)
            self.timestamps.pop(key, None)
    
    def _enforce_size_limit(self):
        """Enforce cache size limit"""
        if len(self.cache) <= self.max_size:
            return
        
        # Remove oldest entries
        sorted_items = sorted(self.timestamps.items(), key=lambda x: x[1])
        items_to_remove = len(self.cache) - self.max_size + 100  # Remove extra items
        
        for key, _ in sorted_items[:items_to_remove]:
            self.cache.pop(key, None)
            self.timestamps.pop(key, None)
    
    def get(self, query: str, params: Any = None) -> Optional[Any]:
        """Get cached result"""
        key = self._generate_key(query, params)
        
        if key in self.cache and not self._is_expired(key):
            return self.cache[key]
        
        # Remove if expired
        if key in self.cache:
            self.cache.pop(key, None)
            self.timestamps.pop(key, None)
        
        return None
    
    def set(self, query: str, result: Any, params: Any = None, ttl: Optional[int] = None):
        """Set cached result"""
        key = self._generate_key(query, params)
        
        self.cache[key] = result
        self.timestamps[key] = time.time()
        
        # Periodic cleanup
        if len(self.cache) % 100 == 0:
            self._cleanup_expired()
            self._enforce_size_limit()
    
    def clear(self):
        """Clear all cached results"""
        self.cache.clear()
        self.timestamps.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'entries': len(self.cache),
            'max_size': self.max_size,
            'default_ttl': self.default_ttl,
            'memory_usage': sum(len(str(v)) for v in self.cache.values())
        }

# Global query cache instance
query_cache = QueryCache()

class ConnectionPool:
    """Database connection pool optimizer"""
    
    @staticmethod
    def get_optimal_pool_settings(max_connections: int = 200) -> Dict[str, Any]:
        """Calculate optimal connection pool settings"""
        
        # Rule of thumb: pool_size should be 2-5x CPU cores
        import os
        cpu_cores = os.cpu_count() or 4
        
        pool_size = min(cpu_cores * 3, max_connections // 4)
        max_overflow = min(pool_size * 2, max_connections - pool_size)
        
        return {
            'pool_size': pool_size,
            'max_overflow': max_overflow,
            'pool_timeout': 30,
            'pool_recycle': 3600,  # 1 hour
            'pool_pre_ping': True,
            'connect_args': {
                'server_settings': {
                    'application_name': 'dotmac_mgmt',
                    'jit': 'off'  # Disable JIT for shorter queries
                }
            }
        }

@asynccontextmanager
async def performance_context(operation_name: str):
    """Context manager for performance monitoring"""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        performance_metrics.record_request_time(operation_name, duration)

class BatchProcessor:
    """Batch processing for database operations"""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
    
    async def process_batch(self, 
                          db: AsyncSession,
                          items: List[Any],
                          process_func: Callable,
                          *args, **kwargs) -> List[Any]:
        """Process items in batches"""
        
        results = []
        
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            
            try:
                async with performance_context(f"batch_process_{process_func.__name__}"):
                    batch_result = await process_func(db, batch, *args, **kwargs)
                    results.extend(batch_result if isinstance(batch_result, list) else [batch_result])
                
                # Commit after each batch
                await db.commit()
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Batch processing error: {e}")
                raise
            
            # Small delay between batches to prevent overwhelming
            await asyncio.sleep(0.01)
        
        return results

def get_performance_report() -> Dict[str, Any]:
    """Generate comprehensive performance report"""
    
    stats = performance_metrics.get_stats()
    
    # Calculate overall metrics
    total_requests = sum(performance_metrics.request_counts.values())
    total_errors = sum(performance_metrics.error_counts.values())
    
    # Find slowest endpoints
    slowest_endpoints = []
    for endpoint, endpoint_stats in stats.items():
        if isinstance(endpoint_stats, dict) and 'avg_response_time' in endpoint_stats:
            slowest_endpoints.append({
                'endpoint': endpoint,
                'avg_response_time': endpoint_stats['avg_response_time']
            })
    
    slowest_endpoints.sort(key=lambda x: x['avg_response_time'], reverse=True)
    
    return {
        'overview': {
            'total_requests': total_requests,
            'total_errors': total_errors,
            'overall_error_rate': (total_errors / max(total_requests, 1)) * 100,
            'report_generated': datetime.utcnow().isoformat()
        },
        'endpoint_stats': stats,
        'slowest_endpoints': slowest_endpoints[:10],  # Top 10 slowest
        'cache_stats': query_cache.stats(),
        'recommendations': generate_performance_recommendations(stats)
    }

def generate_performance_recommendations(stats: Dict[str, Any]) -> List[str]:
    """Generate performance improvement recommendations"""
    
    recommendations = []
    
    for endpoint, endpoint_stats in stats.items():
        if not isinstance(endpoint_stats, dict):
            continue
        
        avg_time = endpoint_stats.get('avg_response_time', 0)
        error_rate = endpoint_stats.get('error_rate', 0)
        
        # Slow endpoint recommendation
        if avg_time > 2.0:  # > 2 seconds
            recommendations.append(
                f"Optimize {endpoint}: Average response time is {avg_time:.2f}s. Consider adding caching or database optimization."
            )
        
        # High error rate recommendation
        if error_rate > 0.05:  # > 5% error rate
            recommendations.append(
                f"Investigate errors in {endpoint}: Error rate is {error_rate*100:.1f}%. Check logs for common error patterns."
            )
    
    # Cache recommendations
    cache_stats = query_cache.stats()
    if cache_stats['entries'] < 10:
        recommendations.append("Consider implementing more aggressive caching - current cache usage is low.")
    
    if not recommendations:
        recommendations.append("Performance metrics look good! Continue monitoring.")
    
    return recommendations