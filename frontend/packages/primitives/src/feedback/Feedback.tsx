/**
 * Unstyled, composable Feedback primitives (Toast, Alert, Loading)
 */

import { Slot } from '@radix-ui/react-slot';
import * as ToastPrimitive from '@radix-ui/react-toast';
import { cva, type VariantProps } from 'class-variance-authority';
import { clsx } from 'clsx';
import { AlertCircle, AlertTriangle, CheckCircle, Info, X } from 'lucide-react';
import type React from 'react';
import { createContext, forwardRef, useCallback, useContext, useState } from 'react';

// Toast variants
const toastVariants = cva('', {
  variants: {
    variant: {
      default: '',
      success: '',
      error: '',
      warning: '',
      info: '',
    },
    position: {
      'top-left': '',
      'top-center': '',
      'top-right': '',
      'bottom-left': '',
      'bottom-center': '',
      'bottom-right': '',
    },
  },
  defaultVariants: {
    variant: 'default',
    position: 'top-right',
  },
});

// Alert variants
const alertVariants = cva('', {
  variants: {
    variant: {
      default: '',
      success: '',
      error: '',
      warning: '',
      info: '',
    },
    size: {
      sm: '',
      md: '',
      lg: '',
    },
  },
  defaultVariants: {
    variant: 'default',
    size: 'md',
  },
});

// Loading variants
const loadingVariants = cva('', {
  variants: {
    variant: {
      spinner: '',
      dots: '',
      pulse: '',
      skeleton: '',
    },
    size: {
      xs: '',
      sm: '',
      md: '',
      lg: '',
      xl: '',
    },
  },
  defaultVariants: {
    variant: 'spinner',
    size: 'md',
  },
});

// Toast Context
interface ToastContextValue {
  toasts: ToastData[];
  addToast: (toast: Omit<ToastData, 'id'>) => string;
  removeToast: (id: string) => void;
  removeAllToasts: () => void;
}

interface ToastData {
  id: string;
  title?: string;
  description?: string;
  variant?: 'default' | 'success' | 'error' | 'warning' | 'info';
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
  onClose?: () => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

// Toast Provider
export interface ToastProviderProps {
  children: React.ReactNode;
  swipeDirection?: 'right' | 'left' | 'up' | 'down';
  swipeThreshold?: number;
  duration?: number;
}

export function ToastProvider({
  children,
  swipeDirection = 'right',
  swipeThreshold = 50,
  duration = 5000,
}: ToastProviderProps) {
  const [toasts, setToasts] = useState<ToastData[]>([]);

  const addToast = useCallback(
    (toast: Omit<ToastData, 'id'>) => {
      const id = Math.random().toString(36).substr(2, 9);
      const newToast: ToastData = {
        ...toast,
        id,
        duration: toast.duration ?? duration,
      };

      setToasts((prev) => [...prev, newToast]);
      return id;
    },
    [duration]
  );

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const removeAllToasts = useCallback(() => {
    setToasts([]);
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast, removeAllToasts }}>
      <ToastPrimitive.Provider swipeDirection={swipeDirection} swipeThreshold={swipeThreshold}>
        {children}

        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            open={true}
            onOpenChange={(open) => {
              if (!open) {
                removeToast(toast.id);
                toast.onClose?.();
              }
            }}
            duration={toast.duration}
            variant={toast.variant}
          >
            <ToastContent>
              {toast.title ? <ToastTitle>{toast.title}</ToastTitle> : null}
              {toast.description ? <ToastDescription>{toast.description}</ToastDescription> : null}
            </ToastContent>

            {toast.action ? (
              <ToastAction
                onClick={toast.action.onClick}
                onKeyDown={(e) => e.key === 'Enter' && toast.action.onClick}
              >
                {toast.action.label}
              </ToastAction>
            ) : null}

            <ToastClose />
          </Toast>
        ))}

        <ToastViewport />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  );
}

// Toast Components
const ToastViewport = forwardRef<
  React.ElementRef<typeof ToastPrimitive.Viewport>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitive.Viewport>
>(({ className, ...props }, ref) => (
  <ToastPrimitive.Viewport ref={ref} className={clsx('toast-viewport', className)} {...props} />
));

export interface ToastProps
  extends React.ComponentPropsWithoutRef<typeof ToastPrimitive.Root>,
    VariantProps<typeof toastVariants> {
  // Implementation pending
}

const Toast = forwardRef<React.ElementRef<typeof ToastPrimitive.Root>, ToastProps>(
  ({ className, variant, ...props }, ref) => (
    <ToastPrimitive.Root
      ref={ref}
      className={clsx(toastVariants({ variant }), 'toast', className)}
      {...props}
    />
  )
);

