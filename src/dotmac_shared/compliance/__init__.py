"""
Shared compliance and regulatory reporting system for DotMac Framework.

This module provides DRY compliance utilities that eliminate duplicated
regulatory reporting, audit trail management, and compliance monitoring code.
"""

from .adapters.isp_compliance_adapter import ISPComplianceAdapter
from .adapters.management_compliance_adapter import ManagementComplianceAdapter
from .core.audit_trail import AuditConfig, AuditTrailManager
from .core.compliance_manager import ComplianceConfig, ComplianceManager
from .core.regulatory_reporter import RegulatoryReporter, ReportingConfig
from .schemas.compliance_schemas import (
    AuditEvent,
    ComplianceEvent,
    ComplianceFramework,
    ComplianceStatus,
    RegulatoryReport,
)
from .services.compliance_service import ComplianceService

__all__ = [
    # Core classes
    "ComplianceManager",
    "RegulatoryReporter",
    "AuditTrailManager",
    # Configuration
    "ComplianceConfig",
    "ReportingConfig",
    "AuditConfig",
    # Schemas
    "ComplianceFramework",
    "ComplianceEvent",
    "RegulatoryReport",
    "ComplianceStatus",
    "AuditEvent",
    # Services
    "ComplianceService",
    # Adapters
    "ISPComplianceAdapter",
    "ManagementComplianceAdapter",
]
