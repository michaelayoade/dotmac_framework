"""
Tests for system monitoring functionality.
"""

from unittest.mock import MagicMock, patch

import pytest

from dotmac_benchmarking.system import SystemMonitor, get_process_info, snapshot


class TestSystemMonitoring:
    """Test system monitoring with mocked psutil."""

    @patch('dotmac_benchmarking.system.SYSTEM_AVAILABLE', True)
    @patch('dotmac_benchmarking.system.psutil')
    def test_snapshot(self, mock_psutil):
        """Test taking system snapshot."""
        # Setup mock psutil data
        mock_psutil.cpu_percent.return_value = 45.2
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_count.side_effect = lambda logical=False: 8 if logical else 4

        mock_memory = MagicMock()
        mock_memory.total = 8589934592  # 8GB
        mock_memory.available = 4294967296  # 4GB
        mock_memory.used = 4294967296  # 4GB
        mock_memory.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_swap = MagicMock()
        mock_swap.total = 2147483648  # 2GB
        mock_swap.used = 1073741824   # 1GB
        mock_swap.percent = 50.0
        mock_psutil.swap_memory.return_value = mock_swap

        mock_disk = MagicMock()
        mock_disk.total = 1099511627776  # 1TB
        mock_disk.used = 549755813888    # 500GB
        mock_disk.free = 549755813888    # 500GB
        mock_psutil.disk_usage.return_value = mock_disk

        mock_network = MagicMock()
        mock_network.bytes_sent = 1048576      # 1MB
        mock_network.bytes_recv = 2097152      # 2MB
        mock_network.packets_sent = 1000
        mock_network.packets_recv = 1500
        mock_psutil.net_io_counters.return_value = mock_network

        mock_psutil.getloadavg.return_value = (0.5, 0.8, 1.2)
        mock_psutil.boot_time.return_value = 1641024000.0

        result = snapshot()

        # Verify CPU metrics
        assert result["cpu_percent"] == 45.2
        assert result["cpu_count_physical"] == 4
        assert result["cpu_count_logical"] == 8
        assert result["load_avg_1m"] == 0.5
        assert result["load_avg_5m"] == 0.8
        assert result["load_avg_15m"] == 1.2

        # Verify memory metrics
        assert result["memory_total"] == 8589934592
        assert result["memory_available"] == 4294967296
        assert result["memory_used"] == 4294967296
        assert result["memory_percent"] == 50.0
        assert result["swap_total"] == 2147483648
        assert result["swap_used"] == 1073741824
        assert result["swap_percent"] == 50.0

        # Verify disk metrics
        assert result["disk_total"] == 1099511627776
        assert result["disk_used"] == 549755813888
        assert result["disk_free"] == 549755813888
        assert result["disk_usage"] == pytest.approx(50.0, abs=0.1)

        # Verify network metrics
        assert result["network_bytes_sent"] == 1048576
        assert result["network_bytes_recv"] == 2097152
        assert result["network_packets_sent"] == 1000
        assert result["network_packets_recv"] == 1500

        # Verify metadata
        assert "timestamp" in result
        assert result["boot_time"] == 1641024000.0

        # Verify psutil calls
        mock_psutil.cpu_percent.assert_called_with(interval=0.1)
        mock_psutil.disk_usage.assert_called_with('/')

    @patch('dotmac_benchmarking.system.SYSTEM_AVAILABLE', True)
    @patch('dotmac_benchmarking.system.psutil')
    def test_snapshot_no_load_avg(self, mock_psutil):
        """Test snapshot when load averages not available (Windows)."""
        # Setup basic mocks
        mock_psutil.cpu_percent.return_value = 25.0
        mock_psutil.cpu_count.return_value = 2
        mock_psutil.cpu_count.side_effect = lambda logical=False: 4 if logical else 2

        mock_memory = MagicMock()
        mock_memory.total = mock_memory.available = mock_memory.used = 1000
        mock_memory.percent = 10.0
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_swap = MagicMock()
        mock_swap.total = mock_swap.used = 500
        mock_swap.percent = 20.0
        mock_psutil.swap_memory.return_value = mock_swap

        mock_disk = MagicMock()
        mock_disk.total = mock_disk.used = mock_disk.free = 1000
        mock_psutil.disk_usage.return_value = mock_disk

        mock_network = MagicMock()
        mock_network.bytes_sent = mock_network.bytes_recv = 1000
        mock_network.packets_sent = mock_network.packets_recv = 100
        mock_psutil.net_io_counters.return_value = mock_network

        # getloadavg not available (raises AttributeError on Windows)
        mock_psutil.getloadavg.side_effect = AttributeError("Not available")
        mock_psutil.boot_time.return_value = 1641024000.0

        result = snapshot()

        # Load averages should be None
        assert result["load_avg_1m"] is None
        assert result["load_avg_5m"] is None
        assert result["load_avg_15m"] is None

        # Other metrics should still be available
        assert result["cpu_percent"] == 25.0

    @patch('dotmac_benchmarking.system.SYSTEM_AVAILABLE', False)
    def test_snapshot_no_psutil(self):
        """Test error when psutil is not available."""
        with pytest.raises(ImportError, match="System monitoring requires psutil"):
            snapshot()

    @patch('dotmac_benchmarking.system.SYSTEM_AVAILABLE', True)
    @patch('dotmac_benchmarking.system.psutil')
    def test_get_process_info_current(self, mock_psutil):
        """Test getting current process info."""
        mock_process = MagicMock()
        mock_process.as_dict.return_value = {
            'pid': 1234,
            'name': 'python',
            'status': 'running',
            'create_time': 1641024000.0,
            'cpu_percent': 15.5,
            'memory_percent': 2.3,
            'memory_info': MagicMock(rss=104857600, vms=209715200),
            'num_threads': 4,
            'num_fds': 32
        }
        mock_psutil.Process.return_value = mock_process

        result = get_process_info()

        assert result['pid'] == 1234
        assert result['name'] == 'python'
        assert result['status'] == 'running'
        assert result['cpu_percent'] == 15.5
        assert result['memory_percent'] == 2.3
        assert result['memory_rss'] == 104857600
        assert result['memory_vms'] == 209715200
        assert result['num_threads'] == 4
        assert result['num_fds'] == 32
        assert 'timestamp' in result

        # Verify Process was called without pid (current process)
        mock_psutil.Process.assert_called_with()

    @patch('dotmac_benchmarking.system.SYSTEM_AVAILABLE', True)
    @patch('dotmac_benchmarking.system.psutil')
    def test_get_process_info_specific_pid(self, mock_psutil):
        """Test getting specific process info."""
        mock_process = MagicMock()
        mock_process.as_dict.return_value = {
            'pid': 5678,
            'name': 'nginx',
            'status': 'sleeping',
            'create_time': 1641020000.0,
            'cpu_percent': 0.1,
            'memory_percent': 0.5,
            'memory_info': MagicMock(rss=52428800, vms=104857600),
            'num_threads': 1,
            'num_fds': 16
        }
        mock_psutil.Process.return_value = mock_process

        result = get_process_info(5678)

        assert result['pid'] == 5678
        assert result['name'] == 'nginx'

        # Verify Process was called with specific pid
        mock_psutil.Process.assert_called_with(5678)

    @patch('dotmac_benchmarking.system.SYSTEM_AVAILABLE', True)
    @patch('dotmac_benchmarking.system.psutil')
    def test_get_process_info_no_memory_info(self, mock_psutil):
        """Test process info when memory_info is not available."""
        mock_process = MagicMock()
        mock_process.as_dict.return_value = {
            'pid': 999,
            'name': 'test',
            'status': 'running',
            'create_time': 1641024000.0,
            'cpu_percent': 1.0,
            'memory_percent': 0.1,
            'memory_info': None,  # No memory info
            'num_threads': 1,
            'num_fds': 8
        }
        mock_psutil.Process.return_value = mock_process

        result = get_process_info(999)

        assert result['pid'] == 999
        assert 'memory_rss' not in result
        assert 'memory_vms' not in result

    @patch('dotmac_benchmarking.system.SYSTEM_AVAILABLE', False)
    def test_get_process_info_no_psutil(self):
        """Test error when psutil is not available."""
        with pytest.raises(ImportError, match="System monitoring requires psutil"):
            get_process_info()


