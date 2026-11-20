import React from "react";

export const C = {
  entrada: "#b4532a",
  salida: "#2b7a69",
  tinta: "#182a3f",
  norma: "#a3262a",
  gris: "#8c8470",
  linea: "#cfc6b0",
  papel: "#efe9dc",
};

export const fmt = (v, d = 1) =>
  v == null || Number.isNaN(v) ? "—" : Number(v).toLocaleString("es-CO", { minimumFractionDigits: d, maximumFractionDigits: d });

const polar = (cx, cy, r, a) => [cx + r * Math.cos(a), cy + r * Math.sin(a)];
const wedge = (cx, cy, r1, r2, a1, a2) => {
  const [x1, y1] = polar(cx, cy, r1, a1), [x2, y2] = polar(cx, cy, r2, a1);
  const [x3, y3] = polar(cx, cy, r2, a2), [x4, y4] = polar(cx, cy, r1, a2);
  return `M${x1},${y1} L${x2},${y2} A${r2},${r2} 0 0 1 ${x3},${y3} L${x4},${y4} A${r1},${r1} 0 0 0 ${x1},${y1}Z`;
};

/* ── 1. Distancia a la norma: cada contaminante como un carril en escala logarítmica ── */
export function DistanciaNorma({ datos }) {
  const W = 640, mL = 92, mR = 28, rowH = 62, top = 34;
  const H = top + rowH * datos.length + 34;
  const lo = Math.log10(0.04), hi = Math.log10(16);
  const x = (r) => mL + ((Math.log10(Math.max(r, 0.04)) - lo) / (hi - lo)) * (W - mL - mR);
  const marcas = [0.1, 0.25, 0.5, 1, 2, 4, 8];
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Razón concentración/límite antes y después del tratamiento">
      <rect x={mL} y={top - 14} width={x(1) - mL} height={H - top - 20} fill="#2b7a69" opacity="0.07" />
      {marcas.map((m) => (
        <g key={m}>
          <line x1={x(m)} x2={x(m)} y1={top - 14} y2={H - 34} stroke={C.linea} strokeDasharray={m === 1 ? "" : "2 4"} />
          <text x={x(m)} y={H - 16} textAnchor="middle" className="t-eje">{m === 1 ? "norma" : `${m}×`}</text>
        </g>
      ))}
      <line x1={x(1)} x2={x(1)} y1={top - 14} y2={H - 34} stroke={C.norma} strokeWidth="1.6" />
      <text x={x(1) + 5} y={top - 18} className="t-eje" fill={C.norma}>Res. 2254/2017</text>
      {datos.map((d, i) => {
        const y = top + rowH * i + rowH / 2;
        const re = d.entrada / d.limite_norma, rs = d.salida / d.limite_norma, ro = d.limite_oms / d.limite_norma;
        const ok = rs <= 1;
        return (
          <g key={d.contaminante}>
            <text x={mL - 14} y={y - 2} textAnchor="end" className="t-lab">{d.etiqueta}</text>
            <text x={mL - 14} y={y + 13} textAnchor="end" className="t-eje">límite {fmt(d.limite_norma, d.limite_norma < 10 ? 2 : 0)} {d.unidad}</text>
            <line x1={x(ro)} x2={x(ro)} y1={y - 15} y2={y + 15} stroke={C.salida} strokeWidth="1.5" strokeDasharray="3 3" />
            <line x1={x(rs)} x2={x(re)} y1={y} y2={y} stroke={C.tinta} strokeWidth="5" strokeLinecap="round" opacity="0.14" />
            <line x1={x(rs)} x2={x(re)} y1={y} y2={y} stroke={C.tinta} strokeWidth="1.4" />
            <circle cx={x(re)} cy={y} r="8" fill={C.entrada} />
            <circle cx={x(rs)} cy={y} r="8" fill={ok ? C.salida : C.papel} stroke={ok ? C.salida : C.norma} strokeWidth="2.4" />
            <text x={x(re)} y={y - 15} textAnchor="middle" className="t-num" fill={C.entrada}>{fmt(d.entrada, d.entrada < 20 ? 1 : 0)}</text>
            <text x={x(rs)} y={y + 24} textAnchor="middle" className="t-num" fill={ok ? C.salida : C.norma}>{fmt(d.salida, d.salida < 20 ? 1 : 0)}</text>
          </g>
        );
      })}
    </svg>
  );
}

