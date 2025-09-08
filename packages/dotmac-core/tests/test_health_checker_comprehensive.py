"""
Comprehensive test coverage for database health checker module.
This addresses the 0% coverage issue for db_toolkit/health/checker.py.
"""

from unittest.mock import AsyncMock, Mock, patch

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from dotmac.core.db_toolkit.health.checker import (
    DatabaseHealthChecker,
    AdvancedHealthChecker,
    HealthCheckResult,
    HealthStatus,
)


class TestHealthStatus:
    """Test HealthStatus enumeration."""

    def test_health_status_values(self):
        """Test all health status values."""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"
        assert HealthStatus.UNKNOWN == "unknown"

    def test_health_status_comparison(self):
        """Test health status comparison and string conversion."""
        assert str(HealthStatus.HEALTHY) == "healthy"
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED != HealthStatus.HEALTHY


class TestHealthCheckResult:
    """Test HealthCheckResult dataclass."""

    def test_health_check_result_creation(self):
        """Test creating a health check result."""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="All systems operational",
            details={"connection": "ok"},
            duration_ms=45.2,
            error=None
        )
        
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All systems operational"
        assert result.details == {"connection": "ok"}
        assert result.duration_ms == 45.2
        assert result.error is None
        assert result.timestamp is not None

    def test_health_check_result_defaults(self):
        """Test default values for health check result."""
        result = HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            message="System down"
        )
        
        assert result.details == {}
        assert result.duration_ms is None
        assert result.error is None
        assert result.timestamp is not None

    def test_health_check_result_with_error(self):
        """Test health check result with error information."""
        result = HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            message="Database connection failed",
            error="Connection timeout after 30 seconds"
        )
        
        assert result.status == HealthStatus.UNHEALTHY
        assert result.error == "Connection timeout after 30 seconds"


