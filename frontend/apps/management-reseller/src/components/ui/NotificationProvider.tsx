'use client';

import { useEffect } from 'react';
import { Toaster } from 'sonner';
import { useNotifications, useUIActions } from '@/store';

export function NotificationProvider() {
  const notifications = useNotifications();
  const { removeNotification } = useUIActions();

  // Handle notifications with Sonner
  useEffect(() => {
    notifications.forEach((notification) => {
      // Only show if not already shown (prevent duplicates)
      if (!notification.id.startsWith('shown-')) {
        const { toast } = require('sonner');
        
        const toastOptions = {
          id: notification.id,
          duration: notification.duration || 5000,
          action: notification.action ? {
            label: notification.action.label,
            onClick: notification.action.onClick,
          } : undefined,
          onDismiss: () => removeNotification(notification.id),
        };

        switch (notification.type) {
          case 'success':
            toast.success(notification.title, {
              description: notification.message,
              ...toastOptions,
            });
            break;
          case 'error':
            toast.error(notification.title, {
              description: notification.message,
              ...toastOptions,
            });
            break;
          case 'warning':
            toast.warning(notification.title, {
              description: notification.message,
              ...toastOptions,
            });
            break;
          case 'info':
          default:
            toast.info(notification.title, {
              description: notification.message,
              ...toastOptions,
            });
            break;
        }

        // Mark as shown to prevent duplicates
        notification.id = `shown-${notification.id}`;
      }
    });
  }, [notifications, removeNotification]);

  return (
    <Toaster
      position="top-right"
      closeButton
      richColors
      expand
      visibleToasts={5}
      toastOptions={{
        duration: 5000,
        className: 'management-toast',
        style: {
          background: 'white',
          border: '1px solid #e5e7eb',
          color: '#374151',
        },
      }}
    />
  );
}