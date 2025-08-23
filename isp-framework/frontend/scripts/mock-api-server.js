#!/usr/bin/env node

/**
 * Mock API Server for DotMac Frontend Teams
 * Provides realistic data for all backend services during development and testing
 * Based on OpenAPI specifications from backend services
 */

const { setupServer } = require('msw/node');
const { http, HttpResponse } = require('msw');
const fs = require('fs');
const path = require('path');
const chalk = require('chalk');

class MockAPIServer {
  constructor() {
    this.server = null;
    this.port = process.env.MOCK_API_PORT || 8080;
    this.baseURL = `http://localhost:${this.port}`;
    this.handlers = [];
    this.backendSpecs = {};
    this.mockData = this.generateMockData();

    // Load backend API specifications
    this.loadBackendSpecs();
    this.setupHandlers();
  }

  loadBackendSpecs() {
    const specsDir = path.join(__dirname, '../../backend/docs/swagger');
    const services = [
      'dotmac_api_gateway',
      'dotmac_identity',
      'dotmac_billing',
      'dotmac_services',
      'dotmac_networking',
      'dotmac_analytics',
      'dotmac_platform',
      'dotmac_core_events',
      'dotmac_core_ops',
    ];

    for (const service of services) {
      const specPath = path.join(specsDir, `${service}.json`);

      if (fs.existsSync(specPath)) {
        try {
          this.backendSpecs[service] = JSON.parse(fs.readFileSync(specPath, 'utf8'));
          console.log(chalk.green(`✓ Loaded ${service} API specification`));
        } catch (error) {
          console.warn(chalk.yellow(`⚠ Failed to load ${service}: ${error.message}`));
        }
      }
    }
  }

