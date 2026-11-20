"""Casos de uso: abrir un lote, registrar lecturas, cerrar y calcular resultados."""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import intelligence, physics
from .models import Alerta, Filtro, Lote, LoteFiltro, Medicion, TasaDecaimiento
from .norms import (
    CO2_CRITICO,
    CONTAMINANTES,
    ETIQUETA,
    LIMITES_NORMA,
    LIMITES_OMS,
    REGULADOS,
    UNIDAD,
    clasificar_resultado,
    indice_severidad,
    nivel_de,
)

CATALOGO = [
    ("PRE-G4", "Prefiltro G4", "Medio fibroso grueso", "Retiene polvo grueso y protege las etapas finas.",
     dict(pm25=0.08, pm10=0.35)),
    ("HEPA-H13", "HEPA H13", "Filtro de partículas de alta eficiencia", "≥ 99,95 % a la partícula más penetrante; no actúa sobre gases.",
     dict(pm25=0.995, pm10=0.999)),
    ("CARB-ACT", "Carbón activado", "Adsorción física", "Adsorbe vapores orgánicos; retiene muy poco CO y nada de CO₂.",
     dict(pm25=0.03, pm10=0.08, co=0.03, tvoc=0.55)),
    ("CAT-CO", "Catalizador de CO", "Oxidación catalítica (tipo hopcalita)", "Oxida CO a CO₂ sobre un lecho catalítico.",
     dict(co=0.45)),
    ("ABS-CO2", "Absorbente de CO₂", "Absorción química (aminas / zeolita)", "Captura CO₂; es la etapa más lenta del sistema.",
     dict(co2=0.15)),
]

PRESETS = {
    "particulas": ["HEPA-H13"],
    "hibrido": ["HEPA-H13", "CARB-ACT"],
    "completo": ["PRE-G4", "HEPA-H13", "CARB-ACT", "CAT-CO", "ABS-CO2"],
}


def sembrar_catalogo(db: Session) -> None:
    existentes = {c for (c,) in db.execute(select(Filtro.codigo))}
    for codigo, nombre, tec, desc, etas in CATALOGO:
        if codigo in existentes:
            continue
        db.add(Filtro(codigo=codigo, nombre=nombre, tecnologia=tec, descripcion=desc, **{f"eta_{k}": v for k, v in etas.items()}))
    db.commit()


def _filtros(db: Session, codigos: list[str]) -> list[Filtro]:
    if not codigos:
        raise ValueError("Seleccione al menos un filtro.")
    filas = {f.codigo: f for f in db.scalars(select(Filtro).where(Filtro.codigo.in_(codigos)))}
    faltan = [c for c in codigos if c not in filas]
    if faltan:
        raise ValueError(f"Filtros inexistentes: {', '.join(faltan)}")
    return [filas[c] for c in codigos]


def _siguiente_codigo(db: Session, ts: datetime) -> str:
    n = db.scalar(select(func.count(Lote.id))) or 0
    return f"AL-{ts:%y%m%d}-{n + 1:04d}"


def firma_de(codigos: list[str]) -> str:
    return "+".join(sorted(codigos))


# ───────────────────────────────────────────────────── historial para el modelo
def k_historico(db: Session, firma: str) -> dict[str, float | None]:
    filas = db.execute(
        select(Lote.firma_tren, TasaDecaimiento.contaminante, TasaDecaimiento.k_h)
        .join(TasaDecaimiento, TasaDecaimiento.lote_id == Lote.id)
        .where(Lote.firma_tren == firma, TasaDecaimiento.r2 > 0.8)
    ).all()
    med = intelligence.mediana_por_firma([tuple(f) for f in filas])
    return {c: med.get((firma, c)) for c in CONTAMINANTES}


def prediccion_para(db: Session, entrada: dict[str, float], filtros: list[Filtro], volumen: float, caudal: float) -> dict:
    etas = [f.etas() for f in filtros]
    firma = firma_de([f.codigo for f in filtros])
    return intelligence.predecir_tiempo_meta(entrada, k_historico(db, firma), intelligence.k_prior(etas, volumen, caudal))


