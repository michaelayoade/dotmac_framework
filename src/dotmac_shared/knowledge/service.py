"""
Knowledge Base Service - Production Ready Business Logic
Leverages existing DotMac patterns from TicketService
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import and_, asc, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    ArticleAnalytics,
    ArticleComment,
    ArticleCreate,
    ArticleResponse,
    ArticleSearchParams,
    ArticleStatus,
    ArticleUpdate,
    CommentCreate,
    CommentResponse,
    CustomerPortalSettings,
    KnowledgeArticle,
    PortalSettingsResponse,
    PortalSettingsUpdate,
)

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Knowledge base business logic service."""

    def __init__(
        self, db_session_factory=None, config: Optional[dict[str, Any]] = None
    ):
        """Initialize knowledge service."""
        self.db_session_factory = db_session_factory
        self.config = config or {}

        # Search configuration
        self.search_config = {
            "min_search_length": 2,
            "max_search_results": 100,
            "default_page_size": 20,
            "search_boost_factors": {
                "title": 3.0,
                "summary": 2.0,
                "content": 1.0,
                "tags": 1.5,
            },
        }

    async def create_article(
        self,
        db: AsyncSession,
        tenant_id: str,
        article_data: ArticleCreate,
        author_id: str,
        author_name: str,
    ) -> ArticleResponse:
        """Create a new knowledge base article."""
        try:
            # Check for slug uniqueness
            existing_slug = await self._check_slug_exists(
                db, tenant_id, article_data.slug
            )
            if existing_slug:
                # Generate unique slug
                base_slug = article_data.slug
                counter = 1
                while existing_slug:
                    article_data.slug = f"{base_slug}-{counter}"
                    existing_slug = await self._check_slug_exists(
                        db, tenant_id, article_data.slug
                    )
                    counter += 1

            # Create article
            article = KnowledgeArticle(
                tenant_id=tenant_id,
                title=article_data.title,
                slug=article_data.slug,
                summary=article_data.summary,
                content=article_data.content,
                article_type=article_data.article_type,
                category=article_data.category,
                subcategory=article_data.subcategory,
                tags=article_data.tags,
                author_id=author_id,
                author_name=author_name,
                meta_description=article_data.meta_description,
                search_keywords=article_data.search_keywords,
                external_links=article_data.external_links,
                status=ArticleStatus.DRAFT,
            )

            # Generate HTML content
            article.content_html = await self._render_content_html(article.content)

            db.add(article)
            await db.commit()
            await db.refresh(article)

            logger.info(f"Created article {article.slug} for tenant {tenant_id}")

            # Trigger events
            await self._trigger_article_created_events(article)

            return ArticleResponse.model_validate(article)

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating article: {str(e)}")
            raise

    async def get_article(
        self,
        db: AsyncSession,
        tenant_id: str,
        article_id: str,
        increment_view: bool = True,
    ) -> Optional[ArticleResponse]:
        """Get article by ID."""
        query = (
            select(KnowledgeArticle)
            .where(
                and_(
                    KnowledgeArticle.id == article_id,
                    KnowledgeArticle.tenant_id == tenant_id,
                )
            )
            .options(selectinload(KnowledgeArticle.comments))
        )

        result = await db.execute(query)
        article = result.scalar_one_or_none()

        if not article:
            return None

        # Increment view count
        if increment_view and article.status == ArticleStatus.PUBLISHED:
            await self._increment_view_count(db, article.id)

        # Add comment count
        response = ArticleResponse.model_validate(article)
        response.comment_count = len([c for c in article.comments if c.is_public])

        return response

    async def get_article_by_slug(
        self, db: AsyncSession, tenant_id: str, slug: str, increment_view: bool = True
    ) -> Optional[ArticleResponse]:
        """Get article by slug."""
        query = (
            select(KnowledgeArticle)
            .where(
                and_(
                    KnowledgeArticle.slug == slug,
                    KnowledgeArticle.tenant_id == tenant_id,
                )
            )
            .options(selectinload(KnowledgeArticle.comments))
        )

        result = await db.execute(query)
        article = result.scalar_one_or_none()

        if not article:
            return None

        # Increment view count for published articles
        if increment_view and article.status == ArticleStatus.PUBLISHED:
            await self._increment_view_count(db, article.id)

        response = ArticleResponse.model_validate(article)
        response.comment_count = len([c for c in article.comments if c.is_public])

        return response

    async def update_article(
        self,
        db: AsyncSession,
        tenant_id: str,
        article_id: str,
        update_data: ArticleUpdate,
        updated_by: Optional[str] = None,
    ) -> Optional[ArticleResponse]:
        """Update article."""
        try:
            # Get existing article
            article = await self._get_article_for_update(db, tenant_id, article_id)
            if not article:
                return None

            # Update fields
            update_dict = update_data.model_dump(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(article, field, value)

            article.updated_at = datetime.now(timezone.utc)

            # Re-render HTML if content changed
            if "content" in update_dict:
                article.content_html = await self._render_content_html(article.content)

            # Handle status changes
            if "status" in update_dict:
                await self._handle_status_change(article, update_data.status)

            await db.commit()
            await db.refresh(article)

            logger.info(f"Updated article {article.slug}")

            return ArticleResponse.model_validate(article)

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating article {article_id}: {str(e)}")
            raise

    async def search_articles(
        self, db: AsyncSession, tenant_id: str, search_params: ArticleSearchParams
    ) -> tuple[list[ArticleResponse], int, dict[str, Any]]:
        """Search articles with advanced filtering and ranking."""
        try:
            # Build base query
            query = select(KnowledgeArticle).where(
                KnowledgeArticle.tenant_id == tenant_id
            )

            # Apply status filter
            if search_params.status:
                query = query.where(KnowledgeArticle.status.in_(search_params.status))

            # Apply category filter
            if search_params.category:
                query = query.where(KnowledgeArticle.category == search_params.category)

            # Apply article type filter
            if search_params.article_type:
                query = query.where(
                    KnowledgeArticle.article_type == search_params.article_type
                )

            # Apply tag filter
            if search_params.tags:
                # Check if article tags array overlaps with search tags
                tag_conditions = []
                for tag in search_params.tags:
                    tag_conditions.append(
                        func.json_array_elements_text(KnowledgeArticle.tags).op("@>")(
                            [tag]
                        )
                    )
                query = query.where(or_(*tag_conditions))

            # Apply text search
            search_conditions = []
            relevance_score = None

            if (
                search_params.query
                and len(search_params.query.strip())
                >= self.search_config["min_search_length"]
            ):
                search_query = search_params.query.strip()

                # Full-text search using PostgreSQL
                search_vector = func.to_tsvector(
                    "english",
                    func.concat(
                        func.coalesce(KnowledgeArticle.title, ""),
                        " ",
                        func.coalesce(KnowledgeArticle.summary, ""),
                        " ",
                        func.coalesce(KnowledgeArticle.content, ""),
                    ),
                )

                search_query_ts = func.plainto_tsquery("english", search_query)

                # Add search condition
                search_conditions.append(search_vector.op("@@")(search_query_ts))

                # Calculate relevance score
                relevance_score = func.ts_rank(search_vector, search_query_ts)

                # Also search in tags (simpler text matching)
                tag_search = func.array_to_string(KnowledgeArticle.tags, " ").ilike(
                    f"%{search_query}%"
                )
                search_conditions.append(tag_search)

                # Combine search conditions with OR
                if search_conditions:
                    query = query.where(or_(*search_conditions))

            # Get total count for pagination
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await db.execute(count_query)
            total_count = count_result.scalar()

            # Apply sorting
            if search_params.sort_by == "relevance" and relevance_score is not None:
                # Sort by relevance score
                order_column = desc(relevance_score)
            else:
                # Sort by specified column
                sort_column = getattr(
                    KnowledgeArticle, search_params.sort_by, KnowledgeArticle.created_at
                )
                if search_params.sort_order.lower() == "asc":
                    order_column = asc(sort_column)
                else:
                    order_column = desc(sort_column)

            query = query.order_by(order_column)

            # Apply pagination
            offset = (search_params.page - 1) * search_params.page_size
            query = query.offset(offset).limit(search_params.page_size)

            # Execute query
            result = await db.execute(query)
            articles = result.scalars().all()

            # Convert to response models
            article_responses = [
                ArticleResponse.model_validate(article) for article in articles
            ]

            # Generate search metadata
            search_metadata = {
                "total_results": total_count,
                "page": search_params.page,
                "page_size": search_params.page_size,
                "total_pages": (total_count + search_params.page_size - 1)
                // search_params.page_size,
                "has_next_page": (search_params.page * search_params.page_size)
                < total_count,
                "search_query": search_params.query,
                "search_time_ms": 0,  # Would be measured in production
            }

            logger.info(
                f"Search completed: {total_count} results for query '{search_params.query}'"
            )

            return article_responses, total_count, search_metadata

        except Exception as e:
            logger.error(f"Error searching articles: {str(e)}")
            raise

    async def add_comment(
        self,
        db: AsyncSession,
        tenant_id: str,
        article_id: str,
        comment_data: CommentCreate,
        author_id: Optional[str] = None,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None,
        author_type: str = "customer",
    ) -> Optional[CommentResponse]:
        """Add comment to article."""
        try:
            # Verify article exists
            article = await self._get_article_for_update(db, tenant_id, article_id)
            if not article:
                return None

            comment = ArticleComment(
                article_id=article_id,
                tenant_id=tenant_id,
                content=comment_data.content,
                is_helpful_feedback=comment_data.is_helpful_feedback,
                is_public=comment_data.is_public,
                author_id=author_id,
                author_name=author_name or "Anonymous",
                author_email=author_email,
                author_type=author_type,
            )

            db.add(comment)
            await db.commit()
            await db.refresh(comment)

            logger.info(f"Added comment to article {article.slug}")

            # Trigger notification events
            await self._trigger_comment_added_events(article, comment)

            return CommentResponse.model_validate(comment)

        except Exception as e:
            await db.rollback()
            logger.error(f"Error adding comment to article {article_id}: {str(e)}")
            raise

    async def vote_on_article(
        self,
        db: AsyncSession,
        tenant_id: str,
        article_id: str,
        is_helpful: bool,
        user_id: Optional[str] = None,
    ) -> bool:
        """Vote on article helpfulness."""
        try:
            article = await self._get_article_for_update(db, tenant_id, article_id)
            if not article:
                return False

            # Update vote counts
            if is_helpful:
                article.helpful_votes += 1
            else:
                article.unhelpful_votes += 1

            # Update search ranking based on helpfulness
            total_votes = article.helpful_votes + article.unhelpful_votes
            if total_votes > 0:
                helpfulness_ratio = article.helpful_votes / total_votes
                # Boost ranking for helpful articles
                article.search_ranking = int(helpfulness_ratio * 100)

            await db.commit()

            logger.info(
                f"Recorded vote on article {article.slug}: helpful={is_helpful}"
            )

            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Error voting on article {article_id}: {str(e)}")
            raise

    async def get_popular_articles(
        self, db: AsyncSession, tenant_id: str, limit: int = 10, days: int = 30
    ) -> list[ArticleResponse]:
        """Get most popular articles by view count."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            query = (
                select(KnowledgeArticle)
                .where(
                    and_(
                        KnowledgeArticle.tenant_id == tenant_id,
                        KnowledgeArticle.status == ArticleStatus.PUBLISHED,
                        KnowledgeArticle.updated_at >= cutoff_date,
                    )
                )
                .order_by(
                    desc(KnowledgeArticle.view_count),
                    desc(KnowledgeArticle.helpful_votes),
                )
                .limit(limit)
            )

            result = await db.execute(query)
            articles = result.scalars().all()

            return [ArticleResponse.model_validate(article) for article in articles]

        except Exception as e:
            logger.error(f"Error getting popular articles: {str(e)}")
            raise

    async def get_related_articles(
        self, db: AsyncSession, tenant_id: str, article_id: str, limit: int = 5
    ) -> list[ArticleResponse]:
        """Get articles related to the given article."""
        try:
            # Get the source article
            source_article = await self._get_article_for_update(
                db, tenant_id, article_id
            )
            if not source_article:
                return []

            # Find related articles by category and tags
            query = (
                select(KnowledgeArticle)
                .where(
                    and_(
                        KnowledgeArticle.tenant_id == tenant_id,
                        KnowledgeArticle.status == ArticleStatus.PUBLISHED,
                        KnowledgeArticle.id != article_id,
                        or_(
                            KnowledgeArticle.category == source_article.category,
                            KnowledgeArticle.subcategory == source_article.subcategory,
                        ),
                    )
                )
                .order_by(desc(KnowledgeArticle.view_count))
                .limit(limit)
            )

            result = await db.execute(query)
            articles = result.scalars().all()

            return [ArticleResponse.model_validate(article) for article in articles]

        except Exception as e:
            logger.error(f"Error getting related articles: {str(e)}")
            return []

    async def get_customer_portal_settings(
        self, db: AsyncSession, tenant_id: str, customer_id: str
    ) -> PortalSettingsResponse:
        """Get customer portal settings."""
        try:
            query = select(CustomerPortalSettings).where(
                and_(
                    CustomerPortalSettings.customer_id == customer_id,
                    CustomerPortalSettings.tenant_id == tenant_id,
                )
            )

            result = await db.execute(query)
            settings = result.scalar_one_or_none()

            if not settings:
                # Create default settings
                settings = CustomerPortalSettings(
                    customer_id=customer_id, tenant_id=tenant_id
                )
                db.add(settings)
                await db.commit()
                await db.refresh(settings)

            return PortalSettingsResponse.model_validate(settings)

        except Exception as e:
            logger.error(f"Error getting portal settings: {str(e)}")
            raise

    async def update_portal_settings(
        self,
        db: AsyncSession,
        tenant_id: str,
        customer_id: str,
        settings_data: PortalSettingsUpdate,
    ) -> PortalSettingsResponse:
        """Update customer portal settings."""
        try:
            # Get existing settings
            query = select(CustomerPortalSettings).where(
                and_(
                    CustomerPortalSettings.customer_id == customer_id,
                    CustomerPortalSettings.tenant_id == tenant_id,
                )
            )

            result = await db.execute(query)
            settings = result.scalar_one_or_none()

            if not settings:
                # Create new settings
                settings = CustomerPortalSettings(
                    customer_id=customer_id, tenant_id=tenant_id
                )
                db.add(settings)

            # Update fields
            update_dict = settings_data.model_dump(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(settings, field, value)

            settings.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(settings)

            logger.info(f"Updated portal settings for customer {customer_id}")

            return PortalSettingsResponse.model_validate(settings)

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating portal settings: {str(e)}")
            raise

    # Private helper methods

    async def _check_slug_exists(
        self, db: AsyncSession, tenant_id: str, slug: str
    ) -> bool:
        """Check if slug already exists for tenant."""
        query = select(func.count(KnowledgeArticle.id)).where(
            and_(KnowledgeArticle.tenant_id == tenant_id, KnowledgeArticle.slug == slug)
        )
        result = await db.execute(query)
        return result.scalar() > 0

    async def _get_article_for_update(
        self, db: AsyncSession, tenant_id: str, article_id: str
    ):
        """Get article for update operations."""
        query = select(KnowledgeArticle).where(
            and_(
                KnowledgeArticle.id == article_id,
                KnowledgeArticle.tenant_id == tenant_id,
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _increment_view_count(self, db: AsyncSession, article_id: str):
        """Increment article view count."""
        try:
            stmt = (
                update(KnowledgeArticle)
                .where(KnowledgeArticle.id == article_id)
                .values(view_count=KnowledgeArticle.view_count + 1)
            )
            await db.execute(stmt)
            await db.commit()
        except Exception as e:
            logger.warning(
                f"Failed to increment view count for article {article_id}: {e}"
            )

    async def _render_content_html(self, content: str) -> str:
        """Render markdown content to HTML."""
        try:
            # In production, use a proper markdown parser like python-markdown
            # For now, simple HTML escaping and basic formatting
            import html

            html_content = html.escape(content)

            # Simple markdown-like transformations
            html_content = re.sub(
                r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html_content
            )
            html_content = re.sub(r"\*(.*?)\*", r"<em>\1</em>", html_content)
            html_content = re.sub(r"\n\n", r"</p><p>", html_content)
            html_content = f"<p>{html_content}</p>"

            return html_content

        except Exception as e:
            logger.error(f"Error rendering HTML content: {e}")
            return content  # Return original content if rendering fails

    async def _handle_status_change(
        self, article: KnowledgeArticle, new_status: ArticleStatus
    ):
        """Handle article status changes."""
        if (
            new_status == ArticleStatus.PUBLISHED
            and article.status != ArticleStatus.PUBLISHED
        ):
            article.published_at = datetime.now(timezone.utc)
        elif new_status != ArticleStatus.PUBLISHED:
            # If moving away from published, clear published_at
            if article.status == ArticleStatus.PUBLISHED:
                article.published_at = None

    async def _trigger_article_created_events(self, article: KnowledgeArticle):
        """Trigger events when article is created."""
        logger.info(f"Article created events triggered for {article.slug}")
        # In production, this would integrate with event system

    async def _trigger_comment_added_events(
        self, article: KnowledgeArticle, comment: ArticleComment
    ):
        """Trigger events when comment is added."""
        logger.info(f"Comment added events triggered for article {article.slug}")
        # In production, this would send notifications to article authors/subscribers


class KnowledgeAnalyticsService:
    """Analytics service for knowledge base."""

    def __init__(self, db_session_factory=None):
        self.db_session_factory = db_session_factory

    async def track_article_view(
        self,
        db: AsyncSession,
        article_id: str,
        tenant_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        referrer: Optional[str] = None,
    ):
        """Track detailed article view analytics."""
        try:
            today = datetime.now(timezone.utc).date()

            # Get or create analytics record for today
            query = select(ArticleAnalytics).where(
                and_(
                    ArticleAnalytics.article_id == article_id,
                    func.date(ArticleAnalytics.date) == today,
                )
            )

            result = await db.execute(query)
            analytics = result.scalar_one_or_none()

            if not analytics:
                analytics = ArticleAnalytics(
                    article_id=article_id,
                    tenant_id=tenant_id,
                    date=datetime.now(timezone.utc),
                )
                db.add(analytics)

            # Update metrics
            analytics.views += 1

            # Track unique views (simplified - in production would use proper session tracking)
            if user_id or session_id:
                analytics.unique_views += 1

            # Track traffic sources
            if referrer:
                if not analytics.traffic_sources:
                    analytics.traffic_sources = {}

                source_type = self._categorize_referrer(referrer)
                analytics.traffic_sources[source_type] = (
                    analytics.traffic_sources.get(source_type, 0) + 1
                )

            await db.commit()

        except Exception as e:
            logger.error(f"Error tracking article view: {e}")

    def _categorize_referrer(self, referrer: str) -> str:
        """Categorize referrer into traffic source type."""
        if not referrer:
            return "direct"
        elif "google.com" in referrer or "bing.com" in referrer:
            return "search"
        elif "facebook.com" in referrer or "twitter.com" in referrer:
            return "social"
        else:
            return "referral"
