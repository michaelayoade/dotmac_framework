"""
FastAPI routes for feature flag management
"""
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta

try:
    from fastapi import APIRouter, HTTPException, Depends, Query, Body
    from fastapi.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    # FastAPI not available, create dummy classes
    FASTAPI_AVAILABLE = False
    class APIRouter:
        def __init__(self, prefix: str, tags: List[str]):
            pass
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
    class JSONResponse:
        pass
    def Query(*args, **kwargs):
        return None
    def Body(*args, **kwargs):
        return None
    def Depends(*args, **kwargs):
        return None

from pydantic import BaseModel, Field, validator

from .client import FeatureFlagClient
from .models import FeatureFlag, RolloutStrategy, FeatureFlagStatus, TargetingAttribute, ComparisonOperator
from dotmac_shared.core.logging import get_logger

logger = get_logger(__name__)


# Request/Response models
class CreateFlagRequest(BaseModel):
    """Request model for creating a feature flag"""
    key: str = Field(..., description="Unique flag key")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = None
    strategy: RolloutStrategy = RolloutStrategy.ALL_OFF
    percentage: float = Field(0.0, ge=0.0, le=100.0)
    user_list: List[str] = Field(default_factory=list)
    tenant_list: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    environments: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    payload: Optional[Dict[str, Any]] = None


