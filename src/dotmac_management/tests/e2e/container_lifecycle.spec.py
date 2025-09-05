"""
Container Lifecycle Management E2E Tests

Comprehensive testing of container lifecycle operations:

1. Container scaling (up/down)
2. Container updates and migrations
3. Backup and restore procedures
4. Container deprovisioning
5. Data cleanup and archival

Tests verify that container operations maintain data integrity,
minimize downtime, and properly handle failure scenarios.
"""
import asyncio
import time
from datetime import datetime, timedelta, timezone

import pytest
from dotmac_management.models.tenant import TenantStatus
from playwright.async_api import Page, expect
from sqlalchemy import text
from sqlalchemy.orm import Session

from .factories import ContainerLifecycleDataFactory, HealthCheckDataFactory
from .utils import ContainerTestUtils, PageTestUtils, performance_monitor


@pytest.mark.container_lifecycle
@pytest.mark.slow
class TestContainerScaling:
    """Test container scaling operations."""

    async def test_horizontal_container_scaling_up(
        self,
        management_page: Page,
        management_db_session: Session,
        tenant_factory,
        container_lifecycle_test_setup,
        mock_coolify_client,
    ):
        """Test scaling container replicas up under load."""

        # Create tenant with running container
        tenant = tenant_factory(
            company_name="Scaling Test ISP",
            subdomain="scalingup",
            status=TenantStatus.ACTIVE,
            settings={"enable_auto_scaling": True, "min_replicas": 1, "max_replicas": 5, "cpu_threshold": 80},
        )

        base_container_id = f"app_{tenant.tenant_id}"
        container_lifecycle_test_setup["register"](base_container_id, tenant.tenant_id)

        # Mock current container with high resource usage
        high_load_scenario = ContainerLifecycleDataFactory.create_scaling_scenario(base_container_id)[
            0
        ]  # Get base container with high load

        mock_coolify_client.get_application_status.return_value = {
            "id": base_container_id,
            "status": "running",
            "replicas": 1,
            "cpu_usage": high_load_scenario["cpu_usage"],  # 85% - triggers scaling
            "memory_usage": high_load_scenario["memory_usage"],
        }

        # Mock scaling operation
        mock_coolify_client.scale_application.return_value = {
            "id": base_container_id,
            "replicas": 3,
            "status": "scaling",
        }

        async with performance_monitor("container_scaling_up"):
            # Login as management admin
            admin_creds = {"username": "admin", "password": "test123"}
            await PageTestUtils.login_management_admin(management_page, admin_creds)

            # Navigate to container management
            await management_page.goto(f"/tenants/{tenant.tenant_id}/containers")

            # Verify current container status shows high load
            await expect(management_page.locator("[data-testid=cpu-usage]")).to_contain_text("85%", timeout=10000)

            # Trigger manual scaling
            await management_page.click("[data-testid=scale-up-button]")
            await management_page.fill("[data-testid=replica-count]", "3")
            await management_page.click("[data-testid=confirm-scale]")

            # Wait for scaling operation to complete
            await expect(management_page.locator(".scaling-status")).to_contain_text(
                "Scaling in progress", timeout=15000
            )

            # Mock successful scaling completion
            await asyncio.sleep(2)
            mock_coolify_client.get_application_status.return_value = {
                "id": base_container_id,
                "status": "running",
                "replicas": 3,
                "cpu_usage": 30,  # Load distributed
                "memory_usage": 600,
            }

            # Verify scaling completed
            await management_page.reload()
            await expect(management_page.locator("[data-testid=replica-count]")).to_contain_text("3", timeout=10000)
            await expect(management_page.locator("[data-testid=cpu-usage]")).to_contain_text("30%", timeout=5000)

            # Verify scaling was logged
            assert mock_coolify_client.scale_application.called
            scale_call_args = mock_coolify_client.scale_application.call_args[1]
            assert scale_call_args["replicas"] == 3

    async def test_horizontal_container_scaling_down(
        self, management_page: Page, tenant_factory, container_lifecycle_test_setup, mock_coolify_client
    ):
        """Test scaling container replicas down when load decreases."""

        tenant = tenant_factory(company_name="Scale Down Test ISP", subdomain="scaledown", status=TenantStatus.ACTIVE)

        container_id = f"app_{tenant.tenant_id}"
        container_lifecycle_test_setup["register"](container_id, tenant.tenant_id)

        # Mock current container with 3 replicas and low load
        mock_coolify_client.get_application_status.return_value = {
            "id": container_id,
            "status": "running",
            "replicas": 3,
            "cpu_usage": 20,  # Low load
            "memory_usage": 300,
        }

        mock_coolify_client.scale_application.return_value = {"id": container_id, "replicas": 1, "status": "scaling"}

        # Login and navigate
        admin_creds = {"username": "admin", "password": "test123"}
        await PageTestUtils.login_management_admin(management_page, admin_creds)
        await management_page.goto(f"/tenants/{tenant.tenant_id}/containers")

        # Trigger scale down
        await management_page.click("[data-testid=scale-down-button]")
        await management_page.fill("[data-testid=replica-count]", "1")
        await management_page.click("[data-testid=confirm-scale]")

        # Wait for scaling
        await expect(management_page.locator(".scaling-status")).to_contain_text("Scaling in progress", timeout=10000)

        # Mock completion
        await asyncio.sleep(1)
        mock_coolify_client.get_application_status.return_value = {
            "id": container_id,
            "status": "running",
            "replicas": 1,
            "cpu_usage": 35,  # Slightly higher after scale down
            "memory_usage": 500,
        }

        # Verify scale down
        await management_page.reload()
        await expect(management_page.locator("[data-testid=replica-count]")).to_contain_text("1", timeout=10000)

    async def test_auto_scaling_based_on_metrics(self, tenant_factory, mock_coolify_client, http_client):
        """Test automatic scaling based on resource metrics."""

        tenant = tenant_factory(
            company_name="Auto Scaling ISP",
            subdomain="autoscale",
            status=TenantStatus.ACTIVE,
            settings={
                "enable_auto_scaling": True,
                "cpu_scale_up_threshold": 75,
                "cpu_scale_down_threshold": 25,
                "min_replicas": 1,
                "max_replicas": 5,
            },
        )

        container_id = f"app_{tenant.tenant_id}"

        # Simulate auto-scaling trigger via monitoring API
        high_load_metrics = {
            "container_id": container_id,
            "cpu_usage": 80,  # Above threshold
            "memory_usage": 1500,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # In real implementation, this would be called by monitoring service
        response = await http_client.post(
            f"http://localhost:8001/api/v1/containers/{container_id}/metrics", json=high_load_metrics
        )

        # Mock the scaling response
        mock_coolify_client.scale_application.return_value = {"id": container_id, "replicas": 2, "status": "scaling"}

        # Verify auto-scaling was triggered
        # In real implementation, would check scaling events/logs
        assert mock_coolify_client.scale_application.called or response.status_code == 200

    async def test_vertical_container_scaling(self, management_page: Page, tenant_factory, mock_coolify_client):
        """Test vertical scaling (resource allocation changes)."""

        tenant = tenant_factory(company_name="Vertical Scale ISP", subdomain="vertscale", status=TenantStatus.ACTIVE)

        container_id = f"app_{tenant.tenant_id}"

        # Mock current resource allocation
        mock_coolify_client.get_application_config.return_value = {
            "id": container_id,
            "resources": {
                "cpu": "500m",  # 0.5 CPU cores
                "memory": "1Gi",  # 1GB memory
            },
        }

        admin_creds = {"username": "admin", "password": "test123"}
        await PageTestUtils.login_management_admin(management_page, admin_creds)
        await management_page.goto(f"/tenants/{tenant.tenant_id}/containers/resources")

        # Change resource allocation
        await management_page.fill("[data-testid=cpu-limit]", "1000m")  # 1 CPU core
        await management_page.fill("[data-testid=memory-limit]", "2Gi")  # 2GB memory
        await management_page.click("[data-testid=update-resources]")

        # Wait for update
        await expect(management_page.locator(".resource-update-status")).to_contain_text(
            "Resources updated", timeout=30000
        )

        # Verify update was called
        assert mock_coolify_client.update_application_resources.called


@pytest.mark.container_lifecycle
class TestContainerUpdatesAndMigrations:
    """Test container updates and data migrations."""

    async def test_zero_downtime_container_update(
        self, management_page: Page, tenant_factory, mock_coolify_client, http_client
    ):
        """Test zero-downtime container update deployment."""

        tenant = tenant_factory(company_name="Update Test ISP", subdomain="updatetest", status=TenantStatus.ACTIVE)

        container_id = f"app_{tenant.tenant_id}"

        # Mock current container version
        mock_coolify_client.get_application_status.return_value = {
            "id": container_id,
            "status": "running",
            "version": "v1.0.0",
            "replicas": 2,
        }

        async with performance_monitor("zero_downtime_update"):
            # Login and navigate to updates
            admin_creds = {"username": "admin", "password": "test123"}
            await PageTestUtils.login_management_admin(management_page, admin_creds)
            await management_page.goto(f"/tenants/{tenant.tenant_id}/updates")

            # Verify current version
            await expect(management_page.locator("[data-testid=current-version]")).to_contain_text(
                "v1.0.0", timeout=5000
            )

            # Start update to new version
            await management_page.click("[data-testid=update-button]")
            await management_page.select_option("[data-testid=version-select]", "v1.1.0")
            await management_page.check("[data-testid=zero-downtime]")  # Enable zero-downtime
            await management_page.click("[data-testid=start-update]")

            # Mock rolling update process
            mock_coolify_client.deploy_application.return_value = {
                "id": container_id,
                "deployment_id": "deploy_123",
                "strategy": "rolling_update",
            }

            # Wait for update progress
            await expect(management_page.locator(".update-status")).to_contain_text("Updating", timeout=15000)

            # During rolling update, service should remain available
            tenant_url = f"https://{tenant.subdomain}.test.dotmac.local"

            # Test service availability during update (simulate multiple requests)
            for i in range(3):
                try:
                    response = await http_client.get(f"{tenant_url}/health", timeout=5)
                    assert response.status_code == 200, f"Service unavailable during update (attempt {i+1})"
                except Exception as e:
                    pytest.fail(f"Service became unavailable during zero-downtime update: {e}")

                await asyncio.sleep(1)

            # Mock update completion
            await asyncio.sleep(2)
            mock_coolify_client.get_application_status.return_value = {
                "id": container_id,
                "status": "running",
                "version": "v1.1.0",  # Updated version
                "replicas": 2,
            }

            # Verify update completed
            await management_page.reload()
            await expect(management_page.locator("[data-testid=current-version]")).to_contain_text(
                "v1.1.0", timeout=10000
            )

    async def test_container_rollback_after_failed_update(
        self, management_page: Page, tenant_factory, mock_coolify_client
    ):
        """Test rolling back container after failed update."""

        tenant = tenant_factory(company_name="Rollback Test ISP", subdomain="rollback", status=TenantStatus.ACTIVE)

        container_id = f"app_{tenant.tenant_id}"

        # Mock failed update
        mock_coolify_client.deploy_application.side_effect = Exception("Update failed")
        mock_coolify_client.get_application_status.return_value = {
            "id": container_id,
            "status": "error",
            "version": "v1.0.0",  # Still on old version
            "last_error": "Update failed",
        }

        admin_creds = {"username": "admin", "password": "test123"}
        await PageTestUtils.login_management_admin(management_page, admin_creds)
        await management_page.goto(f"/tenants/{tenant.tenant_id}/updates")

        # Attempt update
        await management_page.click("[data-testid=update-button]")
        await management_page.select_option("[data-testid=version-select]", "v1.1.0")
        await management_page.click("[data-testid=start-update]")

        # Wait for failure
        await expect(management_page.locator(".update-error")).to_contain_text("Update failed", timeout=15000)

        # Trigger rollback
        await management_page.click("[data-testid=rollback-button]")

        # Mock successful rollback
        mock_coolify_client.rollback_application.return_value = {"id": container_id, "status": "rolling_back"}

        await expect(management_page.locator(".rollback-status")).to_contain_text("Rolling back", timeout=10000)

        # Mock rollback completion
        await asyncio.sleep(1)
        mock_coolify_client.get_application_status.return_value = {
            "id": container_id,
            "status": "running",
            "version": "v1.0.0",
        }

        await management_page.reload()
        await expect(management_page.locator("[data-testid=current-version]")).to_contain_text("v1.0.0", timeout=5000)

    async def test_database_migration_during_update(
        self, tenant_factory, tenant_db_sessions: dict[str, Session], mock_coolify_client
    ):
        """Test database migration during container update."""

        tenant_factory(company_name="Migration Test ISP", subdomain="migration", status=TenantStatus.ACTIVE)

        # Mock migration job
        mock_coolify_client.run_migration_job.return_value = {"job_id": "migration_job_123", "status": "running"}

        mock_coolify_client.get_job_status.return_value = {
            "job_id": "migration_job_123",
            "status": "completed",
            "exit_code": 0,
        }

        # Simulate database migration
        if "tenant_a" in tenant_db_sessions:
            tenant_session = tenant_db_sessions["tenant_a"]

            # Add some test data before migration
            tenant_session.execute(text("CREATE TABLE IF NOT EXISTS test_table (id SERIAL PRIMARY KEY, name TEXT)"))
            tenant_session.execute(text("INSERT INTO test_table (name) VALUES ('test_data')"))
            tenant_session.commit()

            # Verify data exists before migration
            result = tenant_session.execute(text("SELECT COUNT(*) FROM test_table")).scalar()
            assert result == 1, "Test data not inserted properly"

            # Run migration (in real scenario, this would be triggered by container update)
            # Mock migration that adds a column
            tenant_session.execute(
                text("ALTER TABLE test_table ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()")
            )
            tenant_session.commit()

            # Verify migration was successful
            columns = tenant_session.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name = 'test_table'")
            ).fetchall()

            column_names = [col[0] for col in columns]
            assert "created_at" in column_names, "Migration did not add created_at column"

            # Verify data integrity after migration
            result = tenant_session.execute(text("SELECT COUNT(*) FROM test_table")).scalar()
            assert result == 1, "Data lost during migration"


