"""
Partner Branding API for whitelabeling support.

Provides comprehensive branding and whitelabeling capabilities for partners including:
- Brand configuration management (colors, logos, typography)
- Custom domain setup and verification
- Automated asset generation (CSS variables, color palettes)
- Theme configuration for frontend integration
- Public domain-based theme resolution

Leverages existing partner API patterns with DRY compliance.
"""

import colorsys
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID
import time

from fastapi import APIRouter, HTTPException, Depends, status, Path, Query
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from dotmac_shared.api.dependencies import (
    StandardDependencies,
    PaginatedDependencies,
    SearchParams,
    get_standard_deps,
    get_paginated_deps,
    get_admin_deps
)
from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.rate_limiting_decorators import (
    rate_limit_user,
    rate_limit_strict,
    RateLimitType
)
from dotmac_shared.observability.logging import get_logger
from dotmac_shared.database.optimized_queries import (
    get_partner_brand_config_optimized,
    get_brand_config_by_domain_optimized,
    get_partner_branding_bulk_optimized
)
from dotmac_shared.database.session import get_read_session

from ...models.partner_branding import (
    PartnerBrandConfig,
    BrandConfigCreate,
    BrandConfigUpdate,
    BrandConfigResponse,
    WhitelabelTheme,
)
from ...models.partner import Partner

logger = get_logger(__name__)
router = APIRouter(
    prefix="/partners",
    tags=["Partner Branding"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        500: {"description": "Internal server error"}
    }
)


@router.post(
    "/{partner_id}/brand",
    response_model=BrandConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Partner Brand Configuration",
    description="""
    Create a whitelabel brand configuration for a specific partner.
    
    **Business Context:**
    Brand configurations enable whitelabeling by allowing partners to customize:
    - Brand name, logo, and visual identity
    - Color schemes and typography
    - Custom domain and SSL configuration
    - Contact information and legal details
    
    This creates a complete branded experience for the partner's customers.
    """,
    responses={
        201: {
            "description": "Brand configuration created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "partner_id": "partner-456",
                        "brand_name": "Acme Solutions",
                        "primary_color": "#3b82f6",
                        "custom_domain": "portal.acme.com",
                        "is_active": True
                    }
                }
            }
        },
        404: {"description": "Partner not found"},
        409: {"description": "Brand configuration already exists"},
        500: {"description": "Internal server error"}
    },
    tags=["Partner Branding"],
    operation_id="createPartnerBrandConfig"
)
@rate_limit_strict(max_requests=10, time_window_seconds=60)  # Brand creation - strict limits
@standard_exception_handler
async def create_partner_brand_config(
    brand_data: BrandConfigCreate,
    partner_id: UUID = Path(
        ...,
        description="Unique identifier of the partner",
        example="123e4567-e89b-12d3-a456-426614174000"
    ),
    deps: StandardDependencies = Depends(get_standard_deps)
) -> BrandConfigResponse:
    """
    Create a whitelabel brand configuration for a specific partner.
    
    Args:
        partner_id: The UUID of the partner to create brand configuration for
        brand_data: Brand configuration details including colors, logo, domain
        deps: Standard dependencies including database session and authentication
        
    Returns:
        BrandConfigResponse: The created brand configuration with generated assets
        
    Raises:
        HTTPException: 404 if partner not found
        HTTPException: 409 if brand configuration already exists
        HTTPException: 500 if database operation fails
    """
    start_time = time.time()
    
    # Input validation logging for security auditing
    logger.info("Brand config creation requested", extra={
        "partner_id": str(partner_id),
        "user_id": getattr(deps.current_user, 'id', None),
        "brand_name": getattr(brand_data, 'brand_name', None),
        "operation": "create_brand_config"
    })
    
    try:
        # Verify partner exists and user has access
        partner_query = select(Partner).where(Partner.id == partner_id)
        result = await deps.db.execute(partner_query)
        partner = result.scalar_one_or_none()
        
        if not partner:
            logger.warning("Partner not found for brand config creation", extra={
                "partner_id": str(partner_id),
                "user_id": getattr(deps.current_user, 'id', None)
            })
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Partner not found"
            )
        
        # Check if brand config already exists
        existing_query = select(PartnerBrandConfig).where(PartnerBrandConfig.partner_id == partner_id)
        existing_result = await deps.db.execute(existing_query)
        existing_config = existing_result.scalar_one_or_none()
        
        if existing_config:
            logger.warning("Brand config already exists", extra={
                "partner_id": str(partner_id),
                "existing_config_id": getattr(existing_config, 'id', None),
                "user_id": getattr(deps.current_user, 'id', None)
            })
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Brand configuration already exists for this partner"
            )
        
        # Create brand configuration with transaction rollback support
        brand_config = PartnerBrandConfig(
            partner_id=partner_id,
            **brand_data.model_dump(exclude={'partner_id'})
        )
        
        # Generate derived brand assets
        brand_config.generated_assets = _generate_brand_assets(brand_data)
        
        deps.db.add(brand_config)
        await deps.db.commit()
        await deps.db.refresh(brand_config, ['partner'])
        
        # Log successful creation with performance metrics
        execution_time = time.time() - start_time
        logger.info("Brand config created successfully", extra={
            "partner_id": str(partner_id),
            "brand_config_id": getattr(brand_config, 'id', None),
            "user_id": getattr(deps.current_user, 'id', None),
            "execution_time_ms": round(execution_time * 1000, 2),
            "operation": "create_brand_config",
            "status": "success"
        })
        
        # Performance logging for slow operations
        if execution_time > 2.0:
            logger.warning("Slow brand config creation detected", extra={
                "partner_id": str(partner_id),
                "execution_time_ms": round(execution_time * 1000, 2),
                "performance_threshold_exceeded": True
            })
        
        return BrandConfigResponse.model_validate(brand_config)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Database rollback
        await deps.db.rollback()
        
        # Log unexpected errors with full context
        logger.error("Unexpected error creating brand config", extra={
            "partner_id": str(partner_id),
            "user_id": getattr(deps.current_user, 'id', None),
            "error": str(e),
            "error_type": type(e).__name__,
            "operation": "create_brand_config"
        })
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create brand configuration"
        )


