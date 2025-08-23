"""
API documentation endpoints.
Provides comprehensive API documentation, SDK generation, and developer tools.
"""

import json
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status, Response, Request
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...core.auth import get_current_admin_user, get_current_user_dict
from ...core.exceptions import ValidationError, DatabaseError
from ...schemas.api_docs import (
    SDKLanguage,
    DocumentationFormat,
    APIDocumentationRequest,
    SDKGenerationRequest,
    CodeSample,
    DeveloperResource,
    DocumentationFeedback,
    ChangelogEntry
)
from ...services.api_documentation_service import APIDocumentationService

router = APIRouter(prefix="/docs", tags=["documentation"])


@router.get("/openapi.json")
async def get_openapi_spec(
    version: str = Query(default="v1"),
    include_examples: bool = Query(default=True),
    include_deprecated: bool = Query(default=False),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get OpenAPI specification in JSON format.
    """
    try:
        doc_service = APIDocumentationService(db, request.app)
        
        openapi_spec = await doc_service.generate_openapi_spec(
            include_examples=include_examples,
            include_schemas=True,
            version=version
        )
        
        # Filter deprecated endpoints if requested
        if not include_deprecated:
            filtered_paths = {}
            for path, methods in openapi_spec.get("paths", {}).items():
                filtered_methods = {}
                for method, operation in methods.items():
                    if not operation.get("deprecated", False):
                        filtered_methods[method] = operation
                if filtered_methods:
                    filtered_paths[path] = filtered_methods
            openapi_spec["paths"] = filtered_paths
        
        return JSONResponse(content=openapi_spec)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate OpenAPI spec: {str(e)}"
        )


@router.get("/openapi.yaml")
async def get_openapi_spec_yaml(
    version: str = Query(default="v1"),
    include_examples: bool = Query(default=True),
    include_deprecated: bool = Query(default=False),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get OpenAPI specification in YAML format.
    """
    try:
        doc_service = APIDocumentationService(db, request.app)
        
        openapi_spec = await doc_service.generate_openapi_spec(
            include_examples=include_examples,
            include_schemas=True,
            version=version
        )
        
        # Convert to YAML
        yaml_content = yaml.dump(openapi_spec, default_flow_style=False, sort_keys=False)
        
        return Response(
            content=yaml_content,
            media_type="application/x-yaml",
            headers={"Content-Disposition": f"attachment; filename=dotmac-api-{version}.yaml"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate OpenAPI YAML: {str(e)}"
        )


@router.get("/postman")
async def get_postman_collection(
    version: str = Query(default="v1"),
    include_auth: bool = Query(default=True),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get Postman collection for API testing.
    """
    try:
        doc_service = APIDocumentationService(db, request.app)
        
        collection = await doc_service.generate_postman_collection(
            version=version,
            include_auth=include_auth
        )
        
        return Response(
            content=json.dumps(collection, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=dotmac-api-{version}.postman_collection.json"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Postman collection: {str(e)}"
        )


@router.get("/sdk/{language}")
async def get_sdk_documentation(
    language: SDKLanguage,
    version: str = Query(default="v1"),
    format: str = Query(default="json"),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get SDK documentation for specified language.
    """
    try:
        doc_service = APIDocumentationService(db, request.app)
        
        sdk_docs = await doc_service.generate_sdk_documentation(
            language=language,
            version=version
        )
        
        if format.lower() == "json":
            return JSONResponse(content=sdk_docs)
        elif format.lower() == "yaml":
            yaml_content = yaml.dump(sdk_docs, default_flow_style=False, sort_keys=False)
            return Response(
                content=yaml_content,
                media_type="application/x-yaml",
                headers={"Content-Disposition": f"attachment; filename=dotmac-sdk-{language.value}-{version}.yaml"}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported format. Use 'json' or 'yaml'"
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate SDK documentation: {str(e)}"
        )


@router.get("/interactive")
async def get_interactive_docs_config(
    version: str = Query(default="v1"),
    theme: str = Query(default="default"),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get interactive documentation configuration.
    """
    try:
        doc_service = APIDocumentationService(db, request.app)
        
        config = await doc_service.create_interactive_docs(
            version=version,
            theme=theme
        )
        
        return JSONResponse(content=config)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate interactive docs config: {str(e)}"
        )


@router.get("/guide")
async def get_developer_guide(
    sections: Optional[List[str]] = Query(default=None),
    format: str = Query(default="json"),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive developer guide.
    """
    try:
        doc_service = APIDocumentationService(db, request.app)
        
        guide = await doc_service.generate_developer_guide(sections=sections)
        
        if format.lower() == "json":
            return JSONResponse(content=guide)
        elif format.lower() == "markdown":
            # Convert to markdown format
            markdown_content = await _convert_guide_to_markdown(guide)
            return Response(
                content=markdown_content,
                media_type="text/markdown",
                headers={"Content-Disposition": "attachment; filename=dotmac-developer-guide.md"}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported format. Use 'json' or 'markdown'"
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate developer guide: {str(e)}"
        )


@router.get("/code-samples")
async def get_code_samples(
    language: Optional[SDKLanguage] = Query(default=None),
    endpoint: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Get code samples with optional filtering.
    """
    try:
        # In a real implementation, this would query a database of code samples
        # For now, return sample data
        
        samples = [
            {
                "id": "sample_1",
                "language": "python",
                "title": "Create Tenant",
                "description": "Example of creating a new tenant",
                "code": '''
import requests

response = requests.post(
    "https://api.dotmac.io/v1/tenants",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json={
        "name": "Acme Corp",
        "domain": "acme.example.com"
    }
)

tenant = response.json()
print(f"Created tenant: {tenant['id']}")
                '''.strip(),
                "endpoint": "/api/v1/tenants",
                "category": "tenant_management"
            },
            {
                "id": "sample_2",
                "language": "javascript",
                "title": "List Users",
                "description": "Example of listing users with pagination",
                "code": '''
const response = await fetch('https://api.dotmac.io/v1/users?limit=10&offset=0', {
    headers: {
        'Authorization': 'Bearer YOUR_TOKEN',
        'Content-Type': 'application/json'
    }
});

const data = await response.json();
console.log(`Found ${data.users.length} users`);
                '''.strip(),
                "endpoint": "/api/v1/users",
                "category": "user_management"
            }
        ]
        
        # Apply filters
        if language:
            samples = [s for s in samples if s["language"] == language.value]
        if endpoint:
            samples = [s for s in samples if s["endpoint"] == endpoint]
        if category:
            samples = [s for s in samples if s["category"] == category]
        
        return {
            "samples": samples,
            "total_count": len(samples),
            "languages": list(set(s["language"] for s in samples)),
            "categories": list(set(s["category"] for s in samples))
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get code samples: {str(e)}"
        )


@router.post("/code-samples")
async def create_code_sample(
    sample: CodeSample,
    current_user: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new code sample.
    """
    try:
        # In a real implementation, this would save to database
        sample_data = sample.dict()
        sample_data["id"] = "sample_new"
        sample_data["created_by"] = current_user["user_id"]
        sample_data["created_at"] = datetime.utcnow().isoformat()
        
        return {
            "sample": sample_data,
            "status": "created"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create code sample: {str(e)}"
        )


@router.get("/changelog")
async def get_changelog(
    version: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Get API changelog with optional version filtering.
    """
    try:
        # In a real implementation, this would query changelog from database
        changelog_entries = [
            {
                "version": "1.2.0",
                "release_date": "2024-01-15T00:00:00Z",
                "type": "minor",
                "changes": [
                    {
                        "type": "added",
                        "description": "New analytics endpoints for revenue reporting",
                        "category": "analytics"
                    },
                    {
                        "type": "improved",
                        "description": "Enhanced error messages for validation failures",
                        "category": "general"
                    },
                    {
                        "type": "fixed",
                        "description": "Fixed pagination issue in user listing endpoint",
                        "category": "bug_fix"
                    }
                ],
                "breaking_changes": [],
                "author": "API Team"
            },
            {
                "version": "1.1.0",
                "release_date": "2024-01-01T00:00:00Z",
                "type": "minor",
                "changes": [
                    {
                        "type": "added",
                        "description": "Webhook support for real-time notifications",
                        "category": "webhooks"
                    },
                    {
                        "type": "added",
                        "description": "Infrastructure provisioning endpoints",
                        "category": "infrastructure"
                    }
                ],
                "breaking_changes": [],
                "author": "API Team"
            }
        ]
        
        # Filter by version if specified
        if version:
            changelog_entries = [e for e in changelog_entries if e["version"] == version]
        
        # Apply pagination
        total_count = len(changelog_entries)
        changelog_entries = changelog_entries[offset:offset + limit]
        
        return {
            "changelog": changelog_entries,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_next": offset + limit < total_count,
                "has_prev": offset > 0
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get changelog: {str(e)}"
        )


@router.post("/changelog")
async def create_changelog_entry(
    entry: ChangelogEntry,
    current_user: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new changelog entry.
    """
    try:
        # Check permissions - only admins can create changelog entries
        if current_user["role"] not in ["super_admin", "platform_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to create changelog entries"
            )
        
        # In a real implementation, this would save to database
        entry_data = entry.dict()
        entry_data["id"] = "changelog_new"
        entry_data["author"] = current_user["user_id"]
        
        return {
            "changelog_entry": entry_data,
            "status": "created"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create changelog entry: {str(e)}"
        )


@router.get("/metrics")
async def get_api_metrics(
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    current_user: Dict = Depends(get_current_admin_user),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get API usage metrics and documentation analytics.
    """
    try:
        doc_service = APIDocumentationService(db, request.app)
        
        metrics = await doc_service.get_api_metrics(
            start_date=start_date,
            end_date=end_date
        )
        
        return metrics
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get API metrics: {str(e)}"
        )


@router.get("/resources")
async def get_developer_resources(
    type: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    difficulty: Optional[str] = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Get developer resources with filtering and pagination.
    """
    try:
        # In a real implementation, this would query resources from database
        resources = [
            {
                "resource_id": "resource_1",
                "title": "Getting Started Guide",
                "description": "Complete guide to getting started with the DotMac API",
                "type": "guide",
                "category": "onboarding",
                "difficulty": "beginner",
                "estimated_time": "30 minutes",
                "content_url": "https://docs.dotmac.io/getting-started",
                "tags": ["quickstart", "authentication", "first_request"],
                "rating": 4.8,
                "views": 1500
            },
            {
                "resource_id": "resource_2",
                "title": "Webhook Integration Tutorial",
                "description": "Learn how to integrate webhooks for real-time notifications",
                "type": "tutorial",
                "category": "webhooks",
                "difficulty": "intermediate",
                "estimated_time": "45 minutes",
                "content_url": "https://docs.dotmac.io/webhooks-tutorial",
                "tags": ["webhooks", "real-time", "notifications"],
                "rating": 4.6,
                "views": 800
            }
        ]
        
        # Apply filters
        if type:
            resources = [r for r in resources if r["type"] == type]
        if category:
            resources = [r for r in resources if r["category"] == category]
        if difficulty:
            resources = [r for r in resources if r["difficulty"] == difficulty]
        
        # Apply pagination
        total_count = len(resources)
        resources = resources[offset:offset + limit]
        
        return {
            "resources": resources,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_next": offset + limit < total_count,
                "has_prev": offset > 0
            },
            "filters": {
                "types": ["guide", "tutorial", "example", "tool"],
                "categories": ["onboarding", "webhooks", "billing", "infrastructure"],
                "difficulties": ["beginner", "intermediate", "advanced"]
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get developer resources: {str(e)}"
        )


@router.post("/feedback")
async def submit_documentation_feedback(
    feedback: DocumentationFeedback,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit feedback about documentation.
    """
    try:
        # In a real implementation, this would save feedback to database
        feedback_data = feedback.dict()
        feedback_data["feedback_id"] = "feedback_new"
        feedback_data["status"] = "open"
        
        # Could trigger notification to documentation team
        
        return {
            "feedback_id": feedback_data["feedback_id"],
            "status": "submitted",
            "message": "Thank you for your feedback! We'll review it and get back to you."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.get("/stats")
async def get_documentation_stats(
    current_user: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get documentation statistics and usage analytics.
    """
    try:
        # In a real implementation, this would aggregate stats from various sources
        stats = {
            "total_pages": 150,
            "total_endpoints": 85,
            "total_examples": 200,
            "supported_languages": ["python", "javascript", "go", "php"],
            "page_views": {
                "/docs/getting-started": 5000,
                "/docs/authentication": 3500,
                "/docs/webhooks": 2800,
                "/docs/billing": 2200
            },
            "search_queries": {
                "authentication": 1200,
                "webhooks": 800,
                "rate limiting": 600,
                "pagination": 450
            },
            "feedback_summary": {
                "positive": 85,
                "neutral": 12,
                "negative": 8
            },
            "user_engagement": {
                "avg_time_on_page": 3.5,
                "bounce_rate": 0.25,
                "page_completion_rate": 0.78
            },
            "last_updated": datetime.utcnow().isoformat()
        }
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get documentation stats: {str(e)}"
        )


@router.post("/generate")
async def generate_custom_documentation(
    request_data: APIDocumentationRequest,
    current_user: Dict = Depends(get_current_admin_user),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate custom documentation in specified format.
    """
    try:
        doc_service = APIDocumentationService(db, request.app)
        
        if request_data.format == DocumentationFormat.OPENAPI:
            result = await doc_service.generate_openapi_spec(
                include_examples=request_data.include_examples,
                include_schemas=request_data.include_schemas,
                version=request_data.version
            )
        elif request_data.format == DocumentationFormat.POSTMAN:
            result = await doc_service.generate_postman_collection(
                version=request_data.version,
                include_auth=True
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported documentation format: {request_data.format}"
            )
        
        return {
            "format": request_data.format,
            "version": request_data.version,
            "generated_at": datetime.utcnow().isoformat(),
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate documentation: {str(e)}"
        )


# Helper functions

async def _convert_guide_to_markdown(guide: Dict[str, Any]) -> str:
    """Convert developer guide to markdown format."""
    markdown_content = f"# {guide['title']}\n\n"
    markdown_content += f"Version: {guide['version']}\n"
    markdown_content += f"Last Updated: {guide['last_updated']}\n\n"
    
    for section_name, section_data in guide['sections'].items():
        markdown_content += f"## {section_data['title']}\n\n"
        markdown_content += f"{section_data['content']}\n\n"
        
        for subsection in section_data.get('subsections', []):
            markdown_content += f"### {subsection}\n\n"
    
    return markdown_content