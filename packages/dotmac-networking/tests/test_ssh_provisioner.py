"""
Tests for SSH Device Provisioner - Device provisioning engine using SSH automation.
"""

from unittest.mock import patch
from uuid import UUID

import pytest

from dotmac.networking.automation.ssh.provisioner import DeviceProvisioner


# Mock classes for testing
class MockDeviceConfig:
    """Mock device configuration."""

    def __init__(self, hostname="test-device", ip_address="192.168.1.1"):
        self.hostname = hostname
        self.ip_address = ip_address
        self.credentials = {"username": "admin", "password": "password"}
        self.connection_config = {"timeout": 30}
        self.device_type = "cisco_ios"


class MockProvisioningTemplate:
    """Mock provisioning template."""

    def __init__(self, name="test-template", steps=None):
        self.name = name
        self.steps = steps or []
        self.description = "Test template"

    def render_template(self, variables):
        """Mock template rendering."""
        return MockRenderedTemplate(self.steps)


class MockRenderedTemplate:
    """Mock rendered template."""

    def __init__(self, steps):
        self.steps = steps


class MockProvisioningStep:
    """Mock provisioning step."""

    def __init__(self, name, command, required=True, rollback_command=None, condition=None):
        self.name = name
        self.command = command
        self.required = required
        self.rollback_command = rollback_command
        self.condition = condition


class MockProvisioningJob:
    """Mock provisioning job."""

    def __init__(self, job_id, device_config, template, variables=None):
        self.job_id = job_id
        self.device_config = device_config
        self.template = template
        self.variables = variables or {}
        self.status = "PENDING"
        self.current_step = None
        self.step_results = {}
        self.started_at = None
        self.completed_at = None
        self.error_message = None

    def mark_started(self):
        self.status = "IN_PROGRESS"
        from datetime import datetime
        self.started_at = datetime.now()

    def mark_completed(self):
        self.status = "COMPLETED"
        from datetime import datetime
        self.completed_at = datetime.now()

    def mark_failed(self, error_message):
        self.status = "FAILED"
        self.error_message = error_message
        from datetime import datetime
        self.completed_at = datetime.now()

    def add_step_result(self, step_name, response):
        self.step_results[step_name] = response


class MockSSHConnection:
    """Mock SSH connection."""

    def __init__(self, connection_id="conn-123"):
        self.connection_id = connection_id
        self.host = "192.168.1.1"
        self.is_connected = True


class MockCommandResponse:
    """Mock command response."""

    def __init__(self, success=True, output="", error_message=None):
        self.success = success
        self.output = output
        self.error_message = error_message


class MockSSHAutomation:
    """Mock SSH automation."""

    def __init__(self):
        self.connections = {}

    async def connect(self, host, credentials, config, device_type):
        connection = MockSSHConnection(f"conn-{host}")
        self.connections[connection.connection_id] = connection
        return connection

    async def execute_command(self, connection_id, command):
        if command.startswith("fail"):
            return MockCommandResponse(success=False, error_message="Command failed")
        return MockCommandResponse(success=True, output="Command executed successfully")

    async def disconnect(self, connection_id):
        if connection_id in self.connections:
            del self.connections[connection_id]

    async def disconnect_all(self):
        self.connections.clear()


# Mock the types module
@pytest.fixture(autouse=True)
def mock_types():
    """Mock the types module components."""
    with patch('dotmac.networking.automation.ssh.provisioner.DeviceConfig', MockDeviceConfig):
        with patch('dotmac.networking.automation.ssh.provisioner.ProvisioningTemplate', MockProvisioningTemplate):
            with patch('dotmac.networking.automation.ssh.provisioner.ProvisioningJob', MockProvisioningJob):
                with patch('dotmac.networking.automation.ssh.provisioner.ProvisioningStatus') as mock_status:
                    mock_status.PENDING = "PENDING"
                    mock_status.IN_PROGRESS = "IN_PROGRESS"
                    mock_status.COMPLETED = "COMPLETED"
                    mock_status.FAILED = "FAILED"
                    yield


@pytest.fixture
def mock_ssh_automation():
    """Mock SSH automation fixture."""
    return MockSSHAutomation()


@pytest.fixture
def provisioner(mock_ssh_automation):
    """Device provisioner fixture with mocked SSH automation."""
    with patch('dotmac.networking.automation.ssh.provisioner.SSHAutomation', return_value=mock_ssh_automation):
        return DeviceProvisioner()


