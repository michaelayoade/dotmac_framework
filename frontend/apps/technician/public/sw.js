/**
 * Service Worker for Technician App
 * Provides offline capabilities, caching, and background sync
 */

const CACHE_NAME = 'technician-app-v1';
const CACHE_VERSION = 1;
const OFFLINE_URL = '/offline.html';

// Assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/offline.html',
  '/manifest.json',
  // Add your static assets here
];

// API routes that should be cached
const API_CACHE_PATTERNS = [
  /\/api\/work-orders/,
  /\/api\/customers/,
  /\/api\/inventory/,
  /\/api\/technician/,
];

// Routes that should always be fresh (no cache)
const NO_CACHE_PATTERNS = [
  /\/api\/auth/,
  /\/api\/sync/,
  /\/api\/upload/,
];

// Maximum age for cached responses (24 hours)
const MAX_CACHE_AGE = 24 * 60 * 60 * 1000;

// Background sync tags
const SYNC_TAGS = {
  WORK_ORDER_UPDATE: 'work-order-update',
  PHOTO_UPLOAD: 'photo-upload',
  LOCATION_UPDATE: 'location-update',
  INVENTORY_UPDATE: 'inventory-update',
};

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  
  event.waitUntil(
    Promise.all([
      caches.open(CACHE_NAME).then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      }),
      self.skipWaiting()
    ])
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  
  event.waitUntil(
    Promise.all([
      // Clean up old caches
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((cacheName) => {
              return cacheName !== CACHE_NAME;
            })
            .map((cacheName) => {
              console.log('[SW] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            })
        );
      }),
      
      // Take control of all clients
      self.clients.claim()
    ])
  );
});

// Fetch event - handle network requests
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests for now
  if (request.method !== 'GET') {
    return;
  }

  // Skip chrome-extension requests
  if (url.protocol === 'chrome-extension:') {
    return;
  }

  // Handle different types of requests
  if (isApiRequest(url)) {
    event.respondWith(handleApiRequest(request));
  } else if (isNavigationRequest(request)) {
    event.respondWith(handleNavigationRequest(request));
  } else {
    event.respondWith(handleStaticAssetRequest(request));
  }
});

// Message event - handle messages from main thread
self.addEventListener('message', (event) => {
  const { type, payload } = event.data;

  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
    
    case 'GET_VERSION':
      event.ports[0].postMessage({ version: CACHE_VERSION });
      break;
    
    case 'CLEAR_CACHE':
      clearAllCaches().then(() => {
        event.ports[0].postMessage({ success: true });
      });
      break;
    
    case 'CACHE_URLS':
      cacheUrls(payload.urls).then(() => {
        event.ports[0].postMessage({ success: true });
      });
      break;

    case 'PREFETCH_CRITICAL':
      prefetchCriticalData().then(() => {
        event.ports[0].postMessage({ success: true });
      });
      break;
  }
});

// Background sync event
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync:', event.tag);

  switch (event.tag) {
    case SYNC_TAGS.WORK_ORDER_UPDATE:
      event.waitUntil(syncWorkOrderUpdates());
      break;
    
    case SYNC_TAGS.PHOTO_UPLOAD:
      event.waitUntil(syncPhotoUploads());
      break;
    
    case SYNC_TAGS.LOCATION_UPDATE:
      event.waitUntil(syncLocationUpdates());
      break;
    
    case SYNC_TAGS.INVENTORY_UPDATE:
      event.waitUntil(syncInventoryUpdates());
      break;
  }
});

// Push event - handle push notifications
self.addEventListener('push', (event) => {
  console.log('[SW] Push event received');

  if (!event.data) {
    return;
  }

  try {
    const data = event.data.json();
    const options = {
      body: data.body || 'New notification',
      icon: data.icon || '/icons/icon-192x192.png',
      badge: data.badge || '/icons/badge-72x72.png',
      image: data.image,
      tag: data.tag || 'general',
      renotify: true,
      requireInteraction: data.requireInteraction || false,
      actions: data.actions || [],
      data: data.data || {},
      timestamp: Date.now(),
    };

    event.waitUntil(
      self.registration.showNotification(data.title || 'Technician App', options)
    );
  } catch (error) {
    console.error('[SW] Error handling push event:', error);
  }
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event.notification.tag);
  
  event.notification.close();

  const clickAction = event.action;
  const notificationData = event.notification.data;

  // Handle different notification actions
  event.waitUntil(
    handleNotificationClick(clickAction, notificationData)
  );
});

// Helper functions

function isApiRequest(url) {
  return url.pathname.startsWith('/api/');
}

function isNavigationRequest(request) {
  return request.mode === 'navigate';
}

