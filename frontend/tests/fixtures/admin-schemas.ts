/**
 * JSON Schemas for Admin Management APIs
 * Provides validation schemas for deterministic testing
 */

export const DeviceSchema = {
  type: 'object',
  required: ['id', 'hostname', 'device_type', 'status', 'management_ip'],
  properties: {
    id: { type: 'string' },
    hostname: { type: 'string' },
    device_type: {
      type: 'string',
      enum: ['router', 'switch', 'access_point', 'firewall', 'load_balancer', 'ont', 'server'],
    },
    status: {
      type: 'string',
      enum: ['online', 'offline', 'degraded', 'maintenance', 'error'],
    },
    management_ip: {
      type: 'string',
      pattern:
        '^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
    },
    location: {
      type: 'object',
      properties: {
        id: { type: 'string' },
        name: { type: 'string' },
      },
    },
    uptime: { type: 'number', minimum: 0 },
    cpu_usage: { type: 'number', minimum: 0, maximum: 100 },
    memory_usage: { type: 'number', minimum: 0 },
    last_seen: { type: 'string', format: 'date-time' },
    vendor: { type: 'string' },
    model: { type: 'string' },
    firmware_version: { type: 'string' },
    serial_number: { type: 'string' },
  },
};

export const DeviceListResponseSchema = {
  type: 'object',
  required: ['devices', 'total', 'page', 'limit', 'total_pages', 'metrics'],
  properties: {
    devices: {
      type: 'array',
      items: DeviceSchema,
    },
    total: { type: 'number', minimum: 0 },
    page: { type: 'number', minimum: 1 },
    limit: { type: 'number', minimum: 1 },
    total_pages: { type: 'number', minimum: 0 },
    metrics: {
      type: 'object',
      required: ['total_devices', 'online', 'alerts', 'maintenance'],
      properties: {
        total_devices: { type: 'number', minimum: 0 },
        online: { type: 'number', minimum: 0 },
        alerts: { type: 'number', minimum: 0 },
        maintenance: { type: 'number', minimum: 0 },
      },
    },
  },
};

export const SubnetSchema = {
  type: 'object',
  required: [
    'id',
    'subnet',
    'description',
    'utilization',
    'total_ips',
    'used_ips',
    'available_ips',
  ],
  properties: {
    id: { type: 'string' },
    subnet: {
      type: 'string',
      pattern:
        '^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(?:3[0-2]|[12]?[0-9])$',
    },
    description: { type: 'string' },
    vlan_id: { type: ['number', 'null'], minimum: 1, maximum: 4094 },
    utilization: { type: 'number', minimum: 0, maximum: 100 },
    total_ips: { type: 'number', minimum: 1 },
    used_ips: { type: 'number', minimum: 0 },
    available_ips: { type: 'number', minimum: 0 },
    dhcp_enabled: { type: 'boolean' },
    gateway: {
      type: 'string',
      pattern:
        '^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
    },
    dns_servers: {
      type: 'array',
      items: { type: 'string' },
    },
    location: {
      type: 'object',
      properties: {
        id: { type: 'string' },
        name: { type: 'string' },
      },
    },
    subnet_type: {
      type: 'string',
      enum: ['management', 'customer', 'infrastructure', 'dmz', 'guest'],
    },
    ip_version: {
      type: 'string',
      enum: ['4', '6'],
    },
  },
};

export const SubnetListResponseSchema = {
  type: 'object',
  required: ['subnets', 'total', 'page', 'limit', 'total_pages', 'metrics'],
  properties: {
    subnets: {
      type: 'array',
      items: SubnetSchema,
    },
    total: { type: 'number', minimum: 0 },
    page: { type: 'number', minimum: 1 },
    limit: { type: 'number', minimum: 1 },
    total_pages: { type: 'number', minimum: 0 },
    metrics: {
      type: 'object',
      required: ['total_subnets', 'ip_utilization', 'available_ips', 'reservations'],
      properties: {
        total_subnets: { type: 'number', minimum: 0 },
        ip_utilization: { type: 'number', minimum: 0, maximum: 100 },
        available_ips: { type: 'number', minimum: 0 },
        reservations: { type: 'number', minimum: 0 },
      },
    },
  },
};

export const ProjectSchema = {
  type: 'object',
  required: ['id', 'name', 'status', 'progress', 'project_type', 'priority'],
  properties: {
    id: { type: 'string' },
    name: { type: 'string' },
    status: {
      type: 'string',
      enum: ['planning', 'in_progress', 'on_hold', 'completed', 'cancelled'],
    },
    progress: { type: 'number', minimum: 0, maximum: 100 },
    project_type: {
      type: 'string',
      enum: [
        'network_expansion',
        'infrastructure_upgrade',
        'customer_deployment',
        'maintenance',
        'emergency_repair',
        'fiber_installation',
      ],
    },
    priority: {
      type: 'string',
      enum: ['critical', 'high', 'medium', 'low'],
    },
    owner: {
      type: 'object',
      properties: {
        id: { type: 'string' },
        name: { type: 'string' },
      },
    },
    start_date: { type: 'string', format: 'date-time' },
    due_date: { type: 'string', format: 'date-time' },
    budget_allocated: { type: 'number', minimum: 0 },
    budget_used_percentage: { type: 'number', minimum: 0, maximum: 100 },
    team_size: { type: 'number', minimum: 0 },
    location: {
      type: 'object',
      properties: {
        id: { type: 'string' },
        name: { type: 'string' },
      },
    },
  },
};

