/**
 * Test data fixtures for E2E tests
 */

export const testUsers = {
  admin: {
    email: 'admin@dotmac.com',
    password: 'admin123',
    role: 'admin',
    firstName: 'Admin',
    lastName: 'User'
  },
  manager: {
    email: 'manager@dotmac.com',
    password: 'manager123',
    role: 'manager',
    firstName: 'Manager',
    lastName: 'User'
  },
  user: {
    email: 'user@dotmac.com',
    password: 'user123',
    role: 'user',
    firstName: 'Regular',
    lastName: 'User'
  }
};

export const testTenants = [
  {
    id: 'tenant-1',
    name: 'Acme Corporation',
    domain: 'acme.example.com',
    email: 'admin@acme.com',
    status: 'active',
    plan: 'enterprise',
    createdAt: '2024-01-15T10:00:00Z',
    updatedAt: '2024-01-15T10:00:00Z',
    settings: {
      maxUsers: 500,
      storageQuota: '100GB',
      customDomain: true
    }
  },
  {
    id: 'tenant-2',
    name: 'Tech Startup Inc',
    domain: 'techstartup.example.com',
    email: 'admin@techstartup.com',
    status: 'active',
    plan: 'professional',
    createdAt: '2024-02-01T14:30:00Z',
    updatedAt: '2024-02-01T14:30:00Z',
    settings: {
      maxUsers: 50,
      storageQuota: '10GB',
      customDomain: false
    }
  },
  {
    id: 'tenant-3',
    name: 'Suspended Corp',
    domain: 'suspended.example.com',
    email: 'admin@suspended.com',
    status: 'suspended',
    plan: 'basic',
    createdAt: '2024-01-01T09:00:00Z',
    updatedAt: '2024-02-15T16:45:00Z',
    settings: {
      maxUsers: 10,
      storageQuota: '5GB',
      customDomain: false
    }
  }
];

export const testSystemAlerts = [
  {
    id: 'alert-1',
    type: 'error' as const,
    title: 'Database Connection Failed',
    message: 'Unable to connect to primary database. Failover activated.',
    timestamp: new Date().toISOString(),
    acknowledged: false,
    severity: 'high' as const
  },
  {
    id: 'alert-2',
    type: 'warning' as const,
    title: 'High Memory Usage',
    message: 'Memory usage is at 87% on server web-01',
    timestamp: new Date(Date.now() - 300000).toISOString(), // 5 minutes ago
    acknowledged: false,
    severity: 'medium' as const
  },
  {
    id: 'alert-3',
    type: 'info' as const,
    title: 'Maintenance Window Scheduled',
    message: 'System maintenance scheduled for tonight at 2 AM UTC',
    timestamp: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
    acknowledged: true,
    severity: 'low' as const
  }
];

export const testMetrics = [
  {
    name: 'Total Tenants',
    value: 1247,
    change: 3.2,
    trend: 'up' as const,
    lastUpdated: new Date().toISOString(),
    unit: 'count'
  },
  {
    name: 'Active Users',
    value: 8934,
    change: 1.8,
    trend: 'up' as const,
    lastUpdated: new Date().toISOString(),
    unit: 'count'
  },
  {
    name: 'Monthly Revenue',
    value: '$127,580',
    change: 12.5,
    trend: 'up' as const,
    lastUpdated: new Date().toISOString(),
    unit: 'currency'
  },
  {
    name: 'System Health',
    value: '98.7%',
    change: -0.3,
    trend: 'down' as const,
    lastUpdated: new Date().toISOString(),
    unit: 'percentage'
  },
  {
    name: 'Response Time',
    value: '234ms',
    change: 5.7,
    trend: 'up' as const,
    lastUpdated: new Date().toISOString(),
    unit: 'milliseconds'
  },
  {
    name: 'Storage Used',
    value: '2.4TB',
    change: 8.9,
    trend: 'up' as const,
    lastUpdated: new Date().toISOString(),
    unit: 'bytes'
  }
];

export const testUserActivities = [
  {
    userId: 'user-1',
    userName: 'John Smith',
    action: 'Created new tenant "Global Solutions Ltd"',
    timestamp: new Date().toISOString(),
    metadata: {
      tenantId: 'tenant-new-1',
      action: 'create',
      resource: 'tenant'
    }
  },
  {
    userId: 'user-2',
    userName: 'Sarah Johnson',
    action: 'Updated billing plan for "Acme Corporation"',
    timestamp: new Date(Date.now() - 180000).toISOString(), // 3 minutes ago
    metadata: {
      tenantId: 'tenant-1',
      action: 'update',
      resource: 'billing',
      oldPlan: 'professional',
      newPlan: 'enterprise'
    }
  },
  {
    userId: 'user-3',
    userName: 'Mike Wilson',
    action: 'Suspended tenant "Overdue Corp" for non-payment',
    timestamp: new Date(Date.now() - 600000).toISOString(), // 10 minutes ago
    metadata: {
      tenantId: 'tenant-overdue',
      action: 'suspend',
      resource: 'tenant',
      reason: 'non-payment'
    }
  }
];

export const testMFASetup = {
  secret: 'JBSWY3DPEHPK3PXP',
  qrCodeUrl: 'otpauth://totp/DotMac%20Management:admin@dotmac.com?secret=JBSWY3DPEHPK3PXP&issuer=DotMac%20Management',
  manualEntryCode: 'JBSWY3DPEHPK3PXP',
  backupCodes: [
    'BACKUP001',
    'BACKUP002', 
    'BACKUP003',
    'BACKUP004',
    'BACKUP005',
    'BACKUP006',
    'BACKUP007',
    'BACKUP008'
  ]
};

export const testAuditEvents = [
  {
    id: 'audit-1',
    eventType: 'user_login',
    userId: 'user-1',
    userName: 'John Smith',
    description: 'User successfully logged in',
    timestamp: new Date().toISOString(),
    ipAddress: '192.168.1.100',
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    severity: 'low' as const,
    complianceFlags: ['SOX'] as const,
    context: {
      sessionId: 'session-123',
      authMethod: 'password'
    }
  },
  {
    id: 'audit-2',
    eventType: 'data_deleted',
    userId: 'user-2',
    userName: 'Sarah Johnson',
    description: 'Deleted tenant data for "Old Company Inc"',
    timestamp: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
    ipAddress: '192.168.1.101',
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    severity: 'high' as const,
    complianceFlags: ['GDPR', 'SOX'] as const,
    context: {
      tenantId: 'tenant-old',
      recordsDeleted: 1547,
      reason: 'tenant_termination'
    }
  }
];

export const apiResponses = {
  dashboardStats: {
    totalTenants: 1247,
    activeTenants: 1156,
    activeUsers: 8934,
    monthlyRevenue: 127580,
    systemHealth: 98.7,
    responseTime: 234,
    storageUsed: 2400000000000, // 2.4TB in bytes
    trends: {
      tenants: 3.2,
      users: 1.8,
      revenue: 12.5,
      health: -0.3
    }
  },
  systemStatus: {
    status: 'healthy',
    uptime: 99.8,
    services: {
      database: 'healthy',
      cache: 'healthy',
      queue: 'healthy',
      storage: 'healthy'
    },
    lastChecked: new Date().toISOString()
  }
};