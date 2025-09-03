/**
 * Admin Portal MSW Handlers for Management Pages
 * Provides deterministic mocks for devices, IPAM, projects, and containers
 */

import { APIBehaviorTester } from './api-behaviors';

export class AdminManagementMocks {
  private tester: APIBehaviorTester;

  constructor(tester: APIBehaviorTester) {
    this.tester = tester;
  }

  /**
   * Setup Device Management API mocks with realistic data
   */
  async setupDeviceManagementMocks() {
    // Devices listing with filtering and pagination
    await this.tester.mockAndLog(/\/api\/admin\/devices.*/, async (req) => {
      const url = new URL(req.url);
      const page = parseInt(url.searchParams.get('page') || '1');
      const limit = parseInt(url.searchParams.get('limit') || '20');
      const search = url.searchParams.get('search');
      const deviceType = url.searchParams.get('device_type');
      const status = url.searchParams.get('status');
      const locationId = url.searchParams.get('location_id');

      let devices = [
        {
          id: 'dev-core-001',
          hostname: 'sea-core-router-01',
          device_type: 'router',
          status: 'online',
          management_ip: '192.168.1.1',
          location: { id: 'loc-001', name: 'Seattle Data Center' },
          uptime: 7889400, // seconds
          cpu_usage: 34.2,
          memory_usage: 2147483648, // bytes
          last_seen: '2024-08-31T08:30:00Z',
          vendor: 'cisco',
          model: 'ASR-1006-X',
          firmware_version: '17.06.05',
          serial_number: 'CSR1006X001',
        },
        {
          id: 'dev-dist-002',
          hostname: 'bel-dist-switch-02',
          device_type: 'switch',
          status: 'degraded',
          management_ip: '192.168.1.10',
          location: { id: 'loc-002', name: 'Bellevue Distribution' },
          uptime: 2592000,
          cpu_usage: 67.8,
          memory_usage: 1073741824,
          last_seen: '2024-08-31T08:25:00Z',
          vendor: 'cisco',
          model: 'C9300-24UX',
          firmware_version: '16.12.08',
          serial_number: 'C9300UX002',
        },
        {
          id: 'dev-ap-003',
          hostname: 'office-ap-03',
          device_type: 'access_point',
          status: 'online',
          management_ip: '192.168.2.53',
          location: { id: 'loc-003', name: 'Office Building A' },
          uptime: 1296000,
          cpu_usage: 12.4,
          memory_usage: 268435456,
          last_seen: '2024-08-31T08:31:00Z',
          vendor: 'ubiquiti',
          model: 'U6-Enterprise',
          firmware_version: '6.5.55',
          serial_number: 'U6ENT003',
        },
        {
          id: 'dev-fw-004',
          hostname: 'main-firewall-01',
          device_type: 'firewall',
          status: 'maintenance',
          management_ip: '192.168.1.254',
          location: { id: 'loc-001', name: 'Seattle Data Center' },
          uptime: 3888000,
          cpu_usage: 45.1,
          memory_usage: 4294967296,
          last_seen: '2024-08-31T06:00:00Z',
          vendor: 'juniper',
          model: 'SRX4600',
          firmware_version: '21.4R3',
          serial_number: 'SRX4600004',
        },
      ];

      // Apply filters
      if (search) {
        const query = search.toLowerCase();
        devices = devices.filter(
          (d) =>
            d.hostname.toLowerCase().includes(query) ||
            d.management_ip.includes(query) ||
            d.model.toLowerCase().includes(query)
        );
      }

      if (deviceType) {
        devices = devices.filter((d) => d.device_type === deviceType);
      }

      if (status) {
        devices = devices.filter((d) => d.status === status);
      }

      if (locationId) {
        devices = devices.filter((d) => d.location.id === locationId);
      }

      // Calculate metrics
      const totalDevices = devices.length;
      const onlineDevices = devices.filter((d) => d.status === 'online').length;
      const alerts = devices.filter((d) => d.status === 'degraded' || d.status === 'error').length;
      const maintenance = devices.filter((d) => d.status === 'maintenance').length;

      // Pagination
      const start = (page - 1) * limit;
      const paginatedDevices = devices.slice(start, start + limit);

      if (req.method === 'GET') {
        return {
          body: {
            devices: paginatedDevices,
            total: totalDevices,
            page,
            limit,
            total_pages: Math.ceil(totalDevices / limit),
            metrics: {
              total_devices: totalDevices,
              online: onlineDevices,
              alerts,
              maintenance,
            },
          },
        };
      }

      return { status: 405, body: { error: 'Method not allowed' } };
    });

    // Device details
    await this.tester.mockAndLog(/\/api\/admin\/devices\/[^\/]+$/, async (req) => {
      const deviceId = req.url.split('/').pop();

      return {
        body: {
          id: deviceId,
          hostname: `device-${deviceId}`,
          device_type: 'router',
          status: 'online',
          management_ip: '192.168.1.1',
          location: { id: 'loc-001', name: 'Seattle Data Center' },
          uptime: 7889400,
          cpu_usage: 34.2,
          memory_usage: 2147483648,
          last_seen: '2024-08-31T08:30:00Z',
          vendor: 'cisco',
          model: 'ASR-1006-X',
          firmware_version: '17.06.05',
          serial_number: 'CSR1006X001',
          interfaces: [
            {
              name: 'GigabitEthernet0/0/0',
              status: 'up',
              speed: '1000Mbps',
              utilization: 23.4,
            },
          ],
          monitoring_data: {
            cpu_history: [30, 32, 34, 36, 34, 32, 30],
            memory_history: [2.1, 2.2, 2.1, 2.3, 2.2, 2.1, 2.0],
          },
        },
      };
    });

    // Device bulk actions
    await this.tester.mockAndLog('/api/admin/devices/bulk', async (req) => {
      if (req.method !== 'POST') {
        return { status: 405, body: { error: 'Method not allowed' } };
      }

      const { action, device_ids } = req.body;

      if (!action || !device_ids?.length) {
        return {
          status: 400,
          body: { error: 'Missing action or device_ids' },
        };
      }

      // Simulate bulk action processing
      return {
        body: {
          success: true,
          affected_count: device_ids.length,
          action,
          results: device_ids.map((id: string) => ({
            device_id: id,
            status: 'success',
            message: `${action} completed successfully`,
          })),
        },
      };
    });
  }

