"""
Contract tests for SNMP device monitoring integration.

Validates that the SNMP device simulator provides consistent
API contracts for network monitoring functionality.
"""

import pytest
import requests
from typing import List, Dict, Any


@pytest.mark.contract
@pytest.mark.network_monitoring
def test_devices_endpoint_contract():
    """
    Contract Test: /devices endpoint returns valid device list.
    
    Validates:
    1. Response structure is consistent
    2. Device objects have required fields
    3. Data types are correct
    """
    # Given: SNMP simulator is running
    base_url = "http://localhost:8161"
    
    # When: We request device list
    response = requests.get(f"{base_url}/devices")
    
    # Then: Should return valid device list
    assert response.status_code == 200
    devices = response.json()
    
    # Contract: Should return list of devices
    assert isinstance(devices, list)
    assert len(devices) > 0
    
    # Contract: Each device should have required fields
    required_fields = [
        'device_id', 'ip', 'type', 'status', 'uptime',
        'bandwidth_in', 'bandwidth_out'
    ]
    
    for device in devices:
        for field in required_fields:
            assert field in device, f"Device missing required field: {field}"
        
        # Contract: Field types should be correct
        assert isinstance(device['device_id'], str)
        assert isinstance(device['ip'], str)
        assert device['type'] in ['router', 'switch', 'ont', 'olt']
        assert device['status'] in ['online', 'offline']
        assert isinstance(device['uptime'], int)
        assert isinstance(device['bandwidth_in'], int)
        assert isinstance(device['bandwidth_out'], int)
        
        # Contract: IP addresses should be valid format
        ip_parts = device['ip'].split('.')
        assert len(ip_parts) == 4
        for part in ip_parts:
            assert 0 <= int(part) <= 255


@pytest.mark.contract
@pytest.mark.network_monitoring
def test_device_metrics_endpoint_contract():
    """
    Contract Test: /device/{device_id}/metrics endpoint returns valid metrics.
    
    Validates metrics data structure and content for individual devices.
    """
    base_url = "http://localhost:8161"
    
    # Given: We have a list of devices
    devices_response = requests.get(f"{base_url}/devices")
    assert devices_response.status_code == 200
    devices = devices_response.json()
    assert len(devices) > 0
    
    # When: We request metrics for first device
    device_id = devices[0]['device_id']
    metrics_response = requests.get(f"{base_url}/device/{device_id}/metrics")
    
    # Then: Should return valid metrics
    assert metrics_response.status_code == 200
    metrics = metrics_response.json()
    
    # Contract: Metrics should have required structure
    required_fields = ['device_id', 'cpu_usage', 'memory_usage', 'interface_stats']
    for field in required_fields:
        assert field in metrics, f"Metrics missing required field: {field}"
    
    # Contract: Device ID should match request
    assert metrics['device_id'] == device_id
    
    # Contract: Usage values should be valid percentages
    assert 0 <= metrics['cpu_usage'] <= 100
    assert 0 <= metrics['memory_usage'] <= 100
    
    # Contract: Interface stats should have correct structure
    interface_stats = metrics['interface_stats']
    interface_required_fields = ['bytes_in', 'bytes_out', 'packets_in', 'packets_out']
    
    for field in interface_required_fields:
        assert field in interface_stats, f"Interface stats missing: {field}"
        assert isinstance(interface_stats[field], int)
        assert interface_stats[field] >= 0


@pytest.mark.contract
@pytest.mark.network_monitoring
def test_snmp_device_consistency():
    """
    Contract Test: Device data is consistent across multiple requests.
    
    Validates that device information remains stable and doesn't
    change unexpectedly between requests.
    """
    base_url = "http://localhost:8161"
    
    # Given: We make multiple requests for device list
    responses = []
    for _ in range(3):
        response = requests.get(f"{base_url}/devices")
        assert response.status_code == 200
        responses.append(response.json())
    
    # Then: Device count should be consistent
    device_counts = [len(devices) for devices in responses]
    assert all(count == device_counts[0] for count in device_counts), \
        "Device count is inconsistent across requests"
    
    # And: Device IDs should be consistent
    device_ids_sets = [set(device['device_id'] for device in devices) for devices in responses]
    assert all(ids == device_ids_sets[0] for ids in device_ids_sets), \
        "Device IDs are inconsistent across requests"
    
    # And: Device types should be stable
    for i in range(len(responses[0])):
        device_types = [response[i]['type'] for response in responses]
        assert all(device_type == device_types[0] for device_type in device_types), \
            f"Device {i} type is inconsistent across requests"