# ───────────────────────────────────────────────────────────── ciclo del lote
def abrir_lote(
    db: Session,
    escenario: str,
    codigos: list[str],
    duracion_min: float,
    ingreso_ts: datetime,
    volumen_m3: float = 12.0,
    caudal_m3h: float = 180.0,
) -> Lote:
    filtros = _filtros(db, codigos)
    lote = Lote(
        codigo=_siguiente_codigo(db, ingreso_ts),
        escenario=escenario,
        estado="abierto",
        ingreso_ts=ingreso_ts,
        duracion_min=duracion_min,
        volumen_m3=volumen_m3,
        caudal_m3h=caudal_m3h,
        firma_tren=firma_de(codigos),
    )
    for i, f in enumerate(filtros):
        lote.filtros.append(LoteFiltro(filtro=f, orden=i))
    db.add(lote)
    db.flush()
    return lote


def registrar_lecturas(db: Session, lote: Lote, lecturas: list[physics.Lectura]) -> None:
    if lote.estado != "abierto":
        raise ValueError("El lote ya está cerrado.")
    for lec in lecturas:
        db.add(
            Medicion(
                lote_id=lote.id,
                etapa=lec.etapa,
                ts=lote.ingreso_ts + timedelta(seconds=lec.t_seg + 40.0),
                t_seg=lec.t_seg,
                **{k: float(lec.valores.get(k, 0.0)) for k in CONTAMINANTES},
            )
        )
    db.flush()


def _medias(meds: list[Medicion], etapa: str) -> dict[str, float]:
    sel = [m for m in meds if m.etapa == etapa]
    if not sel:
        raise ValueError(f"Faltan mediciones de la etapa «{etapa}».")
    return {c: float(np.mean([getattr(m, c) for m in sel])) for c in CONTAMINANTES}


def _cruce_meta(proceso: list[Medicion], c: str, meta: float) -> float | None:
    """Minutos hasta la primera lectura (mediana móvil de 3) bajo la meta; None si nunca ocurre."""
    v = np.array([getattr(m, c) for m in proceso], dtype=float)
    if len(v) < 3:
        return None
    suave = np.array([np.median(v[max(0, i - 2) : i + 1]) for i in range(len(v))])
    idx = np.where(suave <= meta)[0]
    return float(proceso[idx[0]].t_seg / 60.0) if len(idx) else None


def cerrar_lote(db: Session, lote: Lote) -> Lote:
    meds = list(lote.mediciones)
    ent, sal = _medias(meds, "entrada"), _medias(meds, "salida")
    proceso = sorted((m for m in meds if m.etapa == "proceso"), key=lambda m: m.t_seg)

    reducciones = {c: (100.0 * (1.0 - sal[c] / ent[c]) if ent[c] > 0 else 0.0) for c in CONTAMINANTES}
    tratables = [c for c in REGULADOS if ent[c] > LIMITES_OMS[c]] or list(REGULADOS)
    lote.isr_entrada = indice_severidad(ent)
    lote.isr_salida = indice_severidad(sal)
    lote.nivel_entrada, lote.nivel_salida = nivel_de(lote.isr_entrada), nivel_de(lote.isr_salida)
    lote.clasificacion = clasificar_resultado(sal, reducciones, ent)
    lote.reduccion_global = float(np.mean([reducciones[c] for c in tratables]))

    pendientes = [c for c in REGULADOS if ent[c] > LIMITES_NORMA[c]]
    cruces = [_cruce_meta(proceso, c, LIMITES_NORMA[c]) for c in pendientes]
    lote.t_meta_min = 0.0 if not pendientes else (None if any(x is None for x in cruces) else max(cruces))

    for c in CONTAMINANTES:
        est = intelligence.estimar_k([m.t_seg for m in proceso], [getattr(m, c) for m in proceso], c)
        if est:
            k, r2, n = est
            db.merge(TasaDecaimiento(lote_id=lote.id, contaminante=c, k_h=k, r2=r2, n_puntos=n))

    lote.fin_ts = lote.ingreso_ts + timedelta(seconds=(proceso[-1].t_seg + 100.0) if proceso else 0.0)
    lote.estado = "cerrado"
    db.flush()
    _generar_alertas(db, lote, ent, sal, reducciones)
    db.commit()
    return lote


