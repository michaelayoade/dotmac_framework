"""Compliance management API endpoints."""

from datetime import datetime, date, timedelta, timezone
from typing import List, Optional, Dict, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from dotmac_isp.core.database import get_db
from dotmac_isp.shared.auth import get_current_tenant
from .models import (
    ComplianceRequirement,
    ComplianceAssessment,
    ComplianceFinding,
    ComplianceAudit,
    CompliancePolicy,
    ComplianceReport,
    ComplianceFramework,
    ComplianceStatus,
    AuditType,
    AuditStatus,
    FindingSeverity,
    FindingStatus,
)

router = APIRouter(prefix="/compliance", tags=["compliance"])


def generate_assessment_id() -> str:
    """Generate a unique assessment ID."""
    timestamp = int(datetime.now(timezone.utc).timestamp())
    return f"ASS-{timestamp}"


def generate_finding_id() -> str:
    """Generate a unique finding ID."""
    timestamp = int(datetime.now(timezone.utc).timestamp())
    return f"FND-{timestamp}"


def generate_audit_id() -> str:
    """Generate a unique audit ID."""
    timestamp = int(datetime.now(timezone.utc).timestamp())
    return f"AUD-{timestamp}"


# Requirements Management
@router.post("/requirements")
async def create_requirement(
    requirement_code: str,
    title: str,
    description: str,
    framework: ComplianceFramework,
    mandatory: bool = True,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create a new compliance requirement."""

    # Check if requirement code already exists
    existing = (
        db.query(ComplianceRequirement)
        .filter(
            and_(
                ComplianceRequirement.tenant_id == tenant_id,
                ComplianceRequirement.requirement_code == requirement_code,
            )
        )
        .first()
    )

    if existing:
        raise HTTPException(status_code=400, detail="Requirement code already exists")

    db_requirement = ComplianceRequirement(
        id=str(uuid4()),
        tenant_id=tenant_id,
        requirement_code=requirement_code,
        title=title,
        description=description,
        framework=framework,
        mandatory=mandatory,
    )

    db.add(db_requirement)
    db.commit()
    db.refresh(db_requirement)

    return db_requirement


@router.get("/requirements")
async def list_requirements(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    framework: Optional[ComplianceFramework] = None,
    status: Optional[ComplianceStatus] = None,
    mandatory: Optional[bool] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List compliance requirements."""

    query = db.query(ComplianceRequirement).filter(
        ComplianceRequirement.tenant_id == tenant_id
    )

    if framework:
        query = query.filter(ComplianceRequirement.framework == framework)
    if status:
        query = query.filter(ComplianceRequirement.compliance_status == status)
    if mandatory is not None:
        query = query.filter(ComplianceRequirement.mandatory == mandatory)

    requirements = (
        query.order_by(desc(ComplianceRequirement.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return requirements


@router.get("/requirements/{requirement_id}")
async def get_requirement(
    requirement_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get a specific compliance requirement."""

    requirement = (
        db.query(ComplianceRequirement)
        .filter(
            and_(
                ComplianceRequirement.id == requirement_id,
                ComplianceRequirement.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")

    return requirement


# Assessments Management
@router.post("/assessments")
async def create_assessment(
    requirement_id: str,
    title: str,
    assessor_name: str,
    result_status: ComplianceStatus,
    assessment_date: date = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create a new compliance assessment."""

    assessment_id = generate_assessment_id()

    db_assessment = ComplianceAssessment(
        id=str(uuid4()),
        tenant_id=tenant_id,
        assessment_id=assessment_id,
        requirement_id=requirement_id,
        title=title,
        assessor_name=assessor_name,
        result_status=result_status,
        assessment_date=assessment_date or date.today(),
    )

    db.add(db_assessment)
    db.commit()
    db.refresh(db_assessment)

    return db_assessment


@router.get("/assessments")
async def list_assessments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    requirement_id: Optional[str] = None,
    result_status: Optional[ComplianceStatus] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List compliance assessments."""

    query = db.query(ComplianceAssessment).filter(
        ComplianceAssessment.tenant_id == tenant_id
    )

    if requirement_id:
        query = query.filter(ComplianceAssessment.requirement_id == requirement_id)
    if result_status:
        query = query.filter(ComplianceAssessment.result_status == result_status)

    assessments = (
        query.order_by(desc(ComplianceAssessment.assessment_date))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return assessments


# Findings Management
@router.post("/findings")
async def create_finding(
    requirement_id: str,
    title: str,
    description: str,
    severity: FindingSeverity,
    assessment_id: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create a new compliance finding."""

    finding_id = generate_finding_id()

    db_finding = ComplianceFinding(
        id=str(uuid4()),
        tenant_id=tenant_id,
        finding_id=finding_id,
        requirement_id=requirement_id,
        assessment_id=assessment_id,
        title=title,
        description=description,
        severity=severity,
        discovered_date=date.today(),
    )

    db.add(db_finding)
    db.commit()
    db.refresh(db_finding)

    return db_finding


@router.get("/findings")
async def list_findings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    severity: Optional[FindingSeverity] = None,
    status: Optional[FindingStatus] = None,
    overdue: bool = False,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List compliance findings."""

    query = db.query(ComplianceFinding).filter(ComplianceFinding.tenant_id == tenant_id)

    if severity:
        query = query.filter(ComplianceFinding.severity == severity)
    if status:
        query = query.filter(ComplianceFinding.status == status)
    if overdue:
        query = query.filter(
            and_(
                ComplianceFinding.due_date < date.today(),
                ComplianceFinding.status.in_(
                    [FindingStatus.OPEN, FindingStatus.IN_PROGRESS]
                ),
            )
        )

    findings = (
        query.order_by(desc(ComplianceFinding.discovered_date))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return findings


# Dashboard and Analytics
@router.get("/dashboard")
async def get_compliance_dashboard(
    db: Session = Depends(get_db), tenant_id: str = Depends(get_current_tenant)
):
    """Get compliance dashboard data."""

    # Overall compliance status
    total_requirements = (
        db.query(ComplianceRequirement)
        .filter(ComplianceRequirement.tenant_id == tenant_id)
        .count()
    )

    compliant_requirements = (
        db.query(ComplianceRequirement)
        .filter(
            and_(
                ComplianceRequirement.tenant_id == tenant_id,
                ComplianceRequirement.compliance_status == ComplianceStatus.COMPLIANT,
            )
        )
        .count()
    )

    # Open findings by severity
    critical_findings = (
        db.query(ComplianceFinding)
        .filter(
            and_(
                ComplianceFinding.tenant_id == tenant_id,
                ComplianceFinding.severity == FindingSeverity.CRITICAL,
                ComplianceFinding.status.in_(
                    [FindingStatus.OPEN, FindingStatus.IN_PROGRESS]
                ),
            )
        )
        .count()
    )

    high_findings = (
        db.query(ComplianceFinding)
        .filter(
            and_(
                ComplianceFinding.tenant_id == tenant_id,
                ComplianceFinding.severity == FindingSeverity.HIGH,
                ComplianceFinding.status.in_(
                    [FindingStatus.OPEN, FindingStatus.IN_PROGRESS]
                ),
            )
        )
        .count()
    )

    # Overdue items
    overdue_findings = (
        db.query(ComplianceFinding)
        .filter(
            and_(
                ComplianceFinding.tenant_id == tenant_id,
                ComplianceFinding.due_date < date.today(),
                ComplianceFinding.status.in_(
                    [FindingStatus.OPEN, FindingStatus.IN_PROGRESS]
                ),
            )
        )
        .count()
    )

    return {
        "compliance_overview": {
            "total_requirements": total_requirements,
            "compliant_requirements": compliant_requirements,
            "compliance_rate": (
                round((compliant_requirements / total_requirements * 100), 2)
                if total_requirements > 0
                else 0
            ),
        },
        "findings_summary": {
            "critical_findings": critical_findings,
            "high_findings": high_findings,
            "overdue_findings": overdue_findings,
        },
    }
