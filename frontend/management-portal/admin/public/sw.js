/**
 * Service Worker for Management Admin Portal
 * Provides offline capabilities, caching, and push notifications
 */

const CACHE_NAME = 'mgmt-admin-v1.0.0';
const RUNTIME_CACHE = 'mgmt-admin-runtime';
const OFFLINE_FALLBACK = 'mgmt-admin-offline';

// Resources to cache on install
const PRECACHE_RESOURCES = [
  '/',
  '/login',
  '/dashboard',
  '/offline',
  '/manifest.json',
  '/_next/static/css/app.css',
  '/favicon.ico',
];

// API endpoints that should be cached
const CACHEABLE_API_PATTERNS = [
  /^\/api\/auth\/me$/,
  /^\/api\/tenants\/\w+$/,
  /^\/api\/dashboard\/stats$/,
  /^\/api\/user\/profile$/,
];

// API endpoints that should never be cached
const NEVER_CACHE_PATTERNS = [
  /^\/api\/auth\/login$/,
  /^\/api\/auth\/logout$/,
  /^\/api\/auth\/refresh$/,
  /^\/api\/security\/events$/,
];

// Install event - precache resources
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker');

  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE_NAME);

      try {
        // Add precached resources
        await cache.addAll(PRECACHE_RESOURCES);
        console.log('[SW] Precached resources added');

        // Create offline fallback
        const offlineResponse = new Response(generateOfflinePage(), {
          status: 200,
          statusText: 'OK',
          headers: {
            'Content-Type': 'text/html; charset=utf-8',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
          },
        });

        const offlineCache = await caches.open(OFFLINE_FALLBACK);
        await offlineCache.put('/offline-fallback', offlineResponse);

        // Skip waiting to activate immediately
        self.skipWaiting();
      } catch (error) {
        console.error('[SW] Failed to precache resources:', error);
      }
    })()
  );
});

// Activate event - cleanup old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker');

  event.waitUntil(
    (async () => {
      // Clean up old caches
      const cacheNames = await caches.keys();
      const oldCaches = cacheNames.filter(
        (name) =>
          name.startsWith('mgmt-admin-') &&
          name !== CACHE_NAME &&
          name !== RUNTIME_CACHE &&
          name !== OFFLINE_FALLBACK
      );

      await Promise.all(
        oldCaches.map((cacheName) => {
          console.log('[SW] Deleting old cache:', cacheName);
          return caches.delete(cacheName);
        })
      );

      // Take control of all clients
      self.clients.claim();
    })()
  );
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests and external URLs
  if (request.method !== 'GET' || !url.origin.includes(self.location.origin)) {
    return;
  }

  // Handle different resource types
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(handleAPIRequest(request));
  } else if (url.pathname.startsWith('/_next/static/')) {
    event.respondWith(handleStaticAssets(request));
  } else if (url.pathname.match(/\.(js|css|png|jpg|jpeg|svg|ico|woff|woff2)$/)) {
    event.respondWith(handleAssets(request));
  } else {
    event.respondWith(handleNavigation(request));
  }
});

// Handle API requests with network-first strategy
async function handleAPIRequest(request) {
  const url = new URL(request.url);

  // Never cache certain endpoints
  if (NEVER_CACHE_PATTERNS.some((pattern) => pattern.test(url.pathname))) {
    return fetch(request);
  }

  try {
    // Try network first
    const response = await fetch(request);

    // Cache successful GET responses for cacheable endpoints
    if (response.ok && CACHEABLE_API_PATTERNS.some((pattern) => pattern.test(url.pathname))) {
      const cache = await caches.open(RUNTIME_CACHE);
      const clonedResponse = response.clone();

      // Add cache headers
      const headers = new Headers(clonedResponse.headers);
      headers.set('sw-cache-timestamp', Date.now().toString());

      const cachedResponse = new Response(await clonedResponse.blob(), {
        status: clonedResponse.status,
        statusText: clonedResponse.statusText,
        headers,
      });

      cache.put(request, cachedResponse);
    }

    return response;
  } catch (error) {
    console.log('[SW] Network failed for API request, checking cache:', url.pathname);

    // Try cache if network fails
    const cache = await caches.open(RUNTIME_CACHE);
    const cachedResponse = await cache.match(request);

    if (cachedResponse) {
      // Check if cached response is still valid (1 hour)
      const cacheTimestamp = cachedResponse.headers.get('sw-cache-timestamp');
      const isValid = cacheTimestamp && Date.now() - parseInt(cacheTimestamp) < 3600000;

      if (isValid) {
        console.log('[SW] Serving cached API response:', url.pathname);
        return cachedResponse;
      } else {
        // Remove expired cache entry
        cache.delete(request);
      }
    }

    // Return offline API response for critical endpoints
    if (url.pathname === '/api/auth/me') {
      return new Response(
        JSON.stringify({ error: 'offline', message: 'User data unavailable offline' }),
        {
          status: 503,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    throw error;
  }
}

// Handle static assets with cache-first strategy
async function handleStaticAssets(request) {
  const cache = await caches.open(CACHE_NAME);
  const cachedResponse = await cache.match(request);

  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    console.log('[SW] Failed to fetch static asset:', request.url);
    throw error;
  }
}

// Handle other assets with cache-first strategy
async function handleAssets(request) {
  const cache = await caches.open(RUNTIME_CACHE);
  const cachedResponse = await cache.match(request);

  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    console.log('[SW] Failed to fetch asset:', request.url);
    throw error;
  }
}

// Handle navigation with network-first, cache fallback
async function handleNavigation(request) {
  try {
    const response = await fetch(request);

    // Cache successful navigation responses
    if (response.ok) {
      const cache = await caches.open(RUNTIME_CACHE);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    console.log('[SW] Network failed for navigation, checking cache:', request.url);

    // Try cache first
    const cache = await caches.open(RUNTIME_CACHE);
    const cachedResponse = await cache.match(request);

    if (cachedResponse) {
      return cachedResponse;
    }

    // Try precache
    const precache = await caches.open(CACHE_NAME);
    const precachedResponse = await precache.match(request);

    if (precachedResponse) {
      return precachedResponse;
    }

    // Return offline fallback
    const offlineCache = await caches.open(OFFLINE_FALLBACK);
    const offlineResponse = await offlineCache.match('/offline-fallback');

    return (
      offlineResponse ||
      new Response('Offline - Please check your connection', {
        status: 503,
        headers: { 'Content-Type': 'text/plain' },
      })
    );
  }
}

// Push notification event
self.addEventListener('push', (event) => {
  console.log('[SW] Push message received:', event);

  const options = {
    body: 'New notification from Management Admin Portal',
    icon: '/favicon.ico',
    badge: '/favicon.ico',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: '1',
    },
    actions: [
      {
        action: 'view',
        title: 'View',
        icon: '/icons/view.png',
      },
      {
        action: 'dismiss',
        title: 'Dismiss',
        icon: '/icons/dismiss.png',
      },
    ],
  };

  if (event.data) {
    const data = event.data.json();
    options.body = data.message || options.body;
    options.data = { ...options.data, ...data };
  }

  event.waitUntil(self.registration.showNotification('Management Admin Portal', options));
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification click received:', event);

  event.notification.close();

  if (event.action === 'view') {
    event.waitUntil(clients.openWindow('/dashboard'));
  } else if (event.action === 'dismiss') {
    // Just close the notification
    return;
  } else {
    // Default action - open the app
    event.waitUntil(
      clients.matchAll().then((clientList) => {
        for (const client of clientList) {
          if (client.url === '/' && 'focus' in client) {
            return client.focus();
          }
        }
        if (clients.openWindow) {
          return clients.openWindow('/dashboard');
        }
      })
    );
  }
});

// Background sync event
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync event:', event.tag);

  if (event.tag === 'sync-pending-operations') {
    event.waitUntil(syncPendingOperations());
  }
});

