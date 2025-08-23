# Plugin Licensing System Documentation

The DotMac Management Platform includes a comprehensive plugin licensing system that enables tiered monetization of ISP Framework features through a marketplace model.

## 🎯 **Overview**

The plugin licensing system transforms the ISP Framework from a monolithic deployment into a flexible, revenue-generating SaaS platform where features are unlocked through plugin subscriptions.

### **Core Concepts**

- **Plugin Catalog**: Centralized marketplace of available plugins with pricing tiers
- **Subscription Management**: Per-tenant plugin subscriptions with billing integration  
- **Usage Tracking**: Monitor plugin usage for billing and compliance
- **Feature Entitlements**: License-based access control to advanced functionality
- **Trial Management**: Automated trial-to-paid conversion workflows

## 🏗️ **Architecture**

### **Plugin Tiers**

```python
class PluginTier(enum.Enum):
    FREE = "free"          # Basic features, no charge
    BASIC = "basic"        # Standard features, monthly fee
    PREMIUM = "premium"    # Advanced features, higher monthly fee  
    ENTERPRISE = "enterprise"  # Full features, custom pricing
```

### **Plugin Categories**

- **Network Automation**: SNMP monitoring, device management, automated provisioning
- **GIS Location**: Mapping, coverage analysis, service area management
- **Billing Integration**: Advanced billing, payment processing, invoice management
- **CRM Integration**: Customer relationship management, support ticketing
- **Monitoring**: Advanced analytics, performance monitoring, alerting
- **Communication**: Email campaigns, SMS notifications, customer portals
- **Reporting**: Business intelligence, custom reports, data exports
- **Security**: Advanced security features, compliance reporting, audit trails

## 📊 **Business Model**

### **Revenue Streams**

#### **1. Monthly Subscriptions**
```python
# Example pricing structure
PLUGIN_PRICING = {
    "advanced_billing": {
        "basic": 29.99,     # per month
        "premium": 79.99,   # per month
        "enterprise": 199.99 # per month
    },
    "advanced_analytics": {
        "premium": 49.99,   # per month
        "enterprise": 149.99 # per month
    }
}
```

#### **2. Usage-Based Billing**
```python
# Usage metrics that trigger charges
USAGE_METRICS = {
    "api_calls": 0.001,        # $0.001 per API call over limit
    "storage_gb": 2.50,        # $2.50 per GB over limit
    "transactions": 0.029,     # 2.9% + $0.30 per transaction
    "reports_generated": 1.99, # $1.99 per custom report
    "sms_sent": 0.05,         # $0.05 per SMS notification
    "email_sent": 0.001       # $0.001 per email sent
}
```

#### **3. Feature Entitlements**
```python
# Features unlocked by subscription tier
TIER_FEATURES = {
    "free": [
        "basic_customer_management",
        "simple_billing", 
        "standard_reporting"
    ],
    "basic": [
        "advanced_billing",
        "crm_integration",
        "api_access",
        "email_notifications"
    ],
    "premium": [
        "advanced_analytics",
        "custom_integrations", 
        "white_labeling",
        "sms_notifications",
        "priority_support"
    ],
    "enterprise": [
        "ai_insights",
        "predictive_analytics", 
        "unlimited_apis",
        "custom_development",
        "dedicated_support"
    ]
}
```

## 🔧 **Implementation**

### **Plugin Catalog Management**

```python
# Create a new plugin in the catalog
async def create_plugin_catalog_entry():
    plugin = PluginCatalog(
        plugin_id="advanced_analytics",
        plugin_name="Advanced Analytics Suite",
        category="analytics",
        tier=PluginTier.PREMIUM,
        monthly_price=Decimal("49.99"),
        annual_price=Decimal("499.99"),
        features=[
            "custom_dashboards",
            "advanced_reports", 
            "data_export",
            "api_analytics"
        ],
        usage_limits={
            "reports_generated": 100,    # per month
            "api_calls": 10000,         # per month
            "data_export_gb": 5         # per month
        }
    )
    
    session.add(plugin)
    await session.commit()
```

### **Subscription Creation**

```python
# Subscribe a tenant to a plugin
async def subscribe_tenant_to_plugin(
    tenant_id: str, 
    plugin_id: str, 
    tier: PluginTier
):
    licensing_service = PluginLicensingService(session)
    
    subscription = await licensing_service.create_plugin_subscription(
        tenant_id=tenant_id,
        plugin_id=plugin_id,
        tier=tier,
        trial_days=14 if tier != PluginTier.FREE else None
    )
    
    return subscription
```

### **Usage Tracking**

```python
# Record plugin usage for billing
async def track_plugin_usage(
    tenant_id: str,
    plugin_id: str, 
    metric: str,
    usage_count: int
):
    licensing_service = PluginLicensingService(session)
    
    # This will check limits and record usage
    usage_record = await licensing_service.record_plugin_usage(
        tenant_id=tenant_id,
        plugin_id=plugin_id,
        metric_name=metric,
        usage_count=usage_count
    )
    
    return usage_record
```

