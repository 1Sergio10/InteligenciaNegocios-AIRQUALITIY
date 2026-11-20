import numpy as np
import pytest

from app import intelligence, physics
from app.norms import LIMITES_NORMA, LIMITES_OMS, clasificar_resultado, indice_severidad, nivel_de


def test_limites_co_convertidos_a_ppm():
    assert LIMITES_NORMA["co"] == pytest.approx(4.37, abs=0.01)  # 5 000 µg/m³ a 25 °C
    assert LIMITES_OMS["co"] == pytest.approx(3.49, abs=0.02)  # 4 mg/m³


def test_isr_y_niveles():
    en_limite = {k: LIMITES_NORMA[k] for k in LIMITES_NORMA}
    assert indice_severidad(en_limite) == pytest.approx(1.0)
    assert nivel_de(0.3) == "Bajo" and nivel_de(1.0) == "Alto" and nivel_de(9) == "Crítico"


def test_decaimiento_monotono_y_tiende_al_fondo():
    k = 6.0
    vals = [physics.concentracion(100.0, k, t / 60, "pm25") for t in (0, 5, 10, 60)]
    assert vals[0] == pytest.approx(100.0)
    assert all(a > b for a, b in zip(vals, vals[1:]))
    assert vals[-1] == pytest.approx(physics.FONDO["pm25"], abs=0.3)


def test_hepa_no_actua_sobre_gases():
    hepa = {"pm25": 0.995, "pm10": 0.999}
    eta = physics.eficiencia_tren([hepa])
    assert eta["co"] == 0 and eta["co2"] == 0
    k = physics.tasas_decaimiento([hepa], 12, 180)
    assert physics.tiempo_a_meta_min(500.0, k["co2"], 1000.0, "co2") == 0.0
    assert physics.tiempo_a_meta_min(2000.0, k["co2"], 1000.0, "co2") is None


def test_filtros_en_serie_combinan_eficiencias():
    eta = physics.eficiencia_tren([{"pm25": 0.5}, {"pm25": 0.5}])
    assert eta["pm25"] == pytest.approx(0.75)


def test_estimar_k_recupera_la_tasa_verdadera():
    rng = np.random.default_rng(1)
    k_real = 9.0
    t = np.arange(30, 900, 30.0)
    v = [physics._ruido(physics.concentracion(180.0, k_real, x / 3600, "pm25"), "pm25", rng) for x in t]
    k, r2, n = intelligence.estimar_k(list(t), v, "pm25")
    assert k == pytest.approx(k_real, rel=0.15) and r2 > 0.95


def test_clasificacion():
    ent = {"pm25": 120, "pm10": 200, "co": 10, "co2": 900}
    ok = {"pm25": 5, "pm10": 8, "co": 0.5, "co2": 800}
    assert clasificar_resultado(ok, {}, ent) == "CUMPLE_OMS"
    medio = {"pm25": 30, "pm10": 60, "co": 4, "co2": 900}
    assert clasificar_resultado(medio, {}, ent) == "CUMPLE_NORMA"
    mal = {"pm25": 100, "pm10": 190, "co": 9.5, "co2": 900}
    assert clasificar_resultado(mal, {c: 5.0 for c in ent}, ent) == "INSUFICIENTE"
    limpio = {"pm25": 5, "pm10": 8, "co": 0.5, "co2": 600}
    assert clasificar_resultado(limpio, {}, limpio) == "SIN_NECESIDAD"


def test_recomendador_pide_la_etapa_correcta():
    r = intelligence.recomendar_tren({"pm25": 80, "pm10": 150, "co": 8, "co2": 2600, "tvoc": 500})
    assert {"HEPA-H13", "CAT-CO", "ABS-CO2", "CARB-ACT"} <= set(r["filtros"])
    assert intelligence.recomendar_tren({"pm25": 5, "pm10": 9, "co": 0.2, "co2": 500, "tvoc": 50})["filtros"] == []


def test_ewma_detecta_un_salto_sostenido():
    rng = np.random.default_rng(0)
    base = list(rng.lognormal(np.log(50), 0.2, 60))
    assert not intelligence.ewma_anomalia(base)["anomalia"]
    assert intelligence.ewma_anomalia(base + [260, 280, 300])["anomalia"]
