"""
Security validation utilities for API endpoints.
Ensures all endpoints have proper authentication and input validation.
"""

import ast
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SecurityValidationResult:
    """Result of security validation for an endpoint."""

    endpoint_path: str
    method: str
    function_name: str
    file_path: str
    has_authentication: bool
    has_input_validation: bool
    has_authorization: bool
    security_score: float
    issues: list[str]


@dataclass
class SecurityValidationReport:
    """Complete security validation report."""

    total_endpoints: int
    secure_endpoints: int
    insecure_endpoints: int
    endpoints: list[SecurityValidationResult]
    security_percentage: float
    critical_issues: list[str]
    recommendations: list[str]


class EndpointSecurityValidator:
    """Validates security implementation of API endpoints."""

    def __init__(self):
        self.auth_patterns = [
            "authenticate_user",
            "get_current_user",
            "Depends",
            "HTTPBearer",
            "OAuth2PasswordBearer",
            "Security",
            "require_permissions",
            "require_roles",
        ]

        self.validation_patterns = [
            "BaseModel",
            "Field",
            "field_validator",
            "model_validator",
            "ValidationError",
            "validator",
            "Query",
            "Path",
            "Body",
        ]

        self.authorization_patterns = [
            "require_permissions",
            "require_roles",
            "check_permission",
            "authorize",
            "has_permission",
            "can_access",
        ]

    def validate_file_security(self, file_path: str) -> list[SecurityValidationResult]:
        """Validate security of all endpoints in a file."""
        results = []

        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source, filename=file_path)

            # Find all endpoint functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    endpoint_info = self._analyze_endpoint_security(node, source, file_path)
                    if endpoint_info:
                        results.append(endpoint_info)

        except Exception as e:
            logger.warning(f"Could not validate security for {file_path}: {e}")

        return results

    def _analyze_endpoint_security(
        self, func_node: ast.FunctionDef, source: str, file_path: str
    ) -> Optional[SecurityValidationResult]:
        """Analyze security of a single endpoint function."""
        # Check if this is an API endpoint
        endpoint_info = self._extract_endpoint_info(func_node)
        if not endpoint_info:
            return None

        method, path = endpoint_info

        # Analyze security aspects
        has_auth = self._has_authentication(func_node, source)
        has_validation = self._has_input_validation(func_node, source)
        has_authorization = self._has_authorization(func_node, source)

        # Calculate security score
        score = self._calculate_security_score(has_auth, has_validation, has_authorization)

        # Identify issues
        issues = self._identify_security_issues(has_auth, has_validation, has_authorization, method)

        return SecurityValidationResult(
            endpoint_path=path,
            method=method,
            function_name=func_node.name,
            file_path=file_path,
            has_authentication=has_auth,
            has_input_validation=has_validation,
            has_authorization=has_authorization,
            security_score=score,
            issues=issues,
        )

    def _extract_endpoint_info(self, func_node: ast.FunctionDef) -> Optional[tuple]:
        """Extract method and path from endpoint decorators."""
        for decorator in func_node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                # @router.get, @router.post, etc.
                method = decorator.attr.upper()
                if method in [
                    "GET",
                    "POST",
                    "PUT",
                    "DELETE",
                    "PATCH",
                    "HEAD",
                    "OPTIONS",
                ]:
                    return method, "/"
            elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                # @router.get("/path")
                method = decorator.func.attr.upper()
                if method in [
                    "GET",
                    "POST",
                    "PUT",
                    "DELETE",
                    "PATCH",
                    "HEAD",
                    "OPTIONS",
                ]:
                    path = "/"
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        path = decorator.args[0].value
                    return method, path

        return None

    def _has_authentication(self, func_node: ast.FunctionDef, source: str) -> bool:
        """Check if endpoint has authentication."""
        # Check function decorators
        for decorator in func_node.decorator_list:
            if self._contains_auth_pattern(ast.dump(decorator)):
                return True

        # Check function parameters for Depends(authenticate_user)
        for arg in func_node.args.args:
            if hasattr(arg, "annotation") and arg.annotation:
                if self._contains_auth_pattern(ast.dump(arg.annotation)):
                    return True

        # Check default values for Depends()
        for default in func_node.args.defaults:
            if self._contains_auth_pattern(ast.dump(default)):
                return True

        return False

    def _has_input_validation(self, func_node: ast.FunctionDef, source: str) -> bool:
        """Check if endpoint has input validation."""
        # Check for Pydantic models in parameters
        for arg in func_node.args.args:
            if hasattr(arg, "annotation") and arg.annotation:
                annotation_str = ast.dump(arg.annotation)

                # Check for Pydantic patterns
                if any(pattern in annotation_str for pattern in self.validation_patterns):
                    return True

                # Check for common request model naming patterns
                if isinstance(arg.annotation, ast.Name):
                    name = arg.annotation.id
                    if any(suffix in name for suffix in ["Request", "Create", "Update", "Model", "Schema"]):
                        return True

        # Check for Query, Path, Body parameters
        for default in func_node.args.defaults:
            default_str = ast.dump(default)
            if any(pattern in default_str for pattern in ["Query", "Path", "Body"]):
                return True

        return False

    def _has_authorization(self, func_node: ast.FunctionDef, source: str) -> bool:
        """Check if endpoint has authorization beyond basic authentication."""
        # Check for authorization decorators
        for decorator in func_node.decorator_list:
            if any(pattern in ast.dump(decorator) for pattern in self.authorization_patterns):
                return True

        # Check function parameters for authorization dependencies
        for arg in func_node.args.args:
            if hasattr(arg, "annotation") and arg.annotation:
                if any(pattern in ast.dump(arg.annotation) for pattern in self.authorization_patterns):
                    return True

        return False

    def _contains_auth_pattern(self, code_str: str) -> bool:
        """Check if code string contains authentication patterns."""
        return any(pattern in code_str for pattern in self.auth_patterns)

    def _calculate_security_score(self, has_auth: bool, has_validation: bool, has_authorization: bool) -> float:
        """Calculate security score (0-100)."""
        score = 0.0

        if has_auth:
            score += 50.0  # Authentication is most critical

        if has_validation:
            score += 30.0  # Input validation is important

        if has_authorization:
            score += 20.0  # Authorization adds extra security

        return score

    def _identify_security_issues(
        self, has_auth: bool, has_validation: bool, has_authorization: bool, method: str
    ) -> list[str]:
        """Identify specific security issues."""
        issues = []

        if not has_auth:
            issues.append("Missing authentication - endpoint is publicly accessible")

        if not has_validation and method in ["POST", "PUT", "PATCH"]:
            issues.append("Missing input validation - vulnerable to malicious input")

        if not has_authorization and has_auth:
            issues.append("Missing authorization - all authenticated users can access")

        if method == "DELETE" and not has_authorization:
            issues.append("DELETE endpoint without explicit authorization is risky")

        return issues

    def validate_routers_security(self, router_paths: list[str]) -> SecurityValidationReport:
        """Validate security of multiple router files."""
        all_results = []

        for router_path in router_paths:
            if Path(router_path).exists():
                file_results = self.validate_file_security(router_path)
                all_results.extend(file_results)

        # Calculate overall statistics
        total_endpoints = len(all_results)
        secure_endpoints = sum(1 for r in all_results if r.security_score >= 80.0)
        insecure_endpoints = total_endpoints - secure_endpoints
        security_percentage = (secure_endpoints / total_endpoints * 100) if total_endpoints > 0 else 0

        # Identify critical issues
        critical_issues = []
        no_auth_count = sum(1 for r in all_results if not r.has_authentication)
        if no_auth_count > 0:
            critical_issues.append(f"{no_auth_count} endpoints lack authentication")

        no_validation_count = sum(1 for r in all_results if not r.has_input_validation)
        if no_validation_count > 0:
            critical_issues.append(f"{no_validation_count} endpoints lack input validation")

        # Generate recommendations
        recommendations = self._generate_recommendations(all_results)

        return SecurityValidationReport(
            total_endpoints=total_endpoints,
            secure_endpoints=secure_endpoints,
            insecure_endpoints=insecure_endpoints,
            endpoints=all_results,
            security_percentage=security_percentage,
            critical_issues=critical_issues,
            recommendations=recommendations,
        )

    def _generate_recommendations(self, results: list[SecurityValidationResult]) -> list[str]:
        """Generate security recommendations."""
        recommendations = []

        # Authentication recommendations
        no_auth = [r for r in results if not r.has_authentication]
        if no_auth:
            recommendations.append(f"Add authentication to {len(no_auth)} endpoints using Depends(authenticate_user)")
        # Validation recommendations
        no_validation = [r for r in results if not r.has_input_validation]
        if no_validation:
            recommendations.append(f"Add input validation to {len(no_validation)} endpoints using Pydantic models")
        # Authorization recommendations
        no_authz = [r for r in results if r.has_authentication and not r.has_authorization]
        if no_authz:
            recommendations.append(f"Add role-based authorization to {len(no_authz)} sensitive endpoints")
        # Specific endpoint recommendations
        delete_endpoints = [r for r in results if r.method == "DELETE" and r.security_score < 100]
        if delete_endpoints:
            recommendations.append(f"Review {len(delete_endpoints)} DELETE endpoints for proper authorization")
        return recommendations

    def print_security_report(self, report: SecurityValidationReport):
        """Print a formatted security report."""

        if report.critical_issues:
            for issue in report.critical_issues:
                logger.critical(f"Critical security issue: {issue}")

        if report.recommendations:
            for rec in report.recommendations:
                logger.info(f"Security recommendation: {rec}")

        # Show worst endpoints
        worst_endpoints = sorted(report.endpoints, key=lambda x: x.security_score)[:5]
        if worst_endpoints:
            for endpoint in worst_endpoints:
                logger.warning(f"Low security score endpoint: {endpoint.path} (score: {endpoint.security_score})")


def validate_endpoint_security(
    router_paths: Optional[list[str]] = None,
) -> SecurityValidationReport:
    """Main entry point for endpoint security validation."""
    if router_paths is None:
        # Default router paths
        base_path = Path("/home/dotmac_framework/src/dotmac_isp")
        router_paths = [
            str(base_path / "modules" / "billing" / "router.py"),
            str(base_path / "modules" / "identity" / "router.py"),
            str(base_path / "modules" / "support" / "router.py"),
            str(base_path / "api" / "optimized_routers.py"),
        ]

    validator = EndpointSecurityValidator()
    report = validator.validate_routers_security(router_paths)
    validator.print_security_report(report)

    return report


if __name__ == "__main__":
    # Run security validation
    report = validate_endpoint_security()

    # Exit with appropriate code
    if report.security_percentage < 80.0:
        exit(1)
    else:
        exit(0)
