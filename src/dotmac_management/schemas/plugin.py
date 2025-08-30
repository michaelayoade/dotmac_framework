"""
Plugin system schemas for validation and serialization.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field
from schemas.common import BaseSchema, PaginatedResponse


class PluginBase(BaseModel):
    """PluginBase implementation."""

    name: str = Field(..., description="Plugin name")
    display_name: str = Field(..., description="Human-readable plugin name")
    description: Optional[str] = Field(None, description="Plugin description")
    version: str = Field(..., description="Plugin version")
    category: str = Field(..., description="Plugin category")
    author: str = Field(..., description="Plugin author")
    license: Optional[str] = Field(None, description="Plugin license")
    repository_url: Optional[str] = Field(None, description="Source repository URL")
    documentation_url: Optional[str] = Field(None, description="Documentation URL")
    is_official: bool = Field(default=False, description="Whether plugin is official")
    is_verified: bool = Field(default=False, description="Whether plugin is verified")
    is_active: bool = Field(default=True, description="Whether plugin is active")
    configuration_schema: Dict[str, Any] = Field(
        default_factory=dict, description="Configuration schema"
    )
    api_requirements: List[str] = Field(
        default_factory=list, description="Required API permissions"
    )
    dependencies: List[str] = Field(
        default_factory=list, description="Plugin dependencies"
    )
    supported_versions: List[str] = Field(
        default_factory=list, description="Supported platform versions"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )


class PluginCreate(PluginBase):
    """PluginCreate implementation."""

    pass


class PluginUpdate(BaseModel):
    """PluginUpdate implementation."""

    display_name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    category: Optional[str] = None
    license: Optional[str] = None
    repository_url: Optional[str] = None
    documentation_url: Optional[str] = None
    is_active: Optional[bool] = None
    configuration_schema: Optional[Dict[str, Any]] = None
    api_requirements: Optional[List[str]] = None
    dependencies: Optional[List[str]] = None
    supported_versions: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class Plugin(PluginBase, BaseSchema):
    """Plugin implementation."""

    download_count: int = Field(default=0, description="Total download count")
    rating: Optional[float] = Field(None, description="Average rating")
    review_count: int = Field(default=0, description="Number of reviews")


class PluginInstallationBase(BaseModel):
    """PluginInstallationBase implementation."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    plugin_id: UUID = Field(..., description="Plugin ID")
    status: str = Field(..., description="Installation status")
    installed_version: str = Field(..., description="Installed plugin version")
    configuration: Dict[str, Any] = Field(
        default_factory=dict, description="Plugin configuration"
    )
    enabled: bool = Field(default=True, description="Whether plugin is enabled")
    auto_update: bool = Field(default=False, description="Auto-update setting")
    installed_at: Optional[datetime] = Field(None, description="Installation timestamp")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Installation metadata"
    )


class PluginInstallationCreate(PluginInstallationBase):
    """PluginInstallationCreate implementation."""

    pass


class PluginInstallationUpdate(BaseModel):
    """PluginInstallationUpdate implementation."""

    status: Optional[str] = None
    installed_version: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    auto_update: Optional[bool] = None
    last_updated: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class PluginInstallation(PluginInstallationBase, BaseSchema):
    """PluginInstallation implementation."""

    plugin: Optional[Plugin] = None


class PluginHookBase(BaseModel):
    """PluginHookBase implementation."""

    plugin_id: UUID = Field(..., description="Plugin ID")
    hook_name: str = Field(..., description="Hook name")
    hook_type: str = Field(..., description="Hook type (event, filter, action)")
    priority: int = Field(default=10, description="Hook priority")
    callback_url: Optional[str] = Field(None, description="Webhook callback URL")
    configuration: Dict[str, Any] = Field(
        default_factory=dict, description="Hook configuration"
    )
    is_active: bool = Field(default=True, description="Whether hook is active")


class PluginHookCreate(PluginHookBase):
    """PluginHookCreate implementation."""

    pass


class PluginHookUpdate(BaseModel):
    """PluginHookUpdate implementation."""

    hook_name: Optional[str] = None
    priority: Optional[int] = None
    callback_url: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class PluginHook(PluginHookBase, BaseSchema):
    """PluginHook implementation."""

    plugin: Optional[Plugin] = None


class PluginReviewBase(BaseModel):
    """PluginReviewBase implementation."""

    tenant_id: UUID = Field(..., description="Reviewer tenant ID")
    plugin_id: UUID = Field(..., description="Plugin ID")
    rating: int = Field(..., ge=1, le=5, description="Rating (1-5)")
    title: Optional[str] = Field(None, description="Review title")
    content: Optional[str] = Field(None, description="Review content")
    version_reviewed: str = Field(..., description="Plugin version reviewed")


class PluginReviewCreate(PluginReviewBase):
    """PluginReviewCreate implementation."""

    pass


class PluginReviewUpdate(BaseModel):
    """PluginReviewUpdate implementation."""

    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = None
    content: Optional[str] = None


