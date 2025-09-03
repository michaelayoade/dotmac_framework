"""
Knowledge Base Models - Production Ready with Pydantic v2
Leverages existing DotMac patterns and multi-tenant architecture
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict, validator
from sqlalchemy import (
    JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text,
    Index, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

from dotmac_shared.ticketing.core.models import TicketCategory

Base = declarative_base()


class ArticleStatus(str, Enum):
    """Article publication status."""
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ArticleType(str, Enum):
    """Article content types."""
    ARTICLE = "article"
    FAQ = "faq" 
    TUTORIAL = "tutorial"
    TROUBLESHOOTING = "troubleshooting"
    VIDEO = "video"
    DOWNLOAD = "download"


class KnowledgeArticle(Base):
    """Knowledge base article model."""
    
    __tablename__ = "knowledge_articles"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    
    # Content
    title = Column(String(500), nullable=False)
    slug = Column(String(500), nullable=False)  # URL-friendly version
    summary = Column(String(1000), nullable=True)
    content = Column(Text, nullable=False)
    content_html = Column(Text, nullable=True)  # Rendered HTML version
    
    # Classification
    article_type = Column(String, default=ArticleType.ARTICLE, nullable=False)
    category = Column(String, nullable=False, index=True)
    subcategory = Column(String, nullable=True, index=True)
    tags = Column(JSON, default=list)
    
    # Publishing
    status = Column(String, default=ArticleStatus.DRAFT, nullable=False, index=True)
    published_at = Column(DateTime, nullable=True, index=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Authoring
    author_id = Column(String, nullable=False, index=True)
    author_name = Column(String, nullable=False)
    reviewer_id = Column(String, nullable=True)
    reviewer_name = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Analytics
    view_count = Column(Integer, default=0, nullable=False)
    helpful_votes = Column(Integer, default=0, nullable=False)
    unhelpful_votes = Column(Integer, default=0, nullable=False)
    search_ranking = Column(Integer, default=0, nullable=False)
    
    # SEO & Search
    meta_description = Column(String(300), nullable=True)
    search_keywords = Column(JSON, default=list)  # For search optimization
    
    # Additional metadata
    external_links = Column(JSON, default=list)
    attachments = Column(JSON, default=list)
    related_tickets = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)
    
    # Relationships
    comments = relationship("ArticleComment", back_populates="article", cascade="all, delete-orphan")
    analytics = relationship("ArticleAnalytics", back_populates="article", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_article_tenant_status', 'tenant_id', 'status'),
        Index('ix_article_category_published', 'category', 'published_at'),
        Index('ix_article_search_ranking', 'search_ranking', 'view_count'),
        UniqueConstraint('tenant_id', 'slug', name='uq_article_slug_tenant'),
    )


class ArticleComment(Base):
    """Article comments and feedback."""
    
    __tablename__ = "article_comments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    article_id = Column(String, ForeignKey("knowledge_articles.id"), nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    
    # Content
    content = Column(Text, nullable=False)
    is_helpful_feedback = Column(Boolean, default=False)  # Structured feedback
    is_public = Column(Boolean, default=True)  # Public vs internal comment
    
    # Author
    author_id = Column(String, nullable=True, index=True)
    author_name = Column(String, nullable=False)
    author_email = Column(String, nullable=True)
    author_type = Column(String, default="customer")  # customer, staff, anonymous
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Moderation
    is_approved = Column(Boolean, default=True)
    moderated_by = Column(String, nullable=True)
    moderated_at = Column(DateTime, nullable=True)
    
    # Relationships
    article = relationship("KnowledgeArticle", back_populates="comments")


class ArticleAnalytics(Base):
    """Detailed article analytics."""
    
    __tablename__ = "article_analytics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    article_id = Column(String, ForeignKey("knowledge_articles.id"), nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    
    # Analytics data
    date = Column(DateTime, nullable=False, index=True)
    views = Column(Integer, default=0)
    unique_views = Column(Integer, default=0)
    time_on_page = Column(Integer, default=0)  # seconds
    bounce_rate = Column(Integer, default=0)  # percentage
    
    # User interaction
    helpful_votes = Column(Integer, default=0)
    unhelpful_votes = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    
    # Search analytics
    search_queries = Column(JSON, default=list)  # Queries that led to this article
    search_position = Column(Integer, nullable=True)  # Average position in search results
    
    # Traffic sources
    traffic_sources = Column(JSON, default=dict)  # direct, search, referral, etc.
    
    # Relationships
    article = relationship("KnowledgeArticle", back_populates="analytics")
    
    __table_args__ = (
        Index('ix_analytics_article_date', 'article_id', 'date'),
        UniqueConstraint('article_id', 'date', name='uq_analytics_article_date'),
    )


class CustomerPortalSettings(Base):
    """Customer portal personalization settings."""
    
    __tablename__ = "customer_portal_settings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    customer_id = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    
    # Notification preferences
    email_notifications = Column(Boolean, default=True)
    sms_notifications = Column(Boolean, default=False) 
    push_notifications = Column(Boolean, default=True)
    
    # Communication preferences
    preferred_language = Column(String, default="en")
    timezone = Column(String, default="UTC")
    preferred_contact_method = Column(String, default="email")
    
    # Portal preferences
    dashboard_layout = Column(JSON, default=dict)
    favorite_articles = Column(JSON, default=list)
    bookmarked_tickets = Column(JSON, default=list)
    
    # Privacy settings
    allow_chat_history = Column(Boolean, default=True)
    allow_analytics_tracking = Column(Boolean, default=True)
    public_profile = Column(Boolean, default=False)
    
    # Accessibility
    high_contrast_mode = Column(Boolean, default=False)
    large_text_mode = Column(Boolean, default=False)
    screen_reader_mode = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('customer_id', 'tenant_id', name='uq_customer_portal_settings'),
    )


# Pydantic v2 Models for API

class ArticleCreate(BaseModel):
    """Create article request."""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True
    )
    
    title: str = Field(..., min_length=1, max_length=500)
    slug: Optional[str] = Field(None, max_length=500, pattern=r'^[a-z0-9-]+$')
    summary: Optional[str] = Field(None, max_length=1000)
    content: str = Field(..., min_length=1)
    article_type: ArticleType = ArticleType.ARTICLE
    category: str = Field(..., min_length=1)
    subcategory: Optional[str] = None
    tags: List[str] = Field(default_factory=list, max_items=10)
    meta_description: Optional[str] = Field(None, max_length=300)
    search_keywords: List[str] = Field(default_factory=list, max_items=20)
    external_links: List[str] = Field(default_factory=list, max_items=10)
    
    @validator('slug', pre=True, always=True)
    def generate_slug(cls, v, values):
        if not v and 'title' in values:
            import re
            slug = re.sub(r'[^a-zA-Z0-9\s-]', '', values['title'])
            slug = re.sub(r'\s+', '-', slug.strip())
            return slug.lower()
        return v


class ArticleUpdate(BaseModel):
    """Update article request."""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True
    )
    
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    summary: Optional[str] = Field(None, max_length=1000)
    content: Optional[str] = Field(None, min_length=1)
    article_type: Optional[ArticleType] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    tags: Optional[List[str]] = Field(None, max_items=10)
    status: Optional[ArticleStatus] = None
    meta_description: Optional[str] = Field(None, max_length=300)
    search_keywords: Optional[List[str]] = Field(None, max_items=20)


class ArticleResponse(BaseModel):
    """Article API response."""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )
    
    id: str
    tenant_id: str
    title: str
    slug: str
    summary: Optional[str] = None
    content: str
    content_html: Optional[str] = None
    article_type: ArticleType
    category: str
    subcategory: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    status: ArticleStatus
    published_at: Optional[datetime] = None
    author_name: str
    created_at: datetime
    updated_at: datetime
    view_count: int = 0
    helpful_votes: int = 0
    unhelpful_votes: int = 0
    meta_description: Optional[str] = None
    search_keywords: List[str] = Field(default_factory=list)
    comment_count: Optional[int] = None


class ArticleSearchParams(BaseModel):
    """Article search parameters."""
    
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True
    )
    
    query: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = None
    article_type: Optional[ArticleType] = None
    tags: Optional[List[str]] = Field(None, max_items=10)
    status: Optional[List[ArticleStatus]] = Field(default_factory=lambda: [ArticleStatus.PUBLISHED])
    sort_by: str = Field(default="relevance", pattern=r'^(relevance|created_at|updated_at|view_count|helpful_votes)$')
    sort_order: str = Field(default="desc", pattern=r'^(asc|desc)$')
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class CommentCreate(BaseModel):
    """Create article comment."""
    
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True
    )
    
    content: str = Field(..., min_length=1, max_length=5000)
    is_helpful_feedback: bool = False
    is_public: bool = True


class CommentResponse(BaseModel):
    """Comment API response."""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )
    
    id: str
    article_id: str
    content: str
    is_helpful_feedback: bool
    is_public: bool
    author_name: str
    author_type: str
    created_at: datetime
    is_approved: bool


class PortalSettingsUpdate(BaseModel):
    """Update portal settings."""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )
    
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    preferred_language: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)
    preferred_contact_method: Optional[str] = None
    dashboard_layout: Optional[Dict[str, Any]] = None
    favorite_articles: Optional[List[str]] = Field(None, max_items=50)
    high_contrast_mode: Optional[bool] = None
    large_text_mode: Optional[bool] = None
    allow_analytics_tracking: Optional[bool] = None


class PortalSettingsResponse(BaseModel):
    """Portal settings response."""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )
    
    customer_id: str
    tenant_id: str
    email_notifications: bool
    sms_notifications: bool
    push_notifications: bool
    preferred_language: str
    timezone: str
    preferred_contact_method: str
    dashboard_layout: Dict[str, Any]
    favorite_articles: List[str]
    high_contrast_mode: bool
    large_text_mode: bool
    allow_analytics_tracking: bool
    created_at: datetime
    updated_at: datetime