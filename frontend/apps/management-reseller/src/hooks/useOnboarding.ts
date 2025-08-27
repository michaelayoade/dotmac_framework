import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { API } from '@/lib/api/endpoints';
import { queryKeys, invalidateQueries } from '@/lib/query-client';
import type { OnboardingFilters } from '@/lib/api/types';
import type {
  OnboardingRequest,
  OnboardingStep,
  OnboardingStats,
  CreateOnboardingRequest,
  UpdateOnboardingStepData,
  OnboardingOptimisticUpdate,
} from '@/types/onboarding';

// Query hooks
export function useOnboardingSteps(partnerId?: string) {
  return useQuery({
    queryKey: queryKeys.onboardingSteps(partnerId),
    queryFn: () => API.onboarding.getSteps(partnerId),
    enabled: !!partnerId,
  });
}

export function useOnboardingRequests(filters?: OnboardingFilters) {
  return useQuery({
    queryKey: queryKeys.onboardingList(filters),
    queryFn: () => API.onboarding.list(filters),
    enabled: true,
  });
}

export function useOnboardingRequest(id: string) {
  return useQuery({
    queryKey: queryKeys.onboardingDetail(id),
    queryFn: () => API.onboarding.getById(id),
    enabled: !!id,
  });
}

// Mutation hooks
export function useCreateOnboardingRequest() {
  return useMutation({
    mutationFn: (data: CreateOnboardingRequest) => API.onboarding.create(data),
    onSuccess: () => {
      invalidateQueries.onboarding();
      invalidateQueries.partners();
      invalidateQueries.analytics();
    },
  });
}

export function useUpdateOnboardingStep() {
  const queryClient = useQueryClient();
  const { updateOnboardingOptimistically, revertOptimisticUpdate } = useOptimisticOnboardingUpdate();

  return useMutation({
    mutationFn: ({ stepId, data }: { stepId: string; data: UpdateOnboardingStepData }) => 
      API.onboarding.updateStep(stepId, data),
    onMutate: async ({ id, stepId, data }: { id?: string; stepId: string; data: UpdateOnboardingStepData }) => {
      if (!id) return undefined;
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.onboardingDetail(id) });
      
      // Optimistically update the step
      updateOnboardingOptimistically(id, {
        steps: { [stepId]: { ...data, status: 'COMPLETED', completed_at: new Date().toISOString() } }
      });
      
      return { id };
    },
    onSuccess: (data, variables, context) => {
      const id = context?.id;
      if (!id) return undefined;
      // Update the specific onboarding request in cache with server response
      queryClient.setQueryData(
        queryKeys.onboardingDetail(id),
        data
      );
      
      invalidateQueries.onboarding();
      invalidateQueries.partners();
      invalidateQueries.analytics();
    },
    onError: (error, variables, context) => {
      const id = context?.id;
      if (!id) return undefined;
      // Revert optimistic update on error
      revertOptimisticUpdate(id);
    },
  });
}

export function useApproveOnboardingStep() {
  const queryClient = useQueryClient();
  const { updateOnboardingOptimistically, revertOptimisticUpdate } = useOptimisticOnboardingUpdate();

  return useMutation({
    mutationFn: ({ stepId }: { stepId: string }) => 
      API.onboarding.approveStep(stepId),
    onMutate: async ({ id, stepId }: { id?: string; stepId: string }) => {
      if (!id) return undefined;
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.onboardingDetail(id) });
      
      // Optimistically update the step approval
      updateOnboardingOptimistically(id, {
        steps: { [stepId]: { status: 'APPROVED', approved_at: new Date().toISOString() } }
      });
      
      return { id };
    },
    onSuccess: (data, variables, context) => {
      const id = context?.id;
      if (!id) return undefined;
      // Update the specific onboarding request in cache with server response
      queryClient.setQueryData(
        queryKeys.onboardingDetail(id),
        data
      );
      
      invalidateQueries.onboarding();
      invalidateQueries.partners();
      invalidateQueries.analytics();
    },
    onError: (error, variables, context) => {
      const id = context?.id;
      if (!id) return undefined;
      // Revert optimistic update on error
      revertOptimisticUpdate(id);
    },
  });
}