function shouldCacheApiRequest(url) {
  // Don't cache certain API patterns
  if (NO_CACHE_PATTERNS.some(pattern => pattern.test(url.pathname))) {
    return false;
  }
  
  // Cache specific API patterns
  return API_CACHE_PATTERNS.some(pattern => pattern.test(url.pathname));
}

async function handleApiRequest(request) {
  const url = new URL(request.url);
  
  if (!shouldCacheApiRequest(url)) {
    // Always fetch fresh for non-cacheable APIs
    try {
      return await fetch(request);
    } catch (error) {
      console.error('[SW] API request failed:', error);
      return new Response(
        JSON.stringify({ error: 'Network error', offline: true }),
        {
          status: 503,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }
  }

  // Try cache-first strategy for cacheable APIs
  try {
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
      const cacheDate = new Date(cachedResponse.headers.get('sw-cache-date'));
      const age = Date.now() - cacheDate.getTime();
      
      if (age < MAX_CACHE_AGE) {
        console.log('[SW] Serving API from cache:', url.pathname);
        
        // Fetch fresh data in background if cache is older than 5 minutes
        if (age > 5 * 60 * 1000) {
          fetch(request).then((response) => {
            if (response.ok) {
              const responseClone = response.clone();
              caches.open(CACHE_NAME).then((cache) => {
                const headers = new Headers(responseClone.headers);
                headers.set('sw-cache-date', new Date().toISOString());
                
                const cachedResponse = new Response(responseClone.body, {
                  status: responseClone.status,
                  statusText: responseClone.statusText,
                  headers: headers,
                });
                
                cache.put(request, cachedResponse);
              });
            }
          }).catch(() => {
            // Ignore background fetch errors
          });
        }
        
        return cachedResponse;
      }
    }

    // Fetch fresh data
    const response = await fetch(request);
    
    if (response.ok) {
      const responseClone = response.clone();
      const cache = await caches.open(CACHE_NAME);
      
      const headers = new Headers(responseClone.headers);
      headers.set('sw-cache-date', new Date().toISOString());
      
      const cachedResponse = new Response(responseClone.body, {
        status: responseClone.status,
        statusText: responseClone.statusText,
        headers: headers,
      });
      
      await cache.put(request, cachedResponse);
    }
    
    return response;
  } catch (error) {
    console.error('[SW] API request failed:', error);
    
    // Try to serve stale cache as fallback
    const staleResponse = await caches.match(request);
    if (staleResponse) {
      console.log('[SW] Serving stale API cache:', url.pathname);
      return staleResponse;
    }
    
    return new Response(
      JSON.stringify({ error: 'Network error', offline: true }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

async function handleNavigationRequest(request) {
  try {
    // Always try network first for navigation
    const response = await fetch(request);
    return response;
  } catch (error) {
    console.log('[SW] Navigation failed, serving offline page');
    
    // Serve offline page
    const cache = await caches.open(CACHE_NAME);
    const offlineResponse = await cache.match(OFFLINE_URL);
    
    return offlineResponse || new Response(
      '<h1>App is offline</h1><p>Please check your internet connection.</p>',
      { headers: { 'Content-Type': 'text/html' } }
    );
  }
}

async function handleStaticAssetRequest(request) {
  // Cache first for static assets
  const cachedResponse = await caches.match(request);
  
  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const response = await fetch(request);
    
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    
    return response;
  } catch (error) {
    console.error('[SW] Static asset request failed:', error);
    
    // Return a placeholder for failed asset requests
    if (request.destination === 'image') {
      return new Response('', { status: 200 });
    }
    
    throw error;
  }
}

async function clearAllCaches() {
  const cacheNames = await caches.keys();
  return Promise.all(
    cacheNames.map(cacheName => caches.delete(cacheName))
  );
}

async function cacheUrls(urls) {
  const cache = await caches.open(CACHE_NAME);
  return cache.addAll(urls);
}

async function prefetchCriticalData() {
  const criticalUrls = [
    '/api/work-orders',
    '/api/customers',
    '/api/inventory',
    '/api/technician/profile',
  ];

  const cache = await caches.open(CACHE_NAME);
  
  return Promise.allSettled(
    criticalUrls.map(async (url) => {
      try {
        const response = await fetch(url);
        if (response.ok) {
          const headers = new Headers(response.headers);
          headers.set('sw-cache-date', new Date().toISOString());
          
          const cachedResponse = new Response(response.body, {
            status: response.status,
            statusText: response.statusText,
            headers: headers,
          });
          
          await cache.put(url, cachedResponse);
        }
      } catch (error) {
        console.error('[SW] Failed to prefetch:', url, error);
      }
    })
  );
}

// Background sync functions
async function syncWorkOrderUpdates() {
  try {
    const updates = await getStoredUpdates('workOrderUpdates');
    
    for (const update of updates) {
      try {
        const response = await fetch('/api/work-orders/' + update.id, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(update.data),
        });
        
        if (response.ok) {
          await removeStoredUpdate('workOrderUpdates', update.id);
          
          // Notify main thread
          const clients = await self.clients.matchAll();
          clients.forEach(client => {
            client.postMessage({
              type: 'SYNC_SUCCESS',
              payload: { type: 'work-order', id: update.id },
            });
          });
        }
      } catch (error) {
        console.error('[SW] Failed to sync work order:', update.id, error);
      }
    }
  } catch (error) {
    console.error('[SW] Work order sync failed:', error);
  }
}

async function syncPhotoUploads() {
  try {
    const uploads = await getStoredUpdates('photoUploads');
    
    for (const upload of uploads) {
      try {
        const formData = new FormData();
        formData.append('file', upload.blob);
        formData.append('workOrderId', upload.workOrderId);
        formData.append('category', upload.category);
        
        const response = await fetch('/api/photos/upload', {
          method: 'POST',
          body: formData,
        });
        
        if (response.ok) {
          await removeStoredUpdate('photoUploads', upload.id);
          
          const clients = await self.clients.matchAll();
          clients.forEach(client => {
            client.postMessage({
              type: 'SYNC_SUCCESS',
              payload: { type: 'photo', id: upload.id },
            });
          });
        }
      } catch (error) {
        console.error('[SW] Failed to sync photo:', upload.id, error);
      }
    }
  } catch (error) {
    console.error('[SW] Photo sync failed:', error);
  }
}

async function syncLocationUpdates() {
  try {
    const locations = await getStoredUpdates('locationUpdates');
    
    if (locations.length > 0) {
      const response = await fetch('/api/technician/location', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ locations }),
      });
      
      if (response.ok) {
        await clearStoredUpdates('locationUpdates');
        
        const clients = await self.clients.matchAll();
        clients.forEach(client => {
          client.postMessage({
            type: 'SYNC_SUCCESS',
            payload: { type: 'location', count: locations.length },
          });
        });
      }
    }
  } catch (error) {
    console.error('[SW] Location sync failed:', error);
  }
}

