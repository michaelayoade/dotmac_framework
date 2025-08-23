"""
Cost Management Service - Infrastructure cost monitoring and optimization.

This service provides comprehensive cost tracking, analysis, and optimization
recommendations for the DotMac Management Platform across multiple cloud providers.
"""

from .service import CostManagementService
from .models import (
    CostMetric,
    CostAlert,
    CostBudget,
    OptimizationRecommendation,
    ResourceUtilization
)
from .schemas import (
    CostAnalysisRequest,
    CostAnalysisResponse,
    CostSummaryResponse,
    BudgetCreateRequest,
    OptimizationRecommendationResponse
)

__all__ = [
    'CostManagementService',
    'CostMetric',
    'CostAlert', 
    'CostBudget',
    'OptimizationRecommendation',
    'ResourceUtilization',
    'CostAnalysisRequest',
    'CostAnalysisResponse',
    'CostSummaryResponse',
    'BudgetCreateRequest',
    'OptimizationRecommendationResponse'
]