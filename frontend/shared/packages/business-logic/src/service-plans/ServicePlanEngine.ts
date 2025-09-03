/**
 * Service Plan Management Engine
 * Shared across Admin, Customer, and Reseller portals
 */

import Decimal from 'decimal.js';
import { addMonths, differenceInDays, isAfter, isBefore } from 'date-fns';
import type {
  ServicePlan,
  UpgradeImpact,
  EligibilityResult,
  Money,
  DateRange,
  PortalContext,
  BusinessLogicConfig,
} from '../types';

export interface PlanFilterCriteria {
  customerType?: 'residential' | 'business' | 'enterprise';
  maxPrice?: number;
  minSpeed?: number;
  serviceTypes?: ('fiber' | 'cable' | 'dsl' | 'wireless' | 'satellite')[];
  regions?: string[];
  features?: string[];
  contractTerms?: {
    maxTermMonths?: number;
    allowMonthToMonth?: boolean;
  };
}

export interface PlanChangeRequest {
  customerId: string;
  currentPlanId: string;
  targetPlanId: string;
  effectiveDate: Date;
  reason: 'upgrade' | 'downgrade' | 'feature_change' | 'cost_optimization' | 'service_issue';
  requestedBy: string;
  specialInstructions?: string;
}

export interface CustomerPlanHistory {
  customerId: string;
  changes: PlanChange[];
  totalPlanChanges: number;
  averageMonthsOnPlan: number;
  preferredPlanFeatures: string[];
}

export interface PlanChange {
  id: string;
  fromPlan: ServicePlan;
  toPlan: ServicePlan;
  effectiveDate: Date;
  reason: string;
  impact: UpgradeImpact;
  status: 'pending' | 'approved' | 'scheduled' | 'completed' | 'cancelled';
  completedAt?: Date;
  costs: {
    prorationCredit?: Money;
    prorationCharge?: Money;
    installationFee?: Money;
    equipmentFee?: Money;
    earlyTerminationFee?: Money;
    totalCost: Money;
  };
}

export class ServicePlanEngine {
  private config: BusinessLogicConfig;
  private context: PortalContext;

  constructor(config: BusinessLogicConfig, context: PortalContext) {
    this.config = config;
    this.context = context;
  }

