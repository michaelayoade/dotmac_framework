/**
 * DotMac Platform TypeScript SDK
 * Auto-generated from OpenAPI specification
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

export interface DotMacConfig {
  baseURL?: string;
  apiKey?: string;
  accessToken?: string;
  timeout?: number;
}

export interface Customer {
  id: string;
  customer_number: string;
  display_name: string;
  customer_type: 'residential' | 'business' | 'enterprise';
  state: 'prospect' | 'active' | 'suspended' | 'churned';
  created_at: string;
  updated_at: string;
}

export interface CreateCustomerRequest {
  display_name: string;
  customer_type: 'residential' | 'business' | 'enterprise';
  primary_email: string;
  primary_phone: string;
  service_address?: Record<string, any>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface Ticket {
  id: string;
  customer_id: string;
  subject: string;
  status: 'open' | 'in_progress' | 'resolved' | 'closed';
  priority: 'low' | 'medium' | 'high' | 'critical';
  created_at: string;
  updated_at: string;
}

export interface Invoice {
  id: string;
  customer_id: string;
  amount: number;
  currency: string;
  status: 'draft' | 'sent' | 'paid' | 'overdue';
  due_date: string;
  created_at: string;
}

export class DotMacClient {
  private client: AxiosInstance;
  public customers: CustomerService;
  public tickets: TicketService;
  public invoices: InvoiceService;

  constructor(config: DotMacConfig = {}) {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (config.apiKey) {
      headers['X-API-Key'] = config.apiKey;
    } else if (config.accessToken) {
      headers['Authorization'] = `Bearer ${config.accessToken}`;
    }

    this.client = axios.create({
      baseURL: config.baseURL || 'https://api.dotmac.com',
      timeout: config.timeout || 30000,
      headers,
    });

    // Initialize services
    this.customers = new CustomerService(this.client);
    this.tickets = new TicketService(this.client);
    this.invoices = new InvoiceService(this.client);
  }
}

export class CustomerService {
  constructor(private client: AxiosInstance) {}

  async create(data: CreateCustomerRequest): Promise<Customer> {
    const response = await this.client.post<Customer>('/api/v1/customers', data);
    return response.data;
  }

  async get(customerId: string): Promise<Customer> {
    const response = await this.client.get<Customer>(`/api/v1/customers/${customerId}`);
    return response.data;
  }

  async list(params?: {
    page?: number;
    limit?: number;
    state?: string;
    customer_type?: string;
  }): Promise<PaginatedResponse<Customer>> {
    const response = await this.client.get<PaginatedResponse<Customer>>('/api/v1/customers', {
      params,
    });
    return response.data;
  }

  async update(customerId: string, data: Partial<CreateCustomerRequest>): Promise<Customer> {
    const response = await this.client.patch<Customer>(`/api/v1/customers/${customerId}`, data);
    return response.data;
  }

  async activate(customerId: string, reason?: string): Promise<Customer> {
    const response = await this.client.post<Customer>(
      `/api/v1/customers/${customerId}/activate`,
      { reason }
    );
    return response.data;
  }

  async suspend(customerId: string, reason: string): Promise<Customer> {
    const response = await this.client.post<Customer>(
      `/api/v1/customers/${customerId}/suspend`,
      { reason }
    );
    return response.data;
  }

  async delete(customerId: string, force?: boolean): Promise<void> {
    await this.client.delete(`/api/v1/customers/${customerId}`, {
      params: { force },
    });
  }
}

export class TicketService {
  constructor(private client: AxiosInstance) {}

  async create(data: {
    customer_id: string;
    subject: string;
    description: string;
    priority?: string;
  }): Promise<Ticket> {
    const response = await this.client.post<Ticket>('/api/v1/tickets', data);
    return response.data;
  }

  async get(ticketId: string): Promise<Ticket> {
    const response = await this.client.get<Ticket>(`/api/v1/tickets/${ticketId}`);
    return response.data;
  }

  async list(params?: {
    status?: string;
    priority?: string;
  }): Promise<PaginatedResponse<Ticket>> {
    const response = await this.client.get<PaginatedResponse<Ticket>>('/api/v1/tickets', {
      params,
    });
    return response.data;
  }

  async addComment(ticketId: string, comment: string): Promise<void> {
    await this.client.post(`/api/v1/tickets/${ticketId}/comments`, { comment });
  }

  async close(ticketId: string, resolution: string): Promise<Ticket> {
    const response = await this.client.post<Ticket>(`/api/v1/tickets/${ticketId}/close`, {
      resolution,
    });
    return response.data;
  }
}

export class InvoiceService {
  constructor(private client: AxiosInstance) {}

  async list(params?: {
    customer_id?: string;
    status?: string;
  }): Promise<PaginatedResponse<Invoice>> {
    const response = await this.client.get<PaginatedResponse<Invoice>>('/api/v1/invoices', {
      params,
    });
    return response.data;
  }

  async get(invoiceId: string): Promise<Invoice> {
    const response = await this.client.get<Invoice>(`/api/v1/invoices/${invoiceId}`);
    return response.data;
  }
}

export default DotMacClient;
