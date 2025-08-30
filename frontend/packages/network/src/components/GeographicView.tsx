/**
 * Geographic Network View
 * Interactive map-based visualization of network infrastructure and coverage
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card, Button } from '@dotmac/primitives';
import {
  Map,
  Layers,
  MapPin,
  Satellite,
  Navigation,
  Search,
  Filter,
  AlertTriangle,
  Wifi,
  Signal
} from 'lucide-react';
import { MapContainer, TileLayer, Marker, Popup, Polygon, Circle, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

import type {
  GeographicViewProps,
  ServiceArea,
  NetworkNode,
  CoverageGap,
  NodeType
} from '../types';

// Fix Leaflet default markers
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom marker icons for different node types
const createNodeIcon = (nodeType: NodeType, status: string) => {
  const color = getNodeStatusColor(status);
  const size = getNodeIconSize(nodeType);

  return L.divIcon({
    html: `
      <div style="
        width: ${size}px;
        height: ${size}px;
        background-color: ${color};
        border: 2px solid white;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: ${size * 0.4}px;
        color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
      ">
        ${getNodeTypeIcon(nodeType)}
      </div>
    `,
    className: 'custom-node-marker',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2]
  });
};

const MapController: React.FC<{
  center?: [number, number];
  zoom?: number;
}> = ({ center, zoom }) => {
  const map = useMap();

  useEffect(() => {
    if (center && zoom) {
      map.setView(center, zoom);
    }
  }, [map, center, zoom]);

  return null;
};

export const GeographicView: React.FC<GeographicViewProps> = ({
  service_areas,
  network_nodes,
  coverage_gaps = [],
  show_coverage_overlay = true,
  show_network_overlay = true,
  map_style = 'street',
  interactive = true,
  on_area_click,
  on_node_click,
  on_gap_click,
  className = ''
}) => {
  // State management
  const [mapCenter, setMapCenter] = useState<[number, number]>([40.7128, -74.0060]); // NYC default
  const [mapZoom, setMapZoom] = useState(10);
  const [activeLayerGroup, setActiveLayerGroup] = useState('all');
  const [showCoverageOverlay, setShowCoverageOverlay] = useState(show_coverage_overlay);
  const [showNetworkOverlay, setShowNetworkOverlay] = useState(show_network_overlay);
  const [selectedNode, setSelectedNode] = useState<NetworkNode | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Refs
  const mapRef = useRef<L.Map | null>(null);

  // Calculate map center from nodes
  useEffect(() => {
    if (network_nodes.length > 0) {
      const validNodes = network_nodes.filter(node => node.latitude && node.longitude);
      if (validNodes.length > 0) {
        const avgLat = validNodes.reduce((sum, node) => sum + node.latitude!, 0) / validNodes.length;
        const avgLng = validNodes.reduce((sum, node) => sum + node.longitude!, 0) / validNodes.length;
        setMapCenter([avgLat, avgLng]);
      }
    }
  }, [network_nodes]);

  // Get tile layer URL based on map style
  const getTileLayerUrl = useCallback(() => {
    switch (map_style) {
      case 'satellite':
        return 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
      case 'terrain':
        return 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png';
      case 'dark':
        return 'https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png';
      default:
        return 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
    }
  }, [map_style]);

  // Filter nodes based on search and layer selection
  const filteredNodes = React.useMemo(() => {
    let nodes = network_nodes.filter(node => node.latitude && node.longitude);

    if (searchQuery) {
      nodes = nodes.filter(node =>
        node.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        node.hostname?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        node.node_type.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    if (activeLayerGroup !== 'all') {
      nodes = nodes.filter(node => node.node_type === activeLayerGroup);
    }

    return nodes;
  }, [network_nodes, searchQuery, activeLayerGroup]);

  // Handle node click
  const handleNodeClick = useCallback((node: NetworkNode) => {
    setSelectedNode(node);
    on_node_click?.(node);
  }, [on_node_click]);

  // Handle service area click
  const handleAreaClick = useCallback((area: ServiceArea) => {
    on_area_click?.(area);
  }, [on_area_click]);

  // Handle coverage gap click
  const handleGapClick = useCallback((gap: CoverageGap) => {
    on_gap_click?.(gap);
  }, [on_gap_click]);

  // Get coverage area color based on coverage percentage
  const getCoverageColor = (coveragePercentage: number): string => {
    if (coveragePercentage >= 90) return '#28a745';
    if (coveragePercentage >= 70) return '#ffc107';
    if (coveragePercentage >= 50) return '#fd7e14';
    return '#dc3545';
  };

  // Get gap severity color
  const getGapSeverityColor = (severity: string): string => {
    switch (severity) {
      case 'critical': return '#dc3545';
      case 'high': return '#fd7e14';
      case 'medium': return '#ffc107';
      case 'low': return '#28a745';
      default: return '#6c757d';
    }
  };

  return (
    <Card className={`geographic-view ${className} relative w-full h-full`}>
      {/* Map Controls */}
      <div className="map-controls absolute top-4 left-4 z-10 flex flex-col gap-2">
        {/* Search */}
        <div className="relative">
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 pr-4 py-2 border rounded-lg bg-white text-sm w-64"
          />
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-gray-400" />
        </div>

        {/* Layer Controls */}
        <div className="flex gap-2">
          <select
            value={activeLayerGroup}
            onChange={(e) => setActiveLayerGroup(e.target.value)}
            className="px-3 py-2 border rounded bg-white text-sm"
          >
            <option value="all">All Nodes</option>
            <option value="core_router">Core Routers</option>
            <option value="access_switch">Access Switches</option>
            <option value="wifi_ap">WiFi Access Points</option>
            <option value="cell_tower">Cell Towers</option>
            <option value="pop">Points of Presence</option>
          </select>

          <Button
            variant={showNetworkOverlay ? "default" : "outline"}
            size="sm"
            onClick={() => setShowNetworkOverlay(!showNetworkOverlay)}
            title="Toggle Network Overlay"
          >
            <MapPin className="h-4 w-4" />
          </Button>

          <Button
            variant={showCoverageOverlay ? "default" : "outline"}
            size="sm"
            onClick={() => setShowCoverageOverlay(!showCoverageOverlay)}
            title="Toggle Coverage Overlay"
          >
            <Signal className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Map Style Selector */}
      <div className="map-style-selector absolute top-4 right-4 z-10">
        <select
          value={map_style}
          onChange={(e) => {
            // This would typically update the parent component's map_style
            // For now, we'll just trigger a re-render
          }}
          className="px-3 py-2 border rounded bg-white text-sm"
        >
          <option value="street">Street</option>
          <option value="satellite">Satellite</option>
          <option value="terrain">Terrain</option>
          <option value="dark">Dark</option>
        </select>
      </div>

      {/* Main Map */}
      <MapContainer
        center={mapCenter}
        zoom={mapZoom}
        className="w-full h-full"
        style={{ minHeight: '400px' }}
        zoomControl={false}
        ref={mapRef}
      >
        <MapController center={mapCenter} zoom={mapZoom} />

        {/* Base Tile Layer */}
        <TileLayer
          url={getTileLayerUrl()}
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />

        {/* Service Areas */}
        {showCoverageOverlay && service_areas.map(area => {
          if (!area.polygon_coordinates?.coordinates) return null;

          const positions = area.polygon_coordinates.coordinates[0].map(
            (coord: [number, number]) => [coord[1], coord[0]] as [number, number]
          );

          return (
            <Polygon
              key={area.id}
              positions={positions}
              fillColor={getCoverageColor(area.coverage_percentage)}
              fillOpacity={0.3}
              color={getCoverageColor(area.coverage_percentage)}
              weight={2}
              eventHandlers={{
                click: () => handleAreaClick(area)
              }}
            >
              <Popup>
                <div className="p-2">
                  <h3 className="font-semibold">{area.name}</h3>
                  <div className="text-sm mt-1">
                    <div>Coverage: {area.coverage_percentage}%</div>
                    <div>Population: {area.population.toLocaleString()}</div>
                    <div>Households: {area.households.toLocaleString()}</div>
                    <div>Businesses: {area.businesses.toLocaleString()}</div>
                    <div className="mt-2">
                      Services: {area.service_types.join(', ')}
                    </div>
                  </div>
                </div>
              </Popup>
            </Polygon>
          );
        })}

        {/* Coverage Gaps */}
        {showCoverageOverlay && coverage_gaps.map(gap => {
          if (!gap.polygon_coordinates?.coordinates) return null;

          const positions = gap.polygon_coordinates.coordinates[0].map(
            (coord: [number, number]) => [coord[1], coord[0]] as [number, number]
          );

          return (
            <Polygon
              key={gap.id}
              positions={positions}
              fillColor={getGapSeverityColor(gap.severity)}
              fillOpacity={0.5}
              color={getGapSeverityColor(gap.severity)}
              weight={2}
              dashArray="5, 5"
              eventHandlers={{
                click: () => handleGapClick(gap)
              }}
            >
              <Popup>
                <div className="p-2">
                  <h3 className="font-semibold flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-red-500" />
                    Coverage Gap
                  </h3>
                  <div className="text-sm mt-1">
                    <div>Type: {gap.gap_type}</div>
                    <div>Severity: {gap.severity}</div>
                    <div>Affected Customers: {gap.affected_customers}</div>
                    <div>Potential Revenue: ${gap.potential_revenue.toLocaleString()}</div>
                    <div>Buildout Cost: ${gap.buildout_cost.toLocaleString()}</div>
                    <div>Priority Score: {gap.priority_score.toFixed(1)}</div>
                    {gap.recommendations.length > 0 && (
                      <div className="mt-2">
                        <div className="font-medium">Recommendations:</div>
                        <ul className="list-disc list-inside">
                          {gap.recommendations.slice(0, 3).map((rec, idx) => (
                            <li key={idx} className="text-xs">{rec}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </Popup>
            </Polygon>
          );
        })}

        {/* Network Nodes */}
        {showNetworkOverlay && filteredNodes.map(node => (
          <Marker
            key={node.node_id}
            position={[node.latitude!, node.longitude!]}
            icon={createNodeIcon(node.node_type, node.status)}
            eventHandlers={{
              click: () => handleNodeClick(node)
            }}
          >
            <Popup>
              <div className="p-2 min-w-64">
                <h3 className="font-semibold">{node.name || node.node_id}</h3>
                <div className="text-sm mt-1">
                  <div>Type: {node.node_type.replace(/_/g, ' ')}</div>
                  <div>Status: <span className={`font-medium ${getStatusTextColor(node.status)}`}>
                    {node.status}
                  </span></div>
                  {node.hostname && <div>Hostname: {node.hostname}</div>}
                  {node.ip_address && <div>IP: {node.ip_address}</div>}
                  {node.manufacturer && <div>Vendor: {node.manufacturer}</div>}
                  {node.model && <div>Model: {node.model}</div>}

                  {/* Performance Metrics */}
                  {(node.cpu_usage || node.memory_usage) && (
                    <div className="mt-2 border-t pt-2">
                      <div className="font-medium">Performance:</div>
                      {node.cpu_usage && <div>CPU: {node.cpu_usage}%</div>}
                      {node.memory_usage && <div>Memory: {node.memory_usage}%</div>}
                      {node.temperature && <div>Temp: {node.temperature}°C</div>}
                    </div>
                  )}

                  {/* Connectivity */}
                  <div className="mt-2 border-t pt-2">
                    <div className="font-medium">Connectivity:</div>
                    <div>Links: {node.connected_links.length}</div>
                    <div>Neighbors: {node.neighbor_count}</div>
                    {node.bandwidth_mbps && <div>Bandwidth: {node.bandwidth_mbps} Mbps</div>}
                  </div>

                  {/* Coverage for wireless nodes */}
                  {(node.node_type === 'wifi_ap' || node.node_type === 'cell_tower') && node.coverage_radius_km && (
                    <div className="mt-2 border-t pt-2">
                      <div className="font-medium">Coverage:</div>
                      <div>Radius: {node.coverage_radius_km} km</div>
                    </div>
                  )}

                  {node.last_seen_at && (
                    <div className="mt-2 text-xs text-gray-500">
                      Last seen: {new Date(node.last_seen_at).toLocaleString()}
                    </div>
                  )}
                </div>
              </div>
            </Popup>

            {/* Coverage radius for wireless nodes */}
            {(node.node_type === 'wifi_ap' || node.node_type === 'cell_tower') &&
             node.coverage_radius_km && (
              <Circle
                center={[node.latitude!, node.longitude!]}
                radius={node.coverage_radius_km * 1000} // Convert km to meters
                fillColor={getNodeStatusColor(node.status)}
                fillOpacity={0.1}
                color={getNodeStatusColor(node.status)}
                weight={1}
                opacity={0.5}
              />
            )}
          </Marker>
        ))}
      </MapContainer>

      {/* Legend */}
      <div className="map-legend absolute bottom-4 right-4 z-10 bg-white/95 p-3 rounded-lg shadow-lg max-w-xs">
        <h3 className="font-semibold text-sm mb-2">Legend</h3>

        {/* Node Types */}
        {showNetworkOverlay && (
          <div className="mb-3">
            <div className="text-xs font-medium mb-1">Network Nodes</div>
            {Object.values(NodeType).slice(0, 4).map(type => (
              <div key={type} className="flex items-center gap-2 text-xs mb-1">
                <div
                  className="w-3 h-3 rounded-full border border-white"
                  style={{ backgroundColor: getNodeStatusColor('active') }}
                />
                <span>{type.replace(/_/g, ' ')}</span>
              </div>
            ))}
          </div>
        )}

        {/* Coverage Areas */}
        {showCoverageOverlay && (
          <div>
            <div className="text-xs font-medium mb-1">Coverage</div>
            <div className="flex items-center gap-2 text-xs mb-1">
              <div className="w-3 h-3" style={{ backgroundColor: '#28a745' }} />
              <span>&gt;90%</span>
            </div>
            <div className="flex items-center gap-2 text-xs mb-1">
              <div className="w-3 h-3" style={{ backgroundColor: '#ffc107' }} />
              <span>70-90%</span>
            </div>
            <div className="flex items-center gap-2 text-xs mb-1">
              <div className="w-3 h-3" style={{ backgroundColor: '#fd7e14' }} />
              <span>50-70%</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <div className="w-3 h-3" style={{ backgroundColor: '#dc3545' }} />
              <span>&lt;50%</span>
            </div>
          </div>
        )}
      </div>

      {/* Status Bar */}
      <div className="map-status absolute bottom-4 left-4 z-10 bg-white/95 px-3 py-2 rounded text-xs">
        <span>Showing {filteredNodes.length} of {network_nodes.length} nodes</span>
        {service_areas.length > 0 && (
          <>
            <span className="mx-2">|</span>
            <span>{service_areas.length} service areas</span>
          </>
        )}
        {coverage_gaps.length > 0 && (
          <>
            <span className="mx-2">|</span>
            <span>{coverage_gaps.length} coverage gaps</span>
          </>
        )}
      </div>
    </Card>
  );
};

// Utility functions
function getNodeStatusColor(status: string): string {
  switch (status) {
    case 'active': return '#28a745';
    case 'inactive': return '#dc3545';
    case 'maintenance': return '#ffc107';
    case 'failed': return '#dc3545';
    default: return '#6c757d';
  }
}

function getStatusTextColor(status: string): string {
  switch (status) {
    case 'active': return 'text-green-600';
    case 'inactive': return 'text-red-600';
    case 'maintenance': return 'text-yellow-600';
    case 'failed': return 'text-red-600';
    default: return 'text-gray-600';
  }
}

function getNodeIconSize(nodeType: NodeType): number {
  switch (nodeType) {
    case NodeType.CORE_ROUTER: return 30;
    case NodeType.DISTRIBUTION_ROUTER: return 24;
    case NodeType.POP: return 28;
    case NodeType.DATA_CENTER: return 32;
    case NodeType.CELL_TOWER: return 22;
    case NodeType.ACCESS_SWITCH: return 18;
    case NodeType.WIFI_AP: return 16;
    case NodeType.CUSTOMER_PREMISES: return 14;
    default: return 20;
  }
}

function getNodeTypeIcon(nodeType: NodeType): string {
  switch (nodeType) {
    case NodeType.CORE_ROUTER: return '⚡';
    case NodeType.DISTRIBUTION_ROUTER: return '🔄';
    case NodeType.ACCESS_SWITCH: return '⚡';
    case NodeType.WIFI_AP: return '📶';
    case NodeType.CELL_TOWER: return '📡';
    case NodeType.FIBER_SPLICE: return '🔗';
    case NodeType.POP: return '🏢';
    case NodeType.CUSTOMER_PREMISES: return '🏠';
    case NodeType.DATA_CENTER: return '🏛️';
    default: return '⚡';
  }
}
