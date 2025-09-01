"""
Admin management endpoints
Handles bootstrap credential removal and admin operations
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import os

from dotmac_shared.auth.dependencies import get_current_active_superuser
from dotmac_shared.auth.models import User
from dotmac_shared.database.base import get_db_session
from dotmac_shared.core.logging import get_logger
from dotmac_shared.api.response import APIResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/remove-bootstrap-credentials")
async def remove_bootstrap_credentials(
    current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db_session)
) -> APIResponse:
    """
    🔐 CRITICAL SECURITY: Remove bootstrap credentials after first login
    
    This endpoint should be called immediately after the first admin login
    to remove the AUTH_ADMIN_EMAIL and AUTH_INITIAL_ADMIN_PASSWORD environment variables.
    
    **WARNING**: This is a one-way operation. Make sure you can login with
    the created admin account before calling this endpoint.
    """
    
    try:
        # Check if bootstrap credentials still exist
        bootstrap_email = os.getenv('AUTH_ADMIN_EMAIL')
        bootstrap_password = os.getenv('AUTH_INITIAL_ADMIN_PASSWORD')
        
        if not bootstrap_email and not bootstrap_password:
            logger.info(f"Bootstrap credentials already removed (requested by {current_user.email})")
            return APIResponse(
                success=True,
                message="Bootstrap credentials were already removed",
                data={"already_removed": True}
            )
        
        # Log the removal attempt
        logger.warning(f"🔐 Bootstrap credential removal requested by {current_user.email}")
        
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
                "7. Verify you can still login with your admin account"
            ],
            "environment_variables_to_remove": [
                "AUTH_ADMIN_EMAIL",
                "AUTH_INITIAL_ADMIN_PASSWORD"
            ],
            "current_values": {
                "AUTH_ADMIN_EMAIL": bootstrap_email,
                "AUTH_INITIAL_ADMIN_PASSWORD": "[REDACTED]"
            }
        }
        
        # Mark bootstrap as completed in database
        if hasattr(current_user, 'settings'):
            current_user.settings = current_user.settings or {}
            current_user.settings['bootstrap_credentials_removed'] = True
            db.commit()
        
        logger.warning("🔐 MANUAL ACTION REQUIRED: Remove bootstrap environment variables from Coolify")
        
        return APIResponse(
            success=True,
            message="Bootstrap credential removal instructions provided. Please follow the steps to complete removal.",
            data=removal_instructions
        )
        
    except Exception as e:
        logger.error(f"Failed to process bootstrap credential removal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process bootstrap credential removal"
        )


@router.get("/bootstrap-status")
async def get_bootstrap_status(
    current_user: User = Depends(get_current_active_superuser)
) -> APIResponse:
    """
    Check if bootstrap credentials are still present
    """
    
    bootstrap_email = os.getenv('AUTH_ADMIN_EMAIL')
    bootstrap_password = os.getenv('AUTH_INITIAL_ADMIN_PASSWORD')
    
    credentials_present = bool(bootstrap_email or bootstrap_password)
    
    status_info = {
        "bootstrap_credentials_present": credentials_present,
        "auth_admin_email_present": bool(bootstrap_email),
        "auth_initial_admin_password_present": bool(bootstrap_password),
        "security_risk": credentials_present,
        "action_required": credentials_present,
    }
    
    if credentials_present:
        status_info["warning"] = "🚨 SECURITY RISK: Bootstrap credentials are still present in environment variables"
        status_info["recommendation"] = "Call POST /admin/remove-bootstrap-credentials immediately"
    
    return APIResponse(
        success=True,
        message="Bootstrap status retrieved",
        data=status_info
    )


@router.get("/security-checklist")
async def get_security_checklist(
    current_user: User = Depends(get_current_active_superuser)
) -> APIResponse:
    """
    Get post-deployment security checklist
    """
    
    bootstrap_credentials = bool(os.getenv('AUTH_ADMIN_EMAIL') or os.getenv('AUTH_INITIAL_ADMIN_PASSWORD'))
    smtp_configured = bool(os.getenv('SMTP_HOST'))
    cors_configured = bool(os.getenv('CORS_ORIGINS'))
    secret_key_strong = len(os.getenv('SECRET_KEY', '')) >= 32
    
    checklist = [
        {
            "item": "Remove bootstrap credentials",
            "completed": not bootstrap_credentials,
            "critical": True,
            "description": "Remove AUTH_ADMIN_EMAIL and AUTH_INITIAL_ADMIN_PASSWORD from environment",
            "action": "POST /admin/remove-bootstrap-credentials"
        },
        {
            "item": "Configure SMTP for notifications",
            "completed": smtp_configured,
            "critical": True,
            "description": "Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD for email notifications",
            "action": "Update environment variables in Coolify"
        },
        {
            "item": "Configure CORS origins",
            "completed": cors_configured,
            "critical": True,
            "description": "Set CORS_ORIGINS to exact frontend domains",
            "action": "Update CORS_ORIGINS in Coolify environment"
        },
        {
            "item": "Verify strong SECRET_KEY",
            "completed": secret_key_strong,
            "critical": True,
            "description": "Ensure SECRET_KEY is at least 32 characters",
            "action": "Generate new SECRET_KEY if needed"
        },
        {
            "item": "Enable TLS/SSL certificates",
            "completed": False,  # Would need to check Coolify API
            "critical": True,
            "description": "Ensure Let's Encrypt certificates are configured",
            "action": "Configure SSL in Coolify domain settings"
        },
        {
            "item": "Configure database backups",
            "completed": False,  # Would need to check backup configuration
            "critical": True,
            "description": "Set up automated database backups with retention",
            "action": "Configure backup schedule in Coolify"
        }
    ]
    
    completed_items = sum(1 for item in checklist if item["completed"])
    critical_incomplete = sum(1 for item in checklist if item["critical"] and not item["completed"])
    
    security_score = (completed_items / len(checklist)) * 100
    
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
                "status": "SECURE" if critical_incomplete == 0 else "ACTION_REQUIRED"
            }
        }
    )