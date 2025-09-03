import React, { createContext, useContext, useState, useCallback } from 'react';
import { Transition } from '@headlessui/react';
import { Fragment } from 'react';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  InformationCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
  actions?: Array<{
    label: string;
    onClick: () => void;
    variant?: 'primary' | 'secondary';
  }>;
}

interface ToastContextType {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => string;
  removeToast: (id: string) => void;
  success: (title: string, message?: string, options?: Partial<Toast>) => string;
  error: (title: string, message?: string, options?: Partial<Toast>) => string;
  warning: (title: string, message?: string, options?: Partial<Toast>) => string;
  info: (title: string, message?: string, options?: Partial<Toast>) => string;
}

const ToastContext = createContext<ToastContextType | null>(null);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

interface ToastProviderProps {
  children: React.ReactNode;
  maxToasts?: number;
  defaultDuration?: number;
}

export function ToastProvider({
  children,
  maxToasts = 5,
  defaultDuration = 5000,
}: ToastProviderProps) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const addToast = useCallback(
    (toast: Omit<Toast, 'id'>) => {
      const id = Math.random().toString(36).substr(2, 9);
      const newToast: Toast = {
        ...toast,
        id,
        duration: toast.duration ?? defaultDuration,
      };

      setToasts((prev) => {
        const updated = [newToast, ...prev];
        return updated.slice(0, maxToasts);
      });

      // Auto remove toast after duration
      if (newToast.duration > 0) {
        setTimeout(() => {
          removeToast(id);
        }, newToast.duration);
      }

      return id;
    },
    [defaultDuration, maxToasts, removeToast]
  );

  const success = useCallback(
    (title: string, message?: string, options?: Partial<Toast>) => {
      return addToast({ ...options, type: 'success', title, message });
    },
    [addToast]
  );

  const error = useCallback(
    (title: string, message?: string, options?: Partial<Toast>) => {
      return addToast({
        ...options,
        type: 'error',
        title,
        message,
        duration: options?.duration ?? 7000,
      });
    },
    [addToast]
  );

  const warning = useCallback(
    (title: string, message?: string, options?: Partial<Toast>) => {
      return addToast({ ...options, type: 'warning', title, message });
    },
    [addToast]
  );

  const info = useCallback(
    (title: string, message?: string, options?: Partial<Toast>) => {
      return addToast({ ...options, type: 'info', title, message });
    },
    [addToast]
  );

  const value: ToastContextType = {
    toasts,
    addToast,
    removeToast,
    success,
    error,
    warning,
    info,
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
}

interface ToastContainerProps {
  toasts: Toast[];
  onRemove: (id: string) => void;
}

function ToastContainer({ toasts, onRemove }: ToastContainerProps) {
  return (
    <div className='fixed inset-0 z-50 flex flex-col items-end justify-start px-4 py-6 pointer-events-none sm:p-6 sm:items-start'>
      <div className='w-full flex flex-col items-center space-y-4 sm:items-end'>
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onRemove={onRemove} />
        ))}
      </div>
    </div>
  );
}

interface ToastItemProps {
  toast: Toast;
  onRemove: (id: string) => void;
}

function ToastItem({ toast, onRemove }: ToastItemProps) {
  const [show, setShow] = useState(true);

  const handleRemove = useCallback(() => {
    setShow(false);
    setTimeout(() => onRemove(toast.id), 300);
  }, [onRemove, toast.id]);

  const getToastStyles = (type: ToastType) => {
    switch (type) {
      case 'success':
        return {
          icon: CheckCircleIcon,
          iconColor: 'text-green-400',
          bg: 'bg-white',
          border: 'border-green-200',
        };
      case 'error':
        return {
          icon: XCircleIcon,
          iconColor: 'text-red-400',
          bg: 'bg-white',
          border: 'border-red-200',
        };
      case 'warning':
        return {
          icon: ExclamationTriangleIcon,
          iconColor: 'text-yellow-400',
          bg: 'bg-white',
          border: 'border-yellow-200',
        };
      case 'info':
      default:
        return {
          icon: InformationCircleIcon,
          iconColor: 'text-blue-400',
          bg: 'bg-white',
          border: 'border-blue-200',
        };
    }
  };

  const styles = getToastStyles(toast.type);
  const Icon = styles.icon;

  return (
    <Transition
      show={show}
      as={Fragment}
      enter='transform ease-out duration-300 transition'
      enterFrom='translate-y-2 opacity-0 sm:translate-y-0 sm:translate-x-2'
      enterTo='translate-y-0 opacity-100 sm:translate-x-0'
      leave='transition ease-in duration-100'
      leaveFrom='opacity-100'
      leaveTo='opacity-0'
    >
      <div
        className={`pointer-events-auto w-full max-w-sm overflow-hidden rounded-lg ${styles.bg} shadow-lg ring-1 ring-black ring-opacity-5 border-l-4 ${styles.border}`}
      >
        <div className='p-4'>
          <div className='flex items-start'>
            <div className='flex-shrink-0'>
              <Icon className={`h-6 w-6 ${styles.iconColor}`} aria-hidden='true' />
            </div>
            <div className='ml-3 w-0 flex-1 pt-0.5'>
              <p className='text-sm font-medium text-gray-900'>{toast.title}</p>
              {toast.message && <p className='mt-1 text-sm text-gray-500'>{toast.message}</p>}
              {toast.actions && toast.actions.length > 0 && (
                <div className='mt-3 flex space-x-2'>
                  {toast.actions.map((action, index) => (
                    <button
                      key={index}
                      type='button'
                      className={`text-sm font-medium ${
                        action.variant === 'primary'
                          ? 'text-blue-600 hover:text-blue-500'
                          : 'text-gray-600 hover:text-gray-500'
                      }`}
                      onClick={action.onClick}
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className='ml-4 flex-shrink-0 flex'>
              <button
                className='bg-white rounded-md inline-flex text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
                onClick={handleRemove}
              >
                <span className='sr-only'>Close</span>
                <XMarkIcon className='h-5 w-5' aria-hidden='true' />
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  );
}

// Simple toast function for quick usage without context
export function createToast(type: ToastType, title: string, message?: string) {
  // This would need to be connected to a global toast system
  // For now, it's a placeholder that could fallback to console
  console.log(`[${type.toUpperCase()}] ${title}${message ? ': ' + message : ''}`);
}
