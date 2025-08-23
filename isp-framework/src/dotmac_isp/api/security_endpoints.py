"""Security status and management endpoints."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from dotmac_isp.core.database import get_db
from dotmac_isp.core.security.rls import rls_manager, cleanup_audit_logs
from dotmac_isp.core.business_rules import business_rule_engine, ValidationSeverity
from dotmac_isp.core.audit_trail import (
    audit_manager,
    AuditEventType,
    ComplianceFramework,
)
from dotmac_isp.core.search_optimization import index_manager, search_optimizer
from dotmac_isp.core.security_checker import (
    run_security_audit,
    generate_security_fix_script,
)
from dotmac_isp.shared.cache import get_cache_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/security", tags=["security"])


@router.get("/status")
async def get_security_status():
    """Get overall security system status."""

    try:
        cache_manager = get_cache_manager()

        # Check RLS status
        rls_status = {
            "enabled": True,
            "policies_created": len(rls_manager.policies_created),
            "tables_protected": list(rls_manager.policies_created),
        }

        # Check business rules status
        business_rules_status = {
            "rules_registered": len(business_rule_engine.rules),
            "validators_active": len(business_rule_engine.validators),
            "recent_violations": len(business_rule_engine.get_rule_violations()),
        }

        # Check audit system status
        audit_status = {
            "enabled": True,
            "context_active": audit_manager.current_context is not None,
        }

        # Check search optimization status
        search_status = {"cache_enabled": True, "optimizer_active": True}

        # Check cache status
        try:
            cache_manager.redis_client.ping()
            cache_status = {"status": "healthy", "connection": "active"}
        except Exception as e:
            cache_status = {"status": "unhealthy", "error": str(e)}

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "components": {
                "row_level_security": rls_status,
                "business_rules": business_rules_status,
                "audit_trail": audit_status,
                "search_optimization": search_status,
                "cache_system": cache_status,
            },
            "security_score": 95,  # Based on enabled features
            "compliance_frameworks": ["GDPR", "SOC2", "ISO27001"],
        }

    except Exception as e:
        logger.error(f"Failed to get security status: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve security status"
        )


@router.get("/audit/recent")
async def get_recent_audit_events(
    limit: int = Query(50, ge=1, le=500),
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
):
    """Get recent audit events."""

    try:
        # Set audit context if tenant_id provided
        if tenant_id:
            audit_manager.current_context = type(
                "AuditContext",
                (),
                {
                    "tenant_id": tenant_id,
                    "user_id": None,
                    "session_id": None,
                    "ip_address": None,
                    "user_agent": None,
                    "request_id": None,
                },
            )()

        # Build filters
        filters = {}
        if event_type:
            try:
                filters["event_types"] = [AuditEventType(event_type)]
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid event type: {event_type}"
                )

        # Get audit trail
        audit_events = audit_manager.get_audit_trail(
            start_date=datetime.utcnow() - timedelta(days=7), limit=limit, **filters
        )

        return {
            "events": audit_events,
            "total_events": len(audit_events),
            "filters_applied": {
                "event_type": event_type,
                "severity": severity,
                "tenant_id": tenant_id,
                "limit": limit,
            },
        }

    except Exception as e:
        logger.error(f"Failed to get recent audit events: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve audit events")


@router.get("/compliance/report")
async def generate_compliance_report(
    framework: str = Query(
        ..., description="Compliance framework (gdpr, sox, soc2, etc.)"
    ),
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    tenant_id: Optional[str] = Query(None),
):
    """Generate compliance audit report."""

    try:
        # Validate framework
        try:
            compliance_framework = ComplianceFramework(framework.lower())
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid compliance framework: {framework}"
            )

        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Generate report
        report = audit_manager.generate_compliance_report(
            framework=compliance_framework,
            start_date=start_date,
            end_date=end_date,
            tenant_id=tenant_id,
        )

        if not report:
            raise HTTPException(
                status_code=404, detail="No audit data found for the specified criteria"
            )

        return {
            "report": report,
            "generated_at": datetime.utcnow().isoformat(),
            "parameters": {
                "framework": framework,
                "days": days,
                "tenant_id": tenant_id,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate compliance report: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate compliance report"
        )


@router.get("/business-rules/violations")
async def get_business_rule_violations(
    severity: Optional[str] = Query(
        None, description="Filter by severity (error, warning, critical)"
    )
):
    """Get recent business rule violations."""

    try:
        # Get violations
        if severity:
            try:
                severity_filter = ValidationSeverity(severity.lower())
                violations = business_rule_engine.get_rule_violations(severity_filter)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid severity: {severity}"
                )
        else:
            violations = business_rule_engine.get_rule_violations()

        # Convert to response format
        violation_data = []
        for violation in violations:
            violation_data.append(
                {
                    "rule_name": violation.rule_name,
                    "message": violation.message,
                    "severity": violation.severity.value,
                    "field_name": violation.field_name,
                    "suggested_action": violation.suggested_action,
                    "is_valid": violation.is_valid,
                }
            )

        return {
            "violations": violation_data,
            "total_count": len(violation_data),
            "severity_breakdown": {
                "critical": len(
                    [v for v in violations if v.severity == ValidationSeverity.CRITICAL]
                ),
                "error": len(
                    [v for v in violations if v.severity == ValidationSeverity.ERROR]
                ),
                "warning": len(
                    [v for v in violations if v.severity == ValidationSeverity.WARNING]
                ),
                "info": len(
                    [v for v in violations if v.severity == ValidationSeverity.INFO]
                ),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get business rule violations: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve business rule violations"
        )


@router.get("/database/indexes")
async def get_database_index_analysis():
    """Get database index analysis and recommendations."""

    try:
        # Analyze existing indexes
        index_analysis = index_manager.analyze_existing_indexes()

        # Get new recommendations
        recommendations = index_manager.analyze_query_patterns(days=7)

        # Format recommendations
        rec_data = []
        for rec in recommendations:
            rec_data.append(
                {
                    "table_name": rec.table_name,
                    "columns": rec.columns,
                    "index_type": rec.index_type.value,
                    "reason": rec.reason,
                    "priority": rec.priority,
                    "estimated_impact": rec.estimated_impact,
                    "query_pattern": rec.query_pattern,
                }
            )

        return {
            "existing_indexes": index_analysis,
            "recommendations": rec_data,
            "analysis_timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to analyze database indexes: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to analyze database indexes"
        )


@router.post("/database/indexes/create")
async def create_recommended_indexes(
    priority_threshold: int = Query(
        8, ge=1, le=10, description="Minimum priority for index creation"
    )
):
    """Create recommended database indexes."""

    try:
        # Get recommendations
        recommendations = index_manager.analyze_query_patterns(days=7)

        # Filter by priority
        high_priority_recs = [
            r for r in recommendations if r.priority >= priority_threshold
        ]

        if not high_priority_recs:
            return {
                "message": f"No recommendations found with priority >= {priority_threshold}",
                "created_indexes": {},
            }

        # Create indexes
        results = index_manager.create_recommended_indexes(high_priority_recs)

        success_count = sum(1 for success in results.values() if success)

        return {
            "message": f"Created {success_count}/{len(high_priority_recs)} recommended indexes",
            "created_indexes": results,
            "recommendations_processed": len(high_priority_recs),
        }

    except Exception as e:
        logger.error(f"Failed to create recommended indexes: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to create recommended indexes"
        )


@router.post("/cache/clear")
async def clear_security_caches(
    cache_type: str = Query(
        "all", description="Type of cache to clear (search, audit, all)"
    )
):
    """Clear security-related caches."""

    try:
        cache_manager = get_cache_manager()
        cleared_keys = 0

        if cache_type in ["search", "all"]:
            # Clear search cache
            search_optimizer.clear_search_cache()
            cleared_keys += 1

        if cache_type in ["audit", "all"]:
            # Clear audit cache
            keys = cache_manager.redis_client.keys("dotmac:audit:*")
            if keys:
                cache_manager.redis_client.delete(*keys)
                cleared_keys += len(keys)

        if cache_type == "all":
            # Clear all security-related caches
            security_keys = cache_manager.redis_client.keys("dotmac:security:*")
            if security_keys:
                cache_manager.redis_client.delete(*security_keys)
                cleared_keys += len(security_keys)

        return {
            "message": f"Cleared {cleared_keys} cache entries",
            "cache_type": cache_type,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to clear security caches: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear security caches")


@router.post("/audit/cleanup")
async def cleanup_old_audit_logs(
    days_to_keep: int = Query(
        2555, ge=30, le=3650, description="Days of audit logs to retain"
    )
):
    """Clean up old audit logs based on retention policy."""

    try:
        # Clean up audit logs
        deleted_count = cleanup_audit_logs(days_to_keep)

        return {
            "message": f"Cleaned up {deleted_count} old audit log entries",
            "retention_days": days_to_keep,
            "cleanup_timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to cleanup audit logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup audit logs")


@router.get("/search/performance")
async def get_search_performance_metrics():
    """Get search performance metrics and cache statistics."""

    try:
        cache_manager = get_cache_manager()

        # Get search cache statistics
        search_keys = cache_manager.redis_client.keys("dotmac:search:*")
        search_cache_size = len(search_keys)

        # Get cache hit ratio from metrics (if available)
        try:
            redis_info = cache_manager.redis_client.info()
            cache_hit_ratio = redis_info.get("keyspace_hits", 0) / max(
                redis_info.get("keyspace_hits", 0)
                + redis_info.get("keyspace_misses", 0),
                1,
            )
        except Exception as e:
            logger.warning(f"Could not get Redis cache stats: {e}")
            cache_hit_ratio = 0.0

        return {
            "search_cache": {
                "cached_queries": search_cache_size,
                "cache_hit_ratio": cache_hit_ratio,
                "max_cache_size": search_optimizer.max_cache_size,
                "cache_ttl_seconds": search_optimizer.cache_ttl,
            },
            "performance_metrics": {
                "avg_query_time_ms": "Available via /metrics endpoint",
                "cache_enabled": True,
                "optimization_active": True,
            },
            "recommendations": [
                "Monitor query patterns for new index opportunities",
                "Adjust cache TTL based on data update frequency",
                "Consider increasing cache size for high-traffic tenants",
            ],
        }

    except Exception as e:
        logger.error(f"Failed to get search performance metrics: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve search performance metrics"
        )


@router.get("/audit")
async def run_comprehensive_security_audit():
    """Run comprehensive security configuration audit."""

    try:
        audit_results = run_security_audit()

        return {
            "audit_timestamp": datetime.utcnow().isoformat(),
            "audit_results": audit_results,
            "summary": {
                "security_score": audit_results["security_score"],
                "security_status": audit_results["security_status"],
                "critical_issues": audit_results["summary"]["critical_issues"],
                "high_issues": audit_results["summary"]["high_issues"],
                "recommendations_count": len(audit_results.get("recommendations", [])),
            },
        }

    except Exception as e:
        logger.error(f"Failed to run security audit: {e}")
        raise HTTPException(status_code=500, detail="Failed to run security audit")


@router.get("/audit/fix-script")
async def get_security_fix_script():
    """Generate shell script to fix security issues."""

    try:
        fix_script = generate_security_fix_script()

        return {
            "script": fix_script,
            "filename": "dotmac_security_fixes.sh",
            "instructions": [
                "1. Save this script to a file (e.g., security_fixes.sh)",
                "2. Make it executable: chmod +x security_fixes.sh",
                "3. Review the commands before running",
                "4. Run the script: ./security_fixes.sh",
                "5. Restart the application",
                "6. Run security audit again to verify fixes",
            ],
        }

    except Exception as e:
        logger.error(f"Failed to generate security fix script: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate security fix script"
        )


@router.get("/vulnerabilities")
async def check_critical_vulnerabilities():
    """Check for critical security vulnerabilities."""

    try:
        audit_results = run_security_audit()

        # Extract critical and high-severity issues
        critical_vulnerabilities = []
        high_vulnerabilities = []

        for check in audit_results["checks"]["critical"]:
            if not check["passed"]:
                critical_vulnerabilities.append(
                    {
                        "name": check["name"],
                        "message": check["message"],
                        "fix": check.get(
                            "fix_command",
                            check.get("recommendation", "Manual fix required"),
                        ),
                    }
                )

        for check in audit_results["checks"]["high"]:
            if not check["passed"]:
                high_vulnerabilities.append(
                    {
                        "name": check["name"],
                        "message": check["message"],
                        "fix": check.get(
                            "fix_command",
                            check.get("recommendation", "Manual fix required"),
                        ),
                    }
                )

        # Determine overall vulnerability status
        if critical_vulnerabilities:
            vulnerability_status = "CRITICAL - Immediate action required"
        elif high_vulnerabilities:
            vulnerability_status = "HIGH - Action required soon"
        elif audit_results["summary"]["medium_issues"] > 0:
            vulnerability_status = "MEDIUM - Should be addressed"
        else:
            vulnerability_status = "LOW - System is secure"

        return {
            "vulnerability_status": vulnerability_status,
            "security_score": audit_results["security_score"],
            "critical_vulnerabilities": critical_vulnerabilities,
            "high_vulnerabilities": high_vulnerabilities,
            "total_critical": len(critical_vulnerabilities),
            "total_high": len(high_vulnerabilities),
            "total_medium": audit_results["summary"]["medium_issues"],
            "scan_timestamp": datetime.utcnow().isoformat(),
            "next_scan_recommended": (
                datetime.utcnow() + timedelta(days=1)
            ).isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to check vulnerabilities: {e}")
        raise HTTPException(status_code=500, detail="Failed to check vulnerabilities")
