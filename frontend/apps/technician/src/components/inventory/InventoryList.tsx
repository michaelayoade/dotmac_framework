/**
 * Inventory List Component
 * Displays and manages inventory items for technicians
 */

'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Filter,
  Package,
  ScanLine,
  Plus,
  Minus,
  AlertTriangle,
  CheckCircle,
  Clock,
  MapPin,
  DollarSign,
  Barcode,
  Edit,
  Eye,
  TrendingDown,
  TrendingUp,
  Info,
} from 'lucide-react';
import { InventoryItem, offlineDB } from '../../lib/enhanced-offline-db';
import { InventoryScanner } from './InventoryScanner';
import { useAuth } from '../auth/TechnicianAuth';
import { sanitizeSearchTerm, sanitizeQuantity } from '../../lib/validation/sanitization';

interface InventoryListProps {
  onSelectItem?: (item: InventoryItem) => void;
  onRequestItem?: (item: InventoryItem, quantity: number) => void;
  onUpdateQuantity?: (item: InventoryItem, newQuantity: number) => void;
  workOrderMode?: boolean;
  selectedItems?: string[];
}

export function InventoryList({
  onSelectItem,
  onRequestItem,
  onUpdateQuantity,
  workOrderMode = false,
  selectedItems = [],
}: InventoryListProps) {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [filteredItems, setFilteredItems] = useState<InventoryItem[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [stockFilter, setStockFilter] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showScanner, setShowScanner] = useState(false);
  const [categories, setCategories] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState<'name' | 'quantity' | 'category' | 'location'>('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  
  const { authenticatedRequest } = useAuth();

  useEffect(() => {
    loadInventory();
  }, []);

  useEffect(() => {
    filterAndSortItems();
  }, [items, searchTerm, categoryFilter, stockFilter, sortBy, sortOrder]);

  const loadInventory = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load from local database first
      const localItems = await offlineDB.getInventory?.() || [];
      
      if (localItems.length > 0) {
        setItems(localItems);
        extractCategories(localItems);
        setLoading(false);
      }

      // Try to fetch latest from server if online
      if (navigator.onLine) {
        try {
          const response = await authenticatedRequest('/api/v1/field-ops/inventory');
          if (response.ok) {
            const serverItems = await response.json();
            setItems(serverItems);
            extractCategories(serverItems);
            
            // Update local database
            for (const item of serverItems) {
              await offlineDB.saveInventoryItem?.(item);
            }
          }
        } catch (networkError) {
          console.warn('Failed to fetch inventory from server, using local data');
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load inventory');
      console.error('Failed to load inventory:', err);
    } finally {
      setLoading(false);
    }
  };

  const extractCategories = (items: InventoryItem[]) => {
    const uniqueCategories = [...new Set(items.map(item => item.category))].sort();
    setCategories(uniqueCategories);
  };

  const filterAndSortItems = () => {
    let filtered = items;

    // Filter by category
    if (categoryFilter !== 'all') {
      filtered = filtered.filter(item => item.category === categoryFilter);
    }

    // Filter by stock level
    if (stockFilter !== 'all') {
      filtered = filtered.filter(item => {
        switch (stockFilter) {
          case 'low':
            return item.quantity <= item.minStock;
          case 'normal':
            return item.quantity > item.minStock && item.quantity < item.maxStock;
          case 'high':
            return item.quantity >= item.maxStock;
          case 'out':
            return item.quantity === 0;
          default:
            return true;
        }
      });
    }

    // Filter by search term
    if (searchTerm.trim()) {
      const sanitizedSearch = sanitizeSearchTerm(searchTerm.trim());
      const searchLower = sanitizedSearch.toLowerCase();
      
      filtered = filtered.filter(item =>
        item.name.toLowerCase().includes(searchLower) ||
        item.sku.toLowerCase().includes(searchLower) ||
        item.barcode?.toLowerCase().includes(searchLower) ||
        item.category.toLowerCase().includes(searchLower) ||
        item.description.toLowerCase().includes(searchLower) ||
        item.location.toLowerCase().includes(searchLower) ||
        item.supplier.toLowerCase().includes(searchLower)
      );
    }

    // Sort items
    filtered.sort((a, b) => {
      let aValue: any, bValue: any;
      
      switch (sortBy) {
        case 'name':
          aValue = a.name.toLowerCase();
          bValue = b.name.toLowerCase();
          break;
        case 'quantity':
          aValue = a.quantity;
          bValue = b.quantity;
          break;
        case 'category':
          aValue = a.category.toLowerCase();
          bValue = b.category.toLowerCase();
          break;
        case 'location':
          aValue = a.location.toLowerCase();
          bValue = b.location.toLowerCase();
          break;
        default:
          aValue = a.name.toLowerCase();
          bValue = b.name.toLowerCase();
      }

      if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    setFilteredItems(filtered);
  };

  const getStockStatus = (item: InventoryItem) => {
    if (item.quantity === 0) return 'out';
    if (item.quantity <= item.minStock) return 'low';
    if (item.quantity >= item.maxStock) return 'high';
    return 'normal';
  };

  const getStockStatusColor = (status: string) => {
    switch (status) {
      case 'out':
        return 'text-red-700 bg-red-100 border-red-200';
      case 'low':
        return 'text-yellow-700 bg-yellow-100 border-yellow-200';
      case 'high':
        return 'text-blue-700 bg-blue-100 border-blue-200';
      case 'normal':
        return 'text-green-700 bg-green-100 border-green-200';
      default:
        return 'text-gray-700 bg-gray-100 border-gray-200';
    }
  };

  const getStockStatusIcon = (status: string) => {
    switch (status) {
      case 'out':
        return <AlertTriangle className="w-3 h-3" />;
      case 'low':
        return <TrendingDown className="w-3 h-3" />;
      case 'high':
        return <TrendingUp className="w-3 h-3" />;
      case 'normal':
        return <CheckCircle className="w-3 h-3" />;
      default:
        return <Info className="w-3 h-3" />;
    }
  };

  const handleScanSuccess = async (barcode: string, item?: InventoryItem) => {
    setShowScanner(false);
    
    if (item) {
      onSelectItem?.(item);
    } else {
      // Search for item by barcode
      const foundItem = items.find(i => i.barcode === barcode || i.sku === barcode);
      if (foundItem) {
        onSelectItem?.(foundItem);
      } else {
        // Show error or create new item option
        setError(`No item found with barcode: ${barcode}`);
        setTimeout(() => setError(null), 3000);
      }
    }
  };

  const handleQuantityAdjustment = async (item: InventoryItem, delta: number) => {
    const newQuantity = Math.max(0, item.quantity + delta);
    const sanitizedQuantity = sanitizeQuantity(newQuantity);
    
    try {
      // Update local state immediately for better UX
      setItems(prevItems => 
        prevItems.map(i => 
          i.id === item.id ? { ...i, quantity: sanitizedQuantity } : i
        )
      );

      // Update database
      const updatedItem = { ...item, quantity: sanitizedQuantity };
      await offlineDB.saveInventoryItem?.(updatedItem);
      
      // Notify parent component
      onUpdateQuantity?.(updatedItem, sanitizedQuantity);
      
      // Queue for server sync if online
      if (navigator.onLine) {
        try {
          await authenticatedRequest(`/api/v1/field-ops/inventory/${item.id}`, {
            method: 'PATCH',
            body: JSON.stringify({ quantity: sanitizedQuantity }),
          });
        } catch (error) {
          console.warn('Failed to sync inventory update to server:', error);
        }
      }
    } catch (error) {
      console.error('Failed to update inventory quantity:', error);
      // Revert optimistic update
      loadInventory();
      setError('Failed to update item quantity');
      setTimeout(() => setError(null), 3000);
    }
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(price);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {/* Loading skeleton */}
        <div className="mobile-card">
          <div className="space-y-3">
            <div className="h-10 bg-gray-200 rounded animate-pulse"></div>
            <div className="grid grid-cols-3 gap-2">
              <div className="h-10 bg-gray-200 rounded animate-pulse"></div>
              <div className="h-10 bg-gray-200 rounded animate-pulse"></div>
              <div className="h-10 bg-gray-200 rounded animate-pulse"></div>
            </div>
          </div>
        </div>
        
        {[...Array(5)].map((_, i) => (
          <div key={i} className="mobile-card animate-pulse">
            <div className="flex space-x-3">
              <div className="w-12 h-12 bg-gray-200 rounded"></div>
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                <div className="h-3 bg-gray-200 rounded w-2/3"></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <>
      <div className="space-y-4">
        {/* Search and Filters */}
        <div className="mobile-card">
          <div className="space-y-3">
            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search inventory..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="mobile-input pl-10 pr-10"
              />
              <button
                onClick={() => setShowScanner(true)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-primary-600"
              >
                <ScanLine className="w-4 h-4" />
              </button>
            </div>

            {/* Filter Controls */}
            <div className="grid grid-cols-3 gap-2">
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="mobile-input text-sm"
              >
                <option value="all">All Categories</option>
                {categories.map(category => (
                  <option key={category} value={category}>{category}</option>
                ))}
              </select>
              
              <select
                value={stockFilter}
                onChange={(e) => setStockFilter(e.target.value)}
                className="mobile-input text-sm"
              >
                <option value="all">All Stock</option>
                <option value="out">Out of Stock</option>
                <option value="low">Low Stock</option>
                <option value="normal">Normal</option>
                <option value="high">High Stock</option>
              </select>
              
              <select
                value={`${sortBy}-${sortOrder}`}
                onChange={(e) => {
                  const [field, order] = e.target.value.split('-');
                  setSortBy(field as any);
                  setSortOrder(order as any);
                }}
                className="mobile-input text-sm"
              >
                <option value="name-asc">Name A-Z</option>
                <option value="name-desc">Name Z-A</option>
                <option value="quantity-asc">Stock Low-High</option>
                <option value="quantity-desc">Stock High-Low</option>
                <option value="category-asc">Category A-Z</option>
                <option value="location-asc">Location A-Z</option>
              </select>
            </div>
          </div>
        </div>

        {/* Error Display */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mobile-card bg-red-50 border-red-200"
            >
              <div className="flex items-center text-red-700">
                <AlertTriangle className="w-4 h-4 mr-2" />
                <span className="text-sm">{error}</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Inventory Count */}
        <div className="px-1 text-sm text-gray-600">
          {filteredItems.length} of {items.length} items
          {!navigator.onLine && (
            <span className="ml-2 text-orange-600">• Offline</span>
          )}
        </div>

        {/* Inventory Items */}
        <div className="space-y-3">
          <AnimatePresence>
            {filteredItems.map((item, index) => {
              const stockStatus = getStockStatus(item);
              const isSelected = selectedItems.includes(item.id);
              
              return (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                  onClick={() => onSelectItem?.(item)}
                  className={`mobile-card cursor-pointer transition-all ${
                    isSelected
                      ? 'ring-2 ring-primary-500 bg-primary-50'
                      : 'hover:shadow-md'
                  }`}
                >
                  {/* Header */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-start space-x-3">
                      <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center">
                        <Package className="w-6 h-6 text-gray-600" />
                      </div>
                      
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900 text-sm mb-1">
                          {item.name}
                        </h3>
                        <div className="flex items-center space-x-2 text-xs text-gray-500">
                          <span>SKU: {item.sku}</span>
                          {item.barcode && (
                            <>
                              <span>•</span>
                              <div className="flex items-center">
                                <Barcode className="w-3 h-3 mr-1" />
                                {item.barcode}
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    <div className="text-right">
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium border flex items-center ${getStockStatusColor(stockStatus)}`}
                      >
                        {getStockStatusIcon(stockStatus)}
                        <span className="ml-1 capitalize">{stockStatus}</span>
                      </span>
                    </div>
                  </div>

                  {/* Stock Information */}
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div>
                      <div className="text-xs text-gray-500 mb-1">Current Stock</div>
                      <div className="flex items-center space-x-2">
                        <span className="text-lg font-bold text-gray-900">
                          {item.quantity}
                        </span>
                        <div className="flex items-center space-x-1">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleQuantityAdjustment(item, -1);
                            }}
                            disabled={item.quantity === 0}
                            className="w-6 h-6 bg-gray-200 hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed rounded flex items-center justify-center touch-feedback"
                          >
                            <Minus className="w-3 h-3" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleQuantityAdjustment(item, 1);
                            }}
                            className="w-6 h-6 bg-gray-200 hover:bg-gray-300 rounded flex items-center justify-center touch-feedback"
                          >
                            <Plus className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    </div>
                    
                    <div>
                      <div className="text-xs text-gray-500 mb-1">Value</div>
                      <div className="text-lg font-bold text-gray-900">
                        {formatPrice(item.unitPrice * item.quantity)}
                      </div>
                      <div className="text-xs text-gray-500">
                        {formatPrice(item.unitPrice)} each
                      </div>
                    </div>
                  </div>

                  {/* Details */}
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center justify-between">
                      <div className="text-gray-600">Category:</div>
                      <div className="font-medium">{item.category}</div>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <div className="flex items-center text-gray-600">
                        <MapPin className="w-3 h-3 mr-1" />
                        Location:
                      </div>
                      <div className="font-medium">{item.location}</div>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <div className="text-gray-600">Supplier:</div>
                      <div className="font-medium">{item.supplier}</div>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <div className="text-gray-600">Last Restocked:</div>
                      <div className="font-medium">{formatDate(item.lastRestocked)}</div>
                    </div>
                  </div>

                  {/* Stock Levels */}
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>Min: {item.minStock}</span>
                      <span>Reserved: {item.reserved}</span>
                      <span>Max: {item.maxStock}</span>
                    </div>
                    <div className="mt-1 w-full bg-gray-200 rounded-full h-1">
                      <div
                        className={`h-1 rounded-full ${
                          stockStatus === 'out' ? 'bg-red-500' :
                          stockStatus === 'low' ? 'bg-yellow-500' :
                          stockStatus === 'high' ? 'bg-blue-500' : 'bg-green-500'
                        }`}
                        style={{
                          width: `${Math.min(100, (item.quantity / item.maxStock) * 100)}%`
                        }}
                      />
                    </div>
                  </div>

                  {/* Quick Actions */}
                  {workOrderMode && onRequestItem && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onRequestItem(item, 1);
                        }}
                        className="w-full bg-primary-600 hover:bg-primary-700 text-white py-2 px-3 rounded-lg text-sm font-medium transition-colors"
                      >
                        Request Item
                      </button>
                    </div>
                  )}
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>

        {/* Empty State */}
        {filteredItems.length === 0 && !loading && (
          <div className="text-center py-12">
            <Package className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="font-medium text-gray-900 mb-2">No Items Found</h3>
            <p className="text-gray-600 text-sm">
              {searchTerm || categoryFilter !== 'all' || stockFilter !== 'all'
                ? 'No items match your search criteria'
                : 'No inventory items available'}
            </p>
            {searchTerm && (
              <button
                onClick={() => {
                  setSearchTerm('');
                  setCategoryFilter('all');
                  setStockFilter('all');
                }}
                className="mt-3 text-primary-600 hover:text-primary-700 text-sm font-medium"
              >
                Clear Filters
              </button>
            )}
          </div>
        )}
      </div>

      {/* Barcode Scanner */}
      <AnimatePresence>
        {showScanner && (
          <InventoryScanner
            onScanSuccess={handleScanSuccess}
            onClose={() => setShowScanner(false)}
            onManualEntry={() => {
              setShowScanner(false);
              // Could open a manual entry dialog here
            }}
            scanMode="both"
            autoClose={true}
          />
        )}
      </AnimatePresence>
    </>
  );
}