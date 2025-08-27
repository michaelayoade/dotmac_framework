/**
 * Notification System
 * In-app notifications with different types and management
 */

'use client';

import React, { 
  useState, 
  useEffect, 
  useCallback, 
  createContext, 
  useContext, 
  ReactNode 
} from 'react';
import { 
  Bell,
  Check,
  X,
  AlertTriangle,
  Info,
  MessageSquare,
  User,
  Settings,
  Calendar,
  DollarSign,
  TrendingUp,
  Mail,
  Filter,
  Search,
  MoreVertical
} from 'lucide-react';
import { cn } from '../../design-system/utils';
import { formatDistanceToNow } from 'date-fns';

// Types
export type NotificationType = 
  | 'info' 
  | 'success' 
  | 'warning' 
  | 'error' 
  | 'message'
  | 'user'
  | 'system'
  | 'billing'
  | 'analytics';

export type NotificationPriority = 'low' | 'medium' | 'high' | 'urgent';

export interface Notification {
  id: string;
  type: NotificationType;
  priority: NotificationPriority;
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  archived: boolean;
  actionUrl?: string;
  actionLabel?: string;
  metadata?: Record<string, any>;
  avatar?: string;
  groupId?: string;
}

interface NotificationContextValue {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read' | 'archived'>) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  archiveNotification: (id: string) => void;
  deleteNotification: (id: string) => void;
  clearAll: () => void;
}

// Context
const NotificationContext = createContext<NotificationContextValue | undefined>(undefined);

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
}

// Notification Icon Component
function NotificationIcon({ type, className = '' }: { type: NotificationType; className?: string }) {
  const iconMap = {
    info: Info,
    success: Check,
    warning: AlertTriangle,
    error: AlertTriangle,
    message: MessageSquare,
    user: User,
    system: Settings,
    billing: DollarSign,
    analytics: TrendingUp,
  };

  const Icon = iconMap[type] || Info;
  
  const colorMap = {
    info: 'text-blue-500',
    success: 'text-green-500',
    warning: 'text-yellow-500',
    error: 'text-red-500',
    message: 'text-purple-500',
    user: 'text-indigo-500',
    system: 'text-gray-500',
    billing: 'text-emerald-500',
    analytics: 'text-orange-500',
  };

  return (
    <div className={cn(
      'flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center',
      type === 'success' && 'bg-green-100',
      type === 'error' && 'bg-red-100',
      type === 'warning' && 'bg-yellow-100',
      type === 'info' && 'bg-blue-100',
      type === 'message' && 'bg-purple-100',
      type === 'user' && 'bg-indigo-100',
      type === 'system' && 'bg-gray-100',
      type === 'billing' && 'bg-emerald-100',
      type === 'analytics' && 'bg-orange-100',
      className
    )}>
      <Icon className={cn('w-5 h-5', colorMap[type])} />
    </div>
  );
}

// Priority Badge
function PriorityBadge({ priority }: { priority: NotificationPriority }) {
  const styles = {
    low: 'bg-gray-100 text-gray-600',
    medium: 'bg-blue-100 text-blue-600',
    high: 'bg-orange-100 text-orange-600',
    urgent: 'bg-red-100 text-red-600',
  };

  return (
    <span className={cn(
      'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
      styles[priority]
    )}>
      {priority}
    </span>
  );
}

// Single Notification Item
interface NotificationItemProps {
  notification: Notification;
  onMarkAsRead: (id: string) => void;
  onArchive: (id: string) => void;
  onDelete: (id: string) => void;
  compact?: boolean;
}

