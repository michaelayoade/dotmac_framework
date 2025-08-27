/**
 * Customer Data Hooks
 * Provides React hooks for customer data fetching and management
 */

import { useQuery } from '@tanstack/react-query';
import { customerApi } from '../lib/api/customerApi';

// Hook for network status data
export function useNetworkStatus() {
  return useQuery({
    queryKey: ['network-status'],
    queryFn: () => customerApi.getNetworkStatus(),
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // 1 minute
  });
}

// Hook for usage data
export function useUsageData() {
  return useQuery({
    queryKey: ['usage-data'],
    queryFn: () => customerApi.getUsageData(),
    staleTime: 300000, // 5 minutes
    refetchInterval: 300000, // 5 minutes
  });
}

// Hook for billing information
export function useBillingInfo() {
  return useQuery({
    queryKey: ['billing-info'],
    queryFn: () => customerApi.getBillingInfo(),
    staleTime: 600000, // 10 minutes
    refetchInterval: false, // No auto refetch for billing
  });
}

// Hook for notifications
export function useNotifications() {
  return useQuery({
    queryKey: ['notifications'],
    queryFn: () => customerApi.getNotifications(),
    staleTime: 60000, // 1 minute
    refetchInterval: 120000, // 2 minutes
  });
}

// Hook for customer profile
export function useCustomerProfile() {
  return useQuery({
    queryKey: ['customer-profile'],
    queryFn: () => customerApi.getProfile(),
    staleTime: 300000, // 5 minutes
    refetchInterval: false, // No auto refetch for profile
  });
}