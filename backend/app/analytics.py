"""Consultas analíticas que alimentan el tablero y los reportes."""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from . import intelligence, physics
from .models import Alerta, Filtro, Lote, Medicion, TasaDecaimiento
from .norms import CONTAMINANTES, ETIQUETA, LIMITES_NORMA, LIMITES_OMS, REGULADOS, UNIDAD, orden_de


def df_eficiencia(db: Session) -> pd.DataFrame:
    df = pd.read_sql(text("SELECT * FROM vw_eficiencia_lote ORDER BY ingreso_ts"), db.connection())
    if df.empty:
        return df
    df["ingreso_ts"] = pd.to_datetime(df["ingreso_ts"])
    for c in ("pm25", "pm10", "co2", "co"):
        df[f"red_{c}"] = 100.0 * (1.0 - df[f"{c}_salida"] / df[f"{c}_entrada"].where(df[f"{c}_entrada"] > 0))
    return df


def df_lotes(db: Session) -> pd.DataFrame:
    filas = db.scalars(select(Lote).where(Lote.estado == "cerrado").order_by(Lote.ingreso_ts)).all()
    return pd.DataFrame(
        [
            dict(
                lote_id=l.id, codigo=l.codigo, escenario=l.escenario, ingreso_ts=l.ingreso_ts, firma=l.firma_tren,
                duracion_min=l.duracion_min, isr_entrada=l.isr_entrada, isr_salida=l.isr_salida,
                nivel_entrada=l.nivel_entrada, nivel_salida=l.nivel_salida, clasificacion=l.clasificacion,
                reduccion_global=l.reduccion_global, t_meta_min=l.t_meta_min, t_meta_pred_min=l.t_meta_pred_min,
            )
            for l in filas
        ]
    )


def kpis(db: Session, ultimos_dias: int | None = None) -> dict:
    ef = df_eficiencia(db)
    lt = df_lotes(db)
    if ef.empty:
        return {"lotes": 0}
    if ultimos_dias:
        corte = ef["ingreso_ts"].max() - timedelta(days=ultimos_dias)
        ef, lt = ef[ef["ingreso_ts"] >= corte], lt[lt["ingreso_ts"] >= corte]
    out: dict = {"lotes": int(len(lt)), "desde": ef["ingreso_ts"].min().isoformat(), "hasta": ef["ingreso_ts"].max().isoformat()}
    for c in ("pm25", "pm10", "co2", "co"):
        out[c] = {
            "entrada": float(ef[f"{c}_entrada"].mean()),
            "salida": float(ef[f"{c}_salida"].mean()),
            "reduccion": float(100 * (1 - ef[f"{c}_salida"].sum() / ef[f"{c}_entrada"].sum())),
            "mediana_reduccion_lote": float(ef[f"red_{c}"].median()),
            "unidad": UNIDAD[c],
        }
    ok = lt["clasificacion"].isin(["CUMPLE_OMS", "CUMPLE_NORMA", "SIN_NECESIDAD"])
    tm = lt["t_meta_min"].dropna()
    out.update(
        reduccion_global=float(lt["reduccion_global"].mean()),
        tasa_cumplimiento=float(100 * ok.mean()),
        t_meta_mediana_min=float(tm.median()) if len(tm) else None,
        t_meta_alcanzada_pct=float(100 * lt["t_meta_min"].notna().mean()),
        duracion_media_min=float(lt["duracion_min"].mean()),
        clasificaciones={k: int(v) for k, v in lt["clasificacion"].value_counts().items()},
    )
    return out


def reloj_24h(db: Session) -> list[dict]:
    """PM2.5 medio por hora del día, a la entrada y a la salida (reloj radial del tablero)."""
    ef = df_eficiencia(db)
    if ef.empty:
        return []
    ef["hora"] = ef["ingreso_ts"].dt.hour
    g = ef.groupby("hora").agg(entrada=("pm25_entrada", "mean"), salida=("pm25_salida", "mean"), n=("lote_id", "count"))
    g = g.reindex(range(24))
    return [
        {"hora": int(h), "entrada": None if np.isnan(r.entrada) else float(r.entrada),
         "salida": None if np.isnan(r.salida) else float(r.salida), "n": 0 if np.isnan(r.n) else int(r.n)}
        for h, r in g.iterrows()
    ]