### **Access Control**

```python
# Check if tenant can access a plugin feature
async def validate_plugin_access(tenant_id: str, plugin_id: str, feature: str):
    licensing_service = PluginLicensingService(session)
    
    has_access, reason = await licensing_service.validate_plugin_access(
        tenant_id=tenant_id,
        plugin_id=plugin_id,
        feature_name=feature
    )
    
    if not has_access:
        raise PermissionDenied(f"Plugin access denied: {reason}")
    
    return True
```

## 📈 **Usage Examples**

### **Tenant Plugin Dashboard**

```python
# API endpoint to get tenant's plugin subscriptions
@router.get("/tenants/{tenant_id}/plugins")
async def get_tenant_plugins(
    tenant_id: str,
    session: AsyncSession = Depends(get_session)
):
    licensing_service = PluginLicensingService(session)
    
    subscriptions = await licensing_service.get_tenant_plugin_subscriptions(
        tenant_id=tenant_id,
        active_only=True
    )
    
    return {
        "tenant_id": tenant_id,
        "active_plugins": len(subscriptions),
        "subscriptions": [
            {
                "plugin_id": sub.plugin_id,
                "plugin_name": sub.plugin.plugin_name,
                "tier": sub.tier.value,
                "status": sub.status.value,
                "expires_at": sub.expires_at,
                "usage_limits": sub.usage_limits,
                "current_usage": sub.current_usage
            }
            for sub in subscriptions
        ]
    }
```

### **Plugin Marketplace**

```python
# API endpoint for plugin marketplace
@router.get("/plugins/catalog")
async def get_plugin_catalog(
    category: Optional[str] = None,
    tier: Optional[PluginTier] = None,
    session: AsyncSession = Depends(get_session)
):
    licensing_service = PluginLicensingService(session)
    
    plugins = await licensing_service.get_plugin_catalog(
        category=category,
        tier=tier,
        public_only=True
    )
    
    return {
        "total_plugins": len(plugins),
        "plugins": [
            {
                "plugin_id": plugin.plugin_id,
                "name": plugin.plugin_name,
                "description": plugin.plugin_description,
                "category": plugin.category,
                "tier": plugin.tier.value,
                "monthly_price": plugin.monthly_price,
                "annual_price": plugin.annual_price,
                "features": plugin.features,
                "trial_days": plugin.trial_days
            }
            for plugin in plugins
        ]
    }
```

### **Usage-Based Billing Report**

```python
# Generate usage summary for billing
async def generate_usage_billing_report(tenant_id: str, month: int, year: int):
    licensing_service = PluginLicensingService(session)
    
    # Get all plugin subscriptions for tenant
    subscriptions = await licensing_service.get_tenant_plugin_subscriptions(tenant_id)
    
    billing_summary = {
        "tenant_id": tenant_id,
        "billing_period": f"{year}-{month:02d}",
        "total_charges": Decimal("0.00"),
        "plugin_charges": []
    }
    
    for subscription in subscriptions:
        # Get usage summary for billing period
        usage_summary = await licensing_service.get_plugin_usage_summary(
            tenant_id=tenant_id,
            plugin_id=subscription.plugin_id,
            start_date=date(year, month, 1),
            end_date=date(year, month + 1, 1) - timedelta(days=1)
        )
        
        plugin_total = usage_summary["total_charges"]
        billing_summary["total_charges"] += plugin_total
        billing_summary["plugin_charges"].append({
            "plugin_id": subscription.plugin_id,
            "plugin_name": subscription.plugin.plugin_name,
            "base_charge": subscription.monthly_price or Decimal("0.00"),
            "usage_charges": plugin_total,
            "usage_details": usage_summary["usage_by_metric"]
        })
    
    return billing_summary
```

## 🎛️ **Admin Operations**

### **Plugin Management**

```python
# Create a new plugin
async def create_new_plugin():
    plugin = PluginCatalog(
        plugin_id="custom_branding",
        plugin_name="Custom Branding Suite",
        plugin_description="White-label customization and branding tools",
        category="customization",
        tier=PluginTier.PREMIUM,
        monthly_price=Decimal("39.99"),
        features={
            "premium": [
                "custom_logo",
                "color_schemes", 
                "custom_css",
                "branded_emails"
            ],
            "enterprise": [
                "custom_logo",
                "color_schemes",
                "custom_css", 
                "branded_emails",
                "white_label_domains",
                "custom_login_pages"
            ]
        },
        usage_limits={
            "premium": {
                "custom_themes": 5,
                "branded_templates": 10
            },
            "enterprise": {
                "custom_themes": -1,  # unlimited
                "branded_templates": -1
            }
        }
    )
    
    return plugin
```

### **Subscription Management**

