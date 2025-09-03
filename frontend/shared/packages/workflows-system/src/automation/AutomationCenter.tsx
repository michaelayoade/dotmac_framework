/**
 * Automation Center
 * Centralized management for business rules and automation workflows
 * Leverages existing RuleEngine and AutomationWorkflow from dotmac_shared
 */

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { clsx } from 'clsx';
import {
  Card,
  Button,
  Input,
  Select,
  Textarea,
  Badge,
  Table,
  Modal,
  Alert,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from '@dotmac/primitives';
import { PermissionGuard } from '@dotmac/rbac';
import { withComponentRegistration } from '@dotmac/registry';
import { useRenderProfiler } from '@dotmac/primitives/utils/performance';
import { standard_exception_handler } from '@dotmac/shared';
import { RuleEngine } from '@dotmac/business-rules-engine';
import {
  BusinessRule,
  RuleAction,
  RuleCondition,
  RuleContext,
  RuleExecutionResult,
} from '@dotmac/business-rules-engine/types';
import {
  Plus,
  Play,
  Pause,
  Edit3,
  Trash2,
  Settings,
  Zap,
  AlertTriangle,
  CheckCircle,
  Clock,
  Activity,
  Filter,
  Download,
  Upload,
} from 'lucide-react';

// Rule templates for ISP operations
const RULE_TEMPLATES = {
  service_activation: {
    name: 'Service Activation Rule',
    description: 'Automate service activation based on payment status',
    conditions: [
      { field: 'payment.status', operator: 'equals', value: 'completed' },
      { field: 'service.type', operator: 'in', value: ['internet', 'phone'] },
    ],
    actions: [
      { type: 'activate_service', parameters: { notify_customer: true } },
      { type: 'send_notification', parameters: { template: 'service_activated' } },
    ],
  },
  payment_overdue: {
    name: 'Payment Overdue Escalation',
    description: 'Escalate overdue payments to collections',
    conditions: [
      { field: 'payment.days_overdue', operator: 'greater_than', value: 30 },
      { field: 'account.status', operator: 'equals', value: 'active' },
    ],
    actions: [
      { type: 'suspend_service', parameters: { grace_period: 7 } },
      { type: 'create_task', parameters: { type: 'collections', priority: 'high' } },
    ],
  },
  technical_support: {
    name: 'Technical Support Escalation',
    description: 'Escalate technical tickets based on priority and time',
    conditions: [
      { field: 'ticket.priority', operator: 'equals', value: 'critical' },
      { field: 'ticket.age_hours', operator: 'greater_than', value: 4 },
    ],
    actions: [
      { type: 'escalate', parameters: { level: 'senior_tech', notify: true } },
      { type: 'send_notification', parameters: { recipients: ['tech_manager'] } },
    ],
  },
};

interface AutomationCenterProps {
  tenantId: string;
  onRuleChange?: (rules: BusinessRule[]) => void;
  className?: string;
}

function AutomationCenterImpl({ tenantId, onRuleChange, className = '' }: AutomationCenterProps) {
  useRenderProfiler('AutomationCenter', { tenantId });

  // State
  const [rules, setRules] = useState<BusinessRule[]>([]);
  const [selectedRule, setSelectedRule] = useState<BusinessRule | null>(null);
  const [editingRule, setEditingRule] = useState<BusinessRule | null>(null);
  const [executionResults, setExecutionResults] = useState<RuleExecutionResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [activeTab, setActiveTab] = useState<'rules' | 'execution' | 'analytics'>('rules');
  const [filters, setFilters] = useState({
    status: 'all',
    portal: 'all',
    category: 'all',
  });

  // Rule engine instance
  const ruleEngine = useMemo(
    () =>
      new RuleEngine({
        enableDebug: process.env.NODE_ENV === 'development',
        enableAuditLog: true,
        maxExecutionTime: 10000,
      }),
    []
  );

  // Load rules on mount
  useEffect(() => {
    loadRules();
  }, [tenantId]);

  const loadRules = useCallback(async () => {
    try {
      // In real implementation, this would fetch from API
      const mockRules: BusinessRule[] = [
        {
          id: '1',
          name: 'Auto Service Activation',
          description: 'Automatically activate services when payment is confirmed',
          category: 'service_management',
          status: 'active',
          priority: 100,
          portalScope: ['customer', 'admin'],
          conditionLogic: 'all',
          conditions: [
            {
              id: 'c1',
              field: 'payment.status',
              operator: 'equals',
              value: 'completed',
              description: 'Payment confirmed',
            },
          ],
          actions: [
            {
              id: 'a1',
              type: 'activate_service',
              name: 'Activate Service',
              parameters: { notify_customer: true },
            },
          ],
          createdBy: 'system',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          tenantId,
        },
      ];

      setRules(mockRules);
      onRuleChange?.(mockRules);
    } catch (error) {
      console.error('Failed to load rules:', error);
    }
  }, [tenantId, onRuleChange]);

  // Filtered rules
  const filteredRules = useMemo(() => {
    return rules.filter((rule) => {
      if (filters.status !== 'all' && rule.status !== filters.status) return false;
      if (filters.portal !== 'all' && !rule.portalScope.includes(filters.portal)) return false;
      if (filters.category !== 'all' && rule.category !== filters.category) return false;
      return true;
    });
  }, [rules, filters]);

  // Rule operations
  const createRule = useCallback(
    (template?: keyof typeof RULE_TEMPLATES) => {
      const templateData = template ? RULE_TEMPLATES[template] : null;

      const newRule: BusinessRule = {
        id: `rule_${Date.now()}`,
        name: templateData?.name || 'New Rule',
        description: templateData?.description || '',
        category: 'general',
        status: 'draft',
        priority: 100,
        portalScope: ['admin'],
        conditionLogic: 'all',
        conditions:
          templateData?.conditions?.map((cond, index) => ({
            id: `condition_${index}`,
            ...cond,
          })) || [],
        actions:
          templateData?.actions?.map((action, index) => ({
            id: `action_${index}`,
            name: action.type,
            ...action,
          })) || [],
        createdBy: 'current_user',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        tenantId,
      };

      setEditingRule(newRule);
    },
    [tenantId]
  );

  const saveRule = useCallback(
    async (rule: BusinessRule) => {
      try {
        const isNew = !rules.find((r) => r.id === rule.id);

        if (isNew) {
          setRules((prev) => [...prev, rule]);
        } else {
          setRules((prev) => prev.map((r) => (r.id === rule.id ? rule : r)));
        }

        setEditingRule(null);
        onRuleChange?.(rules);
      } catch (error) {
        console.error('Failed to save rule:', error);
      }
    },
    [rules, onRuleChange]
  );

  const deleteRule = useCallback(
    async (ruleId: string) => {
      if (!confirm('Are you sure you want to delete this rule?')) return;

      try {
        setRules((prev) => prev.filter((r) => r.id !== ruleId));
        if (selectedRule?.id === ruleId) setSelectedRule(null);
      } catch (error) {
        console.error('Failed to delete rule:', error);
      }
    },
    [selectedRule]
  );

  const toggleRule = useCallback(async (ruleId: string) => {
    try {
      setRules((prev) =>
        prev.map((rule) =>
          rule.id === ruleId
            ? { ...rule, status: rule.status === 'active' ? 'inactive' : 'active' }
            : rule
        )
      );
    } catch (error) {
      console.error('Failed to toggle rule:', error);
    }
  }, []);

  // Test rule execution
  const testRules = useCallback(async () => {
    setIsRunning(true);

    try {
      // Mock context for testing
      const testContext: RuleContext = {
        portal: 'admin',
        userId: 'test_user',
        tenantId,
        payment: {
          status: 'completed',
          amount: 99.99,
          days_overdue: 0,
        },
        service: {
          type: 'internet',
          status: 'pending',
        },
        metadata: {},
      };

      const activeRules = rules.filter((r) => r.status === 'active');
      const results = await ruleEngine.executeRules(activeRules, testContext);

      setExecutionResults(results);
      setActiveTab('execution');
    } catch (error) {
      console.error('Rule execution failed:', error);
    } finally {
      setIsRunning(false);
    }
  }, [rules, ruleEngine, tenantId]);

  return (
    <div className={clsx('h-full flex flex-col bg-gray-50', className)}>
      {/* Header */}
      <div className='bg-white border-b px-6 py-4'>
        <div className='flex items-center justify-between'>
          <div>
            <h1 className='text-2xl font-bold text-gray-900'>Automation Center</h1>
            <p className='text-gray-600'>Manage business rules and automation workflows</p>
          </div>

          <div className='flex items-center space-x-3'>
            <Button
              variant='outline'
              onClick={testRules}
              disabled={isRunning || rules.length === 0}
              className='flex items-center space-x-2'
            >
              {isRunning ? (
                <Clock className='h-4 w-4 animate-spin' />
              ) : (
                <Play className='h-4 w-4' />
              )}
              <span>{isRunning ? 'Running...' : 'Test Rules'}</span>
            </Button>

            <PermissionGuard permissions={['automation:create']}>
              <Button onClick={() => createRule()} className='flex items-center space-x-2'>
                <Plus className='h-4 w-4' />
                <span>New Rule</span>
              </Button>
            </PermissionGuard>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className='flex-1 p-6'>
        <Tabs value={activeTab} onValueChange={(value: any) => setActiveTab(value)}>
          <TabsList>
            <TabsTrigger value='rules'>
              <Settings className='h-4 w-4 mr-2' />
              Rules ({filteredRules.length})
            </TabsTrigger>
            <TabsTrigger value='execution'>
              <Activity className='h-4 w-4 mr-2' />
              Execution Log ({executionResults.length})
            </TabsTrigger>
            <TabsTrigger value='analytics'>
              <Zap className='h-4 w-4 mr-2' />
              Analytics
            </TabsTrigger>
          </TabsList>

          <TabsContent value='rules' className='mt-6'>
            <RulesTab
              rules={filteredRules}
              filters={filters}
              onFiltersChange={setFilters}
              onRuleSelect={setSelectedRule}
              onRuleEdit={setEditingRule}
              onRuleDelete={deleteRule}
              onRuleToggle={toggleRule}
              onCreateRule={createRule}
            />
          </TabsContent>

          <TabsContent value='execution' className='mt-6'>
            <ExecutionLogTab results={executionResults} />
          </TabsContent>

          <TabsContent value='analytics' className='mt-6'>
            <AnalyticsTab rules={rules} results={executionResults} />
          </TabsContent>
        </Tabs>
      </div>

      {/* Rule Editor Modal */}
      {editingRule && (
        <RuleEditorModal
          rule={editingRule}
          onSave={saveRule}
          onCancel={() => setEditingRule(null)}
        />
      )}
    </div>
  );
}

// Rules Tab Component
interface RulesTabProps {
  rules: BusinessRule[];
  filters: any;
  onFiltersChange: (filters: any) => void;
  onRuleSelect: (rule: BusinessRule) => void;
  onRuleEdit: (rule: BusinessRule) => void;
  onRuleDelete: (ruleId: string) => void;
  onRuleToggle: (ruleId: string) => void;
  onCreateRule: (template?: keyof typeof RULE_TEMPLATES) => void;
}

function RulesTab({
  rules,
  filters,
  onFiltersChange,
  onRuleSelect,
  onRuleEdit,
  onRuleDelete,
  onRuleToggle,
  onCreateRule,
}: RulesTabProps) {
  return (
    <div className='space-y-6'>
      {/* Filters */}
      <Card className='p-4'>
        <div className='flex items-center space-x-4'>
          <div className='flex items-center space-x-2'>
            <Filter className='h-4 w-4 text-gray-500' />
            <span className='text-sm font-medium'>Filters:</span>
          </div>

          <Select
            value={filters.status}
            onValueChange={(value) => onFiltersChange({ ...filters, status: value })}
          >
            <option value='all'>All Status</option>
            <option value='active'>Active</option>
            <option value='inactive'>Inactive</option>
            <option value='draft'>Draft</option>
          </Select>

          <Select
            value={filters.category}
            onValueChange={(value) => onFiltersChange({ ...filters, category: value })}
          >
            <option value='all'>All Categories</option>
            <option value='service_management'>Service Management</option>
            <option value='billing'>Billing</option>
            <option value='support'>Support</option>
            <option value='general'>General</option>
          </Select>
        </div>
      </Card>

      {/* Rule Templates */}
      <Card className='p-4'>
        <h3 className='font-medium mb-3'>Quick Templates</h3>
        <div className='flex flex-wrap gap-2'>
          {Object.entries(RULE_TEMPLATES).map(([key, template]) => (
            <Button
              key={key}
              size='sm'
              variant='outline'
              onClick={() => onCreateRule(key as keyof typeof RULE_TEMPLATES)}
              className='flex items-center space-x-2'
            >
              <Zap className='h-3 w-3' />
              <span>{template.name}</span>
            </Button>
          ))}
        </div>
      </Card>

      {/* Rules Table */}
      <Card>
        <Table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Category</th>
              <th>Conditions</th>
              <th>Actions</th>
              <th>Last Updated</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rules.map((rule) => (
              <tr key={rule.id} className='hover:bg-gray-50'>
                <td>
                  <div>
                    <div className='font-medium'>{rule.name}</div>
                    {rule.description && (
                      <div className='text-sm text-gray-500'>{rule.description}</div>
                    )}
                  </div>
                </td>
                <td>
                  <Badge
                    variant={
                      rule.status === 'active'
                        ? 'default'
                        : rule.status === 'draft'
                          ? 'secondary'
                          : 'destructive'
                    }
                    className='cursor-pointer'
                    onClick={() => onRuleToggle(rule.id)}
                  >
                    {rule.status}
                  </Badge>
                </td>
                <td>
                  <Badge variant='outline'>{rule.category}</Badge>
                </td>
                <td>{rule.conditions.length}</td>
                <td>{rule.actions.length}</td>
                <td>{new Date(rule.updatedAt).toLocaleDateString()}</td>
                <td>
                  <div className='flex items-center space-x-1'>
                    <Button size='sm' variant='ghost' onClick={() => onRuleEdit(rule)}>
                      <Edit3 className='h-4 w-4' />
                    </Button>
                    <Button
                      size='sm'
                      variant='ghost'
                      onClick={() => onRuleDelete(rule.id)}
                      className='text-red-600'
                    >
                      <Trash2 className='h-4 w-4' />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>

        {rules.length === 0 && (
          <div className='text-center py-8 text-gray-500'>
            <Zap className='h-12 w-12 mx-auto mb-4 text-gray-300' />
            <p>No automation rules configured yet</p>
            <p className='text-sm'>Create your first rule to get started</p>
          </div>
        )}
      </Card>
    </div>
  );
}

// Execution Log Tab
function ExecutionLogTab({ results }: { results: RuleExecutionResult[] }) {
  return (
    <div className='space-y-6'>
      <Card>
        <div className='p-4 border-b'>
          <h3 className='font-medium'>Recent Executions</h3>
        </div>

        <div className='divide-y'>
          {results.map((result, index) => (
            <div key={index} className='p-4'>
              <div className='flex items-center justify-between mb-2'>
                <div className='flex items-center space-x-3'>
                  {result.matched ? (
                    <CheckCircle className='h-5 w-5 text-green-500' />
                  ) : (
                    <AlertTriangle className='h-5 w-5 text-yellow-500' />
                  )}
                  <span className='font-medium'>{result.ruleName}</span>
                </div>

                <div className='flex items-center space-x-2 text-sm text-gray-500'>
                  <Clock className='h-4 w-4' />
                  <span>{result.executionTime}ms</span>
                </div>
              </div>

              <div className='grid grid-cols-2 gap-4 text-sm'>
                <div>
                  <span className='font-medium'>Conditions:</span>{' '}
                  {result.conditionsEvaluated.length}
                  <div className='text-green-600'>
                    ✓ {result.conditionsEvaluated.filter((c) => c.result).length} passed
                  </div>
                </div>
                <div>
                  <span className='font-medium'>Actions:</span> {result.actionsExecuted.length}
                  <div className='text-blue-600'>
                    → {result.actionsExecuted.filter((a) => a.executed).length} executed
                  </div>
                </div>
              </div>

              {result.error && (
                <Alert variant='destructive' className='mt-2'>
                  <AlertTriangle className='h-4 w-4' />
                  <div>Error: {result.error}</div>
                </Alert>
              )}
            </div>
          ))}
        </div>

        {results.length === 0 && (
          <div className='text-center py-8 text-gray-500'>
            <Activity className='h-12 w-12 mx-auto mb-4 text-gray-300' />
            <p>No execution results yet</p>
            <p className='text-sm'>Run some rules to see execution logs</p>
          </div>
        )}
      </Card>
    </div>
  );
}

// Analytics Tab
function AnalyticsTab({
  rules,
  results,
}: {
  rules: BusinessRule[];
  results: RuleExecutionResult[];
}) {
  const analytics = useMemo(() => {
    const totalRules = rules.length;
    const activeRules = rules.filter((r) => r.status === 'active').length;
    const totalExecutions = results.length;
    const successfulExecutions = results.filter((r) => r.matched && !r.error).length;

    return {
      totalRules,
      activeRules,
      totalExecutions,
      successfulExecutions,
      successRate: totalExecutions > 0 ? (successfulExecutions / totalExecutions) * 100 : 0,
    };
  }, [rules, results]);

  return (
    <div className='space-y-6'>
      <div className='grid grid-cols-1 md:grid-cols-5 gap-4'>
        <Card className='p-4'>
          <div className='text-2xl font-bold text-blue-600'>{analytics.totalRules}</div>
          <div className='text-sm text-gray-600'>Total Rules</div>
        </Card>

        <Card className='p-4'>
          <div className='text-2xl font-bold text-green-600'>{analytics.activeRules}</div>
          <div className='text-sm text-gray-600'>Active Rules</div>
        </Card>

        <Card className='p-4'>
          <div className='text-2xl font-bold text-purple-600'>{analytics.totalExecutions}</div>
          <div className='text-sm text-gray-600'>Executions</div>
        </Card>

        <Card className='p-4'>
          <div className='text-2xl font-bold text-orange-600'>{analytics.successfulExecutions}</div>
          <div className='text-sm text-gray-600'>Successful</div>
        </Card>

        <Card className='p-4'>
          <div className='text-2xl font-bold text-indigo-600'>
            {analytics.successRate.toFixed(1)}%
          </div>
          <div className='text-sm text-gray-600'>Success Rate</div>
        </Card>
      </div>
    </div>
  );
}

// Rule Editor Modal (simplified for brevity)
function RuleEditorModal({
  rule,
  onSave,
  onCancel,
}: {
  rule: BusinessRule;
  onSave: (rule: BusinessRule) => void;
  onCancel: () => void;
}) {
  const [editedRule, setEditedRule] = useState(rule);

  return (
    <Modal isOpen onClose={onCancel} size='large'>
      <div className='p-6'>
        <h2 className='text-xl font-bold mb-4'>Edit Rule</h2>

        <div className='space-y-4'>
          <div>
            <label className='block text-sm font-medium mb-2'>Rule Name</label>
            <Input
              value={editedRule.name}
              onChange={(e) => setEditedRule((prev) => ({ ...prev, name: e.target.value }))}
            />
          </div>

          <div>
            <label className='block text-sm font-medium mb-2'>Description</label>
            <Textarea
              value={editedRule.description}
              onChange={(e) => setEditedRule((prev) => ({ ...prev, description: e.target.value }))}
              rows={3}
            />
          </div>

          <div className='flex justify-end space-x-3'>
            <Button variant='outline' onClick={onCancel}>
              Cancel
            </Button>
            <Button onClick={() => onSave(editedRule)}>Save Rule</Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}

export const AutomationCenter = standard_exception_handler(
  withComponentRegistration(AutomationCenterImpl, {
    name: 'AutomationCenter',
    category: 'workflow',
    portal: 'shared',
    version: '1.0.0',
    description: 'Centralized automation and business rules management',
  })
);

export default AutomationCenter;
