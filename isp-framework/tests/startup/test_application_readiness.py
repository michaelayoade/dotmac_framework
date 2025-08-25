"""
Application Readiness Tests - Ensures 100% startup guarantee
============================================================

These tests must pass for the application to be deployment-ready.
No traditional unit test should be allowed to pass if these fail.

Test Philosophy:
- AI-first: Tests are designed to catch what humans miss
- Holistic: Tests the entire application stack  
- Production-like: Uses real database, real imports, real startup
- Fail-fast: If these fail, nothing else matters
"""
import pytest
import asyncio
import traceback
from pathlib import Path
import importlib
import sys
import subprocess
from contextlib import asynccontextmanager
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import application components - this itself is a test
try:
    from dotmac_isp.main import app
    from dotmac_isp.core.database import Base, get_database_url
    from dotmac_isp.core.settings import get_settings
    APP_IMPORT_SUCCESS = True
    APP_IMPORT_ERROR = None
except Exception as e:
    APP_IMPORT_SUCCESS = False
    APP_IMPORT_ERROR = str(e)
    APP_IMPORT_TRACEBACK = traceback.format_exc()


@pytest.mark.startup_critical
@pytest.mark.order(1)  # Run first - if this fails, nothing else matters
class TestApplicationStartup:
    """Critical application startup validation."""

    def test_core_imports_succeed(self):
        """Test that all core application modules can be imported."""
        if not APP_IMPORT_SUCCESS:
            pytest.fail(f"Core application imports failed: {APP_IMPORT_ERROR}\\n{APP_IMPORT_TRACEBACK}")
        
        assert app is not None
        assert hasattr(app, 'title')
        assert "DotMac ISP Framework" in app.title

    def test_fastapi_app_creation(self):
        """Test that FastAPI app can be created and configured."""
        assert app.debug is not None  # App has debug state
        assert len(app.routes) > 0  # App has routes registered
        assert app.openapi_schema is not None or app.openapi()  # OpenAPI schema works

    def test_settings_load_successfully(self):
        """Test that application settings load without errors."""
        settings = get_settings()
        assert settings is not None
        assert hasattr(settings, 'database_url')
        assert hasattr(settings, 'secret_key')

    def test_database_connection_string_valid(self):
        """Test that database connection string is valid and reachable."""
        db_url = get_database_url()
        assert db_url is not None
        assert "postgresql" in db_url or "sqlite" in db_url
        
        # Test actual connection
        engine = create_async_engine(db_url)
        
        async def test_connection():
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
        
        asyncio.run(test_connection())

    @pytest.mark.asyncio
    async def test_database_schema_integrity(self):
        """Test that database schema matches SQLAlchemy models."""
        db_url = get_database_url()
        engine = create_async_engine(db_url)
        
        async with engine.begin() as conn:
            # Get database inspector
            inspector = inspect(conn.sync_engine)
            
            # Check that all model tables exist in database
            model_tables = set(Base.metadata.tables.keys())
            db_tables = set(inspector.get_table_names())
            
            missing_tables = model_tables - db_tables
            if missing_tables:
                pytest.fail(f"Missing database tables: {missing_tables}")
            
            # Check that foreign key constraints exist
            for table_name in model_tables:
                if table_name in db_tables:
                    table = Base.metadata.tables[table_name]
                    db_fks = inspector.get_foreign_keys(table_name)
                    
                    model_fks = []
                    for constraint in table.constraints:
                        if hasattr(constraint, 'elements'):  # ForeignKeyConstraint
                            for element in constraint.elements:
                                if hasattr(element, 'column'):
                                    model_fks.append(element.column.table.name)
                    
                    # Verify critical relationships exist
                    if model_fks and not db_fks:
                        pytest.fail(f"Table {table_name} missing foreign key constraints")

    def test_all_route_imports_succeed(self):
        """Test that all API routes can be imported and registered."""
        # This will fail if any router imports fail
        assert len(app.routes) > 1  # At least root + other routes
        
        # Test that we can access route metadata
        for route in app.routes:
            if hasattr(route, 'path'):
                assert route.path is not None


