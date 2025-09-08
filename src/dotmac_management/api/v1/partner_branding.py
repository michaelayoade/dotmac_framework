"""
Partner Branding API for whitelabeling support.

Provides comprehensive branding and whitelabeling capabilities for partners including:
- Brand configuration management (colors, logos, typography)
- Custom domain setup and verification
- Automated asset generation (CSS variables, color palettes)
- Theme configuration for frontend integration
- Public domain-based theme resolution

Follows DRY patterns using dotmac packages for consistent API structure.
"""

import colorsys
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Path, status

from dotmac.application import standard_exception_handler
from dotmac.application.dependencies.dependencies import (
    StandardDependencies,
    get_standard_deps,
)
from dotmac.platform.observability.logging import get_logger
from dotmac_shared.api.rate_limiting_decorators import rate_limit, rate_limit_strict

from ...models.partner import Partner
from ...models.partner_branding import (
    BrandConfigCreate,
    BrandConfigResponse,
    BrandConfigUpdate,
    PartnerBrandConfig,
    WhitelabelTheme,
)

logger = get_logger(__name__)
router = APIRouter(
    prefix="/partners",
    tags=["Partner Branding"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        500: {"description": "Internal server error"},
    },
)


# ============================================================================
# Brand Configuration Management
# ============================================================================


