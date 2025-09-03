/**
 * React Hook for Service Plan Management
 * Provides service plan operations and plan change functionality
 */

import { useCallback } from 'react';
import { useBusinessLogic } from './useBusinessLogic';
import type {
  ServicePlan,
  UpgradeImpact,
  EligibilityResult,
  CustomerPlanHistory,
  PortalContext,
} from '../types';

interface UseServicePlansProps {
  portalType: PortalContext['portalType'];
  userId: string;
  permissions: string[];
  tenantId?: string;
}

interface PlanFilterCriteria {
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

export function useServicePlans(props: UseServicePlansProps) {
  const { servicePlans: servicePlanEngine } = useBusinessLogic(props);

  const getAvailablePlans = useCallback(
    async (
      customerType: 'residential' | 'business' | 'enterprise',
      filters?: PlanFilterCriteria
    ): Promise<ServicePlan[]> => {
      return servicePlanEngine.getAvailablePlans(customerType, filters);
    },
    [servicePlanEngine]
  );

  const calculateUpgradeImpact = useCallback(
    async (
      currentPlanId: string,
      targetPlanId: string,
      effectiveDate?: Date
    ): Promise<UpgradeImpact> => {
      return servicePlanEngine.calculateUpgradeImpact(currentPlanId, targetPlanId, effectiveDate);
    },
    [servicePlanEngine]
  );

  const applyPlanChange = useCallback(
    async (
      customerId: string,
      newPlanId: string,
      effectiveDate: Date,
      options?: {
        reason?: 'upgrade' | 'downgrade' | 'feature_change' | 'cost_optimization' | 'service_issue';
        requestedBy?: string;
        specialInstructions?: string;
      }
    ) => {
      return servicePlanEngine.applyPlanChange(customerId, newPlanId, effectiveDate, options);
    },
    [servicePlanEngine]
  );

  const validatePlanEligibility = useCallback(
    async (customerId: string, planId: string): Promise<EligibilityResult> => {
      return servicePlanEngine.validatePlanEligibility(customerId, planId);
    },
    [servicePlanEngine]
  );

  const getCustomerPlanHistory = useCallback(
    async (customerId: string): Promise<CustomerPlanHistory> => {
      return servicePlanEngine.getCustomerPlanHistory(customerId);
    },
    [servicePlanEngine]
  );

  return {
    getAvailablePlans,
    calculateUpgradeImpact,
    applyPlanChange,
    validatePlanEligibility,
    getCustomerPlanHistory,
  };
}
