/**
 * Simple Modal Component
 * Basic modal implementation for plugin UI
 */

import React, { useEffect } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  children: React.ReactNode;
  showCloseButton?: boolean;
  closeOnOverlayClick?: boolean;
  closeOnEscape?: boolean;
  className?: string;
}

const sizeStyles = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
  full: 'max-w-7xl',
};

export function Modal({
  isOpen,
  onClose,
  title,
  description,
  size = 'md',
  children,
  showCloseButton = true,
  closeOnOverlayClick = true,
  closeOnEscape = true,
  className = '',
}: ModalProps) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (closeOnEscape && event.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, closeOnEscape, onClose]);

  if (!isOpen) return null;

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (closeOnOverlayClick && e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className='fixed inset-0 z-50 overflow-y-auto'>
      {/* Backdrop */}
      <div
        className='fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity'
        onClick={handleOverlayClick}
        aria-hidden='true'
      />

      {/* Modal Container */}
      <div className='flex min-h-full items-center justify-center p-4 text-center sm:p-0'>
        <div
          className={`
            relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl
            transition-all w-full ${sizeStyles[size]} ${className}
          `}
        >
          {/* Header */}
          <div className='bg-white px-4 pb-4 pt-5 sm:p-6 sm:pb-4'>
            <div className='flex items-start justify-between'>
              <div className='flex-1'>
                {title && (
                  <h3 className='text-lg font-semibold leading-6 text-gray-900'>{title}</h3>
                )}
                {description && <p className='mt-1 text-sm text-gray-500'>{description}</p>}
              </div>

              {showCloseButton && (
                <button
                  type='button'
                  className='rounded-md bg-white text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2'
                  onClick={onClose}
                  aria-label='Close modal'
                >
                  <XMarkIcon className='h-6 w-6' />
                </button>
              )}
            </div>
          </div>

          {/* Content */}
          <div className='bg-white px-4 pb-4 sm:p-6'>{children}</div>
        </div>
      </div>
    </div>
  );
}

export interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'info';
  loading?: boolean;
}

export function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'danger',
  loading = false,
}: ConfirmModalProps) {
  const iconColor = {
    danger: 'text-red-600',
    warning: 'text-yellow-600',
    info: 'text-blue-600',
  };

  const buttonVariant = {
    danger: 'danger',
    warning: 'danger',
    info: 'primary',
  } as const;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size='sm'
      closeOnOverlayClick={!loading}
      closeOnEscape={!loading}
    >
      <div className='sm:flex sm:items-start'>
        <div
          className={`mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-${variant}-100 sm:mx-0 sm:h-10 sm:w-10`}
        >
          <svg
            className={`h-6 w-6 ${iconColor[variant]}`}
            fill='none'
            viewBox='0 0 24 24'
            strokeWidth='1.5'
            stroke='currentColor'
          >
            <path
              strokeLinecap='round'
              strokeLinejoin='round'
              d='M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z'
            />
          </svg>
        </div>

        <div className='mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left'>
          <h3 className='text-base font-semibold leading-6 text-gray-900'>{title}</h3>
          <div className='mt-2'>
            <p className='text-sm text-gray-500'>{message}</p>
          </div>
        </div>
      </div>

      <div className='mt-5 sm:mt-4 sm:flex sm:flex-row-reverse'>
        <button
          type='button'
          className={`inline-flex w-full justify-center rounded-md px-3 py-2 text-sm font-semibold text-white shadow-sm sm:ml-3 sm:w-auto
            ${
              variant === 'danger'
                ? 'bg-red-600 hover:bg-red-500'
                : variant === 'warning'
                  ? 'bg-yellow-600 hover:bg-yellow-500'
                  : 'bg-blue-600 hover:bg-blue-500'
            }
          `}
          onClick={onConfirm}
          disabled={loading}
        >
          {loading ? 'Processing...' : confirmText}
        </button>
        <button
          type='button'
          className='mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:mt-0 sm:w-auto'
          onClick={onClose}
          disabled={loading}
        >
          {cancelText}
        </button>
      </div>
    </Modal>
  );
}
