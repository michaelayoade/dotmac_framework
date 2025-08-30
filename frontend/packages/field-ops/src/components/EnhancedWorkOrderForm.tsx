'use client';

import React, { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Save,
  X,
  AlertCircle,
  Camera,
  MapPin,
  Plus,
  Trash2,
  Loader2,
} from 'lucide-react';
import { Button, Card, Input, Modal } from '@dotmac/primitives';
import { TechnicianLocationTracker, WorkOrderRoutingMap } from '@dotmac/mapping';
import { useMobile } from '@dotmac/mobile';
import { useUniversalAuth } from '@dotmac/headless';
import { WorkOrderSchema } from '../schemas/workOrderSchema';
import { PhotoCapture } from './PhotoCapture';
import { CustomerSearch } from './CustomerSearch';
import type { WorkOrder, Customer, ChecklistItem } from '../types';

interface EnhancedWorkOrderFormProps {
  workOrder?: WorkOrder;
  customer?: Customer;
  onSave: (workOrder: Partial<WorkOrder>) => Promise<void>;
  onCancel: () => void;
  mode: 'create' | 'edit' | 'complete';
  enableMLPredictions?: boolean;
  enableLocationTracking?: boolean;
}

export function EnhancedWorkOrderForm({
  workOrder,
  customer: initialCustomer,
  onSave,
  onCancel,
  mode,
  enableMLPredictions = true,
  enableLocationTracking = true,
}: EnhancedWorkOrderFormProps) {
  const { isMobile } = useMobile();
  const { user } = useUniversalAuth();

  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(initialCustomer || null);
  const [showCustomerSearch, setShowCustomerSearch] = useState(!initialCustomer && !workOrder);
  const [showPhotoCapture, setShowPhotoCapture] = useState(false);
  const [showLocationMap, setShowLocationMap] = useState(false);
  const [photos, setPhotos] = useState<string[]>(workOrder?.photos || []);
  const [checklist, setChecklist] = useState<ChecklistItem[]>(workOrder?.checklist || []);
  const [currentLocation, setCurrentLocation] = useState<[number, number] | null>(null);
  const [mlPredictions, setMlPredictions] = useState({
    estimatedDuration: 0,
    optimalRoute: null as any,
    riskFactors: [] as string[]
  });
  const [loading, setLoading] = useState(false);

  const isCompleting = mode === 'complete';
  const isEditing = mode === 'edit';
  const isCreating = mode === 'create';

  const {
    control,
    handleSubmit,
    formState: { errors, isDirty },
    setValue,
    watch,
    reset,
  } = useForm({
    resolver: zodResolver(WorkOrderSchema.partial()),
    defaultValues: workOrder ? {
      title: workOrder.title,
      description: workOrder.description,
      priority: workOrder.priority,
      scheduledDate: workOrder.scheduledDate?.slice(0, 16),
      notes: workOrder.notes,
      equipment: workOrder.equipment,
    } : {
      title: '',
      description: '',
      priority: 'medium' as const,
      scheduledDate: new Date().toISOString().slice(0, 16),
      notes: '',
      equipment: {
        type: '',
        required: [],
      },
    },
  });

  // Get current location if enabled
  useEffect(() => {
    if (enableLocationTracking && navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setCurrentLocation([position.coords.latitude, position.coords.longitude]);
        },
        (error) => console.warn('Failed to get location:', error)
      );
    }
  }, [enableLocationTracking]);

  // Generate ML predictions when customer or form data changes
  useEffect(() => {
    if (enableMLPredictions && selectedCustomer && isDirty) {
      generateMLPredictions();
    }
  }, [selectedCustomer, watch('title'), watch('description'), watch('priority'), enableMLPredictions]);

  const generateMLPredictions = async () => {
    if (!selectedCustomer) return;

    try {
      // Mock ML predictions - in real implementation, this would call @dotmac/ml-analytics
      const formData = watch();

      // Estimate duration based on work type and customer history
      const baseHours = getPriorityMultiplier(formData.priority || 'medium') * 2;
      const complexity = getComplexityFromDescription(formData.description || '');
      const estimatedDuration = baseHours * complexity;

      // Identify risk factors
      const riskFactors = identifyRiskFactors(formData, selectedCustomer);

      setMlPredictions({
        estimatedDuration,
        optimalRoute: currentLocation ? {
          from: currentLocation,
          to: selectedCustomer.coordinates || [0, 0],
          estimatedTime: 30 // minutes
        } : null,
        riskFactors
      });
    } catch (error) {
      console.warn('Failed to generate ML predictions:', error);
    }
  };

  const getPriorityMultiplier = (priority: string): number => {
    const multipliers = { urgent: 1.5, high: 1.2, medium: 1.0, low: 0.8 };
    return multipliers[priority as keyof typeof multipliers] || 1.0;
  };

  const getComplexityFromDescription = (description: string): number => {
    const complexityKeywords = [
      { words: ['install', 'setup', 'configure'], factor: 1.5 },
      { words: ['repair', 'fix', 'troubleshoot'], factor: 1.3 },
      { words: ['maintenance', 'check', 'inspect'], factor: 1.0 },
      { words: ['emergency', 'urgent', 'outage'], factor: 2.0 },
    ];

    const lowerDesc = description.toLowerCase();
    let complexity = 1.0;

    for (const keyword of complexityKeywords) {
      if (keyword.words.some(word => lowerDesc.includes(word))) {
        complexity = Math.max(complexity, keyword.factor);
      }
    }

    return complexity;
  };

  const identifyRiskFactors = (formData: any, customer: Customer): string[] => {
    const risks: string[] = [];

    if (formData.priority === 'urgent') {
      risks.push('High priority work - potential time pressure');
    }

    if (customer.serviceHistory?.length > 5) {
      risks.push('Customer has extensive service history');
    }

    if (formData.equipment?.required?.length > 3) {
      risks.push('Multiple equipment requirements - check inventory');
    }

    const weatherRisk = Math.random() < 0.3; // Mock weather API
    if (weatherRisk) {
      risks.push('Weather conditions may impact outdoor work');
    }

    return risks;
  };

  const addChecklistItem = () => {
    const newItem: ChecklistItem = {
      id: `checklist_${Date.now()}_${Math.random().toString(36).slice(2)}`,
      text: '',
      completed: false,
      required: false,
    };
    setChecklist([...checklist, newItem]);
  };

  const updateChecklistItem = (id: string, updates: Partial<ChecklistItem>) => {
    setChecklist(checklist.map(item =>
      item.id === id ? { ...item, ...updates } : item
    ));
  };

  const removeChecklistItem = (id: string) => {
    setChecklist(checklist.filter(item => item.id !== id));
  };

  const handlePhotoCapture = (photoDataUrl: string) => {
    setPhotos([...photos, photoDataUrl]);
    setShowPhotoCapture(false);
  };

  const removePhoto = (index: number) => {
    setPhotos(photos.filter((_, i) => i !== index));
  };

  const onSubmit = async (data: any) => {
    if (!selectedCustomer) {
      alert('Please select a customer');
      return;
    }

    setLoading(true);

    try {
      const workOrderData: Partial<WorkOrder> = {
        ...data,
        id: workOrder?.id || `WO_${Date.now()}_${Math.random().toString(36).slice(2)}`,
        customerId: selectedCustomer.id,
        technicianId: user?.id || '',
        scheduledDate: new Date(data.scheduledDate).toISOString(),
        assignedAt: workOrder?.assignedAt || new Date().toISOString(),
        location: {
          address: selectedCustomer.address,
          coordinates: selectedCustomer.coordinates || [0, 0],
        },
        customer: {
          name: selectedCustomer.name,
          phone: selectedCustomer.phone,
          email: selectedCustomer.email,
          serviceId: selectedCustomer.serviceId,
        },
        checklist,
        photos,
        status: isCompleting ? 'completed' : (workOrder?.status || 'pending'),
        completedAt: isCompleting ? new Date().toISOString() : workOrder?.completedAt,
        mlPredictions: enableMLPredictions ? mlPredictions : undefined,
        lastModified: new Date().toISOString(),
      };

      await onSave(workOrderData);
    } catch (error) {
      console.error('Failed to save work order:', error);
      alert('Failed to save work order. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getPriorityColor = (priority: string) => {
    const colors = {
      urgent: 'border-red-300 bg-red-50 text-red-700',
      high: 'border-orange-300 bg-orange-50 text-orange-700',
      medium: 'border-yellow-300 bg-yellow-50 text-yellow-700',
      low: 'border-green-300 bg-green-50 text-green-700'
    };
    return colors[priority as keyof typeof colors] || colors.medium;
  };

  return (
    <>
      <div className="space-y-4 max-w-4xl mx-auto">
        {/* Header with ML Predictions */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-lg font-bold text-gray-900">
                {isCreating ? 'New Work Order' :
                 isCompleting ? 'Complete Work Order' :
                 'Edit Work Order'}
              </h1>
              {workOrder && (
                <p className="text-sm text-gray-600">#{workOrder.id}</p>
              )}
            </div>

            <Button
              variant="ghost"
              size="sm"
              onClick={onCancel}
              className="w-10 h-10 p-0"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>

          {/* ML Predictions Panel */}
          {enableMLPredictions && mlPredictions.estimatedDuration > 0 && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <h3 className="font-medium text-blue-900 mb-2">AI Predictions</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-blue-700 font-medium">Estimated Duration:</span>
                  <div className="text-blue-900">{mlPredictions.estimatedDuration.toFixed(1)} hours</div>
                </div>
                {mlPredictions.optimalRoute && (
                  <div>
                    <span className="text-blue-700 font-medium">Travel Time:</span>
                    <div className="text-blue-900">{mlPredictions.optimalRoute.estimatedTime} minutes</div>
                  </div>
                )}
                <div>
                  <span className="text-blue-700 font-medium">Risk Factors:</span>
                  <div className="text-blue-900">{mlPredictions.riskFactors.length} identified</div>
                </div>
              </div>

              {mlPredictions.riskFactors.length > 0 && (
                <div className="mt-3">
                  <details className="text-sm">
                    <summary className="text-blue-700 font-medium cursor-pointer">View Risk Factors</summary>
                    <ul className="mt-2 space-y-1">
                      {mlPredictions.riskFactors.map((risk, index) => (
                        <li key={index} className="text-blue-800 flex items-start">
                          <span className="mr-2">•</span>
                          {risk}
                        </li>
                      ))}
                    </ul>
                  </details>
                </div>
              )}
            </div>
          )}

          {/* Customer Selection */}
          {selectedCustomer ? (
            <div className="bg-gray-50 rounded-lg p-4 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                  <span className="text-primary-600 font-medium">
                    {selectedCustomer.name.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">{selectedCustomer.name}</h3>
                  <p className="text-sm text-gray-600">
                    {selectedCustomer.serviceId} • {selectedCustomer.address}
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                {enableLocationTracking && selectedCustomer.coordinates && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowLocationMap(true)}
                  >
                    <MapPin className="w-4 h-4" />
                  </Button>
                )}
                {isCreating && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setSelectedCustomer(null);
                      setShowCustomerSearch(true);
                    }}
                  >
                    Change
                  </Button>
                )}
              </div>
            </div>
          ) : (
            <Button
              variant="outline"
              onClick={() => setShowCustomerSearch(true)}
              className="w-full p-4 h-auto"
            >
              <div className="text-center">
                <MapPin className="w-6 h-6 mx-auto mb-2 text-primary-600" />
                <span className="text-primary-700 font-medium">Select Customer</span>
              </div>
            </Button>
          )}
        </Card>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Basic Information */}
          <Card className="p-6">
            <h2 className="font-semibold text-gray-900 mb-4">Work Details</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Title *
                </label>
                <Controller
                  name="title"
                  control={control}
                  rules={{ required: 'Title is required' }}
                  render={({ field }) => (
                    <Input
                      {...field}
                      placeholder="Brief description of the work"
                      error={errors.title?.message as string}
                    />
                  )}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Description *
                </label>
                <Controller
                  name="description"
                  control={control}
                  rules={{ required: 'Description is required' }}
                  render={({ field }) => (
                    <textarea
                      {...field}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                      placeholder="Detailed description of the work to be performed"
                    />
                  )}
                />
                {errors.description && (
                  <p className="mt-1 text-sm text-red-600 flex items-center">
                    <AlertCircle className="w-3 h-3 mr-1" />
                    {errors.description.message as string}
                  </p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Priority
                  </label>
                  <Controller
                    name="priority"
                    control={control}
                    render={({ field }) => (
                      <select
                        {...field}
                        className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 ${getPriorityColor(field.value || 'medium')}`}
                      >
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                        <option value="urgent">Urgent</option>
                      </select>
                    )}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Scheduled Date *
                  </label>
                  <Controller
                    name="scheduledDate"
                    control={control}
                    rules={{ required: 'Scheduled date is required' }}
                    render={({ field }) => (
                      <Input
                        {...field}
                        type="datetime-local"
                        error={errors.scheduledDate?.message as string}
                      />
                    )}
                  />
                </div>
              </div>
            </div>
          </Card>

          {/* Checklist */}
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-gray-900">Checklist</h2>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addChecklistItem}
              >
                <Plus className="w-4 h-4 mr-1" />
                Add Item
              </Button>
            </div>

            <div className="space-y-3">
              {checklist.map((item, index) => (
                <div key={item.id} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                  <input
                    type="checkbox"
                    checked={item.completed}
                    onChange={(e) => updateChecklistItem(item.id, {
                      completed: e.target.checked,
                      timestamp: e.target.checked ? new Date().toISOString() : undefined,
                    })}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    disabled={!isCompleting}
                  />

                  <Input
                    value={item.text}
                    onChange={(e) => updateChecklistItem(item.id, { text: e.target.value })}
                    placeholder="Checklist item"
                    className="flex-1 bg-transparent border-none focus:ring-0 p-0"
                  />

                  <div className="flex items-center space-x-2">
                    <label className="flex items-center space-x-1 text-xs text-gray-600">
                      <input
                        type="checkbox"
                        checked={item.required}
                        onChange={(e) => updateChecklistItem(item.id, { required: e.target.checked })}
                        className="rounded border-gray-300 text-red-600"
                      />
                      <span>Required</span>
                    </label>

                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeChecklistItem(item.id)}
                      className="p-1 text-red-600 hover:text-red-800"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}

              {checklist.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  No checklist items yet. Add some to track progress.
                </div>
              )}
            </div>
          </Card>

          {/* Photos */}
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-gray-900">Photos</h2>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setShowPhotoCapture(true)}
              >
                <Camera className="w-4 h-4 mr-1" />
                Add Photo
              </Button>
            </div>

            <div className="grid grid-cols-3 md:grid-cols-4 gap-3">
              {photos.map((photo, index) => (
                <div key={index} className="relative group">
                  <img
                    src={photo}
                    alt={`Work photo ${index + 1}`}
                    className="w-full h-24 object-cover rounded-lg border"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removePhoto(index)}
                    className="absolute top-1 right-1 w-6 h-6 p-0 bg-red-600 text-white opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X className="w-3 h-3" />
                  </Button>
                </div>
              ))}

              {photos.length === 0 && (
                <div className="col-span-3 md:col-span-4 text-center py-8 text-gray-500">
                  No photos added yet
                </div>
              )}
            </div>
          </Card>

          {/* Actions */}
          <Card className="p-6">
            <div className="flex space-x-4">
              <Button
                type="button"
                variant="outline"
                onClick={onCancel}
                className="flex-1"
              >
                Cancel
              </Button>

              <Button
                type="submit"
                disabled={loading || !selectedCustomer}
                className="flex-1"
              >
                {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                {isCreating ? 'Create Work Order' :
                 isCompleting ? 'Complete Work Order' :
                 'Save Changes'}
              </Button>
            </div>
          </Card>
        </form>
      </div>

      {/* Modals */}
      <AnimatePresence>
        {showCustomerSearch && (
          <Modal
            isOpen={showCustomerSearch}
            onClose={() => setShowCustomerSearch(false)}
            title="Select Customer"
          >
            <CustomerSearch
              onSelectCustomer={(customer) => {
                setSelectedCustomer(customer);
                setShowCustomerSearch(false);
              }}
              onClose={() => setShowCustomerSearch(false)}
            />
          </Modal>
        )}

        {showPhotoCapture && (
          <Modal
            isOpen={showPhotoCapture}
            onClose={() => setShowPhotoCapture(false)}
            title="Capture Photo"
          >
            <PhotoCapture
              onPhotoCapture={handlePhotoCapture}
              onCancel={() => setShowPhotoCapture(false)}
            />
          </Modal>
        )}

        {showLocationMap && selectedCustomer && (
          <Modal
            isOpen={showLocationMap}
            onClose={() => setShowLocationMap(false)}
            title="Location & Route"
            size="lg"
          >
            <div className="h-96">
              <WorkOrderRoutingMap
                workOrders={[{
                  id: 'current',
                  location: {
                    coordinates: selectedCustomer.coordinates || [0, 0],
                    address: selectedCustomer.address
                  }
                } as any]}
                currentLocation={currentLocation}
                onRouteSelected={() => {}}
              />
            </div>
          </Modal>
        )}
      </AnimatePresence>
    </>
  );
}
