import EventEmitter from 'eventemitter3';
import type { JourneyEvent, CustomerJourney, HandoffRecord, TouchpointRecord } from '../types';

/**
 * Centralized event bus for journey orchestration
 * Handles cross-package communication and event routing
 */
export class JourneyEventBus extends EventEmitter {
  private static instance: JourneyEventBus | null = null;
  private eventHistory: JourneyEvent[] = [];
  private maxHistorySize = 1000;
  private processingQueue: JourneyEvent[] = [];
  private isProcessing = false;

  private constructor(private tenantId: string) {
    super();
    this.setupEventHandlers();
  }

  /**
   * Singleton pattern - one event bus per tenant
   */
  static getInstance(tenantId: string): JourneyEventBus {
    if (!JourneyEventBus.instance || JourneyEventBus.instance.tenantId !== tenantId) {
      JourneyEventBus.instance = new JourneyEventBus(tenantId);
    }
    return JourneyEventBus.instance;
  }

  /**
   * Emit a journey event to all listeners
   */
  async emitJourneyEvent(event: Omit<JourneyEvent, 'id' | 'timestamp'>): Promise<void> {
    const fullEvent: JourneyEvent = {
      ...event,
      id: `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      tenantId: this.tenantId,
      processed: false
    };

    // Add to history
    this.addToHistory(fullEvent);

    // Add to processing queue
    this.processingQueue.push(fullEvent);

    // Emit to listeners
    this.emit('journey:event', fullEvent);
    this.emit(event.type, fullEvent);

    // Process queue
    this.processEventQueue();
  }

  /**
   * Subscribe to journey events
   */
  onJourneyEvent(callback: (event: JourneyEvent) => void): () => void {
    this.on('journey:event', callback);
    return () => this.off('journey:event', callback);
  }

  /**
   * Subscribe to specific event types
   */
  onEventType(eventType: string, callback: (event: JourneyEvent) => void): () => void {
    this.on(eventType, callback);
    return () => this.off(eventType, callback);
  }

  /**
   * Journey lifecycle events
   */
  async emitJourneyStarted(journey: CustomerJourney): Promise<void> {
    await this.emitJourneyEvent({
      type: 'journey:started',
      source: 'journey-orchestration',
      journeyId: journey.id,
      customerId: journey.customerId,
      leadId: journey.leadId,
      data: {
        journeyType: journey.type,
        stage: journey.stage,
        templateId: journey.metadata.templateId
      }
    });
  }

  async emitJourneyStepCompleted(journeyId: string, stepId: string, output?: any): Promise<void> {
    await this.emitJourneyEvent({
      type: 'journey:step_completed',
      source: 'journey-orchestration',
      journeyId,
      data: {
        stepId,
        output,
        completedAt: new Date().toISOString()
      }
    });
  }

  async emitJourneyCompleted(journey: CustomerJourney): Promise<void> {
    await this.emitJourneyEvent({
      type: 'journey:completed',
      source: 'journey-orchestration',
      journeyId: journey.id,
      customerId: journey.customerId,
      data: {
        duration: journey.completedAt && journey.startedAt ?
          new Date(journey.completedAt).getTime() - new Date(journey.startedAt).getTime() : null,
        totalSteps: journey.totalSteps,
        completedSteps: journey.completedSteps.length
      }
    });
  }

  /**
   * CRM integration events
   */
  async emitLeadConverted(leadId: string, customerId: string, journeyId?: string): Promise<void> {
    await this.emitJourneyEvent({
      type: 'crm:lead_converted',
      source: 'crm',
      leadId,
      customerId,
      journeyId,
      data: {
        conversionDate: new Date().toISOString(),
        source: 'lead_conversion'
      }
    });
  }

  async emitCustomerCreated(customerId: string, leadId?: string, journeyId?: string): Promise<void> {
    await this.emitJourneyEvent({
      type: 'crm:customer_created',
      source: 'crm',
      customerId,
      leadId,
      journeyId,
      data: {
        creationDate: new Date().toISOString(),
        fromLead: !!leadId
      }
    });
  }

  /**
   * Service provisioning events
   */
  async emitServiceActivated(customerId: string, serviceId: string, journeyId?: string): Promise<void> {
    await this.emitJourneyEvent({
      type: 'service:activated',
      source: 'business-logic',
      customerId,
      journeyId,
      data: {
        serviceId,
        activationDate: new Date().toISOString()
      }
    });
  }

  /**
   * Support system events
   */
  async emitSupportTicketCreated(ticketId: string, customerId: string, journeyId?: string): Promise<void> {
    await this.emitJourneyEvent({
      type: 'support:ticket_created',
      source: 'support-system',
      customerId,
      journeyId,
      data: {
        ticketId,
        createdDate: new Date().toISOString()
      }
    });
  }

  /**
   * Handoff events
   */
  async emitHandoffStarted(handoff: HandoffRecord): Promise<void> {
    await this.emitJourneyEvent({
      type: 'handoff:started',
      source: 'journey-orchestration',
      journeyId: handoff.journeyId,
      data: {
        handoffId: handoff.id,
        fromPackage: handoff.fromPackage,
        toPackage: handoff.toPackage,
        handoffType: handoff.handoffType
      }
    });
  }

  async emitHandoffCompleted(handoff: HandoffRecord): Promise<void> {
    await this.emitJourneyEvent({
      type: 'handoff:completed',
      source: 'journey-orchestration',
      journeyId: handoff.journeyId,
      data: {
        handoffId: handoff.id,
        result: handoff.result,
        duration: handoff.completedAt && handoff.startedAt ?
          new Date(handoff.completedAt).getTime() - new Date(handoff.startedAt).getTime() : null
      }
    });
  }

  /**
   * Touchpoint events
   */
  async emitTouchpointAdded(touchpoint: TouchpointRecord): Promise<void> {
    await this.emitJourneyEvent({
      type: 'touchpoint:added',
      source: touchpoint.source,
      journeyId: touchpoint.journeyId,
      data: {
        touchpointId: touchpoint.id,
        type: touchpoint.type,
        channel: touchpoint.channel,
        outcome: touchpoint.outcome
      }
    });
  }

  /**
   * Get event history
   */
  getEventHistory(limit?: number): JourneyEvent[] {
    return limit ? this.eventHistory.slice(-limit) : [...this.eventHistory];
  }

  /**
   * Get events for specific journey
   */
  getJourneyEvents(journeyId: string): JourneyEvent[] {
    return this.eventHistory.filter(event => event.journeyId === journeyId);
  }

  /**
   * Clear event history
   */
  clearHistory(): void {
    this.eventHistory = [];
  }

  /**
   * Get processing queue status
   */
  getQueueStatus(): { pending: number; processing: boolean } {
    return {
      pending: this.processingQueue.length,
      processing: this.isProcessing
    };
  }

  /**
   * Setup default event handlers for cross-package integration
   */
  private setupEventHandlers(): void {
    // Listen for CRM events to trigger journey progression
    this.on('crm:lead_converted', async (event: JourneyEvent) => {
      // Automatically advance journeys when leads are converted
      this.emit('journey:trigger', {
        type: 'lead_conversion',
        leadId: event.leadId,
        customerId: event.customerId,
        templateId: 'customer_onboarding'
      });
    });

    // Listen for service activation to complete onboarding journeys
    this.on('service:activated', async (event: JourneyEvent) => {
      if (event.journeyId) {
        this.emit('journey:advance', {
          journeyId: event.journeyId,
          stepType: 'service_activation_complete'
        });
      }
    });

    // Listen for support tickets to trigger support journeys
    this.on('support:ticket_created', async (event: JourneyEvent) => {
      this.emit('journey:trigger', {
        type: 'support_needed',
        customerId: event.customerId,
        templateId: 'support_resolution',
        context: {
          ticketId: event.data.ticketId,
          priority: event.data.priority || 'medium'
        }
      });
    });
  }

  /**
   * Add event to history with size management
   */
  private addToHistory(event: JourneyEvent): void {
    this.eventHistory.push(event);

    // Maintain history size limit
    if (this.eventHistory.length > this.maxHistorySize) {
      this.eventHistory = this.eventHistory.slice(-this.maxHistorySize);
    }
  }

  /**
   * Process event queue for reliable event handling
   */
  private async processEventQueue(): Promise<void> {
    if (this.isProcessing || this.processingQueue.length === 0) {
      return;
    }

    this.isProcessing = true;

    try {
      while (this.processingQueue.length > 0) {
        const event = this.processingQueue.shift();
        if (event) {
          await this.processEvent(event);
        }
      }
    } catch (error) {
      console.error('Error processing event queue:', error);
    } finally {
      this.isProcessing = false;
    }
  }

  /**
   * Process individual events
   */
  private async processEvent(event: JourneyEvent): Promise<void> {
    try {
      // Mark as processing
      const historyIndex = this.eventHistory.findIndex(e => e.id === event.id);
      if (historyIndex >= 0) {
        this.eventHistory[historyIndex] = { ...event, processed: true };
      }

      // Emit processed event
      this.emit('journey:event_processed', event);
    } catch (error) {
      console.error(`Error processing event ${event.id}:`, error);

      // Mark as failed
      const historyIndex = this.eventHistory.findIndex(e => e.id === event.id);
      if (historyIndex >= 0) {
        this.eventHistory[historyIndex] = {
          ...event,
          processed: false,
          processingErrors: [...(event.processingErrors || []), error instanceof Error ? error.message : 'Unknown error']
        };
      }
    }
  }

  /**
   * Clean up resources
   */
  destroy(): void {
    this.removeAllListeners();
    this.eventHistory = [];
    this.processingQueue = [];
    JourneyEventBus.instance = null;
  }
}
