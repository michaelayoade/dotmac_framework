"""
Module validation framework for ensuring module quality and completeness.
"""

import ast
import importlib.util
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from dotmac_shared.api.exception_handlers import standard_exception_handler

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(Enum):
    """Validation categories."""

    STRUCTURE = "structure"
    IMPORTS = "imports"
    SYNTAX = "syntax"
    STANDARDS = "standards"
    DEPENDENCIES = "dependencies"
    SECURITY = "security"
    PERFORMANCE = "performance"


@dataclass
class ValidationIssue:
    """Individual validation issue."""

    level: ValidationLevel
    category: ValidationCategory
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    suggestion: Optional[str] = None
    rule_id: Optional[str] = None


@dataclass
class ValidationResult:
    """Results of module validation."""

    module_name: str
    module_path: str
    issues: List[ValidationIssue] = field(default_factory=list)
    missing_components: List[str] = field(default_factory=list)
    warnings_count: int = 0
    errors_count: int = 0
    critical_count: int = 0
    suggestions: List[str] = field(default_factory=list)
    is_valid: bool = field(init=False)
    score: float = field(init=False)  # 0-100

    def __post_init__(self):
        """Calculate counts and validity."""
        self.warnings_count = len(
            [i for i in self.issues if i.level == ValidationLevel.WARNING]
        )
        self.errors_count = len(
            [i for i in self.issues if i.level == ValidationLevel.ERROR]
        )
        self.critical_count = len(
            [i for i in self.issues if i.level == ValidationLevel.CRITICAL]
        )

        # Module is valid if no critical or error issues
        self.is_valid = self.critical_count == 0 and self.errors_count == 0

        # Calculate score (100 - penalty points)
        penalty = (
            (self.critical_count * 50)
            + (self.errors_count * 25)
            + (self.warnings_count * 5)
        )
        self.score = max(0, 100 - penalty)


