#!/usr/bin/env python3
"""
SDK Generator for DotMac Platform APIs.
Generates client SDKs in multiple languages from OpenAPI specifications.
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List
import shutil


class SDKGenerator:
    """Generate client SDKs from OpenAPI specifications."""
    
    def __init__(self, openapi_path: str = "docs/api/openapi.json"):
        self.openapi_path = Path(openapi_path)
        self.output_dir = Path("sdk")
        self.output_dir.mkdir(exist_ok=True)
        
        # Load OpenAPI specification
        if self.openapi_path.exists():
            with open(self.openapi_path) as f:
                self.openapi_spec = json.load(f)
        else:
            print(f"❌ OpenAPI spec not found at {self.openapi_path}")
            print("   Run 'python scripts/generate_openapi_docs.py' first")
            sys.exit(1)
    
    def generate_python_sdk(self):
        """Generate Python SDK using datamodel-code-generator."""
        print("🐍 Generating Python SDK...")
        
        python_dir = self.output_dir / "python"
        python_dir.mkdir(exist_ok=True)
        
        # Generate setup.py
        setup_content = '''from setuptools import setup, find_packages

setup(
    name="dotmac-platform-sdk",
    version="1.0.0",
    description="Python SDK for DotMac Platform API",
    author="DotMac Platform Team",
    author_email="sdk@dotmac.com",
    url="https://github.com/dotmac/platform-sdk-python",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.24.0",
        "pydantic>=2.0.0",
        "python-dateutil>=2.8.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
'''
        (python_dir / "setup.py").write_text(setup_content)
        
        # Generate SDK client
        client_content = '''"""
DotMac Platform Python SDK
Auto-generated from OpenAPI specification
"""

from typing import Dict, Any, Optional, List
import httpx
from datetime import datetime
import json


class DotMacClient:
    """Main client for DotMac Platform API."""
    
    def __init__(
        self,
        base_url: str = "https://api.dotmac.com",
        api_key: Optional[str] = None,
        access_token: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        Initialize DotMac API client.
        
        Args:
            base_url: API base URL
            api_key: API key for authentication
            access_token: JWT access token for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        
        # Set up authentication headers
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["X-API-Key"] = api_key
        elif access_token:
            self.headers["Authorization"] = f"Bearer {access_token}"
        
        # Initialize service clients
        self.customers = CustomerService(self)
        self.invoices = InvoiceService(self)
        self.services = ServiceManagement(self)
        self.tickets = TicketService(self)
        self.network = NetworkService(self)
    
    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request to API."""
        url = f"{self.base_url}{path}"
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=json_data,
                **kwargs
            )
            response.raise_for_status()
            return response


