/**
 * Revenue & Commission Calculation Engine
 * Shared across Management Admin, ISP Admin, and Reseller portals
 */

import Decimal from 'decimal.js';
import { startOfMonth, endOfMonth, differenceInDays, addMonths } from 'date-fns';
import type {
  DateRange,
  Money,
  UsageData,
  PricingPlan,
  Commission,
  PlatformRevenue,
  PortalContext,
  BusinessLogicConfig,
} from '../types';

export interface RevenueCalculationParams {
  customerId: string;
  period: DateRange;
  includeUsage?: boolean;
  includeOverages?: boolean;
  includeTaxes?: boolean;
  includeDiscounts?: boolean;
}

export interface CommissionCalculationParams {
  partnerId: string;
  period: DateRange;
  includeNewCustomers?: boolean;
  includeRenewals?: boolean;
  includeUpgrades?: boolean;
  commissionTier?: 'standard' | 'premium' | 'enterprise';
}

export interface PlatformRevenueParams {
  tenantId: string;
  period: DateRange;
  includeProjections?: boolean;
  includeCosts?: boolean;
  includeMetrics?: boolean;
}

export class RevenueEngine {
  private config: BusinessLogicConfig;
  private context: PortalContext;

  constructor(config: BusinessLogicConfig, context: PortalContext) {
    this.config = config;
    this.context = context;
  }

