import { z } from 'zod';

// Core Types
export type PortalType = 'admin' | 'customer' | 'reseller' | 'technician' | 'management';
export type RuleStatus = 'active' | 'inactive' | 'draft' | 'archived';
export type ConditionOperator =
  | 'equals'
  | 'not_equals'
  | 'greater_than'
  | 'less_than'
  | 'greater_equal'
  | 'less_equal'
  | 'contains'
  | 'not_contains'
  | 'in'
  | 'not_in'
  | 'matches'
  | 'exists'
  | 'not_exists'
  | 'and'
  | 'or'
  | 'not';

export type ActionType =
  | 'set_value'
  | 'send_notification'
  | 'create_task'
  | 'update_status'
  | 'apply_discount'
  | 'suspend_service'
  | 'approve_request'
  | 'reject_request'
  | 'escalate'
  | 'log_event'
  | 'trigger_workflow'
  | 'execute_webhook';

// Rule Condition Schema
export const RuleConditionSchema = z.object({
  id: z.string(),
  field: z.string(),
  operator: z.enum([
    'equals',
    'not_equals',
    'greater_than',
    'less_than',
    'greater_equal',
    'less_equal',
    'contains',
    'not_contains',
    'in',
    'not_in',
    'matches',
    'exists',
    'not_exists',
    'and',
    'or',
    'not',
  ]),
  value: z.any(),
  dataType: z.enum(['string', 'number', 'boolean', 'date', 'array', 'object']).optional(),
});

export type RuleCondition = z.infer<typeof RuleConditionSchema>;

// Rule Action Schema
export const RuleActionSchema = z.object({
  id: z.string(),
  type: z.enum([
    'set_value',
    'send_notification',
    'create_task',
    'update_status',
    'apply_discount',
    'suspend_service',
    'approve_request',
    'reject_request',
    'escalate',
    'log_event',
    'trigger_workflow',
    'execute_webhook',
  ]),
  target: z.string().optional(),
  value: z.any().optional(),
  parameters: z.record(z.any()).optional(),
});

export type RuleAction = z.infer<typeof RuleActionSchema>;

// Business Rule Schema
export const BusinessRuleSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string().optional(),
  category: z.string(),
  conditions: z.array(RuleConditionSchema),
  conditionLogic: z.enum(['all', 'any', 'custom']).default('all'),
  customLogic: z.string().optional(), // For complex logic expressions
  actions: z.array(RuleActionSchema),
  priority: z.number().default(100),
  status: z.enum(['active', 'inactive', 'draft', 'archived']).default('draft'),
  portalScope: z.array(z.enum(['admin', 'customer', 'reseller', 'technician', 'management'])),
  tags: z.array(z.string()).default([]),
  effectiveDate: z.date().optional(),
  expirationDate: z.date().optional(),
  createdAt: z.date(),
  updatedAt: z.date(),
  createdBy: z.string(),
  updatedBy: z.string(),
});

export type BusinessRule = z.infer<typeof BusinessRuleSchema>;

// Rule Execution Context
export interface RuleContext {
  customer?: any;
  service?: any;
  billing?: any;
  user?: any;
  portal?: PortalType;
  timestamp?: Date;
  metadata?: Record<string, any>;
}

// Rule Execution Result
export interface RuleExecutionResult {
  ruleId: string;
  ruleName: string;
  matched: boolean;
  conditionsEvaluated: ConditionResult[];
  actionsExecuted: ActionResult[];
  executionTime: number;
  error?: string;
}

export interface ConditionResult {
  conditionId: string;
  field: string;
  operator: ConditionOperator;
  expectedValue: any;
  actualValue: any;
  result: boolean;
}

export interface ActionResult {
  actionId: string;
  type: ActionType;
  executed: boolean;
  result?: any;
  error?: string;
}

// Rule Engine Configuration
export interface RuleEngineConfig {
  enableDebug?: boolean;
  maxExecutionTime?: number; // milliseconds
  enableAuditLog?: boolean;
  customFunctions?: Record<string, Function>;
  webhookEndpoints?: Record<string, string>;
}

// ISP-Specific Entity Schemas
export const CustomerSchema = z.object({
  id: z.string(),
  type: z.enum(['residential', 'business', 'enterprise']),
  status: z.enum(['active', 'suspended', 'terminated']),
  creditScore: z.number().optional(),
  monthsActive: z.number(),
  monthlyRevenue: z.number(),
  paymentHistory: z.array(
    z.object({
      date: z.date(),
      amount: z.number(),
      status: z.enum(['paid', 'late', 'failed']),
    })
  ),
  services: z.array(z.string()),
  contracts: z.number().default(0),
});

export const ServiceSchema = z.object({
  id: z.string(),
  type: z.enum(['internet', 'phone', 'tv', 'bundle']),
  subType: z.enum(['dsl', 'fiber', 'cable', 'wireless']).optional(),
  bandwidth: z.number(),
  status: z.enum(['active', 'suspended', 'pending', 'terminated']),
  monthlyRate: z.number(),
  installationDate: z.date().optional(),
  lastUsage: z.number().optional(),
  usageLimit: z.number().optional(),
});

export const BillingSchema = z.object({
  customerId: z.string(),
  currentBalance: z.number(),
  pastDueAmount: z.number(),
  daysPastDue: z.number(),
  paymentMethod: z.enum(['credit_card', 'bank_transfer', 'check', 'cash']),
  autoPayEnabled: z.boolean(),
  billingCycle: z.enum(['monthly', 'quarterly', 'annual']),
  nextBillDate: z.date(),
});

// Rule Templates for ISP Operations
export interface RuleTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  template: Omit<BusinessRule, 'id' | 'createdAt' | 'updatedAt' | 'createdBy' | 'updatedBy'>;
  variables: Record<
    string,
    {
      type: 'string' | 'number' | 'boolean' | 'date';
      description: string;
      defaultValue?: any;
    }
  >;
}

export type Customer = z.infer<typeof CustomerSchema>;
export type Service = z.infer<typeof ServiceSchema>;
export type Billing = z.infer<typeof BillingSchema>;
