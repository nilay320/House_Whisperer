const CACHE_NAME = 'inspector-ai-v1';
const urlsToCache = [
  '/',
  '/static/js/bundle.js',
  '/static/css/main.css',
  '/manifest.json'
];

// Install event - cache resources
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // Return cached version or fetch from network
        return response || fetch(event.request);
      }
    )
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Background sync for offline data upload
self.addEventListener('sync', (event) => {
  if (event.tag === 'upload-inspection-data') {
    event.waitUntil(uploadOfflineData());
  }
});

async function uploadOfflineData() {
  try {
    // Get offline data from IndexedDB
    const offlineData = await getOfflineInspectionData();
    
    if (offlineData.length > 0) {
      for (const data of offlineData) {
        try {
          // Attempt to upload to server
          const response = await fetch('/api/upload-inspection', {
            method: 'POST',
            body: data.formData
          });
          
          if (response.ok) {
            // Remove from offline storage after successful upload
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

// Helper functions for IndexedDB operations
async function getOfflineInspectionData() {
  // Implementation would depend on your IndexedDB setup
  return [];
}

async function removeOfflineData(id) {
  // Implementation would depend on your IndexedDB setup
  console.log('Removing offline data:', id);
} 