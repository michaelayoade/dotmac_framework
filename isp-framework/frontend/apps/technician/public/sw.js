/* eslint-disable no-restricted-globals */

const CACHE_NAME = 'dotmac-technician-v1.1.0';
const STATIC_CACHE_NAME = 'dotmac-static-v1.1.0';
const DATA_CACHE_NAME = 'dotmac-data-v1.1.0';
const IMAGES_CACHE_NAME = 'dotmac-images-v1.1.0';
const OFFLINE_QUEUE_NAME = 'dotmac-offline-queue-v1.1.0';

// Assets to cache immediately
const STATIC_ASSETS = [
  '/',
  '/offline',
  '/manifest.json',
  '/_next/static/css/app/globals.css',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
];

// API endpoints to cache
const API_ENDPOINTS = [
  '/api/work-orders',
  '/api/customers',
  '/api/inventory',
  '/api/technician/profile',
];

// Network-first strategy for critical API endpoints
const NETWORK_FIRST_PATTERNS = [
  /\/api\/work-orders\/\d+\/complete/,
  /\/api\/sync/,
  /\/api\/upload/,
];

// Cache-first strategy for static resources
const CACHE_FIRST_PATTERNS = [
  /\/_next\/static\//,
  /\/icons\//,
  /\.(?:png|jpg|jpeg|svg|gif|webp)$/,
  /\.(?:css|js)$/,
];

// Stale-while-revalidate for data
const SWR_PATTERNS = [/\/api\/customers\//, /\/api\/work-orders\//, /\/api\/inventory\//];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[ServiceWorker] Install');

  event.waitUntil(
    (async () => {
      const cache = await caches.open(STATIC_CACHE_NAME);
      console.log('[ServiceWorker] Caching static assets');
      await cache.addAll(STATIC_ASSETS);

      // Skip waiting to activate immediately
      self.skipWaiting();
    })()
  );
});

