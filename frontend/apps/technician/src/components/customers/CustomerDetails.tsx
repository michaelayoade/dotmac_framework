/**
 * Customer Details Component
 * Displays comprehensive customer information and service history
 */

'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft,
  Phone,
  Mail,
  MapPin,
  Calendar,
  User,
  Wifi,
  Settings,
  Clock,
  CheckCircle,
  AlertCircle,
  XCircle,
  Navigation,
  Edit,
  History,
  FileText,
  Wrench,
} from 'lucide-react';
import { Customer, ServiceHistoryItem } from '../../lib/enhanced-offline-db';
import { formatDistanceToNow } from 'date-fns';

interface CustomerDetailsProps {
  customer: Customer;
  onBack: () => void;
  onEditCustomer?: (customer: Customer) => void;
  onCreateWorkOrder?: (customer: Customer) => void;
}

export function CustomerDetails({
  customer,
  onBack,
  onEditCustomer,
  onCreateWorkOrder,
}: CustomerDetailsProps) {
  const [activeTab, setActiveTab] = useState<'info' | 'history' | 'notes'>('info');
  const [loading, setLoading] = useState(false);
  const [expandedHistoryId, setExpandedHistoryId] = useState<string | null>(null);

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

  const getServiceTypeIcon = (type: ServiceHistoryItem['type']) => {
    switch (type) {
      case 'installation':
        return <Settings className="w-4 h-4" />;
      case 'maintenance':
        return <Wrench className="w-4 h-4" />;
      case 'repair':
        return <AlertCircle className="w-4 h-4" />;
      case 'upgrade':
        return <CheckCircle className="w-4 h-4" />;
      default:
        return <Clock className="w-4 h-4" />;
    }
  };

  const getServiceStatusColor = (status: ServiceHistoryItem['status']) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-100';
      case 'partial':
        return 'text-yellow-600 bg-yellow-100';
      case 'cancelled':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const callCustomer = () => {
    window.location.href = `tel:${customer.phone}`;
  };

  const emailCustomer = () => {
    window.location.href = `mailto:${customer.email}`;
  };

  const navigateToCustomer = () => {
    const encodedAddress = encodeURIComponent(customer.address);
    const mapsUrl = `https://www.google.com/maps?q=${encodedAddress}`;
    window.open(mapsUrl, '_blank');
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return {
      date: date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      }),
      time: date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
      }),
    };
  };

  const toggleHistoryExpansion = (historyId: string) => {
    setExpandedHistoryId(expandedHistoryId === historyId ? null : historyId);
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="mobile-card">
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={onBack}
            className="flex items-center text-gray-600 hover:text-gray-800 touch-feedback"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            <span>Back</span>
          </button>
          
          <div className="flex space-x-2">
            {onEditCustomer && (
              <button
                onClick={() => onEditCustomer(customer)}
                className="flex items-center px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg touch-feedback"
              >
                <Edit className="w-3 h-3 mr-1" />
                Edit
              </button>
            )}
            {onCreateWorkOrder && (
              <button
                onClick={() => onCreateWorkOrder(customer)}
                className="flex items-center px-3 py-1 text-sm bg-primary-600 hover:bg-primary-700 text-white rounded-lg touch-feedback"
              >
                <Wrench className="w-3 h-3 mr-1" />
                Work Order
              </button>
            )}
          </div>
        </div>

        {/* Customer Basic Info */}
        <div className="flex items-start space-x-4">
          <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center">
            <User className="w-8 h-8 text-primary-600" />
          </div>
          
          <div className="flex-1">
            <h1 className="text-lg font-bold text-gray-900 mb-1">
              {customer.name}
            </h1>
            <p className="text-gray-600 text-sm mb-2">
              Service ID: {customer.serviceId}
            </p>
            
            <div className="flex items-center space-x-3">
              <span
                className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(customer.status)}`}
              >
                {customer.status.charAt(0).toUpperCase() + customer.status.slice(1)}
              </span>
              
              {!navigator.onLine && (
                <span className="flex items-center text-orange-600 text-xs">
                  <Wifi className="w-3 h-3 mr-1" />
                  Offline
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-3 gap-3">
        <button
          onClick={callCustomer}
          className="mobile-card flex flex-col items-center space-y-2 hover:bg-green-50 touch-feedback"
        >
          <Phone className="w-6 h-6 text-green-600" />
          <span className="text-sm font-medium text-gray-900">Call</span>
        </button>
        
        <button
          onClick={emailCustomer}
          className="mobile-card flex flex-col items-center space-y-2 hover:bg-blue-50 touch-feedback"
        >
          <Mail className="w-6 h-6 text-blue-600" />
          <span className="text-sm font-medium text-gray-900">Email</span>
        </button>
        
        <button
          onClick={navigateToCustomer}
          className="mobile-card flex flex-col items-center space-y-2 hover:bg-purple-50 touch-feedback"
        >
          <Navigation className="w-6 h-6 text-purple-600" />
          <span className="text-sm font-medium text-gray-900">Navigate</span>
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="mobile-card">
        <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg">
          {[
            { id: 'info', label: 'Info', icon: User },
            { id: 'history', label: 'History', icon: History },
            { id: 'notes', label: 'Notes', icon: FileText },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id as any)}
              className={`flex-1 flex items-center justify-center space-x-1 py-2 px-3 text-sm font-medium rounded-md transition-all ${
                activeTab === id
                  ? 'bg-white text-primary-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <AnimatePresence mode="wait">
        {activeTab === 'info' && (
          <motion.div
            key="info"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.2 }}
            className="space-y-4"
          >
            {/* Contact Information */}
            <div className="mobile-card">
              <h3 className="font-semibold text-gray-900 mb-3">Contact Information</h3>
              
              <div className="space-y-3">
                <div className="flex items-center space-x-3">
                  <Phone className="w-4 h-4 text-gray-400" />
                  <div>
                    <div className="text-sm font-medium text-gray-900">
                      {customer.phone}
                    </div>
                    <div className="text-xs text-gray-500">Primary Phone</div>
                  </div>
                </div>
                
                <div className="flex items-center space-x-3">
                  <Mail className="w-4 h-4 text-gray-400" />
                  <div>
                    <div className="text-sm font-medium text-gray-900">
                      {customer.email}
                    </div>
                    <div className="text-xs text-gray-500">Email Address</div>
                  </div>
                </div>
                
                <div className="flex items-start space-x-3">
                  <MapPin className="w-4 h-4 text-gray-400 mt-0.5" />
                  <div>
                    <div className="text-sm font-medium text-gray-900">
                      {customer.address}
                    </div>
                    <div className="text-xs text-gray-500">Service Address</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Service Information */}
            <div className="mobile-card">
              <h3 className="font-semibold text-gray-900 mb-3">Service Information</h3>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-gray-500 mb-1">Plan</div>
                  <div className="text-sm font-medium text-gray-900">
                    {customer.planName}
                  </div>
                  <div className="text-xs text-gray-600 mt-1">
                    {customer.planSpeed}
                  </div>
                </div>
                
                <div>
                  <div className="text-xs text-gray-500 mb-1">Status</div>
                  <span
                    className={`inline-flex px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(customer.status)}`}
                  >
                    {customer.status.charAt(0).toUpperCase() + customer.status.slice(1)}
                  </span>
                </div>
                
                <div>
                  <div className="text-xs text-gray-500 mb-1">Install Date</div>
                  <div className="text-sm font-medium text-gray-900">
                    {formatDate(customer.installDate).date}
                  </div>
                </div>
                
                <div>
                  <div className="text-xs text-gray-500 mb-1">Last Service</div>
                  <div className="text-sm font-medium text-gray-900">
                    {customer.lastServiceDate 
                      ? formatDate(customer.lastServiceDate).date 
                      : 'None'
                    }
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {activeTab === 'history' && (
          <motion.div
            key="history"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.2 }}
            className="space-y-3"
          >
            {customer.serviceHistory.length > 0 ? (
              customer.serviceHistory
                .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
                .map((service) => (
                  <motion.div
                    key={service.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mobile-card"
                  >
                    <div
                      className="cursor-pointer"
                      onClick={() => toggleHistoryExpansion(service.id)}
                    >
                      <div className="flex items-start space-x-3">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                          service.type === 'installation' ? 'bg-blue-100 text-blue-600' :
                          service.type === 'maintenance' ? 'bg-green-100 text-green-600' :
                          service.type === 'repair' ? 'bg-red-100 text-red-600' :
                          'bg-purple-100 text-purple-600'
                        }`}>
                          {getServiceTypeIcon(service.type)}
                        </div>
                        
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <h4 className="font-medium text-gray-900 text-sm">
                              {service.type.charAt(0).toUpperCase() + service.type.slice(1)}
                            </h4>
                            <span
                              className={`px-2 py-1 rounded-full text-xs font-medium ${getServiceStatusColor(service.status)}`}
                            >
                              {service.status}
                            </span>
                          </div>
                          
                          <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                            {service.description}
                          </p>
                          
                          <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                            <div className="flex items-center">
                              <Calendar className="w-3 h-3 mr-1" />
                              {formatDate(service.date).date}
                            </div>
                            <div className="flex items-center">
                              <Clock className="w-3 h-3 mr-1" />
                              {formatDate(service.date).time}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <AnimatePresence>
                      {expandedHistoryId === service.id && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          className="mt-3 pt-3 border-t border-gray-200"
                        >
                          <div className="space-y-2">
                            <div>
                              <span className="text-xs text-gray-500">Technician:</span>
                              <div className="text-sm text-gray-900">
                                {service.technicianName} (ID: {service.technicianId})
                              </div>
                            </div>
                            
                            {service.notes && (
                              <div>
                                <span className="text-xs text-gray-500">Notes:</span>
                                <div className="text-sm text-gray-900 mt-1">
                                  {service.notes}
                                </div>
                              </div>
                            )}
                            
                            {service.workOrderId && (
                              <div>
                                <span className="text-xs text-gray-500">Work Order:</span>
                                <div className="text-sm text-gray-900">
                                  #{service.workOrderId}
                                </div>
                              </div>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                ))
            ) : (
              <div className="text-center py-12">
                <History className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="font-medium text-gray-900 mb-2">No Service History</h3>
                <p className="text-gray-600 text-sm">
                  This customer has no recorded service history yet.
                </p>
              </div>
            )}
          </motion.div>
        )}

        {activeTab === 'notes' && (
          <motion.div
            key="notes"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.2 }}
            className="mobile-card"
          >
            <h3 className="font-semibold text-gray-900 mb-3">Customer Notes</h3>
            
            {customer.notes.trim() ? (
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-sm text-gray-700 whitespace-pre-wrap">
                  {customer.notes}
                </p>
              </div>
            ) : (
              <div className="text-center py-8">
                <FileText className="w-8 h-8 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-600 text-sm">No notes available</p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}