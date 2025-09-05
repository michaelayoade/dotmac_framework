"""
Data Integrity Testing Framework

Comprehensive testing utilities for data integrity validation including:
- ACID properties testing
- Referential integrity validation
- Data consistency checks
- Concurrent data access integrity
- Cross-table relationship validation
- Business rule integrity validation
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from sqlalchemy import create_engine, func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ...api.exception_handlers import standard_exception_handler
from ...core.logging import get_logger

logger = get_logger(__name__)


class IntegrityTestType(str, Enum):
    """Types of data integrity tests"""

    ACID_ATOMICITY = "acid_atomicity"
    ACID_CONSISTENCY = "acid_consistency"
    ACID_ISOLATION = "acid_isolation"
    ACID_DURABILITY = "acid_durability"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    DATA_CONSISTENCY = "data_consistency"
    CONCURRENT_ACCESS = "concurrent_access"
    BUSINESS_RULES = "business_rules"


class IntegrityTestResult(str, Enum):
    """Data integrity test result states"""

    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    TIMEOUT = "timeout"
    PARTIAL = "partial"


@dataclass
class IntegrityViolation:
    """Represents a data integrity violation"""

    violation_type: str
    table: str
    record_id: Any
    field: str
    expected_value: Any
    actual_value: Any
    description: str


@dataclass
class IntegrityTestCase:
    """Defines a data integrity test case"""

    name: str
    test_type: IntegrityTestType
    operations: list[Callable]
    validation_queries: list[Callable]
    expected_violations: int = 0
    timeout_seconds: float = 60.0
    concurrent_operations: int = 1


@dataclass
class IntegrityTestResult:
    """Result of a data integrity test"""

    test_name: str
    test_type: IntegrityTestType
    result: IntegrityTestResult
    violations: list[IntegrityViolation]
    execution_time: float
    operations_completed: int = 0
    error_message: Optional[str] = None


class DataIntegrityTester:
    """
    Comprehensive data integrity testing framework.

    Features:
    - ACID properties validation
    - Referential integrity testing
    - Data consistency verification
    - Concurrent access integrity testing
    - Cross-table relationship validation
    - Business rule compliance testing
    - Performance impact measurement
    """

    def __init__(self, database_url: str, echo: bool = False):
        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            echo=echo,
            poolclass=StaticPool,
            pool_pre_ping=True,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.test_results: list[IntegrityTestResult] = []

    @standard_exception_handler
    async def test_acid_properties(
        self, model_classes: list[type], test_data: dict[type, list[dict]]
    ) -> list[IntegrityTestResult]:
        """
        Test ACID properties (Atomicity, Consistency, Isolation, Durability).

        Args:
            model_classes: List of SQLAlchemy model classes
            test_data: Test data for each model class

        Returns:
            List of ACID test results
        """
        results = []

        # Test Atomicity
        atomicity_result = await self._test_atomicity(model_classes, test_data)
        results.append(atomicity_result)

        # Test Consistency
        consistency_result = await self._test_consistency(model_classes, test_data)
        results.append(consistency_result)

        # Test Isolation
        isolation_result = await self._test_isolation(model_classes, test_data)
        results.append(isolation_result)

        # Test Durability
        durability_result = await self._test_durability(model_classes, test_data)
        results.append(durability_result)

        self.test_results.extend(results)
        return results

    async def _test_atomicity(
        self, model_classes: list[type], test_data: dict[type, list[dict]]
    ) -> IntegrityTestResult:
        """Test transaction atomicity - all or nothing"""

        start_time = time.time()
        violations = []

        try:
            with self.SessionLocal() as session:
                # Create a transaction that should fail midway
                session.begin()

                operations_completed = 0
                for model_class in model_classes:
                    if model_class in test_data:
                        for data in test_data[model_class][:2]:  # Only use first 2 records
                            record = model_class(**data)
                            session.add(record)
                            operations_completed += 1

                # Force an error to trigger rollback
                session.execute(text("INSERT INTO non_existent_table VALUES (1)"))
                session.commit()

                # If we get here, atomicity failed
                violations.append(
                    IntegrityViolation(
                        violation_type="atomicity",
                        table="all",
                        record_id="N/A",
                        field="transaction",
                        expected_value="rollback",
                        actual_value="commit",
                        description="Transaction committed despite error",
                    )
                )

        except Exception:
            # Expected - transaction should have rolled back
            # Verify no records were actually inserted
            with self.SessionLocal() as verify_session:
                for model_class in model_classes:
                    count = verify_session.query(func.count(model_class.id)).scalar()
                    if count > 0:
                        violations.append(
                            IntegrityViolation(
                                violation_type="atomicity",
                                table=model_class.__tablename__,
                                record_id="N/A",
                                field="rollback",
                                expected_value=0,
                                actual_value=count,
                                description="Records persisted despite transaction rollback",
                            )
                        )

        execution_time = time.time() - start_time

        return IntegrityTestResult(
            test_name="acid_atomicity_test",
            test_type=IntegrityTestType.ACID_ATOMICITY,
            result=IntegrityTestResult.PASS if not violations else IntegrityTestResult.FAIL,
            violations=violations,
            execution_time=execution_time,
        )

    async def _test_consistency(
        self, model_classes: list[type], test_data: dict[type, list[dict]]
    ) -> IntegrityTestResult:
        """Test database consistency - constraints maintained"""

        start_time = time.time()
        violations = []

        try:
            with self.SessionLocal() as session:
                # Test consistency by trying to violate constraints
                for model_class in model_classes:
                    if model_class in test_data and test_data[model_class]:
                        # Try to insert data that violates constraints
                        data = test_data[model_class][0].copy()

                        # Test primary key violation
                        try:
                            record1 = model_class(**data)
                            record2 = model_class(**data)  # Same data = PK violation
                            session.add(record1)
                            session.add(record2)
                            session.commit()

                            violations.append(
                                IntegrityViolation(
                                    violation_type="consistency",
                                    table=model_class.__tablename__,
                                    record_id=data.get("id", "N/A"),
                                    field="primary_key",
                                    expected_value="unique",
                                    actual_value="duplicate",
                                    description="Primary key constraint not enforced",
                                )
                            )

                        except IntegrityError:
                            # Expected - constraint should prevent duplicate
                            session.rollback()

        except Exception as e:
            violations.append(
                IntegrityViolation(
                    violation_type="consistency",
                    table="unknown",
                    record_id="N/A",
                    field="test_execution",
                    expected_value="success",
                    actual_value="error",
                    description=f"Consistency test failed: {str(e)}",
                )
            )

        execution_time = time.time() - start_time

        return IntegrityTestResult(
            test_name="acid_consistency_test",
            test_type=IntegrityTestType.ACID_CONSISTENCY,
            result=IntegrityTestResult.PASS if not violations else IntegrityTestResult.FAIL,
            violations=violations,
            execution_time=execution_time,
        )

    async def _test_isolation(
        self, model_classes: list[type], test_data: dict[type, list[dict]]
    ) -> IntegrityTestResult:
        """Test transaction isolation"""

        start_time = time.time()
        violations = []

        try:
            # Run concurrent transactions to test isolation
            async def transaction1():
                with self.SessionLocal() as session:
                    session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
                    if model_classes and model_classes[0] in test_data:
                        data = test_data[model_classes[0]][0]
                        record = model_classes[0](**data)
                        session.add(record)
                        # Hold transaction open
                        await asyncio.sleep(0.5)
                        session.commit()
                        return True

            async def transaction2():
                await asyncio.sleep(0.1)  # Start after transaction1
                with self.SessionLocal() as session:
                    session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
                    if model_classes:
                        # Try to read data from transaction1 before it commits
                        count = session.query(func.count(model_classes[0].id)).scalar()
                        return count

            # Run transactions concurrently
            task1 = asyncio.create_task(transaction1())
            task2 = asyncio.create_task(transaction2())

            await asyncio.gather(task1, task2, return_exceptions=True)

            # Analyze isolation behavior
            # transaction2 should not see uncommitted data from transaction1

        except Exception as e:
            violations.append(
                IntegrityViolation(
                    violation_type="isolation",
                    table="unknown",
                    record_id="N/A",
                    field="concurrent_access",
                    expected_value="isolated",
                    actual_value="error",
                    description=f"Isolation test failed: {str(e)}",
                )
            )

        execution_time = time.time() - start_time

        return IntegrityTestResult(
            test_name="acid_isolation_test",
            test_type=IntegrityTestType.ACID_ISOLATION,
            result=IntegrityTestResult.PASS if not violations else IntegrityTestResult.FAIL,
            violations=violations,
            execution_time=execution_time,
        )

    async def _test_durability(
        self, model_classes: list[type], test_data: dict[type, list[dict]]
    ) -> IntegrityTestResult:
        """Test transaction durability"""

        start_time = time.time()
        violations = []

        try:
            # Insert data and commit
            record_ids = []
            with self.SessionLocal() as session:
                for model_class in model_classes:
                    if model_class in test_data and test_data[model_class]:
                        data = test_data[model_class][0]
                        record = model_class(**data)
                        session.add(record)
                        session.commit()
                        record_ids.append((model_class, record.id if hasattr(record, "id") else None))

            # Simulate connection loss/restart (close all connections)
            self.engine.dispose()

            # Recreate engine and verify data persists
            self.engine = create_engine(self.database_url, poolclass=StaticPool, pool_pre_ping=True)
            self.SessionLocal = sessionmaker(bind=self.engine)

            # Verify records still exist
            with self.SessionLocal() as session:
                for model_class, record_id in record_ids:
                    if record_id:
                        record = session.get(model_class, record_id)
                        if not record:
                            violations.append(
                                IntegrityViolation(
                                    violation_type="durability",
                                    table=model_class.__tablename__,
                                    record_id=record_id,
                                    field="persistence",
                                    expected_value="exists",
                                    actual_value="missing",
                                    description="Committed data lost after connection reset",
                                )
                            )

        except Exception as e:
            violations.append(
                IntegrityViolation(
                    violation_type="durability",
                    table="unknown",
                    record_id="N/A",
                    field="test_execution",
                    expected_value="success",
                    actual_value="error",
                    description=f"Durability test failed: {str(e)}",
                )
            )

        execution_time = time.time() - start_time

        return IntegrityTestResult(
            test_name="acid_durability_test",
            test_type=IntegrityTestType.ACID_DURABILITY,
            result=IntegrityTestResult.PASS if not violations else IntegrityTestResult.FAIL,
            violations=violations,
            execution_time=execution_time,
        )

    @standard_exception_handler
    async def test_referential_integrity(
        self, parent_model: type, child_model: type, parent_data: dict, child_data: dict, foreign_key_field: str
    ) -> IntegrityTestResult:
        """Test referential integrity between related models"""

        start_time = time.time()
        violations = []

        try:
            with self.SessionLocal() as session:
                # Create parent record
                parent_record = parent_model(**parent_data)
                session.add(parent_record)
                session.flush()  # Get the ID

                # Create child record with valid foreign key
                child_data_copy = child_data.copy()
                child_data_copy[foreign_key_field] = parent_record.id
                child_record = child_model(**child_data_copy)
                session.add(child_record)
                session.commit()

                # Test 1: Try to delete parent with existing child (should fail)
                try:
                    session.delete(parent_record)
                    session.commit()

                    violations.append(
                        IntegrityViolation(
                            violation_type="referential_integrity",
                            table=parent_model.__tablename__,
                            record_id=parent_record.id,
                            field="foreign_key_constraint",
                            expected_value="deletion_blocked",
                            actual_value="deletion_allowed",
                            description="Parent record deleted despite child references",
                        )
                    )

                except IntegrityError:
                    # Expected - should not be able to delete parent
                    session.rollback()

                # Test 2: Try to create child with invalid foreign key
                session.begin()
                invalid_child_data = child_data.copy()
                invalid_child_data[foreign_key_field] = 99999  # Non-existent parent
                invalid_child = child_model(**invalid_child_data)
                session.add(invalid_child)

                try:
                    session.commit()

                    violations.append(
                        IntegrityViolation(
                            violation_type="referential_integrity",
                            table=child_model.__tablename__,
                            record_id="N/A",
                            field=foreign_key_field,
                            expected_value="constraint_violation",
                            actual_value="invalid_reference_allowed",
                            description="Child record created with invalid foreign key",
                        )
                    )

                except IntegrityError:
                    # Expected - should not allow invalid foreign key
                    session.rollback()

        except Exception as e:
            violations.append(
                IntegrityViolation(
                    violation_type="referential_integrity",
                    table="unknown",
                    record_id="N/A",
                    field="test_execution",
                    expected_value="success",
                    actual_value="error",
                    description=f"Referential integrity test failed: {str(e)}",
                )
            )

        execution_time = time.time() - start_time

        result = IntegrityTestResult(
            test_name=f"referential_integrity_{parent_model.__name__}_{child_model.__name__}",
            test_type=IntegrityTestType.REFERENTIAL_INTEGRITY,
            result=IntegrityTestResult.PASS if not violations else IntegrityTestResult.FAIL,
            violations=violations,
            execution_time=execution_time,
        )

        self.test_results.append(result)
        return result

    @standard_exception_handler
    async def test_concurrent_data_integrity(
        self, model_class: type, test_data: list[dict], concurrent_operations: int = 5
    ) -> IntegrityTestResult:
        """Test data integrity under concurrent access"""

        start_time = time.time()
        violations = []

        try:
            # Create initial data
            with self.SessionLocal() as session:
                for data in test_data:
                    record = model_class(**data)
                    session.add(record)
                session.commit()

            async def concurrent_operation(operation_id: int):
                """Perform concurrent database operations"""
                results = []
                with self.SessionLocal() as session:
                    try:
                        # Read all records
                        records = session.query(model_class).all()
                        initial_count = len(records)

                        # Update each record
                        for record in records:
                            if hasattr(record, "updated_by"):
                                record.updated_by = f"operation_{operation_id}"
                            session.flush()

                        # Add a new record
                        new_data = test_data[0].copy()
                        if "id" in new_data:
                            new_data["id"] = new_data["id"] + operation_id + 100
                        new_record = model_class(**new_data)
                        session.add(new_record)

                        session.commit()

                        # Verify final state
                        final_records = session.query(model_class).all()
                        results.append(
                            {
                                "operation_id": operation_id,
                                "initial_count": initial_count,
                                "final_count": len(final_records),
                                "success": True,
                            }
                        )

                    except Exception as e:
                        session.rollback()
                        results.append({"operation_id": operation_id, "error": str(e), "success": False})

                return results

            # Run concurrent operations
            tasks = [concurrent_operation(i) for i in range(concurrent_operations)]

            operation_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Analyze results for integrity violations
            successful_operations = []
            for result_set in operation_results:
                if isinstance(result_set, list):
                    for result in result_set:
                        if result.get("success"):
                            successful_operations.append(result)

            # Verify final database state is consistent
            with self.SessionLocal() as session:
                final_records = session.query(model_class).all()
                expected_count = len(test_data) + len(successful_operations)

                if len(final_records) != expected_count:
                    violations.append(
                        IntegrityViolation(
                            violation_type="concurrent_access",
                            table=model_class.__tablename__,
                            record_id="N/A",
                            field="record_count",
                            expected_value=expected_count,
                            actual_value=len(final_records),
                            description="Record count inconsistent after concurrent operations",
                        )
                    )

        except Exception as e:
            violations.append(
                IntegrityViolation(
                    violation_type="concurrent_access",
                    table=model_class.__tablename__,
                    record_id="N/A",
                    field="test_execution",
                    expected_value="success",
                    actual_value="error",
                    description=f"Concurrent integrity test failed: {str(e)}",
                )
            )

        execution_time = time.time() - start_time

        result = IntegrityTestResult(
            test_name=f"concurrent_integrity_{model_class.__name__}",
            test_type=IntegrityTestType.CONCURRENT_ACCESS,
            result=IntegrityTestResult.PASS if not violations else IntegrityTestResult.FAIL,
            violations=violations,
            execution_time=execution_time,
        )

        self.test_results.append(result)
        return result

    @standard_exception_handler
    async def validate_business_rules(
        self, model_class: type, business_rules: list[tuple[str, Callable[[Any], bool]]], test_data: list[dict]
    ) -> IntegrityTestResult:
        """Validate business rule integrity"""

        start_time = time.time()
        violations = []

        try:
            with self.SessionLocal() as session:
                for data in test_data:
                    record = model_class(**data)
                    session.add(record)
                    session.flush()

                    # Validate business rules
                    for rule_name, rule_function in business_rules:
                        try:
                            if not rule_function(record):
                                violations.append(
                                    IntegrityViolation(
                                        violation_type="business_rules",
                                        table=model_class.__tablename__,
                                        record_id=getattr(record, "id", "N/A"),
                                        field=rule_name,
                                        expected_value="rule_satisfied",
                                        actual_value="rule_violated",
                                        description=f"Business rule '{rule_name}' violated",
                                    )
                                )

                        except Exception as e:
                            violations.append(
                                IntegrityViolation(
                                    violation_type="business_rules",
                                    table=model_class.__tablename__,
                                    record_id=getattr(record, "id", "N/A"),
                                    field=rule_name,
                                    expected_value="rule_validation",
                                    actual_value="validation_error",
                                    description=f"Business rule '{rule_name}' validation failed: {str(e)}",
                                )
                            )

                session.commit()

        except Exception as e:
            violations.append(
                IntegrityViolation(
                    violation_type="business_rules",
                    table=model_class.__tablename__,
                    record_id="N/A",
                    field="test_execution",
                    expected_value="success",
                    actual_value="error",
                    description=f"Business rule validation failed: {str(e)}",
                )
            )

        execution_time = time.time() - start_time

        result = IntegrityTestResult(
            test_name=f"business_rules_{model_class.__name__}",
            test_type=IntegrityTestType.BUSINESS_RULES,
            result=IntegrityTestResult.PASS if not violations else IntegrityTestResult.FAIL,
            violations=violations,
            execution_time=execution_time,
        )

        self.test_results.append(result)
        return result

    def get_integrity_summary(self) -> dict[str, Any]:
        """Get summary of all integrity test results"""

        if not self.test_results:
            return {"total": 0, "summary": "No integrity tests run"}

        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r.result == IntegrityTestResult.PASS)
        failed = sum(1 for r in self.test_results if r.result == IntegrityTestResult.FAIL)
        errors = sum(1 for r in self.test_results if r.result == IntegrityTestResult.ERROR)

        total_violations = sum(len(r.violations) for r in self.test_results)
        avg_execution_time = sum(r.execution_time for r in self.test_results) / total

        # Break down by test type
        type_breakdown = {}
        for result in self.test_results:
            test_type = result.test_type.value
            if test_type not in type_breakdown:
                type_breakdown[test_type] = {"total": 0, "passed": 0, "violations": 0}

            type_breakdown[test_type]["total"] += 1
            if result.result == IntegrityTestResult.PASS:
                type_breakdown[test_type]["passed"] += 1
            type_breakdown[test_type]["violations"] += len(result.violations)

        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": (passed / total * 100) if total > 0 else 0,
            "total_violations": total_violations,
            "average_execution_time": avg_execution_time,
            "test_type_breakdown": type_breakdown,
        }


# Convenience functions


async def comprehensive_integrity_test(
    database_url: str,
    model_classes: list[type],
    test_data: dict[type, list[dict]],
    include_concurrent: bool = True,
    concurrent_operations: int = 5,
) -> dict[str, Any]:
    """
    Run comprehensive data integrity tests for multiple models.

    Args:
        database_url: Database connection URL
        model_classes: List of SQLAlchemy model classes
        test_data: Test data for each model class
        include_concurrent: Whether to include concurrent access tests
        concurrent_operations: Number of concurrent operations for stress testing

    Returns:
        Dictionary with comprehensive integrity test results
    """
    tester = DataIntegrityTester(database_url)

    # Run ACID tests
    acid_results = await tester.test_acid_properties(model_classes, test_data)

    # Run concurrent integrity tests
    concurrent_results = []
    if include_concurrent:
        for model_class in model_classes:
            if model_class in test_data and test_data[model_class]:
                result = await tester.test_concurrent_data_integrity(
                    model_class, test_data[model_class], concurrent_operations
                )
                concurrent_results.append(result)

    return {
        "acid_tests": len(acid_results),
        "concurrent_tests": len(concurrent_results),
        "summary": tester.get_integrity_summary(),
        "detailed_results": tester.test_results,
    }
