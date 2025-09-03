/**
 * Technician Mobile App Component
 * 
 * Mobile-optimized interface for field technicians to manage their daily work orders,
 * check in/out, update status, capture photos, and track time.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  MapPin, Clock, Camera, CheckCircle, AlertCircle, 
  Navigation, Phone, FileText, User, Settings,
  PlayCircle, PauseCircle, Square, Upload, Wifi, WifiOff
} from 'lucide-react';

// Types
interface WorkOrder {
  id: string;
  work_order_number: string;
  title: string;
  work_order_type: string;
  status: string;
  priority: string;
  customer_name?: string;
  customer_phone?: string;
  service_address: string;
  access_instructions?: string;
  scheduled_date?: string;
  scheduled_time_start?: string;
  estimated_duration?: number;
  progress_percentage: number;
  checklist_items?: ChecklistItem[];
  required_equipment?: EquipmentItem[];
}

interface ChecklistItem {
  id: string;
  text: string;
  completed: boolean;
  required: boolean;
  evidence?: {
    type: 'photo' | 'signature' | 'measurement';
    data: string;
    timestamp: string;
  };
}

interface EquipmentItem {
  type: string;
  model?: string;
  serial_number?: string;
  quantity: number;
  status: string;
}

interface TimeEntry {
  id: string;
  work_order_id: string;
  activity_type: string;
  start_time: string;
  end_time?: string;
  duration_minutes?: number;
}

const TechnicianMobileApp: React.FC = () => {
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [activeWorkOrder, setActiveWorkOrder] = useState<WorkOrder | null>(null);
  const [currentLocation, setCurrentLocation] = useState<{lat: number, lng: number} | null>(null);
  const [timeEntries, setTimeEntries] = useState<TimeEntry[]>([]);
  const [activeTimer, setActiveTimer] = useState<string | null>(null);
  const [photos, setPhotos] = useState<{[workOrderId: string]: File[]}>({});
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load technician's daily schedule
  const loadSchedule = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/v1/field-operations/mobile/technician/schedule', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to load schedule');
      }

      const scheduleData = await response.json();
      setWorkOrders(scheduleData);
      
      // Set first scheduled work order as active if none selected
      if (!activeWorkOrder && scheduleData.length > 0) {
        const nextOrder = scheduleData.find((wo: WorkOrder) => 
          wo.status === 'scheduled' || wo.status === 'dispatched'
        );
        if (nextOrder) {
          setActiveWorkOrder(nextOrder);
        }
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load schedule');
    } finally {
      setLoading(false);
    }
  }, [activeWorkOrder]);

  // Get current location
  const updateLocation = useCallback(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setCurrentLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude
          });
        },
        (error) => {
          console.error('Location error:', error);
        },
        { enableHighAccuracy: true, timeout: 10000 }
      );
    }
  }, []);

  useEffect(() => {
    loadSchedule();
    updateLocation();

    // Update location every 5 minutes
    const locationInterval = setInterval(updateLocation, 300000);

    // Listen for online/offline events
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      clearInterval(locationInterval);
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [loadSchedule, updateLocation]);

  // Check in to work order
  const handleCheckIn = async (workOrderId: string) => {
    if (!currentLocation) {
      alert('Location required for check-in');
      updateLocation();
      return;
    }

    try {
      const response = await fetch(
        `/api/v1/field-operations/mobile/work-orders/${workOrderId}/checkin?latitude=${currentLocation.lat}&longitude=${currentLocation.lng}`,
        {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Check-in failed');
      }

      const result = await response.json();
      alert('Successfully checked in!');
      
      // Update local work order status
      setWorkOrders(prev => prev.map(wo => 
        wo.id === workOrderId 
          ? { ...wo, status: 'on_site' }
          : wo
      ));

    } catch (err) {
      alert(`Check-in failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  // Update work order status
  const updateWorkOrderStatus = async (workOrderId: string, newStatus: string, notes?: string) => {
    try {
      const params = new URLSearchParams();
      if (currentLocation) {
        params.append('latitude', currentLocation.lat.toString());
        params.append('longitude', currentLocation.lng.toString());
      }

      const response = await fetch(
        `/api/v1/field-operations/work-orders/${workOrderId}/status?${params}`,
        {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            new_status: newStatus,
            notes: notes
          })
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Status update failed');
      }

      // Update local state
      setWorkOrders(prev => prev.map(wo => 
        wo.id === workOrderId 
          ? { ...wo, status: newStatus }
          : wo
      ));

      if (activeWorkOrder?.id === workOrderId) {
        setActiveWorkOrder(prev => prev ? { ...prev, status: newStatus } : null);
      }

    } catch (err) {
      alert(`Status update failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  // Start time tracking
  const startTimer = (workOrderId: string, activityType: string) => {
    const newEntry: TimeEntry = {
      id: Date.now().toString(),
      work_order_id: workOrderId,
      activity_type: activityType,
      start_time: new Date().toISOString()
    };

    setTimeEntries(prev => [...prev, newEntry]);
    setActiveTimer(newEntry.id);
  };

  // Stop time tracking
  const stopTimer = (entryId: string) => {
    const endTime = new Date().toISOString();
    
    setTimeEntries(prev => prev.map(entry => {
      if (entry.id === entryId) {
        const startTime = new Date(entry.start_time);
        const endTimeDate = new Date(endTime);
        const durationMinutes = Math.floor((endTimeDate.getTime() - startTime.getTime()) / 60000);
        
        return {
          ...entry,
          end_time: endTime,
          duration_minutes: durationMinutes
        };
      }
      return entry;
    }));
    
    setActiveTimer(null);
  };

  // Handle photo capture
  const handlePhotoCapture = (workOrderId: string, file: File) => {
    setPhotos(prev => ({
      ...prev,
      [workOrderId]: [...(prev[workOrderId] || []), file]
    }));
  };

  // Update checklist item
  const updateChecklistItem = (workOrderId: string, itemId: string, completed: boolean) => {
    if (activeWorkOrder?.id === workOrderId) {
      setActiveWorkOrder(prev => {
        if (!prev?.checklist_items) return prev;
        
        const updatedItems = prev.checklist_items.map(item =>
          item.id === itemId ? { ...item, completed } : item
        );
        
        const completedCount = updatedItems.filter(item => item.completed).length;
        const progress = Math.floor((completedCount / updatedItems.length) * 100);
        
        return {
          ...prev,
          checklist_items: updatedItems,
          progress_percentage: progress
        };
      });
    }
  };

  // Get status color
  const getStatusColor = (status: string) => {
    const colors = {
      'scheduled': 'bg-blue-100 text-blue-800',
      'dispatched': 'bg-yellow-100 text-yellow-800',
      'on_site': 'bg-green-100 text-green-800',
      'in_progress': 'bg-blue-100 text-blue-800',
      'completed': 'bg-green-100 text-green-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getPriorityColor = (priority: string) => {
    const colors = {
      'emergency': 'text-red-600',
      'urgent': 'text-red-500',
      'high': 'text-orange-500',
      'normal': 'text-gray-600',
      'low': 'text-gray-400'
    };
    return colors[priority] || 'text-gray-600';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-600">Loading schedule...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-blue-600 text-white">
        <div className="px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold">Field Tech</h1>
            <p className="text-blue-100 text-sm">
              {new Date().toLocaleDateString()}
            </p>
          </div>
          <div className="flex items-center space-x-3">
            {isOnline ? (
              <Wifi className="h-5 w-5" />
            ) : (
              <WifiOff className="h-5 w-5 text-red-300" />
            )}
            <Settings className="h-5 w-5" />
          </div>
        </div>
        
        {/* Connection Status */}
        {!isOnline && (
          <div className="bg-red-500 px-4 py-2 text-center">
            <p className="text-sm">Offline - Changes will sync when connected</p>
          </div>
        )}
      </div>

      {/* Work Orders List */}
      <div className="px-4 py-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Today's Schedule</h2>
          <span className="text-sm text-gray-600">{workOrders.length} jobs</span>
        </div>

        <div className="space-y-3">
          {workOrders.map((workOrder) => (
            <div
              key={workOrder.id}
              className={`bg-white rounded-lg shadow-sm border-l-4 ${
                workOrder.id === activeWorkOrder?.id 
                  ? 'border-blue-500 ring-2 ring-blue-100' 
                  : 'border-gray-200'
              } p-4`}
              onClick={() => setActiveWorkOrder(workOrder)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <h3 className="text-sm font-medium text-gray-900">
                      {workOrder.work_order_number}
                    </h3>
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(workOrder.status)}`}>
                      {workOrder.status.replace('_', ' ')}
                    </span>
                    <Clock className={`h-4 w-4 ${getPriorityColor(workOrder.priority)}`} />
                  </div>
                  
                  <p className="text-sm text-gray-600 mt-1">{workOrder.title}</p>
                  
                  <div className="flex items-center mt-2 text-xs text-gray-500">
                    <MapPin className="h-3 w-3 mr-1" />
                    <span className="flex-1">{workOrder.service_address}</span>
                  </div>
                  
                  {workOrder.customer_name && (
                    <div className="flex items-center mt-1 text-xs text-gray-500">
                      <User className="h-3 w-3 mr-1" />
                      <span>{workOrder.customer_name}</span>
                      {workOrder.customer_phone && (
                        <a 
                          href={`tel:${workOrder.customer_phone}`}
                          className="ml-2 text-blue-600"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Phone className="h-3 w-3" />
                        </a>
                      )}
                    </div>
                  )}
                  
                  {workOrder.scheduled_time_start && (
                    <div className="flex items-center mt-1 text-xs text-gray-500">
                      <Clock className="h-3 w-3 mr-1" />
                      <span>{new Date(`2000-01-01T${workOrder.scheduled_time_start}`).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                      {workOrder.estimated_duration && (
                        <span className="ml-2">({workOrder.estimated_duration}min)</span>
                      )}
                    </div>
                  )}
                </div>
                
                <div className="ml-4 flex flex-col items-end space-y-2">
                  {workOrder.status === 'scheduled' || workOrder.status === 'dispatched' ? (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleCheckIn(workOrder.id);
                      }}
                      className="px-3 py-1 bg-green-600 text-white text-xs rounded font-medium"
                    >
                      Check In
                    </button>
                  ) : workOrder.status === 'on_site' ? (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        updateWorkOrderStatus(workOrder.id, 'in_progress');
                      }}
                      className="px-3 py-1 bg-blue-600 text-white text-xs rounded font-medium"
                    >
                      Start Work
                    </button>
                  ) : workOrder.status === 'in_progress' ? (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        updateWorkOrderStatus(workOrder.id, 'completed');
                      }}
                      className="px-3 py-1 bg-green-600 text-white text-xs rounded font-medium"
                    >
                      Complete
                    </button>
                  ) : (
                    <CheckCircle className="h-5 w-5 text-green-600" />
                  )}
                  
                  <div className="text-xs text-gray-500">
                    {workOrder.progress_percentage}%
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Active Work Order Details */}
      {activeWorkOrder && (
        <div className="mt-6 bg-white border-t">
          <div className="px-4 py-3 border-b bg-gray-50">
            <h3 className="text-lg font-medium text-gray-900">
              {activeWorkOrder.work_order_number} - {activeWorkOrder.title}
            </h3>
          </div>
          
          {/* Time Tracking */}
          <div className="px-4 py-3 border-b">
            <h4 className="text-sm font-medium text-gray-900 mb-2">Time Tracking</h4>
            <div className="flex items-center space-x-2">
              {!activeTimer ? (
                <>
                  <button
                    onClick={() => startTimer(activeWorkOrder.id, 'work')}
                    className="flex items-center px-3 py-2 bg-green-600 text-white rounded text-sm"
                  >
                    <PlayCircle className="h-4 w-4 mr-1" />
                    Start Work
                  </button>
                  <button
                    onClick={() => startTimer(activeWorkOrder.id, 'travel')}
                    className="flex items-center px-3 py-2 bg-blue-600 text-white rounded text-sm"
                  >
                    <Navigation className="h-4 w-4 mr-1" />
                    Travel
                  </button>
                </>
              ) : (
                <button
                  onClick={() => stopTimer(activeTimer)}
                  className="flex items-center px-3 py-2 bg-red-600 text-white rounded text-sm"
                >
                  <Square className="h-4 w-4 mr-1" />
                  Stop Timer
                </button>
              )}
            </div>
          </div>

          {/* Checklist */}
          {activeWorkOrder.checklist_items && (
            <div className="px-4 py-3 border-b">
              <h4 className="text-sm font-medium text-gray-900 mb-2">Checklist</h4>
              <div className="space-y-2">
                {activeWorkOrder.checklist_items.map((item) => (
                  <label key={item.id} className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={item.completed}
                      onChange={(e) => updateChecklistItem(activeWorkOrder.id, item.id, e.target.checked)}
                      className="rounded border-gray-300"
                    />
                    <span className={`text-sm ${item.completed ? 'line-through text-gray-500' : 'text-gray-900'}`}>
                      {item.text}
                      {item.required && <span className="text-red-500 ml-1">*</span>}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Photo Capture */}
          <div className="px-4 py-3 border-b">
            <h4 className="text-sm font-medium text-gray-900 mb-2">Photos</h4>
            <div className="flex items-center space-x-2">
              <input
                type="file"
                accept="image/*"
                capture="camera"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    handlePhotoCapture(activeWorkOrder.id, file);
                  }
                }}
                className="hidden"
                id="photo-capture"
              />
              <label
                htmlFor="photo-capture"
                className="flex items-center px-3 py-2 bg-gray-600 text-white rounded text-sm cursor-pointer"
              >
                <Camera className="h-4 w-4 mr-1" />
                Take Photo
              </label>
              
              {photos[activeWorkOrder.id]?.length > 0 && (
                <span className="text-xs text-gray-500">
                  {photos[activeWorkOrder.id].length} photo(s) captured
                </span>
              )}
            </div>
          </div>

          {/* Notes */}
          <div className="px-4 py-3">
            <h4 className="text-sm font-medium text-gray-900 mb-2">Work Notes</h4>
            <textarea
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
              placeholder="Add work notes..."
            />
            <button className="mt-2 px-3 py-1 bg-blue-600 text-white rounded text-sm">
              Save Notes
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TechnicianMobileApp;