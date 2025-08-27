import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { API } from '@/lib/api/endpoints';
import { queryKeys, invalidateQueries } from '@/lib/query-client';
import type { PartnerFilters, Partner } from '@/lib/api/types';
import type {
  PartnerStats,
  CreatePartnerRequest,
  UpdatePartnerRequest,
  BulkPartnerAction,
  BulkPartnerResult,
} from '@/types/partner';

// Query hooks
export function usePartners(filters?: PartnerFilters) {
  return useQuery({
    queryKey: queryKeys.partnersList(filters),
    queryFn: () => API.partners.list(filters),
    enabled: true,
  });
}

export function usePartner(id: string) {
  return useQuery({
    queryKey: queryKeys.partnersDetail(id),
    queryFn: () => API.partners.getById(id),
    enabled: !!id,
  });
}

// Mutation hooks
export function useCreatePartner() {
  return useMutation({
    mutationFn: (partner: Partial<Partner>) => API.partners.create(partner),
    onSuccess: () => {
      invalidateQueries.partners();
      invalidateQueries.analytics();
    },
  });
}

export function useUpdatePartner() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, partner }: { id: string; partner: Partial<Partner> }) => 
      API.partners.update(id, partner),
    onSuccess: (data, variables) => {
      // Update the specific partner in cache
      queryClient.setQueryData(
        queryKeys.partnersDetail(variables.id),
        data
      );
      
      // Invalidate lists and analytics
      invalidateQueries.partners();
      invalidateQueries.analytics();
    },
  });
}

export function useDeletePartner() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => API.partners.delete(id),
    onSuccess: (data, id) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: queryKeys.partnersDetail(id) });
      
      // Invalidate lists and analytics
      invalidateQueries.partners();
      invalidateQueries.analytics();
    },
  });
}

export function useApprovePartner() {
  const queryClient = useQueryClient();
  const { updatePartnerOptimistically, revertOptimisticUpdate } = useOptimisticPartnerUpdate();

  return useMutation({
    mutationFn: (id: string) => API.partners.approve(id),
    onMutate: async (id) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.partnersDetail(id) });
      
      // Optimistically update the partner status
      updatePartnerOptimistically(id, { status: 'ACTIVE' });
      
      return { id };
    },
    onSuccess: (data, id) => {
      // Update the specific partner in cache with server response
      queryClient.setQueryData(
        queryKeys.partnersDetail(id),
        data
      );
      
      // Invalidate lists and analytics
      invalidateQueries.partners();
      invalidateQueries.onboarding();
      invalidateQueries.analytics();
    },
    onError: (error, id) => {
      // Revert optimistic update on error
      revertOptimisticUpdate(id);
    },
  });
}

export function useSuspendPartner() {
  const queryClient = useQueryClient();
  const { updatePartnerOptimistically, revertOptimisticUpdate } = useOptimisticPartnerUpdate();

  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) => 
      API.partners.suspend(id, reason),
    onMutate: async ({ id }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.partnersDetail(id) });
      
      // Optimistically update the partner status
      updatePartnerOptimistically(id, { status: 'SUSPENDED' });
      
      return { id };
    },
    onSuccess: (_data, { id }) => {
      // Update the specific partner in cache with server response
      queryClient.setQueryData(
        queryKeys.partnersDetail(id),
        _data
      );
      
      // Invalidate lists and analytics
      invalidateQueries.partners();
      invalidateQueries.analytics();
    },
    onError: (error, { id }) => {
      // Revert optimistic update on error
      revertOptimisticUpdate(id);
    },
  });
}

export function useUpdatePartnerTier() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, tier }: { id: string; tier: string }) => 
      API.partners.updateTier(id, tier),
    onSuccess: (data, { id }) => {
      // Update the specific partner in cache
      queryClient.setQueryData(
        queryKeys.partnersDetail(id),
        data
      );
      
      // Invalidate lists and analytics
      invalidateQueries.partners();
      invalidateQueries.analytics();
    },
  });
}

// Optimistic update helper
export function useOptimisticPartnerUpdate() {
  const queryClient = useQueryClient();

  const updatePartnerOptimistically = (id: string, updates: Partial<Partner>) => {
    queryClient.setQueryData(
      queryKeys.partnersDetail(id),
      (oldData: any) => {
        if (!oldData?.data) return oldData;
        return {
          ...oldData,
          data: {
            ...oldData.data,
            ...updates,
            updated_at: new Date().toISOString(),
          },
        };
      }
    );
  };

  const revertOptimisticUpdate = (id: string) => {
    queryClient.invalidateQueries({ queryKey: queryKeys.partnersDetail(id) });
  };

  return { updatePartnerOptimistically, revertOptimisticUpdate };
}

// Custom hook for partner statistics
export function usePartnerStats() {
  return useQuery({
    queryKey: [...queryKeys.partners(), 'stats'],
    queryFn: async () => {
      const partnersResponse = await API.partners.list();
      const partners = partnersResponse.data;
      
      return {
        total: partners.length,
        active: partners.filter(p => p.status === 'ACTIVE').length,
        pending: partners.filter(p => p.status === 'PENDING').length,
        suspended: partners.filter(p => p.status === 'SUSPENDED').length,
        byTier: partners.reduce((acc, partner) => {
          acc[partner.tier] = (acc[partner.tier] || 0) + 1;
          return acc;
        }, {} as Record<string, number>),
        byType: partners.reduce((acc, partner) => {
          acc[partner.partner_type] = (acc[partner.partner_type] || 0) + 1;
          return acc;
        }, {} as Record<string, number>),
      };
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}