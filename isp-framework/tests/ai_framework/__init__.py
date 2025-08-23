"""
AI-First Testing Framework

This framework provides utilities for AI-generated and AI-optimized testing:
- Property-based test generation
- Contract validation
- Behavior-driven testing
- Business outcome verification
"""

from .property_testing import AIPropertyTestGenerator, property_test
from .contract_testing import ContractValidator, contract_test
from .behavior_testing import BehaviorValidator, behavior_test
from .ai_test_utils import AITestUtils, generate_test_data
from .business_validators import BusinessRuleValidator, revenue_critical

__all__ = [
    # Property-based testing
    "AIPropertyTestGenerator",
    "property_test",
    
    # Contract testing
    "ContractValidator", 
    "contract_test",
    
    # Behavior testing
    "BehaviorValidator",
    "behavior_test",
    
    # AI utilities
    "AITestUtils",
    "generate_test_data",
    
    # Business validation
    "BusinessRuleValidator",
    "revenue_critical",
]