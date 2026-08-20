/* Service worker: o app precisa abrir mesmo sem rede.
 * Páginas: rede primeiro, cache como rede reserva (dado velho é melhor que tela em branco).
 * Estáticos: cache primeiro, que não mudam entre deploys sem trocar de versão.
 */
const VERSAO = "duck-v1";
const ESSENCIAL = ["/", "/static/tokens.css", "/static/app.js",
                   "/static/logo/logo-horizontal-branco.svg", "/static/logo/marca-cor.svg"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSAO).then(c => c.addAll(ESSENCIAL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== VERSAO).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;                       // POST vai pela fila do app.js
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.startsWith("/api/")) return;           // dado de agente nunca vem de cache

  if (url.pathname.startsWith("/static/")) {
    e.respondWith(caches.match(req).then(r => r || fetch(req).then(resp => {
      const copia = resp.clone();
      caches.open(VERSAO).then(c => c.put(req, copia));
      return resp;
    })));
    return;
  }

  e.respondWith(fetch(req).then(resp => {
    const copia = resp.clone();
    caches.open(VERSAO).then(c => c.put(req, copia));
    return resp;
  }).catch(() => caches.match(req).then(r => r || caches.match("/"))));
});
