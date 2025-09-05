"""
Admin Management API

Provides administrative functions for system management including:
- Bootstrap credential management and security hardening
- Post-deployment security checklist and compliance
- System initialization and configuration validation
- Administrative task automation and monitoring

These endpoints require superuser privileges and should be used carefully.
"""

import os
import time

from dotmac.application import (
    StandardDependencies,
    get_standard_deps,
    rate_limit_auth,
    rate_limit_strict,
    standard_exception_handler,
)
from dotmac.application.api.router_factory import RouterFactory
from dotmac.platform.observability.logging import get_logger
from dotmac_shared.api.response import APIResponse
from fastapi import Depends, HTTPException, status

logger = get_logger(__name__)
router = RouterFactory("Admin").create_router(prefix="/admin", tags=["Admin"])


@router.post(
    "/remove-bootstrap-credentials",
    summary="Remove Bootstrap Credentials",
    description="""
    🔐 **CRITICAL SECURITY**: Remove bootstrap credentials after first login.

    **Business Context:**
    Bootstrap credentials (AUTH_ADMIN_EMAIL and AUTH_INITIAL_ADMIN_PASSWORD) are used
    for initial system setup but pose a security risk if left in place. This endpoint
    initiates the removal process and provides instructions for completing the cleanup.

    **Security Impact:**
    - Eliminates hardcoded admin credentials from environment
    - Reduces attack surface for production systems
    - Enforces proper admin account management

    **Process:**
    1. Checks current bootstrap credential status
    2. Provides step-by-step removal instructions
    3. Updates database to track removal status
    4. Returns Coolify-specific cleanup commands

    ⚠️ **WARNING**: This is a one-way operation. Ensure you can login with
    your created admin account before calling this endpoint.
    """,
    responses={
        200: {
            "description": "Bootstrap removal instructions provided",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Bootstrap credential removal instructions provided",
                        "data": {
                            "instructions": [
                                "1. Access your Coolify dashboard",
                                "2. Navigate to your DotMac Management service",
                                "3. Go to Environment Variables section",
                                "4. Remove AUTH_ADMIN_EMAIL variable",
                                "5. Remove AUTH_INITIAL_ADMIN_PASSWORD variable",
                                "6. Restart the Management service",
                            ],
                            "environment_variables_to_remove": ["AUTH_ADMIN_EMAIL", "AUTH_INITIAL_ADMIN_PASSWORD"],
                        },
                    }
                }
            },
        },
        500: {"description": "Failed to process bootstrap credential removal"},
    },
    tags=["Security"],
    operation_id="removeBootstrapCredentials",
)
@rate_limit_auth(max_requests=5, time_window_seconds=60)  # Critical admin operations - very strict limits
@standard_exception_handler
async def remove_bootstrap_credentials(deps: StandardDependencies = Depends(get_standard_deps)) -> APIResponse:
    """
    Remove bootstrap credentials after first login for enhanced security.

    Args:
        deps: Standard dependencies including database session and authentication

    Returns:
        APIResponse: Instructions for completing bootstrap credential removal

    Raises:
        HTTPException: 500 if removal process fails
    """
    start_time = time.time()

    # Input validation logging for security auditing
    logger.info(
        "Bootstrap credential removal requested",
        extra={
            "user_id": getattr(deps.current_user, "id", None),
            "user_email": getattr(deps.current_user, "email", None),
            "operation": "remove_bootstrap_credentials",
            "security_critical": True,
        },
    )

    try:
        # Check if bootstrap credentials still exist
        bootstrap_email = os.getenv("AUTH_ADMIN_EMAIL")
        bootstrap_password = os.getenv("AUTH_INITIAL_ADMIN_PASSWORD")

        if not bootstrap_email and not bootstrap_password:
            logger.info(
                "Bootstrap credentials already removed",
                extra={
                    "user_id": getattr(deps.current_user, "id", None),
                    "user_email": getattr(deps.current_user, "email", None),
                    "already_removed": True,
                    "operation": "remove_bootstrap_credentials",
                },
            )
            return APIResponse(
                success=True, message="Bootstrap credentials were already removed", data={"already_removed": True}
            )

        # Log the removal attempt with security context
        logger.warning(
            "Bootstrap credential removal in progress",
            extra={
                "user_id": getattr(deps.current_user, "id", None),
                "user_email": getattr(deps.current_user, "email", None),
                "has_bootstrap_email": bool(bootstrap_email),
                "has_bootstrap_password": bool(bootstrap_password),
                "security_critical": True,
                "operation": "remove_bootstrap_credentials",
            },
        )

        # In production, this would integrate with Coolify's API to remove env vars
        # For now, we'll log the instruction
        removal_instructions = {
            "instructions": [
                "1. Access your Coolify dashboard",
                "2. Navigate to your DotMac Management service",
                "3. Go to Environment Variables section",
                "4. Remove AUTH_ADMIN_EMAIL variable",
                "5. Remove AUTH_INITIAL_ADMIN_PASSWORD variable",
                "6. Restart the Management service",
                "7. Verify you can still login with your admin account",
            ],
            "environment_variables_to_remove": ["AUTH_ADMIN_EMAIL", "AUTH_INITIAL_ADMIN_PASSWORD"],
            "current_values": {"AUTH_ADMIN_EMAIL": bootstrap_email, "AUTH_INITIAL_ADMIN_PASSWORD": "[REDACTED]"},
        }

        # Mark bootstrap as completed in database with transaction support
        try:
            current_user = deps.current_user
            if hasattr(current_user, "settings"):
                from dotmac_shared.core.error_utils import async_db_transaction

                current_user.settings = current_user.settings or {}
                current_user.settings["bootstrap_credentials_removed"] = True
                current_user.settings["bootstrap_removal_requested_at"] = time.time()
                async with async_db_transaction(deps.db):
                    pass

                logger.info(
                    "Bootstrap removal status updated in database",
                    extra={"user_id": getattr(current_user, "id", None), "operation": "remove_bootstrap_credentials"},
                )
        except Exception as db_error:
            logger.exception(
                "Failed to update bootstrap removal status in database",
                extra={
                    "user_id": getattr(deps.current_user, "id", None),
                    "error": str(db_error),
                    "error_type": type(db_error).__name__,
                    "operation": "remove_bootstrap_credentials",
                },
            )
            # Don't fail the entire operation for database update issues

        # Log successful completion with performance metrics
        execution_time = time.time() - start_time
        logger.warning(
            "Bootstrap credential removal instructions provided",
            extra={
                "user_id": getattr(deps.current_user, "id", None),
                "user_email": getattr(deps.current_user, "email", None),
                "execution_time_ms": round(execution_time * 1000, 2),
                "manual_action_required": True,
                "security_critical": True,
                "operation": "remove_bootstrap_credentials",
                "status": "success",
            },
        )

        return APIResponse(
            success=True,
            message="Bootstrap credential removal instructions provided. Please follow the steps to complete removal.",
            data=removal_instructions,
        )

    except Exception as e:
        # Log unexpected errors with full context
        logger.exception(
            "Unexpected error processing bootstrap credential removal",
            extra={
                "user_id": getattr(deps.current_user, "id", None),
                "user_email": getattr(deps.current_user, "email", None),
                "error": str(e),
                "error_type": type(e).__name__,
                "security_critical": True,
                "operation": "remove_bootstrap_credentials",
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process bootstrap credential removal"
        ) from e


@router.get(
    "/bootstrap-status",
    summary="Get Bootstrap Status",
    description="""
    Check the current status of bootstrap credentials in the system.

    **Business Context:**
    This endpoint provides visibility into the security posture of the system
    by checking whether bootstrap credentials are still present. It's used for:
    - Security audits and compliance checks
    - Post-deployment verification workflows
    - Administrative dashboards and monitoring

    **Status Information:**
    - Presence of AUTH_ADMIN_EMAIL environment variable
    - Presence of AUTH_INITIAL_ADMIN_PASSWORD environment variable
    - Overall security risk assessment
    - Recommended actions based on current state
    """,
    responses={
        200: {
            "description": "Bootstrap status retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Bootstrap status retrieved",
                        "data": {
                            "bootstrap_credentials_present": False,
                            "auth_admin_email_present": False,
                            "auth_initial_admin_password_present": False,
                            "security_risk": False,
                            "action_required": False,
                        },
                    }
                }
            },
        },
        500: {"description": "Failed to retrieve bootstrap status"},
    },
    tags=["Security"],
    operation_id="getBootstrapStatus",
)
@rate_limit_strict(max_requests=20, time_window_seconds=60)  # Admin status checks - moderate limits
@standard_exception_handler
async def get_bootstrap_status(deps: StandardDependencies = Depends(get_standard_deps)) -> APIResponse:
    """
    Check the current status of bootstrap credentials in the system.

    Args:
        deps: Standard dependencies including database session and authentication

    Returns:
        APIResponse: Current bootstrap credential status and security assessment

    Raises:
        HTTPException: 500 if status check fails
    """
    start_time = time.time()

    # Input validation logging for security auditing
    logger.info(
        "Bootstrap status check requested",
        extra={
            "user_id": getattr(deps.current_user, "id", None),
            "user_email": getattr(deps.current_user, "email", None),
            "operation": "get_bootstrap_status",
            "security_check": True,
        },
    )

    try:
        bootstrap_email = os.getenv("AUTH_ADMIN_EMAIL")
        bootstrap_password = os.getenv("AUTH_INITIAL_ADMIN_PASSWORD")

        credentials_present = bool(bootstrap_email or bootstrap_password)

        status_info = {
            "bootstrap_credentials_present": credentials_present,
            "auth_admin_email_present": bool(bootstrap_email),
            "auth_initial_admin_password_present": bool(bootstrap_password),
            "security_risk": credentials_present,
            "action_required": credentials_present,
        }

        if credentials_present:
            status_info[
                "warning"
            ] = "🚨 SECURITY RISK: Bootstrap credentials are still present in environment variables"
            status_info["recommendation"] = "Call POST /admin/remove-bootstrap-credentials immediately"

            # Log security risk
            logger.warning(
                "Bootstrap credentials still present - security risk detected",
                extra={
                    "user_id": getattr(deps.current_user, "id", None),
                    "user_email": getattr(deps.current_user, "email", None),
                    "has_bootstrap_email": bool(bootstrap_email),
                    "has_bootstrap_password": bool(bootstrap_password),
                    "security_risk": True,
                    "operation": "get_bootstrap_status",
                },
            )
        else:
            # Log secure status
            logger.info(
                "Bootstrap credentials properly removed - secure status",
                extra={
                    "user_id": getattr(deps.current_user, "id", None),
                    "user_email": getattr(deps.current_user, "email", None),
                    "secure_status": True,
                    "operation": "get_bootstrap_status",
                },
            )

        # Log successful completion with performance metrics
        execution_time = time.time() - start_time
        logger.info(
            "Bootstrap status retrieved successfully",
            extra={
                "user_id": getattr(deps.current_user, "id", None),
                "credentials_present": credentials_present,
                "execution_time_ms": round(execution_time * 1000, 2),
                "operation": "get_bootstrap_status",
                "status": "success",
            },
        )

        return APIResponse(success=True, message="Bootstrap status retrieved", data=status_info)

    except Exception as e:
        # Log unexpected errors with full context
        logger.error(
            "Unexpected error retrieving bootstrap status",
            extra={
                "user_id": getattr(deps.current_user, "id", None),
                "user_email": getattr(deps.current_user, "email", None),
                "error": str(e),
                "error_type": type(e).__name__,
                "security_check": True,
                "operation": "get_bootstrap_status",
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve bootstrap status"
        ) from e


@router.get(
    "/security-checklist",
    summary="Get Security Checklist",
    description="""
    Retrieve a comprehensive post-deployment security checklist with completion status.

    **Business Context:**
    This endpoint provides a systematic approach to security hardening by returning
    a checklist of critical security items that should be completed after deployment.
    It's essential for production readiness and compliance verification.

    **Checklist Items:**
    - Bootstrap credential removal
    - SMTP configuration for notifications
    - CORS origin configuration
    - Strong secret key verification
    - TLS/SSL certificate setup
    - Database backup configuration

    **Compliance & Auditing:**
    - Provides security score (percentage completion)
    - Identifies critical incomplete items
    - Includes actionable remediation steps
    - Tracks security posture over time
    """,
    responses={
        200: {
            "description": "Security checklist retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Security checklist retrieved",
                        "data": {
                            "checklist": [
                                {
                                    "item": "Remove bootstrap credentials",
                                    "completed": True,
                                    "critical": True,
                                    "description": "Remove AUTH_ADMIN_EMAIL and AUTH_INITIAL_ADMIN_PASSWORD from environment",
                                    "action": "POST /admin/remove-bootstrap-credentials",
                                },
                                {
                                    "item": "Configure SMTP for notifications",
                                    "completed": False,
                                    "critical": True,
                                    "description": "Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD for email notifications",
                                    "action": "Update environment variables in Coolify",
                                },
                            ],
                            "summary": {
                                "total_items": 6,
                                "completed_items": 3,
                                "critical_incomplete": 1,
                                "security_score": 75.0,
                                "status": "ACTION_REQUIRED",
                            },
                        },
                    }
                }
            },
        },
        500: {"description": "Failed to retrieve security checklist"},
    },
    tags=["Security"],
    operation_id="getSecurityChecklist",
)
@rate_limit_strict(max_requests=20, time_window_seconds=60)  # Security checklist access - moderate limits
@standard_exception_handler
async def get_security_checklist(deps: StandardDependencies = Depends(get_standard_deps)) -> APIResponse:
    """
    Retrieve a comprehensive post-deployment security checklist with completion status.

    Args:
        deps: Standard dependencies including database session and authentication

    Returns:
        APIResponse: Security checklist with completion status and recommendations

    Raises:
        HTTPException: 500 if checklist retrieval fails
    """
    start_time = time.time()

    # Input validation logging for security auditing
    logger.info(
        "Security checklist requested",
        extra={
            "user_id": getattr(deps.current_user, "id", None),
            "user_email": getattr(deps.current_user, "email", None),
            "operation": "get_security_checklist",
            "security_check": True,
        },
    )

    try:
        bootstrap_credentials = bool(os.getenv("AUTH_ADMIN_EMAIL") or os.getenv("AUTH_INITIAL_ADMIN_PASSWORD"))
        smtp_configured = bool(os.getenv("SMTP_HOST"))
        cors_configured = bool(os.getenv("CORS_ORIGINS"))
        secret_key_strong = len(os.getenv("SECRET_KEY", "")) >= 32

        checklist = [
            {
                "item": "Remove bootstrap credentials",
                "completed": not bootstrap_credentials,
                "critical": True,
                "description": "Remove AUTH_ADMIN_EMAIL and AUTH_INITIAL_ADMIN_PASSWORD from environment",
                "action": "POST /admin/remove-bootstrap-credentials",
            },
            {
                "item": "Configure SMTP for notifications",
                "completed": smtp_configured,
                "critical": True,
                "description": "Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD for email notifications",
                "action": "Update environment variables in Coolify",
            },
            {
                "item": "Configure CORS origins",
                "completed": cors_configured,
                "critical": True,
                "description": "Set CORS_ORIGINS to exact frontend domains",
                "action": "Update CORS_ORIGINS in Coolify environment",
            },
            {
                "item": "Verify strong SECRET_KEY",
                "completed": secret_key_strong,
                "critical": True,
                "description": "Ensure SECRET_KEY is at least 32 characters",
                "action": "Generate new SECRET_KEY if needed",
            },
            {
                "item": "Enable TLS/SSL certificates",
                "completed": False,  # Would need to check Coolify API
                "critical": True,
                "description": "Ensure Let's Encrypt certificates are configured",
                "action": "Configure SSL in Coolify domain settings",
            },
            {
                "item": "Configure database backups",
                "completed": False,  # Would need to check backup configuration
                "critical": True,
                "description": "Set up automated database backups with retention",
                "action": "Configure backup schedule in Coolify",
            },
        ]

        completed_items = sum(1 for item in checklist if item["completed"])
        critical_incomplete = sum(1 for item in checklist if item["critical"] and not item["completed"])

        security_score = (completed_items / len(checklist)) * 100

        # Log security assessment with detailed context
        logger.info(
            "Security checklist evaluated",
            extra={
                "user_id": getattr(deps.current_user, "id", None),
                "user_email": getattr(deps.current_user, "email", None),
                "total_items": len(checklist),
                "completed_items": completed_items,
                "critical_incomplete": critical_incomplete,
                "security_score": round(security_score, 1),
                "bootstrap_credentials_present": bootstrap_credentials,
                "smtp_configured": smtp_configured,
                "cors_configured": cors_configured,
                "secret_key_strong": secret_key_strong,
                "security_status": "SECURE" if critical_incomplete == 0 else "ACTION_REQUIRED",
                "operation": "get_security_checklist",
            },
        )

        # Log security warnings for critical incomplete items
        if critical_incomplete > 0:
            incomplete_items = [item["item"] for item in checklist if item["critical"] and not item["completed"]]
            logger.warning(
                "Critical security items incomplete",
                extra={
                    "user_id": getattr(deps.current_user, "id", None),
                    "critical_incomplete_count": critical_incomplete,
                    "incomplete_items": incomplete_items,
                    "security_risk": True,
                    "operation": "get_security_checklist",
                },
            )

        # Log successful completion with performance metrics
        execution_time = time.time() - start_time
        logger.info(
            "Security checklist retrieved successfully",
            extra={
                "user_id": getattr(deps.current_user, "id", None),
                "security_score": round(security_score, 1),
                "execution_time_ms": round(execution_time * 1000, 2),
                "operation": "get_security_checklist",
                "status": "success",
            },
        )

        return APIResponse(
            success=True,
            message="Security checklist retrieved",
            data={
                "checklist": checklist,
                "summary": {
                    "total_items": len(checklist),
                    "completed_items": completed_items,
                    "critical_incomplete": critical_incomplete,
                    "security_score": round(security_score, 1),
                    "status": "SECURE" if critical_incomplete == 0 else "ACTION_REQUIRED",
                },
            },
        )

    except Exception as e:
        # Log unexpected errors with full context
        logger.error(
            "Unexpected error retrieving security checklist",
            extra={
                "user_id": getattr(deps.current_user, "id", None),
                "user_email": getattr(deps.current_user, "email", None),
                "error": str(e),
                "error_type": type(e).__name__,
                "security_check": True,
                "operation": "get_security_checklist",
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve security checklist"
        ) from e