/* ── 2. Reloj del aire: el aire que entra (hacia fuera) y el que sale (hacia dentro) ── */
export function RelojAire({ datos, limNorma, limOms }) {
  const S = 460, cx = S / 2, cy = S / 2, r0 = 118, alto = 92;
  const vmax = Math.max(limNorma * 1.5, ...datos.map((d) => d.entrada || 0));
  const len = (v) => (v / vmax) * alto;
  const a = (h) => (h / 24) * Math.PI * 2 - Math.PI / 2;
  const ancho = (Math.PI * 2) / 24 / 2 - 0.012;
  const pico = datos.reduce((m, d) => ((d.entrada ?? -1) > (m.entrada ?? -1) ? d : m), datos[0] || {});
  return (
    <svg viewBox={`0 0 ${S} ${S}`} role="img" aria-label="PM2.5 medio por hora del día">
      <circle cx={cx} cy={cy} r={r0} fill="none" stroke={C.tinta} strokeWidth="1" />
      <circle cx={cx} cy={cy} r={r0 + len(limNorma)} fill="none" stroke={C.norma} strokeDasharray="5 4" />
      <circle cx={cx} cy={cy} r={r0 + len(limOms)} fill="none" stroke={C.salida} strokeDasharray="2 4" />
      {datos.map((d) => {
        const c = a(d.hora + 0.5);
        return (
          <g key={d.hora}>
            {d.entrada != null && <path d={wedge(cx, cy, r0 + 2, r0 + 2 + len(d.entrada), c - ancho, c + ancho)} fill={C.entrada} opacity={0.35 + 0.65 * Math.min(1, d.n / 14)} />}
            {d.salida != null && <path d={wedge(cx, cy, r0 - 2 - len(d.salida), r0 - 2, c - ancho, c + ancho)} fill={C.salida} />}
          </g>
        );
      })}
      {[0, 3, 6, 9, 12, 15, 18, 21].map((h) => {
        const [tx, ty] = polar(cx, cy, r0 + alto + 20, a(h));
        return <text key={h} x={tx} y={ty + 4} textAnchor="middle" className="t-eje">{String(h).padStart(2, "0")}h</text>;
      })}
      <text x={cx} y={cy - 12} textAnchor="middle" className="t-serif-xl">{pico.hora != null ? `${String(pico.hora).padStart(2, "0")}h` : "—"}</text>
      <text x={cx} y={cy + 8} textAnchor="middle" className="t-eje">hora más cargada</text>
      <text x={cx} y={cy + 24} textAnchor="middle" className="t-eje">{fmt(pico.entrada, 0)} µg/m³ de PM2.5</text>
    </svg>
  );
}

