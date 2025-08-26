"""FreeRADIUS integration database models."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
    BigInteger,
    Index,
, timezone)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from dotmac_isp.shared.database.base import TenantModel
from dotmac_isp.shared.database.base import StatusMixin, AuditMixin


class RadiusUserType(str, Enum):
    """RADIUS user types."""

    CUSTOMER = "customer"
    DEVICE = "device"
    ADMIN = "admin"
    SERVICE = "service"


class RadiusClientType(str, Enum):
    """RADIUS client (NAS) types."""

    NAS = "nas"
    SWITCH = "switch"
    ROUTER = "router"
    ACCESS_POINT = "access_point"
    CONCENTRATOR = "concentrator"
    FIREWALL = "firewall"


class SessionStatus(str, Enum):
    """RADIUS session status."""

    ACTIVE = "active"
    STOPPED = "stopped"
    INTERIM = "interim"
    UNKNOWN = "unknown"


class AccountingStatus(str, Enum):
    """RADIUS accounting status."""

    START = "start"
    INTERIM_UPDATE = "interim_update"
    STOP = "stop"
    ACCOUNTING_ON = "accounting_on"
    ACCOUNTING_OFF = "accounting_off"


class AttributeOperator(str, Enum):
    """RADIUS attribute operators."""

    EQUAL = "="
    NOT_EQUAL = "!="
    LESS_THAN = "<="
    GREATER_THAN = ">="
    REGEX_MATCH = "=~"
    REGEX_NOT_MATCH = "!~"
    ADD = "+="
    SET = ":="


class RadiusUser(TenantModel, StatusMixin, AuditMixin):
    """RADIUS user model."""

    __tablename__ = "radius_users"

    # User identification
    username = Column(String(100), nullable=False, index=True)
    user_type = Column(
        SQLEnum(RadiusUserType),
        default=RadiusUserType.CUSTOMER,
        nullable=False,
        index=True,
    )

    # Authentication credentials
    password = Column(String(255), nullable=True)  # Encrypted password
    password_type = Column(
        String(50), default="cleartext", nullable=False
    )  # cleartext, crypt, md5, etc.

    # User information
    full_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(20), nullable=True)

    # Customer association
    customer_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Account status and limits
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    max_sessions = Column(Integer, default=1, nullable=False)
    max_bandwidth_kbps = Column(Integer, nullable=True)
    max_time_limit = Column(Integer, nullable=True)  # Session time limit in seconds

    # Usage tracking
    total_sessions = Column(Integer, default=0, nullable=False)
    total_bytes_in = Column(BigInteger, default=0, nullable=False)
    total_bytes_out = Column(BigInteger, default=0, nullable=False)
    total_session_time = Column(BigInteger, default=0, nullable=False)  # In seconds

    # Last activity tracking
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_logout = Column(DateTime(timezone=True), nullable=True)
    last_nas_ip = Column(INET, nullable=True)
    last_calling_station_id = Column(String(50), nullable=True)

    # Additional metadata
    description = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    # Relationships
    groups = relationship(
        "RadiusUserGroup", back_populates="user", cascade="all, delete-orphan"
    )
    check_attributes = relationship(
        "RadiusCheck", back_populates="user", cascade="all, delete-orphan"
    )
    reply_attributes = relationship(
        "RadiusReply", back_populates="user", cascade="all, delete-orphan"
    )
    sessions = relationship("RadiusSession", back_populates="user")
    accounting_records = relationship("RadiusAccounting", back_populates="user")

    __table_args__ = (
        Index("ix_radius_users_tenant_username", "tenant_id", "username", unique=True),
    )

    @validates("username")
    def validate_username(self, key, value):
        """Validate username format."""
        if not value or len(value.strip() == 0:
            raise ValueError("Username cannot be empty")
        if len(value) > 100:
            raise ValueError("Username too long")
        return value.strip()

    @hybrid_property
    def is_active(self) -> bool:
        """Check if user is currently active."""
        now = datetime.now(timezone.utc)
        if not self.enabled:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    def __repr__(self):
        """  Repr   operation."""
        return f"<RadiusUser(username='{self.username}', type='{self.user_type}', enabled={self.enabled})>"


class RadiusGroup(TenantModel, StatusMixin, AuditMixin):
    """RADIUS group model."""

    __tablename__ = "radius_groups"

    # Group identification
    group_name = Column(String(100), nullable=False, index=True)
    display_name = Column(String(255), nullable=True)

    # Group configuration
    priority = Column(Integer, default=0, nullable=False)

    # Bandwidth and limits
    max_bandwidth_kbps = Column(Integer, nullable=True)
    max_session_time = Column(Integer, nullable=True)  # Session time limit in seconds
    max_idle_time = Column(Integer, nullable=True)  # Idle timeout in seconds
    max_sessions_per_user = Column(Integer, default=1, nullable=False)

    # Additional metadata
    description = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    # Relationships
    users = relationship(
        "RadiusUserGroup", back_populates="group", cascade="all, delete-orphan"
    )
    check_attributes = relationship(
        "RadiusCheck", back_populates="group", cascade="all, delete-orphan"
    )
    reply_attributes = relationship(
        "RadiusReply", back_populates="group", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_radius_groups_tenant_name", "tenant_id", "group_name", unique=True),
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<RadiusGroup(name='{self.group_name}', priority={self.priority})>"


class RadiusUserGroup(TenantModel):
    """RADIUS user-group association model."""

    __tablename__ = "radius_user_groups"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("radius_users.id"), nullable=False, index=True
    )
    group_id = Column(
        UUID(as_uuid=True), ForeignKey("radius_groups.id"), nullable=False, index=True
    )

    # Association metadata
    priority = Column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("RadiusUser", back_populates="groups")
    group = relationship("RadiusGroup", back_populates="users")

    __table_args__ = (
        Index("ix_radius_user_groups_user_group", "user_id", "group_id", unique=True),
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<RadiusUserGroup(user='{self.user.username if self.user else 'Unknown'}', group='{self.group.group_name if self.group else 'Unknown'}')>"


class RadiusClient(TenantModel, StatusMixin, AuditMixin):
    """RADIUS client (NAS) model."""

    __tablename__ = "radius_clients"

    # Client identification
    client_name = Column(String(255), nullable=False, index=True)
    nas_ip_address = Column(INET, nullable=False, index=True)
    nas_type = Column(
        SQLEnum(RadiusClientType), default=RadiusClientType.NAS, nullable=False
    )

    # Client configuration
    shared_secret = Column(String(255), nullable=False)
    require_message_authenticator = Column(Boolean, default=False, nullable=False)

    # Client information
    vendor = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    location = Column(String(255), nullable=True)

    # Network configuration
    ports = Column(String(100), nullable=True)  # Comma-separated port list
    virtual_server = Column(String(100), nullable=True)

    # Monitoring and health
    last_seen = Column(DateTime(timezone=True), nullable=True)
    total_requests = Column(BigInteger, default=0, nullable=False)
    successful_requests = Column(BigInteger, default=0, nullable=False)
    failed_requests = Column(BigInteger, default=0, nullable=False)

    # Additional metadata
    description = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    # Relationships
    sessions = relationship("RadiusSession", back_populates="nas_client")
    accounting_records = relationship("RadiusAccounting", back_populates="nas_client")

    __table_args__ = (
        Index(
            "ix_radius_clients_tenant_ip", "tenant_id", "nas_ip_address", unique=True
        ),
    )

    @hybrid_property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests > 0:
            return (self.successful_requests / self.total_requests) * 100
        return 0.0

    def __repr__(self):
        """  Repr   operation."""
        return f"<RadiusClient(name='{self.client_name}', ip='{self.nas_ip_address}', type='{self.nas_type}')>"


class RadiusAttribute(TenantModel):
    """Base model for RADIUS attributes."""

    __abstract__ = True

    # Attribute identification
    attribute_name = Column(String(100), nullable=False, index=True)
    attribute_value = Column(Text, nullable=False)
    operator = Column(
        SQLEnum(AttributeOperator), default=AttributeOperator.EQUAL, nullable=False
    )

    # Additional metadata
    description = Column(Text, nullable=True)


class RadiusCheck(RadiusAttribute):
    """RADIUS check attributes model."""

    __tablename__ = "radius_check_attributes"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("radius_users.id"), nullable=True, index=True
    )
    group_id = Column(
        UUID(as_uuid=True), ForeignKey("radius_groups.id"), nullable=True, index=True
    )

    # Relationships
    user = relationship("RadiusUser", back_populates="check_attributes")
    group = relationship("RadiusGroup", back_populates="check_attributes")

    def __repr__(self):
        """  Repr   operation."""
        return f"<RadiusCheck(attribute='{self.attribute_name}', value='{self.attribute_value}', operator='{self.operator}')>"


class RadiusReply(RadiusAttribute):
    """RADIUS reply attributes model."""

    __tablename__ = "radius_reply_attributes"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("radius_users.id"), nullable=True, index=True
    )
    group_id = Column(
        UUID(as_uuid=True), ForeignKey("radius_groups.id"), nullable=True, index=True
    )

    # Relationships
    user = relationship("RadiusUser", back_populates="reply_attributes")
    group = relationship("RadiusGroup", back_populates="reply_attributes")

    def __repr__(self):
        """  Repr   operation."""
        return f"<RadiusReply(attribute='{self.attribute_name}', value='{self.attribute_value}', operator='{self.operator}')>"


class RadiusSession(TenantModel):
    """RADIUS active session model."""

    __tablename__ = "radius_sessions"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("radius_users.id"), nullable=False, index=True
    )
    nas_client_id = Column(
        UUID(as_uuid=True), ForeignKey("radius_clients.id"), nullable=True, index=True
    )

    # Session identification
    unique_session_id = Column(String(255), nullable=False, unique=True, index=True)
    username = Column(String(100), nullable=False, index=True)
    realm = Column(String(100), nullable=True)

    # NAS information
    nas_ip_address = Column(INET, nullable=False, index=True)
    nas_port_id = Column(String(50), nullable=True)
    nas_port_type = Column(String(50), nullable=True)
    calling_station_id = Column(String(50), nullable=True)  # Client MAC/Phone number
    called_station_id = Column(String(50), nullable=True)  # NAS MAC/Number

    # Network information
    framed_ip_address = Column(INET, nullable=True)
    framed_netmask = Column(INET, nullable=True)
    framed_protocol = Column(String(32), nullable=True)
    service_type = Column(String(32), nullable=True)

    # Session timing
    session_start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    session_timeout = Column(Integer, nullable=True)  # Session timeout in seconds
    idle_timeout = Column(Integer, nullable=True)  # Idle timeout in seconds

    # Session status
    status = Column(
        SQLEnum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False, index=True
    )
    terminate_cause = Column(String(50), nullable=True)

    # Traffic statistics (updated by interim updates)
    bytes_in = Column(BigInteger, default=0, nullable=False)
    bytes_out = Column(BigInteger, default=0, nullable=False)
    packets_in = Column(BigInteger, default=0, nullable=False)
    packets_out = Column(BigInteger, default=0, nullable=False)

    # Last update tracking
    last_update = Column(DateTime(timezone=True), nullable=True)

    # Additional session attributes
    session_attributes = Column(JSON, nullable=True)

    # Relationships
    user = relationship("RadiusUser", back_populates="sessions")
    nas_client = relationship("RadiusClient", back_populates="sessions")

    __table_args__ = (
        Index("ix_radius_sessions_nas_user", "nas_ip_address", "username"),
        Index("ix_radius_sessions_active", "status", "session_start_time"),
    )

    @hybrid_property
    def session_duration(self) -> Optional[int]:
        """Calculate session duration in seconds."""
        if self.session_start_time:
            end_time = self.last_update or datetime.now(timezone.utc)
            duration = end_time - self.session_start_time
            return int(duration.total_seconds()
        return None

    def __repr__(self):
        """  Repr   operation."""
        return f"<RadiusSession(username='{self.username}', nas='{self.nas_ip_address}', status='{self.status}')>"


class RadiusAccounting(TenantModel):
    """RADIUS accounting records model."""

    __tablename__ = "radius_accounting"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("radius_users.id"), nullable=True, index=True
    )
    nas_client_id = Column(
        UUID(as_uuid=True), ForeignKey("radius_clients.id"), nullable=True, index=True
    )

    # Accounting record identification
    unique_session_id = Column(String(255), nullable=False, index=True)
    username = Column(String(100), nullable=False, index=True)
    realm = Column(String(100), nullable=True)

    # NAS information
    nas_ip_address = Column(INET, nullable=False, index=True)
    nas_port_id = Column(String(50), nullable=True)
    nas_port_type = Column(String(50), nullable=True)
    calling_station_id = Column(String(50), nullable=True)
    called_station_id = Column(String(50), nullable=True)

    # Network information
    framed_ip_address = Column(INET, nullable=True)
    framed_protocol = Column(String(32), nullable=True)
    service_type = Column(String(32), nullable=True)

    # Accounting information
    acct_status_type = Column(SQLEnum(AccountingStatus), nullable=False, index=True)
    acct_start_time = Column(DateTime(timezone=True), nullable=True, index=True)
    acct_stop_time = Column(DateTime(timezone=True), nullable=True, index=True)
    acct_session_time = Column(Integer, nullable=True)  # Session time in seconds

    # Traffic statistics
    acct_input_octets = Column(BigInteger, default=0, nullable=False)
    acct_output_octets = Column(BigInteger, default=0, nullable=False)
    acct_input_packets = Column(BigInteger, default=0, nullable=False)
    acct_output_packets = Column(BigInteger, default=0, nullable=False)

    # Termination information
    acct_terminate_cause = Column(String(50), nullable=True)

    # Timestamp
    event_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Additional attributes
    accounting_attributes = Column(JSON, nullable=True)

    # Relationships
    user = relationship("RadiusUser", back_populates="accounting_records")
    nas_client = relationship("RadiusClient", back_populates="accounting_records")

    __table_args__ = (
        Index("ix_radius_accounting_session", "unique_session_id", "acct_status_type"),
        Index("ix_radius_accounting_user_time", "username", "acct_start_time"),
        Index("ix_radius_accounting_nas_time", "nas_ip_address", "event_timestamp"),
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<RadiusAccounting(username='{self.username}', status='{self.acct_status_type}', session='{self.unique_session_id}')>"


class RadiusPolicy(TenantModel, StatusMixin, AuditMixin):
    """RADIUS policy model for advanced configurations."""

    __tablename__ = "radius_policies"

    # Policy identification
    policy_name = Column(String(255), nullable=False, index=True)
    policy_type = Column(
        String(50), nullable=False, index=True
    )  # bandwidth, time, access, etc.

    # Policy configuration
    policy_rules = Column(JSON, nullable=False)  # Policy rules in JSON format
    conditions = Column(JSON, nullable=True)  # Conditions for policy application
    actions = Column(JSON, nullable=True)  # Actions to take when policy matches

    # Policy priority and scheduling
    priority = Column(Integer, default=0, nullable=False)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)

    # Usage tracking
    applied_count = Column(Integer, default=0, nullable=False)
    last_applied = Column(DateTime(timezone=True), nullable=True)

    # Additional metadata
    description = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    __table_args__ = (
        Index(
            "ix_radius_policies_tenant_name", "tenant_id", "policy_name", unique=True
        ),
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<RadiusPolicy(name='{self.policy_name}', type='{self.policy_type}', priority={self.priority})>"


class RadiusNas(TenantModel, StatusMixin, AuditMixin):
    """RADIUS NAS (Network Access Server) model."""

    __tablename__ = "radius_nas"

    # NAS identification
    nas_name = Column(String(255), nullable=False, index=True)
    short_name = Column(String(100), nullable=False, index=True)
    nas_type = Column(String(50), nullable=False)

    # Network configuration
    nas_ip = Column(INET, nullable=False, index=True)
    nas_port = Column(Integer, default=1812, nullable=False)
    secret = Column(String(255), nullable=False)

    # NAS capabilities
    ports = Column(Integer, nullable=True)
    virtual_server = Column(String(100), nullable=True)

    # Additional metadata
    description = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_radius_nas_tenant_ip", "tenant_id", "nas_ip", unique=True),
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<RadiusNas(name='{self.nas_name}', ip='{self.nas_ip}', type='{self.nas_type}')>"
