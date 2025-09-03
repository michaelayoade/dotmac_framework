import { create } from 'zustand';
import { subscribeWithSelector, devtools } from 'zustand/middleware';
import type { ManagementUser } from '@/components/auth/AuthTypes';

// Notification types
export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
  timestamp: number;
}

// UI State interface
interface UIState {
  // Layout state
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;

  // Loading states
  globalLoading: boolean;
  pageLoading: Record<string, boolean>;

  // Notifications
  notifications: Notification[];

  // Theme and preferences
  theme: 'light' | 'dark' | 'system';
  density: 'comfortable' | 'compact';

  // Modal and drawer states
  modals: Record<string, boolean>;
  activeModal: string | null;

  // Search and filters
  globalSearch: string;
  activeFilters: Record<string, any>;

  // User preferences
  preferences: {
    autoRefresh: boolean;
    refreshInterval: number;
    showOnboarding: boolean;
    enableNotifications: boolean;
    compactMode: boolean;
  };
}

// Actions interface
interface UIActions {
  // Layout actions
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebarCollapsed: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;

  // Loading actions
  setGlobalLoading: (loading: boolean) => void;
  setPageLoading: (page: string, loading: boolean) => void;
  clearPageLoading: (page: string) => void;

  // Notification actions
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;

  // Theme actions
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  setDensity: (density: 'comfortable' | 'compact') => void;

  // Modal actions
  openModal: (modalId: string) => void;
  closeModal: (modalId: string) => void;
  closeAllModals: () => void;

  // Search and filter actions
  setGlobalSearch: (search: string) => void;
  setFilter: (key: string, value: any) => void;
  clearFilter: (key: string) => void;
  clearAllFilters: () => void;

  // Preference actions
  updatePreferences: (preferences: Partial<UIState['preferences']>) => void;

  // Reset action
  reset: () => void;
}

// Auth state interface
interface AuthState {
  user: ManagementUser | null;
  isAuthenticated: boolean;
  permissions: string[];
  sessionExpiry: number | null;
  lastActivity: number;
}

// Auth actions interface
interface AuthActions {
  setUser: (user: ManagementUser | null) => void;
  setPermissions: (permissions: string[]) => void;
  setSessionExpiry: (expiry: number | null) => void;
  updateLastActivity: () => void;
  clearAuth: () => void;
}

// Combined store interface
type AppStore = UIState & UIActions & AuthState & AuthActions;

// Initial state
const initialUIState: UIState = {
  sidebarOpen: false,
  sidebarCollapsed: false,
  globalLoading: false,
  pageLoading: {},
  notifications: [],
  theme: 'system',
  density: 'comfortable',
  modals: {},
  activeModal: null,
  globalSearch: '',
  activeFilters: {},
  preferences: {
    autoRefresh: true,
    refreshInterval: 30000, // 30 seconds
    showOnboarding: true,
    enableNotifications: true,
    compactMode: false,
  },
};

const initialAuthState: AuthState = {
  user: null,
  isAuthenticated: false,
  permissions: [],
  sessionExpiry: null,
  lastActivity: Date.now(),
};

