/**
 * Core types for DotMac platform
 */

export type PortalType = 'admin' | 'customer' | 'reseller';

export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  roles?: string[];
  tenantId: string;
  permissions: string[];
  avatar?: string;
  company?: string;
  lastLoginAt?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Tenant {
  id: string;
  name: string;
  domain: string;
  plan: string;
  status: 'active' | 'suspended' | 'cancelled';
  settings: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface Customer {
  id: string;
  tenantId: string;
  email: string;
  name: string;
  phone?: string;
  address?: Address;
  status: 'active' | 'suspended' | 'cancelled';
  services: CustomerService[];
  billingInfo: BillingInfo;
  createdAt: string;
  updatedAt: string;
}

export interface Address {
  street: string;
  city: string;
  state: string;
  zipCode: string;
  country: string;
}

export interface CustomerService {
  id: string;
  customerId: string;
  serviceId: string;
  serviceName: string;
  status: 'active' | 'suspended' | 'pending' | 'cancelled';
  plan: string;
  bandwidth: string;
  ipAddress?: string;
  installationDate?: string;
  monthlyRate: number;
  createdAt: string;
  updatedAt: string;
}

export interface BillingInfo {
  customerId: string;
  billingCycle: 'monthly' | 'quarterly' | 'yearly';
  paymentMethod: 'credit_card' | 'bank_transfer' | 'check';
  lastPaymentDate?: string;
  nextBillingDate: string;
  balance: number;
  creditLimit: number;
}

export interface Invoice {
  id: string;
  customerId: string;
  invoiceNumber: string;
  amount: number;
  tax: number;
  total: number;
  status: 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled';
  dueDate: string;
  paidDate?: string;
  items: InvoiceItem[];
  createdAt: string;
  updatedAt: string;
}

export interface InvoiceItem {
  id: string;
  description: string;
  quantity: number;
  unitPrice: number;
  total: number;
  serviceId?: string;
}

export interface NetworkDevice {
  id: string;
  name: string;
  type: 'router' | 'switch' | 'access_point' | 'modem' | 'server';
  ipAddress: string;
  macAddress: string;
  status: 'online' | 'offline' | 'warning' | 'error';
  location: string;
  lastSeen: string;
  uptime: number;
  metrics: DeviceMetrics;
  createdAt: string;
  updatedAt: string;
}

export interface DeviceMetrics {
  cpuUsage: number;
  memoryUsage: number;
  diskUsage: number;
  networkUtilization: number;
  temperature?: number;
  powerStatus?: 'normal' | 'warning' | 'critical';
}

export interface ChatMessage {
  id: string;
  chatId: string;
  senderId: string;
  senderName: string;
  senderType: 'customer' | 'agent' | 'system';
  content: string;
  timestamp: string;
  status: 'sent' | 'delivered' | 'read';
  attachments?: ChatAttachment[];
}

export interface ChatAttachment {
  id: string;
  filename: string;
  fileSize: number;
  mimeType: string;
  url: string;
}

export interface ChatSession {
  id: string;
  customerId: string;
  agentId?: string;
  status: 'waiting' | 'active' | 'resolved' | 'closed';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  subject?: string;
  tags: string[];
  messages: ChatMessage[];
  startedAt: string;
  endedAt?: string;
  rating?: number;
  feedback?: string;
}

export interface Notification {
  id: string;
  userId: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  read: boolean;
  actionUrl?: string;
  metadata?: Record<string, unknown>;
  createdAt: string;
  expiresAt?: string;
}

export interface ServicePlan {
  id: string;
  name: string;
  description: string;
  type: 'internet' | 'voice' | 'tv' | 'bundle';
  bandwidth: string;
  monthlyRate: number;
  setupFee: number;
  features: string[];
  available: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface NetworkAlert {
  id: string;
  deviceId: string;
  deviceName: string;
  severity: 'info' | 'warning' | 'critical';
  type: 'connectivity' | 'performance' | 'security' | 'maintenance';
  title: string;
  description: string;
  status: 'active' | 'acknowledged' | 'resolved';
  acknowledgedBy?: string;
  acknowledgedAt?: string;
  resolvedAt?: string;
  createdAt: string;
}

// API Response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  traceId?: string;
}

// Query parameters
export interface QueryParams {
  page?: number;
  limit?: number;
  sort?: string;
  order?: 'asc' | 'desc';
  search?: string;
  filters?: Record<string, unknown>;
}

// Dashboard metrics
export interface DashboardMetrics {
  totalCustomers: number;
  activeServices: number;
  monthlyRevenue: number;
  networkUptime: number;
  supportTickets: {
    open: number;
    inProgress: number;
    resolved: number;
  };
  recentAlerts: NetworkAlert[];
  topServices: Array<{
    name: string;
    count: number;
    revenue: number;
  }>;
}

// Re-export auth types
export * from './auth';
