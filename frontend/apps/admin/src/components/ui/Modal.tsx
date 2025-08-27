/**
 * Modal/Dialog System
 * Enterprise-grade modal components with accessibility and animations
 */

'use client';

import React, { 
  useState, 
  useEffect, 
  useRef, 
  ReactNode, 
  MouseEvent, 
  KeyboardEvent,
  useCallback 
} from 'react';
import { createPortal } from 'react-dom';
import { X, AlertTriangle, CheckCircle, Info, AlertCircle } from 'lucide-react';
import { cn, animationUtils } from '../../design-system/utils';

// Types
export type ModalSize = 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
export type ModalVariant = 'default' | 'danger' | 'warning' | 'success' | 'info';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
  title?: string;
  description?: string;
  size?: ModalSize;
  variant?: ModalVariant;
  showCloseButton?: boolean;
  closeOnOverlayClick?: boolean;
  closeOnEscape?: boolean;
  preventBodyScroll?: boolean;
  className?: string;
  overlayClassName?: string;
  contentClassName?: string;
  headerClassName?: string;
  footerClassName?: string;
  footer?: ReactNode;
  icon?: ReactNode;
  centered?: boolean;
  animationDuration?: number;
}

interface ConfirmModalProps extends Omit<ModalProps, 'children' | 'footer'> {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm: () => void | Promise<void>;
  onCancel?: () => void;
  isConfirming?: boolean;
  destructive?: boolean;
}

// Modal size configurations
const modalSizes: Record<ModalSize, string> = {
  sm: 'max-w-sm',
  md: 'max-w-md', 
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  '2xl': 'max-w-2xl',
  full: 'max-w-full mx-4',
};

// Variant configurations
const variantConfigs = {
  default: {
    icon: null,
    headerClass: '',
    borderClass: '',
  },
  danger: {
    icon: AlertTriangle,
    headerClass: 'text-red-900',
    borderClass: 'border-red-200',
  },
  warning: {
    icon: AlertCircle,
    headerClass: 'text-yellow-900', 
    borderClass: 'border-yellow-200',
  },
  success: {
    icon: CheckCircle,
    headerClass: 'text-green-900',
    borderClass: 'border-green-200',
  },
  info: {
    icon: Info,
    headerClass: 'text-blue-900',
    borderClass: 'border-blue-200',
  },
};

// Hook for managing modal state
export function useModal(initialState: boolean = false) {
  const [isOpen, setIsOpen] = useState(initialState);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen(prev => !prev), []);

  return {
    isOpen,
    open,
    close,
    toggle,
  };
}

// Hook for focus management
function useFocusTrap(isActive: boolean) {
  const containerRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isActive) return;

    // Store the currently focused element
    previousFocusRef.current = document.activeElement as HTMLElement;

    const container = containerRef.current;
    if (!container) return;

    // Get all focusable elements
    const focusableElements = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

    // Focus the first element
    if (firstElement) {
      firstElement.focus();
    }

    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstElement) {
          lastElement?.focus();
          e.preventDefault();
        }
      } else {
        // Tab
        if (document.activeElement === lastElement) {
          firstElement?.focus();
          e.preventDefault();
        }
      }
    };

    // Add event listener
    container.addEventListener('keydown', handleTabKey as any);

    // Cleanup
    return () => {
      container.removeEventListener('keydown', handleTabKey as any);
      
      // Restore focus
      if (previousFocusRef.current) {
        previousFocusRef.current.focus();
      }
    };
  }, [isActive]);

  return containerRef;
}