// Message event - handle messages from the client
self.addEventListener('message', (event) => {
  console.log('[SW] Message received:', event.data);

  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  } else if (event.data.type === 'CACHE_CONFIG') {
    // Update cache configuration
    console.log('[SW] Cache configuration updated:', event.data.config);
  } else if (event.data.type === 'CLEAR_CACHE') {
    clearCache().then(() => {
      event.ports[0].postMessage({ success: true });
    });
  }
});

// Helper functions
async function syncPendingOperations() {
  try {
    // In a real implementation, you would:
    // 1. Get pending operations from IndexedDB
    // 2. Retry failed API calls
    // 3. Update local data
    console.log('[SW] Syncing pending operations...');

    // Placeholder for actual sync logic
    const pendingOperations = []; // Get from IndexedDB

    for (const operation of pendingOperations) {
      try {
        await fetch(operation.url, operation.options);
        // Remove from pending operations
      } catch (error) {
        console.log('[SW] Failed to sync operation:', operation, error);
      }
    }
  } catch (error) {
    console.error('[SW] Background sync failed:', error);
  }
}

async function clearCache() {
  const cacheNames = await caches.keys();
  await Promise.all(cacheNames.map((cacheName) => caches.delete(cacheName)));
  console.log('[SW] All caches cleared');
}

function generateOfflinePage() {
  return `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Offline - Management Admin Portal</title>
      <style>
        body {
          font-family: system-ui, -apple-system, sans-serif;
          margin: 0;
          padding: 0;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
        }
        .container {
          text-align: center;
          max-width: 500px;
          padding: 2rem;
        }
        .icon {
          font-size: 4rem;
          margin-bottom: 1rem;
          opacity: 0.8;
        }
        h1 {
          font-size: 2rem;
          margin-bottom: 1rem;
          font-weight: 300;
        }
        p {
          font-size: 1.1rem;
          margin-bottom: 2rem;
          opacity: 0.9;
          line-height: 1.6;
        }
        .retry-button {
          background: rgba(255, 255, 255, 0.2);
          border: 2px solid rgba(255, 255, 255, 0.3);
          color: white;
          padding: 1rem 2rem;
          border-radius: 50px;
          font-size: 1rem;
          cursor: pointer;
          transition: all 0.3s ease;
          backdrop-filter: blur(10px);
        }
        .retry-button:hover {
          background: rgba(255, 255, 255, 0.3);
          border-color: rgba(255, 255, 255, 0.5);
          transform: translateY(-2px);
        }
        .status {
          margin-top: 2rem;
          font-size: 0.9rem;
          opacity: 0.7;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="icon">📡</div>
        <h1>You're Offline</h1>
        <p>
          Don't worry! You can still access some features of the Management Admin Portal.
          Your changes will be synced when you reconnect.
        </p>
        <button class="retry-button" onclick="window.location.reload()">
          Try Again
        </button>
        <div class="status">
          Service Worker Active • Offline Cache Enabled
        </div>
      </div>
      
      <script>
        // Check for connection every 5 seconds
        setInterval(() => {
          if (navigator.onLine) {
            window.location.reload();
          }
        }, 5000);
        
        // Listen for online event
        window.addEventListener('online', () => {
          window.location.reload();
        });
      </script>
    </body>
    </html>
  `;
}

console.log('[SW] Service worker script loaded');