  /**
   * Setup IPAM Management API mocks
   */
  async setupIPAMManagementMocks() {
    await this.tester.mockAndLog(/\/api\/admin\/ipam\/subnets.*/, async (req) => {
      const url = new URL(req.url);
      const page = parseInt(url.searchParams.get('page') || '1');
      const limit = parseInt(url.searchParams.get('limit') || '20');

      let subnets = [
        {
          id: 'subnet-001',
          subnet: '192.168.1.0/24',
          description: 'Management Network',
          vlan_id: 100,
          utilization: 75.2,
          total_ips: 254,
          used_ips: 191,
          available_ips: 63,
          dhcp_enabled: true,
          gateway: '192.168.1.1',
          dns_servers: ['8.8.8.8', '8.8.4.4'],
          location: { id: 'loc-001', name: 'Seattle Data Center' },
          subnet_type: 'management',
          ip_version: '4',
        },
        {
          id: 'subnet-002',
          subnet: '10.0.0.0/16',
          description: 'Customer Network - Residential',
          vlan_id: 200,
          utilization: 34.8,
          total_ips: 65534,
          used_ips: 22806,
          available_ips: 42728,
          dhcp_enabled: true,
          gateway: '10.0.0.1',
          dns_servers: ['1.1.1.1', '1.0.0.1'],
          location: { id: 'loc-002', name: 'Bellevue Distribution' },
          subnet_type: 'customer',
          ip_version: '4',
        },
        {
          id: 'subnet-003',
          subnet: '172.16.0.0/20',
          description: 'Infrastructure DMZ',
          vlan_id: 300,
          utilization: 12.1,
          total_ips: 4094,
          used_ips: 495,
          available_ips: 3599,
          dhcp_enabled: false,
          gateway: '172.16.0.1',
          dns_servers: ['208.67.222.222', '208.67.220.220'],
          location: { id: 'loc-001', name: 'Seattle Data Center' },
          subnet_type: 'infrastructure',
          ip_version: '4',
        },
      ];

      // Calculate metrics
      const totalSubnets = subnets.length;
      const totalIPs = subnets.reduce((sum, s) => sum + s.total_ips, 0);
      const usedIPs = subnets.reduce((sum, s) => sum + s.used_ips, 0);
      const avgUtilization = subnets.reduce((sum, s) => sum + s.utilization, 0) / subnets.length;
      const reservations = Math.floor(usedIPs * 0.15); // Estimate reserved IPs

      const start = (page - 1) * limit;
      const paginatedSubnets = subnets.slice(start, start + limit);

      return {
        body: {
          subnets: paginatedSubnets,
          total: totalSubnets,
          page,
          limit,
          total_pages: Math.ceil(totalSubnets / limit),
          metrics: {
            total_subnets: totalSubnets,
            ip_utilization: Math.round(avgUtilization * 10) / 10,
            available_ips: totalIPs - usedIPs,
            reservations,
          },
        },
      };
    });

    // Subnet details
    await this.tester.mockAndLog(/\/api\/admin\/ipam\/subnets\/[^\/]+$/, async (req) => {
      const subnetId = req.url.split('/').pop();

      return {
        body: {
          id: subnetId,
          subnet: '192.168.1.0/24',
          description: 'Management Network',
          vlan_id: 100,
          utilization: 75.2,
          total_ips: 254,
          used_ips: 191,
          available_ips: 63,
          dhcp_enabled: true,
          gateway: '192.168.1.1',
          dns_servers: ['8.8.8.8', '8.8.4.4'],
          location: { id: 'loc-001', name: 'Seattle Data Center' },
          subnet_type: 'management',
          ip_version: '4',
          ip_allocations: [
            {
              ip: '192.168.1.1',
              status: 'reserved',
              description: 'Gateway',
              device_id: 'dev-core-001',
            },
            {
              ip: '192.168.1.10',
              status: 'allocated',
              description: 'Switch Management',
              device_id: 'dev-dist-002',
            },
          ],
        },
      };
    });
  }

