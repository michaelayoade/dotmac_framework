'use client';

import type React from 'react';
import type { ActionType, RuleAction } from '../types';

interface ActionBuilderProps {
  action: RuleAction;
  onChange: (action: RuleAction) => void;
}

// Simple Card component
const Card = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <div className={`border border-gray-200 rounded-lg ${className}`}>{children}</div>
);

export function ActionBuilder({ action, onChange }: ActionBuilderProps) {
  const updateAction = (updates: Partial<RuleAction>) => {
    onChange({ ...action, ...updates });
  };

  const actionTypeOptions: {
    value: ActionType;
    label: string;
    description: string;
  }[] = [
    {
      value: 'set_value',
      label: 'Set Value',
      description: 'Set a field to a specific value',
    },
    {
      value: 'send_notification',
      label: 'Send Notification',
      description: 'Send email, SMS, or in-app notification',
    },
    {
      value: 'create_task',
      label: 'Create Task',
      description: 'Create a task for staff to complete',
    },
    {
      value: 'update_status',
      label: 'Update Status',
      description: 'Change the status of a record',
    },
    {
      value: 'apply_discount',
      label: 'Apply Discount',
      description: 'Apply a discount to billing',
    },
    {
      value: 'suspend_service',
      label: 'Suspend Service',
      description: 'Suspend customer service',
    },
    {
      value: 'approve_request',
      label: 'Approve Request',
      description: 'Automatically approve a request',
    },
    {
      value: 'reject_request',
      label: 'Reject Request',
      description: 'Automatically reject a request',
    },
    {
      value: 'escalate',
      label: 'Escalate',
      description: 'Escalate issue to higher level',
    },
    {
      value: 'log_event',
      label: 'Log Event',
      description: 'Create an audit log entry',
    },
    {
      value: 'trigger_workflow',
      label: 'Trigger Workflow',
      description: 'Start another business process',
    },
    {
      value: 'execute_webhook',
      label: 'Execute Webhook',
      description: 'Call external API endpoint',
    },
  ];

  const renderActionConfiguration = () => {
    switch (action.type) {
      case 'set_value':
        return (
          <div className='grid grid-cols-2 gap-4'>
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>Target Field</label>
              <input
                type='text'
                value={action.target || ''}
                onChange={(e) => updateAction({ target: e.target.value })}
                className='w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
                placeholder='e.g., customer.tier'
              />
            </div>
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>Value</label>
              <input
                type='text'
                value={action.value || ''}
                onChange={(e) => updateAction({ value: e.target.value })}
                className='w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
                placeholder='New value'
              />
            </div>
          </div>
        );

      case 'send_notification':
        return (
          <div className='space-y-4'>
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>
                Notification Type
              </label>
              <select
                value={(action.parameters || {}).type || ''}
                onChange={(e) =>
                  updateAction({
                    parameters: {
                      ...(action.parameters || {}),
                      type: e.target.value,
                    },
                  })
                }
                className='w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
              >
                <option value=''>Select type...</option>
                <option value='email'>Email</option>
                <option value='sms'>SMS</option>
                <option value='in_app'>In-App Notification</option>
                <option value='webhook'>Webhook</option>
              </select>
            </div>
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>
                Message Template
              </label>
              <textarea
                value={(action.parameters || {}).message || ''}
                onChange={(e) =>
                  updateAction({
                    parameters: {
                      ...(action.parameters || {}),
                      message: e.target.value,
                    },
                  })
                }
                className='w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
                rows={3}
                placeholder='Your service will be suspended due to {{billing.daysPastDue}} days overdue payment.'
              />
            </div>
          </div>
        );

      case 'apply_discount':
        return (
          <div className='grid grid-cols-2 gap-4'>
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>Discount Type</label>
              <select
                value={(action.parameters || {}).discountType || 'percentage'}
                onChange={(e) =>
                  updateAction({
                    parameters: {
                      ...(action.parameters || {}),
                      discountType: e.target.value,
                    },
                  })
                }
                className='w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
              >
                <option value='percentage'>Percentage</option>
                <option value='fixed'>Fixed Amount</option>
              </select>
            </div>
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>
                {(action.parameters || {}).discountType === 'fixed'
                  ? 'Amount ($)'
                  : 'Percentage (%)'}
              </label>
              <input
                type='number'
                value={action.value || ''}
                onChange={(e) => updateAction({ value: parseFloat(e.target.value) })}
                className='w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
                placeholder={(action.parameters || {}).discountType === 'fixed' ? '25.00' : '15'}
                min='0'
                step={(action.parameters || {}).discountType === 'fixed' ? '0.01' : '1'}
              />
            </div>
          </div>
        );

      case 'log_event':
        return (
          <div className='space-y-4'>
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>Event Type</label>
              <select
                value={(action.parameters || {}).eventType || ''}
                onChange={(e) =>
                  updateAction({
                    parameters: {
                      ...(action.parameters || {}),
                      eventType: e.target.value,
                    },
                  })
                }
                className='w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
              >
                <option value=''>Select type...</option>
                <option value='rule_triggered'>Rule Triggered</option>
                <option value='status_change'>Status Change</option>
                <option value='payment_event'>Payment Event</option>
                <option value='service_event'>Service Event</option>
                <option value='security_event'>Security Event</option>
              </select>
            </div>
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>Log Message</label>
              <textarea
                value={(action.parameters || {}).message || ''}
                onChange={(e) =>
                  updateAction({
                    parameters: {
                      ...(action.parameters || {}),
                      message: e.target.value,
                    },
                  })
                }
                className='w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
                rows={2}
                placeholder='Business rule applied discount for customer {{customer.id}}'
              />
            </div>
          </div>
        );

      default:
        return (
          <div>
            <label className='block text-sm font-medium text-gray-700 mb-1'>
              Additional Parameters
            </label>
            <textarea
              value={JSON.stringify(action.parameters || {}, null, 2)}
              onChange={(e) => {
                try {
                  updateAction({ parameters: JSON.parse(e.target.value) });
                } catch {
                  // Invalid JSON, don't update
                }
              }}
              className='w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
              rows={4}
              placeholder='{}'
            />
          </div>
        );
    }
  };

  return (
    <Card className='p-4 bg-gray-50'>
      <div className='space-y-4'>
        {/* Action Type Selection */}
        <div>
          <label className='block text-sm font-medium text-gray-700 mb-1'>Action Type</label>
          <select
            value={action.type}
            onChange={(e) =>
              updateAction({
                type: e.target.value as ActionType,
                target: '',
                value: undefined,
                parameters: {},
              })
            }
            className='w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
          >
            {actionTypeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <p className='text-sm text-gray-500 mt-1'>
            {actionTypeOptions.find((opt) => opt.value === action.type)?.description}
          </p>
        </div>

        {/* Action Configuration */}
        {renderActionConfiguration()}
      </div>

      {/* Action Summary */}
      <div className='mt-4 p-2 bg-white rounded border'>
        <span className='text-sm text-gray-600'>
          <strong>Then:</strong> {actionTypeOptions.find((opt) => opt.value === action.type)?.label}
          {action.type === 'set_value' &&
            action.target &&
            action.value &&
            ` "${action.target}" to "${action.value}"`}
          {action.type === 'apply_discount' &&
            action.value &&
            ` of ${action.value}${(action.parameters || {}).discountType === 'fixed' ? '$' : '%'}`}
          {action.type === 'send_notification' &&
            (action.parameters || {}).type &&
            ` via ${(action.parameters || {}).type}`}
        </span>
      </div>
    </Card>
  );
}
