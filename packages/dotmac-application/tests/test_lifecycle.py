"""
Test application lifecycle management.

Tests startup/shutdown phases, lifecycle tasks, and lifecycle event handling.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI
from contextlib import asynccontextmanager

from dotmac.application import (
    create_app,
    PlatformConfig,
    StandardLifecycleManager,
    DeploymentContext,
    DeploymentMode,
)


class TestLifecycleManagement:
    """Test application lifecycle management."""

    @pytest.fixture
    def lifecycle_manager(self):
        """Create a StandardLifecycleManager for testing."""
        config = PlatformConfig(
            platform_name="test_platform",
            title="Test Platform",
            description="Test platform description"
        )
        return StandardLifecycleManager(config)

    def test_lifecycle_manager_initialization(self, lifecycle_manager):
        """Test StandardLifecycleManager initialization."""
        assert lifecycle_manager.config.platform_name == "test_platform"
        assert lifecycle_manager.startup_complete == False
        assert lifecycle_manager.shutdown_complete == False

    @pytest.mark.asyncio
    async def test_startup_phase_execution(self, lifecycle_manager):
        """Test startup phase execution."""
        # Mock startup tasks
        with patch.object(lifecycle_manager, '_execute_startup_tasks', new_callable=AsyncMock) as mock_startup:
            mock_startup.return_value = None
            
            app = FastAPI()
            await lifecycle_manager.startup(app)
            
            # Verify startup was called and state updated
            mock_startup.assert_called_once_with(app)
            assert lifecycle_manager.startup_complete == True

    @pytest.mark.asyncio
    async def test_shutdown_phase_execution(self, lifecycle_manager):
        """Test shutdown phase execution."""
        # Mock shutdown tasks
        with patch.object(lifecycle_manager, '_execute_shutdown_tasks', new_callable=AsyncMock) as mock_shutdown:
            mock_shutdown.return_value = None
            
            app = FastAPI()
            await lifecycle_manager.shutdown(app)
            
            # Verify shutdown was called and state updated
            mock_shutdown.assert_called_once_with(app)
            assert lifecycle_manager.shutdown_complete == True

    @pytest.mark.asyncio
    async def test_startup_tasks_execution(self):
        """Test startup tasks are executed in order."""
        startup_tasks = ["initialize_database", "setup_ssl", "configure_monitoring"]
        
        config = PlatformConfig(
            platform_name="test_platform",
            title="Test Platform",
            description="Test platform description",
            startup_tasks=startup_tasks
        )
        
        lifecycle_manager = StandardLifecycleManager(config)
        
        # Mock task execution
        executed_tasks = []
        
        async def mock_execute_task(task_name, app):
            executed_tasks.append(task_name)
            
        with patch.object(lifecycle_manager, '_execute_single_startup_task', new_callable=AsyncMock) as mock_task:
            mock_task.side_effect = mock_execute_task
            
            app = FastAPI()
            await lifecycle_manager._execute_startup_tasks(app)
            
            # Verify all tasks were executed in order
            assert executed_tasks == startup_tasks

    @pytest.mark.asyncio
    async def test_shutdown_tasks_execution(self):
        """Test shutdown tasks are executed in reverse order."""
        shutdown_tasks = ["cleanup_resources", "close_connections", "save_state"]
        
        config = PlatformConfig(
            platform_name="test_platform",
            title="Test Platform",
            description="Test platform description",
            shutdown_tasks=shutdown_tasks
        )
        
        lifecycle_manager = StandardLifecycleManager(config)
        
        # Mock task execution
        executed_tasks = []
        
        async def mock_execute_task(task_name, app):
            executed_tasks.append(task_name)
            
        with patch.object(lifecycle_manager, '_execute_single_shutdown_task', new_callable=AsyncMock) as mock_task:
            mock_task.side_effect = mock_execute_task
            
            app = FastAPI()
            await lifecycle_manager._execute_shutdown_tasks(app)
            
            # Verify tasks were executed in reverse order
            assert executed_tasks == list(reversed(shutdown_tasks))

    @pytest.mark.asyncio
    async def test_startup_task_failure_handling(self):
        """Test handling of startup task failures."""
        config = PlatformConfig(
            platform_name="test_platform",
            title="Test Platform",
            description="Test platform description",
            startup_tasks=["failing_task", "succeeding_task"]
        )
        
        lifecycle_manager = StandardLifecycleManager(config)
        
        async def mock_failing_task(task_name, app):
            if task_name == "failing_task":
                raise RuntimeError("Task failed")
            
        with patch.object(lifecycle_manager, '_execute_single_startup_task', new_callable=AsyncMock) as mock_task:
            mock_task.side_effect = mock_failing_task
            
            app = FastAPI()
            
            # Startup should handle task failure gracefully
            with pytest.raises(RuntimeError):
                await lifecycle_manager._execute_startup_tasks(app)

    @pytest.mark.asyncio
    async def test_lifespan_context_manager(self):
        """Test lifespan context manager integration."""
        startup_called = False
        shutdown_called = False
        
        config = PlatformConfig(
            platform_name="test_platform",
            title="Test Platform",
            description="Test platform description"
        )
        
        lifecycle_manager = StandardLifecycleManager(config)
        
        # Mock startup and shutdown
        async def mock_startup(app):
            nonlocal startup_called
            startup_called = True
            
        async def mock_shutdown(app):
            nonlocal shutdown_called
            shutdown_called = True
            
        with patch.object(lifecycle_manager, 'startup', new_callable=AsyncMock) as mock_startup_method:
            with patch.object(lifecycle_manager, 'shutdown', new_callable=AsyncMock) as mock_shutdown_method:
                mock_startup_method.side_effect = mock_startup
                mock_shutdown_method.side_effect = mock_shutdown
                
                # Create lifespan context
                lifespan_context = lifecycle_manager.create_lifespan_context()
                
                # Simulate FastAPI lifespan
                app = FastAPI()
                async with lifespan_context(app):
                    # During app lifetime
                    pass
                
                # Verify both startup and shutdown were called
                mock_startup_method.assert_called_once_with(app)
                mock_shutdown_method.assert_called_once_with(app)

    def test_deployment_specific_lifecycle_tasks(self):
        """Test deployment-specific lifecycle tasks."""
        # Management platform deployment
        management_context = DeploymentContext(
            mode=DeploymentMode.MANAGEMENT_PLATFORM
        )
        
        management_config = PlatformConfig(
            platform_name="management_platform",
            title="Management Platform",
            description="Management platform description",
            deployment_context=management_context
        )
        
        management_lifecycle = StandardLifecycleManager(management_config)
        
        # Should have platform-specific tasks
        platform_tasks = management_lifecycle._get_deployment_specific_tasks()
        assert len(platform_tasks) > 0
        
        # Tenant container deployment  
        tenant_context = DeploymentContext(
            mode=DeploymentMode.TENANT_CONTAINER,
            tenant_id="test-tenant"
        )
        
        tenant_config = PlatformConfig(
            platform_name="tenant_platform",
            title="Tenant Platform", 
            description="Tenant platform description",
            deployment_context=tenant_context
        )
        
        tenant_lifecycle = StandardLifecycleManager(tenant_config)
        
        # Should have tenant-specific tasks
        tenant_tasks = tenant_lifecycle._get_deployment_specific_tasks()
        assert len(tenant_tasks) > 0
        
        # Tasks should be different for different deployments
        assert platform_tasks != tenant_tasks

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_task_failure(self):
        """Test graceful degradation when optional tasks fail."""
        config = PlatformConfig(
            platform_name="test_platform",
            title="Test Platform",
            description="Test platform description",
            startup_tasks=["critical_task", "optional_task"]
        )
        
        lifecycle_manager = StandardLifecycleManager(config)
        
        task_results = {}
        
        async def mock_execute_task(task_name, app):
            if task_name == "critical_task":
                task_results[task_name] = "success"
            elif task_name == "optional_task":
                raise RuntimeError("Optional task failed")
                
        with patch.object(lifecycle_manager, '_is_task_critical') as mock_critical:
            with patch.object(lifecycle_manager, '_execute_single_startup_task', new_callable=AsyncMock) as mock_task:
                
                # Make critical_task critical, optional_task not critical
                mock_critical.side_effect = lambda task: task == "critical_task"
                mock_task.side_effect = mock_execute_task
                
                app = FastAPI()
                
                # Should handle optional task failure gracefully
                await lifecycle_manager._execute_startup_tasks(app)
                
                # Critical task should have completed
                assert "critical_task" in task_results

    def test_lifecycle_integration_with_app_factory(self):
        """Test lifecycle manager integration with app factory."""
        config = PlatformConfig(
            platform_name="test_platform",
            title="Test Platform",
            description="Test platform description",
            startup_tasks=["test_startup_task"],
            shutdown_tasks=["test_shutdown_task"]
        )
        
        # App creation should set up lifecycle properly
        app = create_app(config)
        
        # App should have lifespan context configured
        assert hasattr(app, 'lifespan') or hasattr(app.router, 'lifespan')
        
        # App should be properly configured
        assert isinstance(app, FastAPI)
        assert app.title == "Test Platform"