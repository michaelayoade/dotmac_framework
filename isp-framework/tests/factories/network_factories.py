"""Factories for network-related test data."""

from datetime import date, datetime, timedelta
from uuid import uuid4
import factory
from faker import Faker

from .base import (
    BaseFactory,
    TenantMixin,
    TimestampMixin,
    AuditMixin,
)

fake = Faker()


class NetworkDeviceFactory(BaseFactory, TenantMixin, TimestampMixin, AuditMixin):
    """Factory for NetworkDevice test data."""
    
    class Meta:
        model = None
    
    # Device identification
    device_name = factory.LazyAttribute(lambda obj: f"{obj.device_type.upper()}-{fake.city()}-{fake.random_int(1, 99):02d}")
    device_type = "router"  # router, switch, access_point, modem, olt, onu
    
    # Network information
    ip_address = factory.LazyAttribute(lambda obj: fake.ipv4())
    mac_address = factory.LazyAttribute(lambda obj: fake.mac_address())
    management_ip = factory.LazyAttribute(lambda obj: fake.ipv4_private())
    
    # Hardware information
    vendor = factory.LazyAttribute(lambda obj: fake.random_element(["Cisco", "Juniper", "Ubiquiti", "Mikrotik", "Adtran"]))
    model = factory.LazyAttribute(lambda obj: f"{obj.vendor}-{fake.bothify('???####')}")
    serial_number = factory.LazyAttribute(lambda obj: fake.bothify("SN??????####"))
    firmware_version = factory.LazyAttribute(lambda obj: fake.bothify("#.#.#"))
    
    # SNMP configuration
    snmp_community = "public"
    snmp_version = "v2c"
    snmp_port = 161
    
    # Physical location
    site_name = factory.LazyAttribute(lambda obj: fake.city())
    rack_location = factory.LazyAttribute(lambda obj: f"Rack-{fake.random_int(1, 20)}")
    physical_address = factory.LazyAttribute(lambda obj: fake.address())
    
    # Geographic coordinates
    latitude = factory.LazyAttribute(lambda obj: fake.latitude())
    longitude = factory.LazyAttribute(lambda obj: fake.longitude())
    
    # Status and monitoring
    status = "online"  # online, offline, maintenance, error
    last_seen = factory.LazyFunction(lambda: datetime.utcnow() - timedelta(minutes=fake.random_int(1, 60)))
    uptime_seconds = factory.LazyAttribute(lambda obj: fake.random_int(3600, 31536000))  # 1 hour to 1 year
    
    # Performance metrics
    cpu_utilization = factory.LazyAttribute(lambda obj: fake.random_int(10, 80))
    memory_utilization = factory.LazyAttribute(lambda obj: fake.random_int(20, 90))
    temperature_celsius = factory.LazyAttribute(lambda obj: fake.random_int(25, 65))
    
    # Configuration
    config_backup_date = factory.LazyFunction(lambda: date.today() - timedelta(days=fake.random_int(1, 30)))
    config_hash = factory.LazyAttribute(lambda obj: fake.sha256()[:16])
    
    @classmethod
    def create_switch(cls, **kwargs):
        """Create a network switch."""
        device_data = kwargs.copy()
        device_data.update({
            'device_type': 'switch',
            'snmp_port': 161,
        })
        return cls.create(**device_data)
    
    @classmethod
    def create_access_point(cls, **kwargs):
        """Create a wireless access point."""
        device_data = kwargs.copy()
        device_data.update({
            'device_type': 'access_point',
            'vendor': fake.random_element(["Ubiquiti", "Aruba", "Cisco", "Ruckus"]),
        })
        return cls.create(**device_data)
    
    @classmethod
    def create_offline_device(cls, **kwargs):
        """Create an offline device."""
        device_data = kwargs.copy()
        device_data.update({
            'status': 'offline',
            'last_seen': datetime.utcnow() - timedelta(hours=fake.random_int(1, 48)),
            'cpu_utilization': 0,
            'memory_utilization': 0,
        })
        return cls.create(**device_data)