@router.get(
    "/{partner_id}/brand",
    response_model=BrandConfigResponse,
    summary="Get Partner Brand Configuration",
    description="""
    Retrieve the brand configuration for a specific partner.
    
    **Business Context:**
    Returns the complete whitelabel configuration including visual assets,
    domain settings, and generated brand elements like CSS variables.
    Used for configuration management and frontend theme generation.
    """,
    responses={
        200: {
            "description": "Brand configuration retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "partner_id": "partner-456",
                        "brand_name": "Acme Solutions",
                        "primary_color": "#3b82f6",
                        "logo_url": "https://cdn.example.com/logo.png",
                        "custom_domain": "portal.acme.com",
                        "domain_verified": True,
                        "generated_assets": {
                            "css_variables": {"--color-primary-500": "#3b82f6"},
                            "color_palette": {"primary": {"500": "#3b82f6"}}
                        }
                    }
                }
            }
        },
        404: {"description": "Brand configuration not found"},
        500: {"description": "Internal server error"}
    },
    tags=["Partner Branding"],
    operation_id="getPartnerBrandConfig"
)
@rate_limit_user(max_requests=100, time_window_seconds=60)  # Read operations - normal user limits
@standard_exception_handler
async def get_partner_brand_config(
    partner_id: UUID = Path(
        ...,
        description="Unique identifier of the partner",
        example="123e4567-e89b-12d3-a456-426614174000"
    ),
    deps: StandardDependencies = Depends(get_standard_deps)
) -> BrandConfigResponse:
    """
    Retrieve the brand configuration for a specific partner using optimized query.
    
    Args:
        partner_id: The UUID of the partner to get brand configuration for
        deps: Standard dependencies including database session and authentication
        
    Returns:
        BrandConfigResponse: The partner's brand configuration with all assets
        
    Raises:
        HTTPException: 404 if brand configuration not found
        HTTPException: 500 if database operation fails
    """
    
    # Use optimized query with caching
    brand_config_data = await get_partner_brand_config_optimized(deps.db, partner_id)
    
    if not brand_config_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand configuration not found"
        )
    
    return BrandConfigResponse(**brand_config_data)