  generateMockData() {
    return {
      // Identity Service Data
      customers: [
        {
          id: '1',
          firstName: 'John',
          lastName: 'Doe',
          email: 'john.doe@example.com',
          phone: '+1-555-0123',
          status: 'active',
          createdAt: '2024-01-15T10:00:00Z',
          address: {
            street: '123 Main St',
            city: 'Anytown',
            state: 'CA',
            zipCode: '12345',
            country: 'US',
          },
          plan: {
            id: 'plan_premium',
            name: 'Premium Internet',
            speed: '1000/1000',
            price: 99.99,
          },
        },
        {
          id: '2',
          firstName: 'Jane',
          lastName: 'Smith',
          email: 'jane.smith@example.com',
          phone: '+1-555-0124',
          status: 'active',
          createdAt: '2024-02-01T14:30:00Z',
          address: {
            street: '456 Oak Ave',
            city: 'Somewhere',
            state: 'NY',
            zipCode: '67890',
            country: 'US',
          },
          plan: {
            id: 'plan_standard',
            name: 'Standard Internet',
            speed: '500/500',
            price: 59.99,
          },
        },
        {
          id: '3',
          firstName: 'Robert',
          lastName: 'Johnson',
          email: 'robert.johnson@company.com',
          phone: '+1-555-0125',
          status: 'suspended',
          createdAt: '2024-01-20T09:15:00Z',
          address: {
            street: '789 Pine Rd',
            city: 'Elsewhere',
            state: 'TX',
            zipCode: '54321',
            country: 'US',
          },
          plan: {
            id: 'plan_business',
            name: 'Business Internet',
            speed: '2000/2000',
            price: 199.99,
          },
        },
      ],

      // Billing Service Data
      invoices: [
        {
          id: 'inv_001',
          customerId: '1',
          amount: 99.99,
          status: 'paid',
          dueDate: '2024-02-01',
          paidDate: '2024-01-28',
          items: [
            {
              description: 'Premium Internet - February 2024',
              amount: 99.99,
              quantity: 1,
            },
          ],
        },
        {
          id: 'inv_002',
          customerId: '2',
          amount: 59.99,
          status: 'pending',
          dueDate: '2024-02-15',
          paidDate: null,
          items: [
            {
              description: 'Standard Internet - February 2024',
              amount: 59.99,
              quantity: 1,
            },
          ],
        },
        {
          id: 'inv_003',
          customerId: '3',
          amount: 199.99,
          status: 'overdue',
          dueDate: '2024-01-15',
          paidDate: null,
          items: [
            {
              description: 'Business Internet - January 2024',
              amount: 199.99,
              quantity: 1,
            },
          ],
        },
      ],

      // Services Data
      services: [
        {
          id: 'svc_001',
          customerId: '1',
          type: 'internet',
          name: 'Premium Internet',
          status: 'active',
          installDate: '2024-01-15',
          ipAddress: '192.168.1.100',
          macAddress: '00:11:22:33:44:55',
        },
        {
          id: 'svc_002',
          customerId: '2',
          type: 'internet',
          name: 'Standard Internet',
          status: 'active',
          installDate: '2024-02-01',
          ipAddress: '192.168.1.101',
          macAddress: '00:11:22:33:44:56',
        },
        {
          id: 'svc_003',
          customerId: '3',
          type: 'internet',
          name: 'Business Internet',
          status: 'suspended',
          installDate: '2024-01-20',
          ipAddress: '192.168.1.102',
          macAddress: '00:11:22:33:44:57',
        },
      ],

      // Networking Data
      devices: [
        {
          id: 'dev_001',
          customerId: '1',
          type: 'router',
          model: 'DM-1000',
          ipAddress: '192.168.1.1',
          macAddress: '00:AA:BB:CC:DD:EE',
          status: 'online',
          lastSeen: '2024-02-20T15:30:00Z',
          firmware: '1.2.3',
        },
        {
          id: 'dev_002',
          customerId: '2',
          type: 'modem',
          model: 'DM-500',
          ipAddress: '192.168.2.1',
          macAddress: '00:AA:BB:CC:DD:EF',
          status: 'online',
          lastSeen: '2024-02-20T15:25:00Z',
          firmware: '2.1.0',
        },
        {
          id: 'dev_003',
          customerId: '3',
          type: 'switch',
          model: 'DM-2000',
          ipAddress: '192.168.3.1',
          macAddress: '00:AA:BB:CC:DD:F0',
          status: 'offline',
          lastSeen: '2024-02-18T10:15:00Z',
          firmware: '3.0.1',
        },
      ],

      // Analytics Data
      metrics: {
        totalCustomers: 1250,
        activeServices: 1180,
        monthlyRevenue: 125000,
        networkUtilization: 75,
        supportTickets: {
          open: 25,
          closed: 120,
          total: 145,
        },
        bandwidthUsage: [
          { date: '2024-02-01', upload: 850, download: 1200 },
          { date: '2024-02-02', upload: 920, download: 1350 },
          { date: '2024-02-03', upload: 780, download: 1100 },
          { date: '2024-02-04', upload: 1050, download: 1500 },
          { date: '2024-02-05', upload: 1200, download: 1650 },
        ],
      },

      // Support Tickets
      tickets: [
        {
          id: 'tkt_001',
          customerId: '1',
          subject: 'Internet connection slow',
          status: 'open',
          priority: 'medium',
          createdAt: '2024-02-19T09:00:00Z',
          updatedAt: '2024-02-19T14:30:00Z',
          assignedTo: 'support@dotmac.com',
          description: 'Customer reports slow internet speeds during peak hours.',
        },
        {
          id: 'tkt_002',
          customerId: '2',
          subject: 'Billing inquiry',
          status: 'resolved',
          priority: 'low',
          createdAt: '2024-02-18T11:15:00Z',
          updatedAt: '2024-02-18T16:45:00Z',
          assignedTo: 'billing@dotmac.com',
          description: 'Customer had questions about their monthly bill.',
        },
      ],

      // Users and Authentication
      users: [
        {
          id: 'usr_admin',
          email: 'admin@dotmac.com',
          role: 'admin',
          permissions: ['read:all', 'write:all', 'delete:all'],
          profile: {
            firstName: 'Admin',
            lastName: 'User',
            avatar: 'https://via.placeholder.com/150',
          },
        },
        {
          id: 'usr_support',
          email: 'support@dotmac.com',
          role: 'support',
          permissions: ['read:customers', 'write:tickets'],
          profile: {
            firstName: 'Support',
            lastName: 'Agent',
            avatar: 'https://via.placeholder.com/150',
          },
        },
        {
          id: 'usr_reseller',
          email: 'reseller@partner.com',
          role: 'reseller',
          permissions: ['read:customers', 'write:customers'],
          profile: {
            firstName: 'Reseller',
            lastName: 'Partner',
            avatar: 'https://via.placeholder.com/150',
          },
        },
      ],
    };
  }

