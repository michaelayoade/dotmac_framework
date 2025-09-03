/**
 * Territory Map Component
 *
 * Advanced geographic visualization for territory management
 * with interactive features and real-time data visualization.
 *
 * Features:
 * - Interactive territory boundaries
 * - Customer density visualization
 * - Service coverage mapping
 * - Performance analytics overlay
 * - Route optimization
 * - Lead tracking
 */

import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { Map, View } from 'ol';
import { Tile as TileLayer, Vector as VectorLayer } from 'ol/layer';
import { OSM, Vector as VectorSource } from 'ol/source';
import { Style, Fill, Stroke, Circle } from 'ol/style';
import { Feature } from 'ol';
import { Point, Polygon } from 'ol/geom';
import { fromLonLat, toLonLat } from 'ol/proj';
import { Draw, Select } from 'ol/interaction';

// Types
export interface Territory {
  id: string;
  name: string;
  description?: string;
  boundaries: number[][];
  color: string;
  resellerId: string;
  isActive: boolean;
  priority: 'high' | 'medium' | 'low';
  serviceTypes: string[];
  customerCount: number;
  revenue: number;
  potentialCustomers: number;
  metadata: Record<string, any>;
}

export interface Customer {
  id: string;
  name: string;
  address: string;
  coordinates: [number, number];
  services: string[];
  revenue: number;
  status: 'active' | 'inactive' | 'prospect';
  territoryId?: string;
  lastActivity: string;
  metadata: Record<string, any>;
}

export interface Lead {
  id: string;
  name: string;
  address: string;
  coordinates: [number, number];
  score: number;
  source: string;
  status: 'new' | 'contacted' | 'qualified' | 'converted' | 'lost';
  assignedTo?: string;
  territoryId?: string;
  createdAt: string;
  metadata: Record<string, any>;
}

export interface ServiceCoverage {
  id: string;
  serviceType: string;
  coverageArea: number[][];
  quality: 'excellent' | 'good' | 'fair' | 'poor';
  availability: number;
  maxSpeed?: number;
  metadata: Record<string, any>;
}

export interface TerritoryMapProps {
  territories: Territory[];
  customers: Customer[];
  leads: Lead[];
  serviceCoverage: ServiceCoverage[];
  selectedTerritory?: string;
  onTerritorySelect?: (territory: Territory) => void;
  onCustomerSelect?: (customer: Customer) => void;
  onLeadSelect?: (lead: Lead) => void;
  onTerritoryCreate?: (boundaries: number[][]) => void;
  onTerritoryUpdate?: (territoryId: string, boundaries: number[][]) => void;
  onTerritoryDelete?: (territoryId: string) => void;
  mode?: 'view' | 'edit' | 'create';
  showHeatmap?: boolean;
  showRoutes?: boolean;
  showCoverage?: boolean;
  className?: string;
}

// Style configurations
const TERRITORY_STYLES = {
  high: new Style({
    fill: new Fill({ color: 'rgba(239, 68, 68, 0.2)' }),
    stroke: new Stroke({ color: '#EF4444', width: 2 }),
  }),
  medium: new Style({
    fill: new Fill({ color: 'rgba(245, 158, 11, 0.2)' }),
    stroke: new Stroke({ color: '#F59E0B', width: 2 }),
  }),
  low: new Style({
    fill: new Fill({ color: 'rgba(16, 185, 129, 0.2)' }),
    stroke: new Stroke({ color: '#10B981', width: 2 }),
  }),
  selected: new Style({
    fill: new Fill({ color: 'rgba(59, 130, 246, 0.3)' }),
    stroke: new Stroke({ color: '#3B82F6', width: 3 }),
  }),
};

const CUSTOMER_STYLES = {
  active: new Style({
    image: new Circle({
      radius: 6,
      fill: new Fill({ color: '#10B981' }),
      stroke: new Stroke({ color: '#ffffff', width: 2 }),
    }),
  }),
  inactive: new Style({
    image: new Circle({
      radius: 5,
      fill: new Fill({ color: '#6B7280' }),
      stroke: new Stroke({ color: '#ffffff', width: 1 }),
    }),
  }),
  prospect: new Style({
    image: new Circle({
      radius: 5,
      fill: new Fill({ color: '#F59E0B' }),
      stroke: new Stroke({ color: '#ffffff', width: 1 }),
    }),
  }),
};