class TestDatabaseHealthChecker:
    """Test DatabaseHealthChecker functionality."""

    def test_health_checker_initialization(self):
        """Test health checker initialization with custom parameters."""
        checker = DatabaseHealthChecker(
            connection_timeout=10.0,
            query_timeout=15.0,
            slow_query_threshold=2.0
        )
        
        assert checker.connection_timeout == 10.0
        assert checker.query_timeout == 15.0
        assert checker.slow_query_threshold == 2.0

    def test_health_checker_default_initialization(self):
        """Test health checker initialization with default parameters."""
        checker = DatabaseHealthChecker()
        
        assert checker.connection_timeout == 5.0
        assert checker.query_timeout == 10.0
        assert checker.slow_query_threshold == 1.0

    def test_check_health_success(self):
        """Test successful health check."""
        checker = DatabaseHealthChecker()
        mock_session = Mock(spec=Session)
        
        # Mock successful query execution
        mock_result = Mock()
        mock_result.fetchone.return_value = (1,)
        mock_session.execute.return_value = mock_result
        
        with patch.object(checker, '_check_connectivity') as mock_connectivity, \
             patch.object(checker, '_check_performance') as mock_performance, \
             patch.object(checker, '_collect_metrics') as mock_metrics:
            
            # Setup mock returns
            mock_connectivity.return_value = HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message="Connection successful"
            )
            mock_performance.return_value = HealthCheckResult(
                status=HealthStatus.HEALTHY, 
                message="Performance good"
            )
            mock_metrics.return_value = {"version": "PostgreSQL 13"}
            
            result = checker.check_health(mock_session)
            
            assert result.status == HealthStatus.HEALTHY
            assert "Database health check completed" in result.message
            assert result.duration_ms is not None
            assert "connectivity" in result.details
            assert "performance" in result.details
            assert "metrics" in result.details

    def test_check_health_connectivity_failure(self):
        """Test health check when connectivity fails."""
        checker = DatabaseHealthChecker()
        mock_session = Mock(spec=Session)
        
        with patch.object(checker, '_check_connectivity') as mock_connectivity:
            mock_connectivity.return_value = HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message="Connection failed",
                error="Database unreachable"
            )
            
            result = checker.check_health(mock_session)
            
            assert result.status == HealthStatus.UNHEALTHY
            assert result.message == "Connection failed"
            assert result.error == "Database unreachable"

    def test_check_health_exception_handling(self):
        """Test health check exception handling."""
        checker = DatabaseHealthChecker()
        mock_session = Mock(spec=Session)
        
        with patch.object(checker, '_check_connectivity') as mock_connectivity:
            mock_connectivity.side_effect = Exception("Unexpected error")
            
            result = checker.check_health(mock_session)
            
            assert result.status == HealthStatus.UNHEALTHY
            assert "Health check failed" in result.message
            assert result.error == "Unexpected error"
            assert result.duration_ms is not None

    async def test_async_check_health_success(self):
        """Test successful async health check."""
        checker = DatabaseHealthChecker()
        mock_session = AsyncMock(spec=AsyncSession)
        
        with patch.object(checker, '_async_check_connectivity') as mock_connectivity, \
             patch.object(checker, '_async_check_performance') as mock_performance, \
             patch.object(checker, '_async_collect_metrics') as mock_metrics:
            
            # Setup mock returns
            mock_connectivity.return_value = HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message="Connection successful"
            )
            mock_performance.return_value = HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message="Performance good"
            )
            mock_metrics.return_value = {"version": "PostgreSQL 13"}
            
            result = await checker.async_check_health(mock_session)
            
            assert result.status == HealthStatus.HEALTHY
            assert "Database health check completed" in result.message
            assert result.duration_ms is not None

    async def test_async_check_health_exception_handling(self):
        """Test async health check exception handling."""
        checker = DatabaseHealthChecker()
        mock_session = AsyncMock(spec=AsyncSession)
        
        with patch.object(checker, '_async_check_connectivity') as mock_connectivity:
            mock_connectivity.side_effect = Exception("Async error")
            
            result = await checker.async_check_health(mock_session)
            
            assert result.status == HealthStatus.UNHEALTHY
            assert "Health check failed" in result.message
            assert result.error == "Async error"

    def test_check_connectivity_success(self):
        """Test successful connectivity check."""
        checker = DatabaseHealthChecker()
        mock_session = Mock(spec=Session)
        
        # Mock successful query execution
        mock_result = Mock()
        mock_result.fetchone.return_value = (1,)
        mock_session.execute.return_value = mock_result
        
        result = checker._check_connectivity(mock_session)
        
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Database connection successful"
        assert result.details["connection_active"] is True
        assert result.duration_ms is not None
        
        # Verify the query was executed
        mock_session.execute.assert_called_once()
        args = mock_session.execute.call_args[0]
        assert "SELECT 1 as health_check" in str(args[0])

    def test_check_connectivity_wrong_result(self):
        """Test connectivity check with wrong query result."""
        checker = DatabaseHealthChecker()
        mock_session = Mock(spec=Session)
        
        # Mock query returning wrong result
        mock_result = Mock()
        mock_result.fetchone.return_value = (2,)  # Expected 1
        mock_session.execute.return_value = mock_result
        
        result = checker._check_connectivity(mock_session)
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "unexpected result" in result.message
        assert result.details["expected_result"] == 1
        assert result.details["actual_result"] == 2

    def test_check_connectivity_no_result(self):
        """Test connectivity check with no query result."""
        checker = DatabaseHealthChecker()
        mock_session = Mock(spec=Session)
        
        # Mock query returning no result
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = checker._check_connectivity(mock_session)
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "unexpected result" in result.message
        assert result.details["actual_result"] is None

    def test_check_connectivity_sql_error(self):
        """Test connectivity check with SQL error."""
        checker = DatabaseHealthChecker()
        mock_session = Mock(spec=Session)
        
        # Mock SQL error
        sql_error = OperationalError("Connection failed", None, None)
        mock_session.execute.side_effect = sql_error
        
        result = checker._check_connectivity(mock_session)
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "Database connectivity failed" in result.message
        assert result.details["connection_active"] is False
        assert result.details["error_type"] == "OperationalError"
        assert result.error == str(sql_error)

    async def test_async_check_connectivity_success(self):
        """Test successful async connectivity check."""
        checker = DatabaseHealthChecker()
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock successful async query execution
        mock_result = Mock()
        mock_result.fetchone.return_value = (1,)
        mock_session.execute.return_value = mock_result
        
        result = await checker._async_check_connectivity(mock_session)
        
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Database connection successful"
        assert result.details["connection_active"] is True

    def test_check_performance_good(self):
        """Test performance check with good results."""
        checker = DatabaseHealthChecker(slow_query_threshold=1.0)
        mock_session = Mock(spec=Session)
        
        # Mock fast query execution
        mock_result = Mock()
        mock_result.scalar.return_value = 42
        mock_session.execute.return_value = mock_result
        
        with patch('time.time') as mock_time:
            # Mock timing to show fast execution (0.5 seconds)
            mock_time.side_effect = [1000.0, 1000.5]
            
            result = checker._check_performance(mock_session)
            
            assert result.status == HealthStatus.HEALTHY
            assert "performance is good" in result.message
            assert result.details["query_duration_ms"] == 500.0
            assert result.details["table_count"] == 42

    def test_check_performance_degraded(self):
        """Test performance check with degraded results."""
        checker = DatabaseHealthChecker(slow_query_threshold=1.0)
        mock_session = Mock(spec=Session)
        
        # Mock slow query execution
        mock_result = Mock()
        mock_result.scalar.return_value = 42
        mock_session.execute.return_value = mock_result
        
        with patch('time.time') as mock_time:
            # Mock timing to show slow execution (1.5 seconds)
            mock_time.side_effect = [1000.0, 1001.5]
            
            result = checker._check_performance(mock_session)
            
            assert result.status == HealthStatus.DEGRADED
            assert "performance is degraded" in result.message
            assert result.details["query_duration_ms"] == 1500.0

    def test_check_performance_unhealthy(self):
        """Test performance check with unhealthy results."""
        checker = DatabaseHealthChecker(slow_query_threshold=1.0)
        mock_session = Mock(spec=Session)
        
        # Mock very slow query execution
        mock_result = Mock()
        mock_result.scalar.return_value = 42
        mock_session.execute.return_value = mock_result
        
        with patch('time.time') as mock_time:
            # Mock timing to show very slow execution (3 seconds)
            mock_time.side_effect = [1000.0, 1003.0]
            
            result = checker._check_performance(mock_session)
            
            assert result.status == HealthStatus.UNHEALTHY
            assert "performance is poor" in result.message
            assert result.details["query_duration_ms"] == 3000.0

    def test_check_performance_sql_error(self):
        """Test performance check with SQL error."""
        checker = DatabaseHealthChecker()
        mock_session = Mock(spec=Session)
        
        # Mock SQL error
        sql_error = OperationalError("Query failed", None, None)
        mock_session.execute.side_effect = sql_error
        
        result = checker._check_performance(mock_session)
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "Performance check failed" in result.message
        assert result.details["error_type"] == "OperationalError"

    def test_collect_metrics_success(self):
        """Test successful metrics collection."""
        checker = DatabaseHealthChecker()
        mock_session = Mock(spec=Session)
        
        # Mock database version query
        version_result = Mock()
        version_result.scalar.return_value = "PostgreSQL 13.4"
        
        # Mock active connections query
        connections_result = Mock()
        connections_result.scalar.return_value = 5
        
        # Mock database size query
        size_result = Mock()
        size_result.scalar.return_value = "128 MB"
        
        # Setup execute to return different results based on query
        def execute_side_effect(query):
            query_str = str(query)
            if "version()" in query_str:
                return version_result
            elif "pg_stat_activity" in query_str:
                return connections_result
            elif "pg_database_size" in query_str:
                return size_result
            return Mock()
        
        mock_session.execute.side_effect = execute_side_effect
        
        result = checker._collect_metrics(mock_session)
        
        assert result["database_version"] == "PostgreSQL 13.4"
        assert result["active_connections"] == 5
        assert result["database_size"] == "128 MB"

    def test_collect_metrics_partial_failure(self):
        """Test metrics collection with partial failures."""
        checker = DatabaseHealthChecker()
        mock_session = Mock(spec=Session)
        
        # Mock version query success
        version_result = Mock()
        version_result.scalar.return_value = "PostgreSQL 13.4"
        
        def execute_side_effect(query):
            query_str = str(query)
            if "version()" in query_str:
                return version_result
            else:
                # Fail other queries (PostgreSQL-specific)
                raise OperationalError("Permission denied", None, None)
        
        mock_session.execute.side_effect = execute_side_effect
        
        result = checker._collect_metrics(mock_session)
        
        assert result["database_version"] == "PostgreSQL 13.4"
        assert result["active_connections"] == "unavailable"
        assert result["database_size"] == "unavailable"

    def test_collect_metrics_complete_failure(self):
        """Test metrics collection with complete failure."""
        checker = DatabaseHealthChecker()
        mock_session = Mock(spec=Session)
        
        # Mock all queries failing
        sql_error = OperationalError("Database error", None, None)
        mock_session.execute.side_effect = sql_error
        
        result = checker._collect_metrics(mock_session)
        
        assert result["collection_error"] == str(sql_error)

    def test_determine_overall_status_healthy(self):
        """Test determining overall status when all checks are healthy."""
        checker = DatabaseHealthChecker()
        
        results = [
            HealthCheckResult(HealthStatus.HEALTHY, "Good"),
            HealthCheckResult(HealthStatus.HEALTHY, "Great"),
        ]
        
        status = checker._determine_overall_status(results)
        assert status == HealthStatus.HEALTHY

    def test_determine_overall_status_degraded(self):
        """Test determining overall status when some checks are degraded."""
        checker = DatabaseHealthChecker()
        
        results = [
            HealthCheckResult(HealthStatus.HEALTHY, "Good"),
            HealthCheckResult(HealthStatus.DEGRADED, "Slow"),
        ]
        
        status = checker._determine_overall_status(results)
        assert status == HealthStatus.DEGRADED

    def test_determine_overall_status_unhealthy(self):
        """Test determining overall status when any check is unhealthy."""
        checker = DatabaseHealthChecker()
        
        results = [
            HealthCheckResult(HealthStatus.HEALTHY, "Good"),
            HealthCheckResult(HealthStatus.DEGRADED, "Slow"),
            HealthCheckResult(HealthStatus.UNHEALTHY, "Failed"),
        ]
        
        status = checker._determine_overall_status(results)
        assert status == HealthStatus.UNHEALTHY

    def test_determine_overall_status_unknown(self):
        """Test determining overall status with unknown status."""
        checker = DatabaseHealthChecker()
        
        results = [
            HealthCheckResult(HealthStatus.UNKNOWN, "Unknown"),
        ]
        
        status = checker._determine_overall_status(results)
        assert status == HealthStatus.UNKNOWN

    def test_check_connectivity_public_method(self):
        """Test public check_connectivity method."""
        checker = DatabaseHealthChecker()
        mock_session = Mock(spec=Session)
        
        with patch.object(checker, '_check_connectivity') as mock_check:
            expected_result = HealthCheckResult(HealthStatus.HEALTHY, "OK")
            mock_check.return_value = expected_result
            
            result = checker.check_connectivity(mock_session)
            
            assert result == expected_result
            mock_check.assert_called_once_with(mock_session)

    async def test_async_check_connectivity_public_method(self):
        """Test public async_check_connectivity method."""
        checker = DatabaseHealthChecker()
        mock_session = AsyncMock(spec=AsyncSession)
        
        with patch.object(checker, '_async_check_connectivity') as mock_check:
            expected_result = HealthCheckResult(HealthStatus.HEALTHY, "OK")
            mock_check.return_value = expected_result
            
            result = await checker.async_check_connectivity(mock_session)
            
            assert result == expected_result
            mock_check.assert_called_once_with(mock_session)


