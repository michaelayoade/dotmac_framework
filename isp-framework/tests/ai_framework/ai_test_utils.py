"""
AI Test Utilities
================

Utilities for AI-first testing approach.
"""

from typing import Any, Dict, List
from functools import wraps


class AITestGenerator:
    """AI test case generator utility."""
    
    @staticmethod
    def generate_billing_data() -> Dict[str, Any]:
        """Generate realistic billing test data."""
        return {
            'usage_gb': 100.0,
            'rate_per_gb': 0.10,
            'tax_rate': 0.08
        }
    
    @staticmethod
    def generate_customer_data() -> Dict[str, Any]:
        """Generate realistic customer test data.""" 
        return {
            'customer_id': 'test_customer_123',
            'email': 'test@example.com',
            'phone': '+1-555-123-4567'
        }
    
    @staticmethod
    def generate_service_data() -> Dict[str, Any]:
        """Generate realistic service test data."""
        return {
            'service_id': 'service_123',
            'monthly_cost': 79.99,
            'service_type': 'internet'
        }


def property_test(data_generator, max_examples=100):
    """Decorator for property-based tests."""
    def decorator(test_func):
        @wraps(test_func)
        def wrapper(*args, **kwargs):
            # Simple implementation - could be extended with Hypothesis
            for i in range(max_examples):
                test_data = data_generator
                if callable(test_data):
                    test_data = test_data()
                test_func(*args, test_data, **kwargs)
        return wrapper
    return decorator


# For backward compatibility
class AIPropertyTestGenerator:
    """Legacy AI property test generator."""
    
    @staticmethod
    def generate_billing_data():
        return AITestGenerator.generate_billing_data()
    
    @staticmethod
    def generate_customer_data():
        return AITestGenerator.generate_customer_data()
    
    @staticmethod
    def generate_service_data():
        return AITestGenerator.generate_service_data()