/* ── 3. Curva de depuración de un lote ── */
const FONDO_DEF = { pm25: 2, pm10: 4, co2: 420, co: 0.1, tvoc: 15 };
export function CurvaDepuracion({ serie, cont, fondo = FONDO_DEF }) {
  const W = 700, H = 330, mL = 56, mR = 16, mT = 28, mB = 40;
  const pts = serie.puntos;
  const ent = pts.filter((p) => p.etapa === "entrada"), pro = pts.filter((p) => p.etapa === "proceso"), sal = pts.filter((p) => p.etapa === "salida");
  const c0 = ent.reduce((s, p) => s + p[cont], 0) / ent.length;
  const tMin = Math.min(...pts.map((p) => p.t_seg)) / 60, tMax = Math.max(...pts.map((p) => p.t_seg)) / 60;
  const tFin = pro.length ? pro[pro.length - 1].t_seg / 60 : tMax;
  const lim = serie.limites.norma[cont], oms = serie.limites.oms[cont];
  const yMax = Math.max(c0 * 1.08, lim * 1.1);
  const yMin = cont === "co2" ? Math.min(380, ...pts.map((p) => p[cont])) : 0;
  const x = (t) => mL + ((t - tMin) / (tMax - tMin)) * (W - mL - mR);
  const y = (v) => mT + (1 - (v - yMin) / (yMax - yMin)) * (H - mT - mB);
  const curva = (k) => {
    const f = fondo[cont];
    const n = 60;
    return Array.from({ length: n + 1 }, (_, i) => {
      const t = (tFin * i) / n;
      return `${i ? "L" : "M"}${x(t)},${y(f + Math.max(c0 - f, 0) * Math.exp(-k * (t / 60)))}`;
    }).join("");
  };
  const kt = serie.k_teorica_h[cont], ke = serie.k_estimada_h[cont];
  const ticks = Array.from({ length: 5 }, (_, i) => yMin + ((yMax - yMin) * i) / 4);
  const un = cont === "co2" ? "ppm" : cont === "co" ? "ppm" : "µg/m³";
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Curva de depuración de ${cont}`}>
      <rect x={x(tMin)} y={mT} width={x(0) - x(tMin)} height={H - mT - mB} fill={C.entrada} opacity="0.08" />
      <rect x={x(tFin)} y={mT} width={x(tMax) - x(tFin)} height={H - mT - mB} fill={C.salida} opacity="0.09" />
      <text x={(x(tMin) + x(0)) / 2} y={mT - 10} textAnchor="middle" className="t-eje">ingreso</text>
      <text x={(x(0) + x(tFin)) / 2} y={mT - 10} textAnchor="middle" className="t-eje">filtración</text>
      <text x={(x(tFin) + x(tMax)) / 2} y={mT - 10} textAnchor="middle" className="t-eje">verificación</text>
      {ticks.map((v, i) => (
        <g key={i}>
          <line x1={mL} x2={W - mR} y1={y(v)} y2={y(v)} stroke={C.linea} strokeDasharray="2 4" />
          <text x={mL - 8} y={y(v) + 4} textAnchor="end" className="t-eje">{fmt(v, v < 10 ? 1 : 0)}</text>
        </g>
      ))}
      {lim < yMax && (<><line x1={mL} x2={W - mR} y1={y(lim)} y2={y(lim)} stroke={C.norma} strokeWidth="1.5" strokeDasharray="6 4" /><text x={W - mR - 4} y={y(lim) - 6} textAnchor="end" className="t-eje" fill={C.norma}>norma {fmt(lim, lim < 10 ? 2 : 0)}</text></>)}
      {oms < yMax && oms !== lim && (<><line x1={mL} x2={W - mR} y1={y(oms)} y2={y(oms)} stroke={C.salida} strokeWidth="1.2" strokeDasharray="2 4" /><text x={W - mR - 4} y={y(oms) - 6} textAnchor="end" className="t-eje" fill={C.salida}>OMS {fmt(oms, oms < 10 ? 2 : 0)}</text></>)}
      {kt != null && <path d={curva(kt)} fill="none" stroke={C.gris} strokeWidth="1.6" strokeDasharray="5 4" />}
      {ke != null && <path d={curva(ke)} fill="none" stroke={C.tinta} strokeWidth="2.2" />}
      {ent.map((p, i) => <circle key={`e${i}`} cx={x(p.t_seg / 60)} cy={y(p[cont])} r="4.5" fill={C.entrada} />)}
      {pro.map((p, i) => <circle key={`p${i}`} cx={x(p.t_seg / 60)} cy={y(p[cont])} r="2.6" fill={C.tinta} opacity="0.75" />)}
      {sal.map((p, i) => <circle key={`s${i}`} cx={x(p.t_seg / 60)} cy={y(p[cont])} r="4.5" fill={C.salida} />)}
      <text x={mL} y={H - 8} className="t-eje">{fmt(tMin, 0)} min</text>
      <text x={W - mR} y={H - 8} textAnchor="end" className="t-eje">{fmt(tMax, 0)} min · {un}</text>
      <g transform={`translate(${mL + 250},${mT + 70})`}>
        <line x1="0" x2="22" y1="0" y2="0" stroke={C.tinta} strokeWidth="2.2" /><text x="28" y="4" className="t-eje">ajuste a las lecturas (k = {fmt(ke, 1)}/h)</text>
        <line x1="0" x2="22" y1="16" y2="16" stroke={C.gris} strokeWidth="1.6" strokeDasharray="5 4" /><text x="28" y="20" className="t-eje">catálogo nominal (k = {fmt(kt, 1)}/h)</text>
      </g>
    </svg>
  );
}

/* ── 4. Trenes de filtros: cada punto es un tratamiento ── */
const ABR = { "PRE-G4": "G4", "HEPA-H13": "HEPA", "CARB-ACT": "C", "CAT-CO": "CAT", "ABS-CO2": "ABS" };
const orden = ["PRE-G4", "HEPA-H13", "CARB-ACT", "CAT-CO", "ABS-CO2"];
export const nombreTren = (firma) => firma.split("+").sort((a, b) => orden.indexOf(a) - orden.indexOf(b)).map((c) => ABR[c] || c).join(" · ");

export function TrenesFiltros({ trenes }) {
  const filas = [...trenes].sort((a, b) => b.n - a.n).slice(0, 9).sort((a, b) => b.reduccion_mediana - a.reduccion_mediana);
  const W = 660, mL = 205, mR = 96, rowH = 38, top = 12, H = top + filas.length * rowH + 30;
  const x = (v) => mL + (Math.max(0, Math.min(100, v)) / 100) * (W - mL - mR);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Reducción por tren de filtros">
      {[0, 25, 50, 75, 100].map((v) => (
        <g key={v}>
          <line x1={x(v)} x2={x(v)} y1={top} y2={H - 26} stroke={C.linea} strokeDasharray="2 4" />
          <text x={x(v)} y={H - 10} textAnchor="middle" className="t-eje">{v} %</text>
        </g>
      ))}
      {filas.map((f, i) => {
        const y = top + i * rowH + rowH / 2;
        return (
          <g key={f.firma}>
            <text x={mL - 12} y={y + 4} textAnchor="end" className="t-lab">{nombreTren(f.firma)}</text>
            <rect x={x(f.reduccion_p25)} y={y - 11} width={Math.max(2, x(f.reduccion_p75) - x(f.reduccion_p25))} height="22" fill={C.tinta} opacity="0.08" />
            {f.puntos.map((p, j) => (
              <circle key={j} cx={x(p)} cy={y + (((j * 37) % 17) - 8) * 0.85} r="2.5" fill={C.tinta} opacity="0.5" />
            ))}
            <line x1={x(f.reduccion_mediana)} x2={x(f.reduccion_mediana)} y1={y - 14} y2={y + 14} stroke={C.salida} strokeWidth="3" />
            <text x={W - mR + 12} y={y - 1} className="t-num">{fmt(f.reduccion_mediana, 0)} %</text>
            <text x={W - mR + 12} y={y + 13} className="t-eje">n={f.n}</text>
          </g>
        );
      })}
    </svg>
  );
}

/* ── 5. Predicho vs observado del modelo de tiempo ── */
export function PredVsReal({ pares }) {
  const S = 250, m = 36;
  const mx = Math.max(10, ...pares.flatMap((p) => [p.real, p.pred])) * 1.05;
  const s = (v) => m + (v / mx) * (S - m - 12);
  const t = (v) => S - m + 8 - (v / mx) * (S - m - 12) - 8;
  return (
    <svg viewBox={`0 0 ${S} ${S}`} role="img" aria-label="Minutos predichos contra observados">
      <line x1={m} x2={S - 10} y1={S - m} y2={S - m} stroke={C.tinta} />
      <line x1={m} x2={m} y1={S - m} y2={10} stroke={C.tinta} />
      <line x1={s(0)} y1={t(0)} x2={s(mx)} y2={t(mx)} stroke={C.gris} strokeDasharray="4 4" />
      {pares.map((p, i) => <circle key={i} cx={s(p.real)} cy={t(p.pred)} r="3.4" fill={C.salida} opacity="0.7" />)}
      <text x={S / 2 + 10} y={S - 8} textAnchor="middle" className="t-eje">minutos observados</text>
      <text x="10" y={S / 2} transform={`rotate(-90 10 ${S / 2})`} textAnchor="middle" className="t-eje">minutos predichos</text>
      <text x={m - 6} y={S - m + 14} textAnchor="end" className="t-eje">0</text>
      <text x={S - 10} y={S - m + 14} textAnchor="end" className="t-eje">{fmt(mx, 0)}</text>
    </svg>
  );
}
