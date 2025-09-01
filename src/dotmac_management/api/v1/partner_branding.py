"""
Partner branding API for whitelabeling support.
Leverages existing partner API patterns with DRY compliance.
"""

import colorsys
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from dotmac_shared.api.dependencies import StandardDeps
from dotmac_shared.api.exception_handlers import standard_exception_handler

from ...models.partner_branding import (
    PartnerBrandConfig,
    BrandConfigCreate,
    BrandConfigUpdate,
    BrandConfigResponse,
    WhitelabelTheme,
)
from ...models.partner import Partner


router = APIRouter(prefix="/partners", tags=["Partner Branding"])


@router.post("/{partner_id}/brand", response_model=BrandConfigResponse, status_code=status.HTTP_201_CREATED)
@standard_exception_handler
async def create_partner_brand_config(
    partner_id: UUID,
    brand_data: BrandConfigCreate,
    deps: StandardDeps
) -> BrandConfigResponse:
    """Create whitelabel brand configuration for partner."""
    
    # Verify partner exists and user has access
    partner_query = select(Partner).where(Partner.id == partner_id)
    result = await deps.db.execute(partner_query)
    partner = result.scalar_one_or_none()
    
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found"
        )
    
    # Check if brand config already exists
    existing_query = select(PartnerBrandConfig).where(PartnerBrandConfig.partner_id == partner_id)
    existing_result = await deps.db.execute(existing_query)
    existing_config = existing_result.scalar_one_or_none()
    
    if existing_config:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Brand configuration already exists for this partner"
        )
    
    # Create brand configuration
    brand_config = PartnerBrandConfig(
        partner_id=partner_id,
        **brand_data.model_dump(exclude={'partner_id'})
    )
    
    # Generate derived brand assets
    brand_config.generated_assets = _generate_brand_assets(brand_data)
    
    deps.db.add(brand_config)
    await deps.db.commit()
    await deps.db.refresh(brand_config, ['partner'])
    
    return BrandConfigResponse.model_validate(brand_config)


@router.get("/{partner_id}/brand", response_model=BrandConfigResponse)
@standard_exception_handler
async def get_partner_brand_config(
    partner_id: UUID,
    deps: StandardDeps
) -> BrandConfigResponse:
    """Get partner's brand configuration."""
    
    query = select(PartnerBrandConfig).options(
        selectinload(PartnerBrandConfig.partner)
    ).where(PartnerBrandConfig.partner_id == partner_id)
    
    result = await deps.db.execute(query)
    brand_config = result.scalar_one_or_none()
    
    if not brand_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand configuration not found"
        )
    
    return BrandConfigResponse.model_validate(brand_config)


@router.put("/{partner_id}/brand", response_model=BrandConfigResponse)
@standard_exception_handler
async def update_partner_brand_config(
    partner_id: UUID,
    brand_data: BrandConfigUpdate,
    deps: StandardDeps
) -> BrandConfigResponse:
    """Update partner's brand configuration."""
    
    query = select(PartnerBrandConfig).where(PartnerBrandConfig.partner_id == partner_id)
    result = await deps.db.execute(query)
    brand_config = result.scalar_one_or_none()
    
    if not brand_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand configuration not found"
        )
    
    # Update fields
    update_data = brand_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(brand_config, field, value)
    
    # Regenerate brand assets if colors changed
    color_fields = ['primary_color', 'secondary_color', 'accent_color', 'background_color', 'text_color']
    if any(field in update_data for field in color_fields):
        brand_config.generated_assets = _generate_brand_assets(brand_config)
    
    await deps.db.commit()
    await deps.db.refresh(brand_config, ['partner'])
    
    return BrandConfigResponse.model_validate(brand_config)


@router.delete("/{partner_id}/brand", status_code=status.HTTP_204_NO_CONTENT)
@standard_exception_handler
async def delete_partner_brand_config(
    partner_id: UUID,
    deps: StandardDeps
):
    """Delete partner's brand configuration."""
    
    query = select(PartnerBrandConfig).where(PartnerBrandConfig.partner_id == partner_id)
    result = await deps.db.execute(query)
    brand_config = result.scalar_one_or_none()
    
    if not brand_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand configuration not found"
        )
    
    await deps.db.delete(brand_config)
    await deps.db.commit()


@router.get("/{partner_id}/brand/theme", response_model=WhitelabelTheme)
@standard_exception_handler
async def get_partner_theme(
    partner_id: UUID,
    deps: StandardDeps
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
@standard_exception_handler
async def verify_partner_domain(
    partner_id: UUID,
    deps: StandardDeps
) -> Dict[str, Any]:
    """Verify partner's custom domain configuration."""
    
    query = select(PartnerBrandConfig).where(PartnerBrandConfig.partner_id == partner_id)
    result = await deps.db.execute(query)
    brand_config = result.scalar_one_or_none()
    
    if not brand_config or not brand_config.custom_domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No custom domain configured"
        )
    
    # Perform domain verification
    verification_result = await _verify_domain(brand_config.custom_domain)
    
    # Update verification status
    brand_config.domain_verified = verification_result['verified']
    await deps.db.commit()
    
    return verification_result


@router.get("/by-domain/{domain}/theme", response_model=WhitelabelTheme)
@standard_exception_handler
async def get_theme_by_domain(
    domain: str,
    deps: StandardDeps
) -> WhitelabelTheme:
    """Get whitelabel theme by custom domain (for public access)."""
    
    query = select(PartnerBrandConfig).options(
        selectinload(PartnerBrandConfig.partner)
    ).where(
        PartnerBrandConfig.custom_domain == domain,
        PartnerBrandConfig.is_active == True,
        PartnerBrandConfig.domain_verified == True
    )
    
    result = await deps.db.execute(query)
    brand_config = result.scalar_one_or_none()
    
    if not brand_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No verified brand configuration found for domain"
        )
    
    return _build_whitelabel_theme(brand_config)


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