/**
 * Advanced notification system with toast notifications, alerts, and notification center
 */

import { cva, type VariantProps } from 'class-variance-authority';
import { clsx } from 'clsx';
import type React from 'react';
import { createContext, forwardRef, useCallback, useContext, useEffect, useState } from 'react';

// Notification types
export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message?: string;
  duration?: number; // in milliseconds, 0 for persistent
  actions?: NotificationAction[];
  dismissible?: boolean;
  icon?: React.ReactNode;
  metadata?: Record<string, unknown>;
  timestamp: Date;
  read?: boolean;
  persistent?: boolean;
}

export interface NotificationAction {
  label: string;
  action: () => void;
  variant?: 'primary' | 'secondary' | 'destructive';
}

// Toast notification variants
const toastVariants = cva('toast-notification', {
  variants: {
    type: {
      info: 'toast-info',
      success: 'toast-success',
      warning: 'toast-warning',
      error: 'toast-error',
    },
    position: {
      'top-right': 'position-top-right',
      'top-left': 'position-top-left',
      'top-center': 'position-top-center',
      'bottom-right': 'position-bottom-right',
      'bottom-left': 'position-bottom-left',
      'bottom-center': 'position-bottom-center',
    },
    size: {
      sm: 'toast-sm',
      md: 'toast-md',
      lg: 'toast-lg',
    },
  },
  defaultVariants: {
    type: 'info',
    position: 'top-right',
    size: 'md',
  },
});

// Notification context
interface NotificationContextType {
  notifications: Notification[];
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => string;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  getUnreadCount: () => number;
}

const NotificationContext = createContext<NotificationContextType | null>(null);

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
}

// Notification provider
interface NotificationProviderProps {
  children: React.ReactNode;
  maxNotifications?: number;
  defaultDuration?: number;
}

