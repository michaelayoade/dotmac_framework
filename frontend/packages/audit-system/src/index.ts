/**
 * Universal Audit System Package
 * Complete audit logging, activity tracking, and compliance system for ISP portals
 */

// Components
export * from './components';

// Hooks
export * from './hooks';

// Services
export { UniversalAuditService } from './services/UniversalAuditService';

// Types
export * from './types';

// Default exports for convenience
export { UniversalAuditDashboard as AuditDashboard } from './components/UniversalAuditDashboard';
export { useUniversalAudit as useAudit } from './hooks/useUniversalAudit';