class TestAdvancedHealthChecker:
    """Test AdvancedHealthChecker functionality."""

    def test_advanced_health_checker_initialization(self):
        """Test advanced health checker initialization."""
        checker = AdvancedHealthChecker(
            connection_timeout=10.0,
            query_timeout=15.0,
            slow_query_threshold=2.0,
            enable_deep_checks=True
        )
        
        assert checker.connection_timeout == 10.0
        assert checker.query_timeout == 15.0
        assert checker.slow_query_threshold == 2.0
        assert checker.enable_deep_checks is True

    def test_advanced_health_check_basic_only(self):
        """Test advanced health check with only basic checks."""
        checker = AdvancedHealthChecker(enable_deep_checks=False)
        mock_session = Mock(spec=Session)
        
        with patch.object(DatabaseHealthChecker, 'check_health') as mock_basic_check:
            expected_result = HealthCheckResult(HealthStatus.HEALTHY, "All good")
            mock_basic_check.return_value = expected_result
            
            result = checker.check_health(mock_session)
            
            assert result == expected_result
            mock_basic_check.assert_called_once_with(mock_session)

    def test_advanced_health_check_unhealthy_basic(self):
        """Test advanced health check when basic check is unhealthy."""
        checker = AdvancedHealthChecker(enable_deep_checks=True)
        mock_session = Mock(spec=Session)
        
        with patch.object(DatabaseHealthChecker, 'check_health') as mock_basic_check:
            unhealthy_result = HealthCheckResult(HealthStatus.UNHEALTHY, "Failed")
            mock_basic_check.return_value = unhealthy_result
            
            result = checker.check_health(mock_session)
            
            # Should return basic result without deep checks
            assert result == unhealthy_result

    def test_advanced_health_check_with_deep_checks(self):
        """Test advanced health check with deep checks enabled."""
        checker = AdvancedHealthChecker(enable_deep_checks=True)
        mock_session = Mock(spec=Session)
        
        basic_result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="Basic checks passed",
            details={"basic": "ok"}
        )
        
        deep_checks_data = {
            "long_running_queries": 2,
            "largest_tables": [{"table": "users", "size": "1GB"}]
        }
        
        with patch.object(DatabaseHealthChecker, 'check_health') as mock_basic_check, \
             patch.object(checker, '_perform_deep_checks') as mock_deep_checks:
            
            mock_basic_check.return_value = basic_result
            mock_deep_checks.return_value = deep_checks_data
            
            result = checker.check_health(mock_session)
            
            assert result.status == HealthStatus.HEALTHY
            assert result.details["basic"] == "ok"
            assert result.details["deep_checks"] == deep_checks_data

    def test_advanced_health_check_deep_checks_failure(self):
        """Test advanced health check when deep checks fail."""
        checker = AdvancedHealthChecker(enable_deep_checks=True)
        mock_session = Mock(spec=Session)
        
        basic_result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="Basic checks passed",
            details={"basic": "ok"}
        )
        
        with patch.object(DatabaseHealthChecker, 'check_health') as mock_basic_check, \
             patch.object(checker, '_perform_deep_checks') as mock_deep_checks:
            
            mock_basic_check.return_value = basic_result
            mock_deep_checks.side_effect = Exception("Deep check failed")
            
            result = checker.check_health(mock_session)
            
            assert result.status == HealthStatus.HEALTHY  # Basic result preserved
            assert result.details["deep_checks"]["error"] == "Deep check failed"

    def test_perform_deep_checks_success(self):
        """Test successful deep checks execution."""
        checker = AdvancedHealthChecker()
        mock_session = Mock(spec=Session)
        
        # Mock long running queries check
        long_queries_result = Mock()
        long_queries_result.scalar.return_value = 3
        
        # Mock table bloat check
        bloat_result = Mock()
        mock_row1 = Mock()
        mock_row1._mapping = {"schemaname": "public", "tablename": "users", "size": "1 GB"}
        mock_row2 = Mock() 
        mock_row2._mapping = {"schemaname": "public", "tablename": "orders", "size": "512 MB"}
        bloat_result.fetchall.return_value = [mock_row1, mock_row2]
        
        def execute_side_effect(query):
            query_str = str(query)
            if "pg_stat_activity" in query_str and "30 seconds" in query_str:
                return long_queries_result
            elif "pg_tables" in query_str:
                return bloat_result
            return Mock()
        
        mock_session.execute.side_effect = execute_side_effect
        
        result = checker._perform_deep_checks(mock_session)
        
        assert result["long_running_queries"] == 3
        assert len(result["largest_tables"]) == 2
        assert result["largest_tables"][0]["tablename"] == "users"
        assert result["largest_tables"][1]["tablename"] == "orders"

    def test_perform_deep_checks_sql_errors(self):
        """Test deep checks with SQL errors."""
        checker = AdvancedHealthChecker()
        mock_session = Mock(spec=Session)
        
        # Mock SQL errors for PostgreSQL-specific queries
        sql_error = OperationalError("Permission denied", None, None)
        mock_session.execute.side_effect = sql_error
        
        result = checker._perform_deep_checks(mock_session)
        
        assert result["long_running_queries"] == "unavailable"
        assert result["largest_tables"] == "unavailable"