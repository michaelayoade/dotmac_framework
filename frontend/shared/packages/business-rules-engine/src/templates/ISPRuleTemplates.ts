import type { BusinessRule, RuleTemplate } from '../types';

/**
 * Pre-built rule templates for common ISP operations
 */
export const ISPRuleTemplates: RuleTemplate[] = [
  // Billing & Payment Rules
  {
    id: 'auto_suspend_non_payment',
    name: 'Auto Suspend Service for Non-Payment',
    description: 'Automatically suspend service when payment is overdue by specified days',
    category: 'billing',
    template: {
      name: 'Auto Suspend Service for Non-Payment',
      description: 'Automatically suspend service when payment is overdue by specified days',
      category: 'billing',
      conditions: [
        {
          id: 'condition_1',
          field: 'billing.daysPastDue',
          operator: 'greater_than',
          value: '{{days_past_due_threshold}}',
        },
        {
          id: 'condition_2',
          field: 'customer.status',
          operator: 'equals',
          value: 'active',
        },
      ],
      conditionLogic: 'all',
      actions: [
        {
          id: 'action_1',
          type: 'suspend_service',
          parameters: {
            reason: 'non_payment',
            notifyCustomer: true,
          },
        },
        {
          id: 'action_2',
          type: 'create_task',
          parameters: {
            title: 'Service suspended - Follow up required',
            description:
              'Customer {{customer.id}} service suspended for {{billing.daysPastDue}} days overdue payment',
            assignedTo: 'billing_team',
            priority: 'high',
          },
        },
        {
          id: 'action_3',
          type: 'log_event',
          parameters: {
            eventType: 'service_event',
            message:
              'Service suspended for customer {{customer.id}} due to {{billing.daysPastDue}} days overdue payment',
          },
        },
      ],
      priority: 800,
      status: 'draft',
      portalScope: ['admin', 'management'],
      tags: ['billing', 'suspension', 'automation'],
    },
    variables: {
      days_past_due_threshold: {
        type: 'number',
        description: 'Number of days past due before suspension',
        defaultValue: 30,
      },
    },
  },

  {
    id: 'loyalty_discount',
    name: 'Long-term Customer Loyalty Discount',
    description: 'Apply automatic discount for customers with long tenure and good payment history',
    category: 'billing',
    template: {
      name: 'Long-term Customer Loyalty Discount',
      description:
        'Apply automatic discount for customers with long tenure and good payment history',
      category: 'billing',
      conditions: [
        {
          id: 'condition_1',
          field: 'customer.monthsActive',
          operator: 'greater_equal',
          value: '{{minimum_months}}',
        },
        {
          id: 'condition_2',
          field: 'billing.daysPastDue',
          operator: 'equals',
          value: 0,
        },
        {
          id: 'condition_3',
          field: 'customer.monthlyRevenue',
          operator: 'greater_equal',
          value: '{{minimum_revenue}}',
        },
      ],
      conditionLogic: 'all',
      actions: [
        {
          id: 'action_1',
          type: 'apply_discount',
          value: '{{discount_percentage}}',
          parameters: {
            discountType: 'percentage',
            reason: 'Long-term customer loyalty discount',
          },
        },
        {
          id: 'action_2',
          type: 'send_notification',
          parameters: {
            type: 'email',
            message:
              'Congratulations! You qualify for a {{discount_percentage}}% loyalty discount.',
            recipients: 'customer.email',
          },
        },
        {
          id: 'action_3',
          type: 'log_event',
          parameters: {
            eventType: 'billing_event',
            message:
              'Applied {{discount_percentage}}% loyalty discount to customer {{customer.id}}',
          },
        },
      ],
      priority: 600,
      status: 'draft',
      portalScope: ['admin', 'customer'],
      tags: ['billing', 'loyalty', 'discount'],
    },
    variables: {
      minimum_months: {
        type: 'number',
        description: 'Minimum months as customer',
        defaultValue: 12,
      },
      minimum_revenue: {
        type: 'number',
        description: 'Minimum monthly revenue',
        defaultValue: 100,
      },
      discount_percentage: {
        type: 'number',
        description: 'Discount percentage to apply',
        defaultValue: 10,
      },
    },
  },

  // Service Provisioning Rules
  {
    id: 'auto_approve_fiber',
    name: 'Auto-approve Fiber Installation',
    description: 'Automatically approve fiber installation requests in covered areas',
    category: 'provisioning',
    template: {
      name: 'Auto-approve Fiber Installation',
      description: 'Automatically approve fiber installation requests in covered areas',
      category: 'provisioning',
      conditions: [
        {
          id: 'condition_1',
          field: 'service.type',
          operator: 'equals',
          value: 'internet',
        },
        {
          id: 'condition_2',
          field: 'service.subType',
          operator: 'equals',
          value: 'fiber',
        },
        {
          id: 'condition_3',
          field: 'customer.creditScore',
          operator: 'greater_equal',
          value: '{{minimum_credit_score}}',
        },
      ],
      conditionLogic: 'all',
      actions: [
        {
          id: 'action_1',
          type: 'approve_request',
          parameters: {
            reason: 'Automatic approval - meets all criteria',
          },
        },
        {
          id: 'action_2',
          type: 'create_task',
          parameters: {
            title: 'Schedule fiber installation',
            description: 'Customer {{customer.id}} approved for fiber installation',
            assignedTo: 'technical_support',
            priority: 'medium',
          },
        },
        {
          id: 'action_3',
          type: 'send_notification',
          parameters: {
            type: 'email',
            message:
              'Your fiber installation request has been approved! We will contact you to schedule installation.',
            recipients: 'customer.email',
          },
        },
      ],
      priority: 700,
      status: 'draft',
      portalScope: ['admin', 'technician'],
      tags: ['provisioning', 'fiber', 'automation'],
    },
    variables: {
      minimum_credit_score: {
        type: 'number',
        description: 'Minimum credit score for auto-approval',
        defaultValue: 650,
      },
    },
  },

  // Customer Management Rules
  {
    id: 'enterprise_tier_upgrade',
    name: 'Enterprise Tier Auto-upgrade',
    description: 'Automatically upgrade customers to enterprise tier based on usage and contracts',
    category: 'customer_management',
    template: {
      name: 'Enterprise Tier Auto-upgrade',
      description:
        'Automatically upgrade customers to enterprise tier based on usage and contracts',
      category: 'customer_management',
      conditions: [
        {
          id: 'condition_1',
          field: 'customer.monthlyRevenue',
          operator: 'greater_equal',
          value: '{{revenue_threshold}}',
        },
        {
          id: 'condition_2',
          field: 'customer.contracts',
          operator: 'greater_equal',
          value: '{{contract_threshold}}',
        },
        {
          id: 'condition_3',
          field: 'customer.type',
          operator: 'not_equals',
          value: 'enterprise',
        },
      ],
      conditionLogic: 'all',
      actions: [
        {
          id: 'action_1',
          type: 'set_value',
          target: 'customer.type',
          value: 'enterprise',
        },
        {
          id: 'action_2',
          type: 'send_notification',
          parameters: {
            type: 'email',
            message:
              'Congratulations! You have been upgraded to our Enterprise tier with premium support and benefits.',
            recipients: 'customer.email',
          },
        },
        {
          id: 'action_3',
          type: 'create_task',
          parameters: {
            title: 'Enterprise onboarding required',
            description: 'Customer {{customer.id}} upgraded to enterprise - assign account manager',
            assignedTo: 'customer_success',
            priority: 'high',
          },
        },
      ],
      priority: 500,
      status: 'draft',
      portalScope: ['admin', 'customer'],
      tags: ['customer_management', 'tier_upgrade', 'enterprise'],
    },
    variables: {
      revenue_threshold: {
        type: 'number',
        description: 'Minimum monthly revenue for enterprise tier',
        defaultValue: 500,
      },
      contract_threshold: {
        type: 'number',
        description: 'Minimum number of contracts',
        defaultValue: 2,
      },
    },
  },

  // Network Operations Rules
  {
    id: 'high_usage_alert',
    name: 'High Bandwidth Usage Alert',
    description: 'Alert when customer exceeds bandwidth threshold',
    category: 'network_operations',
    template: {
      name: 'High Bandwidth Usage Alert',
      description: 'Alert when customer exceeds bandwidth threshold',
      category: 'network_operations',
      conditions: [
        {
          id: 'condition_1',
          field: 'service.lastUsage',
          operator: 'greater_than',
          value: '{{usage_threshold_percent}}',
        },
        {
          id: 'condition_2',
          field: 'service.status',
          operator: 'equals',
          value: 'active',
        },
      ],
      conditionLogic: 'all',
      actions: [
        {
          id: 'action_1',
          type: 'send_notification',
          parameters: {
            type: 'email',
            message:
              'You have used {{service.lastUsage}}% of your bandwidth allocation. Consider upgrading your plan.',
            recipients: 'customer.email',
          },
        },
        {
          id: 'action_2',
          type: 'create_task',
          parameters: {
            title: 'Upsell opportunity - high usage customer',
            description:
              'Customer {{customer.id}} is using {{service.lastUsage}}% of bandwidth - contact for plan upgrade',
            assignedTo: 'customer_success',
            priority: 'medium',
          },
        },
        {
          id: 'action_3',
          type: 'log_event',
          parameters: {
            eventType: 'usage_event',
            message:
              'High bandwidth usage alert for customer {{customer.id}} - {{service.lastUsage}}% utilized',
          },
        },
      ],
      priority: 400,
      status: 'draft',
      portalScope: ['admin', 'customer'],
      tags: ['network_operations', 'usage', 'upsell'],
    },
    variables: {
      usage_threshold_percent: {
        type: 'number',
        description: 'Usage percentage threshold for alert',
        defaultValue: 80,
      },
    },
  },

  // Support Rules
  {
    id: 'escalate_vip_customer',
    name: 'VIP Customer Issue Escalation',
    description: 'Automatically escalate support tickets for VIP customers',
    category: 'support',
    template: {
      name: 'VIP Customer Issue Escalation',
      description: 'Automatically escalate support tickets for VIP customers',
      category: 'support',
      conditions: [
        {
          id: 'condition_1',
          field: 'customer.type',
          operator: 'equals',
          value: 'enterprise',
        },
        {
          id: 'condition_2',
          field: 'customer.monthlyRevenue',
          operator: 'greater_equal',
          value: '{{vip_revenue_threshold}}',
        },
      ],
      conditionLogic: 'any',
      actions: [
        {
          id: 'action_1',
          type: 'escalate',
          parameters: {
            level: 'manager',
            reason: 'VIP customer - priority handling required',
          },
        },
        {
          id: 'action_2',
          type: 'send_notification',
          parameters: {
            type: 'in_app',
            message: 'VIP customer {{customer.id}} has an open ticket - priority handling required',
            recipients: 'support_manager',
          },
        },
        {
          id: 'action_3',
          type: 'update_status',
          target: 'ticket.priority',
          value: 'high',
        },
      ],
      priority: 900,
      status: 'draft',
      portalScope: ['admin', 'technician'],
      tags: ['support', 'vip', 'escalation'],
    },
    variables: {
      vip_revenue_threshold: {
        type: 'number',
        description: 'Revenue threshold for VIP treatment',
        defaultValue: 1000,
      },
    },
  },

  // Compliance Rules
  {
    id: 'gdpr_data_retention',
    name: 'GDPR Data Retention Compliance',
    description: 'Archive or delete customer data based on retention policies',
    category: 'compliance',
    template: {
      name: 'GDPR Data Retention Compliance',
      description: 'Archive or delete customer data based on retention policies',
      category: 'compliance',
      conditions: [
        {
          id: 'condition_1',
          field: 'customer.status',
          operator: 'equals',
          value: 'terminated',
        },
        {
          id: 'condition_2',
          field: 'customer.monthsInactive',
          operator: 'greater_equal',
          value: '{{retention_months}}',
        },
      ],
      conditionLogic: 'all',
      actions: [
        {
          id: 'action_1',
          type: 'create_task',
          parameters: {
            title: 'GDPR compliance - review customer data for archival/deletion',
            description:
              'Customer {{customer.id}} data needs review for GDPR compliance (inactive {{customer.monthsInactive}} months)',
            assignedTo: 'compliance_team',
            priority: 'high',
          },
        },
        {
          id: 'action_2',
          type: 'log_event',
          parameters: {
            eventType: 'compliance_event',
            message: 'GDPR data retention review triggered for customer {{customer.id}}',
          },
        },
        {
          id: 'action_3',
          type: 'execute_webhook',
          parameters: {
            endpoint: 'compliance_system',
          },
        },
      ],
      priority: 950,
      status: 'draft',
      portalScope: ['admin', 'management'],
      tags: ['compliance', 'gdpr', 'data_retention'],
    },
    variables: {
      retention_months: {
        type: 'number',
        description: 'Months to retain data after termination',
        defaultValue: 24,
      },
    },
  },
];

