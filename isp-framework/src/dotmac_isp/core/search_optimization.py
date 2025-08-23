"""Search performance optimization system with intelligent indexing and caching.

This module provides comprehensive search optimization including:
- Automatic database indexing strategies
- Full-text search capabilities
- Search result caching
- Query optimization and analysis
- Performance monitoring
"""

import logging
import time
import hashlib
import asyncio
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import re

from sqlalchemy import text, Index, func, or_, and_
from sqlalchemy.orm import Session, Query
from sqlalchemy.sql import Select
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.engine import Engine

from dotmac_isp.core.database import engine, get_db
from dotmac_isp.shared.cache import get_cache_manager
from dotmac_isp.core.tracing import trace_function
from dotmac_isp.core.monitoring import metrics_collector

logger = logging.getLogger(__name__)


class SearchType(Enum):
    """Types of search operations."""

    EXACT_MATCH = "exact_match"
    PARTIAL_MATCH = "partial_match"
    FULL_TEXT = "full_text"
    FUZZY = "fuzzy"
    RANGE = "range"
    GEOSPATIAL = "geospatial"


class IndexType(Enum):
    """Database index types."""

    BTREE = "btree"
    HASH = "hash"
    GIN = "gin"
    GIST = "gist"
    SPGIST = "spgist"
    BRIN = "brin"


@dataclass
class SearchQuery:
    """Structured search query representation."""

    table_name: str
    fields: List[str]
    search_term: str
    search_type: SearchType
    filters: Dict[str, Any] = None
    sort_by: str = None
    sort_order: str = "asc"
    limit: int = 100
    offset: int = 0
    tenant_id: str = None


@dataclass
class IndexRecommendation:
    """Database index recommendation."""

    table_name: str
    columns: List[str]
    index_type: IndexType
    reason: str
    priority: int  # 1-10, 10 being highest priority
    estimated_impact: str
    query_pattern: str


@dataclass
class SearchResult:
    """Search operation result with metadata."""

    results: List[Dict[str, Any]]
    total_count: int
    query_time_ms: float
    cache_hit: bool
    search_query: SearchQuery
    suggestions: List[str] = None