@router.put("/{partner_id}/brand", response_model=BrandConfigResponse)
@rate_limit_strict(max_requests=10, time_window_seconds=60)  # Brand updates - strict limits
@standard_exception_handler
async def update_partner_brand_config(
    partner_id: UUID,
    brand_data: BrandConfigUpdate,
    deps: StandardDependencies = Depends(get_standard_deps)
) -> BrandConfigResponse:
    """Update partner's brand configuration."""
    start_time = time.time()
    
    # Input validation logging for security auditing
    update_data = brand_data.model_dump(exclude_unset=True)
    logger.info("Brand config update requested", extra={
        "partner_id": str(partner_id),
        "user_id": getattr(deps.current_user, 'id', None),
        "fields_updated": list(update_data.keys()),
        "operation": "update_brand_config"
    })
    
    try:
        query = select(PartnerBrandConfig).where(PartnerBrandConfig.partner_id == partner_id)
        result = await deps.db.execute(query)
        brand_config = result.scalar_one_or_none()
        
        if not brand_config:
            logger.warning("Brand config not found for update", extra={
                "partner_id": str(partner_id),
                "user_id": getattr(deps.current_user, 'id', None)
            })
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Brand configuration not found"
            )
        
        # Store old values for audit logging
        old_values = {}
        for field in update_data.keys():
            old_values[field] = getattr(brand_config, field, None)
        
        # Update fields
        for field, value in update_data.items():
            setattr(brand_config, field, value)
        
        # Regenerate brand assets if colors changed
        color_fields = ['primary_color', 'secondary_color', 'accent_color', 'background_color', 'text_color']
        regenerate_assets = any(field in update_data for field in color_fields)
        if regenerate_assets:
            brand_config.generated_assets = _generate_brand_assets(brand_config)
            logger.debug("Brand assets regenerated due to color changes", extra={
                "partner_id": str(partner_id),
                "color_fields_changed": [f for f in color_fields if f in update_data]
            })
        
        await deps.db.commit()
        await deps.db.refresh(brand_config, ['partner'])
        
        # Log successful update with performance metrics
        execution_time = time.time() - start_time
        logger.info("Brand config updated successfully", extra={
            "partner_id": str(partner_id),
            "brand_config_id": getattr(brand_config, 'id', None),
            "user_id": getattr(deps.current_user, 'id', None),
            "fields_updated": list(update_data.keys()),
            "assets_regenerated": regenerate_assets,
            "execution_time_ms": round(execution_time * 1000, 2),
            "operation": "update_brand_config",
            "status": "success"
        })
        
        # Performance logging for slow operations
        if execution_time > 2.0:
            logger.warning("Slow brand config update detected", extra={
                "partner_id": str(partner_id),
                "execution_time_ms": round(execution_time * 1000, 2),
                "performance_threshold_exceeded": True
            })
        
        return BrandConfigResponse.model_validate(brand_config)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Database rollback
        await deps.db.rollback()
        
        # Log unexpected errors with full context
        logger.error("Unexpected error updating brand config", extra={
            "partner_id": str(partner_id),
            "user_id": getattr(deps.current_user, 'id', None),
            "fields_attempted": list(update_data.keys()),
            "error": str(e),
            "error_type": type(e).__name__,
            "operation": "update_brand_config"
        })
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update brand configuration"
        )


@router.delete("/{partner_id}/brand", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit_strict(max_requests=5, time_window_seconds=60)  # Delete operations - very strict limits
@standard_exception_handler
async def delete_partner_brand_config(
    partner_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps)
):
    """Delete partner's brand configuration."""
    start_time = time.time()
    
    # Input validation logging for security auditing
    logger.info("Brand config deletion requested", extra={
        "partner_id": str(partner_id),
        "user_id": getattr(deps.current_user, 'id', None),
        "operation": "delete_brand_config"
    })
    
    try:
        query = select(PartnerBrandConfig).where(PartnerBrandConfig.partner_id == partner_id)
        result = await deps.db.execute(query)
        brand_config = result.scalar_one_or_none()
        
        if not brand_config:
            logger.warning("Brand config not found for deletion", extra={
                "partner_id": str(partner_id),
                "user_id": getattr(deps.current_user, 'id', None)
            })
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Brand configuration not found"
            )
        
        # Store config details for audit logging before deletion
        brand_config_id = getattr(brand_config, 'id', None)
        brand_name = getattr(brand_config, 'brand_name', None)
        
        await deps.db.delete(brand_config)
        await deps.db.commit()
        
        # Log successful deletion with performance metrics
        execution_time = time.time() - start_time
        logger.info("Brand config deleted successfully", extra={
            "partner_id": str(partner_id),
            "brand_config_id": brand_config_id,
            "brand_name": brand_name,
            "user_id": getattr(deps.current_user, 'id', None),
            "execution_time_ms": round(execution_time * 1000, 2),
            "operation": "delete_brand_config",
            "status": "success"
        })
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Database rollback
        await deps.db.rollback()
        
        # Log unexpected errors with full context
        logger.error("Unexpected error deleting brand config", extra={
            "partner_id": str(partner_id),
            "user_id": getattr(deps.current_user, 'id', None),
            "error": str(e),
            "error_type": type(e).__name__,
            "operation": "delete_brand_config"
        })
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete brand configuration"
        )