// Base Modal Component
export function Modal({
  isOpen,
  onClose,
  children,
  title,
  description,
  size = 'md',
  variant = 'default',
  showCloseButton = true,
  closeOnOverlayClick = true,
  closeOnEscape = true,
  preventBodyScroll = true,
  className = '',
  overlayClassName = '',
  contentClassName = '',
  headerClassName = '',
  footerClassName = '',
  footer,
  icon,
  centered = true,
  animationDuration = 200,
}: ModalProps) {
  const [isMounted, setIsMounted] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const containerRef = useFocusTrap(isOpen);

  const config = variantConfigs[variant];
  const VariantIcon = icon || config.icon;

  // Mount/unmount handling
  useEffect(() => {
    setIsMounted(true);
    return () => setIsMounted(false);
  }, []);

  // Body scroll prevention
  useEffect(() => {
    if (!preventBodyScroll || !isOpen) return;

    const originalStyle = window.getComputedStyle(document.body).overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.body.style.overflow = originalStyle;
    };
  }, [isOpen, preventBodyScroll]);

  // Animation handling
  useEffect(() => {
    if (isOpen) {
      setIsAnimating(true);
    }
  }, [isOpen]);

  // Keyboard event handling
  useEffect(() => {
    if (!isOpen || !closeOnEscape) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown as any);
    return () => document.removeEventListener('keydown', handleKeyDown as any);
  }, [isOpen, closeOnEscape, onClose]);

  const handleOverlayClick = (e: MouseEvent<HTMLDivElement>) => {
    if (closeOnOverlayClick && e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleAnimationEnd = () => {
    if (!isOpen) {
      setIsAnimating(false);
    }
  };

  if (!isMounted || (!isOpen && !isAnimating)) {
    return null;
  }

  const modalContent = (
    <div
      className={cn(
        'fixed inset-0 z-50 flex items-center justify-center p-4',
        !centered && 'items-start pt-16',
        overlayClassName
      )}
      onClick={handleOverlayClick}
    >
      {/* Backdrop */}
      <div
        className={cn(
          'fixed inset-0 bg-black/50 backdrop-blur-sm',
          isOpen ? animationUtils.fadeIn : animationUtils.fadeOut
        )}
        style={{ animationDuration: `${animationDuration}ms` }}
        onAnimationEnd={handleAnimationEnd}
      />

      {/* Modal Content */}
      <div
        ref={containerRef}
        className={cn(
          'relative bg-white rounded-lg shadow-xl max-h-[calc(100vh-2rem)] overflow-hidden',
          'transform transition-all duration-200 ease-out',
          modalSizes[size],
          config.borderClass,
          isOpen ? animationUtils.modalEnter : animationUtils.modalExit,
          contentClassName,
          className
        )}
        style={{ animationDuration: `${animationDuration}ms` }}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? 'modal-title' : undefined}
        aria-describedby={description ? 'modal-description' : undefined}
      >
        {/* Header */}
        {(title || showCloseButton) && (
          <div className={cn(
            'flex items-center justify-between px-6 py-4 border-b border-gray-200',
            headerClassName
          )}>
            <div className="flex items-center gap-3">
              {VariantIcon && (
                <div className={cn(
                  'flex-shrink-0 w-6 h-6',
                  variant === 'danger' && 'text-red-600',
                  variant === 'warning' && 'text-yellow-600',
                  variant === 'success' && 'text-green-600',
                  variant === 'info' && 'text-blue-600'
                )}>
                  <VariantIcon className="w-6 h-6" />
                </div>
              )}
              <div>
                {title && (
                  <h2
                    id="modal-title"
                    className={cn(
                      'text-lg font-semibold text-gray-900',
                      config.headerClass
                    )}
                  >
                    {title}
                  </h2>
                )}
                {description && (
                  <p
                    id="modal-description"
                    className="text-sm text-gray-600 mt-1"
                  >
                    {description}
                  </p>
                )}
              </div>
            </div>

            {showCloseButton && (
              <button
                type="button"
                onClick={onClose}
                className="flex-shrink-0 p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                aria-label="Close modal"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        )}

        {/* Body */}
        <div className="px-6 py-4 overflow-y-auto max-h-[60vh]">
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div className={cn(
            'px-6 py-4 border-t border-gray-200 bg-gray-50',
            footerClassName
          )}>
            {footer}
          </div>
        )}
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}

// Confirmation Modal
export function ConfirmModal({
  isOpen,
  onClose,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  onConfirm,
  onCancel,
  isConfirming = false,
  destructive = false,
  variant = destructive ? 'danger' : 'default',
  size = 'sm',
  ...props
}: ConfirmModalProps) {
  const handleConfirm = async () => {
    try {
      await onConfirm();
      onClose();
    } catch (error) {
      // Error should be handled by the caller
      console.error('Confirmation action failed:', error);
    }
  };

  const handleCancel = () => {
    onCancel?.();
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      variant={variant}
      size={size}
      closeOnOverlayClick={!isConfirming}
      closeOnEscape={!isConfirming}
      {...props}
      footer={
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={handleCancel}
            disabled={isConfirming}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {cancelText}
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={isConfirming}
            className={cn(
              'px-4 py-2 text-sm font-medium text-white rounded-lg focus:ring-2 disabled:opacity-50',
              destructive
                ? 'bg-red-600 hover:bg-red-700 focus:ring-red-500'
                : 'bg-blue-600 hover:bg-blue-700 focus:ring-blue-500'
            )}
          >
            {isConfirming ? 'Processing...' : confirmText}
          </button>
        </div>
      }
    >
      <p className="text-gray-600">{message}</p>
    </Modal>
  );
}

// Alert Modal (simple notification modal)
export function AlertModal({
  isOpen,
  onClose,
  title,
  message,
  variant = 'info',
  buttonText = 'OK',
  ...props
}: {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  message: string;
  variant?: ModalVariant;
  buttonText?: string;
} & Omit<ModalProps, 'children' | 'footer'>) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      variant={variant}
      size="sm"
      {...props}
      footer={
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500"
          >
            {buttonText}
          </button>
        </div>
      }
    >
      <p className="text-gray-600">{message}</p>
    </Modal>
  );
}

// Form Modal (modal with form handling)
export function FormModal({
  isOpen,
  onClose,
  title,
  onSubmit,
  submitText = 'Save',
  isSubmitting = false,
  children,
  size = 'md',
  ...props
}: {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  onSubmit: (e: React.FormEvent) => void | Promise<void>;
  submitText?: string;
  isSubmitting?: boolean;
  children: ReactNode;
  size?: ModalSize;
} & Omit<ModalProps, 'children' | 'footer'>) {
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await onSubmit(e);
    } catch (error) {
      // Error handling should be done by the caller
      console.error('Form submission failed:', error);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      size={size}
      closeOnOverlayClick={!isSubmitting}
      closeOnEscape={!isSubmitting}
      {...props}
      footer={
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            form="modal-form"
            disabled={isSubmitting}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {isSubmitting ? 'Saving...' : submitText}
          </button>
        </div>
      }
    >
      <form id="modal-form" onSubmit={handleSubmit}>
        {children}
      </form>
    </Modal>
  );
}