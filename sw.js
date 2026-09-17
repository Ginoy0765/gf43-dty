// YANTRA service worker — minimal offline support for the installed app.
// Strategy: stale-while-revalidate for the app shell, so the app opens
// instantly (even offline) but still picks up new versions in the background.
const CACHE = 'yantra-v28.30';
const SHELL = [
  './',
  './index.html',
  './manifest.webmanifest',
  './favicon.svg',
  './favicon-32.png',
  './apple-touch-icon.png',
  './icon-192.png',
  './icon-512.png'
];

self.addEventListener('install', function(e){
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(function(c){ return c.addAll(SHELL); }).catch(function(){}));
});

self.addEventListener('activate', function(e){
  e.waitUntil(
    caches.keys().then(function(keys){
      return Promise.all(keys.filter(function(k){ return k!==CACHE; }).map(function(k){ return caches.delete(k); }));
    }).then(function(){ return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function(e){
  if(e.request.method!=='GET') return;
  var url=new URL(e.request.url);
  if(url.origin!==location.origin) return; // don't touch cross-origin requests

  e.respondWith(
    caches.match(e.request).then(function(cached){
      var network=fetch(e.request).then(function(resp){
        if(resp && resp.ok){
          var copy=resp.clone();
          caches.open(CACHE).then(function(c){ c.put(e.request, copy); });
        }
        return resp;
      }).catch(function(){ return cached; });
      return cached || network;
    })
  );
});
