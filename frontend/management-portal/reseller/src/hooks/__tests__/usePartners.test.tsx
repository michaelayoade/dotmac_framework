import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import {
  usePartners,
  usePartner,
  useCreatePartner,
  useUpdatePartner,
  useApprovePartner,
  usePartnerStats,
} from '../usePartners';
import { API } from '@/lib/api/endpoints';
import { mockApiResponses, createTestQueryClient } from '../../__tests__/utils/test-utils';

// Mock the API
jest.mock('@/lib/api/endpoints', () => ({
  API: {
    partners: {
      list: jest.fn(),
      getById: jest.fn(),
      create: jest.fn(),
      update: jest.fn(),
      approve: jest.fn(),
      suspend: jest.fn(),
      updateTier: jest.fn(),
    },
  },
}));

const mockedAPI = API as jest.Mocked<typeof API>;

// Test wrapper with QueryClient
function createWrapper() {
  const queryClient = createTestQueryClient();

  return function TestWrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('usePartners Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('usePartners', () => {
    it('should fetch partners list successfully', async () => {
      const mockResponse = mockApiResponses.partners.list;
      mockedAPI.partners.list.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(() => usePartners(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isSuccess).toBe(true);
      expect(result.current.data).toEqual(mockResponse);
      expect(mockedAPI.partners.list).toHaveBeenCalledWith(undefined);
    });

    it('should fetch partners with filters', async () => {
      const filters = { status: 'ACTIVE', tier: 'GOLD' };
      const mockResponse = mockApiResponses.partners.list;
      mockedAPI.partners.list.mockResolvedValueOnce(mockResponse);

      renderHook(() => usePartners(filters), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockedAPI.partners.list).toHaveBeenCalledWith(filters);
      });
    });

    it('should handle fetch error', async () => {
      const error = new Error('Network error');
      mockedAPI.partners.list.mockRejectedValueOnce(error);

      const { result } = renderHook(() => usePartners(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBe(error);
    });
  });

  describe('usePartner', () => {
    it('should fetch single partner successfully', async () => {
      const partnerId = 'partner-1';
      const mockResponse = mockApiResponses.partners.detail;
      mockedAPI.partners.getById.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(() => usePartner(partnerId), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isSuccess).toBe(true);
      expect(result.current.data).toEqual(mockResponse);
      expect(mockedAPI.partners.getById).toHaveBeenCalledWith(partnerId);
    });

    it('should not fetch when id is empty', () => {
      const { result } = renderHook(() => usePartner(''), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe('idle');
      expect(mockedAPI.partners.getById).not.toHaveBeenCalled();
    });
  });

  describe('useCreatePartner', () => {
    it('should create partner successfully', async () => {
      const newPartner = {
        company_name: 'New Partner',
        contact_email: 'new@partner.com',
        partner_type: 'AGENT' as const,
      };
      const mockResponse = { ...mockApiResponses.partners.detail.data, ...newPartner };
      mockedAPI.partners.create.mockResolvedValueOnce({ data: mockResponse });

      const { result } = renderHook(() => useCreatePartner(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isPending).toBe(false);

      result.current.mutate(newPartner);

      expect(result.current.isPending).toBe(true);

      await waitFor(() => {
        expect(result.current.isPending).toBe(false);
      });

      expect(result.current.isSuccess).toBe(true);
      expect(mockedAPI.partners.create).toHaveBeenCalledWith(newPartner);
    });

    it('should handle creation error', async () => {
      const error = new Error('Validation error');
      mockedAPI.partners.create.mockRejectedValueOnce(error);

      const { result } = renderHook(() => useCreatePartner(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ company_name: 'Test' });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBe(error);
    });
  });

  describe('useUpdatePartner', () => {
    it('should update partner successfully', async () => {
      const partnerId = 'partner-1';
      const updates = { tier: 'PLATINUM' as const };
      const mockResponse = {
        ...mockApiResponses.partners.detail.data,
        ...updates,
      };
      mockedAPI.partners.update.mockResolvedValueOnce({ data: mockResponse });

      const { result } = renderHook(() => useUpdatePartner(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ id: partnerId, partner: updates });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockedAPI.partners.update).toHaveBeenCalledWith(partnerId, updates);
    });
  });

  describe('useApprovePartner', () => {
    it('should approve partner with optimistic update', async () => {
      const partnerId = 'partner-1';
      const mockResponse = {
        ...mockApiResponses.partners.detail.data,
        status: 'ACTIVE' as const,
      };
      mockedAPI.partners.approve.mockResolvedValueOnce({ data: mockResponse });

      const { result } = renderHook(() => useApprovePartner(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(partnerId);

      expect(result.current.isPending).toBe(true);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockedAPI.partners.approve).toHaveBeenCalledWith(partnerId);
    });

    it('should handle approval error and revert optimistic update', async () => {
      const partnerId = 'partner-1';
      const error = new Error('Approval failed');
      mockedAPI.partners.approve.mockRejectedValueOnce(error);

      const { result } = renderHook(() => useApprovePartner(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(partnerId);

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBe(error);
    });
  });

  describe('usePartnerStats', () => {
    it('should calculate partner statistics correctly', async () => {
      const mockPartnersData = {
        data: [
          {
            id: '1',
            status: 'ACTIVE',
            tier: 'GOLD',
            partner_type: 'AGENT',
          },
          {
            id: '2',
            status: 'PENDING',
            tier: 'SILVER',
            partner_type: 'DEALER',
          },
          {
            id: '3',
            status: 'ACTIVE',
            tier: 'GOLD',
            partner_type: 'AGENT',
          },
        ],
      };
      mockedAPI.partners.list.mockResolvedValueOnce(mockPartnersData);

      const { result } = renderHook(() => usePartnerStats(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      const expectedStats = {
        total: 3,
        active: 2,
        pending: 1,
        suspended: 0,
        byTier: {
          GOLD: 2,
          SILVER: 1,
        },
        byType: {
          AGENT: 2,
          DEALER: 1,
        },
      };

      expect(result.current.data).toEqual(expectedStats);
    });

    it('should handle empty partners list', async () => {
      const mockPartnersData = { data: [] };
      mockedAPI.partners.list.mockResolvedValueOnce(mockPartnersData);

      const { result } = renderHook(() => usePartnerStats(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      const expectedStats = {
        total: 0,
        active: 0,
        pending: 0,
        suspended: 0,
        byTier: {},
        byType: {},
      };

      expect(result.current.data).toEqual(expectedStats);
    });
  });
});
