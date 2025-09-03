/**
 * Centralized Application State Store
 * Manages global app state including UI state, notifications, and shared data
 */

import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { persist, createJSONStorage } from 'zustand/middleware';

// Notification types
export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  duration?: number;
  actions?: NotificationAction[];
  createdAt: number;
}

export interface NotificationAction {
  label: string;
  onClick: () => void;
  variant?: 'primary' | 'secondary';
}

// Loading state types
export interface LoadingState {
  [key: string]: boolean;
}

// Modal state types
export interface ModalState {
  isOpen: boolean;
  type: string | null;
  data: unknown;
  onClose?: () => void;
}

// Sidebar state
export interface SidebarState {
  isCollapsed: boolean;
  activeSection: string | null;
}

// Theme state
export interface ThemeState {
  mode: 'light' | 'dark' | 'system';
  primaryColor: string;
  fontSize: 'small' | 'medium' | 'large';
}

// App settings
export interface AppSettings {
  language: string;
  timezone: string;
  notifications: {
    desktop: boolean;
    email: boolean;
    push: boolean;
  };
  accessibility: {
    highContrast: boolean;
    reducedMotion: boolean;
    screenReader: boolean;
  };
}

interface AppState {
  // UI State
  sidebar: SidebarState;
  modal: ModalState;
  theme: ThemeState;
  settings: AppSettings;

  // Notifications
  notifications: Notification[];

  // Loading states
  loading: LoadingState;

  // Error handling
  errors: Record<string, string>;

