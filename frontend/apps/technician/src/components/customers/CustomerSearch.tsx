/**
 * Customer Search Component
 * Advanced search interface for finding customers quickly
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  X,
  MapPin,
  Phone,
  User,
  Loader2,
  History,
} from 'lucide-react';
import { Customer, offlineDB } from '../../lib/enhanced-offline-db';
import { sanitizeSearchTerm } from '../../lib/validation/sanitization';

interface CustomerSearchProps {
  onSelectCustomer: (customer: Customer) => void;
  onClose: () => void;
  placeholder?: string;
  recentCustomers?: Customer[];
}

export function CustomerSearch({ 
  onSelectCustomer, 
  onClose, 
  placeholder = "Search customers...",
  recentCustomers = []
}: CustomerSearchProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(false);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const searchTimeoutRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    // Load recent searches from localStorage
    const saved = localStorage.getItem('technician_recent_searches');
    if (saved) {
      try {
        setRecentSearches(JSON.parse(saved));
      } catch (error) {
        console.warn('Failed to load recent searches:', error);
      }
    }

    // Focus search input
    searchInputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (searchTerm.trim().length >= 2) {
      performSearch(searchTerm.trim());
    } else {
      setSearchResults([]);
      setLoading(false);
    }
  }, [searchTerm]);

  const performSearch = async (term: string) => {
    setLoading(true);

    // Clear previous timeout
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    // Debounce search
    searchTimeoutRef.current = setTimeout(async () => {
      try {
        const sanitizedTerm = sanitizeSearchTerm(term);
        const results = await searchCustomers(sanitizedTerm);
        setSearchResults(results);
        
        // Save to recent searches
        saveRecentSearch(sanitizedTerm);
      } catch (error) {
        console.error('Search failed:', error);
        setSearchResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
  };

  const searchCustomers = async (term: string): Promise<Customer[]> => {
    try {
      // Search in offline database first
      const customers = await offlineDB.getCustomers?.() || [];
      const searchLower = term.toLowerCase();
      
      const filtered = customers.filter(customer =>
        customer.name.toLowerCase().includes(searchLower) ||
        customer.email.toLowerCase().includes(searchLower) ||
        customer.phone.includes(term) ||
        customer.serviceId.toLowerCase().includes(searchLower) ||
        customer.address.toLowerCase().includes(searchLower) ||
        customer.planName.toLowerCase().includes(searchLower)
      );

      // Sort by relevance (exact matches first, then partial matches)
      return filtered.sort((a, b) => {
        const aExactMatch = a.name.toLowerCase() === searchLower || 
                           a.serviceId.toLowerCase() === searchLower;
        const bExactMatch = b.name.toLowerCase() === searchLower || 
                           b.serviceId.toLowerCase() === searchLower;
        
        if (aExactMatch && !bExactMatch) return -1;
        if (!aExactMatch && bExactMatch) return 1;
        
        // Secondary sort by name
        return a.name.localeCompare(b.name);
      }).slice(0, 10); // Limit to 10 results
    } catch (error) {
      console.error('Customer search failed:', error);
      return [];
    }
  };

  const saveRecentSearch = (term: string) => {
    if (term.length < 2) return;

    const updated = [
      term,
      ...recentSearches.filter(search => search !== term)
    ].slice(0, 5); // Keep only 5 recent searches

    setRecentSearches(updated);
    
    try {
      localStorage.setItem('technician_recent_searches', JSON.stringify(updated));
    } catch (error) {
      console.warn('Failed to save recent search:', error);
    }
  };

  const handleSelectCustomer = (customer: Customer) => {
    // Save to recent searches
    saveRecentSearch(customer.name);
    
    onSelectCustomer(customer);
    onClose();
  };

  const handleRecentSearchClick = (term: string) => {
    setSearchTerm(term);
    searchInputRef.current?.focus();
  };

  const clearRecentSearches = () => {
    setRecentSearches([]);
    localStorage.removeItem('technician_recent_searches');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'ArrowDown' && searchResults.length > 0) {
      // Focus first result
      const firstResult = document.querySelector('[data-result-index="0"]') as HTMLElement;
      firstResult?.focus();
    }
  };

  const handleResultKeyDown = (e: React.KeyboardEvent, customer: Customer, index: number) => {
    if (e.key === 'Enter') {
      handleSelectCustomer(customer);
    } else if (e.key === 'ArrowDown') {
      const nextResult = document.querySelector(`[data-result-index="${index + 1}"]`) as HTMLElement;
      nextResult?.focus();
    } else if (e.key === 'ArrowUp') {
      if (index === 0) {
        searchInputRef.current?.focus();
      } else {
        const prevResult = document.querySelector(`[data-result-index="${index - 1}"]`) as HTMLElement;
        prevResult?.focus();
      }
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-start justify-center pt-16"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, y: -20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -20, scale: 0.95 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 max-h-[80vh] flex flex-col"
      >
        {/* Search Header */}
        <div className="p-4 border-b border-gray-200">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              ref={searchInputRef}
              type="text"
              placeholder={placeholder}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyDown={handleKeyDown}
              className="w-full pl-10 pr-10 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
            <button
              onClick={onClose}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Search Content */}
        <div className="flex-1 overflow-y-auto">
          <AnimatePresence mode="wait">
            {/* Loading State */}
            {loading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="p-8 text-center"
              >
                <Loader2 className="w-6 h-6 animate-spin text-primary-600 mx-auto mb-3" />
                <p className="text-gray-600 text-sm">Searching customers...</p>
              </motion.div>
            )}

            {/* Search Results */}
            {!loading && searchTerm.length >= 2 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                {searchResults.length > 0 ? (
                  <div className="p-2">
                    <div className="text-xs text-gray-500 px-2 py-2 font-medium">
                      {searchResults.length} result{searchResults.length !== 1 ? 's' : ''}
                    </div>
                    
                    {searchResults.map((customer, index) => (
                      <button
                        key={customer.id}
                        data-result-index={index}
                        onClick={() => handleSelectCustomer(customer)}
                        onKeyDown={(e) => handleResultKeyDown(e, customer, index)}
                        className="w-full p-3 rounded-lg hover:bg-gray-50 focus:bg-gray-50 focus:outline-none text-left transition-colors"
                      >
                        <div className="flex items-start space-x-3">
                          <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0">
                            <User className="w-4 h-4 text-primary-600" />
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between">
                              <h4 className="font-medium text-gray-900 text-sm truncate">
                                {customer.name}
                              </h4>
                              <span className={`px-2 py-1 rounded text-xs font-medium ${
                                customer.status === 'active' ? 'bg-green-100 text-green-700' :
                                customer.status === 'suspended' ? 'bg-yellow-100 text-yellow-700' :
                                'bg-red-100 text-red-700'
                              }`}>
                                {customer.status}
                              </span>
                            </div>
                            
                            <div className="flex items-center space-x-4 mt-1 text-xs text-gray-500">
                              <div className="flex items-center">
                                <Phone className="w-3 h-3 mr-1" />
                                {customer.phone}
                              </div>
                              <div className="flex items-center truncate">
                                <MapPin className="w-3 h-3 mr-1 flex-shrink-0" />
                                <span className="truncate">{customer.address}</span>
                              </div>
                            </div>
                            
                            <div className="text-xs text-gray-500 mt-1">
                              ID: {customer.serviceId} • {customer.planName}
                            </div>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="p-8 text-center">
                    <Search className="w-8 h-8 text-gray-400 mx-auto mb-3" />
                    <h3 className="font-medium text-gray-900 mb-1">No customers found</h3>
                    <p className="text-gray-600 text-sm">
                      Try searching by name, phone, email, or service ID
                    </p>
                  </div>
                )}
              </motion.div>
            )}

            {/* Default State - Recent Searches and Customers */}
            {!loading && searchTerm.length < 2 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="p-4 space-y-6"
              >
                {/* Recent Searches */}
                {recentSearches.length > 0 && (
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-medium text-gray-900 flex items-center">
                        <History className="w-4 h-4 mr-2" />
                        Recent Searches
                      </h3>
                      <button
                        onClick={clearRecentSearches}
                        className="text-xs text-gray-500 hover:text-gray-700"
                      >
                        Clear
                      </button>
                    </div>
                    
                    <div className="flex flex-wrap gap-2">
                      {recentSearches.map((term, index) => (
                        <button
                          key={index}
                          onClick={() => handleRecentSearchClick(term)}
                          className="px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded-full text-sm text-gray-700 transition-colors"
                        >
                          {term}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recent Customers */}
                {recentCustomers.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 mb-3 flex items-center">
                      <User className="w-4 h-4 mr-2" />
                      Recent Customers
                    </h3>
                    
                    <div className="space-y-2">
                      {recentCustomers.slice(0, 5).map((customer) => (
                        <button
                          key={customer.id}
                          onClick={() => handleSelectCustomer(customer)}
                          className="w-full p-3 rounded-lg hover:bg-gray-50 text-left transition-colors"
                        >
                          <div className="flex items-center space-x-3">
                            <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                              <User className="w-4 h-4 text-primary-600" />
                            </div>
                            
                            <div className="flex-1 min-w-0">
                              <div className="font-medium text-gray-900 text-sm truncate">
                                {customer.name}
                              </div>
                              <div className="text-xs text-gray-500 truncate">
                                {customer.serviceId} • {customer.planName}
                              </div>
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Empty State */}
                {recentSearches.length === 0 && recentCustomers.length === 0 && (
                  <div className="text-center py-12">
                    <Search className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                    <h3 className="font-medium text-gray-900 mb-2">Search Customers</h3>
                    <p className="text-gray-600 text-sm">
                      Type at least 2 characters to search for customers by name, phone, email, or service ID
                    </p>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Search Tips */}
        <div className="p-3 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">
          <div className="flex items-center justify-center space-x-4">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>Esc Close</span>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}