@pytest.mark.contract
@pytest.mark.performance_baseline
def test_snmp_endpoint_response_times():
    """
    Performance Contract Test: SNMP endpoints meet response time requirements.
    
    Validates that network monitoring API endpoints respond within
    acceptable time limits for real-time monitoring.
    """
    import time
    
    base_url = "http://localhost:8161"
    max_response_time = 2.0  # 2 seconds max for network monitoring
    
    # Test device list endpoint performance
    start_time = time.time()
    response = requests.get(f"{base_url}/devices")
    devices_response_time = time.time() - start_time
    
    assert response.status_code == 200
    assert devices_response_time < max_response_time, \
        f"Devices endpoint took {devices_response_time:.3f}s (max: {max_response_time}s)"
    
    # Test device metrics endpoint performance
    devices = response.json()
    if devices:
        device_id = devices[0]['device_id']
        
        start_time = time.time()
        metrics_response = requests.get(f"{base_url}/device/{device_id}/metrics")
        metrics_response_time = time.time() - start_time
        
        assert metrics_response.status_code == 200
        assert metrics_response_time < max_response_time, \
            f"Metrics endpoint took {metrics_response_time:.3f}s (max: {max_response_time}s)"


@pytest.mark.contract
@pytest.mark.ai_safety
def test_snmp_error_handling_contract():
    """
    AI Safety Contract Test: SNMP endpoints handle errors gracefully.
    
    Validates that AI-generated or modified code properly handles
    error conditions and invalid requests.
    """
    base_url = "http://localhost:8161"
    
    # Test invalid device ID
    invalid_device_response = requests.get(f"{base_url}/device/invalid-device-id/metrics")
    
    # Contract: Should handle invalid device gracefully
    # Either return 404 or return error response with proper structure
    if invalid_device_response.status_code == 200:
        # If it returns 200, should have consistent error structure
        error_data = invalid_device_response.json()
        assert isinstance(error_data, dict)
        # Could return empty metrics or error indication
    else:
        # Or return appropriate HTTP error code
        assert invalid_device_response.status_code in [404, 400]
    
    # Test malformed requests (if applicable)
    # For this simple API, we mainly test that it doesn't crash
    
    # Contract: API should remain responsive after error
    health_response = requests.get(f"{base_url}/devices")
    assert health_response.status_code == 200


@pytest.mark.contract
@pytest.mark.data_safety
def test_snmp_data_validation_contract():
    """
    Data Safety Contract Test: SNMP data meets validation requirements.
    
    Ensures that network monitoring data is within expected ranges
    and meets ISP operational requirements.
    """
    base_url = "http://localhost:8161"
    
    # Get devices and their metrics
    devices_response = requests.get(f"{base_url}/devices")
    assert devices_response.status_code == 200
    devices = devices_response.json()
    
    for device in devices:
        # Get metrics for each device
        metrics_response = requests.get(f"{base_url}/device/{device['device_id']}/metrics")
        assert metrics_response.status_code == 200
        metrics = metrics_response.json()
        
        # Contract: Bandwidth values should be realistic for ISP equipment
        # Assuming values are in bits per second
        max_realistic_bandwidth = 100_000_000_000  # 100 Gbps
        assert device['bandwidth_in'] <= max_realistic_bandwidth
        assert device['bandwidth_out'] <= max_realistic_bandwidth
        
        # Contract: Interface packet counts should be non-negative
        interface_stats = metrics['interface_stats']
        assert interface_stats['packets_in'] >= 0
        assert interface_stats['packets_out'] >= 0
        assert interface_stats['bytes_in'] >= 0
        assert interface_stats['bytes_out'] >= 0
        
        # Contract: CPU and memory should be realistic percentages
        assert 0 <= metrics['cpu_usage'] <= 100
        assert 0 <= metrics['memory_usage'] <= 100
        
        # Contract: Uptime should be positive
        assert device['uptime'] > 0