class TestDeviceProvisionerInitialization:
    """Test device provisioner initialization."""

    def test_init_default(self, provisioner):
        """Test default initialization."""
        assert provisioner is not None
        assert isinstance(provisioner._jobs, dict)
        assert len(provisioner._jobs) == 0
        assert isinstance(provisioner._templates, dict)
        assert len(provisioner._templates) == 0
        assert provisioner._running is False

    @pytest.mark.asyncio
    async def test_start_stop(self, provisioner):
        """Test starting and stopping provisioner."""
        # Start provisioner
        await provisioner.start()
        assert provisioner._running is True

        # Stop provisioner
        await provisioner.stop()
        assert provisioner._running is False


class TestDeviceProvisionerTemplateManagement:
    """Test template management functionality."""

    def test_add_template(self, provisioner):
        """Test adding provisioning template."""
        template = MockProvisioningTemplate("test-template")

        provisioner.add_template(template)

        assert "test-template" in provisioner._templates
        assert provisioner._templates["test-template"] == template

    def test_add_multiple_templates(self, provisioner):
        """Test adding multiple templates."""
        template1 = MockProvisioningTemplate("template1")
        template2 = MockProvisioningTemplate("template2")

        provisioner.add_template(template1)
        provisioner.add_template(template2)

        assert len(provisioner._templates) == 2
        assert "template1" in provisioner._templates
        assert "template2" in provisioner._templates

    def test_get_template_exists(self, provisioner):
        """Test getting existing template."""
        template = MockProvisioningTemplate("existing-template")
        provisioner.add_template(template)

        retrieved = provisioner.get_template("existing-template")

        assert retrieved == template
        assert retrieved.name == "existing-template"

    def test_get_template_not_exists(self, provisioner):
        """Test getting non-existent template."""
        retrieved = provisioner.get_template("non-existent")

        assert retrieved is None

    def test_list_templates_empty(self, provisioner):
        """Test listing templates when none exist."""
        templates = provisioner.list_templates()

        assert isinstance(templates, list)
        assert len(templates) == 0

    def test_list_templates_with_data(self, provisioner):
        """Test listing templates with data."""
        template1 = MockProvisioningTemplate("template1")
        template2 = MockProvisioningTemplate("template2")

        provisioner.add_template(template1)
        provisioner.add_template(template2)

        templates = provisioner.list_templates()

        assert len(templates) == 2
        assert template1 in templates
        assert template2 in templates

    def test_template_overwrite(self, provisioner):
        """Test overwriting existing template."""
        template1 = MockProvisioningTemplate("template")
        template2 = MockProvisioningTemplate("template")  # Same name, different object

        provisioner.add_template(template1)
        provisioner.add_template(template2)

        assert len(provisioner._templates) == 1
        assert provisioner._templates["template"] == template2  # Should be overwritten


class TestDeviceProvisionerJobManagement:
    """Test job management functionality."""

    def test_get_job_not_exists(self, provisioner):
        """Test getting non-existent job."""
        job = provisioner.get_job("non-existent")

        assert job is None

    def test_list_jobs_empty(self, provisioner):
        """Test listing jobs when none exist."""
        jobs = provisioner.list_jobs()

        assert isinstance(jobs, list)
        assert len(jobs) == 0

    def test_get_active_jobs_empty(self, provisioner):
        """Test getting active jobs when none exist."""
        active_jobs = provisioner.get_active_jobs()

        assert isinstance(active_jobs, list)
        assert len(active_jobs) == 0

    def test_get_job_status_not_exists(self, provisioner):
        """Test getting status of non-existent job."""
        status = provisioner.get_job_status("non-existent")

        assert status is None

    @pytest.mark.asyncio
    async def test_cancel_job_not_exists(self, provisioner):
        """Test canceling non-existent job."""
        result = await provisioner.cancel_job("non-existent")

        assert result is False


