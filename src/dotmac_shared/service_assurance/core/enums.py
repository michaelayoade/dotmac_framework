"""Service Assurance enumeration types."""

from enum import Enum


class ProbeType(str, Enum):
    """Service probe type enumeration."""

    ICMP = "icmp"
    DNS = "dns"
    HTTP = "http"
    HTTPS = "https"
    TCP = "tcp"
    UDP = "udp"
    SNMP = "snmp"


class ProbeStatus(str, Enum):
    """Service probe status."""

    ENABLED = "enabled"
    DISABLED = "disabled"
    SUSPENDED = "suspended"
    ERROR = "error"


class AlarmSeverity(str, Enum):
    """Alarm severity levels."""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    WARNING = "warning"
    INFO = "info"
    CLEAR = "clear"


class AlarmStatus(str, Enum):
    """Alarm status enumeration."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    CLEARED = "cleared"
    SUPPRESSED = "suppressed"


class AlarmType(str, Enum):
    """Alarm type classification."""

    EQUIPMENT = "equipment"
    SYSTEM = "system"
    SERVICE = "service"
    PERFORMANCE = "performance"
    SECURITY = "security"
    ENVIRONMENT = "environment"


class EventType(str, Enum):
    """Event type enumeration."""

    SNMP_TRAP = "snmp_trap"
    SYSLOG = "syslog"
    PROBE = "probe"
    THRESHOLD = "threshold"
    CUSTOM = "custom"


class FlowType(str, Enum):
    """Flow data type enumeration."""

    NETFLOW = "netflow"
    SFLOW = "sflow"
    IPFIX = "ipfix"
    J_FLOW = "jflow"


class CollectorStatus(str, Enum):
    """Flow collector status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class SLAComplianceStatus(str, Enum):
    """SLA compliance status."""

    COMPLIANT = "compliant"
    VIOLATION = "violation"
    INSUFFICIENT_DATA = "insufficient_data"
    NO_POLICY = "no_policy"


class SuppressionStatus(str, Enum):
    """Alarm suppression status."""

    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ViolationType(str, Enum):
    """SLA violation type."""

    AVAILABILITY = "availability"
    LATENCY = "latency"
    COMBINED = "combined"