@router.get("/{partner_id}/brand/theme", response_model=WhitelabelTheme)
@rate_limit_user(max_requests=100, time_window_seconds=60)  # Theme access - normal user limits
@standard_exception_handler
async def get_partner_theme(
    partner_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps)
) -> WhitelabelTheme:
    """Get partner's whitelabel theme configuration for frontend."""
    
    query = select(PartnerBrandConfig).options(
        selectinload(PartnerBrandConfig.partner)
    ).where(
        PartnerBrandConfig.partner_id == partner_id,
        PartnerBrandConfig.is_active == True
    )
    
    result = await deps.db.execute(query)
    brand_config = result.scalar_one_or_none()
    
    if not brand_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active brand configuration not found"
        )
    
    return _build_whitelabel_theme(brand_config)


@router.post("/{partner_id}/brand/verify-domain")
@rate_limit_strict(max_requests=10, time_window_seconds=60)  # Domain verification - strict limits
@standard_exception_handler
async def verify_partner_domain(
    partner_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps)
) -> Dict[str, Any]:
    """Verify partner's custom domain configuration."""
    start_time = time.time()
    
    # Input validation logging for security auditing
    logger.info("Domain verification requested", extra={
        "partner_id": str(partner_id),
        "user_id": getattr(deps.current_user, 'id', None),
        "operation": "verify_domain"
    })
    
    try:
        query = select(PartnerBrandConfig).where(PartnerBrandConfig.partner_id == partner_id)
        result = await deps.db.execute(query)
        brand_config = result.scalar_one_or_none()
        
        if not brand_config or not brand_config.custom_domain:
            logger.warning("No custom domain configured for verification", extra={
                "partner_id": str(partner_id),
                "user_id": getattr(deps.current_user, 'id', None),
                "has_brand_config": brand_config is not None,
                "has_domain": bool(getattr(brand_config, 'custom_domain', None)) if brand_config else False
            })
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No custom domain configured"
            )
        
        domain = brand_config.custom_domain
        logger.info("Starting domain verification", extra={
            "partner_id": str(partner_id),
            "domain": domain,
            "user_id": getattr(deps.current_user, 'id', None)
        })
        
        # Perform domain verification
        verification_result = await _verify_domain(domain)
        
        # Update verification status
        old_verification_status = brand_config.domain_verified
        brand_config.domain_verified = verification_result['verified']
        await deps.db.commit()
        
        # Log verification result with performance metrics
        execution_time = time.time() - start_time
        logger.info("Domain verification completed", extra={
            "partner_id": str(partner_id),
            "domain": domain,
            "user_id": getattr(deps.current_user, 'id', None),
            "verification_successful": verification_result['verified'],
            "status_changed": old_verification_status != verification_result['verified'],
            "execution_time_ms": round(execution_time * 1000, 2),
            "operation": "verify_domain",
            "status": "success"
        })
        
        # Performance logging for slow operations
        if execution_time > 5.0:
            logger.warning("Slow domain verification detected", extra={
                "partner_id": str(partner_id),
                "domain": domain,
                "execution_time_ms": round(execution_time * 1000, 2),
                "performance_threshold_exceeded": True
            })
        
        return verification_result
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Database rollback
        await deps.db.rollback()
        
        # Log unexpected errors with full context
        logger.error("Unexpected error during domain verification", extra={
            "partner_id": str(partner_id),
            "user_id": getattr(deps.current_user, 'id', None),
            "error": str(e),
            "error_type": type(e).__name__,
            "operation": "verify_domain"
        })
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify domain"
        )


@router.get("/by-domain/{domain}/theme", response_model=WhitelabelTheme)
@rate_limit_user(max_requests=20, time_window_seconds=60)  # Public domain theme access - moderate limits
@standard_exception_handler
async def get_theme_by_domain(
    domain: str,
    deps: StandardDependencies = Depends(get_standard_deps)
) -> WhitelabelTheme:
    """Get whitelabel theme by custom domain using optimized cached query."""
    
    # Use optimized query with domain-based caching
    theme_data = await get_brand_config_by_domain_optimized(deps.db, domain)
    
    if not theme_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No verified brand configuration found for domain"
        )
    
    # Convert to WhitelabelTheme format
    return WhitelabelTheme(
        brand=theme_data["brand"],
        colors=theme_data["colors"],
        typography=theme_data["typography"],
        domain=theme_data["domain"],
        contact={
            "email": "",
            "phone": "",
            "support_url": ""
        },
        legal={
            "company_name": theme_data["brand"]["name"],
            "privacy_url": "",
            "terms_url": "",
            "address": ""
        },
        social={
            "website": "",
            "facebook": "",
            "twitter": "",
            "linkedin": ""
        },
        css_variables=theme_data["css_variables"],
        custom_css=theme_data["custom_css"]
    )


# === HELPER FUNCTIONS ===