class DatabaseIndexManager:
    """Manages database indexes for optimal search performance."""

    def __init__(self):
        self.cache_manager = get_cache_manager()
        self.query_stats = {}

    def analyze_query_patterns(self, days: int = 7) -> List[IndexRecommendation]:
        """Analyze query patterns and recommend indexes."""

        recommendations = []

        try:
            with engine.connect() as conn:
                # Get slow queries from PostgreSQL stats
                slow_queries = conn.execute(
                    text(
                        """
                    SELECT 
                        query,
                        calls,
                        total_time,
                        mean_time,
                        rows
                    FROM pg_stat_statements 
                    WHERE calls > 10 
                    AND mean_time > 100  -- Queries taking more than 100ms
                    ORDER BY mean_time DESC
                    LIMIT 50;
                """
                    )
                ).fetchall()

                for query_stat in slow_queries:
                    # Analyze query to suggest indexes
                    query_text = query_stat.query
                    recommendations.extend(
                        self._analyze_query_for_indexes(query_text, query_stat)
                    )

        except Exception as e:
            logger.warning(
                f"Could not analyze query patterns from pg_stat_statements: {e}"
            )
            # Fallback to hardcoded recommendations
            recommendations = self._get_default_index_recommendations()

        return recommendations

    def _analyze_query_for_indexes(
        self, query_text: str, query_stat
    ) -> List[IndexRecommendation]:
        """Analyze a specific query to suggest indexes."""
        recommendations = []

        # Extract table names and WHERE conditions
        where_pattern = r"WHERE\s+(.+?)(?:ORDER|GROUP|LIMIT|$)"
        where_match = re.search(where_pattern, query_text, re.IGNORECASE | re.DOTALL)

        if where_match:
            where_clause = where_match.group(1)

            # Look for common patterns
            if "tenant_id" in where_clause and "=" in where_clause:
                recommendations.append(
                    IndexRecommendation(
                        table_name="multiple",
                        columns=["tenant_id"],
                        index_type=IndexType.BTREE,
                        reason="Tenant isolation filtering",
                        priority=9,
                        estimated_impact="High - reduces query time by 60-80%",
                        query_pattern=f"WHERE tenant_id = ? (avg time: {query_stat.mean_time:.1f}ms)",
                    )
                )

            # Email/username searches
            if any(field in where_clause.lower() for field in ["email", "username"]):
                recommendations.append(
                    IndexRecommendation(
                        table_name="users",
                        columns=["email", "username"],
                        index_type=IndexType.BTREE,
                        reason="User lookup optimization",
                        priority=8,
                        estimated_impact="High - essential for auth performance",
                        query_pattern="User authentication and lookup queries",
                    )
                )

            # Customer number searches
            if "customer_number" in where_clause:
                recommendations.append(
                    IndexRecommendation(
                        table_name="customers",
                        columns=["customer_number"],
                        index_type=IndexType.BTREE,
                        reason="Customer lookup optimization",
                        priority=8,
                        estimated_impact="High - customer portal performance",
                        query_pattern="Customer number lookup",
                    )
                )

        return recommendations

    def _get_default_index_recommendations(self) -> List[IndexRecommendation]:
        """Get default index recommendations for ISP systems."""
        return [
            # Tenant isolation indexes (highest priority)
            IndexRecommendation(
                table_name="users",
                columns=["tenant_id"],
                index_type=IndexType.BTREE,
                reason="Multi-tenant data isolation",
                priority=10,
                estimated_impact="Critical - enables tenant isolation",
                query_pattern="All tenant-filtered queries",
            ),
            IndexRecommendation(
                table_name="customers",
                columns=["tenant_id"],
                index_type=IndexType.BTREE,
                reason="Multi-tenant data isolation",
                priority=10,
                estimated_impact="Critical - enables tenant isolation",
                query_pattern="All tenant-filtered queries",
            ),
            # Authentication and user management
            IndexRecommendation(
                table_name="users",
                columns=["email"],
                index_type=IndexType.BTREE,
                reason="User login performance",
                priority=9,
                estimated_impact="High - critical for auth",
                query_pattern="SELECT * FROM users WHERE email = ?",
            ),
            IndexRecommendation(
                table_name="users",
                columns=["username"],
                index_type=IndexType.BTREE,
                reason="User login performance",
                priority=9,
                estimated_impact="High - critical for auth",
                query_pattern="SELECT * FROM users WHERE username = ?",
            ),
            # Customer management
            IndexRecommendation(
                table_name="customers",
                columns=["customer_number"],
                index_type=IndexType.BTREE,
                reason="Customer lookup performance",
                priority=8,
                estimated_impact="High - customer portal performance",
                query_pattern="SELECT * FROM customers WHERE customer_number = ?",
            ),
            IndexRecommendation(
                table_name="customers",
                columns=["email"],
                index_type=IndexType.BTREE,
                reason="Customer search by email",
                priority=7,
                estimated_impact="Medium - customer support efficiency",
                query_pattern="Customer support lookup queries",
            ),
            IndexRecommendation(
                table_name="customers",
                columns=["account_status"],
                index_type=IndexType.BTREE,
                reason="Filter customers by status",
                priority=6,
                estimated_impact="Medium - reporting and analytics",
                query_pattern="SELECT * FROM customers WHERE account_status = ?",
            ),
            # Full-text search capabilities
            IndexRecommendation(
                table_name="customers",
                columns=["display_name", "company_name", "first_name", "last_name"],
                index_type=IndexType.GIN,
                reason="Full-text customer search",
                priority=7,
                estimated_impact="High - customer search functionality",
                query_pattern="Full-text search across customer names",
            ),
            # Audit and compliance
            IndexRecommendation(
                table_name="audit_logs",
                columns=["timestamp"],
                index_type=IndexType.BTREE,
                reason="Audit log time-based queries",
                priority=7,
                estimated_impact="High - compliance reporting",
                query_pattern="Time-based audit queries",
            ),
            IndexRecommendation(
                table_name="audit_logs",
                columns=["event_type"],
                index_type=IndexType.BTREE,
                reason="Filter audit logs by event type",
                priority=6,
                estimated_impact="Medium - security monitoring",
                query_pattern="Security event analysis",
            ),
            # Service management
            IndexRecommendation(
                table_name="services",
                columns=["customer_id"],
                index_type=IndexType.BTREE,
                reason="Customer service lookup",
                priority=7,
                estimated_impact="High - service management",
                query_pattern="SELECT * FROM services WHERE customer_id = ?",
            ),
            # Billing and invoicing
            IndexRecommendation(
                table_name="invoices",
                columns=["customer_id", "status"],
                index_type=IndexType.BTREE,
                reason="Customer invoice queries",
                priority=6,
                estimated_impact="Medium - billing efficiency",
                query_pattern="Customer billing queries",
            ),
            # Session management
            IndexRecommendation(
                table_name="auth_tokens",
                columns=["token_hash"],
                index_type=IndexType.HASH,
                reason="Fast token lookup",
                priority=8,
                estimated_impact="High - session validation performance",
                query_pattern="Token validation queries",
            ),
            IndexRecommendation(
                table_name="auth_tokens",
                columns=["user_id", "expires_at"],
                index_type=IndexType.BTREE,
                reason="User session management",
                priority=7,
                estimated_impact="Medium - session cleanup",
                query_pattern="User token management",
            ),
        ]

    def create_recommended_indexes(
        self, recommendations: List[IndexRecommendation]
    ) -> Dict[str, bool]:
        """Create recommended database indexes."""
        results = {}

        # Sort by priority (highest first)
        sorted_recommendations = sorted(
            recommendations, key=lambda x: x.priority, reverse=True
        )

        with engine.connect() as conn:
            with conn.begin():
                for rec in sorted_recommendations:
                    try:
                        index_name = f"idx_{rec.table_name}_{'_'.join(rec.columns)}"

                        # Check if index already exists
                        existing = conn.execute(
                            text(
                                """
                            SELECT indexname FROM pg_indexes 
                            WHERE tablename = :table_name 
                            AND indexname = :index_name
                        """
                            ),
                            {"table_name": rec.table_name, "index_name": index_name},
                        ).fetchone()

                        if existing:
                            logger.info(f"Index {index_name} already exists, skipping")
                            results[index_name] = True
                            continue

                        # Create the index
                        columns_str = ", ".join(rec.columns)

                        if rec.index_type == IndexType.GIN:
                            # For full-text search
                            tsvector_expr = " || ' ' ".join(
                                [f"COALESCE({col}, '')" for col in rec.columns]
                            )
                            sql = f"""
                                CREATE INDEX {index_name} ON {rec.table_name} 
                                USING gin(to_tsvector('english', {tsvector_expr}))
                            """
                        else:
                            sql = f"""
                                CREATE INDEX {index_name} ON {rec.table_name} 
                                USING {rec.index_type.value} ({columns_str})
                            """

                        conn.execute(text(sql))
                        results[index_name] = True

                        logger.info(f"✅ Created index: {index_name} ({rec.reason})")

                    except Exception as e:
                        logger.error(f"❌ Failed to create index {index_name}: {e}")
                        results[index_name] = False

        return results

    def analyze_existing_indexes(self) -> Dict[str, Any]:
        """Analyze existing database indexes for optimization opportunities."""

        with engine.connect() as conn:
            # Get index usage statistics
            index_stats = conn.execute(
                text(
                    """
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes 
                ORDER BY idx_scan DESC;
            """
                )
            ).fetchall()

            # Get index sizes
            index_sizes = conn.execute(
                text(
                    """
                SELECT 
                    tablename,
                    indexname,
                    pg_size_pretty(pg_relation_size(indexrelid)) as size,
                    pg_relation_size(indexrelid) as size_bytes
                FROM pg_stat_user_indexes 
                ORDER BY pg_relation_size(indexrelid) DESC;
            """
                )
            ).fetchall()

            return {
                "usage_stats": [dict(row) for row in index_stats],
                "size_stats": [dict(row) for row in index_sizes],
                "recommendations": {
                    "unused_indexes": [
                        row.indexname
                        for row in index_stats
                        if row.idx_scan < 10  # Used less than 10 times
                    ],
                    "oversized_indexes": [
                        row.indexname
                        for row in index_sizes
                        if row.size_bytes > 100 * 1024 * 1024  # Larger than 100MB
                    ],
                },
            }


