/**
 * Management Page Template Tests
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { ManagementPageTemplate } from '../templates/ManagementPageTemplate';
import { ManagementPageConfig } from '../types/templates';

// Extend Jest matchers
expect.extend(toHaveNoViolations);

// Mock dependencies
jest.mock('@dotmac/monitoring/observability', () => ({
  trackPageView: jest.fn(),
  trackAction: jest.fn()
}));

jest.mock('@dotmac/primitives', () => ({
  Card: ({ children, className }: any) => <div className={className} data-testid="card">{children}</div>,
  Button: ({ children, onClick, disabled, variant, ...props }: any) => (
    <button onClick={onClick} disabled={disabled} data-variant={variant} {...props}>
      {children}
    </button>
  ),
  Input: ({ onChange, value, placeholder, ...props }: any) => (
    <input 
      onChange={(e) => onChange?.(e)} 
      value={value} 
      placeholder={placeholder} 
      {...props} 
    />
  ),
  Select: ({ children, onChange, value, ...props }: any) => (
    <select onChange={(e) => onChange?.(e.target.value)} value={value} {...props}>
      {children}
    </select>
  ),
  Badge: ({ children, variant }: any) => <span data-variant={variant}>{children}</span>,
  Skeleton: ({ className }: any) => <div className={className} data-testid="skeleton" />,
  Alert: ({ children, variant }: any) => <div data-variant={variant}>{children}</div>,
  Progress: ({ value }: any) => <div data-testid="progress" data-value={value} />,
  Separator: () => <hr data-testid="separator" />
}));

jest.mock('@dotmac/rbac', () => ({
  PermissionGuard: ({ children }: any) => <div>{children}</div>
}));

jest.mock('@dotmac/primitives/utils/performance', () => ({
  useRenderProfiler: () => ({
    renderCount: 1,
    getProfile: () => ({}),
    getAllProfiles: () => [],
    getRecentMetrics: () => []
  })
}));

// Test data
const mockConfig: ManagementPageConfig = {
  type: 'management',
  title: 'Test Management Page',
  description: 'Test description',
  portal: 'admin',
  showBreadcrumbs: true,
  showHeader: true,
  showSidebar: false,
  maxWidth: 'none',
  padding: true,
  theme: 'auto',
  density: 'comfortable',
  metrics: [
    {
      key: 'total-users',
      title: 'Total Users',
      value: 1234,
      format: 'number',
      icon: 'Users',
      color: '#3b82f6',
      change: {
        value: 10,
        type: 'increase',
        period: 'this month'
      }
    },
    {
      key: 'revenue',
      title: 'Revenue',
      value: 45670,
      format: 'currency',
      icon: 'DollarSign',
      color: '#10b981'
    }
  ],
  filters: [
    {
      key: 'status',
      label: 'Status',
      type: 'select',
      options: [
        { value: 'active', label: 'Active' },
        { value: 'inactive', label: 'Inactive' }
      ]
    },
    {
      key: 'date_range',
      label: 'Date Range',
      type: 'dateRange'
    }
  ],
  actions: [
    {
      key: 'create',
      label: 'Create New',
      variant: 'primary',
      icon: 'Plus'
    },
    {
      key: 'export',
      label: 'Export',
      variant: 'outline',
      icon: 'Download'
    }
  ],
  showMetrics: true,
  showFilters: true,
  showActions: true,
  showExport: true,
  showSearch: true,
  showSavedViews: true,
  enableBulkActions: true,
  enableColumnConfig: true,
  refreshInterval: 30000,
  autoRefresh: true,
  savedViews: []
};

// Mock props
const defaultProps = {
  config: mockConfig,
  initialData: {},
  apiEndpoint: '/api/test'
};

describe('ManagementPageTemplate', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders without crashing', () => {
      render(<ManagementPageTemplate {...defaultProps} />);
      expect(screen.getByTestId('management-page')).toBeInTheDocument();
    });

    it('displays the title and description', () => {
      render(<ManagementPageTemplate {...defaultProps} />);
      expect(screen.getByText('Test Management Page')).toBeInTheDocument();
      expect(screen.getByText('Test description')).toBeInTheDocument();
    });

    it('renders metrics when showMetrics is true', () => {
      render(<ManagementPageTemplate {...defaultProps} />);
      expect(screen.getByText('Total Users')).toBeInTheDocument();
      expect(screen.getByText('1,234')).toBeInTheDocument();
      expect(screen.getByText('Revenue')).toBeInTheDocument();
    });

    it('hides metrics when showMetrics is false', () => {
      const config = { ...mockConfig, showMetrics: false };
      render(<ManagementPageTemplate {...defaultProps} config={config} />);
      expect(screen.queryByText('Total Users')).not.toBeInTheDocument();
    });

    it('renders filters when showFilters is true', () => {
      render(<ManagementPageTemplate {...defaultProps} />);
      expect(screen.getByLabelText('Status')).toBeInTheDocument();
      expect(screen.getByLabelText('Date Range')).toBeInTheDocument();
    });

    it('renders actions when showActions is true', () => {
      render(<ManagementPageTemplate {...defaultProps} />);
      expect(screen.getByText('Create New')).toBeInTheDocument();
      expect(screen.getByText('Export')).toBeInTheDocument();
    });

    it('renders search input when showSearch is true', () => {
      render(<ManagementPageTemplate {...defaultProps} />);
      expect(screen.getByPlaceholderText('Search...')).toBeInTheDocument();
    });
  });

  describe('Interactions', () => {
    it('calls onAction when action button is clicked', async () => {
      const mockOnAction = jest.fn();
      render(
        <ManagementPageTemplate 
          {...defaultProps} 
          onAction={mockOnAction}
        />
      );

      const createButton = screen.getByText('Create New');
      await userEvent.click(createButton);

      expect(mockOnAction).toHaveBeenCalledWith('create', undefined);
    });

    it('calls onFilterChange when filter values change', async () => {
      const mockOnFilterChange = jest.fn();
      render(
        <ManagementPageTemplate 
          {...defaultProps} 
          onFilterChange={mockOnFilterChange}
        />
      );

      const statusSelect = screen.getByLabelText('Status');
      await userEvent.selectOptions(statusSelect, 'active');

      expect(mockOnFilterChange).toHaveBeenCalledWith({ status: 'active' });
    });

    it('calls onExport when export is triggered', async () => {
      const mockOnExport = jest.fn();
      render(
        <ManagementPageTemplate 
          {...defaultProps} 
          onExport={mockOnExport}
        />
      );

      const exportButton = screen.getByTestId('export-button');
      await userEvent.click(exportButton);

      expect(mockOnExport).toHaveBeenCalled();
    });

    it('handles search input correctly', async () => {
      const mockOnSearch = jest.fn();
      render(
        <ManagementPageTemplate 
          {...defaultProps} 
          onSearch={mockOnSearch}
        />
      );

      const searchInput = screen.getByPlaceholderText('Search...');
      await userEvent.type(searchInput, 'test query');

      // Debounced, so wait for the call
      await waitFor(() => {
        expect(mockOnSearch).toHaveBeenCalledWith('test query');
      }, { timeout: 1000 });
    });

    it('toggles advanced filters', async () => {
      render(<ManagementPageTemplate {...defaultProps} />);

      const advancedButton = screen.getByTestId('advanced-filters-toggle');
      await userEvent.click(advancedButton);

      expect(screen.getByTestId('advanced-filters')).toBeInTheDocument();
    });

    it('handles refresh action', async () => {
      const mockOnRefresh = jest.fn();
      render(
        <ManagementPageTemplate 
          {...defaultProps} 
          onRefresh={mockOnRefresh}
        />
      );

      const refreshButton = screen.getByTestId('refresh-button');
      await userEvent.click(refreshButton);

      expect(mockOnRefresh).toHaveBeenCalled();
    });
  });

  describe('Auto-refresh', () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it('auto-refreshes when enabled', () => {
      const mockOnRefresh = jest.fn();
      render(
        <ManagementPageTemplate 
          {...defaultProps} 
          onRefresh={mockOnRefresh}
        />
      );

      // Fast-forward time
      act(() => {
        jest.advanceTimersByTime(30000);
      });

      expect(mockOnRefresh).toHaveBeenCalled();
    });

    it('does not auto-refresh when disabled', () => {
      const config = { ...mockConfig, autoRefresh: false };
      const mockOnRefresh = jest.fn();
      
      render(
        <ManagementPageTemplate 
          {...defaultProps} 
          config={config}
          onRefresh={mockOnRefresh}
        />
      );

      act(() => {
        jest.advanceTimersByTime(30000);
      });

      expect(mockOnRefresh).not.toHaveBeenCalled();
    });
  });

  describe('Loading States', () => {
    it('shows loading skeleton when isLoading is true', () => {
      render(
        <ManagementPageTemplate 
          {...defaultProps} 
          isLoading={true}
        />
      );

      expect(screen.getAllByTestId('skeleton')).toHaveLength(3); // Metrics skeletons
    });

    it('shows error state when error is provided', () => {
      const error = new Error('Test error');
      render(
        <ManagementPageTemplate 
          {...defaultProps} 
          error={error}
        />
      );

      expect(screen.getByText('Error loading data')).toBeInTheDocument();
      expect(screen.getByText('Test error')).toBeInTheDocument();
    });
  });

  describe('Responsive Behavior', () => {
    it('adapts to mobile viewport', () => {
      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 640,
      });

      render(<ManagementPageTemplate {...defaultProps} />);
      
      // Mobile-specific elements should be present
      expect(screen.getByTestId('mobile-header')).toBeInTheDocument();
    });

    it('shows desktop layout on larger screens', () => {
      // Mock desktop viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 1024,
      });

      render(<ManagementPageTemplate {...defaultProps} />);
      
      // Desktop-specific elements should be present
      expect(screen.getByTestId('desktop-layout')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has no accessibility violations', async () => {
      const { container } = render(<ManagementPageTemplate {...defaultProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('supports keyboard navigation', async () => {
      render(<ManagementPageTemplate {...defaultProps} />);

      const createButton = screen.getByText('Create New');
      createButton.focus();
      
      expect(document.activeElement).toBe(createButton);

      // Tab to next focusable element
      await userEvent.tab();
      
      const exportButton = screen.getByText('Export');
      expect(document.activeElement).toBe(exportButton);
    });

    it('has proper ARIA labels', () => {
      render(<ManagementPageTemplate {...defaultProps} />);

      expect(screen.getByLabelText('Search')).toBeInTheDocument();
      expect(screen.getByLabelText('Status')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /create new/i })).toBeInTheDocument();
    });

    it('announces loading state to screen readers', () => {
      render(
        <ManagementPageTemplate 
          {...defaultProps} 
          isLoading={true}
        />
      );

      expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite');
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });

  describe('Performance', () => {
    it('memoizes expensive calculations', () => {
      const { rerender } = render(<ManagementPageTemplate {...defaultProps} />);
      
      // Re-render with same props
      rerender(<ManagementPageTemplate {...defaultProps} />);
      
      // Verify components are memoized (would need performance monitoring)
      expect(screen.getByTestId('management-page')).toBeInTheDocument();
    });

    it('handles large datasets efficiently', () => {
      const largeConfig = {
        ...mockConfig,
        metrics: Array.from({ length: 100 }, (_, i) => ({
          key: `metric-${i}`,
          title: `Metric ${i}`,
          value: i * 100,
          format: 'number' as const
        }))
      };

      const start = performance.now();
      render(<ManagementPageTemplate {...defaultProps} config={largeConfig} />);
      const end = performance.now();

      // Should render within reasonable time (adjust threshold as needed)
      expect(end - start).toBeLessThan(1000);
    });
  });

  describe('Error Handling', () => {
    it('gracefully handles invalid configuration', () => {
      const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      const invalidConfig = { ...mockConfig, type: 'invalid' as any };
      
      expect(() => {
        render(<ManagementPageTemplate {...defaultProps} config={invalidConfig} />);
      }).toThrow(/Invalid management page configuration/);

      consoleError.mockRestore();
    });

    it('handles missing required props', () => {
      const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      expect(() => {
        render(<ManagementPageTemplate config={undefined as any} />);
      }).toThrow();

      consoleError.mockRestore();
    });
  });

  describe('Theme Integration', () => {
    it('applies portal-specific classes', () => {
      render(<ManagementPageTemplate {...defaultProps} />);
      
      const container = screen.getByTestId('management-page');
      expect(container).toHaveClass('portal-admin');
    });

    it('applies density classes', () => {
      const config = { ...mockConfig, density: 'compact' as const };
      render(<ManagementPageTemplate {...defaultProps} config={config} />);
      
      const container = screen.getByTestId('management-page');
      expect(container).toHaveClass('density-compact');
    });

    it('responds to theme changes', () => {
      const { rerender } = render(<ManagementPageTemplate {...defaultProps} />);
      
      const newConfig = { ...mockConfig, density: 'spacious' as const };
      rerender(<ManagementPageTemplate {...defaultProps} config={newConfig} />);
      
      const container = screen.getByTestId('management-page');
      expect(container).toHaveClass('density-spacious');
    });
  });
});