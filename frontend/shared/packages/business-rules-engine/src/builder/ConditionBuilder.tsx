'use client';

import type React from 'react';
import type { ConditionOperator, RuleCondition } from '../types';

interface ConditionBuilderProps {
  condition: RuleCondition;
  onChange: (condition: RuleCondition) => void;
}

// Simple Card component
const Card = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <div className={`border border-gray-200 rounded-lg ${className}`}>{children}</div>
);

export function ConditionBuilder({ condition, onChange }: ConditionBuilderProps) {
  const updateCondition = (updates: Partial<RuleCondition>) => {
    onChange({ ...condition, ...updates });
  };

  const operatorOptions: {
    value: ConditionOperator;
    label: string;
    requiresValue: boolean;
  }[] = [
    { value: 'equals', label: 'equals', requiresValue: true },
    { value: 'not_equals', label: 'does not equal', requiresValue: true },
    { value: 'greater_than', label: 'is greater than', requiresValue: true },
    { value: 'less_than', label: 'is less than', requiresValue: true },
    { value: 'contains', label: 'contains', requiresValue: true },
    { value: 'exists', label: 'exists', requiresValue: false },
    { value: 'not_exists', label: 'does not exist', requiresValue: false },
  ];

  const fieldOptions = [
    { value: 'customer.type', label: 'Customer Type' },
    { value: 'customer.status', label: 'Customer Status' },
    { value: 'customer.monthsActive', label: 'Months Active' },
    { value: 'billing.daysPastDue', label: 'Days Past Due' },
    { value: 'service.type', label: 'Service Type' },
  ];

  const selectedOperator = operatorOptions.find((op) => op.value === condition.operator);
  const requiresValue = selectedOperator?.requiresValue ?? true;

  return (
    <Card className='p-4 bg-gray-50'>
      <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
        {/* Field Selection */}
        <div>
          <label className='block text-sm font-medium text-gray-700 mb-1'>Field</label>
          <select
            value={condition.field || ''}
            onChange={(e) => updateCondition({ field: e.target.value, value: '' })}
            className='w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
          >
            <option value=''>Select field...</option>
            {fieldOptions.map((field) => (
              <option key={field.value} value={field.value}>
                {field.label}
              </option>
            ))}
          </select>
        </div>

        {/* Operator Selection */}
        <div>
          <label className='block text-sm font-medium text-gray-700 mb-1'>Operator</label>
          <select
            value={condition.operator}
            onChange={(e) =>
              updateCondition({
                operator: e.target.value as ConditionOperator,
                value: operatorOptions.find((op) => op.value === e.target.value)?.requiresValue
                  ? condition.value
                  : undefined,
              })
            }
            className='w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
          >
            {operatorOptions.map((op) => (
              <option key={op.value} value={op.value}>
                {op.label}
              </option>
            ))}
          </select>
        </div>

        {/* Value Input */}
        {requiresValue && (
          <div>
            <label className='block text-sm font-medium text-gray-700 mb-1'>Value</label>
            <input
              type='text'
              value={condition.value || ''}
              onChange={(e) => updateCondition({ value: e.target.value })}
              className='w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
              placeholder='Enter value'
            />
          </div>
        )}
      </div>

      {/* Condition Summary */}
      {condition.field && (
        <div className='mt-3 p-2 bg-white rounded border'>
          <span className='text-sm text-gray-600'>
            If{' '}
            <strong>
              {fieldOptions.find((f) => f.value === condition.field)?.label || condition.field}
            </strong>{' '}
            <strong>{selectedOperator?.label}</strong>{' '}
            {requiresValue && condition.value !== undefined && condition.value !== '' && (
              <strong>{condition.value.toString()}</strong>
            )}
          </span>
        </div>
      )}
    </Card>
  );
}
