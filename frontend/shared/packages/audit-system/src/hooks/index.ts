/**
 * Audit System Hooks Export
 */

export { useUniversalAudit } from './useUniversalAudit';
export { useUniversalAuditService } from '../services/useUniversalAuditService';

// Portal-specific hooks
export {
  useAdminAudit,
  useManagementAudit,
  useResellerAudit,
  useCustomerAudit,
  useTechnicianAudit,
  useAdminActivity,
  useManagementActivity,
  useResellerActivity,
  useCustomerActivity,
  useTechnicianActivity,
} from './portal-specific';

// Re-export types for convenience
export type { UseAuditSystemOptions, AuditSystemState, AuditSystemActions } from '../types';
