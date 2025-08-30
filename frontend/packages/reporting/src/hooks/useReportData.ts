/**
 * Report Data Hook
 * Leverages @dotmac/headless data fetching patterns
 */

import { useState, useEffect, useCallback } from 'react';
import { useApiData } from '@dotmac/headless';
import type { DataSourceConfig } from '../types';

interface UseReportDataReturn {
  data: any[] | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
  executionTime: number;
}

export const useReportData = (dataSource: DataSourceConfig): UseReportDataReturn => {
  const [executionTime, setExecutionTime] = useState(0);
  const [localError, setLocalError] = useState<string | null>(null);

  // Leverage existing @dotmac/headless useApiData hook
  const {
    data: rawData,
    isLoading,
    error: apiError,
    refetch
  } = useApiData(
    `report-data-${dataSource.endpoint || 'static'}`,
    async () => {
      if (dataSource.type === 'static') {
        return dataSource.parameters?.data || [];
      }

      if (dataSource.type === 'api' && dataSource.endpoint) {
        const response = await fetch(dataSource.endpoint);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      }

      return [];
    },
    {
      enabled: dataSource.type === 'api' && !!dataSource.endpoint,
      ttl: dataSource.caching ? 300000 : 0, // 5 minutes if caching enabled
      retryCount: 3,
      retryDelay: 1000
    }
  );

  // Process data based on data source configuration
  const processedData = useState(() => {
    if (!rawData) return null;

    const startTime = performance.now();

    let result = Array.isArray(rawData) ? rawData : [rawData];

    // Apply data transformation if configured
    if (dataSource.transform && typeof dataSource.transform === 'function') {
      try {
        result = dataSource.transform(result);
      } catch (transformError) {
        console.error('Data transformation failed:', transformError);
        setLocalError('Data transformation failed');
        return null;
      }
    }

    // Handle different data source types
    switch (dataSource.type) {
      case 'static':
        // For static data, use the configured data directly
        result = dataSource.parameters?.data || [];
        break;

      case 'query':
        // For query-based data sources, apply client-side filtering
        if (dataSource.query && result.length > 0) {
          try {
            // Simple query processor (extend as needed)
            const queryFilters = parseSimpleQuery(dataSource.query);
            result = result.filter(item =>
              queryFilters.every(filter =>
                applyQueryFilter(item, filter)
              )
            );
          } catch (queryError) {
            console.error('Query processing failed:', queryError);
            setLocalError('Query processing failed');
            return null;
          }
        }
        break;

      case 'realtime':
        // For real-time data, ensure fresh data (handled by refetchInterval)
        break;

      default:
        // API data is already processed
        break;
    }

    const endTime = performance.now();
    setExecutionTime(endTime - startTime);

    return result;
  })[0];

  // Refresh function that leverages existing refetch
  const refresh = useCallback(async () => {
    setLocalError(null);
    if (dataSource.type === 'api') {
      await refetch();
    } else {
      // For non-API sources, trigger a re-render
      window.location.reload();
    }
  }, [dataSource.type, refetch]);

  // Handle real-time data updates
  useEffect(() => {
    if (dataSource.type === 'realtime' && dataSource.refreshInterval) {
      const interval = setInterval(() => {
        refresh();
      }, dataSource.refreshInterval);

      return () => clearInterval(interval);
    }

    return undefined;
  }, [dataSource.type, dataSource.refreshInterval, refresh]);

  return {
    data: processedData,
    loading: isLoading,
    error: localError || (apiError?.message || null),
    refresh,
    executionTime
  };
};

// Helper functions for query processing
const parseSimpleQuery = (query: string) => {
  // Simple query parser - extend as needed
  // Supports: field=value, field>value, field<value, field LIKE '%value%'
  const filters = [];
  const parts = query.split(' AND ');

  for (const part of parts) {
    const trimmed = part.trim();

    if (trimmed.includes('>=')) {
      const [field, value] = trimmed.split('>=').map(s => s.trim());
      if (field && value) {
        filters.push({ field, operator: 'gte', value: parseValue(value) });
      }
    } else if (trimmed.includes('<=')) {
      const [field, value] = trimmed.split('<=').map(s => s.trim());
      if (field && value) {
        filters.push({ field, operator: 'lte', value: parseValue(value) });
      }
    } else if (trimmed.includes('>')) {
      const [field, value] = trimmed.split('>').map(s => s.trim());
      if (field && value) {
        filters.push({ field, operator: 'gt', value: parseValue(value) });
      }
    } else if (trimmed.includes('<')) {
      const [field, value] = trimmed.split('<').map(s => s.trim());
      if (field && value) {
        filters.push({ field, operator: 'lt', value: parseValue(value) });
      }
    } else if (trimmed.includes('=')) {
      const [field, value] = trimmed.split('=').map(s => s.trim());
      if (field && value) {
        filters.push({ field, operator: 'eq', value: parseValue(value) });
      }
    } else if (trimmed.toUpperCase().includes(' LIKE ')) {
      const [field, value] = trimmed.split(/\s+LIKE\s+/i).map(s => s.trim());
      if (field && value) {
        const cleanValue = value.replace(/['"]/g, '').replace(/%/g, '');
        filters.push({ field, operator: 'contains', value: cleanValue });
      }
    }
  }

  return filters;
};

const parseValue = (value: string) => {
  // Remove quotes
  const cleaned = value.replace(/['"]/g, '');

  // Try to parse as number
  const num = Number(cleaned);
  if (!isNaN(num)) return num;

  // Try to parse as boolean
  if (cleaned.toLowerCase() === 'true') return true;
  if (cleaned.toLowerCase() === 'false') return false;

  // Try to parse as date
  const date = new Date(cleaned);
  if (!isNaN(date.getTime())) return date;

  // Return as string
  return cleaned;
};

const applyQueryFilter = (item: any, filter: any): boolean => {
  const fieldValue = item[filter.field];

  switch (filter.operator) {
    case 'eq':
      return fieldValue === filter.value;
    case 'ne':
      return fieldValue !== filter.value;
    case 'gt':
      return fieldValue > filter.value;
    case 'gte':
      return fieldValue >= filter.value;
    case 'lt':
      return fieldValue < filter.value;
    case 'lte':
      return fieldValue <= filter.value;
    case 'contains':
      return String(fieldValue).toLowerCase().includes(String(filter.value).toLowerCase());
    default:
      return true;
  }
};