  /**
   * Setup Project Management API mocks
   */
  async setupProjectManagementMocks() {
    await this.tester.mockAndLog(/\/api\/admin\/projects.*/, async (req) => {
      const url = new URL(req.url);
      const page = parseInt(url.searchParams.get('page') || '1');
      const limit = parseInt(url.searchParams.get('limit') || '20');

      let projects = [
        {
          id: 'proj-001',
          name: 'Downtown Fiber Expansion',
          status: 'in_progress',
          progress: 67,
          project_type: 'network_expansion',
          priority: 'high',
          owner: { id: 'user-001', name: 'Sarah Johnson' },
          start_date: '2024-06-01T00:00:00Z',
          due_date: '2024-12-31T23:59:59Z',
          budget_allocated: 450000,
          budget_used_percentage: 58.3,
          team_size: 8,
          location: { id: 'loc-001', name: 'Downtown District' },
        },
        {
          id: 'proj-002',
          name: 'Core Router Upgrade',
          status: 'planning',
          progress: 15,
          project_type: 'infrastructure_upgrade',
          priority: 'critical',
          owner: { id: 'user-002', name: 'Mike Chen' },
          start_date: '2024-09-01T00:00:00Z',
          due_date: '2024-11-15T23:59:59Z',
          budget_allocated: 125000,
          budget_used_percentage: 12.8,
          team_size: 4,
          location: { id: 'loc-002', name: 'Seattle Data Center' },
        },
        {
          id: 'proj-003',
          name: 'Customer Deployment - Tech Plaza',
          status: 'completed',
          progress: 100,
          project_type: 'customer_deployment',
          priority: 'medium',
          owner: { id: 'user-003', name: 'Lisa Wang' },
          start_date: '2024-05-01T00:00:00Z',
          due_date: '2024-07-31T23:59:59Z',
          budget_allocated: 35000,
          budget_used_percentage: 94.2,
          team_size: 3,
          location: { id: 'loc-003', name: 'Tech Plaza' },
        },
      ];

      // Calculate metrics
      const activeProjects = projects.filter((p) => p.status === 'in_progress').length;
      const onScheduleProjects = projects.filter(
        (p) => p.status === 'in_progress' && p.progress >= 50
      ).length;
      const totalBudget = projects.reduce((sum, p) => sum + p.budget_allocated, 0);
      const budgetUsed = projects.reduce(
        (sum, p) => sum + (p.budget_allocated * p.budget_used_percentage) / 100,
        0
      );
      const totalTeamMembers = projects.reduce((sum, p) => sum + p.team_size, 0);

      const start = (page - 1) * limit;
      const paginatedProjects = projects.slice(start, start + limit);

      return {
        body: {
          projects: paginatedProjects,
          total: projects.length,
          page,
          limit,
          total_pages: Math.ceil(projects.length / limit),
          metrics: {
            active_projects: activeProjects,
            on_schedule: Math.round((onScheduleProjects / activeProjects) * 100) || 0,
            budget_used: budgetUsed,
            team_members: totalTeamMembers,
          },
        },
      };
    });

    // Project details
    await this.tester.mockAndLog(/\/api\/admin\/projects\/[^\/]+$/, async (req) => {
      const projectId = req.url.split('/').pop();

      return {
        body: {
          id: projectId,
          name: 'Downtown Fiber Expansion',
          description: 'Expanding fiber optic infrastructure to cover downtown business district',
          status: 'in_progress',
          progress: 67,
          project_type: 'network_expansion',
          priority: 'high',
          owner: { id: 'user-001', name: 'Sarah Johnson' },
          start_date: '2024-06-01T00:00:00Z',
          due_date: '2024-12-31T23:59:59Z',
          budget_allocated: 450000,
          budget_used_percentage: 58.3,
          team_size: 8,
          location: { id: 'loc-001', name: 'Downtown District' },
          tasks: [
            {
              id: 'task-001',
              name: 'Site Survey',
              status: 'completed',
              progress: 100,
              assignee: 'John Doe',
            },
            {
              id: 'task-002',
              name: 'Fiber Installation',
              status: 'in_progress',
              progress: 45,
              assignee: 'Jane Smith',
            },
          ],
          milestones: [
            {
              name: 'Phase 1 Complete',
              date: '2024-08-31T00:00:00Z',
              status: 'completed',
            },
            {
              name: 'Phase 2 Complete',
              date: '2024-10-31T00:00:00Z',
              status: 'pending',
            },
          ],
        },
      };
    });
  }