const LEAD_STYLES = {
  new: new Style({
    image: new Circle({
      radius: 4,
      fill: new Fill({ color: '#3B82F6' }),
      stroke: new Stroke({ color: '#ffffff', width: 1 }),
    }),
  }),
  contacted: new Style({
    image: new Circle({
      radius: 4,
      fill: new Fill({ color: '#8B5CF6' }),
      stroke: new Stroke({ color: '#ffffff', width: 1 }),
    }),
  }),
  qualified: new Style({
    image: new Circle({
      radius: 4,
      fill: new Fill({ color: '#F59E0B' }),
      stroke: new Stroke({ color: '#ffffff', width: 1 }),
    }),
  }),
  converted: new Style({
    image: new Circle({
      radius: 4,
      fill: new Fill({ color: '#10B981' }),
      stroke: new Stroke({ color: '#ffffff', width: 1 }),
    }),
  }),
  lost: new Style({
    image: new Circle({
      radius: 3,
      fill: new Fill({ color: '#EF4444' }),
      stroke: new Stroke({ color: '#ffffff', width: 1 }),
    }),
  }),
};

export const TerritoryMap: React.FC<TerritoryMapProps> = ({
  territories,
  customers,
  leads,
  serviceCoverage,
  selectedTerritory,
  onTerritorySelect,
  onCustomerSelect,
  onLeadSelect,
  onTerritoryCreate,
  onTerritoryUpdate,
  onTerritoryDelete,
  mode = 'view',
  showHeatmap = false,
  showRoutes = false,
  showCoverage = false,
  className = '',
}) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<Map | null>(null);
  const [isMapReady, setIsMapReady] = useState(false);
  const [hoveredFeature, setHoveredFeature] = useState<any>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; content: string } | null>(null);

  // Vector sources for different data layers
  const territorySourceRef = useRef<VectorSource>(new VectorSource());
  const customerSourceRef = useRef<VectorSource>(new VectorSource());
  const leadSourceRef = useRef<VectorSource>(new VectorSource());
  const coverageSourceRef = useRef<VectorSource>(new VectorSource());

  // Initialize map
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    const map = new Map({
      target: mapRef.current,
      layers: [
        new TileLayer({
          source: new OSM(),
        }),
        new VectorLayer({
          source: territorySourceRef.current,
          style: (feature) => {
            const territory = feature.get('territory') as Territory;
            const isSelected = selectedTerritory === territory.id;
            return isSelected ? TERRITORY_STYLES.selected : TERRITORY_STYLES[territory.priority];
          },
        }),
        new VectorLayer({
          source: coverageSourceRef.current,
          style: new Style({
            fill: new Fill({ color: 'rgba(59, 130, 246, 0.1)' }),
            stroke: new Stroke({ color: '#3B82F6', width: 1, lineDash: [5, 5] }),
          }),
        }),
        new VectorLayer({
          source: customerSourceRef.current,
          style: (feature) => {
            const customer = feature.get('customer') as Customer;
            return CUSTOMER_STYLES[customer.status];
          },
        }),
        new VectorLayer({
          source: leadSourceRef.current,
          style: (feature) => {
            const lead = feature.get('lead') as Lead;
            return LEAD_STYLES[lead.status];
          },
        }),
      ],
      view: new View({
        center: fromLonLat([-98.5795, 39.8283]), // Center of US
        zoom: 4,
      }),
    });

    // Add interactions
    const selectInteraction = new Select({
      condition: (event) => event.type === 'singleclick',
      style: null, // Keep original style
    });

    selectInteraction.on('select', (event) => {
      if (event.selected.length > 0) {
        const feature = event.selected[0];
        const territory = feature.get('territory');
        const customer = feature.get('customer');
        const lead = feature.get('lead');

        if (territory && onTerritorySelect) {
          onTerritorySelect(territory);
        } else if (customer && onCustomerSelect) {
          onCustomerSelect(customer);
        } else if (lead && onLeadSelect) {
          onLeadSelect(lead);
        }
      }
    });

    map.addInteraction(selectInteraction);

    // Add drawing interaction for create mode
    if (mode === 'create' || mode === 'edit') {
      const drawInteraction = new Draw({
        source: territorySourceRef.current,
        type: 'Polygon',
      });

      drawInteraction.on('drawend', (event) => {
        const feature = event.feature;
        const geometry = feature.getGeometry() as Polygon;
        const coordinates = geometry.getCoordinates()[0].map((coord) => toLonLat(coord));

        if (onTerritoryCreate) {
          onTerritoryCreate(coordinates);
        }
      });

      map.addInteraction(drawInteraction);
    }

    // Mouse hover for tooltips
    map.on('pointermove', (event) => {
      const feature = map.forEachFeatureAtPixel(event.pixel, (feature) => feature);

      if (feature !== hoveredFeature) {
        setHoveredFeature(feature);

        if (feature) {
          const territory = feature.get('territory');
          const customer = feature.get('customer');
          const lead = feature.get('lead');

          let content = '';
          if (territory) {
            content = `<strong>${territory.name}</strong><br/>
                      Customers: ${territory.customerCount}<br/>
                      Revenue: $${territory.revenue.toLocaleString()}`;
          } else if (customer) {
            content = `<strong>${customer.name}</strong><br/>
                      Status: ${customer.status}<br/>
                      Revenue: $${customer.revenue.toLocaleString()}`;
          } else if (lead) {
            content = `<strong>${lead.name}</strong><br/>
                      Score: ${lead.score}<br/>
                      Status: ${lead.status}`;
          }

          setTooltip({
            x: event.pixel[0],
            y: event.pixel[1],
            content,
          });
        } else {
          setTooltip(null);
        }
      }
    });

    mapInstanceRef.current = map;
    setIsMapReady(true);

    return () => {
      map.setTarget(undefined);
      mapInstanceRef.current = null;
      setIsMapReady(false);
    };
  }, [mode]);

  // Update territory features
  useEffect(() => {
    if (!isMapReady || !territorySourceRef.current) return;

    territorySourceRef.current.clear();

    territories.forEach((territory) => {
      const coordinates = territory.boundaries.map((coord) => fromLonLat(coord));
      const polygonFeature = new Feature({
        geometry: new Polygon([coordinates]),
        territory,
      });

      territorySourceRef.current.addFeature(polygonFeature);
    });
  }, [territories, isMapReady]);

  // Update customer features
  useEffect(() => {
    if (!isMapReady || !customerSourceRef.current) return;

    customerSourceRef.current.clear();

    customers.forEach((customer) => {
      const pointFeature = new Feature({
        geometry: new Point(fromLonLat(customer.coordinates)),
        customer,
      });

      customerSourceRef.current.addFeature(pointFeature);
    });
  }, [customers, isMapReady]);

  // Update lead features
  useEffect(() => {
    if (!isMapReady || !leadSourceRef.current) return;

    leadSourceRef.current.clear();

    leads.forEach((lead) => {
      const pointFeature = new Feature({
        geometry: new Point(fromLonLat(lead.coordinates)),
        lead,
      });

      leadSourceRef.current.addFeature(pointFeature);
    });
  }, [leads, isMapReady]);

  // Update service coverage
  useEffect(() => {
    if (!isMapReady || !showCoverage || !coverageSourceRef.current) return;

    coverageSourceRef.current.clear();

    serviceCoverage.forEach((coverage) => {
      const coordinates = coverage.coverageArea.map((coord) => fromLonLat(coord));
      const polygonFeature = new Feature({
        geometry: new Polygon([coordinates]),
        coverage,
      });

      coverageSourceRef.current.addFeature(polygonFeature);
    });
  }, [serviceCoverage, showCoverage, isMapReady]);

  // Fit map to territories
  const fitToTerritories = useCallback(() => {
    if (!mapInstanceRef.current || !territories.length) return;

    const extent = territorySourceRef.current.getExtent();
    mapInstanceRef.current.getView().fit(extent, {
      padding: [50, 50, 50, 50],
      duration: 1000,
    });
  }, [territories]);

  // Territory analytics
  const territoryAnalytics = useMemo(() => {
    return territories.map((territory) => {
      const territoryCustomers = customers.filter((c) => c.territoryId === territory.id);
      const territoryLeads = leads.filter((l) => l.territoryId === territory.id);

      const totalRevenue = territoryCustomers.reduce((sum, c) => sum + c.revenue, 0);
      const averageRevenue = totalRevenue / (territoryCustomers.length || 1);

      const conversionRate =
        territoryLeads.length > 0
          ? (territoryLeads.filter((l) => l.status === 'converted').length /
              territoryLeads.length) *
            100
          : 0;

      return {
        ...territory,
        actualCustomers: territoryCustomers.length,
        actualRevenue: totalRevenue,
        averageRevenue,
        leadsCount: territoryLeads.length,
        conversionRate,
        efficiency: (totalRevenue / territory.potentialCustomers) * 100,
      };
    });
  }, [territories, customers, leads]);

  return (
    <div className={`territory-map-container ${className}`}>
      {/* Map Controls */}
      <div className='map-controls'>
        <div className='control-group'>
          <button onClick={fitToTerritories} className='control-button' title='Fit to territories'>
            🎯
          </button>

          <button
            className={`control-button ${showHeatmap ? 'active' : ''}`}
            title='Toggle heatmap'
          >
            🔥
          </button>

          <button className={`control-button ${showRoutes ? 'active' : ''}`} title='Toggle routes'>
            🛣️
          </button>

          <button
            className={`control-button ${showCoverage ? 'active' : ''}`}
            title='Toggle coverage'
          >
            📡
          </button>
        </div>

        <div className='mode-selector'>
          <select value={mode} className='mode-select'>
            <option value='view'>View</option>
            <option value='edit'>Edit</option>
            <option value='create'>Create</option>
          </select>
        </div>
      </div>

      {/* Map */}
      <div ref={mapRef} className='territory-map' />

      {/* Tooltip */}
      {tooltip && (
        <div
          className='map-tooltip'
          style={{
            left: tooltip.x + 10,
            top: tooltip.y + 10,
          }}
          dangerouslySetInnerHTML={{ __html: tooltip.content }}
        />
      )}

      {/* Legend */}
      <div className='map-legend'>
        <h4>Legend</h4>

        <div className='legend-section'>
          <h5>Territories</h5>
          <div className='legend-item'>
            <div className='legend-color high-priority'></div>
            <span>High Priority</span>
          </div>
          <div className='legend-item'>
            <div className='legend-color medium-priority'></div>
            <span>Medium Priority</span>
          </div>
          <div className='legend-item'>
            <div className='legend-color low-priority'></div>
            <span>Low Priority</span>
          </div>
        </div>

        <div className='legend-section'>
          <h5>Customers</h5>
          <div className='legend-item'>
            <div className='legend-dot active-customer'></div>
            <span>Active ({customers.filter((c) => c.status === 'active').length})</span>
          </div>
          <div className='legend-item'>
            <div className='legend-dot inactive-customer'></div>
            <span>Inactive ({customers.filter((c) => c.status === 'inactive').length})</span>
          </div>
          <div className='legend-item'>
            <div className='legend-dot prospect-customer'></div>
            <span>Prospects ({customers.filter((c) => c.status === 'prospect').length})</span>
          </div>
        </div>

        <div className='legend-section'>
          <h5>Leads</h5>
          <div className='legend-item'>
            <div className='legend-dot new-lead'></div>
            <span>New ({leads.filter((l) => l.status === 'new').length})</span>
          </div>
          <div className='legend-item'>
            <div className='legend-dot qualified-lead'></div>
            <span>Qualified ({leads.filter((l) => l.status === 'qualified').length})</span>
          </div>
          <div className='legend-item'>
            <div className='legend-dot converted-lead'></div>
            <span>Converted ({leads.filter((l) => l.status === 'converted').length})</span>
          </div>
        </div>
      </div>

      {/* Territory Analytics Panel */}
      {selectedTerritory && (
        <div className='analytics-panel'>
          {(() => {
            const territory = territoryAnalytics.find((t) => t.id === selectedTerritory);
            if (!territory) return null;

            return (
              <div className='territory-details'>
                <h3>{territory.name}</h3>

                <div className='metrics-grid'>
                  <div className='metric'>
                    <label>Customers</label>
                    <value>
                      {territory.actualCustomers} / {territory.customerCount}
                    </value>
                  </div>

                  <div className='metric'>
                    <label>Revenue</label>
                    <value>${territory.actualRevenue.toLocaleString()}</value>
                  </div>

                  <div className='metric'>
                    <label>Avg Revenue</label>
                    <value>${territory.averageRevenue.toLocaleString()}</value>
                  </div>

                  <div className='metric'>
                    <label>Leads</label>
                    <value>{territory.leadsCount}</value>
                  </div>

                  <div className='metric'>
                    <label>Conversion</label>
                    <value>{territory.conversionRate.toFixed(1)}%</value>
                  </div>

                  <div className='metric'>
                    <label>Efficiency</label>
                    <value>{territory.efficiency.toFixed(1)}%</value>
                  </div>
                </div>

                <div className='territory-actions'>
                  <button className='action-button primary'>Optimize Routes</button>
                  <button className='action-button secondary'>Generate Leads</button>
                  <button className='action-button secondary'>Export Data</button>
                </div>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
};

export default TerritoryMap;
