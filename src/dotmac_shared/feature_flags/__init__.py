"""
Feature Flag System for DotMac Framework
Supports gradual rollouts, A/B testing, and safe deployments
"""

from .manager import FeatureFlagManager
from .models import FeatureFlag, RolloutStrategy, TargetingRule
from .decorators import feature_flag, requires_feature, ab_test
from .middleware import FeatureFlagMiddleware
from .client import FeatureFlagClient
from .api import create_feature_flag_router

__all__ = [
    'FeatureFlagManager',
    'FeatureFlag',
    'RolloutStrategy', 
    'TargetingRule',
    'feature_flag',
    'requires_feature',
    'ab_test',
    'FeatureFlagMiddleware',
    'FeatureFlagClient',
    'create_feature_flag_router',
]