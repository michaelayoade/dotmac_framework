/**
 * Reusable Progress Indicator components for various progress states
 */
import React from 'react';

export interface LinearProgressProps {
  value: number;
  max: number;
  label?: string;
  showPercentage?: boolean;
  size?: 'sm' | 'md' | 'lg';
  color?: 'blue' | 'green' | 'yellow' | 'red';
  className?: string;
}

export function LinearProgress({
  value,
  max,
  label,
  showPercentage = true,
  size = 'md',
  color = 'blue',
  className = ''
}: LinearProgressProps) {
  const percentage = Math.min(100, (value / max) * 100);
  
  const sizeClasses = {
    sm: 'h-2',
    md: 'h-3',
    lg: 'h-4'
  };

  const colorClasses = {
    blue: 'bg-blue-600',
    green: 'bg-green-600',
    yellow: 'bg-yellow-600',
    red: 'bg-red-600'
  };

  return (
    <div className={className}>
      {label && (
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-700">{label}</span>
          {showPercentage && (
            <span className="text-sm text-gray-500">{Math.round(percentage)}%</span>
          )}
        </div>
      )}
      <div className={`w-full bg-gray-200 rounded-full overflow-hidden ${sizeClasses[size]}`}>
        <div
          className={`h-full ${colorClasses[color]} transition-all duration-300 ease-out rounded-full`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

export interface CircularProgressProps {
  value: number;
  max: number;
  size?: number;
  strokeWidth?: number;
  color?: 'blue' | 'green' | 'yellow' | 'red';
  showValue?: boolean;
  label?: string;
  className?: string;
}

export function CircularProgress({
  value,
  max,
  size = 120,
  strokeWidth = 8,
  color = 'blue',
  showValue = true,
  label,
  className = ''
}: CircularProgressProps) {
  const percentage = Math.min(100, (value / max) * 100);
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (percentage / 100) * circumference;

  const colorClasses = {
    blue: 'stroke-blue-600',
    green: 'stroke-green-600',
    yellow: 'stroke-yellow-600',
    red: 'stroke-red-600'
  };

  return (
    <div className={`flex flex-col items-center ${className}`}>
      <div className="relative">
        <svg
          className="transform -rotate-90"
          width={size}
          height={size}
        >
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            fill="transparent"
            className="text-gray-200"
          />
          {/* Progress circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className={`${colorClasses[color]} transition-all duration-300 ease-out`}
          />
        </svg>
        
        {/* Center content */}
        {showValue && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">
                {Math.round(percentage)}%
              </div>
              {label && (
                <div className="text-sm text-gray-500">{label}</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export interface StepProgressProps {
  steps: Array<{
    title: string;
    description?: string;
    status: 'pending' | 'current' | 'completed';
  }>;
  className?: string;
}

export function StepProgress({ steps, className = '' }: StepProgressProps) {
  return (
    <nav className={className}>
      <ol className="flex items-center">
        {steps.map((step, stepIndex) => (
          <li key={stepIndex} className={`relative ${stepIndex !== steps.length - 1 ? 'pr-8 sm:pr-20' : ''}`}>
            {/* Connector line */}
            {stepIndex !== steps.length - 1 && (
              <div className="absolute top-4 left-4 -ml-px mt-0.5 h-full w-0.5 bg-gray-300" />
            )}
            
            <div className="group relative flex items-start">
              <span className="flex h-9 items-center">
                <span
                  className={`relative z-10 flex h-8 w-8 items-center justify-center rounded-full border-2 ${
                    step.status === 'completed'
                      ? 'bg-blue-600 border-blue-600'
                      : step.status === 'current'
                      ? 'border-blue-600 bg-white'
                      : 'border-gray-300 bg-white'
                  }`}
                >
                  {step.status === 'completed' ? (
                    <svg className="h-5 w-5 text-white" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    <span
                      className={`h-2.5 w-2.5 rounded-full ${
                        step.status === 'current' ? 'bg-blue-600' : 'bg-gray-300'
                      }`}
                    />
                  )}
                </span>
              </span>
              <span className="ml-4 min-w-0 flex flex-col">
                <span
                  className={`text-sm font-medium ${
                    step.status === 'completed'
                      ? 'text-blue-600'
                      : step.status === 'current'
                      ? 'text-blue-600'
                      : 'text-gray-500'
                  }`}
                >
                  {step.title}
                </span>
                {step.description && (
                  <span className="text-sm text-gray-500">{step.description}</span>
                )}
              </span>
            </div>
          </li>
        ))}
      </ol>
    </nav>
  );
}