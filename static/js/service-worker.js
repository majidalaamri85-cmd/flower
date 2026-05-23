const CACHE_NAME = 'shop-management-v2';
const OFFLINE_CACHE = 'offline-data-v1';

const urlsToCache = [
  '/',
  '/sales/pos-offline/',
  '/static/manifest.json',
  '/static/css/theme.css',
  '/static/images/floral-watermark.svg',
  '/static/js/indexeddb.js',
  '/static/js/offline-manager.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(urlsToCache))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (url.pathname.startsWith('/sales/') || url.pathname.startsWith('/reports/')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(OFFLINE_CACHE).then((cache) => cache.put(request, clone));
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((response) => response || fetch(request))
  );
});

self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-sales') {
    event.waitUntil(self.registration.showNotification('المزامنة', {
      body: 'محاولة مزامنة البيانات المحلية...'
    }));
  }
});
