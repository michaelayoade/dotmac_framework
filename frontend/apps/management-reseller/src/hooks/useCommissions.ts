import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { API } from '@/lib/api/endpoints';
import { queryKeys, invalidateQueries } from '@/lib/query-client';
import type { CommissionFilters } from '@/lib/api/types';
import type {
  Commission,
  CommissionSummary,
  CommissionApproval,
  BulkCommissionAction,
  BulkCommissionResult,
} from '@/types/commission';

// Query hooks
export function useCommissions(filters?: CommissionFilters) {
  return useQuery({
    queryKey: queryKeys.commissionsList(filters),
    queryFn: () => API.commissions.list(filters),
    enabled: true,
  });
}

export function useCommission(id: string) {
  return useQuery({
    queryKey: queryKeys.commissionsDetail(id),
    queryFn: () => API.commissions.getById(id),
    enabled: !!id,
  });
}

export function useCommissionSummary() {
  return useQuery({
    queryKey: queryKeys.commissionsSummary(),
    queryFn: () => API.commissions.getSummary(),
    staleTime: 2 * 60 * 1000, // 2 minutes for summary data
  });
}

// Mutation hooks
export function useApproveCommission() {
  const queryClient = useQueryClient();
  const { updateCommissionOptimistically, revertOptimisticUpdate } = useOptimisticCommissionUpdate();

  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) => 
      API.commissions.approveSingle(id, notes),
    onMutate: async ({ id }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.commissionsDetail(id) });
      
      // Optimistically update the commission status
      updateCommissionOptimistically(id, { status: 'APPROVED', approved_at: new Date().toISOString() });
      
      return { id };
    },
    onSuccess: (data, { id }) => {
      // Update the specific commission in cache with server response
      queryClient.setQueryData(
        queryKeys.commissionsDetail(id),
        data
      );
      
      invalidateQueries.commissions();
      invalidateQueries.analytics();
    },
    onError: (error, { id }) => {
      // Revert optimistic update on error
      revertOptimisticUpdate(id);
    },
  });
}

export function useBulkApproveCommissions() {
  return useMutation({
    mutationFn: ({ ids, notes }: { ids: string[]; notes?: string }) => 
      API.commissions.bulkApprove(ids, notes),
    onSuccess: () => {
      invalidateQueries.commissions();
      invalidateQueries.analytics();
    },
  });
}

export function useProcessCommission() {
  const queryClient = useQueryClient();
  const { updateCommissionOptimistically, revertOptimisticUpdate } = useOptimisticCommissionUpdate();

  return useMutation({
    mutationFn: (id: string) => API.commissions.processSingle(id),
    onMutate: async (id) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.commissionsDetail(id) });
      
      // Optimistically update the commission status
      updateCommissionOptimistically(id, { status: 'PAID', paid_at: new Date().toISOString() });
      
      return { id };
    },
    onSuccess: (data, id) => {
      // Update the specific commission in cache with server response
      queryClient.setQueryData(
        queryKeys.commissionsDetail(id),
        data
      );
      
      invalidateQueries.commissions();
      invalidateQueries.analytics();
    },
    onError: (error, id) => {
      // Revert optimistic update on error
      revertOptimisticUpdate(id);
    },
  });
}

export function useBulkProcessCommissions() {
  return useMutation({
    mutationFn: (ids: string[]) => API.commissions.bulkProcess(ids),
    onSuccess: () => {
      invalidateQueries.commissions();
      invalidateQueries.analytics();
    },
  });
}

export function useDisputeCommission() {
  const queryClient = useQueryClient();
  const { updateCommissionOptimistically, revertOptimisticUpdate } = useOptimisticCommissionUpdate();

  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => 
      API.commissions.dispute(id, reason),
    onMutate: async ({ id, reason }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.commissionsDetail(id) });
      
      // Optimistically update the commission status
      updateCommissionOptimistically(id, { 
        status: 'DISPUTED', 
        disputed_at: new Date().toISOString(),
        dispute_reason: reason
      });
      
      return { id };
    },
    onSuccess: (data, { id }) => {
      // Update the specific commission in cache with server response
      queryClient.setQueryData(
        queryKeys.commissionsDetail(id),
        data
      );
      
      invalidateQueries.commissions();
      invalidateQueries.analytics();
    },
    onError: (error, { id }) => {
      // Revert optimistic update on error
      revertOptimisticUpdate(id);
    },
  });
}

export function useExportCommissions() {
  return useMutation({
    mutationFn: (filters?: CommissionFilters) => API.commissions.export(filters),
    onSuccess: (data) => {
      // Create download link
      const url = window.URL.createObjectURL(data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `commissions-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },
  });
}

// Custom hook for commission statistics
export function useCommissionStats() {
  return useQuery({
    queryKey: [...queryKeys.commissions(), 'stats'],
    queryFn: async () => {
      const commissionsResponse = await API.commissions.list();
      const commissions = commissionsResponse.data;
      
      return {
        total: commissions.length,
        calculated: commissions.filter(c => c.status === 'CALCULATED').length,
        approved: commissions.filter(c => c.status === 'APPROVED').length,
        paid: commissions.filter(c => c.status === 'PAID').length,
        disputed: commissions.filter(c => c.status === 'DISPUTED').length,
        totalAmount: commissions.reduce((sum, c) => sum + c.net_amount, 0),
        averageAmount: commissions.length > 0 
          ? commissions.reduce((sum, c) => sum + c.net_amount, 0) / commissions.length 
          : 0,
        byPaymentMethod: commissions.reduce((acc, commission) => {
          acc[commission.payment_method] = (acc[commission.payment_method] || 0) + 1;
          return acc;
        }, {} as Record<string, number>),
      };
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Optimistic update helper for commissions
export function useOptimisticCommissionUpdate() {
  const queryClient = useQueryClient();

  const updateCommissionOptimistically = (id: string, updates: any) => {
    queryClient.setQueryData(
      queryKeys.commissionsDetail(id),
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
    queryClient.invalidateQueries({ queryKey: queryKeys.commissionsDetail(id) });
  };

  return { updateCommissionOptimistically, revertOptimisticUpdate };
}