// Activate event - cleanup old caches
self.addEventListener('activate', (event) => {
  console.log('[ServiceWorker] Activate');

  event.waitUntil(
    (async () => {
      const cacheNames = await caches.keys();
      await Promise.all(
        cacheNames
          .filter(
            (cacheName) =>
              cacheName.startsWith('dotmac-') &&
              ![CACHE_NAME, STATIC_CACHE_NAME, DATA_CACHE_NAME].includes(cacheName)
          )
          .map((cacheName) => {
            console.log('[ServiceWorker] Deleting old cache:', cacheName);
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

  // Skip non-GET requests and cross-origin requests (except API)
  if (request.method !== 'GET') {
    if (request.method === 'POST' && url.pathname.startsWith('/api/sync')) {
      event.respondWith(handleSyncRequest(request));
    }
    return;
  }

  // Handle different request types with appropriate strategies
  event.respondWith(handleRequest(request));
});

async function handleRequest(request) {
  const url = new URL(request.url);

  try {
    // Network-first for critical API endpoints
    if (NETWORK_FIRST_PATTERNS.some((pattern) => pattern.test(url.pathname))) {
      return await networkFirst(request);
    }

    // Cache-first for static resources
    if (CACHE_FIRST_PATTERNS.some((pattern) => pattern.test(url.pathname))) {
      return await cacheFirst(request);
    }

    // Stale-while-revalidate for data
    if (SWR_PATTERNS.some((pattern) => pattern.test(url.pathname))) {
      return await staleWhileRevalidate(request);
    }

    // Default to network with fallback
    return await networkWithFallback(request);
  } catch (error) {
    console.error('[ServiceWorker] Fetch failed:', error);
    return await handleOffline(request);
  }
}

// Network-first strategy
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);

    if (networkResponse.ok) {
      const cache = await caches.open(DATA_CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    console.log('[ServiceWorker] Network failed, trying cache:', request.url);
    const cachedResponse = await caches.match(request);

    if (cachedResponse) {
      return cachedResponse;
    }

    throw error;
  }
}

// Cache-first strategy
async function cacheFirst(request) {
  const cachedResponse = await caches.match(request);

  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);

    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    console.log('[ServiceWorker] Cache and network failed:', request.url);
    throw error;
  }
}

// Stale-while-revalidate strategy
async function staleWhileRevalidate(request) {
  const cachedResponse = await caches.match(request);

  // Always try to update the cache in the background
  const networkResponsePromise = fetch(request)
    .then(async (response) => {
      if (response.ok) {
        const cache = await caches.open(DATA_CACHE_NAME);
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch((error) => {
      console.log('[ServiceWorker] Background update failed:', error);
      return null;
    });

  // Return cached response immediately if available
  if (cachedResponse) {
    networkResponsePromise; // Update cache in background
    return cachedResponse;
  }

  // If no cached response, wait for network
  try {
    return await networkResponsePromise;
  } catch (error) {
    throw error;
  }
}

// Network with cache fallback
async function networkWithFallback(request) {
  try {
    const networkResponse = await fetch(request);

    if (networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    const cachedResponse = await caches.match(request);

    if (cachedResponse) {
      return cachedResponse;
    }

    return await handleOffline(request);
  }
}

// Handle offline scenarios
async function handleOffline(request) {
  const url = new URL(request.url);

  // Return offline page for navigation requests
  if (request.mode === 'navigate') {
    const offlineResponse = await caches.match('/offline');
    if (offlineResponse) {
      return offlineResponse;
    }
  }

  // Return cached version or 404
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }

  // Return a generic offline response
  return new Response(
    JSON.stringify({
      error: 'Offline',
      message: 'You are offline and this content is not cached',
      url: request.url,
    }),
    {
      status: 503,
      statusText: 'Service Unavailable',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );
}

// Handle sync requests (for background sync)
async function handleSyncRequest(request) {
  try {
    // Try to send the request
    const response = await fetch(request);

    if (response.ok) {
      // Remove from pending sync queue
      const data = await request.json();
      await clearPendingSync(data.id);
    }

    return response;
  } catch (error) {
    // Store for later sync
    const data = await request.json();
    await storePendingSync(data);

    return new Response(JSON.stringify({ queued: true, id: data.id }), {
      status: 202,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

// Background sync functionality
self.addEventListener('sync', (event) => {
  if (event.tag === 'work-order-sync') {
    console.log('[ServiceWorker] Background sync: work-order-sync');
    event.waitUntil(syncPendingWorkOrders());
  }

  if (event.tag === 'inventory-sync') {
    console.log('[ServiceWorker] Background sync: inventory-sync');
    event.waitUntil(syncPendingInventory());
  }

  if (event.tag === 'photos-sync') {
    console.log('[ServiceWorker] Background sync: photos-sync');
    event.waitUntil(syncPendingPhotos());
  }
});

async function syncPendingWorkOrders() {
  try {
    const pendingData = await getPendingSync('work-orders');

    for (const item of pendingData) {
      try {
        await fetch('/api/work-orders/sync', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(item.data),
        });

        await clearPendingSync(item.id);
      } catch (error) {
        console.log('[ServiceWorker] Failed to sync work order:', item.id, error);
      }
    }
  } catch (error) {
    console.error('[ServiceWorker] Background sync failed:', error);
  }
}

async function syncPendingInventory() {
  try {
    const pendingData = await getPendingSync('inventory');

    for (const item of pendingData) {
      try {
        await fetch('/api/inventory/sync', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(item.data),
        });

        await clearPendingSync(item.id);
      } catch (error) {
        console.log('[ServiceWorker] Failed to sync inventory:', item.id, error);
      }
    }
  } catch (error) {
    console.error('[ServiceWorker] Inventory sync failed:', error);
  }
}

async function syncPendingPhotos() {
  try {
    const pendingData = await getPendingSync('photos');

    for (const item of pendingData) {
      try {
        const formData = new FormData();
        formData.append('photo', item.data.photo);
        formData.append('workOrderId', item.data.workOrderId);
        formData.append('metadata', JSON.stringify(item.data.metadata));

        await fetch('/api/photos/upload', {
          method: 'POST',
          body: formData,
        });

        await clearPendingSync(item.id);
      } catch (error) {
        console.log('[ServiceWorker] Failed to sync photo:', item.id, error);
      }
    }
  } catch (error) {
    console.error('[ServiceWorker] Photos sync failed:', error);
  }
}

// Utility functions for IndexedDB operations
async function storePendingSync(data) {
  // This would use IndexedDB to store pending sync data
  console.log('[ServiceWorker] Storing pending sync:', data);
}

async function getPendingSync(type) {
  // This would retrieve pending sync data from IndexedDB
  console.log('[ServiceWorker] Getting pending sync for:', type);
  return [];
}

async function clearPendingSync(id) {
  // This would remove synced data from IndexedDB
  console.log('[ServiceWorker] Clearing pending sync:', id);
}

// Push notification handling
self.addEventListener('push', (event) => {
  console.log('[ServiceWorker] Push received:', event);

  const options = {
    body: 'New work order assigned',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/icon-96x96.png',
    data: {
      url: '/work-orders',
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
    requireInteraction: true,
    tag: 'work-order',
    renotify: true,
  };

  event.waitUntil(self.registration.showNotification('DotMac Technician', options));
});

// Notification click handling
self.addEventListener('notificationclick', (event) => {
  console.log('[ServiceWorker] Notification click:', event);

  event.notification.close();

  if (event.action === 'view') {
    event.waitUntil(clients.openWindow(event.notification.data.url));
  }
});

// Message handling for communication with main thread
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'GET_VERSION') {
    event.ports[0].postMessage({ version: CACHE_NAME });
  }
});
