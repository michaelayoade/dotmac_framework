'use client';

import React, { createContext, useContext, useReducer, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, AlertCircle, AlertTriangle, Info, X, Wifi, WifiOff } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'warning' | 'info' | 'offline' | 'online';

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
  persistent?: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface ToastState {
  toasts: Toast[];
}

type ToastAction =
  | { type: 'ADD_TOAST'; payload: Toast }
  | { type: 'REMOVE_TOAST'; payload: string }
  | { type: 'CLEAR_ALL' };

const toastReducer = (state: ToastState, action: ToastAction): ToastState => {
  switch (action.type) {
    case 'ADD_TOAST':
      return {
        ...state,
        toasts: [action.payload, ...state.toasts.slice(0, 4)], // Keep max 5 toasts
      };
    case 'REMOVE_TOAST':
      return {
        ...state,
        toasts: state.toasts.filter((toast) => toast.id !== action.payload),
      };
    case 'CLEAR_ALL':
      return {
        ...state,
        toasts: [],
      };
    default:
      return state;
  }
};

interface ToastContextType {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
  clearAllToasts: () => void;
  success: (title: string, message?: string, options?: Partial<Toast>) => void;
  error: (title: string, message?: string, options?: Partial<Toast>) => void;
  warning: (title: string, message?: string, options?: Partial<Toast>) => void;
  info: (title: string, message?: string, options?: Partial<Toast>) => void;
  offline: (message?: string) => void;
  online: (message?: string) => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(toastReducer, { toasts: [] });

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).substr(2, 9);
    const newToast: Toast = {
      ...toast,
      id,
      duration: toast.duration ?? (toast.type === 'error' ? 8000 : 5000),
    };

    dispatch({ type: 'ADD_TOAST', payload: newToast });

    // Auto-remove toast after duration (unless persistent)
    if (!newToast.persistent && newToast.duration! > 0) {
      setTimeout(() => {
        dispatch({ type: 'REMOVE_TOAST', payload: id });
      }, newToast.duration);
    }
  }, []);

  const removeToast = useCallback((id: string) => {
    dispatch({ type: 'REMOVE_TOAST', payload: id });
  }, []);

  const clearAllToasts = useCallback(() => {
    dispatch({ type: 'CLEAR_ALL' });
  }, []);

  // Convenience methods
  const success = useCallback(
    (title: string, message?: string, options?: Partial<Toast>) => {
      addToast({ type: 'success', title, message, ...options });
    },
    [addToast]
  );

  const error = useCallback(
    (title: string, message?: string, options?: Partial<Toast>) => {
      addToast({ type: 'error', title, message, ...options });
    },
    [addToast]
  );

  const warning = useCallback(
    (title: string, message?: string, options?: Partial<Toast>) => {
      addToast({ type: 'warning', title, message, ...options });
    },
    [addToast]
  );

  const info = useCallback(
    (title: string, message?: string, options?: Partial<Toast>) => {
      addToast({ type: 'info', title, message, ...options });
    },
    [addToast]
  );

  const offline = useCallback(
    (message?: string) => {
      addToast({
        type: 'offline',
        title: 'Connection Lost',
        message: message || 'Working offline. Changes will sync when connection is restored.',
        persistent: true,
      });
    },
    [addToast]
  );

  const online = useCallback(
    (message?: string) => {
      addToast({
        type: 'online',
        title: 'Connection Restored',
        message: message || 'Back online. Syncing pending changes...',
        duration: 3000,
      });
    },
    [addToast]
  );

  const contextValue: ToastContextType = {
    toasts: state.toasts,
    addToast,
    removeToast,
    clearAllToasts,
    success,
    error,
    warning,
    info,
    offline,
    online,
  };

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <ToastContainer />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

function ToastContainer() {
  const { toasts, removeToast } = useToast();

  return (
    <div className='fixed top-4 right-4 z-50 space-y-2 max-w-sm w-full pointer-events-none'>
      <AnimatePresence>
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onRemove={removeToast} />
        ))}
      </AnimatePresence>
    </div>
  );
}

function ToastItem({ toast, onRemove }: { toast: Toast; onRemove: (id: string) => void }) {
  const handleRemove = () => onRemove(toast.id);

  const getToastStyles = (type: ToastType) => {
    switch (type) {
      case 'success':
        return 'bg-green-50 border-green-200 text-green-800';
      case 'error':
        return 'bg-red-50 border-red-200 text-red-800';
      case 'warning':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800';
      case 'info':
        return 'bg-blue-50 border-blue-200 text-blue-800';
      case 'offline':
        return 'bg-gray-50 border-gray-200 text-gray-800';
      case 'online':
        return 'bg-green-50 border-green-200 text-green-800';
      default:
        return 'bg-white border-gray-200 text-gray-800';
    }
  };

  const getIcon = (type: ToastType) => {
    const iconClass = 'w-5 h-5';
    switch (type) {
      case 'success':
        return <CheckCircle className={`${iconClass} text-green-500`} />;
      case 'error':
        return <AlertCircle className={`${iconClass} text-red-500`} />;
      case 'warning':
        return <AlertTriangle className={`${iconClass} text-yellow-500`} />;
      case 'info':
        return <Info className={`${iconClass} text-blue-500`} />;
      case 'offline':
        return <WifiOff className={`${iconClass} text-gray-500`} />;
      case 'online':
        return <Wifi className={`${iconClass} text-green-500`} />;
      default:
        return <Info className={`${iconClass} text-gray-500`} />;
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -50, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -20, scale: 0.95 }}
      transition={{ duration: 0.2 }}
      className={`pointer-events-auto relative rounded-lg border p-4 shadow-lg ${getToastStyles(toast.type)}`}
    >
      <div className='flex items-start space-x-3'>
        <div className='flex-shrink-0'>{getIcon(toast.type)}</div>

        <div className='flex-1 min-w-0'>
          <h4 className='font-medium text-sm'>{toast.title}</h4>
          {toast.message && <p className='mt-1 text-sm opacity-90'>{toast.message}</p>}

          {toast.action && (
            <div className='mt-3'>
              <button
                onClick={toast.action.onClick}
                className='text-sm font-medium underline hover:no-underline focus:outline-none focus:ring-2 focus:ring-current focus:ring-offset-2 rounded'
              >
                {toast.action.label}
              </button>
            </div>
          )}
        </div>

        {!toast.persistent && (
          <button
            onClick={handleRemove}
            className='flex-shrink-0 rounded-md p-1.5 focus:outline-none focus:ring-2 focus:ring-current focus:ring-offset-2 hover:bg-black hover:bg-opacity-10'
          >
            <X className='w-4 h-4' />
          </button>
        )}
      </div>
    </motion.div>
  );
}

// Hook for network status toasts
export function useNetworkToasts() {
  const { offline, online } = useToast();
  const [isOnline, setIsOnline] = React.useState(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  );

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      online();
    };

    const handleOffline = () => {
      setIsOnline(false);
      offline();
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [online, offline]);

  return { isOnline };
}