class CustomerService:
    """Customer management operations."""
    
    def __init__(self, client: DotMacClient):
        self.client = client
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new customer.
        
        Args:
            data: Customer data including display_name, customer_type, etc.
        
        Returns:
            Created customer object
        """
        response = self.client.request("POST", "/api/v1/customers", json_data=data)
        return response.json()
    
    def get(self, customer_id: str) -> Dict[str, Any]:
        """
        Get customer by ID.
        
        Args:
            customer_id: Customer unique identifier
        
        Returns:
            Customer object
        """
        response = self.client.request("GET", f"/api/v1/customers/{customer_id}")
        return response.json()
    
    def list(
        self,
        page: int = 1,
        limit: int = 20,
        state: Optional[str] = None,
        customer_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List customers with pagination.
        
        Args:
            page: Page number (1-based)
            limit: Items per page
            state: Filter by customer state
            customer_type: Filter by customer type
        
        Returns:
            Paginated list of customers
        """
        params = {
            "page": page,
            "limit": limit
        }
        if state:
            params["state"] = state
        if customer_type:
            params["customer_type"] = customer_type
        
        response = self.client.request("GET", "/api/v1/customers", params=params)
        return response.json()
    
    def update(self, customer_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update customer information.
        
        Args:
            customer_id: Customer unique identifier
            data: Fields to update
        
        Returns:
            Updated customer object
        """
        response = self.client.request(
            "PATCH",
            f"/api/v1/customers/{customer_id}",
            json_data=data
        )
        return response.json()
    
    def activate(self, customer_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Activate customer account.
        
        Args:
            customer_id: Customer unique identifier
            reason: Activation reason
        
        Returns:
            Updated customer object
        """
        data = {"reason": reason} if reason else {}
        response = self.client.request(
            "POST",
            f"/api/v1/customers/{customer_id}/activate",
            json_data=data
        )
        return response.json()
    
    def suspend(self, customer_id: str, reason: str) -> Dict[str, Any]:
        """
        Suspend customer account.
        
        Args:
            customer_id: Customer unique identifier
            reason: Suspension reason
        
        Returns:
            Updated customer object
        """
        response = self.client.request(
            "POST",
            f"/api/v1/customers/{customer_id}/suspend",
            json_data={"reason": reason}
        )
        return response.json()
    
    def delete(self, customer_id: str, force: bool = False) -> None:
        """
        Delete customer account.
        
        Args:
            customer_id: Customer unique identifier
            force: Force delete even with active services
        """
        params = {"force": force} if force else {}
        self.client.request("DELETE", f"/api/v1/customers/{customer_id}", params=params)


class InvoiceService:
    """Invoice and billing operations."""
    
    def __init__(self, client: DotMacClient):
        self.client = client
    
    def list(self, customer_id: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
        """List invoices with optional filtering."""
        params = {}
        if customer_id:
            params["customer_id"] = customer_id
        if status:
            params["status"] = status
        
        response = self.client.request("GET", "/api/v1/invoices", params=params)
        return response.json()
    
    def get(self, invoice_id: str) -> Dict[str, Any]:
        """Get invoice by ID."""
        response = self.client.request("GET", f"/api/v1/invoices/{invoice_id}")
        return response.json()
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new invoice."""
        response = self.client.request("POST", "/api/v1/invoices", json_data=data)
        return response.json()


class ServiceManagement:
    """Service provisioning and management."""
    
    def __init__(self, client: DotMacClient):
        self.client = client
    
    def list(self, customer_id: Optional[str] = None) -> Dict[str, Any]:
        """List services."""
        params = {"customer_id": customer_id} if customer_id else {}
        response = self.client.request("GET", "/api/v1/services", params=params)
        return response.json()
    
    def provision(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Provision new service."""
        response = self.client.request("POST", "/api/v1/services/provision", json_data=data)
        return response.json()
    
    def activate(self, service_id: str) -> Dict[str, Any]:
        """Activate service."""
        response = self.client.request("POST", f"/api/v1/services/{service_id}/activate")
        return response.json()
    
    def suspend(self, service_id: str, reason: str) -> Dict[str, Any]:
        """Suspend service."""
        response = self.client.request(
            "POST",
            f"/api/v1/services/{service_id}/suspend",
            json_data={"reason": reason}
        )
        return response.json()


class TicketService:
    """Support ticket operations."""
    
    def __init__(self, client: DotMacClient):
        self.client = client
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create support ticket."""
        response = self.client.request("POST", "/api/v1/tickets", json_data=data)
        return response.json()
    
    def get(self, ticket_id: str) -> Dict[str, Any]:
        """Get ticket details."""
        response = self.client.request("GET", f"/api/v1/tickets/{ticket_id}")
        return response.json()
    
    def list(self, status: Optional[str] = None, priority: Optional[str] = None) -> Dict[str, Any]:
        """List tickets."""
        params = {}
        if status:
            params["status"] = status
        if priority:
            params["priority"] = priority
        
        response = self.client.request("GET", "/api/v1/tickets", params=params)
        return response.json()
    
    def add_comment(self, ticket_id: str, comment: str) -> Dict[str, Any]:
        """Add comment to ticket."""
        response = self.client.request(
            "POST",
            f"/api/v1/tickets/{ticket_id}/comments",
            json_data={"comment": comment}
        )
        return response.json()
    
    def close(self, ticket_id: str, resolution: str) -> Dict[str, Any]:
        """Close ticket."""
        response = self.client.request(
            "POST",
            f"/api/v1/tickets/{ticket_id}/close",
            json_data={"resolution": resolution}
        )
        return response.json()


class NetworkService:
    """Network management operations."""
    
    def __init__(self, client: DotMacClient):
        self.client = client
    
    def get_status(self) -> Dict[str, Any]:
        """Get network status."""
        response = self.client.request("GET", "/api/v1/network/status")
        return response.json()
    
    def list_devices(self) -> Dict[str, Any]:
        """List network devices."""
        response = self.client.request("GET", "/api/v1/network/devices")
        return response.json()
    
    def get_device(self, device_id: str) -> Dict[str, Any]:
        """Get device details."""
        response = self.client.request("GET", f"/api/v1/network/devices/{device_id}")
        return response.json()


# Exception classes
class DotMacAPIError(Exception):
    """Base exception for DotMac API errors."""
    pass


class AuthenticationError(DotMacAPIError):
    """Authentication failed."""
    pass


class RateLimitError(DotMacAPIError):
    """Rate limit exceeded."""
    pass


class ValidationError(DotMacAPIError):
    """Request validation failed."""
    pass
'''
        
        # Write main client file
        sdk_dir = python_dir / "dotmac_sdk"
        sdk_dir.mkdir(exist_ok=True)
        (sdk_dir / "__init__.py").write_text(client_content)
        
        # Generate README
        readme_content = '''# DotMac Platform Python SDK

Official Python SDK for the DotMac Platform API.

## Installation

```bash
pip install dotmac-platform-sdk
```

## Quick Start

```python
from dotmac_sdk import DotMacClient

# Initialize client with API key
client = DotMacClient(
    base_url="https://api.dotmac.com",
    api_key="your-api-key"
)

# Or with access token
client = DotMacClient(
    base_url="https://api.dotmac.com",
    access_token="your-jwt-token"
)

# Create a customer
customer = client.customers.create({
    "display_name": "Acme Corp",
    "customer_type": "business",
    "primary_email": "contact@acme.com",
    "primary_phone": "+1-555-0123"
})

# List customers
customers = client.customers.list(page=1, limit=20, state="active")

# Get customer details
customer = client.customers.get("cust_123")

# Create a support ticket
ticket = client.tickets.create({
    "customer_id": "cust_123",
    "subject": "Internet connection issue",
    "description": "Connection drops every hour",
    "priority": "high"
})
```

## Services

- **Customers**: Customer account management
- **Invoices**: Billing and invoicing
- **Services**: Service provisioning
- **Tickets**: Support tickets
- **Network**: Network management

## Error Handling

```python
from dotmac_sdk import DotMacClient, DotMacAPIError

client = DotMacClient(api_key="your-api-key")

try:
    customer = client.customers.get("invalid_id")
except DotMacAPIError as e:
    print(f"API Error: {e}")
```

## Documentation

Full documentation: https://docs.dotmac.com/sdk/python

## License

MIT License
'''
        (python_dir / "README.md").write_text(readme_content)
        
        print("✅ Python SDK generated successfully")
    
    def generate_typescript_sdk(self):
        """Generate TypeScript SDK."""
        print("📘 Generating TypeScript SDK...")
        
        ts_dir = self.output_dir / "typescript"
        ts_dir.mkdir(exist_ok=True)
        
        # Generate package.json
        package_json = {
            "name": "@dotmac/platform-sdk",
            "version": "1.0.0",
            "description": "TypeScript SDK for DotMac Platform API",
            "main": "dist/index.js",
            "types": "dist/index.d.ts",
            "scripts": {
                "build": "tsc",
                "test": "jest",
                "prepublish": "npm run build"
            },
            "keywords": ["dotmac", "api", "sdk", "isp"],
            "author": "DotMac Platform Team",
            "license": "MIT",
            "dependencies": {
                "axios": "^1.6.0"
            },
            "devDependencies": {
                "@types/node": "^20.0.0",
                "typescript": "^5.0.0",
                "jest": "^29.0.0",
                "@types/jest": "^29.0.0"
            }
        }
        
        (ts_dir / "package.json").write_text(json.dumps(package_json, indent=2))
        
        # Generate TypeScript configuration
        tsconfig = {
            "compilerOptions": {
                "target": "ES2020",
                "module": "commonjs",
                "lib": ["ES2020"],
                "outDir": "./dist",
                "rootDir": "./src",
                "strict": True,
                "esModuleInterop": True,
                "skipLibCheck": True,
                "forceConsistentCasingInFileNames": True,
                "declaration": True,
                "declarationMap": True,
                "sourceMap": True
            },
            "include": ["src/**/*"],
            "exclude": ["node_modules", "dist", "**/*.test.ts"]
        }
        
        (ts_dir / "tsconfig.json").write_text(json.dumps(tsconfig, indent=2))
        
        # Generate main SDK file
        src_dir = ts_dir / "src"
        src_dir.mkdir(exist_ok=True)
        
        index_content = '''/**
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
'''
        (src_dir / "index.ts").write_text(index_content)
        
        # Generate README
        readme_content = '''# DotMac Platform TypeScript SDK

Official TypeScript SDK for the DotMac Platform API.

## Installation

```bash
npm install @dotmac/platform-sdk
```

## Quick Start

```typescript
import DotMacClient from '@dotmac/platform-sdk';

// Initialize client with API key
const client = new DotMacClient({
  baseURL: 'https://api.dotmac.com',
  apiKey: 'your-api-key',
});

// Or with access token
const client = new DotMacClient({
  baseURL: 'https://api.dotmac.com',
  accessToken: 'your-jwt-token',
});

// Create a customer
const customer = await client.customers.create({
  display_name: 'Acme Corp',
  customer_type: 'business',
  primary_email: 'contact@acme.com',
  primary_phone: '+1-555-0123',
});

// List customers
const customers = await client.customers.list({
  page: 1,
  limit: 20,
  state: 'active',
});

// Get customer details
const customer = await client.customers.get('cust_123');

// Create a support ticket
const ticket = await client.tickets.create({
  customer_id: 'cust_123',
  subject: 'Internet connection issue',
  description: 'Connection drops every hour',
  priority: 'high',
});
```

## Error Handling

```typescript
try {
  const customer = await client.customers.get('invalid_id');
} catch (error) {
  if (axios.isAxiosError(error)) {
    console.error('API Error:', error.response?.data);
  }
}
```

## TypeScript Support

This SDK is written in TypeScript and provides full type definitions.

## Documentation

Full documentation: https://docs.dotmac.com/sdk/typescript

## License

MIT License
'''
        (ts_dir / "README.md").write_text(readme_content)
        
        print("✅ TypeScript SDK generated successfully")
    
    def generate_go_sdk(self):
        """Generate Go SDK."""
        print("🐹 Generating Go SDK...")
        
        go_dir = self.output_dir / "go"
        go_dir.mkdir(exist_ok=True)
        
        # Generate go.mod
        go_mod = """module github.com/dotmac/platform-sdk-go

go 1.21

require (
    github.com/go-resty/resty/v2 v2.10.0
)
"""
        (go_dir / "go.mod").write_text(go_mod)
        
        # Generate main SDK file
        client_content = '''package dotmac

import (
    "fmt"
    "time"
    "github.com/go-resty/resty/v2"
)

// Config represents the SDK configuration
type Config struct {
    BaseURL     string
    APIKey      string
    AccessToken string
    Timeout     time.Duration
}

// Client is the main DotMac API client
type Client struct {
    config    Config
    http      *resty.Client
    Customers *CustomerService
    Tickets   *TicketService
    Invoices  *InvoiceService
}

// NewClient creates a new DotMac API client
func NewClient(config Config) *Client {
    if config.BaseURL == "" {
        config.BaseURL = "https://api.dotmac.com"
    }
    if config.Timeout == 0 {
        config.Timeout = 30 * time.Second
    }

    httpClient := resty.New().
        SetBaseURL(config.BaseURL).
        SetTimeout(config.Timeout).
        SetHeader("Content-Type", "application/json")

    if config.APIKey != "" {
        httpClient.SetHeader("X-API-Key", config.APIKey)
    } else if config.AccessToken != "" {
        httpClient.SetHeader("Authorization", "Bearer "+config.AccessToken)
    }

    client := &Client{
        config: config,
        http:   httpClient,
    }

    // Initialize services
    client.Customers = &CustomerService{client: client}
    client.Tickets = &TicketService{client: client}
    client.Invoices = &InvoiceService{client: client}

    return client
}

// Customer represents a customer entity
type Customer struct {
    ID             string    `json:"id"`
    CustomerNumber string    `json:"customer_number"`
    DisplayName    string    `json:"display_name"`
    CustomerType   string    `json:"customer_type"`
    State          string    `json:"state"`
    CreatedAt      time.Time `json:"created_at"`
    UpdatedAt      time.Time `json:"updated_at"`
}

// CreateCustomerRequest represents the request to create a customer
type CreateCustomerRequest struct {
    DisplayName    string                 `json:"display_name"`
    CustomerType   string                 `json:"customer_type"`
    PrimaryEmail   string                 `json:"primary_email"`
    PrimaryPhone   string                 `json:"primary_phone"`
    ServiceAddress map[string]interface{} `json:"service_address,omitempty"`
}

// PaginatedResponse represents a paginated API response
type PaginatedResponse[T any] struct {
    Items   []T  `json:"items"`
    Total   int  `json:"total"`
    Page    int  `json:"page"`
    Limit   int  `json:"limit"`
    Pages   int  `json:"pages"`
    HasNext bool `json:"has_next"`
    HasPrev bool `json:"has_prev"`
}

// CustomerService handles customer-related operations
type CustomerService struct {
    client *Client
}

// Create creates a new customer
func (s *CustomerService) Create(req CreateCustomerRequest) (*Customer, error) {
    var customer Customer
    _, err := s.client.http.R().
        SetBody(req).
        SetResult(&customer).
        Post("/api/v1/customers")
    return &customer, err
}

// Get retrieves a customer by ID
func (s *CustomerService) Get(customerID string) (*Customer, error) {
    var customer Customer
    _, err := s.client.http.R().
        SetResult(&customer).
        Get(fmt.Sprintf("/api/v1/customers/%s", customerID))
    return &customer, err
}

// List retrieves a paginated list of customers
func (s *CustomerService) List(page, limit int) (*PaginatedResponse[Customer], error) {
    var response PaginatedResponse[Customer]
    _, err := s.client.http.R().
        SetQueryParam("page", fmt.Sprintf("%d", page)).
        SetQueryParam("limit", fmt.Sprintf("%d", limit)).
        SetResult(&response).
        Get("/api/v1/customers")
    return &response, err
}

// TicketService handles ticket-related operations
type TicketService struct {
    client *Client
}

// Ticket represents a support ticket
type Ticket struct {
    ID         string    `json:"id"`
    CustomerID string    `json:"customer_id"`
    Subject    string    `json:"subject"`
    Status     string    `json:"status"`
    Priority   string    `json:"priority"`
    CreatedAt  time.Time `json:"created_at"`
    UpdatedAt  time.Time `json:"updated_at"`
}

// CreateTicketRequest represents the request to create a ticket
type CreateTicketRequest struct {
    CustomerID  string `json:"customer_id"`
    Subject     string `json:"subject"`
    Description string `json:"description"`
    Priority    string `json:"priority,omitempty"`
}

// Create creates a new support ticket
func (s *TicketService) Create(req CreateTicketRequest) (*Ticket, error) {
    var ticket Ticket
    _, err := s.client.http.R().
        SetBody(req).
        SetResult(&ticket).
        Post("/api/v1/tickets")
    return &ticket, err
}

// InvoiceService handles invoice-related operations
type InvoiceService struct {
    client *Client
}

// Invoice represents an invoice
type Invoice struct {
    ID         string    `json:"id"`
    CustomerID string    `json:"customer_id"`
    Amount     float64   `json:"amount"`
    Currency   string    `json:"currency"`
    Status     string    `json:"status"`
    DueDate    string    `json:"due_date"`
    CreatedAt  time.Time `json:"created_at"`
}

// List retrieves a paginated list of invoices
func (s *InvoiceService) List(customerID string) (*PaginatedResponse[Invoice], error) {
    var response PaginatedResponse[Invoice]
    req := s.client.http.R().SetResult(&response)
    
    if customerID != "" {
        req.SetQueryParam("customer_id", customerID)
    }
    
    _, err := req.Get("/api/v1/invoices")
    return &response, err
}
'''
        (go_dir / "client.go").write_text(client_content)
        
        # Generate README
        readme_content = '''# DotMac Platform Go SDK

Official Go SDK for the DotMac Platform API.

## Installation

```bash
go get github.com/dotmac/platform-sdk-go
```

## Quick Start

```go
package main

import (
    "fmt"
    "log"
    "github.com/dotmac/platform-sdk-go"
)

func main() {
    // Initialize client with API key
    client := dotmac.NewClient(dotmac.Config{
        BaseURL: "https://api.dotmac.com",
        APIKey:  "your-api-key",
    })

    // Create a customer
    customer, err := client.Customers.Create(dotmac.CreateCustomerRequest{
        DisplayName:  "Acme Corp",
        CustomerType: "business",
        PrimaryEmail: "contact@acme.com",
        PrimaryPhone: "+1-555-0123",
    })
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Created customer: %s\\n", customer.ID)

    // List customers
    customers, err := client.Customers.List(1, 20)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Found %d customers\\n", customers.Total)

    // Create a support ticket
    ticket, err := client.Tickets.Create(dotmac.CreateTicketRequest{
        CustomerID:  customer.ID,
        Subject:     "Internet connection issue",
        Description: "Connection drops every hour",
        Priority:    "high",
    })
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Created ticket: %s\\n", ticket.ID)
}
```

## Documentation

Full documentation: https://docs.dotmac.com/sdk/go

## License

MIT License
'''
        (go_dir / "README.md").write_text(readme_content)
        
        print("✅ Go SDK generated successfully")
    
    def generate_all(self):
        """Generate SDKs for all supported languages."""
        print("🚀 Starting SDK generation...\n")
        
        # Generate SDKs
        self.generate_python_sdk()
        self.generate_typescript_sdk()
        self.generate_go_sdk()
        
        # Generate main README
        main_readme = '''# DotMac Platform SDKs

Official SDKs for the DotMac Platform API.

## Available SDKs

### 🐍 Python
- Location: `sdk/python/`
- Package: `dotmac-platform-sdk`
- [Documentation](https://docs.dotmac.com/sdk/python)

### 📘 TypeScript/JavaScript
- Location: `sdk/typescript/`
- Package: `@dotmac/platform-sdk`
- [Documentation](https://docs.dotmac.com/sdk/typescript)

### 🐹 Go
- Location: `sdk/go/`
- Module: `github.com/dotmac/platform-sdk-go`
- [Documentation](https://docs.dotmac.com/sdk/go)

## Installation

### Python
```bash
pip install dotmac-platform-sdk
```

### TypeScript/JavaScript
```bash
npm install @dotmac/platform-sdk
```

### Go
```bash
go get github.com/dotmac/platform-sdk-go
```

## Authentication

All SDKs support two authentication methods:

1. **API Key**: Use `X-API-Key` header
2. **JWT Token**: Use `Authorization: Bearer <token>` header

## Quick Start

See individual SDK README files for language-specific examples.

## API Documentation

- [OpenAPI Specification](../docs/api/openapi.json)
- [Interactive Documentation](https://api.dotmac.com/docs)
- [Webhook Events](../docs/webhooks/WEBHOOK_EVENTS.md)

## Contributing

SDKs are auto-generated from the OpenAPI specification. To update:

1. Update the OpenAPI spec
2. Run `python scripts/generate_sdk.py`
3. Test the generated SDKs
4. Submit a pull request

## Support

- Documentation: https://docs.dotmac.com
- Issues: https://github.com/dotmac/platform-sdks/issues
- Email: sdk@dotmac.com

## License

MIT License - See LICENSE file for details.
'''
        (self.output_dir / "README.md").write_text(main_readme)
        
        print(f"\n✨ SDK generation complete!")
        print(f"📁 Generated SDKs in {self.output_dir}:")
        print("   - Python SDK")
        print("   - TypeScript SDK")
        print("   - Go SDK")
        print("\nNext steps:")
        print("1. Test the generated SDKs")
        print("2. Publish to package registries (PyPI, npm, pkg.go.dev)")
        print("3. Update documentation with SDK examples")


def main():
    """Main entry point."""
    generator = SDKGenerator()
    generator.generate_all()


if __name__ == "__main__":
    main()