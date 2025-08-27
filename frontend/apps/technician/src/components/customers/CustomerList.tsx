/**
 * Customer List Component
 * Displays and manages customer information for technicians
 */

'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Filter,
  MapPin,
  Phone,
  Mail,
  User,
  Calendar,
  Wifi,
  AlertCircle,
  CheckCircle,
  Clock,
  Navigation,
  Info,
} from 'lucide-react';
import { offlineDB, Customer } from '../../lib/enhanced-offline-db';
import { useAuth } from '../auth/TechnicianAuth';
import { sanitizeSearchTerm } from '../../lib/validation/sanitization';

interface CustomerListProps {
  onSelectCustomer?: (customer: Customer) => void;
  selectedCustomerId?: string;
  workOrderMode?: boolean;
}

export function CustomerList({ 
  onSelectCustomer, 
  selectedCustomerId,
  workOrderMode = false 
}: CustomerListProps) {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [filteredCustomers, setFilteredCustomers] = useState<Customer[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { authenticatedRequest } = useAuth();

  useEffect(() => {
    loadCustomers();
  }, []);

  useEffect(() => {
    filterCustomers();
  }, [customers, searchTerm, statusFilter]);

  const loadCustomers = async () => {
    try {
      setLoading(true);
      setError(null);

      // Try to load from local database first
      const localCustomers = await offlineDB.getCustomers?.() || [];
      
      if (localCustomers.length > 0) {
        setCustomers(localCustomers);
        setLoading(false);
      }

      // Try to fetch latest from server if online
      if (navigator.onLine) {
        try {
          const response = await authenticatedRequest('/api/v1/field-ops/customers');
          if (response.ok) {
            const serverCustomers = await response.json();
            setCustomers(serverCustomers);
            
            // Update local database
            for (const customer of serverCustomers) {
              await offlineDB.saveCustomer?.(customer);
            }
          }
        } catch (networkError) {
          console.warn('Failed to fetch customers from server, using local data');
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load customers');
      console.error('Failed to load customers:', err);
    } finally {
      setLoading(false);
    }
  };

  const filterCustomers = () => {
    let filtered = customers;

    // Filter by status
    if (statusFilter !== 'all') {
      filtered = filtered.filter(customer => customer.status === statusFilter);
    }

    // Filter by search term
    if (searchTerm.trim()) {
      const sanitizedSearch = sanitizeSearchTerm(searchTerm.trim());
      const searchLower = sanitizedSearch.toLowerCase();
      
      filtered = filtered.filter(customer =>
        customer.name.toLowerCase().includes(searchLower) ||
        customer.email.toLowerCase().includes(searchLower) ||
        customer.phone.includes(sanitizedSearch) ||
        customer.serviceId.toLowerCase().includes(searchLower) ||
        customer.address.toLowerCase().includes(searchLower)
      );
    }

    setFilteredCustomers(filtered);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'text-green-700 bg-green-100 border-green-200';
      case 'suspended':
        return 'text-yellow-700 bg-yellow-100 border-yellow-200';
      case 'cancelled':
        return 'text-red-700 bg-red-100 border-red-200';
      default:
        return 'text-gray-700 bg-gray-100 border-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="w-3 h-3" />;
      case 'suspended':
        return <Clock className="w-3 h-3" />;
      case 'cancelled':
        return <AlertCircle className="w-3 h-3" />;
      default:
        return <Info className="w-3 h-3" />;
    }
  };

  const handleCustomerSelect = (customer: Customer) => {
    onSelectCustomer?.(customer);
  };

  const callCustomer = (phone: string) => {
    window.location.href = `tel:${phone}`;
  };

  const emailCustomer = (email: string) => {
    window.location.href = `mailto:${email}`;
  };

  const navigateToCustomer = (address: string) => {
    const encodedAddress = encodeURIComponent(address);
    const mapsUrl = `https://www.google.com/maps?q=${encodedAddress}`;
    window.open(mapsUrl, '_blank');
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="mobile-card">
          <div className="space-y-3">
            <div className="h-10 bg-gray-200 rounded animate-pulse"></div>
            <div className="h-10 bg-gray-200 rounded animate-pulse"></div>
          </div>
        </div>
        
        {[...Array(3)].map((_, i) => (
          <div key={i} className="mobile-card animate-pulse">
            <div className="flex space-x-3">
              <div className="w-12 h-12 bg-gray-200 rounded-full"></div>
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

  if (error) {
    return (
      <div className="mobile-card bg-red-50 border-red-200">
        <div className="flex items-center text-red-700">
          <AlertCircle className="w-5 h-5 mr-3" />
          <div>
            <h3 className="font-medium">Error Loading Customers</h3>
            <p className="text-sm mt-1">{error}</p>
          </div>
        </div>
        <button
          onClick={loadCustomers}
          className="mt-3 text-red-600 hover:text-red-800 text-sm font-medium"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Search and Filter Controls */}
      <div className="mobile-card">
        <div className="space-y-3">
          {/* Search Input */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="Search customers..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="mobile-input pl-10"
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="mobile-input flex-1"
            >
              <option value="all">All Customers</option>
              <option value="active">Active</option>
              <option value="suspended">Suspended</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        </div>
      </div>

      {/* Customer Count */}
      <div className="px-1 text-sm text-gray-600">
        {filteredCustomers.length} of {customers.length} customers
        {!navigator.onLine && (
          <span className="ml-2 inline-flex items-center text-orange-600">
            <Wifi className="w-3 h-3 mr-1" />
            Offline
          </span>
        )}
      </div>

      {/* Customer List */}
      <div className="space-y-3">
        <AnimatePresence>
          {filteredCustomers.map((customer, index) => (
            <motion.div
              key={customer.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
              onClick={() => handleCustomerSelect(customer)}
              className={`mobile-card cursor-pointer transition-all ${
                selectedCustomerId === customer.id
                  ? 'ring-2 ring-primary-500 bg-primary-50'
                  : 'hover:shadow-md'
              }`}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                    <User className="w-5 h-5 text-primary-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 text-sm">
                      {customer.name}
                    </h3>
                    <p className="text-gray-600 text-xs">
                      ID: {customer.serviceId}
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-medium border flex items-center ${getStatusColor(customer.status)}`}
                  >
                    {getStatusIcon(customer.status)}
                    <span className="ml-1 capitalize">{customer.status}</span>
                  </span>
                </div>
              </div>

              {/* Service Info */}
              <div className="grid grid-cols-2 gap-3 mb-3 text-sm">
                <div>
                  <span className="text-gray-600">Plan:</span>
                  <div className="font-medium">{customer.planName}</div>
                  <div className="text-xs text-gray-500">{customer.planSpeed}</div>
                </div>
                <div>
                  <span className="text-gray-600">Installed:</span>
                  <div className="font-medium">{formatDate(customer.installDate)}</div>
                  {customer.lastServiceDate && (
                    <div className="text-xs text-gray-500">
                      Last service: {formatDate(customer.lastServiceDate)}
                    </div>
                  )}
                </div>
              </div>

              {/* Contact Information */}
              <div className="space-y-2 mb-3">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center text-gray-600 flex-1 min-w-0">
                    <Phone className="w-3 h-3 mr-2 flex-shrink-0" />
                    <span className="truncate">{customer.phone}</span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      callCustomer(customer.phone);
                    }}
                    className="text-blue-600 hover:text-blue-700 text-xs font-medium ml-2 touch-feedback"
                  >
                    Call
                  </button>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center text-gray-600 flex-1 min-w-0">
                    <Mail className="w-3 h-3 mr-2 flex-shrink-0" />
                    <span className="truncate">{customer.email}</span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      emailCustomer(customer.email);
                    }}
                    className="text-blue-600 hover:text-blue-700 text-xs font-medium ml-2 touch-feedback"
                  >
                    Email
                  </button>
                </div>
              </div>

              {/* Address */}
              <div className="flex items-start justify-between text-sm">
                <div className="flex items-start text-gray-600 flex-1 min-w-0">
                  <MapPin className="w-3 h-3 mr-2 mt-0.5 flex-shrink-0" />
                  <span className="text-sm">{customer.address}</span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    navigateToCustomer(customer.address);
                  }}
                  className="text-blue-600 hover:text-blue-700 text-xs font-medium ml-2 flex-shrink-0 touch-feedback"
                >
                  <Navigation className="w-3 h-3" />
                </button>
              </div>

              {/* Service History Summary */}
              {customer.serviceHistory.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>{customer.serviceHistory.length} service records</span>
                    <div className="flex space-x-2">
                      {customer.serviceHistory.slice(0, 3).map((service, idx) => (
                        <span
                          key={idx}
                          className={`w-2 h-2 rounded-full ${
                            service.status === 'completed' ? 'bg-green-400' :
                            service.status === 'partial' ? 'bg-yellow-400' : 'bg-red-400'
                          }`}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Empty State */}
      {filteredCustomers.length === 0 && !loading && (
        <div className="text-center py-12">
          <User className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="font-medium text-gray-900 mb-2">No Customers Found</h3>
          <p className="text-gray-600 text-sm">
            {searchTerm || statusFilter !== 'all'
              ? 'No customers match your search criteria'
              : 'No customers available'}
          </p>
          {searchTerm && (
            <button
              onClick={() => {
                setSearchTerm('');
                setStatusFilter('all');
              }}
              className="mt-3 text-primary-600 hover:text-primary-700 text-sm font-medium"
            >
              Clear Search
            </button>
          )}
        </div>
      )}
    </div>
  );
}