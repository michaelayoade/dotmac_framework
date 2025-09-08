"""
Comprehensive tests for monitoring integrations.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from dotmac.platform.monitoring.integrations import (
    GrafanaIntegration,
    IntegrationConfig,
    IntegrationManager,
    IntegrationStatus,
    MetricData,
    MonitoringIntegration,
    PrometheusIntegration,
    SigNozIntegration,
)


class TestIntegrationConfig:
    """Test IntegrationConfig dataclass."""

    def test_integration_config_defaults(self):
        """Test default values are set correctly."""
        config = IntegrationConfig(name="test", endpoint="http://test.com")
        
        assert config.name == "test"
        assert config.endpoint == "http://test.com"
        assert config.api_key is None
        assert config.timeout == 30
        assert config.retry_count == 3
        assert config.enabled is True
        assert config.metadata == {}

    def test_integration_config_custom_values(self):
        """Test custom values are set correctly."""
        metadata = {"custom": "value"}
        config = IntegrationConfig(
            name="custom_test",
            endpoint="https://custom.com",
            api_key="secret_key",
            timeout=60,
            retry_count=5,
            enabled=False,
            metadata=metadata
        )
        
        assert config.name == "custom_test"
        assert config.endpoint == "https://custom.com"
        assert config.api_key == "secret_key"
        assert config.timeout == 60
        assert config.retry_count == 5
        assert config.enabled is False
        assert config.metadata == metadata


class TestMetricData:
    """Test MetricData dataclass."""

    def test_metric_data_defaults(self):
        """Test default values are set correctly."""
        metric = MetricData(name="test_metric", value=42.5)
        
        assert metric.name == "test_metric"
        assert metric.value == 42.5
        assert isinstance(metric.timestamp, datetime)
        assert metric.labels == {}
        assert metric.metadata == {}

    def test_metric_data_custom_values(self):
        """Test custom values are set correctly."""
        timestamp = datetime.utcnow()
        labels = {"service": "api", "env": "prod"}
        metadata = {"source": "benchmark"}
        
        metric = MetricData(
            name="response_time",
            value=150,
            timestamp=timestamp,
            labels=labels,
            metadata=metadata
        )
        
        assert metric.name == "response_time"
        assert metric.value == 150
        assert metric.timestamp == timestamp
        assert metric.labels == labels
        assert metric.metadata == metadata


class TestMonitoringIntegration:
    """Test base MonitoringIntegration class."""

    class MockIntegration(MonitoringIntegration):
        """Mock implementation for testing."""
        
        def __init__(self, config, health_check_result=True):
            super().__init__(config)
            self._health_check_result = health_check_result
            self._metrics_sent = []
            self._alerts_sent = []

        async def health_check(self) -> bool:
            return self._health_check_result

        async def send_metrics(self, metrics) -> bool:
            self._metrics_sent.extend(metrics)
            return True

        async def send_alert(self, alert_data) -> bool:
            self._alerts_sent.append(alert_data)
            return True

    def test_initialization(self):
        """Test integration initialization."""
        config = IntegrationConfig(name="test", endpoint="http://test.com")
        integration = self.MockIntegration(config)
        
        assert integration.config == config
        assert integration.status == IntegrationStatus.PENDING
        assert integration.client is None

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful integration initialization."""
        config = IntegrationConfig(name="test", endpoint="http://test.com")
        integration = self.MockIntegration(config, health_check_result=True)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value = mock_client_instance
            
            result = await integration.initialize()
            
            assert result is True
            assert integration.status == IntegrationStatus.ACTIVE
            assert integration.client is not None

    @pytest.mark.asyncio
    async def test_initialize_health_check_failure(self):
        """Test initialization failure due to health check."""
        config = IntegrationConfig(name="test", endpoint="http://test.com")
        integration = self.MockIntegration(config, health_check_result=False)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value = mock_client_instance
            
            result = await integration.initialize()
            
            assert result is False
            assert integration.status == IntegrationStatus.ERROR

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test integration shutdown."""
        config = IntegrationConfig(name="test", endpoint="http://test.com")
        integration = self.MockIntegration(config)
        
        # Mock client
        mock_client = AsyncMock()
        integration.client = mock_client
        
        await integration.shutdown()
        
        mock_client.aclose.assert_called_once()
        assert integration.client is None
        assert integration.status == IntegrationStatus.INACTIVE

    def test_get_headers_without_api_key(self):
        """Test header generation without API key."""
        config = IntegrationConfig(name="test", endpoint="http://test.com")
        integration = self.MockIntegration(config)
        
        headers = integration._get_headers()
        
        expected_headers = {"Content-Type": "application/json"}
        assert headers == expected_headers

    def test_get_headers_with_api_key(self):
        """Test header generation with API key."""
        config = IntegrationConfig(
            name="test", 
            endpoint="http://test.com", 
            api_key="secret_key"
        )
        integration = self.MockIntegration(config)
        
        headers = integration._get_headers()
        
        expected_headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer secret_key"
        }
        assert headers == expected_headers

    @pytest.mark.asyncio
    async def test_make_request_success(self):
        """Test successful HTTP request."""
        config = IntegrationConfig(name="test", endpoint="http://test.com")
        integration = self.MockIntegration(config)
        
        # Mock client and response
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.content = b'{"status": "ok"}'
        mock_client.request.return_value = mock_response
        integration.client = mock_client
        
        result = await integration._make_request("GET", "/api/health")
        
        assert result == {"status": "ok"}
        mock_client.request.assert_called_once_with(
            "GET", 
            "http://test.com/api/health", 
            json=None
        )

    @pytest.mark.asyncio
    async def test_make_request_no_client(self):
        """Test request when client is not initialized."""
        config = IntegrationConfig(name="test", endpoint="http://test.com")
        integration = self.MockIntegration(config)
        
        result = await integration._make_request("GET", "/api/health")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_make_request_with_retries(self):
        """Test request retry logic."""
        config = IntegrationConfig(name="test", endpoint="http://test.com", retry_count=2)
        integration = self.MockIntegration(config)
        
        # Mock client that fails first time, succeeds second time
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.content = b'{"status": "ok"}'
        
        # First call fails, second succeeds
        mock_client.request.side_effect = [
            httpx.HTTPStatusError("Server Error", request=Mock(), response=Mock()),
            mock_response
        ]
        integration.client = mock_client
        
        with patch('asyncio.sleep'):  # Mock sleep to speed up test
            result = await integration._make_request("GET", "/api/health")
        
        assert result == {"status": "ok"}
        assert mock_client.request.call_count == 2


class TestSigNozIntegration:
    """Test SigNoz integration implementation."""

    def test_initialization(self):
        """Test SigNoz integration initialization."""
        config = IntegrationConfig(name="signoz", endpoint="http://signoz.com")
        integration = SigNozIntegration(config)
        
        assert integration.config == config
        assert integration.status == IntegrationStatus.PENDING

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful SigNoz health check."""
        config = IntegrationConfig(name="signoz", endpoint="http://signoz.com")
        integration = SigNozIntegration(config)
        
        with patch.object(integration, '_make_request') as mock_request:
            mock_request.return_value = {"status": "ok"}
            
            result = await integration.health_check()
            
            assert result is True
            mock_request.assert_called_once_with("GET", "/api/v1/health")

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test SigNoz health check failure."""
        config = IntegrationConfig(name="signoz", endpoint="http://signoz.com")
        integration = SigNozIntegration(config)
        
        with patch.object(integration, '_make_request') as mock_request:
            mock_request.return_value = {"status": "error"}
            
            result = await integration.health_check()
            
            assert result is False

    @pytest.mark.asyncio
    async def test_send_metrics_success(self):
        """Test successful metric sending to SigNoz."""
        config = IntegrationConfig(name="signoz", endpoint="http://signoz.com")
        integration = SigNozIntegration(config)
        
        metrics = [
            MetricData(name="cpu_usage", value=75.5, labels={"host": "server1"}),
            MetricData(name="memory_usage", value=60.2, labels={"host": "server1"})
        ]
        
        with patch.object(integration, '_make_request') as mock_request:
            mock_request.return_value = {"success": True}
            
            result = await integration.send_metrics(metrics)
            
            assert result is True
            mock_request.assert_called_once()
            
            # Verify payload structure
            args, kwargs = mock_request.call_args
            assert args[0] == "POST"
            assert args[1] == "/api/v1/metrics"
            assert "metrics" in args[2]
            assert len(args[2]["metrics"]) == 2

    @pytest.mark.asyncio
    async def test_send_alert_success(self):
        """Test successful alert sending to SigNoz."""
        config = IntegrationConfig(name="signoz", endpoint="http://signoz.com")
        integration = SigNozIntegration(config)
        
        alert_data = {
            "alert_name": "High CPU Usage",
            "severity": "critical",
            "message": "CPU usage is above 90%"
        }
        
        with patch.object(integration, '_make_request') as mock_request:
            mock_request.return_value = {"success": True}
            
            result = await integration.send_alert(alert_data)
            
            assert result is True
            mock_request.assert_called_once_with("POST", "/api/v1/alerts", alert_data)


class TestPrometheusIntegration:
    """Test Prometheus integration implementation."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful Prometheus health check."""
        config = IntegrationConfig(name="prometheus", endpoint="http://prometheus.com")
        integration = PrometheusIntegration(config)
        
        with patch.object(integration, '_make_request') as mock_request:
            mock_request.return_value = {"status": "healthy"}
            
            result = await integration.health_check()
            
            assert result is True
            mock_request.assert_called_once_with("GET", "/-/healthy")

    @pytest.mark.asyncio
    async def test_send_metrics_success(self):
        """Test successful metric sending to Prometheus."""
        config = IntegrationConfig(name="prometheus", endpoint="http://prometheus.com")
        integration = PrometheusIntegration(config)
        
        # Mock client
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        integration.client = mock_client
        
        metrics = [
            MetricData(name="cpu_usage", value=75.5, labels={"host": "server1"}),
            MetricData(name="memory_usage", value=60.2, labels={"host": "server2"})
        ]
        
        result = await integration.send_metrics(metrics)
        
        assert result is True
        mock_client.post.assert_called_once()
        
        # Verify the call arguments
        args, kwargs = mock_client.post.call_args
        assert "prometheus.com/metrics/job/dotmac" in args[0]
        assert kwargs["headers"]["Content-Type"] == "text/plain"
        assert "cpu_usage" in kwargs["content"]
        assert "memory_usage" in kwargs["content"]


