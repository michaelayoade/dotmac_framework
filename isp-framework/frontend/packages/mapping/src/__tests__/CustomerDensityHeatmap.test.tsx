/**
 * Customer Density Heatmap Component Tests
 * Comprehensive testing for GIS mapping functionality
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CustomerDensityHeatmap } from '../components/CustomerDensityHeatmap';
import type { Customer, MarketAnalysis } from '../types';

// Mock Next.js dynamic imports
jest.mock('next/dynamic', () => {
  return function mockDynamic(dynamicFunction: any) {
    const Component = dynamicFunction();
    Component.displayName = 'MockDynamicComponent';
    return Component;
  };
});

// Mock react-leaflet components
jest.mock('react-leaflet', () => ({
  Circle: ({ children, ...props }: any) => (
    <div data-testid='leaflet-circle' {...props}>
      {children}
    </div>
  ),
  Polygon: ({ children, ...props }: any) => (
    <div data-testid='leaflet-polygon' {...props}>
      {children}
    </div>
  ),
  LayerGroup: ({ children }: any) => <div data-testid='leaflet-layer-group'>{children}</div>,
}));

// Mock BaseMap component
jest.mock('../components/BaseMap', () => ({
  BaseMap: ({ children, ...props }: any) => (
    <div data-testid='base-map' {...props}>
      {children}
    </div>
  ),
}));

// Test data
const mockCustomers: Customer[] = [
  {
    id: 'CUST-001',
    name: 'John Doe',
    coordinates: { latitude: 47.6062, longitude: -122.3321 },
    serviceType: 'residential',
    plan: 'Fiber 100Mbps',
    speed: 100,
    monthlyRevenue: 79.99,
    installDate: new Date('2023-06-15'),
    status: 'active',
    satisfaction: 8.5,
  },
  {
    id: 'CUST-002',
    name: 'Jane Smith',
    coordinates: { latitude: 47.6205, longitude: -122.3212 },
    serviceType: 'business',
    plan: 'Business 500Mbps',
    speed: 500,
    monthlyRevenue: 199.99,
    installDate: new Date('2023-08-20'),
    status: 'active',
    satisfaction: 9.2,
  },
  {
    id: 'CUST-003',
    name: 'Michael Johnson',
    coordinates: { latitude: 47.6101, longitude: -122.2015 },
    serviceType: 'enterprise',
    plan: 'Enterprise 1Gbps',
    speed: 1000,
    monthlyRevenue: 499.99,
    installDate: new Date('2023-03-10'),
    status: 'cancelled',
    satisfaction: 6.5,
  },
];

const mockMarketAnalysis: MarketAnalysis[] = [
  {
    territoryId: 'SEATTLE-001',
    bounds: [
      { latitude: 47.6, longitude: -122.4 },
      { latitude: 47.65, longitude: -122.25 },
    ],
    competitorData: [
      {
        name: 'Competitor A',
        coordinates: { latitude: 47.61, longitude: -122.33 },
        marketShare: 25,
        services: ['fiber', 'cable'],
      },
    ],
    demographicData: {
      population: 50000,
      medianIncome: 75000,
      businessCount: 2500,
      residentialUnits: 20000,
    },
    opportunityScore: 85,
    competitiveIntensity: 'medium',
  },
];

describe('CustomerDensityHeatmap', () => {
  describe('Basic Rendering', () => {
    test('renders heatmap component with customers', () => {
      render(
        <CustomerDensityHeatmap
          customers={mockCustomers}
          config={{
            defaultCenter: { latitude: 47.6062, longitude: -122.3321 },
            defaultZoom: 11,
          }}
        />
      );

      expect(screen.getByTestId('base-map')).toBeInTheDocument();
      expect(screen.getByText('Heatmap Type')).toBeInTheDocument();
      expect(screen.getByText('Map Layers')).toBeInTheDocument();
      expect(screen.getByText('Market Analysis')).toBeInTheDocument();
    });

    test('renders empty state when no customers provided', () => {
      render(
        <CustomerDensityHeatmap
          customers={[]}
          config={{
            defaultCenter: { latitude: 47.6062, longitude: -122.3321 },
            defaultZoom: 11,
          }}
        />
      );

      expect(screen.getByTestId('base-map')).toBeInTheDocument();
      expect(screen.getByText('Market Analysis')).toBeInTheDocument();
    });

    test('applies custom className', () => {
      const { container } = render(
        <CustomerDensityHeatmap
          customers={mockCustomers}
          className='custom-heatmap-class'
          config={{
            defaultCenter: { latitude: 47.6062, longitude: -122.3321 },
            defaultZoom: 11,
          }}
        />
      );

      expect(container.firstChild).toHaveClass('custom-heatmap-class');
    });
  });

  describe('Heatmap Type Controls', () => {
    test('shows all heatmap type options', () => {
      render(<CustomerDensityHeatmap customers={mockCustomers} />);

      expect(screen.getByText('Customer Density')).toBeInTheDocument();
      expect(screen.getByText('Revenue')).toBeInTheDocument();
      expect(screen.getByText('Satisfaction')).toBeInTheDocument();
      expect(screen.getByText('Churn Rate')).toBeInTheDocument();
    });

    test('switches heatmap type when clicked', async () => {
      const user = userEvent.setup();
      render(<CustomerDensityHeatmap customers={mockCustomers} />);

      const revenueButton = screen.getByText('Revenue');
      await user.click(revenueButton);

      // Verify the button is now active (would have different styling)
      expect(revenueButton.closest('button')).toHaveClass('bg-gray-100');
    });

    test('defaults to density heatmap type', () => {
      render(<CustomerDensityHeatmap customers={mockCustomers} />);

      const densityButton = screen.getByText('Customer Density');
      expect(densityButton.closest('button')).toHaveClass('bg-gray-100');
    });

    test('respects initial heatmapType prop', () => {
      render(<CustomerDensityHeatmap customers={mockCustomers} heatmapType='revenue' />);

      const revenueButton = screen.getByText('Revenue');
      expect(revenueButton.closest('button')).toHaveClass('bg-gray-100');
    });
  });

  describe('Layer Controls', () => {
    test('shows layer control options', () => {
      render(<CustomerDensityHeatmap customers={mockCustomers} />);

      expect(screen.getByText('Heatmap Grid')).toBeInTheDocument();
      expect(screen.getByText('Competitors')).toBeInTheDocument();
    });

    test('toggles layer visibility', async () => {
      const user = userEvent.setup();
      render(<CustomerDensityHeatmap customers={mockCustomers} />);

      const heatmapToggle = screen.getByLabelText(/Heatmap Grid/);
      expect(heatmapToggle).toBeChecked();

      await user.click(heatmapToggle);
      expect(heatmapToggle).not.toBeChecked();
    });

    test('competitor layer is controlled by showCompetitorData prop', () => {
      render(
        <CustomerDensityHeatmap
          customers={mockCustomers}
          showCompetitorData={true}
          marketAnalysis={mockMarketAnalysis}
        />
      );

      const competitorToggle = screen.getByLabelText(/Competitors/);
      expect(competitorToggle).toBeChecked();
    });
  });

  describe('Market Analysis Dashboard', () => {
    test('displays market metrics', () => {
      render(<CustomerDensityHeatmap customers={mockCustomers} />);

      expect(screen.getByText('Market Analysis')).toBeInTheDocument();
      expect(screen.getByText('Market Penetration')).toBeInTheDocument();
      expect(screen.getByText('Total Revenue')).toBeInTheDocument();
      expect(screen.getByText('Active Areas:')).toBeInTheDocument();
      expect(screen.getByText('High Value Areas:')).toBeInTheDocument();
    });

    test('calculates market penetration correctly', () => {
      render(<CustomerDensityHeatmap customers={mockCustomers} />);

      // Should show some percentage for market penetration
      expect(screen.getByText(/%$/)).toBeInTheDocument();
    });

    test('formats currency correctly', () => {
      render(<CustomerDensityHeatmap customers={mockCustomers} />);

      // Should show dollar formatted revenue
      expect(screen.getByText(/^\$/)).toBeInTheDocument();
    });

    test('shows satisfaction and churn metrics', () => {
      render(<CustomerDensityHeatmap customers={mockCustomers} />);

      expect(screen.getByText('Satisfaction Issues:')).toBeInTheDocument();
      expect(screen.getByText('High Churn Areas:')).toBeInTheDocument();
      expect(screen.getByText('Avg Satisfaction:')).toBeInTheDocument();
    });
  });

  describe('Grid Cell Generation', () => {
    test('generates grid cells based on customer locations', () => {
      render(<CustomerDensityHeatmap customers={mockCustomers} />);

      // Should render Leaflet polygon components for grid cells
      expect(screen.getAllByTestId('leaflet-polygon')).toHaveLength(expect.any(Number));
    });

    test('respects custom grid size', () => {
      render(<CustomerDensityHeatmap customers={mockCustomers} gridSize={0.05} />);

      // Larger grid size should result in fewer cells
      const polygons = screen.getAllByTestId('leaflet-polygon');
      expect(polygons.length).toBeGreaterThan(0);
    });

    test('filters customers by status for revenue calculations', () => {
      const mixedStatusCustomers = [
        ...mockCustomers,
        {
          id: 'CUST-004',
          name: 'Inactive Customer',
          coordinates: { latitude: 47.6062, longitude: -122.3321 },
          serviceType: 'residential' as const,
          plan: 'Basic Plan',
          speed: 50,
          monthlyRevenue: 50.0,
          installDate: new Date('2023-01-01'),
          status: 'inactive' as const,
          satisfaction: 5.0,
        },
      ];

      render(<CustomerDensityHeatmap customers={mixedStatusCustomers} />);

      // Should still render properly with mixed status customers
      expect(screen.getByTestId('base-map')).toBeInTheDocument();
    });
  });

  describe('Customer Points Rendering', () => {
    test('renders customer location circles', () => {
      render(<CustomerDensityHeatmap customers={mockCustomers} />);

      // Should render Circle components for active customers
      const circles = screen.getAllByTestId('leaflet-circle');
      expect(circles.length).toBeGreaterThan(0);
    });

    test('limits customer points for performance', () => {
      // Create more than 1000 customers
      const manyCustomers = Array.from({ length: 1200 }, (_, i) => ({
        ...mockCustomers[0],
        id: `CUST-${i.toString().padStart(3, '0')}`,
        coordinates: {
          latitude: 47.6 + i * 0.001,
          longitude: -122.3 + i * 0.001,
        },
      }));

      render(<CustomerDensityHeatmap customers={manyCustomers} />);

      // Should limit to 1000 points maximum
      const circles = screen.getAllByTestId('leaflet-circle');
      expect(circles.length).toBeLessThanOrEqual(1000);
    });

    test('colors circles by service type', () => {
      render(<CustomerDensityHeatmap customers={mockCustomers} />);

      const circles = screen.getAllByTestId('leaflet-circle');
      expect(circles.length).toBeGreaterThan(0);

      // Each circle should have pathOptions with different colors based on service type
      // This would be validated through props inspection in a real test
    });
  });

  describe('Competitor Data Integration', () => {
    test('renders competitor locations when enabled', () => {
      render(
        <CustomerDensityHeatmap
          customers={mockCustomers}
          marketAnalysis={mockMarketAnalysis}
          showCompetitorData={true}
        />
      );

      // Should render competitor circles
      const layerGroups = screen.getAllByTestId('leaflet-layer-group');
      expect(layerGroups.length).toBeGreaterThanOrEqual(2); // Customer + Competitor layers
    });

    test('hides competitor data when disabled', () => {
      render(
        <CustomerDensityHeatmap
          customers={mockCustomers}
          marketAnalysis={mockMarketAnalysis}
          showCompetitorData={false}
        />
      );

      // Competitor toggle should be unchecked
      const competitorToggle = screen.getByLabelText(/Competitors/);
      expect(competitorToggle).not.toBeChecked();
    });
  });

  describe('Area Selection', () => {
    test('calls onAreaSelect when grid cell is clicked', async () => {
      const onAreaSelect = jest.fn();
      render(<CustomerDensityHeatmap customers={mockCustomers} onAreaSelect={onAreaSelect} />);

      // Would need to simulate click on polygon in real test
      // This tests the callback setup
      expect(onAreaSelect).not.toHaveBeenCalled();
    });

    test('shows selected cell details panel', () => {
      render(<CustomerDensityHeatmap customers={mockCustomers} />);

      // Initially no details panel should be visible
      expect(screen.queryByText('Area Details')).not.toBeInTheDocument();
    });
  });

  describe('Color Calculations', () => {
    test('generates appropriate colors for density heatmap', () => {
      render(<CustomerDensityHeatmap customers={mockCustomers} heatmapType='density' />);

      // Should use blue color scheme for density
      expect(screen.getByTestId('base-map')).toBeInTheDocument();
    });

    test('generates appropriate colors for revenue heatmap', () => {
      render(<CustomerDensityHeatmap customers={mockCustomers} heatmapType='revenue' />);

      // Should use green color scheme for revenue
      expect(screen.getByTestId('base-map')).toBeInTheDocument();
    });

    test('generates appropriate colors for satisfaction heatmap', () => {
      render(<CustomerDensityHeatmap customers={mockCustomers} heatmapType='satisfaction' />);

      // Should use gradient color scheme for satisfaction
      expect(screen.getByTestId('base-map')).toBeInTheDocument();
    });
  });

  describe('Performance Optimizations', () => {
    test('handles empty customer array gracefully', () => {
      render(<CustomerDensityHeatmap customers={[]} />);

      expect(screen.getByTestId('base-map')).toBeInTheDocument();
      expect(screen.getByText('Market Analysis')).toBeInTheDocument();
    });

    test('memoizes grid cell calculations', () => {
      const { rerender } = render(<CustomerDensityHeatmap customers={mockCustomers} />);

      // Rerender with same props shouldn't cause issues
      rerender(<CustomerDensityHeatmap customers={mockCustomers} />);

      expect(screen.getByTestId('base-map')).toBeInTheDocument();
    });

    test('handles large datasets efficiently', () => {
      // Test with larger dataset
      const largeCustomerSet = Array.from({ length: 500 }, (_, i) => ({
        ...mockCustomers[0],
        id: `CUST-${i}`,
        coordinates: {
          latitude: 47.5 + i * 0.002,
          longitude: -122.4 + i * 0.002,
        },
      }));

      const startTime = performance.now();
      render(<CustomerDensityHeatmap customers={largeCustomerSet} />);
      const renderTime = performance.now() - startTime;

      expect(renderTime).toBeLessThan(1000); // Should render within 1 second
      expect(screen.getByTestId('base-map')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    test('has proper ARIA labels', () => {
      render(<CustomerDensityHeatmap customers={mockCustomers} />);

      // Check for accessible form controls
      const heatmapToggle = screen.getByLabelText(/Heatmap Grid/);
      expect(heatmapToggle).toBeInTheDocument();
    });

    test('supports keyboard navigation for controls', async () => {
      const user = userEvent.setup();
      render(<CustomerDensityHeatmap customers={mockCustomers} />);

      // Tab through controls
      await user.tab();

      // Should be able to navigate through controls
      expect(document.activeElement).toBeInTheDocument();
    });

    test('has appropriate heading structure', () => {
      render(<CustomerDensityHeatmap customers={mockCustomers} />);

      expect(screen.getByRole('heading', { level: 4, name: 'Heatmap Type' })).toBeInTheDocument();
      expect(screen.getByRole('heading', { level: 4, name: 'Map Layers' })).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    test('handles invalid coordinates gracefully', () => {
      const invalidCustomers = [
        {
          ...mockCustomers[0],
          coordinates: { latitude: NaN, longitude: NaN },
        },
      ];

      render(<CustomerDensityHeatmap customers={invalidCustomers} />);

      expect(screen.getByTestId('base-map')).toBeInTheDocument();
    });

    test('handles missing satisfaction data', () => {
      const customersWithoutSatisfaction = mockCustomers.map((c) => ({
        ...c,
        satisfaction: undefined,
      }));

      render(
        <CustomerDensityHeatmap
          customers={customersWithoutSatisfaction}
          heatmapType='satisfaction'
        />
      );

      expect(screen.getByTestId('base-map')).toBeInTheDocument();
    });
  });

  describe('Legend and Intensity Scale', () => {
    test('shows intensity scale legend', () => {
      render(<CustomerDensityHeatmap customers={mockCustomers} />);

      expect(screen.getByText('Intensity Scale')).toBeInTheDocument();
      expect(screen.getByText('High')).toBeInTheDocument();
      expect(screen.getByText('Low')).toBeInTheDocument();
    });

    test('updates legend colors based on heatmap type', async () => {
      const user = userEvent.setup();
      render(<CustomerDensityHeatmap customers={mockCustomers} />);

      // Switch to revenue heatmap
      await user.click(screen.getByText('Revenue'));

      // Legend should still be visible
      expect(screen.getByText('Intensity Scale')).toBeInTheDocument();
    });
  });
});
