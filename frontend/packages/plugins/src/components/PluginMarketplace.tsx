import React, { useState, useMemo } from 'react';
import { Button, Input, Card } from '@dotmac/primitives';
import {
  Search,
  Filter,
  Download,
  Star,
  Users,
  Clock,
  CheckCircle,
  AlertCircle,
  Tag
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { usePluginMarketplace } from '../hooks';
import type { PluginMarketplaceProps, PluginMarketplaceItem } from '../types';

export const PluginMarketplace: React.FC<PluginMarketplaceProps> = ({
  defaultCategory = 'all',
  showInstalledOnly = false,
  showFilters = true,
  allowInstallation = true
}) => {
  const {
    items,
    loading,
    error,
    searchPlugins,
    filterByCategory,
    filterByTag,
    clearFilters,
    installFromMarketplace,
    getCategories,
    getPopularTags,
    refreshMarketplace
  } = usePluginMarketplace();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState(defaultCategory);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [showFiltersPanel, setShowFiltersPanel] = useState(false);
  const [installingPlugins, setInstallingPlugins] = useState<Set<string>>(new Set());

  const categories = getCategories();
  const popularTags = getPopularTags();

  // Filter items based on current state
  const filteredItems = useMemo(() => {
    let filtered = items;

    if (showInstalledOnly) {
      filtered = filtered.filter(item => item.installed);
    }

    if (selectedCategory !== 'all') {
      filtered = filtered.filter(item => item.category === selectedCategory);
    }

    if (selectedTags.length > 0) {
      filtered = filtered.filter(item =>
        selectedTags.some(tag => item.tags.includes(tag))
      );
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(item =>
        item.name.toLowerCase().includes(query) ||
        item.display_name.toLowerCase().includes(query) ||
        item.description.toLowerCase().includes(query) ||
        item.author.toLowerCase().includes(query) ||
        item.tags.some(tag => tag.toLowerCase().includes(query))
      );
    }

    return filtered;
  }, [items, showInstalledOnly, selectedCategory, selectedTags, searchQuery]);

  const handleSearch = async (query: string) => {
    setSearchQuery(query);
    if (query.trim()) {
      await searchPlugins(query, {
        category: selectedCategory === 'all' ? undefined : selectedCategory,
        tags: selectedTags.length > 0 ? selectedTags : undefined
      });
    }
  };

  const handleCategoryChange = (category: string) => {
    setSelectedCategory(category);
    if (category !== 'all') {
      filterByCategory(category);
    }
  };

  const handleTagToggle = (tag: string) => {
    const newTags = selectedTags.includes(tag)
      ? selectedTags.filter(t => t !== tag)
      : [...selectedTags, tag];

    setSelectedTags(newTags);
    if (newTags.length > 0) {
      newTags.forEach(t => filterByTag(t));
    }
  };

  const handleInstall = async (item: PluginMarketplaceItem) => {
    if (installingPlugins.has(item.id)) return;

    try {
      setInstallingPlugins(prev => new Set([...prev, item.id]));
      await installFromMarketplace(item);
    } catch (err) {
      console.error('Installation failed:', err);
    } finally {
      setInstallingPlugins(prev => {
        const newSet = new Set(prev);
        newSet.delete(item.id);
        return newSet;
      });
    }
  };

  const handleClearFilters = () => {
    setSearchQuery('');
    setSelectedCategory('all');
    setSelectedTags([]);
    clearFilters();
  };

  const getPricingDisplay = (item: PluginMarketplaceItem) => {
    switch (item.pricing_model) {
      case 'free':
        return <span className="text-green-600 font-medium">Free</span>;
      case 'paid':
        return <span className="text-blue-600 font-medium">${item.price}</span>;
      case 'freemium':
        return <span className="text-purple-600 font-medium">Freemium</span>;
      default:
        return <span className="text-gray-600">Unknown</span>;
    }
  };

  const getCompatibilityBadge = (item: PluginMarketplaceItem) => {
    if (item.compatible) {
      return (
        <div className="flex items-center gap-1 text-green-600">
          <CheckCircle className="h-3 w-3" />
          <span className="text-xs">Compatible</span>
        </div>
      );
    } else {
      return (
        <div className="flex items-center gap-1 text-red-600">
          <AlertCircle className="h-3 w-3" />
          <span className="text-xs">Incompatible</span>
        </div>
      );
    }
  };

  if (error) {
    return (
      <Card className="border-red-200 bg-red-50 p-4">
        <div className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-red-600" />
          <div>
            <h3 className="font-semibold text-red-800">Marketplace Error</h3>
            <p className="text-red-600">{error}</p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <div className="plugin-marketplace space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Plugin Marketplace</h2>
          <p className="text-gray-600">
            Discover and install plugins to extend your system
          </p>
        </div>

        <Button
          variant="outline"
          onClick={refreshMarketplace}
          disabled={loading}
        >
          Refresh
        </Button>
      </div>

      {/* Search and Filters */}
      <div className="space-y-4">
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search plugins..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-10"
            />
          </div>

          {showFilters && (
            <Button
              variant="outline"
              onClick={() => setShowFiltersPanel(!showFiltersPanel)}
            >
              <Filter className="h-4 w-4" />
              Filters
            </Button>
          )}
        </div>

        {showFiltersPanel && (
          <Card className="p-4">
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Category</label>
                  <select
                    value={selectedCategory}
                    onChange={(e) => handleCategoryChange(e.target.value)}
                    className="w-full p-2 border border-gray-300 rounded-md"
                  >
                    <option value="all">All Categories</option>
                    {categories.map(category => (
                      <option key={category} value={category}>{category}</option>
                    ))}
                  </select>
                </div>

                <div className="flex items-end">
                  <Button variant="outline" onClick={handleClearFilters}>
                    Clear Filters
                  </Button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Popular Tags</label>
                <div className="flex flex-wrap gap-2">
                  {popularTags.slice(0, 12).map(tag => (
                    <button
                      key={tag}
                      onClick={() => handleTagToggle(tag)}
                      className={`px-3 py-1 text-sm rounded-full border transition-colors ${
                        selectedTags.includes(tag)
                          ? 'bg-blue-100 border-blue-300 text-blue-800'
                          : 'bg-gray-50 border-gray-300 text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      <Tag className="h-3 w-3 inline mr-1" />
                      {tag}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </Card>
        )}
      </div>

      {/* Results Summary */}
      <div className="flex items-center justify-between text-sm text-gray-600">
        <span>{filteredItems.length} plugins found</span>
        {(selectedCategory !== 'all' || selectedTags.length > 0 || searchQuery) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearFilters}
            className="text-blue-600"
          >
            Clear all filters
          </Button>
        )}
      </div>

      {/* Plugin Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} className="animate-pulse">
              <Card className="h-80 bg-gray-200"></Card>
            </div>
          ))}
        </div>
      ) : filteredItems.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredItems.map((item) => (
            <Card key={item.id} className="overflow-hidden">
              {/* Header */}
              <div className="p-4 border-b border-gray-100">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-gray-900 truncate">{item.display_name}</h3>
                  {item.installed && (
                    <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0 ml-2" />
                  )}
                </div>

                <p className="text-sm text-gray-600 line-clamp-2 mb-3">
                  {item.description}
                </p>

                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>by {item.author}</span>
                  <span>v{item.version}</span>
                </div>
              </div>

              {/* Metrics */}
              <div className="px-4 py-3 bg-gray-50">
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center gap-1">
                    <Star className="h-3 w-3 text-yellow-500" />
                    <span className="text-sm font-medium">{item.rating.toFixed(1)}</span>
                  </div>

                  <div className="flex items-center gap-1">
                    <Users className="h-3 w-3 text-gray-400" />
                    <span className="text-sm">{item.download_count.toLocaleString()}</span>
                  </div>

                  <div className="col-span-2 flex items-center gap-1">
                    <Clock className="h-3 w-3 text-gray-400" />
                    <span className="text-xs text-gray-500">
                      Updated {formatDistanceToNow(new Date(item.last_updated), { addSuffix: true })}
                    </span>
                  </div>
                </div>
              </div>

              {/* Tags */}
              <div className="px-4 py-2">
                <div className="flex flex-wrap gap-1">
                  {item.tags.slice(0, 3).map(tag => (
                    <span key={tag} className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">
                      {tag}
                    </span>
                  ))}
                  {item.tags.length > 3 && (
                    <span className="px-2 py-1 text-xs bg-gray-100 text-gray-500 rounded">
                      +{item.tags.length - 3}
                    </span>
                  )}
                </div>
              </div>

              {/* Footer */}
              <div className="p-4 border-t border-gray-100">
                <div className="flex items-center justify-between mb-3">
                  {getPricingDisplay(item)}
                  {getCompatibilityBadge(item)}
                </div>

                {allowInstallation && (
                  <div className="space-y-2">
                    {item.installed ? (
                      <div className="flex gap-2">
                        <Button size="sm" className="flex-1" disabled>
                          <CheckCircle className="h-3 w-3" />
                          Installed
                        </Button>
                        {item.update_available && (
                          <Button size="sm" variant="outline">
                            Update
                          </Button>
                        )}
                      </div>
                    ) : (
                      <Button
                        size="sm"
                        className="w-full"
                        onClick={() => handleInstall(item)}
                        disabled={!item.compatible || installingPlugins.has(item.id)}
                      >
                        {installingPlugins.has(item.id) ? (
                          <>Installing...</>
                        ) : (
                          <>
                            <Download className="h-3 w-3" />
                            Install
                          </>
                        )}
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="p-8 text-center">
          <div className="text-gray-400 mb-4">
            <Search className="h-12 w-12 mx-auto" />
          </div>
          <h3 className="text-lg font-medium text-gray-600 mb-2">No plugins found</h3>
          <p className="text-gray-500">
            Try adjusting your search terms or filters to find more plugins
          </p>
        </Card>
      )}
    </div>
  );
};
