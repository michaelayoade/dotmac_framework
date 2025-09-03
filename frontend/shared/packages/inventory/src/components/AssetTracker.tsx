import React, { useState, useEffect } from 'react';
import { Card } from '@dotmac/ui/Card';
import { Button } from '@dotmac/ui/Button';
import { Input } from '@dotmac/ui/Input';
import { Badge } from '@dotmac/ui/Badge';
import {
  Search,
  MapPin,
  User,
  Calendar,
  AlertCircle,
  CheckCircle,
  Clock,
  Package,
} from 'lucide-react';
import { useAssetTracking } from '../hooks';
import type { AssetDetails, ItemStatus } from '../types';
import clsx from 'clsx';

interface AssetTrackerProps {
  className?: string;
  defaultView?: 'list' | 'map' | 'grid';
  showFilters?: boolean;
}

export function AssetTracker({
  className,
  defaultView = 'list',
  showFilters = true,
}: AssetTrackerProps) {
  const {
    assets,
    loading,
    error,
    searchAssetsBySerial,
    getAssetsByLocation,
    getAssetsByTechnician,
    getMaintenanceDue,
  } = useAssetTracking();

  const [view, setView] = useState(defaultView);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAsset, setSelectedAsset] = useState<AssetDetails | null>(null);
  const [filteredAssets, setFilteredAssets] = useState<AssetDetails[]>(assets);
  const [filters, setFilters] = useState({
    status: 'all' as ItemStatus | 'all',
    location: 'all',
    technician: 'all',
    maintenanceStatus: 'all',
  });

  useEffect(() => {
    let filtered = assets;

    // Apply search filter
    if (searchQuery) {
      filtered = filtered.filter(
        (asset) =>
          asset.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          asset.item_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
          asset.serial_number?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          asset.manufacturer?.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Apply status filter
    if (filters.status !== 'all') {
      filtered = filtered.filter((asset) => asset.current_status === filters.status);
    }

    // Apply location filter
    if (filters.location !== 'all') {
      filtered = filtered.filter(
        (asset) => asset.current_location?.warehouse_id === filters.location
      );
    }

    // Apply technician filter
    if (filters.technician !== 'all') {
      filtered = filtered.filter(
        (asset) => asset.assigned_to?.technician_id === filters.technician
      );
    }

    setFilteredAssets(filtered);
  }, [assets, searchQuery, filters]);

  const handleSearch = async () => {
    if (searchQuery.trim()) {
      const searchResults = await searchAssetsBySerial(searchQuery.trim());
      setFilteredAssets(searchResults);
    }
  };

  const getStatusColor = (status: ItemStatus): string => {
    const colors = {
      [ItemStatus.AVAILABLE]: 'green',
      [ItemStatus.IN_USE]: 'blue',
      [ItemStatus.ALLOCATED]: 'orange',
      [ItemStatus.IN_REPAIR]: 'red',
      [ItemStatus.RESERVED]: 'yellow',
      [ItemStatus.RETIRED]: 'gray',
      [ItemStatus.LOST]: 'red',
      [ItemStatus.QUARANTINED]: 'red',
    };
    return colors[status] || 'gray';
  };

  const getStatusIcon = (status: ItemStatus) => {
    const icons = {
      [ItemStatus.AVAILABLE]: CheckCircle,
      [ItemStatus.IN_USE]: Package,
      [ItemStatus.ALLOCATED]: Clock,
      [ItemStatus.IN_REPAIR]: AlertCircle,
      [ItemStatus.RESERVED]: Clock,
      [ItemStatus.RETIRED]: AlertCircle,
      [ItemStatus.LOST]: AlertCircle,
      [ItemStatus.QUARANTINED]: AlertCircle,
    };
    const Icon = icons[status] || AlertCircle;
    return <Icon className='h-4 w-4' />;
  };

  if (loading) {
    return (
      <div className={clsx('space-y-4', className)}>
        <Card className='p-6'>
          <div className='animate-pulse space-y-4'>
            <div className='h-8 bg-gray-200 rounded w-64'></div>
            <div className='h-10 bg-gray-200 rounded'></div>
            <div className='space-y-2'>
              {[1, 2, 3].map((i) => (
                <div key={i} className='h-16 bg-gray-200 rounded'></div>
              ))}
            </div>
          </div>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <Card className={clsx('p-6', className)}>
        <div className='text-center text-red-600'>
          <AlertCircle className='h-12 w-12 mx-auto mb-2' />
          <p>Failed to load asset tracking data</p>
          <p className='text-sm text-gray-500 mt-1'>{error}</p>
        </div>
      </Card>
    );
  }

  return (
    <div className={clsx('space-y-6', className)}>
      {/* Search and Filters */}
      <Card className='p-6'>
        <div className='flex flex-col lg:flex-row lg:items-center justify-between gap-4'>
          <div className='flex-1 max-w-md'>
            <div className='relative'>
              <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400' />
              <Input
                placeholder='Search by serial number, name, or code...'
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                className='pl-10'
              />
            </div>
          </div>

          <div className='flex items-center gap-3'>
            <Button onClick={handleSearch} size='sm'>
              Search
            </Button>
            {showFilters && (
              <div className='flex items-center gap-2'>
                <select
                  value={filters.status}
                  onChange={(e) =>
                    setFilters((prev) => ({
                      ...prev,
                      status: e.target.value as ItemStatus | 'all',
                    }))
                  }
                  className='text-sm border rounded px-2 py-1'
                >
                  <option value='all'>All Status</option>
                  <option value={ItemStatus.AVAILABLE}>Available</option>
                  <option value={ItemStatus.IN_USE}>In Use</option>
                  <option value={ItemStatus.ALLOCATED}>Allocated</option>
                  <option value={ItemStatus.IN_REPAIR}>In Repair</option>
                  <option value={ItemStatus.RESERVED}>Reserved</option>
                  <option value={ItemStatus.RETIRED}>Retired</option>
                </select>
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* Asset List */}
      <Card className='p-6'>
        <div className='flex items-center justify-between mb-6'>
          <h3 className='text-lg font-semibold text-gray-900'>Assets ({filteredAssets.length})</h3>
          <div className='flex items-center gap-2'>
            <Button
              variant={view === 'list' ? 'default' : 'outline'}
              size='sm'
              onClick={() => setView('list')}
            >
              List
            </Button>
            <Button
              variant={view === 'grid' ? 'default' : 'outline'}
              size='sm'
              onClick={() => setView('grid')}
            >
              Grid
            </Button>
          </div>
        </div>

        {filteredAssets.length === 0 ? (
          <div className='text-center py-12'>
            <Package className='h-12 w-12 text-gray-400 mx-auto mb-4' />
            <p className='text-gray-500'>No assets found</p>
          </div>
        ) : (
          <div
            className={clsx(
              view === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4' : 'space-y-3'
            )}
          >
            {filteredAssets.map((asset) => (
              <div
                key={asset.id}
                className={clsx(
                  'border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer',
                  selectedAsset?.id === asset.id && 'border-blue-500 bg-blue-50'
                )}
                onClick={() => setSelectedAsset(asset)}
              >
                <div className='flex items-start justify-between mb-3'>
                  <div className='flex-1 min-w-0'>
                    <h4 className='font-medium text-gray-900 truncate'>{asset.name}</h4>
                    <p className='text-sm text-gray-500'>{asset.item_code}</p>
                    {asset.serial_number && (
                      <p className='text-xs text-gray-400'>SN: {asset.serial_number}</p>
                    )}
                  </div>
                  <Badge
                    variant={getStatusColor(asset.current_status) as any}
                    className='flex items-center gap-1'
                  >
                    {getStatusIcon(asset.current_status)}
                    {asset.current_status.replace('_', ' ')}
                  </Badge>
                </div>

                <div className='space-y-2 text-sm'>
                  {asset.current_location && (
                    <div className='flex items-center text-gray-600'>
                      <MapPin className='h-4 w-4 mr-2' />
                      <span>{asset.current_location.warehouse_name}</span>
                      {asset.current_location.bin_location && (
                        <span className='text-gray-400 ml-1'>
                          - {asset.current_location.bin_location}
                        </span>
                      )}
                    </div>
                  )}

                  {asset.assigned_to && (
                    <div className='flex items-center text-gray-600'>
                      <User className='h-4 w-4 mr-2' />
                      <span>{asset.assigned_to.technician_name}</span>
                    </div>
                  )}

                  {asset.customer_deployment && (
                    <div className='flex items-center text-gray-600'>
                      <Package className='h-4 w-4 mr-2' />
                      <span className='truncate'>{asset.customer_deployment.customer_name}</span>
                    </div>
                  )}

                  {asset.next_maintenance_due && (
                    <div className='flex items-center text-orange-600'>
                      <Calendar className='h-4 w-4 mr-2' />
                      <span>
                        Maintenance: {new Date(asset.next_maintenance_due).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Asset Details Modal/Panel */}
      {selectedAsset && (
        <Card className='p-6'>
          <div className='flex items-center justify-between mb-4'>
            <h3 className='text-lg font-semibold text-gray-900'>Asset Details</h3>
            <Button variant='ghost' size='sm' onClick={() => setSelectedAsset(null)}>
              Close
            </Button>
          </div>

          <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
            <div className='space-y-4'>
              <div>
                <label className='text-sm font-medium text-gray-600'>Name</label>
                <p className='text-gray-900'>{selectedAsset.name}</p>
              </div>
              <div>
                <label className='text-sm font-medium text-gray-600'>Item Code</label>
                <p className='text-gray-900'>{selectedAsset.item_code}</p>
              </div>
              <div>
                <label className='text-sm font-medium text-gray-600'>Manufacturer</label>
                <p className='text-gray-900'>{selectedAsset.manufacturer || 'N/A'}</p>
              </div>
              <div>
                <label className='text-sm font-medium text-gray-600'>Model</label>
                <p className='text-gray-900'>{selectedAsset.model || 'N/A'}</p>
              </div>
            </div>

            <div className='space-y-4'>
              <div>
                <label className='text-sm font-medium text-gray-600'>Status</label>
                <div className='flex items-center gap-2 mt-1'>
                  <Badge variant={getStatusColor(selectedAsset.current_status) as any}>
                    {selectedAsset.current_status.replace('_', ' ')}
                  </Badge>
                </div>
              </div>
              <div>
                <label className='text-sm font-medium text-gray-600'>Location</label>
                <p className='text-gray-900'>
                  {selectedAsset.current_location?.warehouse_name || 'Unknown'}
                </p>
              </div>
              <div>
                <label className='text-sm font-medium text-gray-600'>Serial Number</label>
                <p className='text-gray-900'>{selectedAsset.serial_number || 'N/A'}</p>
              </div>
              {selectedAsset.warranty_expiry && (
                <div>
                  <label className='text-sm font-medium text-gray-600'>Warranty Expiry</label>
                  <p className='text-gray-900'>
                    {new Date(selectedAsset.warranty_expiry).toLocaleDateString()}
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className='mt-6 flex gap-3'>
            <Button size='sm'>Track Movement</Button>
            <Button variant='outline' size='sm'>
              View History
            </Button>
            <Button variant='outline' size='sm'>
              Schedule Maintenance
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
