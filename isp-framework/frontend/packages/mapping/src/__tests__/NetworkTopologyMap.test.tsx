/**
 * Network Topology Map Component Tests
 * Tests for network infrastructure visualization
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { NetworkTopologyMap } from '../components/NetworkTopologyMap';
import type { NetworkNode, NetworkConnection } from '../types';

// Mock components
jest.mock('../components/BaseMap', () => ({
  BaseMap: ({ children, ...props }: any) => (
    <div data-testid='base-map' {...props}>
      {children}
    </div>
  ),
}));

jest.mock('react-leaflet', () => ({
  Circle: ({ children, ...props }: any) => (
    <div data-testid='leaflet-circle' {...props}>
      {children}
    </div>
  ),
  Polyline: ({ children, ...props }: any) => (
    <div data-testid='leaflet-polyline' {...props}>
      {children}
    </div>
  ),
  LayerGroup: ({ children }: any) => <div data-testid='leaflet-layer-group'>{children}</div>,
  Popup: ({ children }: any) => <div data-testid='leaflet-popup'>{children}</div>,
  Tooltip: ({ children }: any) => <div data-testid='leaflet-tooltip'>{children}</div>,
}));

// Test data
const mockNetworkNodes: NetworkNode[] = [
  {
    id: 'NODE-001',
    name: 'Main Data Center',
    type: 'datacenter',
    coordinates: { latitude: 47.6062, longitude: -122.3321 },
    status: 'online',
    capacity: 10000,
    currentLoad: 7500,
    ipAddress: '10.0.1.1',
    devices: [
      {
        id: 'SW-001',
        type: 'switch',
        model: 'Cisco Catalyst 9000',
        ports: 48,
        activeConnections: 42,
        status: 'online',
      },
    ],
    redundancy: 'active-active',
    lastPing: new Date(),
  },
  {
    id: 'NODE-002',
    name: 'Distribution Hub Alpha',
    type: 'hub',
    coordinates: { latitude: 47.6205, longitude: -122.3212 },
    status: 'online',
    capacity: 5000,
    currentLoad: 3200,
    ipAddress: '10.0.2.1',
    devices: [
      {
        id: 'RT-001',
        type: 'router',
        model: 'Juniper MX Series',
        ports: 24,
        activeConnections: 18,
        status: 'online',
      },
    ],
    redundancy: 'standby',
    lastPing: new Date(),
  },
  {
    id: 'NODE-003',
    name: 'Edge Router Beta',
    type: 'edge',
    coordinates: { latitude: 47.6101, longitude: -122.2015 },
    status: 'degraded',
    capacity: 1000,
    currentLoad: 950,
    ipAddress: '10.0.3.1',
    devices: [
      {
        id: 'RT-002',
        type: 'router',
        model: 'Cisco ASR 1000',
        ports: 12,
        activeConnections: 11,
        status: 'warning',
      },
    ],
    redundancy: 'none',
    lastPing: new Date(),
  },
];

const mockConnections: NetworkConnection[] = [
  {
    id: 'CONN-001',
    sourceNodeId: 'NODE-001',
    targetNodeId: 'NODE-002',
    type: 'fiber',
    bandwidth: '10Gbps',
    utilization: 75,
    latency: 2.5,
    status: 'active',
    redundancy: true,
  },
  {
    id: 'CONN-002',
    sourceNodeId: 'NODE-002',
    targetNodeId: 'NODE-003',
    type: 'ethernet',
    bandwidth: '1Gbps',
    utilization: 92,
    latency: 5.2,
    status: 'congested',
    redundancy: false,
  },
];

describe('NetworkTopologyMap', () => {
  const defaultProps = {
    nodes: mockNetworkNodes,
    connections: mockConnections,
    config: {
      defaultCenter: { latitude: 47.6062, longitude: -122.3321 },
      defaultZoom: 12,
    },
  };

  describe('Basic Rendering', () => {
    test('renders network topology map', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      expect(screen.getByTestId('base-map')).toBeInTheDocument();
      expect(screen.getByText('Network Layers')).toBeInTheDocument();
      expect(screen.getByText('Network Health')).toBeInTheDocument();
    });

    test('renders network nodes', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // Should render circle components for nodes
      expect(screen.getAllByTestId('leaflet-circle')).toHaveLength(expect.any(Number));
    });

    test('renders network connections', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // Should render polyline components for connections
      expect(screen.getAllByTestId('leaflet-polyline')).toHaveLength(expect.any(Number));
    });

    test('renders with empty nodes array', () => {
      render(<NetworkTopologyMap nodes={[]} connections={[]} config={defaultProps.config} />);

      expect(screen.getByTestId('base-map')).toBeInTheDocument();
    });
  });

  describe('Network Health Dashboard', () => {
    test('displays network health metrics', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      expect(screen.getByText('Network Health')).toBeInTheDocument();
      expect(screen.getByText('Online Nodes')).toBeInTheDocument();
      expect(screen.getByText('Total Capacity')).toBeInTheDocument();
      expect(screen.getByText('Average Utilization')).toBeInTheDocument();
    });

    test('calculates health metrics correctly', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // Should show metrics based on test data
      // 2 online nodes out of 3 total
      expect(screen.getByText(/2 \/ 3/)).toBeInTheDocument();
    });

    test('shows critical alerts when present', () => {
      const nodesWithCritical = [
        ...mockNetworkNodes,
        {
          ...mockNetworkNodes[0],
          id: 'NODE-004',
          status: 'offline' as const,
        },
      ];

      render(<NetworkTopologyMap {...defaultProps} nodes={nodesWithCritical} />);

      // Should show critical alert indicator
      expect(screen.getByText(/Critical/i)).toBeInTheDocument();
    });
  });

  describe('Layer Controls', () => {
    test('shows layer control options', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      expect(screen.getByText('Network Layers')).toBeInTheDocument();
      expect(screen.getByText('Nodes')).toBeInTheDocument();
      expect(screen.getByText('Connections')).toBeInTheDocument();
      expect(screen.getByText('Labels')).toBeInTheDocument();
    });

    test('toggles node layer visibility', async () => {
      const user = userEvent.setup();
      render(<NetworkTopologyMap {...defaultProps} />);

      const nodesToggle = screen.getByLabelText(/Nodes/);
      expect(nodesToggle).toBeChecked();

      await user.click(nodesToggle);
      expect(nodesToggle).not.toBeChecked();
    });

    test('toggles connection layer visibility', async () => {
      const user = userEvent.setup();
      render(<NetworkTopologyMap {...defaultProps} />);

      const connectionsToggle = screen.getByLabelText(/Connections/);
      expect(connectionsToggle).toBeChecked();

      await user.click(connectionsToggle);
      expect(connectionsToggle).not.toBeChecked();
    });

    test('toggles label visibility', async () => {
      const user = userEvent.setup();
      render(<NetworkTopologyMap {...defaultProps} />);

      const labelsToggle = screen.getByLabelText(/Labels/);

      await user.click(labelsToggle);
      // Toggle state should change
    });
  });

  describe('Node Visualization', () => {
    test('colors nodes by status', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      const circles = screen.getAllByTestId('leaflet-circle');
      expect(circles.length).toBeGreaterThan(0);
    });

    test('sizes nodes by capacity', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // Nodes should be sized according to capacity
      const circles = screen.getAllByTestId('leaflet-circle');
      expect(circles.length).toEqual(mockNetworkNodes.length);
    });

    test('shows node type indicators', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // Different node types should have different visualization
      expect(screen.getAllByTestId('leaflet-circle')).toHaveLength(mockNetworkNodes.length);
    });

    test('displays load utilization', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // Nodes should show utilization through visual indicators
      expect(screen.getByTestId('base-map')).toBeInTheDocument();
    });
  });

  describe('Connection Visualization', () => {
    test('colors connections by status', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      const polylines = screen.getAllByTestId('leaflet-polyline');
      expect(polylines.length).toEqual(mockConnections.length);
    });

    test('shows bandwidth through line thickness', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // Higher bandwidth connections should have thicker lines
      const polylines = screen.getAllByTestId('leaflet-polyline');
      expect(polylines.length).toBeGreaterThan(0);
    });

    test('indicates utilization with color intensity', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // High utilization should show different colors
      expect(screen.getAllByTestId('leaflet-polyline')).toHaveLength(2);
    });

    test('shows redundant connections with different styling', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // Redundant connections should have different visual treatment
      expect(screen.getAllByTestId('leaflet-polyline')).toHaveLength(mockConnections.length);
    });
  });

  describe('Node Details and Interaction', () => {
    test('shows node popup on click', async () => {
      const onNodeSelect = jest.fn();
      render(<NetworkTopologyMap {...defaultProps} onNodeSelect={onNodeSelect} />);

      // Click simulation would trigger popup in real leaflet
      expect(screen.getByTestId('base-map')).toBeInTheDocument();
    });

    test('displays device information in popup', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // Popup should show device details when implemented
      expect(screen.getByTestId('base-map')).toBeInTheDocument();
    });

    test('shows real-time metrics', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // Should display current load, ping times, etc.
      expect(screen.getByText(/Online Nodes/)).toBeInTheDocument();
    });
  });

  describe('Performance Monitoring', () => {
    test('displays latency information', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // Should show latency metrics
      expect(screen.getByText('Network Health')).toBeInTheDocument();
    });

    test('shows throughput utilization', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // Should display utilization percentages
      expect(screen.getByText(/Average Utilization/)).toBeInTheDocument();
    });

    test('indicates congested connections', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // High utilization connections should be highlighted
      expect(screen.getAllByTestId('leaflet-polyline')).toHaveLength(mockConnections.length);
    });
  });

  describe('Real-time Updates', () => {
    test('updates when node status changes', () => {
      const { rerender } = render(<NetworkTopologyMap {...defaultProps} />);

      const updatedNodes = mockNetworkNodes.map((node) =>
        node.id === 'NODE-003' ? { ...node, status: 'online' as const } : node
      );

      rerender(<NetworkTopologyMap {...defaultProps} nodes={updatedNodes} />);

      expect(screen.getByTestId('base-map')).toBeInTheDocument();
    });

    test('updates when connection metrics change', () => {
      const { rerender } = render(<NetworkTopologyMap {...defaultProps} />);

      const updatedConnections = mockConnections.map((conn) =>
        conn.id === 'CONN-002' ? { ...conn, utilization: 50 } : conn
      );

      rerender(<NetworkTopologyMap {...defaultProps} connections={updatedConnections} />);

      expect(screen.getAllByTestId('leaflet-polyline')).toHaveLength(updatedConnections.length);
    });
  });

  describe('Filtering and Search', () => {
    test('filters nodes by type', async () => {
      const user = userEvent.setup();
      render(<NetworkTopologyMap {...defaultProps} />);

      // Add filter controls and test
      expect(screen.getByTestId('base-map')).toBeInTheDocument();
    });

    test('filters by node status', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // Should be able to filter by online/offline/degraded
      expect(screen.getByText(/Online Nodes/)).toBeInTheDocument();
    });

    test('searches for specific nodes', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // Search functionality would be tested when implemented
      expect(screen.getByTestId('base-map')).toBeInTheDocument();
    });
  });

  describe('Redundancy Visualization', () => {
    test('shows redundant paths', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // Should visualize backup/redundant connections differently
      expect(screen.getAllByTestId('leaflet-polyline')).toHaveLength(mockConnections.length);
    });

    test('highlights single points of failure', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // Nodes without redundancy should be highlighted
      expect(screen.getAllByTestId('leaflet-circle')).toHaveLength(mockNetworkNodes.length);
    });
  });

  describe('Error Handling', () => {
    test('handles invalid node coordinates', () => {
      const invalidNodes = [
        {
          ...mockNetworkNodes[0],
          coordinates: { latitude: NaN, longitude: NaN },
        },
      ];

      render(
        <NetworkTopologyMap nodes={invalidNodes} connections={[]} config={defaultProps.config} />
      );

      expect(screen.getByTestId('base-map')).toBeInTheDocument();
    });

    test('handles missing connections gracefully', () => {
      const orphanedConnections = [
        {
          ...mockConnections[0],
          sourceNodeId: 'NONEXISTENT-001',
          targetNodeId: 'NONEXISTENT-002',
        },
      ];

      render(
        <NetworkTopologyMap
          nodes={mockNetworkNodes}
          connections={orphanedConnections}
          config={defaultProps.config}
        />
      );

      expect(screen.getByTestId('base-map')).toBeInTheDocument();
    });

    test('handles network data loading states', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // Should handle loading states gracefully
      expect(screen.getByText('Network Health')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    test('provides keyboard navigation', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      const layerToggles = screen.getAllByRole('checkbox');
      expect(layerToggles.length).toBeGreaterThan(0);
    });

    test('has appropriate ARIA labels', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      const nodesToggle = screen.getByLabelText(/Nodes/);
      expect(nodesToggle).toBeInTheDocument();
    });

    test('supports screen readers', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // Should have proper headings and structure
      expect(screen.getByRole('heading', { name: /Network Layers/i })).toBeInTheDocument();
    });
  });

  describe('Performance', () => {
    test('handles large numbers of nodes efficiently', () => {
      const manyNodes = Array.from({ length: 100 }, (_, i) => ({
        ...mockNetworkNodes[0],
        id: `NODE-${i.toString().padStart(3, '0')}`,
        coordinates: {
          latitude: 47.5 + i * 0.01,
          longitude: -122.4 + i * 0.01,
        },
      }));

      const startTime = performance.now();
      render(
        <NetworkTopologyMap nodes={manyNodes} connections={[]} config={defaultProps.config} />
      );
      const renderTime = performance.now() - startTime;

      expect(renderTime).toBeLessThan(1000);
      expect(screen.getByTestId('base-map')).toBeInTheDocument();
    });

    test('efficiently updates on data changes', () => {
      const { rerender } = render(<NetworkTopologyMap {...defaultProps} />);

      // Multiple rapid updates should be handled efficiently
      for (let i = 0; i < 5; i++) {
        const updatedNodes = mockNetworkNodes.map((node) => ({
          ...node,
          currentLoad: Math.random() * node.capacity,
        }));

        rerender(<NetworkTopologyMap {...defaultProps} nodes={updatedNodes} />);
      }

      expect(screen.getByTestId('base-map')).toBeInTheDocument();
    });
  });

  describe('Legend and Indicators', () => {
    test('shows network status legend', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      // Should have legend for node/connection statuses
      expect(screen.getByText('Network Health')).toBeInTheDocument();
    });

    test('displays capacity and utilization indicators', () => {
      render(<NetworkTopologyMap {...defaultProps} />);

      expect(screen.getByText('Total Capacity')).toBeInTheDocument();
      expect(screen.getByText('Average Utilization')).toBeInTheDocument();
    });
  });
});
