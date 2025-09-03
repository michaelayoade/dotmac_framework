import React, { useState, useMemo } from 'react';
import { Button, Input, Card } from '@dotmac/primitives';
import {
  Search,
  Filter,
  RefreshCw,
  Power,
  PowerOff,
  RotateCw,
  Settings,
  AlertCircle,
} from 'lucide-react';
import { usePlugins } from '../hooks';
import { PluginCard } from './PluginCard';
import type { PluginManagerProps, PluginStatus } from '../types';

export const PluginManager: React.FC<PluginManagerProps> = ({
  domain,
  allowBulkOperations = true,
  showAdvancedFeatures = true,
  refreshInterval = 30000,
}) => {
  const {
    plugins,
    loading,
    error,
    enablePlugin,
    disablePlugin,
    restartPlugin,
    enableMultiplePlugins,
    disableMultiplePlugins,
    refreshPlugins,
    findPlugins,
    getAvailableDomains,
  } = usePlugins();

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<PluginStatus | 'all'>('all');
  const [domainFilter, setDomainFilter] = useState<string>(domain || 'all');
  const [selectedPlugins, setSelectedPlugins] = useState<Set<string>>(new Set());
  const [showFilters, setShowFilters] = useState(false);

  // Filter plugins based on current filters
  const filteredPlugins = useMemo(() => {
    return findPlugins({
      domain: domainFilter === 'all' ? undefined : domainFilter,
      status: statusFilter === 'all' ? undefined : statusFilter,
      name_pattern: searchQuery || undefined,
    });
  }, [findPlugins, domainFilter, statusFilter, searchQuery]);

  const availableDomains = getAvailableDomains();

  const handlePluginSelect = (pluginKey: string, selected: boolean) => {
    const newSelection = new Set(selectedPlugins);
    if (selected) {
      newSelection.add(pluginKey);
    } else {
      newSelection.delete(pluginKey);
    }
    setSelectedPlugins(newSelection);
  };

  const handleSelectAll = () => {
    if (selectedPlugins.size === filteredPlugins.length) {
      setSelectedPlugins(new Set());
    } else {
      const allKeys = filteredPlugins.map((p) => `${p.metadata.domain}.${p.metadata.name}`);
      setSelectedPlugins(new Set(allKeys));
    }
  };

  const handleBulkEnable = async () => {
    if (selectedPlugins.size === 0) return;

    try {
      await enableMultiplePlugins(Array.from(selectedPlugins));
      setSelectedPlugins(new Set());
    } catch (err) {
      console.error('Bulk enable failed:', err);
    }
  };

  const handleBulkDisable = async () => {
    if (selectedPlugins.size === 0) return;

    try {
      await disableMultiplePlugins(Array.from(selectedPlugins));
      setSelectedPlugins(new Set());
    } catch (err) {
      console.error('Bulk disable failed:', err);
    }
  };

  const getStatusBadgeClass = (status: PluginStatus) => {
    const baseClass = 'px-2 py-1 text-xs font-medium rounded-full';

    switch (status) {
      case 'active':
        return `${baseClass} bg-green-100 text-green-800`;
      case 'inactive':
        return `${baseClass} bg-gray-100 text-gray-800`;
      case 'error':
        return `${baseClass} bg-red-100 text-red-800`;
      case 'initializing':
      case 'updating':
        return `${baseClass} bg-yellow-100 text-yellow-800`;
      case 'disabled':
        return `${baseClass} bg-gray-100 text-gray-600`;
      default:
        return `${baseClass} bg-gray-100 text-gray-800`;
    }
  };

  if (error) {
    return (
      <Card className='border-red-200 bg-red-50 p-4'>
        <div className='flex items-center gap-2'>
          <AlertCircle className='h-5 w-5 text-red-600' />
          <div>
            <h3 className='font-semibold text-red-800'>Plugin Manager Error</h3>
            <p className='text-red-600'>{error}</p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <div className='plugin-manager space-y-6'>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h2 className='text-xl font-bold'>Plugin Manager</h2>
          <p className='text-gray-600'>
            {filteredPlugins.length} of {plugins.length} plugins
            {domainFilter !== 'all' && ` in ${domainFilter}`}
          </p>
        </div>

        <div className='flex items-center gap-2'>
          <Button variant='outline' size='sm' onClick={refreshPlugins} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>

          {showAdvancedFeatures && (
            <Button variant='outline' size='sm' onClick={() => setShowFilters(!showFilters)}>
              <Filter className='h-4 w-4' />
              Filters
            </Button>
          )}
        </div>
      </div>

      {/* Search and Filters */}
      <div className='space-y-4'>
        <div className='flex gap-4'>
          <div className='flex-1'>
            <Input
              placeholder='Search plugins...'
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className='pl-10'
            />
            <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400' />
          </div>
        </div>

        {showFilters && (
          <Card className='p-4'>
            <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
              <div>
                <label className='block text-sm font-medium mb-2'>Domain</label>
                <select
                  value={domainFilter}
                  onChange={(e) => setDomainFilter(e.target.value)}
                  className='w-full p-2 border border-gray-300 rounded-md'
                >
                  <option value='all'>All Domains</option>
                  {availableDomains.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className='block text-sm font-medium mb-2'>Status</label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as PluginStatus | 'all')}
                  className='w-full p-2 border border-gray-300 rounded-md'
                >
                  <option value='all'>All Status</option>
                  <option value='active'>Active</option>
                  <option value='inactive'>Inactive</option>
                  <option value='error'>Error</option>
                  <option value='disabled'>Disabled</option>
                </select>
              </div>

              <div className='flex items-end'>
                <Button
                  variant='outline'
                  onClick={() => {
                    setSearchQuery('');
                    setStatusFilter('all');
                    setDomainFilter('all');
                  }}
                >
                  Clear Filters
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* Bulk Operations */}
        {allowBulkOperations && filteredPlugins.length > 0 && (
          <Card className='p-4'>
            <div className='flex items-center justify-between'>
              <div className='flex items-center gap-4'>
                <label className='flex items-center'>
                  <input
                    type='checkbox'
                    checked={
                      selectedPlugins.size === filteredPlugins.length && filteredPlugins.length > 0
                    }
                    onChange={handleSelectAll}
                    className='mr-2'
                  />
                  Select All ({selectedPlugins.size} selected)
                </label>
              </div>

              {selectedPlugins.size > 0 && (
                <div className='flex items-center gap-2'>
                  <Button variant='outline' size='sm' onClick={handleBulkEnable}>
                    <Power className='h-4 w-4' />
                    Enable Selected
                  </Button>
                  <Button variant='outline' size='sm' onClick={handleBulkDisable}>
                    <PowerOff className='h-4 w-4' />
                    Disable Selected
                  </Button>
                </div>
              )}
            </div>
          </Card>
        )}
      </div>

      {/* Plugin List */}
      {loading ? (
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className='animate-pulse'>
              <Card className='h-48 bg-gray-200'></Card>
            </div>
          ))}
        </div>
      ) : filteredPlugins.length > 0 ? (
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
          {filteredPlugins.map((plugin) => {
            const pluginKey = `${plugin.metadata.domain}.${plugin.metadata.name}`;

            return (
              <PluginCard
                key={pluginKey}
                plugin={plugin}
                showActions={true}
                showHealth={true}
                selected={allowBulkOperations ? selectedPlugins.has(pluginKey) : undefined}
                onSelect={
                  allowBulkOperations
                    ? (selected) => handlePluginSelect(pluginKey, selected)
                    : undefined
                }
                onEnable={async () => await enablePlugin(pluginKey)}
                onDisable={async () => await disablePlugin(pluginKey)}
                onRestart={async () => await restartPlugin(pluginKey)}
                onConfigure={(key) => console.log('Configure', key)}
              />
            );
          })}
        </div>
      ) : (
        <Card className='p-8 text-center'>
          <div className='text-gray-400 mb-4'>
            <Settings className='h-12 w-12 mx-auto' />
          </div>
          <h3 className='text-lg font-medium text-gray-600 mb-2'>No plugins found</h3>
          <p className='text-gray-500'>
            {searchQuery || statusFilter !== 'all' || domainFilter !== 'all'
              ? 'Try adjusting your search filters'
              : 'No plugins are currently available'}
          </p>
        </Card>
      )}
    </div>
  );
};
