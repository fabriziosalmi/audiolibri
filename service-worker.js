const CACHE_NAME = 'audiolibri-cache-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/styles.css',
  '/app.js',
  '/audiobooks.js',
  '/icons/favicon.ico',
  '/icons/apple-touch-icon.png',
  '/icons/favicon-32x32.png',
  '/icons/favicon-16x16.png',
  '/images/og-image.jpg',
  // Add other essential assets here
];

// Install event - cache essential assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log('Opened cache');
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  const cacheAllowlist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheAllowlist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Fetch event - cache-first strategy with network fallback
self.addEventListener('fetch', event => {
  // Skip cross-origin requests like YouTube API
  if (event.request.url.startsWith(self.location.origin) || 
      !event.request.url.includes('youtube')) {
    event.respondWith(
      caches.match(event.request).then(cachedResponse => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return fetch(event.request).then(response => {
          // Don't cache if not a valid response
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }

          // Clone the response since it's a stream that can only be consumed once
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then(cache => {
            // Cache assets that aren't dynamic (avoid caching YouTube videos)
            if (!event.request.url.includes('youtube') && 
                !event.request.url.includes('google') &&
                !event.request.url.includes('analytics')) {
              cache.put(event.request, responseToCache);
            }
          });
          return response;
        });
      })
    );
  }
});

// Handle offline functionality
self.addEventListener('fetch', event => {
  // Fallback page for when network is unavailable
  if (event.request.mode === 'navigate' || 
      (event.request.method === 'GET' && event.request.headers.get('accept').includes('text/html'))) {
    event.respondWith(
      fetch(event.request).catch(() => {
        return caches.match('/offline.html');
      })
    );
  }
});
