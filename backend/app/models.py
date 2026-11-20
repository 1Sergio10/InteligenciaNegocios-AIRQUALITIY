"""Modelo relacional de Alento (3FN). Las mediciones viven en formato ancho porque el
conjunto de contaminantes es fijo y casi todas las consultas del tablero los comparan
entre sí por fila."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Filtro(Base):
    __tablename__ = "filtro"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(24), unique=True)
    nombre: Mapped[str] = mapped_column(String(80))
    tecnologia: Mapped[str] = mapped_column(String(80))
    descripcion: Mapped[str] = mapped_column(Text, default="")
    eta_pm25: Mapped[float] = mapped_column(Float, default=0.0)
    eta_pm10: Mapped[float] = mapped_column(Float, default=0.0)
    eta_co2: Mapped[float] = mapped_column(Float, default=0.0)
    eta_co: Mapped[float] = mapped_column(Float, default=0.0)
    eta_tvoc: Mapped[float] = mapped_column(Float, default=0.0)

    def etas(self) -> dict[str, float]:
        return {k: getattr(self, f"eta_{k}") for k in ("pm25", "pm10", "co2", "co", "tvoc")}


class Lote(Base):
    """Un tratamiento: entra aire contaminado, se depura, se verifica."""

    __tablename__ = "lote"
    __table_args__ = (
        CheckConstraint("estado IN ('abierto','cerrado')", name="ck_lote_estado"),
        Index("ix_lote_ingreso", "ingreso_ts"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(24), unique=True)
    escenario: Mapped[str] = mapped_column(String(32))
    estado: Mapped[str] = mapped_column(String(10), default="abierto")
    ingreso_ts: Mapped[datetime] = mapped_column(DateTime)
    fin_ts: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duracion_min: Mapped[float] = mapped_column(Float)
    volumen_m3: Mapped[float] = mapped_column(Float, default=12.0)
    caudal_m3h: Mapped[float] = mapped_column(Float, default=180.0)
    firma_tren: Mapped[str] = mapped_column(String(120), default="")
    # resultados (se calculan al cerrar; se guardan para que el tablero no recalcule)
    isr_entrada: Mapped[float | None] = mapped_column(Float, nullable=True)
    isr_salida: Mapped[float | None] = mapped_column(Float, nullable=True)
    nivel_entrada: Mapped[str | None] = mapped_column(String(12), nullable=True)
    nivel_salida: Mapped[str | None] = mapped_column(String(12), nullable=True)
    clasificacion: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reduccion_global: Mapped[float | None] = mapped_column(Float, nullable=True)
    t_meta_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    t_meta_pred_min: Mapped[float | None] = mapped_column(Float, nullable=True)

    filtros: Mapped[list["LoteFiltro"]] = relationship(back_populates="lote", cascade="all, delete-orphan", order_by="LoteFiltro.orden")
    mediciones: Mapped[list["Medicion"]] = relationship(back_populates="lote", cascade="all, delete-orphan", order_by="Medicion.t_seg")
    alertas: Mapped[list["Alerta"]] = relationship(back_populates="lote", cascade="all, delete-orphan")


class LoteFiltro(Base):
    __tablename__ = "lote_filtro"

    lote_id: Mapped[int] = mapped_column(ForeignKey("lote.id", ondelete="CASCADE"), primary_key=True)
    filtro_id: Mapped[int] = mapped_column(ForeignKey("filtro.id"), primary_key=True)
    orden: Mapped[int] = mapped_column(Integer, default=0)

    lote: Mapped[Lote] = relationship(back_populates="filtros")
    filtro: Mapped[Filtro] = relationship()


class Medicion(Base):
    __tablename__ = "medicion"
    __table_args__ = (
        CheckConstraint("etapa IN ('entrada','proceso','salida')", name="ck_medicion_etapa"),
        Index("ix_medicion_lote_etapa", "lote_id", "etapa"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lote.id", ondelete="CASCADE"))
    etapa: Mapped[str] = mapped_column(String(8))
    ts: Mapped[datetime] = mapped_column(DateTime)
    t_seg: Mapped[float] = mapped_column(Float)  # segundos respecto al arranque del ventilador
    pm25: Mapped[float] = mapped_column(Float)
    pm10: Mapped[float] = mapped_column(Float)
    co2: Mapped[float] = mapped_column(Float)
    co: Mapped[float] = mapped_column(Float)
    tvoc: Mapped[float] = mapped_column(Float, default=0.0)

    lote: Mapped[Lote] = relationship(back_populates="mediciones")


class TasaDecaimiento(Base):
    """Característica extraída de cada proceso: k (1/h) estimada por regresión log-lineal.
    Alimenta el modelo predictivo de tiempo de purificación."""

    __tablename__ = "tasa_decaimiento"

    lote_id: Mapped[int] = mapped_column(ForeignKey("lote.id", ondelete="CASCADE"), primary_key=True)
    contaminante: Mapped[str] = mapped_column(String(8), primary_key=True)
    k_h: Mapped[float] = mapped_column(Float)
    r2: Mapped[float] = mapped_column(Float)
    n_puntos: Mapped[int] = mapped_column(Integer)


class Alerta(Base):
    __tablename__ = "alerta"
    __table_args__ = (Index("ix_alerta_ts", "ts"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lote.id", ondelete="CASCADE"))
    ts: Mapped[datetime] = mapped_column(DateTime)
    tipo: Mapped[str] = mapped_column(String(24))
    severidad: Mapped[str] = mapped_column(String(8))  # baja | media | alta | critica
    contaminante: Mapped[str | None] = mapped_column(String(8), nullable=True)
    valor: Mapped[float | None] = mapped_column(Float, nullable=True)
    umbral: Mapped[float | None] = mapped_column(Float, nullable=True)
    mensaje: Mapped[str] = mapped_column(Text)

    lote: Mapped[Lote] = relationship(back_populates="alertas")