def por_tren(db: Session) -> list[dict]:
    lt = df_lotes(db)
    if lt.empty:
        return []
    ef = df_eficiencia(db)[["lote_id", "red_pm25", "red_pm10", "red_co2", "red_co"]]
    m = lt.merge(ef, on="lote_id")
    res = []
    for firma, g in m.groupby("firma"):
        res.append(
            {
                "firma": firma, "n": int(len(g)),
                "reduccion_mediana": float(g["reduccion_global"].median()),
                "reduccion_p25": float(g["reduccion_global"].quantile(0.25)),
                "reduccion_p75": float(g["reduccion_global"].quantile(0.75)),
                "puntos": [round(float(v), 1) for v in g["reduccion_global"]],
                "por_contaminante": {c: float(g[f"red_{c}"].median()) for c in ("pm25", "pm10", "co2", "co")},
                "cumplimiento": float(100 * g["clasificacion"].isin(["CUMPLE_OMS", "CUMPLE_NORMA", "SIN_NECESIDAD"]).mean()),
            }
        )
    return sorted(res, key=lambda r: -r["reduccion_mediana"])


def distancia_a_norma(db: Session, lote_id: int | None = None) -> list[dict]:
    """Razón concentración/límite antes y después (promedio general o de un lote)."""
    ef = df_eficiencia(db)
    if ef.empty:
        return []
    if lote_id:
        ef = ef[ef["lote_id"] == lote_id]
    out = []
    for c in ("pm25", "pm10", "co", "co2"):
        out.append(
            {
                "contaminante": c, "etiqueta": ETIQUETA[c], "unidad": UNIDAD[c],
                "entrada": float(ef[f"{c}_entrada"].mean()), "salida": float(ef[f"{c}_salida"].mean()),
                "limite_norma": LIMITES_NORMA[c], "limite_oms": LIMITES_OMS[c],
            }
        )
    return out


def serie_lote(db: Session, lote_id: int) -> dict:
    lote = db.get(Lote, lote_id)
    if lote is None:
        raise KeyError(lote_id)
    meds = db.scalars(select(Medicion).where(Medicion.lote_id == lote_id).order_by(Medicion.t_seg)).all()
    etas = [lf.filtro.etas() for lf in lote.filtros]
    k = physics.tasas_decaimiento(etas, lote.volumen_m3, lote.caudal_m3h)
    return {
        "lote": resumen_lote(lote),
        "puntos": [{"etapa": m.etapa, "t_seg": m.t_seg, **{c: getattr(m, c) for c in CONTAMINANTES}} for m in meds],
        "k_teorica_h": k,
        "k_estimada_h": {t.contaminante: t.k_h for t in db.scalars(select(TasaDecaimiento).where(TasaDecaimiento.lote_id == lote_id))},
        "limites": {"norma": LIMITES_NORMA, "oms": LIMITES_OMS},
    }


def resumen_lote(l: Lote) -> dict:
    return {
        "id": l.id, "codigo": l.codigo, "escenario": l.escenario, "estado": l.estado,
        "ingreso_ts": l.ingreso_ts.isoformat(), "duracion_min": l.duracion_min,
        "filtros": [lf.filtro.codigo for lf in l.filtros], "firma": l.firma_tren,
        "isr_entrada": l.isr_entrada, "isr_salida": l.isr_salida,
        "nivel_entrada": l.nivel_entrada, "nivel_salida": l.nivel_salida,
        "clasificacion": l.clasificacion, "reduccion_global": l.reduccion_global,
        "t_meta_min": l.t_meta_min, "t_meta_pred_min": l.t_meta_pred_min,
    }


def alertas_recientes(db: Session, limite: int = 40, solo_severas: bool = False) -> list[dict]:
    q = select(Alerta, Lote.codigo).join(Lote, Lote.id == Alerta.lote_id).order_by(Alerta.ts.desc(), Alerta.id.desc()).limit(limite)
    if solo_severas:
        q = q.where(Alerta.severidad.in_(["alta", "critica"]))
    return [
        {"id": a.id, "lote": cod, "ts": a.ts.isoformat(), "tipo": a.tipo, "severidad": a.severidad,
         "contaminante": a.contaminante, "mensaje": a.mensaje}
        for a, cod in db.execute(q)
    ]


def conteo_alertas(db: Session) -> dict:
    df = pd.read_sql(text("SELECT tipo, severidad, COUNT(*) AS n FROM alerta GROUP BY tipo, severidad"), db.connection())
    return {"por_tipo": {t: int(g["n"].sum()) for t, g in df.groupby("tipo")},
            "por_severidad": {s: int(g["n"].sum()) for s, g in df.groupby("severidad")}}


