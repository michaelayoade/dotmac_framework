import type { HandoffRecord, CustomerJourney } from '../types';
import { JourneyEventBus } from '../events/EventBus';

/**
 * Automated Handoff System
 * Manages seamless transitions between packages and teams
 */
export class HandoffSystem {
  private tenantId: string;
  private eventBus: JourneyEventBus;
  private pendingHandoffs = new Map<string, HandoffRecord>();
  private handoffTimeouts = new Map<string, NodeJS.Timeout>();

  // Package integration configurations
  private packageConfigs = {
    'crm': {
      endpoints: {
        'convert_lead': '/api/crm/leads/{leadId}/convert',
        'create_customer': '/api/crm/customers',
        'update_customer': '/api/crm/customers/{customerId}'
      },
      requiredData: {
        'convert_lead': ['leadId', 'customerData'],
        'create_customer': ['customerData'],
        'update_customer': ['customerId', 'updates']
      }
    },
    'business-logic': {
      endpoints: {
        'activate_service': '/api/services/activate',
        'provision_equipment': '/api/services/provision',
        'setup_billing': '/api/services/billing'
      },
      requiredData: {
        'activate_service': ['customerId', 'serviceType', 'planId'],
        'provision_equipment': ['customerId', 'equipmentType', 'location'],
        'setup_billing': ['customerId', 'billingPlan', 'paymentMethod']
      }
    },
    'field-ops': {
      endpoints: {
        'create_work_order': '/api/work-orders',
        'assign_technician': '/api/work-orders/{orderId}/assign',
        'schedule_installation': '/api/work-orders/{orderId}/schedule'
      },
      requiredData: {
        'create_work_order': ['customerId', 'workType', 'location', 'priority'],
        'assign_technician': ['orderId', 'technicianId'],
        'schedule_installation': ['orderId', 'appointmentTime', 'timeWindow']
      }
    },
    'support-system': {
      endpoints: {
        'create_ticket': '/api/support/tickets',
        'assign_agent': '/api/support/tickets/{ticketId}/assign',
        'escalate_ticket': '/api/support/tickets/{ticketId}/escalate'
      },
      requiredData: {
        'create_ticket': ['customerId', 'issue', 'priority'],
        'assign_agent': ['ticketId', 'agentId'],
        'escalate_ticket': ['ticketId', 'escalationLevel', 'reason']
      }
    },
    'billing-system': {
      endpoints: {
        'setup_billing': '/api/billing/accounts',
        'process_payment': '/api/billing/payments',
        'generate_invoice': '/api/billing/invoices'
      },
      requiredData: {
        'setup_billing': ['customerId', 'billingAddress', 'paymentMethod'],
        'process_payment': ['customerId', 'amount', 'paymentMethodId'],
        'generate_invoice': ['customerId', 'services', 'billingPeriod']
      }
    }
  };

  constructor(tenantId: string) {
    this.tenantId = tenantId;
    this.eventBus = JourneyEventBus.getInstance(tenantId);
    this.setupEventHandlers();
  }