  /**
   * Calculate customer revenue for a given period
   * Used by: Management Admin (platform revenue), ISP Admin (customer billing), Reseller (territory revenue)
   */
  async calculateCustomerRevenue(
    params: RevenueCalculationParams
  ): Promise<number> {
    try {
      // Validate permissions
      this.validateRevenueAccess(params.customerId);

      const { customerId, period, includeUsage = true, includeOverages = true, includeTaxes = true, includeDiscounts = true } = params;

      // Get customer's service plan and usage data
      const [customerPlan, usageData, discounts] = await Promise.all([
        this.getCustomerServicePlan(customerId),
        includeUsage ? this.getUsageData(customerId, period) : null,
        includeDiscounts ? this.getCustomerDiscounts(customerId, period) : [],
      ]);

      let totalRevenue = new Decimal(0);

      // 1. Base subscription revenue (prorated if partial period)
      const subscriptionRevenue = this.calculateSubscriptionRevenue(customerPlan, period);
      totalRevenue = totalRevenue.add(subscriptionRevenue);

      // 2. Usage-based revenue (data overages, premium features)
      if (includeUsage && usageData) {
        const usageRevenue = this.calculateUsageRevenue(usageData, customerPlan);
        totalRevenue = totalRevenue.add(usageRevenue);
      }

      // 3. Overage charges (data, bandwidth, API calls)
      if (includeOverages && usageData) {
        const overageRevenue = this.calculateOverageRevenue(usageData, customerPlan);
        totalRevenue = totalRevenue.add(overageRevenue);
      }

      // 4. Apply discounts
      if (includeDiscounts && discounts.length > 0) {
        const discountAmount = this.calculateDiscounts(discounts, totalRevenue.toNumber());
        totalRevenue = totalRevenue.minus(discountAmount);
      }

      // 5. Apply taxes (if required by portal context)
      if (includeTaxes && this.shouldApplyTaxes()) {
        const taxRate = await this.getTaxRate(customerId);
        const taxAmount = totalRevenue.times(taxRate);
        totalRevenue = totalRevenue.add(taxAmount);
      }

      return totalRevenue.toNumber();
    } catch (error) {
      console.error('Revenue calculation failed:', error);
      throw new Error(`Failed to calculate customer revenue: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Calculate partner commissions for a given period
   * Used by: Management Admin (partner payouts), Reseller Portal (earnings tracking)
   */
  async calculatePartnerCommissions(
    params: CommissionCalculationParams
  ): Promise<Commission[]> {
    try {
      this.validateCommissionAccess(params.partnerId);

      const { partnerId, period, includeNewCustomers = true, includeRenewals = true, includeUpgrades = true, commissionTier = 'standard' } = params;

      // Get partner configuration and commission rates
      const [partnerConfig, commissionRates, customerRevenues] = await Promise.all([
        this.getPartnerConfiguration(partnerId),
        this.getCommissionRates(partnerId, commissionTier),
        this.getPartnerCustomerRevenues(partnerId, period),
      ]);

      const commissions: Commission[] = [];

      for (const customerRevenue of customerRevenues) {
        // Determine commission eligibility based on customer type and activity
        const customerType = this.determineCustomerType(customerRevenue);

        if (!this.isCommissionEligible(customerType, { includeNewCustomers, includeRenewals, includeUpgrades })) {
          continue;
        }

        // Calculate commission based on revenue and partner tier
        const commissionRate = this.getCommissionRate(commissionRates, customerRevenue.serviceType, customerType);
        const commissionAmount = new Decimal(customerRevenue.revenue.amount).times(commissionRate).toNumber();

        const commission: Commission = {
          id: this.generateCommissionId(partnerId, customerRevenue.customerId, period),
          partnerId,
          customerId: customerRevenue.customerId,
          serviceId: customerRevenue.serviceId,
          revenue: customerRevenue.revenue,
          commissionRate,
          commissionAmount: {
            amount: commissionAmount,
            currency: customerRevenue.revenue.currency,
          },
          period,
          status: 'calculated',
          calculatedAt: new Date(),
          metadata: {
            planType: customerRevenue.planType,
            customerType,
            paymentMethod: customerRevenue.paymentMethod,
          },
        };

        commissions.push(commission);
      }

      return commissions;
    } catch (error) {
      console.error('Commission calculation failed:', error);
      throw new Error(`Failed to calculate partner commissions: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Calculate platform revenue for a tenant (ISP)
   * Used by: Management Admin (SaaS revenue tracking), ISP Admin (business analytics)
   */
  async calculatePlatformRevenue(
    params: PlatformRevenueParams
  ): Promise<PlatformRevenue> {
    try {
      this.validatePlatformRevenueAccess(params.tenantId);

      const { tenantId, period, includeProjections = false, includeCosts = true, includeMetrics = true } = params;

      // Get all revenue sources for the tenant
      const [
        customerRevenues,
        subscriptionRevenue,
        usageRevenue,
        operationalCosts,
        customerMetrics,
      ] = await Promise.all([
        this.getTenantCustomerRevenues(tenantId, period),
        this.getTenantSubscriptionRevenue(tenantId, period),
        this.getTenantUsageRevenue(tenantId, period),
        includeCosts ? this.getTenantOperationalCosts(tenantId, period) : null,
        includeMetrics ? this.getTenantCustomerMetrics(tenantId, period) : null,
      ]);

      // Calculate total revenue
      const totalCustomerRevenue = customerRevenues.reduce((sum, revenue) => sum + revenue.amount, 0);
      const totalSubscriptionRevenue = subscriptionRevenue.reduce((sum, revenue) => sum + revenue.amount, 0);
      const totalUsageRevenue = usageRevenue.reduce((sum, revenue) => sum + revenue.amount, 0);
      const totalRevenue = totalCustomerRevenue + totalSubscriptionRevenue + totalUsageRevenue;

      // Calculate costs and net revenue
      const costs = includeCosts && operationalCosts ? {
        infrastructure: operationalCosts.infrastructure,
        support: operationalCosts.support,
        marketing: operationalCosts.marketing,
        commissions: operationalCosts.commissions,
        total: operationalCosts.total,
      } : {
        infrastructure: { amount: 0, currency: 'USD' },
        support: { amount: 0, currency: 'USD' },
        marketing: { amount: 0, currency: 'USD' },
        commissions: { amount: 0, currency: 'USD' },
        total: { amount: 0, currency: 'USD' },
      };

      const netRevenue = totalRevenue - costs.total.amount;

      // Build metrics
      const metrics = includeMetrics && customerMetrics ? {
        totalCustomers: customerMetrics.totalCustomers,
        newCustomers: customerMetrics.newCustomers,
        churnedCustomers: customerMetrics.churnedCustomers,
        averageRevenuePerCustomer: {
          amount: customerMetrics.totalCustomers > 0 ? totalCustomerRevenue / customerMetrics.totalCustomers : 0,
          currency: 'USD',
        },
        customerLifetimeValue: {
          amount: customerMetrics.averageLifetimeValue,
          currency: 'USD',
        },
      } : {
        totalCustomers: 0,
        newCustomers: 0,
        churnedCustomers: 0,
        averageRevenuePerCustomer: { amount: 0, currency: 'USD' },
        customerLifetimeValue: { amount: 0, currency: 'USD' },
      };

      const platformRevenue: PlatformRevenue = {
        tenantId,
        period,
        customerRevenue: { amount: totalCustomerRevenue, currency: 'USD' },
        subscriptionRevenue: { amount: totalSubscriptionRevenue, currency: 'USD' },
        usageRevenue: { amount: totalUsageRevenue, currency: 'USD' },
        totalRevenue: { amount: totalRevenue, currency: 'USD' },
        costs,
        netRevenue: { amount: netRevenue, currency: 'USD' },
        metrics,
      };

      return platformRevenue;
    } catch (error) {
      console.error('Platform revenue calculation failed:', error);
      throw new Error(`Failed to calculate platform revenue: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Apply pricing tiers to usage data
   * Used across all portals for consistent pricing calculations
   */
  applyPricingTiers(usageData: UsageData, pricingPlan: PricingPlan): number {
    if (!pricingPlan.tiers || pricingPlan.tiers.length === 0) {
      return pricingPlan.basePrice.amount;
    }

    let totalCost = new Decimal(pricingPlan.basePrice.amount);
    let remainingUsage = usageData.totalBytes;

    // Convert bytes to the appropriate unit for pricing tiers
    const usageInPlanUnit = this.convertBytesToPlanUnit(remainingUsage, pricingPlan.tiers[0].unit);

    for (const tier of pricingPlan.tiers) {
      if (usageInPlanUnit <= tier.threshold) {
        break;
      }

      const tierUsage = Math.min(usageInPlanUnit - tier.threshold, remainingUsage);
      if (tierUsage > 0) {
        const tierCost = new Decimal(tierUsage).times(tier.unitPrice.amount);
        totalCost = totalCost.add(tierCost);
        remainingUsage -= tierUsage;
      }
    }

    return totalCost.toNumber();
  }

  // Private helper methods
  private validateRevenueAccess(customerId: string): void {
    // Check if user has permission to access customer revenue data
    const hasAccess = this.context.permissions.includes('revenue:read') ||
                     this.context.permissions.includes('customer:read') ||
                     this.context.portalType === 'management-admin';

    if (!hasAccess) {
      throw new Error('Insufficient permissions to access revenue data');
    }
  }

  private validateCommissionAccess(partnerId: string): void {
    const hasAccess = this.context.permissions.includes('commission:read') ||
                     this.context.permissions.includes('partner:read') ||
                     (this.context.portalType === 'reseller' && this.context.userId === partnerId) ||
                     this.context.portalType === 'management-admin';

    if (!hasAccess) {
      throw new Error('Insufficient permissions to access commission data');
    }
  }

  private validatePlatformRevenueAccess(tenantId: string): void {
    const hasAccess = this.context.permissions.includes('platform:revenue:read') ||
                     (this.context.tenantId === tenantId && this.context.permissions.includes('tenant:analytics:read')) ||
                     this.context.portalType === 'management-admin';

    if (!hasAccess) {
      throw new Error('Insufficient permissions to access platform revenue data');
    }
  }

  private calculateSubscriptionRevenue(plan: PricingPlan, period: DateRange): number {
    const totalDays = differenceInDays(period.endDate, period.startDate);
    const daysInMonth = differenceInDays(endOfMonth(period.startDate), startOfMonth(period.startDate));

    // Prorate the subscription revenue based on the actual period
    const prorationFactor = totalDays / daysInMonth;
    return new Decimal(plan.basePrice.amount).times(prorationFactor).toNumber();
  }

  private calculateUsageRevenue(usageData: UsageData, plan: PricingPlan): number {
    if (!plan.tiers || plan.tiers.length === 0) {
      return 0;
    }

    return this.applyPricingTiers(usageData, plan);
  }

  private calculateOverageRevenue(usageData: UsageData, plan: PricingPlan): number {
    if (!usageData.overage) {
      return 0;
    }

    return new Decimal(usageData.overage.bytes)
      .dividedBy(1024 * 1024 * 1024) // Convert to GB
      .times(usageData.overage.chargePerGB)
      .toNumber();
  }

  private calculateDiscounts(discounts: any[], baseRevenue: number): number {
    let totalDiscount = new Decimal(0);

    for (const discount of discounts) {
      if (discount.type === 'percentage') {
        const discountAmount = new Decimal(baseRevenue).times(discount.value).dividedBy(100);
        totalDiscount = totalDiscount.add(discountAmount);
      } else if (discount.type === 'fixed') {
        totalDiscount = totalDiscount.add(discount.value);
      }
    }

    return totalDiscount.toNumber();
  }

  private shouldApplyTaxes(): boolean {
    // Tax application logic based on portal type and configuration
    return this.context.portalType !== 'management-admin' && this.config.features.revenueCalculation;
  }

  private convertBytesToPlanUnit(bytes: number, unit: 'GB' | 'TB' | 'Mbps'): number {
    switch (unit) {
      case 'GB':
        return bytes / (1024 * 1024 * 1024);
      case 'TB':
        return bytes / (1024 * 1024 * 1024 * 1024);
      case 'Mbps':
        // For bandwidth-based pricing, we'd need additional context
        return bytes / (1024 * 1024); // Simplified conversion
      default:
        return bytes;
    }
  }

  private determineCustomerType(customerRevenue: any): 'new' | 'upgrade' | 'renewal' {
    // Logic to determine customer type based on revenue data
    // This would be implemented based on business rules
    return customerRevenue.type || 'renewal';
  }

  private isCommissionEligible(
    customerType: 'new' | 'upgrade' | 'renewal',
    options: { includeNewCustomers: boolean; includeRenewals: boolean; includeUpgrades: boolean }
  ): boolean {
    switch (customerType) {
      case 'new':
        return options.includeNewCustomers;
      case 'upgrade':
        return options.includeUpgrades;
      case 'renewal':
        return options.includeRenewals;
      default:
        return false;
    }
  }

  private getCommissionRate(rates: any, serviceType: string, customerType: string): number {
    // Get commission rate based on service type and customer type
    return rates[serviceType]?.[customerType] || rates.default || 0.1; // Default 10%
  }

  private generateCommissionId(partnerId: string, customerId: string, period: DateRange): string {
    const periodKey = `${period.startDate.getFullYear()}-${period.startDate.getMonth() + 1}`;
    return `comm_${partnerId}_${customerId}_${periodKey}`;
  }

  // API integration methods (these would call actual API endpoints)
  private async getCustomerServicePlan(customerId: string): Promise<PricingPlan> {
    // Implementation would make API call to get customer's current plan
    throw new Error('Method not implemented - requires API integration');
  }

  private async getUsageData(customerId: string, period: DateRange): Promise<UsageData> {
    // Implementation would make API call to get usage data
    throw new Error('Method not implemented - requires API integration');
  }

  private async getCustomerDiscounts(customerId: string, period: DateRange): Promise<any[]> {
    // Implementation would make API call to get customer discounts
    throw new Error('Method not implemented - requires API integration');
  }

  private async getTaxRate(customerId: string): Promise<number> {
    // Implementation would determine tax rate based on customer location
    throw new Error('Method not implemented - requires API integration');
  }

  private async getPartnerConfiguration(partnerId: string): Promise<any> {
    throw new Error('Method not implemented - requires API integration');
  }

  private async getCommissionRates(partnerId: string, tier: string): Promise<any> {
    throw new Error('Method not implemented - requires API integration');
  }

  private async getPartnerCustomerRevenues(partnerId: string, period: DateRange): Promise<any[]> {
    throw new Error('Method not implemented - requires API integration');
  }

  private async getTenantCustomerRevenues(tenantId: string, period: DateRange): Promise<Money[]> {
    throw new Error('Method not implemented - requires API integration');
  }

  private async getTenantSubscriptionRevenue(tenantId: string, period: DateRange): Promise<Money[]> {
    throw new Error('Method not implemented - requires API integration');
  }

  private async getTenantUsageRevenue(tenantId: string, period: DateRange): Promise<Money[]> {
    throw new Error('Method not implemented - requires API integration');
  }

  private async getTenantOperationalCosts(tenantId: string, period: DateRange): Promise<any> {
    throw new Error('Method not implemented - requires API integration');
  }

  private async getTenantCustomerMetrics(tenantId: string, period: DateRange): Promise<any> {
    throw new Error('Method not implemented - requires API integration');
  }
}
