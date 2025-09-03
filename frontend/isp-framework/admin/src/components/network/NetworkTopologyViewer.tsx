'use client';

import { useState, useEffect } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Server,
  Wifi,
  Zap,
  Router,
  Network,
  Monitor,
  Settings,
  Globe,
  MapPin,
} from 'lucide-react';

interface NetworkNode {
  id: string;
  name: string;
  type: 'core' | 'distribution' | 'access' | 'customer';
  status: 'operational' | 'degraded' | 'down' | 'maintenance';
  utilization: number;
  capacity: string;
  location: {
    x: number;
    y: number;
    address?: string;
    territory?: string;
  };
  connections: string[];
  metrics: {
    latency: number;
    packetLoss: number;
    bandwidth: number;
  };
  lastSeen: string;
}

interface NetworkConnection {
  id: string;
  from: string;
  to: string;
  type: 'fiber' | 'wireless' | 'copper';
  status: 'active' | 'down' | 'congested';
  capacity: string;
  utilization: number;
}

interface NetworkTopologyViewerProps {
  nodes?: NetworkNode[];
  connections?: NetworkConnection[];
  onNodeSelect?: (node: NetworkNode) => void;
  onConnectionSelect?: (connection: NetworkConnection) => void;
}

const mockNodes: NetworkNode[] = [
  {
    id: 'SEA-CORE-01',
    name: 'Seattle Core Router',
    type: 'core',
    status: 'operational',
    utilization: 67,
    capacity: '100Gbps',
    location: { x: 400, y: 200, address: '1000 Denny Way, Seattle', territory: 'Downtown' },
    connections: ['BEL-DIST-02', 'RED-DIST-03', 'KIR-DIST-04'],
    metrics: { latency: 2, packetLoss: 0.001, bandwidth: 67000 },
    lastSeen: '2024-02-20T14:30:00Z',
  },
  {
    id: 'BEL-DIST-02',
    name: 'Bellevue Distribution',
    type: 'distribution',
    status: 'operational',
    utilization: 82,
    capacity: '40Gbps',
    location: { x: 600, y: 150, address: '500 108th Ave NE, Bellevue', territory: 'Eastside' },
    connections: ['SEA-CORE-01', 'BEL-ACC-05', 'BEL-ACC-06'],
    metrics: { latency: 5, packetLoss: 0.002, bandwidth: 32800 },
    lastSeen: '2024-02-20T14:29:45Z',
  },
  {
    id: 'RED-DIST-03',
    name: 'Redmond Distribution',
    type: 'distribution',
    status: 'maintenance',
    utilization: 0,
    capacity: '40Gbps',
    location: { x: 700, y: 100, address: '200 Redmond Way, Redmond', territory: 'Eastside' },
    connections: ['SEA-CORE-01', 'RED-ACC-07'],
    metrics: { latency: 0, packetLoss: 0, bandwidth: 0 },
    lastSeen: '2024-02-20T12:00:00Z',
  },
  {
    id: 'KIR-DIST-04',
    name: 'Kirkland Distribution',
    type: 'distribution',
    status: 'operational',
    utilization: 55,
    capacity: '40Gbps',
    location: { x: 550, y: 250, address: '300 Kirkland Ave, Kirkland', territory: 'Eastside' },
    connections: ['SEA-CORE-01', 'KIR-ACC-08'],
    metrics: { latency: 4, packetLoss: 0.001, bandwidth: 22000 },
    lastSeen: '2024-02-20T14:30:00Z',
  },
  {
    id: 'BEL-ACC-05',
    name: 'Bellevue Access Point A',
    type: 'access',
    status: 'operational',
    utilization: 78,
    capacity: '10Gbps',
    location: { x: 650, y: 200, territory: 'Eastside' },
    connections: ['BEL-DIST-02', 'CUST-001', 'CUST-002'],
    metrics: { latency: 8, packetLoss: 0.005, bandwidth: 7800 },
    lastSeen: '2024-02-20T14:29:30Z',
  },
  {
    id: 'CUST-001',
    name: 'TechCorp Solutions',
    type: 'customer',
    status: 'operational',
    utilization: 45,
    capacity: '500Mbps',
    location: { x: 680, y: 250, address: '789 Business Park Dr', territory: 'Eastside' },
    connections: ['BEL-ACC-05'],
    metrics: { latency: 12, packetLoss: 0.01, bandwidth: 225 },
    lastSeen: '2024-02-20T14:30:00Z',
  },
];