  /**
   * Create a new handoff between packages
   */
  async createHandoff(handoffData: Omit<HandoffRecord, 'id' | 'startedAt'>): Promise<HandoffRecord> {
    const handoff: HandoffRecord = {
      ...handoffData,
      id: `handoff_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      startedAt: new Date().toISOString(),
      status: 'pending'
    };

    // Validate handoff data
    const validation = this.validateHandoffData(handoff);
    if (!validation.isValid) {
      handoff.status = 'failed';
      handoff.errorMessage = `Validation failed: ${validation.errors.join(', ')}`;
      handoff.validationErrors = validation.errors;
      return handoff;
    }

    // Store pending handoff
    this.pendingHandoffs.set(handoff.id, handoff);

    // Set timeout for handoff completion
    this.setHandoffTimeout(handoff.id);

    // Emit handoff started event
    await this.eventBus.emitHandoffStarted(handoff);

    // Process handoff based on type
    if (handoff.handoffType === 'automatic') {
      // Process immediately for automatic handoffs
      setImmediate(() => this.processHandoff(handoff.id));
    }

    return handoff;
  }

  /**
   * Process a pending handoff
   */
  async processHandoff(handoffId: string): Promise<void> {
    const handoff = this.pendingHandoffs.get(handoffId);
    if (!handoff) {
      throw new Error(`Handoff ${handoffId} not found`);
    }

    if (handoff.status !== 'pending') {
      throw new Error(`Handoff ${handoffId} is not in pending status`);
    }

    // Update status to in_progress
    handoff.status = 'in_progress';
    this.pendingHandoffs.set(handoffId, handoff);

    try {
      // Execute handoff based on target package
      const result = await this.executePackageHandoff(handoff);

      // Mark handoff as completed
      handoff.status = 'completed';
      handoff.completedAt = new Date().toISOString();
      handoff.result = result.success ? 'success' : 'failure';

      if (result.data) {
        handoff.data = { ...handoff.data, ...result.data };
      }

      if (result.error) {
        handoff.errorMessage = result.error;
      }

      // Clear timeout
      this.clearHandoffTimeout(handoffId);

      // Emit completion event
      await this.eventBus.emitHandoffCompleted(handoff);

      // Remove from pending handoffs
      this.pendingHandoffs.delete(handoffId);

    } catch (error) {
      handoff.status = 'failed';
      handoff.completedAt = new Date().toISOString();
      handoff.result = 'failure';
      handoff.errorMessage = error instanceof Error ? error.message : 'Unknown error';

      this.clearHandoffTimeout(handoffId);
      this.pendingHandoffs.delete(handoffId);

      console.error(`Handoff ${handoffId} failed:`, error);
    }
  }

  /**
   * Approve a handoff that requires approval
   */
  async approveHandoff(handoffId: string, approverNotes?: string): Promise<void> {
    const handoff = this.pendingHandoffs.get(handoffId);
    if (!handoff) {
      throw new Error(`Handoff ${handoffId} not found`);
    }

    if (handoff.handoffType !== 'approval_required') {
      throw new Error(`Handoff ${handoffId} does not require approval`);
    }

    if (approverNotes) {
      handoff.notes = approverNotes;
    }

    // Process the approved handoff
    await this.processHandoff(handoffId);
  }

  /**
   * Reject a handoff that requires approval
   */
  async rejectHandoff(handoffId: string, reason: string): Promise<void> {
    const handoff = this.pendingHandoffs.get(handoffId);
    if (!handoff) {
      throw new Error(`Handoff ${handoffId} not found`);
    }

    handoff.status = 'failed';
    handoff.completedAt = new Date().toISOString();
    handoff.result = 'failure';
    handoff.errorMessage = `Rejected: ${reason}`;

    this.clearHandoffTimeout(handoffId);
    this.pendingHandoffs.delete(handoffId);
  }

  /**
   * Get all active handoffs
   */
  getActiveHandoffs(): HandoffRecord[] {
    return Array.from(this.pendingHandoffs.values());
  }

  /**
   * Get handoffs requiring approval
   */
  getPendingApprovals(): HandoffRecord[] {
    return Array.from(this.pendingHandoffs.values())
      .filter(h => h.handoffType === 'approval_required' && h.status === 'pending');
  }

  /**
   * Get failed handoffs for retry
   */
  getFailedHandoffs(): HandoffRecord[] {
    return Array.from(this.pendingHandoffs.values())
      .filter(h => h.status === 'failed');
  }

  /**
   * Retry failed handoffs
   */
  async retryFailedHandoffs(handoffIds: string[]): Promise<void> {
    const retryPromises = handoffIds.map(async (id) => {
      const handoff = this.pendingHandoffs.get(id);
      if (handoff && handoff.status === 'failed') {
        handoff.status = 'pending';
        handoff.errorMessage = undefined;
        handoff.validationErrors = undefined;
        await this.processHandoff(id);
      }
    });

    await Promise.all(retryPromises);
  }

  /**
   * Bulk process multiple handoffs
   */
  async bulkProcessHandoffs(handoffIds: string[]): Promise<void> {
    const processPromises = handoffIds.map(id => this.processHandoff(id));
    await Promise.allSettled(processPromises);
  }

  // Private methods

  private validateHandoffData(handoff: HandoffRecord): { isValid: boolean; errors: string[] } {
    const errors: string[] = [];

    // Check if target package exists
    const packageConfig = this.packageConfigs[handoff.toPackage as keyof typeof this.packageConfigs];
    if (!packageConfig) {
      errors.push(`Unknown target package: ${handoff.toPackage}`);
      return { isValid: false, errors };
    }

    // Check if required data is present
    const requiredData = handoff.requiredData || [];
    for (const field of requiredData) {
      if (!(field in handoff.data)) {
        errors.push(`Missing required field: ${field}`);
      }
    }

    return { isValid: errors.length === 0, errors };
  }

  private async executePackageHandoff(handoff: HandoffRecord): Promise<{
    success: boolean;
    data?: any;
    error?: string;
  }> {
    const packageConfig = this.packageConfigs[handoff.toPackage as keyof typeof this.packageConfigs];
    if (!packageConfig) {
      return { success: false, error: `Unknown package: ${handoff.toPackage}` };
    }

    try {
      // This would make actual API calls to the target package
      // For now, we'll simulate the handoff execution
      const result = await this.simulatePackageCall(handoff);

      return {
        success: true,
        data: result
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Package execution failed'
      };
    }
  }

  private async simulatePackageCall(handoff: HandoffRecord): Promise<any> {
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000));

    // Simulate success/failure
    if (Math.random() < 0.1) { // 10% failure rate
      throw new Error('Simulated package call failure');
    }

    // Return simulated response based on handoff type
    switch (handoff.toPackage) {
      case 'crm':
        return { customerId: `cust_${Date.now()}`, leadConverted: true };
      case 'business-logic':
        return { serviceId: `svc_${Date.now()}`, status: 'activated' };
      case 'field-ops':
        return { workOrderId: `wo_${Date.now()}`, status: 'scheduled' };
      case 'support-system':
        return { ticketId: `tick_${Date.now()}`, status: 'open' };
      case 'billing-system':
        return { billingAccountId: `bill_${Date.now()}`, status: 'active' };
      default:
        return { status: 'completed' };
    }
  }

  private setHandoffTimeout(handoffId: string): void {
    const timeout = setTimeout(() => {
      const handoff = this.pendingHandoffs.get(handoffId);
      if (handoff && handoff.status === 'pending') {
        handoff.status = 'failed';
        handoff.errorMessage = 'Handoff timeout exceeded';
        handoff.completedAt = new Date().toISOString();
        this.pendingHandoffs.delete(handoffId);
      }
    }, 5 * 60 * 1000); // 5 minutes timeout

    this.handoffTimeouts.set(handoffId, timeout);
  }

  private clearHandoffTimeout(handoffId: string): void {
    const timeout = this.handoffTimeouts.get(handoffId);
    if (timeout) {
      clearTimeout(timeout);
      this.handoffTimeouts.delete(handoffId);
    }
  }

  private setupEventHandlers(): void {
    // Listen for journey events that should trigger handoffs
    this.eventBus.onEventType('crm:lead_qualified', async (event) => {
      if (event.leadId) {
        await this.createHandoff({
          journeyId: event.journeyId || '',
          fromPackage: 'crm',
          toPackage: 'business-logic',
          stepId: 'service_setup',
          handoffType: 'automatic',
          data: {
            leadId: event.leadId,
            customerId: event.customerId,
            qualificationData: event.data
          },
          requiredData: ['leadId', 'customerId']
        });
      }
    });

    // Handle service activation to trigger field operations
    this.eventBus.onEventType('service:activated', async (event) => {
      if (event.customerId) {
        await this.createHandoff({
          journeyId: event.journeyId || '',
          fromPackage: 'business-logic',
          toPackage: 'field-ops',
          stepId: 'installation_schedule',
          handoffType: 'automatic',
          data: {
            customerId: event.customerId,
            serviceId: event.data.serviceId,
            installationType: 'standard'
          },
          requiredData: ['customerId', 'serviceId']
        });
      }
    });

    // Handle support ticket creation
    this.eventBus.onEventType('support:ticket_created', async (event) => {
      if (event.customerId && event.data.priority === 'high') {
        await this.createHandoff({
          journeyId: event.journeyId || '',
          fromPackage: 'support-system',
          toPackage: 'field-ops',
          stepId: 'urgent_support_dispatch',
          handoffType: 'approval_required',
          data: {
            customerId: event.customerId,
            ticketId: event.data.ticketId,
            issue: event.data.issue
          },
          requiredData: ['customerId', 'ticketId']
        });
      }
    });
  }

  /**
   * Clean up resources
   */
  destroy(): void {
    // Clear all timeouts
    this.handoffTimeouts.forEach(timeout => clearTimeout(timeout));
    this.handoffTimeouts.clear();

    // Clear pending handoffs
    this.pendingHandoffs.clear();
  }
}