class SearchOptimizer:
    """Optimizes search queries and manages search caching."""

    def __init__(self):
        self.cache_manager = get_cache_manager()
        self.cache_ttl = 300  # 5 minutes default
        self.max_cache_size = 1000

    @trace_function("search_optimization")
    def search(self, search_query: SearchQuery) -> SearchResult:
        """Execute optimized search with caching."""
        start_time = time.time()

        # Generate cache key
        cache_key = self._generate_cache_key(search_query)

        # Try cache first
        cached_result = self.cache_manager.get(cache_key, "search")
        if cached_result:
            logger.debug(f"Search cache hit for key: {cache_key}")
            cached_result["cache_hit"] = True
            return SearchResult(**cached_result)

        # Execute search
        results, total_count = self._execute_search(search_query)

        # Calculate query time
        query_time_ms = (time.time() - start_time) * 1000

        # Create result
        search_result = SearchResult(
            results=results,
            total_count=total_count,
            query_time_ms=query_time_ms,
            cache_hit=False,
            search_query=search_query,
            suggestions=self._generate_search_suggestions(search_query, results),
        )

        # Cache the result
        self._cache_search_result(cache_key, search_result)

        # Record metrics
        metrics_collector.histogram(
            "search.query_time_ms",
            query_time_ms,
            {
                "table": search_query.table_name,
                "search_type": search_query.search_type.value,
            },
        )

        return search_result

    def _execute_search(
        self, search_query: SearchQuery
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Execute the actual search query."""

        with next(get_db()) as db:
            # Build base query based on search type
            if search_query.search_type == SearchType.FULL_TEXT:
                return self._execute_full_text_search(db, search_query)
            elif search_query.search_type == SearchType.FUZZY:
                return self._execute_fuzzy_search(db, search_query)
            elif search_query.search_type == SearchType.EXACT_MATCH:
                return self._execute_exact_search(db, search_query)
            elif search_query.search_type == SearchType.PARTIAL_MATCH:
                return self._execute_partial_search(db, search_query)
            else:
                return self._execute_basic_search(db, search_query)

    def _execute_full_text_search(
        self, db: Session, search_query: SearchQuery
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Execute full-text search using PostgreSQL's text search capabilities."""

        # Build tsvector expression
        fields_expr = " || ' ' ".join(
            [f"COALESCE({field}, '')" for field in search_query.fields]
        )

        # Prepare search terms
        search_terms = search_query.search_term.replace("'", "''")
        tsquery = " & ".join(search_terms.split())

        # Build SQL query
        sql = f"""
            SELECT *, 
                   ts_rank(to_tsvector('english', {fields_expr}), to_tsquery('english', :search_terms)) as rank
            FROM {search_query.table_name}
            WHERE to_tsvector('english', {fields_expr}) @@ to_tsquery('english', :search_terms)
        """

        # Add tenant filtering
        if search_query.tenant_id:
            sql += " AND tenant_id = :tenant_id"

        # Add additional filters
        if search_query.filters:
            for field, value in search_query.filters.items():
                sql += f" AND {field} = :filter_{field}"

        # Add ordering
        sql += " ORDER BY rank DESC"

        # Add pagination
        sql += " LIMIT :limit OFFSET :offset"

        # Execute query
        params = {
            "search_terms": tsquery,
            "limit": search_query.limit,
            "offset": search_query.offset,
        }

        if search_query.tenant_id:
            params["tenant_id"] = search_query.tenant_id

        if search_query.filters:
            for field, value in search_query.filters.items():
                params[f"filter_{field}"] = value

        result = db.execute(text(sql), params)
        rows = result.fetchall()

        # Get total count
        count_sql = f"""
            SELECT COUNT(*)
            FROM {search_query.table_name}
            WHERE to_tsvector('english', {fields_expr}) @@ to_tsquery('english', :search_terms)
        """

        if search_query.tenant_id:
            count_sql += " AND tenant_id = :tenant_id"

        if search_query.filters:
            for field, value in search_query.filters.items():
                count_sql += f" AND {field} = :filter_{field}"

        count_result = db.execute(text(count_sql), params)
        total_count = count_result.scalar()

        # Convert rows to dictionaries
        results = [dict(row) for row in rows]

        return results, total_count

    def _execute_fuzzy_search(
        self, db: Session, search_query: SearchQuery
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Execute fuzzy search using PostgreSQL's similarity functions."""

        # Require pg_trgm extension for fuzzy search
        try:
            db.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        except Exception as e:
            logger.warning(f"Could not create pg_trgm extension: {e}")  # Extension might already exist or user lacks permissions

        # Build similarity conditions
        similarity_conditions = []
        for field in search_query.fields:
            similarity_conditions.append(f"similarity({field}, :search_term) > 0.3")

        similarity_expr = " OR ".join(similarity_conditions)

        sql = f"""
            SELECT *,
                   GREATEST({", ".join([f"similarity({field}, :search_term)" for field in search_query.fields])}) as similarity_score
            FROM {search_query.table_name}
            WHERE ({similarity_expr})
        """

        # Add tenant filtering
        if search_query.tenant_id:
            sql += " AND tenant_id = :tenant_id"

        # Add additional filters
        if search_query.filters:
            for field, value in search_query.filters.items():
                sql += f" AND {field} = :filter_{field}"

        # Order by similarity
        sql += " ORDER BY similarity_score DESC"
        sql += " LIMIT :limit OFFSET :offset"

        # Execute query
        params = {
            "search_term": search_query.search_term,
            "limit": search_query.limit,
            "offset": search_query.offset,
        }

        if search_query.tenant_id:
            params["tenant_id"] = search_query.tenant_id

        if search_query.filters:
            for field, value in search_query.filters.items():
                params[f"filter_{field}"] = value

        result = db.execute(text(sql), params)
        rows = result.fetchall()

        # Get total count (simplified for fuzzy search)
        total_count = (
            len(rows) + search_query.offset
            if len(rows) == search_query.limit
            else len(rows)
        )

        results = [dict(row) for row in rows]
        return results, total_count

    def _execute_exact_search(
        self, db: Session, search_query: SearchQuery
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Execute exact match search."""

        # Build exact match conditions
        exact_conditions = []
        for field in search_query.fields:
            exact_conditions.append(f"{field} = :search_term")

        conditions_expr = " OR ".join(exact_conditions)

        sql = f"SELECT * FROM {search_query.table_name} WHERE ({conditions_expr})"

        # Add tenant filtering
        if search_query.tenant_id:
            sql += " AND tenant_id = :tenant_id"

        # Add additional filters
        if search_query.filters:
            for field, value in search_query.filters.items():
                sql += f" AND {field} = :filter_{field}"

        # Add ordering and pagination
        if search_query.sort_by:
            sql += f" ORDER BY {search_query.sort_by} {search_query.sort_order.upper()}"

        sql += " LIMIT :limit OFFSET :offset"

        # Execute query
        params = {
            "search_term": search_query.search_term,
            "limit": search_query.limit,
            "offset": search_query.offset,
        }

        if search_query.tenant_id:
            params["tenant_id"] = search_query.tenant_id

        if search_query.filters:
            for field, value in search_query.filters.items():
                params[f"filter_{field}"] = value

        result = db.execute(text(sql), params)
        rows = result.fetchall()

        # Get total count
        count_sql = (
            f"SELECT COUNT(*) FROM {search_query.table_name} WHERE ({conditions_expr})"
        )

        if search_query.tenant_id:
            count_sql += " AND tenant_id = :tenant_id"

        if search_query.filters:
            for field, value in search_query.filters.items():
                count_sql += f" AND {field} = :filter_{field}"

        count_result = db.execute(text(count_sql), params)
        total_count = count_result.scalar()

        results = [dict(row) for row in rows]
        return results, total_count

    def _execute_partial_search(
        self, db: Session, search_query: SearchQuery
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Execute partial match search using ILIKE."""

        # Build partial match conditions
        partial_conditions = []
        for field in search_query.fields:
            partial_conditions.append(f"{field} ILIKE :search_pattern")

        conditions_expr = " OR ".join(partial_conditions)

        sql = f"SELECT * FROM {search_query.table_name} WHERE ({conditions_expr})"

        # Add tenant filtering
        if search_query.tenant_id:
            sql += " AND tenant_id = :tenant_id"

        # Add additional filters
        if search_query.filters:
            for field, value in search_query.filters.items():
                sql += f" AND {field} = :filter_{field}"

        # Add ordering and pagination
        if search_query.sort_by:
            sql += f" ORDER BY {search_query.sort_by} {search_query.sort_order.upper()}"

        sql += " LIMIT :limit OFFSET :offset"

        # Execute query
        search_pattern = f"%{search_query.search_term}%"
        params = {
            "search_pattern": search_pattern,
            "limit": search_query.limit,
            "offset": search_query.offset,
        }

        if search_query.tenant_id:
            params["tenant_id"] = search_query.tenant_id

        if search_query.filters:
            for field, value in search_query.filters.items():
                params[f"filter_{field}"] = value

        result = db.execute(text(sql), params)
        rows = result.fetchall()

        # Get total count
        count_sql = (
            f"SELECT COUNT(*) FROM {search_query.table_name} WHERE ({conditions_expr})"
        )

        if search_query.tenant_id:
            count_sql += " AND tenant_id = :tenant_id"

        if search_query.filters:
            for field, value in search_query.filters.items():
                count_sql += f" AND {field} = :filter_{field}"

        count_result = db.execute(text(count_sql), params)
        total_count = count_result.scalar()

        results = [dict(row) for row in rows]
        return results, total_count

    def _execute_basic_search(
        self, db: Session, search_query: SearchQuery
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Execute basic search (fallback)."""
        return self._execute_partial_search(db, search_query)

    def _generate_cache_key(self, search_query: SearchQuery) -> str:
        """Generate cache key for search query."""
        key_data = f"{search_query.table_name}:{':'.join(search_query.fields)}:{search_query.search_term}:{search_query.search_type.value}:{search_query.limit}:{search_query.offset}"

        if search_query.filters:
            filter_str = ":".join(
                f"{k}={v}" for k, v in sorted(search_query.filters.items())
            )
            key_data += f":{filter_str}"

        if search_query.tenant_id:
            key_data += f":tenant={search_query.tenant_id}"

        return f"search:{hashlib.sha256(key_data.encode()).hexdigest()}"

    def _cache_search_result(self, cache_key: str, search_result: SearchResult):
        """Cache search result."""
        try:
            # Convert search result to cacheable format
            cache_data = {
                "results": search_result.results,
                "total_count": search_result.total_count,
                "query_time_ms": search_result.query_time_ms,
                "cache_hit": False,
                "search_query": {
                    "table_name": search_result.search_query.table_name,
                    "fields": search_result.search_query.fields,
                    "search_term": search_result.search_query.search_term,
                    "search_type": search_result.search_query.search_type.value,
                    "filters": search_result.search_query.filters,
                    "limit": search_result.search_query.limit,
                    "offset": search_result.search_query.offset,
                },
                "suggestions": search_result.suggestions,
            }

            self.cache_manager.set(cache_key, cache_data, self.cache_ttl, "search")

        except Exception as e:
            logger.warning(f"Failed to cache search result: {e}")

    def _generate_search_suggestions(
        self, search_query: SearchQuery, results: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate search suggestions based on results."""
        suggestions = []

        # If no results, suggest similar terms
        if not results and len(search_query.search_term) > 2:
            # Basic suggestion: try without last character
            if len(search_query.search_term) > 3:
                suggestions.append(search_query.search_term[:-1])

            # Suggest common variations
            term_lower = search_query.search_term.lower()
            if "customer" in term_lower:
                suggestions.append("customer")
            if "service" in term_lower:
                suggestions.append("service")

        return suggestions[:5]  # Limit to 5 suggestions

    def clear_search_cache(self, pattern: str = None):
        """Clear search cache."""
        try:
            if pattern:
                # Clear specific pattern
                keys = self.cache_manager.redis_client.keys(
                    f"dotmac:search:*{pattern}*"
                )
                if keys:
                    self.cache_manager.redis_client.delete(*keys)
                    logger.info(
                        f"Cleared {len(keys)} search cache entries matching pattern: {pattern}"
                    )
            else:
                # Clear all search cache
                keys = self.cache_manager.redis_client.keys("dotmac:search:*")
                if keys:
                    self.cache_manager.redis_client.delete(*keys)
                    logger.info(f"Cleared {len(keys)} search cache entries")

        except Exception as e:
            logger.error(f"Failed to clear search cache: {e}")


def initialize_search_optimization():
    """Initialize search optimization system."""
    try:
        # Create index manager and analyzer
        index_manager = DatabaseIndexManager()

        # Analyze current query patterns
        recommendations = index_manager.analyze_query_patterns()

        # Create high-priority indexes
        high_priority_recs = [r for r in recommendations if r.priority >= 8]
        if high_priority_recs:
            logger.info(f"Creating {len(high_priority_recs)} high-priority indexes...")
            results = index_manager.create_recommended_indexes(high_priority_recs)

            success_count = sum(1 for success in results.values() if success)
            logger.info(
                f"✅ Created {success_count}/{len(high_priority_recs)} recommended indexes"
            )

        # Initialize search optimizer
        search_optimizer = SearchOptimizer()

        logger.info("🔍 Search optimization system initialized")

        return {
            "index_manager": index_manager,
            "search_optimizer": search_optimizer,
            "recommendations": recommendations,
        }

    except Exception as e:
        logger.error(f"❌ Failed to initialize search optimization: {e}")
        raise


# Global instances
index_manager = DatabaseIndexManager()
search_optimizer = SearchOptimizer()


# Convenience functions
def search_customers(
    search_term: str,
    tenant_id: str,
    search_type: SearchType = SearchType.PARTIAL_MATCH,
    limit: int = 50,
) -> SearchResult:
    """Search customers with optimization."""
    query = SearchQuery(
        table_name="customers",
        fields=[
            "display_name",
            "customer_number",
            "email",
            "company_name",
            "first_name",
            "last_name",
        ],
        search_term=search_term,
        search_type=search_type,
        tenant_id=tenant_id,
        limit=limit,
    )
    return search_optimizer.search(query)


def search_users(
    search_term: str,
    tenant_id: str,
    search_type: SearchType = SearchType.PARTIAL_MATCH,
    limit: int = 50,
) -> SearchResult:
    """Search users with optimization."""
    query = SearchQuery(
        table_name="users",
        fields=["username", "email", "first_name", "last_name"],
        search_term=search_term,
        search_type=search_type,
        tenant_id=tenant_id,
        limit=limit,
    )
    return search_optimizer.search(query)
