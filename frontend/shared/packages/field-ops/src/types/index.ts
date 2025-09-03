export interface WorkOrderLocation {
  address: string;
  coordinates: [number, number];
  apartment?: string;
  accessNotes?: string;
  geoFence?: {
    radius: number;
    center: [number, number];
  };
}

export interface WorkOrderCustomer {
  id: string;
  name: string;
  phone: string;
  email?: string;
  serviceId: string;
  preferences?: {
    contactMethod: 'phone' | 'email' | 'sms';
    language: string;
  };
}

export interface WorkOrderEquipment {
  type: string;
  model?: string;
  serialNumber?: string;
  required: string[];
  installed?: string[];
  returned?: string[];
}

export interface WorkOrderChecklistItem {
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

export interface WorkOrderPhoto {
  id: string;
  category: 'BEFORE' | 'DURING' | 'AFTER' | 'EQUIPMENT' | 'DAMAGE' | 'COMPLETION';
  url: string;
  thumbnail?: string;
  metadata: {
    timestamp: string;
    location?: [number, number];
    description?: string;
    tags?: string[];
  };
}

export interface WorkOrderNote {
  id: string;
  timestamp: string;
  author: string;
  content: string;
  type: 'general' | 'customer' | 'technical' | 'billing';
  attachments?: string[];
}

export type WorkOrderStatus =
  | 'scheduled'
  | 'dispatched'
  | 'en_route'
  | 'on_site'
  | 'in_progress'
  | 'completed'
  | 'cancelled'
  | 'requires_followup';

export type WorkOrderPriority = 'low' | 'medium' | 'high' | 'urgent' | 'emergency';

export type WorkOrderType =
  | 'installation'
  | 'maintenance'
  | 'repair'
  | 'upgrade'
  | 'inspection'
  | 'disconnect';

export interface WorkOrder {
  id: string;
  tenantId: string;
  type: WorkOrderType;
  title: string;
  description: string;

  // Scheduling
  scheduledDate: string;
  estimatedDuration: number; // minutes
  timeWindow?: {
    start: string;
    end: string;
  };

  // Assignment
  technicianId: string;
  assignedAt: string;
  assignedBy: string;

  // Status and Progress
  status: WorkOrderStatus;
  priority: WorkOrderPriority;
  progress: number; // 0-100

  // Location and Customer
  location: WorkOrderLocation;
  customer: WorkOrderCustomer;

  // Work Details
  equipment: WorkOrderEquipment;
  checklist: WorkOrderChecklistItem[];
  photos: WorkOrderPhoto[];
  notes: WorkOrderNote[];

  // Workflow Tracking
  timeline: WorkOrderTimelineEvent[];

  // Sync and Metadata
  syncStatus: 'synced' | 'pending' | 'error';
  lastModified: string;
  createdAt: string;
  completedAt?: string;

  // Business Logic
  servicePlan?: string;
  billable: boolean;
  costEstimate?: number;
  actualCost?: number;
}

export interface WorkOrderTimelineEvent {
  id: string;
  timestamp: string;
  type: 'status_change' | 'note_added' | 'photo_taken' | 'checklist_updated' | 'location_update';
  description: string;
  data?: any;
  author: string;
}

export interface WorkOrderFilter {
  status?: WorkOrderStatus[];
  priority?: WorkOrderPriority[];
  type?: WorkOrderType[];
  technicianId?: string;
  dateRange?: {
    start: string;
    end: string;
  };
  location?: {
    bounds: {
      north: number;
      south: number;
      east: number;
      west: number;
    };
  };
}

export interface WorkOrderMetrics {
  total: number;
  completed: number;
  pending: number;
  overdue: number;
  averageCompletionTime: number;
  customerSatisfaction: number;
}

// API Response Types
export interface WorkOrderResponse {
  workOrder: WorkOrder;
  success: boolean;
  message?: string;
}

export interface WorkOrderListResponse {
  workOrders: WorkOrder[];
  total: number;
  page: number;
  pageSize: number;
  success: boolean;
  message?: string;
}

export interface WorkOrderSyncPayload {
  workOrder: Partial<WorkOrder>;
  syncType: 'create' | 'update' | 'complete';
  priority: number;
}
