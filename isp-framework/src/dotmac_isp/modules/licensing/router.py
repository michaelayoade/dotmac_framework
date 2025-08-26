"""Licensing management API endpoints."""

from datetime import datetime, date, timedelta, timezone
from typing import List, Optional, Dict, Any
from uuid import uuid4
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc

from dotmac_isp.core.database import get_db
from dotmac_isp.shared.auth import get_current_tenant
from .models import (
    Software,
    License,
    LicenseAllocation,
    Installation,
    LicenseAudit,
    AuditFinding,
    LicenseAlert,
    LicenseType,
    LicenseStatus,
    ComplianceStatus,
    AllocationStatus,
    AuditStatus,
    AlertType,
)

router = APIRouter(prefix="/licensing", tags=["licensing"])


def generate_license_number(vendor: str) -> str:
    """Generate a unique license number."""
    timestamp = int(datetime.now(timezone.utc).timestamp())
    prefix = vendor[:3].upper()
    return f"{prefix}-LIC-{timestamp}"


def generate_audit_id() -> str:
    """Generate a unique audit ID."""
    timestamp = int(datetime.now(timezone.utc).timestamp())
    return f"AUDIT-{timestamp}"


def generate_finding_id() -> str:
    """Generate a unique finding ID."""
    timestamp = int(datetime.now(timezone.utc).timestamp())
    return f"FIND-{timestamp}"


def generate_alert_id() -> str:
    """Generate a unique alert ID."""
    timestamp = int(datetime.now(timezone.utc).timestamp())
    return f"ALERT-{timestamp}"


def generate_installation_id() -> str:
    """Generate a unique installation ID."""
    timestamp = int(datetime.now(timezone.utc).timestamp())
    return f"INST-{timestamp}"