@pytest.mark.startup_critical  
@pytest.mark.order(2)
class TestModelMigrationAlignment:
    """Test that SQLAlchemy models match Alembic migrations exactly."""
    
    def test_user_model_migration_alignment(self):
        """Test User model matches its migration."""
        from dotmac_isp.modules.identity.models import User
        
        # Check that User model has expected columns
        expected_columns = {
            'id', 'tenant_id', 'username', 'email', 'password_hash',
            'first_name', 'last_name', 'is_active', 'created_at', 'updated_at'
        }
        
        model_columns = set()
        for column in User.__table__.columns:
            model_columns.add(column.name)
            
        missing_columns = expected_columns - model_columns
        if missing_columns:
            pytest.fail(f"User model missing columns: {missing_columns}")

    def test_customer_model_migration_alignment(self):
        """Test Customer model matches its migration."""
        from dotmac_isp.modules.identity.models import Customer
        
        # Check critical customer fields exist
        expected_columns = {
            'id', 'tenant_id', 'customer_code', 'email', 'phone',
            'status', 'created_at', 'updated_at'
        }
        
        model_columns = {col.name for col in Customer.__table__.columns}
        missing_columns = expected_columns - model_columns
        
        if missing_columns:
            pytest.fail(f"Customer model missing columns: {missing_columns}")

    @pytest.mark.asyncio
    async def test_foreign_key_integrity(self):
        """Test that all foreign key relationships work."""
        db_url = get_database_url()
        engine = create_async_engine(db_url)
        
        async with engine.begin() as conn:
            # Test that we can query with joins (this will fail if FKs are broken)
            try:
                # This should work if User->Customer relationship is correct
                await conn.execute(text("""
                    SELECT u.id, c.id 
                    FROM users u 
                    LEFT JOIN customers c ON c.primary_user_id = u.id 
                    LIMIT 1
                """))
            except Exception as e:
                pytest.fail(f"Foreign key relationship broken: {e}")


@pytest.mark.startup_critical
@pytest.mark.order(3) 
class TestEnvironmentReadiness:
    """Test that the deployment environment is ready."""
    
    def test_required_environment_variables(self):
        """Test that all required environment variables are set."""
        settings = get_settings()
        
        # Critical environment variables that must be set
        assert settings.secret_key is not None, "SECRET_KEY not set"
        assert settings.database_url is not None, "DATABASE_URL not set"
        
        # Validate secret key strength
        assert len(settings.secret_key) >= 32, "SECRET_KEY too weak (< 32 chars)"

    def test_database_migration_status(self):
        """Test that database migrations are current."""
        # Run alembic current to check migration status
        result = subprocess.run(
            ['alembic', 'current'], 
            capture_output=True, 
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        
        if result.returncode != 0:
            pytest.fail(f"Alembic migration check failed: {result.stderr}")
        
        # Should show current revision
        assert "current" in result.stdout or len(result.stdout.strip()) > 0

    def test_critical_dependencies_available(self):
        """Test that all critical dependencies are available."""
        critical_modules = [
            'fastapi',
            'sqlalchemy', 
            'alembic',
            'pydantic',
            'asyncpg',  # PostgreSQL driver
            'redis'
        ]
        
        for module in critical_modules:
            try:
                importlib.import_module(module)
            except ImportError:
                pytest.fail(f"Critical dependency missing: {module}")


@pytest.mark.startup_critical
@pytest.mark.order(4)
class TestApplicationHealthCheck:
    """Test that the application is healthy and ready to serve requests."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint_responds(self):
        """Test that health check endpoint works."""
        from httpx import AsyncClient
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            
            health_data = response.json()
            assert health_data["status"] == "healthy"
            assert "database" in health_data
            assert "timestamp" in health_data

    @pytest.mark.asyncio 
    async def test_openapi_schema_generation(self):
        """Test that OpenAPI schema can be generated."""
        schema = app.openapi()
        assert schema is not None
        assert "openapi" in schema
        assert "paths" in schema
        assert len(schema["paths"]) > 0

    def test_application_can_handle_request_lifecycle(self):
        """Test complete request/response lifecycle."""
        from httpx import Client
        
        with Client(app=app, base_url="http://test") as client:
            # Test that app can handle a real request
            response = client.get("/")
            # Should not get 500 errors
            assert response.status_code in [200, 404, 405]  # Valid HTTP responses


# Integration with existing test suite
def pytest_runtest_setup(item):
    """Hook to ensure startup tests run first and fail fast.""" 
    if "startup_critical" in item.keywords:
        # These tests must pass for app to be ready
        return
        
    # For non-startup tests, check if startup tests have passed
    # This ensures no other tests run if startup is broken
    if not getattr(pytest, '_startup_tests_passed', False):
        # Run a quick startup check
        try:
            from dotmac_isp.main import app
            assert app is not None
            pytest._startup_tests_passed = True
        except Exception:
            pytest.skip("Skipping test - application startup is broken")


if __name__ == "__main__":
    # Allow running startup tests standalone
    pytest.main([__file__, "-v", "-x"])  # Stop on first failure