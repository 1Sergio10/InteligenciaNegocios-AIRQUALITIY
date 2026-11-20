from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def crear_motor(url: str | None = None) -> Engine:
    url = url or settings.database_url
    if url.startswith("sqlite"):
        from sqlalchemy.pool import StaticPool

        kwargs = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url or url == "sqlite://":
            kwargs["poolclass"] = StaticPool
        return create_engine(url, **kwargs)
    return create_engine(url, pool_pre_ping=True)


engine = crear_motor()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

VISTA_EFICIENCIA = """
CREATE VIEW vw_eficiencia_lote AS
SELECT
    l.id AS lote_id,
    l.codigo,
    l.escenario,
    l.ingreso_ts,
    l.firma_tren,
    l.duracion_min,
    AVG(CASE WHEN m.etapa = 'entrada' THEN m.pm25 END) AS pm25_entrada,
    AVG(CASE WHEN m.etapa = 'salida'  THEN m.pm25 END) AS pm25_salida,
    AVG(CASE WHEN m.etapa = 'entrada' THEN m.pm10 END) AS pm10_entrada,
    AVG(CASE WHEN m.etapa = 'salida'  THEN m.pm10 END) AS pm10_salida,
    AVG(CASE WHEN m.etapa = 'entrada' THEN m.co2  END) AS co2_entrada,
    AVG(CASE WHEN m.etapa = 'salida'  THEN m.co2  END) AS co2_salida,
    AVG(CASE WHEN m.etapa = 'entrada' THEN m.co   END) AS co_entrada,
    AVG(CASE WHEN m.etapa = 'salida'  THEN m.co   END) AS co_salida
FROM lote l
JOIN medicion m ON m.lote_id = l.id
WHERE l.estado = 'cerrado'
GROUP BY l.id, l.codigo, l.escenario, l.ingreso_ts, l.firma_tren, l.duracion_min
"""


def crear_esquema(eng: Engine | None = None) -> None:
    from . import models  # noqa: F401  (registra las tablas)

    eng = eng or engine
    Base.metadata.create_all(eng)
    with eng.begin() as conn:
        conn.execute(text("DROP VIEW IF EXISTS vw_eficiencia_lote"))
        conn.execute(text(VISTA_EFICIENCIA))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
