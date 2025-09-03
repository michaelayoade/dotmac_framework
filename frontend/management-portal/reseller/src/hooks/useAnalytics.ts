import { useQuery } from '@tanstack/react-query';
import { API } from '@/lib/api/endpoints';
import { queryKeys } from '@/lib/query-client';

export function useChannelMetrics() {
  return useQuery({
    queryKey: queryKeys.channelMetrics(),
    queryFn: () => API.analytics.getChannelMetrics(),
    staleTime: 2 * 60 * 1000, // 2 minutes for analytics data
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
  });
}

export function usePartnerPerformance(partnerId?: string) {
  return useQuery({
    queryKey: queryKeys.partnerPerformance(partnerId),
    queryFn: () => API.analytics.getPartnerPerformance(partnerId),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: partnerId !== undefined || partnerId === undefined, // Always enabled for both cases
  });
}

export function useRevenueByTier() {
  return useQuery({
    queryKey: queryKeys.revenueByTier(),
    queryFn: () => API.analytics.getRevenueByTier(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useCommissionTrends() {
  return useQuery({
    queryKey: queryKeys.commissionTrends(),
    queryFn: () => API.analytics.getCommissionTrends(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useTerritoryMetrics() {
  return useQuery({
    queryKey: queryKeys.territoryMetrics(),
    queryFn: () => API.analytics.getTerritoryMetrics(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Combined dashboard metrics hook
export function useDashboardMetrics() {
  const channelMetrics = useChannelMetrics();
  const partnerPerformance = usePartnerPerformance();
  const revenueByTier = useRevenueByTier();
  const commissionTrends = useCommissionTrends();

  return {
    channelMetrics: channelMetrics.data?.data,
    partnerPerformance: partnerPerformance.data?.data,
    revenueByTier: revenueByTier.data?.data,
    commissionTrends: commissionTrends.data?.data,
    isLoading:
      channelMetrics.isLoading ||
      partnerPerformance.isLoading ||
      revenueByTier.isLoading ||
      commissionTrends.isLoading,
    error:
      channelMetrics.error ||
      partnerPerformance.error ||
      revenueByTier.error ||
      commissionTrends.error,
    refetch: () => {
      channelMetrics.refetch();
      partnerPerformance.refetch();
      revenueByTier.refetch();
      commissionTrends.refetch();
    },
  };
}
