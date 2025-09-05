"""
API documentation schemas for validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class SDKLanguage(str, Enum):
    """Supported SDK languages."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    PHP = "php"
    RUBY = "ruby"
    JAVA = "java"
    CSHARP = "csharp"
    SWIFT = "swift"
    KOTLIN = "kotlin"


class DocumentationFormat(str, Enum):
    """Documentation output formats."""

    OPENAPI = "openapi"
    SWAGGER = "swagger"
    REDOC = "redoc"
    POSTMAN = "postman"
    INSOMNIA = "insomnia"
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"


class APIEndpointMethod(str, Enum):
    """HTTP methods for API endpoints."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class APIEndpoint(BaseModel):
    """API endpoint schema."""

    path: str = Field(..., description="Endpoint path")
    method: APIEndpointMethod = Field(..., description="HTTP method")
    summary: str = Field(..., description="Endpoint summary")
    description: Optional[str] = Field(None, description="Detailed description")
    tags: list[str] = Field(default_factory=list, description="Endpoint tags")
    parameters: list[dict[str, Any]] = Field(
        default_factory=list, description="Request parameters"
    )
    request_body: Optional[dict[str, Any]] = Field(
        None, description="Request body schema"
    )
    responses: dict[str, dict[str, Any]] = Field(..., description="Response schemas")
    examples: Optional[dict[str, Any]] = Field(
        None, description="Request/response examples"
    )
    deprecated: bool = Field(
        default=False, description="Whether endpoint is deprecated"
    )
    rate_limit: Optional[dict[str, int]] = Field(None, description="Rate limiting info")
    requires_auth: bool = Field(
        default=True, description="Whether authentication is required"
    )
    permissions: list[str] = Field(
        default_factory=list, description="Required permissions"
    )


class CodeSample(BaseModel):
    """Code sample schema."""

    language: SDKLanguage = Field(..., description="Programming language")
    title: str = Field(..., description="Sample title")
    description: Optional[str] = Field(None, description="Sample description")
    code: str = Field(..., description="Code content")
    output: Optional[str] = Field(None, description="Expected output")
    endpoint: Optional[str] = Field(None, description="Related API endpoint")
    category: str = Field(default="general", description="Sample category")


class APIDocumentation(BaseModel):
    """API documentation schema."""

    title: str = Field(..., description="Documentation title")
    version: str = Field(..., description="API version")
    description: str = Field(..., description="API description")
    base_url: HttpUrl = Field(..., description="Base API URL")
    endpoints: list[APIEndpoint] = Field(..., description="API endpoints")
    schemas: dict[str, dict[str, Any]] = Field(..., description="Data schemas")
    authentication: dict[str, Any] = Field(..., description="Authentication methods")
    rate_limiting: dict[str, Any] = Field(..., description="Rate limiting information")
    error_codes: dict[str, str] = Field(..., description="Error code descriptions")
    changelog: list[dict[str, Any]] = Field(..., description="API changelog")
    generated_at: datetime = Field(..., description="Generation timestamp")


class SDKDocumentation(BaseModel):
    """SDK documentation schema."""

    language: SDKLanguage = Field(..., description="SDK language")
    version: str = Field(..., description="SDK version")
    api_version: str = Field(..., description="Compatible API version")
    installation: dict[str, str] = Field(..., description="Installation instructions")
    quickstart: dict[str, str] = Field(..., description="Quickstart guide")
    authentication: dict[str, str] = Field(..., description="Authentication examples")
    code_samples: list[CodeSample] = Field(..., description="Code samples")
    error_handling: dict[str, str] = Field(..., description="Error handling examples")
    best_practices: list[str] = Field(..., description="Best practices")
    changelog: list[dict[str, Any]] = Field(..., description="SDK changelog")
    download_url: Optional[HttpUrl] = Field(None, description="SDK download URL")
    repository_url: Optional[HttpUrl] = Field(None, description="Source repository URL")
    documentation_url: Optional[HttpUrl] = Field(
        None, description="Full documentation URL"
    )


class DeveloperGuide(BaseModel):
    """Developer guide schema."""

    title: str = Field(..., description="Guide title")
    version: str = Field(..., description="Guide version")
    sections: list[dict[str, Any]] = Field(..., description="Guide sections")
    last_updated: datetime = Field(..., description="Last update timestamp")
    authors: list[str] = Field(default_factory=list, description="Guide authors")
    reviewers: list[str] = Field(default_factory=list, description="Guide reviewers")
    next_review: Optional[datetime] = Field(None, description="Next review date")


class GuideSection(BaseModel):
    """Guide section schema."""

    id: str = Field(..., description="Section identifier")
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content (Markdown)")
    order: int = Field(..., description="Section order")
    subsections: list["GuideSection"] = Field(
        default_factory=list, description="Subsections"
    )
    code_samples: list[CodeSample] = Field(
        default_factory=list, description="Code samples"
    )
    images: list[str] = Field(default_factory=list, description="Image URLs")
    links: list[dict[str, str]] = Field(
        default_factory=list, description="External links"
    )
    tags: list[str] = Field(default_factory=list, description="Section tags")
    difficulty: str = Field(default="beginner", description="Difficulty level")


class ChangelogEntry(BaseModel):
    """Changelog entry schema."""

    version: str = Field(..., description="Release version")
    release_date: datetime = Field(..., description="Release date")
    type: str = Field(..., description="Release type (major, minor, patch)")
    changes: list[dict[str, Any]] = Field(..., description="List of changes")
    breaking_changes: list[str] = Field(
        default_factory=list, description="Breaking changes"
    )
    migration_guide: Optional[str] = Field(None, description="Migration guide URL")
    author: str = Field(..., description="Release author")
    created_at: datetime = Field(..., description="Entry creation timestamp")


class ChangelogChange(BaseModel):
    """Individual changelog change schema."""

    type: str = Field(
        ...,
        description="Change type (added, changed, deprecated, removed, fixed, security)",
    )
    description: str = Field(..., description="Change description")
    issue_number: Optional[str] = Field(None, description="Related issue number")
    pull_request: Optional[str] = Field(None, description="Related pull request")
    impact: str = Field(default="low", description="Impact level (low, medium, high)")
    category: str = Field(default="general", description="Change category")


class PostmanCollection(BaseModel):
    """Postman collection schema."""

    info: dict[str, str] = Field(..., description="Collection information")
    auth: Optional[dict[str, Any]] = Field(
        None, description="Authentication configuration"
    )
    variables: list[dict[str, str]] = Field(..., description="Collection variables")
    items: list[dict[str, Any]] = Field(..., description="Request items")
    events: list[dict[str, Any]] = Field(
        default_factory=list, description="Collection events"
    )
    generated_at: datetime = Field(..., description="Generation timestamp")


class OpenAPISpec(BaseModel):
    """OpenAPI specification schema."""

    openapi: str = Field(default="3.0.3", description="OpenAPI version")
    info: dict[str, Any] = Field(..., description="API information")
    servers: list[dict[str, str]] = Field(..., description="Server configurations")
    paths: dict[str, dict[str, Any]] = Field(..., description="API paths")
    components: dict[str, Any] = Field(..., description="Reusable components")
    security: list[dict[str, list[str]]] = Field(
        default_factory=list, description="Security requirements"
    )
    tags: list[dict[str, str]] = Field(default_factory=list, description="API tags")
    external_docs: Optional[dict[str, str]] = Field(
        None, description="External documentation"
    )


class InteractiveDocsConfig(BaseModel):
    """Interactive documentation configuration schema."""

    title: str = Field(..., description="Documentation title")
    version: str = Field(..., description="API version")
    theme: str = Field(default="default", description="Documentation theme")
    spec_url: str = Field(..., description="OpenAPI spec URL")
    redoc_config: dict[str, Any] = Field(..., description="ReDoc configuration")
    swagger_config: dict[str, Any] = Field(..., description="Swagger UI configuration")
    custom_css: Optional[str] = Field(None, description="Custom CSS styles")
    custom_js: Optional[str] = Field(None, description="Custom JavaScript")
    logo_url: Optional[HttpUrl] = Field(None, description="Logo URL")
    favicon_url: Optional[HttpUrl] = Field(None, description="Favicon URL")
    google_analytics: Optional[str] = Field(None, description="Google Analytics ID")


class APIExample(BaseModel):
    """API example schema."""

    name: str = Field(..., description="Example name")
    description: str = Field(..., description="Example description")
    endpoint: str = Field(..., description="API endpoint")
    method: APIEndpointMethod = Field(..., description="HTTP method")
    request_headers: dict[str, str] = Field(
        default_factory=dict, description="Request headers"
    )
    request_body: Optional[dict[str, Any]] = Field(None, description="Request body")
    response_status: int = Field(..., description="Response status code")
    response_headers: dict[str, str] = Field(
        default_factory=dict, description="Response headers"
    )
    response_body: dict[str, Any] = Field(..., description="Response body")
    curl_command: Optional[str] = Field(None, description="Generated cURL command")
    code_samples: list[CodeSample] = Field(
        default_factory=list, description="Code samples"
    )


class APIMetrics(BaseModel):
    """API usage metrics schema."""

    period: dict[str, Optional[str]] = Field(..., description="Metrics period")
    total_requests: int = Field(..., description="Total API requests")
    unique_developers: int = Field(..., description="Number of unique developers")
    most_used_endpoints: list[dict[str, Any]] = Field(
        ..., description="Most popular endpoints"
    )
    error_rates: dict[str, float] = Field(..., description="Error rates by type")
    response_times: dict[str, float] = Field(
        ..., description="Response time percentiles"
    )
    sdk_downloads: dict[str, int] = Field(..., description="SDK download counts")
    documentation_views: int = Field(..., description="Documentation page views")
    geographic_usage: dict[str, int] = Field(
        default_factory=dict, description="Usage by geography"
    )
    user_agents: dict[str, int] = Field(
        default_factory=dict, description="Usage by user agent"
    )
    generated_at: datetime = Field(..., description="Metrics generation timestamp")


class DeveloperResource(BaseModel):
    """Developer resource schema."""

    resource_id: UUID = Field(..., description="Resource identifier")
    title: str = Field(..., description="Resource title")
    description: str = Field(..., description="Resource description")
    type: str = Field(..., description="Resource type (guide, tutorial, example, tool)")
    category: str = Field(..., description="Resource category")
    difficulty: str = Field(..., description="Difficulty level")
    estimated_time: Optional[str] = Field(None, description="Estimated completion time")
    content_url: Optional[HttpUrl] = Field(None, description="Content URL")
    download_url: Optional[HttpUrl] = Field(None, description="Download URL")
    prerequisites: list[str] = Field(default_factory=list, description="Prerequisites")
    tags: list[str] = Field(default_factory=list, description="Resource tags")
    rating: Optional[float] = Field(None, description="Average user rating")
    views: int = Field(default=0, description="Number of views")
    downloads: int = Field(default=0, description="Number of downloads")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class APITestCase(BaseModel):
    """API test case schema."""

    test_id: UUID = Field(..., description="Test case identifier")
    name: str = Field(..., description="Test case name")
    description: str = Field(..., description="Test case description")
    endpoint: str = Field(..., description="API endpoint")
    method: APIEndpointMethod = Field(..., description="HTTP method")
    setup: Optional[dict[str, Any]] = Field(None, description="Test setup requirements")
    request: dict[str, Any] = Field(..., description="Test request configuration")
    expected_response: dict[str, Any] = Field(..., description="Expected response")
    assertions: list[str] = Field(..., description="Test assertions")
    tags: list[str] = Field(default_factory=list, description="Test tags")
    category: str = Field(..., description="Test category")
    automated: bool = Field(default=True, description="Whether test is automated")


class DocumentationFeedback(BaseModel):
    """Documentation feedback schema."""

    feedback_id: UUID = Field(..., description="Feedback identifier")
    page_url: str = Field(..., description="Documentation page URL")
    section: Optional[str] = Field(None, description="Specific section")
    feedback_type: str = Field(
        ..., description="Feedback type (bug, improvement, question)"
    )
    rating: Optional[int] = Field(None, ge=1, le=5, description="Page rating (1-5)")
    message: str = Field(..., description="Feedback message")
    user_email: Optional[str] = Field(None, description="User email (optional)")
    user_agent: Optional[str] = Field(None, description="User agent")
    ip_address: Optional[str] = Field(None, description="IP address")
    created_at: datetime = Field(..., description="Feedback timestamp")
    status: str = Field(default="open", description="Feedback status")
    response: Optional[str] = Field(None, description="Response to feedback")
    responded_by: Optional[UUID] = Field(None, description="User who responded")
    responded_at: Optional[datetime] = Field(None, description="Response timestamp")


class APIDocumentationRequest(BaseModel):
    """API documentation generation request schema."""

    format: DocumentationFormat = Field(..., description="Output format")
    version: str = Field(..., description="API version")
    include_examples: bool = Field(default=True, description="Include examples")
    include_schemas: bool = Field(default=True, description="Include detailed schemas")
    include_deprecated: bool = Field(
        default=False, description="Include deprecated endpoints"
    )
    filter_tags: Optional[list[str]] = Field(
        None, description="Filter by specific tags"
    )
    custom_config: Optional[dict[str, Any]] = Field(
        None, description="Custom configuration"
    )
    output_filename: Optional[str] = Field(None, description="Output filename")


class SDKGenerationRequest(BaseModel):
    """SDK generation request schema."""

    language: SDKLanguage = Field(..., description="Target language")
    version: str = Field(..., description="SDK version")
    api_version: str = Field(..., description="Target API version")
    package_name: str = Field(..., description="Package/module name")
    namespace: Optional[str] = Field(None, description="Namespace/package namespace")
    include_examples: bool = Field(default=True, description="Include code examples")
    include_tests: bool = Field(default=True, description="Include test files")
    custom_config: Optional[dict[str, Any]] = Field(
        None, description="Language-specific configuration"
    )
    output_format: str = Field(default="zip", description="Output format (zip, tar.gz)")


class DocumentationStats(BaseModel):
    """Documentation statistics schema."""

    total_pages: int = Field(..., description="Total documentation pages")
    total_endpoints: int = Field(..., description="Total API endpoints")
    total_examples: int = Field(..., description="Total code examples")
    supported_languages: list[str] = Field(..., description="Supported SDK languages")
    page_views: dict[str, int] = Field(..., description="Page views by URL")
    search_queries: dict[str, int] = Field(..., description="Popular search queries")
    feedback_summary: dict[str, int] = Field(
        ..., description="Feedback summary by type"
    )
    user_engagement: dict[str, float] = Field(
        ..., description="User engagement metrics"
    )
    last_updated: datetime = Field(..., description="Last statistics update")


# Forward reference resolution
GuideSection.model_rebuild()
