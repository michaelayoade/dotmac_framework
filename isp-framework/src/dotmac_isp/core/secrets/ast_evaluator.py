"""
Secure AST Expression Evaluator - Extracted from RBAC for better maintainability.

This module provides safe evaluation of Python expressions using AST parsing,
preventing code injection while supporting common comparison and logical operations.
"""

import ast
import logging
import operator
from typing import Any

logger = logging.getLogger(__name__)


class ASTNodeEvaluator:
    """Handles evaluation of specific AST node types."""

    # Supported operators mapping
    OPERATORS = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.In: lambda a, b: a in b,
        ast.NotIn: lambda a, b: a not in b,
        ast.And: lambda a, b: a and b,
        ast.Or: lambda a, b: a or b,
        ast.Not: lambda a: not a,
    }

    def __init__(self, context: dict[str, Any]):
        self.context = context

    def evaluate_bool_op(self, node: ast.BoolOp) -> bool:
        """Evaluate boolean operations (and, or)."""
        if isinstance(node.op, ast.And):
            return all(self.evaluate_node(value) for value in node.values)
        elif isinstance(node.op, ast.Or):
            return any(self.evaluate_node(value) for value in node.values)
        else:
            raise ValueError(f"Unsupported boolean operator: {type(node.op)}")

    def evaluate_unary_op(self, node: ast.UnaryOp) -> Any:
        """Evaluate unary operations (not)."""
        if isinstance(node.op, ast.Not):
            return not self.evaluate_node(node.operand)
        else:
            raise ValueError(f"Unsupported unary operator: {type(node.op)}")

    def evaluate_compare(self, node: ast.Compare) -> bool:
        """Evaluate comparison operations."""
        left = self.evaluate_node(node.left)

        for i, (comparator, op) in enumerate(zip(node.comparators, node.ops)):
            right = self.evaluate_node(comparator)

            if type(op) not in self.OPERATORS:
                raise ValueError(f"Unsupported comparison operator: {type(op)}")

            if not self.OPERATORS[type(op)](left, right):
                return False
            left = right  # For chained comparisons

        return True

    def evaluate_name(self, node: ast.Name) -> Any:
        """Evaluate variable names."""
        if node.id in self.context:
            return self.context[node.id]
        else:
            raise ValueError(f"Unknown variable: {node.id}")

    def evaluate_attribute(self, node: ast.Attribute) -> Any:
        """Evaluate attribute access (e.g., user.role)."""
        obj = self.evaluate_node(node.value)
        if hasattr(obj, node.attr):
            return getattr(obj, node.attr)
        else:
            raise ValueError(f"Unknown attribute: {node.attr}")

    def evaluate_constant(self, node: ast.Constant) -> Any:
        """Evaluate constant values."""
        return node.value

    def evaluate_list(self, node: ast.List) -> list:
        """Evaluate list literals."""
        return [self.evaluate_node(item) for item in node.elts]

    def evaluate_legacy_str(self, node: ast.Str) -> str:
        """Evaluate string literals (Python < 3.8)."""
        return node.s

    def evaluate_legacy_num(self, node: ast.Num) -> int | float:
        """Evaluate numeric literals (Python < 3.8)."""
        return node.n

    def evaluate_node(self, node: ast.AST) -> Any:
        """Main node evaluation dispatcher."""
        evaluators = {
            ast.BoolOp: self.evaluate_bool_op,
            ast.UnaryOp: self.evaluate_unary_op,
            ast.Compare: self.evaluate_compare,
            ast.Name: self.evaluate_name,
            ast.Attribute: self.evaluate_attribute,
            ast.Constant: self.evaluate_constant,
            ast.List: self.evaluate_list,
            ast.Str: self.evaluate_legacy_str,  # Python < 3.8
            ast.Num: self.evaluate_legacy_num,  # Python < 3.8
        }

        node_type = type(node)
        if node_type in evaluators:
            return evaluators[node_type](node)
        else:
            raise ValueError(f"Unsupported AST node type: {node_type}")


class SafeExpressionEvaluator:
    """Safe expression evaluator using AST parsing."""

    def __init__(self, max_expression_length: int = 1000):
        self.max_expression_length = max_expression_length

    def evaluate(self, expression: str, context: dict[str, Any]) -> bool:
        """
        Safely evaluate a Python expression.

        Args:
            expression: The expression to evaluate
            context: Variables available during evaluation

        Returns:
            bool: Result of expression evaluation

        Raises:
            ValueError: If expression is invalid or uses unsupported features
            SyntaxError: If expression has syntax errors
        """
        if len(expression) > self.max_expression_length:
            raise ValueError(
                f"Expression too long: {len(expression)} > {self.max_expression_length}"
            )

        try:
            # Parse the expression into an AST
            tree = ast.parse(expression, mode="eval")

            # Create evaluator with context
            evaluator = ASTNodeEvaluator(context)

            # Evaluate the AST safely
            result = evaluator.evaluate_node(tree.body)

            # Ensure result is boolean for policy evaluation
            return bool(result)

        except (SyntaxError, ValueError, TypeError) as e:
            logger.warning(
                f"Expression evaluation failed: {expression}",
                error=str(e),
                context_keys=list(context.keys()),
            )
            return False

    def validate_expression(self, expression: str) -> bool:
        """
        Validate an expression without evaluating it.

        Args:
            expression: The expression to validate

        Returns:
            bool: True if expression is valid, False otherwise
        """
        try:
            tree = ast.parse(expression, mode="eval")
            # Create dummy evaluator to check node types
            evaluator = ASTNodeEvaluator({})
            self._validate_ast_node(tree.body, evaluator)
            return True
        except (SyntaxError, ValueError):
            return False

    def _validate_ast_node(self, node: ast.AST, evaluator: ASTNodeEvaluator) -> None:
        """Recursively validate AST nodes without evaluation."""
        if type(node) not in evaluator.OPERATORS and not hasattr(
            evaluator, f"evaluate_{type(node).__name__.lower()}"
        ):
            # Check if there's a method to handle this node type
            method_name = f"evaluate_{type(node).__name__.lower()}"
            if not hasattr(evaluator.__class__, method_name):
                raise ValueError(f"Unsupported AST node type: {type(node)}")

        # Recursively validate child nodes
        for child in ast.iter_child_nodes(node):
            self._validate_ast_node(child, evaluator)


# Global evaluator instance for convenience
default_evaluator = SafeExpressionEvaluator()


def safe_evaluate(expression: str, context: dict[str, Any]) -> bool:
    """
    Convenience function for safe expression evaluation.

    Args:
        expression: The expression to evaluate
        context: Variables available during evaluation

    Returns:
        bool: Result of expression evaluation
    """
    return default_evaluator.evaluate(expression, context)


def validate_expression(expression: str) -> bool:
    """
    Convenience function for expression validation.

    Args:
        expression: The expression to validate

    Returns:
        bool: True if expression is valid, False otherwise
    """
    return default_evaluator.validate_expression(expression)
