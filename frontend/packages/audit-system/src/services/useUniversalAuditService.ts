/**
 * Universal Audit Service Hook
 * Provides access to the UniversalAuditService instance
 */

'use client';

import { useMemo } from 'react';
import { UniversalAuditService } from './UniversalAuditService';

let auditServiceInstance: UniversalAuditService | null = null;

export function useUniversalAuditService() {
  const auditService = useMemo(() => {
    if (!auditServiceInstance) {
      auditServiceInstance = new UniversalAuditService();
    }
    return auditServiceInstance;
  }, []);

  return auditService;
}

export default useUniversalAuditService;
