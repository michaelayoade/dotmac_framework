export interface PWAConfig {
  /** Service worker registration path */
  swPath?: string;
  /** Enable automatic updates */
  autoUpdate?: boolean;
  /** Update check interval (ms) */
  updateInterval?: number;
  /** Show install prompt */
  showInstallPrompt?: boolean;
  /** Install prompt delay (ms) */
  installPromptDelay?: number;
  /** Enable offline indicators */
  offlineIndicator?: boolean;
  /** Enable push notifications */
  pushNotifications?: boolean;
  /** Notification icon */
  notificationIcon?: string;
  /** App name for notifications */
  appName?: string;
}

export interface ServiceWorkerConfig {
  /** Service worker script path */
  scriptPath: string;
  /** Registration scope */
  scope?: string;
  /** Update via cache mode */
  updateViaCache?: 'imports' | 'all' | 'none';
  /** Enable automatic registration */
  autoRegister?: boolean;
  /** Enable update checks */
  enableUpdates?: boolean;
  /** Custom registration options */
  registrationOptions?: RegistrationOptions;
}

export interface InstallPromptOptions {
  /** Show prompt automatically */
  autoShow?: boolean;
  /** Delay before showing prompt (ms) */
  delay?: number;
  /** Minimum visits before showing */
  minVisits?: number;
  /** Days to wait before showing again after dismissal */
  dismissedDays?: number;
  /** Custom prompt component */
  customPrompt?: React.ComponentType<InstallPromptProps>;
  /** Prompt position */
  position?: 'top' | 'bottom' | 'center';
  /** Show close button */
  showClose?: boolean;
}

export interface InstallPromptProps {
  /** Show/hide the prompt */
  show: boolean;
  /** Handle install action */
  onInstall: () => void;
  /** Handle dismiss action */
  onDismiss: () => void;
  /** Is installation supported */
  canInstall: boolean;
  /** Platform information */
  platform: string;
}

export interface AppUpdateOptions {
  /** Automatically apply updates */
  autoApply?: boolean;
  /** Show update notification */
  showNotification?: boolean;
  /** Force refresh on update */
  forceRefresh?: boolean;
  /** Update notification timeout (ms) */
  notificationTimeout?: number;
  /** Custom update component */
  customNotification?: React.ComponentType<AppUpdateNotificationProps>;
}

export interface AppUpdateNotificationProps {
  /** Show/hide the notification */
  show: boolean;
  /** Handle update action */
  onUpdate: () => void;
  /** Handle dismiss action */
  onDismiss: () => void;
  /** Update details */
  updateInfo?: {
    version?: string;
    changelog?: string[];
    size?: number;
  };
}

export interface PWACapabilities {
  /** Service Worker support */
  serviceWorker: boolean;
  /** Add to home screen support */
  addToHomeScreen: boolean;
  /** Web App Manifest support */
  webAppManifest: boolean;
  /** Push notifications support */
  pushNotifications: boolean;
  /** Background sync support */
  backgroundSync: boolean;
  /** Cache API support */
  cacheAPI: boolean;
  /** IndexedDB support */
  indexedDB: boolean;
  /** Geolocation support */
  geolocation: boolean;
  /** Camera API support */
  camera: boolean;
  /** Device orientation support */
  deviceOrientation: boolean;
  /** Vibration API support */
  vibration: boolean;
  /** Web Share API support */
  webShare: boolean;
  /** Is running as PWA */
  isPWA: boolean;
  /** Is running in standalone mode */
  isStandalone: boolean;
  /** Platform information */
  platform: 'ios' | 'android' | 'desktop' | 'unknown';
}

export interface PushSubscriptionData {
  endpoint: string;
  keys: {
    p256dh: string;
    auth: string;
  };
  vapidPublicKey?: string;
}

export interface NotificationPayload {
  title: string;
  body?: string;
  icon?: string;
  badge?: string;
  image?: string;
  data?: any;
  tag?: string;
  requireInteraction?: boolean;
  actions?: Array<{
    action: string;
    title: string;
    icon?: string;
  }>;
}

export type ServiceWorkerMessage =
  | { type: 'SW_UPDATE_AVAILABLE'; payload: { version?: string } }
  | { type: 'SW_CACHE_UPDATED'; payload: { urls: string[] } }
  | { type: 'SW_OFFLINE_READY' }
  | { type: 'SW_ERROR'; payload: { error: string } }
  | { type: 'SW_BACKGROUND_SYNC'; payload: { tag: string; success: boolean } };

export interface BackgroundSyncOptions {
  /** Sync tag identifier */
  tag: string;
  /** Sync data payload */
  data?: any;
  /** Minimum interval between syncs (ms) */
  minInterval?: number;
  /** Maximum retries */
  maxRetries?: number;
}

export interface CacheStrategy {
  /** Strategy name */
  name: 'cacheFirst' | 'networkFirst' | 'staleWhileRevalidate' | 'networkOnly' | 'cacheOnly';
  /** URL pattern to match */
  urlPattern: string | RegExp;
  /** Cache name */
  cacheName?: string;
  /** Cache expiration */
  expiration?: {
    maxEntries?: number;
    maxAgeSeconds?: number;
  };
  /** Network timeout (ms) */
  networkTimeoutSeconds?: number;
}
