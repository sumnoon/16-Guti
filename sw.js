// Offline cache for the installed web app (the Android app ships its files and does not use this).
// Stale-while-revalidate: answer from the cache at once, refresh it in the background, so a new
// release shows up on the next launch. Each place (village, rooftop) loads its files when first shown;
// main.js then fetches the other places' files in the background, so one online visit is enough to
// play everywhere offline afterwards.
const CACHE = 'sholo-guti-v1';
const CORE = ['./', 'index.html', 'manifest.webmanifest', 'vendor/three/build/three.module.min.js', 'vendor/fonts/fonts.css'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  e.respondWith(caches.open(CACHE).then(async (cache) => {
    const hit = await cache.match(req, { ignoreSearch: true });
    const fresh = fetch(req).then((res) => { if (res.ok) cache.put(req, res.clone()); return res; });
    if (hit) { e.waitUntil(fresh.catch(() => {})); return hit; }
    return fresh;
  }));
});