@router.post(
    "/{partner_id}/brand",
    response_model=BrandConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Partner Brand Configuration",
    description="Create a comprehensive brand configuration for partner whitelabeling",
)
@rate_limit_strict(max_requests=10, time_window_seconds=60)
@standard_exception_handler
async def create_brand_config(
    request: BrandConfigCreate,
    partner_id: UUID = Path(..., description="Partner ID"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> BrandConfigResponse:
    """Create a comprehensive brand configuration for partner whitelabeling."""

    # Verify partner exists
    partner = deps.db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        from dotmac.core.exceptions import EntityNotFoundError

        raise EntityNotFoundError(f"Partner {partner_id} not found")

    # Check if brand config already exists
    existing_config = deps.db.query(PartnerBrandConfig).filter(PartnerBrandConfig.partner_id == partner_id).first()

    if existing_config:
        from dotmac.core.exceptions import BusinessRuleError

        raise BusinessRuleError("Brand configuration already exists for this partner")

    # Generate derived theme colors
    theme_data = _generate_theme_colors(
        primary_color=request.primary_color,
        secondary_color=request.secondary_color or request.primary_color,
    )

    # Create brand configuration
    brand_config = PartnerBrandConfig(
        partner_id=partner_id,
        brand_name=request.brand_name,
        primary_color=request.primary_color,
        secondary_color=request.secondary_color,
        accent_color=request.accent_color,
        background_color=request.background_color,
        text_color=request.text_color,
        font_family_primary=request.font_family_primary,
        font_family_secondary=request.font_family_secondary,
        logo_url=request.logo_url,
        favicon_url=request.favicon_url,
        custom_css=request.custom_css,
        theme_config=theme_data,
        domain_name=request.domain_name,
        is_domain_verified=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    deps.db.add(brand_config)
    deps.db.commit()
    deps.db.refresh(brand_config)

    return BrandConfigResponse.model_validate(brand_config)


@router.get(
    "/{partner_id}/brand",
    response_model=BrandConfigResponse,
    summary="Get Partner Brand Configuration",
    description="Retrieve the current brand configuration for a partner",
)
@rate_limit(max_requests=120, time_window_seconds=60)
@standard_exception_handler
async def get_brand_config(
    partner_id: UUID = Path(..., description="Partner ID"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> BrandConfigResponse:
    """Retrieve the current brand configuration for a partner."""

    brand_config = deps.db.query(PartnerBrandConfig).filter(PartnerBrandConfig.partner_id == partner_id).first()

    if not brand_config:
        from dotmac.core.exceptions import EntityNotFoundError

        raise EntityNotFoundError("Brand configuration not found")

    return BrandConfigResponse.model_validate(brand_config)


@router.put(
    "/{partner_id}/brand",
    response_model=BrandConfigResponse,
    summary="Update Partner Brand Configuration",
    description="Update an existing brand configuration",
)
@rate_limit_strict(max_requests=30, time_window_seconds=60)
@standard_exception_handler
async def update_brand_config(
    request: BrandConfigUpdate,
    partner_id: UUID = Path(..., description="Partner ID"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> BrandConfigResponse:
    """Update an existing brand configuration."""

    brand_config = deps.db.query(PartnerBrandConfig).filter(PartnerBrandConfig.partner_id == partner_id).first()

    if not brand_config:
        from dotmac.core.exceptions import EntityNotFoundError

        raise EntityNotFoundError("Brand configuration not found")

    # Update fields
    update_data = request.model_dump(exclude_unset=True)

    # Regenerate theme if colors changed
    if any(key in update_data for key in ["primary_color", "secondary_color"]):
        primary_color = update_data.get("primary_color", brand_config.primary_color)
        secondary_color = update_data.get("secondary_color", brand_config.secondary_color or primary_color)
        update_data["theme_config"] = _generate_theme_colors(primary_color, secondary_color)

    for field, value in update_data.items():
        if hasattr(brand_config, field):
            setattr(brand_config, field, value)

    brand_config.updated_at = datetime.now(timezone.utc)

    # Reset domain verification if domain changed
    if "domain_name" in update_data:
        brand_config.is_domain_verified = False

    deps.db.commit()
    deps.db.refresh(brand_config)

    return BrandConfigResponse.model_validate(brand_config)


@router.delete(
    "/{partner_id}/brand",
    response_model=dict,
    summary="Delete Partner Brand Configuration",
    description="Delete brand configuration for a partner",
)
@rate_limit_strict(max_requests=10, time_window_seconds=60)
@standard_exception_handler
async def delete_brand_config(
    partner_id: UUID = Path(..., description="Partner ID"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict:
    """Delete brand configuration for a partner."""

    brand_config = deps.db.query(PartnerBrandConfig).filter(PartnerBrandConfig.partner_id == partner_id).first()

    if not brand_config:
        from dotmac.core.exceptions import EntityNotFoundError

        raise EntityNotFoundError("Brand configuration not found")

    deps.db.delete(brand_config)
    deps.db.commit()

    return {
        "success": True,
        "message": f"Brand configuration deleted for partner {partner_id}",
    }


# ============================================================================
# Domain Verification
# ============================================================================


@router.post(
    "/{partner_id}/brand/verify-domain",
    response_model=dict,
    summary="Verify Custom Domain",
    description="Verify ownership of a custom domain for partner branding",
)
@rate_limit_strict(max_requests=5, time_window_seconds=60)
@standard_exception_handler
async def verify_domain(
    partner_id: UUID = Path(..., description="Partner ID"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict:
    """Verify ownership of a custom domain for partner branding."""

    brand_config = deps.db.query(PartnerBrandConfig).filter(PartnerBrandConfig.partner_id == partner_id).first()

    if not brand_config or not brand_config.domain_name:
        from dotmac.core.exceptions import BusinessRuleError

        raise BusinessRuleError("No domain configured for verification")

    # Use actual domain verification service
    from ...services.domain_verification_service import (
        domain_verification_service,
        VerificationMethod,
    )
    
    try:
        # Create DNS TXT verification challenge (preferred method)
        challenge = domain_verification_service.create_verification_challenge(
            domain=brand_config.domain_name,
            method=VerificationMethod.DNS_TXT
        )
        
        # Attempt verification
        verification_successful, error_message = await domain_verification_service.verify_domain_challenge(challenge)
        
        if not verification_successful:
            logger.warning(f"Domain verification failed for {brand_config.domain_name}: {error_message}")
            
    except Exception as e:
        logger.error(f"Domain verification error for {brand_config.domain_name}: {e}")
        verification_successful = False
        error_message = str(e)

    if verification_successful:
        brand_config.is_domain_verified = True
        brand_config.domain_verified_at = datetime.now(timezone.utc)
        brand_config.updated_at = datetime.now(timezone.utc)
        deps.db.commit()

        return {
            "success": True,
            "message": f"Domain {brand_config.domain_name} verified successfully",
            "verified_at": brand_config.domain_verified_at.isoformat(),
        }
    else:
        return {
            "success": False,
            "message": f"Domain {brand_config.domain_name} verification failed",
            "error": error_message if 'error_message' in locals() else "Unable to verify domain ownership",
        }


@router.get(
    "/{partner_id}/brand/domain-verification-instructions",
    response_model=dict,
    summary="Get Domain Verification Instructions",
    description="Get instructions for verifying domain ownership",
)
@standard_exception_handler
async def get_domain_verification_instructions(
    partner_id: UUID = Path(..., description="Partner ID"),
    method: str = "dns_txt",  # dns_txt or http_file
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict:
    """Get instructions for verifying domain ownership."""
    
    brand_config = deps.db.query(PartnerBrandConfig).filter(PartnerBrandConfig.partner_id == partner_id).first()
    
    if not brand_config or not brand_config.domain_name:
        from dotmac.core.exceptions import BusinessRuleError
        raise BusinessRuleError("No domain configured for verification")
    
    from ...services.domain_verification_service import (
        domain_verification_service,
        VerificationMethod,
    )
    
    verification_method = VerificationMethod.DNS_TXT if method == "dns_txt" else VerificationMethod.HTTP_FILE
    
    # Create a challenge to get instructions
    challenge = domain_verification_service.create_verification_challenge(
        domain=brand_config.domain_name,
        method=verification_method
    )
    
    instructions = domain_verification_service.get_verification_instructions(challenge)
    
    return {
        "domain": brand_config.domain_name,
        "is_verified": brand_config.is_domain_verified or False,
        "verification_instructions": instructions,
    }


# ============================================================================
# Public Theme Resolution
# ============================================================================


@router.get(
    "/theme/by-domain/{domain}",
    response_model=WhitelabelTheme,
    summary="Get Theme by Domain",
    description="Resolve partner theme configuration by custom domain",
)
@rate_limit(max_requests=300, time_window_seconds=60)
@standard_exception_handler
async def get_theme_by_domain(
    domain: str = Path(..., description="Custom domain"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> WhitelabelTheme:
    """Resolve partner theme configuration by custom domain."""

    brand_config = (
        deps.db.query(PartnerBrandConfig)
        .filter(
            PartnerBrandConfig.domain_name == domain,
            PartnerBrandConfig.is_domain_verified is True,
        )
        .first()
    )

    if not brand_config:
        # Return default theme
        return WhitelabelTheme(
            brand_name="DotMac",
            primary_color="#007bff",
            secondary_color="#6c757d",
            background_color="#ffffff",
            text_color="#212529",
            font_family_primary="Inter, sans-serif",
            theme_config=_generate_theme_colors("#007bff", "#6c757d"),
        )

    return WhitelabelTheme(
        brand_name=brand_config.brand_name,
        primary_color=brand_config.primary_color,
        secondary_color=brand_config.secondary_color,
        accent_color=brand_config.accent_color,
        background_color=brand_config.background_color,
        text_color=brand_config.text_color,
        font_family_primary=brand_config.font_family_primary,
        font_family_secondary=brand_config.font_family_secondary,
        logo_url=brand_config.logo_url,
        favicon_url=brand_config.favicon_url,
        custom_css=brand_config.custom_css,
        theme_config=brand_config.theme_config,
    )


# ============================================================================
# Asset Generation
# ============================================================================


@router.get(
    "/{partner_id}/brand/css",
    response_class=str,
    summary="Generate Brand CSS",
    description="Generate CSS variables and styles for the partner brand",
)
@rate_limit(max_requests=60, time_window_seconds=60)
@standard_exception_handler
async def generate_brand_css(
    partner_id: UUID = Path(..., description="Partner ID"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> str:
    """Generate CSS variables and styles for the partner brand."""

    brand_config = deps.db.query(PartnerBrandConfig).filter(PartnerBrandConfig.partner_id == partner_id).first()

    if not brand_config:
        from dotmac.core.exceptions import EntityNotFoundError

        raise EntityNotFoundError("Brand configuration not found")

    # Generate CSS with brand variables
    css_content = f"""
/* Partner Brand CSS Variables */
:root {{
  --brand-primary: {brand_config.primary_color};
  --brand-secondary: {brand_config.secondary_color or brand_config.primary_color};
  --brand-accent: {brand_config.accent_color or brand_config.primary_color};
  --brand-background: {brand_config.background_color or '#ffffff'};
  --brand-text: {brand_config.text_color or '#212529'};
  --brand-font-primary: {brand_config.font_family_primary or 'Inter, sans-serif'};
  --brand-font-secondary: {brand_config.font_family_secondary or 'Inter, sans-serif'};
}}

/* Generated Theme Colors */
"""

    if brand_config.theme_config:
        for color_name, color_value in brand_config.theme_config.items():
            css_content += f"  --brand-{color_name.replace('_', '-')}: {color_value};\n"

    css_content += "\n}\n"

    # Add custom CSS if provided
    if brand_config.custom_css:
        css_content += f"\n/* Custom Brand CSS */\n{brand_config.custom_css}\n"

    return css_content


# ============================================================================
# Helper Functions
# ============================================================================


def _generate_theme_colors(primary_color: str, secondary_color: str) -> dict[str, str]:
    """Generate a complete color palette from primary and secondary colors."""

    def hex_to_hsl(hex_color: str) -> tuple[float, float, float]:
        """Convert hex color to HSL."""
        hex_color = hex_color.lstrip("#")
        r, g, b = tuple(int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
        return colorsys.rgb_to_hls(r, g, b)

    def hsl_to_hex(h: float, l: float, s: float) -> str:
        """Convert HSL to hex color."""
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

    try:
        h, l, s = hex_to_hsl(primary_color)

        # Generate color variations
        theme_colors = {
            "primary_50": hsl_to_hex(h, min(0.97, l + 0.4), max(0.1, s - 0.1)),
            "primary_100": hsl_to_hex(h, min(0.95, l + 0.3), max(0.2, s - 0.05)),
            "primary_200": hsl_to_hex(h, min(0.9, l + 0.2), s),
            "primary_300": hsl_to_hex(h, min(0.8, l + 0.1), s),
            "primary_400": hsl_to_hex(h, l, s),
            "primary_500": primary_color,
            "primary_600": hsl_to_hex(h, max(0.1, l - 0.1), min(1.0, s + 0.1)),
            "primary_700": hsl_to_hex(h, max(0.05, l - 0.2), min(1.0, s + 0.15)),
            "primary_800": hsl_to_hex(h, max(0.03, l - 0.3), min(1.0, s + 0.2)),
            "primary_900": hsl_to_hex(h, max(0.02, l - 0.4), min(1.0, s + 0.25)),
        }

        return theme_colors

    except Exception as e:
        logger.warning(f"Failed to generate theme colors: {e}")
        return {
            "primary_500": primary_color,
            "secondary_500": secondary_color,
        }
