'use client';

import React, { useState, useEffect } from 'react';
import { MapPinIcon, TruckIcon, SignalIcon, WrenchScrewdriverIcon } from '@heroicons/react/24/outline';

interface MapLocation {
  id: string;
  latitude: number;
  longitude: number;
  type: 'work_order' | 'technician' | 'customer' | 'tower';
  title: string;
  subtitle?: string;
  status?: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  priority?: 'low' | 'medium' | 'high' | 'urgent';
  workOrderId?: string;
  customerId?: string;
}

const mockLocations: MapLocation[] = [
  {
    id: 'wo-1',
    latitude: 40.7128,
    longitude: -74.0060,
    type: 'work_order',
    title: 'Installation - 123 Main St',
    subtitle: 'Customer: John Doe',
    status: 'pending',
    priority: 'high',
    workOrderId: 'WO-2023-001',
    customerId: 'CUST-001'
  },
  {
    id: 'wo-2',
    latitude: 40.7589,
    longitude: -73.9851,
    type: 'work_order',
    title: 'Maintenance - 456 Oak Ave',
    subtitle: 'Customer: Jane Smith',
    status: 'in_progress',
    priority: 'medium',
    workOrderId: 'WO-2023-002',
    customerId: 'CUST-002'
  },
  {
    id: 'tech-1',
    latitude: 40.7505,
    longitude: -73.9934,
    type: 'technician',
    title: 'Your Location',
    subtitle: 'Technician ID: TECH-001'
  },
  {
    id: 'tower-1',
    latitude: 40.7282,
    longitude: -74.0776,
    type: 'tower',
    title: 'Cell Tower - Manhattan West',
    subtitle: 'Signal Strength: -65 dBm'
  }
];