class UpdateFlagRequest(BaseModel):
    """Request model for updating a feature flag"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[FeatureFlagStatus] = None
    strategy: Optional[RolloutStrategy] = None
    percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    user_list: Optional[List[str]] = None
    tenant_list: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    payload: Optional[Dict[str, Any]] = None


class TargetingRuleRequest(BaseModel):
    """Request model for adding targeting rules"""
    attribute: TargetingAttribute
    operator: ComparisonOperator
    value: Union[str, int, float, List[str], bool]
    description: Optional[str] = None


class ABTestVariantRequest(BaseModel):
    """Request model for A/B test variants"""
    name: str
    percentage: float = Field(ge=0.0, le=100.0)
    payload: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


class CreateABTestRequest(BaseModel):
    """Request model for creating A/B test flags"""
    key: str
    name: str
    description: Optional[str] = None
    variants: List[ABTestVariantRequest]
    tags: List[str] = Field(default_factory=list)
    environments: List[str] = Field(default_factory=list)
    
    @validator('variants')
    def validate_variants_sum_to_100(cls, v):
        total = sum(variant.percentage for variant in v)
        if abs(total - 100.0) > 0.01:
            raise ValueError(f'Variant percentages must sum to 100%, got {total}%')
        return v


class GradualRolloutRequest(BaseModel):
    """Request model for gradual rollouts"""
    duration_hours: int = Field(24, ge=1, le=720)  # Max 30 days
    start_percentage: float = Field(0.0, ge=0.0, le=100.0)
    end_percentage: float = Field(100.0, ge=0.0, le=100.0)
    increment_hours: int = Field(2, ge=1)
    
    @validator('end_percentage')
    def validate_end_greater_than_start(cls, v, values):
        if 'start_percentage' in values and v <= values['start_percentage']:
            raise ValueError('end_percentage must be greater than start_percentage')
        return v


class EvaluationRequest(BaseModel):
    """Request model for flag evaluation"""
    context: Dict[str, Any] = Field(default_factory=dict)


class EvaluationResponse(BaseModel):
    """Response model for flag evaluation"""
    enabled: bool
    variant: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


class FlagSummaryResponse(BaseModel):
    """Response model for flag summaries"""
    key: str
    name: str
    description: Optional[str]
    status: str
    strategy: str
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    # Strategy-specific fields
    percentage: Optional[float] = None
    user_count: Optional[int] = None
    current_percentage: Optional[float] = None
    variants: Optional[List[str]] = None


def create_feature_flag_router(client: FeatureFlagClient) -> APIRouter:
    """Create FastAPI router for feature flag management"""
    router = APIRouter(prefix="/api/feature-flags", tags=["Feature Flags"])
    
    @router.get("/", response_model=List[FlagSummaryResponse])
    async def list_flags(
        tags: Optional[str] = Query(None, description="Comma-separated list of tags to filter by")
    ):
        """List all feature flags"""
        try:
            tag_list = tags.split(",") if tags else None
            flags_data = await client.list_flags(tag_list)
            
            return [FlagSummaryResponse(**flag_data) for flag_data in flags_data]
        except Exception as e:
            logger.error(f"Error listing flags: {e}")
            raise HTTPException(status_code=500, detail="Failed to list feature flags")
    
    @router.get("/{flag_key}", response_model=Dict[str, Any])
    async def get_flag(flag_key: str):
        """Get detailed information about a specific flag"""
        try:
            flag_info = await client.get_flag_info(flag_key)
            if not flag_info:
                raise HTTPException(status_code=404, detail="Feature flag not found")
            
            return flag_info
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting flag {flag_key}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get feature flag")
    
    @router.post("/", status_code=201)
    async def create_flag(request: CreateFlagRequest):
        """Create a new feature flag"""
        try:
            # Convert request to FeatureFlag model
            flag_data = request.dict()
            if not flag_data["environments"]:
                flag_data["environments"] = [client.environment]
            
            flag = FeatureFlag(**flag_data, status=FeatureFlagStatus.ACTIVE)
            
            success = await client.manager.create_flag(flag)
            if not success:
                raise HTTPException(status_code=400, detail="Failed to create feature flag")
            
            return {"message": "Feature flag created successfully", "key": request.key}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating flag {request.key}: {e}")
            raise HTTPException(status_code=500, detail="Failed to create feature flag")
    
    @router.put("/{flag_key}")
    async def update_flag(flag_key: str, request: UpdateFlagRequest):
        """Update an existing feature flag"""
        try:
            # Get current flag
            current_flag = await client.manager.get_flag_details(flag_key)
            if not current_flag:
                raise HTTPException(status_code=404, detail="Feature flag not found")
            
            # Update fields
            update_data = request.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(current_flag, field, value)
            
            current_flag.updated_at = datetime.utcnow()
            
            success = await client.manager.update_flag(current_flag)
            if not success:
                raise HTTPException(status_code=400, detail="Failed to update feature flag")
            
            return {"message": "Feature flag updated successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating flag {flag_key}: {e}")
            raise HTTPException(status_code=500, detail="Failed to update feature flag")
    
    @router.delete("/{flag_key}")
    async def delete_flag(flag_key: str):
        """Delete a feature flag"""
        try:
            success = await client.delete_flag(flag_key)
            if not success:
                raise HTTPException(status_code=404, detail="Feature flag not found")
            
            return {"message": "Feature flag deleted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting flag {flag_key}: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete feature flag")
    
    @router.post("/{flag_key}/evaluate", response_model=EvaluationResponse)
    async def evaluate_flag(flag_key: str, request: EvaluationRequest):
        """Evaluate a feature flag for given context"""
        try:
            enabled = await client.is_enabled(flag_key, request.context)
            variant = await client.get_variant(flag_key, request.context)
            payload = await client.get_payload(flag_key, request.context)
            
            return EvaluationResponse(
                enabled=enabled,
                variant=variant,
                payload=payload
            )
        except Exception as e:
            logger.error(f"Error evaluating flag {flag_key}: {e}")
            raise HTTPException(status_code=500, detail="Failed to evaluate feature flag")
    
    @router.post("/{flag_key}/enable")
    async def enable_flag(flag_key: str):
        """Enable a feature flag (set to ALL_ON)"""
        try:
            success = await client.enable_flag(flag_key)
            if not success:
                raise HTTPException(status_code=404, detail="Feature flag not found")
            
            return {"message": "Feature flag enabled successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error enabling flag {flag_key}: {e}")
            raise HTTPException(status_code=500, detail="Failed to enable feature flag")
    
    @router.post("/{flag_key}/disable")
    async def disable_flag(flag_key: str):
        """Disable a feature flag (set to ALL_OFF)"""
        try:
            success = await client.disable_flag(flag_key)
            if not success:
                raise HTTPException(status_code=404, detail="Feature flag not found")
            
            return {"message": "Feature flag disabled successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error disabling flag {flag_key}: {e}")
            raise HTTPException(status_code=500, detail="Failed to disable feature flag")
    
    @router.put("/{flag_key}/percentage")
    async def update_percentage(flag_key: str, percentage: float = Body(..., ge=0.0, le=100.0)):
        """Update the percentage for a percentage-based flag"""
        try:
            success = await client.update_flag_percentage(flag_key, percentage)
            if not success:
                raise HTTPException(status_code=404, detail="Feature flag not found")
            
            return {"message": f"Flag percentage updated to {percentage}%"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating percentage for flag {flag_key}: {e}")
            raise HTTPException(status_code=500, detail="Failed to update percentage")
    
    @router.post("/{flag_key}/targeting-rules")
    async def add_targeting_rule(flag_key: str, rule: TargetingRuleRequest):
        """Add a targeting rule to a flag"""
        try:
            success = await client.add_targeting_rule(
                flag_key,
                rule.attribute.value,
                rule.operator.value,
                rule.value,
                rule.description or ""
            )
            if not success:
                raise HTTPException(status_code=404, detail="Feature flag not found")
            
            return {"message": "Targeting rule added successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error adding targeting rule to flag {flag_key}: {e}")
            raise HTTPException(status_code=500, detail="Failed to add targeting rule")
    
    @router.post("/{flag_key}/gradual-rollout")
    async def start_gradual_rollout(flag_key: str, request: GradualRolloutRequest):
        """Start a gradual rollout for a flag"""
        try:
            success = await client.start_gradual_rollout(
                flag_key,
                request.duration_hours,
                request.start_percentage,
                request.end_percentage
            )
            if not success:
                raise HTTPException(status_code=404, detail="Feature flag not found")
            
            return {"message": "Gradual rollout started successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error starting gradual rollout for flag {flag_key}: {e}")
            raise HTTPException(status_code=500, detail="Failed to start gradual rollout")
    
    @router.delete("/{flag_key}/gradual-rollout")
    async def stop_gradual_rollout(
        flag_key: str,
        final_percentage: Optional[float] = Query(None, ge=0.0, le=100.0)
    ):
        """Stop a gradual rollout"""
        try:
            success = await client.stop_gradual_rollout(flag_key, final_percentage)
            if not success:
                raise HTTPException(status_code=404, detail="Feature flag not found")
            
            return {"message": "Gradual rollout stopped successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error stopping gradual rollout for flag {flag_key}: {e}")
            raise HTTPException(status_code=500, detail="Failed to stop gradual rollout")
    
    @router.post("/ab-test", status_code=201)
    async def create_ab_test(request: CreateABTestRequest):
        """Create an A/B test feature flag"""
        try:
            variants = []
            for variant in request.variants:
                variants.append({
                    'name': variant.name,
                    'percentage': variant.percentage,
                    'payload': variant.payload,
                    'description': variant.description
                })
            
            success = await client.create_ab_test_flag(
                request.key,
                request.name,
                variants,
                request.description or "",
                request.tags
            )
            
            if not success:
                raise HTTPException(status_code=400, detail="Failed to create A/B test flag")
            
            return {"message": "A/B test flag created successfully", "key": request.key}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating A/B test flag {request.key}: {e}")
            raise HTTPException(status_code=500, detail="Failed to create A/B test flag")
    
    @router.post("/bulk/create")
    async def create_bulk_flags(config: Dict[str, Any]):
        """Create multiple flags from configuration"""
        try:
            results = await client.create_flags_from_config(config)
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            return {
                "message": f"Created {success_count}/{total_count} flags successfully",
                "results": results
            }
        except Exception as e:
            logger.error(f"Error in bulk flag creation: {e}")
            raise HTTPException(status_code=500, detail="Failed to create flags")
    
    @router.get("/export", response_model=Dict[str, Any])
    async def export_flags(tags: Optional[str] = Query(None)):
        """Export feature flag configurations"""
        try:
            tag_list = tags.split(",") if tags else None
            config = await client.export_flags(tag_list)
            
            return config
        except Exception as e:
            logger.error(f"Error exporting flags: {e}")
            raise HTTPException(status_code=500, detail="Failed to export flags")
    
    return router


def create_evaluation_router(client: FeatureFlagClient) -> APIRouter:
    """Create a lightweight router for flag evaluation only"""
    router = APIRouter(prefix="/api/flags", tags=["Flag Evaluation"])
    
    @router.post("/{flag_key}/check", response_model=Dict[str, bool])
    async def check_flag(flag_key: str, context: Dict[str, Any] = Body(default_factory=dict)):
        """Quick flag evaluation endpoint"""
        try:
            enabled = await client.is_enabled(flag_key, context)
            return {"enabled": enabled}
        except Exception as e:
            logger.error(f"Error checking flag {flag_key}: {e}")
            return {"enabled": False}  # Fail closed
    
    @router.post("/batch/check")
    async def check_multiple_flags(
        flags: List[str] = Body(...),
        context: Dict[str, Any] = Body(default_factory=dict)
    ):
        """Check multiple flags at once"""
        try:
            results = {}
            for flag_key in flags:
                try:
                    enabled = await client.is_enabled(flag_key, context)
                    results[flag_key] = {"enabled": enabled}
                except Exception as e:
                    logger.warning(f"Error checking flag {flag_key}: {e}")
                    results[flag_key] = {"enabled": False, "error": str(e)}
            
            return results
        except Exception as e:
            logger.error(f"Error in batch flag check: {e}")
            raise HTTPException(status_code=500, detail="Failed to check flags")
    
    return router