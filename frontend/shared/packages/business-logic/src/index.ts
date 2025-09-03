/**
 * DotMac Business Logic Library
 * Shared business operations across all ISP portals
 */

// Export types
export * from './types';

// Export engines
export { RevenueEngine } from './revenue/RevenueEngine';
export { ServicePlanEngine } from './service-plans/ServicePlanEngine';
export { NetworkServiceEngine } from './network/NetworkServiceEngine';

// Export factory function for creating configured engines
export { BusinessLogicFactory } from './factory/BusinessLogicFactory';

// Export React hooks for easy integration
export { useBusinessLogic } from './hooks/useBusinessLogic';
export { useRevenueCalculations } from './hooks/useRevenueCalculations';
export { useServicePlans } from './hooks/useServicePlans';
export { useNetworkOperations } from './hooks/useNetworkOperations';
