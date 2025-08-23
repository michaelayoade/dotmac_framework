/**
 * Real-time Notifications State Management
 * Handles WebSocket connections, real-time updates, and notification persistence
 */

import { create } from 'zustand';
import { createJSONStorage, persist, subscribeWithSelector } from 'zustand/middleware';
import { secureStorage } from '../utils/secureStorage';

// Notification types
export interface NotificationData {
  id: string;
  type: 'system' | 'billing' | 'network' | 'support' | 'security' | 'maintenance';
  severity: 'info' | 'warning' | 'error' | 'critical' | 'success';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  dismissed: boolean;
  persistent: boolean;
  category: string;
  source: string;
  metadata?: Record<string, any>;
  actions?: NotificationAction[];
  expiresAt?: Date;
  tenant_id?: string;
  user_id?: string;
}

export interface NotificationAction {
  id: string;
  label: string;
  type: 'primary' | 'secondary' | 'danger';
  action: () => void | Promise<void>;
  icon?: string;
}

// Real-time connection state
export interface RealtimeConnectionState {
  connected: boolean;
  connectionId?: string;
  lastConnected?: Date;
  reconnectAttempts: number;
  maxReconnectAttempts: number;
  reconnectDelay: number;
  heartbeatInterval?: NodeJS.Timeout;
  pingLatency?: number;
}

// Notification filters and preferences
export interface NotificationFilters {
  types: string[];
  severities: string[];
  categories: string[];
  sources: string[];
  dateRange?: {
    start: Date;
    end: Date;
  };
  readStatus: 'all' | 'unread' | 'read';
  showDismissed: boolean;
}

export interface NotificationPreferences {
  enabled: boolean;
  sound: boolean;
  desktop: boolean;
  email: boolean;
  push: boolean;
  categories: {
    [key: string]: {
      enabled: boolean;
      sound: boolean;
      desktop: boolean;
      email: boolean;
      priority: 'low' | 'normal' | 'high';
    };
  };
  quietHours: {
    enabled: boolean;
    start: string; // HH:MM
    end: string; // HH:MM
    timezone: string;
  };
  consolidation: {
    enabled: boolean;
    interval: number; // minutes
    maxGroupSize: number;
  };
}

// Store state interface
interface NotificationsState {
  // Notifications data
  notifications: NotificationData[];
  unreadCount: number;
  totalCount: number;
  
  // Real-time connection
  realtime: RealtimeConnectionState;
  
  // Filtering and preferences
  filters: NotificationFilters;
  preferences: NotificationPreferences;
  
  // UI state
  panelOpen: boolean;
  activeTab: 'all' | 'unread' | 'archived';
  searchTerm: string;
  isLoading: boolean;
  error: string | null;
  
  // WebSocket/SSE connection
  connection: WebSocket | EventSource | null;
}

// Store actions interface
interface NotificationsActions {
  // Notification management
  addNotification: (notification: Omit<NotificationData, 'id' | 'timestamp'>) => string;
  updateNotification: (id: string, updates: Partial<NotificationData>) => void;
  removeNotification: (id: string) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  dismissNotification: (id: string) => void;
  dismissAll: () => void;
  archiveNotification: (id: string) => void;
  restoreNotification: (id: string) => void;
  
  // Bulk operations
  markMultipleAsRead: (ids: string[]) => void;
  dismissMultiple: (ids: string[]) => void;
  archiveMultiple: (ids: string[]) => void;
  deleteExpired: () => void;
  
  // Real-time connection management
  connect: (endpoint: string, options?: { 
    protocol: 'websocket' | 'sse';
    auth?: string;
    tenant_id?: string;
  }) => Promise<void>;
  disconnect: () => void;
  reconnect: () => Promise<void>;
  sendHeartbeat: () => void;
  
  // Filtering and search
  updateFilters: (updates: Partial<NotificationFilters>) => void;
  resetFilters: () => void;
  setSearchTerm: (term: string) => void;
  
  // Preferences
  updatePreferences: (updates: Partial<NotificationPreferences>) => void;
  toggleCategoryPreference: (category: string, type: keyof NotificationPreferences['categories'][string]) => void;
  