const ToastContent = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={clsx('toast-content', className)} {...props} />
  )
);

const ToastTitle = forwardRef<
  React.ElementRef<typeof ToastPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitive.Title>
>(({ className, ...props }, ref) => (
  <ToastPrimitive.Title ref={ref} className={clsx('toast-title', className)} {...props} />
));

const ToastDescription = forwardRef<
  React.ElementRef<typeof ToastPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitive.Description>
>(({ className, ...props }, ref) => (
  <ToastPrimitive.Description
    ref={ref}
    className={clsx('toast-description', className)}
    {...props}
  />
));

const ToastAction = forwardRef<
  React.ElementRef<typeof ToastPrimitive.Action>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitive.Action>
>(({ className, ...props }, ref) => (
  <ToastPrimitive.Action ref={ref} className={clsx('toast-action', className)} {...props} />
));

const ToastClose = forwardRef<
  React.ElementRef<typeof ToastPrimitive.Close>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitive.Close>
>(({ className, ...props }, ref) => (
  <ToastPrimitive.Close
    ref={ref}
    className={clsx('toast-close', className)}
    toast-close=''
    {...props}
  >
    <X className='toast-close-icon' />
    <span className='sr-only'>Close</span>
  </ToastPrimitive.Close>
));

// Alert Component
export interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {
  asChild?: boolean;
  icon?: React.ReactNode;
  closable?: boolean;
  onClose?: () => void;
}

export const Alert = forwardRef<HTMLDivElement, AlertProps>(
  (
    {
      className,
      variant,
      size,
      icon,
      closable = false,
      onClose,
      children,
      asChild = false,
      ...props
    },
    ref
  ) => {
    const Comp = asChild ? Slot : 'div';

    const defaultIcons = {
      default: <Info className='alert-icon' />,
      success: <CheckCircle className='alert-icon' />,
      error: <AlertCircle className='alert-icon' />,
      warning: <AlertTriangle className='alert-icon' />,
      info: <Info className='alert-icon' />,
    };

    const displayIcon = icon ?? (variant ? defaultIcons[variant] : defaultIcons.default);

    return (
      <Comp
        ref={ref}
        className={clsx(alertVariants({ variant, size }), 'alert', className)}
        role='alert'
        {...props}
      >
        {displayIcon ? <div className='alert-icon-wrapper'>{displayIcon}</div> : null}

        <div className='alert-content'>{children}</div>

        {closable ? (
          <button
            type='button'
            className='alert-close'
            onClick={onClose}
            onKeyDown={(e) => e.key === 'Enter' && onClose}
            aria-label='Close alert'
          >
            <X className='alert-close-icon' />
          </button>
        ) : null}
      </Comp>
    );
  }
);

// Alert Title
export interface AlertTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  asChild?: boolean;
}

export const AlertTitle = forwardRef<HTMLHeadingElement, AlertTitleProps>(
  ({ className, asChild = false, ...props }, _ref) => {
    const Comp = asChild ? Slot : 'h5';

    return <Comp ref={ref} className={clsx('alert-title', className)} {...props} />;
  }
);

// Alert Description
export interface AlertDescriptionProps extends React.HTMLAttributes<HTMLDivElement> {
  asChild?: boolean;
}

export const AlertDescription = forwardRef<HTMLDivElement, AlertDescriptionProps>(
  ({ className, asChild = false, ...props }, _ref) => {
    const Comp = asChild ? Slot : 'div';

    return <Comp ref={ref} className={clsx('alert-description', className)} {...props} />;
  }
);

// Loading Component
export interface LoadingProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof loadingVariants> {
  asChild?: boolean;
  text?: string;
  overlay?: boolean;
}

export const Loading = forwardRef<HTMLDivElement, LoadingProps>(
  ({ className, variant, size, text, overlay = false, asChild = false, ...props }, _ref) => {
    const Comp = asChild ? Slot : 'div';

    const renderSpinner = () => (
      <div className='loading-spinner'>
        <div className='spinner' />
      </div>
    );

    const renderDots = () => (
      <div className='loading-dots'>
        <div className='dot' />
        <div className='dot' />
        <div className='dot' />
      </div>
    );

    const renderPulse = () => (
      <div className='loading-pulse'>
        <div className='pulse' />
      </div>
    );

    const renderContent = () => {
      switch (variant) {
        case 'spinner':
          return renderSpinner();
        case 'dots':
          return renderDots();
        case 'pulse':
          return renderPulse();
        case 'skeleton':
          return <div className='loading-skeleton' />;
        default:
          return renderSpinner();
      }
    };

    const content = (
      <Comp
        ref={ref}
        className={clsx(
          loadingVariants({ variant, size }),
          'loading',
          { 'loading-overlay': overlay },
          className
        )}
        role='alert'
        aria-live='polite'
        aria-label={text || 'Loading'}
        {...props}
      >
        {renderContent()}
        {text ? <span className='loading-text'>{text}</span> : null}
        <span className='sr-only'>{text || 'Loading...'}</span>
      </Comp>
    );

    if (overlay) {
      return <div className='loading-overlay-container'>{content}</div>;
    }

    return content;
  }
);

