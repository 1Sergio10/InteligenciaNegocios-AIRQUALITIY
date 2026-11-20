"""Genera un histórico reproducible de tratamientos simulados.

    python -m app.seed --dias 40 --por-dia 8

Los lotes se crean en orden cronológico y cada predicción de tiempo se hace solo con el
historial previo, de modo que `t_meta_pred_min` es una predicción genuinamente fuera de muestra.
"""
from __future__ import annotations

import argparse
import math
from datetime import datetime, timedelta

import numpy as np

from . import intelligence, physics, services
from .config import settings
from .db import SessionLocal, crear_esquema, engine
from .models import Lote

PESOS_ESCENARIO = {"via_urbana": 0.34, "industrial": 0.22, "quema_biomasa": 0.12, "recinto_ocupado": 0.24, "aire_de_referencia": 0.08}
ESTRATEGIAS = ["recomendado", "particulas", "hibrido", "completo", "aleatorio"]
PESOS_ESTRATEGIA = [0.34, 0.18, 0.16, 0.16, 0.16]


def _hora_ocupada(rng: np.random.Generator) -> float:
    # más ensayos en jornada laboral que de madrugada
    return float(np.clip(rng.normal(13.0, 5.2), 0.2, 23.8))


def generar(dias: int, por_dia: int, fin: datetime, semilla: int) -> int:
    rng = np.random.default_rng(semilla)
    crear_esquema()
    with SessionLocal() as db:
        services.sembrar_catalogo(db)
        if db.query(Lote).count():
            print("La base ya tiene lotes; no se siembra de nuevo.")
            return 0
        momentos = []
        for d in range(dias):
            dia = fin - timedelta(days=dias - 1 - d)
            for _ in range(por_dia):
                h = _hora_ocupada(rng)
                momentos.append(datetime(dia.year, dia.month, dia.day) + timedelta(hours=h))
        momentos.sort()
        nombres = list(PESOS_ESCENARIO)
        creados = 0
        for ts in momentos:
            esc = str(rng.choice(nombres, p=list(PESOS_ESCENARIO.values())))
            real = physics.generar_entrada(esc, ts.hour + ts.minute / 60, rng)
            estrategia = str(rng.choice(ESTRATEGIAS, p=PESOS_ESTRATEGIA))
            if estrategia == "recomendado":
                rec = intelligence.recomendar_tren(real)["filtros"] or ["HEPA-H13"]
                codigos = rec
            elif estrategia == "aleatorio":
                todos = [c[0] for c in services.CATALOGO]
                n = int(rng.integers(1, 4))
                codigos = [str(x) for x in rng.choice(todos, size=n, replace=False)]
            else:
                codigos = services.PRESETS[estrategia]
            filtros = services._filtros(db, codigos)
            if estrategia == "recomendado":
                p = services.prediccion_para(db, real, filtros, 12.0, 180.0)["minutos"]
                duracion = float(np.clip(math.ceil((p if p is not None else 30) + 3), 8, 60))
            else:
                duracion = float(rng.choice([10, 15, 20, 25, 30]))
            services.simular_lote(db, esc, codigos, duracion, ts.replace(microsecond=0), rng, entrada_real=real)
            creados += 1
        return creados


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=40)
    ap.add_argument("--por-dia", type=int, default=8)
    ap.add_argument("--fin", default="2026-11-19", help="Último día del histórico (AAAA-MM-DD)")
    a = ap.parse_args()
    n = generar(a.dias, a.por_dia, datetime.fromisoformat(a.fin), settings.semilla)
    print(f"Lotes creados: {n} · motor: {engine.url.render_as_string(hide_password=True)}")
