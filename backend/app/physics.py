"""Cámara de depuración simulada.

El aire se modela como una cámara de mezcla perfecta de volumen V que recircula por un
tren de filtros con caudal Q. Para cada contaminante i:

    dC_i/dt = -(Q·η_i / V + k_dep_i) · (C_i − C_fondo_i)
    C_i(t)  = C_fondo_i + (C_i(0) − C_fondo_i) · exp(−k_i · t)
    k_i     = Q·η_i / V + k_dep_i

η_i es la eficiencia por paso del tren; para filtros en serie η = 1 − Π(1 − η_j).
Las eficiencias del catálogo son supuestos de ingeniería (órdenes de magnitud de fichas
técnicas típicas), no mediciones; el informe lo declara como limitación.

Esta clase es el *puerto de sensores simulado*: cualquier fuente real (Arduino, MQTT,
PMS5003 + MH-Z19 + MQ-7) puede sustituirla enviando lecturas a la API.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .norms import CONTAMINANTES

FONDO = {"pm25": 2.0, "pm10": 4.0, "co2": 420.0, "co": 0.1, "tvoc": 15.0}
DEPOSICION_H = {"pm25": 0.15, "pm10": 0.45, "co2": 0.0, "co": 0.0, "tvoc": 0.05}
RUIDO_ABS = {"pm25": 0.5, "pm10": 0.9, "co2": 12.0, "co": 0.05, "tvoc": 4.0}
RUIDO_REL = {"pm25": 0.035, "pm10": 0.045, "co2": 0.012, "co": 0.05, "tvoc": 0.05}
RESOLUCION = {"pm25": 0.1, "pm10": 0.1, "co2": 1.0, "co": 0.01, "tvoc": 1.0}

# (mediana, sigma lognormal) del aire que ingresa, por escenario
ESCENARIOS: dict[str, dict] = {
    "via_urbana": {
        "nombre": "Vía urbana con tráfico pesado",
        "perfil": {"pm25": (58, 0.35), "pm10": (98, 0.35), "co2": (640, 0.08), "co": (6.5, 0.40), "tvoc": (240, 0.40)},
    },
    "industrial": {
        "nombre": "Corredor industrial",
        "perfil": {"pm25": (115, 0.40), "pm10": (205, 0.40), "co2": (880, 0.12), "co": (13.0, 0.40), "tvoc": (640, 0.50)},
    },
    "quema_biomasa": {
        "nombre": "Humo de quema de biomasa",
        "perfil": {"pm25": (190, 0.35), "pm10": (240, 0.35), "co2": (1150, 0.15), "co": (26.0, 0.40), "tvoc": (880, 0.50)},
    },
    "recinto_ocupado": {
        "nombre": "Recinto cerrado con alta ocupación",
        "perfil": {"pm25": (19, 0.30), "pm10": (32, 0.30), "co2": (2300, 0.20), "co": (1.3, 0.50), "tvoc": (430, 0.40)},
    },
    "aire_de_referencia": {
        "nombre": "Aire de referencia (control)",
        "perfil": {"pm25": (8, 0.30), "pm10": (14, 0.30), "co2": (520, 0.06), "co": (0.5, 0.40), "tvoc": (90, 0.40)},
    },
}


def factor_horario(escenario: str, hora: float) -> float:
    """Modulación diaria de la concentración que ingresa (picos de movilidad, jornada industrial)."""
    def pico(h0: float, ancho: float = 2.0) -> float:
        d = min(abs(hora - h0), 24 - abs(hora - h0))
        return math.exp(-(d**2) / (2 * ancho**2))

    if escenario == "via_urbana":
        return 0.55 + 0.95 * pico(7.5) + 1.05 * pico(18.0, 2.3)
    if escenario == "industrial":
        return 0.6 + 0.9 * pico(13.0, 4.5)
    if escenario == "quema_biomasa":
        return 0.7 + 0.8 * pico(20.5, 2.8) + 0.35 * pico(6.0, 2.0)
    if escenario == "recinto_ocupado":
        return 0.35 + 1.0 * pico(11.0, 3.0) + 0.7 * pico(16.0, 2.5)
    return 1.0


def generar_entrada(escenario: str, hora: float, rng: np.random.Generator) -> dict[str, float]:
    esc = ESCENARIOS[escenario]
    f = factor_horario(escenario, hora)
    out = {}
    for k in CONTAMINANTES:
        mediana, sigma = esc["perfil"][k]
        base = FONDO[k] if k in ("co2",) else 0.0
        exceso = (mediana - base) * f if k == "co2" else mediana * f
        out[k] = max(FONDO[k], base + exceso * float(rng.lognormal(0.0, sigma)))
    return out


# Sesgo de la planta simulada: la «verdad» del simulador difiere del catálogo nominal
# (dispersión de fabricación, envejecimiento, fugas). El modelo predictivo no conoce estos
# factores; debe aprenderlos del historial. Se documentan en el informe como parte del diseño
# del experimento, no como hallazgo de laboratorio.
SESGO_PLANTA = {"PRE-G4": 0.85, "HEPA-H13": 1.0, "CARB-ACT": 0.80, "CAT-CO": 0.75, "ABS-CO2": 1.30}


def etas_reales(codigo: str, etas: dict[str, float]) -> dict[str, float]:
    f = SESGO_PLANTA.get(codigo, 1.0)
    return {k: min(v * f, 0.9995) for k, v in etas.items()}


def eficiencia_tren(etas: list[dict[str, float]]) -> dict[str, float]:
    """Eficiencia combinada de filtros en serie."""
    res = {}
    for k in CONTAMINANTES:
        pasa = 1.0
        for e in etas:
            pasa *= 1.0 - e.get(k, 0.0)
        res[k] = 1.0 - pasa
    return res


def tasas_decaimiento(etas: list[dict[str, float]], volumen_m3: float, caudal_m3h: float) -> dict[str, float]:
    """k_i en 1/h para el tren y la cámara dados."""
    eta = eficiencia_tren(etas)
    return {k: caudal_m3h * eta[k] / volumen_m3 + DEPOSICION_H[k] for k in CONTAMINANTES}


def concentracion(c0: float, k_h: float, t_h: float, contaminante: str) -> float:
    f = FONDO[contaminante]
    return f + max(c0 - f, 0.0) * math.exp(-k_h * t_h) if c0 > f else c0


def tiempo_a_meta_min(c0: float, k_h: float, meta: float, contaminante: str) -> float | None:
    """Minutos hasta bajar de `meta`. 0 si ya está por debajo; None si es inalcanzable."""
    f = FONDO[contaminante]
    if c0 <= meta:
        return 0.0
    if meta <= f or k_h <= 1e-3:
        return None
    return 60.0 * math.log((c0 - f) / (meta - f)) / k_h


def _ruido(valor: float, k: str, rng: np.random.Generator) -> float:
    sigma = RUIDO_ABS[k] + RUIDO_REL[k] * valor
    leido = valor + float(rng.normal(0.0, sigma))
    res = RESOLUCION[k]
    return max(0.0, round(leido / res) * res)


@dataclass
class Lectura:
    etapa: str  # entrada | proceso | salida
    t_seg: float
    valores: dict[str, float]


@dataclass
class CamaraSimulada:
    volumen_m3: float = 12.0
    caudal_m3h: float = 180.0
    intervalo_s: float = 30.0
    lecturas_verificacion: int = 3
    rng: np.random.Generator = field(default_factory=lambda: np.random.default_rng(0))

    def ejecutar(self, entrada_real: dict[str, float], etas: list[dict[str, float]], duracion_min: float) -> list[Lectura]:
        k = tasas_decaimiento(etas, self.volumen_m3, self.caudal_m3h)
        lecturas: list[Lectura] = []
        # 1) tres lecturas de ingreso (Módulo 1), 20 s entre ellas, antes de arrancar el ventilador
        for i in range(3):
            lecturas.append(Lectura("entrada", -40.0 + 20.0 * i, {c: _ruido(entrada_real[c], c, self.rng) for c in k}))
        # 2) proceso (Módulo 2)
        n = int(duracion_min * 60 // self.intervalo_s)
        for j in range(1, n + 1):
            t = j * self.intervalo_s
            lecturas.append(
                Lectura("proceso", t, {c: _ruido(concentracion(entrada_real[c], k[c], t / 3600.0, c), c, self.rng) for c in k})
            )
        # 3) verificación con el ventilador detenido (Módulo 3)
        t_fin = n * self.intervalo_s
        for i in range(self.lecturas_verificacion):
            t = t_fin + 20.0 * (i + 1)
            lecturas.append(
                Lectura("salida", t, {c: _ruido(concentracion(entrada_real[c], k[c], t_fin / 3600.0, c), c, self.rng) for c in k})
            )
        return lecturas
