import React, { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api.js";
import { C, CurvaDepuracion, DistanciaNorma, PredVsReal, RelojAire, TrenesFiltros, fmt, nombreTren } from "./charts.jsx";

const CLASES = {
  CUMPLE_OMS: ["Cumple guías OMS", "ok"],
  CUMPLE_NORMA: ["Cumple norma", "ok"],
  SIN_NECESIDAD: ["Sin necesidad", "neutro"],
  PARCIAL: ["Mejora parcial", "aviso"],
  INSUFICIENTE: ["Insuficiente", "mal"],
};
const CONT_TABS = [["pm25", "PM2.5"], ["pm10", "PM10"], ["co2", "CO₂"], ["co", "CO"]];

function Seccion({ n, titulo, nota, children, className = "" }) {
  return (
    <section className={`seccion ${className}`}>
      <header>
        <span className="num">§ {n}</span>
        <h2>{titulo}</h2>
      </header>
      {nota && <p className="nota">{nota}</p>}
      {children}
    </section>
  );
}

function Indicador({ etiqueta, antes, despues, unidad, pie, d = 0, solo }) {
  return (
    <article className="indicador">
      <span className="et">{etiqueta}</span>
      {solo != null ? (
        <p className="cifra">{solo}<small>{unidad}</small></p>
      ) : (
        <p className="cifra">
          <span className="antes">{fmt(antes, d)}</span>
          <i>→</i>
          <span className="despues">{fmt(despues, d)}</span>
          <small>{unidad}</small>
        </p>
      )}
      <span className="pie">{pie}</span>
    </article>
  );
}

function Constructor({ filtros, escenarios, normas, onEjecutado }) {
  const [esc, setEsc] = useState("via_urbana");
  const [sel, setSel] = useState(["HEPA-H13"]);
  const [dur, setDur] = useState(20);
  const [rec, setRec] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const e = escenarios.find((x) => x.id === esc);

  const alternar = (c) => setSel((s) => (s.includes(c) ? s.filter((x) => x !== c) : [...s, c]));
  const sugerir = async () => {
    setErr("");
    try {
      const r = await api.recomendar({ ...e.mediana, volumen_m3: 12, caudal_m3h: 180 });
      setRec(r);
      if (r.filtros.length) setSel(r.filtros);
      if (r.duracion_sugerida_min) setDur(Math.min(120, r.duracion_sugerida_min));
    } catch (x) { setErr(x.message); }
  };
  const ejecutar = async () => {
    setBusy(true); setErr("");
    try { onEjecutado(await api.simular({ escenario: esc, filtros: sel, duracion_min: dur })); }
    catch (x) { setErr(x.message); }
    finally { setBusy(false); }
  };

  return (
    <div className="constructor">
      <label>Aire que ingresa
        <select value={esc} onChange={(ev) => { setEsc(ev.target.value); setRec(null); }}>
          {escenarios.map((x) => <option key={x.id} value={x.id}>{x.nombre}</option>)}
        </select>
      </label>
      <div className="mediana">
        {["pm25", "pm10", "co2", "co"].map((c) => (
          <span key={c}><b>{fmt(e.mediana[c], e.mediana[c] < 20 ? 1 : 0)}</b> {normas.etiqueta[c]}</span>
        ))}
      </div>
      <fieldset>
        <legend>Tren de filtros</legend>
        <div className="chips">
          {filtros.map((f) => (
            <button type="button" key={f.codigo} className={sel.includes(f.codigo) ? "chip on" : "chip"} onClick={() => alternar(f.codigo)} title={f.descripcion}>
              {f.nombre}
            </button>
          ))}
        </div>
      </fieldset>
      <label>Tiempo de funcionamiento · <b>{dur} min</b>
        <input type="range" min="5" max="90" step="1" value={dur} onChange={(ev) => setDur(+ev.target.value)} />
      </label>
      <div className="acciones">
        <button type="button" className="sec" onClick={sugerir}>Sugerir tren y tiempo</button>
        <button type="button" className="pri" disabled={busy || !sel.length} onClick={ejecutar}>{busy ? "Procesando…" : "Ejecutar tratamiento"}</button>
      </div>
      {rec && (
        <div className="rec">
          <p>{!rec.prediccion ? "El aire ya cumple las guías: no hace falta tratarlo." : rec.duracion_sugerida_min ? <>Tiempo estimado hasta norma: <b>{fmt(rec.prediccion.minutos, 1)} min</b> (base: {Object.values(rec.prediccion.fuente).includes("historial") ? "historial de la planta" : "catálogo nominal"}).</> : "Con este tren la norma no es alcanzable para todos los contaminantes."}</p>
          <ul>{rec.razones.map((r, i) => <li key={i}>{r}</li>)}</ul>
        </div>
      )}
      {err && <p className="error">{err}</p>}
    </div>
  );
}

function Alertas({ datos }) {
  if (!datos) return null;
  const tot = datos.conteo.por_severidad || {};
  return (
    <div className="alertas">
      <div className="resumen-alertas">
        {["critica", "alta", "media"].map((s) => (<span key={s} className={`sev ${s}`}><b>{tot[s] || 0}</b> {s === "critica" ? "críticas" : s === "alta" ? "altas" : "medias"}</span>))}
      </div>
      <ul>
        {datos.items.slice(0, 9).map((a) => (
          <li key={a.id} className={a.severidad}>
            <span className="punto" />
            <div>
              <p>{a.mensaje}</p>
              <small>{a.lote} · {new Date(a.ts).toLocaleString("es-CO", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })} · {a.tipo.replaceAll("_", " ").toLowerCase()}</small>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function App() {
  const [d, setD] = useState(null);
  const [lote, setLote] = useState(null);
  const [cont, setCont] = useState("pm25");
  const [ultimo, setUltimo] = useState(null);
  const [error, setError] = useState("");

  const cargar = useCallback(async (seleccionar) => {
    try {
      const [kpis, norma, reloj, trenes, lotes, alertas, ejecutivo, modelo, filtros, escenarios, normas] = await Promise.all([
        api.kpis(), api.norma(), api.reloj(), api.trenes(), api.lotes(40), api.alertas(), api.ejecutivo(), api.modelo(), api.filtros(), api.escenarios(), api.normas(),
      ]);
      setD({ kpis, norma, reloj, trenes, lotes, alertas, ejecutivo, modelo, filtros, escenarios, normas });
      const id = seleccionar ?? lotes.find((l) => l.filtros.includes("HEPA-H13") && ["CUMPLE_OMS", "CUMPLE_NORMA"].includes(l.clasificacion))?.id ?? lotes[0]?.id;
      if (id) setLote(await api.lote(id));
    } catch (e) { setError(e.message); }
  }, []);
  useEffect(() => { cargar(); }, [cargar]);

  const elegir = async (id) => setLote(await api.lote(+id));
  const ejecutado = async (serie) => { setUltimo(serie.lote); setLote(serie); await cargar(serie.lote.id); };

  const tiempo = useMemo(() => d?.lotes.filter((l) => l.t_meta_min != null && l.t_meta_min > 0).map((l) => l.t_meta_min).sort((a, b) => a - b) ?? [], [d]);
  if (error) return <main className="vacio"><h1>alento</h1><p>No se pudo conectar con la API: {error}</p></main>;
  if (!d) return <main className="vacio"><h1>alento</h1><p>Cargando mediciones…</p></main>;
  const k = d.kpis;
  const L = lote?.lote;
  const clase = L ? CLASES[L.clasificacion] || [L.clasificacion, "neutro"] : null;

  return (
    <div className="app">
      <header className="cabecera">
        <div className="marca">
          <h1>alento</h1>
          <p>inteligencia del aire · admisión, depuración y verificación</p>
        </div>
        <div className="cabecera-der">
          <span>{k.lotes} tratamientos · {new Date(k.desde).toLocaleDateString("es-CO", { day: "numeric", month: "short" })} – {new Date(k.hasta).toLocaleDateString("es-CO", { day: "numeric", month: "short", year: "numeric" })}</span>
          <a className="boton-linea" href="/api/reportes/lotes.csv">Descargar CSV</a>
        </div>
      </header>

      <main>
        <section className="indicadores" aria-label="Indicadores principales">
          <Indicador etiqueta="PM2.5 · antes → después" antes={k.pm25.entrada} despues={k.pm25.salida} unidad="µg/m³" d={1} pie={`${fmt(k.pm25.reduccion, 0)} % menos · norma 24 h: 37`} />
          <Indicador etiqueta="CO₂ · antes → después" antes={k.co2.entrada} despues={k.co2.salida} unidad="ppm" d={0} pie={`${fmt(k.co2.reduccion, 0)} % menos · el más difícil de filtrar`} />
          <Indicador etiqueta="Reducción de contaminantes" solo={fmt(k.reduccion_global, 0)} unidad="%" pie={`media por lote, sobre los contaminantes que lo requerían`} />
          <Indicador etiqueta="Tiempo de purificación" solo={fmt(k.t_meta_mediana_min, 1)} unidad="min" pie={`mediana hasta cumplir la norma · alcanzada en ${fmt(k.t_meta_alcanzada_pct, 0)} % de los lotes`} />
        </section>

        <div className="rejilla g-a">
          <Seccion n="01" titulo="Distancia a la norma" nota="Cada carril compara el promedio de ingreso (ocre) con el de salida (verde) frente al límite legal, en escala logarítmica. La línea punteada verde es la guía OMS 2021.">
            <DistanciaNorma datos={d.norma} />
          </Seccion>
          <Seccion n="02" titulo="Reloj del aire" nota="PM2.5 medio por hora. Hacia afuera, lo que entra; hacia adentro, lo que sale. Los anillos punteados marcan norma (rojo) y OMS (verde).">
            <RelojAire datos={d.reloj} limNorma={d.normas.norma.pm25} limOms={d.normas.oms.pm25} />
          </Seccion>
        </div>

        <div className="rejilla g-b">
          <Seccion n="03" titulo="Curva de depuración" className="curva">
            <div className="barra-curva">
              <select value={L?.id} onChange={(ev) => elegir(ev.target.value)} aria-label="Lote">
                {(ultimo && !d.lotes.some((l) => l.id === ultimo.id) ? [ultimo, ...d.lotes] : d.lotes).map((l) => (
                  <option key={l.id} value={l.id}>{l.codigo} · {nombreTren(l.firma)} · {new Date(l.ingreso_ts).toLocaleDateString("es-CO", { day: "2-digit", month: "short" })}</option>
                ))}
              </select>
              <div className="tabs">{CONT_TABS.map(([c, t]) => <button key={c} className={cont === c ? "on" : ""} onClick={() => setCont(c)}>{t}</button>)}</div>
            </div>
            {lote && <CurvaDepuracion serie={lote} cont={cont} fondo={d.normas.fondo} />}
            {L && (
              <dl className="ficha">
                <div><dt>Resultado</dt><dd><span className={`sello ${clase[1]}`}>{clase[0]}</span></dd></div>
                <div><dt>Severidad</dt><dd>{L.nivel_entrada} → {L.nivel_salida}</dd></div>
                <div><dt>Reducción global</dt><dd>{fmt(L.reduccion_global, 0)} %</dd></div>
                <div><dt>Tiempo a norma</dt><dd>{L.t_meta_min == null ? "no alcanzada" : `${fmt(L.t_meta_min, 1)} min`}</dd></div>
                <div><dt>Estimado antes de iniciar</dt><dd>{L.t_meta_pred_min == null ? "inalcanzable" : `${fmt(L.t_meta_pred_min, 1)} min`}</dd></div>
              </dl>
            )}
          </Seccion>
          <Seccion n="04" titulo="Nuevo tratamiento" nota="Módulos 1 y 2: elija el aire que ingresa, el tren de filtros y el tiempo. El sistema mide, depura y verifica.">
            <Constructor filtros={d.filtros} escenarios={d.escenarios} normas={d.normas} onEjecutado={ejecutado} />
          </Seccion>
        </div>

        <div className="rejilla g-c">
          <Seccion n="05" titulo="Trenes de filtros" nota="Cada punto es un tratamiento; la marca verde es la mediana y la banda, el rango intercuartílico. G4 prefiltro · HEPA · C carbón · CAT catalizador de CO · ABS absorbente de CO₂.">
            <TrenesFiltros trenes={d.trenes} />
          </Seccion>
          <Seccion n="06" titulo="Alertas" nota="Reglas sobre la norma, la eficiencia y un control EWMA del ingreso.">
            <Alertas datos={d.alertas} />
          </Seccion>
        </div>

        <div className="rejilla g-d">
          <Seccion n="07" titulo="Informe para decidir">
            <div className="informe">
              <h3>Hallazgos</h3>
              <ul>{d.ejecutivo.hallazgos.map((h, i) => <li key={i}>{h}</li>)}</ul>
              <h3>Acciones</h3>
              <ul>{d.ejecutivo.acciones.map((h, i) => <li key={i}>{h}</li>)}</ul>
              <div className="clases">
                {Object.entries(k.clasificaciones).map(([c, n]) => (<span key={c} className={`sello ${CLASES[c]?.[1] || "neutro"}`}>{CLASES[c]?.[0] || c} · {n}</span>))}
              </div>
            </div>
          </Seccion>
          <Seccion n="08" titulo="¿Cuánto tarda? El modelo, auditado" nota="Validación temporal: se entrena con los primeros lotes y se predice el resto.">
            {d.modelo.pares ? (
              <div className="modelo">
                <PredVsReal pares={d.modelo.pares} />
                <dl>
                  <div><dt>Error medio del modelo</dt><dd>{fmt(d.modelo.mae_modelo_min, 1)} min</dd></div>
                  <div><dt>Solo con el catálogo</dt><dd>{fmt(d.modelo.mae_a_priori_min, 1)} min</dd></div>
                  <div><dt>Siempre la mediana</dt><dd>{fmt(d.modelo.mae_baseline_min, 1)} min</dd></div>
                  <div><dt>R² · casos evaluados</dt><dd>{fmt(d.modelo.r2_modelo, 2)} · {d.modelo.n_evaluados}</dd></div>
                </dl>
              </div>
            ) : <p className="nota">{d.modelo.mensaje}</p>}
          </Seccion>
        </div>
      </main>

      <footer>
        <p>Límites: Resolución 2254 de 2017 (MinAmbiente) y guías de calidad del aire de la OMS (2021). CO₂ no está regulado; se usa 1 000 ppm como umbral operativo. Los datos de este tablero son simulados; las eficiencias de filtro son supuestos de ingeniería.</p>
      </footer>
    </div>
  );
}