class PluginReview(PluginReviewBase, BaseSchema):
    """PluginReview implementation."""

    plugin: Optional[Plugin] = None


class PluginEventBase(BaseModel):
    """PluginEventBase implementation."""

    plugin_installation_id: UUID = Field(..., description="Plugin installation ID")
    event_type: str = Field(..., description="Event type")
    event_data: Dict[str, Any] = Field(..., description="Event data")
    processed: bool = Field(default=False, description="Whether event was processed")
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")
    error_message: Optional[str] = Field(
        None, description="Error message if processing failed"
    )
    retry_count: int = Field(default=0, description="Number of retry attempts")


class PluginEventCreate(PluginEventBase):
    """PluginEventCreate implementation."""

    pass


class PluginEvent(PluginEventBase, BaseSchema):
    """PluginEvent implementation."""

    installation: Optional[PluginInstallation] = None


# Response schemas
class PluginListResponse(PaginatedResponse):
    """PluginListResponse implementation."""

    items: List[Plugin]


class PluginInstallationListResponse(PaginatedResponse):
    """PluginInstallationListResponse implementation."""

    items: List[PluginInstallation]


class PluginHookListResponse(PaginatedResponse):
    """PluginHookListResponse implementation."""

    items: List[PluginHook]


class PluginReviewListResponse(PaginatedResponse):
    """PluginReviewListResponse implementation."""

    items: List[PluginReview]


class PluginEventListResponse(PaginatedResponse):
    """PluginEventListResponse implementation."""

    items: List[PluginEvent]


# Complex operation schemas
class PluginInstallRequest(BaseModel):
    """PluginInstallRequest implementation."""

    plugin_id: UUID = Field(..., description="Plugin to install")
    version: Optional[str] = Field(None, description="Specific version to install")
    configuration: Dict[str, Any] = Field(
        default_factory=dict, description="Initial configuration"
    )
    auto_update: bool = Field(default=False, description="Enable auto-updates")


class PluginUpdateRequest(BaseModel):
    """PluginUpdateRequest implementation."""

    version: Optional[str] = Field(None, description="Target version")
    configuration: Optional[Dict[str, Any]] = Field(
        None, description="Updated configuration"
    )


class PluginConfigurationUpdate(BaseModel):
    """PluginConfigurationUpdate implementation."""

    configuration: Dict[str, Any] = Field(..., description="Updated configuration")
    restart_required: bool = Field(
        default=False, description="Whether restart is required"
    )


class BulkPluginOperation(BaseModel):
    """BulkPluginOperation implementation."""

    plugin_ids: List[UUID] = Field(..., description="Plugin IDs to operate on")
    operation: str = Field(
        ..., description="Operation (enable, disable, update, uninstall)"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Operation parameters"
    )


# Plugin marketplace schemas
class PluginSearchFilters(BaseModel):
    """PluginSearchFilters implementation."""

    category: Optional[str] = None
    author: Optional[str] = None
    is_official: Optional[bool] = None
    is_verified: Optional[bool] = None
    min_rating: Optional[float] = Field(None, ge=0, le=5)
    tags: Optional[List[str]] = None


class PluginSearchRequest(BaseModel):
    """PluginSearchRequest implementation."""

    query: Optional[str] = Field(None, description="Search query")
    filters: Optional[PluginSearchFilters] = None
    sort_by: str = Field(default="popularity", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order")


class PluginAnalytics(BaseModel):
    """PluginAnalytics implementation."""

    plugin_id: UUID
    total_installations: int
    active_installations: int
    daily_installs: List[Dict[str, Any]]
    ratings_distribution: Dict[str, int]
    average_rating: float
    popular_versions: List[Dict[str, Any]]
    geographic_distribution: Dict[str, int]
    usage_statistics: Dict[str, Any]


class TenantPluginOverview(BaseModel):
    """TenantPluginOverview implementation."""

    tenant_id: UUID
    total_plugins_installed: int
    active_plugins: int
    plugins_needing_updates: int
    plugin_categories: Dict[str, int]
    resource_usage_by_plugins: Dict[str, float]
    recent_installations: List[PluginInstallation]
    recent_events: List[PluginEvent]


# Plugin development schemas
class PluginSubmission(BaseModel):
    """PluginSubmission implementation."""

    name: str = Field(..., description="Plugin name")
    display_name: str = Field(..., description="Display name")
    description: str = Field(..., description="Plugin description")
    version: str = Field(..., description="Initial version")
    category: str = Field(..., description="Plugin category")
    source_url: str = Field(..., description="Source repository URL")
    documentation_url: Optional[str] = None
    license: str = Field(..., description="License")
    configuration_schema: Dict[str, Any] = Field(
        ..., description="Configuration schema"
    )
    api_requirements: List[str] = Field(..., description="Required permissions")


class PluginValidationResult(BaseModel):
    """PluginValidationResult implementation."""

    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    security_score: Optional[int] = Field(None, ge=0, le=100)
    performance_score: Optional[int] = Field(None, ge=0, le=100)
    compatibility_matrix: Dict[str, bool] = Field(default_factory=dict)