/**
 * Helper function to instantiate a rule template with custom variables
 */
export function instantiateRuleTemplate(
  templateId: string,
  variables: Record<string, any>,
  customizations?: Partial<BusinessRule>
): BusinessRule {
  const template = ISPRuleTemplates.find((t) => t.id === templateId);
  if (!template) {
    throw new Error(`Template not found: ${templateId}`);
  }

  // Create a deep copy of the template
  const rule: BusinessRule = {
    ...JSON.parse(JSON.stringify(template.template)),
    id: `rule_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    createdAt: new Date(),
    updatedAt: new Date(),
    createdBy: 'system',
    updatedBy: 'system',
    ...customizations,
  };

  // Replace variables in the rule
  const ruleString = JSON.stringify(rule);
  const processedRuleString = ruleString.replace(/\{\{(\w+)\}\}/g, (match, varName) => {
    return variables[varName] !== undefined ? variables[varName].toString() : match;
  });

  return JSON.parse(processedRuleString);
}

/**
 * Get rule templates by category
 */
export function getRuleTemplatesByCategory(category: string): RuleTemplate[] {
  return ISPRuleTemplates.filter((template) => template.category === category);
}

/**
 * Get all available categories
 */
export function getRuleTemplateCategories(): string[] {
  return Array.from(new Set(ISPRuleTemplates.map((template) => template.category)));
}
