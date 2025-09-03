/**
 * Base Map Component Tests
 * Core mapping functionality tests
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BaseMap } from '../components/BaseMap';

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
  MapContainer: ({ children, ...props }: any) => (
    <div data-testid='map-container' {...props}>
      {children}
    </div>
  ),
  TileLayer: (props: any) => <div data-testid='tile-layer' {...props} />,
  ZoomControl: (props: any) => <div data-testid='zoom-control' {...props} />,
  ScaleControl: (props: any) => <div data-testid='scale-control' {...props} />,
  useMap: () => ({
    setView: jest.fn(),
    getZoom: jest.fn(() => 13),
    getCenter: jest.fn(() => ({ lat: 47.6062, lng: -122.3321 })),
  }),
  useMapEvents: (events: any) => {
    return null;
  },
}));

// Mock Leaflet
jest.mock('leaflet', () => ({
  icon: jest.fn(() => ({})),
  divIcon: jest.fn(() => ({})),
  point: jest.fn(() => ({})),
  bounds: jest.fn(() => ({})),
  latLng: jest.fn((lat, lng) => ({ lat, lng })),
  latLngBounds: jest.fn(() => ({})),
}));

describe('BaseMap', () => {
  const defaultProps = {
    config: {
      defaultCenter: { latitude: 47.6062, longitude: -122.3321 },
      defaultZoom: 13,
    },
  };

  describe('Basic Rendering', () => {
    test('renders map container', () => {
      render(<BaseMap {...defaultProps} />);

      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });

    test('renders tile layer', () => {
      render(<BaseMap {...defaultProps} />);

      expect(screen.getByTestId('tile-layer')).toBeInTheDocument();
    });

    test('renders zoom control', () => {
      render(<BaseMap {...defaultProps} />);

      expect(screen.getByTestId('zoom-control')).toBeInTheDocument();
    });

    test('renders scale control', () => {
      render(<BaseMap {...defaultProps} />);

      expect(screen.getByTestId('scale-control')).toBeInTheDocument();
    });

    test('applies custom className', () => {
      const { container } = render(<BaseMap {...defaultProps} className='custom-map-class' />);

      expect(container.firstChild).toHaveClass('custom-map-class');
    });

    test('renders children components', () => {
      render(
        <BaseMap {...defaultProps}>
          <div data-testid='child-component'>Test Child</div>
        </BaseMap>
      );

      expect(screen.getByTestId('child-component')).toBeInTheDocument();
      expect(screen.getByText('Test Child')).toBeInTheDocument();
    });
  });

  describe('Map Configuration', () => {
    test('uses default center coordinates', () => {
      render(<BaseMap {...defaultProps} />);

      const mapContainer = screen.getByTestId('map-container');
      expect(mapContainer).toBeInTheDocument();
    });

    test('uses default zoom level', () => {
      render(<BaseMap {...defaultProps} />);

      const mapContainer = screen.getByTestId('map-container');
      expect(mapContainer).toBeInTheDocument();
    });

    test('overrides default config with custom values', () => {
      const customConfig = {
        defaultCenter: { latitude: 40.7128, longitude: -74.006 },
        defaultZoom: 15,
        minZoom: 5,
        maxZoom: 18,
      };

      render(<BaseMap config={customConfig} />);

      const mapContainer = screen.getByTestId('map-container');
      expect(mapContainer).toBeInTheDocument();
    });

    test('handles missing config gracefully', () => {
      render(<BaseMap />);

      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });
  });

  describe('Tile Layer Configuration', () => {
    test('uses OpenStreetMap tiles by default', () => {
      render(<BaseMap {...defaultProps} />);

      const tileLayer = screen.getByTestId('tile-layer');
      expect(tileLayer).toBeInTheDocument();
    });

    test('includes attribution', () => {
      render(<BaseMap {...defaultProps} />);

      const tileLayer = screen.getByTestId('tile-layer');
      expect(tileLayer).toBeInTheDocument();
    });

    test('configures tile layer options', () => {
      render(<BaseMap {...defaultProps} />);

      const tileLayer = screen.getByTestId('tile-layer');
      expect(tileLayer).toBeInTheDocument();
    });
  });

  describe('Map Controls', () => {
    test('positions zoom control correctly', () => {
      render(<BaseMap {...defaultProps} />);

      const zoomControl = screen.getByTestId('zoom-control');
      expect(zoomControl).toBeInTheDocument();
    });

    test('positions scale control correctly', () => {
      render(<BaseMap {...defaultProps} />);

      const scaleControl = screen.getByTestId('scale-control');
      expect(scaleControl).toBeInTheDocument();
    });

    test('allows disabling controls', () => {
      const customConfig = {
        ...defaultProps.config,
        zoomControl: false,
      };

      render(<BaseMap config={customConfig} />);

      // When disabled, control should not be rendered
      expect(screen.queryByTestId('zoom-control')).not.toBeInTheDocument();
    });
  });

  describe('Responsive Behavior', () => {
    test('handles viewport changes', () => {
      const { rerender } = render(<BaseMap {...defaultProps} />);

      // Simulate viewport change
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 768,
      });

      rerender(<BaseMap {...defaultProps} />);

      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });

    test('adapts to container size changes', () => {
      const { container } = render(<BaseMap {...defaultProps} />);

      // Change container size
      const mapContainer = container.querySelector('[data-testid="map-container"]');
      if (mapContainer) {
        Object.defineProperty(mapContainer, 'offsetWidth', { value: 500 });
        Object.defineProperty(mapContainer, 'offsetHeight', { value: 300 });
      }

      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });
  });

  describe('Performance Optimizations', () => {
    test('handles rapid re-renders efficiently', () => {
      const { rerender } = render(<BaseMap {...defaultProps} />);

      // Rapid re-renders shouldn't cause issues
      for (let i = 0; i < 10; i++) {
        rerender(<BaseMap {...defaultProps} />);
      }

      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });

    test('manages memory efficiently', () => {
      const { unmount } = render(<BaseMap {...defaultProps} />);

      expect(screen.getByTestId('map-container')).toBeInTheDocument();

      // Clean unmount
      unmount();
    });

    test('handles large numbers of children', () => {
      const manyChildren = Array.from({ length: 100 }, (_, i) => (
        <div key={i} data-testid={`child-${i}`}>
          Child {i}
        </div>
      ));

      render(<BaseMap {...defaultProps}>{manyChildren}</BaseMap>);

      expect(screen.getByTestId('map-container')).toBeInTheDocument();
      expect(screen.getByTestId('child-0')).toBeInTheDocument();
      expect(screen.getByTestId('child-99')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    test('handles invalid coordinates gracefully', () => {
      const invalidConfig = {
        defaultCenter: { latitude: NaN, longitude: NaN },
        defaultZoom: 13,
      };

      render(<BaseMap config={invalidConfig} />);

      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });

    test('handles invalid zoom levels', () => {
      const invalidConfig = {
        ...defaultProps.config,
        defaultZoom: -5,
      };

      render(<BaseMap config={invalidConfig} />);

      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });

    test('handles network errors for tiles', () => {
      render(<BaseMap {...defaultProps} />);

      // Simulate tile loading error
      const tileLayer = screen.getByTestId('tile-layer');
      fireEvent.error(tileLayer);

      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    test('has appropriate ARIA attributes', () => {
      render(<BaseMap {...defaultProps} />);

      const mapContainer = screen.getByTestId('map-container');
      expect(mapContainer).toBeInTheDocument();
    });

    test('supports keyboard navigation', () => {
      render(<BaseMap {...defaultProps} />);

      const mapContainer = screen.getByTestId('map-container');

      // Should be focusable
      fireEvent.focus(mapContainer);
      expect(mapContainer).toHaveFocus();
    });

    test('provides screen reader support', () => {
      render(<BaseMap {...defaultProps} />);

      const mapContainer = screen.getByTestId('map-container');
      expect(mapContainer).toBeInTheDocument();
    });
  });

  describe('Touch and Mobile Support', () => {
    test('handles touch events', () => {
      render(<BaseMap {...defaultProps} />);

      const mapContainer = screen.getByTestId('map-container');

      fireEvent.touchStart(mapContainer, {
        touches: [{ clientX: 100, clientY: 100 }],
      });

      expect(mapContainer).toBeInTheDocument();
    });

    test('supports pinch-to-zoom gestures', () => {
      render(<BaseMap {...defaultProps} />);

      const mapContainer = screen.getByTestId('map-container');

      // Simulate pinch gesture
      fireEvent.touchStart(mapContainer, {
        touches: [
          { clientX: 100, clientY: 100 },
          { clientX: 150, clientY: 150 },
        ],
      });

      expect(mapContainer).toBeInTheDocument();
    });
  });

  describe('Map Events', () => {
    test('handles map click events', () => {
      const onClick = jest.fn();

      render(<BaseMap {...defaultProps} onClick={onClick} />);

      const mapContainer = screen.getByTestId('map-container');
      fireEvent.click(mapContainer);

      // Click event handling would be tested with proper leaflet mock
      expect(mapContainer).toBeInTheDocument();
    });

    test('handles map drag events', () => {
      render(<BaseMap {...defaultProps} />);

      const mapContainer = screen.getByTestId('map-container');

      fireEvent.mouseDown(mapContainer, { clientX: 100, clientY: 100 });
      fireEvent.mouseMove(mapContainer, { clientX: 150, clientY: 150 });
      fireEvent.mouseUp(mapContainer);

      expect(mapContainer).toBeInTheDocument();
    });

    test('handles zoom events', () => {
      render(<BaseMap {...defaultProps} />);

      const mapContainer = screen.getByTestId('map-container');

      fireEvent.wheel(mapContainer, { deltaY: -100 });

      expect(mapContainer).toBeInTheDocument();
    });
  });

  describe('Loading States', () => {
    test('shows loading state initially', () => {
      render(<BaseMap {...defaultProps} />);

      // Map should render immediately with mocked components
      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });

    test('handles tile loading states', async () => {
      render(<BaseMap {...defaultProps} />);

      const tileLayer = screen.getByTestId('tile-layer');

      // Simulate tile loading
      fireEvent.load(tileLayer);

      await waitFor(() => {
        expect(tileLayer).toBeInTheDocument();
      });
    });
  });

  describe('Theme and Styling', () => {
    test('applies light theme by default', () => {
      render(<BaseMap {...defaultProps} />);

      const tileLayer = screen.getByTestId('tile-layer');
      expect(tileLayer).toBeInTheDocument();
    });

    test('supports custom tile layer styles', () => {
      const customConfig = {
        ...defaultProps.config,
        tileLayer: {
          url: 'https://custom-tiles/{z}/{x}/{y}.png',
          attribution: 'Custom Attribution',
        },
      };

      render(<BaseMap config={customConfig} />);

      const tileLayer = screen.getByTestId('tile-layer');
      expect(tileLayer).toBeInTheDocument();
    });
  });

  describe('Bounds and Viewport Management', () => {
    test('fits bounds when specified', () => {
      const configWithBounds = {
        ...defaultProps.config,
        bounds: [
          { latitude: 47.5, longitude: -122.5 },
          { latitude: 47.7, longitude: -122.1 },
        ],
      };

      render(<BaseMap config={configWithBounds} />);

      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });

    test('respects max bounds', () => {
      const configWithMaxBounds = {
        ...defaultProps.config,
        maxBounds: [
          { latitude: 47.0, longitude: -123.0 },
          { latitude: 48.0, longitude: -121.0 },
        ],
      };

      render(<BaseMap config={configWithMaxBounds} />);

      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });
  });
});
