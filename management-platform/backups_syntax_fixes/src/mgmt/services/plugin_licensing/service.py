"""Plugin licensing service for managing ISP Framework plugin subscriptions."""

import asyncio
import logging
import secrets
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload, joinedload

from mgmt.services.billing_saas.models import Subscription, PricingTier
from .models import ()
    PluginCatalog, PluginSubscription, LicenseEntitlement, PluginUsageRecord,
    LicenseStatus, PluginTier, UsageMetricType, PluginLicenseHistory
, timezone)
from .exceptions import ()
    LicensingError, PluginNotFoundError, LicenseExpiredError, 
    UsageLimitExceededError, InvalidLicenseError, PluginSubscriptionError
)


logger = logging.getLogger(__name__)


class PluginLicensingService:
    """Service for managing plugin licensing and integration with billing system."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_plugin_catalog(self)
                                category: Optional[str] = None,
                                tier: Optional[PluginTier] = None,
                                public_only: bool = True) -> List[PluginCatalog]:
        """Get available plugins from catalog."""
        try:
            query = select(PluginCatalog).where(PluginCatalog.is_active == True)
            
            if public_only:
                query = query.where(PluginCatalog.is_public == True)
            
            if category:
                query = query.where(PluginCatalog.category == category)
                
            if tier:
                query = query.where(PluginCatalog.tier == tier)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error fetching plugin catalog: {str(e)}")
            raise LicensingError(f"Failed to fetch plugin catalog: {str(e)}")
    
    async def get_plugin_by_id(self, plugin_id: str) -> PluginCatalog:
        """Get plugin details by ID."""
        result = await self.session.execute()
            select(PluginCatalog).where(PluginCatalog.plugin_id == plugin_id)
        )
        plugin = result.scalar_one_or_none()
        
        if not plugin:
            raise PluginNotFoundError(f"Plugin not found: {plugin_id}")
            
        return plugin
    
    async def create_plugin_subscription(self)
                                       tenant_id: str,
                                       plugin_id: str,
                                       tier: PluginTier,
                                       billing_subscription_id: Optional[str] = None,
                                       trial_days: Optional[int] = None,
                                       custom_config: Optional[Dict[str, Any]] = None) -> PluginSubscription:
        """Create a new plugin subscription for a tenant."""
        try:
            # Verify plugin exists
            plugin = await self.get_plugin_by_id(plugin_id)
            
            # Check if tenant already has subscription for this plugin
            existing = await self.session.execute()
                select(PluginSubscription).where()
                    and_()
                        PluginSubscription.tenant_id == tenant_id,
                        PluginSubscription.plugin_id == plugin_id,
                        PluginSubscription.status != LicenseStatus.CANCELLED
                    )
                )
            )
            
            if existing.scalar_one_or_none():
                raise PluginSubscriptionError(f"Active subscription already exists for plugin {plugin_id}")
            
            # Determine if this is a trial
            is_trial = trial_days is not None and trial_days > 0
            if is_trial:
                trial_ends_at = datetime.now(timezone.utc) + timedelta(days=trial_days)
                expires_at = trial_ends_at
            else:
                trial_ends_at = None
                # For paid subscriptions, set expiry based on billing cycle
                expires_at = datetime.now(timezone.utc) + timedelta(days=30)  # Default 30 days
            
            # Create subscription
            subscription = PluginSubscription()
                tenant_id=tenant_id,
                plugin_id=plugin_id,
                subscription_id=billing_subscription_id,
                tier=tier,
                status=LicenseStatus.TRIAL if is_trial else LicenseStatus.ACTIVE,
                starts_at=datetime.now(timezone.utc),
                expires_at=expires_at,
                is_trial=is_trial,
                trial_ends_at=trial_ends_at,
                monthly_price=plugin.monthly_price if not is_trial else Decimal('0.00'),
                annual_price=plugin.annual_price if not is_trial else Decimal('0.00'),
                usage_limits=plugin.usage_limits,
                feature_entitlements=plugin.features,
                plugin_config=custom_config or {},
                license_key=self._generate_license_key(tenant_id, plugin_id),
                activated_at=datetime.now(timezone.utc)
            )
            
            self.session.add(subscription)
            await self.session.flush()  # Get ID
            
            # Create feature entitlements
            await self._create_plugin_entitlements(subscription, plugin)
            
            # Log history
            await self._log_license_history()
                subscription.id, "activated", None, subscription.status,
                f"Plugin subscription created for tier: {tier.value}"
            )
            
            await self.session.commit()
            
            logger.info(f"Created plugin subscription: {subscription.id} for tenant {tenant_id}")
            return subscription
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating plugin subscription: {str(e)}")
            raise PluginSubscriptionError(f"Failed to create plugin subscription: {str(e)}")
    
    async def _create_plugin_entitlements(self, subscription: PluginSubscription, plugin: PluginCatalog):
        """Create feature entitlements based on plugin tier."""
        if not plugin.features:
            return
            
        # Get tier-specific features
        tier_features = plugin.features.get(subscription.tier.value, plugin.features.get("default", [])
        
        if isinstance(tier_features, dict):
            # Features with limits
            for feature_name, feature_config in tier_features.items():
                if isinstance(feature_config, dict):
                    entitlement = LicenseEntitlement()
                        tenant_id=subscription.tenant_id,
                        plugin_subscription_id=subscription.id,
                        feature_name=feature_name,
                        feature_description=feature_config.get("description"),
                        is_enabled=feature_config.get("enabled", True),
                        usage_limit=feature_config.get("usage_limit"),
                        usage_period=feature_config.get("usage_period", "monthly"),
                        feature_config=feature_config
                    )
                else:
                    # Simple boolean feature
                    entitlement = LicenseEntitlement()
                        tenant_id=subscription.tenant_id,
                        plugin_subscription_id=subscription.id,
                        feature_name=feature_name,
                        is_enabled=bool(feature_config)
                    )
                
                self.session.add(entitlement)
        
        elif isinstance(tier_features, list):
            # Simple list of feature names
            for feature_name in tier_features:
                entitlement = LicenseEntitlement()
                    tenant_id=subscription.tenant_id,
                    plugin_subscription_id=subscription.id,
                    feature_name=feature_name,
                    is_enabled=True
                )
                self.session.add(entitlement)
    
    def _generate_license_key(self, tenant_id: str, plugin_id: str) -> str:
        """Generate secure license key for plugin."""
        # Create a secure license key with tenant and plugin info
        random_part = secrets.token_urlsafe(32)
        timestamp = int(datetime.now(timezone.utc).timestamp()
        
        # Format: PLUGIN-TENANT-TIMESTAMP-RANDOM
        return f"{plugin_id[:8].upper()}-{tenant_id[:8].upper()}-{timestamp}-{random_part[:16]}"
    
    async def get_tenant_plugin_subscriptions(self, tenant_id: str)
                                            active_only: bool = True) -> List[PluginSubscription]:
        """Get all plugin subscriptions for a tenant."""
        query = select(PluginSubscription).options()
            joinedload(PluginSubscription.plugin),
            selectinload(PluginSubscription.entitlements)
        ).where(PluginSubscription.tenant_id == tenant_id)
        
        if active_only:
            query = query.where()
                or_()
                    PluginSubscription.status == LicenseStatus.ACTIVE,
                    PluginSubscription.status == LicenseStatus.TRIAL
                )
            )
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_plugin_subscription(self, tenant_id: str, plugin_id: str) -> Optional[PluginSubscription]:
        """Get specific plugin subscription for tenant."""
        result = await self.session.execute()
            select(PluginSubscription).options()
                joinedload(PluginSubscription.plugin),
                selectinload(PluginSubscription.entitlements)
            ).where()
                and_()
                    PluginSubscription.tenant_id == tenant_id,
                    PluginSubscription.plugin_id == plugin_id,
                    PluginSubscription.status != LicenseStatus.CANCELLED
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def validate_plugin_access(self, tenant_id: str, plugin_id: str)
                                   feature_name: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Validate if tenant has access to plugin and optionally specific feature."""
        try:
            subscription = await self.get_plugin_subscription(tenant_id, plugin_id)
            
            if not subscription:
                return False, "No active subscription found"
            
            if not subscription.is_active:
                return False, f"Subscription is {subscription.status.value}"
            
            # Check trial expiry
            if subscription.is_trial and not subscription.is_trial_active:
                return False, "Trial period has expired"
            
            # Check feature access if specified
            if feature_name:
                entitlement = None
                for ent in subscription.entitlements:
                    if ent.feature_name == feature_name:
                        entitlement = ent
                        break
                
                if not entitlement:
                    return False, f"Feature '{feature_name}' not included in subscription"
                
                if not entitlement.can_use_feature():
                    return False, f"Feature '{feature_name}' usage limit exceeded or expired"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating plugin access: {str(e)}")
            return False, f"Validation error: {str(e)}"
    
    async def record_plugin_usage(self, tenant_id: str, plugin_id: str)
                                metric_name: str, usage_count: int = 1,
                                usage_value: Optional[Decimal] = None,
                                context: Optional[Dict[str, Any]] = None) -> PluginUsageRecord:
        """Record plugin usage for billing and analytics."""
        try:
            subscription = await self.get_plugin_subscription(tenant_id, plugin_id)
            if not subscription:
                raise LicensingError(f"No active subscription for plugin {plugin_id}")
            
            # Check usage limits
            if not subscription.check_usage_limit(metric_name, usage_count):
                raise UsageLimitExceededError(f"Usage limit exceeded for metric {metric_name}")
            
            # Determine metric type
            metric_type = UsageMetricType.API_CALLS  # Default
            if "user" in metric_name.lower():
                metric_type = UsageMetricType.MONTHLY_ACTIVE_USERS
            elif "storage" in metric_name.lower():
                metric_type = UsageMetricType.STORAGE_GB
            elif "report" in metric_name.lower():
                metric_type = UsageMetricType.REPORTS_GENERATED
            elif "transaction" in metric_name.lower():
                metric_type = UsageMetricType.TRANSACTIONS
            
            # Get plugin for pricing info
            plugin = await self.get_plugin_by_id(plugin_id)
            
            # Calculate charges if usage-based billing
            unit_price = None
            total_charge = None
            if plugin.has_usage_billing and plugin.usage_rates:
                unit_price = Decimal(str(plugin.usage_rates.get(metric_name, 0)
                total_charge = unit_price * Decimal(str(usage_count)
            
            # Create usage record
            usage_record = PluginUsageRecord()
                tenant_id=tenant_id,
                plugin_subscription_id=subscription.id,
                plugin_id=plugin_id,
                usage_date=date.today(),
                usage_hour=datetime.now(timezone.utc).hour,
                metric_name=metric_name,
                metric_type=metric_type,
                usage_count=usage_count,
                usage_value=usage_value,
                is_billable=plugin.has_usage_billing,
                unit_price=unit_price,
                total_charge=total_charge,
                usage_context=context or {}
            )
            
            self.session.add(usage_record)
            
            # Update subscription usage counters
            subscription.increment_usage(metric_name, usage_count)
            
            await self.session.commit()
            
            logger.debug(f"Recorded usage: {metric_name}={usage_count} for {tenant_id}/{plugin_id}")
            return usage_record
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error recording plugin usage: {str(e)}")
            raise
    
    async def upgrade_plugin_subscription(self, tenant_id: str, plugin_id: str)
                                        new_tier: PluginTier) -> PluginSubscription:
        """Upgrade plugin subscription to higher tier."""
        try:
            subscription = await self.get_plugin_subscription(tenant_id, plugin_id)
            if not subscription:
                raise PluginSubscriptionError(f"No subscription found for plugin {plugin_id}")
            
            if new_tier.value <= subscription.tier.value:
                raise PluginSubscriptionError("Cannot downgrade using this method")
            
            plugin = await self.get_plugin_by_id(plugin_id)
            
            # Store previous state
            previous_tier = subscription.tier
            previous_config = {
                "tier": previous_tier.value,
                "usage_limits": subscription.usage_limits,
                "features": subscription.feature_entitlements
            }
            
            # Update subscription
            subscription.tier = new_tier
            subscription.monthly_price = plugin.monthly_price
            subscription.annual_price = plugin.annual_price
            subscription.usage_limits = plugin.usage_limits
            subscription.feature_entitlements = plugin.features
            subscription.last_updated = datetime.now(timezone.utc)
            
            # If trial, convert to paid
            if subscription.is_trial:
                subscription.is_trial = False
                subscription.trial_converted = True
                subscription.status = LicenseStatus.ACTIVE
                subscription.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            
            # Delete old entitlements
            await self.session.execute()
                delete(LicenseEntitlement).where()
                    LicenseEntitlement.plugin_subscription_id == subscription.id
                )
            )
            
            # Create new entitlements
            await self._create_plugin_entitlements(subscription, plugin)
            
            # Log history
            await self._log_license_history()
                subscription.id, "upgraded", previous_tier, subscription.status,
                f"Upgraded from {previous_tier.value} to {new_tier.value}",
                previous_config=previous_config
            )
            
            await self.session.commit()
            
            logger.info(f"Upgraded plugin subscription {subscription.id} to {new_tier.value}")
            return subscription
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error upgrading plugin subscription: {str(e)}")
            raise PluginSubscriptionError(f"Failed to upgrade subscription: {str(e)}")
    
    async def suspend_plugin_subscription(self, tenant_id: str, plugin_id: str)
                                        reason: str) -> PluginSubscription:
        """Suspend plugin subscription."""
        try:
            subscription = await self.get_plugin_subscription(tenant_id, plugin_id)
            if not subscription:
                raise PluginSubscriptionError(f"No subscription found for plugin {plugin_id}")
            
            previous_status = subscription.status
            subscription.status = LicenseStatus.SUSPENDED
            subscription.suspended_at = datetime.now(timezone.utc)
            subscription.suspension_reason = reason
            
            # Log history
            await self._log_license_history()
                subscription.id, "suspended", previous_status, LicenseStatus.SUSPENDED,
                f"Subscription suspended: {reason}"
            )
            
            await self.session.commit()
            
            logger.info(f"Suspended plugin subscription {subscription.id}: {reason}")
            return subscription
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error suspending plugin subscription: {str(e)}")
            raise
    
    async def reactivate_plugin_subscription(self, tenant_id: str, plugin_id: str) -> PluginSubscription:
        """Reactivate suspended plugin subscription."""
        try:
            subscription = await self.get_plugin_subscription(tenant_id, plugin_id)
            if not subscription:
                raise PluginSubscriptionError(f"No subscription found for plugin {plugin_id}")
            
            if subscription.status != LicenseStatus.SUSPENDED:
                raise PluginSubscriptionError("Subscription is not suspended")
            
            previous_status = subscription.status
            subscription.status = LicenseStatus.ACTIVE
            subscription.suspended_at = None
            subscription.suspension_reason = None
            
            # Extend expiry if needed
            if subscription.expires_at and subscription.expires_at <= datetime.now(timezone.utc):
                subscription.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            
            # Log history
            await self._log_license_history()
                subscription.id, "reactivated", previous_status, LicenseStatus.ACTIVE,
                "Subscription reactivated"
            )
            
            await self.session.commit()
            
            logger.info(f"Reactivated plugin subscription {subscription.id}")
            return subscription
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error reactivating plugin subscription: {str(e)}")
            raise
    
    async def get_plugin_usage_summary(self, tenant_id: str, plugin_id: str)
                                     start_date: Optional[date] = None,
                                     end_date: Optional[date] = None) -> Dict[str, Any]:
        """Get plugin usage summary for billing period."""
        try:
            if not start_date:
                start_date = date.today().replace(day=1)  # Start of current month
            if not end_date:
                end_date = date.today()
            
            subscription = await self.get_plugin_subscription(tenant_id, plugin_id)
            if not subscription:
                raise PluginSubscriptionError(f"No subscription found for plugin {plugin_id}")
            
            # Get usage records for period
            result = await self.session.execute()
                select(PluginUsageRecord).where()
                    and_()
                        PluginUsageRecord.plugin_subscription_id == subscription.id,
                        PluginUsageRecord.usage_date >= start_date,
                        PluginUsageRecord.usage_date <= end_date
                    )
                )
            )
            
            usage_records = result.scalars().all()
            
            # Aggregate usage by metric
            usage_summary = {}
            total_charges = Decimal('0.00')
            
            for record in usage_records:
                metric = record.metric_name
                if metric not in usage_summary:
                    usage_summary[metric] = {
                        "total_count": 0,
                        "total_value": Decimal('0.00'),
                        "total_charges": Decimal('0.00'),
                        "records": 0
                    }
                
                usage_summary[metric]["total_count"] += record.usage_count
                usage_summary[metric]["total_value"] += record.usage_value or Decimal('0.00')
                usage_summary[metric]["total_charges"] += record.total_charge or Decimal('0.00')
                usage_summary[metric]["records"] += 1
                
                total_charges += record.total_charge or Decimal('0.00')
            
            return {
                "subscription_id": str(subscription.id),
                "plugin_id": plugin_id,
                "tenant_id": tenant_id,
                "period_start": start_date,
                "period_end": end_date,
                "tier": subscription.tier.value,
                "usage_by_metric": usage_summary,
                "total_charges": total_charges,
                "current_limits": subscription.usage_limits,
                "current_usage": subscription.current_usage
            }
            
        except Exception as e:
            logger.error(f"Error getting usage summary: {str(e)}")
            raise LicensingError(f"Failed to get usage summary: {str(e)}")
    
    async def _log_license_history(self, subscription_id: str, action_type: str)
                                 previous_status: Optional[LicenseStatus],
                                 new_status: LicenseStatus, reason: str,
                                 previous_config: Optional[Dict[str, Any]] = None,
                                 new_config: Optional[Dict[str, Any]] = None):
        """Log license history record."""
        history_record = PluginLicenseHistory()
            tenant_id="system",  # Will be set properly with tenant context
            plugin_subscription_id=subscription_id,
            action_type=action_type,
            previous_status=previous_status,
            new_status=new_status,
            reason=reason,
            previous_config=previous_config,
            new_config=new_config
        )
        
        self.session.add(history_record)
    
    async def cleanup_expired_trials(self) -> int:
        """Clean up expired trial subscriptions."""
        try:
            expired_trials = await self.session.execute()
                select(PluginSubscription).where()
                    and_()
                        PluginSubscription.is_trial == True,
                        PluginSubscription.trial_ends_at <= datetime.now(timezone.utc),
                        PluginSubscription.status == LicenseStatus.TRIAL
                    )
                )
            )
            
            count = 0
            for subscription in expired_trials.scalars():
                # Mark as expired
                subscription.status = LicenseStatus.EXPIRED
                
                # Log history
                await self._log_license_history()
                    subscription.id, "expired", LicenseStatus.TRIAL, LicenseStatus.EXPIRED,
                    "Trial period expired"
                )
                
                count += 1
            
            await self.session.commit()
            
            if count > 0:
                logger.info(f"Cleaned up {count} expired trial subscriptions")
            
            return count
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error cleaning up expired trials: {str(e)}")
            return 0