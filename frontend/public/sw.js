const APP_SHELL_CACHE = 'hw-app-shell-v1';
const ASSETS_CACHE = 'hw-assets-v1';

// Resources to ensure the app shell loads
const APP_SHELL_URLS = [
  '/',
  '/index.html',
  '/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(APP_SHELL_CACHE).then((cache) => cache.addAll(APP_SHELL_URLS))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((key) => {
          if (key !== APP_SHELL_CACHE && key !== ASSETS_CACHE) {
            return caches.delete(key);
          }
        })
      )
    )
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // 1) HTML navigations: network-first with fallback to cached app shell
  if (request.mode === 'navigate') {
    event.respondWith(
      (async () => {
        try {
          const networkResponse = await fetch(request);
          // Optionally update cached index
          const cache = await caches.open(APP_SHELL_CACHE);
          cache.put('/index.html', networkResponse.clone());
          return networkResponse;
        } catch (err) {
          // Offline or fetch failed → serve cached shell
          const cached = await caches.match('/index.html');
          return cached || Response.error();
        }
      })()
    );
    return;
  }

  // 2) Static assets (scripts, styles, images, fonts): cache-first
  const isStaticAsset =
    request.destination === 'script' ||
    request.destination === 'style' ||
    request.destination === 'image' ||
    request.destination === 'font' ||
    url.pathname.startsWith('/static/');

  if (isStaticAsset) {
    event.respondWith(
      caches.open(ASSETS_CACHE).then(async (cache) => {
        const cached = await cache.match(request);
        if (cached) return cached;
        const response = await fetch(request);
        // Only cache successful, basic responses
        if (response && response.status === 200 && response.type === 'basic') {
          cache.put(request, response.clone());
        }
        return response;
      })
    );
    return;
  }

  // 3) Fallback: try cache then network
  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request))
  );
});

// Background sync placeholder kept for future use
self.addEventListener('sync', (event) => {
  if (event.tag === 'upload-inspection-data') {
    event.waitUntil(uploadOfflineData());
  }
});

async function uploadOfflineData() {
  try {
    const offlineData = await getOfflineInspectionData();
    if (offlineData.length > 0) {
      for (const data of offlineData) {
        try {
          const response = await fetch('/api/upload-inspection', {
            method: 'POST',
            body: data.formData
          });
          if (response.ok) {
            await removeOfflineData(data.id);
            console.log('Offline data uploaded successfully');
          }
        } catch (error) {
          console.log('Failed to upload offline data:', error);
        }
      }
    }
  } catch (error) {
    console.log('Error processing offline data:', error);
  }
}

async function getOfflineInspectionData() {
  return [];
}

async function removeOfflineData(id) {
  console.log('Removing offline data:', id);
} 