class NetworkInterfaceFactory(BaseFactory, TenantMixin, TimestampMixin):
    """Factory for NetworkInterface test data."""
    
    class Meta:
        model = None
    
    # Interface identification
    device_id = factory.LazyFunction(lambda: str(uuid4()))
    interface_name = factory.LazyAttribute(lambda obj: fake.random_element(["GigabitEthernet0/1", "FastEthernet0/24", "eth0", "wlan0"]))
    interface_type = factory.LazyAttribute(lambda obj: fake.random_element(["ethernet", "wireless", "fiber", "serial"]))
    
    # Interface configuration
    ip_address = factory.LazyAttribute(lambda obj: fake.ipv4() if fake.boolean() else None)
    subnet_mask = factory.LazyAttribute(lambda obj: fake.ipv4() if obj.ip_address else None)
    mac_address = factory.LazyAttribute(lambda obj: fake.mac_address())
    
    # Status and statistics
    admin_status = "up"  # up, down, testing
    operational_status = "up"  # up, down, testing, unknown
    speed_mbps = factory.LazyAttribute(lambda obj: fake.random_element([10, 100, 1000, 10000]))
    duplex = "full"  # full, half, auto
    
    # Traffic statistics
    bytes_in = factory.LazyAttribute(lambda obj: fake.random_int(1000000, 1000000000))
    bytes_out = factory.LazyAttribute(lambda obj: fake.random_int(1000000, 1000000000))
    packets_in = factory.LazyAttribute(lambda obj: fake.random_int(10000, 10000000))
    packets_out = factory.LazyAttribute(lambda obj: fake.random_int(10000, 10000000))
    errors_in = factory.LazyAttribute(lambda obj: fake.random_int(0, 100))
    errors_out = factory.LazyAttribute(lambda obj: fake.random_int(0, 100))
    
    # Last update
    last_updated = factory.LazyFunction(lambda: datetime.utcnow())
    
    @classmethod
    def create_down_interface(cls, **kwargs):
        """Create a down interface."""
        interface_data = kwargs.copy()
        interface_data.update({
            'admin_status': 'down',
            'operational_status': 'down',
            'bytes_in': 0,
            'bytes_out': 0,
            'packets_in': 0,
            'packets_out': 0,
        })
        return cls.create(**interface_data)


class NetworkMonitoringEventFactory(BaseFactory, TenantMixin, TimestampMixin):
    """Factory for NetworkMonitoringEvent test data."""
    
    class Meta:
        model = None
    
    # Event identification
    event_id = factory.LazyAttribute(lambda obj: fake.bothify("EVT-######"))
    device_id = factory.LazyFunction(lambda: str(uuid4()))
    
    # Event details
    event_type = factory.LazyAttribute(lambda obj: fake.random_element(["device_down", "device_up", "high_cpu", "interface_down", "config_change"]))
    severity = factory.LazyAttribute(lambda obj: fake.random_element(["info", "warning", "error", "critical"]))
    
    # Event timing
    event_time = factory.LazyFunction(lambda: datetime.utcnow() - timedelta(minutes=fake.random_int(1, 1440)))
    acknowledged = False
    acknowledged_by = None
    acknowledged_at = None
    resolved = factory.LazyAttribute(lambda obj: fake.boolean(chance_of_getting_true=70))
    resolved_at = factory.LazyAttribute(lambda obj: obj.event_time + timedelta(minutes=fake.random_int(5, 120)) if obj.resolved else None)
    
    # Event description
    title = factory.LazyAttribute(lambda obj: f"{obj.event_type.replace('_', ' ').title()} Alert")
    description = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=300))
    
    # Related data
    metric_name = factory.LazyAttribute(lambda obj: fake.random_element(["cpu_utilization", "memory_utilization", "interface_status", "ping_response"]))
    metric_value = factory.LazyAttribute(lambda obj: fake.random_int(0, 100))
    threshold_value = factory.LazyAttribute(lambda obj: fake.random_int(70, 95))
    
    @classmethod
    def create_critical_alert(cls, **kwargs):
        """Create a critical alert."""
        event_data = kwargs.copy()
        event_data.update({
            'severity': 'critical',
            'event_type': 'device_down',
            'acknowledged': False,
            'resolved': False,
            'title': 'Critical Device Failure',
        })
        return cls.create(**event_data)
    
    @classmethod
    def create_resolved_event(cls, **kwargs):
        """Create a resolved event."""
        event_data = kwargs.copy()
        event_time = datetime.utcnow() - timedelta(hours=fake.random_int(1, 24))
        event_data.update({
            'event_time': event_time,
            'acknowledged': True,
            'acknowledged_by': str(uuid4()),
            'acknowledged_at': event_time + timedelta(minutes=fake.random_int(1, 60)),
            'resolved': True,
            'resolved_at': event_time + timedelta(minutes=fake.random_int(30, 240)),
        })
        return cls.create(**event_data)


