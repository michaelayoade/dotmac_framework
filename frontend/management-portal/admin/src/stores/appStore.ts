/**
 * Central Application Store
 * Manages global application state using Zustand
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

// Types
export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'super_admin';
  permissions: string[];
  avatar?: string;
  lastLogin?: string;
}

export interface SystemHealth {
  status: 'healthy' | 'warning' | 'critical';
  uptime: number;
  version: string;
  lastUpdated: string;
}

export interface GlobalNotification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  persistent?: boolean;
}

export interface UIState {
  sidebarCollapsed: boolean;
  theme: 'light' | 'dark' | 'system';
  loading: {
    global: boolean;
    components: Record<string, boolean>;
  };
  modals: {
    confirmDialog: {
      open: boolean;
      title?: string;
      message?: string;
      onConfirm?: () => void;
      onCancel?: () => void;
      confirmText?: string;
      cancelText?: string;
      variant?: 'danger' | 'warning' | 'info';
    };
  };
}

export interface AppStore {
  // State
  user: User | null;
  isAuthenticated: boolean;
  systemHealth: SystemHealth | null;
  notifications: GlobalNotification[];
  ui: UIState;

  // User Actions
  setUser: (user: User) => void;
  clearUser: () => void;
  updateUserPermissions: (permissions: string[]) => void;

  // System Actions
  setSystemHealth: (health: SystemHealth) => void;

  // Notification Actions
  addNotification: (notification: Omit<GlobalNotification, 'id' | 'timestamp' | 'read'>) => void;
  markNotificationRead: (id: string) => void;
  removeNotification: (id: string) => void;
  clearAllNotifications: () => void;

  // UI Actions
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setTheme: (theme: UIState['theme']) => void;
  setGlobalLoading: (loading: boolean) => void;
  setComponentLoading: (component: string, loading: boolean) => void;
  openConfirmDialog: (config: Omit<UIState['modals']['confirmDialog'], 'open'>) => void;
  closeConfirmDialog: () => void;

  // Utility Actions
  reset: () => void;
}

const initialState = {
  user: null,
  isAuthenticated: false,
  systemHealth: null,
  notifications: [],
  ui: {
    sidebarCollapsed: false,
    theme: 'light' as const,
    loading: {
      global: false,
      components: {},
    },
    modals: {
      confirmDialog: {
        open: false,
      },
    },
  },
};

export const useAppStore = create<AppStore>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,

        // User Actions
        setUser: (user) =>
          set((state) => ({
            ...state,
            user,
            isAuthenticated: true,
          })),

        clearUser: () =>
          set((state) => ({
            ...state,
            user: null,
            isAuthenticated: false,
          })),

        updateUserPermissions: (permissions) =>
          set((state) => ({
            ...state,
            user: state.user ? { ...state.user, permissions } : null,
          })),

        // System Actions
        setSystemHealth: (health) =>
          set((state) => ({
            ...state,
            systemHealth: health,
          })),

        // Notification Actions
        addNotification: (notification) =>
          set((state) => {
            const newNotification: GlobalNotification = {
              ...notification,
              id: `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
              timestamp: new Date().toISOString(),
              read: false,
            };
            const updatedNotifications = [newNotification, ...state.notifications];

            // Keep only last 50 notifications
            return {
              ...state,
              notifications: updatedNotifications.slice(0, 50),
            };
          }),

        markNotificationRead: (id) =>
          set((state) => ({
            ...state,
            notifications: state.notifications.map((n) => (n.id === id ? { ...n, read: true } : n)),
          })),

        removeNotification: (id) =>
          set((state) => ({
            ...state,
            notifications: state.notifications.filter((n) => n.id !== id),
          })),

        clearAllNotifications: () =>
          set((state) => ({
            ...state,
            notifications: [],
          })),

        // UI Actions
        toggleSidebar: () =>
          set((state) => ({
            ...state,
            ui: {
              ...state.ui,
              sidebarCollapsed: !state.ui.sidebarCollapsed,
            },
          })),

        setSidebarCollapsed: (collapsed) =>
          set((state) => ({
            ...state,
            ui: {
              ...state.ui,
              sidebarCollapsed: collapsed,
            },
          })),

        setTheme: (theme) =>
          set((state) => ({
            ...state,
            ui: {
              ...state.ui,
              theme,
            },
          })),

        setGlobalLoading: (loading) =>
          set((state) => ({
            ...state,
            ui: {
              ...state.ui,
              loading: {
                ...state.ui.loading,
                global: loading,
              },
            },
          })),

        setComponentLoading: (component, loading) =>
          set((state) => {
            const components = { ...state.ui.loading.components };
            if (loading) {
              components[component] = true;
            } else {
              delete components[component];
            }

            return {
              ...state,
              ui: {
                ...state.ui,
                loading: {
                  ...state.ui.loading,
                  components,
                },
              },
            };
          }),

        openConfirmDialog: (config) =>
          set((state) => ({
            ...state,
            ui: {
              ...state.ui,
              modals: {
                ...state.ui.modals,
                confirmDialog: {
                  ...config,
                  open: true,
                },
              },
            },
          })),

        closeConfirmDialog: () =>
          set((state) => ({
            ...state,
            ui: {
              ...state.ui,
              modals: {
                ...state.ui.modals,
                confirmDialog: {
                  open: false,
                },
              },
            },
          })),

        // Utility Actions
        reset: () =>
          set(() => ({
            ...initialState,
          })),
      }),
      {
        name: 'dotmac-admin-store',
        partialize: (state) => ({
          user: state.user,
          isAuthenticated: state.isAuthenticated,
          ui: {
            sidebarCollapsed: state.ui.sidebarCollapsed,
            theme: state.ui.theme,
          },
        }),
      }
    ),
    {
      name: 'DotMac Admin Store',
    }
  )
);

// Selectors for optimized component subscriptions
export const useUser = () => useAppStore((state) => state.user);
export const useIsAuthenticated = () => useAppStore((state) => state.isAuthenticated);
export const useSystemHealth = () => useAppStore((state) => state.systemHealth);
export const useNotifications = () => useAppStore((state) => state.notifications);
export const useUnreadNotifications = () =>
  useAppStore((state) => state.notifications.filter((n) => !n.read));
export const useUIState = () => useAppStore((state) => state.ui);
export const useGlobalLoading = () => useAppStore((state) => state.ui.loading.global);
export const useComponentLoading = (component: string) =>
  useAppStore((state) => state.ui.loading.components[component] ?? false);
