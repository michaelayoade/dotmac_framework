/**
 * Service Worker for Customer Portal
 * Implements caching strategies for performance optimization
 */

const CACHE_NAME = 'dotmac-customer-v1';
const RUNTIME_CACHE = 'dotmac-runtime-v1';
const IMAGE_CACHE = 'dotmac-images-v1';
const API_CACHE = 'dotmac-api-v1';

// Assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/dashboard',
  '/billing',
  '/services',
  '/support',
  '/offline',
  '/manifest.json',
  '/favicon.ico',
  '/_next/static/css/',
  '/_next/static/js/'
];

// Cache-first resources (long-lived assets)
const CACHE_FIRST_PATTERNS = [
  /\/_next\/static\//,
  /\/images\//,
  /\/icons\//,
  /\.(?:png|jpg|jpeg|svg|gif|webp|avif)$/,
  /\.(?:css|js|woff|woff2|ttf|eot)$/
];

// Network-first resources (dynamic content)
const NETWORK_FIRST_PATTERNS = [
  /\/api\//,
  /\/auth\//,
  /\/dashboard/,
  /\/billing/,
  /\/services/
];

// Stale-while-revalidate patterns
const SWR_PATTERNS = [
  /\/_next\/data\//,
  /\/api\/user/,
  /\/api\/billing\/overview/
];

self.addEventListener('install', event => {
  console.log('Service Worker installing...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('Service Worker installed');
        return self.skipWaiting();
      })
      .catch(error => {
        console.error('Service Worker installation failed:', error);
      })
  );
});

self.addEventListener('activate', event => {
  console.log('Service Worker activating...');
  
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames
            .filter(cacheName => 
              cacheName.startsWith('dotmac-') && 
              ![CACHE_NAME, RUNTIME_CACHE, IMAGE_CACHE, API_CACHE].includes(cacheName)
            )
            .map(cacheName => {
              console.log('Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            })
        );
      })
      .then(() => {
        console.log('Service Worker activated');
        return self.clients.claim();
      })
  );
});

self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip cross-origin requests
  if (url.origin !== self.location.origin) {
    return;
  }

  // Handle different caching strategies
  if (shouldCacheFirst(request)) {
    event.respondWith(cacheFirst(request));
  } else if (shouldNetworkFirst(request)) {
    event.respondWith(networkFirst(request));
  } else if (shouldStaleWhileRevalidate(request)) {
    event.respondWith(staleWhileRevalidate(request));
  } else {
    // Default: network first with cache fallback
    event.respondWith(networkFirst(request));
  }
});

// Cache-first strategy (for static assets)
async function cacheFirst(request) {
  try {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(getCacheName(request));
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.error('Cache-first failed:', error);
    return caches.match(request) || caches.match('/offline');
  }
}

// Network-first strategy (for dynamic content)
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      const cache = await caches.open(getCacheName(request));
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.error('Network-first failed:', error);
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Return offline page for navigation requests
    if (request.destination === 'document') {
      return caches.match('/offline');
    }
    
    throw error;
  }
}

// Stale-while-revalidate strategy
async function staleWhileRevalidate(request) {
  const cache = await caches.open(getCacheName(request));
  const cachedResponse = await cache.match(request);
  
  const fetchPromise = fetch(request).then(networkResponse => {
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  }).catch(error => {
    console.error('SWR network request failed:', error);
    return cachedResponse;
  });

  // Return cached version immediately, update in background
  return cachedResponse || fetchPromise;
}

// Determine caching strategy based on request
function shouldCacheFirst(request) {
  const url = request.url;
  return CACHE_FIRST_PATTERNS.some(pattern => pattern.test(url));
}

function shouldNetworkFirst(request) {
  const url = request.url;
  return NETWORK_FIRST_PATTERNS.some(pattern => pattern.test(url));
}

function shouldStaleWhileRevalidate(request) {
  const url = request.url;
  return SWR_PATTERNS.some(pattern => pattern.test(url));
}

// Get appropriate cache name based on request type
function getCacheName(request) {
  const url = request.url;
  
  if (/\.(?:png|jpg|jpeg|svg|gif|webp|avif)$/.test(url)) {
    return IMAGE_CACHE;
  }
  
  if (/\/api\//.test(url)) {
    return API_CACHE;
  }
  
  return RUNTIME_CACHE;
}

// Handle background sync for offline actions
self.addEventListener('sync', event => {
  console.log('Background sync:', event.tag);
  
  if (event.tag === 'background-billing-sync') {
    event.waitUntil(syncBillingData());
  } else if (event.tag === 'background-usage-sync') {
    event.waitUntil(syncUsageData());
  }
});

// Sync billing data when back online
async function syncBillingData() {
  try {
    const pendingRequests = await getStoredRequests('billing-queue');
    
    for (const requestData of pendingRequests) {
      try {
        await fetch(requestData.url, requestData.options);
        await removeStoredRequest('billing-queue', requestData.id);
      } catch (error) {
        console.error('Failed to sync billing request:', error);
      }
    }
  } catch (error) {
    console.error('Billing sync failed:', error);
  }
}

// Sync usage data when back online
async function syncUsageData() {
  try {
    const pendingRequests = await getStoredRequests('usage-queue');
    
    for (const requestData of pendingRequests) {
      try {
        await fetch(requestData.url, requestData.options);
        await removeStoredRequest('usage-queue', requestData.id);
      } catch (error) {
        console.error('Failed to sync usage request:', error);
      }
    }
  } catch (error) {
    console.error('Usage sync failed:', error);
  }
}

// Store requests for background sync
async function getStoredRequests(queueName) {
  // In a real implementation, you'd use IndexedDB
  return [];
}

async function removeStoredRequest(queueName, id) {
  // In a real implementation, you'd remove from IndexedDB
  console.log(`Removed request ${id} from ${queueName}`);
}

// Handle push notifications
self.addEventListener('push', event => {
  console.log('Push notification received');
  
  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body,
      icon: '/icons/icon-192x192.png',
      badge: '/icons/badge-72x72.png',
      data: data.data,
      actions: data.actions || [],
      requireInteraction: data.requireInteraction || false,
      silent: data.silent || false,
      timestamp: Date.now()
    };

    event.waitUntil(
      self.registration.showNotification(data.title, options)
    );
  }
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
  event.notification.close();
  
  const data = event.notification.data;
  let url = '/dashboard';
  
  if (data && data.url) {
    url = data.url;
  }
  
  event.waitUntil(
    self.clients.matchAll({ type: 'window' }).then(clients => {
      // Check if there's already a window open
      for (const client of clients) {
        if (client.url.includes(url) && 'focus' in client) {
          return client.focus();
        }
      }
      
      // Open new window
      if (self.clients.openWindow) {
        return self.clients.openWindow(url);
      }
    })
  );
});

// Performance monitoring
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

console.log('Service Worker script loaded');