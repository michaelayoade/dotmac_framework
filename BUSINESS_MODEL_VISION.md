# 🎯 **DotMac Platform Business Model & Vision**

*Definitive business model documentation - source of truth for all platform communications*

## **💡 Executive Vision**

**DotMac is a SaaS platform that provides Internet Service Providers (ISPs) with complete operational management through dedicated containerized instances, using usage-based per-customer pricing plus premium feature bundles.**

---

## **🏗️ Business Model Architecture**

### **Platform Operator Model**
- **You (Platform Owner)** operate the DotMac Management Platform
- **ISPs** are tenants who get dedicated containers for their operations  
- **Vendors/Resellers** can partner to resell services to ISPs
- **ISPs** manage their own customers and can have sub-resellers

### **Revenue Streams**

#### **Primary Revenue: Usage-Based SaaS**
```
Base Pricing: Per-customer monthly fee (market-competitive rates)
- ISP with 100 customers = Competitive monthly rate
- ISP with 1,000 customers = Scaled pricing  
- ISP with 5,000 customers = Enterprise volume pricing
```

#### **Premium Feature Bundles**
- **Reseller Platform**: $100-300/month (enables ISP to manage resellers)
- **Advanced CRM Bundle**: $50-150/month (sales pipeline, lead management)
- **Project Management Bundle**: $75-200/month (field ops, work orders)
- **Field Operations Bundle**: $100-250/month (technician management, scheduling)
- **AI Chatbot Bundle**: $50-150/month (automated customer support)
- **Advanced Analytics**: $25-100/month (business intelligence, reporting)

#### **Partner Revenue: Reseller Commissions**
- **Vendor Partners**: 10-20% commission on sales they generate
- **Implementation Partners**: $500-2,000 per ISP onboarding
- **Support Partners**: $100-500/month per ISP managed

---

## **🔧 Technical Architecture Model**

### **Container-per-Tenant Isolation**
```
Management Platform (Your Infrastructure):
├── Shared Services
│   ├── Tenant Management & Billing
│   ├── Partner Portal & Commission Tracking  
│   ├── Marketplace & Premium Features
│   └── Monitoring & Support Dashboard
├── Per-ISP Containers
│   ├── Dedicated ISP Framework Instance
│   ├── Isolated PostgreSQL Database
│   ├── Custom Configuration & Branding
│   └── Resource Scaling Based on Customer Count
└── Shared Infrastructure
    ├── Redis (Multi-tenant Safe)
    ├── OpenBao Secrets Management
    ├── SignOz Centralized Monitoring
    └── Load Balancing & SSL Termination
```

### **Deployment Model**
- **ISPs never see Kubernetes** - they get a simple container deployment
- **Automatic scaling** based on customer count (50-10,000 customers)
- **Zero-downtime updates** for ISP containers
- **4-minute provisioning** for new ISP tenants

---

## **🎯 Target Markets**

### **Primary Market: Small-Medium ISPs**
- **Rural/Wireless ISPs**: 50-2,000 customers
- **Regional Cable/Fiber**: 500-5,000 customers  
- **WISP Operators**: 100-3,000 customers
- **Emerging ISPs**: 50-1,000 customers

### **Geographic Focus**
- **Phase 1**: North America (US/Canada)
- **Phase 2**: English-speaking markets (AU/NZ/UK)
- **Phase 3**: European expansion

---

## **📊 Unit Economics**

### **Cost Structure per ISP Tenant**
```
Revenue (500 customers): Usage-based fee + Premium bundles = Competitive total
Costs:
- Container infrastructure: $25/month
- Database & storage: $15/month  
- Monitoring & support: $10/month
- Platform overhead: $20/month
Total Cost: $70/month

Gross Margin: Strong margin at scale (target 80%+)
```

### **Scale Economics**
```
At 100 ISP Tenants (50,000 total customers):
Revenue: Usage-based revenue + Premium bundles = Strong monthly recurring revenue
Costs: $7,000/month infrastructure + $8,000/month operations = $15,000/month
Gross Profit: Strong margins at scale (target 60-80%)
Net Revenue (after all costs): Sustainable profit margins
```

