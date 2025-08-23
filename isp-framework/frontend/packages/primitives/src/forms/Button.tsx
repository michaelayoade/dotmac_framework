/**
 * Button Primitive Component
 *
 * Enhanced base button component with comprehensive TypeScript support,
 * accessibility features, loading states, and security considerations
 */

import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { clsx } from 'clsx';
import * as React from 'react';
import { Loader2 } from 'lucide-react';

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground shadow hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90',
        outline:
          'border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground',
        secondary: 'bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-9 px-4 py-2',
        sm: 'h-8 rounded-md px-3 text-xs',
        lg: 'h-10 rounded-md px-8',
        icon: 'h-9 w-9',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  /** Whether the button is in a loading state */
  isLoading?: boolean;
  /** Custom loading component */
  loadingComponent?: React.ReactNode;
  /** Icon to display on the left */
  leftIcon?: React.ReactNode;
  /** Icon to display on the right */
  rightIcon?: React.ReactNode;
  /** Whether to prevent form submission */
  preventFormSubmission?: boolean;
  /** Custom click handler with security considerations */
  onSecureClick?: (event: React.MouseEvent<HTMLButtonElement>) => void | Promise<void>;
  /** Whether to show loading state during async operations */
  showAsyncLoading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      asChild = false,
      isLoading = false,
      loadingComponent,
      leftIcon,
      rightIcon,
      preventFormSubmission = false,
      onSecureClick,
      showAsyncLoading = true,
      disabled,
      onClick,
      type = 'button',
      children,
      ...props
    },
    ref
  ) => {
    const [isAsyncLoading, setIsAsyncLoading] = React.useState(false);
    const Comp = asChild ? Slot : 'button';

    // Determine if button should be disabled
    const isButtonDisabled = disabled || isLoading || isAsyncLoading;

    // Handle click with security and async considerations
    const handleClick = React.useCallback(
      async (event: React.MouseEvent<HTMLButtonElement>) => {
        // Prevent form submission if requested
        if (preventFormSubmission) {
          event.preventDefault();
        }

        // Handle secure click if provided
        if (onSecureClick) {
          if (showAsyncLoading) {
            setIsAsyncLoading(true);
          }

          try {
            await onSecureClick(event);
          } catch (error) {
            console.error('Secure click handler error:', error);
          } finally {
            if (showAsyncLoading) {
              setIsAsyncLoading(false);
            }
          }
          return;
        }

        // Standard click handler
        if (onClick) {
          if (showAsyncLoading) {
            setIsAsyncLoading(true);
            try {
              const result = onClick(event);
              // Handle potential promise
              if (result && typeof result.then === 'function') {
                await result;
              }
            } catch (error) {
              console.error('Click handler error:', error);
            } finally {
              setIsAsyncLoading(false);
            }
          } else {
            onClick(event);
          }
        }
      },
      [onClick, onSecureClick, preventFormSubmission, showAsyncLoading]
    );

    // Determine what to show inside button
    const showLoading = isLoading || isAsyncLoading;
    const LoadingIcon = loadingComponent || <Loader2 className='mr-2 h-4 w-4 animate-spin' />;

    // When using asChild, pass only children to avoid Slot conflicts
    if (asChild) {
      return (
        <Comp
          className={clsx(buttonVariants({ variant, size, className }))}
          ref={ref}
          disabled={disabled} // Don't modify disabled when asChild
          type={type}
          onClick={onClick} // Use original onClick when asChild
          aria-disabled={disabled ? 'true' : undefined}
          {...props}
        >
          {children}
        </Comp>
      );
    }

    return (
      <Comp
        className={clsx(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={isButtonDisabled}
        type={type}
        onClick={handleClick}
        aria-disabled={isButtonDisabled ? 'true' : undefined}
        {...props}
      >
        {showLoading && LoadingIcon}
        {leftIcon && !showLoading && <span className='mr-2 flex items-center'>{leftIcon}</span>}
        {children}
        {rightIcon && !showLoading && <span className='ml-2 flex items-center'>{rightIcon}</span>}
      </Comp>
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
