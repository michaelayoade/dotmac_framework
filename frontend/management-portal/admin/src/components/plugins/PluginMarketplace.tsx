/**
 * Plugin Marketplace Component
 * Following DRY patterns from existing components
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  StarIcon,
  CloudArrowDownIcon,
  CheckBadgeIcon,
  ExclamationTriangleIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';
import { StarIcon as StarSolidIcon } from '@heroicons/react/24/solid';
import { Button, IconButton } from '@dotmac/primitives';
import { Modal } from '../ui/Modal';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { useApiClient, useToast } from '@dotmac/headless';
import type {
  PluginCatalogItem,
  PluginMarketplaceFilters,
  PluginInstallationRequest,
} from '@dotmac/headless';

interface PluginMarketplaceProps {
  className?: string;
}

export function PluginMarketplace({ className = '' }: PluginMarketplaceProps) {
  const apiClient = useApiClient();
  const { success, error: showError } = useToast();
  const [plugins, setPlugins] = useState<PluginCatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPlugin, setSelectedPlugin] = useState<PluginCatalogItem | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [installing, setInstalling] = useState<string | null>(null);

  // Filters and search state
  const [filters, setFilters] = useState<PluginMarketplaceFilters>({
    search: '',
    category: [],
    license_type: [],
    verified_only: false,
    min_rating: 0,
    sort_by: 'downloads',
    sort_order: 'desc',
  });

  const loadPlugins = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.getPluginCatalog(filters, { limit: 24 });
      setPlugins(response.data);
    } catch (err) {
      setError('Failed to load plugins');
      console.error('Plugin catalog error:', err);
    } finally {
      setLoading(false);
    }
  }, [apiClient, filters]);

  useEffect(() => {
    loadPlugins();
  }, [loadPlugins]);

  const handleInstallPlugin = async (plugin: PluginCatalogItem, licenseTier: string = 'trial') => {
    setInstalling(plugin.id);

    try {
      const request: PluginInstallationRequest = {
        plugin_id: plugin.id,
        license_tier: licenseTier as any,
        auto_enable: true,
      };

      const response = await apiClient.installPlugin(request);

      // Show success message
      success(
        'Plugin Installation Started',
        `Installation ID: ${response.data.installation_id}. You can monitor progress in the plugins dashboard.`,
        {
          duration: 7000,
          actions: [
            {
              label: 'View Progress',
              onClick: () => {
                // Navigate to plugin installation status
                window.location.href = `/plugins/installations/${response.data.installation_id}`;
              },
              variant: 'primary',
            },
          ],
        }
      );
    } catch (err) {
      showError(
        'Plugin Installation Failed',
        err instanceof Error
          ? err.message
          : 'An unexpected error occurred during plugin installation.',
        { duration: 8000 }
      );
      console.error('Installation error:', err);
    } finally {
      setInstalling(null);
    }
  };

  const updateFilters = (newFilters: Partial<PluginMarketplaceFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
  };

  const renderStars = (rating: number, reviews: number) => {
    const stars = [];
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;

    for (let i = 0; i < fullStars; i++) {
      stars.push(<StarSolidIcon key={i} className='h-4 w-4 text-yellow-400' />);
    }

    if (hasHalfStar) {
      stars.push(<StarIcon key='half' className='h-4 w-4 text-yellow-400' />);
    }

    const remainingStars = 5 - Math.ceil(rating);
    for (let i = 0; i < remainingStars; i++) {
      stars.push(<StarIcon key={`empty-${i}`} className='h-4 w-4 text-gray-300' />);
    }

    return (
      <div className='flex items-center space-x-1'>
        <div className='flex'>{stars}</div>
        <span className='text-sm text-gray-600'>({reviews})</span>
      </div>
    );
  };

  const getCategoryColor = (category: string) => {
    const colors = {
      billing: 'bg-green-100 text-green-800',
      networking: 'bg-blue-100 text-blue-800',
      analytics: 'bg-purple-100 text-purple-800',
      crm: 'bg-pink-100 text-pink-800',
      integration: 'bg-orange-100 text-orange-800',
      security: 'bg-red-100 text-red-800',
      other: 'bg-gray-100 text-gray-800',
    };
    return colors[category as keyof typeof colors] || colors.other;
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h1 className='text-2xl font-bold text-gray-900'>Plugin Marketplace</h1>
          <p className='mt-1 text-sm text-gray-500'>
            Extend your ISP platform with powerful plugins
          </p>
        </div>

        <Button
          variant='outline'
          leftIcon={FunnelIcon}
          onClick={() => setShowFilters(!showFilters)}
        >
          Filters
        </Button>
      </div>

      {/* Search and Sort */}
      <div className='flex flex-col sm:flex-row gap-4'>
        <div className='relative flex-1'>
          <MagnifyingGlassIcon className='absolute left-3 top-3 h-5 w-5 text-gray-400' />
          <input
            type='text'
            placeholder='Search plugins...'
            value={filters.search || ''}
            onChange={(e) => updateFilters({ search: e.target.value })}
            className='w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent'
          />
        </div>

        <select
          value={filters.sort_by}
          onChange={(e) => updateFilters({ sort_by: e.target.value as any })}
          className='px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent'
        >
          <option value='downloads'>Most Downloaded</option>
          <option value='rating'>Highest Rated</option>
          <option value='updated'>Recently Updated</option>
          <option value='name'>Name (A-Z)</option>
        </select>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className='bg-gray-50 p-4 rounded-lg border border-gray-200'>
          <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
            {/* Category Filter */}
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-2'>Category</label>
              <div className='space-y-2'>
                {['billing', 'networking', 'analytics', 'crm', 'integration', 'security'].map(
                  (category) => (
                    <label key={category} className='flex items-center'>
                      <input
                        type='checkbox'
                        checked={filters.category?.includes(category) || false}
                        onChange={(e) => {
                          const currentCategories = filters.category || [];
                          const newCategories = e.target.checked
                            ? [...currentCategories, category]
                            : currentCategories.filter((c) => c !== category);
                          updateFilters({ category: newCategories });
                        }}
                        className='mr-2 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded'
                      />
                      <span className='text-sm text-gray-600 capitalize'>{category}</span>
                    </label>
                  )
                )}
              </div>
            </div>

            {/* License Type Filter */}
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-2'>License Type</label>
              <div className='space-y-2'>
                {['free', 'freemium', 'paid'].map((type) => (
                  <label key={type} className='flex items-center'>
                    <input
                      type='checkbox'
                      checked={filters.license_type?.includes(type as any) || false}
                      onChange={(e) => {
                        const currentTypes = filters.license_type || [];
                        const newTypes = e.target.checked
                          ? [...currentTypes, type as any]
                          : currentTypes.filter((t) => t !== type);
                        updateFilters({ license_type: newTypes });
                      }}
                      className='mr-2 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded'
                    />
                    <span className='text-sm text-gray-600 capitalize'>{type}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Additional Filters */}
            <div className='space-y-4'>
              <label className='flex items-center'>
                <input
                  type='checkbox'
                  checked={filters.verified_only || false}
                  onChange={(e) => updateFilters({ verified_only: e.target.checked })}
                  className='mr-2 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded'
                />
                <span className='text-sm text-gray-600'>Verified only</span>
              </label>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-2'>
                  Minimum Rating
                </label>
                <input
                  type='range'
                  min='0'
                  max='5'
                  step='0.5'
                  value={filters.min_rating || 0}
                  onChange={(e) => updateFilters({ min_rating: parseFloat(e.target.value) })}
                  className='w-full'
                />
                <div className='text-sm text-gray-600'>{filters.min_rating} stars+</div>
              </div>
            </div>
          </div>

          <div className='mt-4 flex justify-end space-x-2'>
            <Button
              variant='outline'
              onClick={() =>
                setFilters({
                  search: '',
                  category: [],
                  license_type: [],
                  verified_only: false,
                  min_rating: 0,
                  sort_by: 'downloads',
                  sort_order: 'desc',
                })
              }
            >
              Clear All
            </Button>
            <Button onClick={() => setShowFilters(false)}>Apply Filters</Button>
          </div>
        </div>
      )}

      {/* Plugin Grid */}
      {loading ? (
        <div className='flex justify-center py-12'>
          <LoadingSpinner size='large' />
        </div>
      ) : error ? (
        <div className='text-center py-12'>
          <ExclamationTriangleIcon className='mx-auto h-12 w-12 text-red-400' />
          <h3 className='mt-2 text-sm font-medium text-gray-900'>Error loading plugins</h3>
          <p className='mt-1 text-sm text-gray-500'>{error}</p>
          <Button className='mt-4' onClick={loadPlugins}>
            Try Again
          </Button>
        </div>
      ) : plugins.length === 0 ? (
        <div className='text-center py-12'>
          <div className='text-gray-400 text-lg'>No plugins found matching your criteria</div>
        </div>
      ) : (
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'>
          {plugins.map((plugin) => (
            <div
              key={plugin.id}
              className='bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow'
            >
              {/* Plugin Icon/Screenshot */}
              <div className='aspect-video bg-gray-100 rounded-t-lg overflow-hidden'>
                {plugin.screenshots?.[0] ? (
                  <img
                    src={plugin.screenshots[0]}
                    alt={plugin.name}
                    className='w-full h-full object-cover'
                  />
                ) : (
                  <div className='flex items-center justify-center h-full text-gray-400'>
                    <CloudArrowDownIcon className='h-12 w-12' />
                  </div>
                )}
              </div>

              {/* Plugin Info */}
              <div className='p-4'>
                <div className='flex items-start justify-between mb-2'>
                  <h3 className='font-semibold text-gray-900 truncate flex-1'>{plugin.name}</h3>
                  <div className='flex items-center space-x-1 ml-2'>
                    {plugin.security.verified && (
                      <CheckBadgeIcon className='h-4 w-4 text-blue-500' title='Verified' />
                    )}
                    {plugin.security.signed && (
                      <ShieldCheckIcon className='h-4 w-4 text-green-500' title='Signed' />
                    )}
                  </div>
                </div>

                <p className='text-sm text-gray-600 mb-3 line-clamp-2'>{plugin.description}</p>

                {/* Category */}
                <div className='mb-2'>
                  <span
                    className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${getCategoryColor(plugin.category)}`}
                  >
                    {plugin.category}
                  </span>
                </div>

                {/* Rating and Downloads */}
                <div className='flex items-center justify-between mb-3'>
                  {renderStars(plugin.stats.rating, plugin.stats.reviews)}
                  <span className='text-xs text-gray-500'>
                    {plugin.stats.downloads.toLocaleString()} downloads
                  </span>
                </div>

                {/* Pricing */}
                <div className='mb-3'>
                  {plugin.pricing.type === 'free' ? (
                    <span className='text-sm font-medium text-green-600'>Free</span>
                  ) : plugin.pricing.type === 'freemium' ? (
                    <span className='text-sm font-medium text-blue-600'>Freemium</span>
                  ) : (
                    <span className='text-sm font-medium text-gray-900'>
                      From ${plugin.pricing.tiers?.[0]?.price || 'N/A'}/mo
                    </span>
                  )}
                </div>

                {/* Actions */}
                <div className='flex space-x-2'>
                  <Button size='sm' className='flex-1' onClick={() => setSelectedPlugin(plugin)}>
                    View Details
                  </Button>
                  <Button
                    size='sm'
                    variant='primary'
                    loading={installing === plugin.id}
                    onClick={() => handleInstallPlugin(plugin)}
                    disabled={installing !== null}
                  >
                    Install
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Plugin Details Modal */}
      {selectedPlugin && (
        <PluginDetailsModal
          plugin={selectedPlugin}
          onClose={() => setSelectedPlugin(null)}
          onInstall={(licenseTier) => handleInstallPlugin(selectedPlugin, licenseTier)}
          installing={installing === selectedPlugin.id}
        />
      )}
    </div>
  );
}

// Plugin Details Modal Component
interface PluginDetailsModalProps {
  plugin: PluginCatalogItem;
  onClose: () => void;
  onInstall: (licenseTier: string) => void;
  installing: boolean;
}

function PluginDetailsModal({ plugin, onClose, onInstall, installing }: PluginDetailsModalProps) {
  const [selectedTier, setSelectedTier] = useState(0);

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title={plugin.name}
      size='xl'
      className='max-h-[80vh] overflow-y-auto'
    >
      <div className='space-y-6'>
        {/* Plugin Header */}
        <div className='flex items-start space-x-4'>
          <div className='w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center'>
            {plugin.icon ? (
              <img src={plugin.icon} alt={plugin.name} className='w-12 h-12' />
            ) : (
              <CloudArrowDownIcon className='h-8 w-8 text-gray-400' />
            )}
          </div>

          <div className='flex-1'>
            <h2 className='text-xl font-bold text-gray-900'>{plugin.name}</h2>
            <p className='text-gray-600 mb-2'>{plugin.description}</p>
            <div className='flex items-center space-x-4 text-sm text-gray-500'>
              <span>by {plugin.author}</span>
              <span>v{plugin.version}</span>
              <span>{plugin.stats.downloads.toLocaleString()} downloads</span>
            </div>
          </div>
        </div>

        {/* Screenshots */}
        {plugin.screenshots && plugin.screenshots.length > 0 && (
          <div>
            <h3 className='font-medium text-gray-900 mb-3'>Screenshots</h3>
            <div className='grid grid-cols-2 gap-4'>
              {plugin.screenshots.slice(0, 4).map((screenshot, index) => (
                <img
                  key={index}
                  src={screenshot}
                  alt={`Screenshot ${index + 1}`}
                  className='w-full h-32 object-cover rounded border'
                />
              ))}
            </div>
          </div>
        )}

        {/* Pricing Tiers */}
        {plugin.pricing.tiers && plugin.pricing.tiers.length > 0 && (
          <div>
            <h3 className='font-medium text-gray-900 mb-3'>Pricing Plans</h3>
            <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
              {plugin.pricing.tiers.map((tier, index) => (
                <div
                  key={index}
                  className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                    selectedTier === index
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => setSelectedTier(index)}
                >
                  <h4 className='font-medium'>{tier.name}</h4>
                  <div className='text-2xl font-bold text-gray-900 my-2'>
                    ${tier.price}
                    <span className='text-sm font-normal text-gray-500'>/mo</span>
                  </div>
                  <ul className='text-sm text-gray-600 space-y-1'>
                    {tier.features.map((feature, fIndex) => (
                      <li key={fIndex} className='flex items-center'>
                        <CheckBadgeIcon className='h-4 w-4 text-green-500 mr-2' />
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Permissions */}
        <div>
          <h3 className='font-medium text-gray-900 mb-3'>Required Permissions</h3>
          <div className='grid grid-cols-1 md:grid-cols-2 gap-4 text-sm'>
            {Object.entries(plugin.permissions).map(
              ([category, perms]) =>
                perms.length > 0 && (
                  <div key={category} className='bg-gray-50 p-3 rounded'>
                    <h4 className='font-medium capitalize text-gray-900 mb-2'>{category}</h4>
                    <ul className='text-gray-600 space-y-1'>
                      {perms.map((perm, index) => (
                        <li key={index}>• {perm}</li>
                      ))}
                    </ul>
                  </div>
                )
            )}
          </div>
        </div>

        {/* Actions */}
        <div className='flex justify-end space-x-3 pt-4 border-t'>
          <Button variant='outline' onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant='primary'
            loading={installing}
            onClick={() => onInstall(plugin.pricing.tiers?.[selectedTier]?.name || 'trial')}
          >
            Install Plugin
          </Button>
        </div>
      </div>
    </Modal>
  );
}