class NetworkTopologyFactory(BaseFactory, TenantMixin, TimestampMixin):
    """Factory for NetworkTopology test data."""
    
    class Meta:
        model = None
    
    # Topology identification
    topology_name = factory.LazyAttribute(lambda obj: f"Network-{fake.city()}")
    
    # Topology structure
    parent_device_id = factory.LazyFunction(lambda: str(uuid4()))
    child_device_id = factory.LazyFunction(lambda: str(uuid4()))
    connection_type = factory.LazyAttribute(lambda obj: fake.random_element(["ethernet", "fiber", "wireless", "vpn"]))
    
    # Connection details
    parent_interface = factory.LazyAttribute(lambda obj: fake.random_element(["GigabitEthernet0/1", "eth0", "wlan0"]))
    child_interface = factory.LazyAttribute(lambda obj: fake.random_element(["GigabitEthernet0/1", "eth0", "wlan0"]))
    
    # Discovery information
    discovered_via = factory.LazyAttribute(lambda obj: fake.random_element(["cdp", "lldp", "snmp", "manual"]))
    discovery_date = factory.LazyFunction(lambda: datetime.utcnow() - timedelta(days=fake.random_int(1, 365)))
    last_verified = factory.LazyFunction(lambda: datetime.utcnow() - timedelta(days=fake.random_int(1, 30)))
    
    # Status
    connection_status = "active"  # active, inactive, unknown
    is_redundant_path = factory.LazyAttribute(lambda obj: fake.boolean(chance_of_getting_true=20))


class VLANConfigurationFactory(BaseFactory, TenantMixin, TimestampMixin, AuditMixin):
    """Factory for VLAN configuration test data."""
    
    class Meta:
        model = None
    
    # VLAN identification
    vlan_id = factory.LazyAttribute(lambda obj: fake.random_int(1, 4094))
    vlan_name = factory.LazyAttribute(lambda obj: f"VLAN-{obj.vlan_id}")
    
    # VLAN configuration
    description = factory.LazyAttribute(lambda obj: fake.catch_phrase())
    subnet = factory.LazyAttribute(lambda obj: fake.ipv4_network())
    gateway_ip = factory.LazyAttribute(lambda obj: fake.ipv4())
    
    # VLAN type and purpose
    vlan_type = factory.LazyAttribute(lambda obj: fake.random_element(["data", "voice", "management", "guest"]))
    is_management_vlan = factory.LazyAttribute(lambda obj: obj.vlan_type == "management")
    
    # Associated devices
    device_id = factory.LazyFunction(lambda: str(uuid4()))
    assigned_interfaces = factory.LazyAttribute(lambda obj: [fake.random_element(["eth0", "eth1", "wlan0"]) for _ in range(fake.random_int(1, 5))])
    
    # Status
    is_active = True
    
    @classmethod
    def create_management_vlan(cls, **kwargs):
        """Create a management VLAN."""
        vlan_data = kwargs.copy()
        vlan_data.update({
            'vlan_id': 1,
            'vlan_name': 'MANAGEMENT',
            'vlan_type': 'management',
            'is_management_vlan': True,
            'description': 'Network Management VLAN',
        })
        return cls.create(**vlan_data)