class TestGrafanaIntegration:
    """Test Grafana integration implementation."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful Grafana health check."""
        config = IntegrationConfig(name="grafana", endpoint="http://grafana.com")
        integration = GrafanaIntegration(config)
        
        with patch.object(integration, '_make_request') as mock_request:
            mock_request.return_value = {"database": "ok", "version": "8.0"}
            
            result = await integration.health_check()
            
            assert result is True
            mock_request.assert_called_once_with("GET", "/api/health")

    @pytest.mark.asyncio
    async def test_send_metrics_as_annotations(self):
        """Test sending metrics as Grafana annotations."""
        config = IntegrationConfig(name="grafana", endpoint="http://grafana.com")
        integration = GrafanaIntegration(config)
        
        metrics = [
            MetricData(name="deployment", value=1, labels={"version": "v1.2.3"}),
        ]
        
        with patch.object(integration, '_make_request') as mock_request:
            mock_request.return_value = {"id": 1}
            
            result = await integration.send_metrics(metrics)
            
            assert result is True
            mock_request.assert_called_once()
            
            # Verify annotation payload
            args, kwargs = mock_request.call_args
            assert args[0] == "POST"
            assert args[1] == "/api/annotations"
            annotation = args[2]
            assert "deployment: 1" in annotation["text"]
            assert "version" in annotation["tags"]

    @pytest.mark.asyncio
    async def test_send_alert_as_annotation(self):
        """Test sending alert as Grafana annotation."""
        config = IntegrationConfig(name="grafana", endpoint="http://grafana.com")
        integration = GrafanaIntegration(config)
        
        alert_data = {
            "id": "alert_123",
            "message": "System overload detected",
            "severity": "critical"
        }
        
        with patch.object(integration, '_make_request') as mock_request:
            mock_request.return_value = {"id": 1}
            
            result = await integration.send_alert(alert_data)
            
            assert result is True
            mock_request.assert_called_once()
            
            # Verify annotation payload
            args, kwargs = mock_request.call_args
            assert args[0] == "POST"
            assert args[1] == "/api/annotations"
            annotation = args[2]
            assert annotation["text"] == "System overload detected"
            assert "alert" in annotation["tags"]
            assert "critical" in annotation["tags"]
            assert annotation["alertId"] == "alert_123"


