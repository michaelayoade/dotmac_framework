/**
 * Notifications Section - Decomposed from CustomerDashboard
 */
import { Bell, AlertCircle, Info, CheckCircle } from 'lucide-react';
import React from 'react';

interface Notification {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  timestamp: string;
  action?: {
    label: string;
    url?: string;
    onClick?: () => void;
  };
}

interface NotificationsSectionProps {
  notifications: Notification[];
  onDismiss?: (notificationId: string) => void;
  onViewAll?: () => void;
  className?: string;
}

const notificationConfig = {
  info: {
    icon: Info,
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    iconColor: 'text-blue-600',
    titleColor: 'text-blue-900'
  },
  warning: {
    icon: AlertCircle,
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    iconColor: 'text-yellow-600',
    titleColor: 'text-yellow-900'
  },
  error: {
    icon: AlertCircle,
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    iconColor: 'text-red-600',
    titleColor: 'text-red-900'
  },
  success: {
    icon: CheckCircle,
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    iconColor: 'text-green-600',
    titleColor: 'text-green-900'
  }
};

export function NotificationsSection({
  notifications,
  onDismiss,
  onViewAll,
  className = ''
}: NotificationsSectionProps) {
  if (notifications.length === 0) {
    return (
      <div className={`bg-white border border-gray-200 rounded-lg p-6 ${className}`}>
        <div className="text-center">
          <Bell className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="font-medium text-gray-900 mb-2">No notifications</h3>
          <p className="text-gray-500 text-sm">You're all caught up!</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white border border-gray-200 rounded-lg ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <Bell className="h-5 w-5 text-gray-600 mr-2" />
            <h3 className="font-semibold text-gray-900">Recent Notifications</h3>
          </div>
          {onViewAll && notifications.length > 3 && (
            <button
              onClick={onViewAll}
              className="text-sm font-medium text-blue-600 hover:text-blue-500"
            >
              View All
            </button>
          )}
        </div>
      </div>

      {/* Notifications List */}
      <div className="divide-y divide-gray-200">
        {notifications.slice(0, 5).map((notification) => {
          const config = notificationConfig[notification.type];
          const Icon = config.icon;

          return (
            <div key={notification.id} className="p-4">
              <div className={`p-4 rounded-lg ${config.bgColor} ${config.borderColor} border`}>
                <div className="flex items-start">
                  <Icon className={`h-5 w-5 ${config.iconColor} mt-0.5 flex-shrink-0`} />
                  
                  <div className="ml-3 flex-1">
                    <div className="flex items-center justify-between">
                      <h4 className={`font-medium ${config.titleColor}`}>
                        {notification.title}
                      </h4>
                      {onDismiss && (
                        <button
                          onClick={() => onDismiss(notification.id)}
                          className="text-gray-400 hover:text-gray-600 ml-2"
                        >
                          ×
                        </button>
                      )}
                    </div>
                    
                    <p className="text-sm text-gray-600 mt-1">
                      {notification.message}
                    </p>
                    
                    <div className="flex items-center justify-between mt-3">
                      <span className="text-xs text-gray-500">
                        {new Date(notification.timestamp).toLocaleString()}
                      </span>
                      
                      {notification.action && (
                        <button
                          onClick={notification.action.onClick}
                          className="text-sm font-medium text-blue-600 hover:text-blue-500"
                        >
                          {notification.action.label}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      {notifications.length > 5 && (
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
          <p className="text-sm text-gray-500 text-center">
            {notifications.length - 5} more notifications...
          </p>
        </div>
      )}
    </div>
  );
}