export function NotificationProvider({
  children,
  maxNotifications = 100,
  defaultDuration = 5000,
}: NotificationProviderProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const generateId = () => Math.random().toString(36).substr(2, 9);

  const addNotification = useCallback(
    (notification: Omit<Notification, 'id' | 'timestamp'>) => {
      const id = generateId();
      const newNotification: Notification = {
        ...notification,
        id,
        timestamp: new Date(),
        duration: notification.duration ?? defaultDuration,
        dismissible: notification.dismissible ?? true,
        read: false,
      };

      setNotifications((prev) => {
        const updated = [newNotification, ...prev];
        return updated.slice(0, maxNotifications);
      });

      // Auto-dismiss if duration is set
      if (newNotification.duration && newNotification.duration > 0) {
        setTimeout(() => {
          removeNotification(id);
        }, newNotification.duration);
      }

      return id;
    },
    [defaultDuration, maxNotifications, removeNotification, generateId]
  );

  const removeNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  const markAsRead = useCallback((id: string) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  const getUnreadCount = useCallback(() => {
    return notifications.filter((n) => !n.read).length;
  }, [notifications]);

  const value: NotificationContextType = {
    notifications,
    addNotification,
    removeNotification,
    clearNotifications,
    markAsRead,
    markAllAsRead,
    getUnreadCount,
  };

  return <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>;
}

// Toast notification component
interface ToastNotificationProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof toastVariants> {
  notification: Notification;
  onDismiss?: () => void;
  showTimestamp?: boolean;
}

const ToastNotification = forwardRef<HTMLDivElement, ToastNotificationProps>(
  (
    { notification, onDismiss, showTimestamp = false, _type, position, size, className, ...props },
    ref
  ) => {
    const [isVisible, setIsVisible] = useState(false);
    const [isExiting, setIsExiting] = useState(false);

    useEffect(() => {
      // Entrance animation
      const timer = setTimeout(() => setIsVisible(true), 10);
      return () => clearTimeout(timer);
    }, []);

    const handleDismiss = () => {
      if (!notification.dismissible) {
        return;
      }

      setIsExiting(true);
      setTimeout(() => {
        onDismiss?.();
      }, 300); // Animation duration
    };

    const getIcon = () => {
      if (notification.icon) {
        return notification.icon;
      }

      switch (notification.type) {
        case 'success':
          return '✅';
        case 'warning':
          return '⚠️';
        case 'error':
          return '❌';
        default:
          return 'ℹ️';
      }
    };

    const formatTimestamp = (date: Date) => {
      const now = new Date();
      const diff = now.getTime() - date.getTime();
      const minutes = Math.floor(diff / 60000);

      if (minutes < 1) {
        return 'Just now';
      }
      if (minutes < 60) {
        return `${minutes}m ago`;
      }
      const hours = Math.floor(minutes / 60);
      if (hours < 24) {
        return `${hours}h ago`;
      }
      return date.toLocaleDateString();
    };

    return (
      <div
        ref={ref}
        className={clsx(
          toastVariants({ type: notification.type, position, size }),
          {
            'toast-visible': isVisible,
            'toast-exiting': isExiting,
          },
          className
        )}
        {...props}
      >
        <div className='toast-content'>
          <div className='toast-icon'>{getIcon()}</div>

          <div className='toast-body'>
            <div className='toast-title'>{notification.title}</div>
            {notification.message ? (
              <div className='toast-message'>{notification.message}</div>
            ) : null}

            {showTimestamp ? (
              <div className='toast-timestamp'>{formatTimestamp(notification.timestamp)}</div>
            ) : null}

            {notification.actions && notification.actions.length > 0 ? (
              <div className='toast-actions'>
                {notification.actions.map((action, index) => (
                  <button
                    type='button'
                    key={`item-${index}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      action.action();
                    }}
                    className={clsx('toast-action-button', action.variant)}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            ) : null}
          </div>

          {notification.dismissible ? (
            <button
              type='button'
              onClick={handleDismiss} onKeyDown={(e) => e.key === "Enter" && handleDismiss}
              className='toast-dismiss'
              aria-label='Dismiss notification'
            >
              ✕
            </button>
          ) : null}
        </div>

        {notification.duration && notification.duration > 0 ? (
          <div className='toast-progress'>
            <div
              className='toast-progress-bar'
              style={{
                animation: `toast-progress ${notification.duration}ms linear`,
              }}
            />
          </div>
        ) : null}
      </div>
    );
  }
);

// Toast container component
interface ToastContainerProps {
  position?:
    | 'top-right'
    | 'top-left'
    | 'top-center'
    | 'bottom-right'
    | 'bottom-left'
    | 'bottom-center';
  maxVisible?: number;
  spacing?: number;
}

export function ToastContainer({
  position = 'top-right',
  maxVisible = 5,
  spacing = 8,
}: ToastContainerProps) {
  const { notifications, _removeNotification } = useNotifications();

  // Only show toast notifications (non-persistent)
  const toastNotifications = notifications.filter((n) => !n.persistent).slice(0, maxVisible);

  if (toastNotifications.length === 0) {
    return null;
  }

  return (
    <div
      className={clsx('toast-container', `position-${position}`)}
      style={{ gap: `${spacing}px` }}
    >
      {toastNotifications.map((notification, index) => (
        <ToastNotification
          key={notification.id}
          notification={notification}
          position={position}
          onDismiss={() => removeNotification(notification.id)}
          style={{
            zIndex: 1000 - index,
          }}
        />
      ))}
    </div>
  );
}

// Notification center component
interface NotificationCenterProps extends React.HTMLAttributes<HTMLDivElement> {
  maxHeight?: number;
  showFilters?: boolean;
  onNotificationClick?: (notification: Notification) => void;
}

export const NotificationCenter = forwardRef<HTMLDivElement, NotificationCenterProps>(
  ({ className, maxHeight = 400, showFilters = true, onNotificationClick, ...props }, _ref) => {
    const {
      notifications,
      removeNotification,
      clearNotifications,
      markAsRead,
      markAllAsRead,
      getUnreadCount,
    } = useNotifications();

    const [filter, setFilter] = useState<'all' | 'unread'>('all');
    const [typeFilter, setTypeFilter] = useState<'all' | Notification['type']>('all');

    const filteredNotifications = notifications.filter((n) => {
      if (filter === 'unread' && n.read) {
        return false;
      }
      if (typeFilter !== 'all' && n.type !== typeFilter) {
        return false;
      }
      return true;
    });

    const _HandleNotificationClick = (notification: Notification) => {
      if (!notification.read) {
        markAsRead(notification.id);
      }
      onNotificationClick?.(notification);
    };

    const formatTime = (date: Date) => {
      return date.toLocaleString();
    };

    const getIcon = (type: Notification['type']) => {
      switch (type) {
        case 'success':
          return '✅';
        case 'warning':
          return '⚠️';
        case 'error':
          return '❌';
        default:
          return 'ℹ️';
      }
    };

    return (
      <div ref={ref} className={clsx('notification-center', className)} {...props}>
        <div className='notification-center-header'>
          <h3 className='notification-center-title'>
            Notifications
            {getUnreadCount() > 0 && <span className='unread-badge'>{getUnreadCount()}</span>}
          </h3>

          <div className='notification-center-actions'>
            {getUnreadCount() > 0 && (
              <button type='button' onClick={markAllAsRead} onKeyDown={(e) => e.key === "Enter" && markAllAsRead} className='action-button'>
                Mark all read
              </button>
            )}
            <button type='button' onClick={clearNotifications} onKeyDown={(e) => e.key === "Enter" && clearNotifications} className='action-button'>
              Clear all
            </button>
          </div>
        </div>

        {showFilters ? (
          <div className='notification-filters'>
            <div className='filter-group'>
              <button
                type='button'
                onClick={() => setFilter('all')}
                className={clsx('filter-button', { active: filter === 'all' })}
              >
                All ({notifications.length})
              </button>
              <button
                type='button'
                onClick={() => setFilter('unread')}
                className={clsx('filter-button', { active: filter === 'unread' })}
              >
                Unread ({getUnreadCount()})
              </button>
            </div>

            <div className='filter-group'>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value as unknown)}
                className='type-filter'
              >
                <option value='all'>All types</option>
                <option value='info'>Info</option>
                <option value='success'>Success</option>
                <option value='warning'>Warning</option>
                <option value='error'>Error</option>
              </select>
            </div>
          </div>
        ) : null}

        <div className='notification-list' style={{ maxHeight: `${maxHeight}px` }}>
          {filteredNotifications.length === 0 ? (
            <div className='empty-notifications'>
              <span className='empty-icon'>🔔</span>
              <span>No notifications</span>
            </div>
          ) : (
            filteredNotifications.map((notification) => (
              <div
                key={notification.id}
                className={clsx('notification-item', {
                  unread: !notification.read,
                  [`type-${notification.type}`]: true,
                })}
                onClick={() => HandleNotificationClick(notification)}
                onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.click()}
                role="button"
                tabIndex={0}
              >
                <div className='notification-icon'>
                  {notification.icon || getIcon(notification.type)}
                </div>

                <div className='notification-content'>
                  <div className='notification-title'>
                    {notification.title}
                    {!notification.read && <span className='unread-dot' />}
                  </div>

                  {notification.message ? (
                    <div className='notification-message'>{notification.message}</div>
                  ) : null}

                  <div className='notification-meta'>
                    <span className='notification-time'>{formatTime(notification.timestamp)}</span>
                    <span className={clsx('notification-type', `type-${notification.type}`)}>
                      {notification.type}
                    </span>
                  </div>

                  {notification.actions && notification.actions.length > 0 ? (
                    <div className='notification-actions'>
                      {notification.actions.map((action, index) => (
                        <button
                          type='button'
                          key={`item-${index}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            action.action();
                          }}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.stopPropagation();
                              action.action();
                            }
                          }}
                          className={clsx('notification-action-button', action.variant)}
                        >
                          {action.label}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>

                <button
                  type='button'
                  onClick={(e) => {
                    e.stopPropagation();
                    removeNotification(notification.id);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.stopPropagation();
                      removeNotification(notification.id);
                    }
                  }}
                  className='notification-remove'
                  aria-label='Remove notification'
                >
                  ✕
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    );
  }
);

// Notification bell icon component
interface NotificationBellProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  size?: 'sm' | 'md' | 'lg';
  showCount?: boolean;
  maxCount?: number;
}