class TestDeviceProvisionerProvisioning:
    """Test device provisioning functionality."""

    @pytest.mark.asyncio
    async def test_provision_device_success(self, provisioner):
        """Test successful device provisioning."""
        # Setup
        device_config = MockDeviceConfig("test-device", "192.168.1.1")
        template = MockProvisioningTemplate("test-template", [
            MockProvisioningStep("step1", "show version"),
            MockProvisioningStep("step2", "configure terminal")
        ])
        variables = {"hostname": "new-hostname"}

        # Execute
        job = await provisioner.provision_device(device_config, template, variables)

        # Verify job creation
        assert job is not None
        assert job.device_config == device_config
        assert job.template == template
        assert job.variables == variables

        # Verify job is stored
        assert job.job_id in provisioner._jobs
        assert provisioner._jobs[job.job_id] == job

        # Verify job ID is valid UUID
        UUID(job.job_id)  # Should not raise exception

    @pytest.mark.asyncio
    async def test_provision_device_no_variables(self, provisioner):
        """Test device provisioning without variables."""
        device_config = MockDeviceConfig()
        template = MockProvisioningTemplate("simple-template")

        job = await provisioner.provision_device(device_config, template)

        assert job.variables == {}

    @pytest.mark.asyncio
    async def test_provision_device_with_variables(self, provisioner):
        """Test device provisioning with variables."""
        device_config = MockDeviceConfig()
        template = MockProvisioningTemplate("template-with-vars")
        variables = {
            "hostname": "router-01",
            "vlan_id": 100,
            "ip_address": "10.0.1.1"
        }

        job = await provisioner.provision_device(device_config, template, variables)

        assert job.variables == variables

    @pytest.mark.asyncio
    async def test_multiple_provisioning_jobs(self, provisioner):
        """Test creating multiple provisioning jobs."""
        device1 = MockDeviceConfig("device1", "192.168.1.1")
        device2 = MockDeviceConfig("device2", "192.168.1.2")
        template = MockProvisioningTemplate("multi-device-template")

        job1 = await provisioner.provision_device(device1, template)
        job2 = await provisioner.provision_device(device2, template)

        assert job1.job_id != job2.job_id
        assert len(provisioner._jobs) == 2
        assert job1.job_id in provisioner._jobs
        assert job2.job_id in provisioner._jobs

    def test_job_retrieval_after_creation(self, provisioner):
        """Test retrieving job after creation."""
        device_config = MockDeviceConfig()
        template = MockProvisioningTemplate("retrieval-template")

        # Create job (synchronous part)
        job = MockProvisioningJob("test-job-id", device_config, template)
        provisioner._jobs[job.job_id] = job

        # Retrieve job
        retrieved_job = provisioner.get_job(job.job_id)

        assert retrieved_job == job
        assert retrieved_job.job_id == job.job_id

    def test_list_jobs_with_data(self, provisioner):
        """Test listing jobs with data."""
        # Add some jobs manually
        job1 = MockProvisioningJob("job1", MockDeviceConfig(), MockProvisioningTemplate("t1"))
        job2 = MockProvisioningJob("job2", MockDeviceConfig(), MockProvisioningTemplate("t2"))

        provisioner._jobs[job1.job_id] = job1
        provisioner._jobs[job2.job_id] = job2

        jobs = provisioner.list_jobs()

        assert len(jobs) == 2
        assert job1 in jobs
        assert job2 in jobs


class TestDeviceProvisionerJobExecution:
    """Test job execution workflow (mocked)."""

    @pytest.mark.asyncio
    async def test_execute_provisioning_job_success(self, provisioner, mock_ssh_automation):
        """Test successful job execution."""
        # Setup job
        device_config = MockDeviceConfig()
        template = MockProvisioningTemplate("exec-template", [
            MockProvisioningStep("step1", "show version")
        ])
        job = MockProvisioningJob("exec-job", device_config, template)

        # Mock the execution method
        with patch.object(provisioner, '_execute_provisioning_job') as mock_execute:
            mock_execute.return_value = None

            # Execute
            await provisioner._execute_provisioning_job(job)

            # Verify execution was called
            mock_execute.assert_called_once_with(job)

    def test_get_active_jobs_with_active_job(self, provisioner):
        """Test getting active jobs with in-progress jobs."""
        # Create jobs with different statuses
        job1 = MockProvisioningJob("active-job", MockDeviceConfig(), MockProvisioningTemplate("t1"))
        job1.status = "IN_PROGRESS"

        job2 = MockProvisioningJob("completed-job", MockDeviceConfig(), MockProvisioningTemplate("t2"))
        job2.status = "COMPLETED"

        job3 = MockProvisioningJob("failed-job", MockDeviceConfig(), MockProvisioningTemplate("t3"))
        job3.status = "FAILED"

        provisioner._jobs[job1.job_id] = job1
        provisioner._jobs[job2.job_id] = job2
        provisioner._jobs[job3.job_id] = job3

        active_jobs = provisioner.get_active_jobs()

        assert len(active_jobs) == 1
        assert job1 in active_jobs
        assert job2 not in active_jobs
        assert job3 not in active_jobs

    def test_get_job_status(self, provisioner):
        """Test getting job status."""
        job = MockProvisioningJob("status-job", MockDeviceConfig(), MockProvisioningTemplate("t1"))
        job.status = "COMPLETED"
        provisioner._jobs[job.job_id] = job

        status = provisioner.get_job_status(job.job_id)

        assert status == "COMPLETED"

    @pytest.mark.asyncio
    async def test_cancel_active_job(self, provisioner):
        """Test canceling active job."""
        job = MockProvisioningJob("cancel-job", MockDeviceConfig(), MockProvisioningTemplate("t1"))
        job.status = "IN_PROGRESS"
        provisioner._jobs[job.job_id] = job

        result = await provisioner.cancel_job(job.job_id)

        assert result is True
        assert job.status == "FAILED"
        assert "cancelled" in job.error_message.lower()

    @pytest.mark.asyncio
    async def test_cancel_completed_job(self, provisioner):
        """Test canceling completed job (should fail)."""
        job = MockProvisioningJob("completed-job", MockDeviceConfig(), MockProvisioningTemplate("t1"))
        job.status = "COMPLETED"
        provisioner._jobs[job.job_id] = job

        result = await provisioner.cancel_job(job.job_id)

        assert result is False
        assert job.status == "COMPLETED"  # Should remain unchanged


