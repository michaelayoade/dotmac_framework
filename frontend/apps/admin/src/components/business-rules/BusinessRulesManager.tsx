'use client';

import React, { useState, useEffect } from 'react';
import {
  RuleManager,
  BusinessRule,
  RuleBuilder,
  ISPRuleTemplates,
  instantiateRuleTemplate,
  getRuleTemplatesByCategory,
  RuleExecutionResult
} from '@dotmac/business-rules-engine';
import { Button } from '@dotmac/primitives';
import { Card } from '@dotmac/primitives';
import { Plus, Play, Settings, Template, FileText, BarChart3 } from 'lucide-react';

export function BusinessRulesManager() {
  const [ruleManager] = useState(() => new RuleManager());
  const [rules, setRules] = useState<BusinessRule[]>([]);
  const [selectedRule, setSelectedRule] = useState<BusinessRule | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [activeView, setActiveView] = useState<'rules' | 'templates' | 'testing' | 'analytics'>('rules');
  const [executionResults, setExecutionResults] = useState<RuleExecutionResult[]>([]);

  useEffect(() => {
    // Load initial rules
    setRules(ruleManager.getAllRules());
  }, [ruleManager]);

  const handleSaveRule = (rule: BusinessRule) => {
    ruleManager.addRule(rule);
    setRules(ruleManager.getAllRules());
    setIsCreating(false);
    setSelectedRule(null);
  };

  const handleUpdateRule = (ruleId: string, updates: Partial<BusinessRule>) => {
    ruleManager.updateRule(ruleId, updates);
    setRules(ruleManager.getAllRules());
    setSelectedRule(null);
  };

  const handleDeleteRule = (ruleId: string) => {
    ruleManager.removeRule(ruleId);
    setRules(ruleManager.getAllRules());
  };

  const handleTestRules = async () => {
    // Mock context for testing
    const testContext = {
      customer: {
        id: 'test-customer-123',
        type: 'business' as const,
        status: 'active' as const,
        creditScore: 750,
        monthsActive: 18,
        monthlyRevenue: 250,
        contracts: 1,
      },
      service: {
        type: 'internet' as const,
        subType: 'fiber' as const,
        bandwidth: 1000,
        status: 'active' as const,
        monthlyRate: 150,
        lastUsage: 85,
        usageLimit: 1000,
      },
      billing: {
        currentBalance: 150,
        pastDueAmount: 0,
        daysPastDue: 0,
        paymentMethod: 'credit_card' as const,
        autoPayEnabled: true,
        billingCycle: 'monthly' as const,
      },
      portal: 'admin' as const,
      timestamp: new Date(),
    };

    const results = await ruleManager.executeRules(testContext);
    setExecutionResults(results);
  };

  const handleInstantiateTemplate = (templateId: string, variables: Record<string, any>) => {
    const rule = instantiateRuleTemplate(templateId, variables, {
      createdBy: 'admin-user', // In real app, get from auth context
      updatedBy: 'admin-user',
    });
    ruleManager.addRule(rule);
    setRules(ruleManager.getAllRules());
  };

  const renderRulesView = () => (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Business Rules</h2>
          <p className="text-gray-600">Manage automated business logic and decision-making rules</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={handleTestRules}
            className="flex items-center gap-2"
          >
            <Play className="h-4 w-4" />
            Test All Rules
          </Button>
          <Button
            onClick={() => setIsCreating(true)}
            className="flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Create Rule
          </Button>
        </div>
      </div>

      {isCreating && (
        <Card className="p-6">
          <RuleBuilder
            onSave={handleSaveRule}
            onCancel={() => setIsCreating(false)}
          />
        </Card>
      )}

      {selectedRule && (
        <Card className="p-6">
          <RuleBuilder
            rule={selectedRule}
            isEditing
            onSave={(rule) => handleUpdateRule(rule.id, rule)}
            onCancel={() => setSelectedRule(null)}
          />
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4">
        {rules.map((rule) => (
          <Card key={rule.id} className="p-6">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-lg font-semibold text-gray-900">{rule.name}</h3>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    rule.status === 'active' ? 'bg-green-100 text-green-800' :
                    rule.status === 'inactive' ? 'bg-red-100 text-red-800' :
                    rule.status === 'draft' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {rule.status.charAt(0).toUpperCase() + rule.status.slice(1)}
                  </span>
                  <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs">
                    {rule.category}
                  </span>
                </div>
                <p className="text-gray-600 mb-3">{rule.description}</p>
                <div className="flex items-center gap-4 text-sm text-gray-500">
                  <span>{rule.conditions.length} condition{rule.conditions.length !== 1 ? 's' : ''}</span>
                  <span>{rule.actions.length} action{rule.actions.length !== 1 ? 's' : ''}</span>
                  <span>Priority: {rule.priority}</span>
                  {rule.portalScope.length > 0 && (
                    <span>Scope: {rule.portalScope.join(', ')}</span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 ml-4">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedRule(rule)}
                >
                  Edit
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    if (confirm('Are you sure you want to delete this rule?')) {
                      handleDeleteRule(rule.id);
                    }
                  }}
                  className="text-red-600 hover:text-red-800"
                >
                  Delete
                </Button>
              </div>
            </div>
          </Card>
        ))}

        {rules.length === 0 && (
          <Card className="p-12 text-center">
            <Settings className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Business Rules</h3>
            <p className="text-gray-600 mb-4">
              Create your first business rule to automate decision-making processes.
            </p>
            <Button onClick={() => setIsCreating(true)}>
              Create First Rule
            </Button>
          </Card>
        )}
      </div>
    </div>
  );

  const renderTemplatesView = () => (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Rule Templates</h2>
        <p className="text-gray-600">Pre-built templates for common ISP business scenarios</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {ISPRuleTemplates.map((template) => (
          <Card key={template.id} className="p-6">
            <div className="flex items-start justify-between mb-3">
              <Template className="h-8 w-8 text-blue-600" />
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs">
                {template.category}
              </span>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">{template.name}</h3>
            <p className="text-gray-600 text-sm mb-4">{template.description}</p>
            <div className="text-xs text-gray-500 mb-4">
              Variables: {Object.keys(template.variables).join(', ')}
            </div>
            <Button
              size="sm"
              onClick={() => {
                // For demo, use default values
                const variables = Object.entries(template.variables).reduce(
                  (acc, [key, config]) => ({
                    ...acc,
                    [key]: config.defaultValue,
                  }),
                  {}
                );
                handleInstantiateTemplate(template.id, variables);
              }}
              className="w-full"
            >
              Use Template
            </Button>
          </Card>
        ))}
      </div>
    </div>
  );

  const renderTestingView = () => (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Rule Testing</h2>
        <p className="text-gray-600">Test business rules with sample data</p>
      </div>

      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Execution Results</h3>
          <Button onClick={handleTestRules} className="flex items-center gap-2">
            <Play className="h-4 w-4" />
            Run Tests
          </Button>
        </div>

        {executionResults.length === 0 ? (
          <p className="text-gray-500 text-center py-8">
            No test results yet. Click "Run Tests" to execute all active rules.
          </p>
        ) : (
          <div className="space-y-4">
            {executionResults.map((result, index) => (
              <div key={index} className={`p-4 rounded-lg border ${
                result.matched ? 'bg-green-50 border-green-200' : 'bg-gray-50 border-gray-200'
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium">{result.ruleName}</h4>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      result.matched ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {result.matched ? 'Matched' : 'No Match'}
                    </span>
                    <span className="text-xs text-gray-500">{result.executionTime}ms</span>
                  </div>
                </div>

                {result.error && (
                  <p className="text-red-600 text-sm mb-2">Error: {result.error}</p>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <h5 className="font-medium text-gray-700 mb-1">Conditions</h5>
                    <ul className="space-y-1">
                      {result.conditionsEvaluated.map((condition, idx) => (
                        <li key={idx} className={`flex items-center gap-2 ${
                          condition.result ? 'text-green-600' : 'text-red-600'
                        }`}>
                          <span>{condition.result ? '✓' : '✗'}</span>
                          <span className="text-xs">
                            {condition.field} {condition.operator} {condition.expectedValue}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {result.matched && result.actionsExecuted.length > 0 && (
                    <div>
                      <h5 className="font-medium text-gray-700 mb-1">Actions</h5>
                      <ul className="space-y-1">
                        {result.actionsExecuted.map((action, idx) => (
                          <li key={idx} className={`flex items-center gap-2 ${
                            action.executed ? 'text-green-600' : 'text-red-600'
                          }`}>
                            <span>{action.executed ? '✓' : '✗'}</span>
                            <span className="text-xs">{action.type}</span>
                            {action.error && (
                              <span className="text-red-500 text-xs">({action.error})</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );

  const renderAnalyticsView = () => {
    const stats = ruleManager.getRuleStatistics();

    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Rule Analytics</h2>
          <p className="text-gray-600">Overview of business rules usage and performance</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="p-6">
            <div className="flex items-center">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">Total Rules</p>
                <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
              </div>
              <FileText className="h-8 w-8 text-blue-600" />
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">Active Rules</p>
                <p className="text-2xl font-bold text-green-600">{stats.active}</p>
              </div>
              <Settings className="h-8 w-8 text-green-600" />
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">Draft Rules</p>
                <p className="text-2xl font-bold text-yellow-600">{stats.draft}</p>
              </div>
              <Template className="h-8 w-8 text-yellow-600" />
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">Categories</p>
                <p className="text-2xl font-bold text-gray-900">{Object.keys(stats.byCategory).length}</p>
              </div>
              <BarChart3 className="h-8 w-8 text-purple-600" />
            </div>
          </Card>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Rules by Category</h3>
            <div className="space-y-2">
              {Object.entries(stats.byCategory).map(([category, count]) => (
                <div key={category} className="flex items-center justify-between">
                  <span className="capitalize text-gray-600">{category.replace('_', ' ')}</span>
                  <span className="font-medium">{count}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Portal Distribution</h3>
            <div className="space-y-2">
              {Object.entries(stats.byPortal).map(([portal, count]) => (
                <div key={portal} className="flex items-center justify-between">
                  <span className="capitalize text-gray-600">{portal}</span>
                  <span className="font-medium">{count}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Navigation */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          {[
            { key: 'rules', label: 'Rules', icon: Settings },
            { key: 'templates', label: 'Templates', icon: Template },
            { key: 'testing', label: 'Testing', icon: Play },
            { key: 'analytics', label: 'Analytics', icon: BarChart3 },
          ].map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setActiveView(key as any)}
              className={`flex items-center gap-2 py-2 px-1 border-b-2 font-medium text-sm ${
                activeView === key
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      {activeView === 'rules' && renderRulesView()}
      {activeView === 'templates' && renderTemplatesView()}
      {activeView === 'testing' && renderTestingView()}
      {activeView === 'analytics' && renderAnalyticsView()}
    </div>
  );
}