export function useRejectOnboardingStep() {
  const queryClient = useQueryClient();
  const { updateOnboardingOptimistically, revertOptimisticUpdate } = useOptimisticOnboardingUpdate();

  return useMutation({
    mutationFn: ({ stepId, reason }: { stepId: string; reason: string }) => 
      API.onboarding.rejectStep(stepId, reason),
    onMutate: async ({ id, stepId, reason }: { id?: string; stepId: string; reason: string }) => {
      if (!id) return undefined;
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.onboardingDetail(id) });
      
      // Optimistically update the step rejection
      updateOnboardingOptimistically(id, {
        steps: { 
          [stepId]: { 
            status: 'REJECTED', 
            rejected_at: new Date().toISOString(),
            rejection_reason: reason
          }
        }
      });
      
      return { id };
    },
    onSuccess: (data, variables, context) => {
      const id = context?.id;
      if (!id) return undefined;
      // Update the specific onboarding request in cache with server response
      queryClient.setQueryData(
        queryKeys.onboardingDetail(id),
        data
      );
      
      invalidateQueries.onboarding();
      invalidateQueries.partners();
      invalidateQueries.analytics();
    },
    onError: (error, variables, context) => {
      const id = context?.id;
      if (!id) return undefined;
      // Revert optimistic update on error
      revertOptimisticUpdate(id);
    },
  });
}

export function useCompleteOnboarding() {
  const queryClient = useQueryClient();
  const { updateOnboardingOptimistically, revertOptimisticUpdate } = useOptimisticOnboardingUpdate();

  return useMutation({
    mutationFn: (id: string) => API.onboarding.complete(id),
    onMutate: async (id) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.onboardingDetail(id) });
      
      // Optimistically update the onboarding completion
      updateOnboardingOptimistically(id, {
        status: 'COMPLETED',
        completed_at: new Date().toISOString()
      });
      
      return { id };
    },
    onSuccess: (data, id) => {
      // Update the specific onboarding request in cache with server response
      queryClient.setQueryData(
        queryKeys.onboardingDetail(id),
        data
      );
      
      invalidateQueries.onboarding();
      invalidateQueries.partners();
      invalidateQueries.analytics();
    },
    onError: (error, id) => {
      // Revert optimistic update on error
      revertOptimisticUpdate(id);
    },
  });
}

// Custom hook for onboarding statistics
export function useOnboardingStats() {
  return useQuery({
    queryKey: [...queryKeys.onboarding(), 'stats'],
    queryFn: async () => {
      const onboardingResponse = await API.onboarding.list();
      const requests = onboardingResponse.data as any[];
      
      return {
        total: requests.length,
        pending: requests.filter(r => r.status === 'PENDING').length,
        in_progress: requests.filter(r => r.status === 'IN_PROGRESS').length,
        completed: requests.filter(r => r.status === 'COMPLETED').length,
        rejected: requests.filter(r => r.status === 'REJECTED').length,
        avgCompletionTime: calculateAverageCompletionTime(requests),
        byPartnerType: requests.reduce((acc, request) => {
          acc[request.partner_type] = (acc[request.partner_type] || 0) + 1;
          return acc;
        }, {} as Record<string, number>),
      };
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Optimistic update helper for onboarding
export function useOptimisticOnboardingUpdate() {
  const queryClient = useQueryClient();

  const updateOnboardingOptimistically = (id: string, updates: OnboardingOptimisticUpdate) => {
    queryClient.setQueryData(
      queryKeys.onboardingDetail(id),
      (oldData: { data: OnboardingRequest } | undefined) => {
        if (!oldData?.data) return oldData;
        
        let updatedData = {
          ...oldData.data,
          ...updates,
          updated_at: new Date().toISOString(),
        };

        // Handle step updates
        if (updates.steps) {
          updatedData.steps = {
            ...oldData.data.steps,
            ...Object.keys(updates.steps).reduce((acc, stepId) => {
              acc[stepId] = {
                ...oldData.data.steps?.[stepId],
                ...updates.steps?.[stepId],
              } as OnboardingStep;
              return acc;
            }, {} as Record<string, OnboardingStep>),
          };
        }

        return {
          ...oldData,
          data: updatedData,
        };
      }
    );
  };

  const revertOptimisticUpdate = (id: string) => {
    queryClient.invalidateQueries({ queryKey: queryKeys.onboardingDetail(id) });
  };

  return { updateOnboardingOptimistically, revertOptimisticUpdate };
}

// Helper function to calculate average completion time
function calculateAverageCompletionTime(requests: OnboardingRequest[]): number {
  const completedRequests = requests.filter(r => r.status === 'COMPLETED' && r.created_at && r.completed_at);
  
  if (completedRequests.length === 0) return 0;
  
  const totalTime = completedRequests.reduce((sum, request) => {
    const created = new Date(request.created_at).getTime();
    const completed = new Date(request.completed_at).getTime();
    return sum + (completed - created);
  }, 0);
  
  // Return average time in days
  return Math.round((totalTime / completedRequests.length) / (1000 * 60 * 60 * 24));
}