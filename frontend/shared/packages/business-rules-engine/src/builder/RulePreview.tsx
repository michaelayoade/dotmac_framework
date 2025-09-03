'use client';

import { AlertCircle, CheckCircle, Clock, Tag } from 'lucide-react';
import type React from 'react';
import type { BusinessRule } from '../types';

interface RulePreviewProps {
  rule: BusinessRule;
}

// Simple Card component
const Card = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <div className={`border border-gray-200 rounded-lg ${className}`}>{children}</div>
);

export function RulePreview({ rule }: RulePreviewProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'text-green-600 bg-green-100';
      case 'inactive':
        return 'text-red-600 bg-red-100';
      case 'draft':
        return 'text-yellow-600 bg-yellow-100';
      case 'archived':
        return 'text-gray-600 bg-gray-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getPriorityLabel = (priority: number) => {
    if (priority >= 900) return 'Critical';
    if (priority >= 700) return 'High';
    if (priority >= 400) return 'Medium';
    return 'Low';
  };

  const formatConditionLogic = (logic: string) => {
    switch (logic) {
      case 'all':
        return 'ALL conditions must be true (AND)';
      case 'any':
        return 'ANY condition can be true (OR)';
      case 'custom':
        return 'Custom logic expression';
      default:
        return logic;
    }
  };

  return (
    <Card className='p-6'>
      <div className='space-y-6'>
        {/* Header */}
        <div>
          <div className='flex items-center justify-between mb-2'>
            <h3 className='text-lg font-semibold text-gray-900'>{rule.name}</h3>
            <span
              className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(rule.status)}`}
            >
              {rule.status.charAt(0).toUpperCase() + rule.status.slice(1)}
            </span>
          </div>
          {rule.description && <p className='text-sm text-gray-600'>{rule.description}</p>}
        </div>

        {/* Metadata */}
        <div className='grid grid-cols-2 gap-4 text-sm'>
          <div className='flex items-center text-gray-600'>
            <Tag className='h-4 w-4 mr-2' />
            <span>Category: {rule.category}</span>
          </div>
          <div className='flex items-center text-gray-600'>
            <Clock className='h-4 w-4 mr-2' />
            <span>Priority: {getPriorityLabel(rule.priority)}</span>
          </div>
        </div>

        {/* Conditions */}
        <div>
          <div className='flex items-center mb-3'>
            <AlertCircle className='h-4 w-4 mr-2 text-orange-600' />
            <h4 className='text-sm font-medium text-gray-900'>
              Conditions ({formatConditionLogic(rule.conditionLogic)})
            </h4>
          </div>
          <div className='space-y-2'>
            {rule.conditions.map((condition, index) => (
              <div
                key={condition.id}
                className='p-3 bg-orange-50 rounded-lg border border-orange-200'
              >
                <div className='text-sm text-orange-700'>
                  <span className='font-medium'>{index + 1}.</span> If{' '}
                  <strong>{condition.field}</strong> <strong>{condition.operator}</strong>{' '}
                  {condition.value !== undefined && <strong>{condition.value.toString()}</strong>}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div>
          <div className='flex items-center mb-3'>
            <CheckCircle className='h-4 w-4 mr-2 text-green-600' />
            <h4 className='text-sm font-medium text-gray-900'>Actions</h4>
          </div>
          <div className='space-y-2'>
            {rule.actions.map((action, index) => (
              <div key={action.id} className='p-3 bg-green-50 rounded-lg border border-green-200'>
                <div className='text-sm text-green-700'>
                  <span className='font-medium'>{index + 1}.</span>{' '}
                  <strong>{action.type.replace('_', ' ')}</strong>
                  {action.target && action.value && (
                    <span>
                      {' '}
                      "{action.target}" to "{action.value}"
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Rule Logic Summary */}
        <div className='border-t pt-4'>
          <h4 className='text-sm font-medium text-gray-900 mb-2'>Rule Logic Summary</h4>
          <div className='text-sm text-gray-700 space-y-1'>
            <div>
              <strong>When:</strong> {formatConditionLogic(rule.conditionLogic)} of the{' '}
              {rule.conditions.length} condition
              {rule.conditions.length !== 1 ? 's' : ''}
            </div>
            <div>
              <strong>Then:</strong> Execute {rule.actions.length} action
              {rule.actions.length !== 1 ? 's' : ''} in sequence
            </div>
            <div>
              <strong>Priority:</strong> {rule.priority} ({getPriorityLabel(rule.priority)})
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