  setupHandlers() {
    // Authentication endpoints
    this.handlers.push(
      http.post('/api/auth/login', ({ request }) => {
        const { email, password } = request.json();

        const user = this.mockData.users.find((u) => u.email === email);

        if (user && password === 'password') {
          return HttpResponse.json({
            success: true,
            token: 'mock-jwt-token',
            user: user,
            expiresIn: 3600,
          });
        }

        return HttpResponse.json(
          { success: false, message: 'Invalid credentials' },
          { status: 401 }
        );
      }),

      http.post('/api/auth/refresh', () => {
        return HttpResponse.json({
          success: true,
          token: 'refreshed-mock-jwt-token',
          expiresIn: 3600,
        });
      }),

      http.post('/api/auth/logout', () => {
        return HttpResponse.json({ success: true });
      }),

      http.get('/api/auth/me', ({ request }) => {
        const authHeader = request.headers.get('Authorization');

        if (!authHeader || !authHeader.includes('Bearer')) {
          return HttpResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        return HttpResponse.json({
          success: true,
          user: this.mockData.users[0], // Return admin user by default
        });
      })
    );

    // Customer endpoints
    this.handlers.push(
      http.get('/api/customers', ({ request }) => {
        const url = new URL(request.url);
        const page = parseInt(url.searchParams.get('page')) || 1;
        const limit = parseInt(url.searchParams.get('limit')) || 10;
        const search = url.searchParams.get('search') || '';

        let customers = this.mockData.customers;

        if (search) {
          customers = customers.filter(
            (c) =>
              c.firstName.toLowerCase().includes(search.toLowerCase()) ||
              c.lastName.toLowerCase().includes(search.toLowerCase()) ||
              c.email.toLowerCase().includes(search.toLowerCase())
          );
        }

        const start = (page - 1) * limit;
        const end = start + limit;
        const paginatedCustomers = customers.slice(start, end);

        return HttpResponse.json({
          data: paginatedCustomers,
          pagination: {
            page,
            limit,
            total: customers.length,
            totalPages: Math.ceil(customers.length / limit),
          },
        });
      }),

      http.get('/api/customers/:id', ({ params }) => {
        const customer = this.mockData.customers.find((c) => c.id === params.id);

        if (!customer) {
          return HttpResponse.json({ error: 'Customer not found' }, { status: 404 });
        }

        return HttpResponse.json({ data: customer });
      }),

      http.post('/api/customers', ({ request }) => {
        const customerData = request.json();

        const newCustomer = {
          id: String(this.mockData.customers.length + 1),
          ...customerData,
          createdAt: new Date().toISOString(),
          status: 'active',
        };

        this.mockData.customers.push(newCustomer);

        return HttpResponse.json({ data: newCustomer }, { status: 201 });
      }),

      http.put('/api/customers/:id', ({ params, request }) => {
        const customerIndex = this.mockData.customers.findIndex((c) => c.id === params.id);

        if (customerIndex === -1) {
          return HttpResponse.json({ error: 'Customer not found' }, { status: 404 });
        }

        const updates = request.json();
        this.mockData.customers[customerIndex] = {
          ...this.mockData.customers[customerIndex],
          ...updates,
          updatedAt: new Date().toISOString(),
        };

        return HttpResponse.json({
          data: this.mockData.customers[customerIndex],
        });
      }),

      http.delete('/api/customers/:id', ({ params }) => {
        const customerIndex = this.mockData.customers.findIndex((c) => c.id === params.id);

        if (customerIndex === -1) {
          return HttpResponse.json({ error: 'Customer not found' }, { status: 404 });
        }

        this.mockData.customers.splice(customerIndex, 1);

        return HttpResponse.json({ success: true });
      })
    );

    // Billing endpoints
    this.handlers.push(
      http.get('/api/billing/invoices', ({ request }) => {
        const url = new URL(request.url);
        const customerId = url.searchParams.get('customerId');

        let invoices = this.mockData.invoices;

        if (customerId) {
          invoices = invoices.filter((i) => i.customerId === customerId);
        }

        return HttpResponse.json({ data: invoices });
      }),

      http.get('/api/billing/invoices/:id', ({ params }) => {
        const invoice = this.mockData.invoices.find((i) => i.id === params.id);

        if (!invoice) {
          return HttpResponse.json({ error: 'Invoice not found' }, { status: 404 });
        }

        return HttpResponse.json({ data: invoice });
      }),

      http.post('/api/billing/invoices/:id/pay', ({ params }) => {
        const invoiceIndex = this.mockData.invoices.findIndex((i) => i.id === params.id);

        if (invoiceIndex === -1) {
          return HttpResponse.json({ error: 'Invoice not found' }, { status: 404 });
        }

        this.mockData.invoices[invoiceIndex].status = 'paid';
        this.mockData.invoices[invoiceIndex].paidDate = new Date().toISOString().split('T')[0];

        return HttpResponse.json({
          success: true,
          data: this.mockData.invoices[invoiceIndex],
        });
      })
    );

    // Services endpoints
    this.handlers.push(
      http.get('/api/services', ({ request }) => {
        const url = new URL(request.url);
        const customerId = url.searchParams.get('customerId');

        let services = this.mockData.services;

        if (customerId) {
          services = services.filter((s) => s.customerId === customerId);
        }

        return HttpResponse.json({ data: services });
      }),

      http.get('/api/services/:id', ({ params }) => {
        const service = this.mockData.services.find((s) => s.id === params.id);

        if (!service) {
          return HttpResponse.json({ error: 'Service not found' }, { status: 404 });
        }

        return HttpResponse.json({ data: service });
      })
    );

    // Networking endpoints
    this.handlers.push(
      http.get('/api/network/devices', ({ request }) => {
        const url = new URL(request.url);
        const customerId = url.searchParams.get('customerId');

        let devices = this.mockData.devices;

        if (customerId) {
          devices = devices.filter((d) => d.customerId === customerId);
        }

        return HttpResponse.json({ data: devices });
      }),

      http.get('/api/network/devices/:id', ({ params }) => {
        const device = this.mockData.devices.find((d) => d.id === params.id);

        if (!device) {
          return HttpResponse.json({ error: 'Device not found' }, { status: 404 });
        }

        return HttpResponse.json({ data: device });
      })
    );

    // Analytics endpoints
    this.handlers.push(
      http.get('/api/analytics/dashboard', () => {
        return HttpResponse.json({ data: this.mockData.metrics });
      }),

      http.get('/api/analytics/usage', ({ request }) => {
        const url = new URL(request.url);
        const period = url.searchParams.get('period') || '7d';

        // Generate usage data based on period
        const data = this.generateUsageData(period);

        return HttpResponse.json({ data });
      })
    );

    // Support endpoints
    this.handlers.push(
      http.get('/api/support/tickets', ({ request }) => {
        const url = new URL(request.url);
        const customerId = url.searchParams.get('customerId');
        const status = url.searchParams.get('status');

        let tickets = this.mockData.tickets;

        if (customerId) {
          tickets = tickets.filter((t) => t.customerId === customerId);
        }

        if (status) {
          tickets = tickets.filter((t) => t.status === status);
        }

        return HttpResponse.json({ data: tickets });
      }),

      http.post('/api/support/tickets', ({ request }) => {
        const ticketData = request.json();

        const newTicket = {
          id: `tkt_${String(this.mockData.tickets.length + 1).padStart(3, '0')}`,
          ...ticketData,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          status: 'open',
        };

        this.mockData.tickets.push(newTicket);

        return HttpResponse.json({ data: newTicket }, { status: 201 });
      })
    );

    // Health check endpoints
    this.handlers.push(
      http.get('/api/health', () => {
        return HttpResponse.json({
          status: 'healthy',
          timestamp: new Date().toISOString(),
          services: {
            database: 'healthy',
            redis: 'healthy',
            api: 'healthy',
          },
        });
      }),

      http.get('/api/ready', () => {
        return HttpResponse.json({
          ready: true,
          timestamp: new Date().toISOString(),
        });
      })
    );
  }

  generateUsageData(period) {
    const now = new Date();
    const data = [];

    let days;
    switch (period) {
      case '1d':
        days = 1;
        break;
      case '7d':
        days = 7;
        break;
      case '30d':
        days = 30;
        break;
      default:
        days = 7;
    }

    for (let i = days - 1; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);

      data.push({
        date: date.toISOString().split('T')[0],
        upload: Math.floor(Math.random() * 1000) + 500,
        download: Math.floor(Math.random() * 1500) + 800,
        users: Math.floor(Math.random() * 100) + 200,
      });
    }

    return data;
  }

