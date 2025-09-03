import { useUIActions } from '@/store';
import { useCallback } from 'react';

export function useNotificationActions() {
  const { addNotification } = useUIActions();

  const showSuccess = useCallback(
    (
      title: string,
      message?: string,
      options?: {
        duration?: number;
        action?: { label: string; onClick: () => void };
      }
    ) => {
      addNotification({
        type: 'success',
        title,
        message: message || '',
        duration: options?.duration,
        action: options?.action,
      });
    },
    [addNotification]
  );

  const showError = useCallback(
    (
      title: string,
      message?: string,
      options?: {
        duration?: number;
        action?: { label: string; onClick: () => void };
      }
    ) => {
      addNotification({
        type: 'error',
        title,
        message: message || '',
        duration: options?.duration || 0, // Errors persist until dismissed
        action: options?.action,
      });
    },
    [addNotification]
  );

  const showWarning = useCallback(
    (
      title: string,
      message?: string,
      options?: {
        duration?: number;
        action?: { label: string; onClick: () => void };
      }
    ) => {
      addNotification({
        type: 'warning',
        title,
        message: message || '',
        duration: options?.duration,
        action: options?.action,
      });
    },
    [addNotification]
  );

  const showInfo = useCallback(
    (
      title: string,
      message?: string,
      options?: {
        duration?: number;
        action?: { label: string; onClick: () => void };
      }
    ) => {
      addNotification({
        type: 'info',
        title,
        message: message || '',
        duration: options?.duration,
        action: options?.action,
      });
    },
    [addNotification]
  );

  // Convenience methods for common scenarios
  const showApiSuccess = useCallback(
    (action: string, resource?: string) => {
      showSuccess('Success!', `${resource || 'Item'} ${action} successfully.`);
    },
    [showSuccess]
  );

  const showApiError = useCallback(
    (action: string, error?: string, resource?: string) => {
      showError(
        'Operation Failed',
        error || `Failed to ${action} ${resource || 'item'}. Please try again.`,
        {
          action: {
            label: 'Retry',
            onClick: () => window.location.reload(),
          },
        }
      );
    },
    [showError]
  );

  const showValidationError = useCallback(
    (message: string) => {
      showWarning('Validation Error', message);
    },
    [showWarning]
  );

  const showNetworkError = useCallback(() => {
    showError(
      'Network Error',
      'Unable to connect to the server. Please check your internet connection.',
      {
        action: {
          label: 'Retry',
          onClick: () => window.location.reload(),
        },
      }
    );
  }, [showError]);

  const showMaintenanceNotice = useCallback(() => {
    showInfo(
      'System Maintenance',
      'The system will be undergoing maintenance shortly. Please save your work.',
      {
        duration: 0, // Persist until dismissed
        action: {
          label: 'Learn More',
          onClick: () => window.open('/maintenance', '_blank'),
        },
      }
    );
  }, [showInfo]);

  return {
    // Basic notification methods
    showSuccess,
    showError,
    showWarning,
    showInfo,

    // Convenience methods
    showApiSuccess,
    showApiError,
    showValidationError,
    showNetworkError,
    showMaintenanceNotice,

    // Original addNotification for compatibility
    addNotification,
  };
}

// Export standardized hook only - NO BACKWARD COMPATIBILITY
export { useNotificationActions };
