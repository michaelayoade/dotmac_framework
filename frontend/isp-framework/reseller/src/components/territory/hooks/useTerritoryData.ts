/**
 * Territory Data Management Hook
 * Handles territory data loading and state management
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { mockApiWrapper, MockDataIndicator } from '@dotmac/headless/utils/production-data-guard';

export interface Territory {
  id: string;
  name: string;
  region: string;
  coordinates: [number, number];
  radius: number;
  population: number;
  households: number;
  averageIncome: number;
  competition: 'low' | 'medium' | 'high';
  marketPenetration: number;
  totalCustomers: number;
  activeProspects: number;
  monthlyRevenue: number;
  growthRate: number;
  serviceability: number;
  lastUpdated: string;
  demographics: {
    residential: number;
    business: number;
    enterprise: number;
  };
  services: {
    fiber: number;
    cable: number;
    dsl: number;
  };
  opportunities: {
    newDevelopments: number;
    businessParks: number;
    competitorWeakness: number;
  };
}

export interface TerritoryFilters {
  searchTerm: string;
  sortBy: 'name' | 'revenue' | 'growth' | 'penetration';
  region?: string;
  competitionLevel?: 'low' | 'medium' | 'high';
}

export interface UseTerritoryDataReturn {
  territories: Territory[];
  filteredTerritories: Territory[];
  isLoading: boolean;
  error: string | null;
  filters: TerritoryFilters;
  updateFilters: (updates: Partial<TerritoryFilters>) => void;
  refreshData: () => Promise<void>;
  isUsingMockData: boolean;
}

// Development-only mock data - automatically removed from production builds
const createMockTerritories = (): Territory[] => [
  {
    id: 'territory_1',
    name: 'Downtown Core',
    region: 'Central',
    coordinates: [40.7128, -74.006],
    radius: 5.2,
    population: 125000,
    households: 48000,
    averageIncome: 75000,
    competition: 'high',
    marketPenetration: 34.5,
    totalCustomers: 16560,
    activeProspects: 2890,
    monthlyRevenue: 892400,
    growthRate: 12.3,
    serviceability: 95,
    lastUpdated: '2024-01-15T10:30:00Z',
    demographics: { residential: 70, business: 25, enterprise: 5 },
    services: { fiber: 60, cable: 35, dsl: 5 },
    opportunities: {
      newDevelopments: 12,
      businessParks: 3,
      competitorWeakness: 8,
    },
  },
  {
    id: 'territory_2',
    name: 'Suburban West',
    region: 'West',
    coordinates: [40.7589, -74.0851],
    radius: 8.1,
    population: 95000,
    households: 35000,
    averageIncome: 85000,
    competition: 'medium',
    marketPenetration: 45.2,
    totalCustomers: 15820,
    activeProspects: 1250,
    monthlyRevenue: 1125600,
    growthRate: 18.7,
    serviceability: 88,
    lastUpdated: '2024-01-15T11:15:00Z',
    demographics: { residential: 85, business: 12, enterprise: 3 },
    services: { fiber: 75, cable: 20, dsl: 5 },
    opportunities: {
      newDevelopments: 8,
      businessParks: 2,
      competitorWeakness: 15,
    },
  },
];

// Real API call for production
const fetchTerritoryDataFromAPI = async (): Promise<Territory[]> => {
  // TODO: Replace with actual API endpoint
  const response = await fetch('/api/v1/territories', {
    headers: {
      Authorization: `Bearer ${localStorage.getItem('auth-token')}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch territories: ${response.statusText}`);
  }

  const data = await response.json();
  return data.territories || [];
};

// Create mock-aware API wrapper - only use mocks for tests
const fetchTerritories = mockApiWrapper(fetchTerritoryDataFromAPI, createMockTerritories, {
  delay: 1000,
  enableInDevelopment: false, // Real API in development
  enableInTest: true, // Mocks only for tests
  warningMessage: 'Territory data - using mock data for testing',
  fallbackToEmpty: true,
});

export function useTerritoryData(): UseTerritoryDataReturn {
  const [territories, setTerritories] = useState<Territory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUsingMockData, setIsUsingMockData] = useState(false);
  const [filters, setFilters] = useState<TerritoryFilters>({
    searchTerm: '',
    sortBy: 'revenue',
  });

  const loadTerritories = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await fetchTerritories();
      setTerritories(data);
      setIsUsingMockData(process.env.NODE_ENV === 'development');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load territories');
      setTerritories([]); // Clear territories on error
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateFilters = useCallback((updates: Partial<TerritoryFilters>) => {
    setFilters((prev) => ({ ...prev, ...updates }));
  }, []);

  const filteredTerritories = useMemo(() => {
    let filtered = [...territories];

    // Apply search filter
    if (filters.searchTerm) {
      const searchLower = filters.searchTerm.toLowerCase();
      filtered = filtered.filter(
        (territory) =>
          territory.name.toLowerCase().includes(searchLower) ||
          territory.region.toLowerCase().includes(searchLower)
      );
    }

    // Apply region filter
    if (filters.region) {
      filtered = filtered.filter((territory) => territory.region === filters.region);
    }

    // Apply competition filter
    if (filters.competitionLevel) {
      filtered = filtered.filter((territory) => territory.competition === filters.competitionLevel);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      switch (filters.sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'revenue':
          return b.monthlyRevenue - a.monthlyRevenue;
        case 'growth':
          return b.growthRate - a.growthRate;
        case 'penetration':
          return b.marketPenetration - a.marketPenetration;
        default:
          return 0;
      }
    });

    return filtered;
  }, [territories, filters]);

  const refreshData = useCallback(async () => {
    await loadTerritories();
  }, [loadTerritories]);

  // Initial load
  useEffect(() => {
    loadTerritories();
  }, [loadTerritories]);

  return {
    territories,
    filteredTerritories,
    isLoading,
    error,
    filters,
    updateFilters,
    refreshData,
    isUsingMockData,
  };
}