  start() {
    console.log(chalk.blue('🚀 Starting DotMac Mock API Server...\\n'));

    this.server = setupServer(...this.handlers);
    this.server.listen({
      onUnhandledRequest: 'warn',
    });

    console.log(chalk.green('✅ Mock API Server is running'));
    console.log(chalk.blue(`🌐 Base URL: ${this.baseURL}`));
    console.log(chalk.yellow('📋 Available endpoints:'));

    const endpoints = [
      'POST   /api/auth/login',
      'POST   /api/auth/refresh',
      'POST   /api/auth/logout',
      'GET    /api/auth/me',
      'GET    /api/customers',
      'GET    /api/customers/:id',
      'POST   /api/customers',
      'PUT    /api/customers/:id',
      'DELETE /api/customers/:id',
      'GET    /api/billing/invoices',
      'GET    /api/billing/invoices/:id',
      'POST   /api/billing/invoices/:id/pay',
      'GET    /api/services',
      'GET    /api/services/:id',
      'GET    /api/network/devices',
      'GET    /api/network/devices/:id',
      'GET    /api/analytics/dashboard',
      'GET    /api/analytics/usage',
      'GET    /api/support/tickets',
      'POST   /api/support/tickets',
      'GET    /api/health',
      'GET    /api/ready',
    ];

    endpoints.forEach((endpoint) => {
      console.log(`  ${chalk.gray(endpoint)}`);
    });

    console.log(chalk.blue('\\n📚 Sample Authentication:'));
    console.log('  Email: admin@dotmac.com');
    console.log('  Password: password');

    return this.server;
  }