export const ProjectListResponseSchema = {
  type: 'object',
  required: ['projects', 'total', 'page', 'limit', 'total_pages', 'metrics'],
  properties: {
    projects: {
      type: 'array',
      items: ProjectSchema,
    },
    total: { type: 'number', minimum: 0 },
    page: { type: 'number', minimum: 1 },
    limit: { type: 'number', minimum: 1 },
    total_pages: { type: 'number', minimum: 0 },
    metrics: {
      type: 'object',
      required: ['active_projects', 'on_schedule', 'budget_used', 'team_members'],
      properties: {
        active_projects: { type: 'number', minimum: 0 },
        on_schedule: { type: 'number', minimum: 0, maximum: 100 },
        budget_used: { type: 'number', minimum: 0 },
        team_members: { type: 'number', minimum: 0 },
      },
    },
  },
};

export const ContainerSchema = {
  type: 'object',
  required: ['id', 'name', 'image', 'status', 'uptime', 'cpu_usage', 'memory_usage'],
  properties: {
    id: { type: 'string' },
    name: { type: 'string' },
    image: { type: 'string' },
    status: {
      type: 'string',
      enum: ['running', 'stopped', 'paused', 'restarting', 'dead'],
    },
    uptime: { type: 'number', minimum: 0 },
    cpu_usage: { type: 'number', minimum: 0 },
    memory_usage: { type: 'number', minimum: 0, maximum: 100 },
    memory_limit: { type: 'number', minimum: 0 },
    network_io: {
      type: 'object',
      properties: {
        rx: { type: 'number', minimum: 0 },
        tx: { type: 'number', minimum: 0 },
      },
    },
    restart_count: { type: 'number', minimum: 0 },
    health_status: {
      type: 'string',
      enum: ['healthy', 'unhealthy', 'starting', 'unknown'],
    },
    node: { type: 'string' },
    service_name: { type: 'string' },
  },
};

export const ContainerListResponseSchema = {
  type: 'object',
  required: ['containers', 'total', 'page', 'limit', 'total_pages', 'metrics'],
  properties: {
    containers: {
      type: 'array',
      items: ContainerSchema,
    },
    total: { type: 'number', minimum: 0 },
    page: { type: 'number', minimum: 1 },
    limit: { type: 'number', minimum: 1 },
    total_pages: { type: 'number', minimum: 0 },
    metrics: {
      type: 'object',
      required: ['running_containers', 'cpu_usage', 'memory_usage', 'restarts_24h'],
      properties: {
        running_containers: { type: 'number', minimum: 0 },
        cpu_usage: { type: 'number', minimum: 0 },
        memory_usage: { type: 'number', minimum: 0 },
        restarts_24h: { type: 'number', minimum: 0 },
      },
    },
  },
};

export const BulkActionRequestSchema = {
  type: 'object',
  required: ['action', 'device_ids'],
  properties: {
    action: { type: 'string' },
    device_ids: {
      type: 'array',
      items: { type: 'string' },
      minItems: 1,
    },
  },
};

export const BulkActionResponseSchema = {
  type: 'object',
  required: ['success', 'affected_count', 'results'],
  properties: {
    success: { type: 'boolean' },
    affected_count: { type: 'number', minimum: 0 },
    action: { type: 'string' },
    results: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          device_id: { type: 'string' },
          status: { type: 'string' },
          message: { type: 'string' },
        },
      },
    },
  },
};

// Schema validation utility
export function validateSchema(data: any, schema: any): { valid: boolean; errors?: string[] } {
  // Simple JSON schema validation - in a real app you'd use ajv or similar
  try {
    // Basic type checking
    if (schema.type && typeof data !== schema.type) {
      return { valid: false, errors: [`Expected type ${schema.type}, got ${typeof data}`] };
    }

    // Required fields checking
    if (schema.required && schema.type === 'object') {
      const missing = schema.required.filter((field: string) => !(field in data));
      if (missing.length > 0) {
        return { valid: false, errors: [`Missing required fields: ${missing.join(', ')}`] };
      }
    }

    // Array items validation
    if (schema.type === 'array' && schema.items && Array.isArray(data)) {
      const errors: string[] = [];
      data.forEach((item, index) => {
        const result = validateSchema(item, schema.items);
        if (!result.valid) {
          errors.push(`Item ${index}: ${result.errors?.join(', ')}`);
        }
      });
      if (errors.length > 0) {
        return { valid: false, errors };
      }
    }

    return { valid: true };
  } catch (error) {
    return { valid: false, errors: [`Validation error: ${error.message}`] };
  }
}
