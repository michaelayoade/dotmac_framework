'use client';

import { clsx } from 'clsx';
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { DataSet } from 'vis-data';
import { Network } from 'vis-network';

import type { NetworkDevice, NetworkLink, Coordinates } from '../types';

interface NetworkTopologyMapProps {
  devices: NetworkDevice[];
  links: NetworkLink[];
  onDeviceSelect?: (device: NetworkDevice) => void;
  onLinkSelect?: (link: NetworkLink) => void;
  className?: string;
  showLabels?: boolean;
  highlightPath?: string[]; // Device IDs to highlight
}

interface NetworkNode {
  id: string;
  label: string;
  group: string;
  title: string;
  color?: {
    background: string;
    border: string;
    highlight: { background: string; border: string };
  };
  size?: number;
  physics?: boolean;
}

interface NetworkEdge {
  id: string;
  from: string;
  to: string;
  label?: string;
  color?: string;
  width?: number;
  smooth?: {
    enabled: boolean;
    type: string;
    roundness: number;
  };
  arrows?: {
    to: { enabled: boolean };
  };
}

export function NetworkTopologyMap({
  devices,
  links,
  onDeviceSelect,
  onLinkSelect,
  className,
  showLabels = true,
  highlightPath = [],
}: NetworkTopologyMapProps) {
  const networkRef = useRef<HTMLDivElement>(null);
  const networkInstance = useRef<Network | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  const getDeviceColor = useCallback(
    (device: NetworkDevice) => {
      const isHighlighted = highlightPath.includes(device.id);
      const baseColors = {
        router: { bg: '#3B82F6', border: '#1D4ED8' },
        switch: { bg: '#10B981', border: '#047857' },
        'fiber-node': { bg: '#8B5CF6', border: '#6D28D9' },
        tower: { bg: '#F59E0B', border: '#D97706' },
        pop: { bg: '#EF4444', border: '#DC2626' },
        core: { bg: '#6B7280', border: '#374151' },
      };

      const statusOverlay = {
        online: { opacity: 1.0, border: undefined },
        warning: { opacity: 0.8, border: undefined },
        offline: { opacity: 0.4, border: undefined },
        critical: { opacity: 0.6, border: '#DC2626' },
      };

      const baseColor = baseColors[device.type] || baseColors.router;
      const status = statusOverlay[device.status];

      return {
        background: isHighlighted ? '#FFD700' : baseColor.bg,
        border: isHighlighted ? '#FFA500' : status.border || baseColor.border,
        highlight: {
          background: '#FFD700',
          border: '#FFA500',
        },
      };
    },
    [highlightPath]
  );

  const getDeviceSize = useCallback((device: NetworkDevice) => {
    const sizeMap = {
      core: 40,
      pop: 35,
      router: 25,
      switch: 20,
      'fiber-node': 30,
      tower: 35,
    };

    const utilizationBonus = Math.floor(device.utilization / 10) * 2;
    return (sizeMap[device.type] || 25) + utilizationBonus;
  }, []);

  const getLinkColor = useCallback(
    (link: NetworkLink) => {
      const isHighlighted =
        highlightPath.includes(link.source) && highlightPath.includes(link.target);

      const baseColors = {
        fiber: '#10B981',
        wireless: '#3B82F6',
        copper: '#F59E0B',
      };

      const statusColors = {
        active: baseColors[link.type],
        degraded: '#F59E0B',
        inactive: '#6B7280',
      };

      if (isHighlighted) {
        return '#FFD700';
      }

      return statusColors[link.status] || statusColors.active;
    },
    [highlightPath]
  );

  const getLinkWidth = useCallback((link: NetworkLink) => {
    const baseWidth = 2;
    const capacityBonus = Math.min(link.capacity / 1000, 5); // Scale by Gbps
    const utilizationBonus = link.utilization > 80 ? 2 : 0;

    return baseWidth + capacityBonus + utilizationBonus;
  }, []);

  const createNetworkData = useCallback(() => {
    const nodes: NetworkNode[] = devices.map((device) => ({
      id: device.id,
      label: showLabels ? device.name : '',
      group: device.type,
      title: `
        <div class="p-3 bg-white rounded-lg shadow-lg border">
          <h4 class="font-bold text-gray-900 mb-2">${device.name}</h4>
          <div class="text-sm text-gray-600 space-y-1">
            <div><strong>Type:</strong> ${device.type}</div>
            <div><strong>Status:</strong> <span class="capitalize">${device.status}</span></div>
            <div><strong>Utilization:</strong> ${device.utilization.toFixed(1)}%</div>
            <div><strong>Capacity:</strong> ${device.capacity} Mbps</div>
            <div><strong>Connections:</strong> ${device.connections.length}</div>
            <div><strong>Location:</strong> ${device.coordinates.latitude.toFixed(4)}, ${device.coordinates.longitude.toFixed(4)}</div>
          </div>
        </div>
      `,
      color: getDeviceColor(device),
      size: getDeviceSize(device),
      physics: true,
    }));

    const edges: NetworkEdge[] = links.map((link) => ({
      id: link.id,
      from: link.source,
      to: link.target,
      label: showLabels ? `${link.utilization.toFixed(0)}%` : '',
      color: getLinkColor(link),
      width: getLinkWidth(link),
      smooth: {
        enabled: true,
        type: 'continuous',
        roundness: 0.5,
      },
      arrows: { to: { enabled: false } },
    }));

    return {
      nodes: new DataSet(nodes),
      edges: new DataSet(edges),
    };
  }, [devices, links, showLabels, getDeviceColor, getDeviceSize, getLinkColor, getLinkWidth]);

  const getNetworkOptions = useCallback(
    () => ({
      nodes: {
        shape: 'dot',
        font: {
          size: 12,
          color: '#1F2937',
        },
        borderWidth: 2,
        shadow: {
          enabled: true,
          color: 'rgba(0,0,0,0.1)',
          size: 5,
          x: 2,
          y: 2,
        },
      },
      edges: {
        font: {
          size: 10,
          color: '#6B7280',
          strokeWidth: 2,
          strokeColor: '#FFFFFF',
        },
        smooth: {
          enabled: true,
          type: 'continuous',
          forceDirection: 'none',
          roundness: 0.5,
        },
      },
      physics: {
        enabled: true,
        stabilization: {
          enabled: true,
          iterations: 100,
        },
        barnesHut: {
          gravitationalConstant: -2000,
          centralGravity: 0.1,
          springLength: 150,
          springConstant: 0.04,
          damping: 0.1,
        },
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
        hideEdgesOnDrag: false,
        hideEdgesOnZoom: false,
      },
      layout: {
        improvedLayout: true,
        hierarchical: {
          enabled: false,
        },
      },
    }),
    []
  );

  useEffect(() => {
    if (!networkRef.current || isInitialized) return;

    const data = createNetworkData();
    const options = getNetworkOptions();

    networkInstance.current = new Network(networkRef.current, data, options);

    // Event listeners
    networkInstance.current.on('selectNode', (event) => {
      if (event.nodes.length > 0) {
        const selectedDevice = devices.find((d) => d.id === event.nodes[0]);
        if (selectedDevice && onDeviceSelect) {
          onDeviceSelect(selectedDevice);
        }
      }
    });

    networkInstance.current.on('selectEdge', (event) => {
      if (event.edges.length > 0) {
        const selectedLink = links.find((l) => l.id === event.edges[0]);
        if (selectedLink && onLinkSelect) {
          onLinkSelect(selectedLink);
        }
      }
    });

    // Stabilization event
    networkInstance.current.on('stabilizationIterationsDone', () => {
      networkInstance.current?.setOptions({ physics: false });
    });

    setIsInitialized(true);

    return () => {
      if (networkInstance.current) {
        networkInstance.current.destroy();
        networkInstance.current = null;
      }
    };
  }, []);

  // Update network data when props change
  useEffect(() => {
    if (!networkInstance.current || !isInitialized) return;

    const data = createNetworkData();
    networkInstance.current.setData(data);
  }, [devices, links, showLabels, highlightPath, createNetworkData, isInitialized]);

  const handleFitNetwork = useCallback(() => {
    if (networkInstance.current) {
      networkInstance.current.fit({
        animation: {
          duration: 1000,
          easingFunction: 'easeInOutQuad',
        },
      });
    }
  }, []);

  const handleTogglePhysics = useCallback(() => {
    if (networkInstance.current) {
      // Toggle physics state by inverting current state
      const currentOptions = (networkInstance.current as any).physics?.options;
      const currentPhysicsEnabled = currentOptions?.enabled ?? true;
      networkInstance.current.setOptions({
        physics: { enabled: !currentPhysicsEnabled },
      });
    }
  }, []);

  return (
    <div className={clsx('relative w-full h-full', className)}>
      {/* Network Visualization */}
      <div
        ref={networkRef}
        className='w-full h-full bg-gray-50 rounded-lg border border-gray-200'
      />

      {/* Controls */}
      <div className='absolute top-4 right-4 flex flex-col space-y-2'>
        <button
          onClick={handleFitNetwork}
          className='px-3 py-1 text-xs bg-white border border-gray-300 rounded shadow-sm hover:bg-gray-50 transition-colors'
          title='Fit to view'
        >
          Fit View
        </button>
        <button
          onClick={handleTogglePhysics}
          className='px-3 py-1 text-xs bg-white border border-gray-300 rounded shadow-sm hover:bg-gray-50 transition-colors'
          title='Toggle physics'
        >
          Physics
        </button>
      </div>

      {/* Legend */}
      <div className='absolute bottom-4 left-4 bg-white p-3 rounded-lg shadow-lg border border-gray-200'>
        <h4 className='text-xs font-semibold text-gray-900 mb-2'>Device Types</h4>
        <div className='grid grid-cols-2 gap-2 text-xs'>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-blue-500'></div>
            <span>Router</span>
          </div>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-green-500'></div>
            <span>Switch</span>
          </div>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-purple-500'></div>
            <span>Fiber Node</span>
          </div>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-yellow-500'></div>
            <span>Tower</span>
          </div>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-red-500'></div>
            <span>POP</span>
          </div>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-gray-500'></div>
            <span>Core</span>
          </div>
        </div>
        <div className='mt-3 pt-2 border-t border-gray-200'>
          <div className='text-xs text-gray-600'>
            <div>Size = Capacity</div>
            <div>Color intensity = Status</div>
            <div>Line width = Utilization</div>
          </div>
        </div>
      </div>

      {/* Network Stats */}
      <div className='absolute top-4 left-4 bg-white p-3 rounded-lg shadow-lg border border-gray-200'>
        <div className='text-xs space-y-1'>
          <div>
            <strong>Devices:</strong> {devices.length}
          </div>
          <div>
            <strong>Links:</strong> {links.length}
          </div>
          <div>
            <strong>Online:</strong> {devices.filter((d) => d.status === 'online').length}
          </div>
          <div>
            <strong>Issues:</strong> {devices.filter((d) => d.status !== 'online').length}
          </div>
        </div>
      </div>
    </div>
  );
}

export default NetworkTopologyMap;
