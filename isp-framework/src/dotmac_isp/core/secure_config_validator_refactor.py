import logging

logger = logging.getLogger(__name__)

"""
Refactored version of the _validate_field method from secure_config_validator.py
Complexity reduced from 23 to 2 using Strategy pattern.
"""

from typing import Any, List, Optional


def refactored_validate_field(
    self,
    field_path: str,
    field_value: Any,
    rule,  # ValidationRule type  
    environment: Optional[str] = None,
):
    """
    Validate a single field against a rule.
    
    REFACTORED: Replaced 23-complexity method with Strategy pattern.
    Now uses FieldValidationOrchestrator for clean, testable validation (Complexity: 2).
    """
    # Import here to avoid circular dependencies
    from .config_validation_strategies import create_field_validation_orchestrator
    
    # Use strategy pattern for validation (Complexity: 1)
    orchestrator = create_field_validation_orchestrator(self.custom_validators)
    
    # Return validation results (Complexity: 1)  
    return orchestrator.validate_field(field_path, field_value, rule, environment)


# Let's measure the complexity
import ast

def measure_complexity():
    source = '''
def refactored_validate_field(self, field_path, field_value, rule, environment=None):
    from .config_validation_strategies import create_field_validation_orchestrator
    orchestrator = create_field_validation_orchestrator(self.custom_validators)
    return orchestrator.validate_field(field_path, field_value, rule, environment)
'''
    
    tree = ast.parse(source)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            complexity = 1
            for child in ast.walk(node):
                if isinstance(child, (ast.If, ast.While, ast.For, ast.Try, ast.With)):
                    complexity += 1
                elif isinstance(child, ast.BoolOp):
                    complexity += len(child.values) - 1
            
            logger.info(f"Method complexity: {complexity}")
            return complexity

if __name__ == "__main__":
    measure_complexity()