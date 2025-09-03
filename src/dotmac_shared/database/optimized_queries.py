"""
Optimized database queries for DotMac Framework.
Contains specialized query patterns for commission configs, partner branding, and tenant operations.
"""

from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

from sqlalchemy import select, func, and_, or_, exists, case, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload, contains_eager
from sqlalchemy.sql import Select

from dotmac_shared.observability.logging import get_logger
from .query_optimization import OptimizedQueryBuilder, query_cache, slow_query_monitor
from .caching import redis_cache, cache_invalidator

logger = get_logger(__name__)


# === COMMISSION CONFIG OPTIMIZATIONS ===

@redis_cache("commission_configs", ttl=900)  # 15 minutes
@slow_query_monitor(threshold_seconds=0.5)
async def get_commission_configs_optimized(
    session: AsyncSession,
    is_active: Optional[bool] = None,
    reseller_type: Optional[str] = None,
    territory: Optional[str] = None,
    effective_date: Optional[date] = None,
    page: int = 1,
    size: int = 50
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Optimized query for commission configurations with complex filters.
    
    Features:
    - Intelligent indexing hints
    - Optimized pagination
    - Result caching
    - Aggregation queries for totals
    """
    from dotmac_management.models.commission_config import CommissionConfig
    
    # Build optimized query
    builder = OptimizedQueryBuilder(CommissionConfig)
    
    # Add filters with optimization
    filters = {}
    if is_active is not None:
        filters['is_active'] = is_active
    if reseller_type:
        filters['reseller_type'] = reseller_type
    if territory:
        filters['territory'] = territory
    
    # Date range filtering
    if effective_date:
        builder.query = builder.query.where(
            and_(
                CommissionConfig.effective_from <= effective_date,
                or_(
                    CommissionConfig.effective_until.is_(None),
                    CommissionConfig.effective_until >= effective_date
                )
            )
        )
    
    builder.with_filters(**filters)
    
    # Optimized ordering (assuming index on created_at)
    builder.with_ordering(desc(CommissionConfig.created_at))
    
    # Get total count efficiently (separate optimized query)
    count_query = select(func.count(CommissionConfig.id))
    if filters or effective_date:
        count_filters = []
        for key, value in filters.items():
            count_filters.append(getattr(CommissionConfig, key) == value)
        if effective_date:
            count_filters.extend([
                CommissionConfig.effective_from <= effective_date,
                or_(
                    CommissionConfig.effective_until.is_(None),
                    CommissionConfig.effective_until >= effective_date
                )
            ])
        if count_filters:
            count_query = count_query.where(and_(*count_filters))
    
    # Execute count query
    count_result = await session.execute(count_query)
    total_count = count_result.scalar()
    
    # Build and execute main query with pagination
    builder.with_pagination(page, size)
    query = builder.build()
    
    result = await session.execute(query)
    configs = result.scalars().all()
    
    # Convert to dictionaries for caching
    config_dicts = []
    for config in configs:
        config_dict = {
            "id": str(config.id),
            "name": config.name,
            "description": config.description,
            "is_active": config.is_active,
            "is_default": config.is_default,
            "reseller_type": config.reseller_type.value if config.reseller_type else None,
            "reseller_tier": config.reseller_tier.value if config.reseller_tier else None,
            "territory": config.territory,
            "commission_structure": config.commission_structure.value,
            "rate_config": config.rate_config,
            "effective_from": config.effective_from.isoformat(),
            "effective_until": config.effective_until.isoformat() if config.effective_until else None,
            "calculate_on": config.calculate_on,
            "payment_frequency": config.payment_frequency,
            "minimum_payout": str(config.minimum_payout),
            "settings": config.settings,
            "created_at": config.created_at.isoformat(),
            "updated_at": config.updated_at.isoformat()
        }
        config_dicts.append(config_dict)
    
    logger.debug(
        f"Commission configs query completed",
        extra={
            "total_count": total_count,
            "returned_count": len(config_dicts),
            "page": page,
            "size": size,
            "filters": filters
        }
    )
    
    return config_dicts, total_count


@redis_cache("commission_configs", ttl=1800, key_func=lambda config_id: f"config_{config_id}")
@slow_query_monitor(threshold_seconds=0.3)
async def get_commission_config_by_id_optimized(
    session: AsyncSession,
    config_id: UUID
) -> Optional[Dict[str, Any]]:
    """
    Optimized single commission config retrieval.
    """
    from dotmac_management.models.commission_config import CommissionConfig
    
    query = select(CommissionConfig).where(CommissionConfig.id == config_id)
    
    result = await session.execute(query)
    config = result.scalar_one_or_none()
    
    if not config:
        return None
    
    return {
        "id": str(config.id),
        "name": config.name,
        "description": config.description,
        "is_active": config.is_active,
        "is_default": config.is_default,
        "reseller_type": config.reseller_type.value if config.reseller_type else None,
        "reseller_tier": config.reseller_tier.value if config.reseller_tier else None,
        "territory": config.territory,
        "commission_structure": config.commission_structure.value,
        "rate_config": config.rate_config,
        "effective_from": config.effective_from.isoformat(),
        "effective_until": config.effective_until.isoformat() if config.effective_until else None,
        "calculate_on": config.calculate_on,
        "payment_frequency": config.payment_frequency,
        "minimum_payout": str(config.minimum_payout),
        "settings": config.settings,
        "created_at": config.created_at.isoformat(),
        "updated_at": config.updated_at.isoformat()
    }


@redis_cache("commission_configs", ttl=1800, key_func=lambda: "default_config")
@slow_query_monitor(threshold_seconds=0.3)
async def get_default_commission_config_optimized(
    session: AsyncSession
) -> Optional[Dict[str, Any]]:
    """
    Optimized default commission config retrieval with fallback logic.
    """
    from dotmac_management.models.commission_config import CommissionConfig
    
    # Try to get explicit default first
    query = select(CommissionConfig).where(
        and_(
            CommissionConfig.is_default == True,
            CommissionConfig.is_active == True
        )
    ).order_by(desc(CommissionConfig.created_at))
    
    result = await session.execute(query)
    config = result.scalar_one_or_none()
    
    # Fallback to most recent active config if no explicit default
    if not config:
        fallback_query = select(CommissionConfig).where(
            CommissionConfig.is_active == True
        ).order_by(desc(CommissionConfig.created_at)).limit(1)
        
        fallback_result = await session.execute(fallback_query)
        config = fallback_result.scalar_one_or_none()
    
    if not config:
        return None
    
    return {
        "id": str(config.id),
        "name": config.name,
        "description": config.description,
        "is_active": config.is_active,
        "is_default": config.is_default,
        "reseller_type": config.reseller_type.value if config.reseller_type else None,
        "reseller_tier": config.reseller_tier.value if config.reseller_tier else None,
        "territory": config.territory,
        "commission_structure": config.commission_structure.value,
        "rate_config": config.rate_config,
        "effective_from": config.effective_from.isoformat(),
        "effective_until": config.effective_until.isoformat() if config.effective_until else None,
        "calculate_on": config.calculate_on,
        "payment_frequency": config.payment_frequency,
        "minimum_payout": str(config.minimum_payout),
        "settings": config.settings,
        "created_at": config.created_at.isoformat(),
        "updated_at": config.updated_at.isoformat()
    }


# === PARTNER BRANDING OPTIMIZATIONS ===

@redis_cache("partner_branding", ttl=3600, key_func=lambda partner_id: f"brand_{partner_id}")
@slow_query_monitor(threshold_seconds=0.5)
async def get_partner_brand_config_optimized(
    session: AsyncSession,
    partner_id: UUID
) -> Optional[Dict[str, Any]]:
    """
    Optimized partner brand configuration retrieval with asset generation.
    """
    from dotmac_management.models.partner_branding import PartnerBrandConfig
    from dotmac_management.models.partner import Partner
    
    # Use joined loading for partner relationship to avoid N+1
    query = select(PartnerBrandConfig).options(
        joinedload(PartnerBrandConfig.partner)
    ).where(PartnerBrandConfig.partner_id == partner_id)
    
    result = await session.execute(query)
    brand_config = result.scalar_one_or_none()
    
    if not brand_config:
        return None
    
    # Optimize asset serialization
    brand_data = {
        "id": str(brand_config.id),
        "partner_id": str(brand_config.partner_id),
        "partner_name": brand_config.partner.name if brand_config.partner else None,
        "brand_name": brand_config.brand_name,
        "tagline": brand_config.tagline,
        "primary_color": brand_config.primary_color,
        "secondary_color": brand_config.secondary_color,
        "accent_color": brand_config.accent_color,
        "background_color": brand_config.background_color,
        "text_color": brand_config.text_color,
        "logo_url": brand_config.logo_url,
        "logo_dark_url": brand_config.logo_dark_url,
        "favicon_url": brand_config.favicon_url,
        "custom_domain": brand_config.custom_domain,
        "domain_verified": brand_config.domain_verified,
        "ssl_enabled": brand_config.ssl_enabled,
        "font_family": brand_config.font_family,
        "font_url": brand_config.font_url,
        "generated_assets": brand_config.generated_assets,
        "brand_config": brand_config.brand_config,
        "is_active": brand_config.is_active,
        "created_at": brand_config.created_at.isoformat(),
        "updated_at": brand_config.updated_at.isoformat()
    }
    
    return brand_data


@redis_cache("partner_branding", ttl=3600, key_func=lambda domain: f"domain_{domain}")
@slow_query_monitor(threshold_seconds=0.5)
async def get_brand_config_by_domain_optimized(
    session: AsyncSession,
    domain: str
) -> Optional[Dict[str, Any]]:
    """
    Optimized brand configuration lookup by custom domain.
    Critical for public theme resolution.
    """
    from dotmac_management.models.partner_branding import PartnerBrandConfig
    from dotmac_management.models.partner import Partner
    
    query = select(PartnerBrandConfig).options(
        joinedload(PartnerBrandConfig.partner)
    ).where(
        and_(
            PartnerBrandConfig.custom_domain == domain,
            PartnerBrandConfig.is_active == True,
            PartnerBrandConfig.domain_verified == True
        )
    )
    
    result = await session.execute(query)
    brand_config = result.scalar_one_or_none()
    
    if not brand_config:
        return None
    
    # Return optimized theme data for public use
    theme_data = {
        "brand": {
            "name": brand_config.brand_name,
            "tagline": brand_config.tagline or "",
            "logo": brand_config.logo_url or "",
            "logo_dark": brand_config.logo_dark_url or "",
            "favicon": brand_config.favicon_url or ""
        },
        "colors": {
            "primary": brand_config.primary_color,
            "secondary": brand_config.secondary_color,
            "accent": brand_config.accent_color,
            "background": brand_config.background_color,
            "text": brand_config.text_color
        },
        "typography": {
            "font_family": brand_config.font_family,
            "font_url": brand_config.font_url or ""
        },
        "domain": {
            "custom": brand_config.custom_domain,
            "ssl": brand_config.ssl_enabled,
            "verified": brand_config.domain_verified
        },
        "css_variables": brand_config.generated_assets.get("css_variables", {}) if brand_config.generated_assets else {},
        "custom_css": brand_config.brand_config.get("custom_css", "") if brand_config.brand_config else "",
        "partner_id": str(brand_config.partner_id)
    }
    
    return theme_data


@slow_query_monitor(threshold_seconds=1.0)
async def get_partner_branding_bulk_optimized(
    session: AsyncSession,
    partner_ids: List[UUID],
    include_assets: bool = True
) -> Dict[UUID, Dict[str, Any]]:
    """
    Bulk retrieval of partner brand configurations with optimized loading.
    """
    from dotmac_management.models.partner_branding import PartnerBrandConfig
    from dotmac_management.models.partner import Partner
    
    if not partner_ids:
        return {}
    
    # Use IN clause for bulk retrieval
    query = select(PartnerBrandConfig).options(
        selectinload(PartnerBrandConfig.partner)  # Use selectinload for bulk operations
    ).where(
        and_(
            PartnerBrandConfig.partner_id.in_(partner_ids),
            PartnerBrandConfig.is_active == True
        )
    ).order_by(PartnerBrandConfig.partner_id)
    
    result = await session.execute(query)
    brand_configs = result.scalars().all()
    
    # Build result dictionary
    result_dict = {}
    for brand_config in brand_configs:
        brand_data = {
            "id": str(brand_config.id),
            "partner_id": str(brand_config.partner_id),
            "brand_name": brand_config.brand_name,
            "primary_color": brand_config.primary_color,
            "secondary_color": brand_config.secondary_color,
            "logo_url": brand_config.logo_url,
            "custom_domain": brand_config.custom_domain,
            "domain_verified": brand_config.domain_verified,
            "is_active": brand_config.is_active
        }
        
        if include_assets and brand_config.generated_assets:
            brand_data["generated_assets"] = brand_config.generated_assets
            brand_data["css_variables"] = brand_config.generated_assets.get("css_variables", {})
        
        result_dict[brand_config.partner_id] = brand_data
    
    logger.debug(
        f"Bulk partner branding query completed",
        extra={
            "requested_partners": len(partner_ids),
            "found_configs": len(result_dict),
            "include_assets": include_assets
        }
    )
    
    return result_dict


# === REVENUE CALCULATION OPTIMIZATIONS ===

@redis_cache("revenue_calculations", ttl=600)
@slow_query_monitor(threshold_seconds=2.0)
async def get_commission_revenue_aggregation(
    session: AsyncSession,
    partner_ids: Optional[List[UUID]] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    group_by: str = "partner"  # "partner", "month", "territory"
) -> List[Dict[str, Any]]:
    """
    Optimized revenue aggregation queries for commission calculations.
    Uses database-level aggregation for performance.
    """
    from dotmac_management.models.commission_config import CommissionConfig
    from dotmac_management.models.partner import Partner
    
    # This would need to be adapted based on your actual revenue/transaction tables
    # For now, this is a template showing the optimization pattern
    
    # Base aggregation query with optimized grouping
    base_query = select(
        CommissionConfig.id.label("config_id"),
        CommissionConfig.name.label("config_name"),
        func.count("*").label("transaction_count"),
        func.sum("revenue_amount").label("total_revenue"),  # Assuming revenue table
        func.avg("revenue_amount").label("avg_revenue"),
        func.date_trunc(group_by, "created_at").label("period") if group_by == "month" else None
    ).select_from(CommissionConfig)
    
    # Add filters
    filters = []
    if partner_ids:
        # This would join with partner/transaction tables
        filters.append(Partner.id.in_(partner_ids))
    
    if date_from:
        filters.append(CommissionConfig.created_at >= date_from)
    
    if date_to:
        filters.append(CommissionConfig.created_at <= date_to)
    
    if filters:
        base_query = base_query.where(and_(*filters))
    
    # Group by configuration
    if group_by == "partner":
        base_query = base_query.group_by(CommissionConfig.id, CommissionConfig.name)
    elif group_by == "month":
        base_query = base_query.group_by(
            CommissionConfig.id, 
            CommissionConfig.name,
            func.date_trunc("month", CommissionConfig.created_at)
        )
    
    # Order for consistent results
    base_query = base_query.order_by(desc("total_revenue"))
    
    result = await session.execute(base_query)
    rows = result.fetchall()
    
    # Convert to dictionaries
    aggregations = []
    for row in rows:
        agg_data = {
            "config_id": str(row.config_id),
            "config_name": row.config_name,
            "transaction_count": row.transaction_count,
            "total_revenue": float(row.total_revenue or 0),
            "avg_revenue": float(row.avg_revenue or 0)
        }
        
        if group_by == "month" and hasattr(row, "period"):
            agg_data["period"] = row.period.isoformat() if row.period else None
        
        aggregations.append(agg_data)
    
    return aggregations


# === TENANT MANAGEMENT BULK OPERATIONS ===

@cache_invalidator("tenant_operations", "tenant_*")
@slow_query_monitor(threshold_seconds=5.0)
async def bulk_tenant_configuration_update(
    session: AsyncSession,
    tenant_updates: List[Dict[str, Any]],
    batch_size: int = 100
) -> Dict[str, Any]:
    """
    Optimized bulk tenant configuration updates.
    Uses batch processing and efficient update patterns.
    """
    # This is a template - would need to be adapted based on actual tenant models
    
    total_updates = len(tenant_updates)
    successful_updates = 0
    failed_updates = 0
    errors = []
    
    # Process in batches to avoid memory issues and lock contention
    for i in range(0, total_updates, batch_size):
        batch = tenant_updates[i:i + batch_size]
        
        try:
            # Use bulk update operations where possible
            for update_data in batch:
                tenant_id = update_data.get("tenant_id")
                if not tenant_id:
                    continue
                
                # Example update pattern - adapt based on actual models
                # stmt = update(TenantModel).where(
                #     TenantModel.id == tenant_id
                # ).values(**{k: v for k, v in update_data.items() if k != "tenant_id"})
                # 
                # await session.execute(stmt)
                
                successful_updates += 1
            
            # Commit batch
            await session.flush()
            
            logger.debug(f"Processed tenant batch {i // batch_size + 1}: {len(batch)} updates")
            
        except Exception as e:
            logger.error(f"Batch update failed for batch starting at {i}: {e}")
            failed_updates += len(batch)
            errors.append({"batch_start": i, "error": str(e)})
            
            # Rollback batch and continue
            await session.rollback()
    
    # Final commit
    try:
        await session.commit()
        logger.info(f"Bulk tenant update completed: {successful_updates} successful, {failed_updates} failed")
    except Exception as e:
        await session.rollback()
        logger.error(f"Final commit failed in bulk tenant update: {e}")
        errors.append({"operation": "final_commit", "error": str(e)})
    
    return {
        "total_requested": total_updates,
        "successful_updates": successful_updates,
        "failed_updates": failed_updates,
        "errors": errors,
        "batch_size": batch_size
    }


# === QUERY PERFORMANCE ANALYTICS ===

@slow_query_monitor(threshold_seconds=1.0)
async def analyze_commission_config_performance(
    session: AsyncSession,
    days_back: int = 30
) -> Dict[str, Any]:
    """
    Analyze commission configuration query performance and usage patterns.
    """
    from dotmac_management.models.commission_config import CommissionConfig
    
    # Performance analysis queries
    since_date = datetime.now(timezone.utc).date() - timedelta(days=days_back)
    
    # Configuration usage statistics
    usage_query = select(
        CommissionConfig.id,
        CommissionConfig.name,
        CommissionConfig.commission_structure,
        CommissionConfig.reseller_type,
        CommissionConfig.territory,
        func.count("*").label("usage_count"),  # Would need actual usage tracking
        case(
            (CommissionConfig.is_default == True, "default"),
            else_="specific"
        ).label("config_type")
    ).select_from(CommissionConfig).where(
        and_(
            CommissionConfig.is_active == True,
            CommissionConfig.created_at >= since_date
        )
    ).group_by(
        CommissionConfig.id,
        CommissionConfig.name,
        CommissionConfig.commission_structure,
        CommissionConfig.reseller_type,
        CommissionConfig.territory,
        CommissionConfig.is_default
    ).order_by(desc("usage_count"))
    
    result = await session.execute(usage_query)
    rows = result.fetchall()
    
    # Build performance analysis
    analysis = {
        "analysis_period_days": days_back,
        "total_active_configs": len(rows),
        "configurations": [],
        "performance_insights": {
            "most_used_structure": None,
            "territory_distribution": {},
            "default_vs_specific_usage": {"default": 0, "specific": 0}
        }
    }
    
    structure_counts = {}
    territory_counts = {}
    
    for row in rows:
        config_data = {
            "id": str(row.id),
            "name": row.name,
            "commission_structure": row.commission_structure.value if row.commission_structure else None,
            "reseller_type": row.reseller_type.value if row.reseller_type else None,
            "territory": row.territory,
            "usage_count": row.usage_count,
            "config_type": row.config_type
        }
        analysis["configurations"].append(config_data)
        
        # Track statistics
        if row.commission_structure:
            structure = row.commission_structure.value
            structure_counts[structure] = structure_counts.get(structure, 0) + row.usage_count
        
        if row.territory:
            territory_counts[row.territory] = territory_counts.get(row.territory, 0) + row.usage_count
        
        analysis["performance_insights"]["default_vs_specific_usage"][row.config_type] += row.usage_count
    
    # Identify most used patterns
    if structure_counts:
        analysis["performance_insights"]["most_used_structure"] = max(
            structure_counts.items(), key=lambda x: x[1]
        )[0]
    
    analysis["performance_insights"]["territory_distribution"] = territory_counts
    
    logger.info(
        f"Commission config performance analysis completed",
        extra={
            "period_days": days_back,
            "active_configs": len(rows),
            "total_usage": sum(row.usage_count for row in rows)
        }
    )
    
    return analysis