'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import type {
  WorkflowStep,
  ApprovalStepConfig,
  WorkflowInstance
} from '../types';

interface ApprovalStepProps {
  step: WorkflowStep & { type: 'approval' };
  instance: WorkflowInstance;
  currentUserId: string;
  currentUserRoles: string[];
  onApprove: (comment?: string) => Promise<void>;
  onReject: (reason: string) => Promise<void>;
  onDelegate: (to: string, comment?: string) => Promise<void>;
  className?: string;
}

interface Approval {
  id: string;
  approver: string;
  approverName?: string;
  status: 'pending' | 'approved' | 'rejected';
  timestamp?: number;
  comment?: string;
  required: boolean;
  order?: number;
}

export function ApprovalStep({
  step,
  instance,
  currentUserId,
  currentUserRoles,
  onApprove,
  onReject,
  onDelegate,
  className
}: ApprovalStepProps) {
  const [comment, setComment] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [showDelegateDialog, setShowDelegateDialog] = useState(false);
  const [delegateTo, setDelegateTo] = useState('');
  const [delegateComment, setDelegateComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Parse approval configuration from step input
  const approvalConfig = useMemo((): ApprovalStepConfig => {
    if (step.input && typeof step.input === 'object' && 'approvers' in step.input) {
      return step.input as ApprovalStepConfig;
    }

    // Default configuration
    return {
      approvers: [
        { type: 'role', identifier: 'admin', required: true }
      ],
      policy: 'any'
    };
  }, [step.input]);

  // Get current approvals from instance
  const currentApprovals = useMemo((): Approval[] => {
    const approvals = instance.approvals?.filter(a => a.stepId === step.id) || [];

    // Merge with approval configuration
    return approvalConfig.approvers.map((approver, index) => {
      const existing = approvals.find(a => a.approver === approver.identifier);

      return {
        id: existing?.id || `approval_${index}`,
        approver: approver.identifier,
        approverName: getApproverDisplayName(approver.identifier, approver.type),
        status: existing?.status || 'pending',
        timestamp: existing?.timestamp,
        comment: existing?.comment,
        required: approver.required !== false,
        order: approver.order || index,
      };
    });
  }, [instance.approvals, step.id, approvalConfig.approvers]);

  // Check if current user can approve
  const canApprove = useMemo(() => {
    return approvalConfig.approvers.some(approver => {
      if (approver.type === 'user' && approver.identifier === currentUserId) {
        return true;
      }
      if (approver.type === 'role' && currentUserRoles.includes(approver.identifier)) {
        return true;
      }
      return false;
    });
  }, [approvalConfig.approvers, currentUserId, currentUserRoles]);

  // Check if current user has already acted
  const userHasActed = useMemo(() => {
    return currentApprovals.some(approval =>
      approval.approver === currentUserId && approval.status !== 'pending'
    );
  }, [currentApprovals, currentUserId]);

  // Calculate approval status
  const approvalStatus = useMemo(() => {
    const approvedCount = currentApprovals.filter(a => a.status === 'approved').length;
    const rejectedCount = currentApprovals.filter(a => a.status === 'rejected').length;
    const requiredCount = currentApprovals.filter(a => a.required).length;
    const requiredApprovedCount = currentApprovals.filter(a => a.required && a.status === 'approved').length;

    // Check rejection first
    if (rejectedCount > 0) {
      return 'rejected';
    }

    // Check approval based on policy
    switch (approvalConfig.policy) {
      case 'any':
        return approvedCount > 0 ? 'approved' : 'pending';
      case 'all':
        return requiredApprovedCount === requiredCount ? 'approved' : 'pending';
      case 'majority':
        return approvedCount > Math.floor(currentApprovals.length / 2) ? 'approved' : 'pending';
      case 'sequential':
        // Check if all previous required approvals are completed
        const sortedApprovals = currentApprovals
          .filter(a => a.required)
          .sort((a, b) => (a.order || 0) - (b.order || 0));

        for (let i = 0; i < sortedApprovals.length; i++) {
          if (sortedApprovals[i].status === 'rejected') {
            return 'rejected';
          }
          if (sortedApprovals[i].status === 'pending') {
            return i === 0 || sortedApprovals[i - 1].status === 'approved' ? 'pending' : 'waiting';
          }
        }
        return 'approved';
      default:
        return 'pending';
    }
  }, [currentApprovals, approvalConfig.policy]);

  // Handle approval submission
  const handleApprove = async () => {
    if (!canApprove || userHasActed || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onApprove(comment || undefined);
      setComment('');
    } catch (error) {
      console.error('Approval failed:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!canApprove || userHasActed || !rejectReason.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onReject(rejectReason);
      setRejectReason('');
      setShowRejectDialog(false);
    } catch (error) {
      console.error('Rejection failed:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelegate = async () => {
    if (!delegateTo.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onDelegate(delegateTo, delegateComment || undefined);
      setDelegateTo('');
      setDelegateComment('');
      setShowDelegateDialog(false);
    } catch (error) {
      console.error('Delegation failed:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Helper function to get display name for approver
  function getApproverDisplayName(identifier: string, type: 'user' | 'role' | 'group'): string {
    // This would typically integrate with your user/role management system
    switch (type) {
      case 'user':
        return `User: ${identifier}`;
      case 'role':
        return `Role: ${identifier}`;
      case 'group':
        return `Group: ${identifier}`;
      default:
        return identifier;
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <span className="status-icon approved">✓</span>;
      case 'rejected':
        return <span className="status-icon rejected">✕</span>;
      case 'pending':
        return <span className="status-icon pending">⏳</span>;
      default:
        return <span className="status-icon waiting">⏸</span>;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'rejected':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'pending':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  return (
    <div className={clsx('approval-step', className)}>
      <div className="approval-header">
        <div className="step-info">
          <h3 className="step-title">{step.name}</h3>
          {step.description && (
            <p className="step-description">{step.description}</p>
          )}
        </div>

        <div className={clsx('approval-status-badge', getStatusColor(approvalStatus))}>
          {getStatusIcon(approvalStatus)}
          <span className="status-text">
            {approvalStatus === 'waiting' ? 'Waiting for Prerequisites' : approvalStatus}
          </span>
        </div>
      </div>

      {/* Approval Policy Info */}
      <div className="approval-policy">
        <h4>Approval Policy</h4>
        <div className="policy-details">
          <span className="policy-type">
            {approvalConfig.policy === 'any' && 'Any approver can approve'}
            {approvalConfig.policy === 'all' && 'All required approvers must approve'}
            {approvalConfig.policy === 'majority' && 'Majority approval required'}
            {approvalConfig.policy === 'sequential' && 'Sequential approval required'}
          </span>

          {approvalConfig.escalation && (
            <div className="escalation-info">
              <small>
                Escalates to {approvalConfig.escalation.to} after {approvalConfig.escalation.delay} minutes
              </small>
            </div>
          )}
        </div>
      </div>

      {/* Approvers List */}
      <div className="approvers-list">
        <h4>Approvers ({currentApprovals.filter(a => a.status !== 'pending').length}/{currentApprovals.length})</h4>

        <div className="approvers-grid">
          <AnimatePresence>
            {currentApprovals
              .sort((a, b) => (a.order || 0) - (b.order || 0))
              .map((approval) => (
                <motion.div
                  key={approval.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className={clsx('approver-card', {
                    'current-user': approval.approver === currentUserId,
                    'required': approval.required,
                  })}
                >
                  <div className="approver-header">
                    <div className="approver-info">
                      <span className="approver-name">{approval.approverName}</span>
                      {approval.required && (
                        <span className="required-badge">Required</span>
                      )}
                    </div>
                    <div className={clsx('approval-status', approval.status)}>
                      {getStatusIcon(approval.status)}
                    </div>
                  </div>

                  {approval.comment && (
                    <div className="approval-comment">
                      <p>"{approval.comment}"</p>
                    </div>
                  )}

                  {approval.timestamp && (
                    <div className="approval-timestamp">
                      <small>{new Date(approval.timestamp).toLocaleString()}</small>
                    </div>
                  )}
                </motion.div>
              ))}
          </AnimatePresence>
        </div>
      </div>

      {/* Action Section */}
      {canApprove && !userHasActed && approvalStatus === 'pending' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="approval-actions"
        >
          <div className="comment-section">
            <label htmlFor="approval-comment">Comment (optional)</label>
            <textarea
              id="approval-comment"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Add a comment about your decision..."
              rows={3}
              className="comment-input"
            />
          </div>

          <div className="action-buttons">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleApprove}
              disabled={isSubmitting}
              className="approve-button"
            >
              {isSubmitting ? (
                <>
                  <span className="loading-spinner" />
                  Approving...
                </>
              ) : (
                <>
                  <span className="button-icon">✓</span>
                  Approve
                </>
              )}
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setShowRejectDialog(true)}
              disabled={isSubmitting}
              className="reject-button"
            >
              <span className="button-icon">✕</span>
              Reject
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setShowDelegateDialog(true)}
              disabled={isSubmitting}
              className="delegate-button"
            >
              <span className="button-icon">↗</span>
              Delegate
            </motion.button>
          </div>
        </motion.div>
      )}

      {/* Already Acted Message */}
      {userHasActed && (
        <div className="already-acted">
          <p>You have already provided your approval decision for this step.</p>
        </div>
      )}

      {/* Cannot Approve Message */}
      {!canApprove && (
        <div className="cannot-approve">
          <p>You do not have permission to approve this step.</p>
        </div>
      )}

      {/* Reject Dialog */}
      <AnimatePresence>
        {showRejectDialog && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="dialog-overlay"
            onClick={() => !isSubmitting && setShowRejectDialog(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              onClick={(e) => e.stopPropagation()}
              className="dialog-content"
            >
              <h3>Reject Approval</h3>
              <p>Please provide a reason for rejecting this approval:</p>

              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Reason for rejection..."
                rows={4}
                className="dialog-textarea"
                autoFocus
              />

              <div className="dialog-actions">
                <button
                  onClick={() => !isSubmitting && setShowRejectDialog(false)}
                  disabled={isSubmitting}
                  className="cancel-button"
                >
                  Cancel
                </button>
                <button
                  onClick={handleReject}
                  disabled={!rejectReason.trim() || isSubmitting}
                  className="confirm-reject-button"
                >
                  {isSubmitting ? 'Rejecting...' : 'Reject'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Delegate Dialog */}
      <AnimatePresence>
        {showDelegateDialog && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="dialog-overlay"
            onClick={() => !isSubmitting && setShowDelegateDialog(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              onClick={(e) => e.stopPropagation()}
              className="dialog-content"
            >
              <h3>Delegate Approval</h3>
              <p>Delegate this approval to another user:</p>

              <input
                type="text"
                value={delegateTo}
                onChange={(e) => setDelegateTo(e.target.value)}
                placeholder="User ID or email..."
                className="dialog-input"
                autoFocus
              />

              <textarea
                value={delegateComment}
                onChange={(e) => setDelegateComment(e.target.value)}
                placeholder="Optional comment..."
                rows={3}
                className="dialog-textarea"
              />

              <div className="dialog-actions">
                <button
                  onClick={() => !isSubmitting && setShowDelegateDialog(false)}
                  disabled={isSubmitting}
                  className="cancel-button"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelegate}
                  disabled={!delegateTo.trim() || isSubmitting}
                  className="confirm-delegate-button"
                >
                  {isSubmitting ? 'Delegating...' : 'Delegate'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default ApprovalStep;