def _alerta(db: Session, lote: Lote, tipo: str, sev: str, msg: str, cont: str | None = None, valor=None, umbral=None) -> None:
    db.add(Alerta(lote_id=lote.id, ts=lote.fin_ts or lote.ingreso_ts, tipo=tipo, severidad=sev, contaminante=cont, valor=valor, umbral=umbral, mensaje=msg))


def _generar_alertas(db: Session, lote: Lote, ent: dict, sal: dict, red: dict) -> None:
    for c in REGULADOS:
        lim = LIMITES_NORMA[c]
        u = UNIDAD[c]
        if ent[c] > lim:
            ratio = ent[c] / lim
            sev = "critica" if ratio >= 2 or (c == "co2" and ent[c] >= CO2_CRITICO) else "alta" if c != "co2" else "media"
            _alerta(db, lote, "INGRESO_SOBRE_NORMA", sev,
                    f"{ETIQUETA[c]} de ingreso en {ent[c]:.1f} {u}, {ratio:.1f}× el límite ({lim:g} {u}).", c, ent[c], lim)
        if sal[c] > lim:
            _alerta(db, lote, "SALIDA_SOBRE_NORMA", "alta",
                    f"Tras el tratamiento {ETIQUETA[c]} sigue en {sal[c]:.1f} {u} (límite {lim:g} {u}).", c, sal[c], lim)
            if lote.filtros and all(f.filtro.etas()[c] < 0.02 for f in lote.filtros):
                _alerta(db, lote, "FILTRO_NO_APLICABLE", "media",
                        f"Ningún filtro del tren actúa sobre {ETIQUETA[c]}; revise la recomendación de filtros.", c)
        elif ent[c] > LIMITES_OMS[c] and red[c] < 50.0:
            _alerta(db, lote, "BAJA_EFICIENCIA", "media",
                    f"{ETIQUETA[c]} bajó solo {red[c]:.0f} %: el tren no es el adecuado para este contaminante.", c, red[c], 50.0)

    hist = [
        float(v)
        for v in db.scalars(
            select(func.avg(Medicion.pm25))
            .join(Lote, Lote.id == Medicion.lote_id)
            .where(Medicion.etapa == "entrada", Lote.ingreso_ts < lote.ingreso_ts, Lote.estado == "cerrado", Lote.escenario == lote.escenario)
            .group_by(Lote.id, Lote.ingreso_ts)
            .order_by(Lote.ingreso_ts)
        )
    ]
    hist.append(ent["pm25"])
    ew = intelligence.ewma_anomalia(hist)
    if ew["anomalia"]:
        _alerta(db, lote, "ANOMALIA_INGRESO", "media",
                f"El ingreso de PM2.5 se aleja de su comportamiento reciente (EWMA {ew['z']:.0f} > {ew['limite']:.0f} µg/m³).",
                "pm25", ew["z"], ew["limite"])


def simular_lote(
    db: Session,
    escenario: str,
    codigos: list[str],
    duracion_min: float,
    ingreso_ts: datetime,
    rng: np.random.Generator,
    volumen_m3: float = 12.0,
    caudal_m3h: float = 180.0,
    entrada_real: dict[str, float] | None = None,
) -> Lote:
    if escenario not in physics.ESCENARIOS:
        raise ValueError(f"Escenario desconocido: {escenario}")
    filtros = _filtros(db, codigos)
    hora = ingreso_ts.hour + ingreso_ts.minute / 60.0
    real = entrada_real or physics.generar_entrada(escenario, hora, rng)
    camara = physics.CamaraSimulada(volumen_m3=volumen_m3, caudal_m3h=caudal_m3h, rng=rng)
    lecturas = camara.ejecutar(real, [physics.etas_reales(f.codigo, f.etas()) for f in filtros], duracion_min)

    lote = abrir_lote(db, escenario, codigos, duracion_min, ingreso_ts, volumen_m3, caudal_m3h)
    ent_obs = {c: float(np.mean([l.valores[c] for l in lecturas if l.etapa == "entrada"])) for c in CONTAMINANTES}
    pred = prediccion_para(db, ent_obs, filtros, volumen_m3, caudal_m3h)
    lote.t_meta_pred_min = pred["minutos"]
    registrar_lecturas(db, lote, lecturas)
    return cerrar_lote(db, lote)
