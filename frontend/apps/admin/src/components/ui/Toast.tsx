/**
 * Toast Notification System
 * Accessible toast notifications with animations and management
 */

'use client';

import React, { 
  useState, 
  useEffect, 
  useCallback, 
  createContext, 
  useContext, 
  ReactNode,
  useMemo 
} from 'react';
import { createPortal } from 'react-dom';
import { 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  Info, 
  X,
  Loader2
} from 'lucide-react';
import { cn, animationUtils } from '../../design-system/utils';

// Types
export type ToastType = 'success' | 'error' | 'warning' | 'info' | 'loading';
export type ToastPosition = 
  | 'top-left' 
  | 'top-center' 
  | 'top-right'
  | 'bottom-left' 
  | 'bottom-center' 
  | 'bottom-right';

export interface Toast {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
  duration?: number;
  persistent?: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
  onDismiss?: () => void;
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => string;
  removeToast: (id: string) => void;
  clearAllToasts: () => void;
  updateToast: (id: string, updates: Partial<Toast>) => void;
}

// Context
const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

// Hook for easy toast creation
export function useToastActions() {
  const { addToast, removeToast, updateToast } = useToast();

  const success = useCallback((message: string, options?: Partial<Toast>) => {
    return addToast({ type: 'success', message, ...options });
  }, [addToast]);

  const error = useCallback((message: string, options?: Partial<Toast>) => {
    return addToast({ type: 'error', message, persistent: true, ...options });
  }, [addToast]);

  const warning = useCallback((message: string, options?: Partial<Toast>) => {
    return addToast({ type: 'warning', message, ...options });
  }, [addToast]);

  const info = useCallback((message: string, options?: Partial<Toast>) => {
    return addToast({ type: 'info', message, ...options });
  }, [addToast]);

  const loading = useCallback((message: string, options?: Partial<Toast>) => {
    return addToast({ type: 'loading', message, persistent: true, ...options });
  }, [addToast]);

  const promise = useCallback(<T,>(
    promise: Promise<T>,
    {
      loading: loadingMessage,
      success: successMessage,
      error: errorMessage,
    }: {
      loading: string;
      success: string | ((data: T) => string);
      error: string | ((error: any) => string);
    }
  ): Promise<T> => {
    const toastId = loading(loadingMessage);

    return promise
      .then((data) => {
        const message = typeof successMessage === 'function' ? successMessage(data) : successMessage;
        updateToast(toastId, { type: 'success', message, persistent: false, duration: 4000 });
        return data;
      })
      .catch((err) => {
        const message = typeof errorMessage === 'function' ? errorMessage(err) : errorMessage;
        updateToast(toastId, { type: 'error', message, persistent: false, duration: 6000 });
        throw err;
      });
  }, [loading, updateToast]);

  const dismiss = useCallback((id: string) => {
    removeToast(id);
  }, [removeToast]);

  return {
    success,
    error,
    warning,
    info,
    loading,
    promise,
    dismiss,
  };
}

// Toast Component
interface ToastItemProps {
  toast: Toast;
  onRemove: (id: string) => void;
  position: ToastPosition;
}

function ToastItem({ toast, onRemove, position }: ToastItemProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isRemoving, setIsRemoving] = useState(false);

  // Auto-remove timer
  useEffect(() => {
    if (!toast.persistent && toast.duration !== 0) {
      const duration = toast.duration || getDefaultDuration(toast.type);
      const timer = setTimeout(() => {
        handleDismiss();
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [toast.duration, toast.persistent, toast.type]);

  // Show animation
  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), 50);
    return () => clearTimeout(timer);
  }, []);

  const handleDismiss = useCallback(() => {
    setIsRemoving(true);
    toast.onDismiss?.();
    
    // Wait for exit animation
    setTimeout(() => {
      onRemove(toast.id);
    }, 200);
  }, [toast, onRemove]);

  const handleAction = useCallback(() => {
    toast.action?.onClick();
    handleDismiss();
  }, [toast.action, handleDismiss]);

  const config = getToastConfig(toast.type);
  const positionClasses = getPositionClasses(position);

  return (
    <div
      className={cn(
        'pointer-events-auto w-full max-w-sm overflow-hidden rounded-lg shadow-lg ring-1 ring-black ring-opacity-5',
        'transform transition-all duration-300 ease-out',
        config.bgClass,
        config.borderClass,
        isVisible && !isRemoving ? positionClasses.enter : positionClasses.exit
      )}
      role="alert"
      aria-live={toast.type === 'error' ? 'assertive' : 'polite'}
      aria-atomic="true"
    >
      <div className="p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <config.icon 
              className={cn('h-5 w-5', config.iconClass)}
              aria-hidden="true"
            />
          </div>
          
          <div className="ml-3 w-0 flex-1">
            {toast.title && (
              <p className={cn('text-sm font-medium', config.titleClass)}>
                {toast.title}
              </p>
            )}
            <p className={cn(
              'text-sm',
              toast.title ? 'mt-1' : '',
              config.messageClass
            )}>
              {toast.message}
            </p>
            
            {toast.action && (
              <div className="mt-3">
                <button
                  type="button"
                  onClick={handleAction}
                  className={cn(
                    'rounded-md text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2',
                    config.actionClass
                  )}
                >
                  {toast.action.label}
                </button>
              </div>
            )}
          </div>
          
          <div className="ml-4 flex flex-shrink-0">
            <button
              type="button"
              onClick={handleDismiss}
              className={cn(
                'inline-flex rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2',
                config.dismissClass
              )}
            >
              <span className="sr-only">Close</span>
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Toast Container
interface ToastContainerProps {
  toasts: Toast[];
  position: ToastPosition;
  onRemove: (id: string) => void;
}

function ToastContainer({ toasts, position, onRemove }: ToastContainerProps) {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted || toasts.length === 0) {
    return null;
  }

  const containerClasses = getContainerClasses(position);

  const content = (
    <div className={cn('fixed z-50 pointer-events-none', containerClasses)}>
      <div className="flex flex-col space-y-4">
        {toasts.map((toast) => (
          <ToastItem
            key={toast.id}
            toast={toast}
            onRemove={onRemove}
            position={position}
          />
        ))}
      </div>
    </div>
  );

  return createPortal(content, document.body);
}

