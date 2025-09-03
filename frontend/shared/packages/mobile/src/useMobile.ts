import { useMobileContext } from './MobileProvider';
import { useMobileOfflineSync } from './offline/useMobileOfflineSync';
import { useMobileCache } from './offline/useMobileCache';
import { usePWA } from './pwa/usePWA';

export function useMobile() {
  const context = useMobileContext();

  // Initialize mobile features based on config
  const offlineSync = useMobileOfflineSync(context.config.offline);
  const cache = useMobileCache(context.config.cache);
  const pwa = usePWA(context.config.pwa);

  return {
    // Device context
    ...context,

    // Offline capabilities
    offline: offlineSync,
    cache,

    // PWA capabilities
    pwa,

    // Utility methods
    utils: {
      /** Check if device is in landscape mode */
      isLandscape: () => context.orientation === 'landscape',

      /** Check if device is in portrait mode */
      isPortrait: () => context.orientation === 'portrait',

      /** Get device pixel ratio */
      getPixelRatio: () => window.devicePixelRatio || 1,

      /** Check if device is in low power mode (estimated) */
      isLowPowerMode: () => {
        return context.battery ? !context.battery.charging && context.battery.level < 20 : false;
      },

      /** Check if connection is slow */
      isSlowConnection: () => {
        return (
          context.network.effectiveType === '2g' || context.network.effectiveType === 'slow-2g'
        );
      },

      /** Get safe area insets */
      getSafeAreaInsets: () => {
        const style = getComputedStyle(document.documentElement);
        return {
          top: parseInt(style.getPropertyValue('--safe-area-top') || '0', 10),
          bottom: parseInt(style.getPropertyValue('--safe-area-bottom') || '0', 10),
          left: parseInt(style.getPropertyValue('--safe-area-left') || '0', 10),
          right: parseInt(style.getPropertyValue('--safe-area-right') || '0', 10),
        };
      },

      /** Vibrate device (if supported) */
      vibrate: (pattern: number | number[] = 200) => {
        if ('vibrate' in navigator) {
          navigator.vibrate(pattern);
        }
      },

      /** Share content (if supported) */
      share: async (data: { title?: string; text?: string; url?: string }) => {
        return await pwa.shareContent(data);
      },
    },
  };
}
