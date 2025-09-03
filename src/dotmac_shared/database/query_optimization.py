"""
Database query optimization utilities for DotMac Framework.
Provides decorators, patterns, and utilities for optimized database operations.
"""

import hashlib
import json
import time
import functools
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, Tuple
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from sqlalchemy import and_, or_, func, select, update, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload, contains_eager
from sqlalchemy.sql import Select
from sqlalchemy.exc import SQLAlchemyError

from dotmac_shared.observability.logging import get_logger
from .session import get_async_db, _query_cache, _cache_ttl

logger = get_logger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


# === QUERY OPTIMIZATION DECORATORS ===

def query_cache(ttl_seconds: int = 300, cache_key_prefix: str = "") -> Callable[[F], F]:
    """
    Decorator for caching query results with TTL.
    
    Args:
        ttl_seconds: Time to live for cache entries
        cache_key_prefix: Prefix for cache keys to avoid collisions
        
    Usage:
        @query_cache(ttl_seconds=600, cache_key_prefix="commission_config")
        async def get_commission_configs(filters: dict):
            # Query implementation
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name, args, and kwargs
            cache_data = {
                "func": func.__name__,
                "args": str(args),
                "kwargs": sorted(kwargs.items())
            }
            cache_key = f"{cache_key_prefix}:{hashlib.md5(json.dumps(cache_data, sort_keys=True).encode()).hexdigest()}"
            
            # Check cache
            now = datetime.now(timezone.utc)
            if cache_key in _query_cache:
                cached_result, cached_time = _query_cache[cache_key]
                if (now - cached_time).total_seconds() < ttl_seconds:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cached_result
                else:
                    # Remove expired entry
                    del _query_cache[cache_key]
            
            # Execute query and cache result
            start_time = time.time()
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Cache the result
            _query_cache[cache_key] = (result, now)
            
            logger.debug(
                f"Query executed and cached: {func.__name__} ({execution_time:.3f}s)",
                extra={
                    "function": func.__name__,
                    "execution_time": execution_time,
                    "cache_key": cache_key[:20] + "..."
                }
            )
            
            return result
            
        return wrapper
    return decorator


def slow_query_monitor(threshold_seconds: float = 1.0) -> Callable[[F], F]:
    """
    Decorator for monitoring slow queries.
    
    Args:
        threshold_seconds: Threshold for considering a query slow
        
    Usage:
        @slow_query_monitor(threshold_seconds=2.0)
        async def complex_query():
            # Query implementation
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                if execution_time > threshold_seconds:
                    logger.warning(
                        f"Slow query detected: {func.__name__} ({execution_time:.3f}s)",
                        extra={
                            "function": func.__name__,
                            "execution_time": execution_time,
                            "threshold": threshold_seconds,
                            "args_count": len(args),
                            "kwargs_count": len(kwargs)
                        }
                    )
                else:
                    logger.debug(f"Query completed: {func.__name__} ({execution_time:.3f}s)")
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"Query failed: {func.__name__} ({execution_time:.3f}s)",
                    extra={
                        "function": func.__name__,
                        "execution_time": execution_time,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )
                raise
                
        return wrapper
    return decorator


