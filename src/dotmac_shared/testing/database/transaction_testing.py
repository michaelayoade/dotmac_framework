"""
Database Transaction Testing Framework

Comprehensive testing utilities for database transactions, rollbacks,
isolation levels, and concurrent operations.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ...api.exception_handlers import standard_exception_handler
from ...core.logging import get_logger

logger = get_logger(__name__)


class TransactionTestResult(str, Enum):
    """Transaction test result states"""

    SUCCESS = "success"
    ROLLBACK = "rollback"
    INTEGRITY_ERROR = "integrity_error"
    DEADLOCK = "deadlock"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class TransactionTestCase:
    """Defines a transaction test case"""

    name: str
    operations: list[Callable]
    expected_result: TransactionTestResult
    isolation_level: Optional[str] = None
    timeout_seconds: float = 30.0
    concurrent_sessions: int = 1


@dataclass
class TransactionTestResult:
    """Result of a transaction test"""

    test_name: str
    result: TransactionTestResult
    execution_time: float
    error_message: Optional[str] = None
    operations_completed: int = 0
    rollback_occurred: bool = False


class DatabaseTransactionTester:
    """
    Comprehensive database transaction testing framework.

    Features:
    - Transaction rollback testing
    - Isolation level validation
    - Concurrent transaction testing
    - Deadlock detection and handling
    - Performance measurement
    - Data integrity validation
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
        self.test_results: list[TransactionTestResult] = []

    @standard_exception_handler
    async def run_transaction_test(self, test_case: TransactionTestCase) -> TransactionTestResult:
        """Run a single transaction test case"""
        logger.info(f"Running transaction test: {test_case.name}")
        start_time = time.time()

        try:
            if test_case.concurrent_sessions > 1:
                result = await self._run_concurrent_test(test_case)
            else:
                result = await self._run_single_session_test(test_case)

            execution_time = time.time() - start_time

            test_result = TransactionTestResult(
                test_name=test_case.name,
                result=result.result,
                execution_time=execution_time,
                error_message=result.error_message,
                operations_completed=result.operations_completed,
                rollback_occurred=result.rollback_occurred,
            )

            self.test_results.append(test_result)
            return test_result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Transaction test {test_case.name} failed: {e}")

            test_result = TransactionTestResult(
                test_name=test_case.name,
                result=TransactionTestResult.ERROR,
                execution_time=execution_time,
                error_message=str(e),
            )

            self.test_results.append(test_result)
            return test_result

    async def _run_single_session_test(self, test_case: TransactionTestCase) -> TransactionTestResult:
        """Run test case with single database session"""
        with self.SessionLocal() as session:
            try:
                # Set isolation level if specified
                if test_case.isolation_level:
                    session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {test_case.isolation_level}"))

                operations_completed = 0
                rollback_occurred = False

                # Execute operations within transaction
                for i, operation in enumerate(test_case.operations):
                    try:
                        await self._execute_operation(session, operation)
                        operations_completed = i + 1
                    except Exception as e:
                        logger.warning(f"Operation {i} failed: {e}")
                        if isinstance(e, IntegrityError):
                            session.rollback()
                            rollback_occurred = True
                            return TransactionTestResult(
                                test_name=test_case.name,
                                result=TransactionTestResult.INTEGRITY_ERROR,
                                execution_time=0,
                                error_message=str(e),
                                operations_completed=operations_completed,
                                rollback_occurred=rollback_occurred,
                            )
                        raise

                # Commit transaction
                session.commit()

                return TransactionTestResult(
                    test_name=test_case.name,
                    result=TransactionTestResult.SUCCESS,
                    execution_time=0,
                    operations_completed=operations_completed,
                    rollback_occurred=rollback_occurred,
                )

            except Exception as e:
                session.rollback()
                rollback_occurred = True

                if "deadlock" in str(e).lower():
                    result_type = TransactionTestResult.DEADLOCK
                else:
                    result_type = TransactionTestResult.ERROR

                return TransactionTestResult(
                    test_name=test_case.name,
                    result=result_type,
                    execution_time=0,
                    error_message=str(e),
                    operations_completed=operations_completed,
                    rollback_occurred=rollback_occurred,
                )

    async def _run_concurrent_test(self, test_case: TransactionTestCase) -> TransactionTestResult:
        """Run test case with concurrent database sessions"""

        async def run_concurrent_session(session_id: int):
            """Run operations in a single concurrent session"""
            with self.SessionLocal() as session:
                try:
                    if test_case.isolation_level:
                        session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {test_case.isolation_level}"))

                    operations_completed = 0
                    for i, operation in enumerate(test_case.operations):
                        await self._execute_operation(session, operation)
                        operations_completed = i + 1

                        # Add small delay to increase chance of conflicts
                        await asyncio.sleep(0.01)

                    session.commit()
                    return {"success": True, "operations_completed": operations_completed}

                except Exception as e:
                    session.rollback()
                    return {"success": False, "error": str(e), "operations_completed": operations_completed}

        # Run concurrent sessions
        tasks = [run_concurrent_session(i) for i in range(test_case.concurrent_sessions)]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        successful_sessions = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        total_operations = sum(r.get("operations_completed", 0) for r in results if isinstance(r, dict))

        errors = [r.get("error") for r in results if isinstance(r, dict) and not r.get("success")]

        if successful_sessions == test_case.concurrent_sessions:
            result_type = TransactionTestResult.SUCCESS
        elif any("deadlock" in str(e).lower() for e in errors if e):
            result_type = TransactionTestResult.DEADLOCK
        elif any("integrity" in str(e).lower() for e in errors if e):
            result_type = TransactionTestResult.INTEGRITY_ERROR
        else:
            result_type = TransactionTestResult.ERROR

        return TransactionTestResult(
            test_name=test_case.name,
            result=result_type,
            execution_time=0,
            error_message="; ".join(str(e) for e in errors if e),
            operations_completed=total_operations,
            rollback_occurred=successful_sessions < test_case.concurrent_sessions,
        )

    async def _execute_operation(self, session: Session, operation: Callable):
        """Execute a single database operation"""
        if asyncio.iscoroutinefunction(operation):
            await operation(session)
        else:
            operation(session)

    @standard_exception_handler
    async def test_rollback_scenarios(self, model_class: type, test_data: list[dict]) -> list[TransactionTestResult]:
        """Test various rollback scenarios"""

        test_cases = [
            # Basic rollback test
            TransactionTestCase(
                name=f"basic_rollback_{model_class.__name__}",
                operations=[
                    lambda s: self._create_record(s, model_class, test_data[0]),
                    lambda s: s.rollback(),  # Explicit rollback
                    lambda s: self._verify_record_not_exists(s, model_class, test_data[0]),
                ],
                expected_result=TransactionTestResult.ROLLBACK,
            ),
            # Constraint violation rollback
            TransactionTestCase(
                name=f"constraint_violation_{model_class.__name__}",
                operations=[
                    lambda s: self._create_record(s, model_class, test_data[0]),
                    lambda s: s.commit(),
                    lambda s: self._create_record(s, model_class, test_data[0]),  # Duplicate
                ],
                expected_result=TransactionTestResult.INTEGRITY_ERROR,
            ),
            # Savepoint rollback
            TransactionTestCase(
                name=f"savepoint_rollback_{model_class.__name__}",
                operations=[
                    lambda s: self._create_record(s, model_class, test_data[0]),
                    lambda s: s.begin_nested(),  # Savepoint
                    lambda s: self._create_record(s, model_class, test_data[1]),
                    lambda s: s.rollback(),  # Rollback to savepoint
                    lambda s: s.commit(),
                    lambda s: self._verify_record_exists(s, model_class, test_data[0]),
                    lambda s: self._verify_record_not_exists(s, model_class, test_data[1]),
                ],
                expected_result=TransactionTestResult.SUCCESS,
            ),
        ]

        results = []
        for test_case in test_cases:
            result = await self.run_transaction_test(test_case)
            results.append(result)

        return results

    @standard_exception_handler
    async def test_isolation_levels(self, model_class: type, test_data: dict) -> list[TransactionTestResult]:
        """Test different transaction isolation levels"""

        isolation_levels = ["READ UNCOMMITTED", "READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE"]

        test_cases = []
        for isolation_level in isolation_levels:
            test_cases.append(
                TransactionTestCase(
                    name=f"isolation_{isolation_level.replace(' ', '_').lower()}_{model_class.__name__}",
                    operations=[
                        lambda s: self._create_record(s, model_class, test_data),
                        lambda s: s.commit(),
                        lambda s: self._read_record(s, model_class, test_data),
                    ],
                    expected_result=TransactionTestResult.SUCCESS,
                    isolation_level=isolation_level,
                )
            )

        results = []
        for test_case in test_cases:
            result = await self.run_transaction_test(test_case)
            results.append(result)

        return results

    @standard_exception_handler
    async def test_concurrent_access(self, model_class: type, test_data: list[dict]) -> list[TransactionTestResult]:
        """Test concurrent database access scenarios"""

        test_cases = [
            # Concurrent inserts
            TransactionTestCase(
                name=f"concurrent_inserts_{model_class.__name__}",
                operations=[lambda s: self._create_record(s, model_class, test_data[0])],
                expected_result=TransactionTestResult.SUCCESS,
                concurrent_sessions=5,
            ),
            # Concurrent updates
            TransactionTestCase(
                name=f"concurrent_updates_{model_class.__name__}",
                operations=[lambda s: self._update_record(s, model_class, test_data[0], {"updated": True})],
                expected_result=TransactionTestResult.SUCCESS,
                concurrent_sessions=3,
            ),
            # Read-write conflicts
            TransactionTestCase(
                name=f"read_write_conflicts_{model_class.__name__}",
                operations=[
                    lambda s: self._read_record(s, model_class, test_data[0]),
                    lambda s: self._update_record(s, model_class, test_data[0], {"version": 2}),
                    lambda s: asyncio.sleep(0.1),  # Hold transaction open
                ],
                expected_result=TransactionTestResult.SUCCESS,
                concurrent_sessions=4,
                isolation_level="REPEATABLE READ",
            ),
        ]

        results = []
        for test_case in test_cases:
            result = await self.run_transaction_test(test_case)
            results.append(result)

        return results

    def _create_record(self, session: Session, model_class: type, data: dict) -> Any:
        """Helper to create a database record"""
        record = model_class(**data)
        session.add(record)
        session.flush()
        return record

    def _update_record(self, session: Session, model_class: type, filter_data: dict, update_data: dict) -> Any:
        """Helper to update a database record"""
        record = session.query(model_class).filter_by(**filter_data).first()
        if record:
            for key, value in update_data.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            session.flush()
        return record

    def _read_record(self, session: Session, model_class: type, filter_data: dict) -> Any:
        """Helper to read a database record"""
        return session.query(model_class).filter_by(**filter_data).first()

    def _verify_record_exists(self, session: Session, model_class: type, filter_data: dict) -> bool:
        """Verify a record exists"""
        record = session.query(model_class).filter_by(**filter_data).first()
        if not record:
            raise AssertionError(f"Record does not exist: {filter_data}")
        return True

    def _verify_record_not_exists(self, session: Session, model_class: type, filter_data: dict) -> bool:
        """Verify a record does not exist"""
        record = session.query(model_class).filter_by(**filter_data).first()
        if record:
            raise AssertionError(f"Record should not exist: {filter_data}")
        return True

    def get_test_summary(self) -> dict[str, Any]:
        """Get summary of all test results"""
        if not self.test_results:
            return {"total": 0, "summary": "No tests run"}

        total = len(self.test_results)
        successful = sum(1 for r in self.test_results if r.result == TransactionTestResult.SUCCESS)
        failed = total - successful

        avg_execution_time = sum(r.execution_time for r in self.test_results) / total

        result_counts = {}
        for result in self.test_results:
            result_type = result.result.value
            result_counts[result_type] = result_counts.get(result_type, 0) + 1

        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total * 100,
            "average_execution_time": avg_execution_time,
            "result_breakdown": result_counts,
            "tests_with_rollbacks": sum(1 for r in self.test_results if r.rollback_occurred),
        }


