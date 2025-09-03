export type NotificationType = 'info' | 'success' | 'warning' | 'error';

export interface MobileNotificationOptions {
  /** Show native browser notifications if permission granted */
  useNativeNotifications?: boolean;
  /** Show in-app toast notifications */
  useInAppNotifications?: boolean;
  /** Auto-hide timeout in ms */
  autoHideTimeout?: number;
  /** Maximum number of notifications to show */
  maxNotifications?: number;
}

export interface NotificationData {
  id: string;
  title: string;
  message: string;
  type: NotificationType;
  timestamp: number;
  autoHide?: boolean;
  persistent?: boolean;
}

export class OfflineNotificationManager {
  private notifications: NotificationData[] = [];
  private listeners: Set<(notifications: NotificationData[]) => void> = new Set();
  private options: Required<MobileNotificationOptions>;

  constructor(options: MobileNotificationOptions = {}) {
    this.options = {
      useNativeNotifications: true,
      useInAppNotifications: true,
      autoHideTimeout: 5000,
      maxNotifications: 5,
      ...options,
    };

    this.requestPermission();
  }

  private async requestPermission(): Promise<void> {
    if (!this.options.useNativeNotifications) return;

    if ('Notification' in window && Notification.permission === 'default') {
      try {
        await Notification.requestPermission();
      } catch (error) {
        console.warn('Failed to request notification permission:', error);
      }
    }
  }

  private generateId(): string {
    return Date.now().toString() + Math.random().toString(36).substr(2, 9);
  }

  private notifyListeners(): void {
    this.listeners.forEach((listener) => {
      try {
        listener([...this.notifications]);
      } catch (error) {
        console.warn('Notification listener error:', error);
      }
    });
  }

  private async showNativeNotification(
    title: string,
    message: string,
    type: NotificationType
  ): Promise<void> {
    if (!this.options.useNativeNotifications) return;
    if (!('Notification' in window)) return;
    if (Notification.permission !== 'granted') return;

    try {
      const icon = this.getTypeIcon(type);
      const notification = new Notification(title, {
        body: message,
        icon,
        badge: icon,
        tag: `dotmac-mobile-${type}`,
        requireInteraction: type === 'error',
        silent: type === 'info',
      });

      // Auto-close non-error notifications
      if (type !== 'error') {
        setTimeout(() => {
          notification.close();
        }, this.options.autoHideTimeout);
      }

      // Handle click
      notification.onclick = () => {
        notification.close();
        // Focus the app if possible
        if (window.focus) {
          window.focus();
        }
      };
    } catch (error) {
      console.warn('Failed to show native notification:', error);
    }
  }

  private getTypeIcon(type: NotificationType): string {
    const baseUrl = '/icons'; // Adjust path as needed
    const iconMap = {
      info: `${baseUrl}/info.png`,
      success: `${baseUrl}/success.png`,
      warning: `${baseUrl}/warning.png`,
      error: `${baseUrl}/error.png`,
    };

    return iconMap[type] || iconMap.info;
  }

  private removeExpiredNotifications(): void {
    const now = Date.now();
    const expiredThreshold = 30 * 60 * 1000; // 30 minutes

    this.notifications = this.notifications.filter(
      (notification) => notification.persistent || now - notification.timestamp < expiredThreshold
    );
  }

  showNotification(
    title: string,
    message: string,
    type: NotificationType = 'info',
    options: {
      persistent?: boolean;
      autoHide?: boolean;
    } = {}
  ): string {
    const id = this.generateId();
    const notification: NotificationData = {
      id,
      title,
      message,
      type,
      timestamp: Date.now(),
      persistent: options.persistent || type === 'error',
      autoHide: options.autoHide ?? type !== 'error',
    };

    // Show native notification
    this.showNativeNotification(title, message, type);

    // Add to in-app notifications if enabled
    if (this.options.useInAppNotifications) {
      this.notifications.unshift(notification);

      // Limit number of notifications
      if (this.notifications.length > this.options.maxNotifications) {
        this.notifications = this.notifications.slice(0, this.options.maxNotifications);
      }

      // Auto-hide if specified
      if (notification.autoHide) {
        setTimeout(() => {
          this.hideNotification(id);
        }, this.options.autoHideTimeout);
      }

      this.notifyListeners();
    }

    // Clean up expired notifications
    this.removeExpiredNotifications();

    return id;
  }

  hideNotification(id: string): void {
    const index = this.notifications.findIndex((n) => n.id === id);
    if (index !== -1) {
      this.notifications.splice(index, 1);
      this.notifyListeners();
    }
  }

  clearAllNotifications(): void {
    this.notifications = [];
    this.notifyListeners();
  }

  clearByType(type: NotificationType): void {
    this.notifications = this.notifications.filter((n) => n.type !== type);
    this.notifyListeners();
  }

  getNotifications(): NotificationData[] {
    return [...this.notifications];
  }

  getNotificationsByType(type: NotificationType): NotificationData[] {
    return this.notifications.filter((n) => n.type === type);
  }

  subscribe(listener: (notifications: NotificationData[]) => void): () => void {
    this.listeners.add(listener);

    // Send current notifications immediately
    listener([...this.notifications]);

    // Return unsubscribe function
    return () => {
      this.listeners.delete(listener);
    };
  }

  // Convenience methods for different types
  showInfo(title: string, message: string, persistent = false): string {
    return this.showNotification(title, message, 'info', { persistent });
  }

  showSuccess(title: string, message: string, persistent = false): string {
    return this.showNotification(title, message, 'success', { persistent });
  }

  showWarning(title: string, message: string, persistent = false): string {
    return this.showNotification(title, message, 'warning', { persistent });
  }

  showError(title: string, message: string, persistent = true): string {
    return this.showNotification(title, message, 'error', { persistent });
  }

  // Sync-specific notifications
  showSyncStarted(operationCount: number): string {
    return this.showInfo('Sync Started', `Synchronizing ${operationCount} operations...`);
  }

  showSyncComplete(synced: number, failed: number): string {
    if (failed === 0) {
      return this.showSuccess('Sync Complete', `Successfully synchronized ${synced} operations`);
    } else {
      return this.showWarning('Sync Completed with Errors', `Synced: ${synced}, Failed: ${failed}`);
    }
  }

  showSyncError(error: string): string {
    return this.showError('Sync Failed', `Synchronization failed: ${error}`);
  }

  showStorageWarning(usagePercent: number): string {
    return this.showWarning(
      'Storage Almost Full',
      `${usagePercent}% of storage used. Consider clearing old data.`
    );
  }

  showNetworkStatus(isOnline: boolean): string {
    if (isOnline) {
      return this.showInfo('Back Online', 'Network connection restored. Sync will resume.', false);
    } else {
      return this.showWarning(
        'Offline',
        'No network connection. Changes will be saved and synced when online.',
        false
      );
    }
  }
}