---

## **🤝 Partnership Strategy**

### **Vendor Reseller Network**
- **Hardware Vendors**: Ubiquiti, Cambium, MikroTik partnerships
- **ISP Consultants**: Implementation and ongoing management services
- **Regional Distributors**: Geographic market penetration
- **Software Integrators**: Custom plugin development

### **Revenue Sharing Model**
- **Sales Commissions**: 10-20% of first year revenue
- **Ongoing Referral**: 5-10% of monthly recurring revenue
- **Implementation Fees**: $500-2,000 per successful deployment
- **Support Revenue**: 30-50% of support service revenue

---

## **🚀 Go-to-Market Strategy**

### **Customer Acquisition**
1. **Direct Sales**: Target ISPs directly with competitive per-customer value proposition
2. **Partner Channel**: Leverage vendor relationships for warm introductions
3. **Community Engagement**: WISP associations, industry conferences
4. **Content Marketing**: ISP operational efficiency content and case studies

### **Customer Success & Expansion**
1. **Onboarding**: 4-minute automated provisioning + 7-day guided setup
2. **Adoption**: Feature usage tracking and expansion recommendations
3. **Retention**: 99.5% uptime SLA + dedicated success management
4. **Expansion**: Premium bundle upgrades based on usage patterns

---

## **📈 Success Metrics & KPIs**

### **Business Metrics**
- **Monthly Recurring Revenue (MRR)**: Target $10K by month 12
- **Customer Count per ISP**: Average 500 customers per tenant
- **Premium Bundle Attach Rate**: 60% of ISPs use 2+ bundles
- **Gross Revenue Retention**: >95% year-over-year
- **Net Revenue Retention**: >120% (through expansion)

### **Operational Metrics**
- **ISP Onboarding Time**: <4 minutes automated + <2 hours guided
- **Platform Uptime**: >99.5% per ISP container
- **Support Response Time**: <2 hours for critical issues
- **Container Resource Efficiency**: <$30/month per ISP infrastructure cost

### **Partner Metrics**
- **Partner-Generated Revenue**: 40% of total sales by year 2
- **Partner Satisfaction**: >90% would recommend program
- **Commission Payments**: On-time payment to partners
- **Partner Onboarding**: <1 week from inquiry to active selling

---

## **🎯 Competitive Differentiation**

### **vs. Traditional ISP Software**
- **No upfront license fees** - pay only for active customers
- **Instant deployment** - 4 minutes vs 3-6 months implementation
- **Modern architecture** - cloud-native vs legacy on-premise systems
- **Automatic scaling** - no infrastructure management required

### **vs. Other SaaS ISP Platforms**
- **True multi-tenancy** - dedicated containers vs shared databases
- **Vendor agnostic** - works with any hardware vs ecosystem lock-in
- **Transparent pricing** - Simple per-customer rates vs complex pricing tiers
- **Partner-friendly** - revenue sharing vs direct-only sales

---

## **📋 Documentation Alignment Requirements**

**All documentation MUST communicate:**

1. **SaaS-First Model**: ISPs are tenants, not software buyers
2. **Container-per-Tenant**: Each ISP gets dedicated infrastructure  
3. **Usage-Based Pricing**: Per-customer pricing + premium bundles
4. **Partner Network**: Vendor/reseller revenue sharing opportunity
5. **Operational Focus**: Platform owner manages infrastructure, ISPs focus on customers

**Deprecated Language to Remove:**
- ❌ "ISP software license"
- ❌ "On-premise deployment"
- ❌ "Self-hosted installation"
- ❌ "Kubernetes for ISPs"
- ❌ "ISP manages infrastructure"

**Required Language to Use:**
- ✅ "SaaS platform for ISPs"
- ✅ "Container-per-tenant isolation"
- ✅ "Usage-based per-customer pricing"
- ✅ "Vendor partner network"
- ✅ "Automated ISP provisioning"

---

This document serves as the **single source of truth** for all business model communications across documentation, marketing materials, and partner communications.