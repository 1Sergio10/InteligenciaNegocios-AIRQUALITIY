"""Componente de inteligencia de Alento.

Tres piezas pequeñas y auditables, en vez de una caja negra:

1. Recomendador de tren de filtración (reglas por contaminante dominante).
2. Detector de anomalías de ingreso con EWMA (Roberts, 1959).
3. Modelo de tiempo de purificación: regresión log-lineal de la caída exponencial,
   agregada por tren de filtros, con un a priori físico cuando aún no hay historial.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Iterable

import numpy as np

from . import physics
from .norms import CO2_CRITICO, LIMITES_NORMA, LIMITES_OMS, REGULADOS

# ──────────────────────────────────────────────────────────────── recomendador
COVT_REFERENCIA_PPB = 300.0  # referencia operativa del proyecto (no es un límite normativo)


def recomendar_tren(entrada: dict[str, float]) -> dict:
    codigos: list[str] = []
    razones: list[str] = []
    pm_alto = entrada["pm25"] > LIMITES_OMS["pm25"] or entrada["pm10"] > LIMITES_OMS["pm10"]
    if pm_alto:
        if entrada["pm10"] > 2 * LIMITES_NORMA["pm10"]:
            codigos.append("PRE-G4")
            razones.append("PM10 por encima de 2 veces la norma: un prefiltro grueso protege al HEPA de la saturación.")
        codigos.append("HEPA-H13")
        razones.append("Material particulado sobre las guías OMS: el HEPA es la única etapa que lo captura con eficiencia alta.")
    if entrada["tvoc"] > COVT_REFERENCIA_PPB:
        codigos.append("CARB-ACT")
        razones.append("COV totales elevados: el carbón activado adsorbe vapores orgánicos; no captura partículas ni CO.")
    if entrada["co"] > LIMITES_OMS["co"]:
        codigos.append("CAT-CO")
        razones.append("CO sobre la guía OMS: ni el HEPA ni el carbón lo retienen; hace falta una etapa catalítica.")
    if entrada["co2"] > LIMITES_NORMA["co2"]:
        codigos.append("ABS-CO2")
        razones.append(
            "CO₂ sobre 1 000 ppm: solo un absorbente lo reduce y es lento. En un recinto real, ventilar con aire exterior sigue siendo más barato."
        )
        if entrada["co2"] > CO2_CRITICO:
            razones.append("Con más de 2 500 ppm conviene ventilar de inmediato, sin esperar al tratamiento.")
    if not codigos:
        razones.append("El aire ya cumple las guías OMS; el tratamiento no es necesario.")
    return {"filtros": codigos, "razones": razones}


# ───────────────────────────────────────────────────────────────── EWMA
def ewma_anomalia(historial: Iterable[float], lam: float = 0.3, L: float = 2.5, ventana: int = 60) -> dict:
    """EWMA sobre ln(PM2.5 de ingreso). Devuelve el último estadístico y su límite de control.

    Límite superior: μ + L·σ·sqrt(λ/(2−λ)), con μ y σ estimados con las observaciones
    previas (hasta `ventana`) para que la anomalía no contamine su propia línea base.
    """
    x = np.log(np.maximum(np.asarray(list(historial), dtype=float), 1e-3))
    if len(x) < 12:
        return {"anomalia": False, "z": None, "limite": None, "motivo": "historial insuficiente"}
    base = x[max(0, len(x) - 1 - ventana) : -1]
    mu, sd = float(base.mean()), float(base.std(ddof=1))
    z = mu
    for xi in x[-8:]:
        z = lam * xi + (1 - lam) * z
    limite = mu + L * sd * math.sqrt(lam / (2 - lam))
    return {"anomalia": bool(z > limite), "z": math.exp(z), "limite": math.exp(limite), "motivo": ""}


# ───────────────────────────────────────────────── estimación de tasas k
def estimar_k(t_seg: list[float], valores: list[float], contaminante: str) -> tuple[float, float, int] | None:
    """Regresión de ln(C − C_fondo) contra t. Solo usa puntos claramente por encima del ruido."""
    f = physics.FONDO[contaminante]
    piso = 4.0 * physics.RUIDO_ABS[contaminante]
    pts = [(t / 3600.0, v - f) for t, v in zip(t_seg, valores) if v - f > piso]
    if len(pts) < 4:
        return None
    t = np.array([p[0] for p in pts])
    y = np.log([p[1] for p in pts])
    pendiente, intercepto = np.polyfit(t, y, 1)
    pred = pendiente * t + intercepto
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum()) or 1e-12
    return max(0.0, -float(pendiente)), 1.0 - ss_res / ss_tot, len(pts)


# ─────────────────────────────────────── modelo de tiempo de purificación
def k_prior(etas: list[dict[str, float]], volumen: float, caudal: float) -> dict[str, float]:
    return physics.tasas_decaimiento(etas, volumen, caudal)


def predecir_tiempo_meta(
    entrada: dict[str, float],
    k_hist: dict[str, float | None],
    k_a_priori: dict[str, float],
) -> dict:
    """Minutos hasta que todos los contaminantes regulados queden bajo la norma.

    k_hist: mediana histórica de k por contaminante para este mismo tren (None si hay < 3 casos).
    """
    por_cont: dict[str, float | None] = {}
    fuente: dict[str, str] = {}
    inalcanzable = False
    total = 0.0
    for c in REGULADOS:
        meta = LIMITES_NORMA[c]
        k = k_hist.get(c)
        fuente[c] = "historial"
        if k is None:
            k = k_a_priori[c]
            fuente[c] = "a priori físico"
        t = physics.tiempo_a_meta_min(entrada[c], k, meta, c)
        por_cont[c] = t
        if t is None:
            inalcanzable = True
        else:
            total = max(total, t)
    return {"minutos": None if inalcanzable else total, "por_contaminante": por_cont, "fuente": fuente}


def mediana_por_firma(filas: list[tuple[str, str, float]], minimo: int = 3) -> dict[tuple[str, str], float]:
    """filas: (firma_tren, contaminante, k_h) → mediana por (firma, contaminante) si hay ≥ minimo."""
    acc: dict[tuple[str, str], list[float]] = defaultdict(list)
    for firma, cont, k in filas:
        acc[(firma, cont)].append(k)
    return {key: float(np.median(v)) for key, v in acc.items() if len(v) >= minimo}
