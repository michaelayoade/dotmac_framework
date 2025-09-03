/**
 * Dynamic Work Order Form Component
 * Handles work order creation and updates with validation and offline support
 */

'use client';

import { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Save,
  X,
  AlertCircle,
  CheckCircle,
  Clock,
  MapPin,
  User,
  Calendar,
  Settings,
  Camera,
  FileText,
  Plus,
  Trash2,
  Loader2,
} from 'lucide-react';
import { WorkOrderSchema, ChecklistItemSchema } from '../../lib/validation/schemas';
import { WorkOrder, ChecklistItem, Customer } from '../../lib/enhanced-offline-db';
import { SignatureCapture } from './SignatureCapture';
import { PhotoCapture } from './PhotoCapture';
import { CustomerSearch } from '../customers/CustomerSearch';
import { sanitizeObject } from '../../lib/validation/sanitization';

interface WorkOrderFormProps {
  workOrder?: WorkOrder;
  customer?: Customer;
  onSave: (workOrder: Partial<WorkOrder>) => void;
  onCancel: () => void;
  mode: 'create' | 'edit' | 'complete';
  technicianId: string;
}

export function WorkOrderForm({
  workOrder,
  customer: initialCustomer,
  onSave,
  onCancel,
  mode,
  technicianId,
}: WorkOrderFormProps) {
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(
    initialCustomer || null
  );
  const [showCustomerSearch, setShowCustomerSearch] = useState(!initialCustomer && !workOrder);
  const [showSignature, setShowSignature] = useState(false);
  const [showPhotoCapture, setShowPhotoCapture] = useState(false);
  const [photos, setPhotos] = useState<string[]>(workOrder?.photos || []);
  const [checklist, setChecklist] = useState<ChecklistItem[]>(workOrder?.checklist || []);
  const [signature, setSignature] = useState<string | null>(workOrder?.signature || null);
  const [loading, setLoading] = useState(false);

  const isCompleting = mode === 'complete';
  const isEditing = mode === 'edit';
  const isCreating = mode === 'create';

  const defaultValues = workOrder
    ? {
        title: workOrder.title,
        description: workOrder.description,
        priority: workOrder.priority,
        scheduledDate: workOrder.scheduledDate.slice(0, 16), // Format for datetime-local
        notes: workOrder.notes,
        equipment: workOrder.equipment,
      }
    : {
        title: '',
        description: '',
        priority: 'medium' as const,
        scheduledDate: new Date().toISOString().slice(0, 16),
        notes: '',
        equipment: {
          type: '',
          required: [],
        },
      };

  const {
    control,
    handleSubmit,
    formState: { errors, isDirty },
    setValue,
    watch,
    reset,
  } = useForm({
    resolver: zodResolver(WorkOrderSchema.partial()),
    defaultValues,
  });

  const watchedPriority = watch('priority');

  useEffect(() => {
    if (workOrder && selectedCustomer) {
      // Pre-fill form with work order data
      reset({
        title: workOrder.title,
        description: workOrder.description,
        priority: workOrder.priority,
        scheduledDate: workOrder.scheduledDate.slice(0, 16),
        notes: workOrder.notes,
        equipment: workOrder.equipment,
      });
    }
  }, [workOrder, selectedCustomer, reset]);

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
    setChecklist(checklist.map((item) => (item.id === id ? { ...item, ...updates } : item)));
  };

  const removeChecklistItem = (id: string) => {
    setChecklist(checklist.filter((item) => item.id !== id));
  };

  const addEquipmentRequirement = () => {
    const equipment = watch('equipment') || { type: '', required: [] };
    setValue(
      'equipment',
      {
        ...equipment,
        required: [...equipment.required, ''],
      },
      { shouldDirty: true }
    );
  };

  const updateEquipmentRequirement = (index: number, value: string) => {
    const equipment = watch('equipment') || { type: '', required: [] };
    const updated = [...equipment.required];
    updated[index] = value;
    setValue(
      'equipment',
      {
        ...equipment,
        required: updated,
      },
      { shouldDirty: true }
    );
  };

  const removeEquipmentRequirement = (index: number) => {
    const equipment = watch('equipment') || { type: '', required: [] };
    setValue(
      'equipment',
      {
        ...equipment,
        required: equipment.required.filter((_, i) => i !== index),
      },
      { shouldDirty: true }
    );
  };

  const handlePhotoCapture = (photoDataUrl: string) => {
    setPhotos([...photos, photoDataUrl]);
    setShowPhotoCapture(false);
  };

  const removePhoto = (index: number) => {
    setPhotos(photos.filter((_, i) => i !== index));
  };

  const handleSignatureCapture = (signatureDataUrl: string) => {
    setSignature(signatureDataUrl);
    setShowSignature(false);
  };

  const onSubmit = async (data: any) => {
    if (!selectedCustomer) {
      alert('Please select a customer');
      return;
    }

    setLoading(true);

    try {
      const sanitizedData = sanitizeObject(data);

      const workOrderData: Partial<WorkOrder> = {
        ...sanitizedData,
        id: workOrder?.id || `WO_${Date.now()}_${Math.random().toString(36).slice(2)}`,
        customerId: selectedCustomer.id,
        technicianId,
        scheduledDate: new Date(sanitizedData.scheduledDate).toISOString(),
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
        signature,
        status: isCompleting ? 'completed' : workOrder?.status || 'pending',
        completedAt: isCompleting ? new Date().toISOString() : workOrder?.completedAt,
        syncStatus: 'pending' as const,
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
    switch (priority) {
      case 'urgent':
        return 'border-red-300 bg-red-50 text-red-700';
      case 'high':
        return 'border-orange-300 bg-orange-50 text-orange-700';
      case 'medium':
        return 'border-yellow-300 bg-yellow-50 text-yellow-700';
      case 'low':
        return 'border-green-300 bg-green-50 text-green-700';
      default:
        return 'border-gray-300 bg-gray-50 text-gray-700';
    }
  };

  return (
    <>
      <div className='space-y-4'>
        {/* Header */}
        <div className='mobile-card'>
          <div className='flex items-center justify-between mb-4'>
            <div>
              <h1 className='text-lg font-bold text-gray-900'>
                {isCreating
                  ? 'New Work Order'
                  : isCompleting
                    ? 'Complete Work Order'
                    : 'Edit Work Order'}
              </h1>
              {workOrder && <p className='text-sm text-gray-600'>#{workOrder.id}</p>}
            </div>

            <button
              onClick={onCancel}
              className='w-10 h-10 bg-gray-100 hover:bg-gray-200 rounded-full flex items-center justify-center text-gray-600'
            >
              <X className='w-5 h-5' />
            </button>
          </div>

          {/* Customer Selection */}
          {selectedCustomer ? (
            <div className='bg-gray-50 rounded-lg p-3 mb-4'>
              <div className='flex items-center justify-between'>
                <div className='flex items-center space-x-3'>
                  <div className='w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center'>
                    <User className='w-4 h-4 text-primary-600' />
                  </div>
                  <div>
                    <h3 className='font-medium text-gray-900'>{selectedCustomer.name}</h3>
                    <p className='text-xs text-gray-600'>{selectedCustomer.serviceId}</p>
                  </div>
                </div>

                {isCreating && (
                  <button
                    onClick={() => {
                      setSelectedCustomer(null);
                      setShowCustomerSearch(true);
                    }}
                    className='text-primary-600 hover:text-primary-700 text-sm font-medium'
                  >
                    Change
                  </button>
                )}
              </div>

              <div className='mt-2 text-xs text-gray-600 flex items-center'>
                <MapPin className='w-3 h-3 mr-1' />
                {selectedCustomer.address}
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowCustomerSearch(true)}
              className='w-full bg-primary-50 hover:bg-primary-100 border border-primary-200 rounded-lg p-4 text-center transition-colors'
            >
              <User className='w-6 h-6 text-primary-600 mx-auto mb-2' />
              <span className='text-primary-700 font-medium'>Select Customer</span>
            </button>
          )}
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className='space-y-4'>
          {/* Basic Information */}
          <div className='mobile-card'>
            <h2 className='font-semibold text-gray-900 mb-3'>Basic Information</h2>

            <div className='space-y-4'>
              {/* Title */}
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>Title *</label>
                <Controller
                  name='title'
                  control={control}
                  rules={{ required: 'Title is required' }}
                  render={({ field }) => (
                    <input
                      {...field}
                      type='text'
                      className={`mobile-input ${errors.title ? 'border-red-300' : ''}`}
                      placeholder='Brief description of the work'
                    />
                  )}
                />
                {errors.title && (
                  <p className='mt-1 text-sm text-red-600 flex items-center'>
                    <AlertCircle className='w-3 h-3 mr-1' />
                    {errors.title.message as string}
                  </p>
                )}
              </div>

              {/* Description */}
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>
                  Description *
                </label>
                <Controller
                  name='description'
                  control={control}
                  rules={{ required: 'Description is required' }}
                  render={({ field }) => (
                    <textarea
                      {...field}
                      rows={3}
                      className={`mobile-input ${errors.description ? 'border-red-300' : ''}`}
                      placeholder='Detailed description of the work to be performed'
                    />
                  )}
                />
                {errors.description && (
                  <p className='mt-1 text-sm text-red-600 flex items-center'>
                    <AlertCircle className='w-3 h-3 mr-1' />
                    {errors.description.message as string}
                  </p>
                )}
              </div>

              {/* Priority and Schedule */}
              <div className='grid grid-cols-2 gap-3'>
                <div>
                  <label className='block text-sm font-medium text-gray-700 mb-1'>Priority</label>
                  <Controller
                    name='priority'
                    control={control}
                    render={({ field }) => (
                      <select
                        {...field}
                        className={`mobile-input ${getPriorityColor(watchedPriority || 'medium')}`}
                      >
                        <option value='low'>Low</option>
                        <option value='medium'>Medium</option>
                        <option value='high'>High</option>
                        <option value='urgent'>Urgent</option>
                      </select>
                    )}
                  />
                </div>

                <div>
                  <label className='block text-sm font-medium text-gray-700 mb-1'>
                    Scheduled Date *
                  </label>
                  <Controller
                    name='scheduledDate'
                    control={control}
                    rules={{ required: 'Scheduled date is required' }}
                    render={({ field }) => (
                      <input
                        {...field}
                        type='datetime-local'
                        className={`mobile-input ${errors.scheduledDate ? 'border-red-300' : ''}`}
                      />
                    )}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Equipment Requirements */}
          <div className='mobile-card'>
            <div className='flex items-center justify-between mb-3'>
              <h2 className='font-semibold text-gray-900'>Equipment</h2>
              <button
                type='button'
                onClick={addEquipmentRequirement}
                className='text-primary-600 hover:text-primary-700 text-sm font-medium flex items-center'
              >
                <Plus className='w-3 h-3 mr-1' />
                Add Item
              </button>
            </div>

            <div className='space-y-3'>
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>
                  Equipment Type
                </label>
                <Controller
                  name='equipment.type'
                  control={control}
                  render={({ field }) => (
                    <input
                      {...field}
                      type='text'
                      className='mobile-input'
                      placeholder='e.g., Fiber ONT, Cable Modem'
                    />
                  )}
                />
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>
                  Required Items
                </label>
                <div className='space-y-2'>
                  {(watch('equipment.required') || []).map((item: string, index: number) => (
                    <div key={index} className='flex items-center space-x-2'>
                      <input
                        value={item}
                        onChange={(e) => updateEquipmentRequirement(index, e.target.value)}
                        className='mobile-input flex-1'
                        placeholder='Equipment or tool needed'
                      />
                      <button
                        type='button'
                        onClick={() => removeEquipmentRequirement(index)}
                        className='w-8 h-8 bg-red-100 hover:bg-red-200 text-red-600 rounded flex items-center justify-center'
                      >
                        <Trash2 className='w-3 h-3' />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Checklist */}
          <div className='mobile-card'>
            <div className='flex items-center justify-between mb-3'>
              <h2 className='font-semibold text-gray-900'>Checklist</h2>
              <button
                type='button'
                onClick={addChecklistItem}
                className='text-primary-600 hover:text-primary-700 text-sm font-medium flex items-center'
              >
                <Plus className='w-3 h-3 mr-1' />
                Add Item
              </button>
            </div>

            <div className='space-y-2'>
              {checklist.map((item, index) => (
                <div key={item.id} className='flex items-start space-x-3 p-2 bg-gray-50 rounded'>
                  <input
                    type='checkbox'
                    checked={item.completed}
                    onChange={(e) =>
                      updateChecklistItem(item.id, {
                        completed: e.target.checked,
                        timestamp: e.target.checked ? new Date().toISOString() : undefined,
                      })
                    }
                    className='mt-1'
                    disabled={!isCompleting}
                  />

                  <input
                    value={item.text}
                    onChange={(e) => updateChecklistItem(item.id, { text: e.target.value })}
                    className='flex-1 bg-transparent border-none focus:ring-0 p-0 text-sm'
                    placeholder='Checklist item'
                  />

                  <div className='flex items-center space-x-1'>
                    <input
                      type='checkbox'
                      checked={item.required}
                      onChange={(e) => updateChecklistItem(item.id, { required: e.target.checked })}
                      title='Required'
                      className='text-red-600'
                    />
                    <span className='text-xs text-gray-500'>Req</span>

                    <button
                      type='button'
                      onClick={() => removeChecklistItem(item.id)}
                      className='text-red-600 hover:text-red-800'
                    >
                      <Trash2 className='w-3 h-3' />
                    </button>
                  </div>
                </div>
              ))}

              {checklist.length === 0 && (
                <div className='text-center py-4 text-gray-500 text-sm'>
                  No checklist items yet. Add some to track progress.
                </div>
              )}
            </div>
          </div>

          {/* Photos */}
          <div className='mobile-card'>
            <div className='flex items-center justify-between mb-3'>
              <h2 className='font-semibold text-gray-900'>Photos</h2>
              <button
                type='button'
                onClick={() => setShowPhotoCapture(true)}
                className='text-primary-600 hover:text-primary-700 text-sm font-medium flex items-center'
              >
                <Camera className='w-3 h-3 mr-1' />
                Add Photo
              </button>
            </div>

            <div className='grid grid-cols-3 gap-2'>
              {photos.map((photo, index) => (
                <div key={index} className='relative group'>
                  <img
                    src={photo}
                    alt={`Work photo ${index + 1}`}
                    className='w-full h-20 object-cover rounded border'
                  />
                  <button
                    type='button'
                    onClick={() => removePhoto(index)}
                    className='absolute top-1 right-1 w-6 h-6 bg-red-600 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity'
                  >
                    <X className='w-3 h-3' />
                  </button>
                </div>
              ))}

              {photos.length === 0 && (
                <div className='col-span-3 text-center py-4 text-gray-500 text-sm'>
                  No photos added yet
                </div>
              )}
            </div>
          </div>

          {/* Digital Signature */}
          {(isCompleting || signature) && (
            <div className='mobile-card'>
              <div className='flex items-center justify-between mb-3'>
                <h2 className='font-semibold text-gray-900'>Customer Signature</h2>
                {!signature && (
                  <button
                    type='button'
                    onClick={() => setShowSignature(true)}
                    className='text-primary-600 hover:text-primary-700 text-sm font-medium'
                  >
                    Capture Signature
                  </button>
                )}
              </div>

              {signature ? (
                <div className='bg-gray-50 rounded-lg p-3'>
                  <img
                    src={signature}
                    alt='Customer Signature'
                    className='w-full h-20 object-contain bg-white rounded border'
                  />
                  <div className='flex items-center justify-between mt-2 text-xs text-gray-600'>
                    <span>Signed by: {selectedCustomer?.name || 'Customer'}</span>
                    <button
                      type='button'
                      onClick={() => setSignature(null)}
                      className='text-red-600 hover:text-red-800'
                    >
                      Clear
                    </button>
                  </div>
                </div>
              ) : isCompleting ? (
                <div className='text-center py-4 text-gray-500 text-sm'>
                  Customer signature required for completion
                </div>
              ) : null}
            </div>
          )}

          {/* Notes */}
          <div className='mobile-card'>
            <h2 className='font-semibold text-gray-900 mb-3'>Notes</h2>
            <Controller
              name='notes'
              control={control}
              render={({ field }) => (
                <textarea
                  {...field}
                  rows={4}
                  className='mobile-input'
                  placeholder='Additional notes, observations, or comments'
                />
              )}
            />
          </div>

          {/* Actions */}
          <div className='mobile-card'>
            <div className='flex space-x-3'>
              <button type='button' onClick={onCancel} className='flex-1 mobile-button-secondary'>
                Cancel
              </button>

              <button
                type='submit'
                disabled={loading || !selectedCustomer || (isCompleting && !signature)}
                className='flex-1 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-white py-3 px-4 rounded-lg font-medium transition-colors flex items-center justify-center'
              >
                {loading ? (
                  <Loader2 className='w-4 h-4 animate-spin mr-2' />
                ) : (
                  <Save className='w-4 h-4 mr-2' />
                )}
                {isCreating
                  ? 'Create Work Order'
                  : isCompleting
                    ? 'Complete Work Order'
                    : 'Save Changes'}
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Customer Search Modal */}
      <AnimatePresence>
        {showCustomerSearch && (
          <CustomerSearch
            onSelectCustomer={(customer) => {
              setSelectedCustomer(customer);
              setShowCustomerSearch(false);
            }}
            onClose={() => setShowCustomerSearch(false)}
          />
        )}
      </AnimatePresence>

      {/* Signature Capture */}
      <AnimatePresence>
        {showSignature && (
          <SignatureCapture
            onSignatureComplete={handleSignatureCapture}
            onCancel={() => setShowSignature(false)}
            customerName={selectedCustomer?.name}
            workOrderId={workOrder?.id}
            required={isCompleting}
          />
        )}
      </AnimatePresence>

      {/* Photo Capture */}
      <AnimatePresence>
        {showPhotoCapture && (
          <PhotoCapture
            onPhotoCapture={handlePhotoCapture}
            onCancel={() => setShowPhotoCapture(false)}
            workOrderId={workOrder?.id}
          />
        )}
      </AnimatePresence>
    </>
  );
}