  // Actions
  // Notification actions
  addNotification: (notification: Omit<Notification, 'id' | 'createdAt'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;

  // Loading actions
  setLoading: (key: string, isLoading: boolean) => void;
  isLoading: (key: string) => boolean;

  // Modal actions
  openModal: (type: string, data?: unknown, onClose?: () => void) => void;
  closeModal: () => void;

  // Sidebar actions
  toggleSidebar: () => void;
  setSidebarSection: (section: string) => void;

  // Theme actions
  setTheme: (theme: Partial<ThemeState>) => void;

  // Settings actions
  updateSettings: (settings: Partial<AppSettings>) => void;

  // Error actions
  setError: (key: string, error: string) => void;
  clearError: (key: string) => void;
  clearAllErrors: () => void;

  // Utility actions
  reset: () => void;
}

// Default state values
const defaultSidebarState: SidebarState = {
  isCollapsed: false,
  activeSection: null,
};

const defaultModalState: ModalState = {
  isOpen: false,
  type: null,
  data: null,
};

const defaultThemeState: ThemeState = {
  mode: 'system',
  primaryColor: '#3B82F6',
  fontSize: 'medium',
};

const defaultSettings: AppSettings = {
  language: 'en',
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  notifications: {
    desktop: true,
    email: true,
    push: false,
  },
  accessibility: {
    highContrast: false,
    reducedMotion: false,
    screenReader: false,
  },
};

// Custom storage for app preferences
const appStorage = createJSONStorage(() => localStorage, {
  reviver: (key, value) => {
    // Handle dates and other special values
    if (key === 'createdAt' && typeof value === 'number') {
      return value;
    }
    return value;
  },
});

export const useAppStore = create<AppState>()(
  persist(
    immer((set, get) => ({
      // Initial state
      sidebar: defaultSidebarState,
      modal: defaultModalState,
      theme: defaultThemeState,
      settings: defaultSettings,
      notifications: [],
      loading: {},
      errors: {},

      // Notification actions
      addNotification: (notification) => {
        const id = `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const newNotification: Notification = {
          ...notification,
          id,
          createdAt: Date.now(),
        };

        set((state) => {
          state.notifications.push(newNotification);
        });

        // Auto-remove notification after duration
        if (notification.duration !== 0) {
          const duration = notification.duration || 5000;
          setTimeout(() => {
            get().removeNotification(id);
          }, duration);
        }
      },

      removeNotification: (id) => {
        set((state) => {
          const index = state.notifications.findIndex((n) => n.id === id);
          if (index > -1) {
            state.notifications.splice(index, 1);
          }
        });
      },

      clearNotifications: () => {
        set((state) => {
          state.notifications = [];
        });
      },

      // Loading actions
      setLoading: (key, isLoading) => {
        set((state) => {
          state.loading[key] = isLoading;
        });
      },

      isLoading: (key) => {
        return get().loading[key] || false;
      },

      // Modal actions
      openModal: (type, data, onClose) => {
        set((state) => {
          state.modal = {
            isOpen: true,
            type,
            data: data || null,
            onClose,
          };
        });
      },

      closeModal: () => {
        const { modal } = get();
        if (modal.onClose) {
          modal.onClose();
        }

        set((state) => {
          state.modal = defaultModalState;
        });
      },

      // Sidebar actions
      toggleSidebar: () => {
        set((state) => {
          state.sidebar.isCollapsed = !state.sidebar.isCollapsed;
        });
      },

      setSidebarSection: (section) => {
        set((state) => {
          state.sidebar.activeSection = section;
        });
      },

      // Theme actions
      setTheme: (theme) => {
        set((state) => {
          Object.assign(state.theme, theme);
        });
      },

      // Settings actions
      updateSettings: (settings) => {
        set((state) => {
          Object.assign(state.settings, settings);
        });
      },

      // Error actions
      setError: (key, error) => {
        set((state) => {
          state.errors[key] = error;
        });
      },

      clearError: (key) => {
        set((state) => {
          delete state.errors[key];
        });
      },

      clearAllErrors: () => {
        set((state) => {
          state.errors = {};
        });
      },

      // Reset to default state
      reset: () => {
        set((state) => {
          state.sidebar = defaultSidebarState;
          state.modal = defaultModalState;
          state.notifications = [];
          state.loading = {};
          state.errors = {};
          // Keep theme and settings as they are user preferences
        });
      },
    })),
    {
      name: 'app-store',
      storage: appStorage,
      // Only persist user preferences, not ephemeral state
      partialize: (state) => ({
        sidebar: {
          isCollapsed: state.sidebar.isCollapsed,
          // Don't persist activeSection
        },
        theme: state.theme,
        settings: state.settings,
      }),
    }
  )
);

// Convenience hooks for specific parts of the store
export const useNotifications = () =>
  useAppStore((state) => ({
    notifications: state.notifications,
    addNotification: state.addNotification,
    removeNotification: state.removeNotification,
    clearNotifications: state.clearNotifications,
  }));

export const useLoading = () =>
  useAppStore((state) => ({
    loading: state.loading,
    setLoading: state.setLoading,
    isLoading: state.isLoading,
  }));

export const useModal = () =>
  useAppStore((state) => ({
    modal: state.modal,
    openModal: state.openModal,
    closeModal: state.closeModal,
  }));

export const useSidebar = () =>
  useAppStore((state) => ({
    sidebar: state.sidebar,
    toggleSidebar: state.toggleSidebar,
    setSidebarSection: state.setSidebarSection,
  }));

export const useTheme = () =>
  useAppStore((state) => ({
    theme: state.theme,
    setTheme: state.setTheme,
  }));

export const useSettings = () =>
  useAppStore((state) => ({
    settings: state.settings,
    updateSettings: state.updateSettings,
  }));

export const useErrors = () =>
  useAppStore((state) => ({
    errors: state.errors,
    setError: state.setError,
    clearError: state.clearError,
    clearAllErrors: state.clearAllErrors,
  }));

// Global notification helpers
export const showSuccessNotification = (title: string, message: string) => {
  useAppStore.getState().addNotification({
    type: 'success',
    title,
    message,
  });
};

export const showErrorNotification = (title: string, message: string, duration = 0) => {
  useAppStore.getState().addNotification({
    type: 'error',
    title,
    message,
    duration,
  });
};

export const showWarningNotification = (title: string, message: string) => {
  useAppStore.getState().addNotification({
    type: 'warning',
    title,
    message,
  });
};

export const showInfoNotification = (title: string, message: string) => {
  useAppStore.getState().addNotification({
    type: 'info',
    title,
    message,
  });
};