def batch_query(batch_size: int = 100) -> Callable[[F], F]:
    """
    Decorator for processing queries in batches to avoid memory issues.
    
    Args:
        batch_size: Number of items to process per batch
        
    Usage:
        @batch_query(batch_size=50)
        async def process_large_dataset(session, item_ids: List[str]):
            # Process items in batches
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Look for list arguments to batch
            new_args = []
            batched_lists = []
            
            for arg in args:
                if isinstance(arg, list) and len(arg) > batch_size:
                    batched_lists.append(arg)
                    new_args.append(None)  # Placeholder
                else:
                    new_args.append(arg)
            
            # Look for list kwargs to batch
            new_kwargs = {}
            batched_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, list) and len(value) > batch_size:
                    batched_kwargs[key] = value
                else:
                    new_kwargs[key] = value
            
            # If no batching needed, execute normally
            if not batched_lists and not batched_kwargs:
                return await func(*args, **kwargs)
            
            # Process in batches
            results = []
            total_items = max(
                [len(lst) for lst in batched_lists] + 
                [len(lst) for lst in batched_kwargs.values()]
            )
            
            for i in range(0, total_items, batch_size):
                batch_args = []
                for j, arg in enumerate(new_args):
                    if arg is None and j < len(batched_lists):
                        batch_args.append(batched_lists[j][i:i + batch_size])
                    else:
                        batch_args.append(arg)
                
                batch_kwargs = new_kwargs.copy()
                for key, value in batched_kwargs.items():
                    batch_kwargs[key] = value[i:i + batch_size]
                
                batch_result = await func(*batch_args, **batch_kwargs)
                if isinstance(batch_result, list):
                    results.extend(batch_result)
                else:
                    results.append(batch_result)
            
            return results
            
        return wrapper
    return decorator


# === QUERY BUILDER UTILITIES ===

class OptimizedQueryBuilder:
    """Advanced query builder with optimization features."""
    
    def __init__(self, model_class):
        self.model_class = model_class
        self.query = select(model_class)
        self._joins = []
        self._filters = []
        self._eager_loads = []
        
    def with_filters(self, **filters):
        """Add filters to the query with automatic optimization."""
        for key, value in filters.items():
            if value is not None:
                if isinstance(value, list):
                    # Use IN clause for lists
                    self._filters.append(getattr(self.model_class, key).in_(value))
                elif isinstance(value, tuple) and len(value) == 2:
                    # Range filter (min, max)
                    min_val, max_val = value
                    if min_val is not None:
                        self._filters.append(getattr(self.model_class, key) >= min_val)
                    if max_val is not None:
                        self._filters.append(getattr(self.model_class, key) <= max_val)
                elif isinstance(value, str) and '%' in value:
                    # LIKE pattern
                    self._filters.append(getattr(self.model_class, key).like(value))
                else:
                    # Exact match
                    self._filters.append(getattr(self.model_class, key) == value)
        return self
    
    def with_eager_loading(self, *relationships):
        """Add eager loading for relationships."""
        for relationship in relationships:
            if isinstance(relationship, str):
                self._eager_loads.append(selectinload(getattr(self.model_class, relationship)))
            else:
                self._eager_loads.append(relationship)
        return self
    
    def with_joined_loading(self, *relationships):
        """Add joined loading for relationships (use with caution)."""
        for relationship in relationships:
            if isinstance(relationship, str):
                self._eager_loads.append(joinedload(getattr(self.model_class, relationship)))
            else:
                self._eager_loads.append(relationship)
        return self
    
    def with_pagination(self, page: int = 1, size: int = 50):
        """Add pagination with optimization."""
        offset = (page - 1) * size
        self.query = self.query.offset(offset).limit(size)
        return self
    
    def with_ordering(self, *order_by):
        """Add ordering with index optimization hints."""
        self.query = self.query.order_by(*order_by)
        return self
    
    def build(self) -> Select:
        """Build the optimized query."""
        # Apply filters
        if self._filters:
            self.query = self.query.where(and_(*self._filters))
        
        # Apply eager loading
        if self._eager_loads:
            self.query = self.query.options(*self._eager_loads)
        
        return self.query


# === SPECIALIZED QUERY PATTERNS ===

@asynccontextmanager
async def bulk_operation_session():
    """Context manager for bulk operations with optimized settings."""
    async with get_async_db(read_only=False) as session:
        # Disable autoflush for better bulk performance
        session.autoflush = False
        try:
            yield session
            # Manual flush and commit for bulk operations
            await session.flush()
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            session.autoflush = True


async def bulk_insert(session: AsyncSession, model_class, items: List[Dict[str, Any]], 
                     batch_size: int = 1000) -> int:
    """
    Perform bulk insert with batching for optimal performance.
    
    Args:
        session: Database session
        model_class: SQLAlchemy model class
        items: List of dictionaries with item data
        batch_size: Number of items per batch
        
    Returns:
        Number of items inserted
    """
    total_inserted = 0
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        try:
            # Add timestamp fields if not present
            now = datetime.now(timezone.utc)
            for item in batch:
                if 'created_at' not in item:
                    item['created_at'] = now
                if 'updated_at' not in item:
                    item['updated_at'] = now
            
            # Bulk insert
            session.add_all([model_class(**item) for item in batch])
            await session.flush()
            
            total_inserted += len(batch)
            logger.debug(f"Bulk inserted batch of {len(batch)} {model_class.__name__} records")
            
        except SQLAlchemyError as e:
            logger.error(f"Bulk insert failed for batch starting at index {i}: {e}")
            await session.rollback()
            raise
    
    return total_inserted


async def bulk_update(session: AsyncSession, model_class, updates: List[Dict[str, Any]], 
                     key_field: str = 'id', batch_size: int = 1000) -> int:
    """
    Perform bulk update with batching.
    
    Args:
        session: Database session
        model_class: SQLAlchemy model class
        updates: List of dictionaries with update data (must include key field)
        key_field: Field name used as the update key
        batch_size: Number of items per batch
        
    Returns:
        Number of items updated
    """
    total_updated = 0
    
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i + batch_size]
        
        try:
            # Add updated_at timestamp
            now = datetime.now(timezone.utc)
            for item in batch:
                item['updated_at'] = now
            
            # Bulk update
            for item in batch:
                key_value = item.pop(key_field)
                stmt = update(model_class).where(
                    getattr(model_class, key_field) == key_value
                ).values(**item)
                await session.execute(stmt)
            
            await session.flush()
            total_updated += len(batch)
            logger.debug(f"Bulk updated batch of {len(batch)} {model_class.__name__} records")
            
        except SQLAlchemyError as e:
            logger.error(f"Bulk update failed for batch starting at index {i}: {e}")
            await session.rollback()
            raise
    
    return total_updated


async def bulk_delete(session: AsyncSession, model_class, ids: List[Any], 
                     id_field: str = 'id', batch_size: int = 1000) -> int:
    """
    Perform bulk delete with batching.
    
    Args:
        session: Database session
        model_class: SQLAlchemy model class
        ids: List of IDs to delete
        id_field: Field name used as the ID field
        batch_size: Number of items per batch
        
    Returns:
        Number of items deleted
    """
    total_deleted = 0
    
    for i in range(0, len(ids), batch_size):
        batch = ids[i:i + batch_size]
        
        try:
            stmt = delete(model_class).where(
                getattr(model_class, id_field).in_(batch)
            )
            result = await session.execute(stmt)
            deleted_count = result.rowcount
            
            await session.flush()
            total_deleted += deleted_count
            logger.debug(f"Bulk deleted {deleted_count} {model_class.__name__} records")
            
        except SQLAlchemyError as e:
            logger.error(f"Bulk delete failed for batch starting at index {i}: {e}")
            await session.rollback()
            raise
    
    return total_deleted


# === QUERY ANALYTICS AND PROFILING ===

class QueryProfiler:
    """Query profiler for performance analysis."""
    
    def __init__(self):
        self.query_stats = {}
        
    def profile_query(self, query_name: str):
        """Decorator for profiling specific queries."""
        def decorator(func: F) -> F:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                start_memory = 0  # Could integrate memory profiling if needed
                
                try:
                    result = await func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # Update statistics
                    if query_name not in self.query_stats:
                        self.query_stats[query_name] = {
                            'count': 0,
                            'total_time': 0,
                            'avg_time': 0,
                            'min_time': float('inf'),
                            'max_time': 0
                        }
                    
                    stats = self.query_stats[query_name]
                    stats['count'] += 1
                    stats['total_time'] += execution_time
                    stats['avg_time'] = stats['total_time'] / stats['count']
                    stats['min_time'] = min(stats['min_time'], execution_time)
                    stats['max_time'] = max(stats['max_time'], execution_time)
                    
                    return result
                    
                except Exception as e:
                    execution_time = time.time() - start_time
                    logger.error(
                        f"Profiled query failed: {query_name} ({execution_time:.3f}s)",
                        extra={"query_name": query_name, "error": str(e)}
                    )
                    raise
                    
            return wrapper
        return decorator
    
    def get_stats(self) -> Dict[str, Any]:
        """Get query profiling statistics."""
        return self.query_stats.copy()
    
    def reset_stats(self):
        """Reset profiling statistics."""
        self.query_stats.clear()


# Global query profiler instance
query_profiler = QueryProfiler()


# === CACHE MANAGEMENT ===

def clear_query_cache():
    """Clear the global query cache."""
    _query_cache.clear()
    logger.info("Query cache cleared")


def get_cache_stats() -> Dict[str, Any]:
    """Get query cache statistics."""
    now = datetime.now(timezone.utc)
    valid_entries = 0
    expired_entries = 0
    
    for key, (result, cached_time) in _query_cache.items():
        if (now - cached_time).total_seconds() < _cache_ttl:
            valid_entries += 1
        else:
            expired_entries += 1
    
    return {
        "total_entries": len(_query_cache),
        "valid_entries": valid_entries,
        "expired_entries": expired_entries,
        "cache_hit_ratio": valid_entries / max(len(_query_cache), 1),
        "default_ttl": _cache_ttl
    }


def cleanup_expired_cache():
    """Clean up expired cache entries."""
    now = datetime.now(timezone.utc)
    expired_keys = []
    
    for key, (result, cached_time) in _query_cache.items():
        if (now - cached_time).total_seconds() >= _cache_ttl:
            expired_keys.append(key)
    
    for key in expired_keys:
        del _query_cache[key]
    
    logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    return len(expired_keys)