def evaluar_modelo(db: Session, fraccion_entrenamiento: float = 0.7) -> dict:
    """Validación temporal del modelo de tiempo de purificación.

    Se entrena con los primeros lotes y se predice el resto con la misma regla que usa el
    sistema en producción. Se compara contra un baseline sin información de física
    (la mediana del tiempo observado en entrenamiento). Los lotes cuya meta no se alcanzó
    en la duración configurada están censurados y se cuentan aparte.
    """
    lt = df_lotes(db)
    if len(lt) < 30:
        return {"n": int(len(lt)), "mensaje": "Se necesitan al menos 30 lotes cerrados."}
    corte = int(len(lt) * fraccion_entrenamiento)
    train, test = lt.iloc[:corte], lt.iloc[corte:]
    tasas = pd.read_sql(
        text("SELECT t.lote_id, t.contaminante, t.k_h FROM tasa_decaimiento t WHERE t.r2 > 0.8"), db.connection()
    ).merge(lt[["lote_id", "firma"]], on="lote_id")
    tr = tasas[tasas["lote_id"].isin(train["lote_id"])]
    med = intelligence.mediana_por_firma([(r.firma, r.contaminante, r.k_h) for r in tr.itertuples()])
    ef = df_eficiencia(db).set_index("lote_id")
    filtros = {f.codigo: f for f in db.scalars(select(Filtro))}
    reales, pred_modelo, pred_prior = [], [], []
    baseline = float(train["t_meta_min"].dropna().median())
    censurados = 0
    for r in test.itertuples():
        if r.t_meta_min is None or (isinstance(r.t_meta_min, float) and np.isnan(r.t_meta_min)):
            censurados += 1
            continue
        lote = db.get(Lote, int(r.lote_id))
        entrada = {c: float(ef.loc[r.lote_id, f"{c}_entrada"]) if c in ("pm25", "pm10", "co2", "co") else 0.0 for c in CONTAMINANTES}
        etas = [filtros[cod].etas() for cod in r.firma.split("+")]
        k0 = intelligence.k_prior(etas, lote.volumen_m3, lote.caudal_m3h)
        khist = {c: med.get((r.firma, c)) for c in CONTAMINANTES}
        p = intelligence.predecir_tiempo_meta(entrada, khist, k0)["minutos"]
        p0 = intelligence.predecir_tiempo_meta(entrada, {}, k0)["minutos"]
        if p is None or p0 is None:
            continue
        reales.append(float(r.t_meta_min)); pred_modelo.append(p); pred_prior.append(p0)
    if not reales:
        return {"n": int(len(lt)), "mensaje": "Sin casos evaluables."}
    y, a, b = np.array(reales), np.array(pred_modelo), np.array(pred_prior)
    mae = lambda p: float(np.mean(np.abs(p - y)))
    ss_tot = float(((y - y.mean()) ** 2).sum()) or 1e-12
    return {
        "n_total": int(len(lt)), "n_entrenamiento": int(len(train)), "n_prueba": int(len(test)),
        "n_evaluados": int(len(y)), "n_censurados": int(censurados),
        "mae_modelo_min": mae(a), "mae_a_priori_min": mae(b), "mae_baseline_min": float(np.mean(np.abs(baseline - y))),
        "r2_modelo": 1.0 - float(((y - a) ** 2).sum()) / ss_tot,
        "sesgo_modelo_min": float(np.mean(a - y)),
        "pares": [{"real": float(i), "pred": float(j)} for i, j in zip(y, a)],
    }


def reporte_ejecutivo(db: Session) -> dict:
    k = kpis(db)
    if not k.get("lotes"):
        return {"hallazgos": [], "acciones": []}
    trenes = por_tren(db)
    hall, acc = [], []
    hall.append(f"Se trataron {k['lotes']} lotes; el aire de salida cumplió norma u OMS en {k['tasa_cumplimiento']:.0f} % de los casos.")
    hall.append(f"PM2.5 bajó de {k['pm25']['entrada']:.1f} a {k['pm25']['salida']:.1f} µg/m³ ({k['pm25']['reduccion']:.0f} % de reducción agregada).")
    hall.append(f"El CO₂ solo bajó {k['co2']['reduccion']:.0f} %: es el contaminante más difícil de tratar con filtración.")
    if trenes:
        mejor, peor = trenes[0], trenes[-1]
        hall.append(f"Mejor tren por mediana de reducción: {mejor['firma']} ({mejor['reduccion_mediana']:.0f} %). Peor: {peor['firma']} ({peor['reduccion_mediana']:.0f} %).")
    if k.get("t_meta_alcanzada_pct") is not None and k["t_meta_alcanzada_pct"] < 100:
        acc.append(f"En {100 - k['t_meta_alcanzada_pct']:.0f} % de los lotes la norma no se alcanzó en el tiempo configurado: ampliar la duración o añadir las etapas que falten según el recomendador.")
    if k["co2"]["salida"] > LIMITES_NORMA["co2"]:
        acc.append("Para CO₂ complementar con ventilación con aire exterior; el absorbente es la etapa más lenta y costosa del tren.")
    acc.append("Recalibrar las eficiencias del catálogo con datos del fabricante o con ensayos en cámara antes de usar el sistema fuera del entorno simulado.")
    return {"hallazgos": hall, "acciones": acc, "kpis": k}