# Convenience functions for common testing scenarios


async def test_model_transactions(
    database_url: str, model_class: type, test_data: list[dict], include_concurrent: bool = True
) -> dict[str, Any]:
    """
    Comprehensive transaction testing for a model class.

    Args:
        database_url: Database connection URL
        model_class: SQLAlchemy model class to test
        test_data: List of test data dictionaries
        include_concurrent: Whether to include concurrent access tests

    Returns:
        Dictionary with test results and summary
    """
    tester = DatabaseTransactionTester(database_url)

    # Run rollback tests
    rollback_results = await tester.test_rollback_scenarios(model_class, test_data)

    # Run isolation level tests
    isolation_results = await tester.test_isolation_levels(model_class, test_data[0])

    # Run concurrent access tests
    concurrent_results = []
    if include_concurrent and len(test_data) > 1:
        concurrent_results = await tester.test_concurrent_access(model_class, test_data)

    return {
        "model": model_class.__name__,
        "rollback_tests": len(rollback_results),
        "isolation_tests": len(isolation_results),
        "concurrent_tests": len(concurrent_results),
        "summary": tester.get_test_summary(),
        "detailed_results": tester.test_results,
    }


async def validate_transaction_integrity(
    database_url: str, operations: list[Callable], expected_state_validator: Callable[[Session], bool]
) -> bool:
    """
    Validate that a series of operations maintains data integrity.

    Args:
        database_url: Database connection URL
        operations: List of database operations to perform
        expected_state_validator: Function to validate final database state

    Returns:
        True if integrity is maintained, False otherwise
    """
    tester = DatabaseTransactionTester(database_url)

    test_case = TransactionTestCase(
        name="integrity_validation",
        operations=operations + [expected_state_validator],
        expected_result=TransactionTestResult.SUCCESS,
    )

    result = await tester.run_transaction_test(test_case)
    return result.result == TransactionTestResult.SUCCESS
