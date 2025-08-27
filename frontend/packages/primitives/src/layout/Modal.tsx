/**
 * Refactored Modal component using composition pattern
 * Simplified interfaces for better testability
 */
'use client';

import { cva, type VariantProps } from 'class-variance-authority';
import { clsx } from 'clsx';
import React, { forwardRef, useCallback, useEffect, useState, useId } from 'react';

// Modal variants
const modalVariants = cva('modal-container', {
  variants: {
    size: {
      sm: 'modal-sm',
      md: 'modal-md',
      lg: 'modal-lg',
      xl: 'modal-xl',
      full: 'modal-full',
    },
    variant: {
      default: 'modal-default',
      centered: 'modal-centered',
      drawer: 'modal-drawer',
      sidebar: 'modal-sidebar',
    },
    state: {
      closed: 'modal-closed',
      opening: 'modal-opening',
      open: 'modal-open',
      closing: 'modal-closing',
    },
  },
  defaultVariants: {
    size: 'md',
    variant: 'default',
    state: 'closed',
  },
});

// Focus management utilities
export const ModalFocusUtils = {
  //  // Removed - can't use hooks in objects
  getFocusableElements: (container: HTMLElement): HTMLElement[] => {
    const focusableSelectors = [
      'button:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      'a[href]',
      '[tabindex]:not([tabindex="-1"])',
    ].join(',');

    return Array.from(container.querySelectorAll(focusableSelectors));
  },

  trapFocus: (container: HTMLElement, event: KeyboardEvent) => {
    if (event.key !== 'Tab') {
      return;
    }

    const focusableElements = ModalFocusUtils.getFocusableElements(container);
    if (focusableElements.length === 0) {
      return;
    }

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    if (event.shiftKey && document.activeElement === firstElement) {
      event.preventDefault();
      lastElement.focus();
    } else if (!event.shiftKey && document.activeElement === lastElement) {
      event.preventDefault();
      firstElement.focus();
    }
  },

  setInitialFocus: (container: HTMLElement) => {
    const focusableElements = ModalFocusUtils.getFocusableElements(container);
    if (focusableElements.length > 0) {
      focusableElements[0].focus();
    } else {
      container.focus();
    }
  },
};

// Modal state management hook
export const useModalState = (defaultOpen = false, onOpenChange?: (open: boolean) => void) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [previousFocus, setPreviousFocus] = useState<HTMLElement | null>(null);

  const open = useCallback(() => {
    setPreviousFocus(document.activeElement as HTMLElement);
    setIsOpen(true);
    onOpenChange?.(true);
  }, [onOpenChange]);

  const close = useCallback(() => {
    setIsOpen(false);
    onOpenChange?.(false);
    // Restore focus after a brief delay to allow for transitions
    setTimeout(() => {
      previousFocus?.focus();
    }, 100);
  }, [onOpenChange, previousFocus]);

  const toggle = useCallback(() => {
    if (isOpen) {
      close();
    } else {
      open();
    }
  }, [isOpen, open, close]);

  return {
    isOpen,
    open,
    close,
    toggle,
  };
};

// Modal backdrop component
export interface ModalBackdropProps extends React.HTMLAttributes<HTMLDivElement> {
  onClick?: () => void;
  closeOnClick?: boolean;
}

export const ModalBackdrop = forwardRef<HTMLDivElement, ModalBackdropProps>(
  ({ className, onClick, closeOnClick = true, ...props }, ref) => {
    const id = useId();
    const handleClick = useCallback(
      (e: React.MouseEvent) => {
        if (closeOnClick && e.target === e.currentTarget) {
          onClick?.();
        }
      },
      [closeOnClick, onClick]
    );

    return (
      <div
        ref={ref}
        className={clsx('modal-backdrop', className)}
        onClick={handleClick}
        onKeyDown={(e) => e.key === 'Enter' && handleClick}
        data-testid={`${id}-modal-backdrop`}
        {...props}
      />
    );
  }
);

// Modal content container
export interface ModalContentProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof modalVariants> {
  showClose?: boolean;
  closeOnEscape?: boolean;
  trapFocus?: boolean;
  onClose?: () => void;
}

export const ModalContent = forwardRef<HTMLDivElement, ModalContentProps>(
  (
    {
      className,
      children,
      size,
      variant,
      showClose = true,
      closeOnEscape = true,
      trapFocus = true,
      onClose,
      ...props
    },
    ref
  ) => {
    const id = useId();
    const contentRef = React.useRef<HTMLDivElement>(null);
    const combinedRef = (ref as React.RefObject<HTMLDivElement>) || contentRef;

    useEffect(() => {
      const container = combinedRef.current;
      if (!container) {
        return;
      }

      // Set initial focus
      ModalFocusUtils.setInitialFocus(container);

      const handleKeyDown = (e: KeyboardEvent) => {
        if (closeOnEscape && e.key === 'Escape') {
          e.preventDefault();
          onClose?.();
          return;
        }

        if (trapFocus) {
          ModalFocusUtils.trapFocus(container, e);
        }
      };

      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }, [closeOnEscape, trapFocus, onClose, combinedRef]);

    return (
      <div
        ref={combinedRef}
        className={clsx(modalVariants({ size, variant }), 'modal-content', className)}
        role='dialog'
        aria-modal='true'
        tabIndex={-1}
        data-testid={`${id}-modal-content`}
        {...props}
      >
        {children}

        {showClose && (
          <button
            type='button'
            className='modal-close'
            onClick={onClose}
            onKeyDown={(e) => e.key === 'Enter' && onClose}
            aria-label='Close modal'
            data-testid={`${id}-modal-close`}
          >
            <span aria-hidden='true'>×</span>
          </button>
        )}
      </div>
    );
  }
);

