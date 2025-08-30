/**
 * Advanced Network Topology Viewer
 * Comprehensive topology visualization with multiple rendering engines
 */

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Card, Button } from '@dotmac/primitives';
import {
  ZoomIn,
  ZoomOut,
  Maximize,
  RotateCcw,
  Settings,
  Layers,
  Filter,
  Search,
  Download,
  AlertTriangle,
  Activity,
  MapPin
} from 'lucide-react';
import * as d3 from 'd3';
import cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
import cose from 'cytoscape-cose-bilkent';

import type {
  NetworkTopologyProps,
  NetworkNode,
  NetworkLink,
  LayoutOptions,
  ViewportState,
  FilterOptions,
  SelectionState,
  NodeType,
  NodeStatus
} from '../types';

// Register cytoscape extensions
cytoscape.use(dagre);
cytoscape.use(cose);

export const NetworkTopologyViewer: React.FC<NetworkTopologyProps> = ({
  nodes,
  links,
  layout = { algorithm: 'force' },
  filters,
  selection,
  viewport,
  interactive = true,
  show_minimap = false,
  show_controls = true,
  show_legends = true,
  on_node_click,
  on_link_click,
  on_selection_change,
  on_viewport_change,
  className = '',
  style
}) => {
  // Refs for rendering engines
  const svgRef = useRef<SVGSVGElement>(null);
  const cytoscapeRef = useRef<HTMLDivElement>(null);
  const cytoscapeInstance = useRef<cytoscape.Core | null>(null);

  // State management
  const [currentEngine, setCurrentEngine] = useState<'d3' | 'cytoscape'>('d3');
  const [currentViewport, setCurrentViewport] = useState<ViewportState>(
    viewport || { zoom: 1, pan_x: 0, pan_y: 0 }
  );
  const [currentSelection, setCurrentSelection] = useState<SelectionState>(
    selection || { selected_nodes: [], selected_links: [] }
  );
  const [showControls, setShowControls] = useState(show_controls);
  const [showFilters, setShowFilters] = useState(false);

  // Filtered data based on active filters
  const filteredData = useMemo(() => {
    let filteredNodes = nodes;
    let filteredLinks = links;

    if (filters) {
      // Filter nodes by type
      if (filters.node_types && filters.node_types.length > 0) {
        filteredNodes = filteredNodes.filter(node =>
          filters.node_types!.includes(node.node_type)
        );
      }

      // Filter nodes by status
      if (filters.status_filter && filters.status_filter.length > 0) {
        filteredNodes = filteredNodes.filter(node =>
          filters.status_filter!.includes(node.status)
        );
      }

      // Filter links by type
      if (filters.link_types && filters.link_types.length > 0) {
        filteredLinks = filteredLinks.filter(link =>
          filters.link_types!.includes(link.link_type)
        );
      }

      // Remove links that reference filtered-out nodes
      const nodeIds = new Set(filteredNodes.map(node => node.node_id));
      filteredLinks = filteredLinks.filter(link =>
        nodeIds.has(link.source_node_id) && nodeIds.has(link.target_node_id)
      );
    }

    return { nodes: filteredNodes, links: filteredLinks };
  }, [nodes, links, filters]);

  // D3 Force Simulation Rendering
  const renderWithD3 = useCallback(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    const container = svg.select('.topology-container');

    // Clear existing content
    container.selectAll('*').remove();

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    // Create force simulation
    const simulation = d3.forceSimulation(filteredData.nodes as any)
      .force('link', d3.forceLink(filteredData.links as any)
        .id((d: any) => d.node_id)
        .distance(d => (d as NetworkLink).length_km ? (d as NetworkLink).length_km! * 10 : 100)
        .strength(0.5)
      )
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(30));

    // Create zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        container.attr('transform', event.transform);
        const newViewport = {
          zoom: event.transform.k,
          pan_x: event.transform.x,
          pan_y: event.transform.y
        };
        setCurrentViewport(newViewport);
        on_viewport_change?.(newViewport);
      });

    svg.call(zoom);

    // Draw links
    const linkElements = container
      .selectAll('.link')
      .data(filteredData.links)
      .enter()
      .append('line')
      .classed('link', true)
      .attr('stroke', d => d.color || getStatusColor(d.status))
      .attr('stroke-width', d => d.width || 2)
      .attr('stroke-dasharray', d => d.style === 'dashed' ? '5,5' : null)
      .style('cursor', interactive ? 'pointer' : 'default')
      .on('click', (event, d) => {
        if (interactive) {
          event.stopPropagation();
          on_link_click?.(d);
        }
      });

    // Add link labels for performance metrics
    if (filters?.show_performance_overlay) {
      container
        .selectAll('.link-label')
        .data(filteredData.links.filter(l => l.utilization_percentage !== undefined))
        .enter()
        .append('text')
        .classed('link-label', true)
        .text(d => `${Math.round(d.utilization_percentage!)}%`)
        .attr('font-size', 10)
        .attr('text-anchor', 'middle')
        .attr('fill', '#666');
    }

    // Draw nodes
    const nodeElements = container
      .selectAll('.node')
      .data(filteredData.nodes)
      .enter()
      .append('g')
      .classed('node', true)
      .style('cursor', interactive ? 'pointer' : 'default')
      .on('click', (event, d) => {
        if (interactive) {
          event.stopPropagation();
          handleNodeSelection(d);
          on_node_click?.(d);
        }
      });

    // Node circles
    nodeElements
      .append('circle')
      .attr('r', d => d.size || getNodeSize(d.node_type))
      .attr('fill', d => d.color || getNodeTypeColor(d.node_type))
      .attr('stroke', d => currentSelection.selected_nodes.includes(d.node_id) ? '#007bff' : '#fff')
      .attr('stroke-width', d => currentSelection.selected_nodes.includes(d.node_id) ? 3 : 2);

    // Node icons (simplified as text for now)
    nodeElements
      .append('text')
      .text(d => getNodeIcon(d.node_type))
      .attr('text-anchor', 'middle')
      .attr('dy', '.35em')
      .attr('font-family', 'Arial')
      .attr('font-size', 12)
      .attr('fill', '#fff');

    // Node labels
    if (filters?.show_labels !== false) {
      nodeElements
        .append('text')
        .text(d => d.name || d.node_id)
        .attr('text-anchor', 'middle')
        .attr('dy', d => (d.size || getNodeSize(d.node_type)) + 15)
        .attr('font-family', 'Arial')
        .attr('font-size', 11)
        .attr('fill', '#333');
    }

    // Performance overlay for nodes
    if (filters?.show_performance_overlay) {
      nodeElements
        .filter(d => d.cpu_usage !== undefined || d.memory_usage !== undefined)
        .append('circle')
        .attr('r', d => (d.size || getNodeSize(d.node_type)) + 5)
        .attr('fill', 'none')
        .attr('stroke', d => {
          const cpu = d.cpu_usage || 0;
          const memory = d.memory_usage || 0;
          const maxUsage = Math.max(cpu, memory);
          if (maxUsage > 90) return '#dc3545';
          if (maxUsage > 75) return '#ffc107';
          return '#28a745';
        })
        .attr('stroke-width', 2);
    }

    // Update positions on simulation tick
    simulation.on('tick', () => {
      linkElements
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      container.selectAll('.link-label')
        .attr('x', (d: any) => (d.source.x + d.target.x) / 2)
        .attr('y', (d: any) => (d.source.y + d.target.y) / 2);

      nodeElements.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
    });

    // Drag behavior for nodes
    if (interactive) {
      nodeElements.call(
        d3.drag<any, any>()
          .on('start', (event, d: any) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (event, d: any) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on('end', (event, d: any) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      );
    }

  }, [filteredData, currentSelection, filters, interactive, on_node_click, on_link_click, on_viewport_change]);

  // Cytoscape Rendering
  const renderWithCytoscape = useCallback(() => {
    if (!cytoscapeRef.current) return;

    // Destroy existing instance
    if (cytoscapeInstance.current) {
      cytoscapeInstance.current.destroy();
    }

    // Prepare data for Cytoscape
    const elements = [
      ...filteredData.nodes.map(node => ({
        data: {
          id: node.node_id,
          label: node.name || node.node_id,
          type: node.node_type,
          status: node.status,
          ...node
        },
        classes: `node-${node.node_type} status-${node.status}`
      })),
      ...filteredData.links.map(link => ({
        data: {
          id: link.link_id,
          source: link.source_node_id,
          target: link.target_node_id,
          type: link.link_type,
          status: link.status,
          ...link
        },
        classes: `link-${link.link_type} status-${link.status}`
      }))
    ];

    // Initialize Cytoscape
    const cy = cytoscape({
      container: cytoscapeRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': (ele: any) => ele.data('color') || getNodeTypeColor(ele.data('type')),
            'label': (ele: any) => filters?.show_labels !== false ? ele.data('label') : '',
            'width': (ele: any) => ele.data('size') || getNodeSize(ele.data('type')),
            'height': (ele: any) => ele.data('size') || getNodeSize(ele.data('type')),
            'text-valign': 'center',
            'text-halign': 'center',
            'color': '#fff',
            'text-outline-width': 2,
            'text-outline-color': '#333',
            'font-size': 10
          }
        },
        {
          selector: 'edge',
          style: {
            'width': (ele: any) => ele.data('width') || 2,
            'line-color': (ele: any) => ele.data('color') || getStatusColor(ele.data('status')),
            'target-arrow-color': (ele: any) => ele.data('color') || getStatusColor(ele.data('status')),
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier'
          }
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 3,
            'border-color': '#007bff'
          }
        },
        {
          selector: 'edge:selected',
          style: {
            'line-color': '#007bff',
            'target-arrow-color': '#007bff',
            'width': 4
          }
        }
      ],
      layout: getCytoscapeLayout(layout.algorithm),
      minZoom: 0.1,
      maxZoom: 4,
      wheelSensitivity: 0.5
    });

    // Event handlers
    if (interactive) {
      cy.on('tap', 'node', (event) => {
        const node = event.target.data() as NetworkNode;
        handleNodeSelection(node);
        on_node_click?.(node);
      });

      cy.on('tap', 'edge', (event) => {
        const link = event.target.data() as NetworkLink;
        on_link_click?.(link);
      });

      cy.on('viewport', () => {
        const viewport = cy.pan();
        const zoom = cy.zoom();
        const newViewport = {
          zoom,
          pan_x: viewport.x,
          pan_y: viewport.y
        };
        setCurrentViewport(newViewport);
        on_viewport_change?.(newViewport);
      });
    }

    cytoscapeInstance.current = cy;
  }, [filteredData, layout, filters, interactive, on_node_click, on_link_click, on_viewport_change, currentSelection]);

  // Handle node selection
  const handleNodeSelection = useCallback((node: NetworkNode) => {
    const newSelection = {
      ...currentSelection,
      selected_nodes: currentSelection.selected_nodes.includes(node.node_id)
        ? currentSelection.selected_nodes.filter(id => id !== node.node_id)
        : [...currentSelection.selected_nodes, node.node_id]
    };
    setCurrentSelection(newSelection);
    on_selection_change?.(newSelection);
  }, [currentSelection, on_selection_change]);

  // Control handlers
  const handleZoomIn = useCallback(() => {
    if (currentEngine === 'd3' && svgRef.current) {
      const svg = d3.select(svgRef.current);
      svg.transition().call(
        d3.zoom<SVGSVGElement, unknown>().scaleBy as any, 1.5
      );
    } else if (cytoscapeInstance.current) {
      cytoscapeInstance.current.zoom(cytoscapeInstance.current.zoom() * 1.5);
    }
  }, [currentEngine]);

  const handleZoomOut = useCallback(() => {
    if (currentEngine === 'd3' && svgRef.current) {
      const svg = d3.select(svgRef.current);
      svg.transition().call(
        d3.zoom<SVGSVGElement, unknown>().scaleBy as any, 0.75
      );
    } else if (cytoscapeInstance.current) {
      cytoscapeInstance.current.zoom(cytoscapeInstance.current.zoom() * 0.75);
    }
  }, [currentEngine]);

  const handleFitView = useCallback(() => {
    if (currentEngine === 'd3' && svgRef.current) {
      const svg = d3.select(svgRef.current);
      const container = svg.select('.topology-container');
      const bounds = container.node()?.getBBox();
      if (bounds) {
        const width = svgRef.current.clientWidth;
        const height = svgRef.current.clientHeight;
        const scale = Math.min(width / bounds.width, height / bounds.height) * 0.9;
        const transform = d3.zoomIdentity
          .translate(width / 2, height / 2)
          .scale(scale)
          .translate(-bounds.x - bounds.width / 2, -bounds.y - bounds.height / 2);
        svg.transition().call(
          d3.zoom<SVGSVGElement, unknown>().transform as any, transform
        );
      }
    } else if (cytoscapeInstance.current) {
      cytoscapeInstance.current.fit();
    }
  }, [currentEngine]);

  const handleReset = useCallback(() => {
    if (currentEngine === 'd3') {
      renderWithD3();
    } else {
      renderWithCytoscape();
    }
    setCurrentViewport({ zoom: 1, pan_x: 0, pan_y: 0 });
  }, [currentEngine, renderWithD3, renderWithCytoscape]);

  // Render based on selected engine
  useEffect(() => {
    if (currentEngine === 'd3') {
      renderWithD3();
    } else {
      renderWithCytoscape();
    }
  }, [currentEngine, renderWithD3, renderWithCytoscape]);

  return (
    <Card className={`network-topology-viewer ${className}`} style={style}>
      {/* Controls */}
      {showControls && (
        <div className="topology-controls absolute top-4 left-4 z-10 flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleZoomIn}
            title="Zoom In"
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleZoomOut}
            title="Zoom Out"
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleFitView}
            title="Fit to View"
          >
            <Maximize className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleReset}
            title="Reset View"
          >
            <RotateCcw className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
            title="Toggle Filters"
          >
            <Filter className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Engine Selector */}
      {showControls && (
        <div className="engine-selector absolute top-4 right-4 z-10">
          <select
            value={currentEngine}
            onChange={(e) => setCurrentEngine(e.target.value as 'd3' | 'cytoscape')}
            className="px-3 py-1 border rounded bg-white text-sm"
          >
            <option value="d3">D3 Force</option>
            <option value="cytoscape">Cytoscape</option>
          </select>
        </div>
      )}

      {/* Main Visualization Area */}
      <div className="topology-canvas relative w-full h-full">
        {currentEngine === 'd3' ? (
          <svg
            ref={svgRef}
            className="w-full h-full"
            style={{ minHeight: '400px' }}
          >
            <g className="topology-container" />
          </svg>
        ) : (
          <div
            ref={cytoscapeRef}
            className="w-full h-full"
            style={{ minHeight: '400px' }}
          />
        )}
      </div>

      {/* Status Bar */}
      {showControls && (
        <div className="topology-status absolute bottom-4 left-4 z-10 bg-white/90 px-3 py-1 rounded text-xs">
          <span>Nodes: {filteredData.nodes.length}</span>
          <span className="mx-2">|</span>
          <span>Links: {filteredData.links.length}</span>
          <span className="mx-2">|</span>
          <span>Zoom: {Math.round(currentViewport.zoom * 100)}%</span>
        </div>
      )}

      {/* Legend */}
      {show_legends && (
        <div className="topology-legend absolute bottom-4 right-4 z-10 bg-white/90 p-3 rounded text-xs">
          <div className="font-medium mb-2">Node Types</div>
          {Object.values(NodeType).map(type => (
            <div key={type} className="flex items-center gap-2 mb-1">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: getNodeTypeColor(type) }}
              />
              <span>{type.replace(/_/g, ' ')}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
};

// Utility functions
function getNodeTypeColor(nodeType: NodeType): string {
  const colors: Record<NodeType, string> = {
    [NodeType.CORE_ROUTER]: '#dc3545',
    [NodeType.DISTRIBUTION_ROUTER]: '#fd7e14',
    [NodeType.ACCESS_SWITCH]: '#20c997',
    [NodeType.WIFI_AP]: '#0dcaf0',
    [NodeType.CELL_TOWER]: '#6f42c1',
    [NodeType.FIBER_SPLICE]: '#198754',
    [NodeType.POP]: '#0d6efd',
    [NodeType.CUSTOMER_PREMISES]: '#6c757d',
    [NodeType.DATA_CENTER]: '#495057'
  };
  return colors[nodeType] || '#6c757d';
}

function getStatusColor(status: NodeStatus): string {
  const colors: Record<NodeStatus, string> = {
    [NodeStatus.ACTIVE]: '#28a745',
    [NodeStatus.INACTIVE]: '#dc3545',
    [NodeStatus.MAINTENANCE]: '#ffc107',
    [NodeStatus.FAILED]: '#dc3545',
    [NodeStatus.UNKNOWN]: '#6c757d'
  };
  return colors[status] || '#6c757d';
}

function getNodeSize(nodeType: NodeType): number {
  const sizes: Record<NodeType, number> = {
    [NodeType.CORE_ROUTER]: 25,
    [NodeType.DISTRIBUTION_ROUTER]: 20,
    [NodeType.ACCESS_SWITCH]: 15,
    [NodeType.WIFI_AP]: 12,
    [NodeType.CELL_TOWER]: 18,
    [NodeType.FIBER_SPLICE]: 8,
    [NodeType.POP]: 22,
    [NodeType.CUSTOMER_PREMISES]: 10,
    [NodeType.DATA_CENTER]: 30
  };
  return sizes[nodeType] || 15;
}

function getNodeIcon(nodeType: NodeType): string {
  const icons: Record<NodeType, string> = {
    [NodeType.CORE_ROUTER]: '⚡',
    [NodeType.DISTRIBUTION_ROUTER]: '🔄',
    [NodeType.ACCESS_SWITCH]: '⚡',
    [NodeType.WIFI_AP]: '📶',
    [NodeType.CELL_TOWER]: '📡',
    [NodeType.FIBER_SPLICE]: '🔗',
    [NodeType.POP]: '🏢',
    [NodeType.CUSTOMER_PREMISES]: '🏠',
    [NodeType.DATA_CENTER]: '🏛️'
  };
  return icons[nodeType] || '⚡';
}

function getCytoscapeLayout(algorithm: string): any {
  switch (algorithm) {
    case 'hierarchical':
      return { name: 'dagre', rankDir: 'TB' };
    case 'cose':
      return { name: 'cose-bilkent' };
    case 'circular':
      return { name: 'circle' };
    case 'grid':
      return { name: 'grid' };
    default:
      return { name: 'cose' };
  }
}