// Loading Skeleton
export interface LoadingSkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  asChild?: boolean;
  lines?: number;
  avatar?: boolean;
  width?: string | number;
  height?: string | number;
}

export const LoadingSkeleton = forwardRef<HTMLDivElement, LoadingSkeletonProps>(
  ({ className, lines = 3, avatar = false, width, height, asChild = false, ...props }, _ref) => {
    const Comp = asChild ? Slot : 'div';

    return (
      <Comp ref={ref} className={clsx('loading-skeleton-container', className)} {...props}>
        {avatar ? <div className='skeleton-avatar' /> : null}

        <div className='skeleton-content'>
          {Array.from({ length: lines }, (_, i) => (
            <div
              key={`item-${i}`}
              className='skeleton-line'
              style={{
                width: i === lines - 1 ? '60%' : width,
                height,
              }}
            />
          ))}
        </div>
      </Comp>
    );
  }
);

// Progress Component
export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
  max?: number;
  indeterminate?: boolean;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'success' | 'error' | 'warning';
  showValue?: boolean;
  label?: string;
}

export const Progress = forwardRef<HTMLDivElement, ProgressProps>(
  (
    {
      className,
      value = 0,
      max = 100,
      indeterminate = false,
      size = 'md',
      variant = 'default',
      showValue = false,
      label,
      ...props
    },
    ref
  ) => {
    const percentage = indeterminate ? 0 : Math.min(Math.max((value / max) * 100, 0), 100);

    return (
      <div
        ref={ref}
        className={clsx(
          'progress-container',
          `size-${size}`,
          `variant-${variant}`,
          { indeterminate },
          className
        )}
        {...props}
      >
        {label || showValue ? (
          <div className='progress-header'>
            {label ? <span className='progress-label'>{label}</span> : null}
            {showValue && !indeterminate ? (
              <span className='progress-value'>{Math.round(percentage)}%</span>
            ) : null}
          </div>
        ) : null}

        <div
          className='progress-track'
          role='progressbar'
          aria-valuenow={indeterminate ? undefined : value}
          aria-valuemin={0}
          aria-valuemax={max}
          aria-label={label}
        >
          <div
            className='progress-indicator'
            style={{
              transform: `translateX(-${100 - percentage}%)`,
            }}
          />
        </div>
      </div>
    );
  }
);

// Presence Indicator Component
export interface PresenceIndicatorProps extends React.HTMLAttributes<HTMLDivElement> {
  status: 'online' | 'offline' | 'busy' | 'away' | 'idle';
  size?: 'sm' | 'md' | 'lg';
  withPulse?: boolean;
  label?: string;
}

export const PresenceIndicator = forwardRef<HTMLDivElement, PresenceIndicatorProps>(
  ({ className, status, size = 'md', withPulse = false, label, ...props }, _ref) => {
    return (
      <div
        ref={ref}
        className={clsx(
          'status-indicator',
          `status-${status}`,
          `size-${size}`,
          { 'with-pulse': withPulse },
          className
        )}
        title={label || status}
        {...props}
      >
        <div className='status-dot' />
        {withPulse ? <div className='status-pulse' /> : null}
        {label ? <span className='status-label'>{label}</span> : null}
      </div>
    );
  }
);

// Set display names
ToastViewport.displayName = 'ToastViewport';
Toast.displayName = 'Toast';
ToastContent.displayName = 'ToastContent';
ToastTitle.displayName = 'ToastTitle';
ToastDescription.displayName = 'ToastDescription';
ToastAction.displayName = 'ToastAction';
ToastClose.displayName = 'ToastClose';
Alert.displayName = 'Alert';
AlertTitle.displayName = 'AlertTitle';
AlertDescription.displayName = 'AlertDescription';
Loading.displayName = 'Loading';
LoadingSkeleton.displayName = 'LoadingSkeleton';
Progress.displayName = 'Progress';
PresenceIndicator.displayName = 'PresenceIndicator';

export {
  ToastViewport,
  Toast,
  ToastContent,
  ToastTitle,
  ToastDescription,
  ToastAction,
  ToastClose,
};