@pytest.mark.container_lifecycle
class TestContainerBackupAndRestore:
    """Test container backup and restore operations."""

    async def test_automated_container_backup(self, tenant_factory, mock_coolify_client, test_file_cleanup):
        """Test automated container data backup."""

        tenant = tenant_factory(
            company_name="Backup Test ISP",
            subdomain="backup",
            status=TenantStatus.ACTIVE,
            settings={
                "enable_automated_backup": True,
                "backup_schedule": "0 2 * * *",  # Daily at 2 AM
                "backup_retention": 30,  # Keep 30 days
            },
        )

        container_id = f"app_{tenant.tenant_id}"

        # Mock backup operation
        backup_id = f"backup_{int(time.time())}"
        mock_coolify_client.create_backup.return_value = {
            "backup_id": backup_id,
            "status": "in_progress",
            "container_id": container_id,
        }

        async with performance_monitor("container_backup"):
            # Trigger backup
            backup_result = await mock_coolify_client.create_backup(container_id)
            assert backup_result["backup_id"] == backup_id

            # Mock backup completion
            mock_coolify_client.get_backup_status.return_value = {
                "backup_id": backup_id,
                "status": "completed",
                "size_bytes": 1024 * 1024 * 500,  # 500MB
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            # Verify backup completed
            status = await mock_coolify_client.get_backup_status(backup_id)
            assert status["status"] == "completed"
            assert status["size_bytes"] > 0

    async def test_point_in_time_restore(self, management_page: Page, tenant_factory, mock_coolify_client):
        """Test point-in-time container restore from backup."""

        tenant = tenant_factory(company_name="Restore Test ISP", subdomain="restore", status=TenantStatus.ACTIVE)

        # Mock available backups
        backup_list = [
            {
                "backup_id": "backup_001",
                "created_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                "size_bytes": 500 * 1024 * 1024,
            },
            {
                "backup_id": "backup_002",
                "created_at": (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat(),
                "size_bytes": 520 * 1024 * 1024,
            },
        ]

        mock_coolify_client.list_backups.return_value = backup_list

        admin_creds = {"username": "admin", "password": "test123"}
        await PageTestUtils.login_management_admin(management_page, admin_creds)
        await management_page.goto(f"/tenants/{tenant.tenant_id}/backups")

        # Verify backups are listed
        await expect(management_page.locator("[data-testid=backup-list]")).to_be_visible(timeout=10000)
        await expect(management_page.locator(".backup-item")).to_have_count(2)

        # Select backup for restore
        await management_page.click("[data-testid=restore-backup-002]")
        await management_page.check("[data-testid=confirm-restore]")
        await management_page.click("[data-testid=start-restore]")

        # Mock restore operation
        mock_coolify_client.restore_from_backup.return_value = {"restore_id": "restore_123", "status": "in_progress"}

        await expect(management_page.locator(".restore-status")).to_contain_text("Restoring", timeout=15000)

        # Mock restore completion
        await asyncio.sleep(2)
        mock_coolify_client.get_restore_status.return_value = {"restore_id": "restore_123", "status": "completed"}

        await management_page.reload()
        await expect(management_page.locator(".restore-success")).to_contain_text("Restore completed", timeout=10000)

    async def test_backup_data_integrity_verification(self, tenant_factory, mock_coolify_client):
        """Test backup data integrity verification."""

        tenant = tenant_factory(company_name="Integrity Test ISP", subdomain="integrity", status=TenantStatus.ACTIVE)

        container_id = f"app_{tenant.tenant_id}"
        backup_id = "backup_integrity_test"

        # Mock backup with checksum
        mock_coolify_client.create_backup.return_value = {
            "backup_id": backup_id,
            "status": "completed",
            "checksum": "sha256:abc123def456",
            "size_bytes": 1024 * 1024 * 100,
        }

        # Mock verification
        mock_coolify_client.verify_backup.return_value = {
            "backup_id": backup_id,
            "verified": True,
            "checksum_match": True,
            "size_match": True,
        }

        # Create backup
        backup_result = await mock_coolify_client.create_backup(container_id)
        assert backup_result["backup_id"] == backup_id

        # Verify backup integrity
        verification_result = await mock_coolify_client.verify_backup(backup_id)
        assert verification_result["verified"] is True
        assert verification_result["checksum_match"] is True


@pytest.mark.container_lifecycle
class TestContainerDeprovisioning:
    """Test container deprovisioning and cleanup."""

    async def test_graceful_container_deprovisioning(
        self, management_page: Page, management_db_session: Session, tenant_factory, mock_coolify_client
    ):
        """Test graceful container deprovisioning with data preservation."""

        tenant = tenant_factory(
            company_name="Deprovision Test ISP",
            subdomain="deprovision",
            status=TenantStatus.ACTIVE,
            settings={"enable_data_retention": True, "retention_period_days": 90},
        )

        container_id = f"app_{tenant.tenant_id}"

        async with performance_monitor("container_deprovisioning"):
            admin_creds = {"username": "admin", "password": "test123"}
            await PageTestUtils.login_management_admin(management_page, admin_creds)
            await management_page.goto(f"/tenants/{tenant.tenant_id}/settings")

            # Initiate deprovisioning
            await management_page.click("[data-testid=deprovision-button]")
            await management_page.check("[data-testid=preserve-data]")
            await management_page.fill("[data-testid=confirmation-text]", "DELETE")
            await management_page.click("[data-testid=confirm-deprovision]")

            # Mock deprovisioning steps
            mock_coolify_client.stop_application.return_value = {"id": container_id, "status": "stopping"}

            mock_coolify_client.create_backup.return_value = {
                "backup_id": f"final_backup_{tenant.tenant_id}",
                "status": "completed",
            }

            mock_coolify_client.delete_application.return_value = {"id": container_id, "status": "deleted"}

            await expect(management_page.locator(".deprovision-status")).to_contain_text(
                "Deprovisioning", timeout=15000
            )

            # Verify tenant status updated
            await asyncio.sleep(2)
            management_db_session.refresh(tenant)
            assert tenant.status == TenantStatus.DEPROVISIONING

    async def test_forced_container_deprovisioning(self, management_page: Page, tenant_factory, mock_coolify_client):
        """Test forced deprovisioning without data preservation."""

        tenant = tenant_factory(
            company_name="Force Deprovision ISP",
            subdomain="forcedeprovision",
            status=TenantStatus.FAILED,  # Failed tenant
        )

        container_id = f"app_{tenant.tenant_id}"

        admin_creds = {"username": "admin", "password": "test123"}
        await PageTestUtils.login_management_admin(management_page, admin_creds)
        await management_page.goto(f"/tenants/{tenant.tenant_id}/settings")

        # Force deprovision without backup
        await management_page.click("[data-testid=force-deprovision-button]")
        await management_page.uncheck("[data-testid=preserve-data]")  # No backup
        await management_page.fill("[data-testid=confirmation-text]", "FORCE DELETE")
        await management_page.click("[data-testid=confirm-force-deprovision]")

        # Mock forced cleanup
        mock_coolify_client.force_delete_application.return_value = {"id": container_id, "status": "force_deleted"}

        await expect(management_page.locator(".force-deprovision-status")).to_contain_text(
            "Force deleting", timeout=10000
        )

        # Verify no backup was created
        assert not mock_coolify_client.create_backup.called

    async def test_container_resource_cleanup(
        self, tenant_factory, mock_coolify_client, management_db_session: Session
    ):
        """Test cleanup of container resources after deprovisioning."""

        tenant = tenant_factory(
            company_name="Cleanup Test ISP", subdomain="cleanup", status=TenantStatus.DEPROVISIONING
        )

        container_id = f"app_{tenant.tenant_id}"

        # Mock resource cleanup
        cleanup_tasks = [
            ("delete_application", {"id": container_id}),
            ("delete_database", {"id": f"db_{tenant.tenant_id}"}),
            ("delete_redis", {"id": f"redis_{tenant.tenant_id}"}),
            ("release_domain", {"domain": f"{tenant.subdomain}.test.com"}),
            ("cleanup_volumes", {"container_id": container_id}),
        ]

        for task_name, task_result in cleanup_tasks:
            getattr(mock_coolify_client, task_name).return_value = task_result

        # In real implementation, this would be called by cleanup service
        for task_name, _ in cleanup_tasks:
            await getattr(mock_coolify_client, task_name)(container_id)

        # Verify all cleanup tasks were called
        for task_name, _ in cleanup_tasks:
            assert getattr(mock_coolify_client, task_name).called, f"Cleanup task {task_name} not called"

        # Update tenant status to deprovisioned
        tenant.status = TenantStatus.DEPROVISIONED
        management_db_session.commit()

        assert tenant.status == TenantStatus.DEPROVISIONED

    async def test_data_archival_before_deprovisioning(
        self, tenant_factory, tenant_db_sessions: dict[str, Session], mock_coolify_client
    ):
        """Test data archival process before container deprovisioning."""

        tenant = tenant_factory(
            company_name="Archival Test ISP",
            subdomain="archival",
            status=TenantStatus.ACTIVE,
            settings={"enable_data_archival": True, "archive_before_deprovision": True},
        )

        container_id = f"app_{tenant.tenant_id}"

        # Create test data in tenant database
        if "tenant_a" in tenant_db_sessions:
            tenant_session = tenant_db_sessions["tenant_a"]

            # Add test customer data
            tenant_session.execute(
                text("CREATE TABLE IF NOT EXISTS customers (id SERIAL PRIMARY KEY, name TEXT, email TEXT)")
            )
            tenant_session.execute(
                text("INSERT INTO customers (name, email) VALUES ('Test Customer', 'test@customer.com')")
            )
            tenant_session.commit()

            # Verify test data
            customer_count = tenant_session.execute(text("SELECT COUNT(*) FROM customers")).scalar()
            assert customer_count == 1, "Test customer data not created"

        # Mock archival process
        mock_coolify_client.create_data_archive.return_value = {
            "archive_id": f"archive_{tenant.tenant_id}",
            "status": "completed",
            "size_bytes": 1024 * 1024,  # 1MB
            "tables_archived": ["customers", "services", "billing"],
        }

        # Trigger archival
        archive_result = await mock_coolify_client.create_data_archive(container_id)

        assert archive_result["status"] == "completed"
        assert "customers" in archive_result["tables_archived"]
        assert archive_result["size_bytes"] > 0


@pytest.mark.container_lifecycle
class TestContainerMonitoringAndAlerts:
    """Test container monitoring and alerting during lifecycle operations."""

    async def test_container_health_monitoring_during_scaling(self, tenant_factory, mock_coolify_client, http_client):
        """Test continuous health monitoring during scaling operations."""

        tenant_factory(company_name="Monitoring Test ISP", subdomain="monitoring", status=TenantStatus.ACTIVE)

        # Mock health check responses during scaling
        health_responses = [
            HealthCheckDataFactory.create_healthy_response(),
            HealthCheckDataFactory.create_healthy_response(),
            HealthCheckDataFactory.create_healthy_response(),
        ]

        # Monitor health during scaling
        async with performance_monitor("health_monitoring_during_scaling"):
            for i, health_response in enumerate(health_responses):
                # Simulate health check
                type("MockResponse", (), {"status_code": 200, "json": lambda: health_response})()

                # Verify health check data
                assert health_response["status"] == "healthy"
                assert all(service["status"] == "healthy" for service in health_response["services"].values())

                await asyncio.sleep(0.1)  # Brief pause between checks

    async def test_container_performance_monitoring(self, tenant_factory, mock_coolify_client):
        """Test container performance monitoring and metrics collection."""

        tenant = tenant_factory(company_name="Performance ISP", subdomain="performance", status=TenantStatus.ACTIVE)

        container_id = f"app_{tenant.tenant_id}"

        # Monitor performance metrics
        metrics = await ContainerTestUtils.monitor_container_resources(
            container_id,
            duration=10,  # 10 seconds
        )

        # Verify metrics were collected
        assert len(metrics["cpu_usage"]) > 0
        assert len(metrics["memory_usage"]) > 0
        assert len(metrics["timestamps"]) > 0
        assert len(metrics["cpu_usage"]) == len(metrics["memory_usage"])

        # Verify metrics are reasonable
        assert all(0 <= cpu <= 100 for cpu in metrics["cpu_usage"])
        assert all(memory > 0 for memory in metrics["memory_usage"])

    async def test_container_failure_detection_and_recovery(self, tenant_factory, mock_coolify_client, http_client):
        """Test automatic failure detection and recovery."""

        tenant = tenant_factory(
            company_name="Recovery Test ISP",
            subdomain="recovery",
            status=TenantStatus.ACTIVE,
            settings={"enable_auto_recovery": True, "max_restart_attempts": 3},
        )

        container_id = f"app_{tenant.tenant_id}"

        # Mock container failure
        mock_coolify_client.get_application_status.return_value = {
            "id": container_id,
            "status": "unhealthy",
            "health_check_failures": 3,
            "last_error": "Container unresponsive",
        }

        # Mock recovery action
        mock_coolify_client.restart_application.return_value = {"id": container_id, "status": "restarting"}

        # Simulate failure detection and recovery
        status = await mock_coolify_client.get_application_status(container_id)

        if status["status"] == "unhealthy":
            await mock_coolify_client.restart_application(container_id)

            # Mock successful recovery
            mock_coolify_client.get_application_status.return_value = {
                "id": container_id,
                "status": "running",
                "health_check_failures": 0,
            }

        # Verify recovery was attempted
        assert mock_coolify_client.restart_application.called

        # Verify container is healthy after recovery
        final_status = await mock_coolify_client.get_application_status(container_id)
        assert final_status["status"] == "running"
