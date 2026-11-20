async function req(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).detail || msg; } catch {}
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return r.json();
}
const post = (url, body) => req(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const api = {
  kpis: () => req("/api/kpis"),
  norma: () => req("/api/analitica/norma"),
  reloj: () => req("/api/analitica/reloj"),
  trenes: () => req("/api/analitica/trenes"),
  lotes: (n = 40) => req(`/api/lotes?limite=${n}`),
  lote: (id) => req(`/api/lotes/${id}`),
  alertas: (n = 14) => req(`/api/alertas?limite=${n}`),
  ejecutivo: () => req("/api/reportes/ejecutivo"),
  modelo: () => req("/api/modelo/evaluacion"),
  filtros: () => req("/api/filtros"),
  escenarios: () => req("/api/escenarios"),
  normas: () => req("/api/normas"),
  recomendar: (b) => post("/api/recomendacion", b),
  simular: (b) => post("/api/lotes/simular", b),
};