  /**
   * Get available service plans based on customer type and filtering criteria
   * Used by: Admin (all plans), Customer (eligible plans), Reseller (offered plans)
   */
  async getAvailablePlans(
    customerType: 'residential' | 'business' | 'enterprise',
    filters?: PlanFilterCriteria
  ): Promise<ServicePlan[]> {
    try {
      // Validate access permissions
      this.validatePlanAccess();

      // Get all plans for the customer type
      const allPlans = await this.fetchPlansFromApi(customerType);

      // Apply portal-specific filtering
      let filteredPlans = this.applyPortalFiltering(allPlans);

      // Apply user-provided filters
      if (filters) {
        filteredPlans = this.applyPlanFilters(filteredPlans, filters);
      }

      // Sort plans by relevance (price, popularity, etc.)
      return this.sortPlansByRelevance(filteredPlans, customerType);
    } catch (error) {
      console.error('Failed to get available plans:', error);
      throw new Error(
        `Failed to retrieve service plans: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  }

  /**
   * Calculate the impact of upgrading/downgrading from current plan to target plan
   * Used by: Admin (plan change analysis), Customer (upgrade preview), Reseller (sales tools)
   */
  async calculateUpgradeImpact(
    currentPlanId: string,
    targetPlanId: string,
    effectiveDate?: Date
  ): Promise<UpgradeImpact> {
    try {
      this.validatePlanAccess();

      const [currentPlan, targetPlan] = await Promise.all([
        this.getPlanById(currentPlanId),
        this.getPlanById(targetPlanId),
      ]);

      if (!currentPlan || !targetPlan) {
        throw new Error('One or both service plans not found');
      }

      const changeDate = effectiveDate || new Date();

      // Calculate service changes
      const changes = this.calculateServiceChanges(currentPlan, targetPlan);

      // Calculate pricing impact
      const pricing = this.calculatePricingImpact(currentPlan, targetPlan, changeDate);

      // Calculate timeline and requirements
      const timeline = await this.calculateChangeTimeline(currentPlan, targetPlan, changeDate);

      const upgradeImpact: UpgradeImpact = {
        currentPlan,
        targetPlan,
        changes,
        pricing,
        timeline,
      };

      return upgradeImpact;
    } catch (error) {
      console.error('Failed to calculate upgrade impact:', error);
      throw new Error(
        `Failed to calculate upgrade impact: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  }

  /**
   * Apply a plan change for a customer
   * Used by: Admin (plan management), Customer (self-service upgrades), Reseller (plan changes)
   */
  async applyPlanChange(
    customerId: string,
    newPlanId: string,
    effectiveDate: Date,
    changeRequest?: Partial<PlanChangeRequest>
  ): Promise<PlanChange> {
    try {
      this.validatePlanChangeAccess(customerId);

      // Get current customer plan
      const currentPlan = await this.getCurrentCustomerPlan(customerId);
      const targetPlan = await this.getPlanById(newPlanId);

      if (!currentPlan || !targetPlan) {
        throw new Error('Current plan or target plan not found');
      }

      // Validate eligibility
      const eligibility = await this.validatePlanEligibility(customerId, newPlanId);
      if (!eligibility.eligible) {
        throw new Error(`Plan change not eligible: ${eligibility.reasons.join(', ')}`);
      }

      // Calculate impact and costs
      const impact = await this.calculateUpgradeImpact(currentPlan.id, newPlanId, effectiveDate);

      // Create plan change record
      const planChange: PlanChange = {
        id: this.generatePlanChangeId(),
        fromPlan: currentPlan,
        toPlan: targetPlan,
        effectiveDate,
        reason: changeRequest?.reason || 'upgrade',
        impact,
        status: this.determineInitialStatus(impact),
        costs: {
          prorationCredit:
            impact.pricing.currentMonthlyPrice.amount > impact.pricing.newMonthlyPrice.amount
              ? {
                  amount:
                    impact.pricing.currentMonthlyPrice.amount -
                    impact.pricing.newMonthlyPrice.amount,
                  currency: impact.pricing.currentMonthlyPrice.currency,
                }
              : undefined,
          prorationCharge: impact.pricing.proratedCharge,
          installationFee: impact.pricing.installationFee,
          equipmentFee: impact.pricing.equipmentFee,
          totalCost: impact.pricing.totalUpfrontCost,
        },
      };

      // Process the plan change
      const processedChange = await this.processPlanChange(customerId, planChange);

      // Schedule provisioning if required
      if (impact.timeline.requiresInstallation) {
        await this.scheduleServiceProvisioning(customerId, planChange);
      }

      // Update customer record
      await this.updateCustomerPlan(customerId, planChange);

      // Send notifications based on portal context
      await this.sendPlanChangeNotifications(customerId, planChange);

      return processedChange;
    } catch (error) {
      console.error('Failed to apply plan change:', error);
      throw new Error(
        `Failed to apply plan change: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  }

  /**
   * Validate customer eligibility for a specific plan
   * Used by: Admin (eligibility checks), Customer (plan validation), Reseller (sales qualification)
   */
  async validatePlanEligibility(customerId: string, planId: string): Promise<EligibilityResult> {
    try {
      this.validateCustomerAccess(customerId);

      const [customer, plan, currentPlan] = await Promise.all([
        this.getCustomerDetails(customerId),
        this.getPlanById(planId),
        this.getCurrentCustomerPlan(customerId),
      ]);

      if (!customer || !plan) {
        return {
          eligible: false,
          reasons: ['Customer or plan not found'],
        };
      }

      const reasons: string[] = [];
      let eligible = true;

      // 1. Geographic eligibility
      if (!this.isServiceAvailableInRegion(plan, customer.address.region)) {
        eligible = false;
        reasons.push('Service not available in customer region');
      }

      // 2. Credit check requirements
      if (plan.pricing.basePrice.amount > customer.creditLimit && !customer.creditCheckPassed) {
        eligible = false;
        reasons.push('Credit check required for this plan');
      }

      // 3. Technical feasibility
      const technicalEligibility = await this.checkTechnicalEligibility(customer, plan);
      if (!technicalEligibility.feasible) {
        eligible = false;
        reasons.push(...technicalEligibility.reasons);
      }

      // 4. Contract restrictions
      if (currentPlan) {
        const contractRestrictions = this.checkContractRestrictions(currentPlan, plan);
        if (contractRestrictions.restricted) {
          eligible = false;
          reasons.push(...contractRestrictions.reasons);
        }
      }

      // 5. Plan-specific requirements
      const planRequirements = this.checkPlanSpecificRequirements(customer, plan);
      if (planRequirements.length > 0) {
        // These might be requirements rather than blockers
      }

      const result: EligibilityResult = {
        eligible,
        reasons,
      };

      // Add requirements if eligible but conditions apply
      if (eligible && planRequirements.length > 0) {
        result.requirements = {
          creditCheck: planRequirements.includes('credit_check'),
          equipmentUpgrade: planRequirements.includes('equipment_upgrade'),
          serviceVisit: planRequirements.includes('service_visit'),
          contractExtension: planRequirements.includes('contract_extension'),
        };
      }

      // Add restrictions if contract limitations apply
      if (currentPlan && this.hasContractRestrictions(currentPlan)) {
        result.restrictions = {
          minimumContractMonths: currentPlan.contractTerms.minimumTermMonths,
          earlyTerminationPenalty: currentPlan.contractTerms.earlyTerminationFee || {
            amount: 0,
            currency: 'USD',
          },
          geographicLimitations: plan.availability.regions,
        };
      }

      return result;
    } catch (error) {
      console.error('Failed to validate plan eligibility:', error);
      throw new Error(
        `Failed to validate plan eligibility: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  }

  /**
   * Get customer's plan history and recommendations
   * Used by: Admin (customer insights), Customer (plan history), Reseller (customer analysis)
   */
  async getCustomerPlanHistory(customerId: string): Promise<CustomerPlanHistory> {
    try {
      this.validateCustomerAccess(customerId);

      const planChanges = await this.getCustomerPlanChanges(customerId);
      const analytics = this.analyzePlanHistory(planChanges);

      return {
        customerId,
        changes: planChanges,
        totalPlanChanges: planChanges.length,
        averageMonthsOnPlan: analytics.averageMonthsOnPlan,
        preferredPlanFeatures: analytics.preferredFeatures,
      };
    } catch (error) {
      console.error('Failed to get customer plan history:', error);
      throw new Error(
        `Failed to retrieve customer plan history: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  }

  // Private helper methods
  private validatePlanAccess(): void {
    const hasAccess =
      this.context.permissions.includes('plans:read') ||
      this.context.permissions.includes('customer:read') ||
      this.context.portalType === 'customer';

    if (!hasAccess) {
      throw new Error('Insufficient permissions to access service plans');
    }
  }

  private validatePlanChangeAccess(customerId: string): void {
    const hasAccess =
      this.context.permissions.includes('plans:write') ||
      (this.context.portalType === 'customer' && this.context.userId === customerId) ||
      this.context.portalType === 'admin' ||
      this.context.portalType === 'reseller';

    if (!hasAccess) {
      throw new Error('Insufficient permissions to change service plans');
    }
  }

  private validateCustomerAccess(customerId: string): void {
    const hasAccess =
      this.context.permissions.includes('customer:read') ||
      (this.context.portalType === 'customer' && this.context.userId === customerId) ||
      this.context.portalType === 'admin';

    if (!hasAccess) {
      throw new Error('Insufficient permissions to access customer data');
    }
  }

  private applyPortalFiltering(plans: ServicePlan[]): ServicePlan[] {
    switch (this.context.portalType) {
      case 'customer':
        // Customers see only plans they're eligible for
        return plans.filter((plan) => this.isCustomerEligibleForPlan(plan));

      case 'reseller':
        // Resellers see only plans they're authorized to sell
        return plans.filter((plan) => this.isResellerAuthorizedForPlan(plan));

      case 'admin':
      case 'management-admin':
        // Admins see all plans
        return plans;

      default:
        return plans;
    }
  }

  private applyPlanFilters(plans: ServicePlan[], filters: PlanFilterCriteria): ServicePlan[] {
    return plans.filter((plan) => {
      // Customer type filter
      if (filters.customerType && plan.category !== filters.customerType) {
        return false;
      }

      // Price filter
      if (filters.maxPrice && plan.pricing.basePrice.amount > filters.maxPrice) {
        return false;
      }

      // Speed filter
      if (filters.minSpeed && plan.technical.downloadSpeedMbps < filters.minSpeed) {
        return false;
      }

      // Service type filter
      if (
        filters.serviceTypes &&
        !filters.serviceTypes.some((type) => plan.availability.serviceTypes.includes(type))
      ) {
        return false;
      }

      // Region filter
      if (
        filters.regions &&
        !filters.regions.some((region) => plan.availability.regions.includes(region))
      ) {
        return false;
      }

      // Features filter
      if (
        filters.features &&
        !filters.features.every((feature) =>
          plan.pricing.features.some((planFeature) => planFeature.name.includes(feature))
        )
      ) {
        return false;
      }

      // Contract terms filter
      if (filters.contractTerms) {
        if (
          filters.contractTerms.maxTermMonths &&
          plan.contractTerms.minimumTermMonths > filters.contractTerms.maxTermMonths
        ) {
          return false;
        }

        if (filters.contractTerms.allowMonthToMonth && plan.contractTerms.minimumTermMonths > 1) {
          return false;
        }
      }

      return true;
    });
  }

  private sortPlansByRelevance(plans: ServicePlan[], customerType: string): ServicePlan[] {
    return plans.sort((a, b) => {
      // Prioritize by customer type match
      if (a.category === customerType && b.category !== customerType) return -1;
      if (b.category === customerType && a.category !== customerType) return 1;

      // Then by price (ascending for residential, descending for business/enterprise)
      const priceSort =
        customerType === 'residential'
          ? a.pricing.basePrice.amount - b.pricing.basePrice.amount
          : b.pricing.basePrice.amount - a.pricing.basePrice.amount;

      return priceSort;
    });
  }

  private calculateServiceChanges(currentPlan: ServicePlan, targetPlan: ServicePlan) {
    const speedIncrease = {
      downloadMbps:
        targetPlan.technical.downloadSpeedMbps - currentPlan.technical.downloadSpeedMbps,
      uploadMbps: targetPlan.technical.uploadSpeedMbps - currentPlan.technical.uploadSpeedMbps,
    };

    const dataAllowanceChange =
      (targetPlan.technical.dataAllowanceGB || 0) - (currentPlan.technical.dataAllowanceGB || 0);

    const featureChanges = this.calculateFeatureChanges(currentPlan, targetPlan);

    return {
      speedIncrease,
      dataAllowanceChange: dataAllowanceChange !== 0 ? dataAllowanceChange : undefined,
      featureChanges,
    };
  }

  private calculatePricingImpact(
    currentPlan: ServicePlan,
    targetPlan: ServicePlan,
    effectiveDate: Date
  ) {
    const currentMonthlyPrice = currentPlan.pricing.basePrice;
    const newMonthlyPrice = targetPlan.pricing.basePrice;
    const monthlyDifference = {
      amount: newMonthlyPrice.amount - currentMonthlyPrice.amount,
      currency: newMonthlyPrice.currency,
    };

    // Calculate prorated charges/credits
    const daysUntilEndOfMonth = this.getDaysUntilEndOfMonth(effectiveDate);
    const daysInMonth = this.getDaysInMonth(effectiveDate);
    const prorationFactor = daysUntilEndOfMonth / daysInMonth;

    const proratedCharge =
      monthlyDifference.amount > 0
        ? {
            amount: monthlyDifference.amount * prorationFactor,
            currency: monthlyDifference.currency,
          }
        : undefined;

    // Installation and equipment fees
    const installationFee = targetPlan.technical.installationFee;
    const equipmentFee = this.calculateEquipmentUpgradeFee(currentPlan, targetPlan);

    const totalUpfrontCost = {
      amount:
        (proratedCharge?.amount || 0) +
        (installationFee?.amount || 0) +
        (equipmentFee?.amount || 0),
      currency: newMonthlyPrice.currency,
    };

    return {
      currentMonthlyPrice,
      newMonthlyPrice,
      monthlyDifference,
      proratedCharge,
      installationFee,
      equipmentFee,
      totalUpfrontCost,
    };
  }

  private async calculateChangeTimeline(
    currentPlan: ServicePlan,
    targetPlan: ServicePlan,
    effectiveDate: Date
  ) {
    const requiresInstallation = this.requiresInstallation(currentPlan, targetPlan);
    const estimatedInstallationDays = requiresInstallation
      ? await this.getEstimatedInstallationTime(targetPlan)
      : 0;

    const estimatedActivationDate = addMonths(effectiveDate, 0);
    if (requiresInstallation) {
      estimatedActivationDate.setDate(
        estimatedActivationDate.getDate() + estimatedInstallationDays
      );
    }

    return {
      effectiveDate,
      estimatedActivationDate,
      requiresInstallation,
      estimatedInstallationDays,
    };
  }

  private calculateFeatureChanges(currentPlan: ServicePlan, targetPlan: ServicePlan) {
    const currentFeatures = new Set(currentPlan.pricing.features.map((f) => f.id));
    const targetFeatures = new Set(targetPlan.pricing.features.map((f) => f.id));

    const added = targetPlan.pricing.features.filter((f) => !currentFeatures.has(f.id));
    const removed = currentPlan.pricing.features.filter((f) => !targetFeatures.has(f.id));
    const modified = targetPlan.pricing.features.filter((f) => {
      const currentFeature = currentPlan.pricing.features.find((cf) => cf.id === f.id);
      return (
        currentFeature &&
        (currentFeature.included !== f.included ||
          currentFeature.additionalCost?.amount !== f.additionalCost?.amount)
      );
    });

    return { added, removed, modified };
  }

  private generatePlanChangeId(): string {
    return `pc_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private determineInitialStatus(impact: UpgradeImpact): 'pending' | 'approved' | 'scheduled' {
    // Business logic to determine if approval is needed
    if (impact.pricing.totalUpfrontCost.amount > 100) {
      return 'pending'; // Requires approval for high-cost changes
    }

    if (impact.timeline.requiresInstallation) {
      return 'scheduled'; // Requires scheduling
    }

    return 'approved'; // Can proceed immediately
  }

  private requiresInstallation(currentPlan: ServicePlan, targetPlan: ServicePlan): boolean {
    // Check if upgrade requires new equipment or service visit
    return (
      targetPlan.availability.requiresInstallation ||
      currentPlan.availability.serviceTypes[0] !== targetPlan.availability.serviceTypes[0]
    );
  }

  private getDaysUntilEndOfMonth(date: Date): number {
    const endOfMonth = new Date(date.getFullYear(), date.getMonth() + 1, 0);
    return Math.max(0, differenceInDays(endOfMonth, date));
  }

  private getDaysInMonth(date: Date): number {
    return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
  }

  private calculateEquipmentUpgradeFee(
    currentPlan: ServicePlan,
    targetPlan: ServicePlan
  ): Money | undefined {
    // Logic to calculate equipment upgrade fees
    const currentEquipment = new Set(currentPlan.technical.equipmentIncluded);
    const targetEquipment = new Set(targetPlan.technical.equipmentIncluded);

    const newEquipment = [...targetEquipment].filter((eq) => !currentEquipment.has(eq));

    if (newEquipment.length === 0) {
      return undefined;
    }

    // Simplified equipment fee calculation
    return {
      amount: newEquipment.length * 50, // $50 per equipment item
      currency: 'USD',
    };
  }

  // API integration methods (these would call actual API endpoints)
  private async fetchPlansFromApi(customerType: string): Promise<ServicePlan[]> {
    throw new Error('Method not implemented - requires API integration');
  }

  private async getPlanById(planId: string): Promise<ServicePlan | null> {
    throw new Error('Method not implemented - requires API integration');
  }

  private async getCurrentCustomerPlan(customerId: string): Promise<ServicePlan | null> {
    throw new Error('Method not implemented - requires API integration');
  }

  private async getCustomerDetails(customerId: string): Promise<any> {
    throw new Error('Method not implemented - requires API integration');
  }

  private async getCustomerPlanChanges(customerId: string): Promise<PlanChange[]> {
    throw new Error('Method not implemented - requires API integration');
  }

  private async getEstimatedInstallationTime(plan: ServicePlan): Promise<number> {
    // This would integrate with scheduling system
    return 7; // Default 7 days
  }

  private async processPlanChange(customerId: string, planChange: PlanChange): Promise<PlanChange> {
    throw new Error('Method not implemented - requires API integration');
  }

  private async scheduleServiceProvisioning(
    customerId: string,
    planChange: PlanChange
  ): Promise<void> {
    throw new Error('Method not implemented - requires API integration');
  }

  private async updateCustomerPlan(customerId: string, planChange: PlanChange): Promise<void> {
    throw new Error('Method not implemented - requires API integration');
  }

  private async sendPlanChangeNotifications(
    customerId: string,
    planChange: PlanChange
  ): Promise<void> {
    throw new Error('Method not implemented - requires API integration');
  }

  private isCustomerEligibleForPlan(plan: ServicePlan): boolean {
    // Customer-specific eligibility logic
    return true; // Simplified
  }

  private isResellerAuthorizedForPlan(plan: ServicePlan): boolean {
    // Reseller authorization logic
    return true; // Simplified
  }

  private isServiceAvailableInRegion(plan: ServicePlan, region: string): boolean {
    return plan.availability.regions.includes(region);
  }

  private async checkTechnicalEligibility(
    customer: any,
    plan: ServicePlan
  ): Promise<{ feasible: boolean; reasons: string[] }> {
    // Technical feasibility checks
    return { feasible: true, reasons: [] };
  }

  private checkContractRestrictions(
    currentPlan: ServicePlan,
    targetPlan: ServicePlan
  ): { restricted: boolean; reasons: string[] } {
    // Contract restriction logic
    return { restricted: false, reasons: [] };
  }

  private checkPlanSpecificRequirements(customer: any, plan: ServicePlan): string[] {
    // Plan-specific requirement checks
    return [];
  }

  private hasContractRestrictions(plan: ServicePlan): boolean {
    return plan.contractTerms.minimumTermMonths > 1;
  }

  private analyzePlanHistory(changes: PlanChange[]): {
    averageMonthsOnPlan: number;
    preferredFeatures: string[];
  } {
    // Analyze customer plan change patterns
    return {
      averageMonthsOnPlan: 12, // Simplified
      preferredFeatures: [], // Simplified
    };
  }
}
