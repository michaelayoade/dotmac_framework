"""
AI-First Testing Framework

This framework provides utilities for AI-generated and AI-optimized testing:
- Property-based test generation
- Contract validation
- Behavior-driven testing
- Business outcome verification
"""

from .property_testing import AIPropertyTestGenerator, property_test
from .ai_test_utils import AITestGenerator

__all__ = [
    # Property-based testing
    "AIPropertyTestGenerator",
    "property_test",
    
    # AI utilities
    "AITestGenerator",
]