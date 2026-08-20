/* Duck Studios — scanner e fila offline.
 *
 * Premissa do projeto: em locação a rede cai, e conferência de equipamento não pode parar por
 * isso. Toda bipada vira um registro local com client_uuid próprio; o servidor deduplica por
 * esse uuid, então reenviar depois nunca conta duas vezes.
 */
const DS = {
  fila: "ds-fila-bipes",

  uuid() {
    return crypto.randomUUID ? crypto.randomUUID()
      : "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
          const r = Math.random() * 16 | 0;
          return (c === "x" ? r : (r & 0x3 | 0x8)).toString(16);
        });
  },

  lerFila() { try { return JSON.parse(localStorage.getItem(DS.fila) || "[]"); } catch { return []; } },
  salvarFila(f) { localStorage.setItem(DS.fila, JSON.stringify(f)); DS.pintarFila(); },

  pintarFila() {
    const n = DS.lerFila().length;
    const el = document.getElementById("ds-pendentes");
    if (!el) return;
    el.hidden = n === 0;
    el.textContent = n === 1 ? "1 bipada aguardando rede" : `${n} bipadas aguardando rede`;
  },

  async enviar(rid, codigo, momento) {
    const item = { rid, codigo, momento, client_uuid: DS.uuid(), quando: Date.now() };
    if (!navigator.onLine) { DS.enfileirar(item); return { ok: true, offline: true }; }
    try {
      const r = await fetch(`/api/saidas/${rid}/bipar`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(item),
      });
      const dados = await r.json();
      if (!r.ok) return dados;                 // recusa do servidor: regra de negócio, não rede
      return dados;
    } catch {
      DS.enfileirar(item);                     // falha de rede: guarda e segue
      return { ok: true, offline: true };
    }
  },

  enfileirar(item) { const f = DS.lerFila(); f.push(item); DS.salvarFila(f); },

  async sincronizar() {
    if (!navigator.onLine) return;
    let f = DS.lerFila();
    if (!f.length) return;
    const restantes = [];
    for (const item of f) {
      try {
        const r = await fetch(`/api/saidas/${item.rid}/bipar`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(item),
        });
        // 409 é recusa por regra (item sublocado, já reservado): não adianta reenviar
        if (!r.ok && r.status !== 409) restantes.push(item);
      } catch { restantes.push(item); }
    }
    DS.salvarFila(restantes);
    if (f.length !== restantes.length) location.reload();
  },

  /* ---- câmera ------------------------------------------------------------
     Usa BarcodeDetector quando existe (Chrome/Android e Safari recente). Onde não existe,
     o campo de digitação e o leitor USB continuam funcionando — a tela nunca fica sem saída. */
  async abrirCamera(aoLer) {
    const caixa = document.getElementById("ds-camera");
    const video = document.getElementById("ds-video");
    const aviso = document.getElementById("ds-camera-aviso");
    caixa.hidden = false;

    if (!("BarcodeDetector" in window)) {
      aviso.textContent = "Este navegador não lê código pela câmera. Use o leitor ou digite o código.";
      return;
    }
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
      });
    } catch {
      aviso.textContent = "Sem permissão de câmera. Libere nas configurações do navegador.";
      return;
    }
    video.srcObject = stream;
    await video.play();

    const det = new BarcodeDetector({ formats: ["qr_code", "code_128", "code_39", "ean_13"] });
    let ultimo = "", travado = 0;
    const parar = () => { stream.getTracks().forEach(t => t.stop()); caixa.hidden = true; };
    caixa.querySelector("[data-fechar]").onclick = parar;

    const laco = async () => {
      if (caixa.hidden) return;
      try {
        const achados = await det.detect(video);
        const agora = Date.now();
        if (achados.length && (achados[0].rawValue !== ultimo || agora - travado > 2500)) {
          ultimo = achados[0].rawValue; travado = agora;
          if (navigator.vibrate) navigator.vibrate(60);
          aoLer(ultimo);
        }
      } catch { /* quadro ruim: tenta o próximo */ }
      requestAnimationFrame(laco);
    };
    requestAnimationFrame(laco);
  },
};

function pintarRede() {
  const el = document.getElementById("ds-offline");
  if (el) el.hidden = navigator.onLine;
}
window.addEventListener("online", () => { pintarRede(); DS.sincronizar(); });
window.addEventListener("offline", pintarRede);
document.addEventListener("DOMContentLoaded", () => { pintarRede(); DS.pintarFila(); DS.sincronizar(); });

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/static/sw.js").catch(() => {});
}
