"""
Search SDK - Contract-first search and indexing.

Provides full-text search, faceted search, and document indexing
with multi-tenant isolation and advanced query capabilities.
"""

import logging
import time
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from dotmac_isp.sdks.contracts.search import (
    SearchDocument,
    SearchFacet,
    SearchHealthCheck,
    SearchHit,
    SearchIndex,
    SearchIndexStats,
    SearchQuery,
    SearchResponse,
    SearchSuggestion,
    SearchSuggestionResponse,
)
from dotmac_isp.sdks.contracts.transport import RequestContext
from dotmac_isp.sdks.platform.utils.datetime_compat import UTC

logger = logging.getLogger(__name__)


class SearchSDKConfig:
    """Search SDK configuration."""

    def __init__(
        """  Init   operation."""
        self,
        max_indexes_per_tenant: int = 100,
        max_documents_per_index: int = 100000,
        enable_query_caching: bool = True,
        query_cache_ttl_seconds: int = 300,
        enable_analytics: bool = True,
        default_query_timeout_ms: int = 30000,
    ):
        self.max_indexes_per_tenant = max_indexes_per_tenant
        self.max_documents_per_index = max_documents_per_index
        self.enable_query_caching = enable_query_caching
        self.query_cache_ttl_seconds = query_cache_ttl_seconds
        self.enable_analytics = enable_analytics
        self.default_query_timeout_ms = default_query_timeout_ms


