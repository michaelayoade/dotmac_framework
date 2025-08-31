"""
Shared compliance and regulatory reporting system for DotMac Framework.

This module provides DRY compliance utilities that eliminate duplicated 
regulatory reporting, audit trail management, and compliance monitoring code.
"""

from .core.compliance_manager import ComplianceManager, ComplianceConfig
from .core.regulatory_reporter import RegulatoryReporter, ReportingConfig
from .core.audit_trail import AuditTrailManager, AuditConfig
from .schemas.compliance_schemas import (
    ComplianceFramework,
    ComplianceEvent,
    RegulatoryReport,
    ComplianceStatus,
    AuditEvent,
)
from .services.compliance_service import ComplianceService
from .adapters.isp_compliance_adapter import ISPComplianceAdapter
from .adapters.management_compliance_adapter import ManagementComplianceAdapter

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