export const TechnicianMap: React.FC = () => {
  const [locations, setLocations] = useState<MapLocation[]>(mockLocations);
  const [selectedLocation, setSelectedLocation] = useState<MapLocation | null>(null);
  const [mapCenter, setMapCenter] = useState({ lat: 40.7128, lng: -74.0060 });
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    workOrders: true,
    customers: true,
    towers: true,
    status: 'all',
    priority: 'all'
  });

  // Get current location
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          setMapCenter({ lat: latitude, lng: longitude });
          
          // Update technician location
          setLocations(prev => prev.map(loc => 
            loc.type === 'technician' 
              ? { ...loc, latitude, longitude }
              : loc
          ));
        },
        (error) => {
          console.warn('Geolocation error:', error);
        }
      );
    }
  }, []);

  const getLocationIcon = (location: MapLocation) => {
    switch (location.type) {
      case 'work_order':
        return <WrenchScrewdriverIcon className="w-5 h-5" />;
      case 'technician':
        return <TruckIcon className="w-5 h-5" />;
      case 'tower':
        return <SignalIcon className="w-5 h-5" />;
      default:
        return <MapPinIcon className="w-5 h-5" />;
    }
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'pending': return 'bg-yellow-500';
      case 'in_progress': return 'bg-blue-500';
      case 'completed': return 'bg-green-500';
      case 'cancelled': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getPriorityColor = (priority?: string) => {
    switch (priority) {
      case 'urgent': return 'border-red-500 bg-red-50';
      case 'high': return 'border-orange-500 bg-orange-50';
      case 'medium': return 'border-yellow-500 bg-yellow-50';
      case 'low': return 'border-green-500 bg-green-50';
      default: return 'border-gray-300 bg-white';
    }
  };

  const handleLocationClick = (location: MapLocation) => {
    setSelectedLocation(location);
    setMapCenter({ lat: location.latitude, lng: location.longitude });
  };

  const handleNavigateToLocation = (location: MapLocation) => {
    const url = `https://maps.google.com/?q=${location.latitude},${location.longitude}`;
    window.open(url, '_blank');
  };

  const filteredLocations = locations.filter(location => {
    if (!filters.workOrders && location.type === 'work_order') return false;
    if (!filters.customers && location.type === 'customer') return false;
    if (!filters.towers && location.type === 'tower') return false;
    
    if (filters.status !== 'all' && location.status !== filters.status) return false;
    if (filters.priority !== 'all' && location.priority !== filters.priority) return false;
    
    return true;
  });

  return (
    <div className="technician-map h-full flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Service Map</h1>
            <p className="text-gray-600">{filteredLocations.length} locations shown</p>
          </div>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`
                px-4 py-2 text-sm font-medium rounded-md border
                ${showFilters 
                  ? 'bg-blue-50 text-blue-700 border-blue-200' 
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                }
              `}
            >
              Filters
            </button>
            
            <button
              onClick={() => {
                if (navigator.geolocation) {
                  navigator.geolocation.getCurrentPosition(
                    (position) => {
                      setMapCenter({ 
                        lat: position.coords.latitude, 
                        lng: position.coords.longitude 
                      });
                    }
                  );
                }
              }}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
            >
              My Location
            </button>
          </div>
        </div>

        {/* Filters */}
        {showFilters && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {/* Show/Hide Options */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Show</label>
                <div className="space-y-2">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={filters.workOrders}
                      onChange={(e) => setFilters({...filters, workOrders: e.target.checked})}
                      className="h-4 w-4 text-blue-600 rounded border-gray-300"
                    />
                    <span className="ml-2 text-sm text-gray-700">Work Orders</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={filters.customers}
                      onChange={(e) => setFilters({...filters, customers: e.target.checked})}
                      className="h-4 w-4 text-blue-600 rounded border-gray-300"
                    />
                    <span className="ml-2 text-sm text-gray-700">Customers</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={filters.towers}
                      onChange={(e) => setFilters({...filters, towers: e.target.checked})}
                      className="h-4 w-4 text-blue-600 rounded border-gray-300"
                    />
                    <span className="ml-2 text-sm text-gray-700">Towers</span>
                  </label>
                </div>
              </div>

              {/* Status Filter */}
              <div>
                <label htmlFor="status-filter" className="block text-sm font-medium text-gray-700 mb-2">
                  Status
                </label>
                <select
                  id="status-filter"
                  value={filters.status}
                  onChange={(e) => setFilters({...filters, status: e.target.value})}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md"
                >
                  <option value="all">All Status</option>
                  <option value="pending">Pending</option>
                  <option value="in_progress">In Progress</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>

              {/* Priority Filter */}
              <div>
                <label htmlFor="priority-filter" className="block text-sm font-medium text-gray-700 mb-2">
                  Priority
                </label>
                <select
                  id="priority-filter"
                  value={filters.priority}
                  onChange={(e) => setFilters({...filters, priority: e.target.value})}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md"
                >
                  <option value="all">All Priorities</option>
                  <option value="urgent">Urgent</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Map Container */}
      <div className="flex-1 flex">
        {/* Map Placeholder */}
        <div className="flex-1 bg-gray-100 relative">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <MapPinIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-600 mb-2">Interactive Map</h3>
              <p className="text-gray-500 mb-4">
                Map integration placeholder<br />
                Showing {filteredLocations.length} locations
              </p>
              <div className="text-sm text-gray-500">
                Center: {mapCenter.lat.toFixed(4)}, {mapCenter.lng.toFixed(4)}
              </div>
            </div>
          </div>

          {/* Map Markers Simulation */}
          <div className="absolute top-4 left-4 space-y-2">
            {filteredLocations.slice(0, 3).map((location) => (
              <div
                key={location.id}
                onClick={() => handleLocationClick(location)}
                className={`
                  p-2 rounded-lg border-2 cursor-pointer transition-all
                  ${selectedLocation?.id === location.id 
                    ? 'bg-blue-100 border-blue-500 shadow-lg' 
                    : getPriorityColor(location.priority)
                  }
                `}
              >
                <div className="flex items-center space-x-2">
                  <div className={`p-1 rounded-full text-white ${getStatusColor(location.status)}`}>
                    {getLocationIcon(location)}
                  </div>
                  <div>
                    <div className="font-medium text-sm">{location.title}</div>
                    {location.subtitle && (
                      <div className="text-xs text-gray-600">{location.subtitle}</div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Location Details Sidebar */}
        <div className="w-80 bg-white border-l border-gray-200 overflow-y-auto">
          <div className="p-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Locations</h3>
            
            <div className="space-y-3">
              {filteredLocations.map((location) => (
                <div
                  key={location.id}
                  onClick={() => handleLocationClick(location)}
                  className={`
                    p-3 rounded-lg border cursor-pointer transition-all hover:shadow-md
                    ${selectedLocation?.id === location.id 
                      ? 'border-blue-500 bg-blue-50' 
                      : 'border-gray-200 hover:border-gray-300'
                    }
                  `}
                >
                  <div className="flex items-start space-x-3">
                    <div className={`p-2 rounded-full text-white ${getStatusColor(location.status)}`}>
                      {getLocationIcon(location)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium text-gray-900 truncate">
                          {location.title}
                        </h4>
                        {location.priority && (
                          <span className={`
                            px-2 py-1 text-xs font-medium rounded capitalize
                            ${location.priority === 'urgent' ? 'bg-red-100 text-red-800' :
                              location.priority === 'high' ? 'bg-orange-100 text-orange-800' :
                              location.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-green-100 text-green-800'
                            }
                          `}>
                            {location.priority}
                          </span>
                        )}
                      </div>
                      
                      {location.subtitle && (
                        <p className="text-sm text-gray-600 mt-1">{location.subtitle}</p>
                      )}
                      
                      {location.status && (
                        <div className="flex items-center mt-2">
                          <span className={`
                            inline-flex items-center px-2 py-1 text-xs font-medium rounded capitalize
                            ${location.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                              location.status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
                              location.status === 'completed' ? 'bg-green-100 text-green-800' :
                              'bg-red-100 text-red-800'
                            }
                          `}>
                            {location.status.replace('_', ' ')}
                          </span>
                        </div>
                      )}
                      
                      <div className="mt-3 flex space-x-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleNavigateToLocation(location);
                          }}
                          className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                        >
                          Navigate
                        </button>
                        
                        {location.workOrderId && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              // Navigate to work order details
                            }}
                            className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                          >
                            View Details
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};