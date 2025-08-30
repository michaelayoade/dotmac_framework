/**
 * Business Logic Factory
 * Creates configured business logic engines for different portal contexts
 */

import { RevenueEngine } from '../revenue/RevenueEngine';
import { ServicePlanEngine } from '../service-plans/ServicePlanEngine';
import { NetworkServiceEngine } from '../network/NetworkServiceEngine';
import type { BusinessLogicConfig, PortalContext } from '../types';

export interface BusinessLogicEngines {
  revenue: RevenueEngine;
  servicePlans: ServicePlanEngine;
  network: NetworkServiceEngine;
}

export class BusinessLogicFactory {
  /**
   * Create all business logic engines for a given portal context
   */
  static createEngines(
    config: BusinessLogicConfig,
    context: PortalContext
  ): BusinessLogicEngines {
    return {
      revenue: new RevenueEngine(config, context),
      servicePlans: new ServicePlanEngine(config, context),
      network: new NetworkServiceEngine(config, context),
    };
  }

  /**
   * Create default configuration for different portal types
   */
  static createDefaultConfig(portalType: PortalContext['portalType']): BusinessLogicConfig {
    const baseConfig: BusinessLogicConfig = {
      apiBaseUrl: '/api',
      timeout: 30000,
      retryAttempts: 3,
      cacheTtl: 300000, // 5 minutes
      features: {
        revenueCalculation: true,
        commissionTracking: true,
        servicePlanManagement: true,
        networkDiagnostics: true,
        provisioningAutomation: true,
      },
    };

    // Portal-specific configuration overrides
    switch (portalType) {
      case 'management-admin':
        return {
          ...baseConfig,
          features: {
            ...baseConfig.features,
            // Management admin has access to all features
          },
        };

      case 'admin':
        return {
          ...baseConfig,
          features: {
            ...baseConfig.features,
            // ISP admin has access to all customer-facing features
            commissionTracking: false, // No partner commissions at ISP level
          },
        };

      case 'customer':
        return {
          ...baseConfig,
          features: {
            revenueCalculation: false, // Customers don't calculate revenue
            commissionTracking: false, // No commission access
            servicePlanManagement: true, // Can view and change plans
            networkDiagnostics: true, // Can run self-service diagnostics
            provisioningAutomation: false, // No provisioning access
          },
        };

      case 'reseller':
        return {
          ...baseConfig,
          features: {
            ...baseConfig.features,
            provisioningAutomation: false, // Resellers don't provision directly
          },
        };

      case 'technician':
        return {
          ...baseConfig,
          features: {
            revenueCalculation: false, // Technicians don't handle revenue
            commissionTracking: false, // No commission access
            servicePlanManagement: true, // Can view plans for installations
            networkDiagnostics: true, // Full diagnostic access
            provisioningAutomation: true, // Can provision services
          },
        };

      default:
        return baseConfig;
    }
  }

  /**
   * Create portal context from user session and portal type
   */
  static createPortalContext(
    portalType: PortalContext['portalType'],
    userId: string,
    permissions: string[],
    tenantId?: string,
    preferences?: Record<string, any>
  ): PortalContext {
    return {
      portalType,
      userId,
      tenantId,
      permissions,
      preferences,
    };
  }

  /**
   * Create a pre-configured business logic instance for Management Admin Portal
   */
  static forManagementAdmin(
    userId: string,
    permissions: string[],
    tenantId?: string
  ): BusinessLogicEngines {
    const config = this.createDefaultConfig('management-admin');
    const context = this.createPortalContext('management-admin', userId, permissions, tenantId);

    return this.createEngines(config, context);
  }

  /**
   * Create a pre-configured business logic instance for ISP Admin Portal
   */
  static forISPAdmin(
    userId: string,
    permissions: string[],
    tenantId: string
  ): BusinessLogicEngines {
    const config = this.createDefaultConfig('admin');
    const context = this.createPortalContext('admin', userId, permissions, tenantId);

    return this.createEngines(config, context);
  }

  /**
   * Create a pre-configured business logic instance for Customer Portal
   */
  static forCustomer(
    userId: string,
    permissions: string[],
    tenantId: string
  ): BusinessLogicEngines {
    const config = this.createDefaultConfig('customer');
    const context = this.createPortalContext('customer', userId, permissions, tenantId);

    return this.createEngines(config, context);
  }

  /**
   * Create a pre-configured business logic instance for Reseller Portal
   */
  static forReseller(
    userId: string,
    permissions: string[],
    tenantId: string
  ): BusinessLogicEngines {
    const config = this.createDefaultConfig('reseller');
    const context = this.createPortalContext('reseller', userId, permissions, tenantId);

    return this.createEngines(config, context);
  }

  /**
   * Create a pre-configured business logic instance for Technician Portal
   */
  static forTechnician(
    userId: string,
    permissions: string[],
    tenantId: string
  ): BusinessLogicEngines {
    const config = this.createDefaultConfig('technician');
    const context = this.createPortalContext('technician', userId, permissions, tenantId);

    return this.createEngines(config, context);
  }
}
