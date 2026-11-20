from __future__ import annotations

import csv
import io
import math
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import analytics, intelligence, physics, services
from .config import settings
from .db import SessionLocal, crear_esquema, get_db
from .models import Filtro, Lote
from .norms import CONTAMINANTES, ETIQUETA, LIMITES_NORMA, LIMITES_OMS, UNIDAD
from .schemas import AbrirIn, LecturaIn, RecomendarIn, SimularIn


@asynccontextmanager
async def lifespan(_: FastAPI):
    crear_esquema()
    with SessionLocal() as db:
        services.sembrar_catalogo(db)
    yield


app = FastAPI(title="Alento API", version="1.0.0", lifespan=lifespan,
              description="Monitoreo, depuración y verificación de aire con indicadores de inteligencia de negocios.")
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["*"], allow_headers=["*"])
_rng = np.random.default_rng()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)


# ───────────────────────────────────────────────────────────── catálogos
@app.get("/api/salud")
def salud(db: Session = Depends(get_db)):
    return {"estado": "ok", "lotes": len(db.scalars(select(Lote.id)).all())}


@app.get("/api/filtros")
def filtros(db: Session = Depends(get_db)):
    return [
        {"codigo": f.codigo, "nombre": f.nombre, "tecnologia": f.tecnologia, "descripcion": f.descripcion,
         "eficiencias": f.etas()}
        for f in db.scalars(select(Filtro).order_by(Filtro.id))
    ]


@app.get("/api/escenarios")
def escenarios():
    return [{"id": k, "nombre": v["nombre"], "mediana": {c: v["perfil"][c][0] for c in CONTAMINANTES}}
            for k, v in physics.ESCENARIOS.items()]


@app.get("/api/normas")
def normas():
    return {"norma": LIMITES_NORMA, "oms": LIMITES_OMS, "unidad": UNIDAD, "etiqueta": ETIQUETA,
            "presets": services.PRESETS, "fondo": physics.FONDO}


@app.post("/api/recomendacion")
def recomendacion(body: RecomendarIn, db: Session = Depends(get_db)):
    entrada = body.model_dump(exclude={"volumen_m3", "caudal_m3h"})
    rec = intelligence.recomendar_tren(entrada)
    pred = None
    if rec["filtros"]:
        fl = services._filtros(db, rec["filtros"])
        pred = services.prediccion_para(db, entrada, fl, body.volumen_m3, body.caudal_m3h)
    dur = None if not pred or pred["minutos"] is None else max(5, math.ceil(pred["minutos"] + 3))
    return {**rec, "prediccion": pred, "duracion_sugerida_min": dur}


# ───────────────────────────────────────────────────────────── lotes
@app.post("/api/lotes/simular", status_code=201)
def simular(body: SimularIn, db: Session = Depends(get_db)):
    try:
        lote = services.simular_lote(
            db, body.escenario, body.filtros, body.duracion_min, body.ingreso_ts or _utcnow(), _rng,
            body.volumen_m3, body.caudal_m3h, body.entrada_manual.model_dump() if body.entrada_manual else None,
        )
    except ValueError as e:
        raise HTTPException(422, str(e))
    return analytics.serie_lote(db, lote.id)


@app.post("/api/lotes", status_code=201)
def abrir(body: AbrirIn, db: Session = Depends(get_db)):
    try:
        lote = services.abrir_lote(db, body.escenario, body.filtros, body.duracion_min, body.ingreso_ts or _utcnow(),
                                   body.volumen_m3, body.caudal_m3h)
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return analytics.resumen_lote(lote)


@app.post("/api/lotes/{lote_id}/lecturas", status_code=201)
def lectura(lote_id: int, body: list[LecturaIn], db: Session = Depends(get_db)):
    lote = db.get(Lote, lote_id)
    if lote is None:
        raise HTTPException(404, "Lote no encontrado")
    try:
        services.registrar_lecturas(db, lote, [physics.Lectura(b.etapa, b.t_seg, b.model_dump(exclude={"etapa", "t_seg"})) for b in body])
    except ValueError as e:
        raise HTTPException(409, str(e))
    db.commit()
    return {"registradas": len(body)}


@app.post("/api/lotes/{lote_id}/cerrar")
def cerrar(lote_id: int, db: Session = Depends(get_db)):
    lote = db.get(Lote, lote_id)
    if lote is None:
        raise HTTPException(404, "Lote no encontrado")
    if lote.estado == "cerrado":
        raise HTTPException(409, "El lote ya está cerrado")
    try:
        services.cerrar_lote(db, lote)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return analytics.serie_lote(db, lote.id)


@app.get("/api/lotes")
def lotes(limite: int = Query(30, ge=1, le=500), db: Session = Depends(get_db)):
    filas = db.scalars(select(Lote).where(Lote.estado == "cerrado").order_by(Lote.ingreso_ts.desc()).limit(limite)).all()
    return [analytics.resumen_lote(l) for l in filas]


@app.get("/api/lotes/{lote_id}")
def lote(lote_id: int, db: Session = Depends(get_db)):
    try:
        return analytics.serie_lote(db, lote_id)
    except KeyError:
        raise HTTPException(404, "Lote no encontrado")


# ───────────────────────────────────────────────────────────── analítica
@app.get("/api/kpis")
def kpis(dias: int | None = Query(None, ge=1, le=365), db: Session = Depends(get_db)):
    return analytics.kpis(db, dias)


@app.get("/api/analitica/reloj")
def reloj(db: Session = Depends(get_db)):
    return analytics.reloj_24h(db)


@app.get("/api/analitica/trenes")
def trenes(db: Session = Depends(get_db)):
    return analytics.por_tren(db)


@app.get("/api/analitica/norma")
def norma(lote_id: int | None = None, db: Session = Depends(get_db)):
    return analytics.distancia_a_norma(db, lote_id)


@app.get("/api/alertas")
def alertas(limite: int = Query(40, ge=1, le=300), severas: bool = False, db: Session = Depends(get_db)):
    return {"items": analytics.alertas_recientes(db, limite, severas), "conteo": analytics.conteo_alertas(db)}


@app.get("/api/modelo/evaluacion")
def evaluacion(db: Session = Depends(get_db)):
    return analytics.evaluar_modelo(db)


# ───────────────────────────────────────────────────────────── reportes
@app.get("/api/reportes/ejecutivo")
def ejecutivo(db: Session = Depends(get_db)):
    return analytics.reporte_ejecutivo(db)


@app.get("/api/reportes/lotes.csv")
def csv_lotes(db: Session = Depends(get_db)):
    ef = analytics.df_eficiencia(db)
    lt = analytics.df_lotes(db)
    df = lt.merge(ef.drop(columns=["codigo", "escenario", "ingreso_ts", "firma_tren", "duracion_min"]), on="lote_id")
    buf = io.StringIO()
    df.round({c: 2 for c in df.select_dtypes('number').columns}).to_csv(buf, index=False, quoting=csv.QUOTE_MINIMAL)
    return Response(buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="alento_lotes.csv"'})


# ───────────────────────────────────────────────────────────── interfaz web
if settings.static_dir.exists():
    app.mount("/assets", StaticFiles(directory=settings.static_dir / "assets"), name="assets")

    @app.get("/{ruta:path}", include_in_schema=False)
    def spa(ruta: str):
        archivo = settings.static_dir / ruta
        return FileResponse(archivo if ruta and archivo.is_file() else settings.static_dir / "index.html")