function NotificationItem({
  notification,
  onMarkAsRead,
  onArchive,
  onDelete,
  compact = false
}: NotificationItemProps) {
  const [showActions, setShowActions] = useState(false);

  const handleClick = () => {
    if (!notification.read) {
      onMarkAsRead(notification.id);
    }
    
    if (notification.actionUrl) {
      window.open(notification.actionUrl, '_blank');
    }
  };

  const timeAgo = formatDistanceToNow(notification.timestamp, { addSuffix: true });

  return (
    <div
      className={cn(
        'group relative flex items-start space-x-3 p-4 hover:bg-gray-50 cursor-pointer border-l-2',
        notification.read ? 'border-transparent' : 'border-blue-500 bg-blue-50/30',
        compact && 'p-3'
      )}
      onClick={handleClick}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Avatar or Icon */}
      {notification.avatar ? (
        <img
          className="w-10 h-10 rounded-full"
          src={notification.avatar}
          alt=""
        />
      ) : (
        <NotificationIcon type={notification.type} />
      )}

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-2 mb-1">
              <p className={cn(
                'text-sm font-medium text-gray-900 truncate',
                !notification.read && 'font-semibold'
              )}>
                {notification.title}
              </p>
              {!compact && <PriorityBadge priority={notification.priority} />}
              {!notification.read && (
                <div className="w-2 h-2 bg-blue-500 rounded-full" />
              )}
            </div>
            
            <p className={cn(
              'text-sm text-gray-600 line-clamp-2',
              compact && 'line-clamp-1'
            )}>
              {notification.message}
            </p>
            
            <div className="flex items-center justify-between mt-2">
              <p className="text-xs text-gray-500">{timeAgo}</p>
              {notification.actionLabel && (
                <button className="text-xs text-blue-600 hover:text-blue-500 font-medium">
                  {notification.actionLabel}
                </button>
              )}
            </div>
          </div>

          {/* Actions */}
          {(showActions || !notification.read) && (
            <div className="flex items-center space-x-1 ml-2">
              {!notification.read && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onMarkAsRead(notification.id);
                  }}
                  className="p-1 text-blue-500 hover:text-blue-600 rounded"
                  title="Mark as read"
                >
                  <Check className="w-4 h-4" />
                </button>
              )}
              
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onArchive(notification.id);
                }}
                className="p-1 text-gray-400 hover:text-gray-600 rounded"
                title="Archive"
              >
                <Mail className="w-4 h-4" />
              </button>
              
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(notification.id);
                }}
                className="p-1 text-red-400 hover:text-red-600 rounded"
                title="Delete"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Notification List
interface NotificationListProps {
  notifications: Notification[];
  onMarkAsRead: (id: string) => void;
  onArchive: (id: string) => void;
  onDelete: (id: string) => void;
  showArchived?: boolean;
  compact?: boolean;
  maxHeight?: string;
}

