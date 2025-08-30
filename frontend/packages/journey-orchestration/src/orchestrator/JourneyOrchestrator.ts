import { BehaviorSubject, Observable, Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import type {
  CustomerJourney,
  JourneyTemplate,
  JourneyStep,
  JourneyTrigger,
  TouchpointRecord,
  ConversionEvent,
  JourneyStage,
  JourneyStatus
} from '../types';
import { JourneyEventBus } from '../events/EventBus';
import { HandoffSystem } from '../handoffs/HandoffSystem';

/**
 * Journey Orchestrator - Main engine for managing customer journeys
 * Coordinates between packages, manages state, and tracks progress
 */
export class JourneyOrchestrator {
  private tenantId: string;
  private eventBus: JourneyEventBus;
  private handoffSystem: HandoffSystem;

  // State management
  private journeys = new Map<string, CustomerJourney>();
  private templates = new Map<string, JourneyTemplate>();
  private triggers = new Map<string, JourneyTrigger>();

  // Reactive state streams
  private journeysSubject = new BehaviorSubject<CustomerJourney[]>([]);
  private activeJourneySubject = new BehaviorSubject<CustomerJourney | null>(null);
  private stateChanges = new Subject<{ type: string; journeyId: string; data?: any }>();

  // Configuration
  private config = {
    maxConcurrentJourneys: 100,
    stepTimeoutMinutes: 60,
    autoProgressEnabled: true,
    persistenceEnabled: true
  };

  constructor(tenantId: string, configuration?: Partial<typeof this.config>) {
    this.tenantId = tenantId;
    this.config = { ...this.config, ...configuration };

    this.eventBus = JourneyEventBus.getInstance(tenantId);
    this.handoffSystem = new HandoffSystem(tenantId);

    this.setupEventHandlers();
    this.setupStateManagement();
  }

  /**
   * Start a new customer journey from template
   */
  async startJourney(
    templateId: string,
    context: Record<string, any> = {},
    customerId?: string,
    leadId?: string
  ): Promise<CustomerJourney> {
    const template = this.templates.get(templateId);
    if (!template) {
      throw new Error(`Journey template ${templateId} not found`);
    }

    // Check concurrent journey limit
    const activeJourneys = Array.from(this.journeys.values())
      .filter(j => j.status === 'active').length;

    if (activeJourneys >= this.config.maxConcurrentJourneys) {
      throw new Error('Maximum concurrent journeys limit reached');
    }

    // Create journey from template
    const journey: CustomerJourney = {
      id: `journey_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      customerId,
      leadId,
      tenantId: this.tenantId,
      name: template.name,
      type: template.category,
      stage: template.steps[0]?.stage || 'prospect',
      status: 'active',
      priority: context.priority || 'medium',
      startedAt: new Date().toISOString(),
      lastActivity: new Date().toISOString(),
      currentStep: template.steps[0]?.id || '',
      completedSteps: [],
      totalSteps: template.steps.length,
      progress: 0,
      context: { ...template.defaultContext, ...context, templateId },
      metadata: { templateId, version: template.version },
      activeHandoffs: [],
      integrationStatus: {},
      touchpoints: [],
      conversionEvents: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      createdBy: context.userId || 'system'
    };

    // Store journey
    this.journeys.set(journey.id, journey);

    // Update reactive streams
    this.updateJourneysStream();
    this.stateChanges.next({ type: 'journey_started', journeyId: journey.id });

    // Emit journey started event
    await this.eventBus.emitJourneyStarted(journey);

    // Auto-advance first step if enabled
    if (this.config.autoProgressEnabled && template.settings.autoProgress) {
      setImmediate(() => this.processNextStep(journey.id));
    }

    return journey;
  }

  /**
   * Advance journey to next step
   */
  async advanceStep(journeyId: string, stepId?: string): Promise<void> {
    const journey = this.journeys.get(journeyId);
    if (!journey) {
      throw new Error(`Journey ${journeyId} not found`);
    }

    const template = this.templates.get(journey.metadata.templateId);
    if (!template) {
      throw new Error(`Template for journey ${journeyId} not found`);
    }

    // Find current step
    const currentStepIndex = template.steps.findIndex(s => s.id === journey.currentStep);
    const currentStep = template.steps[currentStepIndex];

    if (!currentStep) {
      throw new Error(`Current step ${journey.currentStep} not found in template`);
    }

    // Mark current step as completed
    if (!journey.completedSteps.includes(currentStep.id)) {
      journey.completedSteps.push(currentStep.id);
    }

    // Emit step completion event
    await this.eventBus.emitJourneyStepCompleted(journeyId, currentStep.id);

    // Find next step
    let nextStep: JourneyStep | undefined;

    if (stepId) {
      // Specific step requested
      nextStep = template.steps.find(s => s.id === stepId);
    } else {
      // Get next step in sequence
      nextStep = template.steps[currentStepIndex + 1];
    }

    if (nextStep) {
      // Check if next step conditions are met
      const canAdvance = await this.checkStepConditions(journey, nextStep);

      if (!canAdvance.allowed) {
        throw new Error(`Cannot advance to step ${nextStep.id}: ${canAdvance.reason}`);
      }

      // Update journey to next step
      journey.currentStep = nextStep.id;
      journey.stage = nextStep.stage;
      journey.progress = Math.round((journey.completedSteps.length / journey.totalSteps) * 100);
      journey.lastActivity = new Date().toISOString();
      journey.updatedAt = new Date().toISOString();

      // Process the new step
      await this.processStep(journey, nextStep);
    } else {
      // No more steps - complete journey
      await this.completeJourney(journeyId);
    }

    // Update state
    this.journeys.set(journeyId, journey);
    this.updateJourneysStream();
    this.stateChanges.next({ type: 'step_advanced', journeyId, data: { stepId: nextStep?.id } });
  }

  /**
   * Skip a journey step with reason
   */
  async skipStep(journeyId: string, stepId: string, reason: string): Promise<void> {
    const journey = this.journeys.get(journeyId);
    if (!journey) {
      throw new Error(`Journey ${journeyId} not found`);
    }

    // Add skip metadata
    journey.metadata.skippedSteps = journey.metadata.skippedSteps || {};
    journey.metadata.skippedSteps[stepId] = {
      reason,
      timestamp: new Date().toISOString()
    };

    // Add to completed steps (as skipped)
    if (!journey.completedSteps.includes(stepId)) {
      journey.completedSteps.push(stepId);
    }

    journey.updatedAt = new Date().toISOString();
    this.journeys.set(journeyId, journey);

    // Advance to next step
    await this.advanceStep(journeyId);
  }

  /**
   * Pause journey execution
   */
  async pauseJourney(journeyId: string): Promise<void> {
    const journey = this.journeys.get(journeyId);
    if (!journey) {
      throw new Error(`Journey ${journeyId} not found`);
    }

    journey.status = 'paused';
    journey.metadata.pausedAt = new Date().toISOString();
    journey.updatedAt = new Date().toISOString();

    this.journeys.set(journeyId, journey);
    this.updateJourneysStream();
    this.stateChanges.next({ type: 'journey_paused', journeyId });
  }

  /**
   * Resume paused journey
   */
  async resumeJourney(journeyId: string): Promise<void> {
    const journey = this.journeys.get(journeyId);
    if (!journey) {
      throw new Error(`Journey ${journeyId} not found`);
    }

    if (journey.status !== 'paused') {
      throw new Error(`Journey ${journeyId} is not paused`);
    }

    journey.status = 'active';
    journey.lastActivity = new Date().toISOString();
    journey.updatedAt = new Date().toISOString();
    delete journey.metadata.pausedAt;

    this.journeys.set(journeyId, journey);
    this.updateJourneysStream();
    this.stateChanges.next({ type: 'journey_resumed', journeyId });

    // Continue processing if auto-progress enabled
    if (this.config.autoProgressEnabled) {
      await this.processNextStep(journeyId);
    }
  }

  /**
   * Complete a journey
   */
  async completeJourney(journeyId: string): Promise<void> {
    const journey = this.journeys.get(journeyId);
    if (!journey) {
      throw new Error(`Journey ${journeyId} not found`);
    }

    journey.status = 'completed';
    journey.completedAt = new Date().toISOString();
    journey.progress = 100;
    journey.updatedAt = new Date().toISOString();

    this.journeys.set(journeyId, journey);
    this.updateJourneysStream();

    // Emit completion event
    await this.eventBus.emitJourneyCompleted(journey);
    this.stateChanges.next({ type: 'journey_completed', journeyId });
  }

  /**
   * Abandon a journey
   */
  async abandonJourney(journeyId: string, reason?: string): Promise<void> {
    const journey = this.journeys.get(journeyId);
    if (!journey) {
      throw new Error(`Journey ${journeyId} not found`);
    }

    journey.status = 'abandoned';
    journey.completedAt = new Date().toISOString();
    journey.updatedAt = new Date().toISOString();
    journey.metadata.abandonmentReason = reason;

    this.journeys.set(journeyId, journey);
    this.updateJourneysStream();
    this.stateChanges.next({ type: 'journey_abandoned', journeyId, data: { reason } });
  }

  /**
   * Update journey context
   */
  async updateContext(journeyId: string, updates: Record<string, any>): Promise<void> {
    const journey = this.journeys.get(journeyId);
    if (!journey) {
      throw new Error(`Journey ${journeyId} not found`);
    }

    journey.context = { ...journey.context, ...updates };
    journey.updatedAt = new Date().toISOString();
    journey.lastActivity = new Date().toISOString();

    this.journeys.set(journeyId, journey);
    this.updateJourneysStream();
    this.stateChanges.next({ type: 'context_updated', journeyId, data: updates });
  }

  /**
   * Add touchpoint to journey
   */
  async addTouchpoint(
    journeyId: string,
    touchpoint: Omit<TouchpointRecord, 'id' | 'journeyId'>
  ): Promise<TouchpointRecord> {
    const journey = this.journeys.get(journeyId);
    if (!journey) {
      throw new Error(`Journey ${journeyId} not found`);
    }

    const fullTouchpoint: TouchpointRecord = {
      ...touchpoint,
      id: `tp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      journeyId,
      timestamp: touchpoint.timestamp || new Date().toISOString()
    };

    journey.touchpoints = journey.touchpoints || [];
    journey.touchpoints.push(fullTouchpoint);
    journey.lastActivity = new Date().toISOString();
    journey.updatedAt = new Date().toISOString();

    this.journeys.set(journeyId, journey);
    this.updateJourneysStream();

    // Emit touchpoint event
    await this.eventBus.emitTouchpointAdded(fullTouchpoint);

    return fullTouchpoint;
  }

  /**
   * Record conversion event
   */
  async recordConversion(
    journeyId: string,
    conversionEvent: Omit<ConversionEvent, 'id' | 'journeyId' | 'timestamp'>
  ): Promise<void> {
    const journey = this.journeys.get(journeyId);
    if (!journey) {
      throw new Error(`Journey ${journeyId} not found`);
    }

    const fullEvent: ConversionEvent = {
      ...conversionEvent,
      id: `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      journeyId,
      timestamp: new Date().toISOString()
    };

    journey.conversionEvents = journey.conversionEvents || [];
    journey.conversionEvents.push(fullEvent);
    journey.lastActivity = new Date().toISOString();
    journey.updatedAt = new Date().toISOString();

    this.journeys.set(journeyId, journey);
    this.updateJourneysStream();
  }

  /**
   * Get all journeys
   */
  getJourneys(): CustomerJourney[] {
    return Array.from(this.journeys.values());
  }

  /**
   * Get journey by ID
   */
  getJourney(journeyId: string): CustomerJourney | undefined {
    return this.journeys.get(journeyId);
  }

  /**
   * Search journeys
   */
  searchJourneys(query: string): CustomerJourney[] {
    const searchTerm = query.toLowerCase();
    return Array.from(this.journeys.values()).filter(journey =>
      journey.name.toLowerCase().includes(searchTerm) ||
      journey.type.toLowerCase().includes(searchTerm) ||
      journey.stage.toLowerCase().includes(searchTerm) ||
      journey.customerId?.toLowerCase().includes(searchTerm) ||
      journey.leadId?.toLowerCase().includes(searchTerm)
    );
  }

  /**
   * Filter journeys
   */
  filterJourneys(filters: {
    status?: JourneyStatus[];
    stage?: JourneyStage[];
    type?: string[];
    priority?: string[];
    assignedTo?: string[];
  }): CustomerJourney[] {
    return Array.from(this.journeys.values()).filter(journey => {
      if (filters.status && !filters.status.includes(journey.status)) return false;
      if (filters.stage && !filters.stage.includes(journey.stage)) return false;
      if (filters.type && !filters.type.includes(journey.type)) return false;
      if (filters.priority && !filters.priority.includes(journey.priority)) return false;
      if (filters.assignedTo && journey.assignedTo && !filters.assignedTo.includes(journey.assignedTo)) return false;
      return true;
    });
  }

  /**
   * Subscribe to journey changes
   */
  subscribeToJourneys(): Observable<CustomerJourney[]> {
    return this.journeysSubject.asObservable();
  }

  /**
   * Subscribe to active journey changes
   */
  subscribeToActiveJourney(): Observable<CustomerJourney | null> {
    return this.activeJourneySubject.asObservable();
  }

  /**
   * Subscribe to state changes
   */
  subscribeToStateChanges(): Observable<{ type: string; journeyId: string; data?: any }> {
    return this.stateChanges.asObservable();
  }

  /**
   * Load journey template
   */
  loadTemplate(template: JourneyTemplate): void {
    this.templates.set(template.id, template);
  }

  /**
   * Register journey trigger
   */
  registerTrigger(trigger: JourneyTrigger): void {
    this.triggers.set(trigger.id, trigger);
  }

  // Private methods

  private setupEventHandlers(): void {
    // Listen for external events that should trigger journeys
    this.eventBus.onEventType('crm:lead_converted', async (event) => {
      const trigger = Array.from(this.triggers.values())
        .find(t => t.event === 'lead_converted' && t.isActive);

      if (trigger && event.customerId) {
        await this.startJourney(
          trigger.templateId,
          {
            customerId: event.customerId,
            leadId: event.leadId,
            conversionSource: event.source
          },
          event.customerId,
          event.leadId
        );
      }
    });

    // Listen for journey trigger events
    this.eventBus.onEventType('journey:trigger', async (event) => {
      const templateId = event.data.templateId;
      const context = event.data.context || {};

      if (templateId) {
        await this.startJourney(templateId, context, event.customerId, event.leadId);
      }
    });

    // Listen for journey advance events
    this.eventBus.onEventType('journey:advance', async (event) => {
      if (event.data.journeyId) {
        await this.advanceStep(event.data.journeyId);
      }
    });
  }

  private setupStateManagement(): void {
    // Debounce state changes to prevent excessive updates
    this.stateChanges.pipe(
      debounceTime(100),
      distinctUntilChanged((prev, curr) =>
        prev.type === curr.type && prev.journeyId === curr.journeyId
      )
    ).subscribe(() => {
      if (this.config.persistenceEnabled) {
        this.persistState();
      }
    });
  }

  private updateJourneysStream(): void {
    this.journeysSubject.next(Array.from(this.journeys.values()));
  }

  private async processNextStep(journeyId: string): Promise<void> {
    try {
      await this.advanceStep(journeyId);
    } catch (error) {
      console.error(`Error processing next step for journey ${journeyId}:`, error);

      // Mark journey as failed if critical error
      const journey = this.journeys.get(journeyId);
      if (journey) {
        journey.status = 'failed';
        journey.metadata.error = error instanceof Error ? error.message : 'Unknown error';
        journey.updatedAt = new Date().toISOString();
        this.journeys.set(journeyId, journey);
        this.updateJourneysStream();
      }
    }
  }

  private async processStep(journey: CustomerJourney, step: JourneyStep): Promise<void> {
    // Handle different step types
    switch (step.type) {
      case 'integration':
        await this.processIntegrationStep(journey, step);
        break;
      case 'approval':
        await this.processApprovalStep(journey, step);
        break;
      case 'automated':
        await this.processAutomatedStep(journey, step);
        break;
      case 'notification':
        await this.processNotificationStep(journey, step);
        break;
      default:
        // Manual step - wait for external trigger
        break;
    }
  }

  private async processIntegrationStep(journey: CustomerJourney, step: JourneyStep): Promise<void> {
    if (step.integration) {
      // Create handoff to target package
      await this.handoffSystem.createHandoff({
        journeyId: journey.id,
        fromPackage: 'journey-orchestration',
        toPackage: step.integration.package,
        stepId: step.id,
        handoffType: 'automatic',
        data: {
          ...journey.context,
          ...step.integration.params
        },
        requiredData: step.requiredData
      });
    }
  }

  private async processApprovalStep(journey: CustomerJourney, step: JourneyStep): Promise<void> {
    // Create approval handoff
    await this.handoffSystem.createHandoff({
      journeyId: journey.id,
      fromPackage: 'journey-orchestration',
      toPackage: 'approval-system',
      stepId: step.id,
      handoffType: 'approval_required',
      data: journey.context,
      assignedTo: step.assignedTo
    });
  }

  private async processAutomatedStep(journey: CustomerJourney, step: JourneyStep): Promise<void> {
    // Execute automated step logic
    setTimeout(() => {
      this.advanceStep(journey.id);
    }, step.estimatedDuration * 1000 || 1000);
  }

  private async processNotificationStep(journey: CustomerJourney, step: JourneyStep): Promise<void> {
    // Send notification and auto-advance
    await this.eventBus.emitJourneyEvent({
      type: 'notification:send',
      source: 'journey-orchestration',
      journeyId: journey.id,
      data: {
        stepId: step.id,
        message: step.description,
        recipient: journey.assignedTo || journey.customerId
      }
    });

    // Auto-advance after notification
    setTimeout(() => {
      this.advanceStep(journey.id);
    }, 1000);
  }

  private async checkStepConditions(journey: CustomerJourney, step: JourneyStep): Promise<{
    allowed: boolean;
    reason?: string;
  }> {
    if (!step.entryConditions || step.entryConditions.length === 0) {
      return { allowed: true };
    }

    for (const condition of step.entryConditions) {
      const contextValue = journey.context[condition.field];
      const isConditionMet = this.evaluateCondition(contextValue, condition.operator, condition.value);

      if (!isConditionMet) {
        return {
          allowed: false,
          reason: `Condition not met: ${condition.field} ${condition.operator} ${condition.value}`
        };
      }
    }

    return { allowed: true };
  }

  private evaluateCondition(contextValue: any, operator: string, expectedValue: any): boolean {
    switch (operator) {
      case 'equals':
        return contextValue === expectedValue;
      case 'not_equals':
        return contextValue !== expectedValue;
      case 'contains':
        return String(contextValue).includes(String(expectedValue));
      case 'not_contains':
        return !String(contextValue).includes(String(expectedValue));
      case 'greater_than':
        return Number(contextValue) > Number(expectedValue);
      case 'less_than':
        return Number(contextValue) < Number(expectedValue);
      case 'exists':
        return contextValue !== undefined && contextValue !== null;
      case 'not_exists':
        return contextValue === undefined || contextValue === null;
      case 'in':
        return Array.isArray(expectedValue) && expectedValue.includes(contextValue);
      case 'not_in':
        return Array.isArray(expectedValue) && !expectedValue.includes(contextValue);
      default:
        return false;
    }
  }

  private async persistState(): Promise<void> {
    // In a real implementation, this would persist to database
    // For now, just log the persistence
    if (typeof window !== 'undefined' && window.localStorage) {
      const stateData = {
        journeys: Array.from(this.journeys.entries()),
        templates: Array.from(this.templates.entries()),
        triggers: Array.from(this.triggers.entries()),
        timestamp: new Date().toISOString()
      };

      localStorage.setItem(`journey_state_${this.tenantId}`, JSON.stringify(stateData));
    }
  }

  /**
   * Clean up resources
   */
  destroy(): void {
    this.journeysSubject.complete();
    this.activeJourneySubject.complete();
    this.stateChanges.complete();
    this.handoffSystem.destroy();
  }
}
