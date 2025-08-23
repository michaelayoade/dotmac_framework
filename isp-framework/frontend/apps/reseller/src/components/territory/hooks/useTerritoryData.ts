/**
 * Territory Data Management Hook
 * Handles territory data loading and state management
 */

import { useState, useEffect, useCallback, useMemo } from 'react';

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
}

// Mock data - in real app, this would come from API
const mockTerritories: Territory[] = [
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
    opportunities: { newDevelopments: 12, businessParks: 3, competitorWeakness: 8 },
  },
  // Add more mock territories as needed
];

export function useTerritoryData(): UseTerritoryDataReturn {
  const [territories, setTerritories] = useState<Territory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<TerritoryFilters>({
    searchTerm: '',
    sortBy: 'revenue',
  });

  const loadTerritories = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));
      setTerritories(mockTerritories);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load territories');
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
  };
}