  /**
   * Setup Container Management API mocks
   */
  async setupContainerManagementMocks() {
    await this.tester.mockAndLog(/\/api\/admin\/containers.*/, async (req) => {
      const url = new URL(req.url);
      const page = parseInt(url.searchParams.get('page') || '1');
      const limit = parseInt(url.searchParams.get('limit') || '20');

      let containers = [
        {
          id: 'cont-001',
          name: 'isp-framework-api',
          image: 'dotmac/isp-framework:v2.1.3',
          status: 'running',
          uptime: 2592000, // seconds
          cpu_usage: 34.5,
          memory_usage: 78.2,
          memory_limit: 2147483648, // 2GB in bytes
          network_io: { rx: 1073741824, tx: 2147483648 }, // bytes
          restart_count: 2,
          health_status: 'healthy',
          node: 'worker-01',
          service_name: 'isp-framework',
        },
        {
          id: 'cont-002',
          name: 'management-platform-web',
          image: 'dotmac/management-platform:v1.4.7',
          status: 'running',
          uptime: 1728000,
          cpu_usage: 12.8,
          memory_usage: 45.3,
          memory_limit: 1073741824, // 1GB
          network_io: { rx: 536870912, tx: 1073741824 },
          restart_count: 0,
          health_status: 'healthy',
          node: 'worker-02',
          service_name: 'management-platform',
        },
        {
          id: 'cont-003',
          name: 'postgres-primary',
          image: 'postgres:15.4-alpine',
          status: 'running',
          uptime: 7776000,
          cpu_usage: 23.1,
          memory_usage: 89.7,
          memory_limit: 4294967296, // 4GB
          network_io: { rx: 2147483648, tx: 1073741824 },
          restart_count: 1,
          health_status: 'healthy',
          node: 'master-01',
          service_name: 'database',
        },
        {
          id: 'cont-004',
          name: 'redis-cache',
          image: 'redis:7.2-alpine',
          status: 'restarting',
          uptime: 300,
          cpu_usage: 5.4,
          memory_usage: 15.2,
          memory_limit: 536870912, // 512MB
          network_io: { rx: 134217728, tx: 67108864 },
          restart_count: 5,
          health_status: 'starting',
          node: 'worker-01',
          service_name: 'cache',
        },
      ];

      // Calculate metrics
      const runningContainers = containers.filter((c) => c.status === 'running').length;
      const avgCpuUsage = containers.reduce((sum, c) => sum + c.cpu_usage, 0) / containers.length;
      const totalMemoryUsed = containers.reduce(
        (sum, c) => sum + (c.memory_limit * c.memory_usage) / 100,
        0
      );
      const totalRestarts = containers.reduce((sum, c) => sum + c.restart_count, 0);

      const start = (page - 1) * limit;
      const paginatedContainers = containers.slice(start, start + limit);

      return {
        body: {
          containers: paginatedContainers,
          total: containers.length,
          page,
          limit,
          total_pages: Math.ceil(containers.length / limit),
          metrics: {
            running_containers: runningContainers,
            cpu_usage: Math.round(avgCpuUsage * 10) / 10,
            memory_usage: Math.round((totalMemoryUsed / 1024 ** 3) * 10) / 10, // GB
            restarts_24h: totalRestarts,
          },
        },
      };
    });

    // Container details
    await this.tester.mockAndLog(/\/api\/admin\/containers\/[^\/]+$/, async (req) => {
      const containerId = req.url.split('/').pop();

      return {
        body: {
          id: containerId,
          name: 'isp-framework-api',
          image: 'dotmac/isp-framework:v2.1.3',
          status: 'running',
          uptime: 2592000,
          cpu_usage: 34.5,
          memory_usage: 78.2,
          memory_limit: 2147483648,
          network_io: { rx: 1073741824, tx: 2147483648 },
          restart_count: 2,
          health_status: 'healthy',
          node: 'worker-01',
          service_name: 'isp-framework',
          environment: {
            POSTGRES_HOST: 'postgres-primary',
            REDIS_HOST: 'redis-cache',
            LOG_LEVEL: 'info',
          },
          volumes: [
            {
              source: '/data/isp-framework',
              destination: '/app/data',
              mode: 'rw',
            },
          ],
          ports: [
            {
              host_port: 8000,
              container_port: 8000,
              protocol: 'tcp',
            },
          ],
          logs: [
            {
              timestamp: '2024-08-31T08:30:15.123Z',
              level: 'info',
              message: 'Application started successfully',
            },
            {
              timestamp: '2024-08-31T08:30:10.456Z',
              level: 'info',
              message: 'Database connection established',
            },
          ],
        },
      };
    });

    // Container restart action
    await this.tester.mockAndLog('/api/admin/containers/bulk', async (req) => {
      if (req.method !== 'POST') {
        return { status: 405, body: { error: 'Method not allowed' } };
      }

      const { action, container_ids } = req.body;

      if (action === 'bulk_restart' && container_ids?.length) {
        return {
          body: {
            success: true,
            affected_count: container_ids.length,
            results: container_ids.map((id: string) => ({
              container_id: id,
              status: 'success',
              message: 'Container restart initiated',
            })),
          },
        };
      }

      return {
        status: 400,
        body: { error: 'Invalid action or missing container_ids' },
      };
    });
  }

  /**
   * Setup all admin management mocks
   */
  async setupAll() {
    await this.setupDeviceManagementMocks();
    await this.setupIPAMManagementMocks();
    await this.setupProjectManagementMocks();
    await this.setupContainerManagementMocks();
  }
}
