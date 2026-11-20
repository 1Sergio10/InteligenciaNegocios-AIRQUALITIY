from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Concentraciones(BaseModel):
    pm25: float = Field(ge=0, le=2000, description="µg/m³")
    pm10: float = Field(ge=0, le=3000, description="µg/m³")
    co2: float = Field(ge=300, le=40000, description="ppm")
    co: float = Field(ge=0, le=1000, description="ppm")
    tvoc: float = Field(default=0.0, ge=0, le=50000, description="ppb")


class SimularIn(BaseModel):
    escenario: str = "via_urbana"
    filtros: list[str] = Field(min_length=1)
    duracion_min: float = Field(default=20.0, ge=1, le=180)
    volumen_m3: float = Field(default=12.0, gt=0, le=500)
    caudal_m3h: float = Field(default=180.0, gt=0, le=5000)
    ingreso_ts: datetime | None = None
    entrada_manual: Concentraciones | None = None


class AbrirIn(BaseModel):
    escenario: str = "manual"
    filtros: list[str] = Field(min_length=1)
    duracion_min: float = Field(default=20.0, ge=1, le=180)
    volumen_m3: float = Field(default=12.0, gt=0, le=500)
    caudal_m3h: float = Field(default=180.0, gt=0, le=5000)
    ingreso_ts: datetime | None = None


class LecturaIn(Concentraciones):
    etapa: Literal["entrada", "proceso", "salida"]
    t_seg: float


class RecomendarIn(Concentraciones):
    volumen_m3: float = 12.0
    caudal_m3h: float = 180.0
