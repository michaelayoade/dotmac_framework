"""Shared enums to eliminate duplication across the ISP framework."""

from enum import Enum


class CommonStatus(str, Enum):
    """Common status values used across multiple modules."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    FAILED = "failed"
    MAINTENANCE = "maintenance"


class EntityLifecycle(str, Enum):
    """Standard entity lifecycle states."""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ProcessingStatus(str, Enum):
    """Status values for processing workflows."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    ON_HOLD = "on_hold"


class PaymentStatus(str, Enum):
    """Payment and financial status values."""

    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    DISPUTED = "disputed"


class AlertSeverity(str, Enum):
    """Alert and notification severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    INFORMATIONAL = "informational"


class Priority(str, Enum):
    """Priority levels for tasks, tickets, etc."""

    LOW = "low"
    MEDIUM = "medium"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class NetworkStatus(str, Enum):
    """Network-related status values."""

    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    UNREACHABLE = "unreachable"
    UNKNOWN = "unknown"


class DeliveryStatus(str, Enum):
    """Delivery and notification status values."""

    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    READ = "read"
    CLICKED = "clicked"


class AuditAction(str, Enum):
    """Audit log action types."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    APPROVE = "approve"
    REJECT = "reject"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"


class ComplianceStatus(str, Enum):
    """Compliance and regulatory status values."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    AT_RISK = "at_risk"
    UNDER_REVIEW = "under_review"
    UNKNOWN = "unknown"


class ContractStatus(str, Enum):
    """Contract and agreement status values."""

    DRAFT = "draft"
    PENDING_SIGNATURE = "pending_signature"
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    SUSPENDED = "suspended"
    RENEWED = "renewed"


# TicketStatus moved to dotmac_shared.ticketing package
# Use: from dotmac_shared.ticketing import TicketStatus


class UserStatus(str, Enum):
    """User account status values."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_VERIFICATION = "pending_verification"
    SUSPENDED = "suspended"
    LOCKED = "locked"
    PASSWORD_RESET_REQUIRED = "password_reset_required"  # noqa: S105 - status label
    DELETED = "deleted"


class ServiceStatus(str, Enum):
    """Service provisioning status values."""

    PENDING = "pending"
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEPROVISIONING = "deprovisioning"
    DEPROVISIONED = "deprovisioned"
    FAILED = "failed"
    MAINTENANCE = "maintenance"


class OrderStatus(str, Enum):
    """Order processing status values."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RETURNED = "returned"
    REFUNDED = "refunded"


class InventoryMovementType(str, Enum):
    """Inventory movement types."""

    RECEIPT = "receipt"
    ISSUE = "issue"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"
    RETURN = "return"
    LOST = "lost"
    FOUND = "found"
    DAMAGED = "damaged"
    DISPOSED = "disposed"


class WorkOrderStatus(str, Enum):
    """Work order status values."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class InstallationStatus(str, Enum):
    """Installation and deployment status values."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLBACK = "rollback"


class CommunicationChannel(str, Enum):
    """Communication channel types."""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"
    PHONE = "phone"
    IN_APP = "in_app"


class ContactType(str, Enum):
    """Contact relationship types."""

    PRIMARY = "primary"
    BILLING = "billing"
    TECHNICAL = "technical"
    EMERGENCY = "emergency"
    SALES = "sales"
    SUPPORT = "support"
    LEGAL = "legal"
    MANAGER = "manager"


class AddressType(str, Enum):
    """Address types for locations."""

    BILLING = "billing"
    SHIPPING = "shipping"
    SERVICE = "service"
    INSTALLATION = "installation"
    CORPORATE = "corporate"
    BRANCH = "branch"
    WAREHOUSE = "warehouse"


class DeviceType(str, Enum):
    """Network device types."""

    ROUTER = "router"
    SWITCH = "switch"
    FIREWALL = "firewall"
    ACCESS_POINT = "access_point"
    MODEM = "modem"
    SERVER = "server"
    UPS = "ups"
    ANTENNA = "antenna"
    AMPLIFIER = "amplifier"
    SPLITTER = "splitter"


class MetricType(str, Enum):
    """Metric and measurement types."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    RATE = "rate"
    PERCENTAGE = "percentage"


class ReportFormat(str, Enum):
    """Report output formats."""

    PDF = "pdf"
    CSV = "csv"
    XLSX = "xlsx"
    JSON = "json"
    HTML = "html"
    XML = "xml"


class TimeZone(str, Enum):
    """Common timezone values."""

    UTC = "UTC"
    EST = "America/New_York"
    CST = "America/Chicago"
    MST = "America/Denver"
    PST = "America/Los_Angeles"
    GMT = "Europe/London"


class Currency(str, Enum):
    """Currency codes."""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CAD = "CAD"
    AUD = "AUD"
    JPY = "JPY"


class Country(str, Enum):
    """Common country codes."""

    US = "US"
    CA = "CA"
    GB = "GB"
    AU = "AU"
    DE = "DE"
    FR = "FR"
    JP = "JP"


class LanguageCode(str, Enum):
    """Language codes for localization."""

    EN = "en"
    ES = "es"
    FR = "fr"
    DE = "de"
    IT = "it"
    PT = "pt"
    JA = "ja"
    ZH = "zh"