class ModuleValidator:
    """Comprehensive module validator."""

    def __init__(self):
        self.required_components = {
            "__init__.py",
            "router.py",
            "service.py",
            "models.py",
            "schemas.py",
            "repository.py",
        }
        self.recommended_components = {"tasks.py", "dependencies.py", "exceptions.py"}
        self.all_components = self.required_components | self.recommended_components

        # Validation rules
        self.validation_rules = self._initialize_validation_rules()

    def _initialize_validation_rules(self) -> Dict[str, Any]:
        """Initialize validation rules."""
        return {
            "required_imports": {
                "router.py": ["fastapi", "APIRouter"],
                "service.py": ["typing", "sqlalchemy"],
                "models.py": ["sqlalchemy", "Column"],
                "schemas.py": ["pydantic", "BaseModel"],
                "repository.py": ["typing", "sqlalchemy", "Session"],
            },
            "forbidden_imports": [
                "os.system",
                "subprocess.call",
                "eval",
                "exec",
                "input",
            ],
            "naming_conventions": {
                "service_class_suffix": "Service",
                "repository_class_suffix": "Repository",
                "model_class_pattern": r"^[A-Z][a-zA-Z0-9]*$",
                "schema_class_patterns": ["Response", "Create", "Update", "Query"],
            },
            "required_methods": {
                "service": ["get_", "list_", "create_", "update_", "delete_"],
                "repository": ["get_by_id", "create", "update", "delete"],
            },
        }

    async def validate_module(
        self, module_path: Path, module_name: str
    ) -> ValidationResult:
        """Validate a complete module."""
        logger.info(f"🔍 Validating module: {module_name}")

        result = ValidationResult(module_name=module_name, module_path=str(module_path))

        try:
            # 1. Structural validation
            await self._validate_structure(module_path, result)

            # 2. Component validation
            await self._validate_components(module_path, result)

            # 3. Import validation
            await self._validate_imports(module_path, result)

            # 4. Standards compliance
            await self._validate_standards(module_path, result)

            # 5. Security validation
            await self._validate_security(module_path, result)

            # 6. Performance validation
            await self._validate_performance(module_path, result)

            # 7. Generate suggestions
            self._generate_suggestions(result)

        except Exception as e:
            logger.error(f"Error validating module {module_name}: {e}")
            result.issues.append(
                ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    category=ValidationCategory.STRUCTURE,
                    message=f"Validation failed: {str(e)}",
                    rule_id="VALIDATION_ERROR",
                )
            )

        logger.info(
            f"✅ Validation complete for {module_name}: Score {result.score:.1f}/100"
        )
        return result

    async def _validate_structure(self, module_path: Path, result: ValidationResult):
        """Validate module structure."""
        # Check for required components
        for component in self.required_components:
            component_path = module_path / component
            if not component_path.exists():
                result.missing_components.append(component)
                result.issues.append(
                    ValidationIssue(
                        level=ValidationLevel.ERROR,
                        category=ValidationCategory.STRUCTURE,
                        message=f"Missing required component: {component}",
                        suggestion=f"Create {component} file with appropriate template",
                        rule_id="MISSING_REQUIRED_COMPONENT",
                    )
                )

        # Check for recommended components
        for component in self.recommended_components:
            component_path = module_path / component
            if not component_path.exists():
                result.issues.append(
                    ValidationIssue(
                        level=ValidationLevel.WARNING,
                        category=ValidationCategory.STRUCTURE,
                        message=f"Missing recommended component: {component}",
                        suggestion=f"Consider adding {component} for better module organization",
                        rule_id="MISSING_RECOMMENDED_COMPONENT",
                    )
                )

        # Check for unexpected files
        allowed_extensions = {".py", ".md", ".txt", ".yml", ".yaml", ".json"}
        for file_path in module_path.rglob("*"):
            if file_path.is_file() and file_path.suffix not in allowed_extensions:
                result.issues.append(
                    ValidationIssue(
                        level=ValidationLevel.WARNING,
                        category=ValidationCategory.STRUCTURE,
                        message=f"Unexpected file type: {file_path.name}",
                        file_path=str(file_path.relative_to(module_path)),
                        suggestion="Consider if this file belongs in the module",
                        rule_id="UNEXPECTED_FILE_TYPE",
                    )
                )

    async def _validate_components(self, module_path: Path, result: ValidationResult):
        """Validate individual components."""
        for component in self.all_components:
            component_path = module_path / component
            if component_path.exists():
                await self._validate_component_file(component_path, component, result)

    async def _validate_component_file(
        self, file_path: Path, component: str, result: ValidationResult
    ):
        """Validate a specific component file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse AST for deeper validation
            try:
                tree = ast.parse(content, filename=str(file_path))
                await self._validate_ast(tree, file_path, component, result)
            except SyntaxError as e:
                result.issues.append(
                    ValidationIssue(
                        level=ValidationLevel.CRITICAL,
                        category=ValidationCategory.SYNTAX,
                        message=f"Syntax error in {component}: {e.msg}",
                        file_path=str(file_path),
                        line_number=e.lineno,
                        column=e.offset,
                        rule_id="SYNTAX_ERROR",
                    )
                )

            # Component-specific validations
            if component == "router.py":
                await self._validate_router(content, file_path, result)
            elif component == "service.py":
                await self._validate_service(content, file_path, result)
            elif component == "models.py":
                await self._validate_models(content, file_path, result)
            elif component == "schemas.py":
                await self._validate_schemas(content, file_path, result)

        except Exception as e:
            result.issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message=f"Could not read {component}: {str(e)}",
                    file_path=str(file_path),
                    rule_id="FILE_READ_ERROR",
                )
            )

    async def _validate_ast(
        self, tree: ast.AST, file_path: Path, component: str, result: ValidationResult
    ):
        """Validate using AST analysis."""

        class ValidationVisitor(ast.NodeVisitor):
            def __init__(
                self, validator_instance, result_instance, file_path, component
            ):
                self.validator = validator_instance
                self.result = result_instance
                self.file_path = file_path
                self.component = component
                self.classes_found = []
                self.functions_found = []
                self.imports_found = []

            def visit_ClassDef(self, node):
                self.classes_found.append(node.name)

                # Check naming conventions
                if self.component == "service.py":
                    if not node.name.endswith("Service"):
                        self.result.issues.append(
                            ValidationIssue(
                                level=ValidationLevel.WARNING,
                                category=ValidationCategory.STANDARDS,
                                message=f"Service class '{node.name}' should end with 'Service'",
                                file_path=str(self.file_path),
                                line_number=node.lineno,
                                rule_id="NAMING_CONVENTION_SERVICE",
                            )
                        )

                elif self.component == "repository.py":
                    if not node.name.endswith("Repository"):
                        self.result.issues.append(
                            ValidationIssue(
                                level=ValidationLevel.WARNING,
                                category=ValidationCategory.STANDARDS,
                                message=f"Repository class '{node.name}' should end with 'Repository'",
                                file_path=str(self.file_path),
                                line_number=node.lineno,
                                rule_id="NAMING_CONVENTION_REPOSITORY",
                            )
                        )

                self.generic_visit(node)

            def visit_FunctionDef(self, node):
                self.functions_found.append(node.name)
                self.generic_visit(node)

            def visit_Import(self, node):
                for alias in node.names:
                    self.imports_found.append(alias.name)
                self.generic_visit(node)

            def visit_ImportFrom(self, node):
                if node.module:
                    for alias in node.names:
                        import_name = f"{node.module}.{alias.name}"
                        self.imports_found.append(import_name)
                self.generic_visit(node)

        visitor = ValidationVisitor(self, result, file_path, component)
        visitor.visit(tree)

        # Validate required methods exist
        if component == "service.py":
            required_methods = self.validation_rules["required_methods"]["service"]
            for req_method in required_methods:
                if not any(
                    method.startswith(req_method) for method in visitor.functions_found
                ):
                    result.issues.append(
                        ValidationIssue(
                            level=ValidationLevel.WARNING,
                            category=ValidationCategory.STANDARDS,
                            message=f"Service missing method starting with '{req_method}'",
                            file_path=str(file_path),
                            suggestion=f"Implement methods like {req_method}item_name",
                            rule_id="MISSING_SERVICE_METHOD",
                        )
                    )

    async def _validate_imports(self, module_path: Path, result: ValidationResult):
        """Validate module imports."""
        for component, required in self.validation_rules["required_imports"].items():
            component_path = module_path / component
            if component_path.exists():
                try:
                    with open(component_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    for req_import in required:
                        if req_import not in content:
                            result.issues.append(
                                ValidationIssue(
                                    level=ValidationLevel.WARNING,
                                    category=ValidationCategory.IMPORTS,
                                    message=f"{component} missing recommended import: {req_import}",
                                    file_path=component,
                                    suggestion=f"Add 'from ... import {req_import}' or 'import {req_import}'",
                                    rule_id="MISSING_RECOMMENDED_IMPORT",
                                )
                            )

                    # Check for forbidden imports
                    for forbidden in self.validation_rules["forbidden_imports"]:
                        if forbidden in content:
                            result.issues.append(
                                ValidationIssue(
                                    level=ValidationLevel.CRITICAL,
                                    category=ValidationCategory.SECURITY,
                                    message=f"{component} uses forbidden import: {forbidden}",
                                    file_path=component,
                                    suggestion="Remove or replace with secure alternative",
                                    rule_id="FORBIDDEN_IMPORT",
                                )
                            )

                except Exception as e:
                    logger.warning(f"Could not validate imports in {component}: {e}")

    async def _validate_router(
        self, content: str, file_path: Path, result: ValidationResult
    ):
        """Validate router.py specific requirements."""
        # Check for APIRouter instance
        if "APIRouter" not in content:
            result.issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message="Router file missing APIRouter import",
                    file_path=str(file_path),
                    rule_id="MISSING_API_ROUTER",
                )
            )

        if "router = APIRouter" not in content:
            result.issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message="Router file missing router instance creation",
                    file_path=str(file_path),
                    rule_id="MISSING_ROUTER_INSTANCE",
                )
            )

        # Check for standard CRUD endpoints
        crud_methods = ["@router.get", "@router.post", "@router.put", "@router.delete"]
        missing_methods = []
        for method in crud_methods:
            if method not in content:
                missing_methods.append(method.replace("@router.", ""))

        if missing_methods:
            result.issues.append(
                ValidationIssue(
                    level=ValidationLevel.WARNING,
                    category=ValidationCategory.STANDARDS,
                    message=f"Router missing standard HTTP methods: {', '.join(missing_methods)}",
                    file_path=str(file_path),
                    suggestion="Consider implementing full CRUD operations",
                    rule_id="INCOMPLETE_CRUD_OPERATIONS",
                )
            )

    async def _validate_service(
        self, content: str, file_path: Path, result: ValidationResult
    ):
        """Validate service.py specific requirements."""
        # Check for service class
        if "class " not in content or "Service" not in content:
            result.issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message="Service file missing service class",
                    file_path=str(file_path),
                    rule_id="MISSING_SERVICE_CLASS",
                )
            )

        # Check for database session handling
        if "Session" not in content:
            result.issues.append(
                ValidationIssue(
                    level=ValidationLevel.WARNING,
                    category=ValidationCategory.STANDARDS,
                    message="Service should handle database sessions",
                    file_path=str(file_path),
                    rule_id="MISSING_SESSION_HANDLING",
                )
            )

    async def _validate_models(
        self, content: str, file_path: Path, result: ValidationResult
    ):
        """Validate models.py specific requirements."""
        # Check for SQLAlchemy imports
        if "Column" not in content or "Integer" not in content:
            result.issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message="Models file missing SQLAlchemy column imports",
                    file_path=str(file_path),
                    rule_id="MISSING_SQLALCHEMY_IMPORTS",
                )
            )

        # Check for __tablename__
        if "__tablename__" not in content:
            result.issues.append(
                ValidationIssue(
                    level=ValidationLevel.WARNING,
                    category=ValidationCategory.STANDARDS,
                    message="Models should define __tablename__",
                    file_path=str(file_path),
                    rule_id="MISSING_TABLENAME",
                )
            )

    async def _validate_schemas(
        self, content: str, file_path: Path, result: ValidationResult
    ):
        """Validate schemas.py specific requirements."""
        # Check for Pydantic imports
        if "BaseModel" not in content:
            result.issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message="Schemas file missing Pydantic BaseModel import",
                    file_path=str(file_path),
                    rule_id="MISSING_BASEMODEL_IMPORT",
                )
            )

        # Check for standard schema classes
        schema_types = ["Create", "Update", "Response"]
        missing_schemas = []
        for schema_type in schema_types:
            if f"{schema_type}" not in content:
                missing_schemas.append(schema_type)

        if missing_schemas:
            result.issues.append(
                ValidationIssue(
                    level=ValidationLevel.WARNING,
                    category=ValidationCategory.STANDARDS,
                    message=f"Missing standard schema types: {', '.join(missing_schemas)}",
                    file_path=str(file_path),
                    suggestion="Add Create, Update, and Response schema classes",
                    rule_id="MISSING_SCHEMA_TYPES",
                )
            )

    async def _validate_standards(self, module_path: Path, result: ValidationResult):
        """Validate coding standards compliance."""
        # Check for docstrings
        for component in ["router.py", "service.py", "models.py"]:
            component_path = module_path / component
            if component_path.exists():
                try:
                    with open(component_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    if '"""' not in content and "'''" not in content:
                        result.issues.append(
                            ValidationIssue(
                                level=ValidationLevel.INFO,
                                category=ValidationCategory.STANDARDS,
                                message=f"{component} missing docstrings",
                                file_path=component,
                                suggestion="Add module and function docstrings",
                                rule_id="MISSING_DOCSTRINGS",
                            )
                        )

                except Exception:
                    pass

    async def _validate_security(self, module_path: Path, result: ValidationResult):
        """Validate security best practices."""
        security_patterns = [
            (r'password\s*=\s*["\'][^"\']*["\']', "Hardcoded password detected"),
            (r'secret\s*=\s*["\'][^"\']*["\']', "Hardcoded secret detected"),
            (r'api[_-]?key\s*=\s*["\'][^"\']*["\']', "Hardcoded API key detected"),
            (r"eval\s*\(", "Use of eval() function detected"),
            (r"exec\s*\(", "Use of exec() function detected"),
        ]

        for component_path in module_path.glob("*.py"):
            try:
                with open(component_path, "r", encoding="utf-8") as f:
                    content = f.read()

                for pattern, message in security_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[: match.start()].count("\n") + 1
                        result.issues.append(
                            ValidationIssue(
                                level=ValidationLevel.CRITICAL,
                                category=ValidationCategory.SECURITY,
                                message=message,
                                file_path=str(component_path.name),
                                line_number=line_num,
                                rule_id="SECURITY_ISSUE",
                            )
                        )

            except Exception:
                pass

    async def _validate_performance(self, module_path: Path, result: ValidationResult):
        """Validate performance best practices."""
        performance_patterns = [
            (r"\.all\(\)", "Consider using pagination instead of .all()"),
            (r"for\s+\w+\s+in\s+.*\.query\(", "Potential N+1 query in loop"),
        ]

        for component_path in module_path.glob("*.py"):
            try:
                with open(component_path, "r", encoding="utf-8") as f:
                    content = f.read()

                for pattern, message in performance_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        line_num = content[: match.start()].count("\n") + 1
                        result.issues.append(
                            ValidationIssue(
                                level=ValidationLevel.WARNING,
                                category=ValidationCategory.PERFORMANCE,
                                message=message,
                                file_path=str(component_path.name),
                                line_number=line_num,
                                rule_id="PERFORMANCE_ISSUE",
                            )
                        )

            except Exception:
                pass

    def _generate_suggestions(self, result: ValidationResult):
        """Generate module improvement suggestions."""
        if result.missing_components:
            result.suggestions.append(
                f"Complete missing components: {', '.join(result.missing_components)}"
            )

        if result.critical_count > 0:
            result.suggestions.append("Address all critical issues immediately")

        if result.errors_count > 0:
            result.suggestions.append("Fix all error-level issues before deployment")

        if result.warnings_count > 5:
            result.suggestions.append(
                "Consider addressing warning-level issues for better code quality"
            )

        if result.score < 80:
            result.suggestions.append(
                "Module needs significant improvements before production use"
            )
        elif result.score < 90:
            result.suggestions.append("Module is good but has room for improvement")
        else:
            result.suggestions.append("Module meets high quality standards")

    async def validate_multiple_modules(
        self, modules_info: Dict[str, Any]
    ) -> Dict[str, ValidationResult]:
        """Validate multiple modules and return results."""
        results = {}

        for module_name, module_info in modules_info.items():
            try:
                module_path = (
                    Path(module_info["path"])
                    if isinstance(module_info, dict)
                    else Path(str(module_info))
                )
                result = await self.validate_module(module_path, module_name)
                results[module_name] = result
            except Exception as e:
                logger.error(f"Failed to validate module {module_name}: {e}")
                results[module_name] = ValidationResult(
                    module_name=module_name,
                    module_path=str(module_path),
                    is_valid=False,
                    score=0,
                )

        return results

    def generate_validation_report(self, results: Dict[str, ValidationResult]) -> str:
        """Generate a comprehensive validation report."""
        report = []
        report.append("# Module Validation Report")
        report.append("=" * 50)
        report.append("")

        # Summary statistics
        total_modules = len(results)
        valid_modules = len([r for r in results.values() if r.is_valid])
        avg_score = (
            sum(r.score for r in results.values()) / total_modules
            if total_modules > 0
            else 0
        )

        report.append("## Summary")
        report.append(f"- Total modules validated: {total_modules}")
        report.append(
            f"- Valid modules: {valid_modules} ({valid_modules/total_modules*100:.1f}%)"
        )
        report.append(f"- Average score: {avg_score:.1f}/100")
        report.append("")

        # Top issues
        all_issues = []
        for result in results.values():
            all_issues.extend(result.issues)

        issue_counts = {}
        for issue in all_issues:
            key = f"{issue.category.value}-{issue.level.value}"
            issue_counts[key] = issue_counts.get(key, 0) + 1

        report.append("## Issue Summary")
        for issue_type, count in sorted(
            issue_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]:
            report.append(f"- {issue_type}: {count} occurrences")
        report.append("")

        # Module details
        report.append("## Module Details")
        for module_name, result in sorted(
            results.items(), key=lambda x: x[1].score, reverse=True
        ):
            report.append(f"### {module_name} - Score: {result.score:.1f}/100")
            report.append(
                f"**Status:** {'✅ Valid' if result.is_valid else '❌ Invalid'}"
            )

            if result.issues:
                report.append("**Issues:**")
                for issue in result.issues[:5]:  # Top 5 issues
                    icon = {
                        "critical": "🚨",
                        "error": "❌",
                        "warning": "⚠️",
                        "info": "ℹ️",
                    }[issue.level.value]
                    report.append(f"  {icon} {issue.message}")
                    if issue.suggestion:
                        report.append(f"     💡 {issue.suggestion}")

                if len(result.issues) > 5:
                    report.append(f"  ... and {len(result.issues) - 5} more issues")

            if result.suggestions:
                report.append("**Suggestions:**")
                for suggestion in result.suggestions[:3]:
                    report.append(f"  - {suggestion}")

            report.append("")

        return "\n".join(report)
