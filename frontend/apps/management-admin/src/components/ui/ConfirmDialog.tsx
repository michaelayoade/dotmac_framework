import React from 'react';
import { Modal } from '@dotmac/primitives';
import { ExclamationTriangleIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';

export interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'info' | 'success';
  loading?: boolean;
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'warning',
  loading = false,
}: ConfirmDialogProps) {
  const getVariantStyles = () => {
    switch (variant) {
      case 'danger':
        return {
          iconColor: 'text-red-600',
          iconBg: 'bg-red-100',
          confirmButton: 'btn-danger',
          icon: XCircleIcon,
        };
      case 'warning':
        return {
          iconColor: 'text-yellow-600',
          iconBg: 'bg-yellow-100',
          confirmButton: 'btn-warning',
          icon: ExclamationTriangleIcon,
        };
      case 'success':
        return {
          iconColor: 'text-green-600',
          iconBg: 'bg-green-100',
          confirmButton: 'btn-primary',
          icon: CheckCircleIcon,
        };
      case 'info':
      default:
        return {
          iconColor: 'text-blue-600',
          iconBg: 'bg-blue-100',
          confirmButton: 'btn-primary',
          icon: ExclamationTriangleIcon,
        };
    }
  };

  const styles = getVariantStyles();
  const Icon = styles.icon;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      size="sm"
    >
      <div className="flex items-start space-x-4">
        <div className={`flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full ${styles.iconBg}`}>
          <Icon className={`h-6 w-6 ${styles.iconColor}`} aria-hidden="true" />
        </div>
        <div className="flex-1">
          <p className="text-sm text-gray-500">
            {message}
          </p>
        </div>
      </div>

      <div className="mt-6 flex gap-3 justify-end">
        <button
          type="button"
          className="btn-secondary"
          onClick={onClose}
          disabled={loading}
        >
          {cancelText}
        </button>
        <button
          type="button"
          className={`${styles.confirmButton} ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
          onClick={onConfirm}
          disabled={loading}
        >
          {loading ? (
            <div className="flex items-center">
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-current" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Processing...
            </div>
          ) : (
            confirmText
          )}
        </button>
      </div>
    </Modal>
  );
}

// Hook for easier usage
export function useConfirmDialog() {
  const [dialog, setDialog] = React.useState<{
    isOpen: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
    variant?: ConfirmDialogProps['variant'];
    confirmText?: string;
    cancelText?: string;
  }>({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: () => {},
  });

  const confirm = React.useCallback((options: {
    title: string;
    message: string;
    onConfirm: () => void;
    variant?: ConfirmDialogProps['variant'];
    confirmText?: string;
    cancelText?: string;
  }) => {
    return new Promise<boolean>((resolve) => {
      setDialog({
        ...options,
        isOpen: true,
      });

      // Override onConfirm to resolve promise
      const originalOnConfirm = options.onConfirm;
      setDialog(prev => ({
        ...prev,
        onConfirm: () => {
          originalOnConfirm();
          resolve(true);
          setDialog(prev => ({ ...prev, isOpen: false }));
        },
      }));
    });
  }, []);

  const close = React.useCallback(() => {
    setDialog(prev => ({ ...prev, isOpen: false }));
  }, []);

  const ConfirmDialogComponent = React.useCallback(() => (
    <ConfirmDialog
      isOpen={dialog.isOpen}
      onClose={close}
      onConfirm={dialog.onConfirm}
      title={dialog.title}
      message={dialog.message}
      variant={dialog.variant}
      confirmText={dialog.confirmText}
      cancelText={dialog.cancelText}
    />
  ), [dialog, close]);

  return {
    confirm,
    close,
    ConfirmDialog: ConfirmDialogComponent,
  };
}