  stop() {
    if (this.server) {
      this.server.close();
      console.log(chalk.green('✅ Mock API Server stopped'));
    }
  }

  // Method to get current mock data (useful for testing)
  getData() {
    return this.mockData;
  }

  // Method to reset mock data
  reset() {
    this.mockData = this.generateMockData();
    console.log(chalk.yellow('🔄 Mock data reset'));
  }

  // Method to add custom endpoints
  addHandler(handler) {
    this.handlers.push(handler);

    if (this.server) {
      this.server.use(handler);
    }
  }
}

// CLI interface
if (require.main === module) {
  const mockServer = new MockAPIServer();

  const command = process.argv[2];

  switch (command) {
    case 'start':
      mockServer.start();

      // Keep the process running
      process.on('SIGINT', () => {
        console.log(chalk.yellow('\\n🛑 Shutting down Mock API Server...'));
        mockServer.stop();
        process.exit(0);
      });

      // Keep alive
      setInterval(() => {}, 1000);
      break;

    case 'test':
      // Run basic tests
      console.log(chalk.blue('🧪 Testing Mock API Server...'));

      const server = mockServer.start();

      // Test authentication
      fetch('http://localhost:8080/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'admin@dotmac.com',
          password: 'password',
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          console.log(chalk.green('✅ Authentication test passed'));
          console.log('Token:', data.token);
          mockServer.stop();
        })
        .catch((error) => {
          console.error(chalk.red('❌ Authentication test failed:'), error);
          mockServer.stop();
          process.exit(1);
        });
      break;

    default:
      console.log(chalk.blue('DotMac Mock API Server'));
      console.log('');
      console.log('Usage:');
      console.log('  node mock-api-server.js start  - Start the mock server');
      console.log('  node mock-api-server.js test   - Run basic tests');
      console.log('');
      console.log('Environment variables:');
      console.log('  MOCK_API_PORT - Server port (default: 8080)');
      break;
  }
}

module.exports = MockAPIServer;