// Create store with middleware
export const useAppStore = create<AppStore>()(
  devtools(
    subscribeWithSelector((set, get) => ({
      // Initial state
      ...initialUIState,
      ...initialAuthState,

      // UI Actions
      toggleSidebar: () =>
        set((state) => ({
          ...state,
          sidebarOpen: !state.sidebarOpen,
        })),

      setSidebarOpen: (open: boolean) =>
        set((state) => ({
          ...state,
          sidebarOpen: open,
        })),

      toggleSidebarCollapsed: () =>
        set((state) => ({
          ...state,
          sidebarCollapsed: !state.sidebarCollapsed,
        })),

      setSidebarCollapsed: (collapsed: boolean) =>
        set((state) => ({
          ...state,
          sidebarCollapsed: collapsed,
        })),

      setGlobalLoading: (loading: boolean) =>
        set((state) => ({
          ...state,
          globalLoading: loading,
        })),

      setPageLoading: (page: string, loading: boolean) =>
        set((state) => ({
          ...state,
          pageLoading: { ...state.pageLoading, [page]: loading },
        })),

      clearPageLoading: (page: string) => {
        const { [page]: _, ...rest } = get().pageLoading;
        set((state) => ({
          ...state,
          pageLoading: rest,
        }));
      },

      addNotification: (notification) =>
        set((state) => {
          const newNotification: Notification = {
            ...notification,
            id: Math.random().toString(36).substr(2, 9),
            timestamp: Date.now(),
          };

          const updatedNotifications = [...state.notifications, newNotification];

          // Auto-remove notification after duration
          if (notification.duration !== 0) {
            setTimeout(() => {
              const currentState = get();
              const exists = currentState.notifications.find(
                (n: Notification) => n.id === newNotification.id
              );
              if (exists) {
                currentState.removeNotification(newNotification.id);
              }
            }, notification.duration || 5000);
          }

          return { ...state, notifications: updatedNotifications };
        }),

      removeNotification: (id: string) =>
        set((state) => ({
          ...state,
          notifications: state.notifications.filter((n: Notification) => n.id !== id),
        })),

      clearNotifications: () =>
        set((state) => ({
          ...state,
          notifications: [],
        })),

      setTheme: (theme: 'light' | 'dark' | 'system') =>
        set((state) => ({
          ...state,
          theme,
        })),

      setDensity: (density: 'comfortable' | 'compact') =>
        set((state) => ({
          ...state,
          density,
        })),

      openModal: (modalId: string) =>
        set((state) => ({
          ...state,
          modals: { ...state.modals, [modalId]: true },
          activeModal: modalId,
        })),

      closeModal: (modalId: string) =>
        set((state) => ({
          ...state,
          modals: { ...state.modals, [modalId]: false },
          activeModal: state.activeModal === modalId ? null : state.activeModal,
        })),

      closeAllModals: () =>
        set((state) => {
          const closedModals = Object.keys(state.modals).reduce(
            (acc, key) => {
              acc[key] = false;
              return acc;
            },
            {} as Record<string, boolean>
          );
          return {
            ...state,
            modals: closedModals,
            activeModal: null,
          };
        }),

      setGlobalSearch: (search: string) =>
        set((state) => ({
          ...state,
          globalSearch: search,
        })),

      setFilter: (key: string, value: any) =>
        set((state) => ({
          ...state,
          activeFilters: { ...state.activeFilters, [key]: value },
        })),

      clearFilter: (key: string) => {
        const { [key]: _, ...rest } = get().activeFilters;
        set((state) => ({
          ...state,
          activeFilters: rest,
        }));
      },

      clearAllFilters: () =>
        set((state) => ({
          ...state,
          activeFilters: {},
        })),

      updatePreferences: (preferences) =>
        set((state) => ({
          ...state,
          preferences: { ...state.preferences, ...preferences },
        })),

      // Auth Actions
      setUser: (user: ManagementUser | null) =>
        set((state) => ({
          ...state,
          user,
          isAuthenticated: !!user,
          permissions: user?.permissions || [],
        })),

      setPermissions: (permissions: string[]) =>
        set((state) => ({
          ...state,
          permissions,
        })),

      setSessionExpiry: (expiry: number | null) =>
        set((state) => ({
          ...state,
          sessionExpiry: expiry,
        })),

      updateLastActivity: () =>
        set((state) => ({
          ...state,
          lastActivity: Date.now(),
        })),

      clearAuth: () =>
        set((state) => ({
          ...state,
          user: null,
          isAuthenticated: false,
          permissions: [],
          sessionExpiry: null,
        })),

      // Reset action
      reset: () =>
        set(() => ({
          ...initialUIState,
          ...initialAuthState,
        })),
    })),
    {
      name: 'management-app-store',
      partialize: (state: any) => ({
        // Only persist user preferences and theme
        theme: state.theme,
        density: state.density,
        preferences: state.preferences,
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    }
  )
);

// Selectors for common use cases
export const useUser = () => useAppStore((state) => state.user);
export const useIsAuthenticated = () => useAppStore((state) => state.isAuthenticated);
export const usePermissions = () => useAppStore((state) => state.permissions);
export const useNotifications = () => useAppStore((state) => state.notifications);
export const useTheme = () => useAppStore((state) => state.theme);
export const useGlobalLoading = () => useAppStore((state) => state.globalLoading);
export const useSidebar = () =>
  useAppStore((state) => ({
    isOpen: state.sidebarOpen,
    isCollapsed: state.sidebarCollapsed,
  }));

// Action selectors
export const useUIActions = () =>
  useAppStore((state) => ({
    toggleSidebar: state.toggleSidebar,
    setSidebarOpen: state.setSidebarOpen,
    addNotification: state.addNotification,
    removeNotification: state.removeNotification,
    setGlobalLoading: state.setGlobalLoading,
    setPageLoading: state.setPageLoading,
    openModal: state.openModal,
    closeModal: state.closeModal,
    setGlobalSearch: state.setGlobalSearch,
    setFilter: state.setFilter,
  }));

export const useAuthActions = () =>
  useAppStore((state) => ({
    setUser: state.setUser,
    clearAuth: state.clearAuth,
    updateLastActivity: state.updateLastActivity,
  }));