function NotificationList({
  notifications,
  onMarkAsRead,
  onArchive,
  onDelete,
  showArchived = false,
  compact = false,
  maxHeight = '400px'
}: NotificationListProps) {
  const [filter, setFilter] = useState<NotificationType | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  const filteredNotifications = notifications
    .filter(notif => showArchived || !notif.archived)
    .filter(notif => filter === 'all' || notif.type === filter)
    .filter(notif => 
      !searchQuery || 
      notif.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      notif.message.toLowerCase().includes(searchQuery.toLowerCase())
    )
    .sort((a, b) => {
      // Unread first, then by timestamp
      if (a.read !== b.read) return a.read ? 1 : -1;
      return b.timestamp.getTime() - a.timestamp.getTime();
    });

  if (notifications.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <Bell className="w-12 h-12 text-gray-400 mb-4" />
        <p className="text-gray-500 text-center">No notifications yet</p>
      </div>
    );
  }

  return (
    <div>
      {/* Filters */}
      {!compact && (
        <div className="border-b border-gray-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search notifications..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={cn(
                'ml-3 p-2 rounded-lg border',
                showFilters 
                  ? 'bg-blue-50 border-blue-200 text-blue-600'
                  : 'border-gray-300 text-gray-700 hover:bg-gray-50'
              )}
            >
              <Filter className="w-4 h-4" />
            </button>
          </div>

          {showFilters && (
            <div className="flex flex-wrap gap-2">
              {(['all', 'info', 'success', 'warning', 'error', 'message', 'user', 'system', 'billing', 'analytics'] as const).map((type) => (
                <button
                  key={type}
                  onClick={() => setFilter(type)}
                  className={cn(
                    'px-3 py-1 rounded-full text-xs font-medium border',
                    filter === type
                      ? 'bg-blue-100 border-blue-200 text-blue-700'
                      : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
                  )}
                >
                  {type}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Notification List */}
      <div 
        className="divide-y divide-gray-200 overflow-y-auto"
        style={{ maxHeight }}
      >
        {filteredNotifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8">
            <p className="text-gray-500">No notifications match your filter</p>
          </div>
        ) : (
          filteredNotifications.map((notification) => (
            <NotificationItem
              key={notification.id}
              notification={notification}
              onMarkAsRead={onMarkAsRead}
              onArchive={onArchive}
              onDelete={onDelete}
              compact={compact}
            />
          ))
        )}
      </div>
    </div>
  );
}

// Notification Bell/Dropdown
interface NotificationDropdownProps {
  className?: string;
}

export function NotificationDropdown({ className = '' }: NotificationDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { 
    notifications, 
    unreadCount, 
    markAsRead, 
    markAllAsRead,
    archiveNotification,
    deleteNotification 
  } = useNotifications();

  const recentNotifications = notifications.slice(0, 10);

  return (
    <div className={cn('relative', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-lg"
      >
        <Bell className="w-6 h-6" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 h-5 w-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg ring-1 ring-black ring-opacity-5 z-20">
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-gray-900">Notifications</h3>
                {unreadCount > 0 && (
                  <button
                    onClick={markAllAsRead}
                    className="text-sm text-blue-600 hover:text-blue-500"
                  >
                    Mark all as read
                  </button>
                )}
              </div>
            </div>

            <NotificationList
              notifications={recentNotifications}
              onMarkAsRead={markAsRead}
              onArchive={archiveNotification}
              onDelete={deleteNotification}
              compact
              maxHeight="300px"
            />

            {notifications.length > 10 && (
              <div className="p-4 border-t border-gray-200">
                <button 
                  onClick={() => {
                    setIsOpen(false);
                    // Navigate to full notifications page
                    window.location.href = '/notifications';
                  }}
                  className="w-full text-center text-sm text-blue-600 hover:text-blue-500 font-medium"
                >
                  View all notifications
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// Full Notification Panel
interface NotificationPanelProps {
  className?: string;
  showArchived?: boolean;
}

export function NotificationPanel({ 
  className = '',
  showArchived = false 
}: NotificationPanelProps) {
  const { 
    notifications, 
    markAsRead, 
    markAllAsRead,
    archiveNotification,
    deleteNotification,
    clearAll 
  } = useNotifications();

  return (
    <div className={cn('bg-white rounded-lg border shadow-sm', className)}>
      <div className="flex items-center justify-between p-6 border-b border-gray-200">
        <h2 className="text-xl font-semibold text-gray-900">Notifications</h2>
        <div className="flex items-center space-x-2">
          <button
            onClick={markAllAsRead}
            className="px-3 py-1 text-sm text-blue-600 hover:text-blue-500"
          >
            Mark all as read
          </button>
          <button
            onClick={clearAll}
            className="px-3 py-1 text-sm text-red-600 hover:text-red-500"
          >
            Clear all
          </button>
        </div>
      </div>

      <NotificationList
        notifications={notifications}
        onMarkAsRead={markAsRead}
        onArchive={archiveNotification}
        onDelete={deleteNotification}
        showArchived={showArchived}
        maxHeight="600px"
      />
    </div>
  );
}

// Provider
interface NotificationProviderProps {
  children: ReactNode;
  initialNotifications?: Notification[];
}

export function NotificationProvider({ 
  children, 
  initialNotifications = [] 
}: NotificationProviderProps) {
  const [notifications, setNotifications] = useState<Notification[]>(initialNotifications);

  const addNotification = useCallback((notif: Omit<Notification, 'id' | 'timestamp' | 'read' | 'archived'>) => {
    const newNotification: Notification = {
      ...notif,
      id: `notif-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
      read: false,
      archived: false,
    };

    setNotifications(prev => [newNotification, ...prev]);
  }, []);

  const markAsRead = useCallback((id: string) => {
    setNotifications(prev => 
      prev.map(notif => 
        notif.id === id ? { ...notif, read: true } : notif
      )
    );
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications(prev => 
      prev.map(notif => ({ ...notif, read: true }))
    );
  }, []);

  const archiveNotification = useCallback((id: string) => {
    setNotifications(prev => 
      prev.map(notif => 
        notif.id === id ? { ...notif, archived: true } : notif
      )
    );
  }, []);

  const deleteNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(notif => notif.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  const unreadCount = notifications.filter(notif => !notif.read && !notif.archived).length;

  const value = {
    notifications,
    unreadCount,
    addNotification,
    markAsRead,
    markAllAsRead,
    archiveNotification,
    deleteNotification,
    clearAll,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}