export const NotificationBell = forwardRef<HTMLButtonElement, NotificationBellProps>(
  ({ className, size = 'md', showCount = true, maxCount = 99, ...props }, _ref) => {
    const { getUnreadCount } = useNotifications();
    const unreadCount = getUnreadCount();

    return (
      <button
        type='button'
        ref={ref}
        className={clsx('notification-bell', `size-${size}`, className)}
        {...props}
      >
        <span className='bell-icon'>🔔</span>
        {showCount && unreadCount > 0 ? (
          <span className='notification-count'>
            {unreadCount > maxCount ? `${maxCount}+` : unreadCount}
          </span>
        ) : null}
      </button>
    );
  }
);

// Hook for easier toast creation
export function useToast() {
  const { addNotification } = useNotifications();

  const toast = useCallback(
    (
      type: Notification['type'],
      title: string,
      message?: string,
      options?: Partial<Omit<Notification, 'id' | 'timestamp' | 'type' | 'title' | 'message'>>
    ) => {
      return addNotification({
        type,
        title,
        message,
        ...options,
      });
    },
    [addNotification]
  );

  return {
    success: (title: string, message?: string, options?: unknown) =>
      toast('success', title, message, options),
    error: (title: string, message?: string, options?: unknown) =>
      toast('error', title, message, options),
    warning: (title: string, message?: string, options?: unknown) =>
      toast('warning', title, message, options),
    info: (title: string, message?: string, options?: unknown) =>
      toast('info', title, message, options),
    custom: toast,
  };
}

ToastNotification.displayName = 'ToastNotification';
NotificationCenter.displayName = 'NotificationCenter';
NotificationBell.displayName = 'NotificationBell';

export { ToastNotification };