// Provider Component
interface ToastProviderProps {
  children: ReactNode;
  position?: ToastPosition;
  maxToasts?: number;
}

export function ToastProvider({ 
  children, 
  position = 'top-right',
  maxToasts = 5 
}: ToastProviderProps) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((toast: Omit<Toast, 'id'>): string => {
    const id = generateToastId();
    const newToast: Toast = { ...toast, id };
    
    setToasts(prev => {
      const updated = [newToast, ...prev];
      return updated.slice(0, maxToasts);
    });
    
    return id;
  }, [maxToasts]);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  }, []);

  const clearAllToasts = useCallback(() => {
    setToasts([]);
  }, []);

  const updateToast = useCallback((id: string, updates: Partial<Toast>) => {
    setToasts(prev => prev.map(toast => 
      toast.id === id ? { ...toast, ...updates } : toast
    ));
  }, []);

  const value = useMemo(() => ({
    toasts,
    addToast,
    removeToast,
    clearAllToasts,
    updateToast,
  }), [toasts, addToast, removeToast, clearAllToasts, updateToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer 
        toasts={toasts}
        position={position}
        onRemove={removeToast}
      />
    </ToastContext.Provider>
  );
}

// Utility functions
function generateToastId(): string {
  return `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

function getDefaultDuration(type: ToastType): number {
  switch (type) {
    case 'success':
      return 4000;
    case 'error':
      return 6000;
    case 'warning':
      return 5000;
    case 'info':
      return 4000;
    case 'loading':
      return 0; // Persistent by default
    default:
      return 4000;
  }
}

function getToastConfig(type: ToastType) {
  const configs = {
    success: {
      icon: CheckCircle,
      bgClass: 'bg-white',
      borderClass: 'border-l-4 border-green-400',
      iconClass: 'text-green-400',
      titleClass: 'text-gray-900',
      messageClass: 'text-gray-500',
      actionClass: 'bg-white text-green-600 hover:text-green-500 focus:ring-green-500',
      dismissClass: 'text-gray-400 hover:text-gray-500 focus:ring-gray-500',
    },
    error: {
      icon: XCircle,
      bgClass: 'bg-white',
      borderClass: 'border-l-4 border-red-400',
      iconClass: 'text-red-400',
      titleClass: 'text-gray-900',
      messageClass: 'text-gray-500',
      actionClass: 'bg-white text-red-600 hover:text-red-500 focus:ring-red-500',
      dismissClass: 'text-gray-400 hover:text-gray-500 focus:ring-gray-500',
    },
    warning: {
      icon: AlertTriangle,
      bgClass: 'bg-white',
      borderClass: 'border-l-4 border-yellow-400',
      iconClass: 'text-yellow-400',
      titleClass: 'text-gray-900',
      messageClass: 'text-gray-500',
      actionClass: 'bg-white text-yellow-600 hover:text-yellow-500 focus:ring-yellow-500',
      dismissClass: 'text-gray-400 hover:text-gray-500 focus:ring-gray-500',
    },
    info: {
      icon: Info,
      bgClass: 'bg-white',
      borderClass: 'border-l-4 border-blue-400',
      iconClass: 'text-blue-400',
      titleClass: 'text-gray-900',
      messageClass: 'text-gray-500',
      actionClass: 'bg-white text-blue-600 hover:text-blue-500 focus:ring-blue-500',
      dismissClass: 'text-gray-400 hover:text-gray-500 focus:ring-gray-500',
    },
    loading: {
      icon: Loader2,
      bgClass: 'bg-white',
      borderClass: 'border-l-4 border-blue-400',
      iconClass: 'text-blue-400 animate-spin',
      titleClass: 'text-gray-900',
      messageClass: 'text-gray-500',
      actionClass: 'bg-white text-blue-600 hover:text-blue-500 focus:ring-blue-500',
      dismissClass: 'text-gray-400 hover:text-gray-500 focus:ring-gray-500',
    },
  };

  return configs[type];
}

function getContainerClasses(position: ToastPosition): string {
  const positions = {
    'top-left': 'top-4 left-4',
    'top-center': 'top-4 left-1/2 transform -translate-x-1/2',
    'top-right': 'top-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'bottom-center': 'bottom-4 left-1/2 transform -translate-x-1/2',
    'bottom-right': 'bottom-4 right-4',
  };

  return positions[position];
}

function getPositionClasses(position: ToastPosition) {
  const isLeft = position.includes('left');
  const isRight = position.includes('right');
  const isTop = position.includes('top');

  let enter = 'opacity-100 ';
  let exit = 'opacity-0 ';

  if (isLeft) {
    enter += 'translate-x-0';
    exit += '-translate-x-full';
  } else if (isRight) {
    enter += 'translate-x-0';
    exit += 'translate-x-full';
  } else {
    // Center
    enter += 'scale-100';
    exit += 'scale-95';
  }

  if (isTop) {
    enter += ' translate-y-0';
    exit += ' -translate-y-2';
  } else {
    enter += ' translate-y-0';
    exit += ' translate-y-2';
  }

  return { enter, exit };
}