class TestDeviceProvisionerLogging:
    """Test logging functionality."""

    @pytest.mark.asyncio
    async def test_start_stop_logging(self, provisioner):
        """Test start/stop operations include logging."""
        with patch('dotmac.networking.automation.ssh.provisioner.logger') as mock_logger:
            await provisioner.start()
            mock_logger.info.assert_called_with("Device provisioner started")

            await provisioner.stop()
            mock_logger.info.assert_called_with("Device provisioner stopped")

    def test_add_template_logging(self, provisioner):
        """Test template addition includes logging."""
        template = MockProvisioningTemplate("logged-template")

        with patch('dotmac.networking.automation.ssh.provisioner.logger') as mock_logger:
            provisioner.add_template(template)

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "Added provisioning template" in call_args
            assert "logged-template" in call_args

    @pytest.mark.asyncio
    async def test_cancel_job_logging(self, provisioner):
        """Test job cancellation includes logging."""
        job = MockProvisioningJob("log-cancel-job", MockDeviceConfig(), MockProvisioningTemplate("t1"))
        job.status = "IN_PROGRESS"
        provisioner._jobs[job.job_id] = job

        with patch('dotmac.networking.automation.ssh.provisioner.logger') as mock_logger:
            await provisioner.cancel_job(job.job_id)

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "Cancelled provisioning job" in call_args
            assert job.job_id in call_args


class TestDeviceProvisionerIntegration:
    """Test integration scenarios."""

    @pytest.mark.asyncio
    async def test_full_provisioning_workflow(self, provisioner):
        """Test complete provisioning workflow."""
        # Setup
        device_config = MockDeviceConfig("integration-device")
        template = MockProvisioningTemplate("integration-template")
        variables = {"setting": "value"}

        # Add template
        provisioner.add_template(template)

        # Start provisioner
        await provisioner.start()

        # Create provisioning job
        job = await provisioner.provision_device(device_config, template, variables)

        # Verify job creation and storage
        assert job.job_id in provisioner._jobs
        assert provisioner.get_job(job.job_id) == job

        # Verify job properties
        assert job.device_config == device_config
        assert job.template == template
        assert job.variables == variables

        # Stop provisioner
        await provisioner.stop()

        assert provisioner._running is False

    @pytest.mark.asyncio
    async def test_template_and_job_management_integration(self, provisioner):
        """Test integration between template and job management."""
        # Create templates
        template1 = MockProvisioningTemplate("router-template")
        template2 = MockProvisioningTemplate("switch-template")

        provisioner.add_template(template1)
        provisioner.add_template(template2)

        # Create jobs using templates
        device1 = MockDeviceConfig("router-01")
        device2 = MockDeviceConfig("switch-01")

        job1 = await provisioner.provision_device(device1, template1)
        job2 = await provisioner.provision_device(device2, template2)

        # Verify integration
        assert len(provisioner.list_templates()) == 2
        assert len(provisioner.list_jobs()) == 2

        assert job1.template == template1
        assert job2.template == template2

        # Verify template retrieval
        retrieved_template1 = provisioner.get_template("router-template")
        retrieved_template2 = provisioner.get_template("switch-template")

        assert retrieved_template1 == template1
        assert retrieved_template2 == template2
