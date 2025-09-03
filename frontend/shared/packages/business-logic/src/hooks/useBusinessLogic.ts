/**
 * React Hook for Business Logic Integration
 * Provides easy access to business logic engines with portal context
 */

import { useMemo } from 'react';
import { BusinessLogicFactory, type BusinessLogicEngines } from '../factory/BusinessLogicFactory';
import type { PortalContext } from '../types';

// This would typically come from your auth context or app context
interface UseBusinessLogicProps {
  portalType: PortalContext['portalType'];
  userId: string;
  permissions: string[];
  tenantId?: string;
  preferences?: Record<string, any>;
}

/**
 * Main hook for accessing all business logic engines
 */
export function useBusinessLogic(props: UseBusinessLogicProps): BusinessLogicEngines {
  const { portalType, userId, permissions, tenantId, preferences } = props;

  return useMemo(() => {
    const config = BusinessLogicFactory.createDefaultConfig(portalType);
    const context = BusinessLogicFactory.createPortalContext(
      portalType,
      userId,
      permissions,
      tenantId,
      preferences
    );

    return BusinessLogicFactory.createEngines(config, context);
  }, [portalType, userId, permissions, tenantId, preferences]);
}
