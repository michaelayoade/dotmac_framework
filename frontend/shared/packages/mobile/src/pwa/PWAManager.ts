import { ServiceWorkerManager } from './ServiceWorkerManager';
import { PWAConfig, PWACapabilities, NotificationPayload, PushSubscriptionData } from './types';

export class PWAManager {
  private config: Required<PWAConfig>;
  private serviceWorkerManager: ServiceWorkerManager;
  private capabilities: PWACapabilities | null = null;
  private installPromptEvent: any = null;
  private pushSubscription: PushSubscription | null = null;

  constructor(config: PWAConfig = {}) {
    this.config = {
      swPath: '/sw.js',
      autoUpdate: true,
      updateInterval: 60000, // 1 minute
      showInstallPrompt: true,
      installPromptDelay: 10000, // 10 seconds
      offlineIndicator: true,
      pushNotifications: false,
      notificationIcon: '/icons/notification-icon.png',
      appName: 'DotMac ISP',
      ...config,
    };

    this.serviceWorkerManager = new ServiceWorkerManager({
      scriptPath: this.config.swPath,
      autoRegister: true,
      enableUpdates: this.config.autoUpdate,
    });

    this.initialize();
  }

  private async initialize(): Promise<void> {
    try {
      // Detect PWA capabilities
      this.capabilities = await this.detectCapabilities();

      // Setup service worker
      if (this.capabilities.serviceWorker) {
        await this.setupServiceWorker();
      }

      // Setup install prompt
      if (this.config.showInstallPrompt && this.capabilities.addToHomeScreen) {
        this.setupInstallPrompt();
      }

      // Setup push notifications
      if (this.config.pushNotifications && this.capabilities.pushNotifications) {
        await this.setupPushNotifications();
      }

      // Setup offline indicator
      if (this.config.offlineIndicator) {
        this.setupOfflineIndicator();
      }

      console.log('PWA Manager initialized', this.capabilities);
    } catch (error) {
      console.error('Failed to initialize PWA Manager:', error);
    }
  }

  private async detectCapabilities(): Promise<PWACapabilities> {
    const capabilities: PWACapabilities = {
      serviceWorker: 'serviceWorker' in navigator,
      addToHomeScreen: 'serviceWorker' in navigator && 'standalone' in (window as any),
      webAppManifest: 'serviceWorker' in navigator,
      pushNotifications: 'serviceWorker' in navigator && 'PushManager' in window,
      backgroundSync:
        'serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration?.prototype,
      cacheAPI: 'caches' in window,
      indexedDB: 'indexedDB' in window,
      geolocation: 'geolocation' in navigator,
      camera: 'mediaDevices' in navigator && 'getUserMedia' in navigator.mediaDevices,
      deviceOrientation: 'DeviceOrientationEvent' in window,
      vibration: 'vibrate' in navigator,
      webShare: 'share' in navigator,
      isPWA: this.isPWAMode(),
      isStandalone: this.isStandaloneMode(),
      platform: this.detectPlatform(),
    };

    return capabilities;
  }

  private isPWAMode(): boolean {
    return (
      window.matchMedia('(display-mode: standalone)').matches ||
      (window as any).navigator?.standalone === true ||
      document.referrer.includes('android-app://')
    );
  }

  private isStandaloneMode(): boolean {
    return (
      window.matchMedia('(display-mode: standalone)').matches ||
      (window as any).navigator?.standalone === true
    );
  }

  private detectPlatform(): 'ios' | 'android' | 'desktop' | 'unknown' {
    const userAgent = navigator.userAgent.toLowerCase();

    if (/iphone|ipad|ipod/.test(userAgent)) {
      return 'ios';
    } else if (/android/.test(userAgent)) {
      return 'android';
    } else if (/windows|mac|linux/.test(userAgent)) {
      return 'desktop';
    }

    return 'unknown';
  }

  private async setupServiceWorker(): Promise<void> {
    try {
      await this.serviceWorkerManager.register();

      // Setup update checker
      if (this.config.autoUpdate) {
        setInterval(async () => {
          await this.serviceWorkerManager.checkForUpdates();
        }, this.config.updateInterval);
      }
    } catch (error) {
      console.error('Service Worker setup failed:', error);
    }
  }

  private setupInstallPrompt(): void {
    window.addEventListener('beforeinstallprompt', (event) => {
      event.preventDefault();
      this.installPromptEvent = event;

      // Show install prompt after delay
      setTimeout(() => {
        this.showInstallPrompt();
      }, this.config.installPromptDelay);
    });

    // Handle successful installation
    window.addEventListener('appinstalled', (event) => {
      console.log('PWA was installed successfully');
      this.installPromptEvent = null;
    });
  }

