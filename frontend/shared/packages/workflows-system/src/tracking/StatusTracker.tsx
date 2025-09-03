'use client';

import React, { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import type { WorkflowInstance, WorkflowStep } from '../types';

interface StatusTrackerProps {
  instance: WorkflowInstance;
  className?: string;
  variant?: 'default' | 'compact' | 'detailed';
  showTimeline?: boolean;
  showMetrics?: boolean;
  showLogs?: boolean;
  onStepClick?: (step: WorkflowStep) => void;
}

export function StatusTracker({
  instance,
  className,
  variant = 'default',
  showTimeline = true,
  showMetrics = true,
  showLogs = false,
  onStepClick,
}: StatusTrackerProps) {
  // Calculate metrics
  const metrics = useMemo(() => {
    const totalSteps = instance.steps.length;
    const completedSteps = instance.completedSteps.length;
    const failedSteps = instance.failedSteps.length;
    const skippedSteps = instance.skippedSteps.length;
    const pendingSteps = totalSteps - completedSteps - failedSteps - skippedSteps;

    const completionRate = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0;
    const failureRate = totalSteps > 0 ? (failedSteps / totalSteps) * 100 : 0;

    const estimatedCompletion = calculateEstimatedCompletion();
    const averageStepTime = calculateAverageStepTime();

    return {
      totalSteps,
      completedSteps,
      failedSteps,
      skippedSteps,
      pendingSteps,
      completionRate,
      failureRate,
      estimatedCompletion,
      averageStepTime,
    };
  }, [instance]);

  function calculateEstimatedCompletion(): Date | null {
    if (instance.status !== 'running') return null;

    const remainingSteps = instance.steps.filter((s) => s.status === 'pending');
    if (remainingSteps.length === 0) return null;

    const totalEstimatedTime = remainingSteps.reduce((total, step) => {
      return total + (step.estimatedDuration || 5); // Default 5 minutes per step
    }, 0);

    return new Date(Date.now() + totalEstimatedTime * 60 * 1000);
  }

  function calculateAverageStepTime(): number {
    const completedWithDuration = instance.steps.filter(
      (s) => s.status === 'completed' && s.actualDuration
    );

    if (completedWithDuration.length === 0) return 0;

    const totalDuration = completedWithDuration.reduce(
      (total, step) => total + (step.actualDuration || 0),
      0
    );

    return Math.round(totalDuration / completedWithDuration.length / 60000); // Convert to minutes
  }

  const getStepStatusColor = (status: WorkflowStep['status']) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-100';
      case 'failed':
        return 'text-red-600 bg-red-100';
      case 'in_progress':
        return 'text-blue-600 bg-blue-100';
      case 'skipped':
        return 'text-gray-600 bg-gray-100';
      case 'cancelled':
        return 'text-orange-600 bg-orange-100';
      default:
        return 'text-yellow-600 bg-yellow-100';
    }
  };

  const getWorkflowStatusColor = (status: WorkflowInstance['status']) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'failed':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'running':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'paused':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'cancelled':
        return 'text-orange-600 bg-orange-50 border-orange-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getStepIcon = (step: WorkflowStep) => {
    switch (step.status) {
      case 'completed':
        return '✓';
      case 'failed':
        return '✕';
      case 'in_progress':
        return '⟳';
      case 'skipped':
        return '→';
      case 'cancelled':
        return '⏹';
      default:
        return '○';
    }
  };

  if (variant === 'compact') {
    return (
      <div className={clsx('status-tracker compact', className)}>
        <div className='workflow-status-compact'>
          <div className={clsx('status-badge', getWorkflowStatusColor(instance.status))}>
            <span className='status-text'>{instance.status}</span>
          </div>
          <div className='progress-info'>
            <span className='progress-percentage'>{Math.round(instance.progress)}%</span>
            <div className='progress-bar-compact'>
              <motion.div
                className='progress-fill'
                initial={{ width: 0 }}
                animate={{ width: `${instance.progress}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
          </div>
          <div className='step-counts'>
            <span className='completed-count'>{metrics.completedSteps}</span>
            <span className='separator'>/</span>
            <span className='total-count'>{metrics.totalSteps}</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={clsx('status-tracker', className, variant)}>
      {/* Workflow Overview */}
      <div className='workflow-overview'>
        <div className='workflow-header'>
          <div className='workflow-title'>
            <h3>{instance.name}</h3>
            <div className={clsx('workflow-status', getWorkflowStatusColor(instance.status))}>
              {instance.status}
            </div>
          </div>

          <div className='workflow-meta'>
            <div className='meta-item'>
              <label>Progress:</label>
              <span>{Math.round(instance.progress)}%</span>
            </div>
            <div className='meta-item'>
              <label>Priority:</label>
              <span className={clsx('priority-badge', `priority-${instance.priority}`)}>
                {instance.priority}
              </span>
            </div>
            {instance.startTime && (
              <div className='meta-item'>
                <label>Started:</label>
                <span>{new Date(instance.startTime).toLocaleString()}</span>
              </div>
            )}
            {metrics.estimatedCompletion && (
              <div className='meta-item'>
                <label>ETA:</label>
                <span>{metrics.estimatedCompletion.toLocaleString()}</span>
              </div>
            )}
          </div>
        </div>

        {/* Progress Bar */}
        <div className='progress-section'>
          <div className='progress-bar'>
            <motion.div
              className='progress-fill'
              initial={{ width: 0 }}
              animate={{ width: `${instance.progress}%` }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
            />
            <div className='progress-text'>{Math.round(instance.progress)}% Complete</div>
          </div>
        </div>
      </div>

      {/* Metrics */}
      {showMetrics && (
        <div className='metrics-section'>
          <div className='metrics-grid'>
            <div className='metric-card'>
              <div className='metric-value'>{metrics.completedSteps}</div>
              <div className='metric-label'>Completed</div>
              <div className='metric-bar'>
                <div
                  className='metric-bar-fill completed'
                  style={{ width: `${metrics.completionRate}%` }}
                />
              </div>
            </div>

            <div className='metric-card'>
              <div className='metric-value'>{metrics.pendingSteps}</div>
              <div className='metric-label'>Pending</div>
              <div className='metric-bar'>
                <div
                  className='metric-bar-fill pending'
                  style={{ width: `${(metrics.pendingSteps / metrics.totalSteps) * 100}%` }}
                />
              </div>
            </div>

            <div className='metric-card'>
              <div className='metric-value'>{metrics.failedSteps}</div>
              <div className='metric-label'>Failed</div>
              <div className='metric-bar'>
                <div
                  className='metric-bar-fill failed'
                  style={{ width: `${metrics.failureRate}%` }}
                />
              </div>
            </div>

            <div className='metric-card'>
              <div className='metric-value'>{metrics.skippedSteps}</div>
              <div className='metric-label'>Skipped</div>
              <div className='metric-bar'>
                <div
                  className='metric-bar-fill skipped'
                  style={{ width: `${(metrics.skippedSteps / metrics.totalSteps) * 100}%` }}
                />
              </div>
            </div>
          </div>

          {metrics.averageStepTime > 0 && (
            <div className='additional-metrics'>
              <div className='avg-time-metric'>
                <label>Average Step Time:</label>
                <span>{metrics.averageStepTime} minutes</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Timeline */}
      {showTimeline && (
        <div className='timeline-section'>
          <h4>Step Timeline</h4>
          <div className='timeline'>
            <AnimatePresence>
              {instance.steps.map((step, index) => (
                <motion.div
                  key={step.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ delay: index * 0.1 }}
                  className={clsx('timeline-item', {
                    clickable: onStepClick,
                    current: step.status === 'in_progress',
                  })}
                  onClick={() => onStepClick && onStepClick(step)}
                >
                  <div className='timeline-marker'>
                    <div className={clsx('timeline-icon', getStepStatusColor(step.status))}>
                      {getStepIcon(step)}
                    </div>
                    {index < instance.steps.length - 1 && (
                      <div
                        className={clsx('timeline-connector', {
                          completed:
                            instance.completedSteps.includes(step.id) ||
                            instance.skippedSteps.includes(step.id),
                        })}
                      />
                    )}
                  </div>

                  <div className='timeline-content'>
                    <div className='step-header'>
                      <div className='step-name'>{step.name}</div>
                      <div className={clsx('step-status', getStepStatusColor(step.status))}>
                        {step.status}
                      </div>
                    </div>

                    {variant === 'detailed' && (
                      <div className='step-details'>
                        {step.description && (
                          <div className='step-description'>{step.description}</div>
                        )}

                        <div className='step-meta'>
                          <div className='meta-row'>
                            <span className='meta-label'>Type:</span>
                            <span className='meta-value'>{step.type}</span>
                          </div>

                          {step.assignedTo && (
                            <div className='meta-row'>
                              <span className='meta-label'>Assigned to:</span>
                              <span className='meta-value'>{step.assignedTo}</span>
                            </div>
                          )}

                          {step.startTime && (
                            <div className='meta-row'>
                              <span className='meta-label'>Started:</span>
                              <span className='meta-value'>
                                {new Date(step.startTime).toLocaleString()}
                              </span>
                            </div>
                          )}

                          {step.endTime && (
                            <div className='meta-row'>
                              <span className='meta-label'>Completed:</span>
                              <span className='meta-value'>
                                {new Date(step.endTime).toLocaleString()}
                              </span>
                            </div>
                          )}

                          {step.actualDuration && (
                            <div className='meta-row'>
                              <span className='meta-label'>Duration:</span>
                              <span className='meta-value'>
                                {Math.round(step.actualDuration / 60000)} minutes
                              </span>
                            </div>
                          )}
                        </div>

                        {step.error && (
                          <div className='step-error'>
                            <strong>Error:</strong> {step.error}
                          </div>
                        )}

                        {step.output && Object.keys(step.output).length > 0 && (
                          <div className='step-output'>
                            <strong>Output:</strong>
                            <details>
                              <summary>View output data</summary>
                              <pre>{JSON.stringify(step.output, null, 2)}</pre>
                            </details>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Basic timing info for non-detailed view */}
                    {variant !== 'detailed' && (step.startTime || step.actualDuration) && (
                      <div className='step-timing'>
                        {step.actualDuration && (
                          <span className='duration'>
                            {Math.round(step.actualDuration / 60000)}min
                          </span>
                        )}
                        {step.startTime && (
                          <span className='timestamp'>
                            {new Date(step.startTime).toLocaleTimeString()}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>
      )}

      {/* Logs */}
      {showLogs && instance.logs.length > 0 && (
        <div className='logs-section'>
          <h4>Activity Log</h4>
          <div className='logs-container'>
            <AnimatePresence>
              {instance.logs
                .slice()
                .reverse()
                .slice(0, 10) // Show last 10 logs
                .map((log, index) => (
                  <motion.div
                    key={`${log.timestamp}-${index}`}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className={clsx('log-entry', `log-${log.level}`)}
                  >
                    <div className='log-timestamp'>{new Date(log.timestamp).toLocaleString()}</div>
                    <div className='log-message'>{log.message}</div>
                    {log.stepId && (
                      <div className='log-step'>
                        Step: {instance.steps.find((s) => s.id === log.stepId)?.name || log.stepId}
                      </div>
                    )}
                    {log.userId && <div className='log-user'>By: {log.userId}</div>}
                  </motion.div>
                ))}
            </AnimatePresence>
          </div>
        </div>
      )}
    </div>
  );
}

export default StatusTracker;
