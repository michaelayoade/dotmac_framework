"""
Database benchmarking utilities.

Requires the 'db' extra: pip install dotmac-benchmarking[db]
"""

import time
from typing import Any

try:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession
    DB_AVAILABLE = True
except ImportError:
    AsyncConnection = AsyncEngine = AsyncSession = None
    text = None
    DB_AVAILABLE = False


async def benchmark_query(
    engine_or_session: "AsyncEngine | AsyncSession | AsyncConnection",
    query: str,
    params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Benchmark a single database query.
    
    Args:
        engine_or_session: SQLAlchemy async engine, session, or connection
        query: SQL query string (use parameterized queries for safety)
        params: Query parameters (optional)
        
    Returns:
        Dictionary with timing and query information
        
    Raises:
        ImportError: If sqlalchemy is not installed
        
    Example:
        from sqlalchemy.ext.asyncio import create_async_engine
        from dotmac_benchmarking.db import benchmark_query
        
        engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
        
        result = await benchmark_query(
            engine,
            "SELECT COUNT(*) FROM users WHERE active = :active",
            {"active": True}
        )
        print(f"Query time: {result['duration']:.3f}s")
    """
    if not DB_AVAILABLE:
        raise ImportError(
            "Database benchmarking requires sqlalchemy. Install with: pip install dotmac-benchmarking[db]"
        )

    start_time = time.perf_counter()

    try:
        # Handle different SQLAlchemy object types
        if hasattr(engine_or_session, 'execute'):
            # AsyncSession or AsyncConnection
            if params:
                result = await engine_or_session.execute(text(query), params)
            else:
                result = await engine_or_session.execute(text(query))
        else:
            # AsyncEngine - need to create connection
            async with engine_or_session.begin() as conn:
                if params:
                    result = await conn.execute(text(query), params)
                else:
                    result = await conn.execute(text(query))

        duration = time.perf_counter() - start_time

        # Try to get result metadata
        rowcount = getattr(result, 'rowcount', None) if result else None

        return {
            "duration": duration,
            "query": query,
            "params": params,
            "rowcount": rowcount,
            "success": True,
            "timestamp": time.time()
        }

    except Exception as e:
        duration = time.perf_counter() - start_time

        return {
            "duration": duration,
            "query": query,
            "params": params,
            "error": str(e),
            "error_type": type(e).__name__,
            "success": False,
            "timestamp": time.time()
        }


async def benchmark_query_batch(
    engine_or_session: "AsyncEngine | AsyncSession | AsyncConnection",
    queries: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Benchmark multiple database queries sequentially.
    
    Args:
        engine_or_session: SQLAlchemy async engine, session, or connection
        queries: List of query configs, each with 'query' and optional 'params'
        
    Returns:
        List of benchmark results for each query
        
    Example:
        queries = [
            {"query": "SELECT COUNT(*) FROM users"},
            {"query": "SELECT COUNT(*) FROM orders WHERE status = :status", "params": {"status": "active"}},
        ]
        
        results = await benchmark_query_batch(engine, queries)
    """
    if not DB_AVAILABLE:
        raise ImportError(
            "Database benchmarking requires sqlalchemy. Install with: pip install dotmac-benchmarking[db]"
        )

    results = []

    for query_config in queries:
        result = await benchmark_query(
            engine_or_session,
            query_config["query"],
            query_config.get("params")
        )
        results.append(result)

    return results


async def benchmark_transaction(
    engine_or_session: "AsyncEngine | AsyncSession",
    queries: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Benchmark multiple queries within a single transaction.
    
    Args:
        engine_or_session: SQLAlchemy async engine or session
        queries: List of query configs to run in transaction
        
    Returns:
        Benchmark result for the entire transaction
    """
    if not DB_AVAILABLE:
        raise ImportError(
            "Database benchmarking requires sqlalchemy. Install with: pip install dotmac-benchmarking[db]"
        )

    start_time = time.perf_counter()

    try:
        if hasattr(engine_or_session, 'begin'):
            # AsyncSession
            async with engine_or_session.begin():
                query_results = []
                for query_config in queries:
                    if query_config.get("params"):
                        result = await engine_or_session.execute(
                            text(query_config["query"]),
                            query_config["params"]
                        )
                    else:
                        result = await engine_or_session.execute(text(query_config["query"]))
                    query_results.append(result)
        else:
            # AsyncEngine
            async with engine_or_session.begin() as conn:
                query_results = []
                for query_config in queries:
                    if query_config.get("params"):
                        result = await conn.execute(
                            text(query_config["query"]),
                            query_config["params"]
                        )
                    else:
                        result = await conn.execute(text(query_config["query"]))
                    query_results.append(result)

        duration = time.perf_counter() - start_time

        return {
            "duration": duration,
            "query_count": len(queries),
            "queries": [q["query"] for q in queries],
            "success": True,
            "timestamp": time.time()
        }

    except Exception as e:
        duration = time.perf_counter() - start_time

        return {
            "duration": duration,
            "query_count": len(queries),
            "queries": [q["query"] for q in queries],
            "error": str(e),
            "error_type": type(e).__name__,
            "success": False,
            "timestamp": time.time()
        }