  // UI management
  openPanel: () => void;
  closePanel: () => void;
  togglePanel: () => void;
  setActiveTab: (tab: 'all' | 'unread' | 'archived') => void;
  
  // Utility functions
  getFilteredNotifications: () => NotificationData[];
  getUnreadNotifications: () => NotificationData[];
  getNotificationsByCategory: (category: string) => NotificationData[];
  shouldPlaySound: (notification: NotificationData) => boolean;
  shouldShowDesktop: (notification: NotificationData) => boolean;
  isInQuietHours: () => boolean;
  
  // Permission management
  requestNotificationPermission: () => Promise<NotificationPermission>;
  checkPermissions: () => {
    notifications: NotificationPermission;
    sound: boolean;
  };
}

type NotificationsStore = NotificationsState & NotificationsActions;

// Default states
const defaultFilters: NotificationFilters = {
  types: [],
  severities: [],
  categories: [],
  sources: [],
  readStatus: 'all',
  showDismissed: false,
};

const defaultPreferences: NotificationPreferences = {
  enabled: true,
  sound: true,
  desktop: true,
  email: false,
  push: true,
  categories: {
    system: { enabled: true, sound: false, desktop: true, email: false, priority: 'normal' },
    billing: { enabled: true, sound: true, desktop: true, email: true, priority: 'high' },
    network: { enabled: true, sound: true, desktop: true, email: false, priority: 'high' },
    support: { enabled: true, sound: false, desktop: true, email: false, priority: 'normal' },
    security: { enabled: true, sound: true, desktop: true, email: true, priority: 'high' },
    maintenance: { enabled: true, sound: false, desktop: true, email: false, priority: 'low' },
  },
  quietHours: {
    enabled: false,
    start: '22:00',
    end: '08:00',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  },
  consolidation: {
    enabled: true,
    interval: 5,
    maxGroupSize: 10,
  },
};

const defaultRealtimeState: RealtimeConnectionState = {
  connected: false,
  reconnectAttempts: 0,
  maxReconnectAttempts: 5,
  reconnectDelay: 1000,
};