# Software Management
@router.post("/software")
async def create_software(
    software_code: str,
    name: str,
    vendor_name: str,
    category: str,
    description: Optional[str] = None,
    version: Optional[str] = None,
    edition: Optional[str] = None,
    platform: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create a new software product."""

    # Check if software code already exists
    existing = (
        db.query(Software)
        .filter(
            and_(
                Software.tenant_id == tenant_id, Software.software_code == software_code
            )
        )
        .first()
    )

    if existing:
        raise HTTPException(status_code=400, detail="Software code already exists")

    db_software = Software(
        id=str(uuid4()),
        tenant_id=tenant_id,
        software_code=software_code,
        name=name,
        description=description,
        vendor_name=vendor_name,
        version=version,
        edition=edition,
        platform=platform,
        category=category,
    )

    db.add(db_software)
    db.commit()
    db.refresh(db_software)

    return db_software


@router.get("/software")
async def list_software(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    vendor_name: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List software products."""

    query = db.query(Software).filter(Software.tenant_id == tenant_id)

    if vendor_name:
        query = query.filter(Software.vendor_name == vendor_name)
    if category:
        query = query.filter(Software.category == category)
    if search:
        query = query.filter(
            or_(
                Software.name.ilike(f"%{search}%"),
                Software.software_code.ilike(f"%{search}%"),
                Software.description.ilike(f"%{search}%"),
            )
        )

    software = query.order_by(desc(Software.created_at)).offset(skip).limit(limit).all()
    return software


@router.get("/software/{software_id}")
async def get_software(
    software_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get a specific software product."""

    software = (
        db.query(Software)
        .filter(and_(Software.id == software_id, Software.tenant_id == tenant_id))
        .first()
    )

    if not software:
        raise HTTPException(status_code=404, detail="Software not found")

    return software


# License Management
@router.post("/licenses")
async def create_license(
    software_id: str,
    license_type: LicenseType,
    licensed_quantity: int,
    vendor_name: str,
    effective_date: date,
    license_key: Optional[str] = None,
    expiry_date: Optional[date] = None,
    purchase_cost: Optional[float] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create a new license."""

    # Verify software exists
    software = (
        db.query(Software)
        .filter(and_(Software.id == software_id, Software.tenant_id == tenant_id))
        .first()
    )

    if not software:
        raise HTTPException(status_code=404, detail="Software not found")

    license_number = generate_license_number(vendor_name)

    db_license = License(
        id=str(uuid4()),
        tenant_id=tenant_id,
        license_key=license_key,
        license_number=license_number,
        software_id=software_id,
        license_type=license_type,
        licensed_quantity=licensed_quantity,
        vendor_name=vendor_name,
        effective_date=effective_date,
        expiry_date=expiry_date,
        purchase_cost=Decimal(str(purchase_cost)) if purchase_cost else None,
    )

    db.add(db_license)
    db.commit()
    db.refresh(db_license)

    return db_license


@router.get("/licenses")
async def list_licenses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    software_id: Optional[str] = None,
    license_type: Optional[LicenseType] = None,
    license_status: Optional[LicenseStatus] = None,
    expiring_soon: bool = False,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List licenses."""

    query = db.query(License).filter(License.tenant_id == tenant_id)

    if software_id:
        query = query.filter(License.software_id == software_id)
    if license_type:
        query = query.filter(License.license_type == license_type)
    if license_status:
        query = query.filter(License.license_status == license_status)
    if expiring_soon:
        cutoff_date = date.today() + timedelta(days=90)
        query = query.filter(
            and_(License.expiry_date.isnot(None), License.expiry_date <= cutoff_date)
        )

    licenses = query.order_by(desc(License.created_at)).offset(skip).limit(limit).all()
    return licenses


@router.get("/licenses/{license_id}")
async def get_license(
    license_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get a specific license."""

    license = (
        db.query(License)
        .filter(and_(License.id == license_id, License.tenant_id == tenant_id))
        .first()
    )

    if not license:
        raise HTTPException(status_code=404, detail="License not found")

    return license


@router.put("/licenses/{license_id}/status")
async def update_license_status(
    license_id: str,
    status: LicenseStatus,
    compliance_status: Optional[ComplianceStatus] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Update license status."""

    license = (
        db.query(License)
        .filter(and_(License.id == license_id, License.tenant_id == tenant_id))
        .first()
    )

    if not license:
        raise HTTPException(status_code=404, detail="License not found")

    license.license_status = status
    if compliance_status:
        license.compliance_status = compliance_status
    if notes:
        license.notes = notes
    license.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(license)

    return license


# License Allocations
@router.post("/allocations")
async def create_allocation(
    license_id: str,
    allocation_type: str,
    allocated_to_name: str,
    allocated_to_id: Optional[str] = None,
    allocated_to_email: Optional[str] = None,
    business_justification: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Allocate a license to a user or device."""

    # Verify license exists and has available quantity
    license = (
        db.query(License)
        .filter(and_(License.id == license_id, License.tenant_id == tenant_id))
        .first()
    )

    if not license:
        raise HTTPException(status_code=404, detail="License not found")

    if license.used_quantity >= license.licensed_quantity:
        raise HTTPException(status_code=400, detail="No available license quantity")

    db_allocation = LicenseAllocation(
        id=str(uuid4()),
        tenant_id=tenant_id,
        license_id=license_id,
        allocation_type=allocation_type,
        allocated_to_id=allocated_to_id,
        allocated_to_name=allocated_to_name,
        allocated_to_email=allocated_to_email,
        business_justification=business_justification,
        allocation_date=date.today(),
    )

    # Update license usage
    license.used_quantity += 1

    db.add(db_allocation)
    db.commit()
    db.refresh(db_allocation)

    return db_allocation


@router.get("/allocations")
async def list_allocations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    license_id: Optional[str] = None,
    allocation_status: Optional[AllocationStatus] = None,
    allocated_to_id: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List license allocations."""

    query = db.query(LicenseAllocation).filter(LicenseAllocation.tenant_id == tenant_id)

    if license_id:
        query = query.filter(LicenseAllocation.license_id == license_id)
    if allocation_status:
        query = query.filter(LicenseAllocation.allocation_status == allocation_status)
    if allocated_to_id:
        query = query.filter(LicenseAllocation.allocated_to_id == allocated_to_id)

    allocations = (
        query.order_by(desc(LicenseAllocation.allocation_date))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return allocations


@router.delete("/allocations/{allocation_id}")
async def deallocate_license(
    allocation_id: str,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Deallocate a license."""

    allocation = (
        db.query(LicenseAllocation)
        .filter(
            and_(
                LicenseAllocation.id == allocation_id,
                LicenseAllocation.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")

    # Update license usage
    license = db.query(License).filter(License.id == allocation.license_id).first()
    if license:
        license.used_quantity = max(0, license.used_quantity - 1)

    allocation.allocation_status = AllocationStatus.UNALLOCATED
    allocation.deactivation_date = date.today()
    allocation.notes = reason or "License deallocated"

    db.commit()

    return {"message": "License deallocated successfully"}


# Installations
@router.post("/installations")
async def create_installation(
    software_id: str,
    device_name: str,
    installation_date: date,
    device_id: Optional[str] = None,
    installed_version: Optional[str] = None,
    installation_path: Optional[str] = None,
    user_name: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Record a software installation."""

    installation_id = generate_installation_id()

    db_installation = Installation(
        id=str(uuid4()),
        tenant_id=tenant_id,
        installation_id=installation_id,
        software_id=software_id,
        device_id=device_id,
        device_name=device_name,
        installed_version=installed_version,
        installation_date=installation_date,
        installation_path=installation_path,
        user_name=user_name,
    )

    db.add(db_installation)
    db.commit()
    db.refresh(db_installation)

    return db_installation


@router.get("/installations")
async def list_installations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    software_id: Optional[str] = None,
    device_id: Optional[str] = None,
    user_name: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List software installations."""

    query = db.query(Installation).filter(Installation.tenant_id == tenant_id)

    if software_id:
        query = query.filter(Installation.software_id == software_id)
    if device_id:
        query = query.filter(Installation.device_id == device_id)
    if user_name:
        query = query.filter(Installation.user_name.ilike(f"%{user_name}%"))

    installations = (
        query.order_by(desc(Installation.installation_date))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return installations


# License Audits
@router.post("/audits")
async def create_audit(
    audit_name: str,
    audit_type: str,
    auditor_name: str,
    planned_start_date: date,
    planned_end_date: date,
    description: Optional[str] = None,
    license_id: Optional[str] = None,
    vendor_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create a new license audit."""

    audit_id = generate_audit_id()

    db_audit = LicenseAudit(
        id=str(uuid4()),
        tenant_id=tenant_id,
        audit_id=audit_id,
        audit_name=audit_name,
        description=description,
        audit_type=audit_type,
        license_id=license_id,
        vendor_filter=vendor_filter,
        planned_start_date=planned_start_date,
        planned_end_date=planned_end_date,
        auditor_name=auditor_name,
    )

    db.add(db_audit)
    db.commit()
    db.refresh(db_audit)

    return db_audit


@router.get("/audits")
async def list_audits(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    audit_status: Optional[AuditStatus] = None,
    auditor_name: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List license audits."""

    query = db.query(LicenseAudit).filter(LicenseAudit.tenant_id == tenant_id)

    if audit_status:
        query = query.filter(LicenseAudit.audit_status == audit_status)
    if auditor_name:
        query = query.filter(LicenseAudit.auditor_name.ilike(f"%{auditor_name}%"))

    audits = (
        query.order_by(desc(LicenseAudit.planned_start_date))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return audits


@router.put("/audits/{audit_id}/status")
async def update_audit_status(
    audit_id: str,
    status: AuditStatus,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Update audit status."""

    audit = (
        db.query(LicenseAudit)
        .filter(and_(LicenseAudit.id == audit_id, LicenseAudit.tenant_id == tenant_id))
        .first()
    )

    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit.audit_status = status
    if status == AuditStatus.IN_PROGRESS and not audit.actual_start_date:
        audit.actual_start_date = date.today()
    elif status == AuditStatus.COMPLETED and not audit.actual_end_date:
        audit.actual_end_date = date.today()

    if notes:
        audit.notes = notes

    db.commit()
    db.refresh(audit)

    return audit


# Audit Findings
@router.post("/findings")
async def create_finding(
    audit_id: str,
    title: str,
    description: str,
    finding_type: str,
    severity: str,
    recommended_action: str,
    license_id: Optional[str] = None,
    software_id: Optional[str] = None,
    remediation_due_date: Optional[date] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create an audit finding."""

    finding_id = generate_finding_id()

    db_finding = AuditFinding(
        id=str(uuid4()),
        tenant_id=tenant_id,
        finding_id=finding_id,
        title=title,
        description=description,
        audit_id=audit_id,
        license_id=license_id,
        software_id=software_id,
        finding_type=finding_type,
        severity=severity,
        recommended_action=recommended_action,
        remediation_due_date=remediation_due_date,
    )

    db.add(db_finding)
    db.commit()
    db.refresh(db_finding)

    return db_finding


@router.get("/findings")
async def list_findings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    audit_id: Optional[str] = None,
    severity: Optional[str] = None,
    finding_status: Optional[str] = None,
    overdue: bool = False,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List audit findings."""

    query = db.query(AuditFinding).filter(AuditFinding.tenant_id == tenant_id)

    if audit_id:
        query = query.filter(AuditFinding.audit_id == audit_id)
    if severity:
        query = query.filter(AuditFinding.severity == severity)
    if finding_status:
        query = query.filter(AuditFinding.finding_status == finding_status)
    if overdue:
        query = query.filter(
            and_(
                AuditFinding.remediation_due_date < date.today(),
                AuditFinding.finding_status.in_(["open", "in_progress"]),
            )
        )

    findings = (
        query.order_by(desc(AuditFinding.created_at)).offset(skip).limit(limit).all()
    )
    return findings


# Alerts
@router.post("/alerts")
async def create_alert(
    title: str,
    description: str,
    alert_type: AlertType,
    severity: str,
    license_id: Optional[str] = None,
    software_id: Optional[str] = None,
    due_date: Optional[date] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create a license alert."""

    alert_id = generate_alert_id()

    db_alert = LicenseAlert(
        id=str(uuid4()),
        tenant_id=tenant_id,
        alert_id=alert_id,
        title=title,
        description=description,
        alert_type=alert_type,
        severity=severity,
        license_id=license_id,
        software_id=software_id,
        due_date=due_date,
        trigger_conditions={},
    )

    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)

    return db_alert


@router.get("/alerts")
async def list_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    alert_type: Optional[AlertType] = None,
    severity: Optional[str] = None,
    alert_status: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List license alerts."""

    query = db.query(LicenseAlert).filter(LicenseAlert.tenant_id == tenant_id)

    if alert_type:
        query = query.filter(LicenseAlert.alert_type == alert_type)
    if severity:
        query = query.filter(LicenseAlert.severity == severity)
    if alert_status:
        query = query.filter(LicenseAlert.alert_status == alert_status)
    if acknowledged is not None:
        query = query.filter(LicenseAlert.acknowledged == acknowledged)

    alerts = (
        query.order_by(desc(LicenseAlert.trigger_date)).offset(skip).limit(limit).all()
    )
    return alerts


@router.put("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    acknowledged_by: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Acknowledge a license alert."""

    alert = (
        db.query(LicenseAlert)
        .filter(and_(LicenseAlert.id == alert_id, LicenseAlert.tenant_id == tenant_id))
        .first()
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.acknowledged = True
    alert.acknowledged_by = acknowledged_by
    alert.acknowledged_date = datetime.now(timezone.utc)

    db.commit()
    db.refresh(alert)

    return alert


# Dashboard and Reports
@router.get("/dashboard")
async def get_licensing_dashboard(
    db: Session = Depends(get_db), tenant_id: str = Depends(get_current_tenant)
):
    """Get licensing dashboard data."""

    # License statistics
    total_licenses = db.query(License).filter(License.tenant_id == tenant_id).count()

    active_licenses = (
        db.query(License)
        .filter(
            and_(
                License.tenant_id == tenant_id,
                License.license_status == LicenseStatus.ACTIVE,
            )
        )
        .count()
    )

    expired_licenses = (
        db.query(License)
        .filter(
            and_(
                License.tenant_id == tenant_id,
                License.license_status == LicenseStatus.EXPIRED,
            )
        )
        .count()
    )

    # Compliance overview
    compliant_licenses = (
        db.query(License)
        .filter(
            and_(
                License.tenant_id == tenant_id,
                License.compliance_status == ComplianceStatus.COMPLIANT,
            )
        )
        .count()
    )

    non_compliant_licenses = (
        db.query(License)
        .filter(
            and_(
                License.tenant_id == tenant_id,
                License.compliance_status == ComplianceStatus.NON_COMPLIANT,
            )
        )
        .count()
    )

    # Expiring soon (next 90 days)
    expiring_soon = (
        db.query(License)
        .filter(
            and_(
                License.tenant_id == tenant_id,
                License.expiry_date.isnot(None),
                License.expiry_date <= date.today() + timedelta(days=90),
                License.expiry_date >= date.today(),
            )
        )
        .count()
    )

    # Active alerts
    active_alerts = (
        db.query(LicenseAlert)
        .filter(
            and_(
                LicenseAlert.tenant_id == tenant_id,
                LicenseAlert.alert_status == "active",
                LicenseAlert.resolved == False,
            )
        )
        .count()
    )

    # Utilization stats
    utilization_stats = (
        db.query(
            func.sum(License.used_quantity).label("total_used"),
            func.sum(License.licensed_quantity).label("total_licensed"),
        )
        .filter(License.tenant_id == tenant_id)
        .first()
    )

    total_used = utilization_stats.total_used or 0
    total_licensed = utilization_stats.total_licensed or 0
    utilization_rate = (
        round((total_used / total_licensed * 100), 2) if total_licensed > 0 else 0
    )

    return {
        "license_summary": {
            "total_licenses": total_licenses,
            "active_licenses": active_licenses,
            "expired_licenses": expired_licenses,
            "expiring_soon": expiring_soon,
        },
        "compliance_overview": {
            "compliant_licenses": compliant_licenses,
            "non_compliant_licenses": non_compliant_licenses,
            "compliance_rate": (
                round((compliant_licenses / total_licenses * 100), 2)
                if total_licenses > 0
                else 0
            ),
        },
        "utilization": {
            "total_used": total_used,
            "total_licensed": total_licensed,
            "utilization_rate": utilization_rate,
        },
        "alerts": {"active_alerts": active_alerts},
    }


@router.get("/reports/license-inventory")
async def get_license_inventory_report(
    vendor_name: Optional[str] = None,
    license_type: Optional[LicenseType] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get license inventory report."""

    query = (
        db.query(
            Software.name.label("software_name"),
            Software.vendor_name,
            License.license_number,
            License.license_type,
            License.license_status,
            License.licensed_quantity,
            License.used_quantity,
            License.expiry_date,
            License.purchase_cost,
        )
        .join(Software)
        .filter(License.tenant_id == tenant_id)
    )

    if vendor_name:
        query = query.filter(License.vendor_name == vendor_name)
    if license_type:
        query = query.filter(License.license_type == license_type)

    results = query.all()

    total_cost = sum(float(r.purchase_cost) if r.purchase_cost else 0 for r in results)
    total_licenses = len(results)

    return {
        "report_date": date.today(),
        "filters": {"vendor_name": vendor_name, "license_type": license_type},
        "summary": {
            "total_licenses": total_licenses,
            "total_cost": total_cost,
            "active_licenses": len(
                [r for r in results if r.license_status == LicenseStatus.ACTIVE]
            ),
            "expired_licenses": len(
                [r for r in results if r.license_status == LicenseStatus.EXPIRED]
            ),
        },
        "licenses": [
            {
                "software_name": r.software_name,
                "vendor_name": r.vendor_name,
                "license_number": r.license_number,
                "license_type": r.license_type,
                "status": r.license_status,
                "licensed_quantity": r.licensed_quantity,
                "used_quantity": r.used_quantity,
                "utilization": (
                    round((r.used_quantity / r.licensed_quantity * 100), 2)
                    if r.licensed_quantity > 0
                    else 0
                ),
                "expiry_date": r.expiry_date,
                "purchase_cost": float(r.purchase_cost) if r.purchase_cost else 0,
            }
            for r in results
        ],
    }


@router.get("/reports/compliance-summary")
async def get_compliance_report(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get license compliance summary report."""

    # License compliance by status
    compliance_stats = (
        db.query(License.compliance_status, func.count(License.id).label("count"))
        .filter(
            and_(
                License.tenant_id == tenant_id,
                License.created_at >= start_date,
                License.created_at <= end_date,
            )
        )
        .group_by(License.compliance_status)
        .all()
    )

    # Recent audit findings
    recent_findings = (
        db.query(AuditFinding)
        .filter(
            and_(
                AuditFinding.tenant_id == tenant_id,
                AuditFinding.created_at >= start_date,
                AuditFinding.created_at <= end_date,
            )
        )
        .order_by(desc(AuditFinding.created_at))
        .limit(20)
        .all()
    )

    # Active alerts by type
    alert_stats = (
        db.query(LicenseAlert.alert_type, func.count(LicenseAlert.id).label("count"))
        .filter(
            and_(
                LicenseAlert.tenant_id == tenant_id,
                LicenseAlert.alert_status == "active",
                LicenseAlert.resolved == False,
            )
        )
        .group_by(LicenseAlert.alert_type)
        .all()
    )

    return {
        "report_period": {"start_date": start_date, "end_date": end_date},
        "compliance_breakdown": [
            {"status": stat.compliance_status, "count": stat.count}
            for stat in compliance_stats
        ],
        "recent_findings": [
            {
                "finding_id": finding.finding_id,
                "title": finding.title,
                "severity": finding.severity,
                "finding_type": finding.finding_type,
                "created_date": finding.created_at,
                "status": finding.finding_status,
            }
            for finding in recent_findings
        ],
        "active_alerts": [
            {"alert_type": stat.alert_type, "count": stat.count} for stat in alert_stats
        ],
    }
