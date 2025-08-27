/**
 * Reusable Diagnostic Progress component for troubleshooting workflows
 */
import { CheckCircle, Clock, AlertCircle, Loader } from 'lucide-react';
import React from 'react';

export interface DiagnosticStep {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  duration?: number;
  result?: string;
  action?: string;
}

export interface DiagnosticProgressProps {
  steps: DiagnosticStep[];
  currentStepId?: string;
  onStepAction?: (stepId: string, action: string) => void;
  className?: string;
}

const statusConfig = {
  pending: {
    icon: Clock,
    iconColor: 'text-gray-400',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-200'
  },
  running: {
    icon: Loader,
    iconColor: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200'
  },
  completed: {
    icon: CheckCircle,
    iconColor: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200'
  },
  failed: {
    icon: AlertCircle,
    iconColor: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200'
  }
};

export function DiagnosticProgress({
  steps,
  currentStepId,
  onStepAction,
  className = ''
}: DiagnosticProgressProps) {
  return (
    <div className={`space-y-4 ${className}`}>
      {steps.map((step, index) => {
        const config = statusConfig[step.status];
        const Icon = config.icon;
        const isActive = currentStepId === step.id;
        
        return (
          <div
            key={step.id}
            className={`p-4 rounded-lg border ${config.bgColor} ${config.borderColor} ${
              isActive ? 'ring-2 ring-blue-500 ring-opacity-50' : ''
            }`}
          >
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <Icon 
                  className={`h-5 w-5 ${config.iconColor} ${
                    step.status === 'running' ? 'animate-spin' : ''
                  }`} 
                />
              </div>
              
              <div className="ml-4 flex-1">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium text-gray-900">
                    {step.title}
                  </h4>
                  {step.duration && (
                    <span className="text-sm text-gray-500">
                      ~{step.duration}s
                    </span>
                  )}
                </div>
                
                <p className="text-sm text-gray-600 mt-1">
                  {step.description}
                </p>
                
                {step.result && (
                  <div className="mt-2 p-3 bg-white rounded-md border">
                    <p className="text-sm text-gray-700">
                      <strong>Result:</strong> {step.result}
                    </p>
                  </div>
                )}
                
                {step.action && onStepAction && (
                  <button
                    onClick={() => onStepAction(step.id, step.action!)}
                    className="mt-3 text-sm font-medium text-blue-600 hover:text-blue-500"
                  >
                    {step.action}
                  </button>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function DiagnosticSummary({
  steps,
  onRetry,
  onContactSupport,
  className = ''
}: {
  steps: DiagnosticStep[];
  onRetry?: () => void;
  onContactSupport?: () => void;
  className?: string;
}) {
  const completed = steps.filter(s => s.status === 'completed').length;
  const failed = steps.filter(s => s.status === 'failed').length;
  const total = steps.length;
  
  const hasFailures = failed > 0;
  const allCompleted = completed === total;
  
  return (
    <div className={`p-6 rounded-lg border ${
      hasFailures ? 'bg-red-50 border-red-200' : 
      allCompleted ? 'bg-green-50 border-green-200' : 
      'bg-blue-50 border-blue-200'
    } ${className}`}>
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-gray-900">
            Diagnostic Summary
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            {completed} of {total} tests completed
            {failed > 0 && `, ${failed} failed`}
          </p>
        </div>
        
        <div className="flex space-x-3">
          {hasFailures && onRetry && (
            <button
              onClick={onRetry}
              className="px-4 py-2 text-sm font-medium text-blue-600 bg-white border border-blue-300 rounded-md hover:bg-blue-50"
            >
              Retry Failed Tests
            </button>
          )}
          
          {hasFailures && onContactSupport && (
            <button
              onClick={onContactSupport}
              className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700"
            >
              Contact Support
            </button>
          )}
        </div>
      </div>
    </div>
  );
}