def _generate_brand_assets(brand_config: Any) -> Dict[str, Any]:
    """Generate derived brand assets from base configuration."""
    
    # Extract base colors
    primary = brand_config.primary_color if hasattr(brand_config, 'primary_color') else brand_config.get('primary_color', '#3b82f6')
    secondary = brand_config.secondary_color if hasattr(brand_config, 'secondary_color') else brand_config.get('secondary_color', '#22c55e')
    accent = brand_config.accent_color if hasattr(brand_config, 'accent_color') else brand_config.get('accent_color', '#f97316')
    
    # Generate color palette variations
    color_palette = {
        'primary': _generate_color_shades(primary),
        'secondary': _generate_color_shades(secondary),
        'accent': _generate_color_shades(accent),
    }
    
    # Generate CSS variables
    css_variables = {}
    for color_name, shades in color_palette.items():
        for shade, color_value in shades.items():
            css_variables[f'--color-{color_name}-{shade}'] = color_value
    
    return {
        'color_palette': color_palette,
        'css_variables': css_variables,
        'theme_preview': f"linear-gradient(135deg, {primary} 0%, {secondary} 50%, {accent} 100%)",
        'generated_at': datetime.utcnow().isoformat()
    }


def _generate_color_shades(hex_color: str) -> Dict[str, str]:
    """Generate color shade variations from base hex color."""
    
    # Remove # if present
    hex_color = hex_color.lstrip('#')
    
    # Convert to RGB
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    # Convert to HSL for easier manipulation
    h, s, l = colorsys.rgb_to_hls(r/255.0, g/255.0, b/255.0)
    
    # Generate shades
    shades = {}
    shade_levels = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900]
    
    for i, level in enumerate(shade_levels):
        # Adjust lightness based on shade level
        if level <= 500:
            # Lighter shades
            new_l = l + (1 - l) * (1 - level / 500) * 0.4
        else:
            # Darker shades  
            new_l = l * (1 - (level - 500) / 500 * 0.6)
        
        # Convert back to RGB
        new_r, new_g, new_b = colorsys.hls_to_rgb(h, new_l, s)
        
        # Convert to hex
        hex_value = f"#{int(new_r*255):02x}{int(new_g*255):02x}{int(new_b*255):02x}"
        shades[str(level)] = hex_value
    
    return shades


def _build_whitelabel_theme(brand_config: PartnerBrandConfig) -> WhitelabelTheme:
    """Build whitelabel theme object from brand configuration."""
    
    return WhitelabelTheme(
        brand={
            'name': brand_config.brand_name,
            'tagline': brand_config.tagline or '',
            'logo': brand_config.logo_url or '',
            'logo_dark': brand_config.logo_dark_url or '',
            'favicon': brand_config.favicon_url or '',
        },
        colors={
            'primary': brand_config.primary_color,
            'secondary': brand_config.secondary_color,
            'accent': brand_config.accent_color,
            'background': brand_config.background_color,
            'text': brand_config.text_color,
        },
        typography={
            'font_family': brand_config.font_family,
            'font_url': brand_config.font_url or '',
        },
        domain={
            'custom': brand_config.custom_domain,
            'ssl': brand_config.ssl_enabled,
            'verified': brand_config.domain_verified,
        },
        contact={
            'email': brand_config.support_email or '',
            'phone': brand_config.support_phone or '',
            'support_url': brand_config.support_url or '',
        },
        legal={
            'company_name': brand_config.company_legal_name or brand_config.brand_name,
            'privacy_url': brand_config.privacy_policy_url or '',
            'terms_url': brand_config.terms_of_service_url or '',
            'address': brand_config.address or '',
        },
        social={
            'website': brand_config.website_url or '',
            'facebook': brand_config.facebook_url or '',
            'twitter': brand_config.twitter_url or '',
            'linkedin': brand_config.linkedin_url or '',
        },
        css_variables=brand_config.generated_assets.get('css_variables', {}),
        custom_css=brand_config.brand_config.get('custom_css', ''),
    )


async def _verify_domain(domain: str) -> Dict[str, Any]:
    """Verify domain configuration and SSL certificate."""
    
    import asyncio
    import socket
    import ssl
    
    try:
        # Basic DNS resolution
        ip_address = socket.gethostbyname(domain)
        
        # SSL certificate check
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                ssl_valid = True
                ssl_expires = cert.get('notAfter', '')
        
        return {
            'verified': True,
            'ip_address': ip_address,
            'ssl_valid': ssl_valid,
            'ssl_expires': ssl_expires,
            'verified_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            'verified': False,
            'error': str(e),
            'verified_at': datetime.utcnow().isoformat()
        }