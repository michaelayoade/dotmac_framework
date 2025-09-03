import type {
  ActionResult,
  BusinessRule,
  ConditionOperator,
  ConditionResult,
  RuleAction,
  RuleCondition,
  RuleContext,
  RuleEngineConfig,
  RuleExecutionResult,
} from '../types';

// Simple get function to replace lodash
function get(obj: any, path: string): any {
  return path.split('.').reduce((current, key) => current?.[key], obj);
}

export class RuleEngine {
  private config: RuleEngineConfig;
  private auditLog: RuleExecutionResult[] = [];

  constructor(config: RuleEngineConfig = {}) {
    this.config = {
      enableDebug: false,
      maxExecutionTime: 5000,
      enableAuditLog: true,
      customFunctions: {},
      webhookEndpoints: {},
      ...config,
    };

    // Custom functions would be registered here in a real implementation
  }

  /**
   * Execute a set of rules against a context
   */
  async executeRules(rules: BusinessRule[], context: RuleContext): Promise<RuleExecutionResult[]> {
    const results: RuleExecutionResult[] = [];

    // Filter active rules applicable to current portal
    const activeRules = rules.filter(
      (rule) =>
        rule.status === 'active' &&
        (!rule.portalScope.length || rule.portalScope.includes(context.portal!))
    );

    // Sort by priority (higher priority first)
    const sortedRules = activeRules.sort((a, b) => b.priority - a.priority);

    for (const rule of sortedRules) {
      try {
        const result = await this.executeRule(rule, context);
        results.push(result);

        if (this.config.enableAuditLog) {
          this.auditLog.push(result);
        }
      } catch (error) {
        const errorResult: RuleExecutionResult = {
          ruleId: rule.id,
          ruleName: rule.name,
          matched: false,
          conditionsEvaluated: [],
          actionsExecuted: [],
          executionTime: 0,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
        results.push(errorResult);
      }
    }

    return results;
  }

  /**
   * Execute a single rule
   */
  private async executeRule(
    rule: BusinessRule,
    context: RuleContext
  ): Promise<RuleExecutionResult> {
    const startTime = Date.now();

    // Evaluate conditions
    const conditionsEvaluated = await this.evaluateConditions(rule, context);
    const allConditionsMet = this.checkConditionLogic(rule, conditionsEvaluated);

    let actionsExecuted: ActionResult[] = [];

    // Execute actions if conditions are met
    if (allConditionsMet) {
      actionsExecuted = await this.executeActions(rule.actions, context);
    }

    const executionTime = Date.now() - startTime;

    const result: RuleExecutionResult = {
      ruleId: rule.id,
      ruleName: rule.name,
      matched: allConditionsMet,
      conditionsEvaluated,
      actionsExecuted,
      executionTime,
    };

    if (this.config.enableDebug) {
      console.log('Rule execution result:', result);
    }

    return result;
  }

  /**
   * Evaluate all conditions in a rule
   */
  private async evaluateConditions(
    rule: BusinessRule,
    context: RuleContext
  ): Promise<ConditionResult[]> {
    const results: ConditionResult[] = [];

    for (const condition of rule.conditions) {
      const result = await this.evaluateCondition(condition, context);
      results.push(result);
    }

    return results;
  }

  /**
   * Evaluate a single condition
   */
  private async evaluateCondition(
    condition: RuleCondition,
    context: RuleContext
  ): Promise<ConditionResult> {
    const actualValue = get(context, condition.field);
    const expectedValue = condition.value;

    let result = false;

    try {
      switch (condition.operator) {
        case 'equals':
          result = actualValue === expectedValue;
          break;
        case 'not_equals':
          result = actualValue !== expectedValue;
          break;
        case 'greater_than':
          result = actualValue > expectedValue;
          break;
        case 'less_than':
          result = actualValue < expectedValue;
          break;
        case 'greater_equal':
          result = actualValue >= expectedValue;
          break;
        case 'less_equal':
          result = actualValue <= expectedValue;
          break;
        case 'contains':
          result = actualValue?.toString().includes(expectedValue?.toString());
          break;
        case 'not_contains':
          result = !actualValue?.toString().includes(expectedValue?.toString());
          break;
        case 'in':
          result = Array.isArray(expectedValue) && expectedValue.includes(actualValue);
          break;
        case 'not_in':
          result = Array.isArray(expectedValue) && !expectedValue.includes(actualValue);
          break;
        case 'matches':
          result = new RegExp(expectedValue).test(actualValue?.toString() || '');
          break;
        case 'exists':
          result = actualValue !== undefined && actualValue !== null;
          break;
        case 'not_exists':
          result = actualValue === undefined || actualValue === null;
          break;
        default:
          throw new Error(`Unknown operator: ${condition.operator}`);
      }
    } catch (error) {
      console.error('Error evaluating condition:', error);
      result = false;
    }

    return {
      conditionId: condition.id,
      field: condition.field,
      operator: condition.operator,
      expectedValue,
      actualValue,
      result,
    };
  }

  /**
   * Check if condition logic is satisfied
   */
  private checkConditionLogic(rule: BusinessRule, conditionResults: ConditionResult[]): boolean {
    if (conditionResults.length === 0) return true;

    switch (rule.conditionLogic) {
      case 'all':
        return conditionResults.every((c) => c.result);
      case 'any':
        return conditionResults.some((c) => c.result);
      case 'custom':
        // Custom logic would be implemented here in a real application
        return conditionResults.every((c) => c.result);
      default:
        return conditionResults.every((c) => c.result);
    }
  }

  /**
   * Execute all actions in a rule
   */
  private async executeActions(
    actions: RuleAction[],
    context: RuleContext
  ): Promise<ActionResult[]> {
    const results: ActionResult[] = [];

    for (const action of actions) {
      const result = await this.executeAction(action, context);
      results.push(result);
    }

    return results;
  }

  /**
   * Execute a single action
   */
  private async executeAction(action: RuleAction, context: RuleContext): Promise<ActionResult> {
    try {
      let result: any;
      let executed = true;

      switch (action.type) {
        case 'set_value':
          if (action.target && context.metadata) {
            context.metadata[action.target] = action.value;
            result = action.value;
          }
          break;

        case 'send_notification':
          // Integration point for notification system
          result = await this.sendNotification(action, context);
          break;

        case 'create_task':
          // Integration point for task system
          result = await this.createTask(action, context);
          break;

        case 'update_status':
          if (action.target && context.metadata) {
            context.metadata[action.target + '_status'] = action.value;
            result = action.value;
          }
          break;

        case 'apply_discount':
          result = await this.applyDiscount(action, context);
          break;

        case 'suspend_service':
          result = await this.suspendService(action, context);
          break;

        case 'approve_request':
          if (context.metadata) {
            context.metadata.approval_status = 'approved';
            context.metadata.approval_reason = action.parameters?.reason;
          }
          result = 'approved';
          break;

        case 'reject_request':
          if (context.metadata) {
            context.metadata.approval_status = 'rejected';
            context.metadata.rejection_reason = action.parameters?.reason;
          }
          result = 'rejected';
          break;

        case 'escalate':
          result = await this.escalateIssue(action, context);
          break;

        case 'log_event':
          result = await this.logEvent(action, context);
          break;

        case 'trigger_workflow':
          result = await this.triggerWorkflow(action, context);
          break;

        case 'execute_webhook':
          result = await this.executeWebhook(action, context);
          break;

        default:
          executed = false;
          throw new Error(`Unknown action type: ${action.type}`);
      }

      return {
        actionId: action.id,
        type: action.type,
        executed,
        result,
      };
    } catch (error) {
      return {
        actionId: action.id,
        type: action.type,
        executed: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * ISP-specific helper functions would be registered here in a real implementation
   */

  // Action implementation methods
  private async sendNotification(action: RuleAction, context: RuleContext): Promise<any> {
    // Integration point - would connect to notification system
    console.log('Sending notification:', action.parameters);
    return { sent: true, type: action.parameters?.type };
  }

  private async createTask(action: RuleAction, context: RuleContext): Promise<any> {
    // Integration point - would connect to task management system
    console.log('Creating task:', action.parameters);
    return { taskId: `task_${Date.now()}`, status: 'created' };
  }

  private async applyDiscount(action: RuleAction, context: RuleContext): Promise<any> {
    const discountPercent = action.value || action.parameters?.percent || 0;
    console.log(`Applying ${discountPercent}% discount`);
    return { discount: discountPercent, applied: true };
  }

  private async suspendService(action: RuleAction, context: RuleContext): Promise<any> {
    console.log('Suspending service:', action.parameters);
    return { suspended: true, reason: action.parameters?.reason };
  }

  private async escalateIssue(action: RuleAction, context: RuleContext): Promise<any> {
    console.log('Escalating issue:', action.parameters);
    return { escalated: true, level: action.parameters?.level || 'manager' };
  }

  private async logEvent(action: RuleAction, context: RuleContext): Promise<any> {
    const logEntry = {
      timestamp: new Date(),
      event: action.parameters?.event,
      context: action.parameters?.includeContext ? context : undefined,
    };
    console.log('Logging event:', logEntry);
    return logEntry;
  }

  private async triggerWorkflow(action: RuleAction, context: RuleContext): Promise<any> {
    console.log('Triggering workflow:', action.parameters?.workflowId);
    return { workflowId: action.parameters?.workflowId, triggered: true };
  }

  private async executeWebhook(action: RuleAction, context: RuleContext): Promise<any> {
    const webhookUrl = this.config.webhookEndpoints?.[action.parameters?.endpoint || ''];
    if (!webhookUrl) {
      throw new Error('Webhook endpoint not configured');
    }

    console.log('Executing webhook:', webhookUrl);
    // In real implementation, would make HTTP request
    return { webhook: webhookUrl, executed: true };
  }

  /**
   * Get audit log
   */
  getAuditLog(): RuleExecutionResult[] {
    return [...this.auditLog];
  }

  /**
   * Clear audit log
   */
  clearAuditLog(): void {
    this.auditLog = [];
  }
}