  private async setupPushNotifications(): Promise<void> {
    try {
      const permission = await Notification.requestPermission();

      if (permission === 'granted') {
        const registration = await this.serviceWorkerManager.getRegistration();

        if (registration) {
          this.pushSubscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: this.urlBase64ToUint8Array(
              process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY || ''
            ),
          });

          console.log('Push subscription created:', this.pushSubscription);
        }
      }
    } catch (error) {
      console.error('Push notification setup failed:', error);
    }
  }

  private setupOfflineIndicator(): void {
    const updateOnlineStatus = () => {
      const isOnline = navigator.onLine;
      document.body.classList.toggle('app-offline', !isOnline);

      // Dispatch custom event
      window.dispatchEvent(
        new CustomEvent('pwa:network-status', {
          detail: { online: isOnline },
        })
      );

      // Show notification
      if (!isOnline) {
        this.showNotification({
          title: "You're offline",
          body: 'Some features may not be available',
          icon: this.config.notificationIcon,
          tag: 'offline-indicator',
        });
      }
    };

    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);

    // Initial status
    updateOnlineStatus();
  }

  private urlBase64ToUint8Array(base64String: string): Uint8Array {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/\\-/g, '+').replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  // Public API
  public getCapabilities(): PWACapabilities | null {
    return this.capabilities;
  }

  public async showInstallPrompt(): Promise<boolean> {
    if (!this.installPromptEvent) {
      console.warn('Install prompt not available');
      return false;
    }

    try {
      this.installPromptEvent.prompt();
      const { outcome } = await this.installPromptEvent.userChoice;

      if (outcome === 'accepted') {
        console.log('User accepted the install prompt');
        return true;
      } else {
        console.log('User dismissed the install prompt');
        return false;
      }
    } catch (error) {
      console.error('Install prompt failed:', error);
      return false;
    }
  }

  public async showNotification(payload: NotificationPayload): Promise<void> {
    if (!this.capabilities?.pushNotifications || Notification.permission !== 'granted') {
      console.warn('Notifications not available or not permitted');
      return;
    }

    try {
      const registration = await this.serviceWorkerManager.getRegistration();

      if (registration) {
        await registration.showNotification(payload.title, {
          body: payload.body,
          icon: payload.icon || this.config.notificationIcon,
          badge: payload.badge,
          image: payload.image,
          data: payload.data,
          tag: payload.tag,
          requireInteraction: payload.requireInteraction,
          actions: payload.actions,
        });
      } else {
        // Fallback to simple notification
        new Notification(payload.title, {
          body: payload.body,
          icon: payload.icon || this.config.notificationIcon,
        });
      }
    } catch (error) {
      console.error('Failed to show notification:', error);
    }
  }

  public async requestPushSubscription(): Promise<PushSubscriptionData | null> {
    if (!this.capabilities?.pushNotifications) {
      return null;
    }

    try {
      const permission = await Notification.requestPermission();

      if (permission !== 'granted') {
        return null;
      }

      const registration = await this.serviceWorkerManager.getRegistration();

      if (!registration) {
        return null;
      }

      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: this.urlBase64ToUint8Array(
          process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY || ''
        ),
      });

      const p256dh = btoa(String.fromCharCode(...new Uint8Array(subscription.getKey('p256dh')!)))
        .replace(/\\+/g, '-')
        .replace(/\\/ / g, '_')
        .replace(/=+$/, '');

      const auth = btoa(String.fromCharCode(...new Uint8Array(subscription.getKey('auth')!)))
        .replace(/\\+/g, '-')
        .replace(/\\/ / g, '_')
        .replace(/=+$/, '');

      return {
        endpoint: subscription.endpoint,
        keys: { p256dh, auth },
        vapidPublicKey: process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY,
      };
    } catch (error) {
      console.error('Failed to create push subscription:', error);
      return null;
    }
  }

  public async share(data: { title?: string; text?: string; url?: string }): Promise<boolean> {
    if (!this.capabilities?.webShare) {
      return false;
    }

    try {
      await navigator.share(data);
      return true;
    } catch (error) {
      console.error('Web share failed:', error);
      return false;
    }
  }

  public async updateApp(): Promise<void> {
    await this.serviceWorkerManager.skipWaiting();
  }

  public async clearCache(): Promise<void> {
    if (this.capabilities?.cacheAPI) {
      const cacheNames = await caches.keys();
      await Promise.all(cacheNames.map((cacheName) => caches.delete(cacheName)));
    }
  }

  public isInstalled(): boolean {
    return this.capabilities?.isPWA || false;
  }

  public isStandalone(): boolean {
    return this.capabilities?.isStandalone || false;
  }

  public getPlatform(): string {
    return this.capabilities?.platform || 'unknown';
  }
}
