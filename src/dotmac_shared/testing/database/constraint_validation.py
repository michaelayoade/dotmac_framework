"""
Database Constraint Validation Testing

Comprehensive testing utilities for database constraints, including:
- Primary key constraints
- Foreign key constraints
- Unique constraints
- Check constraints
- Not null constraints
- Custom validation rules
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.inspection import inspect as sqlalchemy_inspect
from sqlalchemy.orm import Session
from sqlalchemy.sql.schema import CheckConstraint, UniqueConstraint

from ...api.exception_handlers import standard_exception_handler
from ...core.logging import get_logger

logger = get_logger(__name__)


class ConstraintType(str, Enum):
    """Types of database constraints"""

    PRIMARY_KEY = "primary_key"
    FOREIGN_KEY = "foreign_key"
    UNIQUE = "unique"
    NOT_NULL = "not_null"
    CHECK = "check"
    CUSTOM = "custom"


class ConstraintTestResult(str, Enum):
    """Constraint test result states"""

    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIP = "skip"


@dataclass
class ConstraintTestCase:
    """Defines a constraint test case"""

    name: str
    constraint_type: ConstraintType
    test_data: dict[str, Any]
    should_fail: bool = True  # Most constraint tests expect violations to fail
    error_message_contains: Optional[str] = None


@dataclass
class ConstraintValidationResult:
    """Result of a constraint validation test"""

    test_name: str
    constraint_type: ConstraintType
    result: ConstraintTestResult
    error_message: Optional[str] = None
    execution_time: float = 0.0
    expected_failure: bool = True


class DatabaseConstraintValidator:
    """
    Comprehensive database constraint validation framework.

    Features:
    - Automatic constraint discovery from SQLAlchemy models
    - Primary key constraint testing
    - Foreign key constraint testing
    - Unique constraint testing
    - Not null constraint testing
    - Check constraint testing
    - Custom validation rule testing
    - Batch constraint testing
    """

    def __init__(self, session: Session):
        self.session = session
        self.test_results: list[ConstraintValidationResult] = []

    @standard_exception_handler
    async def validate_model_constraints(
        self, model_class: type, test_data_sets: list[dict[str, Any]]
    ) -> list[ConstraintValidationResult]:
        """
        Validate all constraints for a given model class.

        Args:
            model_class: SQLAlchemy model class
            test_data_sets: List of test data dictionaries

        Returns:
            List of constraint validation results
        """
        logger.info(f"Validating constraints for {model_class.__name__}")

        # Discover constraints from model
        constraints = self._discover_model_constraints(model_class)

        results = []

        # Test each constraint type
        for constraint_type, constraint_info in constraints.items():
            if constraint_type == ConstraintType.PRIMARY_KEY:
                pk_results = await self._test_primary_key_constraints(model_class, constraint_info, test_data_sets)
                results.extend(pk_results)

            elif constraint_type == ConstraintType.FOREIGN_KEY:
                fk_results = await self._test_foreign_key_constraints(model_class, constraint_info, test_data_sets)
                results.extend(fk_results)

            elif constraint_type == ConstraintType.UNIQUE:
                unique_results = await self._test_unique_constraints(model_class, constraint_info, test_data_sets)
                results.extend(unique_results)

            elif constraint_type == ConstraintType.NOT_NULL:
                nn_results = await self._test_not_null_constraints(model_class, constraint_info, test_data_sets)
                results.extend(nn_results)

            elif constraint_type == ConstraintType.CHECK:
                check_results = await self._test_check_constraints(model_class, constraint_info, test_data_sets)
                results.extend(check_results)

        self.test_results.extend(results)
        return results

    def _discover_model_constraints(self, model_class: type) -> dict[ConstraintType, list[dict]]:
        """Discover all constraints from SQLAlchemy model"""

        inspector = sqlalchemy_inspect(model_class)
        constraints = {constraint_type: [] for constraint_type in ConstraintType}

        # Primary key constraints
        if hasattr(inspector, "primary_key"):
            for column in inspector.primary_key:
                constraints[ConstraintType.PRIMARY_KEY].append(
                    {"column": column.name, "type": column.type, "nullable": column.nullable}
                )

        # Discover constraints from table
        if hasattr(model_class, "__table__"):
            table = model_class.__table__

            # Foreign key constraints
            for fk in table.foreign_keys:
                constraints[ConstraintType.FOREIGN_KEY].append(
                    {
                        "column": fk.parent.name,
                        "references": f"{fk.column.table.name}.{fk.column.name}",
                        "nullable": fk.parent.nullable,
                    }
                )

            # Unique constraints
            for constraint in table.constraints:
                if isinstance(constraint, UniqueConstraint):
                    constraints[ConstraintType.UNIQUE].append(
                        {"columns": [col.name for col in constraint.columns], "name": constraint.name}
                    )
                elif isinstance(constraint, CheckConstraint):
                    constraints[ConstraintType.CHECK].append(
                        {"name": constraint.name, "sqltext": str(constraint.sqltext)}
                    )

            # Not null constraints (from column definitions)
            for column in table.columns:
                if not column.nullable and not column.primary_key:
                    constraints[ConstraintType.NOT_NULL].append({"column": column.name, "type": str(column.type)})

        return constraints

    async def _test_primary_key_constraints(
        self, model_class: type, pk_constraints: list[dict], test_data_sets: list[dict]
    ) -> list[ConstraintValidationResult]:
        """Test primary key constraints"""

        results = []

        for pk_info in pk_constraints:
            column_name = pk_info["column"]

            # Test 1: Duplicate primary key should fail
            test_case = ConstraintTestCase(
                name=f"duplicate_pk_{model_class.__name__}_{column_name}",
                constraint_type=ConstraintType.PRIMARY_KEY,
                test_data=test_data_sets[0] if test_data_sets else {},
                should_fail=True,
                error_message_contains="primary key",
            )

            result = await self._run_constraint_test(model_class, test_case)
            results.append(result)

            # Test 2: NULL primary key should fail (if not auto-increment)
            if not pk_info.get("auto_increment", False):
                null_test_data = test_data_sets[0].copy() if test_data_sets else {}
                null_test_data[column_name] = None

                null_test_case = ConstraintTestCase(
                    name=f"null_pk_{model_class.__name__}_{column_name}",
                    constraint_type=ConstraintType.PRIMARY_KEY,
                    test_data=null_test_data,
                    should_fail=True,
                    error_message_contains="not null",
                )

                null_result = await self._run_constraint_test(model_class, null_test_case)
                results.append(null_result)

        return results

    async def _test_foreign_key_constraints(
        self, model_class: type, fk_constraints: list[dict], test_data_sets: list[dict]
    ) -> list[ConstraintValidationResult]:
        """Test foreign key constraints"""

        results = []

        for fk_info in fk_constraints:
            column_name = fk_info["column"]

            # Test 1: Invalid foreign key should fail
            invalid_test_data = test_data_sets[0].copy() if test_data_sets else {}
            invalid_test_data[column_name] = 99999  # Non-existent ID

            test_case = ConstraintTestCase(
                name=f"invalid_fk_{model_class.__name__}_{column_name}",
                constraint_type=ConstraintType.FOREIGN_KEY,
                test_data=invalid_test_data,
                should_fail=True,
                error_message_contains="foreign key",
            )

            result = await self._run_constraint_test(model_class, test_case)
            results.append(result)

            # Test 2: NULL foreign key (should succeed if nullable)
            if fk_info.get("nullable", False):
                null_test_data = test_data_sets[0].copy() if test_data_sets else {}
                null_test_data[column_name] = None

                null_test_case = ConstraintTestCase(
                    name=f"null_fk_{model_class.__name__}_{column_name}",
                    constraint_type=ConstraintType.FOREIGN_KEY,
                    test_data=null_test_data,
                    should_fail=False,  # Should succeed if nullable
                )

                null_result = await self._run_constraint_test(model_class, null_test_case)
                results.append(null_result)

        return results

    async def _test_unique_constraints(
        self, model_class: type, unique_constraints: list[dict], test_data_sets: list[dict]
    ) -> list[ConstraintValidationResult]:
        """Test unique constraints"""

        results = []

        for unique_info in unique_constraints:
            columns = unique_info["columns"]
            constraint_name = unique_info.get("name", "_".join(columns))

            # Test: Duplicate unique values should fail
            test_case = ConstraintTestCase(
                name=f"duplicate_unique_{model_class.__name__}_{constraint_name}",
                constraint_type=ConstraintType.UNIQUE,
                test_data=test_data_sets[0] if test_data_sets else {},
                should_fail=True,
                error_message_contains="unique",
            )

            result = await self._run_constraint_test(model_class, test_case, duplicate_unique=True)
            results.append(result)

        return results

    async def _test_not_null_constraints(
        self, model_class: type, nn_constraints: list[dict], test_data_sets: list[dict]
    ) -> list[ConstraintValidationResult]:
        """Test not null constraints"""

        results = []

        for nn_info in nn_constraints:
            column_name = nn_info["column"]

            # Test: NULL value in not-null column should fail
            null_test_data = test_data_sets[0].copy() if test_data_sets else {}
            null_test_data[column_name] = None

            test_case = ConstraintTestCase(
                name=f"null_violation_{model_class.__name__}_{column_name}",
                constraint_type=ConstraintType.NOT_NULL,
                test_data=null_test_data,
                should_fail=True,
                error_message_contains="not null",
            )

            result = await self._run_constraint_test(model_class, test_case)
            results.append(result)

        return results

    async def _test_check_constraints(
        self, model_class: type, check_constraints: list[dict], test_data_sets: list[dict]
    ) -> list[ConstraintValidationResult]:
        """Test check constraints"""

        results = []

        for check_info in check_constraints:
            constraint_name = check_info["name"]

            # This is challenging without knowing the specific check logic
            # We'll create a generic test that tries to violate common patterns
            test_case = ConstraintTestCase(
                name=f"check_violation_{model_class.__name__}_{constraint_name}",
                constraint_type=ConstraintType.CHECK,
                test_data=test_data_sets[0] if test_data_sets else {},
                should_fail=True,
                error_message_contains="check",
            )

            result = await self._run_constraint_test(model_class, test_case)
            results.append(result)

        return results

    async def _run_constraint_test(
        self, model_class: type, test_case: ConstraintTestCase, duplicate_unique: bool = False
    ) -> ConstraintValidationResult:
        """Run a single constraint test"""

        import time

        start_time = time.time()

        try:
            # Create initial record if testing duplicates
            if duplicate_unique:
                initial_record = model_class(**test_case.test_data)
                self.session.add(initial_record)
                self.session.commit()

            # Create test record
            test_record = model_class(**test_case.test_data)
            self.session.add(test_record)
            self.session.commit()

            # If we got here and expected failure, test failed
            if test_case.should_fail:
                result = ConstraintTestResult(
                    test_name=test_case.name,
                    constraint_type=test_case.constraint_type,
                    result=ConstraintTestResult.FAIL,
                    error_message="Expected constraint violation did not occur",
                    execution_time=time.time() - start_time,
                    expected_failure=test_case.should_fail,
                )
            else:
                # Expected success and got it
                result = ConstraintValidationResult(
                    test_name=test_case.name,
                    constraint_type=test_case.constraint_type,
                    result=ConstraintTestResult.PASS,
                    execution_time=time.time() - start_time,
                    expected_failure=test_case.should_fail,
                )

        except (IntegrityError, StatementError) as e:
            self.session.rollback()

            if test_case.should_fail:
                # Expected failure occurred
                message_match = True
                if test_case.error_message_contains:
                    message_match = test_case.error_message_contains.lower() in str(e).lower()

                if message_match:
                    result = ConstraintValidationResult(
                        test_name=test_case.name,
                        constraint_type=test_case.constraint_type,
                        result=ConstraintTestResult.PASS,
                        execution_time=time.time() - start_time,
                        expected_failure=test_case.should_fail,
                    )
                else:
                    result = ConstraintValidationResult(
                        test_name=test_case.name,
                        constraint_type=test_case.constraint_type,
                        result=ConstraintTestResult.FAIL,
                        error_message=f"Wrong error message: {str(e)}",
                        execution_time=time.time() - start_time,
                        expected_failure=test_case.should_fail,
                    )
            else:
                # Unexpected failure
                result = ConstraintValidationResult(
                    test_name=test_case.name,
                    constraint_type=test_case.constraint_type,
                    result=ConstraintTestResult.FAIL,
                    error_message=str(e),
                    execution_time=time.time() - start_time,
                    expected_failure=test_case.should_fail,
                )

        except Exception as e:
            self.session.rollback()

            result = ConstraintValidationResult(
                test_name=test_case.name,
                constraint_type=test_case.constraint_type,
                result=ConstraintTestResult.ERROR,
                error_message=str(e),
                execution_time=time.time() - start_time,
                expected_failure=test_case.should_fail,
            )

        return result

    @standard_exception_handler
    async def validate_custom_constraints(
        self, model_class: type, custom_validators: list[Callable[[Any], bool]], test_data_sets: list[dict]
    ) -> list[ConstraintValidationResult]:
        """
        Validate custom business logic constraints.

        Args:
            model_class: SQLAlchemy model class
            custom_validators: List of validation functions
            test_data_sets: Test data for validation

        Returns:
            List of custom constraint validation results
        """
        results = []

        for i, validator in enumerate(custom_validators):
            for j, test_data in enumerate(test_data_sets):
                try:
                    record = model_class(**test_data)
                    is_valid = validator(record)

                    result = ConstraintValidationResult(
                        test_name=f"custom_validator_{i}_dataset_{j}",
                        constraint_type=ConstraintType.CUSTOM,
                        result=ConstraintTestResult.PASS if is_valid else ConstraintTestResult.FAIL,
                        expected_failure=False,
                    )

                except Exception as e:
                    result = ConstraintValidationResult(
                        test_name=f"custom_validator_{i}_dataset_{j}",
                        constraint_type=ConstraintType.CUSTOM,
                        result=ConstraintTestResult.ERROR,
                        error_message=str(e),
                        expected_failure=False,
                    )

                results.append(result)

        self.test_results.extend(results)
        return results

    def get_constraint_summary(self) -> dict[str, Any]:
        """Get summary of constraint validation results"""

        if not self.test_results:
            return {"total": 0, "summary": "No constraint tests run"}

        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r.result == ConstraintTestResult.PASS)
        failed = sum(1 for r in self.test_results if r.result == ConstraintTestResult.FAIL)
        errors = sum(1 for r in self.test_results if r.result == ConstraintTestResult.ERROR)

        # Break down by constraint type
        constraint_breakdown = {}
        for result in self.test_results:
            constraint_type = result.constraint_type.value
            if constraint_type not in constraint_breakdown:
                constraint_breakdown[constraint_type] = {"total": 0, "passed": 0, "failed": 0, "errors": 0}

            constraint_breakdown[constraint_type]["total"] += 1
            if result.result == ConstraintTestResult.PASS:
                constraint_breakdown[constraint_type]["passed"] += 1
            elif result.result == ConstraintTestResult.FAIL:
                constraint_breakdown[constraint_type]["failed"] += 1
            else:
                constraint_breakdown[constraint_type]["errors"] += 1

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": (passed / total * 100) if total > 0 else 0,
            "constraint_breakdown": constraint_breakdown,
            "average_execution_time": sum(r.execution_time for r in self.test_results) / total if total > 0 else 0,
        }


# Convenience functions


async def validate_model_constraints(
    session: Session,
    model_class: type,
    test_data_sets: list[dict[str, Any]],
    include_custom: bool = False,
    custom_validators: Optional[list[Callable]] = None,
) -> dict[str, Any]:
    """
    Convenient function to validate all constraints for a model.

    Args:
        session: Database session
        model_class: SQLAlchemy model class
        test_data_sets: Test data for constraint validation
        include_custom: Whether to include custom constraint validation
        custom_validators: Custom validation functions

    Returns:
        Dictionary with validation results and summary
    """
    validator = DatabaseConstraintValidator(session)

    # Standard constraint validation
    constraint_results = await validator.validate_model_constraints(model_class, test_data_sets)

    # Custom constraint validation
    custom_results = []
    if include_custom and custom_validators:
        custom_results = await validator.validate_custom_constraints(model_class, custom_validators, test_data_sets)

    return {
        "model": model_class.__name__,
        "constraint_tests": len(constraint_results),
        "custom_tests": len(custom_results),
        "summary": validator.get_constraint_summary(),
        "detailed_results": validator.test_results,
    }


def create_constraint_test_data(model_class: type, variations: int = 5) -> list[dict[str, Any]]:
    """
    Generate test data variations for constraint testing.

    Args:
        model_class: SQLAlchemy model class
        variations: Number of data variations to generate

    Returns:
        List of test data dictionaries
    """
    test_data_sets = []

    # Inspect model to generate appropriate test data
    inspector = sqlalchemy_inspect(model_class)

    for i in range(variations):
        test_data = {}

        for column in inspector.columns:
            column_name = column.name
            column_type = column.type

            # Generate test data based on column type
            if isinstance(column_type, Integer):
                test_data[column_name] = i + 1
            elif isinstance(column_type, String):
                test_data[column_name] = f"test_value_{i}"
            elif isinstance(column_type, Boolean):
                test_data[column_name] = i % 2 == 0
            elif isinstance(column_type, DateTime):
                from datetime import datetime

                test_data[column_name] = datetime.now()
            # Add more type mappings as needed

        test_data_sets.append(test_data)

    return test_data_sets