async function syncInventoryUpdates() {
  try {
    const updates = await getStoredUpdates('inventoryUpdates');
    
    for (const update of updates) {
      try {
        const response = await fetch('/api/inventory/' + update.id, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(update.data),
        });
        
        if (response.ok) {
          await removeStoredUpdate('inventoryUpdates', update.id);
          
          const clients = await self.clients.matchAll();
          clients.forEach(client => {
            client.postMessage({
              type: 'SYNC_SUCCESS',
              payload: { type: 'inventory', id: update.id },
            });
          });
        }
      } catch (error) {
        console.error('[SW] Failed to sync inventory:', update.id, error);
      }
    }
  } catch (error) {
    console.error('[SW] Inventory sync failed:', error);
  }
}

async function handleNotificationClick(action, data) {
  const clients = await self.clients.matchAll({ type: 'window' });
  
  if (clients.length > 0) {
    // Focus existing window
    const client = clients[0];
    await client.focus();
    
    // Navigate to specific page based on notification data
    if (data && data.workOrderId) {
      client.postMessage({
        type: 'NAVIGATE',
        payload: { path: `/work-orders/${data.workOrderId}` },
      });
    }
  } else {
    // Open new window
    let url = '/';
    if (data && data.workOrderId) {
      url = `/work-orders/${data.workOrderId}`;
    }
    
    await self.clients.openWindow(url);
  }
}

// IndexedDB helpers for background sync data
async function getStoredUpdates(storeName) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('TechnicianAppSync', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      const db = request.result;
      const transaction = db.transaction([storeName], 'readonly');
      const store = transaction.objectStore(storeName);
      const getAll = store.getAll();
      
      getAll.onsuccess = () => resolve(getAll.result || []);
      getAll.onerror = () => reject(getAll.error);
    };
    
    request.onupgradeneeded = () => {
      const db = request.result;
      
      ['workOrderUpdates', 'photoUploads', 'locationUpdates', 'inventoryUpdates'].forEach(name => {
        if (!db.objectStoreNames.contains(name)) {
          db.createObjectStore(name, { keyPath: 'id' });
        }
      });
    };
  });
}

async function removeStoredUpdate(storeName, id) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('TechnicianAppSync', 1);
    
    request.onsuccess = () => {
      const db = request.result;
      const transaction = db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      const deleteReq = store.delete(id);
      
      deleteReq.onsuccess = () => resolve();
      deleteReq.onerror = () => reject(deleteReq.error);
    };
  });
}

async function clearStoredUpdates(storeName) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('TechnicianAppSync', 1);
    
    request.onsuccess = () => {
      const db = request.result;
      const transaction = db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      const clear = store.clear();
      
      clear.onsuccess = () => resolve();
      clear.onerror = () => reject(clear.error);
    };
  });
}