const mockConnections: NetworkConnection[] = [
  {
    id: 'conn-1',
    from: 'SEA-CORE-01',
    to: 'BEL-DIST-02',
    type: 'fiber',
    status: 'active',
    capacity: '40Gbps',
    utilization: 82,
  },
  {
    id: 'conn-2',
    from: 'SEA-CORE-01',
    to: 'RED-DIST-03',
    type: 'fiber',
    status: 'down',
    capacity: '40Gbps',
    utilization: 0,
  },
  {
    id: 'conn-3',
    from: 'SEA-CORE-01',
    to: 'KIR-DIST-04',
    type: 'fiber',
    status: 'active',
    capacity: '40Gbps',
    utilization: 55,
  },
  {
    id: 'conn-4',
    from: 'BEL-DIST-02',
    to: 'BEL-ACC-05',
    type: 'fiber',
    status: 'congested',
    capacity: '10Gbps',
    utilization: 95,
  },
  {
    id: 'conn-5',
    from: 'BEL-ACC-05',
    to: 'CUST-001',
    type: 'fiber',
    status: 'active',
    capacity: '1Gbps',
    utilization: 45,
  },
];

export function NetworkTopologyViewer({
  nodes = mockNodes,
  connections = mockConnections,
  onNodeSelect,
  onConnectionSelect,
}: NetworkTopologyViewerProps) {
  const [selectedNode, setSelectedNode] = useState<NetworkNode | null>(null);
  const [selectedConnection, setSelectedConnection] = useState<NetworkConnection | null>(null);
  const [viewMode, setViewMode] = useState<'topology' | 'utilization' | 'status'>('topology');

  const getNodeIcon = (type: string) => {
    switch (type) {
      case 'core':
        return Server;
      case 'distribution':
        return Router;
      case 'access':
        return Wifi;
      case 'customer':
        return Monitor;
      default:
        return Network;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'operational':
        return 'text-green-600 bg-green-100';
      case 'degraded':
        return 'text-yellow-600 bg-yellow-100';
      case 'down':
        return 'text-red-600 bg-red-100';
      case 'maintenance':
        return 'text-blue-600 bg-blue-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getConnectionColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'stroke-green-500';
      case 'congested':
        return 'stroke-yellow-500';
      case 'down':
        return 'stroke-red-500';
      default:
        return 'stroke-gray-400';
    }
  };

  const getUtilizationColor = (utilization: number) => {
    if (utilization > 90) return 'text-red-600 bg-red-100';
    if (utilization > 75) return 'text-yellow-600 bg-yellow-100';
    return 'text-green-600 bg-green-100';
  };

  const handleNodeClick = (node: NetworkNode) => {
    setSelectedNode(node);
    setSelectedConnection(null);
    onNodeSelect?.(node);
  };

  const handleConnectionClick = (connection: NetworkConnection) => {
    setSelectedConnection(connection);
    setSelectedNode(null);
    onConnectionSelect?.(connection);
  };

  return (
    <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
      <div className='flex justify-between items-center mb-6'>
        <div>
          <h3 className='text-lg font-semibold text-gray-900'>Network Topology</h3>
          <p className='text-sm text-gray-600'>Real-time network infrastructure overview</p>
        </div>

        <div className='flex gap-2'>
          <select
            value={viewMode}
            onChange={(e) => setViewMode(e.target.value as any)}
            className='text-sm border border-gray-300 rounded px-2 py-1'
          >
            <option value='topology'>Topology View</option>
            <option value='utilization'>Utilization View</option>
            <option value='status'>Status View</option>
          </select>
          <button className='px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700'>
            <Settings className='h-4 w-4' />
          </button>
        </div>
      </div>

      <div className='grid grid-cols-1 lg:grid-cols-4 gap-6'>
        {/* Network Diagram */}
        <div className='lg:col-span-3'>
          <div className='relative bg-gray-50 rounded-lg p-4 h-96 overflow-hidden'>
            <svg width='100%' height='100%' viewBox='0 0 800 400' className='absolute inset-0'>
              {/* Render connections */}
              {connections.map((connection) => {
                const fromNode = nodes.find((n) => n.id === connection.from);
                const toNode = nodes.find((n) => n.id === connection.to);
                if (!fromNode || !toNode) return null;

                return (
                  <line
                    key={connection.id}
                    x1={fromNode.location.x}
                    y1={fromNode.location.y}
                    x2={toNode.location.x}
                    y2={toNode.location.y}
                    className={`${getConnectionColor(connection.status)} cursor-pointer`}
                    strokeWidth={selectedConnection?.id === connection.id ? '4' : '2'}
                    onClick={() => handleConnectionClick(connection)}
                  />
                );
              })}

              {/* Render nodes */}
              {nodes.map((node) => {
                const Icon = getNodeIcon(node.type);
                return (
                  <g key={node.id}>
                    <circle
                      cx={node.location.x}
                      cy={node.location.y}
                      r={node.type === 'core' ? 20 : node.type === 'distribution' ? 15 : 12}
                      className={`${getStatusColor(node.status)} cursor-pointer stroke-2 ${
                        selectedNode?.id === node.id ? 'stroke-blue-600' : 'stroke-gray-300'
                      }`}
                      onClick={() => handleNodeClick(node)}
                    />

                    {/* Status indicator */}
                    <circle
                      cx={node.location.x + 12}
                      cy={node.location.y - 12}
                      r={4}
                      className={
                        node.status === 'operational'
                          ? 'fill-green-500'
                          : node.status === 'degraded'
                            ? 'fill-yellow-500'
                            : node.status === 'down'
                              ? 'fill-red-500'
                              : 'fill-blue-500'
                      }
                    />

                    {/* Node label */}
                    <text
                      x={node.location.x}
                      y={node.location.y + 35}
                      textAnchor='middle'
                      className='text-xs font-medium fill-gray-700'
                    >
                      {node.name.split(' ')[0]}
                    </text>

                    {/* Utilization indicator in utilization view */}
                    {viewMode === 'utilization' && (
                      <text
                        x={node.location.x}
                        y={node.location.y + 50}
                        textAnchor='middle'
                        className={`text-xs font-bold ${
                          node.utilization > 90
                            ? 'fill-red-600'
                            : node.utilization > 75
                              ? 'fill-yellow-600'
                              : 'fill-green-600'
                        }`}
                      >
                        {node.utilization}%
                      </text>
                    )}
                  </g>
                );
              })}
            </svg>

            {/* Legend */}
            <div className='absolute bottom-4 left-4 bg-white rounded-lg shadow-sm border p-3'>
              <div className='text-xs font-medium text-gray-700 mb-2'>Legend</div>
              <div className='space-y-1 text-xs'>
                <div className='flex items-center gap-2'>
                  <div className='w-3 h-3 rounded-full bg-green-100 border-2 border-green-500'></div>
                  <span>Operational</span>
                </div>
                <div className='flex items-center gap-2'>
                  <div className='w-3 h-3 rounded-full bg-yellow-100 border-2 border-yellow-500'></div>
                  <span>Degraded</span>
                </div>
                <div className='flex items-center gap-2'>
                  <div className='w-3 h-3 rounded-full bg-red-100 border-2 border-red-500'></div>
                  <span>Down</span>
                </div>
                <div className='flex items-center gap-2'>
                  <div className='w-3 h-3 rounded-full bg-blue-100 border-2 border-blue-500'></div>
                  <span>Maintenance</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Details Panel */}
        <div className='space-y-4'>
          {selectedNode ? (
            <div className='bg-gray-50 rounded-lg p-4'>
              <div className='flex items-center gap-2 mb-3'>
                {React.createElement(getNodeIcon(selectedNode.type), {
                  className: 'h-5 w-5 text-gray-600',
                })}
                <h4 className='font-medium text-gray-900'>{selectedNode.name}</h4>
              </div>

              <div className='space-y-3 text-sm'>
                <div className='flex justify-between'>
                  <span className='text-gray-600'>Status:</span>
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(selectedNode.status)}`}
                  >
                    {selectedNode.status}
                  </span>
                </div>

                <div className='flex justify-between'>
                  <span className='text-gray-600'>Utilization:</span>
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-medium ${getUtilizationColor(selectedNode.utilization)}`}
                  >
                    {selectedNode.utilization}%
                  </span>
                </div>

                <div className='flex justify-between'>
                  <span className='text-gray-600'>Capacity:</span>
                  <span className='font-medium'>{selectedNode.capacity}</span>
                </div>

                <div className='flex justify-between'>
                  <span className='text-gray-600'>Latency:</span>
                  <span className='font-medium'>{selectedNode.metrics.latency}ms</span>
                </div>

                <div className='flex justify-between'>
                  <span className='text-gray-600'>Packet Loss:</span>
                  <span className='font-medium'>{selectedNode.metrics.packetLoss}%</span>
                </div>

                {selectedNode.location.address && (
                  <div>
                    <span className='text-gray-600 text-xs'>Location:</span>
                    <p className='text-xs mt-1'>{selectedNode.location.address}</p>
                  </div>
                )}

                <div>
                  <span className='text-gray-600 text-xs'>Connections:</span>
                  <div className='mt-1 space-y-1'>
                    {selectedNode.connections.map((connId) => {
                      const connectedNode = nodes.find((n) => n.id === connId);
                      return connectedNode ? (
                        <div key={connId} className='text-xs bg-white rounded px-2 py-1'>
                          {connectedNode.name}
                        </div>
                      ) : null;
                    })}
                  </div>
                </div>
              </div>
            </div>
          ) : selectedConnection ? (
            <div className='bg-gray-50 rounded-lg p-4'>
              <div className='flex items-center gap-2 mb-3'>
                <Network className='h-5 w-5 text-gray-600' />
                <h4 className='font-medium text-gray-900'>Connection Details</h4>
              </div>

              <div className='space-y-3 text-sm'>
                <div className='flex justify-between'>
                  <span className='text-gray-600'>Status:</span>
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(selectedConnection.status)}`}
                  >
                    {selectedConnection.status}
                  </span>
                </div>

                <div className='flex justify-between'>
                  <span className='text-gray-600'>Utilization:</span>
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-medium ${getUtilizationColor(selectedConnection.utilization)}`}
                  >
                    {selectedConnection.utilization}%
                  </span>
                </div>

                <div className='flex justify-between'>
                  <span className='text-gray-600'>Capacity:</span>
                  <span className='font-medium'>{selectedConnection.capacity}</span>
                </div>

                <div className='flex justify-between'>
                  <span className='text-gray-600'>Type:</span>
                  <span className='font-medium capitalize'>{selectedConnection.type}</span>
                </div>

                <div>
                  <span className='text-gray-600 text-xs'>Endpoints:</span>
                  <div className='mt-1 space-y-1'>
                    <div className='text-xs bg-white rounded px-2 py-1'>
                      From: {nodes.find((n) => n.id === selectedConnection.from)?.name}
                    </div>
                    <div className='text-xs bg-white rounded px-2 py-1'>
                      To: {nodes.find((n) => n.id === selectedConnection.to)?.name}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className='bg-gray-50 rounded-lg p-4 text-center text-gray-500'>
              <Network className='h-8 w-8 mx-auto mb-2 text-gray-400' />
              <p className='text-sm'>Click on a node or connection to view details</p>
            </div>
          )}

          {/* Quick Stats */}
          <div className='bg-gray-50 rounded-lg p-4'>
            <h4 className='font-medium text-gray-900 mb-3'>Network Overview</h4>
            <div className='space-y-2 text-sm'>
              <div className='flex justify-between'>
                <span className='text-gray-600'>Total Nodes:</span>
                <span className='font-medium'>{nodes.length}</span>
              </div>
              <div className='flex justify-between'>
                <span className='text-gray-600'>Active Connections:</span>
                <span className='font-medium'>
                  {connections.filter((c) => c.status === 'active').length}
                </span>
              </div>
              <div className='flex justify-between'>
                <span className='text-gray-600'>Issues:</span>
                <span className='font-medium text-red-600'>
                  {nodes.filter((n) => n.status === 'down').length +
                    connections.filter((c) => c.status === 'down').length}
                </span>
              </div>
              <div className='flex justify-between'>
                <span className='text-gray-600'>Maintenance:</span>
                <span className='font-medium text-blue-600'>
                  {nodes.filter((n) => n.status === 'maintenance').length}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
