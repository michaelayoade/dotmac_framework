/**
 * React Hook for Revenue Calculations
 * Provides revenue and commission calculation functionality
 */

import { useCallback } from 'react';
import { useBusinessLogic } from './useBusinessLogic';
import type {
  DateRange,
  Commission,
  PlatformRevenue,
  UsageData,
  PricingPlan,
  PortalContext,
} from '../types';

interface UseRevenueCalculationsProps {
  portalType: PortalContext['portalType'];
  userId: string;
  permissions: string[];
  tenantId?: string;
}

export function useRevenueCalculations(props: UseRevenueCalculationsProps) {
  const { revenue: revenueEngine } = useBusinessLogic(props);

  const calculateCustomerRevenue = useCallback(
    async (
      customerId: string,
      period: DateRange,
      options?: {
        includeUsage?: boolean;
        includeOverages?: boolean;
        includeTaxes?: boolean;
        includeDiscounts?: boolean;
      }
    ): Promise<number> => {
      return revenueEngine.calculateCustomerRevenue({
        customerId,
        period,
        ...options,
      });
    },
    [revenueEngine]
  );

  const calculatePartnerCommissions = useCallback(
    async (
      partnerId: string,
      period: DateRange,
      options?: {
        includeNewCustomers?: boolean;
        includeRenewals?: boolean;
        includeUpgrades?: boolean;
        commissionTier?: 'standard' | 'premium' | 'enterprise';
      }
    ): Promise<Commission[]> => {
      return revenueEngine.calculatePartnerCommissions({
        partnerId,
        period,
        ...options,
      });
    },
    [revenueEngine]
  );

  const calculatePlatformRevenue = useCallback(
    async (
      tenantId: string,
      period: DateRange,
      options?: {
        includeProjections?: boolean;
        includeCosts?: boolean;
        includeMetrics?: boolean;
      }
    ): Promise<PlatformRevenue> => {
      return revenueEngine.calculatePlatformRevenue({
        tenantId,
        period,
        ...options,
      });
    },
    [revenueEngine]
  );

  const applyPricingTiers = useCallback(
    (usageData: UsageData, pricingPlan: PricingPlan): number => {
      return revenueEngine.applyPricingTiers(usageData, pricingPlan);
    },
    [revenueEngine]
  );

  return {
    calculateCustomerRevenue,
    calculatePartnerCommissions,
    calculatePlatformRevenue,
    applyPricingTiers,
  };
}