```python
# Upgrade a plugin subscription
async def upgrade_plugin_subscription(tenant_id: str, plugin_id: str):
    licensing_service = PluginLicensingService(session)
    
    # Get current subscription
    current_sub = await licensing_service.get_plugin_subscription(tenant_id, plugin_id)
    
    if current_sub.tier == PluginTier.BASIC:
        new_tier = PluginTier.PREMIUM
    elif current_sub.tier == PluginTier.PREMIUM:
        new_tier = PluginTier.ENTERPRISE
    else:
        raise ValueError("Cannot upgrade from current tier")
    
    # Perform upgrade
    upgraded_sub = await licensing_service.upgrade_plugin_subscription(
        tenant_id=tenant_id,
        plugin_id=plugin_id,
        new_tier=new_tier
    )
    
    return upgraded_sub
```

## 🔒 **Security & Compliance**

### **License Validation**

```python
# Middleware to validate plugin access
async def validate_plugin_access_middleware(
    request: Request,
    plugin_id: str,
    feature: Optional[str] = None
):
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id:
        raise HTTPException(401, "Missing tenant ID")
    
    licensing_service = PluginLicensingService(request.app.state.db_session)
    
    has_access, reason = await licensing_service.validate_plugin_access(
        tenant_id=tenant_id,
        plugin_id=plugin_id,
        feature_name=feature
    )
    
    if not has_access:
        raise HTTPException(403, f"Plugin access denied: {reason}")
    
    return True
```

### **Audit Logging**

```python
# Automatic audit logging for licensing events
class PluginLicenseHistory(TenantModel):
    action_type = Column(String(50), nullable=False)  # activated, suspended, upgraded
    previous_status = Column(Enum(LicenseStatus), nullable=True)  
    new_status = Column(Enum(LicenseStatus), nullable=False)
    reason = Column(Text, nullable=True)
    changed_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    changed_at = Column(DateTime(timezone=True), default=datetime.utcnow)
```

## 📊 **Analytics & Reporting**

### **Plugin Performance Metrics**

```python
# Track plugin adoption and usage across tenant base
async def get_plugin_analytics():
    return {
        "total_plugins": await session.scalar(select(func.count(PluginCatalog.id))),
        "active_subscriptions": await session.scalar(
            select(func.count(PluginSubscription.id))
            .where(PluginSubscription.status == LicenseStatus.ACTIVE)
        ),
        "monthly_revenue": await calculate_plugin_revenue(),
        "top_plugins": await get_most_popular_plugins(),
        "usage_trends": await get_usage_trends()
    }
```

### **Revenue Analytics**

```python
# Calculate plugin-specific revenue
async def calculate_plugin_revenue(plugin_id: Optional[str] = None):
    query = select(
        func.sum(PluginUsageRecord.total_charge),
        func.count(PluginSubscription.id)
    ).select_from(
        PluginSubscription.__table__.join(PluginUsageRecord.__table__)
    )
    
    if plugin_id:
        query = query.where(PluginSubscription.plugin_id == plugin_id)
    
    result = await session.execute(query)
    total_revenue, subscription_count = result.first()
    
    return {
        "total_revenue": total_revenue or Decimal("0.00"),
        "active_subscriptions": subscription_count or 0,
        "average_revenue_per_subscription": (
            total_revenue / subscription_count 
            if subscription_count > 0 
            else Decimal("0.00")
        )
    }
```

## 🚀 **Getting Started**

### **1. Initialize Plugin Catalog**

```bash
# Seed the plugin catalog with initial plugins
python -m mgmt.scripts.seed_plugin_catalog
```

### **2. Create a Plugin Subscription**

```bash
# Subscribe a tenant to a plugin via API
curl -X POST http://localhost:8000/api/v1/plugins/subscriptions \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "demo-isp-001",
    "plugin_id": "advanced_analytics",
    "tier": "premium",
    "trial_days": 14
  }'
```

### **3. Track Plugin Usage**

```bash
# Record plugin usage
curl -X POST http://localhost:8000/api/v1/plugins/usage \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "demo-isp-001", 
    "plugin_id": "advanced_analytics",
    "metric_name": "reports_generated",
    "usage_count": 1
  }'
```

### **4. Check Usage Summary**

```bash
# Get usage summary for billing
curl "http://localhost:8000/api/v1/plugins/usage-summary/demo-isp-001/advanced_analytics?start_date=2025-01-01&end_date=2025-01-31"
```

## 🎯 **Best Practices**

### **Plugin Development**
- Design plugins with clear tier boundaries
- Implement graceful degradation for lower tiers
- Include comprehensive usage metrics
- Provide clear documentation and onboarding

### **Subscription Management**
- Implement automatic trial-to-paid conversion
- Provide clear usage limits and overage notifications
- Enable easy upgrades and downgrades
- Maintain audit trails for all license changes

### **Billing Integration**
- Track usage in real-time for accurate billing
- Implement usage-based pricing for scalable revenue
- Provide transparent billing breakdowns
- Enable self-service subscription management

This plugin licensing system transforms the ISP Framework into a scalable SaaS platform with flexible monetization options, enabling sustainable growth while providing value-based pricing for customers.