export const useNotificationsStore = create<NotificationsStore>()(
  subscribeWithSelector(
    persist(
      (set, get) => ({
        // Initial state
        notifications: [],
        unreadCount: 0,
        totalCount: 0,
        realtime: defaultRealtimeState,
        filters: defaultFilters,
        preferences: defaultPreferences,
        panelOpen: false,
        activeTab: 'all',
        searchTerm: '',
        isLoading: false,
        error: null,
        connection: null,

        // Notification management
        addNotification: (notificationData) => {
          const id = `notif_${Date.now()}_${Math.random().toString(36).substring(2)}`;
          const notification: NotificationData = {
            ...notificationData,
            id,
            timestamp: new Date(),
            read: false,
            dismissed: false,
          };

          set((state) => {
            const newNotifications = [notification, ...state.notifications];
            return {
              notifications: newNotifications,
              unreadCount: state.unreadCount + 1,
              totalCount: state.totalCount + 1,
            };
          });

          // Handle desktop notifications
          const { shouldShowDesktop, shouldPlaySound } = get();
          if (shouldShowDesktop(notification)) {
            get().requestNotificationPermission().then((permission) => {
              if (permission === 'granted') {
                const desktopNotif = new Notification(notification.title, {
                  body: notification.message,
                  icon: '/icons/notification.png',
                  tag: notification.id,
                  timestamp: notification.timestamp.getTime(),
                });
                
                desktopNotif.onclick = () => {
                  get().markAsRead(id);
                  get().openPanel();
                  desktopNotif.close();
                };
              }
            });
          }

          // Handle sound notifications
          if (shouldPlaySound(notification)) {
            const audio = new Audio('/sounds/notification.mp3');
            audio.play().catch(() => {
              // Ignore audio play failures
            });
          }

          return id;
        },

        updateNotification: (id, updates) => {
          set((state) => ({
            notifications: state.notifications.map((n) =>
              n.id === id ? { ...n, ...updates } : n
            ),
          }));
        },

        removeNotification: (id) => {
          set((state) => {
            const notification = state.notifications.find((n) => n.id === id);
            const newNotifications = state.notifications.filter((n) => n.id !== id);
            
            return {
              notifications: newNotifications,
              unreadCount: notification && !notification.read 
                ? state.unreadCount - 1 
                : state.unreadCount,
              totalCount: state.totalCount - 1,
            };
          });
        },

        markAsRead: (id) => {
          set((state) => {
            const notification = state.notifications.find((n) => n.id === id);
            if (!notification || notification.read) return state;

            return {
              notifications: state.notifications.map((n) =>
                n.id === id ? { ...n, read: true } : n
              ),
              unreadCount: state.unreadCount - 1,
            };
          });
        },

        markAllAsRead: () => {
          set((state) => ({
            notifications: state.notifications.map((n) => ({ ...n, read: true })),
            unreadCount: 0,
          }));
        },

        dismissNotification: (id) => {
          get().updateNotification(id, { dismissed: true });
        },

        dismissAll: () => {
          set((state) => ({
            notifications: state.notifications.map((n) => ({ ...n, dismissed: true })),
          }));
        },

        archiveNotification: (id) => {
          get().updateNotification(id, { 
            dismissed: true, 
            read: true,
            metadata: { ...get().notifications.find(n => n.id === id)?.metadata, archived: true }
          });
        },

        restoreNotification: (id) => {
          get().updateNotification(id, { 
            dismissed: false,
            metadata: { ...get().notifications.find(n => n.id === id)?.metadata, archived: false }
          });
        },

        // Bulk operations
        markMultipleAsRead: (ids) => {
          ids.forEach((id) => get().markAsRead(id));
        },

        dismissMultiple: (ids) => {
          ids.forEach((id) => get().dismissNotification(id));
        },

        archiveMultiple: (ids) => {
          ids.forEach((id) => get().archiveNotification(id));
        },

        deleteExpired: () => {
          const now = new Date();
          set((state) => ({
            notifications: state.notifications.filter((n) => {
              if (!n.expiresAt) return true;
              return n.expiresAt > now;
            }),
          }));
        },

        // Real-time connection management
        connect: async (endpoint, options = {}) => {
          const { protocol = 'websocket' } = options;
          
          try {
            set({ isLoading: true, error: null });

            if (protocol === 'websocket') {
              const ws = new WebSocket(endpoint);
              
              ws.onopen = () => {
                set((state) => ({
                  connection: ws,
                  realtime: {
                    ...state.realtime,
                    connected: true,
                    lastConnected: new Date(),
                    reconnectAttempts: 0,
                  },
                  isLoading: false,
                }));

                // Send authentication if provided
                if (options.auth) {
                  ws.send(JSON.stringify({ type: 'auth', token: options.auth }));
                }

                // Setup heartbeat
                const heartbeat = setInterval(() => {
                  if (ws.readyState === WebSocket.OPEN) {
                    const pingTime = Date.now();
                    ws.send(JSON.stringify({ type: 'ping', timestamp: pingTime }));
                  }
                }, 30000);

                set((state) => ({
                  realtime: { ...state.realtime, heartbeatInterval: heartbeat },
                }));
              };

              ws.onmessage = (event) => {
                try {
                  const data = JSON.parse(event.data);
                  
                  if (data.type === 'pong') {
                    const latency = Date.now() - data.timestamp;
                    set((state) => ({
                      realtime: { ...state.realtime, pingLatency: latency },
                    }));
                  } else if (data.type === 'notification') {
                    get().addNotification(data.notification);
                  }
                } catch (error) {
                  console.error('Error parsing WebSocket message:', error);
                }
              };

              ws.onclose = () => {
                set((state) => ({
                  realtime: { ...state.realtime, connected: false },
                  connection: null,
                }));
                
                // Attempt reconnection
                get().reconnect();
              };

              ws.onerror = (error) => {
                set({ error: 'WebSocket connection error' });
                console.error('WebSocket error:', error);
              };

            } else if (protocol === 'sse') {
              const sse = new EventSource(endpoint);
              
              sse.onopen = () => {
                set((state) => ({
                  connection: sse,
                  realtime: {
                    ...state.realtime,
                    connected: true,
                    lastConnected: new Date(),
                    reconnectAttempts: 0,
                  },
                  isLoading: false,
                }));
              };

              sse.onmessage = (event) => {
                try {
                  const data = JSON.parse(event.data);
                  if (data.type === 'notification') {
                    get().addNotification(data.notification);
                  }
                } catch (error) {
                  console.error('Error parsing SSE message:', error);
                }
              };

              sse.onerror = () => {
                set((state) => ({
                  realtime: { ...state.realtime, connected: false },
                  connection: null,
                }));
                
                get().reconnect();
              };
            }

          } catch (error) {
            set({ 
              isLoading: false, 
              error: `Connection failed: ${error instanceof Error ? error.message : 'Unknown error'}` 
            });
          }
        },

        disconnect: () => {
          const { connection, realtime } = get();
          
          if (connection) {
            if (connection instanceof WebSocket) {
              connection.close();
            } else if (connection instanceof EventSource) {
              connection.close();
            }
          }

          if (realtime.heartbeatInterval) {
            clearInterval(realtime.heartbeatInterval);
          }

          set({
            connection: null,
            realtime: { ...realtime, connected: false, heartbeatInterval: undefined },
          });
        },

        reconnect: async () => {
          const { realtime } = get();
          
          if (realtime.reconnectAttempts >= realtime.maxReconnectAttempts) {
            set({ error: 'Max reconnection attempts reached' });
            return;
          }

          const delay = realtime.reconnectDelay * Math.pow(2, realtime.reconnectAttempts);
          
          set((state) => ({
            realtime: {
              ...state.realtime,
              reconnectAttempts: state.realtime.reconnectAttempts + 1,
            },
          }));

          setTimeout(() => {
            // Would need to store original connection parameters to reconnect
            // This is a simplified version
            console.log('Attempting to reconnect...');
          }, delay);
        },

        sendHeartbeat: () => {
          const { connection } = get();
          if (connection instanceof WebSocket && connection.readyState === WebSocket.OPEN) {
            connection.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
          }
        },

        // Filtering and search
        updateFilters: (updates) => {
          set((state) => ({
            filters: { ...state.filters, ...updates },
          }));
        },

        resetFilters: () => {
          set({ filters: defaultFilters, searchTerm: '' });
        },

        setSearchTerm: (term) => {
          set({ searchTerm: term });
        },

        // Preferences
        updatePreferences: (updates) => {
          set((state) => ({
            preferences: { ...state.preferences, ...updates },
          }));
        },

        toggleCategoryPreference: (category, type) => {
          set((state) => ({
            preferences: {
              ...state.preferences,
              categories: {
                ...state.preferences.categories,
                [category]: {
                  ...state.preferences.categories[category],
                  [type]: !state.preferences.categories[category]?.[type],
                },
              },
            },
          }));
        },

        // UI management
        openPanel: () => set({ panelOpen: true }),
        closePanel: () => set({ panelOpen: false }),
        togglePanel: () => set((state) => ({ panelOpen: !state.panelOpen })),
        setActiveTab: (tab) => set({ activeTab: tab }),

        // Utility functions
        getFilteredNotifications: () => {
          const { notifications, filters, searchTerm, activeTab } = get();
          
          let filtered = notifications.filter((notification) => {
            // Tab filtering
            if (activeTab === 'unread' && notification.read) return false;
            if (activeTab === 'archived' && !notification.metadata?.archived) return false;

            // Search term filtering
            if (searchTerm) {
              const searchLower = searchTerm.toLowerCase();
              const matchesSearch = 
                notification.title.toLowerCase().includes(searchLower) ||
                notification.message.toLowerCase().includes(searchLower) ||
                notification.category.toLowerCase().includes(searchLower) ||
                notification.source.toLowerCase().includes(searchLower);
              
              if (!matchesSearch) return false;
            }

            // Type filtering
            if (filters.types.length > 0 && !filters.types.includes(notification.type)) {
              return false;
            }

            // Severity filtering
            if (filters.severities.length > 0 && !filters.severities.includes(notification.severity)) {
              return false;
            }

            // Category filtering
            if (filters.categories.length > 0 && !filters.categories.includes(notification.category)) {
              return false;
            }

            // Source filtering
            if (filters.sources.length > 0 && !filters.sources.includes(notification.source)) {
              return false;
            }

            // Read status filtering
            if (filters.readStatus === 'read' && !notification.read) return false;
            if (filters.readStatus === 'unread' && notification.read) return false;

            // Dismissed filtering
            if (!filters.showDismissed && notification.dismissed) return false;

            // Date range filtering
            if (filters.dateRange) {
              const notificationDate = notification.timestamp;
              if (filters.dateRange.start && notificationDate < filters.dateRange.start) return false;
              if (filters.dateRange.end && notificationDate > filters.dateRange.end) return false;
            }

            return true;
          });

          return filtered;
        },

        getUnreadNotifications: () => {
          const { notifications } = get();
          return notifications.filter((n) => !n.read && !n.dismissed);
        },

        getNotificationsByCategory: (category) => {
          const { notifications } = get();
          return notifications.filter((n) => n.category === category);
        },

        shouldPlaySound: (notification) => {
          const { preferences } = get();
          if (!preferences.enabled || !preferences.sound) return false;
          if (get().isInQuietHours()) return false;
          
          const categoryPref = preferences.categories[notification.category];
          return categoryPref?.enabled && categoryPref?.sound;
        },

        shouldShowDesktop: (notification) => {
          const { preferences } = get();
          if (!preferences.enabled || !preferences.desktop) return false;
          
          const categoryPref = preferences.categories[notification.category];
          return categoryPref?.enabled && categoryPref?.desktop;
        },

        isInQuietHours: () => {
          const { preferences } = get();
          if (!preferences.quietHours.enabled) return false;

          const now = new Date();
          const currentTime = now.getHours() * 60 + now.getMinutes();
          
          const [startHour, startMin] = preferences.quietHours.start.split(':').map(Number);
          const [endHour, endMin] = preferences.quietHours.end.split(':').map(Number);
          
          const startTime = startHour * 60 + startMin;
          const endTime = endHour * 60 + endMin;

          if (startTime <= endTime) {
            return currentTime >= startTime && currentTime <= endTime;
          } else {
            // Spans midnight
            return currentTime >= startTime || currentTime <= endTime;
          }
        },

        // Permission management
        requestNotificationPermission: async () => {
          if (!("Notification" in window)) {
            return 'denied' as NotificationPermission;
          }

          if (Notification.permission === 'granted') {
            return 'granted';
          }

          if (Notification.permission === 'denied') {
            return 'denied';
          }

          return await Notification.requestPermission();
        },

        checkPermissions: () => {
          return {
            notifications: Notification?.permission || 'denied',
            sound: true, // Browser sound is generally available
          };
        },
      }),
      {
        name: 'dotmac-notifications',
        storage: createJSONStorage(() => ({
          getItem: (name) => secureStorage.getItem(name),
          setItem: (name, value) => secureStorage.setItem(name, value),
          removeItem: (name) => secureStorage.removeItem(name),
        })),
        partialize: (state) => ({
          // Persist notifications (limited to last 100)
          notifications: state.notifications.slice(0, 100),
          preferences: state.preferences,
          filters: state.filters,
          // Don't persist connection state or UI state
        }),
        version: 1,
        migrate: (persistedState: any, version: number) => {
          if (version === 0) {
            // Migration logic for older versions
            return {
              ...persistedState,
              preferences: { ...defaultPreferences, ...persistedState.preferences },
            };
          }
          return persistedState;
        },
      }
    )
  )
);

// Cleanup expired notifications periodically
setInterval(() => {
  useNotificationsStore.getState().deleteExpired();
}, 60000); // Every minute