class SearchSDK:
    """
    Contract-first Search SDK with comprehensive search capabilities.

    Features:
    - Full-text search with relevance scoring
    - Faceted search and aggregations
    - Multi-tenant document indexing
    - Query caching for performance
    - Search suggestions and autocomplete
    - Index statistics and analytics
    - Advanced filtering and sorting
    - Highlighting and snippets
    """

    def __init__(
        self,
        config: SearchSDKConfig | None = None,
        cache_sdk: Any | None = None,
        database_sdk: Any | None = None,
    ):
        """Initialize Search SDK."""
        self.config = config or SearchSDKConfig()
        self.cache_sdk = cache_sdk
        self.database_sdk = database_sdk

        # In-memory storage for testing/development
        self._indexes: dict[str, dict[str, SearchIndex]] = (
            {}
        )  # tenant_id -> index_name -> index
        self._documents: dict[str, dict[str, dict[str, SearchDocument]]] = (
            {}
        )  # tenant_id -> index_name -> doc_id -> document
        self._query_cache: dict[str, dict[str, Any]] = {}  # query_hash -> cached_result
        self._stats: dict[str, dict[str, SearchIndexStats]] = (
            {}
        )  # tenant_id -> index_name -> stats

        logger.info("SearchSDK initialized")

    async def create_index(
        self,
        index: SearchIndex,
        context: RequestContext | None = None,
    ) -> SearchIndex:
        """Create a new search index."""
        try:
            tenant_id_str = str(index.tenant_id)

            # Check if index already exists
            if (
                tenant_id_str in self._indexes
                and index.name in self._indexes[tenant_id_str]
            ):
                raise ValueError(f"Index '{index.name}' already exists")

            # Check tenant index limit
            if tenant_id_str in self._indexes:
                if (
                    len(self._indexes[tenant_id_str])
                    >= self.config.max_indexes_per_tenant
                ):
                    raise ValueError(
                        f"Maximum indexes per tenant ({self.config.max_indexes_per_tenant}) exceeded"
                    )

            # Create index with metadata
            new_index = index.model_copy()
            new_index.id = uuid4()
            new_index.created_at = datetime.now(UTC)
            new_index.updated_at = datetime.now(UTC)
            new_index.created_by = context.headers.x_user_id if context else None

            # Store index
            if tenant_id_str not in self._indexes:
                self._indexes[tenant_id_str] = {}
            self._indexes[tenant_id_str][index.name] = new_index

            # Initialize document storage
            if tenant_id_str not in self._documents:
                self._documents[tenant_id_str] = {}
            self._documents[tenant_id_str][index.name] = {}

            # Initialize stats
            if tenant_id_str not in self._stats:
                self._stats[tenant_id_str] = {}
            self._stats[tenant_id_str][index.name] = SearchIndexStats(
                tenant_id=index.tenant_id,
                index_name=index.name,
                document_count=0,
                deleted_document_count=0,
                store_size_bytes=0,
                query_total=0,
                query_time_ms=0,
                indexing_total=0,
                indexing_time_ms=0,
                avg_query_time_ms=0.0,
                queries_per_second=0.0,
                field_stats={},
                last_updated=datetime.now(UTC),
            )

            logger.info(
                f"Created search index: {index.name} for tenant: {tenant_id_str}"
            )
            return new_index

        except Exception as e:
            logger.error(f"Failed to create index {index.name}: {e}")
            raise

    async def index_document(
        self,
        document: SearchDocument,
        context: RequestContext | None = None,
    ) -> SearchDocument:
        """Index a document."""
        try:
            tenant_id_str = str(document.tenant_id)

            # Check if index exists
            if (
                tenant_id_str not in self._indexes
                or document.index_name not in self._indexes[tenant_id_str]
            ):
                raise ValueError(f"Index '{document.index_name}' not found")

            # Check document limit
            if (
                len(self._documents[tenant_id_str][document.index_name])
                >= self.config.max_documents_per_index
            ):
                raise ValueError(
                    f"Maximum documents per index ({self.config.max_documents_per_index}) exceeded"
                )

            # Create document with metadata
            new_document = document.model_copy()
            new_document.created_at = datetime.now(UTC)
            new_document.updated_at = datetime.now(UTC)

            # Store document
            self._documents[tenant_id_str][document.index_name][
                document.id
            ] = new_document

            # Update stats
            stats = self._stats[tenant_id_str][document.index_name]
            stats.document_count += 1
            stats.indexing_total += 1
            stats.store_size_bytes += len(str(document.data))

            logger.info(
                f"Indexed document: {document.id} in index: {document.index_name}"
            )
            return new_document

        except Exception as e:
            logger.error(f"Failed to index document {document.id}: {e}")
            raise

    async def search(
        self,
        query: SearchQuery,
        context: RequestContext | None = None,
    ) -> SearchResponse:
        """Search documents."""
        start_time = time.time()

        try:
            tenant_id_str = str(query.tenant_id)

            # Check if index exists
            if (
                tenant_id_str not in self._indexes
                or query.index_name not in self._indexes[tenant_id_str]
            ):
                raise ValueError(f"Index '{query.index_name}' not found")

            # Check query cache
            cache_key = None
            if self.config.enable_query_caching:
                cache_key = self._generate_query_cache_key(query)
                cached_result = self._query_cache.get(cache_key)
                if cached_result:
                    logger.info(
                        f"Returning cached search result for query: {query.query}"
                    )
                    return SearchResponse(**cached_result)

            # Get documents from index
            documents = self._documents[tenant_id_str][query.index_name]

            # Apply filters
            filtered_docs = self._apply_filters(documents, query)

            # Calculate relevance scores
            scored_docs = self._calculate_relevance_scores(filtered_docs, query)

            # Sort results
            sorted_docs = self._sort_results(scored_docs, query)

            # Apply pagination
            paginated_hits = self._paginate_results(sorted_docs, query)

            # Calculate facets
            facets = self._calculate_facets(filtered_docs, query)

            # Calculate max score
            max_score = max([hit.score for hit in paginated_hits], default=0.0)

            # Calculate execution time
            took_ms = (time.time() - start_time) * 1000

            # Create response
            result = SearchResponse(
                hits=paginated_hits,
                total_hits=len(scored_docs),
                max_score=max_score,
                facets=facets,
                took_ms=took_ms,
                timed_out=False,
                **{"from": query.from_},
                size=query.size,
                suggestions={},
            )

            # Cache result
            if self.config.enable_query_caching and cache_key:
                self._query_cache[cache_key] = result.model_dump(by_alias=True)

            # Update stats
            stats = self._stats[tenant_id_str][query.index_name]
            stats.query_total += 1
            stats.query_time_ms += int(took_ms)
            stats.avg_query_time_ms = stats.query_time_ms / stats.query_total

            logger.info(
                f"Search completed: {len(paginated_hits)} hits in {took_ms:.2f}ms"
            )
            return result

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    async def suggest(
        self,
        suggestion: SearchSuggestion,
        context: RequestContext | None = None,
    ) -> SearchSuggestionResponse:
        """Get search suggestions."""
        start_time = time.time()

        try:
            tenant_id_str = str(suggestion.tenant_id)

            # Check if index exists
            if (
                tenant_id_str not in self._indexes
                or suggestion.index_name not in self._indexes[tenant_id_str]
            ):
                raise ValueError(f"Index '{suggestion.index_name}' not found")

            # Get documents from index
            documents = self._documents[tenant_id_str][suggestion.index_name]

            # Extract suggestions from field values
            suggestions = set()
            for doc in documents.values():
                field_value = doc.data.get(suggestion.field)
                if field_value and isinstance(field_value, str):
                    # Simple prefix matching
                    if field_value.lower().startswith(suggestion.text.lower()):
                        suggestions.add(field_value)

                    # Word-level matching
                    words = field_value.lower().split()
                    for word in words:
                        if word.startswith(suggestion.text.lower()):
                            suggestions.add(word)

            # Limit and sort suggestions
            sorted_suggestions = sorted(suggestions)[: suggestion.size]

            # Calculate execution time
            took_ms = (time.time() - start_time) * 1000

            return SearchSuggestionResponse(
                suggestions=sorted_suggestions,
                took_ms=took_ms,
            )

        except Exception as e:
            logger.error(f"Suggestion failed: {e}")
            raise

    async def delete_document(
        self,
        tenant_id: UUID,
        index_name: str,
        document_id: str,
        context: RequestContext | None = None,
    ) -> bool:
        """Delete a document from index."""
        try:
            tenant_id_str = str(tenant_id)

            # Check if index exists
            if (
                tenant_id_str not in self._indexes
                or index_name not in self._indexes[tenant_id_str]
            ):
                raise ValueError(f"Index '{index_name}' not found")

            # Check if document exists
            if document_id not in self._documents[tenant_id_str][index_name]:
                return False

            # Delete document
            del self._documents[tenant_id_str][index_name][document_id]

            # Update stats
            stats = self._stats[tenant_id_str][index_name]
            stats.document_count -= 1
            stats.deleted_document_count += 1

            logger.info(f"Deleted document: {document_id} from index: {index_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            raise

    async def get_index_stats(
        self,
        tenant_id: UUID,
        index_name: str,
        context: RequestContext | None = None,
    ) -> SearchIndexStats:
        """Get index statistics."""
        try:
            tenant_id_str = str(tenant_id)

            # Check if index exists
            if (
                tenant_id_str not in self._indexes
                or index_name not in self._indexes[tenant_id_str]
            ):
                raise ValueError(f"Index '{index_name}' not found")

            return self._stats[tenant_id_str][index_name]

        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            raise

    async def health_check(self) -> SearchHealthCheck:
        """Perform health check."""
        total_indexes = sum(
            len(tenant_indexes) for tenant_indexes in self._indexes.values()
        )
        total_documents = sum(
            len(index_docs)
            for tenant_docs in self._documents.values()
            for index_docs in tenant_docs.values()
        )

        return SearchHealthCheck(
            status="healthy",
            timestamp=datetime.now(UTC),
            search_engine_available=True,
            cluster_health="green",
            total_indexes=total_indexes,
            total_documents=total_documents,
            total_size_gb=0.0,
            avg_query_latency_ms=1.0,
            avg_indexing_latency_ms=1.0,
            query_error_rate=0.0,
            indexing_error_rate=0.0,
            memory_usage_percent=50.0,
            disk_usage_percent=25.0,
            details={
                "cache_enabled": self.config.enable_query_caching,
                "analytics_enabled": self.config.enable_analytics,
            },
        )

    def _apply_filters(
        self, documents: dict[str, SearchDocument], query: SearchQuery
    ) -> dict[str, SearchDocument]:
        """Apply filters to documents."""
        if not query.filters:
            return documents

        filtered = {}
        for doc_id, doc in documents.items():
            match = True
            for field, value in query.filters.items():
                doc_value = doc.data.get(field)
                if doc_value != value:
                    match = False
                    break
            if match:
                filtered[doc_id] = doc

        return filtered

    def _calculate_relevance_scores(
        self, documents: dict[str, SearchDocument], query: SearchQuery
    ) -> list[SearchHit]:
        """Calculate relevance scores for documents."""
        hits = []

        for doc_id, doc in documents.items():
            score = self._calculate_relevance_score(doc, query)

            hit = SearchHit(
                id=doc_id,
                score=score,
                source=doc.data,
                highlight={},
            )
            hits.append(hit)

        return hits

    def _calculate_relevance_score(
        self, document: SearchDocument, query: SearchQuery
    ) -> float:
        """Calculate relevance score for a document."""
        if not query.query:
            # For filter-only queries, assign a base score to allow results
            return 1.0

        score = 0.0
        query_terms = query.query.lower().split()

        # Score based on text fields
        for field_name, field_value in document.data.items():
            if isinstance(field_value, str):
                field_text = field_value.lower()
                field_score = 0.0

                # Term frequency scoring
                for term in query_terms:
                    if term in field_text:
                        field_score += field_text.count(term)

                # Apply field boost (simplified)
                if field_name == "title":
                    field_score *= 2.0

                score += field_score

        # Apply document boost
        score *= document.boost

        return max(score, 0.1)  # Minimum score for matching documents

    def _sort_results(
        self, hits: list[SearchHit], query: SearchQuery
    ) -> list[SearchHit]:
        """Sort search results."""
        if query.sort:
            # Custom sorting (simplified implementation)
            return sorted(hits, key=lambda h: h.score, reverse=True)
        else:
            # Default: sort by relevance score
            return sorted(hits, key=lambda h: h.score, reverse=True)

    def _paginate_results(
        self, hits: list[SearchHit], query: SearchQuery
    ) -> list[SearchHit]:
        """Apply pagination to results."""
        start = query.from_
        end = start + query.size
        return hits[start:end]

    def _calculate_facets(
        self, documents: dict[str, SearchDocument], query: SearchQuery
    ) -> list[SearchFacet]:
        """Calculate facets for search results."""
        facets = []

        for facet_field in query.facets:
            facet_values = {}

            for doc in documents.values():
                field_value = doc.data.get(facet_field)
                if field_value is not None:
                    value_str = str(field_value)
                    facet_values[value_str] = facet_values.get(value_str, 0) + 1

            # Convert to facet format
            facet_list = [
                {"value": value, "count": count}
                for value, count in sorted(
                    facet_values.items(), key=lambda x: x[1], reverse=True
                )
            ]

            facet = SearchFacet(
                field=facet_field,
                values=facet_list[: query.facet_size],
                missing=0,
            )
            facets.append(facet)

        return facets

    def _generate_query_cache_key(self, query: SearchQuery) -> str:
        """Generate cache key for query."""
        query_data = query.model_dump(by_alias=True)
        # Simple hash of query parameters
        return f"search:{hash(str(sorted(query_data.items())))}"