// Modal header component
export interface ModalHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  as?: keyof JSX.IntrinsicElements;
}

export const ModalHeader = forwardRef<HTMLDivElement, ModalHeaderProps>(
  ({ className, as: Component = 'div', children, ...props }, ref) => {
    return (
      <Component ref={ref} className={clsx('modal-header', className)} {...props}>
        {children}
      </Component>
    );
  }
);

// Modal title component
export interface ModalTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
}

export const ModalTitle = forwardRef<HTMLHeadingElement, ModalTitleProps>(
  ({ className, as: Component = 'h2', children, ...props }, ref) => {
    const id = useId();
    return (
      <Component
        ref={ref}
        className={clsx('modal-title', className)}
        data-testid={`${id}-modal-title`}
        {...props}
      >
        {children}
      </Component>
    );
  }
);

// Modal description component
export const ModalDescription = forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, children, ...props }, ref) => {
  const id = useId();
  return (
    <p
      ref={ref}
      className={clsx('modal-description', className)}
      data-testid={`${id}-modal-description`}
      {...props}
    >
      {children}
    </p>
  );
});

// Modal body component
export const ModalBody = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => {
    const id = useId();
    return (
      <div
        ref={ref}
        className={clsx('modal-body', className)}
        data-testid={`${id}-modal-body`}
        {...props}
      >
        {children}
      </div>
    );
  }
);

// Modal footer component
export const ModalFooter = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => {
    const id = useId();
    return (
      <div
        ref={ref}
        className={clsx('modal-footer', className)}
        data-testid={`${id}-modal-footer`}
        {...props}
      >
        {children}
      </div>
    );
  }
);

// Modal trigger component
export interface ModalTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean;
}

export const ModalTrigger = forwardRef<HTMLButtonElement, ModalTriggerProps>(
  ({ className, children, onClick, asChild = false, ...props }, ref) => {
    const id = useId();
    if (asChild && React.isValidElement(children)) {
      return React.cloneElement(children, {
        ...children.props,
        onClick: (e: React.MouseEvent) => {
          children.props.onClick?.(e);
          onClick?.(e);
        },
      });
    }

    return (
      <button
        type='button'
        ref={ref}
        className={clsx('modal-trigger', className)}
        onClick={onClick}
        onKeyDown={(e) => e.key === 'Enter' && onClick}
        data-testid={`${id}-modal-trigger`}
        {...props}
      >
        {children}
      </button>
    );
  }
);

// Main Modal component using composition
export interface ModalProps {
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  children: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({
  open: controlledOpen,
  defaultOpen = false,
  onOpenChange,
  children,
}) => {
  const id = useId();
  const { isOpen: uncontrolledOpen, open, close } = useModalState(defaultOpen, onOpenChange);

  // Use controlled state if provided, otherwise use internal state
  const isOpen = controlledOpen !== undefined ? controlledOpen : uncontrolledOpen;

  const handleOpenChange = useCallback(
    (newOpen: boolean) => {
      if (controlledOpen === undefined) {
        // Uncontrolled mode
        if (newOpen) {
          open();
        } else {
          close();
        }
      } else {
        // Controlled mode
        onOpenChange?.(newOpen);
      }
    },
    [controlledOpen, onOpenChange, open]
  );

  useEffect(() => {
    const handleBodyScroll = () => {
      document.body.style.overflow = isOpen ? 'hidden' : '';
    };

    handleBodyScroll();
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) {
    return null;
  }

  const childrenWithProps = React.Children.map(children, (child) => {
    if (React.isValidElement(child)) {
      // Pass close function to interactive components
      if (child.type === ModalTrigger) {
        return React.cloneElement(child, {
          ...child.props,
          onClick: (e: React.MouseEvent) => {
            child.props.onClick?.(e);
            handleOpenChange(!isOpen);
          },
        });
      }

      if (child.type === ModalContent || child.type === ModalBackdrop) {
        return React.cloneElement(child, {
          ...child.props,
          onClose: () => handleOpenChange(false),
          onClick:
            child.type === ModalBackdrop ? () => handleOpenChange(false) : child.props.onClick,
        });
      }
    }
    return child;
  });

  return (
    <div className='modal-portal' data-testid={`${id}-modal-portal`}>
      {childrenWithProps}
    </div>
  );
};

// Export display names
ModalBackdrop.displayName = 'ModalBackdrop';
ModalContent.displayName = 'ModalContent';
ModalHeader.displayName = 'ModalHeader';
ModalTitle.displayName = 'ModalTitle';
ModalDescription.displayName = 'ModalDescription';
ModalBody.displayName = 'ModalBody';
ModalFooter.displayName = 'ModalFooter';
ModalTrigger.displayName = 'ModalTrigger';
Modal.displayName = 'Modal';
