"""Umbrales normativos y utilidades de severidad.

Fuentes:
  * Resolución 2254 de 2017 (MinAmbiente, Colombia): límites a 24 h de PM10 (75 µg/m³)
    y PM2.5 (37 µg/m³) vigentes desde el 1 de julio de 2018; CO a 8 h = 5 000 µg/m³.
  * OMS (2021), guías de calidad del aire: PM2.5 15 µg/m³ y PM10 45 µg/m³ (24 h),
    CO 4 mg/m³ (24 h).
  * CO2 no está regulado como contaminante criterio. Se usa 1 000 ppm como umbral de
    atención y 2 500 ppm como crítico, que son las concentraciones donde Satish et al.
    (2012) midieron deterioro en la toma de decisiones.

El CO se convierte de µg/m³ a ppm con las condiciones de referencia de la norma
(25 °C, 101,325 kPa):  1 ppm CO = 1,145 mg/m³.
"""
from __future__ import annotations

CONTAMINANTES = ("pm25", "pm10", "co2", "co", "tvoc")
REGULADOS = ("pm25", "pm10", "co", "co2")  # los que entran al índice de severidad

UNIDAD = {"pm25": "µg/m³", "pm10": "µg/m³", "co2": "ppm", "co": "ppm", "tvoc": "ppb"}
ETIQUETA = {"pm25": "PM2.5", "pm10": "PM10", "co2": "CO₂", "co": "CO", "tvoc": "COVT"}

_CO_UGM3_POR_PPM = 1145.0
LIMITES_NORMA = {"pm25": 37.0, "pm10": 75.0, "co": round(5000.0 / _CO_UGM3_POR_PPM, 2), "co2": 1000.0}
LIMITES_OMS = {"pm25": 15.0, "pm10": 45.0, "co": round(4000.0 / _CO_UGM3_POR_PPM, 2), "co2": 1000.0}
CO2_CRITICO = 2500.0

NIVELES = (  # (cota superior de la razón concentración/límite, nombre, orden)
    (0.5, "Bajo", 0),
    (1.0, "Moderado", 1),
    (2.0, "Alto", 2),
    (4.0, "Muy alto", 3),
    (float("inf"), "Crítico", 4),
)


def razon_a_norma(valores: dict[str, float | None]) -> dict[str, float]:
    """Concentración dividida por el límite de la Res. 2254 (o el umbral operativo de CO2)."""
    return {k: valores[k] / LIMITES_NORMA[k] for k in REGULADOS if valores.get(k) is not None}


def indice_severidad(valores: dict[str, float | None]) -> float:
    """ISR: máxima razón concentración/límite entre los contaminantes regulados.

    Un ISR de 1,0 significa que el peor contaminante está exactamente en el límite.
    """
    razones = razon_a_norma(valores)
    return max(razones.values()) if razones else 0.0


def nivel_de(isr: float) -> str:
    for cota, nombre, _ in NIVELES:
        if isr < cota:
            return nombre
    return NIVELES[-1][1]


def orden_de(nivel: str) -> int:
    return next(o for _, n, o in NIVELES if n == nivel)


def clasificar_resultado(salida: dict[str, float], reducciones: dict[str, float], entrada: dict[str, float]) -> str:
    """Clasificación del tratamiento (Módulo 3).

    CUMPLE_OMS      todo el aire de salida está dentro de las guías OMS 2021.
    CUMPLE_NORMA    todo está dentro de la Res. 2254 (pero no de la OMS).
    PARCIAL         hubo mejora de al menos 50 % en algún contaminante problemático
                    pero queda algo fuera de norma.
    INSUFICIENTE    nada relevante mejoró o el aire sigue claramente fuera de norma.
    SIN_NECESIDAD   el aire ya entró dentro de la OMS: no había nada que tratar.
    """
    if all(entrada[k] <= LIMITES_OMS[k] for k in REGULADOS):
        return "SIN_NECESIDAD"
    if all(salida[k] <= LIMITES_OMS[k] for k in REGULADOS):
        return "CUMPLE_OMS"
    if all(salida[k] <= LIMITES_NORMA[k] for k in REGULADOS):
        return "CUMPLE_NORMA"
    problematicos = [k for k in REGULADOS if entrada[k] > LIMITES_NORMA[k]]
    if any(reducciones.get(k, 0.0) >= 50.0 for k in problematicos):
        return "PARCIAL"
    return "INSUFICIENTE"