class TestSystemMonitor:
    """Test SystemMonitor class."""

    @patch('dotmac_benchmarking.system.SYSTEM_AVAILABLE', True)
    @patch('dotmac_benchmarking.system.snapshot')
    def test_system_monitor_init(self, mock_snapshot):
        """Test SystemMonitor initialization."""
        monitor = SystemMonitor(history_size=50)
        
        assert monitor.history_size == 50
        assert monitor.history == []

    @patch('dotmac_benchmarking.system.SYSTEM_AVAILABLE', False)
    def test_system_monitor_no_psutil(self):
        """Test SystemMonitor error when psutil not available."""
        with pytest.raises(ImportError, match="System monitoring requires psutil"):
            SystemMonitor()

    @patch('dotmac_benchmarking.system.SYSTEM_AVAILABLE', True)
    @patch('dotmac_benchmarking.system.snapshot')
    def test_take_snapshot(self, mock_snapshot):
        """Test taking snapshots."""
        mock_snapshot.return_value = {
            'cpu_percent': 30.0,
            'memory_percent': 40.0,
            'timestamp': 1641024000.0
        }

        monitor = SystemMonitor(history_size=2)
        
        # Take first snapshot
        result = monitor.take_snapshot()
        
        assert result['cpu_percent'] == 30.0
        assert len(monitor.history) == 1

        # Take second snapshot
        mock_snapshot.return_value = {
            'cpu_percent': 35.0,
            'memory_percent': 45.0,
            'timestamp': 1641024001.0
        }
        
        result = monitor.take_snapshot()
        
        assert result['cpu_percent'] == 35.0
        assert len(monitor.history) == 2

        # Take third snapshot - should trim history
        mock_snapshot.return_value = {
            'cpu_percent': 40.0,
            'memory_percent': 50.0,
            'timestamp': 1641024002.0
        }
        
        result = monitor.take_snapshot()
        
        assert len(monitor.history) == 2  # Limited by history_size
        assert monitor.history[0]['cpu_percent'] == 35.0  # First one was removed
        assert monitor.history[1]['cpu_percent'] == 40.0  # Latest one

    @patch('dotmac_benchmarking.system.SYSTEM_AVAILABLE', True)
    @patch('dotmac_benchmarking.system.snapshot')  
    def test_get_history(self, mock_snapshot):
        """Test getting history."""
        monitor = SystemMonitor()
        
        mock_snapshot.return_value = {'cpu_percent': 25.0}
        monitor.take_snapshot()
        
        history = monitor.get_history()
        
        assert len(history) == 1
        assert history[0]['cpu_percent'] == 25.0
        
        # Should return a copy
        history.append({'fake': 'data'})
        assert len(monitor.get_history()) == 1

    @patch('dotmac_benchmarking.system.SYSTEM_AVAILABLE', True)
    @patch('dotmac_benchmarking.system.snapshot')
    def test_get_averages(self, mock_snapshot):
        """Test calculating averages."""
        monitor = SystemMonitor()
        
        # Add some snapshots
        snapshots = [
            {'cpu_percent': 20.0, 'memory_percent': 30.0, 'swap_percent': 10.0, 'disk_usage': 50.0},
            {'cpu_percent': 30.0, 'memory_percent': 40.0, 'swap_percent': 15.0, 'disk_usage': 55.0},
            {'cpu_percent': 40.0, 'memory_percent': 50.0, 'swap_percent': 20.0, 'disk_usage': 60.0}
        ]
        
        for snapshot_data in snapshots:
            mock_snapshot.return_value = snapshot_data
            monitor.take_snapshot()

        # Test all averages
        averages = monitor.get_averages()
        
        assert averages['avg_cpu_percent'] == 30.0  # (20+30+40)/3
        assert averages['avg_memory_percent'] == 40.0  # (30+40+50)/3
        assert averages['avg_swap_percent'] == 15.0  # (10+15+20)/3
        assert averages['avg_disk_usage'] == 55.0  # (50+55+60)/3

        # Test windowed averages
        windowed_averages = monitor.get_averages(window=2)
        
        assert windowed_averages['avg_cpu_percent'] == 35.0  # (30+40)/2
        assert windowed_averages['avg_memory_percent'] == 45.0  # (40+50)/2

    @patch('dotmac_benchmarking.system.SYSTEM_AVAILABLE', True)  
    @patch('dotmac_benchmarking.system.snapshot')
    def test_get_averages_empty_history(self, mock_snapshot):
        """Test averages with empty history."""
        monitor = SystemMonitor()
        
        averages = monitor.get_averages()
        
        assert averages == {}

    @patch('dotmac_benchmarking.system.SYSTEM_AVAILABLE', True)
    @patch('dotmac_benchmarking.system.snapshot')
    def test_get_averages_missing_fields(self, mock_snapshot):
        """Test averages with missing or None fields."""
        monitor = SystemMonitor()
        
        # Snapshot with some None values
        mock_snapshot.return_value = {
            'cpu_percent': 25.0,
            'memory_percent': None,  # Missing value
            'swap_percent': 10.0,
            # disk_usage missing entirely
        }
        
        monitor.take_snapshot()
        
        averages = monitor.get_averages()
        
        assert averages['avg_cpu_percent'] == 25.0
        assert averages['avg_swap_percent'] == 10.0
        assert 'avg_memory_percent' not in averages  # Skipped due to None
        assert 'avg_disk_usage' not in averages  # Missing field

    @patch('dotmac_benchmarking.system.SYSTEM_AVAILABLE', True)
    @patch('dotmac_benchmarking.system.snapshot')
    def test_clear_history(self, mock_snapshot):
        """Test clearing history."""
        monitor = SystemMonitor()
        
        mock_snapshot.return_value = {'cpu_percent': 25.0}
        monitor.take_snapshot()
        
        assert len(monitor.history) == 1
        
        monitor.clear_history()
        
        assert len(monitor.history) == 0