class TestIntegrationManager:
    """Test IntegrationManager functionality."""

    def test_initialization(self):
        """Test integration manager initialization."""
        manager = IntegrationManager()
        
        assert manager.integrations == {}
        assert manager.logger is not None

    @pytest.mark.asyncio
    async def test_add_integration_success(self):
        """Test successful integration addition."""
        manager = IntegrationManager()
        
        config = IntegrationConfig(name="test", endpoint="http://test.com")
        integration = Mock()
        integration.config = config
        integration.initialize = AsyncMock(return_value=True)
        
        result = await manager.add_integration(integration)
        
        assert result is True
        assert "test" in manager.integrations
        assert manager.integrations["test"] == integration
        integration.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_integration_failure(self):
        """Test integration addition failure."""
        manager = IntegrationManager()
        
        config = IntegrationConfig(name="test", endpoint="http://test.com")
        integration = Mock()
        integration.config = config
        integration.initialize = AsyncMock(return_value=False)
        
        result = await manager.add_integration(integration)
        
        assert result is False
        assert "test" not in manager.integrations

    @pytest.mark.asyncio
    async def test_remove_integration_success(self):
        """Test successful integration removal."""
        manager = IntegrationManager()
        
        # Add integration first
        integration = Mock()
        integration.shutdown = AsyncMock()
        manager.integrations["test"] = integration
        
        result = await manager.remove_integration("test")
        
        assert result is True
        assert "test" not in manager.integrations
        integration.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_integration_not_found(self):
        """Test integration removal when integration doesn't exist."""
        manager = IntegrationManager()
        
        result = await manager.remove_integration("nonexistent")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast_metrics(self):
        """Test broadcasting metrics to all integrations."""
        manager = IntegrationManager()
        
        # Setup mock integrations
        integration1 = Mock()
        integration1.status = IntegrationStatus.ACTIVE
        integration1.send_metrics = AsyncMock(return_value=True)
        
        integration2 = Mock()
        integration2.status = IntegrationStatus.ACTIVE
        integration2.send_metrics = AsyncMock(return_value=False)
        
        integration3 = Mock()
        integration3.status = IntegrationStatus.ERROR
        integration3.send_metrics = AsyncMock()
        
        manager.integrations = {
            "integration1": integration1,
            "integration2": integration2,
            "integration3": integration3
        }
        
        metrics = [MetricData(name="test", value=42)]
        results = await manager.broadcast_metrics(metrics)
        
        # Verify results
        assert results["integration1"] is True
        assert results["integration2"] is False
        assert results["integration3"] is False  # Not active, so False
        
        # Verify calls
        integration1.send_metrics.assert_called_once_with(metrics)
        integration2.send_metrics.assert_called_once_with(metrics)
        integration3.send_metrics.assert_not_called()  # Not active

    @pytest.mark.asyncio
    async def test_broadcast_alert(self):
        """Test broadcasting alerts to all integrations."""
        manager = IntegrationManager()
        
        # Setup mock integrations
        integration1 = Mock()
        integration1.status = IntegrationStatus.ACTIVE
        integration1.send_alert = AsyncMock(return_value=True)
        
        integration2 = Mock()
        integration2.status = IntegrationStatus.INACTIVE
        integration2.send_alert = AsyncMock()
        
        manager.integrations = {
            "integration1": integration1,
            "integration2": integration2
        }
        
        alert_data = {"message": "Test alert"}
        results = await manager.broadcast_alert(alert_data)
        
        # Verify results
        assert results["integration1"] is True
        assert results["integration2"] is False  # Not active
        
        # Verify calls
        integration1.send_alert.assert_called_once_with(alert_data)
        integration2.send_alert.assert_not_called()

    def test_get_integration_status(self):
        """Test getting status of all integrations."""
        manager = IntegrationManager()
        
        integration1 = Mock()
        integration1.status = IntegrationStatus.ACTIVE
        
        integration2 = Mock()
        integration2.status = IntegrationStatus.ERROR
        
        manager.integrations = {
            "integration1": integration1,
            "integration2": integration2
        }
        
        status = manager.get_integration_status()
        
        assert status == {
            "integration1": IntegrationStatus.ACTIVE,
            "integration2": IntegrationStatus.ERROR
        }

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        """Test health check for all integrations."""
        manager = IntegrationManager()
        
        # Setup mock integrations
        integration1 = Mock()
        integration1.status = IntegrationStatus.ACTIVE
        integration1.health_check = AsyncMock(return_value=True)
        
        integration2 = Mock()
        integration2.status = IntegrationStatus.ERROR
        integration2.health_check = AsyncMock(return_value=False)
        
        manager.integrations = {
            "integration1": integration1,
            "integration2": integration2
        }
        
        results = await manager.health_check_all()
        
        # Verify results
        assert results["integration1"] is True
        assert results["integration2"] is False
        
        # Verify calls
        integration1.health_check.assert_called_once()
        integration2.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_all(self):
        """Test shutting down all integrations."""
        manager = IntegrationManager()
        
        # Setup mock integrations
        integration1 = Mock()
        integration1.shutdown = AsyncMock()
        
        integration2 = Mock()
        integration2.shutdown = AsyncMock()
        
        manager.integrations = {
            "integration1": integration1,
            "integration2": integration2
        }
        
        await manager.shutdown_all()
        
        # Verify calls
        integration1.shutdown.assert_called_once()
        integration2.shutdown.assert_called_once()
        
        # Verify integrations are cleared
        assert manager.integrations == {}